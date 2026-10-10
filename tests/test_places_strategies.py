"""Clause segmentation, the model-free strategies, quote snapping, places and local answers, the benchmark."""
import json

import pytest

from lexflow import config
from lexflow.extract import strategies as ST
from lexflow.extract.ollama import check_facts
from lexflow.extract.schema import LegalProcessFacts
from lexflow.extract.segment import segment
from lexflow.municipal import places, scoring, statutes
from lexflow.store import db

DC_STYLE = """(a) Any person has a right to inspect any public record of a public body.
(b)(1) A public body shall respond to a request within 15 days.
  (2) The public body may extend the time by 10 working days.
(c) A public body may charge fees, provided that:
  (A) fees are reasonable; and
  (i) waived for the indigent.
"""
MD_STYLE = """(a) (1) Except as provided in paragraph (2) of this subsection, the custodian shall grant or deny the application promptly, but not more than 30 days after receiving the application.

(2) The custodian shall grant or deny an application that is the subject of § 4–356 of this title not more than 50 days after receiving the application.

(b) (1) A custodian who approves the application shall produce the public record immediately or within the reasonable period that is needed to retrieve the public record, but not more than 30 days after receiving the application.
"""


def test_segment_labels_and_exact_spans():
    for text in (DC_STYLE, MD_STYLE):
        for c in segment(text):
            assert text[c.start:c.start + len(c.text)] == c.text
    md = segment(MD_STYLE)
    assert [c.label for c in md] == ["a.1", "a.2", "b.1"]
    assert md[0].modal == "shall" and md[0].subject == "custodian" and md[0].deadline["amount"] == 30
    dc = {c.label: c for c in segment(DC_STYLE)}
    assert dc["b.1"].deadline == {**dc["b.1"].deadline, "amount": 15, "unit": "days"}
    assert dc["b.2"].deadline["unit"] == "business_days" and dc["b.2"].modal == "may"
    assert "c.A.i" in dc


def test_prohibition_and_additional_days():
    text = "B. No public body shall impose surplus fees. The public body shall have an additional seven work days."
    cs = segment(text)
    assert cs[0].modal == "shall not"
    assert cs[1].deadline["amount"] == 7 and cs[1].deadline["unit"] == "business_days"


def test_rules_strategy_quotes_are_exact(va_statutes):
    t = statutes.section_texts("va", ["2.2-3704"])[0]
    r = ST.run("rules", t.text, section=t.section, title=t.title, code=t.code, jurisdiction="Virginia",
               question="records")
    assert r.facts is not None and r.problems == [] and check_facts(r.facts, t.text) == []
    assert any(s.deadline and s.deadline.amount == 5 for s in r.facts.steps)


def test_multi_section_text_cites_each_section(va_statutes):
    texts = statutes.section_texts("va", ["13.1-1010", "13.1-1011"])
    text = statutes.combined_text(texts)
    r = ST.run("rules", text, section=texts[0].section, title="", code=texts[0].code, jurisdiction="Virginia",
               question="business")
    sections = {s.source.section for s in r.facts.steps}
    assert sections <= {"13.1-1010", "13.1-1011"} and len(sections) == 2


def test_snap_repairs_a_paraphrased_quote(va_statutes):
    spec = json.loads((config.CURATED_DIR / "va" / "records.json").read_text())
    facts = LegalProcessFacts.model_validate(spec["facts"])
    text = statutes.combined_text(statutes.section_texts("va", spec["sections"]))
    broken = facts.model_dump()
    broken["steps"][0]["source"]["quote"] = "A request for records shall identify the records requested with reasonable specificity."
    bad = LegalProcessFacts.model_validate(broken)
    assert check_facts(bad, text)
    fixed, n = ST.snap_quotes(bad, text)
    assert n >= 1 and check_facts(fixed, text) == []


class FakeAsker:
    """Stands in for a local model: labels every candidate a step, or plans fixed steps."""

    def __init__(self, replies):
        self.replies = replies
        self.calls = 0

    def ask(self, system, user, schema, retries=1):
        self.calls += 1
        for key, reply in self.replies:
            if key in system:
                return reply(user) if callable(reply) else reply
        return None


def test_outline_grounds_planned_steps_in_clauses(va_statutes):
    t = statutes.section_texts("va", ["2.2-3704"])[0]
    clauses = segment(t.text)
    asker = FakeAsker([
        ("summarise one subsection", {"acts": True, "who": "public body", "summary": "responds"}),
        ("turn a summary", {"steps": [
            {"sub": "B", "who": "requester", "action": "Identify the records requested", "kind": "filing", "condition": ""},
            {"sub": "B", "who": "public body", "action": "Provide records or respond in writing", "kind": "decision",
             "condition": ""}]}),
    ])
    drafts = ST.outline_drafts(asker, clauses, "records", "requesting public records")
    facts = ST.assemble(drafts, clauses, t.section, "records", "Request public records")
    assert check_facts(facts, t.text) == []
    assert facts.steps[1].deadline and facts.steps[1].deadline.amount == 5
    assert all(s.source.subsection.startswith("B") for s in facts.steps)


def test_exclusive_merge_and_deemed_denial_route():
    """Branches that rejoin use an exclusive merge; a missed deadline can lead to a named outcome."""
    from lexflow.extract.compile import compile_facts
    from lexflow.bpmn_xml import to_bpmn_xml
    from lexflow.ir import SectionText
    from lexflow.petri import analyse
    from lexflow.validate import xsd_errors
    text = ("A. A person may request a record. B. The custodian shall respond within 30 days. "
            "C. The custodian may extend the time. D. The custodian shall release the record. "
            "E. Failure to respond is deemed a denial.")
    q = lambda s, sub: {"section": "1-1", "subsection": sub, "quote": s}  # noqa: E731
    facts = LegalProcessFacts.model_validate({
        "process_name": "Request", "trigger": "A request", "trigger_source": q("A person may request a record.", "A"),
        "actors": [{"id": "person", "name": "Person", "kind": "private-party", "source": q("A person may request a record.", "A")},
                   {"id": "custodian", "name": "Custodian", "kind": "public-body", "source": q("The custodian shall respond within 30 days.", "B")}],
        "steps": [
            {"id": "request", "actor": "person", "action": "Request a record", "kind": "filing", "modality": "permission",
             "after": [], "recipient": "custodian", "source": q("A person may request a record.", "A")},
            {"id": "respond", "actor": "custodian", "action": "Respond", "kind": "decision", "modality": "obligation",
             "after": ["request"], "source": q("The custodian shall respond within 30 days.", "B"),
             "deadline": {"amount": 30, "unit": "days", "anchor": "the request", "consequence": "deemed-denial",
                          "on_miss": "deemed_denied", "source": q("The custodian shall respond within 30 days.", "B")}},
            {"id": "extend", "actor": "custodian", "action": "Extend the time", "kind": "act", "modality": "permission",
             "after": ["respond"], "condition": "needs_more_time", "source": q("The custodian may extend the time.", "C")},
            {"id": "release", "actor": "custodian", "action": "Release the record", "kind": "act", "modality": "obligation",
             "after": ["respond", "extend"], "join": "any", "source": q("The custodian shall release the record.", "D")}],
        "outcomes": [{"id": "released", "description": "Released", "after": ["release"], "source": q("The custodian shall release the record.", "D")},
                     {"id": "deemed_denied", "description": "Deemed denied", "after": [], "source": q("Failure to respond is deemed a denial.", "E")}]})
    assert check_facts(facts, text) == []
    m = compile_facts(facts, model_id="t-merge", jurisdiction="va", jurisdiction_name="Test", code="Test Code",
                      text=SectionText(section="1-1", title="t", code="Test Code", jurisdiction="va", text=text))
    nodes = {n.id: n for _, _, n in m.iter_nodes()}
    assert nodes["release_join"].type == "exclusiveGateway"
    flows = [f for p in m.processes() for f in p.flows]
    assert any(f.source == "respond_deadline" and f.target in ("deemed_denied", "deemed_denied_merge") for f in flows)
    assert xsd_errors(to_bpmn_xml(m)) == []
    report, *_ = analyse(m.processes()[0])
    assert report.sound and not report.error


def _govs(con):
    db.upsert(con, "governments", [
        dict(gov_id="47210400100000", state="va", name="City of Charlottesville", kind="municipality",
             county_fips="51540", place_fips="14968", population=45672, website="http://www.charlottesville.org/"),
        dict(gov_id="21200400100000", state="md", name="City of Baltimore", kind="municipality", county_fips="24510",
             population=576498),
        dict(gov_id="21100300300000", state="md", name="Baltimore County", kind="county", county_fips="24005",
             population=849316),
        dict(gov_id="09200100100000", state="dc", name="City of Washington DC", kind="municipality",
             county_fips="11001", population=670050)])
    con.commit()


def test_place_specs_resolve(con):
    _govs(con)
    name = lambda spec: [g["name"] for g in places.resolve(con, spec)]  # noqa: E731
    assert name("va:charlottesville") == ["City of Charlottesville"]
    assert name("md:baltimore") == ["City of Baltimore"]
    assert name("md:baltimore county") == ["Baltimore County"]
    assert name("dc") == ["City of Washington DC"]
    with pytest.raises(ValueError):
        places.resolve_all(con, "va:nowhere")


def test_local_answers_load_and_raise_the_score(con, va_statutes, tmp_path, monkeypatch):
    _govs(con)
    pdir = tmp_path / "places" / "va"
    pdir.mkdir(parents=True)
    (pdir / "charlottesville.json").write_text(json.dumps({
        "place": "va:charlottesville", "researched": "2026-10-10", "verified": True,
        "answers": {"records": {"summary": "Ask the city's FOIA officer.", "steps": [],
                                "contacts": [{"kind": "portal", "value": "https://example.test/foia",
                                              "label": "FOIA portal", "url": "https://example.test/foia"}],
                                "local_law": [], "fees": "Actual cost", "caveats": []}},
        "sources": [{"url": "https://example.test/foia", "title": "FOIA"}]}))
    monkeypatch.setattr(places, "PLACES_DIR", tmp_path / "places")
    out = places.load_local(con)
    assert out["answers"] == 1
    scoring.run(con, "va", log=lambda *_: None, gov_ids=["47210400100000"])
    a = db.one(con, "SELECT local_score, contact_level FROM answers WHERE gov_id='47210400100000' AND question='records'")
    assert a["local_score"] == 1.0 and a["contact_level"] == "page"


def test_benchmark_scores_rules_against_the_reference(con, va_statutes):
    from lexflow.extract import benchmark as BM
    row = BM.run_one(con, "va.records", "rules", None, log=lambda *_: None)
    assert row["valid"] == 1 and 0 < row["equivalence"] < 1 and row["gold_steps"] >= 5
    best = BM.best(con)
    assert best and best[0]["strategy"] == "rules"


def test_wiki_pages_escape_and_stay_in_namespace(con, va_statutes):
    from lexflow.municipal import build, locator
    from lexflow.municipal.questions import QUESTIONS
    from lexflow.publish import lexipedia as LX
    assert LX.esc("§ 4-202(c)(1) [[x]] a|b") == "§ 4-202%%(c)%%(1) %%[[%%x%%]]%% a%%|%%b"
    _govs(con)
    locator.run(con, QUESTIONS["records"], ["va"], log=lambda *_: None)
    build.build(con, "va", "records", use_llm=False, log=lambda *_: None)
    pages = LX.all_pages(con)
    assert set(pages) >= {"lexflow:start", "lexflow:va:records"}
    assert all(p.startswith("lexflow:") for p in pages)
    assert '<bpmnio type="bpmn">' in pages["lexflow:va:records"] and "</bpmnio>" in pages["lexflow:va:records"]
