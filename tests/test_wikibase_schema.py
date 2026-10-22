"""The Wikibase schema contract (docs/design/wikibase-schema.md): the property table, the key forms and a
neutral graph build on a seeded database."""
import json
import re
from pathlib import Path

import pytest

from lexflow.ask import coverage as CV
from lexflow.municipal import quotes as QT
from lexflow.publish import graph, schema as SC
from lexflow.store import db
from lexflow import privacy

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "design" / "wikibase-schema.md"


# --------------------------------------------------------------------------- the property table
def _doc_rows():
    rows = []
    for line in DOC.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|", line)
        if m:
            rows.append((int(m.group(1)), m.group(2), m.group(3)))
    return rows


def test_property_table_matches_the_doc_numbering_and_datatypes():
    doc = _doc_rows()
    assert doc, "the doc's section 3 table was not found"
    by_number = {}
    for p in SC.PROPERTIES:
        by_number.setdefault(p.number, []).append(p)
    for number, label, datatype in doc:
        props = by_number.get(number)
        assert props, f"doc row {number} ({label}) is missing from schema.PROPERTIES"
        if "×4" in datatype:                                  # the four SKOS matches share one row
            assert sorted(p.label for p in props) == sorted(label.replace(" / ", "/").split("/"))
            assert all(p.datatype == "url" for p in props)
        else:
            assert [p.label for p in props] == [label], f"row {number}: {label!r}"
            assert props[0].datatype == datatype.strip(), f"row {number}: {datatype!r}"
    assert {n for n, _, _ in doc} == set(by_number), "schema has numbers the doc lacks or the other way round"
    assert len(SC.PROPERTIES) == 82 and len({p.label for p in SC.PROPERTIES}) == 82
    assert all(p.datatype in ("item", "string", "url", "time", "quantity", "monolingualtext", "external-id")
               for p in SC.PROPERTIES)
    assert not set(SC.EXISTING) & {p.label for p in SC.PROPERTIES}


def test_existing_properties_and_classes():
    # the wiki holds 25 properties; P1-P4 are the sandbox's, the 21 from P5 are reused
    assert len(SC.EXISTING) == 21 and set(SC.EXISTING.values()) == {f"P{i}" for i in range(5, 26)}
    assert SC.unit_tokens("STATE_MN_P13_13C_C13_S13.03") == ["P13_13C", "C13", "S13.03"]
    assert SC.EXISTING["legal identifier"] == "P25" and SC.EXISTING["instance of"] == "P5"
    existing = {c.qid: c.label for c in SC.CLASSES if c.qid}
    assert existing["Q7"] == "legal process" and existing["Q10"] == "statute or legal provision"
    assert existing["Q23"] == "legal role" and len(existing) == 17
    assert SC.class_key("legal-process") == "legal process"                 # referred to by label
    assert SC.class_key("government") == "lexflow:class:government"         # created by key
    for set_, entries in SC.VOCAB.items():
        assert set_ in SC.CLASS_BY_SLUG, set_
        assert len({v.slug for v in entries}) == len(entries)
    assert [v.slug for v in SC.VOCAB["reference-type"]] == [
        "definition", "override", "exception", "penalty", "prerequisite_process", "authority", "procedure",
        "condition", "scope", "other"]
    from lexflow.law import xref
    assert tuple(v.slug for v in SC.VOCAB["reference-type"]) == xref.ROLES


# --------------------------------------------------------------------------- keys
def test_keys_follow_the_doc_and_are_deterministic():
    assert SC.key_for("unit", "va", "STATE_VA_T2.2_SII_PB_C37") == "lexflow:unit:va:t2.2-sii-pb-c37"
    assert SC.key_for("unit", "va", "STATE_VA_T2.2") == "lexflow:unit:va:t2.2"
    assert SC.key_for("code", "va") == "lexflow:code:va" and SC.key_for("code", "va", "vac") == "lexflow:code:va:vac"
    assert SC.key_for("statute", "va", "2.2-3704") == "lexflow:statute:va:2.2-3704"
    assert SC.key_for("gov", "47210400100000") == "lexflow:gov:47210400100000"
    assert SC.key_for("agency", "va", "Virginia State Corporation Commission") == \
        "lexflow:agency:va:state_corporation_commission"
    assert SC.key_for("agency", "va", "state_corporation_commission") == \
        "lexflow:agency:va:state_corporation_commission"
    assert SC.key_for("office-type", "fl", "Clerk of Circuit Court") == "lexflow:office-type:fl:clerk_of_circuit_court"
    assert SC.key_for("position", "dc", "Mayor") == "lexflow:position:dc:mayor"
    assert SC.key_for("position-type", "va", "FOIA officer") == "lexflow:position-type:va:foia_officer"
    assert SC.key_for("role", "va", "records", "public_body") == "lexflow:role:va:records:public_body"
    assert SC.key_for("process", "va.records") == "lexflow:process:va.records"
    assert SC.key_for("process", "47210400100000", "parking_ticket") == "lexflow:process:47210400100000:parking_ticket"
    assert SC.key_for("step", "va.records", "respond") == "lexflow:step:va.records:respond"
    assert SC.key_for("decision", "va.records", "response_type") == "lexflow:decision:va.records:response_type"
    assert SC.key_for("outcome", "va.records", "deemed_denied") == "lexflow:outcome:va.records:deemed_denied"
    assert SC.key_for("form", "47210400100000", "parking_ticket", "f1") == \
        "lexflow:form:47210400100000:parking_ticket:f1"
    assert SC.key_for("vocab", "trigger", "deemed_denied") == "lexflow:vocab:trigger:deemed_denied"
    assert SC.key_for("class", "government") == "lexflow:class:government"
    assert SC.key_for("power", "extend time") == "lexflow:power:extend-time"
    assert SC.key_for("jurisdiction", "VA") == "lexflow:jurisdiction:va"
    assert SC.key_for("case", "123") == "courtlistener:cluster:123"
    assert SC.key_for("private-party") == "lexflow:private-party"
    with pytest.raises(ValueError):
        SC.key_for("nonsense", "x")
    # rung keys: the section slug from the act_id, the subtype from the closed code list
    assert SC.section_slug("Cal. GOV § 11523", "STATE_CA_Cgov_T2_D3_P1_C5_S11523") == "gov-11523"
    assert SC.section_slug("Cal. BPC § 485(b)", "STATE_CA_Cbpc_D2_C1_A4_S485") == "bpc-485-b"
    assert SC.section_slug("N.Y. PBO Law § 89(4)(a)", "STATE_NY_APBO_A6_S89") == "pbo-89-4-a"
    assert SC.section_slug("Fla. Stat. § 605.0210(7)", "STATE_FL_TXXXVI_C605_S605.0210") == "605.0210-7"
    assert SC.section_slug("Va. Code Ann. § 13.1-1004(E)", "STATE_VA_T13.1_C12_A1_S13.1-1004") == "13.1-1004-e"
    assert SC.section_slug("5 ILCS 140/9.5(a)", "STATE_IL_C5_A140_S9.5") == "140-9.5-a"
    assert SC.section_slug("Va. Code Ann. § 2.2-3704(B)(3)") == "2.2-3704-b-3"        # no act_id: the citation
    assert SC.subtype_code("writ of mandate") == "writ-of-mandate"
    assert SC.subtype_code("corrected refiling") == "corrected-refiling"
    assert SC.subtype_code("something the fixture never says") is None
    assert SC.key_for("rung", "ca", "license_conviction", SC.section_slug("Cal. GOV § 11523", "STATE_CA_Cgov_T2_D3_P1_C5_S11523"),
                      SC.subtype_code("writ of mandate")) == "lexflow:rung:ca:license_conviction:gov-11523:writ-of-mandate"
    ladders = json.loads((ROOT / "fixtures" / "authority" / "ladders.json").read_text(encoding="utf-8"))
    missing = {r["subtype"] for l in ladders["ladders"] for r in l["rungs"] if not SC.subtype_code(r["subtype"])}
    assert not missing, f"subtypes without a code: {sorted(missing)[:5]}"
    assert SC.strip_pinpoint("Md. Code, General Provisions § 4-203(d)(2)") == ("Md. Code, General Provisions § 4-203", "(d)(2)")
    # the same input always gives the same key, and a slug is idempotent
    for _ in range(3):
        assert SC.slug("The Virginia Department of Taxation (Tax Commissioner)") == "department_of_taxation"
    assert SC.slug(SC.slug("Florida Department of State, Division of Corporations")) == \
        "department_of_state_division_of_corporations"
    assert len(SC.slug("a " + "verylongword " * 10)) <= SC.SLUG_MAX


def test_sort_key_orders_the_code():
    k = SC.sort_key
    assert k("STATE_VA_T2.2_SII_PB_C37_S2.2-3704") == "00002.00002-00002-b-00037-00002.00002-03704"
    assert k("STATE_VA_T2.2_SII_PB_C37_S2.2-3704") < k("STATE_VA_T2.2_SII_PB_C37_S2.2-3704.1") < \
        k("STATE_VA_T2.2_SII_PB_C37_S2.2-3705") < k("STATE_VA_T13.1_C12_A1_S13.1-1004")
    assert k("STATE_CA_Cgov_T1_S2000") < k("STATE_CA_Cgov_T1_S12345")              # numeric, not lexical
    assert k("STATE_FL_TIX_C101_S101.015") < k("STATE_FL_TX_C102_S102.001")        # roman numerals
    assert k("STATE_VA_T2.2_SII_PB_C37") == k("STATE_VA_T2.2_SII_PB_C37_S2.2-3704").rsplit("-", 2)[0]
    assert SC.unit_prefix("STATE_VA_T2.2_SII_PB_C37_S2.2-3704", 2) == "STATE_VA_T2.2_SII"
    assert SC.code_token("STATE_VA_T13.1_C12_A1_S13.1-1004") is None               # an article is not an act


# --------------------------------------------------------------------------- a build on a seeded database
_SEC = {
    "2.2-3704": dict(id=1, ref="2.2-3704", citation="Va. Code Ann. § 2.2-3704", section_number="2.2-3704",
                     original_title="Public records to be open to inspection; procedure for requesting records",
                     title="", path="Virginia Code / Title 2.2 / Subtitle II / Part B / Chapter 37 / Section 2.2-3704",
                     act_id="STATE_VA_T2.2_SII_PB_C37_S2.2-3704", url="https://law.lis.virginia.gov/vacode/2.2-3704/",
                     effective_from=None, effective_until=None),
    "2.2-3704.2": dict(id=2, ref="2.2-3704.2", citation="Va. Code Ann. § 2.2-3704.2", section_number="2.2-3704.2",
                       original_title="Public bodies to designate FOIA officer", title="",
                       path="Virginia Code / Title 2.2 / Subtitle II / Part B / Chapter 37 / Section 2.2-3704.2",
                       act_id="STATE_VA_T2.2_SII_PB_C37_S2.2-3704.2", url="https://law.lis.virginia.gov/vacode/2.2-3704.2/",
                       effective_from=None, effective_until=None),
    "2.2-3713": dict(id=3, ref="2.2-3713", citation="Va. Code Ann. § 2.2-3713", section_number="2.2-3713",
                     original_title="Proceedings for enforcement of chapter", title="",
                     path="Virginia Code / Title 2.2 / Subtitle II / Part B / Chapter 37 / Section 2.2-3713",
                     act_id="STATE_VA_T2.2_SII_PB_C37_S2.2-3713", url="https://law.lis.virginia.gov/vacode/2.2-3713/",
                     effective_from="2026-07-01", effective_until=None),
    "30-179": dict(id=4, ref="30-179", citation="Va. Code Ann. § 30-179", section_number="30-179",
                   original_title="Powers and duties of the Council", title="",
                   path="Virginia Code / Title 30 / Chapter 21 / Section 30-179",
                   act_id="STATE_VA_T30_C21_S30-179", url="https://law.lis.virginia.gov/vacode/30-179/",
                   effective_from=None, effective_until=None),
}
NO_REPRINT_WORDS = "Requests taking longer than 30 minutes may be subject to a charge"
PERSONAL = "jane.doe@example.gov"


def _fake_row(self, state, ref):
    number = ref.split("§")[-1].strip()
    return dict(_SEC[number]) if state == "va" and number in _SEC else None


@pytest.fixture()
def seeded(con, monkeypatch):
    monkeypatch.setattr(graph.Build, "row", _fake_row)
    model = json.loads((ROOT / "curated" / "va" / "records.json").read_text(encoding="utf-8"))
    db.upsert(con, "process_models", [{
        "model_id": "va.records", "state": "va", "question": "records", "title": model["facts"]["process_name"],
        "tier": "reviewed", "stages": json.dumps({"validated": "2026-10-11T09:01:04Z"}),
        "facts": json.dumps(model["facts"]), "metrics": json.dumps({"sections": ["2.2-3704"]}),
        "citation": "Va. Code Ann. § 2.2-3704", "source_url": "https://law.lis.virginia.gov/vacode/2.2-3704/"}])
    db.upsert(con, "process_models", [{
        "model_id": "wy.records", "state": "wy", "question": "records", "title": "Draft", "tier": "single",
        "stages": "{}", "facts": json.dumps({"actors": [{"id": "custodian", "name": "Custodian", "kind": "office"}],
                                            "steps": [{"id": "s1", "action": "Respond", "actor": "custodian",
                                                       "modality": "obligation", "kind": "decision",
                                                       "deadline": {"amount": 3, "unit": "days"},
                                                       "source": {"section": "1", "quote": "x"}}]}),
        "metrics": "{}"}])
    gid = "47210400100000"
    db.upsert(con, "governments", [{"gov_id": gid, "state": "va", "name": "City of Charlottesville",
                                    "kind": "municipality", "website": "http://www.charlottesville.org/",
                                    "wikidata": "Q123766"}])
    db.upsert(con, "local_answers", [{"gov_id": gid, "state": "va", "question": "records"}])
    db.upsert(con, "contacts", [
        {"gov_id": gid, "state": "va", "question": "general", "kind": "postal",
         "value": "P.O. Box 911, Charlottesville, VA 22902", "label": "Mayor", "source": "census-gus-2022"},
        {"gov_id": gid, "state": "va", "question": "general", "kind": "email", "value": "foia@charlottesville.gov",
         "label": "Records Division", "source": "site-scan"},
        {"gov_id": gid, "state": "va", "question": "public_records_request", "kind": "email",
         "value": "foia@charlottesville.gov", "label": "FOIA Office", "source": "local-research"},
        {"gov_id": gid, "state": "va", "question": "public_records_request", "kind": "email", "value": PERSONAL,
         "label": "Jane Doe, FOIA Officer", "source": "local-research"},
        {"gov_id": gid, "state": "va", "question": "public_records_request", "kind": "phone",
         "value": "434-555-0100", "label": "Clerk's Office main line", "source": "local-research"},
        {"gov_id": gid, "state": "va", "question": "public_records_request", "kind": "phone",
         "value": "434-555-0199", "label": "Jane Doe direct", "source": "local-research"},
        {"gov_id": gid, "state": "va", "question": "public_records_request", "kind": "office",
         "value": "City Hall, 605 E Main Street, Room A120, Charlottesville, VA 22902 Attn: Jane Doe",
         "label": "FOIA Office", "source": "local-research"},
        {"gov_id": gid, "state": "va", "question": "public_records_request", "kind": "page",
         "value": "https://www.charlottesville.gov/foia", "label": "FOIA page", "source": "local-research"},
    ])
    spec = {
        "place": "va:charlottesville", "gov_id": gid, "process": "public_records_request",
        "title": "Request public records from the City", "question": "How do I request City records?",
        "category": "records", "kind": "process", "audience": ["residents"], "office": "FOIA Office",
        "summary": "Ask the FOIA Officer.", "verified": True,
        "checks": {"verified_by": "Claude (lexflow verifier)", "date": "2026-10-10"},
        "sources": [{"url": "https://www.charlottesville.gov/foia", "title": "FOIA", "retrieved": "2026-10-10"}],
        "legal_basis": [{"level": "state", "citation": "Va. Code § 2.2-3704(B)",
                         "url": "https://law.lis.virginia.gov/vacode/2.2-3704/",
                         "quote": "promptly, but in all cases within five working days", "role": "authority"}],
        "steps": [
            {"id": "s1", "step": "Ask for records in writing", "who": "You (the requester)",
             "how": "Use the form.", "deadline": None, "fee": None, "form": "f1",
             "url": "https://www.charlottesville.gov/foia", "quote": "Submit your request online",
             "source": "https://www.charlottesville.gov/foia"},
            {"id": "s2", "step": "The City answers", "who": "FOIA Officer",
             "how": "The City answers.", "deadline": "within five working days of receiving a request",
             "fee": "$20 for the first hour; actual cost after", "form": None,
             "url": "https://www.albemarle.org/foia", "quote": NO_REPRINT_WORDS,
             "source": "https://www.albemarle.org/foia"},
        ],
        "forms": [{"id": "f1", "title": "Online FOIA request form", "number": "FOIA-1",
                   "url": "https://www.charlottesville.gov/foia/form", "official": True, "fillable": True}],
        "fees": [{"item": "Copies", "amount": "$0.10 per page", "basis": "https://www.charlottesville.gov/foia",
                  "quote": "ten cents per page"}],
        "contacts": [], "escalation": [
            {"trigger": "The City misses the deadline", "next": "Petition the general district court",
             "type": "judicial review", "deadline": None, "basis": "Va. Code § 2.2-3713(A)",
             "quote": "Any person denied the rights and privileges conferred by this chapter may proceed"}],
    }
    db.upsert(con, "place_processes", [{"gov_id": gid, "state": "va", "process": "public_records_request",
                                        "title": spec["title"], "question": spec["question"], "category": "records",
                                        "kind": "process", "office": "FOIA Office", "verified": 1, "spec": spec}])
    db.upsert(con, "case_law", [{"state": "va", "section": "2.2-3704", "question": "records", "cluster_id": "77",
                                 "case_name": "Doe v. City", "court": "Court of Appeals of Virginia",
                                 "court_id": "vactapp", "date_filed": "2025-04-29", "cite_count": 1,
                                 "url": "https://www.courtlistener.com/opinion/77/doe-v-city/"}])
    con.execute("INSERT INTO wikibase_items(key, qid) VALUES ('lexflow:statute:va:2.2-3704', 'Q500')")
    con.execute("INSERT INTO wikibase_items(key, qid) VALUES ('lexflow:process:va.records', 'Q501')")
    con.commit()
    return con


def _values(items):
    for it in items:
        for c in it.claims:
            yield it, c, c.value
            for _, v in c.qualifiers:
                yield it, c, v
            for ref in c.references:
                for _, v in ref:
                    yield it, c, v


def test_build_yields_the_item_kinds_and_a_grounded_deadline(seeded):
    logs = []
    items = graph.build(seeded, states=["va", "wy"], log=logs.append)
    by = {it.key: it for it in items}
    kinds = graph.by_kind(items)
    for kind in ("class", "vocab", "jurisdiction", "code", "unit", "statute", "process", "step", "decision", "outcome",
                 "role", "rung", "gov", "agency", "form", "cluster", "private-party"):
        assert kind in kinds, kind
    assert by["lexflow:statute:va:2.2-3704"].exists and by["lexflow:process:va.records"].exists
    assert not by["lexflow:statute:va:2.2-3713"].exists
    # law as a hierarchy
    sec = by["lexflow:statute:va:2.2-3704"]
    props = {c.prop: c for c in sec.claims}
    assert props["part of"].value.value == "lexflow:unit:va:t2.2-sii-pb-c37"
    assert props["unit level"].value.value == "lexflow:vocab:unit-level:section"
    assert props["heading text"].value.kind == "monolingual" and props["sort key"].value.value.startswith("00002")
    assert props["act identifier"].value.value == "STATE_VA_T2.2_SII_PB_C37_S2.2-3704"
    assert by["lexflow:unit:va:t2.2-sii-pb-c37"].claims[0].prop == "part of" or any(
        c.prop == "part of" and c.value.value == "lexflow:unit:va:t2.2-sii-pb" for c in by["lexflow:unit:va:t2.2-sii-pb-c37"].claims)
    assert any(c.prop == "part of" and c.value.value == "lexflow:code:va" for c in by["lexflow:unit:va:t2.2"].claims)
    assert by["lexflow:code:va"].cls == "lexflow:class:legal-code" and by["lexflow:code:va"].label == "Virginia Code"
    assert any(c.prop == "follows" and c.value.value == "lexflow:statute:va:2.2-3704" for c in by["lexflow:statute:va:2.2-3704.2"].claims)
    assert any(c.prop == "effective date" and c.value.value == "2026-07-01" for c in by["lexflow:statute:va:2.2-3713"].claims)
    # the grounded deadline of section 4.6
    step = by["lexflow:step:va.records:respond"]
    limit = next(c for c in step.claims if c.prop == "time limit")
    assert limit.value.kind == "quantity" and limit.value.value == "5"
    quals = dict(limit.qualifiers)
    assert quals["time unit"].value == "lexflow:vocab:time-unit:working-days"         # the law's own word
    assert quals["counted from"].value == "receiving a request"
    assert quals["on expiry"].value == "lexflow:outcome:va.records:deemed_denied"
    ref = dict(limit.references[0])
    assert ref["source section"].value == "lexflow:statute:va:2.2-3704" and ref["pinpoint"].value == "B"
    assert ref["quoted text"].value == "promptly, but in all cases within five working days of receiving a request"
    assert ref["determination method"].value == "lexflow:vocab:determination-method:curated"
    proc = by["lexflow:process:va.records"]
    assert any(c.prop == "time limit" and c.value.value == "5" for c in proc.claims)
    assert any(c.prop == "review status" and c.value.value.endswith(":reviewed") for c in proc.claims)
    assert any(c.prop == "question asked" and c.value.kind == "monolingual" for c in proc.claims)
    assert any(c.prop == "has part" and c.value.value == "lexflow:decision:va.records:response_type" for c in proc.claims)
    assert any(c.prop == "escalates to" and c.value.value.startswith("lexflow:rung:va:records:2.2-3704-b-3:")
               for c in step.claims)
    rung = by["lexflow:rung:va:records:2.2-3704-b-3:custodian-redirect"]
    assert any(c.prop == "escalation type" and c.value.value.endswith(":referral") for c in rung.claims)
    assert any(c.prop == "defers to" and c.value.value == "lexflow:office-type:va:public_body" for c in rung.claims)
    assert any(c.prop == "played by" and c.value.value == "lexflow:private-party"
               for c in by["lexflow:role:va:records:requester"].claims)
    # the draft gets the process, steps and roles marked draft, no decisions, no escalation
    assert any(c.prop == "review status" and c.value.value.endswith(":draft") for c in by["lexflow:process:wy.records"].claims)
    assert "lexflow:step:wy.records:s1" in by and not any(k.startswith("lexflow:rung:wy:") for k in by)
    assert not any(c.prop == "time limit" for c in by["lexflow:step:wy.records:s1"].claims)
    # the local process
    local = by["lexflow:process:47210400100000:public_records_request"]
    lp = {c.prop for c in local.claims}
    assert {"applies to jurisdiction", "question asked", "topic", "audience", "review status", "checked on",
            "references", "form used", "fee", "escalates to", "contact page URL", "email address", "phone number",
            "postal address", "has part"} <= lp
    assert any(c.prop == "review status" and c.value.value.endswith(":agreed") for c in local.claims)
    s2 = by["lexflow:step:47210400100000:public_records_request:s2"]
    lim = next(c for c in s2.claims if c.prop == "time limit")
    assert lim.value.value == "5" and dict(lim.qualifiers)["time unit"].value.endswith(":working-days")
    fee = next(c for c in s2.claims if c.prop == "fee")
    assert fee.value.value == "20" and fee.value.unit == SC.USD
    # s2's source is albemarle.org (NO_REPRINT): the amount is written, the fee and deadline texts are not
    assert "fee basis" not in dict(fee.qualifiers) and "counted from" not in dict(lim.qualifiers)
    pfee = next(c for c in local.claims if c.prop == "fee")
    assert pfee.value.value == "0.10" and dict(pfee.qualifiers)["fee basis"].value == "Copies — $0.10 per page"
    assert any(c.prop == "bearer" and c.value.value.endswith(":office") for c in s2.claims)
    assert any(c.prop == "played by" and c.value.value == "lexflow:agency:47210400100000:foia_office"
               for c in by["lexflow:role:47210400100000:public_records_request:office"].claims)
    assert any(c.prop == "form number" and c.value.value == "FOIA-1" for c in by["lexflow:form:47210400100000:public_records_request:f1"].claims)
    # case law
    case = by["courtlistener:cluster:77"]
    # court_keys.json: CourtListener's vactapp is the ladder's Court of Appeals of Virginia, one item
    assert any(c.prop == "court" and c.value.value == "lexflow:agency:va:court_of_appeals" for c in case.claims)
    assert "lexflow:agency:va:court_vactapp" not in by and "lexflow:agency:va:court_va" not in by
    assert by["lexflow:agency:va:court_of_appeals"].cls == "lexflow:class:court"
    # the existing class items get their canonical key and, where the old loader wrote the label form, that too
    cd = by["lexflow:class:court-decision"]
    assert cd.exists and [c.value.value for c in cd.claims if c.prop == "legal identifier"] == [
        "lexflow:class:court decision", "lexflow:class:court-decision"]
    lp = by["lexflow:class:legal-process"]
    assert [c.value.value for c in lp.claims if c.prop == "legal identifier"] == ["lexflow:class:legal-process"]
    # the ontology hook: the existing class item is appended its close matches (CLASS_CLOSE), nothing else
    assert sorted((c.prop, c.value.value) for c in lp.claims if c.prop != "legal identifier") == [
        ("close match", "http://www.estrellaproject.org/lkif-core/process.owl#Process"),
        ("close match", "https://schema.org/GovernmentService")]
    assert not by["lexflow:class:government"].exists
    assert any(c.prop == "CourtListener ID" for c in case.claims) and any(c.prop == "date decided" for c in case.claims)
    # every item value points at something in the build (or an existing class)
    labels = {c.label for c in SC.CLASSES if c.qid}
    for it, c, v in _values(items):
        if v.kind == "item":
            assert v.value in by or v.value in labels, (it.key, c.prop, v.value)
        assert v.kind != "string" or len(v.value) <= SC.STRING_MAX
    assert all(len(it.label) <= 250 and len(it.description) <= 250 for it in items)
    assert all(c.prop in SC.ALL_PROPERTY_LABELS for it in items for c in it.claims)


def test_no_value_carries_a_personal_mailbox_or_no_reprint_words_and_contacts_are_filtered(seeded):
    items = graph.build(seeded, states=["va"], log=lambda s: None)
    by = {it.key: it for it in items}
    text = " ".join(v.value for _, _, v in _values(items)) + " ".join(it.label + it.description for it in items)
    assert PERSONAL not in text and "Jane Doe" not in text and "434-555-0199" not in text
    assert NO_REPRINT_WORDS not in text                                   # albemarle.org is NO_REPRINT
    assert QT.policy("https://www.albemarle.org/foia")
    s2 = by["lexflow:step:47210400100000:public_records_request:s2"]
    ref = dict(next(c for c in s2.claims if c.prop == "time limit").references[0])
    assert "quoted text" not in ref and ref["source URL"].value == "https://www.albemarle.org/foia"
    s1 = by["lexflow:step:47210400100000:public_records_request:s1"]
    ref1 = dict(next(c for c in s1.claims if c.prop == "contact page URL").references[0])
    assert ref1["quoted text"].value == "Submit your request online" and ref1["retrieved"].value == "2026-10-10"
    assert ref1["determination method"].value.endswith(":software-match")
    local = by["lexflow:process:47210400100000:public_records_request"]
    mail = [c.value.value for c in local.claims if c.prop == "email address"]
    assert mail == ["mailto:foia@charlottesville.gov"]
    assert privacy.is_office_mailbox("foia@charlottesville.gov") and not privacy.is_office_mailbox(PERSONAL)
    phones = [c.value.value for c in local.claims if c.prop == "phone number"]
    assert phones == ["434-555-0100"]
    postal = [c.value.value for c in local.claims if c.prop == "postal address"]
    assert postal and all("Jane" not in p for p in postal)
    office = by["lexflow:agency:47210400100000:foia_office"]
    assert [c.value.value for c in office.claims if c.prop == "email address"] == ["mailto:foia@charlottesville.gov"]
    gov = by["lexflow:gov:47210400100000"]
    assert not any(c.prop == "email address" for c in gov.claims)         # general mailboxes wait for the checks
    assert any(c.prop == "Wikidata item ID" and c.value.value == "Q123766" for c in gov.claims)
    assert any(c.prop == "government ID" for c in gov.claims)
    jur = by["lexflow:jurisdiction:va"]
    assert any(c.prop == "Wikidata item ID" and c.value.value == "Q1370" for c in jur.claims)


def test_build_is_deterministic(seeded):
    a = graph.build(seeded, states=["va"], log=lambda s: None)
    b = graph.build(seeded, states=["va"], log=lambda s: None)
    assert [it.key for it in a] == sorted(it.key for it in a)
    assert repr(a) == repr(b)
    assert graph.parse_limit("within three business days of receiving a request") == (3, "business-days", "receiving a request")
    assert graph.parse_limit("within 30 days") == (30, "calendar-days", None)
    assert graph.parse_limit("Registration deadline October 23") is None
    assert graph.parse_fee("$1,500.50 plus value") == ("1500.50", "$1,500.50 plus value")
    assert graph.parse_fee("$500") == ("500", None) and graph.parse_fee("No fee") == ("0", "No fee")
    assert graph.personal_mailbox("write to jane.doe@example.gov") == "jane.doe@example.gov"
    assert graph.personal_mailbox("write to foia@example.gov") is None


def test_local_deadline_and_fee_texts_reduce():
    """The common shapes of the researched place files (docs: 60 files, 273 step deadlines and 177 fees that did not
    reduce before 15 October 2026)."""
    pl, pf = graph.parse_limit, graph.parse_fee
    assert pl("within 30 days") == (30, "calendar-days", None)
    assert pl("5 working days") == (5, "working-days", None)
    assert pl("no later than 10 business days after the hearing") == (10, "business-days", "the hearing")
    assert pl("Not later than 45 days before the election") == (45, "calendar-days", "the election")
    assert pl("Within ten days from the conviction") == (10, "calendar-days", "the conviction")
    assert pl("Before noon on the third day after the election") == (3, "calendar-days", "the election")
    assert pl("Within 96 hours for the lower fine") == (96, "hours", None)
    assert pl("30 days from service of the decision (Rule 2A:2), plus 3 days if served by mail") == \
        (30, "calendar-days", "service of the decision")
    assert pl("Within one (1) year of the decision") == (1, "years", "the decision")
    assert pl("within a year") == (1, "years", None)
    assert pl("Responses by mail within 5 to 10 business days") == (10, "business-days", None)
    assert pl("by the close of the next business day") == (1, "business-days", None)
    assert pl("at least 60 days preceding the tax year (Va. Code § 58.1-3234(1))") == (60, "calendar-days", "the tax year")
    assert pl("Within 30 days after the dog turns 4 months old") == (30, "calendar-days", "the dog turns 4 months old")
    # no limit: a date, a vague phrase, an age, nothing stated
    for t in ("June 5 and December 5", "By the due date", "Not stated", "None stated", "The dog must be vaccinated from "
              "4 months of age", "Registration deadline October 23", "", None):
        assert pl(t) is None, t
    assert pf("$75") == ("75", None) and pf("$25 per year") == ("25", "$25 per year")
    assert pf("$0.50 per $100 of value") == ("0.50", "$0.50 per $100 of value")
    assert pf("$20 if paid within 96 hours; $40 after") == ("20", "$20 if paid within 96 hours; $40 after")
    assert pf("ten cents per page") == ("0.10", "ten cents per page") and pf("five dollars") == ("5", "five dollars")
    assert pf("No fee") == ("0", "No fee") and pf("No license tax") == ("0", "No license tax") and pf("Free") == ("0", "Free")
    assert pf("None: the return envelope is postage prepaid") == ("0", "None: the return envelope is postage prepaid")
    assert pf("No application fee when only the use changes") == ("0", "No application fee when only the use changes")
    # not a fee of nothing, and not a dollar amount
    for t in ("None stated", "Not stated", "No fee stated", "No late penalties while the request is under review",
              "2.5%", "10% of the tax", "The fine on the ticket", "Same as s4", "", None):
        assert pf(t) is None, t


def test_courts_are_named_from_the_fixture_and_keep_the_id_as_alias(seeded):
    b = graph.Build(seeded, states=["va", "wy"], log=lambda s: None)
    b.court_names = {"wyo": {"name": "Supreme Court of Wyoming", "jurisdiction": "wy",
                             "url": "https://www.courts.state.wy.us/", "citation": "Wyo."},
                     "va": {"name": "Supreme Court of Virginia", "jurisdiction": "va", "url": "http://www.vacourts.gov/"}}
    by = {it.key: it for it in b.run()}
    wyo = by["lexflow:agency:wy:court_wyo"]
    assert wyo.label == "Supreme Court of Wyoming" and "wyo" in wyo.aliases and wyo.cls == "lexflow:class:court"
    assert any(c.prop == "official website" and c.value.value == "https://www.courts.state.wy.us/" for c in wyo.claims)
    # the ladder's court keeps its own label; the fixture's name and the id become aliases
    va = by["lexflow:agency:va:supreme_court"]
    assert "va" in va.aliases and "Supreme Court of Virginia" in va.aliases + [va.label]
    vactapp = by["lexflow:agency:va:court_of_appeals"]
    assert "vactapp" in vactapp.aliases and "Court of Appeals of Virginia" in vactapp.aliases + [vactapp.label]
    assert not [it.key for it in by.values() if it.cls == "lexflow:class:court" and it.label.startswith("Wyoming court")]
    assert "courts without a name (courts.json or case_law)" not in b.gaps
    # the shipped fixture names every court of caselaw.COURTS
    from lexflow.municipal.caselaw import COURTS
    shipped = json.loads((ROOT / "fixtures" / "entities" / "courts.json").read_text(encoding="utf-8"))["courts"]
    assert all(cid in shipped and shipped[cid]["name"] and shipped[cid]["jurisdiction"] == st
               for st, ids in COURTS.items() for cid in ids)


def test_topics_json_is_used_only_when_accepted_or_sure(seeded):
    seeded.execute("UPDATE place_processes SET category='courts_legal'")
    seeded.commit()
    key = "47210400100000/public_records_request"
    pkey = "lexflow:process:47210400100000:public_records_request"

    def run(entry, audience_in_file=True):
        logs = []
        b = graph.Build(seeded, states=["va"], log=logs.append)
        b.topics = {key: entry} if entry else {}
        items = b.run()
        proc = next(it for it in items if it.key == pkey)
        return ([c.value.value for c in proc.claims if c.prop == "topic"],
                [c.value.value for c in proc.claims if c.prop == "audience"], logs, b.gaps)
    topics, auds, logs, gaps = run(None)
    assert topics == [] and auds == ["lexflow:vocab:audience:resident"] and gaps.get("local processes of unmapped category (courts_legal)") == 1
    sure = {"topic": "courts", "topic_confidence": 0.97, "audience": "requester", "audience_confidence": 0.5,
            "confidence": 0.5, "model": "tev1:0.8b", "date": "2026-10-15", "accepted": False}
    topics, auds, logs, gaps = run(sure)
    assert topics == ["lexflow:vocab:topic:courts"] and auds == ["lexflow:vocab:audience:resident"]   # the file's audience
    assert any("topic courts from topics.json (model confidence 0.97" in l for l in logs)
    unsure = {**sure, "topic_confidence": 0.6, "confidence": 0.6}
    topics, auds, logs, gaps = run(unsure)
    assert topics == [] and any("topics.json topic courts not used (confidence 0.60" in l for l in logs)
    accepted = {**unsure, "accepted": True}
    topics, auds, logs, gaps = run(accepted)
    assert topics == ["lexflow:vocab:topic:courts"] and any("accepted by a person" in l for l in logs)
    # with no audience in the file, the decided audience is used under the same rule
    spec = json.loads(db.one(seeded, "SELECT spec FROM place_processes")["spec"])
    spec["audience"] = []
    seeded.execute("UPDATE place_processes SET spec=?", (json.dumps(spec),))
    seeded.commit()
    topics, auds, logs, gaps = run({**sure, "audience_confidence": 0.95})
    assert auds == ["lexflow:vocab:audience:requester"]
    topics, auds, logs, gaps = run({**sure, "topic": "nonsense", "topic_confidence": 1.0})
    assert topics == [] and any("is not in the vocabulary" in l for l in logs)


def test_local_step_kind_from_the_file_or_a_sure_decision_model(seeded):
    from lexflow.extract import decide as D
    spec = json.loads(db.one(seeded, "SELECT spec FROM place_processes")["spec"])
    spec["steps"][0]["kind"] = "filing"
    seeded.execute("UPDATE place_processes SET spec=?", (json.dumps(spec),))
    seeded.commit()
    s1k, s2k = ("lexflow:step:47210400100000:public_records_request:s1", "lexflow:step:47210400100000:public_records_request:s2")

    def kinds(items, key):
        it = next(i for i in items if i.key == key)
        return [(c.value.value, dict(c.references[0])["determination method"].value) for c in it.claims if c.prop == "step kind"]
    # no decider (LEXFLOW_DECIDE off): the file's kind only
    b = graph.Build(seeded, states=["va"], log=lambda s: None)
    b.decider = None
    items = b.run()
    assert kinds(items, s1k) == [("lexflow:vocab:step-kind:filing", "lexflow:vocab:determination-method:curated")]
    assert kinds(items, s2k) == []
    asked = []

    def answer(state, questions):
        asked.append(D.normalise_state(state))
        return {"model": "stub", "answers": {"kind": D.parse_answer("choice", {"choice": "decision", "confidence": 0.88,
                                                                              "probabilities": {"decision": 0.9}})}, "usage": {}, "ms": 1}
    stub = D.Decider(cache=False, backend_info={"kind": "decision", "model": "stub", "models": []}, answer=answer)
    items = graph.build(seeded, states=["va"], log=lambda s: None, decider=stub)
    assert kinds(items, s1k)[0][0].endswith(":filing")                      # the file wins; the model is not asked
    assert kinds(items, s2k) == [("lexflow:vocab:step-kind:decision", "lexflow:vocab:determination-method:ai-verifier")]
    assert asked == ["Step: The City answers\nLaw: " + NO_REPRINT_WORDS]
    unsure = D.Decider(cache=False, backend_info={"kind": "decision", "model": "stub", "models": []},
                       answer=lambda s, q: {"model": "stub", "answers": {"kind": D.parse_answer(
                           "choice", {"choice": "decision", "confidence": 0.5, "probabilities": {}})}, "usage": {}, "ms": 1})
    items = graph.build(seeded, states=["va"], log=lambda s: None, decider=unsure)
    assert kinds(items, s2k) == []


def test_unit_descriptions_say_where_they_sit_and_what_they_hold(seeded, monkeypatch):
    items = graph.build(seeded, states=["va"], log=lambda s: None)
    by = {it.key: it for it in items}
    assert by["lexflow:code:va"].description == "Code of Virginia: 2 titles, 4 sections cited by lexflow"
    assert by["lexflow:unit:va:t2.2"].description == "Title 2.2 of the Virginia Code; holds §§ 2.2-3704 to 2.2-3713, 3 sections " \
        "(first: Public records to be open to inspection; procedure for requesting records)"
    assert by["lexflow:unit:va:t2.2-sii"].description.startswith("Subtitle II of Va. Code Ann. Title 2.2; holds §§ 2.2-3704 to 2.2-3713")
    assert by["lexflow:unit:va:t2.2-sii-pb-c37"].description.startswith(
        "Chapter 37 of Va. Code Ann. Title 2.2, Subtitle II, Part B; holds §§ 2.2-3704 to 2.2-3713, 3 sections (first: ")
    assert by["lexflow:unit:va:t30-c21"].description == "Chapter 21 of Va. Code Ann. Title 30; holds § 30-179 (first: Powers and duties of the Council)"
    assert all(len(it.description) <= 250 for it in items)
    # a heading from fixtures/law/unit_headings.json leads the description and is the heading text
    monkeypatch.setattr(graph, "_unit_headings", lambda: {"lexflow:unit:va:t2.2-sii-pb-c37": {
        "name": "Virginia Freedom of Information Act", "source": "https://law.lis.virginia.gov/", "retrieved": "2026-10-15"}})
    by2 = {it.key: it for it in graph.build(seeded, states=["va"], log=lambda s: None)}
    ch = by2["lexflow:unit:va:t2.2-sii-pb-c37"]
    assert ch.description.startswith("Virginia Freedom of Information Act — Chapter 37 of Va. Code Ann. Title 2.2, Subtitle II, Part B; holds")
    assert [c.value.value for c in ch.claims if c.prop == "heading text"] == ["Virginia Freedom of Information Act"]
    assert repr(graph.build(seeded, states=["va"], log=lambda s: None)) == repr(graph.build(seeded, states=["va"], log=lambda s: None))


def test_office_texts_split_into_offices_and_addresses_fold():
    so = graph.split_offices
    assert so("Commissioner of the Revenue (assessment); City Treasurer (billing and collection)") == [
        ("Commissioner of the Revenue", "assessment"), ("City Treasurer", "billing and collection")]
    assert so("Commissioner of the Revenue, City of Charlottesville (elected constitutional officer); billing and "
              "collection by the City Treasurer") == [
        ("Commissioner of the Revenue", "elected constitutional officer; City of Charlottesville"),
        ("City Treasurer", "billing and collection by the City Treasurer")]
    assert so("Board of Zoning Appeals and Planning Commission") == [("Board of Zoning Appeals", None), ("Planning Commission", None)]
    assert so("Department of Finance and Budget, County Assessor's Office (real estate assessment)") == [
        ("Department of Finance and Budget, County Assessor's Office", "real estate assessment")]
    albemarle = so("Department of Finance & Budget, Office of Revenue Administration (Business & Personal Tax Unit), County of "
                   "Albemarle. Under the county executive form there is no elected Commissioner of the Revenue or Treasurer: "
                   "the Director of Finance assesses and collects the tax.")
    assert [l for l, _ in albemarle] == ["Department of Finance & Budget, Office of Revenue Administration"]
    assert "Under the county executive form" in albemarle[0][1] and "Business & Personal Tax Unit" in albemarle[0][1]
    staunton = so("Commissioner of the Revenue, City of Staunton (an elected constitutional officer, who assesses and issues "
                  "business licenses; the City Treasurer collects payments)")
    assert [l for l, _ in staunton] == ["Commissioner of the Revenue"] and "City of Staunton" in staunton[0][1]
    assert so("Community Development Department, Zoning Division (Zoning Administrator): homestay zoning clearance; "
              "Department of Finance & Budget, Office of Revenue Administration (Business & Personal Tax Unit): business license") == [
        ("Community Development Department, Zoning Division", "homestay zoning clearance; Zoning Administrator"),
        ("Department of Finance & Budget, Office of Revenue Administration", "business license; Business & Personal Tax Unit")]
    assert so("City Treasurer; City Treasurer (elected constitutional officer)") == [("City Treasurer", "elected constitutional officer")]
    assert so("") == [] and so(None) == []
    roles = [("r1", "k1", "Commissioner of the Revenue"), ("r2", "k2", "City Treasurer")]
    assert graph._pick_office_role("City Treasurer", None, roles) == "r2"
    assert graph._pick_office_role("Treasurer's cashier", "Pay the bill", roles) == "r2"
    assert graph._pick_office_role("The office", "Assess the return", roles) == "r1"
    assert graph._pick_office_role("Commissioner of the Revenue", None, []) is None
    np, pk = graph.normalise_postal, graph.postal_key
    assert np("605 E Main Street, Room A-130, Charlottesville, VA 22902 (in person Monday to Friday, 8:30 am to 4:30 pm)") == \
        "605 E Main Street, Room A-130, Charlottesville, VA 22902"
    assert np("Treasurer,  PO Box 2964,\nCharlottesville, VA 22902") == "Treasurer, P.O. Box 2964, Charlottesville, VA 22902"
    assert np("P. O. Box 911, Charlottesville, VA 22902 (mailing address)") == "P.O. Box 911, Charlottesville, VA 22902 (mailing address)"
    assert pk("605 E Main St, Charlottesville, VA 22902") == pk("605 East Main Street, Charlottesville, Virginia 22902 (Zoning physical address)")
    assert pk("Commissioner of the Revenue, PO Box 2964, Charlottesville, VA 22902") == pk("Commissioner of the Revenue, P.O. Box 2964, Charlottesville, VA 22902")
    assert pk("605 E Main St, Room A-130, Charlottesville, VA 22902") != pk("605 E Main St, Room A120, Charlottesville, VA 22902")


def test_split_offices_roles_office_types_and_one_address_per_office(seeded):
    gid = "47210400100000"
    spec = json.loads(db.one(seeded, "SELECT spec FROM place_processes")["spec"])
    spec["office"] = "Commissioner of the Revenue (assessment); City Treasurer (billing and collection)"
    spec["steps"][1]["who"] = "City Treasurer"
    spec["steps"].append({"id": "s3", "step": "Assess the return", "who": "Commissioner of the Revenue staff", "how": "x",
                          "deadline": None, "fee": None, "form": None, "url": None, "quote": "assessed by the Commissioner",
                          "source": "https://www.charlottesville.gov/foia"})
    seeded.execute("UPDATE place_processes SET spec=?, office=? WHERE gov_id=?", (json.dumps(spec), spec["office"], gid))
    db.upsert(seeded, "contacts", [
        {"gov_id": gid, "state": "va", "question": "public_records_request", "kind": "office",
         "value": "City Hall, 605 E Main Street, Room A-130, Charlottesville, VA 22902 (in person Monday to Friday, 8:30 am to 4:30 pm)",
         "label": "Commissioner of the Revenue", "source": "local-research"},
        {"gov_id": gid, "state": "va", "question": "public_records_request", "kind": "office",
         "value": "City Hall, 605 E Main St, Room A-130, Charlottesville, VA 22902", "label": "Commissioner of the Revenue",
         "source": "local-research"},
        {"gov_id": gid, "state": "va", "question": "public_records_request", "kind": "postal",
         "value": "Commissioner of the Revenue, P.O. Box 2964, Charlottesville, VA 22902", "label": "mail", "source": "local-research"},
        {"gov_id": gid, "state": "va", "question": "public_records_request", "kind": "postal",
         "value": "Commissioner of the Revenue, PO Box 2964, Charlottesville, VA 22902", "label": "mail", "source": "local-research"},
    ])
    seeded.commit()
    items = graph.build(seeded, states=["va"], log=lambda s: None)
    by = {it.key: it for it in items}
    cor, tre = by[f"lexflow:agency:{gid}:commissioner_of_the_revenue"], by[f"lexflow:agency:{gid}:city_treasurer"]
    assert cor.label == "Commissioner of the Revenue" and "assessment" in cor.description
    assert tre.label == "City Treasurer" and "billing and collection" in tre.description
    assert not [k for k in by if k.startswith(f"lexflow:agency:{gid}:") and (";" in by[k].label or "(" in by[k].label)]
    # the local offices are instances of the state's office types, which the state roles are played by
    assert any(c.prop == "instance of" and c.value.value == "lexflow:office-type:va:commissioner_of_the_revenue" for c in cor.claims)
    assert any(c.prop == "instance of" and c.value.value == "lexflow:office-type:va:treasurer" for c in tre.claims)
    ot = by["lexflow:office-type:va:treasurer"]
    assert ot.cls == "lexflow:class:office-type" and ot.label == "Treasurer"
    assert any(c.prop == "subclass of" and c.value.value == "lexflow:class:government-agency" for c in ot.claims)
    # roles: the first office keeps the "office" role, the other is named after it; steps point at the right one
    role_office, role_tre = by[f"lexflow:role:{gid}:public_records_request:office"], by[f"lexflow:role:{gid}:public_records_request:city_treasurer"]
    assert any(c.prop == "played by" and c.value.value == cor.key for c in role_office.claims)
    assert any(c.prop == "played by" and c.value.value == tre.key for c in role_tre.claims)
    bearer = lambda sid: next(c.value.value for c in by[f"lexflow:step:{gid}:public_records_request:{sid}"].claims if c.prop == "bearer")  # noqa: E731
    assert bearer("s2") == role_tre.key and bearer("s3") == role_office.key and bearer("s1").endswith(":applicant")
    # one address per distinct address on the office and on the process
    postal = [c.value.value for c in cor.claims if c.prop == "postal address"]
    assert postal == ["City Hall, 605 E Main St, Room A-130, Charlottesville, VA 22902",
                      "City Hall, 605 E Main Street, Room A120, Charlottesville, VA 22902",      # the fixture's own row
                      "Commissioner of the Revenue, P.O. Box 2964, Charlottesville, VA 22902"]
    proc = by[f"lexflow:process:{gid}:public_records_request"]
    assert len([c for c in proc.claims if c.prop == "postal address"]) == 3
    assert not any("8:30 am" in c.value.value for c in proc.claims if c.prop == "postal address")


def test_state_roles_are_played_by_office_types(seeded):
    m = db.one(seeded, "SELECT facts FROM process_models WHERE model_id='va.records'")
    facts = json.loads(m["facts"])
    facts["actors"].append({"id": "commissioner_revenue", "name": "Commissioner of the revenue", "kind": "official",
                            "source": facts["actors"][0]["source"]})
    facts["actors"].append({"id": "registrar", "name": "General registrar", "kind": "official", "source": facts["actors"][0]["source"]})
    seeded.execute("UPDATE process_models SET facts=? WHERE model_id='va.records'", (json.dumps(facts),))
    seeded.commit()
    by = {it.key: it for it in graph.build(seeded, states=["va"], log=lambda s: None)}
    assert [c.value.value for c in by["lexflow:role:va:records:commissioner_revenue"].claims if c.prop == "played by"] == \
        ["lexflow:office-type:va:commissioner_of_the_revenue"]
    assert [c.value.value for c in by["lexflow:role:va:records:registrar"].claims if c.prop == "played by"] == \
        ["lexflow:office-type:va:general_registrar"]
    assert not any(c.prop == "played by" and c.value.value.startswith("lexflow:office-type")
                   for c in by["lexflow:role:va:records:public_body"].claims)   # the ladder's body, not an office type
    for slug_ in ("commissioner_of_the_revenue", "treasurer", "clerk_of_the_circuit_court", "attorney_for_the_commonwealth",
                  "sheriff", "general_registrar"):
        assert f"lexflow:office-type:va:{slug_}" in by


def test_dangling_keys_fail_the_build(seeded, monkeypatch):
    """Every item value must name a key the build emits: the check lists every dangling one and raises."""
    original = graph.Build.cases

    def cases_with_a_dangling_body(self, per_section=15):
        original(self, per_section)
        role = self.items["lexflow:role:va:records:requester"]
        self.claim(role, "played by", graph.item("lexflow:agency:va:nobody_builds_this"))
        self.claim(role, "escalates to", graph.item("lexflow:rung:va:records:missing:appeal"))

    monkeypatch.setattr(graph.Build, "cases", cases_with_a_dangling_body)
    logs = []
    with pytest.raises(graph.DanglingKeyError) as e:
        graph.build(seeded, states=["va"], log=logs.append)
    assert sorted(e.value.keys) == [
        "lexflow:role:va:records:requester: escalates to -> lexflow:rung:va:records:missing:appeal",
        "lexflow:role:va:records:requester: played by -> lexflow:agency:va:nobody_builds_this"]
    assert any("dangling: lexflow:role:va:records:requester: played by -> lexflow:agency:va:nobody_builds_this" in l
               for l in logs)


def test_labels_and_descriptions_are_unique_and_levels_are_classified(seeded):
    items = graph.build(seeded, states=["va", "wy"], log=lambda s: None)
    pairs = [(it.label, it.description) for it in items if not it.exists]
    assert len(pairs) == len(set(pairs)), "two new items with one label and description (the wiki refuses that)"
    assert all(it.description for it in items if not it.exists)
    # unit levels: the path's word first, then the act_id token's letter
    assert SC.unit_level("Chapter 37", "C37") == "chapter" and SC.unit_level("Subtitle II", "SII") == "subtitle"
    assert SC.unit_level("T48", "T48") == "title" and SC.unit_level("Chapter 48-3a", "S48_3a_1103") == "chapter"
    assert SC.unit_level("Ley de Transparencia", "TRANSPARENCIA") == "act" and SC.unit_level("", "SIII") == "subtitle"
    assert SC.unit_level("Part B", "PB") == "part" and SC.unit_level("Nonsense", "") is None
    assert graph._token_name("T48") == "Title 48" and graph._token_name("S48_3a_1103") == "§ 48-3a-1103"
    # a local rung's key takes the leading section number of its free-text basis, never a URL or a remark
    assert graph.basis_slug("58.1-3984(A) (circuit court once the assessor has ruled; https://x.gov/a)") == "58.1-3984-a"
    assert graph.basis_slug("12VAC30-110-160") == "12vac30-110-160" and graph.basis_slug("Va. Code § 2.2-3713(A)") == "2.2-3713-a"
    assert graph.basis_slug("https://www.dmas.virginia.gov/appeals/") == "local" and graph.basis_slug("Notice (https://x)") == "local"
    assert graph.basis_slug("15-149 (as cited on https://www.charlottesville.gov/557/parking-tickets)") == "15-149"
    assert not [it.key for it in items if "http:" in it.key or "https:" in it.key or " " in it.key]
    # words from a no-reprint host, or from an Internet Archive capture of one, are never quoted
    assert graph.no_reprint("https://www.albemarle.org/foia") and not graph.no_reprint("https://www.charlottesville.gov/foia")
    assert graph.no_reprint("https://web.archive.org/web/20190918120018/http://www.albemarle.org/upload/a.pdf")
    assert graph.first_url("Albemarle County Code § 15-501; https://web.archive.org/web/2019/http://x.org/a.pdf") ==         "https://web.archive.org/web/2019/http://x.org/a.pdf"
    assert graph._leading_url("http://albemarlemarriage.org/ (redirects to https://albemarlemarriage.org/)") == "http://albemarlemarriage.org/"
    assert graph._leading_url("see the portal") is None
    # the key forms of the class items: canonical slug, label-form alias for the three the wiki holds
    assert SC.key_for("class", "court-decision") == "lexflow:class:court-decision"
    assert SC.legacy_class_key("court-decision") == SC.LEGACY_CLASS_KEYS["court-decision"] == "lexflow:class:court decision"
    assert SC.legacy_class_key("jurisdiction") == SC.key_for("class", "jurisdiction")
    court_keys = json.loads((ROOT / "fixtures" / "entities" / "court_keys.json").read_text(encoding="utf-8"))["courts"]
    ladders = json.loads((ROOT / "fixtures" / "authority" / "ladders.json").read_text(encoding="utf-8"))
    ladder_keys = {b["key"] for b in ladders["bodies"].values() if b.get("key")}
    from lexflow.municipal.caselaw import COURTS
    for ref, m in court_keys.items():
        st, cid = ref.split(":")
        assert cid in COURTS[st] and m["key"] in ladder_keys and SC.kind_of(m["key"]) == "agency", ref


# --------------------------------------------------------------------------- the ontology hook
def test_ontology_hook_fills_equivalents_and_class_matches():
    from lexflow.publish import ontology_map as OM
    for p in SC.PROPERTIES:
        assert p.equivalents == tuple(OM.PROPERTY_EQUIV.get(p.label, ())), p.label
        assert SC.PROP_BY_LABEL[p.label] is p
    for c in SC.CLASSES:
        assert c.exact == tuple(OM.CLASS_MATCH.get(c.slug, ())) and c.close == tuple(OM.CLASS_CLOSE.get(c.slug, ())), c.slug
        assert SC.CLASS_BY_SLUG[c.slug] is c and SC.CLASS_BY_LABEL[c.label] is c
    with_equiv = {p.label for p in SC.PROPERTIES if p.equivalents} | {l for l, v in SC.EXISTING_EQUIVALENTS.items() if v}
    assert with_equiv == set(OM.PROPERTY_EQUIV) and len(with_equiv) == 43          # the doc's 43 of 85
    assert sum(1 for c in SC.CLASSES if c.exact) == 20 and sum(1 for c in SC.CLASSES if c.close) == 18
    assert SC.equivalents_of("part of") == ("http://data.europa.eu/eli/ontology#is_part_of", "https://schema.org/isPartOf")
    assert SC.equivalents_of("topic") == SC.PROP_BY_LABEL["topic"].equivalents and SC.equivalents_of("sort key") == ()
    assert SC.CLASS_BY_SLUG["norm"].exact == ("http://www.estrellaproject.org/lkif-core/norm.owl#Norm",)
    assert SC.CLASS_BY_SLUG["currency"].exact == () and SC.CLASS_BY_SLUG["currency"].wikidata == "Q8142"


def test_class_items_carry_exact_and_close_matches(seeded):
    items = graph.build(seeded, states=["va"], log=lambda s: None)
    by = {it.key: it for it in items}
    statute = by["lexflow:class:statute"]
    assert [c.value.value for c in statute.claims if c.prop == "exact match"] == [
        "http://data.europa.eu/eli/ontology#LegalResourceSubdivision"]
    assert [c.value.value for c in statute.claims if c.prop == "close match"] == ["https://schema.org/Legislation"]
    court = by["lexflow:class:court"]
    assert sorted(c.value.value for c in court.claims if c.prop == "exact match") == sorted(
        [SC.WIKIDATA_ENTITY + SC.CLASS_BY_SLUG["court"].wikidata] + list(SC.CLASS_BY_SLUG["court"].exact))
    # an existing class item (Q11 norm) is appended its LKIF exact match beside its keys
    norm = by["lexflow:class:norm"]
    assert norm.exists and [c.value.value for c in norm.claims if c.prop == "exact match"] == [
        "http://www.estrellaproject.org/lkif-core/norm.owl#Norm"]
    assert all(c.value.kind == "url" for it in items for c in it.claims if c.prop in ("exact match", "close match"))


# --------------------------------------------------------------------------- a merged office already on the wiki
def test_merged_office_on_the_wiki_is_marked_superseded_not_duplicated(seeded):
    gid = "47210400100000"
    spec = json.loads(db.one(seeded, "SELECT spec FROM place_processes")["spec"])
    merged_text = "Commissioner of the Revenue (assessment); City Treasurer (billing and collection)"
    spec["office"] = merged_text
    seeded.execute("UPDATE place_processes SET spec=?, office=? WHERE gov_id=?", (json.dumps(spec), merged_text, gid))
    merged_key = SC.key_for("agency", gid, merged_text)
    seeded.execute("INSERT INTO wikibase_items (key, qid, label) VALUES (?, ?, ?)", (merged_key, "Q4242", merged_text))
    seeded.commit()
    items = graph.build(seeded, states=["va"], log=lambda s: None)
    by = {it.key: it for it in items}
    cor, tre = f"lexflow:agency:{gid}:commissioner_of_the_revenue", f"lexflow:agency:{gid}:city_treasurer"
    assert cor in by and tre in by and merged_key not in (cor, tre)
    old = by[merged_key]
    assert old.exists and old.label == merged_text and old.cls == "lexflow:class:government-agency"
    assert old.description.startswith("Superseded: split into Commissioner of the Revenue and City Treasurer (")
    assert sorted(c.value.value for c in old.claims if c.prop == "replaced by") == sorted([cor, tre])
    assert any(c.prop == "part of" and c.value.value == f"lexflow:gov:{gid}" for c in old.claims)
    # nothing else points at the old item, and no second item carries its label
    assert not [k for k, it in by.items() for c in it.claims if c.value.value == merged_key and k != merged_key]
    assert sum(1 for it in items if it.label == merged_text) == 1
    assert graph.superseded_description(["A"], "Town") == "Superseded: split into A (Town)"
    assert graph.superseded_description(["A", "B", "C"], "Town") == "Superseded: split into A, B and C (Town)"


# ---------------------------------------------------------------- asked answers as drafts (schema 4.4)
def _asked_row(con, qid="public_records", misses=0, status="answered"):
    model = json.loads((ROOT / "curated" / "va" / "records.json").read_text(encoding="utf-8"))
    db.upsert(con, "asked_answers", [{
        "question_id": qid, "target": "va", "state": "va", "gov_id": None, "question_text": "a question",
        "status": status, "sections": json.dumps({"chosen": [{"ref": "2.2-3704", "id": 1}]}),
        "facts": json.dumps(model["facts"]), "answer": "{}", "model": "qwen3:1.7b", "seconds": 30.0,
        "metrics": json.dumps({"quotes_checked": 4, "quote_misses": misses, "answered_at": "2026-10-18T10:00:00Z",
                               "coverage_fill": {"run": "r1", "node": "ollama"}})}])
    con.commit()


def test_asked_answers_become_draft_process_items_only_when_asked_for(seeded):
    _asked_row(seeded)
    _asked_row(seeded, qid="dog_license", misses=1)                     # a quote the statute text does not hold
    _asked_row(seeded, qid="eviction", status="not_found")
    # the default build (and so the push and the lint by default) has no asked item
    plain = {it.key for it in graph.build(seeded, states=["va"], log=lambda s: None)}
    assert not any(":asked:" in k for k in plain)
    logs = []
    items = graph.build(seeded, states=["va"], asked_drafts=True, log=logs.append)
    by = {it.key: it for it in items}
    asked = {k: it for k, it in by.items() if ":asked:" in k}
    pkey = "lexflow:process:asked:va:public_records"
    assert pkey in by and not any("dog_license" in k or "eviction" in k for k in asked)
    proc = by[pkey]
    props = {c.prop: c for c in proc.claims}
    assert proc.cls == "legal process" and not proc.exists
    assert props["review status"].value.value == "lexflow:vocab:review-status:draft"
    assert props["question asked"].value.value == CV.question("public_records")["text"]    # the coverage question
    assert props["topic"].value.value == "lexflow:vocab:topic:public-records"
    assert props["audience"].value.value == "lexflow:vocab:audience:resident"
    assert props["applies to jurisdiction"].value.value == "lexflow:jurisdiction:va"
    assert props["checked on"].value.value.startswith("2026-10-18")
    assert any(c.prop == "references" and c.value.value == "lexflow:statute:va:2.2-3704" for c in proc.claims)
    assert "draft" not in proc.description.lower() and "draft" not in proc.label.lower()
    # steps hang on the process with their roles; the roles are the question's own, drafts too
    steps = [it for k, it in asked.items() if k.startswith("lexflow:step:asked:va:public_records:")]
    assert steps and all(any(c.prop == "part of" and c.value.value == pkey for c in s.claims) for s in steps)
    bearers = {c.value.value for s in steps for c in s.claims if c.prop == "bearer"}
    assert bearers and all(b.startswith("lexflow:role:va:public_records:") and b in by for b in bearers)
    assert all(any(c.prop == "review status" and c.value.value.endswith(":draft") for c in by[b].claims) for b in bearers)
    # a deadline cut from a checked quote keeps its grounding, marked as matched by software
    limit = next(c for s in steps for c in s.claims if c.prop == "time limit")
    ref = dict(limit.references[0])
    assert ref["quoted text"].kind == "string" and ref["determination method"].value.endswith(":software-match")
    # never a contact, an office type, an escalation or a decision on an asked draft
    contact = {"contact page URL", "email address", "phone number", "official website", "postal address"}
    for it in asked.values():
        assert not any(c.prop in contact or c.prop in ("escalates to", "defers to") for c in it.claims), it.key
        assert not any(":decision:" in c.value.value or ":outcome:" in c.value.value for c in it.claims
                       if c.value.kind == "item"), it.key
    roles = [by[b] for b in bearers]
    assert all(all(c.value.value == "lexflow:private-party" for c in r.claims if c.prop == "played by") for r in roles)
    assert not any(c.prop in contact for r in roles for c in r.claims)
    # the lint holds nothing new on them: no drafting words, no person names, no bare labels
    from datetime import date
    from lexflow.publish import lint
    findings = {k: lint.check_item(it, date(2026, 10, 18), set(by)) for k, it in asked.items()}
    assert not {k: f for k, f in findings.items() if f}, findings
    assert any("asked answers written as drafts: 1" in line for line in logs)
    assert graph.build(seeded, states=["dc"], asked_drafts=True, log=lambda s: None) and \
        not any(":asked:" in it.key for it in graph.build(seeded, states=["dc"], asked_drafts=True, log=lambda s: None))
