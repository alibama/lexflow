"""lexflow.scenarios: the decision-table evaluator, the glass-studio family, its scenario space, runs, sensitivity,
intake, storage, the API and the coverage signal, and the invariants docs/design/hypotheticals.md promises."""
from __future__ import annotations

import copy
import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lexflow import config  # noqa: E402
from lexflow.scenarios import dmn  # noqa: E402
from lexflow.scenarios import expand as X  # noqa: E402
from lexflow.scenarios import intake as IN  # noqa: E402
from lexflow.scenarios import run as R  # noqa: E402
from lexflow.scenarios import sensitivity as SE  # noqa: E402
from lexflow.scenarios.family import COUNTED, Family, FamilyError  # noqa: E402
from lexflow.store import db  # noqa: E402

FAMILY = "glass_studio_va"


@pytest.fixture(scope="module")
def fam():
    return Family.load(FAMILY)


@pytest.fixture(scope="module")
def population(fam):
    """Every pairwise scenario, under the baseline and each variant, evaluated once."""
    tests = X.pairwise(fam, by_class=True, variants=tuple(fam.variants))
    outs = [R.evaluate(fam, t) for t in tests]
    outs += [R.evaluate(fam, t, v) for t in tests for v in fam.variants]
    return tests, outs


@pytest.fixture(scope="module")
def personas(fam):
    return {(p, loc): R.evaluate(fam, fam.persona_inputs(p, loc)) for p in fam.personas for loc in fam.localities()}


# ======================================================================================== the evaluator
def _records():
    return json.loads((ROOT / "curated" / "va" / "records.json").read_text(encoding="utf-8"))["facts"]["decisions"]


def test_va_records_response_type_follows_the_statute():
    d = next(x for x in _records() if x["id"] == "response_type")
    assert dmn.check(d) == []
    def ev(**kw):
        return dmn.evaluate(d, kw)
    r = ev(practical=False, records_exist=True, all_exempt=False, some_exempt=False)
    assert r["hits"] == [0] and r["outputs"]["not_practically_possible"] is True
    assert ev(practical=True, records_exist=False, all_exempt=False, some_exempt=False)["hits"] == [1]
    assert ev(practical=True, records_exist=True, all_exempt=True, some_exempt=True)["outputs"]["response"].startswith("Entirely withheld")
    r = ev(practical=True, records_exist=True, all_exempt=False, some_exempt=True)
    assert r["hits"] == [3] and r["outputs"]["records_provided"] is True
    assert ev(practical=True, records_exist=True, all_exempt=False, some_exempt=False)["outputs"]["response"] == "Provide the records"
    assert dmn.gaps(d) == []                         # FIRST over the whole grid: complete
    assert d["rules"][1]["source"]["subsection"] == "B.3"


def _curated_decisions():
    for p in sorted((ROOT / "curated").glob("*/*.json")):
        try:
            spec = json.loads(p.read_text(encoding="utf-8"))
        except ValueError:
            continue
        for d in (spec.get("facts") or {}).get("decisions") or []:
            yield p, d


def test_two_implementations_agree_on_every_curated_decision():
    """VRSLite's reconciliation idea: lexflow.scenarios.dmn (the facts shape) and lexflow.dmn_eval (the compiled IR)
    give the same rule and outputs at every point of every curated table's grid."""
    from lexflow.dmn_eval import decide
    n = points = 0
    for p, d in _curated_decisions():
        if d.get("hit_policy") not in ("FIRST", "UNIQUE"):
            continue
        ir = dmn.to_ir(d)
        n += 1
        for g in dmn.grid(d):
            points += 1
            try:
                mine = dmn.evaluate(d, g)
            except dmn.DecisionError:
                with pytest.raises(ValueError):
                    decide(ir, g)
                continue
            theirs = decide(ir, g)
            if not mine["hits"]:
                assert theirs == {}, (p.name, d["id"], g)
                continue
            assert theirs.pop("_rule") == f"{d['id']}_r{mine['hits'][0] + 1}", (p.name, d["id"], g)
            assert theirs == mine["outputs"], (p.name, d["id"], g)
    assert n >= 50 and points > 1000


def test_hit_policies_cells_and_errors():
    d = {"id": "t", "hit_policy": "COLLECT",
         "inputs": [{"name": "n", "type": "number"}, {"name": "kind", "type": "string"}, {"name": "flag", "type": "boolean"}],
         "outputs": [{"name": "out", "type": "string"}],
         "rules": [{"when": [">=50", "-", "-"], "then": ['"big"']}, {"when": ["<50", '"a","b"', "-"], "then": ['"small ab"']},
                   {"when": ["[1..49]", 'not("a")', "true"], "then": ['"small not a"']},
                   {"when": ["(50000..100000]", "-", "-"], "then": ['"mid band"']}]}
    assert dmn.check(d) == []
    assert [o["out"] for o in dmn.evaluate(d, {"n": 60, "kind": "a", "flag": False})["outputs"]] == ["big"]
    assert [o["out"] for o in dmn.evaluate(d, {"n": 10, "kind": "b", "flag": True})["outputs"]] == ["small ab", "small not a"]
    assert dmn.evaluate(d, {"n": 50000, "kind": "c", "flag": False})["outputs"][0]["out"] == "big"
    assert [o["out"] for o in dmn.evaluate(d, {"n": 100000, "kind": "c", "flag": False})["outputs"]] == ["big", "mid band"]
    u = {**d, "hit_policy": "UNIQUE"}
    with pytest.raises(dmn.DecisionError):
        dmn.evaluate(u, {"n": 10, "kind": "b", "flag": True})
    f = {**d, "hit_policy": "FIRST"}
    assert dmn.evaluate(f, {"n": 10, "kind": "b", "flag": True})["hits"] == [1]
    a = {**d, "hit_policy": "ANY"}
    with pytest.raises(dmn.DecisionError):
        dmn.evaluate(a, {"n": 10, "kind": "b", "flag": True})
    with pytest.raises(dmn.DecisionError):
        dmn.evaluate(d, {"n": 10})                   # strict: an input the table names is missing
    assert dmn.matches("-", None) and not dmn.matches(">= 2", None)
    with pytest.raises(dmn.DecisionError):
        dmn.matches(">= 2", "x")                     # a number test on a string is a modelling error
    assert dmn.check({**d, "rules": [{"when": ["-"], "then": []}]})


def _bpc_checker():
    path = ROOT / "out" / "design" / "check_bpc_480.py"
    if not path.exists() or not (ROOT / "out" / "design" / "bpc_480.dmn").exists():
        pytest.skip("out/design/bpc_480.dmn and its checker are not present here")
    pytest.importorskip("lxml")
    spec = importlib.util.spec_from_file_location("check_bpc_480_for_tests", path)
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except ImportError as e:
        pytest.skip(f"the checker's imports are not available here: {e}")
    return mod


def test_bpc_480_cases_through_the_imported_tables():
    """out/design/bpc_480.dmn read into the facts shape: every applicant's every table hits the rule the applicant
    states independently (``path``), with the outputs lexflow.dmn_eval gives."""
    chk = _bpc_checker()
    from lxml import etree
    model = dmn.from_dmn(ROOT / "out" / "design" / "bpc_480.dmn")
    tables = {t["id"]: t for t in model["tables"]}
    assert len(tables) == 9 and set(model["literals"]) == {"conviction_recent", "incarceration_recent",
                                                             "discipline_recent", "discipline_older"}
    assert all(r["source"] and r["source"].get("quote") for t in tables.values() for r in t["rules"])
    drd = chk.DRD(etree.parse(str(ROOT / "out" / "design" / "bpc_480.dmn")).getroot())
    checked = 0
    for a in chk.resolved():
        env, hits = drd.evaluate(a)
        for name, n in zip(chk.PATH_TABLES, a["path"]):
            t = tables[f"d_{name}"]
            data = {i["name"]: env.get(i["name"]) for i in t["inputs"]}
            mine = dmn.evaluate(t, data)
            assert t["rules"][mine["hits"][0]]["id"] == f"d_{name}_r{n}" == hits[f"d_{name}"], (a["id"], name)
            want = env[t["name"]] if len(t["outputs"]) == 1 else env[t["name"]]
            got = mine["outputs"][t["outputs"][0]["name"]] if len(t["outputs"]) == 1 else mine["outputs"]
            assert got == want, (a["id"], name)
            checked += 1
    assert checked > 300
    for t in tables.values():                        # Catala's checks over each UNIQUE table's whole domain
        doms = {i["name"]: ([True, False] if i["type"] == "boolean" else [v.strip('"') for v in i.get("values") or []])
                for i in t["inputs"]}
        assert dmn.conflicts(t, doms) == [] and dmn.gaps(t, doms) == [], t["id"]


# ======================================================================================== the family
def test_family_shape_and_grounding(fam):
    assert fam.check() == []
    s = fam.summary()
    assert s["dimensions"] == 12 and s["tables"] == 8 and s["rules"] >= 100 and s["dropped"] == 0
    g = fam.spec["grounding"]
    assert g["sources"] == g["matched"] and not g["unmatched"]
    for t in fam.tables:
        assert t["hit_policy"] == "COLLECT"
        for r in t["rules"]:
            src = r["source"]
            assert src["grounding"]["matched"] and src["from"].split("#")[0] in _allowed_files(), r["id"]
            assert src.get("quote") or (src.get("quote_sha256") and src.get("paraphrase")), r["id"]
    assert fam.grammar_text().startswith("{LOC}-{DIST}-{BLD}-{FUEL}")
    assert set(fam.spec["serves"]) >= {f"glass_q{i}" for i in (1, 2, 3, 5, 6, 7, 10, 11, 12)} | {"glass_studio"}


def _allowed_files():
    files = {str(p.relative_to(ROOT)).replace("\\", "/") for p in (ROOT / "curated" / "places" / "va").glob("*/glass_*.json")}
    return files | {"fixtures/places/va/glass/state-backbone.json"}


def test_every_pointer_quote_is_still_in_its_file(fam):
    """The quote a rule carries is the one at its pointer (the committed form of the file)."""
    from lexflow.scenarios.family import resolve
    for t in fam.spec["tables"]:
        for r in t["rules"]:
            for key in ("source", "fee_source", "deadline_source"):
                src = r.get(key)
                if not src:
                    continue
                f, where = src["from"].split("#")
                entry = resolve(json.loads((ROOT / f).read_text(encoding="utf-8")), where)
                if src.get("quote"):
                    assert entry.get("quote") == src["quote"], (r["id"], key)
                else:
                    assert entry.get("quote_sha256") == src["quote_sha256"], (r["id"], key)


def test_grammar_round_trip_and_personas(fam, population):
    tests, outs = population
    for o in outs:
        inputs, variant = fam.parse_id(o["scenario"])
        assert fam.scenario_id(inputs, variant) == o["scenario"]
    for p in fam.personas:
        for loc in fam.localities():
            inp = fam.persona_inputs(p, loc)
            assert not fam.violations(inp)
    with pytest.raises(FamilyError):
        fam.parse_id("CVL-CCX8")
    with pytest.raises(FamilyError):
        R.evaluate(fam, {**fam.persona_inputs("cold_studio", "albemarle"), "district": "CX-8"})   # out of scope


# ======================================================================================== the space
def test_expansion_counts_and_pairwise_coverage(fam, population):
    full, by = X.count(fam, by_class=False), X.count(fam, by_class=True)
    assert full["valid"] > by["valid"] > 1000 and full["product"] > full["valid"]
    tests, _ = population
    cov = X.pair_coverage(fam, tests, by_class=True, variants=tuple(fam.variants))
    assert cov["covered"] == cov["valid_pairs"] and len(tests) < 80
    for t in tests:
        assert not fam.violations(t)
        assert not (t["alcohol"] != "none" and t["occupants"] == 0 and t["food"] == "none")   # C1 prunes


def test_district_classes_are_equivalent(fam):
    """Two districts of one class give the same output for every table (why the expansion keeps one of each)."""
    base = fam.persona_inputs("hot_shop_classes", "charlottesville")
    groups = X.classes(fam, "district", tuple(fam.variants))
    for rep, members in groups.items():
        outs = []
        for code in members:
            opt = fam.dim["district"].by_code(code)
            loc = opt["scope"]["locality"][0]
            inp = {**fam.persona_inputs("hot_shop_classes", loc), "district": opt["value"]}
            for v in [None, *fam.variants]:
                o = R.evaluate(fam, inp, v)
                outs.append((v, json.dumps([(r["id"], r["status"]) for r in o["requirements"]])))
        by_variant = {}
        for v, sig in outs:
            by_variant.setdefault(v, set()).add(sig)
        assert all(len(s) == 1 for s in by_variant.values()), rep
    assert base["district"] == "IX-5"


def test_a_dimension_no_rule_reads_never_changes_the_output(fam):
    spec = copy.deepcopy(fam.spec)
    spec["dimensions"].append({"name": "kiln_colour", "label": "Kiln colour", "type": "string", "default": "red",
                               "values": [{"value": "red", "code": "KR", "label": "Red"},
                                          {"value": "blue", "code": "KB", "label": "Blue"}]})
    spec["grammar"]["slots"].append("kiln_colour")
    f2 = Family(spec)
    referenced = f2.table_inputs() | {d["from"] for d in f2.derived}
    unread = [d.name for d in f2.dims if d.name not in referenced]
    assert unread == ["kiln_colour"]
    for p in f2.personas:
        for loc in f2.localities():
            inp = f2.persona_inputs(p, loc)
            a = R.evaluate(f2, {**inp, "kiln_colour": "red"})
            b = R.evaluate(f2, {**inp, "kiln_colour": "blue"})
            strip = lambda o: json.dumps({k: v for k, v in o.items() if k not in ("scenario", "inputs", "ms")}, default=str)
            assert strip(a) == strip(b)


# ======================================================================================== the invariants
def test_every_requirement_cites_a_matched_quote(population, personas):
    _, outs = population
    for o in list(outs) + list(personas.values()):
        assert o["requirements"]
        for r in o["requirements"]:
            s = r["source"]
            # the words, or for a site that forbids reposting them lexflow's paraphrase (or the citation and link)
            assert s["matched"] and (s.get("quote") or s.get("paraphrase") or s.get("withheld")), (o["scenario"], r["id"])
            assert s["citation"] or s["url"]
            for k in ("fee_source", "deadline_source"):
                if r.get(k):
                    assert r[k]["matched"], (o["scenario"], r["id"], k)


def test_outputs_never_say_you_need_without_the_office(population, personas):
    _, outs = population
    for o in list(outs) + list(personas.values()):
        for r in o["requirements"]:
            assert r["office"]["label"] and r["office"]["label"] != r["office"]["id"]
        for line in R.text(o).splitlines():
            if re.search(r"\bneed\b", line):
                m = re.search(r"\bneed (.+?) from (.+?) \[", line)
                assert m and m.group(2).strip(), line
            if line.lstrip()[:1].isdigit():                # every numbered line names its office
                assert " from " in line or "(office: " in line or re.search(r"Ask first \((.+?)\):", line), line


def test_fees_are_labelled_known_and_the_unknown_are_listed(population, personas):
    _, outs = population
    for o in list(outs) + list(personas.values()):
        f = o["fees"]
        assert f["label"] == "known fees" and f["summary"].startswith("Known fees: $")
        unknown = {u["requirement"] for u in f["unknown"]}
        total = 0.0
        for r in o["requirements"]:
            if r["status"] not in COUNTED or r["fee"]["kind"] != "fee":
                continue
            if r["fee"]["known"]:
                total += r["fee"]["usd"]
            elif r["fee"].get("min_usd") is None:
                assert r["id"] in unknown
        assert abs(total - f["known_required_usd"] - f["known_possible_usd"]) < 0.01
        for u in f["unknown"]:
            assert u["title"] in f["summary"]


def test_albemarle_words_never_leave_the_evidence_store(fam, population):
    """The committed fixture holds a NO_REPRINT quote only as its fingerprint and paraphrase (or the plain words the
    place file itself keeps plain, as the state code's); no output prints such a site's words; the scan finds no
    run of withheld words in the files a commit carries."""
    from lexflow.municipal import quotes as Q
    from lexflow.scenarios.family import resolve
    held = 0
    for t in fam.spec["tables"]:
        for r in t["rules"]:
            for key in ("source", "fee_source", "deadline_source"):
                src = r.get(key)
                if not src or not Q.policy(src.get("url")):
                    continue
                f, where = src["from"].split("#")
                entry = resolve(json.loads((ROOT / f).read_text(encoding="utf-8")), where)
                if src.get("quote"):
                    assert entry.get("quote") == src["quote"] and not entry.get("quote_sha256")
                else:
                    held += 1
                    assert src["quote_sha256"] and src.get("paraphrase") is not None
    assert held >= 20
    _, outs = population
    for o in outs:
        for r in o["requirements"]:
            for k in ("source", "fee_source", "deadline_source"):
                s = r.get(k)
                if s and Q.policy(s.get("url")):
                    assert ("quote" not in s and s.get("withheld")) or s.get("free_words"), (o["scenario"], r["id"])
    files = [ROOT / "fixtures" / "families" / f"{FAMILY}.json", ROOT / "docs" / "design" / "hypotheticals.md",
             Path(__file__)] + sorted((ROOT / "lexflow" / "scenarios").glob("*.py"))
    files = [p for p in files if p.exists()]
    ev = Q.all_evidence()
    assert Q.leaks(files, ev) == []
    shas = Q.held_shas([files[0]])
    assert shas and all(len(s) == 64 for s in shas)


def test_order_respects_every_rule(personas, fam):
    for (p, loc), o in personas.items():
        pos = {s["id"]: s["n"] for s in o["order"]["steps"]}
        assert not o["order"]["cycle"]
        for s in o["order"]["steps"]:
            for a in s["after"]:
                assert pos[a["node"]] < s["n"], (p, loc, a, s["id"])
                assert a["because"], (p, loc, s["id"])
    cafe = personas[("studio_cafe_historic", "staunton")]
    pos = {s["id"]: s["n"] for s in cafe["order"]["steps"]}
    assert pos["stn_co"] < pos["csh_food_permit"] < pos["abc_wine_beer"]
    assert pos["stn_coa"] < pos["stn_building_alteration"]
    assert pos["csh_food_permit"] < pos["stn_bpol_large"]
    hot = personas[("hot_shop_classes", "charlottesville")]
    pos = {s["id"]: s["n"] for s in hot["order"]["steps"]}
    assert pos["cvl_zoning_letter"] < pos["m:lease"] < pos["cvl_building_permit"] < pos["m:construction"] < pos["cvl_co"]
    assert pos["cvl_co"] < pos["cvl_bpol_mid"] < pos["m:opening"]


def test_policy_variant_changes_only_charlottesville_fuel_fired_studios(fam, population):
    tests, _ = population
    for t in tests:
        a, b = R.evaluate(fam, t), R.evaluate(fam, t, "highimpact")
        same = [(r["id"], r["status"]) for r in a["requirements"]] == [(r["id"], r["status"]) for r in b["requirements"]]
        if t["locality"] != "charlottesville" or t["fuel"] == "electric":
            assert same, a["scenario"]
        assert b["scenario"].endswith("-RHI") and b["kind"] == "policy"
    o = R.evaluate(fam, fam.persona_inputs("hot_shop_classes", "charlottesville"), "highimpact")
    assert {"cvl_sup", "cvl_sup_preapp"} <= {r["id"] for r in o["requirements"]}
    o = R.evaluate(fam, fam.persona_inputs("studio_cafe_historic", "charlottesville"), "highimpact")
    assert o["blocked"]


def test_sensitivity_ranks_the_drivers(fam):
    s = SE.for_persona(fam, "hot_shop_classes", "charlottesville")
    dims = [r["dimension"] for r in s["ranking"]]
    assert "locality" not in dims and len(dims) == len(fam.dims) - 1
    assert s["ranking"][0]["score"] >= s["ranking"][-1]["score"]
    row = next(r for r in s["dimensions"] if r["dimension"] == "district")
    assert row["can_block"]
    alc = next(r for r in s["dimensions"] if r["dimension"] == "occupants")
    assert any(not a["possible"] for a in alc["alternatives"]) or all(a["possible"] for a in alc["alternatives"])
    s2 = SE.for_persona(fam, "hot_shop_classes", "charlottesville", hold=())
    assert "locality" in [r["dimension"] for r in s2["ranking"]]
    assert len(SE.top(s)) == 3


# ======================================================================================== intake
SENTENCE = ("I want to open a glass studio with a gas furnace in Staunton, district B-2, with classes of 60 people "
            "and wine at events")


def test_intake_patterns_read_the_plain_facts(fam):
    res = IN.intake(fam, SENTENCE, use_model=False)
    assert res["inputs"]["locality"] == "STN" and res["inputs"]["district"] == "SB2"
    assert res["inputs"]["fuel"] == "NG" and res["inputs"]["occupants"] == 60 and res["inputs"]["alcohol"] == "WR"
    assert all(m["tag"] == "SCN" and m["method"] == "pattern" for m in res["methods"].values())
    assert res["local_only"] and not res["complete"]
    assert {q["dimension"] for q in res["ask"]} >= {"employees", "receipts"}
    inputs, methods = IN.with_defaults(fam, res)
    o = R.evaluate(fam, inputs)
    assert o["scenario"].startswith("STN-SB2-") and methods["employees"]["tag"] == "ASM"



def test_intake_takes_the_model_only_when_sure(fam, tmp_path):
    from lexflow.extract import decide as D

    def answer(state, questions):
        assert "Fact pattern" in D.normalise_state(state)
        out = {}
        for name, q in questions.items():
            if name == "fuel":
                out[name] = {"type": "choice", "choice": "LP", "confidence": 0.93, "probabilities": {"LP": 0.93, "NG": 0.05}}
            elif name == "food":
                out[name] = {"type": "choice", "choice": "FK", "confidence": 0.55, "probabilities": {"FK": 0.55}}
            elif name == "employees":
                out[name] = {"type": "choice", "choice": "E3", "confidence": None, "probabilities": {"E3": 1.0}}
            else:
                out[name] = {"type": "choice", "choice": IN.NOT_SAID, "confidence": 0.9, "probabilities": {}}
        return {"model": "stub", "answers": out}
    dec = D.Decider(answer=answer, cache_dir=tmp_path)
    res = IN.intake(fam, "a lampworking studio", decider=dec, use_patterns=False)
    assert res["inputs"] == {"fuel": "LP"}
    assert res["methods"]["fuel"]["method"] == "decision-model" and res["methods"]["fuel"]["p"] == 0.93
    asked = {q["dimension"]: q for q in res["ask"]}
    assert asked["food"]["best_guess"] == "FK" and asked["food"]["p"] == 0.55       # under the threshold: ask
    assert asked["employees"]["best_guess"] == "E3"                                # no confidence (chat): ask
    qs = IN.questions(fam)
    assert all(IN.NOT_SAID in q["criteria"] and len(q["criteria"]) >= 3 for q in qs.values())


# ======================================================================================== storage
def test_storage_keeps_scenarios_local_and_families_shared(con, fam):
    assert {"families", "personas", "assumptions"} <= set(db.SYNCED)
    assert "scenarios" not in db.SYNCED and "scenario_runs" not in db.SYNCED
    R.save_family(con, fam)
    row = db.one(con, "SELECT * FROM families WHERE id=?", FAMILY)
    assert row["content_hash"] == fam.content_hash() and row["state"] == "va"
    from lexflow.municipal import quotes as Q
    for t in json.loads(row["tables"]):
        for r in t["rules"]:
            if Q.policy(r["source"].get("url")) and not r["source"].get("quote"):
                assert r["source"]["quote_sha256"]
    assert db.scalar(con, "SELECT count(*) FROM personas WHERE family=?", FAMILY) == len(fam.personas)
    assert db.scalar(con, "SELECT count(*) FROM assumptions WHERE family=?", FAMILY) == len(fam.assumptions)
    res = IN.intake(fam, SENTENCE, use_model=False)
    inputs, methods = IN.with_defaults(fam, res)
    o = R.evaluate(fam, inputs)
    rid = R.record(con, fam, o, created_by="intake", local_only=True, method=methods)
    assert rid == R.run_id(o) and rid.startswith(FAMILY + ":")
    s = db.one(con, "SELECT * FROM scenarios WHERE family=? AND id=?", FAMILY, o["scenario"])
    assert s["local_only"] == 1 and s["kind"] == "fact" and SENTENCE not in json.dumps(dict(s))
    ins = json.loads(s["inputs"])
    assert ins["locality"]["tag"] == "SCN" and ins["locality"]["method"] == "pattern" and ins["employees"]["tag"] == "ASM"
    run = db.one(con, "SELECT * FROM scenario_runs WHERE run_id=?", rid)
    assert run["tables_hash"] == fam.content_hash() and run["engine"] == R.ENGINE
    R.record(con, fam, o, created_by="cli")                            # once local, always local
    assert db.scalar(con, "SELECT local_only FROM scenarios WHERE id=?", o["scenario"]) == 1
    from lexflow.store import turso as T
    with pytest.raises(T.SyncTableError):
        T.check_tables("scenarios")


# ======================================================================================== API and coverage
def test_api_families_run_and_sensitivity(con, monkeypatch):
    from fastapi.testclient import TestClient
    from lexflow.api import app as API
    monkeypatch.setattr(config, "JOB_RUNNER", False)
    with TestClient(API.app) as c:
        fams = c.get("/api/hypo/families").json()["families"]
        f = next(x for x in fams if x["id"] == FAMILY)
        assert "glass_q1" in f["serves"] and len(f["dimensions"]) == 12 and f["personas"]
        r = c.get(f"/api/hypo/{FAMILY}/run", params={"persona": "hot_shop_classes", "locality": "staunton"})
        assert r.status_code == 200
        body = r.json()
        assert body["scenario"].startswith("STN-") and body["requirements"] and "You need" in body["text"]
        r2 = c.get(f"/api/hypo/{FAMILY}/run", params={"persona": "hot_shop_classes", "locality": "staunton", "fuel": "propane"})
        assert "stn_lp_gas" in {x["id"] for x in r2.json()["requirements"]}
        r3 = c.get(f"/api/hypo/{FAMILY}/run", params={"scenario": body["scenario"]})
        assert r3.json()["scenario"] == body["scenario"]
        s = c.get(f"/api/hypo/{FAMILY}/sens", params={"persona": "cold_studio", "locality": "albemarle"}).json()
        assert s["ranking"] and s["base"].startswith("ALB-")
        assert c.get("/api/hypo/nope/run").status_code == 404
        assert c.get("/api/hypo/BAD!/run").status_code in (400, 404)
        assert c.get(f"/api/hypo/{FAMILY}/run", params={"fuel": "coal"}).status_code == 400


def test_coverage_counts_a_computed_answer():
    from lexflow.ask import coverage as CV
    q1 = CV.question("glass_q1")
    c = CV.computed_signal(q1, "va", "47210400100000")
    assert c["requirements"] > 5 and c["kinds"]["who"] and c["kinds"]["steps"] and c["kinds"]["fee"]
    assert not c["kinds"]["form"]
    st = CV.computed_signal(q1, "va", "")
    assert st["scope"] == "state" and not st["kinds"]["appeal"]
    assert CV.computed_signal(q1, "dc", "") is None
    assert CV.computed_signal(CV.question("glass_q4"), "va", "") is None
    probe = {"processes": [], "kinds": {k: False for k in CV.KINDS}, "counts": dict(CV.EMPTY_COUNTS)}
    assert CV.verdict(q1, probe, None, None)[0] == "none"
    probe2 = {**probe, "computed": c, "kinds": {**probe["kinds"], **{k: v for k, v in c["kinds"].items() if v}}}
    v, missing = CV.verdict(q1, probe2, None, None)
    assert v == "partial" and missing == ["form"]
