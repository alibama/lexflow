"""lexflow.law.ontology (the section tagger) and lexflow.publish.ontology_map (the mappings)."""
from __future__ import annotations

import json
import os

import pytest

from lexflow.law import ontology as O
from lexflow.publish import ontology_map as OM
from lexflow.publish import schema as S


# --------------------------------------------------------------------------- (a) structure
@pytest.mark.parametrize("path, act_id, want", [
    ("Virginia Code / Title 2.2 / Subtitle II / Part B / Chapter 37 / Section 2.2-3704",
     "STATE_VA_T2.2_SII_PB_C37_S2.2-3704", "title/subtitle/part/chapter/section"),
    ("California Code / Code bpc / Division 1.5 / Chapter 2 / Section 480.5", "STATE_CA_Cbpc_D1.5_C2_S480.5",
     "code/division/chapter/section"),
    ("Illinois Code / Chapter 105 / Act 5 / Section 19b-1.1", "STATE_IL_C105_A5_S19b-1.1", "chapter/act/section"),
    ("LA Code / Code childrens-code / Article 1004.1", "STATE_LA_Cchildrens-code_A1004.1", "code/article"),
    ("Ley sobre Política Pública Ambiental (2004) / Ley sobre Política Pública Ambiental / Art. 15",
     "STATE_PR_AMBIENTAL_ART15", "act/article"),
    ("Código Civil de Puerto Rico (2020) / Libro Sexto: La Sucesión por Causa de Muerte / Art. 1767",
     "STATE_PR_CIVIL_ART1767", "book/article"),
    ("Utah Code / Title 10 / Chapter 10-15 / § 10-15-4", "STATE_UT_T10_S10_15_4", "title/chapter/section"),
    ("MD Code / Article gab / Title 10 / Subtitle 13 / Section 10-1305", "STATE_MD_Agab_T10_S13_S10-1305",
     "article/title/subtitle/section"),
    ("New York Code / Act ABC / Article 11 / Section 160", "STATE_NY_AABC_A11_S160", "act/article/section"),
    ("DC Code / Title 10 / Chapter 12 / § 10-1202.33", "STATE_DC_T10_C12_S10-1202.33", "title/chapter/section"),
    ("North Carolina Code / Chapter 100 / Section 100-16", "STATE_NC_C100_S100-16", "chapter/section"),
    ("", "", "section"),
])
def test_structure_from_path(path, act_id, want):
    assert O.structure(path, act_id) == want


def test_every_structure_token_is_an_akn_hierarchy_element_or_act():
    for level, m in OM.STRUCTURE_MATCH.items():
        assert m["akn"] in OM.AKN_HIERARCHY or m["akn"] == "act", level
    for tok in O.structure("Virginia Code / Title 2.2 / Chapter 37 / Section 2.2-3704",
                           "STATE_VA_T2.2_C37_S2.2-3704").split("/"):
        assert tok in OM.STRUCTURE_MATCH


# --------------------------------------------------------------------------- (c) ELI identifiers
@pytest.mark.parametrize("state, act_id, want", [
    ("va", "STATE_VA_T2.2_SII_PB_C37_S2.2-3704", "https://lexipedia.wikibase.cloud/eli/us-va/code/2.2-3704"),
    ("ca", "STATE_CA_Cgov_D10_C22_S7922.535", "https://lexipedia.wikibase.cloud/eli/us-ca/gov/7922.535"),
    ("ny", "STATE_NY_APBO_A6_S89", "https://lexipedia.wikibase.cloud/eli/us-ny/pbo/89"),
    ("md", "STATE_MD_Agab_T10_S13_S10-1305", "https://lexipedia.wikibase.cloud/eli/us-md/gab/10-1305"),
    ("tx", "STATE_TX_Cag_C122_S122.053", "https://lexipedia.wikibase.cloud/eli/us-tx/ag/122.053"),
    ("la", "STATE_LA_Cchildrens-code_A1004.1", "https://lexipedia.wikibase.cloud/eli/us-la/childrens-code/1004.1"),
    ("il", "STATE_IL_C105_A5_S19b-1.1", "https://lexipedia.wikibase.cloud/eli/us-il/105-5/19b-1.1"),
    ("pr", "STATE_PR_AMBIENTAL_ART15", "https://lexipedia.wikibase.cloud/eli/us-pr/ambiental/15"),
    ("mi", "STATE_MI_C108_AAct-215-of-1895_S108.2", "https://lexipedia.wikibase.cloud/eli/us-mi/code/108.2"),
    ("fl", "STATE_FL_TII_C7_S7.09", "https://lexipedia.wikibase.cloud/eli/us-fl/code/7.09"),
])
def test_eli_uri(state, act_id, want):
    assert OM.eli_uri(state, act_id) == want
    assert OM.eli_uri(state, act_id, "2026-07-01") == want + "/en@2026-07-01"


def test_eli_uri_is_stable_and_distinct_across_codes():
    a = OM.eli_uri("ca", "STATE_CA_Cgov_D10_C22_S480")
    b = OM.eli_uri("ca", "STATE_CA_Cbpc_D1.5_C2_S480")
    assert a != b and a.endswith("/gov/480") and b.endswith("/bpc/480")
    assert OM.eli_uri("va", "") is None
    assert OM.eli_unit_uri("va", "STATE_VA_T2.2_SII_PB_C37") == \
        "https://lexipedia.wikibase.cloud/eli/us-va/code/unit/t2.2-sii-pb-c37"


# --------------------------------------------------------------------------- (b) norm types: rules
def test_rules_find_each_norm_type():
    cases = {
        "definition": 'As used in this chapter, "public body" means any legislative body.',
        "obligation": "The custodian shall provide the records within five working days.",
        "permission": "A requester may inspect the records during office hours.",
        "prohibition": "No public body shall charge a fee for the first hour of search time.",
        "power": "The board is authorized to adopt rules to carry out this section.",
        "penalty": "A violation of this section is a Class 1 misdemeanor punishable by a fine of not more than $500.",
        "procedure": "The appeal shall be filed within 30 days of the decision and the clerk shall give notice.",
    }
    for want, text in cases.items():
        got = O.rule_types(text)
        assert got[want] == 1.0, (want, got)
    assert all(v == 0.0 for v in O.rule_types("The short title of this act is the Records Act.").values())


def test_rules_do_not_read_shall_mean_or_shall_not_as_an_obligation():
    got = O.rule_types('"Record" shall mean any writing. A custodian shall not withhold a record.')
    assert got["obligation"] == 0.0 and got["definition"] == 1.0 and got["prohibition"] == 1.0


# --------------------------------------------------------------------------- (b) norm types: stubbed model
def _stub(probs: dict[str, float], model="stub"):
    from lexflow.extract import decide as D

    def answer(state, questions):
        return {"model": model, "answers": {k: D.parse_answer("noul", {"noul": probs.get(k, 0.1)})
                                           for k in questions}, "usage": {}, "ms": 2.0}
    return D.Decider(cache=False, backend_info={"kind": "decision", "model": model, "models": []}, answer=answer)


ROW = {"state": "va", "ref": "2.2-3704", "citation": "Va. Code Ann. § 2.2-3704", "head": "Public records to be open",
       "path": "Virginia Code / Title 2.2 / Subtitle II / Part B / Chapter 37 / Section 2.2-3704",
       "act_id": "STATE_VA_T2.2_SII_PB_C37_S2.2-3704"}
TEXT = "A. Except as otherwise specifically provided by law, all public records shall be open to citizens."


def test_model_state_is_head_plus_first_1500_characters():
    st = O.model_state(ROW, "x " * 2000)
    assert st["Section"].startswith("Va. Code Ann. § 2.2-3704 Public records")
    assert len(st["Text"]) == O.HEAD_CHARS


def test_tag_row_merges_rules_and_model_over_threshold():
    d = _stub({"power": 0.9, "penalty": 0.3, "obligation": 0.95})
    row = O.tag_row(ROW, TEXT, d)
    assert row["structure"] == "title/subtitle/part/chapter/section"
    assert row["method"] == "rules+decision" and row["model"] == "stub"
    assert row["norm_types"] == ["obligation", "power"]       # obligation by rule and model; power by model only
    assert row["confidence"]["rules"]["obligation"] == 1.0 and row["confidence"]["model"]["power"] == 0.9
    assert row["confidence"]["eli"] == "https://lexipedia.wikibase.cloud/eli/us-va/code/2.2-3704"
    rules_only = O.tag_row(ROW, TEXT)
    assert rules_only["method"] == "rules" and rules_only["model"] is None
    assert rules_only["norm_types"] == ["obligation"] and rules_only["confidence"]["model"] is None


def test_tag_row_survives_a_failing_model():
    from lexflow.extract import decide as D

    def boom(state, questions):
        raise D.DecisionError("down")
    d = D.Decider(cache=False, backend_info={"kind": "decision", "model": "x", "models": []}, answer=boom)
    row = O.tag_row(ROW, TEXT, d)
    assert row["model"] == "error" and row["norm_types"] == ["obligation"]
    assert all(v is None for v in row["confidence"]["model"].values())


def test_merge_threshold_per_type():
    rules = {k: 0.0 for k in O.NORM_TYPES}
    model = {"definition": 0.6, "penalty": 0.6}
    assert O.merge(rules, model, {"definition": 0.5, "penalty": 0.7}) == ["definition"]
    assert O.merge(rules, None) == []


# --------------------------------------------------------------------------- the table
def test_table_round_trip_and_resume(con, tmp_path, monkeypatch):
    O.ensure_table(con)
    assert "section_tags" in [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    rows = [O.tag_row(ROW, TEXT), O.tag_row({**ROW, "ref": "2.2-3705"}, "The requester may inspect the records.")]
    assert O.upsert(con, rows) == 2
    con.commit()
    got = {r["ref"]: r for r in con.execute("SELECT * FROM section_tags ORDER BY ref")}
    assert set(got) == {"2.2-3704", "2.2-3705"}
    assert json.loads(got["2.2-3705"]["norm_types"]) == ["permission"]
    assert got["2.2-3704"]["updated_at"] and got["2.2-3704"]["origin"] and got["2.2-3704"]["method"] == "rules"
    assert O.status(con, ["va"]) == {"va": {"rules": 2}}
    # the same key again replaces the row (an upsert, not a duplicate)
    O.upsert(con, [O.tag_row(ROW, TEXT, _stub({"penalty": 0.99}))])
    con.commit()
    r = con.execute("SELECT method, norm_types FROM section_tags WHERE ref='2.2-3704'").fetchone()
    assert r[0] == "rules+decision" and json.loads(r[1]) == ["obligation", "penalty"]
    assert con.execute("SELECT count(*) FROM section_tags").fetchone()[0] == 2


def test_run_state_resumes_and_keeps_the_budget(con, monkeypatch):
    rows = [{"id": i, "ref": f"1-{i}", "citation": f"X § 1-{i}", "title": "t", "head": "t", "state": "xx",
             "path": f"X Code / Title 1 / Section 1-{i}", "act_id": f"STATE_XX_T1_S1-{i}",
             "effective_from": None, "text": "The clerk shall file the notice within 10 days."} for i in range(5)]
    monkeypatch.setattr(O, "_index_rows", lambda state, corpus="statutes": iter([dict(r) for r in rows]))
    monkeypatch.setattr(O, "section_count", lambda state, corpus="statutes": len(rows))
    log = []
    out = O.run_state(con, "xx", log=log.append)
    assert out["tagged"] == 5 and out["model_calls"] == 0 and out["method"] == "rules"
    out = O.run_state(con, "xx", log=log.append)                           # resume: nothing to do
    assert out["tagged"] == 0 and out["skipped"] == 5
    d = _stub({"procedure": 0.9})
    out = O.run_state(con, "xx", decider=d, budget=2, log=log.append)      # a new method retags; 2 model calls
    assert out["tagged"] == 5 and out["model_calls"] == 2 and out["method"] == "rules+decision"
    by = {r[0]: r[1] for r in con.execute("SELECT method, count(*) FROM section_tags GROUP BY method")}
    assert by == {"rules": 3, "rules+decision": 2}
    out = O.run_state(con, "xx", decider=d, budget=10, log=log.append)     # the next run finishes the rest
    assert out["tagged"] == 3 and out["skipped"] == 2 and out["model_calls"] == 3
    assert any("done" in m for m in log)


def test_section_tags_is_local_not_synced():
    from lexflow.store import db
    assert "section_tags" in db.LOCAL_KEYS and "section_tags" not in db.SYNCED
    assert "section_tags" in db.SCHEMA


def test_step_is_registered():
    from lexflow.pipeline import jobs, steps
    s = steps.STEPS["ontology"]
    assert s.needs == ["index"] and s.run is steps.run_ontology and "states" in s.params
    assert "ontology" in jobs.EXCLUSIVE


# --------------------------------------------------------------------------- the mappings
def test_mapping_keys_are_schema_labels_and_slugs():
    labels = set(S.ALL_PROPERTY_LABELS)
    assert set(OM.PROPERTY_EQUIV) <= labels, set(OM.PROPERTY_EQUIV) - labels
    assert set(OM.PROPERTY_RELATED) <= labels, set(OM.PROPERTY_RELATED) - labels
    slugs = set(S.CLASS_BY_SLUG)
    assert set(OM.CLASS_MATCH) <= slugs, set(OM.CLASS_MATCH) - slugs
    assert set(OM.CLASS_CLOSE) <= slugs, set(OM.CLASS_CLOSE) - slugs
    assert set(OM.NORM_TYPE_MATCH) == set(OM.NORM_TYPES)
    levels = {v.slug for v in S.VOCAB["unit-level"]}
    assert levels <= set(OM.STRUCTURE_MATCH), levels - set(OM.STRUCTURE_MATCH)


def test_every_iri_is_absolute_and_in_a_known_namespace():
    known = (OM.ELI, OM.SCHEMA, OM.PROV, OM.SKOS, OM.ORG, OM.DCT, OM.ONTOLEX, OM.RDF, OM.RDFS, OM.OWL, OM.FIBO_LAW,
             OM.LKIF, OM.AKN_XSD)
    for iri in OM.all_iris():
        assert iri.startswith(known), iri
        assert " " not in iri
    # the adopted ontologies each contribute something
    assert any(i.startswith(OM.ELI) for i in OM.all_iris())
    assert any(i.startswith(OM.LKIF) for i in OM.all_iris())
    assert any(i.startswith(OM.SCHEMA) for i in OM.all_iris())
    assert any(i.startswith(OM.PROV) for i in OM.all_iris())


def test_document_of_and_found():
    assert OM.document_of(OM.lkif("norm", "Obligation")) == (OM.LKIF_RAW + "norm.owl", "Obligation")
    assert OM.document_of(OM.schema("Legislation")) == (OM.schema("Legislation"), None)
    assert OM.document_of(OM.prov("value")) == (OM.PROV[:-1], "value")
    assert OM._found("Obligation", '<owl:Class rdf:about="http://x/norm.owl#Obligation">')
    assert OM._found("hcontainer", '<xsd:element name="hcontainer" type="hierarchy"/>')
    assert not OM._found("Obligation", "Obligations are not it")


def test_resolve_all_with_a_stub_and_cache(tmp_path):
    def fetch(url):
        if url.endswith("norm.owl"):
            return 200, 'rdf:about="http://www.estrellaproject.org/lkif-core/norm.owl#Obligation"'
        if url.startswith("https://schema.org/"):
            return 200, "<html>"
        return 404, ""
    iris = [OM.lkif("norm", "Obligation"), OM.lkif("norm", "Nope"), OM.schema("Legislation"), OM.prov("value")]
    out = OM.resolve_all(iris, cache=tmp_path / "c.json", pace=0, fetch_fn=fetch)
    assert out[iris[0]]["ok"] and out[iris[0]]["found"] is True
    assert not out[iris[1]]["ok"] and out[iris[1]]["found"] is False
    assert out[iris[2]]["ok"] and out[iris[2]]["found"] is None
    assert not out[iris[3]]["ok"] and out[iris[3]]["status"] == 404
    calls = []
    again = OM.resolve_all(iris, cache=tmp_path / "c.json", pace=0, fetch_fn=lambda u: calls.append(u) or (500, ""))
    assert calls == [] and again[iris[0]]["ok"]                            # served from the cache


@pytest.mark.skipif(os.environ.get("LEXFLOW_NET") != "1", reason="network; set LEXFLOW_NET=1")
def test_every_iri_resolves_live(tmp_path):
    from lexflow import config
    out = OM.resolve_all(cache=tmp_path / "iris.json")
    bad = [r["iri"] for r in out.values() if not r["ok"]]
    assert not bad, bad
    assert len(out) == len(OM.all_iris())
