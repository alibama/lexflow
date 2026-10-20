"""Asking new questions: the planner, the statute index, retrieval, the answer and its checks, the references,
AskBench scoring, the wiki's sub-pages, and the job claim."""
import json

import pytest

from lexflow import config
from lexflow.ask import answer as A
from lexflow.ask import bench as AB
from lexflow.ask import index as I
from lexflow.ask import plan as PL
from lexflow.ask import reference as R
from lexflow.store import db


def test_plan_concepts_kind_and_slug():
    p = PL.plan("How do I get my criminal record expunged or sealed?")
    assert p.kind == "process"
    flat = [t for g in p.groups for t in g]
    assert "expungement" in flat and "sealing" in flat and "criminal history" in flat
    assert PL.kind_of("How much do jails charge for phone calls?") == "facts"
    assert PL.slug("How do I get my criminal record expunged?") == PL.slug("how do i get my CRIMINAL record expunged")
    assert "sets" not in flat and "much" not in [t for g in PL.plan("How much does it cost?").groups for t in g]


def test_index_builds_from_the_statutes_and_reads_sections(con, va_statutes):
    from lexflow.municipal import statutes
    assert I.ensure("va")
    assert I.ready("va")
    hits = I.search("va", I.match([["public records"], ["request", "inspection"]], "and"))
    assert hits and hits[0]["ref"] == "2.2-3704"
    row = I.by_ref("va", "2.2-3704")
    assert row["citation"].endswith("2.2-3704") and "head" in row
    via_index = statutes.section_texts("va", ["2.2-3704"])[0]
    via_frame = statutes.section_texts("va", ["2.2-3704"], df=va_statutes)[0]
    assert via_index.text == via_frame.text and via_index.title == via_frame.title and via_index.code == via_frame.code
    assert I.effective("(Effective until December 1, 2026) Expungement") == (None, "2026-12-01")
    assert I.effective("(Effective January 1, 2027) Definitions") == ("2027-01-01", None)
    assert I._heading("–203.", "Md. Code, General Provisions § 4-203", "", "(a)(1) A custodian shall grant.") \
        == "Md. Code, General Provisions: A custodian shall grant."
    assert I.match([["and", "or"]]) == '("and" OR "or")'        # words FTS5 would read as operators are quoted


def test_retrieve_and_answer_a_records_question(con, va_statutes, monkeypatch):
    from lexflow.ask import pipeline as AP
    from lexflow.ask.retrieve import retrieve
    monkeypatch.setattr(config, "VECTORS", "tfidf")
    p = PL.plan("How do I request public records from a public body, and how long does it have to respond?")
    r = retrieve("va", p, embedder=None)
    assert r["chosen"] and r["chosen"][0]["ref"] == "2.2-3704"
    monkeypatch.setattr(config, "ASK_MIN_SIMILARITY", -1.0)    # no embedding server in the tests
    row = AP.answer_state(con, "records_q", p, "va", emb=None, log=lambda *_: None)
    ans = json.loads(row["answer"])
    text = va_statutes[va_statutes["section_number"] == "2.2-3704"].iloc[0]["text"]
    assert row["status"] == "answered" and ans["quotes"]
    assert all(q["text"] in text for q in ans["quotes"])              # every quote is the law's own words
    assert any(q["deadline"] for q in ans["quotes"])
    assert db.one(con, "SELECT status FROM asked_answers WHERE question_id='records_q' AND target='va'")


def test_retrieval_follows_the_codes_structure(con, va_statutes):
    from lexflow.ask import retrieve as RT
    assert I.ensure("va")
    row = I.by_ref("va", "50-73.83")                        # cites § 50-73.88 in its text
    assert "50-73.88" in [r["ref"] for r in RT.cited("va", row)]
    assert I.parent({"path": "Virginia Code / Title 2.2 / Chapter 37 / Section 2.2-3704"}) \
        == "Virginia Code / Title 2.2 / Chapter 37"
    assert I.parent({"path": "", "chapter": "Chapter 15. Judges."}) == "Chapter 15. Judges."


def test_verify_keeps_only_claims_the_quotes_support():
    quotes = [{"id": "Q1", "text": "The clerk may allow payment in installments over 90 days."},
              {"id": "Q2", "text": "A fee of $10 shall be charged."}]
    out = A.verify({"status": "answered", "claims": [
        {"text": "You can pay in installments.", "quotes": ["Q1"]},
        {"text": "The fee is $25.", "quotes": ["Q2"]},                     # a number the quote does not have
        {"text": "Judges always waive fees.", "quotes": []},               # cites nothing
        {"text": "There is a $10 fee [Q2].", "quotes": []}]}, quotes)     # an id inline counts
    assert [c["text"] for c in out["claims"]] == ["You can pay in installments.", "There is a $10 fee."]
    assert len(out["dropped"]) == 2 and out["status"] == "answered"


def _ref(text):
    return {"qid": "records_q", "question": "How do I request records?", "state": "va", "question_type": "facts",
            "coverage": "in_code", "profile": {"groups": [["public records"], ["request"]]},
            "gold_sections": [{"ref": "2.2-3704", "role": "primary", "why": "the procedure"}],
            "nuggets": [{"id": "N1", "text": "Five working days to respond.", "importance": "vital",
                         "section": "2.2-3704", "quote": "within five working days of receiving a request",
                         "slot": "deadline"}],
            "slots": {"deadline": [{"amount": 5, "unit": "working days", "anchor": "receipt", "nuggets": ["N1"]}]},
            "answer": "A public body must respond to a records request within five working days of receiving it "
                      "[N1]. It can be said in more words here so the answer is long enough to pass the length "
                      "check for a reference answer in the benchmark.",
            "out_of_corpus": [], "steps": None}


def test_reference_check_finds_bad_quotes_and_slots(con, va_statutes):
    spec = _ref(None)
    text = va_statutes[va_statutes["section_number"] == "2.2-3704"].iloc[0]["text"]
    assert "within five working days of receiving a request" in text
    assert R.check(spec, "records_q", "va")["ok"], R.check(spec, "records_q", "va")
    bad = json.loads(json.dumps(spec))
    bad["nuggets"][0]["quote"] = "within ten working days of receiving a request"
    bad["slots"]["deadline"][0]["amount"] = 12
    problems = R.check(bad, "records_q", "va")["problems"]
    assert any("not word for word" in p for p in problems) and any("12 does not appear" in p for p in problems)


def test_bench_scores_retrieval_nuggets_and_the_gate(con, va_statutes):
    spec = _ref(None)
    row = {"status": "answered", "sections": {"candidates": [{"id": I.by_ref("va", "2.2-3704")["id"]}] if I.ensure("va")
                                              else [], "chosen": []},
           "answer": {"quotes": [{"section": "2.2-3704", "text": "shall respond to the request within five working days "
                                                                   "of receiving a request by"}], "steps": []}}
    s = AB.score(spec, row)
    assert s["recall@5"] == 1.0 and s["mrr"] == 1.0 and s["vital_recall"] == 1.0
    assert s["citation_precision"] == 1.0 and s["slot_match"] == 1.0 and s["gate_correct"] == 1.0
    refused = AB.score(dict(spec, coverage="not_in_code"), dict(row, status="answered"))
    assert refused["gate_correct"] == 0.0 and refused["composite"] == 0.0


def test_claude_vs_claude_agreement(con, va_statutes):
    spec = _ref(None)
    assert I.ensure("va")
    same = AB.agreement(spec, json.loads(json.dumps(spec)))
    assert same["mean"] == 1.0 and same["sections"] == 1.0 and same["vital_nuggets"] == 1.0
    other = json.loads(json.dumps(spec))
    other["gold_sections"] = [{"ref": "13.1-1010", "role": "primary", "why": "x"}]
    other["coverage"] = "partial"
    diff = AB.agreement(spec, other)
    assert diff["sections"] == 0.0 and diff["coverage"] == 0.0 and diff["mean"] < 1.0


def test_place_processes_are_sub_pages(con, va_statutes, monkeypatch, tmp_path):
    from lexflow.municipal import build, locator, places
    from lexflow.municipal.questions import QUESTIONS
    from lexflow.publish import lexipedia as LX
    from test_places_strategies import _govs
    _govs(con)
    locator.run(con, QUESTIONS["records"], ["va"], log=lambda *_: None)
    build.build(con, "va", "records", use_llm=False, log=lambda *_: None)
    places.load_local(con, log=lambda *_: None)
    from lexflow.municipal import scoring
    scoring.run(con, "va", log=lambda *_: None)
    g = db.one(con, "SELECT * FROM governments WHERE name='City of Charlottesville'")
    # on the wiki only because it is marked for it and a named person has reviewed it (tests/test_gate0.py)
    from lexflow import signoff
    row = {"question_id": "jail_phone_rates", "target": g["gov_id"], "state": "va", "gov_id": g["gov_id"],
           "question_text": "Who sets jail phone rates?", "status": "not_found", "answer": json.dumps({"quotes": []}),
           "published": 1}
    from lexflow import reviewers
    listed = reviewers.add(con, "Ana Villamar", "researcher", added_by="operator")     # on the operator's list
    reviewer = {"reviewer": listed["id"], "date": "2026-10-01", "attested": True}
    signed = signoff.bind(reviewer, signoff.row_text(row, signoff.ASKED_TEXT))     # a sign-off of this text
    db.upsert(con, "asked_answers", [{**row, "reviewed_by": signed}])
    # recorded as this copy's review API records it (a page names a reviewer only for a review this copy recorded)
    reviewers.log_review(con, "review", row["question_id"], row["target"], listed["id"], signed["text_hash"],
                         at="2026-10-01T12:00:00Z")
    con.commit()
    pages = LX.all_pages(con)
    assert all(p.startswith("lexflow:") for p in pages)
    main = pages["lexflow:va:charlottesville"]
    assert "[[lexflow:va:charlottesville:records|" in main and "Who sets jail phone rates?" in main
    assert "lexflow:va:charlottesville:records" in pages and "lexflow:va:charlottesville:jail_phone_rates" in pages
    asked = pages["lexflow:va:charlottesville:jail_phone_rates"]
    assert "Drafted with an AI system from the statute text" in asked
    assert "Reviewed by Ana Villamar, researcher, on 1 October 2026" in asked
    assert "[[lexflow:va:charlottesville|" in pages["lexflow:va"]
    assert "===== What state law requires =====" not in main                # the detail is on the sub-page


def test_a_queued_job_is_claimed_once(con):
    from lexflow.pipeline import jobs
    jid = jobs.enqueue(con, "score", {})
    assert jobs.claim(con, jid) is True
    assert jobs.claim(con, jid) is False
    row = db.one(con, "SELECT status, runner FROM jobs WHERE id=?", jid)
    assert row["status"] == "running" and row["runner"] == jobs.RUNNER_ID


def test_ask_api_queues_and_lists(con, monkeypatch):
    from fastapi.testclient import TestClient
    from lexflow.api import app as API
    monkeypatch.setattr(config, "JOB_RUNNER", False)
    with TestClient(API.app) as c:
        assert c.get("/api/targets", params={"q": "virg"}).json()[0]["target"] == "va"
        r = c.post("/api/ask", json={"question": "How do I appeal a property tax assessment?", "targets": ["va"]})
        assert r.status_code == 200 and r.json()["question_id"] == PL.slug("How do I appeal a property tax assessment?")
        job = db.one(con, "SELECT step, args FROM jobs WHERE id=?", r.json()["job"])
        assert job["step"] == "ask" and json.loads(job["args"])["question_id"] == r.json()["question_id"]
        assert c.post("/api/ask", json={"question": "short", "targets": ["va"]}).status_code == 400
        assert c.get("/api/ask/suggestions").json()[0]["questions"]
        # the Processes page lists every asked question: its kind, state answers and draft maps
        from lexflow.ask import pipeline as AP
        qid = r.json()["question_id"]
        text = "How do I appeal a property tax assessment?"
        AP.save_question(con, text, PL.plan(text), qid)          # what the job does before it answers
        db.upsert(con, "asked_answers", [{"question_id": qid, "target": "va", "state": "va", "gov_id": None,
                                          "question_text": "How do I appeal a property tax assessment?",
                                          "status": "partial", "bpmn": "<definitions/>", "answer": "{}",
                                          "updated_at": db.now()}])
        con.commit()
        listed = {q["question_id"]: q for q in c.get("/api/ask").json()}[qid]
        assert listed["kind"] == "process" and listed["states"] == 1 and listed["maps"] == 1
        assert c.get(f"/api/ask/{qid}").json()["answers"][0]["map"] is True


# ------------------------------------------------------------------------------- one answer row per model
def test_asked_answers_are_keyed_by_model_and_an_old_store_is_rebuilt(tmp_path, monkeypatch):
    """The key of asked_answers is (question_id, target, model).  A store made before ``model`` joined the key is
    rebuilt once on connect: the rows keep their model, those without one are filed under the default
    (qwen3:1.7b), and nothing else changes."""
    import sqlite3
    path = tmp_path / "old.db"
    old = sqlite3.connect(path)
    old.executescript(db.SCHEMA.replace("model TEXT NOT NULL DEFAULT 'qwen3:1.7b'", "model TEXT")
                      .replace("PRIMARY KEY (question_id, target, model)", "PRIMARY KEY (question_id, target)"))
    old.execute("INSERT INTO asked_answers(question_id, target, state, status, model, published, updated_at, reviewed_by) "
                "VALUES ('q', 'va', 'va', 'answered', NULL, 1, '2026-10-01T00:00:00Z', 'r')")
    old.execute("INSERT INTO asked_answers(question_id, target, state, status, model, updated_at) "
                "VALUES ('q', 'dc', 'dc', 'partial', 'gemma3:1b', '2026-10-02T00:00:00Z')")
    old.commit()
    assert db.primary_key(old, "asked_answers") == ("question_id", "target")
    old.close()
    con = db.connect(path)
    try:
        assert db.primary_key(con, "asked_answers") == ("question_id", "target", "model")
        rows = db.rows(con, "SELECT * FROM asked_answers ORDER BY target")
        assert [(r["target"], r["model"], r["status"], r["published"], r["reviewed_by"]) for r in rows] == [
            ("dc", "gemma3:1b", "partial", 0, None), ("va", db.ASKED_DEFAULT_MODEL, "answered", 1, "r")]
        assert db.migrate_asked_answers(con) is False                      # once
        assert any(r[1] == "asked_answers_state" for r in con.execute("PRAGMA index_list(asked_answers)"))
        # a second model's answer to the same cell lands beside the first; an upsert without a model is the default's
        db.upsert(con, "asked_answers", [{"question_id": "q", "target": "va", "state": "va", "status": "partial",
                                          "model": "qwen3:8b", "updated_at": db.now()}])
        db.upsert(con, "asked_answers", [{"question_id": "q", "target": "va", "state": "va", "status": "not_found",
                                          "updated_at": db.now()}])
        rows = db.rows(con, "SELECT model, status FROM asked_answers WHERE target='va' ORDER BY model")
        assert [(r["model"], r["status"]) for r in rows] == [("qwen3:1.7b", "not_found"), ("qwen3:8b", "partial")]
        assert db.SYNCED["asked_answers"] == ("question_id", "target", "model")
    finally:
        con.close()


def test_readers_show_one_answer_per_target_the_preferred_model(con, monkeypatch):
    """With two models' answers to a cell, the ask API, the drafts of publish.graph and the wiki show one: the
    model LEXFLOW_ASK_PREFER names, else the best-scoring row; ``?model=`` reads the other."""
    from fastapi.testclient import TestClient
    from lexflow.api import app as API
    from lexflow.ask import prefer
    from lexflow.ask import pipeline as AP
    monkeypatch.setattr(config, "JOB_RUNNER", False)
    text = "How do I license a dog?"
    AP.save_question(con, text, PL.plan(text), "dog_q")
    base = {"question_id": "dog_q", "target": "va", "state": "va", "gov_id": None, "question_text": text,
            "sections": json.dumps({"chosen": [{"ref": "3.2-6524", "id": 1}]}), "bpmn": "<definitions/>",
            "facts": json.dumps({"steps": [{"id": "s1"}]}), "updated_at": db.now()}
    small = dict(base, model="qwen3:1.7b", status="partial", answer=json.dumps({"summary": None, "quotes": []}),
                 metrics=json.dumps({"quotes_checked": 4, "quote_misses": 1, "answered_at": db.now()}))
    big = dict(base, model="qwen3:8b", status="answered", answer=json.dumps({"summary": {"claims": [{"text": "c"}]},
                                                                            "quotes": []}),
               metrics=json.dumps({"quotes_checked": 4, "quote_misses": 0, "answered_at": db.now()}))
    db.upsert(con, "asked_answers", [small, big])
    con.commit()
    assert prefer.pick([small, big])["model"] == "qwen3:8b"            # answered beats partial
    assert [r["model"] for r in prefer.preferred([small, big, dict(small, target="dc")])] == ["qwen3:8b", "qwen3:1.7b"]
    with TestClient(API.app) as c:
        listed = {q["question_id"]: q for q in c.get("/api/ask").json()}["dog_q"]
        assert listed["answers"] == 1 and listed["answered"] == 1 and listed["partial"] == 0
        assert listed["models"] == ["qwen3:1.7b", "qwen3:8b"]
        brief = c.get("/api/ask/dog_q").json()["answers"]
        assert len(brief) == 1 and brief[0]["model"] == "qwen3:8b" and brief[0]["models"] == ["qwen3:1.7b", "qwen3:8b"]
        r = c.get("/api/ask/dog_q/va").json()
        assert r["model"] == "qwen3:8b" and r["status"] == "answered" and r["models"] == ["qwen3:1.7b", "qwen3:8b"]
        assert c.get("/api/ask/dog_q/va", params={"model": "qwen3:1.7b"}).json()["status"] == "partial"
        assert c.get("/api/ask/dog_q/va", params={"model": "nope"}).status_code == 404
        monkeypatch.setattr(config, "ASK_PREFER", "qwen3:1.7b")
        assert c.get("/api/ask/dog_q/va").json()["model"] == "qwen3:1.7b"
        monkeypatch.setattr(config, "ASK_PREFER", "")
    # the drafts for the store: one per question and state
    from lexflow.publish import graph as G
    build = G.Build(con, states=["va"], drafts=True, asked_drafts=True)
    drafts = [m for m in build.asked_rows() if m["question"] == "dog_q"]
    assert len(drafts) == 1 and drafts[0]["model_id"] == "asked:va:dog_q"
    # the wiki: one page per published answer, the preferred model's
    con.execute("UPDATE asked_answers SET published=1 WHERE question_id='dog_q'")
    con.commit()
    from lexflow.publish import lexipedia as LX
    assert len([r for r in prefer.preferred(db.rows(con, "SELECT * FROM asked_answers WHERE published=1"))]) == 1
    assert LX.published_asked(con, state="va") == []                      # nobody has reviewed either


def test_asker_json_mode_describes_the_schema_in_words_and_parses_the_reply():
    """``mode="json"``: the schema is shown in the prompt, Ollama's plain ``format: json`` is used (no grammar), the
    reply is parsed and must carry the required keys; a bad reply is retried once with a reminder."""
    from lexflow.extract.strategies import Asker

    class Client:
        model = "qwen3:8b"

        def __init__(self, replies):
            self.replies, self.calls = list(replies), []

        def chat(self, messages, schema=None, temperature=0.0, max_tokens=None):
            self.calls.append((messages, schema, max_tokens))
            return self.replies.pop(0)
    good = '<think>hm</think>{"status": "answered", "claims": [{"text": "Hearing within 15 days.", "quotes": ["Q1"]}]}'
    c = Client(["not json at all", good])
    out = Asker(c, mode="json", max_tokens=400).ask(A.SUMMARY_SYSTEM, "Question: ...", A.SUMMARY_SCHEMA)
    assert out["status"] == "answered" and out["claims"][0]["quotes"] == ["Q1"]
    assert len(c.calls) == 2 and c.calls[0][1] == "json" and c.calls[0][2] == 800
    system = c.calls[0][0][0]["content"]
    assert 'shaped like {"status": "answered|partial|not_found", "claims": [{"text": "...", "quotes": ["...", ...]}, ...]}' in system
    assert "valid JSON object with the keys status, claims" in c.calls[1][0][-1]["content"]
    # a reply without the required keys is a miss after the retry
    assert Asker(Client(['{"claims": []}', '{"nope": 1}']), mode="json").ask("s", "u", A.SUMMARY_SCHEMA) is None
    # the default mode is unchanged (schema), and LEXFLOW_ASK_MODE picks the mode of the pipeline's asker
    assert Asker(Client([]), mode="schema").mode == "schema" and config.ASK_MODE in ("schema", "json", "lines")
