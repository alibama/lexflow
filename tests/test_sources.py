"""Text rebuild, history/citation parsing, SearXNG client, Legistar case building."""
import json
from pathlib import Path

import responses

from lexflow import gold
from lexflow.extract.searx import SearX, classify, queries_for
from lexflow.sources.legistar import build_cases, conformance
from lexflow.text.citations import find_citations
from lexflow.text.clean import clean_text
from lexflow.text.history import parse_history
from lexflow.text.sections import resegment

ROOT = Path(__file__).resolve().parents[1]
ROWS = json.loads((ROOT / "fixtures/locus/va_samples.json").read_text())["rows"]


def sections(key, value, code, juris):
    return {s.number: s for s in resegment([r for r in ROWS if r[key] == value], code, juris)}


def test_page_furniture_removed_and_sentence_rejoined():
    row = next(r for r in ROWS if r["row"] == 1949245)
    text, removed = clean_text(row["content"])
    assert "10:00 p.m. and 6:00 a.m." in text and "Supp. No." not in text and "$ 16-9" not in text
    assert "CHARLOTTESVILLE CITY CODE" in removed


def test_17_211_rebuilt_from_seven_chunks_with_gap_flagged():
    s = sections("county", "albemarle_county", "Albemarle County Code", "va/albemarle_county")["17-211"]
    assert len(s.rows) == 7 and s.subsections == ["A", "B", "C", "D", "F"]
    assert "missing-subsection:E" in s.flags and any(f.startswith("page-head-row") for f in s.flags)
    assert "F. Judicial review. A final decision" in s.text


def test_header_content_mismatch_detected():
    secs = sections("city", "charlottesville", "Charlottesville City Code", "va/charlottesville")
    assert any(f.startswith("header-mismatch") for f in secs["17-21"].flags)
    assert {"17-1", "17-2", "17-3"} <= set(secs)          # sections recovered from inside a mislabelled row


def test_history_parsing_dates_and_ordinances():
    s = sections("county", "albemarle_county", "Albemarle County Code", "va/albemarle_county")["17-207"]
    h = parse_history(s.history)
    assert h.first_enacted == "1975-06-18" and h.last_amended == "2024-06-05"
    assert any(a.ordinance == "Ord. 14-17(1)" and a.effective == "2014-07-01" for a in h.amendments)


def test_citations_resolve_to_lis_and_wiki_pages():
    s = sections("county", "albemarle_county", "Albemarle County Code", "va/albemarle_county")["17-211"]
    found = {(c.kind, c.section) for c in find_citations(s.text, "va/albemarle_county")}
    assert ("va-code", "62.1-44.15:46") in found and ("va-admin", "9VAC25-875-560") in found
    assert ("local", "17-300") in found


@responses.activate
def test_searx_client_and_plan():
    responses.add(responses.GET, "http://searx.test/search", json={"results": [
        {"title": "§ 62.1-44.15:46. Appeals", "url": "https://law.lis.virginia.gov/vacode/62.1-44.15:46/",
         "content": "...", "engine": "brave"},
        {"title": "Code of Ordinances", "url": "https://library.municode.com/va/albemarle_county/codes/code_of_ordinances",
         "content": "...", "engine": "duckduckgo"}]})
    hits = SearX("http://searx.test").search('"62.1-44.15:46" site:law.lis.virginia.gov')
    assert [h["kind"] for h in hits] == ["va-code", "municipal-code"]
    assert "format=json" in responses.calls[0].request.url
    plan = queries_for(gold.albemarle_17_211().texts[0], "Albemarle County")
    wants = {p["want"] for p in plan}
    assert {"municipal-code", "va-code", "va-admin-code", "legislation", "case-law"} <= wants


def test_classify():
    assert classify("https://webapi.legistar.com/v1/albemarle/matters") == "legislation"
    assert classify("https://www.courtlistener.com/opinion/1/x/") == "case-law"


def test_legistar_cases_and_conformance():
    d = json.loads((ROOT / "fixtures/legistar/albemarle_2026.json").read_text())
    cases = build_cases(d["matters"], d["histories"])
    assert len(cases) == 6
    r = conformance(cases)
    assert r.complete_cases == 5 and sorted(r.days_authorize_to_decision) == [28, 28, 28, 28, 35]
    assert "notice_1" in r.unobservable_steps
