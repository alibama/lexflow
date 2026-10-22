"""Retirement benefits (lexflow.benefits, docs/design/retirement-benefits.md): the Census unit-file reader and its
join to governments, the grounding of the fixtures, the Virginia family's eligibility rules (the Rule of 90 written
as decision-table rules), the fixtures' shapes and privacy, the lookup, and the API route."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from lexflow import config
from lexflow.benefits import census as C
from lexflow.benefits import family_va as FV
from lexflow.benefits import ground as G
from lexflow.benefits import programs as PR

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "fixtures" / "benefits"

HEADER = "SAMPLE_YEAR,UNIT_NAME,PID6,STATE,UNIT_TYPE,ITEM_CODE,ITEM_VALUE,EIC,ISC,FINAL_WEIGHT\n"


def _unit_file(path: Path, year: int, rows: list[tuple]) -> Path:
    lines = [HEADER] + [f"{year},{n},{p},{s},{t},{code},{v},R,V,1\n" for n, p, s, t, code, v in rows]
    path.write_text("﻿" + "".join(lines), encoding="utf-8")
    return path


def _govs(con):
    from lexflow.store import db
    rows = [("51100100100000", "va", "Fairfax County", "county", "FAIRFAX"),
            ("51200100100000", "va", "City of Fairfax", "municipality", "FAIRFAX"),
            ("51200200100000", "va", "City of Charlottesville", "municipality", "CHARLOTTESVILLE CITY"),
            ("42300100100000", "pa", "Township of Penn", "township", "YORK"),
            ("42300200100000", "pa", "Township of Penn", "township", "LANCASTER"),
            ("27300100100000", "mn", "Township of Clinton", "township", "ST LOUIS"),
            ("27300200100000", "mn", "Township of Clinton", "township", "ROCK"),
            ("24100100100000", "md", "Washington County", "county", "WASHINGTON")]
    db.upsert(con, "governments", [{"gov_id": g, "state": s, "name": n, "kind": k, "county_name": cn,
                                    "updated_at": db.now()} for g, s, n, k, cn in rows])
    con.commit()


# ============================================================================================== the Census join
def test_display_names_read_the_census_abbreviations():
    assert C.display_name("VIRGINIA RETIREMENT SYSTEM (STATE)") == "Virginia Retirement System (State)"
    assert C.display_name("AK PUBLIC EMPLOYEES RET SYSTEM (PERS-DB)") == "Alaska Public Employees Retirement System (PERS-DB)"
    assert C.display_name("VA LAW OFFICERS' RET SYSTEM (VALORS)") == "Virginia Law Officers' Retirement System (VaLORS)"
    assert C.display_name("WASHINGTON CO COUNTY PENSION PLAN") == "Washington County Pension Plan"


def test_government_core_names():
    assert C.gov_core("City of Charlottesville") == ["charlottesville"]
    assert C.gov_core("Fairfax County") == ["fairfax"]
    assert C.gov_core("City of University City") == ["university", "city"]
    assert C.gov_core("Township of Upper Merion") == ["upper", "merion"]


def test_name_join_unique_ambiguous_hinted_and_other_bodies():
    va_cities = [{"gov_id": "c1", "name": "City of Charlottesville", "kind": "municipality"},
                 {"gov_id": "c2", "name": "City of Fairfax", "kind": "municipality"}]
    m = C.match_government("CHARLOTTESVILLE RETIREMENT FUND", va_cities)
    assert m["gov_id"] == "c1" and "charlottesville" in m["how"]
    assert C.match_government("NORFOLK EMPLOYEES RETIREMENT SYSTEM", va_cities)["gov_id"] is None
    twps = [{"gov_id": "p1", "name": "Township of Penn", "kind": "township", "county_name": "YORK"},
            {"gov_id": "p2", "name": "Township of Penn", "kind": "township", "county_name": "LANCASTER"}]
    amb = C.match_government("PENN TWP POLICE PENSION PLAN", twps)
    assert amb["gov_id"] is None and amb["how"].startswith("ambiguous") and amb["candidates"] == 2
    mn = [{"gov_id": "m1", "name": "Township of Clinton", "kind": "township", "county_name": "ST LOUIS"},
          {"gov_id": "m2", "name": "Township of Clinton", "kind": "township", "county_name": "ROCK"}]
    assert C.match_government("CLINTON FIRE RELIEF ASSOCIATION [ST LOUIS]", mn)["gov_id"] == "m1"
    counties = [{"gov_id": "w1", "name": "Washington County", "kind": "county"}]
    assert C.match_government("WASHINGTON SUBURBAN SANITARY COMMISSION RETIREMENT PLAN", counties)["gov_id"] is None
    assert C.match_government("WASHINGTON COUNTY PENSION PLAN", counties)["gov_id"] == "w1"


def test_membership_and_local_coverage_rules():
    vrs_psd = {"census_name": "VIRGINIA RETIREMENT SYSTEM (POLITICAL SUBDIVISIONS)", "type": "0", "items": {"RJ11": 5}}
    m = C.membership(vrs_psd)
    assert [x["type"] for x in m] == ["local_employee"] and C.covers_local(vrs_psd, m)
    spors = {"census_name": "VA STATE POLICE OFFICERS' RET SYSTEM (SPORS)", "type": "0", "items": {}}
    m = C.membership(spors)
    assert {x["type"] for x in m} == {"public_safety", "state_employee"} and not C.covers_local(spors, m)
    pers = {"census_name": "AK PUBLIC EMPLOYEES RET SYSTEM (PERS-DB)", "type": "0", "items": {"RJ12": 0},
            "local_members_years": [2022]}
    assert C.covers_local(pers, C.membership(pers))          # local members in an earlier year still count
    calstrs = {"census_name": "CALSTRS DEFINED BENEFIT PROGRAM", "type": "0", "items": {}}
    assert [x["type"] for x in C.membership(calstrs)] == ["teacher"]
    local = {"census_name": "FAIRFAX COUNTY POLICE OFFICERS RETIREMENT SYSTEM", "type": "1", "items": {}}
    assert [x["type"] for x in C.membership(local)] == ["public_safety"]


def test_build_and_load_join_systems_to_governments(con, tmp_path):
    _govs(con)
    f25 = _unit_file(tmp_path / "u25.csv", 2025, [
        ("VIRGINIA RETIREMENT SYSTEM (POLITICAL SUBDIVISIONS)", "1", "VA", "0", "RJ10", "100"),
        ("VIRGINIA RETIREMENT SYSTEM (POLITICAL SUBDIVISIONS)", "1", "VA", "0", "RJ12", "100"),
        ("VA STATE POLICE OFFICERS' RET SYSTEM (SPORS)", "2", "VA", "0", "RJ11", "50"),
        ("CHARLOTTESVILLE RETIREMENT FUND", "3", "VA", "2", "RJ10", "678")])
    f22 = _unit_file(tmp_path / "u22.csv", 2022, [
        ("FAIRFAX COUNTY EMPLOYEES RETIREMENT SYSTEM", "4", "VA", "1", "RJ10", "9000"),
        ("PENN TWP POLICE PENSION PLAN", "5", "PA", "3", "RJ10", "5"),
        ("CHARLOTTESVILLE RETIREMENT FUND", "3", "VA", "2", "RJ20", "781")])
    units = C.merged({2025: f25, 2022: f22})
    assert units["3"]["years"] == [2025, 2022] and units["3"]["items"] == {"RJ10": 678, "RJ20": 781}
    stats = C.load(con, log=lambda m: None, units=units, use_curated=False)
    assert stats["systems"] == 5 and stats["local_joined"] == 2 and stats["local_ambiguous"] == 1
    from lexflow.store import db
    cvl = db.rows(con, "SELECT * FROM pension_coverage WHERE gov_id='51200200100000' ORDER BY how")
    assert [(r["system_id"], r["how"]) for r in cvl] == [("census-pid6:3", "administers"), ("census-pid6:1", "statewide")]
    ffx_city = {r["system_id"] for r in db.rows(con, "SELECT system_id FROM pension_coverage WHERE gov_id='51200100100000'")}
    assert ffx_city == {"census-pid6:1"}                       # the county's system is not the city's
    assert not db.rows(con, "SELECT 1 FROM pension_coverage WHERE system_id='census-pid6:2'")   # SPORS: state only
    assert stats["governments_with_own_system"] == 2
    row = db.one(con, "SELECT * FROM pension_systems WHERE id='census-pid6:3'")
    assert row["level"] == "local" and row["admin_gov_id"] == "51200200100000" and row["members_active"] == 678


# ================================================================================================= grounding
def test_ground_statute_and_page_sources(monkeypatch):
    text = "The governing body of a political subdivision may adopt a resolution requesting that its eligible employees"
    monkeypatch.setattr(G, "statute_rows", lambda st, ref: [{"ref": ref, "citation": f"Va. Code § {ref}",
                                                              "url": "u", "text": text}])
    ok = G.ground({"kind": "statute", "ref": "51.1-130", "quote": "may adopt a resolution requesting"}, "va")
    assert ok["grounding"]["matched"] and ok["grounding"]["by"] == "code" and ok["citation"] == "Va. Code § 51.1-130"
    bad = G.ground({"kind": "statute", "ref": "51.1-130", "quote": "may not adopt any resolution"}, "va")
    assert not bad["grounding"]["matched"] and "word for word" in bad["grounding"]["why"]
    from lexflow.municipal import quotes as Q
    monkeypatch.setattr(Q, "cached", lambda u: {"url": u, "via": "live", "fetched": "2026-10-22",
                                                "text": "Welcome to your Maryland State Retirement and Pension System"})
    pg = G.ground({"kind": "page", "url": "https://sra.maryland.gov/", "quote": "your Maryland State Retirement"})
    assert pg["grounding"]["matched"] and pg["grounding"]["by"] == "live"
    assert not G.ground({"kind": "page", "url": "x", "quote": "two words"})["grounding"]["matched"]
    doc = {"state": "va", "items": {"a": {"sources": [{"kind": "statute", "ref": "51.1-130",
                                                         "quote": "may adopt a resolution requesting"}]}}}
    rep = G.ground_all(doc)
    assert rep == {"sources": 1, "matched": 1, "by": {"code": 1}, "unmatched": []}
    assert doc["items"]["a"]["sources"][0]["grounding"]["matched"]


# ============================================================================================ the VA family
def test_eligibility_rules_follow_the_code():
    E = FV.eligibility
    assert E("plan1", 65, 5)[0] == "unreduced" and E("plan1", 50, 30)[:2] == ("unreduced", "plan1_50_30")
    assert E("plan1", 55, 25)[:2] == ("reduced", "early_55_5") and E("plan1", 52, 10)[:2] == ("reduced", "plan1_50_10")
    assert E("plan1", 52, 9)[0] == "not_yet"
    assert E("plan2", 60, 30)[:2] == ("unreduced", "rule_of_90") and E("plan2", 60, 29)[:2] == ("reduced", "early_60_5")
    assert E("plan2", 67, 5)[:2] == ("unreduced", "normal") and E("plan2", 59, 30)[0] == "not_yet"
    assert E("hazardous", 50, 25)[0] == "unreduced" and E("hazardous", 50, 24)[0] == "reduced"
    assert E("hazardous", 60, 5)[0] == "unreduced" and E("hazardous", 49, 30)[0] == "not_yet"


def test_rule_runs_reproduce_eligibility_on_the_whole_grid():
    """The decision-table rules written from ``runs`` give, for every whole age and year of service, exactly one
    retirement rule per plan class, with the category ``eligibility`` computes (the Rule of 90 is exact)."""
    from lexflow.scenarios import dmn
    rules = FV.retirement_rules()
    table = {"id": "retirement", "hit_policy": "COLLECT", "rules": rules,
             "inputs": [{"name": "plan", "type": "string"}, {"name": "employer", "type": "string"},
                        {"name": "age", "type": "number"}, {"name": "service", "type": "number"}],
             "outputs": [{"name": "requirement", "type": "string"}, {"name": "status", "type": "string"}]}
    assert dmn.check(table) == []
    cat = {"retire_unreduced": "unreduced", "retire_reduced": "reduced", "retire_not_yet": "not_yet"}
    cases = [("plan1", "plan1", "teacher"), ("plan2", "plan2", "state"), ("plan2", "hybrid", "political_subdivision"),
             ("hazardous", "plan2", "hazardous"), ("hazardous", "plan1", "hazardous")]
    for klass, plan, emp in cases:
        for age in range(18, 91, 1):
            for svc in range(0, 46, 1):
                res = dmn.evaluate(table, {"plan": plan, "employer": emp, "age": age, "service": svc})
                assert len(res["hits"]) == 1, (klass, age, svc, res["hits"])
                assert cat[res["outputs"][0]["requirement"]] == FV.eligibility(klass, age, svc)[0], (klass, age, svc)


def test_committed_family_is_grounded_and_answers_the_personas():
    from lexflow.scenarios import run as R
    from lexflow.scenarios.family import Family
    fam = Family.load("retirement_va")
    assert fam.check() == [] and not fam.dropped
    g = fam.spec.get("grounding") or {}
    assert g.get("sources") and g["matched"] == g["sources"]
    got = {}
    for pid in fam.personas:
        out = R.evaluate(fam, fam.persona_inputs(pid, "virginia"))
        ids = {r["id"]: r for r in out["requirements"]}
        got[pid] = ids
        assert all((r.get("source") or {}).get("matched") for r in out["requirements"])
        assert all(r["office"]["label"] for r in out["requirements"])
    assert "retire_reduced" in got["teacher_55_25"] and "plan_1" in got["teacher_55_25"]
    assert "retire_reduced" in got["state_60_10"] and "plan_2" in got["state_60_10"]
    assert got["firefighter_50_25"]["retire_unreduced"]["status"] == "required"
    assert "ask_hazardous_election" in got["firefighter_50_25"]
    assert got["hybrid_45_8"]["retire_not_yet"]["status"] == "not required" and "plan_hybrid" in got["hybrid_45_8"]
    # a hazardous-duty member hired in 2014 or later is in Plan 2, never the hybrid program (scope of the value)
    assert fam.violations(fam.normalise({"employer": "hazardous", "membership": "2014_on", "age": 40, "service": 10}))
    o = R.evaluate(fam, {"employer": "hazardous", "membership": "2014_on_hazardous", "age": 50, "service": 10})
    assert o["derived"]["plan"] == "plan2" and "retire_reduced" in {r["id"] for r in o["requirements"]}
    # changing nothing the tables read never changes the output
    a = R.evaluate(fam, {"employer": "state", "membership": "2010_to_2013", "age": 62, "service": 28})
    b = R.evaluate(fam, {"employer": "state", "membership": "before_2010_not_vested", "age": 62, "service": 28})
    assert {r["id"] for r in a["requirements"]} == {r["id"] for r in b["requirements"]} and \
        "retire_unreduced" in {r["id"] for r in a["requirements"]}   # 62 + 28 = 90


# ============================================================================================== the fixtures
def test_tax_fixtures_shape():
    files = sorted((FIX / "tax").glob("*.json"))
    assert len(files) >= 51
    for f in files:
        d = json.loads(f.read_text(encoding="utf-8"))
        assert d["state"] == f.stem and set(d["items"]) == set(PR.INCOME_ITEMS), f
        for k, it in d["items"].items():
            assert it["treatment"] in PR.TREATMENTS, (f, k)
            if it["treatment"] != "unknown":
                assert it.get("sources"), (f, k)
            for s in it.get("sources") or []:
                assert s["kind"] in G.KINDS and len(s["quote"].split()) >= 3, (f, k)


def test_auto_ira_and_federal_fixtures_shape():
    d = json.loads((FIX / "auto_ira.json").read_text(encoding="utf-8"))
    kinds = {"creates", "board", "mandate", "threshold", "deadline", "exemption", "self_employed", "penalty",
             "default_contribution", "voluntary"}
    ids = [p["id"] for p in d["programs"]]
    assert len(ids) == len(set(ids)) and {"va", "md", "ca", "or", "il"} <= {p["state"] for p in d["programs"]}
    for p in d["programs"]:
        assert p["status"] in ("open", "enacted", "closed") and isinstance(p["mandate"], bool)
        for f in p["facts"]:
            assert f["kind"] in kinds and f["sources"], (p["id"], f)
    fed = json.loads((FIX / "federal.json").read_text(encoding="utf-8"))
    for p in fed["programs"]:
        assert set(p["applies_to"]) <= set(PR.PERSON_TYPES) and p["url"].startswith("https://")


def test_systems_fixtures_cover_each_census_unit_once():
    files = sorted((FIX / "systems").glob("*.json"))
    assert len(files) >= 51
    roles = {"establishes", "defines", "none", None}
    for f in files:
        d = json.loads(f.read_text(encoding="utf-8"))
        seen = []
        for s in d["systems"]:
            seen += s.get("census_units") or []
            assert s.get("statute_role") in roles, (f, s["name"])
            assert set(s.get("membership") or []) <= {"state_employee", "teacher", "local_employee", "public_safety",
                                                       "judge", "legislator"}, (f, s["name"])
        assert len(seen) == len(set(seen)), f


def test_channels_in_fixtures_are_office_channels_only():
    from lexflow.ask import who as W
    for f in sorted((FIX / "systems").glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        for s in d["systems"]:
            owner = [(s.get("body") or {}).get("name") or s["name"], s["name"]]
            for c in s.get("channels") or []:
                assert W._channel(c["kind"], c["value"], c.get("label"), "fixture", None, owner), (f, c)
            assert "@" not in json.dumps(s.get("channels") or []) or all(
                c["kind"] != "email" or W.channel_ok("email", c["value"], c.get("label"), owner)
                for c in s.get("channels") or [])


def test_va_pilot_fixtures_name_no_person():
    """The pilot's own fixtures hold programs, bodies and offices only: no personal title with a name."""
    import re
    for p in [FIX / "systems" / "va.json", FIX / "systems" / "md.json", FIX / "va_retirement_backbone.json",
              FIX / "federal.json", ROOT / "fixtures" / "families" / "retirement_va.json"]:
        text = p.read_text(encoding="utf-8")
        assert not re.search(r"\b(Mr|Mrs|Ms|Dr)\.\s+[A-Z][a-z]+", text), p
        assert "Davenport" not in text


# ====================================================================================== lookup and the API
def _index_ready(st: str) -> bool:
    try:
        from lexflow.ask import index as I
        return I.ready(st)
    except Exception:  # noqa: BLE001
        return False


def test_lookup_virginia_teacher_with_the_real_fixtures():
    if not _index_ready("va"):
        pytest.skip("no Virginia statute index on this copy")
    from lexflow.benefits import lookup as L
    from lexflow.store import db
    con = db.connect()
    try:
        out = L.lookup("va", "teacher", con)
        names = [s["name"] for s in out["systems"]]
        assert names == ["Virginia Retirement System"]
        vrs = out["systems"][0]
        assert vrs["statute"]["matched"] and "establishes the Virginia Retirement System" in vrs["statute"]["quote"]
        assert vrs["family"]["id"] == "retirement_va" and vrs["apply"]["grounded"] and vrs["appeal"]["grounded"]
        assert any(c["kind"] == "phone" for c in vrs["channels"])
        assert out["tax"]["items"]["social_security"]["treatment"] == "exempt"
        assert any(f["id"] == "us_social_security_retirement" for f in out["federal"])
        priv = L.lookup("va", "private_no_plan", con)
        assert priv["auto_ira"] and priv["auto_ira"][0]["mandate"] and priv["auto_ira"][0]["smallest_employer"] == 5
        with pytest.raises(L.LookupError_):
            L.lookup("va", "astronaut", con)
        cards = L.ask("va", "teacher", con)["roles"]
        assert cards[0]["played_by"]["label"].startswith("Board of Trustees") and cards[0]["quotes"]
    finally:
        con.close()


def test_api_benefits_route(con, monkeypatch):
    from fastapi.testclient import TestClient
    from lexflow.api import app as API
    monkeypatch.setattr(config, "JOB_RUNNER", False)
    with TestClient(API.app) as c:
        types = c.get("/api/benefits").json()["person_types"]
        assert {t["id"] for t in types} == set(PR.PERSON_TYPES)
        assert c.get("/api/benefits", params={"gov_id": "va"}).status_code == 400
        assert c.get("/api/benefits", params={"gov_id": "va", "person": "Bad-Type"}).status_code == 422
        assert c.get("/api/benefits", params={"gov_id": "zz-nowhere", "person": "teacher"}).status_code == 400
        if _index_ready("md"):
            r = c.get("/api/benefits", params={"gov_id": "md", "person": "private_no_plan"})
            assert r.status_code == 200 and r.json()["auto_ira"][0]["id"] == "md_marylandsaves"
