"""Publishing fixes: distinct page ids for same-named places, no orphan answers, raw-safe headings and link titles,
and the retired v1 Wikibase loader.  No network.  The API writer's own behaviour (find-before-create, label
clashes, resume, the HELD gate) is tested in test_push.py."""
import json
import re

import pytest

from lexflow import signoff
from lexflow.publish import lexipedia as LX
from lexflow.publish import wikibase_lexipedia as WL
from lexflow.store import db


def _gov(gov_id, state, name, kind="municipality", county=None, pop=None):
    return dict(gov_id=gov_id, state=state, name=name, kind=kind, county_name=county, population=pop)


# a review naming a (made-up) person on the operator's reviewer list (lexflow/reviewers.py): the list row is put in
# every test store below, since a page names a reviewer only from the list
REVIEWER = {"reviewer": "rv-0000000b", "date": "2026-10-01", "attested": True}


@pytest.fixture(autouse=True)
def _reviewer_on_the_list(request):
    if "con" in request.fixturenames:
        con = request.getfixturevalue("con")
        db.upsert(con, "reviewers", [{"id": "rv-0000000b", "name": "Ana Villamar", "role": "researcher",
                                      "added_by": "operator", "added_at": "2026-09-30T00:00:00Z"}])
        con.commit()


def _asked(qid, g, text="Do I need a permit for a deck?", gov=True):
    """An asked answer marked for the wiki and signed by a (made-up) reviewer of this text: only those are
    published (the sign-off carries the hash of the text it covers, lexflow/signoff.py)."""
    row = {"question_id": qid, "target": g["gov_id"] if gov else g["state"], "state": g["state"],
           "gov_id": g["gov_id"] if gov else None, "question_text": text, "status": "answered",
           "answer": json.dumps({"quotes": []}), "local": json.dumps({"name": g["name"]} if gov else {}),
           "published": 1}
    return {**row, "reviewed_by": signoff.bind(REVIEWER, signoff.row_text(row, signoff.ASKED_TEXT))}


def _recorded(con):
    """The review_log entries the review API writes for each signed answer: a page names a reviewer only for a
    review this copy recorded (lexflow/reviewers.py, ``recorded``)."""
    from lexflow import reviewers
    for r in db.rows(con, "SELECT question_id, target, reviewed_by FROM asked_answers WHERE reviewed_by IS NOT NULL"):
        rev = json.loads(r["reviewed_by"])
        reviewers.log_review(con, "review", r["question_id"], r["target"], rev["reviewer"], rev["text_hash"],
                             at=f"{rev['date']}T12:00:00Z")
    con.commit()


def _links(pages):
    return {m.group(1).strip() for t in pages.values() for m in re.finditer(r"\[\[([^|\]]+)", t)}


# --- page ids

OAK_COOKE = _gov("44204940100000", "tx", "Town of Oak Ridge", county="Cooke", pop=253)
OAK_KAUFMAN = _gov("44212980300000", "tx", "Town of Oak Ridge", county="Kaufman", pop=887)


def test_same_named_places_get_distinct_page_ids(con):
    govs = [OAK_COOKE, OAK_KAUFMAN, _gov("44200000000001", "tx", "City of Oak Ridge North", county="Montgomery", pop=3032),
            _gov("07200000000001", "ct", "Town of Groton", "township", "Southeastern Connecticut", 38456),
            _gov("07200000000002", "ct", "City of Groton", "municipality", "Southeastern Connecticut", 9326),
            _gov("15200000000001", "in", "Township of Jackson", "township", "Hamilton", 11082),
            _gov("15200000000002", "in", "Township of Jackson", "township", "Allen", 509),
            _gov("15200000000003", "in", "Township of Jackson", "township", "Allen", 400),
            _gov("42100000000001", "pa", "Bedford", "county", "Bedford", 47000),
            _gov("42100000000002", "pa", "Bedford County", "county", "Bedford Twp", 10)]
    db.upsert(con, "governments", govs)
    con.commit()
    seg = {g["gov_id"]: LX.place_segment(con, g) for g in govs}
    assert seg[OAK_KAUFMAN["gov_id"]] == "oak_ridge"                     # the more populous keeps the plain id
    assert seg[OAK_COOKE["gov_id"]] == "oak_ridge_cooke"
    assert seg["44200000000001"] == "oak_ridge_north"
    assert seg["07200000000001"] == "groton" and seg["07200000000002"] == "groton_city"
    assert seg["15200000000001"] == "jackson"
    assert seg["15200000000002"] == "jackson_15200000000002" and seg["15200000000003"] == "jackson_15200000000003"
    assert seg["42100000000001"] == "bedford_county" and seg["42100000000002"] == "bedford_county_bedford_twp"
    assert LX.place_page(OAK_COOKE) == "lexflow:tx:oak_ridge"           # the old call still works

    rows = [_asked("deck", OAK_COOKE), _asked("deck", OAK_KAUFMAN)]
    for r, county in zip(rows, ("Cooke", "Kaufman")):
        r["local"] = json.dumps({"name": f"Oak Ridge, {county} County"})
        r["reviewed_by"] = signoff.bind(REVIEWER, signoff.row_text(r, signoff.ASKED_TEXT))   # signed as changed
    db.upsert(con, "asked_answers", rows)
    _recorded(con)
    pages = LX.all_pages(con)
    a, b = "lexflow:tx:oak_ridge_cooke:deck", "lexflow:tx:oak_ridge:deck"
    assert "Cooke County" in pages[a] and "Kaufman County" in pages[b]          # neither answer overwrites the other
    assert f"[[{a}|" in pages["lexflow:tx"] and f"[[{b}|" in pages["lexflow:tx"]


def test_live_place_ids_do_not_change(con):
    from test_places_strategies import _govs
    _govs(con)
    for g in db.rows(con, "SELECT * FROM governments"):
        assert LX.place_page(g, con) == LX.place_page(g)
    g = db.one(con, "SELECT * FROM governments WHERE name='City of Charlottesville'")
    assert LX.place_page(g, con) == "lexflow:va:charlottesville"


# --- orphan answers

def test_place_answers_without_a_place_page_are_linked_and_have_no_dead_links(con):
    cville = _gov("47210400100000", "va", "City of Charlottesville", county="Charlottesville City", pop=45672)
    fairfax = _gov("47102900000000", "va", "Fairfax County", "county", "Fairfax", 1150000)
    db.upsert(con, "governments", [cville, fairfax])
    db.upsert(con, "local_answers", [{"gov_id": cville["gov_id"], "state": "va", "question": "records",
                                      "summary": "Ask the city's FOIA officer."}])
    db.upsert(con, "asked_answers", [_asked("deck", cville), _asked("deck", fairfax), _asked("deck", cville, gov=False)])
    _recorded(con)
    pages = LX.all_pages(con)
    loose = pages["lexflow:va:fairfax_county:deck"]
    assert "lexflow:va:fairfax_county" not in pages
    assert "[[lexflow:va:fairfax_county|" not in loose and "[[lexflow:va|Virginia]]" in loose
    assert "[[lexflow:va:fairfax_county:deck|Do I need a permit for a deck?]] — Fairfax County" in pages["lexflow:va"]
    assert "[[lexflow:va:charlottesville|City of Charlottesville]]" in pages["lexflow:va:charlottesville:deck"]
    links = _links(pages)
    assert {x for x in links if x.startswith("lexflow:")} <= set(pages)          # no dead links
    assert set(pages) - {"lexflow:start"} <= links                               # no orphan pages


# --- headings and link titles

def test_headings_and_link_titles_are_not_nowiki_wrapped(con):
    assert LX.title_esc("Freedom of Information Act (FOIA) | DC") == "Freedom of Information Act (FOIA) | DC"
    assert LX.title_esc("a [[b]] {{c}} <d> **e**") == "a [ [b] ] { {c} } <d> **e**"
    assert LX.title_esc("== Who?\nnext ==", True) == "Who? next"
    assert LX._contacts_block([{"value": "https://dc.gov/foia", "label": "Freedom of Information Act (FOIA) | DC"}]) == \
        ["  * [[https://dc.gov/foia|Freedom of Information Act (FOIA) | DC]]"]
    va = _gov("47102900000000", "va", "Fairfax County", "county", "Fairfax", 1150000)
    db.upsert(con, "governments", [va])
    q = "Does § 4-202(c) apply to <records> held by a contractor?"
    db.upsert(con, "asked_answers", [_asked("contractor_records", va, text=q, gov=False)])
    _recorded(con)
    pages = LX.all_pages(con)
    page = pages["lexflow:va:contractor_records"]
    assert page.splitlines()[0] == f"====== {q} ======"
    assert f"[[lexflow:va:contractor_records|{q}]]" in pages["lexflow:va"]
    assert LX.esc("§ 4-202(c)") == "§ 4-202%%(c)%%"                              # body text is still escaped


# --- Wikibase

def test_the_v1_loader_is_gone_and_only_the_api_client_remains():
    """Job 77 (2026-10-18) ran the v1 ``Loader`` (``clear`` with the v1 statement set, then ``retire_drafts``) over
    1,795 items the schema-v2 pusher had written and wiped their claims.  The module keeps only the API client the
    pusher reuses; no code path can relabel, retire or rewrite items in the v1 shape any more."""
    assert hasattr(WL, "Wikibase") and hasattr(WL, "WikibaseError")
    for gone in ("Loader", "run", "retire_drafts", "PROPS", "CLASSES", "MODALITY", "_snak"):
        assert not hasattr(WL, gone), gone
    import inspect
    src = inspect.getsource(WL)
    assert "def retire_drafts" not in src and "class Loader" not in src and "def run(" not in src
