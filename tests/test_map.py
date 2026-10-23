"""The home map's holdings numbers: /api/map on a seeded temp store (municipal.map_layers)."""
import json
import sqlite3

import pytest

from lexflow.municipal import map_layers as ML
from lexflow.store import db

CVILLE, ALBEMARLE, DCGOV = "47210400100000", "47100200200000", "11000100100000"
NOW = "2026-10-18T10:00:00Z"


def _index_file(path, sections, with_meta=True):
    c = sqlite3.connect(path)
    c.executescript("CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT); CREATE TABLE sec(id INTEGER PRIMARY KEY, ref TEXT);")
    c.executemany("INSERT INTO sec VALUES (?, ?)", [(i, f"s{i}") for i in range(1, sections + 1)])
    if with_meta:
        c.execute("INSERT INTO meta VALUES ('sections', ?)", (str(sections),))
    c.commit()
    c.close()


@pytest.fixture()
def seeded(con, tmp_path):
    from lexflow.ask import coverage as CV
    CV.ensure_table(con)
    ML.clear()
    govs = [(CVILLE, "va", "City of Charlottesville", "municipality", "51540", 46000),
            (ALBEMARLE, "va", "Albemarle County", "county", "51003", 112000),
            (DCGOV, "dc", "District of Columbia", "county", "11001", 680000)]
    con.executemany("INSERT INTO governments(gov_id, state, name, kind, county_fips, population, updated_at) VALUES (?,?,?,?,?,?,?)",
                    [g + (NOW,) for g in govs])
    con.executemany("INSERT INTO process_models(model_id, state, question, scope, tier, stages, updated_at) VALUES (?,?,?,?,?,'{}',?)", [
        ("va.records", "va", "records", "state", "reviewed", NOW), ("va.business", "va", "business", "state", "reviewed", NOW),
        ("dc.records", "dc", "records", "state", "agreed", NOW), ("ca.records", "ca", "records", "state", "single", NOW),
        ("md.records", "md", "records", "state", "none", NOW)])
    ok = json.dumps({"quotes_checked": 3, "quote_misses": 0})
    facts = json.dumps({"steps": [{"label": "file"}]})
    con.executemany("INSERT INTO asked_answers(question_id, target, state, gov_id, status, facts, metrics, updated_at) VALUES (?,?,?,?,?,?,?,?)", [
        ("public_records", "va", "va", None, "answered", facts, ok, NOW),                     # counts
        ("foia_appeal", "va", "va", None, "partial", facts, json.dumps({"quotes_checked": 2, "quote_misses": 1}), NOW),  # a quote missed
        ("start_llc", "va", "va", None, "answered", json.dumps({"steps": []}), ok, NOW),      # no steps
        ("public_records", f"va:{CVILLE}", "va", CVILLE, "answered", facts, ok, NOW),        # a place answer, not a state draft
        ("public_records", "dc", "dc", None, "partial", facts, ok, NOW),                     # counts
        ("business_license", "dc", "dc", None, "not_found", facts, ok, NOW)])
    cells = [  # run, qid, state, gov, arm, verdict, missing, drafts_only, updated_at
        ("r1", "public_records", "va", "", "coverage", "none", "[]", 0, "2026-10-17T00:00:00Z"),
        ("r2", "public_records", "va", "", "coverage", "adequate", "[]", 0, NOW),
        ("r2", "public_records", "va", "", "ollama", "partial", '["fee"]', 0, NOW),           # the same cell's other arm: not a second cell
        ("r2", "foia_appeal", "va", "", "coverage", "partial", '["who"]', 1, NOW),            # partial on drafts alone -> draft
        ("r2", "start_llc", "va", "", "coverage", "partial", '["who", "form"]', 0, NOW),
        ("r2", "business_license", "va", "", "coverage", "none", '["who", "steps"]', 0, NOW),
        ("r2", "public_records", "va", CVILLE, "coverage", "adequate", "[]", 0, NOW),
        ("r2", "foia_appeal", "va", CVILLE, "coverage", "none", '["steps"]', 0, NOW),
        ("r2", "public_records", "dc", "", "coverage", "none", '["steps"]', 0, NOW),
        ("r2", "foia_appeal", "dc", "", "ollama", "adequate", "[]", 0, NOW)]                  # an Ollama-only cell still counts
    con.executemany("INSERT INTO coverage_runs(run_id, qid, state, gov_id, arm, verdict, missing, probe, updated_at) VALUES (?,?,?,?,?,?,?,?,?)",
                    [(r, q, s, g, a, v, m, json.dumps({"drafts_only": bool(d)}), t) for r, q, s, g, a, v, m, d, t in cells])
    con.executemany("INSERT INTO wikibase_items(key, qid, updated_at) VALUES (?,?,?)", [
        ("lexflow:statute:va:2.2-3704", "Q1", NOW), ("lexflow:unit:va:t2.2", "Q2", NOW), ("lexflow:statute:va:2.2-3705", "Q3", NOW),
        (f"lexflow:step:{CVILLE}:records:s1", "Q4", NOW), (f"lexflow:process:{CVILLE}:records", "Q5", NOW),
        ("lexflow:step:dc.records:file", "Q6", NOW), ("lexflow:process:asked:va:public_records", "Q7", NOW),
        ("lexflow:class:statute", "Q8", NOW), ("courtlistener:cluster:1", "Q9", NOW), ("lexflow:jurisdiction:dc", "Q10", NOW)])
    con.executemany("INSERT INTO place_processes(gov_id, state, process, verified, updated_at) VALUES (?,?,?,?,?)", [
        (CVILLE, "va", "records_request", 1, NOW), (CVILLE, "va", "business_license", 0, NOW), (ALBEMARLE, "va", "records_request", 1, NOW)])
    db.bump(con)
    con.commit()
    idx = tmp_path / "index"
    idx.mkdir()
    _index_file(idx / "statutes_va.sqlite", 123)
    _index_file(idx / "regulations_va.sqlite", 45)
    _index_file(idx / "statutes_dc.sqlite", 7, with_meta=False)       # an older index without the meta row: max(id)
    _index_file(idx / "statutes_zz.sqlite", 9)                        # not a state
    (idx / "statutes_ca.building.1.2").write_bytes(b"")               # a build in progress
    (idx / "regulations_dc.lock").write_bytes(b"")
    return con


@pytest.fixture()
def client(seeded):
    from fastapi.testclient import TestClient
    from lexflow.api.app import app
    return TestClient(app)


def test_holdings_numbers(seeded):
    h = ML.holdings(seeded)
    va, dc, ca, md = (h["states"][f] for f in ("51", "11", "06", "24"))
    # processes: reviewed and agreed state models plus the asked drafts that pass the publish rule
    assert va["processes"] == {"value": 3, "tiers": {"reviewed": 2}, "asked": 1}
    assert dc["processes"] == {"value": 2, "tiers": {"agreed": 1}, "asked": 1}
    assert ca["processes"] == {"value": 0, "tiers": {"single": 1}, "asked": 0}
    assert md["processes"]["value"] == 0 and md["processes"]["tiers"] == {"none": 1}
    # coverage: the latest run, one cell per question, drafts apart, top missing kinds
    assert va["coverage"]["run"] == "r2" and va["coverage"]["cells"] == 4
    assert {k: va["coverage"][k] for k in ("adequate", "partial", "draft", "none")} == {"adequate": 1, "partial": 1, "draft": 1, "none": 1}
    assert va["coverage"]["share"] == 0.25 and tuple(va["coverage"]["missing"][0]) == ("who", 3)
    assert dc["coverage"]["cells"] == 2 and dc["coverage"]["adequate"] == 1 and dc["coverage"]["none"] == 1
    assert ca["coverage"] is None
    # places: by county, with the coverage of the place's own cells
    assert set(h["places"]) == {"51540", "51003"}
    cv = h["places"]["51540"]["govs"][0]
    assert cv["gov_id"] == CVILLE and cv["processes"] == 2 and cv["verified"] == 1
    assert cv["coverage"]["cells"] == 2 and cv["coverage"]["adequate"] == 1 and cv["coverage"]["none"] == 1
    assert h["places"]["51003"]["govs"][0]["coverage"] is None
    # the Wikibase: keys resolve to a state through the state, a model id, a gov_id or an asked draft
    assert va["wikibase"] == {"value": 6, "kinds": {"statute": 2, "unit": 1, "step": 1, "process": 2}}
    assert dc["wikibase"] == {"value": 2, "kinds": {"step": 1, "jurisdiction": 1}}
    # the index: the meta row, or max(id) without one; non-state and in-progress files skipped
    assert va["index"] == {"value": 123, "sections": 123, "regulations": 45}
    assert dc["index"] == {"value": 7, "sections": 7, "regulations": 0}
    t = h["totals"]
    assert t["states_with_models"] == 2 and t["localities"] == 2 and t["local_processes"] == 3
    assert t["coverage"] == {"run": "r2", "cells": 6, "adequate": 2, "partial": 1, "draft": 1, "none": 2, "questions": 4}
    assert t["wikibase"] == 10 and t["wikibase_shared"] == {"class": 1, "cluster": 1}
    assert t["index"] == {"sections": 130, "regulations": 45, "states": 2}


def test_holdings_cache_follows_the_store_version(seeded):
    first = ML.holdings(seeded)
    assert ML.holdings(seeded) is first                           # same version: the cached dict
    seeded.execute("INSERT INTO place_processes(gov_id, state, process, verified, updated_at) VALUES (?,?,?,?,?)",
                   (ALBEMARLE, "va", "dog_licence", 1, NOW))
    assert ML.holdings(seeded) is first                           # no bump yet: still cached
    db.bump(seeded)
    seeded.commit()
    again = ML.holdings(seeded)
    assert again is not first and again["totals"]["local_processes"] == 4


def test_api_map_carries_the_holdings(client):
    d = client.get("/api/map").json()
    va = d["states"]["51"]
    assert va["processes"]["value"] == 3 and va["coverage"]["adequate"] == 1 and va["wikibase"]["value"] == 6 and va["index"]["sections"] == 123
    assert d["states"]["06"]["coverage"] is None and d["states"]["06"]["index"]["sections"] == 0
    assert d["places"]["51540"]["govs"][0]["name"] == "City of Charlottesville"
    assert d["holdings"]["localities"] == 2 and d["holdings"]["coverage"]["run"] == "r2"
    assert d["counties"] == {} and d["question"] == "records"   # the scored layers are untouched
    assert client.get("/api/map?question=nope").status_code == 400


def test_empty_store_has_zero_holdings(con, tmp_path):
    ML.clear()
    h = ML.holdings(con)
    assert h["states"] == {} and h["places"] == {}
    assert h["totals"]["coverage"]["run"] is None and h["totals"]["wikibase"] == 0 and h["totals"]["index"]["sections"] == 0


def test_world_view_gives_each_country_its_stage(seeded, tmp_path, monkeypatch):
    """/api/world (map_layers.world): indexed, downloaded, adapter or permission per registry entry, Australia's
    registers under its regions by ISO 3166-2 code, and the US totals from the holdings."""
    from lexflow.corpus import countries as C
    raw = tmp_path / "raw" / "countries"
    monkeypatch.setattr(C, "DIR", raw)
    (raw / "aus-wa").mkdir(parents=True)
    (raw / "aus-wa" / "list.jsonl").write_text('{"native_id": "a"}\n{"native_id": "b"}\n', encoding="utf-8")
    (raw / "aus-wa" / "progress.jsonl").write_text('{"native_id": "a", "status": "ok"}\n{"native_id": "a", "status": "ok"}\n'
                                                   '{"native_id": "b", "status": "empty"}\n', encoding="utf-8")
    (raw / "rou").mkdir()
    (raw / "rou" / "MANIFEST.json").write_text('{"acts": 50}', encoding="utf-8")   # a manifest alone: nothing downloaded
    _index_file(tmp_path / "index" / "statutes_jpn.sqlite", 40)
    _index_file(tmp_path / "index" / "statutes_aus-tas.sqlite", 5)                  # a hyphenated key is an index too
    seeded.execute("INSERT INTO wikibase_items(key, qid, updated_at) VALUES ('lexflow:unit:jpn:x', 'Q11', ?)", (NOW,))
    db.bump(seeded)
    seeded.commit()
    ML.clear()
    w = ML.world(seeded)
    assert w["stages"] == ["indexed", "downloaded", "adapter", "permission"]
    by = {c["key"]: c for c in w["countries"]}
    assert w["countries"][0]["key"] == "usa" and by["usa"]["sections"] == 130 and by["usa"]["wikibase"] == 10
    assert by["jpn"]["stage"] == "indexed" and by["jpn"]["sections"] == 40 and by["jpn"]["wikibase"] == 1
    assert by["jpn"]["numeric"] == "392" and by["bra"]["numeric"] == "076"
    assert by["per"]["stage"] == "permission" and by["per"]["note"] and by["gha"]["stage"] == "permission"
    assert by["chl"]["stage"] == "adapter" and by["rou"]["stage"] == "adapter"
    regions = {r["key"]: r for r in by["aus"]["regions"]}
    assert "aus-wa" not in by and by["aus"]["stage"] == "adapter"
    assert regions["aus-wa"]["stage"] == "downloaded" and regions["aus-wa"]["listed"] == 2 and regions["aus-wa"]["downloaded"] == 1
    assert regions["aus-tas"]["stage"] == "indexed" and regions["aus-tas"]["iso3166_2"] == "AU-TAS"
    assert regions["aus-nsw"]["stage"] == "permission"


def test_api_world(client):
    d = client.get("/api/world").json()
    assert d["countries"][0]["key"] == "usa" and {c["key"] for c in d["countries"]} >= {"jpn", "bra", "aus", "chl"}
