"""Regressions from the ask pipeline review: section texts fetched by index row id, whole-number claim checks,
section numbers and grouped cites in claims, the wiki tick kept on re-asking, and distinct question ids."""
import json

import pytest

from lexflow import config
from lexflow.ask import answer as A
from lexflow.ask import index as I
from lexflow.ask import pipeline as AP
from lexflow.ask import plan as PL
from lexflow.store import db

OLD = "Old wording: a public body shall respond to every request for records within twelve working days."


def quiet(*_):
    pass


@pytest.fixture()
def offline(monkeypatch):
    monkeypatch.setattr(config, "COURTLISTENER_TOKEN", "")
    monkeypatch.setattr(config, "SEARXNG_URL", "")


@pytest.fixture()
def two_versions(va_statutes, monkeypatch):
    """The Virginia fixture with an expired version of § 2.2-3704 filed just before the current one (as NC files
    § 105-113.36A), so the one ref names two index rows and the first is the expired one."""
    import pandas as pd
    from lexflow.municipal import statutes
    df = va_statutes.reset_index(drop=True)
    i = int(df.index[df["section_number"] == "2.2-3704"][0])
    old = df.loc[[i]].assign(section_title="(Effective until July 1, 2020) Public records to be open to inspection",
                             text=OLD, act_id="old")
    frame = pd.concat([df.loc[:i - 1], old, df.loc[i:]], ignore_index=True)
    real = statutes.load
    monkeypatch.setattr(statutes, "load", lambda st: frame if st == "va" else real(st))
    assert I.ensure("va")
    return frame


def test_section_texts_come_from_the_chosen_row_not_the_ref(con, two_versions, va_statutes, offline, monkeypatch):
    from lexflow.ask.retrieve import retrieve
    from lexflow.municipal import statutes
    real = I.lookup
    monkeypatch.setattr(I, "lookup", lambda st, ref, with_text=False: sorted(real(st, ref, with_text),
                                                                            key=lambda r: r["id"]))
    rows = I.lookup("va", "2.2-3704")                                   # in file order: the expired one first
    assert len(rows) == 2 and rows[0]["effective_until"] == "2020-07-01" and not rows[1]["effective_until"]
    r = AP.oracle("va", ["2.2-3704"])
    assert [c["id"] for c in r["chosen"]] == [rows[1]["id"]]          # the version in force, not rows[0]
    current = statutes.section_texts("va", ["2.2-3704"], df=va_statutes)[0]
    assert AP.texts_of("va", r["chosen"]) == [current]                 # the same object section_texts gives
    assert AP.texts_of("va", [rows[0]])[0].text == OLD                 # fetched by id, whichever row it is
    p = PL.plan("How do I request public records from a public body, and how long does it have to respond?")
    row = AP.answer_state(con, "records_q", p, "va", oracle_refs=["2.2-3704"], log=quiet)
    quotes = json.loads(row["answer"])["quotes"]
    assert quotes and all(q["text"] in current.text for q in quotes) and not any("Old wording" in q["text"]
                                                                               for q in quotes)
    # retrieval drops the expired row; its ref alone is ambiguous (no '§'), which used to abort the job
    monkeypatch.setattr(config, "VECTORS", "tfidf")
    monkeypatch.setattr(config, "ASK_MIN_SIMILARITY", -1.0)
    chosen = retrieve("va", p, embedder=None)["chosen"]
    assert chosen[0]["ref"] == "2.2-3704" and chosen[0]["id"] == rows[1]["id"]
    row = AP.answer_state(con, "records_q", p, "va", emb=None, log=quiet)
    assert row["status"] == "answered"
    assert all(q["text"] in current.text for q in json.loads(row["answer"])["quotes"])


def test_verify_compares_whole_numbers():
    quotes = [{"id": "Q1", "text": "A public body shall respond within 30 days; the charge shall not exceed $150."},
              {"id": "Q2", "text": "No petition may be filed after 10 years."},
              {"id": "Q3", "text": "The clerk shall act within thirty days and may charge one hundred twenty-five "
                                   "dollars, or five hundred dollars for a corporation."}]
    out = A.verify({"status": "answered", "claims": [
        {"text": "The body must respond within 3 days [Q1].", "quotes": []},
        {"text": "It can charge at most $15 [Q1].", "quotes": []},
        {"text": "You can file after 1 year [Q2].", "quotes": []},
        {"text": "The charge is $1,50.", "quotes": ["Q1"]},
        {"text": "The clerk can charge $100 [Q3].", "quotes": []},           # "one hundred" is part of 125
        {"text": "A corporation pays $5 [Q3].", "quotes": []},               # "five" is part of 500
        {"text": "The body responds within 30 days and charges up to $150.00 [Q1].", "quotes": []},
        {"text": "The clerk acts within 30 days and charges $125, or $500 for a corporation [Q3].", "quotes": []},
        {"text": "You can file after 10 years [Q2].", "quotes": []}]}, quotes)
    assert [c["text"] for c in out["claims"]] == [
        "The body responds within 30 days and charges up to $150.00.",
        "The clerk acts within 30 days and charges $125, or $500 for a corporation.",
        "You can file after 10 years."]
    assert len(out["dropped"]) == 6 and all(d["why"].startswith("a number") for d in out["dropped"])
    assert A.spelled("between five and ten days, or two thousand five hundred and one") == {"5", "10", "2501"}
    assert A.number("$1,500.00") == "1500" and A.number("2.50%") == "2.5" and A.number("1,50") == "1,50"


def test_verify_keeps_section_numbers_and_grouped_cites():
    quotes = [{"id": "Q1", "section": "105-113.36A", "text": "The tax is due on the day the stamps are bought."},
              {"id": "Q2", "section": "19.2-392.2", "text": "No petition may be filed after 10 years."}]
    out = A.verify({"status": "answered", "claims": [
        {"text": "Under § 105-113.36A the tax is due when the stamps are bought [Q1].", "quotes": []},
        {"text": "Section 19.2-392.2 bars a petition after 10 years [Q2].", "quotes": []},
        {"text": "You may file after 10 years [Q1, Q2].", "quotes": []},
        {"text": "You may file after 10 years [Q1, Q2].", "quotes": ["Q2"]},
        {"text": "Under § 58.1-3 the tax is due [Q1].", "quotes": []}]}, quotes)    # a section no quote is from
    assert [(c["text"], c["quotes"]) for c in out["claims"]] == [
        ("Under § 105-113.36A the tax is due when the stamps are bought.", ["Q1"]),
        ("Section 19.2-392.2 bars a petition after 10 years.", ["Q2"]),
        ("You may file after 10 years.", ["Q1", "Q2"]),
        ("You may file after 10 years.", ["Q2", "Q1"])]
    assert [d["text"] for d in out["dropped"]] == ["Under § 58.1-3 the tax is due."]


def test_reasking_keeps_the_wiki_tick(con, va_statutes, offline):
    assert I.ensure("va")
    p = PL.plan("How long does a public body have to respond to a request for public records?")   # facts: no BPMN
    g = {"state": "va", "gov_id": "51540", "name": "City of Charlottesville", "kind": "city", "website": None}

    def ask():
        srow = AP.answer_state(con, "records_q", p, "va", oracle_refs=["2.2-3704"], log=quiet)
        AP.answer_place(con, "records_q", p, g, srow, grouped={}, keys={})
        AP.answer_state(con, "records_q", p, "wy", log=quiet)             # no statute file: stored all the same
        con.commit()

    def ticks():
        return {r["target"]: r["published"] for r in db.rows(con, "SELECT target, published FROM asked_answers "
                                                                  "WHERE question_id='records_q'")}
    ask()
    assert ticks() == {"va": 0, "51540": 0, "wy": 0}                    # new answers start unticked
    con.execute("UPDATE asked_answers SET published=1 WHERE question_id='records_q'")
    con.commit()
    ask()
    assert ticks() == {"va": 1, "51540": 1, "wy": 1}


def test_question_ids_are_stable_and_distinct(con, monkeypatch):
    from fastapi.testclient import TestClient
    from lexflow.api import app as API
    a = "How do I get my criminal record sealed in Virginia after a misdemeanor conviction for possession?"
    b = "How do I get my criminal record sealed in Virginia after a misdemeanor conviction for shoplifting?"
    assert PL.slug(a) == PL.slug(b)
    qa = AP.save_question(con, a, PL.plan(a))
    assert qa == PL.slug(a)                                             # a new slug is the id, as before
    assert AP.qid_for(con, "  how do I get my CRIMINAL record sealed in virginia after a misdemeanor conviction "
                           "for possession ") == qa                    # the same question asked again
    qb = AP.save_question(con, b, PL.plan(b))
    assert qb != qa and qb.startswith(qa + "_")
    assert AP.qid_for(con, a) == qa and AP.qid_for(con, b) == qb
    # a question answered elsewhere (synced answers, no local asked_questions row) holds its id too
    db.upsert(con, "asked_answers", [{"question_id": "seal_criminal_record", "target": "va", "state": "va",
                                      "question_text": "When can I seal my criminal record?"}])
    con.commit()
    assert PL.slug("Who can seal my criminal record?") == "seal_criminal_record"
    assert AP.qid_for(con, "Who can seal my criminal record?") != "seal_criminal_record"
    assert AP.qid_for(con, "When can I seal my criminal record?") == "seal_criminal_record"
    assert AP.qid_for(con, "Any suggestions?") != "suggestions"         # GET /api/ask/suggestions is a route
    # the API gives out the same ids, and holds one before its job runs
    monkeypatch.setattr(config, "JOB_RUNNER", False)
    c = "How much does a dog license cost in the city?"
    d = "How much does a dog license cost in the county?"
    assert PL.slug(c) == PL.slug(d)
    with TestClient(API.app) as client:
        ids = [client.post("/api/ask", json={"question": q, "targets": ["va"]}).json()["question_id"]
               for q in (c, d, c, a)]
    assert ids[0] == PL.slug(c) and ids[1] != ids[0] and ids[2] == ids[0] and ids[3] == qa
