"""Publishing fixes: distinct page ids for same-named places, no orphan answers, raw-safe headings and link titles,
and Wikibase re-runs that neither duplicate items nor crash on a states filter.  No network: the wiki is faked."""
import json
import re

import pytest

from lexflow.publish import lexipedia as LX
from lexflow.publish import wikibase_lexipedia as WL
from lexflow.store import db


def _gov(gov_id, state, name, kind="municipality", county=None, pop=None):
    return dict(gov_id=gov_id, state=state, name=name, kind=kind, county_name=county, population=pop)


def _asked(qid, g, text="Do I need a permit for a deck?", gov=True):
    return {"question_id": qid, "target": g["gov_id"] if gov else g["state"], "state": g["state"],
            "gov_id": g["gov_id"] if gov else None, "question_text": text, "status": "answered",
            "answer": json.dumps({"quotes": []}), "local": json.dumps({"name": g["name"]} if gov else {}),
            "published": 1}


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
    db.upsert(con, "asked_answers", rows)
    con.commit()
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
    con.commit()
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
    con.commit()
    pages = LX.all_pages(con)
    page = pages["lexflow:va:contractor_records"]
    assert page.splitlines()[0] == f"====== {q} ======"
    assert f"[[lexflow:va:contractor_records|{q}]]" in pages["lexflow:va"]
    assert LX.esc("§ 4-202(c)") == "§ 4-202%%(c)%%"                              # body text is still escaped


# --- Wikibase

class _Resp:
    def __init__(self, data):
        self.data = data

    def raise_for_status(self):
        pass

    def json(self):
        return self.data


class FakeAPI:
    """wbeditentity and wbgetentities on an in-memory wiki that, like Wikibase, allows one item per label and
    description, and answers a clash with Wikibase's own message."""

    def __init__(self, fail=None):
        self.headers, self.items, self.fail = {}, {}, fail

    def get(self, url, params=None, timeout=None):
        assert params["action"] == "wbgetentities"
        return _Resp({"entities": {q: self.items[q] for q in params["ids"].split("|") if q in self.items}})

    def post(self, url, data=None, timeout=None):
        assert data["action"] == "wbeditentity"
        if self.fail:
            return _Resp({"error": {"code": "failed-save", "info": self.fail}})
        ent, qid = json.loads(data["data"]), data.get("id")
        label, desc = ent["labels"]["en"]["value"], ent["descriptions"]["en"]["value"]
        for q, e in self.items.items():
            if q != qid and (e["labels"]["en"]["value"], e["descriptions"]["en"]["value"]) == (label, desc):
                return _Resp({"error": {"code": "modification-failed", "info":
                                        f'Item [[Item:{q}|{q}]] already has label "{label}" associated with '
                                        f'language code en, using the same description text.'}})
        qid = qid or f"Q{len(self.items) + 1}"
        claims = {}
        for s in ent.get("claims", []):
            claims.setdefault(s["mainsnak"]["property"], []).append(s)
        self.items[qid] = {"id": qid, "labels": ent["labels"], "descriptions": ent["descriptions"], "claims": claims}
        return _Resp({"entity": {"id": qid}})


def _loader(con, api, log=lambda *_: None):
    ld = WL.Loader(con, WL.Wikibase("https://wikibase.invalid", session=api), log=log)
    ld.p = {v: f"P{i}" for i, v in enumerate(WL.PROPS.values(), 1)}
    ld.c = {lab: f"Q{900 + i}" for i, lab in enumerate(WL.CLASSES)}
    return ld


def _map(con):
    return {r["key"]: r["qid"] for r in db.rows(con, "SELECT key, qid FROM wikibase_items")}


def test_rerun_after_losing_the_item_map_reuses_items(con):
    api = FakeAPI()
    _loader(con, api).jurisdictions(["dc", "md", "va"])
    before = _map(con)
    assert len(api.items) == 3
    con.execute("DELETE FROM wikibase_items")
    con.commit()
    _loader(con, api).jurisdictions(["dc", "md", "va"])
    assert len(api.items) == 3 and _map(con) == before
    assert not any(e["descriptions"]["en"]["value"].endswith("]") for e in api.items.values())


def test_label_clash_with_another_key_suffixes_once_and_reruns_reuse_it(con):
    api = FakeAPI()
    ld = _loader(con, api)
    for key in ("courtlistener:cluster:1", "courtlistener:cluster:2"):         # one name, court and date
        ld.entity(key, "Smith v. Jones", "Supreme Court of Virginia, 2001-01-01", [], kind="case")
    before = _map(con)
    assert len(api.items) == 2 and api.items[before["courtlistener:cluster:2"]]["descriptions"]["en"]["value"] \
        == "Supreme Court of Virginia, 2001-01-01 [2]"
    con.execute("DELETE FROM wikibase_items")
    con.commit()
    ld = _loader(con, api)
    for key in ("courtlistener:cluster:2", "courtlistener:cluster:1"):
        ld.entity(key, "Smith v. Jones", "Supreme Court of Virginia, 2001-01-01", [], kind="case")
    assert len(api.items) == 2 and _map(con) == before


def test_label_clash_never_creates_a_second_item_for_someone_elses_label(con):
    api = FakeAPI()
    api.items = {"Q1": {"id": "Q1", "labels": {"en": {"value": "Smith v. Jones"}},
                        "descriptions": {"en": {"value": "court, 2001"}}, "claims": {}},
                 "Q2": {"id": "Q2", "labels": {"en": {"value": "Smith v. Jones"}},
                        "descriptions": {"en": {"value": "court, 2001 [7]"}}, "claims": {}}}
    with pytest.raises(WL.WikibaseError, match="already has label"):
        _loader(con, api).entity("courtlistener:cluster:7", "Smith v. Jones", "court, 2001", [], kind="case")
    assert len(api.items) == 2 and not _map(con)
    with pytest.raises(WL.WikibaseError, match="rate|bad"):
        _loader(con, FakeAPI(fail="bad token")).entity("lexflow:x:1", "X", "y", [])


def test_states_filtered_run_skips_places_and_models_without_a_jurisdiction(con):
    from test_places_strategies import _govs
    _govs(con)
    dc = db.one(con, "SELECT * FROM governments WHERE state='dc'")
    va = db.one(con, "SELECT * FROM governments WHERE state='va'")
    db.upsert(con, "local_answers", [{"gov_id": g["gov_id"], "state": g["state"], "question": "records"}
                                     for g in (dc, va)])
    facts = {"actors": [{"id": "custodian", "name": "Custodian", "kind": "office"}],
             "steps": [{"id": "s1", "action": "Respond", "actor": "custodian", "modality": "obligation",
                        "source": {"section": "1"}}]}
    db.upsert(con, "process_models", [
        {"model_id": f"{st}.records", "state": st, "question": "records", "title": "Records", "tier": tier,
         "stages": "{}", "facts": json.dumps(facts), "metrics": "{}"}
        for st, tier in (("va", "reviewed"), ("md", "single"))])
    con.execute("INSERT INTO wikibase_items(key, qid) VALUES ('lexflow:process:md.records', 'Q77')")
    con.commit()
    logs = []
    api = FakeAPI()
    ld = _loader(con, api, log=logs.append)
    ld.jurisdictions(["va"])
    ld.processes()
    ld.retire_drafts()
    assert f"lexflow:gov:{va['gov_id']}" in ld.items and f"lexflow:gov:{dc['gov_id']}" not in ld.items
    assert "lexflow:process:va.records" in ld.items and "lexflow:step:va.records:s1" in ld.items
    assert any(x.startswith("skipped 1 places in dc") for x in logs)
    assert any(x.startswith("skipped 1 models in md") for x in logs)
    assert "Q77" not in api.items and "draft-retired" not in ld.counts            # the skipped draft is kept as is
