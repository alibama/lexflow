"""The coverage test (lexflow.ask.coverage): the question file, the gold loader and its quote checks, the probe on a
tiny local store, the verdict rules, the step registration and the matrix writer."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from lexflow.ask import coverage as CV  # noqa: E402
from lexflow.publish import schema as SC  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------------------------- the questions
def test_question_file_shape_and_topic_slugs():
    qs = CV.questions()
    assert len(qs) == 57          # 49, and the eight retirement_* questions (docs/design/retirement-benefits.md)
    assert CV.check_questions(qs) == []
    topics = {v.slug for v in SC.VOCAB["topic"]}
    assert all(q["topic"] in topics for q in qs)
    assert len({q["id"] for q in qs}) == 57
    assert all(set(q["needs"]) <= set(CV.KINDS) and 2 <= len(q["phrasings"]) <= 3 for q in qs)
    assert {q["level"] for q in qs} <= set(CV.LEVELS)
    bad = CV.check_questions([{"id": "x", "text": "t", "topic": "nope", "audience": "resident", "level": "state",
                               "needs": ["who"], "phrasings": ["a", "b"]}])
    assert any("topic" in p for p in bad)


# ---------------------------------------------------------------------------------------------------- the gold
def test_gold_files_exist_for_every_question_in_both_states():
    qids = {q["id"] for q in CV.questions()}
    for st in ("va", "dc"):
        assert {qid for qid, s in CV.gold_cases([st])} == qids
        for qid in qids:
            g = CV.load_gold(st, qid)
            assert g["qid"] == qid and g["state"] == st and g["gold"] in CV.GOLD_KINDS
            if g["gold"] != "none":
                assert g["nuggets"] and all(n["kind"] in CV.KINDS and n["source"] in CV.SOURCES for n in g["nuggets"])


@pytest.mark.parametrize("state,qid", [("dc", "public_records"), ("dc", "police_incident_records"), ("va", "start_llc")])
def test_gold_loader_validates_quotes_against_the_index(con, va_statutes, state, qid):
    """Three entries whose sections are in the test fixtures: every quote is word for word in the index text, and a
    tampered quote is reported."""
    from lexflow.ask import index as I
    assert I.ensure(state)
    g = CV.load_gold(state, qid)
    r = CV.check_gold(g, state, qid, skip_missing=True)
    assert r["ok"], r["problems"]
    assert r["checked"] >= 2
    bad = json.loads(json.dumps(g))
    n = next(x for x in bad["nuggets"] if x["source"] == "index")
    n["quote"] = n["quote"] + " and some words the statute never says"
    r = CV.check_gold(bad, state, qid, skip_missing=True)
    assert not r["ok"] and any("not word for word" in p for p in r["problems"])


def test_gold_loader_validates_local_quotes_and_shape():
    g = CV.load_gold("va", "dog_license")
    local = [n for n in g["nuggets"] if n["source"] == "local"]
    assert local and g["local_process"]["process"] == "dog_license"
    text = CV.local_text(g["local_process"]["gov_id"], "dog_license")
    from lexflow import validate
    assert all(validate.quote_in(n["quote"], text) for n in local)
    none = CV.load_gold("dc", "noise_complaint")
    assert none["gold"] == "none" and none["nuggets"] == [] and CV.check_gold(none, "dc", "noise_complaint")["ok"]
    ref = CV.as_reference(g)
    assert ref["coverage"] == "in_code" and ref["gold_sections"] and all({"id", "quote", "importance"} <= set(n) for n in ref["nuggets"])


# --------------------------------------------------------------------------------------------------- the probe
@pytest.fixture()
def tiny_store(tmp_path, monkeypatch):
    """The hand-made items of test_sparql (a process with two steps, a role played by a body with a channel, a
    deadline with its quote, a fee and a rung) in an in-memory store."""
    pytest.importorskip("pyoxigraph")
    import sys
    from lexflow import config
    from lexflow.publish import ids as I
    from lexflow.publish import rdf
    sys.path.insert(0, str(ROOT / "tests"))
    from test_sparql import hand_made
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "t.db")
    monkeypatch.setattr(I, "IDS_PATH", tmp_path / "ids.json")
    m = I.IdMap()
    monkeypatch.setattr(I, "_default", m)
    out = rdf.write(hand_made(), tmp_path / "lexipedia.ttl", m)
    return CV.Store(live=False, store=rdf.memory_store(out), idmap=m)


def test_probe_counts_on_a_tiny_store(tiny_store):
    route = {"jurisdiction": "va", "gov_id": None, "topic": "public-records",
             "processes": [{"key": "lexflow:process:va.records", "scope": "state", "topic": "public-records"}],
             "process_keys": ["lexflow:process:va.records"]}
    p = CV.probe(route, store=tiny_store)
    assert p["source"] == "store" and p["errors"] == []
    assert [x["key"] for x in p["processes"]] == ["lexflow:process:va.records"]
    assert p["processes"][0]["status"] == "reviewed" and p["state_process"] and not p["local_process"]
    c = p["counts"]
    assert c["processes"] == 1 and c["reviewed"] == 1
    assert c["steps"] == 2 and c["steps_with_bearer"] == 2
    assert c["bearers_resolved"] == 1                    # the custodian's body; the requester is a private party
    assert c["bodies_with_channels"] == 1               # the body has an email address
    assert c["deadlines"] == 2 and c["deadlines_quoted"] == 1   # the step's (quoted) and the rung's
    assert c["fees"] == 1 and c["forms"] == 0 and c["escalation"] == 2 and c["sections"] == 1
    assert p["kinds"] == {"who": True, "steps": True, "deadline": True, "fee": True, "form": False, "where": True,
                          "appeal": True}
    # a topic nothing carries, and no route keys: nothing found
    empty = CV.probe({"jurisdiction": "va", "gov_id": None, "topic": "animals", "processes": [], "process_keys": []},
                     store=tiny_store)
    assert empty["processes"] == [] and empty["counts"] == CV.EMPTY_COUNTS
    assert CV.probe(route, live=False, store=None)["source"] in ("store", "none")   # no store built here: no crash


def test_who_counts_and_wiki_quotes():
    who = {"source": "store", "roles": [
        {"label": "custodian", "played_by": {"kind": "body", "key": "lexflow:agency:va:dgs", "channels": [{"kind": "email"}]},
         "quotes": [{"section": "Va. Code Ann. § 2.2-3704", "text": "within five working days of receiving a request"}],
         "steps": [{"limit": "5", "quote": "five working days", "sections": [{"section": "Va. Code Ann. § 2.2-3704", "text": "shall promptly, but in all cases within five working days"}]}]},
        {"label": "requester", "played_by": {"kind": "private-party"}, "quotes": [], "steps": []}], "local": [], "missing": []}
    w = CV.who_counts(who)
    assert w == {"source": "store", "roles": 2, "local": 0, "bodies": 1, "bodies_with_channels": 1, "deadlines": 1,
                 "deadlines_quoted": 1, "missing": []}
    q = CV.wiki_quotes(who)
    assert [x["id"] for x in q] == ["W1", "W2", "W3"] and q[0]["section"] == "2.2-3704" and q[2]["section"] is None


# ------------------------------------------------------------------------------------------------- the verdict
def test_verdict_rules():
    q = {"needs": ["who", "steps", "deadline", "fee"]}
    nothing = {"processes": [], "kinds": CV.kinds_of(CV.EMPTY_COUNTS)}
    full = {"processes": [{"key": "p"}], "kinds": {k: True for k in CV.KINDS}}
    some = {"processes": [{"key": "p"}], "kinds": {**{k: False for k in CV.KINDS}, "steps": True, "who": True}}
    gold = {"gold": "index"}
    assert CV.verdict(q, nothing, None, None) == ("none", ["who", "steps", "deadline", "fee"])
    assert CV.verdict(q, full, None, None) == ("adequate", [])
    assert CV.verdict(q, some, None, {"gold": "none"}) == ("partial", ["deadline", "fee"])
    # with gold and a scored answer: the answer's covered kinds count, and the vital recall must reach the bar
    assert CV.verdict(q, some, {"vital_recall": 1.0, "kinds": {"deadline": True, "fee": True}}, gold) == ("adequate", [])
    assert CV.verdict(q, some, {"vital_recall": 0.25, "kinds": {"deadline": True, "fee": True}}, gold) == ("partial", [])
    assert CV.verdict(q, full, {"vital_recall": 0.0, "kinds": {}}, gold) == ("partial", [])
    assert CV.verdict(q, nothing, {"vital_recall": 0.0, "kinds": {}}, gold) == ("none", ["who", "steps", "deadline", "fee"])
    assert CV.verdict(q, nothing, {"vital_recall": 0.5, "kinds": {"who": True}}, gold)[0] == "partial"


# ---------------------------------------------------------------------------------------- the step and the CLI
def test_coverage_step_is_registered():
    from lexflow.pipeline.steps import get_step, run_coverage
    s = get_step("coverage")
    assert s.run is run_coverage and {"states", "places", "questions", "arm", "node"} <= set(s.params)
    assert s.credits
    from lexflow.pipeline import jobs
    assert "coverage" in jobs.EXCLUSIVE
    from lexflow import cli
    import argparse
    ap = argparse.ArgumentParser()
    # the run subcommand accepts the coverage flags
    import contextlib, io
    with contextlib.redirect_stdout(io.StringIO()):
        with pytest.raises(SystemExit):
            cli.main(["run", "--help"])
    assert CV.node_of(None)[1]


def test_node_of_reads_llm_nodes(monkeypatch):
    monkeypatch.setenv("LEXFLOW_LLM_NODES", "local=http://ollama:11434|embed, shop=http://100.64.0.2:11434|threads=6")
    assert CV.node_of("shop") == ("shop", "http://100.64.0.2:11434")
    with pytest.raises(ValueError):
        CV.node_of("mac")
    monkeypatch.delenv("LEXFLOW_LLM_NODES")
    name, url = CV.node_of(None)
    assert url and name


# ----------------------------------------------------------------------------------------- the matrix writer
def _row(qid, state, gov, verdict, missing, arm="coverage", score=None, seconds=4.0):
    return {"run_id": "t", "qid": qid, "state": state, "gov_id": gov, "arm": arm, "model": "m" if arm == "ollama" else None,
            "node": "ollama", "verdict": verdict, "missing": missing, "seconds": seconds, "score": score,
            "probe": {"source": "store", "counts": dict(CV.EMPTY_COUNTS), "gold": "index"}}


def test_matrix_and_markdown_and_reports(con, tmp_path):
    rows = [_row("public_records", "va", "", "adequate", [], "ollama", {"composite": 0.8, "vital_recall": 1.0, "citation_precision": 0.5}, 90),
            _row("dog_license", "va", "", "partial", ["fee", "form"]),
            _row("dog_license", "va", "47210400100000", "adequate", []),
            _row("public_records", "dc", "", "none", ["who", "steps", "deadline", "fee", "appeal"]),
            _row("dog_license", "dc", "", "partial", ["fee"])]
    m = CV.matrix(rows)
    assert list(m["columns"]) == ["va", "va/47210400100000", "dc"]
    va = m["columns"]["va"]
    assert va["adequate"] == 1 and va["partial"] == 1 and va["top_missing"] == [("fee", 1), ("form", 1)]
    assert va["ollama_cells"] == 1 and va["ollama"]["composite"] == 0.8 and va["ollama_seconds_mean"] == 90
    assert m["columns"]["dc"]["top_missing"][0] == ("fee", 2)
    assert m["totals"] == {"adequate": 2, "partial": 2, "none": 1, "draft": 0}
    assert m["cells"]["dog_license|va"]["missing"] == ["fee", "form"]
    md = CV.markdown(m, "t")
    assert "| dog_license | P fee,form | A | P fee |" in md
    assert "| public_records | A (0.8) |" in md and "| va | 2 | 1 | 1 | 0 | 0 | fee (1), form (1) | 1 | 0.8 |" in md
    # the writer reads the rows back from the table
    CV.ensure_table(con)
    from lexflow.store import db
    for r in rows:
        db.upsert(con, "coverage_runs", [{**r, "probe": json.dumps(r["probe"]), "score": json.dumps(r["score"]) if r["score"] else None,
                                          "missing": json.dumps(r["missing"]), "updated_at": db.now()}],
                  keys=("run_id", "qid", "state", "gov_id", "arm"), stamp=False)
    con.commit()
    assert CV.latest_run(con) == "t" and CV.runs(con)[0]["cells"] == 5
    out = CV.write_reports(con, "t", docs_dir=tmp_path, log=lambda *_: None)
    doc = json.loads(Path(out["json"]).read_text(encoding="utf-8"))
    assert doc["run"] == "t" and doc["states"] == ["dc", "va"] and len(doc["rows"]) == 5 and doc["matrix"]["totals"]["adequate"] == 2
    assert (tmp_path / "coverage.md").read_text(encoding="utf-8").startswith("# Coverage")
    assert CV.latest_report(tmp_path)["run"] == "t"


# ------------------------------------------------------------------------------------------ drafts in the probe
def _draft_items():
    """The hand-made items plus an asked answer's draft process on another topic (animals), with one step whose
    bearer is a private party, and a single-tier draft on the same topic as the reviewed process."""
    import sys
    sys.path.insert(0, str(ROOT / "tests"))
    from test_sparql import hand_made
    from lexflow.publish.rdf import Claim, Item, Value
    items = hand_made()
    items += [
        Item("lexflow:vocab:topic:animals", "animals", "", [], "lexflow:class:topic", []),
        Item("lexflow:vocab:review-status:draft", "draft", "", [], "lexflow:class:review-status", []),
        Item("lexflow:process:asked:va:dog_license", "Dog licence (Virginia)", "", [], "legal process", [
            Claim("applies to jurisdiction", Value("item", "lexflow:jurisdiction:va")),
            Claim("topic", Value("item", "lexflow:vocab:topic:animals")),
            Claim("question asked", Value("monolingual", "Does my dog need a licence, and how do I get one?", lang="en")),
            Claim("review status", Value("item", "lexflow:vocab:review-status:draft"))]),
        Item("lexflow:role:va:dog_license:owner", "owner", "", [], "legal role",
             [Claim("played by", Value("item", "lexflow:private-party"))]),
        Item("lexflow:step:asked:va:dog_license:apply", "Apply for the licence", "", [], "legal process step", [
            Claim("part of", Value("item", "lexflow:process:asked:va:dog_license")),
            Claim("bearer", Value("item", "lexflow:role:va:dog_license:owner")),
            Claim("fee", Value("quantity", "10", unit="lexflow:vocab:currency:usd"))]),
        Item("lexflow:process:va.records2", "Records, a second take (Virginia)", "", [], "legal process", [
            Claim("applies to jurisdiction", Value("item", "lexflow:jurisdiction:va")),
            Claim("topic", Value("item", "lexflow:vocab:topic:public-records")),
            Claim("review status", Value("item", "lexflow:vocab:review-status:draft"))]),
    ]
    return items


@pytest.fixture()
def draft_store(tmp_path, monkeypatch):
    pytest.importorskip("pyoxigraph")
    from lexflow import config
    from lexflow.publish import ids as I
    from lexflow.publish import rdf
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "t.db")
    monkeypatch.setattr(I, "IDS_PATH", tmp_path / "ids.json")
    m = I.IdMap()
    monkeypatch.setattr(I, "_default", m)
    out = rdf.write(_draft_items(), tmp_path / "lexipedia.ttl", m)
    return CV.Store(live=False, store=rdf.memory_store(out), idmap=m)


def test_probe_counts_drafts_apart_and_the_verdict_caps_on_drafts_alone(draft_store):
    q = {"id": "dog_license", "needs": ["steps", "fee"]}
    # the asked draft is the only process item on its topic: counted as a draft, the cell at most partial
    route = {"jurisdiction": "va", "gov_id": None, "topic": "animals", "processes": [], "process_keys": []}
    p = CV.probe(route, store=draft_store)
    assert len(p["processes"]) == 1 and p["processes"][0]["status"] == "draft"
    c = p["counts"]
    assert c["processes"] == 1 and c["drafts"] == 1 and c["reviewed"] == 0 and c["steps"] == 1 and c["fees"] == 1
    assert p["kinds"]["steps"] and p["kinds"]["fee"] and CV.drafts_only(p)
    assert CV.verdict(q, p, None, None) == ("partial", [])
    assert CV.verdict(q, p, {"vital_recall": 1.0, "kinds": {"steps": True, "fee": True}}, {"gold": "index"}) == ("partial", [])
    # with a kind still missing the verdict is partial as before, and the missing kinds are reported
    assert CV.verdict({"id": "dog_license", "needs": ["steps", "fee", "who"]}, p, None, None) == ("partial", ["who"])
    # a reviewed process next to a draft on the same topic: not drafts alone, adequate stays possible
    route = {"jurisdiction": "va", "gov_id": None, "topic": "public-records",
             "processes": [{"key": "lexflow:process:va.records", "scope": "state", "topic": "public-records"}],
             "process_keys": ["lexflow:process:va.records"]}
    p2 = CV.probe(route, store=draft_store)
    assert p2["counts"]["processes"] == 2 and p2["counts"]["drafts"] == 1 and p2["counts"]["reviewed"] == 1
    assert not CV.drafts_only(p2)
    assert CV.verdict({"id": "x", "needs": ["steps", "who"]}, p2, None, None) == ("adequate", [])
    # the matrix shows the shade: D for a partial cell on drafts alone, with the column and total counts
    rows = [_row("dog_license", "va", "", "partial", []), _row("public_records", "va", "", "adequate", [])]
    rows[0]["probe"]["drafts_only"] = True
    m = CV.matrix(rows)
    assert m["cells"]["dog_license|va"]["draft"] and not m["cells"]["public_records|va"]["draft"]
    assert m["columns"]["va"]["draft"] == 1 and m["totals"]["draft"] == 1 and m["totals"]["partial"] == 1
    md = CV.markdown(m, "t")
    assert "| dog_license | D |" in md and "| public_records | A |" in md
    assert "| va | 2 | 1 | 1 | 1 | 0 |" in md


# ------------------------------------------------------------------------------------------------- the fill
def _seed_run(con, run_id="r1"):
    from lexflow.store import db
    CV.ensure_table(con)
    cells = [("public_records", "va", "partial", ["who"]), ("dog_license", "va", "none", ["who", "steps", "fee"]),
             ("business_license", "va", "partial", ["fee"]), ("procurement_bids", "va", "adequate", []),
             ("dog_license", "dc", "none", ["who", "steps"]), ("noise_complaint", "dc", "none", ["who", "steps", "where"])]
    for qid, st, v, missing in cells:
        db.upsert(con, "coverage_runs", [{"run_id": run_id, "qid": qid, "state": st, "gov_id": "", "arm": "coverage",
                                          "verdict": v, "missing": json.dumps(missing), "probe": "{}", "seconds": 1.0,
                                          "updated_at": db.now()}], keys=("run_id", "qid", "state", "gov_id", "arm"),
                  stamp=False)
    con.commit()


def test_gap_cells_are_none_or_partial_without_steps_or_who_gold_first(con):
    _seed_run(con)
    cells = CV.gap_cells(con, "r1", ["va", "dc"])
    assert [(c["qid"], c["state"]) for c in cells] == [("public_records", "va"), ("dog_license", "va"),
                                                       ("dog_license", "dc"), ("noise_complaint", "dc")]
    # business_license (fee only) and procurement_bids (adequate) are not gaps; dc's noise_complaint has gold: none
    # so dog_license (gold) comes first in dc although noise_complaint is earlier in the question file
    dc = [c for c in cells if c["state"] == "dc"]
    assert dc[0]["qid"] == "dog_license" and dc[0]["gold"] and not dc[1]["gold"]
    assert CV.gap_cells(con, "r1", ["dc"], qids=["dog_license"]) == [dc[0]]
    terms = CV.fill_terms(CV.question("dog_license"))
    assert terms and all(isinstance(g, list) and g for g in terms)


def _stub(calls, status="answered"):
    """A stand-in for pipeline.answer_state that stores a row under the model lane the fill names."""
    from lexflow.store import db

    def stub(con_, qid, plan, state, *, asker=None, emb=None, log=print, store=True, oracle_refs=None, model=None):
        calls.append((qid, state, plan.kind, plan.source))
        row = {"question_id": qid, "target": state, "state": state, "gov_id": None, "question_text": plan.text,
               "status": status, "sections": json.dumps({"chosen": [{"ref": "3.2-6524", "id": 1}]}),
               "facts": json.dumps({"steps": [{"id": "s1"}]}), "answer": "{}", "model": model, "seconds": 1.0,
               "metrics": json.dumps({"quotes_checked": 3, "quote_misses": 0, "answered_at": db.now()})}
        db.upsert(con_, "asked_answers", [row])
        con_.commit()
        return row
    return stub


def test_fill_registers_questions_runs_the_stub_pipeline_resumes_and_caps(con):
    from lexflow.store import db
    _seed_run(con)
    calls = []

    stub = _stub(calls)
    log = []
    out = CV.fill(con, ["va", "dc"], run_id="r1", llm_cells=1, pipeline=stub, log=log.append)
    assert out["run"] == "r1" and out["gap_cells"] == 4 and out["answered"] == 2 and out["status"]["answered"] == 2
    # one cell per state, the gold cells first, in question order; the plan is a process plan
    assert calls == [("public_records", "va", "process", "coverage-fill"), ("dog_license", "dc", "process", "coverage-fill")]
    q = db.one(con, "SELECT * FROM asked_questions WHERE id='public_records'")
    assert q and q["kind"] == "process" and json.loads(q["terms"]) and q["text"] == CV.question("public_records")["text"]
    a = db.one(con, "SELECT * FROM asked_answers WHERE question_id='dog_license' AND target='dc'")
    fill_ = json.loads(a["metrics"])["coverage_fill"]
    assert fill_["run"] == "r1" and fill_["node"] and fill_["verdict"] == "none" and "steps" in fill_["missing"]
    assert CV.filled(con, "dog_license", "dc")["status"] == "answered" and CV.filled(con, "dog_license", "va") is None
    # the row is filed under the model the fill ran with (no asker in the tests: the configured ask model)
    from lexflow import config
    assert a["model"] == config.ASK_MODEL and fill_["model"] == config.ASK_MODEL and fill_["summary"] is False
    assert out["model"] == config.ASK_MODEL and out["cells"] == "gaps"
    # resumable: the same call again answers nothing new; without the cap the remaining cells are answered
    out = CV.fill(con, ["va", "dc"], run_id="r1", llm_cells=1, pipeline=stub, log=log.append)
    assert out["answered"] == 0 and out["status"]["skipped"] == 2 and len(calls) == 2
    out = CV.fill(con, ["va"], run_id="r1", pipeline=stub, log=log.append)
    assert out["answered"] == 1 and calls[-1][:2] == ("dog_license", "va")
    # force answers again; a failing pipeline is counted and does not stop the fill
    out = CV.fill(con, ["dc"], run_id="r1", qids=["dog_license"], pipeline=stub, force=True, log=log.append)
    assert out["answered"] == 1 and calls[-1][:2] == ("dog_license", "dc")

    def broken(*a, **k):
        raise RuntimeError("no index")
    out = CV.fill(con, ["dc"], run_id="r1", pipeline=broken, force=True, log=log.append)
    assert out["status"]["failed"] == 2 and any("failed: RuntimeError" in line for line in log)
    # the step takes --fill
    from lexflow.pipeline.steps import get_step
    assert "fill" in get_step("coverage").params


def test_fill_cells_filled_answers_the_same_set_with_a_second_model_beside_the_first(con):
    """``--cells filled``: a second model answers the cells another model filled, under its own key, so the first
    answer stays and the two can be compared; ``all`` adds the remaining gaps; the resume is per model."""
    from lexflow import config
    from lexflow.store import db
    _seed_run(con)
    calls = []
    # the first model fills two cells (one per state): the former gaps are no gaps any more once the next run
    # marks them partial with steps and who (what happened after the qwen3:1.7b fill)
    out = CV.fill(con, ["va", "dc"], run_id="r1", llm_cells=1, pipeline=_stub(calls), model="qwen3:1.7b", log=lambda *_: None)
    assert out["answered"] == 2 and out["model"] == "qwen3:1.7b"
    for qid, st in (("public_records", "va"), ("dog_license", "dc")):
        db.upsert(con, "coverage_runs", [{"run_id": "r2", "qid": qid, "state": st, "gov_id": "", "arm": "coverage",
                                          "verdict": "partial", "missing": json.dumps(["fee"]), "probe": "{}",
                                          "seconds": 1.0, "updated_at": db.now()}],
                  keys=("run_id", "qid", "state", "gov_id", "arm"), stamp=False)
    con.commit()
    assert CV.gap_cells(con, "r2", ["va", "dc"]) == []
    with pytest.raises(ValueError):
        CV.fill_cells(con, "r2", ["va", "dc"], cells="nope")
    # the filled cells, as another model sees them: both, with who filled them and the first fill's verdict
    cells = CV.filled_cells(con, ["va", "dc"], model="qwen3:8b")
    assert [(c["qid"], c["state"], c["filled_by"], c["verdict"]) for c in cells] == [
        ("public_records", "va", ["qwen3:1.7b"], "partial"), ("dog_license", "dc", ["qwen3:1.7b"], "none")]
    assert CV.filled_cells(con, ["va", "dc"], model="qwen3:1.7b") == []       # its own fills are not "another model's"
    assert CV.fill_cells(con, "r2", ["va", "dc"], cells="gaps") == []
    assert [(c["qid"], c["state"]) for c in CV.fill_cells(con, "r2", ["va", "dc"], cells="filled", model="qwen3:8b")] == \
        [("public_records", "va"), ("dog_license", "dc")]
    # the second model answers the same two cells under its own key: the first answers are untouched
    calls.clear()
    out = CV.fill(con, ["va", "dc"], run_id="r2", pipeline=_stub(calls, "partial"), model="qwen3:8b", cells="filled",
                  log=lambda *_: None)
    assert out["answered"] == 2 and out["cells"] == "filled" and out["model"] == "qwen3:8b"
    assert [c[:2] for c in calls] == [("public_records", "va"), ("dog_license", "dc")]
    rows = db.rows(con, "SELECT model, status, metrics FROM asked_answers WHERE question_id='dog_license' AND target='dc' "
                        "ORDER BY model")
    assert [(r["model"], r["status"]) for r in rows] == [("qwen3:1.7b", "answered"), ("qwen3:8b", "partial")]
    fills = CV.fills(con, "dog_license", "dc")
    assert fills["qwen3:1.7b"]["run"] == "r1" and fills["qwen3:8b"]["run"] == "r2"
    assert fills["qwen3:8b"]["beside"] == ["qwen3:1.7b"] and fills["qwen3:8b"]["model"] == "qwen3:8b"
    # resumable per model: the second model skips its own fills, the first model's are still skipped too
    out = CV.fill(con, ["va", "dc"], run_id="r2", pipeline=_stub(calls), model="qwen3:8b", cells="filled", log=lambda *_: None)
    assert out["answered"] == 0 and out["status"]["skipped"] == 2
    # ``all`` = the gaps of the run plus the filled cells: r1 still has two gap cells the first model never answered
    cells = CV.fill_cells(con, "r1", ["va", "dc"], cells="all", model="qwen3:8b")
    assert sorted((c["qid"], c["state"]) for c in cells) == sorted([("public_records", "va"), ("dog_license", "va"),
                                                                     ("dog_license", "dc"), ("noise_complaint", "dc")])
    # the preferred reader shows one answer per cell: the better status wins, LEXFLOW_ASK_PREFER overrides
    from lexflow.ask import prefer
    assert prefer.answer(con, "dog_license", "dc")["model"] == "qwen3:1.7b"
    config.ASK_PREFER = "qwen3:8b"
    try:
        assert prefer.answer(con, "dog_license", "dc")["model"] == "qwen3:8b"
        assert CV.filled(con, "dog_license", "dc")["model"] == "qwen3:8b"
    finally:
        config.ASK_PREFER = ""
    assert prefer.models_of(con, "dog_license", "dc") == ["qwen3:1.7b", "qwen3:8b"]
    # the CLI and the step take --cells
    from lexflow.pipeline.steps import get_step
    assert "cells" in get_step("coverage").params


def test_fill_cells_named_takes_the_questions_given_filled_or_not(con, monkeypatch):
    """``--cells named --questions a,b``: every state-level cell of those questions, whether any model filled it
    before (then the first fill's verdict and the other models are carried) or not; it needs --questions."""
    import pytest
    from lexflow.ask import coverage as CV
    monkeypatch.setattr(CV, "load_gold", lambda st, qid: {"gold": "index"} if qid == "dog_license" else None)
    qs = [q["id"] for q in CV.questions()][:2] + ["dog_license"]
    calls = []
    CV.fill(con, ["va"], run_id="r1", pipeline=_stub(calls, "partial"), model="qwen3:1.7b", cells="named",
            qids=["dog_license"], log=lambda *_: None)
    cells = CV.fill_cells(con, "r9", ["va", "dc"], qids=qs, cells="named", model="qwen3:8b")
    assert [(c["qid"], c["state"], c["gold"]) for c in cells] == \
        [("dog_license", "va", True), (qs[0], "va", False), (qs[1], "va", False),
         ("dog_license", "dc", True), (qs[0], "dc", False), (qs[1], "dc", False)]
    assert cells[0]["filled_by"] == ["qwen3:1.7b"] and cells[1]["filled_by"] == []
    with pytest.raises(ValueError):
        CV.fill_cells(con, "r9", ["va"], cells="named")
