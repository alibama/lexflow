"""The product layer: store, Turso sync, locator, curated builds, scoring, checklist and API."""
import json
from pathlib import Path

import pandas as pd
import pytest
import responses

from lexflow import config
from lexflow.municipal import build, contacts, governments, locator, scoring, statutes
from lexflow.municipal import method as M
from lexflow.municipal.questions import QUESTIONS
from lexflow.store import db
from lexflow.store import turso as T

ROOT = Path(__file__).resolve().parents[1]
VA = json.loads((ROOT / "fixtures/statutes/va_sections.json").read_text())["sections"]


@pytest.fixture()
def con(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "TURSO_URL", "")
    monkeypatch.setattr(config, "DOKUWIKI_URL", "")
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "t.db")
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "JOBS_DIR", tmp_path / "jobs")
    c = db.connect(tmp_path / "t.db")
    yield c
    c.close()


@pytest.fixture()
def va_statutes(monkeypatch):
    """Serve the five fixture sections plus decoys as if the VA parquet were downloaded."""
    rows = [dict(act_id=f"STATE_VA_{s['section_number']}", citation=s["citation"], section_number=s["section_number"],
                 section_title=s["section_title"], chapter_name="", display_path="", act_status="in_force",
                 text=s["text"], source_url=s["source_url"], word_count=len(s["text"].split()), last_amended_year=2023)
            for s in VA]
    rows += [dict(act_id="d1", citation="Va. Code Ann. § 18.2-107", section_number="18.2-107",
                  section_title="Theft or destruction of public records by others than officers", chapter_name="",
                  display_path="", act_status="in_force", text="If any person steal public records...",
                  source_url="u", word_count=10, last_amended_year=1975)]
    df = pd.DataFrame(rows)
    df["norm_section"] = df["section_number"].map(statutes.norm_section)
    monkeypatch.setattr(statutes, "load", lambda state: df)
    monkeypatch.setattr(statutes, "have", lambda state: state == "va")
    return df


def _gov(con, n=3):
    rows = [dict(gov_id=f"g{i}", state="va", name=f"Town {i}", kind="municipality", county_fips="51003",
                 place_fips=f"0000{i}", population=1000 * i, website=f"https://town{i}.example" if i else None)
            for i in range(n)]
    rows.append(dict(gov_id="gc", state="va", name="Albemarle County", kind="county", county_fips="51003",
                     place_fips="99003", population=110000, website="https://www.albemarle.org"))
    db.upsert(con, "governments", rows)
    db.upsert(con, "contacts", [dict(gov_id="gc", state="va", question="general", kind="website",
                                     value="https://www.albemarle.org"),
                                dict(gov_id="g1", state="va", question="records", kind="page",
                                     value="https://town1.example/foia")])
    con.commit()


# ------------------------------------------------------------------ store
def test_upsert_newer_only_keeps_the_newest_row(con):
    db.upsert(con, "located_law", [dict(state="va", question="records", status="found", updated_at="2026-10-09T10:00:00Z")])
    db.upsert(con, "located_law", [dict(state="va", question="records", status="not-found",
                                        updated_at="2026-10-01T00:00:00Z")], stamp=False, newer_only=True)
    assert db.one(con, "SELECT status FROM located_law")["status"] == "found"


def test_remote_schema_covers_only_shared_tables():
    stmts = T.remote_schema()
    names = {s.split()[5] for s in stmts if s.startswith("CREATE TABLE")}
    assert names == set(db.SYNCED)


@responses.activate
def test_turso_pipeline_encodes_and_decodes_values():
    def reply(request):
        body = json.loads(request.body)
        assert body["requests"][0]["stmt"]["args"] == [{"type": "integer", "value": "5"}, {"type": "text", "value": "va"},
                                                       {"type": "null"}, {"type": "float", "value": 0.5}]
        assert body["requests"][-1] == {"type": "close"}
        assert request.headers["Authorization"] == "Bearer tok"
        res = {"type": "ok", "response": {"type": "execute", "result": {
            "cols": [{"name": "n"}, {"name": "s"}], "rows": [[{"type": "integer", "value": "7"}, {"type": "text", "value": "x"}]],
            "affected_row_count": 0}}}
        return 200, {}, json.dumps({"baton": None, "results": [res, {"type": "ok", "response": {"type": "close"}}]})
    responses.add_callback(responses.POST, "https://db-org.turso.io/v2/pipeline", callback=reply)
    t = T.Turso("libsql://db-org.turso.io", "tok")
    assert t.query("SELECT ?, ?, ?, ?", 5, "va", None, 0.5) == [{"n": 7, "s": "x"}]


@responses.activate
def test_turso_errors_name_the_statement():
    responses.add(responses.POST, "http://libsql:8080/v2/pipeline",
                  json={"results": [{"type": "error", "error": {"message": "no such table: nope"}}]})
    with pytest.raises(T.TursoError, match="no such table"):
        T.Turso("http://libsql:8080").query("SELECT * FROM nope")


# ---------------------------------------------------------------- sources
def test_census_names_read_naturally():
    assert governments.nice_name("COUNTY OF AUTAUGA", "county") == "Autauga County"
    assert governments.nice_name("CITY OF CHARLOTTESVILLE", "municipality") == "City of Charlottesville"
    assert governments.nice_name("TOWN OF MCKENNEY", "municipality") == "Town of McKenney"


def test_contact_ladder():
    assert contacts.level([], "records") == "none"
    assert contacts.level([{"question": "general", "kind": "postal"}], "records") == "postal"
    assert contacts.level([{"question": "general", "kind": "website"}], "records") == "website"
    assert contacts.level([{"question": "general", "kind": "phone"}], "records") == "direct"
    assert contacts.level([{"question": "records", "kind": "page"}], "records") == "page"
    assert contacts.level([{"question": "records", "kind": "page"}], "business") == "none"


def test_locator_uses_verified_seed_and_skips_decoys(va_statutes):
    r = locator.locate(QUESTIONS["records"], "va")
    assert r["status"] == "found" and r["section"] == "2.2-3704" and r["method"] == "seed" and r["score"] == 1.0
    b = locator.locate(QUESTIONS["business"], "va")
    assert b["section"] in ("13.1-1011", "13.1-1010") and b["status"] == "found"


def test_locator_falls_back_to_keywords(va_statutes, monkeypatch):
    monkeypatch.setitem(QUESTIONS["records"].seeds, "va", ("99-999",))
    r = locator.locate(QUESTIONS["records"], "va")
    assert r["method"] == "keyword" and r["section"] == "2.2-3704" and 0.4 <= r["score"] < 1.0
    assert "18.2-107" not in [c["section"] for c in json.loads(r["candidates"])][:1]


def test_no_statutes_is_reported(va_statutes):
    assert locator.locate(QUESTIONS["records"], "ga")["status"] == "no-statutes"


# --------------------------------------------------------- curated builds
@pytest.mark.parametrize("question", ["records", "business"])
def test_curated_virginia_model_is_reviewed_and_valid(con, va_statutes, question):
    locator.run(con, QUESTIONS[question], ["va"], log=lambda *_: None)
    out = build.build(con, "va", question, use_llm=False, log=print)
    assert out["tier"] == "reviewed"
    row = db.one(con, "SELECT * FROM process_models WHERE model_id=?", f"va.{question}")
    m = json.loads(row["metrics"])
    stages = json.loads(row["stages"])
    assert m["quote_misses"] == 0 and m["quotes_checked"] >= 10
    assert m["bpmn_xsd_errors"] == 0 and m.get("dmn_xsd_errors", 0) == 0
    assert m["lint_errors"] == 0, m
    assert m["nets"] >= 1 and m["nets_sound"] == m["nets"]
    assert stages["validated"] and stages["reviewed"] and not stages["published"]
    assert row["completion"] == pytest.approx(7 / 8) and row["quality"] > 0.8
    assert build.rebuild(con, f"va.{question}").title == row["title"]


def test_found_tier_when_no_model_available(con, va_statutes, monkeypatch):
    monkeypatch.setattr(config, "CURATED_DIR", Path("/nonexistent"))
    locator.run(con, QUESTIONS["records"], ["va"], log=lambda *_: None)
    out = build.build(con, "va", "records", use_llm=False, log=lambda *_: None)
    assert out["tier"] == "found"
    row = db.one(con, "SELECT completion, stages FROM process_models WHERE model_id='va.records'")
    assert row["completion"] == pytest.approx(2 / 8)


def test_agreement_is_one_for_identical_facts():
    from lexflow.extract.schema import LegalProcessFacts
    spec = json.loads((ROOT / "curated/va/records.json").read_text())
    f = LegalProcessFacts.model_validate(spec["facts"])
    text = VA[0]["text"]
    a = build.agreement(f, f, text)
    assert a["value"] == pytest.approx(1.0) and a["step_f1"] == 1.0


# ---------------------------------------------------------------- scoring
def test_scoring_combines_state_local_and_contact(con, va_statutes):
    _gov(con)
    locator.run(con, QUESTIONS["records"], ["va"], log=lambda *_: None)
    build.build(con, "va", "records", use_llm=False, log=lambda *_: None)
    scoring.run(con, "va", log=lambda *_: None)
    w = M.DEFAULTS["weights"]["records"]
    a1 = db.one(con, "SELECT * FROM answers WHERE gov_id='g1' AND question='records'")
    assert a1["tier"] == "reviewed" and a1["contact_level"] == "page"
    assert a1["confidence"] == pytest.approx(w["state"] * 1.0 + w["contact"] * 1.0, abs=1e-4)
    a0 = db.one(con, "SELECT * FROM answers WHERE gov_id='g0' AND question='records'")
    assert a0["contact_level"] == "none" and a0["confidence"] == pytest.approx(w["state"], abs=1e-4)
    biz = db.one(con, "SELECT tier, confidence FROM answers WHERE gov_id='gc' AND question='business'")
    assert biz["tier"] == "none"


def test_build_run_rescores_the_state(con, va_statutes):
    _gov(con)
    locator.run(con, QUESTIONS["records"], ["va"], log=lambda *_: None)
    tiers = build.run(con, ["va"], ["records"], use_llm=False, log=lambda *_: None)
    assert tiers == {"reviewed": 1}
    assert db.scalar(con, "SELECT tier FROM answers WHERE gov_id='g1' AND question='records'") == "reviewed"


def test_method_weights_can_be_changed(con):
    m = M.get(con)
    m["weights"]["records"] = {"state": 0.5, "local": 0.2, "contact": 0.3}
    assert M.save(con, m)["weights"]["records"]["local"] == 0.2


# -------------------------------------------------------------- checklist
def test_checklist_starts_with_everything_unticked(con):
    from lexflow.pipeline.steps import checklist
    items = {s["id"]: s for s in checklist(con)}
    assert items["governments"]["status"] == "todo"
    assert items["locate"]["status"] == "blocked"
    assert items["sync"]["status"] == "optional"


def test_checklist_ticks_as_data_arrives(con, va_statutes):
    from lexflow.pipeline.steps import checklist
    _gov(con, 30_001)
    db.upsert(con, "statute_files", [{"state": s, "status": "downloaded"} for s in ("va",)], keys=("state",), stamp=False)
    locator.run(con, QUESTIONS["records"], ["va"], log=lambda *_: None)
    items = {s["id"]: s for s in checklist(con)}
    assert items["governments"]["status"] == "done"
    assert items["statutes"]["status"] == "partial"
    assert items["locate"]["status"] == "partial"


# -------------------------------------------------------------------- API
def test_api_smoke(con, va_statutes, monkeypatch):
    from fastapi.testclient import TestClient
    from lexflow.api import app as A
    monkeypatch.setattr(A.runner, "start", lambda: None)
    _gov(con)
    locator.run(con, QUESTIONS["records"], ["va"], log=lambda *_: None)
    build.build(con, "va", "records", use_llm=False, log=lambda *_: None)
    scoring.run(con, "va", log=lambda *_: None)
    with TestClient(A.app) as c:
        assert c.get("/api/health").json()["ok"]
        assert {s["id"] for s in c.get("/api/setup").json()["steps"]} >= {"governments", "build", "sync"}
        mp = c.get("/api/map?question=records&layer=confidence").json()
        assert mp["counties"]["51003"]["n"] == 4
        assert mp["states"]["51"]["tier"] == "reviewed"
        model = c.get("/api/models/va.records").json()
        assert model["tier"] == "reviewed" and model["steps"] and model["law"]["section"] == "2.2-3704"
        assert c.get("/api/models/va.records/bpmn").text.startswith("<?xml")
        ans = c.get("/api/answers/g1").json()["answers"]["records"]
        assert ans["steps"][0]["cite"].startswith("§ 2.2-3704")
        assert c.get("/api/lookup?url=https://www.albemarle.org/government").json()["matches"]
        job = c.post("/api/jobs", json={"step": "score", "args": {"states": "va"}}).json()
        assert c.get(f"/api/jobs/{job['id']}").json()["status"] == "queued"
        assert c.post("/api/jobs", json={"step": "nope"}).status_code == 400
        assert c.put("/api/method", json={"weights": {"records": {"state": 1, "local": 1, "contact": 1}}}).status_code == 400
        assert c.get("/").status_code == 200
