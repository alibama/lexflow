"""Official forms by step (lexflow/forms/registry.py) and drafts made from the statute (lexflow/forms/draft.py).

The worked-example tests read out/forms/. The app container does not mount out/, so there they skip unless
LEXFLOW_FORMS_OUT names a copy of out/forms (for example one copied into the container's /tmp). The comparison of
the statute texts with the ones the worked examples were built from runs wherever the texts are: Virginia's from
fixtures/statutes everywhere, California's where the local open-us-law store is (the app container)."""
import dataclasses
import hashlib
import json
import os
import re
import unicodedata
from datetime import date
from pathlib import Path

import pytest

from lexflow.forms import draft as D
from lexflow.forms import registry as R

ROOT = Path(__file__).resolve().parents[1]
STATUTES = ROOT / "fixtures" / "statutes"
OUT = Path(os.environ.get("LEXFLOW_FORMS_OUT") or ROOT / "out" / "forms")
SKELETON = {"subject", "salutation", "closing"}
OBLIGATION = re.compile(r"\b(must|shall|should|ought|require|required|requires|requiring|requirement|req|reqd|need|"
                        r"needs|needed|needful|need to|have to|has to|necessary|necessity|essential|compulsory|"
                        r"compelled|obligatory|obliged|obliges|obligate|obligated|mandatory|mandated|expected to|"
                        r"please|kindly|is to be|are to be)\b", re.I)


def asterisks(s: str) -> list[str]:
    """The test's own list of asterisk-like marks: "*" and any character whose Unicode name says asterisk."""
    return [c for c in s if c in "*＊﹡" or "ASTERISK" in unicodedata.name(c, "")]
# SHA-256 of each section text the worked examples in out/forms were built from (their "sources")
BUILT_FROM = {
    "va-foia-request": {"2.2-3704": "5ceba789d92d41064073d09218834643f5bff43f3fcfb95643ee8d33c1256754"},
    "ca-bpc-485-hearing-request": {
        "Cal. BPC § 476": "3aa4d717ee335ab53e81b580101409617de1691afbeea0c75fe8fede2bb40797",
        "Cal. BPC § 480": "4c38fca14eaa35ab72935671504b3888239f8e6e4ab445a00207c8745e9d4e94",
        "Cal. BPC § 481": "490cf02ceaa31ed42a1881b241399c75e2144c576bb4adaea2c114253cd4ab64",
        "Cal. BPC § 482": "0299d73ee37bb76f2d33adf0318fae013be86e318bf5a7207adba68e45d294e7",
        "Cal. BPC § 485": "58798ccecfdc62f7a764b98001c04549ecc977bfeb839824ec8cfcb423ea9c35",
        "Cal. BPC § 486": "7dad01914d1038a92688ef29fccf92a508ac8e858beb92be2ce9a6907d5fa385",
        "Cal. BPC § 487": "a8ea880a0567b037fabf4bbfd883e1f5988f76644a6665cbf2e332eda8ffd618"},
}


def norm(s: str) -> str:
    """The test's own normalisation, independent of draft.norm: whitespace and curly quotation marks only."""
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    return re.sub(r"\s+", " ", s.replace(" ", " ")).strip()


def fixture_text(state: str, ref: str):
    """The section's text from fixtures/statutes/<state>_sections.json, or None when the fixture lacks it."""
    path = STATUTES / f"{state}_sections.json"
    if not path.exists():
        return None
    number = ref.rsplit("§", 1)[-1].strip()
    code = ref.rsplit("§", 1)[0].strip() if "§" in ref else None
    for s in json.loads(path.read_text(encoding="utf-8"))["sections"]:
        if s["section_number"] == number and (code is None or s["citation"].startswith(code)):
            return s["text"]
    return None


def snapshot_text(spec_id: str, ref: str):
    """The text the worked example in out/forms/ was built from (taken from the open-us-law store)."""
    path = OUT / f"{spec_id}.json"
    if not path.exists():
        return None
    return next((s["text"] for s in json.loads(path.read_text(encoding="utf-8"))["sources"] if s["ref"] == ref),
                None)


def store_text(state: str, ref: str):
    try:
        from lexflow.ask import index as I
        if not I.ready(state):
            return None
        from lexflow.municipal import statutes
        return statutes.section_texts(state, [ref])[0].text
    except Exception:  # noqa: BLE001 - no local store here
        return None


def texts_for(spec: D.Spec) -> dict[str, dict]:
    """Section texts for a spec: the statute fixture first; for sections the fixture does not hold (California's
    Bus. & Prof. Code §§ 476-487 are not in ca_sections.json), the worked example's snapshot, then the store."""
    out = {}
    for ref in spec.sections:
        for origin, text in (("fixture", fixture_text(spec.state, ref)), ("snapshot", snapshot_text(spec.id, ref)),
                             ("store", store_text(spec.state, ref))):
            if text is not None:
                out[ref] = {"text": text, "origin": origin}
                break
        else:
            pytest.skip(f"no text for {ref}: not in fixtures/statutes, out/forms or a local store")
    return out


@pytest.fixture(scope="module")
def reg():
    return R.registry()


# ------------------------------------------------------------------------------------------------- registry
def test_every_step_reference_matches_its_curated_file(reg):
    assert reg.check_steps() == []


def test_step_file_key_reads_both_layouts():
    assert R.step_file_key("curated/va/records.json") == ("va", "records")
    assert R.step_file_key("curated_ask/record_sealing/ca.json") == ("ca", "record_sealing")
    assert R.step_file("tx", "court_debt") == "curated_ask/court_debt/tx.json"
    with pytest.raises(ValueError):
        R.step_file_key("fixtures/forms/forms.json")


def test_forms_for_a_step_come_exact_first(reg):
    forms = reg.forms_for_step("va", "record_sealing", "file_petition")
    assert [(f["id"], f["match"]) for f in forms] == [
        ("va-cc-1201", "exact"), ("va-cc-1201a", "partial"), ("va-cc-1203", "related")]
    assert forms[0]["form_number"] == "CC-1201" and forms[0]["fillable"] is True
    assert [f["id"] for f in reg.forms_for_step("va", "record_sealing", "file_petition", matches=("exact",))] == [
        "va-cc-1201"]


def test_virginia_records_request_has_a_sample_letter_but_no_form(reg):
    forms = reg.forms_for_step("va", "records", "submit_request")
    assert [f["id"] for f in forms] == ["va-foia-request-letter"]
    assert forms[0]["kind"] == "sample_letter"
    assert not reg.has_official_form("va", "records", "submit_request")
    note = reg.no_form_for_step("va", "records", "submit_request")
    assert note["statute"] == "Va. Code § 2.2-3704(A)-(B)"
    assert reg.has_official_form("va", "record_sealing", "file_petition")
    assert not reg.has_official_form("dc", "records", "submit_request")      # a portal, not a paper form


def test_lookup_follows_the_step_file_not_the_forms_process(reg):
    # BCIA 8016RR (a request for one's own record) is filed under record sealing; it is linked, as related only,
    # to the evidence step of the licence-conviction model too
    assert reg.form("ca-doj-bcia-8016rr")["process"] == "record_sealing"
    forms = reg.forms_for_step("ca", "license_conviction", "submit_rehab_evidence")
    assert [(f["id"], f["match"]) for f in forms] == [("ca-doj-bcia-8016rr", "related")]
    assert reg.forms_for_step("ca", "license_conviction", "submit_rehab_evidence", matches=("exact", "partial")) == []


def test_the_fixture_records_printed_revisions_and_redirects(reg):
    printed = {"va-cc-1201": "07/26", "va-dpor-a406-01predet": "V2, 08/20/2026",
               "ca-jc-cr-180": "Rev. January 1, 2024", "ca-jc-cr-181": "Rev. January 1, 2024",
               "ca-jc-cr-409": "Rev. January 1, 2024", "ca-jc-cr-410": "New January 1, 2019",
               "ca-doj-bcia-8016rr": "rev. 03/2024", "dc-dlc-1": "Ver. 8, October 2022"}
    for fid, rev in printed.items():
        assert reg.form(fid)["revision"] == rev, fid
        assert not reg.form(fid).get("revision_note"), fid
    # revisions the 2026-10-10 re-check could not find printed in the file carry a note saying so
    for fid in ("md-cc-dc-cr-072a", "tx-sos-205", "ny-doccs-crd-cgc-application"):
        assert reg.form(fid)["revision"] and reg.form(fid)["revision_note"], fid
        assert R.summary(reg.form(fid))["revision_note"] == reg.form(fid)["revision_note"]
    for fid in ("ca-jc-cr-180", "ca-jc-cr-181", "ca-jc-cr-409", "ca-jc-cr-410"):
        final = reg.form(fid)["verification"]["final_url"]
        assert final.startswith("https://courts.ca.gov/sites/default/files/courts/default/2024-11/"), fid
        assert R.summary(reg.form(fid))["final_url"] == final
        assert R.summary(reg.form(fid))["url"] == reg.form(fid)["url"]          # pages keep the publisher's URL
    assert "own criminal record" in reg.form("ca-doj-bcia-8016rr")["notes"]
    assert "not a form for sending evidence" in reg.form("ca-doj-bcia-8016rr")["notes"]


def test_a_step_with_no_form_has_a_note_and_a_draft(reg):
    assert reg.forms_for_step("ca", "license_conviction", "request_hearing") == []
    note = reg.no_form_for_step("ca", "license_conviction", "request_hearing")
    assert "485(b)" in note["statute"]
    assert D.spec_for_step("ca", "license_conviction", "request_hearing").id == "ca-bpc-485-hearing-request"
    assert reg.forms_for_step("zz", "records", "submit_request") == []
    assert reg.no_form_for_step("zz", "records", "submit_request") is None


def test_forms_that_serve_no_modelled_step_are_listed(reg):
    assert "va-dc-495" in [f["id"] for f in reg.unlinked_forms("va", "records")]
    va_records = [f["id"] for f in reg.forms_for_state("va", "records")]
    assert set(va_records) == {"va-foia-request-letter", "va-dc-495"}


def test_forms_for_a_curated_model(reg):
    by_step = {s["id"]: s for s in reg.forms_for_model("curated/va/records.json")}
    doc = json.loads((ROOT / "curated/va/records.json").read_text(encoding="utf-8"))
    assert set(by_step) == {s["id"] for s in doc["facts"]["steps"]}
    assert by_step["submit_request"]["forms"][0]["id"] == "va-foia-request-letter"
    assert by_step["submit_request"]["draft"] == "va-foia-request"
    assert by_step["submit_request"]["no_form"]["statute"].startswith("Va. Code § 2.2-3704")
    ask = json.loads((ROOT / "curated_ask/license_conviction/ca.json").read_text(encoding="utf-8"))
    steps = {s["id"]: s for s in reg.forms_for_model(ask)}
    assert steps["request_hearing"]["forms"] == [] and steps["request_hearing"]["no_form"] is not None
    assert steps["request_hearing"]["draft"] == "ca-bpc-485-hearing-request"
    assert [f["id"] for f in steps["submit_rehab_evidence"]["forms"]] == ["ca-doj-bcia-8016rr"]


def test_forms_for_a_compiled_model(reg):
    from lexflow.extract.compile import compile_facts
    from lexflow.extract.schema import LegalProcessFacts
    from lexflow.ir import SectionText
    doc = json.loads((ROOT / "curated/va/records.json").read_text(encoding="utf-8"))
    text = SectionText(section="2.2-3704", title="Public records", code="Code of Virginia", jurisdiction="va",
                       text=fixture_text("va", "2.2-3704"), url="https://law.lis.virginia.gov/vacode/2.2-3704/")
    model = compile_facts(LegalProcessFacts.model_validate(doc["facts"]), model_id="va-records", jurisdiction="va",
                          jurisdiction_name="Virginia", code="Code of Virginia", text=text)
    steps = {s["id"]: s for s in reg.forms_for_model(model)}
    # the requester's filing compiles to a message catch event in the public body's pool, under the step's id
    assert steps["submit_request"]["kind"] == "intermediateCatchEvent"
    assert steps["submit_request"]["forms"][0]["id"] == "va-foia-request-letter"
    assert steps["submit_request"]["draft"] == "va-foia-request"


def test_setup_status_follows_the_fixtures_rule(reg):
    today = date(2026, 10, 10)
    st = reg.setup_status(today=today)
    forms = reg.data["forms"]
    assert st["status"] == "partial"                      # ilsos.gov timed out, so one link waits for a recheck
    assert st["stale"] == ["il-sos-llc-5-5"]
    assert st["total"] == sum(1 for f in forms if f.get("url"))
    assert st["detail"].startswith(f"{len(forms)} forms for ")
    assert "1 link to recheck" in st["detail"]
    assert reg.setup_status(states=["va"], today=today)["status"] == "done"   # robots.txt refusal counts as checked
    assert reg.setup_status(states=["va"], today=date(2027, 3, 1))["status"] == "partial"   # older than 90 days
    assert reg.setup_status(states=["zz"], today=today)["status"] == "optional"
    unchecked = json.loads(json.dumps(reg.data))
    for f in unchecked["forms"]:
        f["verification"] = {}
    assert R.Registry(unchecked).setup_status(today=today)["status"] == "todo"
    assert reg.setup_entry()["id"] == "forms" and reg.setup_entry()["needs"] == ["build"]


# ---------------------------------------------------------------------------------------------------- drafts
@pytest.fixture(scope="module", params=sorted(D.SPECS))
def built(request):
    spec = D.SPECS[request.param]
    texts = texts_for(spec)
    d = D.build(spec, {ref: t["text"] for ref, t in texts.items()}, as_of="2026-10-10")
    return spec, texts, d


def test_every_element_cites_its_section_and_quotes_it(built):
    spec, texts, d = built
    assert d["elements"]
    for e in d["elements"]:
        assert e["section"] in spec.sections
        assert e["citation"].startswith(spec.citations[e["section"]]), e["id"]
        if e["subsection"]:
            assert e["citation"].endswith("".join(f"({p})" for p in e["subsection"].split("."))), e["id"]
        assert e["quote"].strip(), e["id"]
        assert norm(e["quote"]) in norm(texts[e["section"]]["text"]), (e["id"], texts[e["section"]]["origin"])
        assert D.locate(texts[e["section"]]["text"], e["quote"], e["subsection"]) is None, e["id"]


def test_required_and_duty_elements_quote_mandatory_words(built):
    spec, texts, d = built
    for e in d["elements"]:
        if e["level"] == "required":
            assert re.search(r"\b(shall|must|unless|only if)\b", e["quote"], re.I), e["id"]
        if e["level"] == "if_asked":
            assert re.search(r"\bmay require\b", e["quote"], re.I), e["id"]
        if e["level"] == "duty":
            assert re.search(r"\b(shall|must)\b", e["quote"], re.I), e["id"]
    for el in spec.elements:
        if el.level in ("required", "if_asked", "duty"):
            assert D.bearer(spec, el, texts[el.section]["text"]) is None, el.id
    assert any(e["level"] == "required" for e in d["elements"])


def _element_texts(e: dict):
    yield (e["letter"] or "").replace("{quote}", "")
    yield e["help"] or ""
    yield e["label"]
    yield e["condition"] or ""
    for f in e["fields"]:
        yield f["label"]
        yield f["placeholder"]
        yield from f["options"]
    for f in e["forms"]:
        yield f["role"]


def test_the_letter_states_no_requirement_outside_a_quote(built):
    spec, _, d = built
    for e in d["elements"]:
        for txt in _element_texts(e):
            assert not asterisks(txt), (e["id"], txt)
            assert txt.isascii() or not re.search(r"[^\W\d_]", re.sub(r"[A-Za-zÀ-ɏ]", "", txt)), txt
            for m in OBLIGATION.finditer(txt):
                # plain levels state no obligation at all; the others only one their own quote states
                assert e["level"] in ("required", "if_asked", "duty"), (e["id"], txt)
                assert re.search(r"\b" + m[0] + r"\b", e["quote"], re.I), (e["id"], txt)
    # the spec's own texts on the pages state none at all
    spec_texts = [d["title"], d["summary"], d["scope"], spec.subject, spec.salutation, spec.closing]
    spec_texts += [g["title"] for g in d["related"]]
    spec_texts += [(d["no_form_note"] or {}).get("note") or ""]
    for txt in spec_texts:
        assert not OBLIGATION.search(txt) and not asterisks(txt), txt


def test_no_field_has_a_default_value(built):
    _, _, d = built
    for e in d["elements"]:
        for f in e["fields"]:
            assert f["default"] in (None, False, ""), (e["id"], f["name"])
    page = D.render_form(d)
    assert not re.search(r"<input[^>]*\schecked", page)   # no box ticked and no option chosen for the person
    assert not re.search(r"<option[^>]*\sselected", page)


def test_the_letter_is_made_of_elements_only(built):
    spec, _, d = built
    ids = {e["id"] for e in d["elements"]}
    page = D.render_letter(d)
    body = page.split("<div id=\"letter-body\">", 1)[1].split("</div>", 1)[0]
    paras = re.findall(r"<p\b[^>]*>", body)
    tagged = re.findall(r"<p data-element=\"([^\"]+)\"", body)
    assert len(paras) == len(tagged) == len(spec.layout)
    assert set(tagged) <= ids | SKELETON
    assert {e["id"] for e in d["elements"] if e["letter"]} <= set(tagged)
    # the fillable page builds the same letter in the browser, from the same layout and elements
    data = json.loads(re.search(r"<script type=\"application/json\" id=\"draft-data\">(.*?)</script>",
                                D.render_form(d), re.S)[1])
    assert data["letter"]["layout"] == list(spec.layout)
    assert [e["id"] for e in data["elements"]] == [e["id"] for e in d["elements"]]


def test_every_page_carries_the_banner_and_the_form_sends_nothing(built):
    _, _, d = built
    assert D.BANNER == ("Draft made by lexflow from the statute; not an official form and not legal advice; use "
                        "the official form if the agency has one")
    form, letter = D.render_form(d), D.render_letter(d)
    for page in (form, letter):
        assert D.BANNER in page
    assert form.count(D.BANNER) >= 2                       # on the page and on the printed letter
    assert "<form id=\"draft-form\"" in form and " action=" not in form and "method=" not in form
    for api in ("fetch(", "XMLHttpRequest", "sendBeacon", "localStorage", "sessionStorage", "indexedDB",
                "document.cookie", "<script src", "<link rel=\"stylesheet\""):
        assert api not in form, api


def _part(page: str, opening: str) -> str:
    """The HTML from an opening tag to the next part of the printed letter page."""
    rest = page.split(opening, 1)[1]
    for nxt in ("<div class=\"letter\">", "<section class=\"notes\">", "<p class=\"muted\">Made "):
        if nxt in rest and nxt != opening:
            rest = rest.split(nxt, 1)[0]
    return rest


def test_every_printed_sheet_carries_the_banner(built):
    _, _, d = built
    letter, form = D.render_letter(d), D.render_form(d)
    printed = f"<div class=\"letter-banner printonly\" role=\"note\">{D.BANNER}</div>"
    # each printed part starts a new sheet with the banner at its top: the scope and official forms, the letter,
    # the notes (on screen the banner above the page serves, so the first and last are print-only)
    first = _part(letter, "<div class=\"first-page\">")
    assert first.lstrip().startswith(printed) and "Official form first" in first
    assert _part(letter, "<div class=\"letter\">").lstrip().startswith(f"<div class=\"letter-banner\">{D.BANNER}")
    notes = _part(letter, "<section class=\"notes\">")
    assert notes.lstrip().startswith(printed) and "Notes for you" in notes
    assert ".first-page{break-after:page}" in letter and ".notes{break-before:page}" in letter
    assert ".printonly{display:none}" in letter and "@media print{" in letter
    assert re.search(r"@media print\{[^@]*\.printonly\{display:block\}", letter)
    # and a page-margin box repeats it on every sheet where the browser supports margin boxes
    for page in (letter, form):
        assert f"@page{{@top-center{{content:\"{D.BANNER}\";" in page
    assert "<div class=\"letter\"><div class=\"letter-banner\">" + D.BANNER in form   # the form page prints the letter


def test_pages_send_no_referrer_and_links_open_safely(built):
    # rule 10: no referrer leaves the page, and every outbound link is noopener noreferrer
    _, _, d = built
    for page in (D.render_form(d), D.render_letter(d), D.render_index([d])):
        assert "<meta name=\"referrer\" content=\"no-referrer\">" in page
        links = re.findall(r"<a\s[^>]*>", page)
        outbound = [a for a in links if re.search(r"href=\"https?://", a)]
        for a in outbound:
            assert "rel=\"noopener noreferrer\"" in a, a
        assert all(re.search(r"href=\"[\w.-]+\.(html|json)\"", a) for a in links if a not in outbound), links
    assert any("https://" in a for a in re.findall(r"<a\s[^>]*>", D.render_form(d)))


def test_official_alternatives_are_listed_first(built):
    spec, _, d = built
    reg = R.registry()
    assert d["official"] == reg.forms_for_step(spec.state, spec.question, spec.step)
    assert d["no_form_note"] == reg.no_form_for_step(spec.state, spec.question, spec.step)
    page = D.render_form(d)
    assert page.index("Official form first") < page.index("What goes in the letter")
    letter = D.render_letter(d)
    assert letter.count("Official form first") == 1
    assert letter.index("Official form first") < letter.index("<div class=\"letter\">") < letter.index(
        "id=\"letter-body\"")
    # printed, the official box and the scope take the first page and the letter starts on the next
    first = letter.split("<div class=\"first-page\">", 1)[1].split("<div class=\"letter\">", 1)[0]
    assert "Official form first" in first and ".first-page{break-after:page}" in letter
    for e in d["elements"]:
        for f in e["forms"]:
            assert reg.form(f["id"]) is not None
            assert f["match"] in ("partial", "related") and f["role"], (e["id"], f["id"])


def test_the_california_draft_lists_the_dismissal_petition():
    d = D.build(D.CA_HEARING, {ref: t["text"] for ref, t in texts_for(D.CA_HEARING).items()})
    related = [f["id"] for g in d["related"] for f in g["forms"]]
    assert "ca-jc-cr-180" in related and "ca-jc-cr-181" in related
    dismissed = next(e for e in d["elements"] if e["id"] == "dismissed")
    assert [f["id"] for f in dismissed["forms"]] == ["ca-jc-cr-180", "ca-jc-cr-181"]
    assert next(e for e in d["elements"] if e["id"] == "hearing_request")["level"] == "required"


def _ca():
    return D.build(D.CA_HEARING, {ref: t["text"] for ref, t in texts_for(D.CA_HEARING).items()})


def _el(d: dict, element_id: str) -> dict:
    return next(e for e in d["elements"] if e["id"] == element_id)


def test_the_california_seven_year_sentence_quotes_both_branches_and_asserts_nothing():
    d = _ca()
    seven = _el(d, "seven_years")
    # both branches of § 480(a)(1)'s first sentence, not the first alone
    assert seven["quote"].startswith("The applicant has been convicted of a crime within the preceding seven years")
    assert "regardless of whether the applicant was incarcerated for that crime" in seven["quote"]
    assert "presently incarcerated or for which the applicant was released from incarceration within the " \
           "preceding seven years from the date of application" in seven["quote"]
    assert seven["citation"] == "Cal. Bus. & Prof. Code § 480(a)(1)"
    # the letter quotes the condition and the person states the facts: no claim that the condition is not met
    assert "not met" not in seven["letter"] and "not met" not in seven["label"]
    assert "subparagraphs (A) and (B)" in seven["letter"] and "{seven_years_facts}" in seven["letter"]
    assert "does not say whether the condition is met" in seven["help"]
    page = D.render_letter(d)
    para = re.search(r"<p data-element=\"seven_years\">(.*?)</p>", page, re.S)[1]
    assert "not met" not in para and "presently incarcerated" in para
    # the exceptions are quoted in full: (A), (B) and the licences (i)-(v) that (B) lists
    exc = _el(d, "seven_year_exceptions")
    assert exc["quote"].startswith("However, the preceding seven-year limitation shall not apply")
    for words in ("(A) The applicant was convicted of a serious felony", "(B) The applicant was convicted of a "
                  "financial crime", "(i) Chapter 6 (commencing with Section 6500)",
                  "(v) Division 4 (commencing with Section 10000)."):
        assert words in exc["quote"], words


def test_the_california_draft_says_which_licences_it_does_not_cover():
    d = _ca()
    excluded = _el(d, "excluded_licences")
    assert excluded["citation"] == "Cal. Bus. & Prof. Code § 476(a)"
    assert "nothing in this division shall apply" in excluded["quote"]
    for words in ("State Bar Act", "Alcoholic Beverage Control Act", "Gambling Control Act",
                  "This draft does not apply to those licences"):
        assert words in excluded["help"], words
    for words in ("State Bar Act", "Alcoholic Beverage Control Act", "Gambling Control Act", "§ 476(a)",
                  "does not apply to them", "§ 4202.6", "§ 5100.2", "(§§ 1687, 1958.1, 2660.5)"):
        assert words in d["scope"], words
    # § 4989.24(b) applies § 480's conditions, so the scope does not list it as a departure from § 480
    assert "Section 4989.24, in the Educational Psychologist Practice Act" in d["scope"]
    assert "its subdivision (b) applies the conditions for denial in § 480 to such a denial" in d["scope"]
    # both of § 4989.24(a)'s territorial reaches, not California alone
    assert "a conviction, in California, in another state or in a territory of the United States, of a crime " \
           "involving sexual abuse of children" in d["scope"]
    assert "subject to that registration or the equivalent in another state or territory" in d["scope"]
    assert "depart" not in d["scope"] and "4989.24)" not in d["scope"]
    # the cannabis provision, in the statute's words
    assert "§ 26057(b)(2) lets the Department of Cannabis Control deny" in d["scope"]
    assert "Chapter 2 of Division 1.5 (commencing with § 480), “except as otherwise specified” in § 26057 and " \
           "§ 26059" in d["scope"]
    # the scope is on both pages, and on the printable letter before the letter
    letter = D.render_letter(d)
    assert letter.index("Gambling Control Act") < letter.index("<div class=\"letter\">")
    assert "Gambling Control Act" in D.render_form(d)


def test_the_california_scope_follows_the_practice_act_texts():
    # the scope's practice-act sentences, against the statute store (they are not among the spec's sections, so
    # check() does not quote-check them)
    refs = ("4202.6", "5100.2", "1687", "1958.1", "2660.5", "4989.10", "4989.24", "26001", "26057")
    texts = {n: store_text("ca", f"Cal. BPC § {n}") for n in refs}
    if any(t is None for t in texts.values()):
        pytest.skip("no local open-us-law store for California here")
    t = {n: norm(v) for n, v in texts.items()}
    assert t["4202.6"].startswith("Notwithstanding Section 480, the board may deny")
    assert "In addition to the grounds for the denial of a license pursuant to Section 480" in t["5100.2"]
    assert "The seven-year limitation as described in paragraph (1) of subdivision (a) of Section 480 shall not " \
           "apply." in t["5100.2"]
    for n in ("1687", "1958.1"):
        assert "required to register as a sex offender pursuant to Section 290 of the Penal Code" in t[n], n
        assert "shall deny an application by the individual for licensure" in t[n] and "(b) This section shall " \
               "not apply to any of the following:" in t[n], n
    assert t["2660.5"].startswith("The board shall deny a physical therapist license") and \
        "required to register pursuant to Section 290 of the Penal Code" in t["2660.5"] and \
        "This section does not apply to an applicant" in t["2660.5"]
    assert "Educational Psychologist Practice Act" in t["4989.10"]
    assert "sexual abuse of children or who is required to register pursuant to Section 290" in t["4989.24"]
    assert "convicted of a crime in this or any other state or in a territory of the United States" in t["4989.24"]
    assert "Section 290 of the Penal Code or the equivalent in another state or territory." in t["4989.24"]
    assert "(b) A denial issued pursuant to this section shall comply with the conditions for denial specified " \
           "in Section 480." in t["4989.24"]
    assert "“Department” means the Department of Cannabis Control".translate(D._QUOTES) in t["26001"]
    assert "The department may deny the application for licensure or renewal of a state license" in t["26057"]
    assert "(2) Conduct that constitutes grounds for denial of licensure under Chapter 2 (commencing with Section " \
           "480) of Division 1.5, except as otherwise specified in this section and Section 26059." in t["26057"]


def test_the_california_discipline_condition_carries_both_qualifiers():
    d = _ca()
    help_ = _el(d, "only_if")["help"]
    # § 480(a)(2): discipline based on a dismissed conviction is no basis, and older discipline counts only for
    # the conduct the last sentence names
    assert "not a basis for denial if it was based on a conviction dismissed under Penal Code § 1203.4, 1203.4a, " \
           "1203.41, 1203.42 or 1203.425, or a comparable dismissal or expungement" in help_
    assert "Discipline older than seven years can be a ground only if it was for conduct that, by a California " \
           "physician and surgeon, would have been sexual abuse, misconduct or relations with a patient under " \
           "§ 726, or sexual exploitation under § 729(a)" in help_
    disc = _el(d, "formal_discipline")
    assert disc["citation"] == "Cal. Bus. & Prof. Code § 480(a)(2)" and disc["level"] == "notice"
    for words in ("The applicant has been subjected to formal discipline by a licensing board in or outside "
                  "California", "However, prior disciplinary action by a licensing board within the preceding "
                  "seven years shall not be the basis for denial", "Formal discipline that occurred earlier than "
                  "seven years preceding the date of application may be grounds for denial of a license only if",
                  "sexual exploitation as defined in subdivision (a) of Section 729."):
        assert words in disc["quote"], words


def test_the_california_notes_cover_the_hearing_and_reapplication_duties():
    d = _ca()
    cites = {e["id"]: (e["level"], e["citation"]) for e in d["elements"]}
    assert cites["hearing_within"] == ("duty", "Cal. Bus. & Prof. Code § 487")
    assert "within 90 days" in _el(d, "hearing_within")["quote"]
    assert cites["reapply_evidence"] == ("notice", "Cal. Bus. & Prof. Code § 486(b)")
    assert cites["rehab_criteria"] == ("duty", "Cal. Bus. & Prof. Code § 486")
    assert "criteria relating to rehabilitation formulated under Section 482" in _el(d, "rehab_criteria")["quote"]
    # § 481(b) describes the criteria; its subject is "Criteria", not the board, so it is a note, not a duty
    assert cites["substantial_relation"] == ("notice", "Cal. Bus. & Prof. Code § 481(b)")
    assert "The nature and gravity of the offense." in _el(d, "substantial_relation")["quote"]
    assert {e["id"] for e in d["elements"] if e["in_letter"]} == {
        e for e in D.CA_HEARING.layout if not e.startswith("@")}


def test_bcia_8016rr_is_labelled_as_a_record_request_not_an_evidence_form():
    d = _ca()
    for element_id in ("evidence", "record_copy"):
        (f,) = _el(d, element_id)["forms"]
        assert (f["id"], f["match"]) == ("ca-doj-bcia-8016rr", "related")
        assert "copy of your own criminal record" in f["role"] and "not a form for sending evidence" in f["role"]
    for page in (D.render_form(d), D.render_letter(d)):
        assert "Official form:</strong>" not in page and "Official form: " not in page
        for block in re.findall(r"<p class=\"forms\">(.*?)</p>", page, re.S):
            if "BCIA 8016RR" in block:
                assert block.startswith("<strong>Related official form:</strong>") and "related match" in block
                assert "not a form for sending evidence" in block
    # an element may not promote the form beyond the fixture's match, nor call any element form exact
    ca = {ref: t["text"] for ref, t in texts_for(D.CA_HEARING).items()}
    for match, words in (("partial", "stronger than the fixture"), ("exact", "is linked as 'exact'")):
        bad = _with(D.CA_HEARING, "evidence", forms=(D.FormLink("ca-doj-bcia-8016rr", match, "x"),))
        assert any("evidence" in p and words in p for p in D.check(bad, ca)), match
    bad = _with(D.CA_HEARING, "evidence", forms=(D.FormLink("ca-doj-bcia-8016rr", "related", " "),))
    assert any("does not say what the form is" in p for p in D.check(bad, ca))


def test_the_virginia_draft_wording_follows_the_subsections():
    d = D.build(D.VA_FOIA, _va_texts())
    deposit = _el(d, "deposit")
    assert "likely to exceed $200" in deposit["label"] and "over $200" not in deposit["label"]
    assert "up to the amount of that advance determination" in deposit["help"]
    ext = _el(d, "extension")
    assert ext["citation"] == "Va. Code § 2.2-3704(B)(4)" and "60 work days" in ext["quote"]
    assert "60 work days" in ext["help"] and "criminal investigative files" in ext["help"]
    email = _el(d, "email")
    assert "electronic database" in email["letter"] and "electronic database" in email["help"]
    assert "capability" in email["quote"]
    assert _el(d, "search_notice")["level"] == "duty" and _el(d, "search_notice")["citation"].endswith("(F)")
    assert "Prior to conducting a search for records" in _el(d, "search_notice")["quote"]
    assert _el(d, "court_extension")["citation"].endswith("(C)")
    assert "petition the appropriate court" in _el(d, "court_extension")["quote"]
    assert "pauses the response time" in _el(d, "cost_estimate")["help"]


# ---------------------------------------------------------------------------------------- the rules hold
def _va_texts():
    return {ref: t["text"] for ref, t in texts_for(D.VA_FOIA).items()}


def _with(spec, element_id, **changes):
    els = tuple(dataclasses.replace(e, **changes) if e.id == element_id else e for e in spec.elements)
    return dataclasses.replace(spec, elements=els)


def test_a_misquote_is_refused():
    bad = _with(D.VA_FOIA, "records", quote="A request for public records shall identify the records precisely.")
    with pytest.raises(D.DraftError, match="quote not found"):
        D.build(bad, _va_texts())


def test_a_quote_under_the_wrong_subsection_is_refused():
    bad = _with(D.VA_FOIA, "records", subsection="C")
    with pytest.raises(D.DraftError, match=r"not under subsection \(C\)"):
        D.build(bad, _va_texts())


def _plus(spec, *elements, letter=False):
    spec = dataclasses.replace(spec, elements=spec.elements + elements)
    if letter:
        spec = dataclasses.replace(spec, layout=spec.layout + tuple(e.id for e in elements))
    return spec


def test_an_invented_requirement_is_refused():
    phone = D.Element("phone", "right", "Phone number", "2.2-3704", "A",
                      "at the option of the requester", fields=(D.Field("phone", "Phone"),),
                      help="You must give a phone number.")
    problems = D.check(_plus(D.VA_FOIA, phone), _va_texts())
    assert any("phone" in p and "obligation" in p for p in problems)
    # the option to inspect is not a duty to choose: the quote's "shall" binds the custodian, not the requester
    req = _with(D.VA_FOIA, "access", level="required")
    assert any("access" in p and "does not put the mandatory words on the person" in p
               for p in D.check(req, _va_texts()))
    req = _with(D.VA_FOIA, "access", level="required", quote="at the option of the requester")
    assert any("access" in p and "required element must quote" in p for p in D.check(req, _va_texts()))


def test_a_requirement_in_a_field_label_or_placeholder_is_refused():
    # the verifier's case: a 'right' element whose field label and placeholder add a requirement
    phone = D.Element("phone", "right", "Phone number", "2.2-3704", "A", "at the option of the requester",
                      fields=(D.Field("phone", "Phone number (required)", placeholder="you have to give one"),))
    problems = D.check(_plus(D.VA_FOIA, phone), _va_texts())
    assert any("field phone label states an obligation ('required')" in p for p in problems)
    assert any("field phone placeholder states an obligation ('have to')" in p for p in problems)
    assert any("phone" in p and "shares no word with its quote" in p for p in problems)
    # in a required element, a requirement word must be one its quote uses
    records = next(e for e in D.VA_FOIA.elements if e.id == "records")
    loud = dataclasses.replace(records, fields=(dataclasses.replace(records.fields[0], label="Records (required)"),))
    bad = dataclasses.replace(D.VA_FOIA, elements=tuple(loud if e.id == "records" else e for e in D.VA_FOIA.elements))
    assert any("records" in p and "says 'required', which its quote does not" in p
               for p in D.check(bad, _va_texts()))
    # an option of a choice is checked too
    bad = _with(D.VA_FOIA, "access", fields=(D.Field("access", "I would like to", "radio",
                                                     options=("inspect the records", "copies, as required")),))
    assert any("field access option states an obligation" in p for p in D.check(bad, _va_texts()))


def test_an_element_resting_on_an_unrelated_sentence_is_refused():
    # the verifier's case: a required 'purpose' resting on the custodian's duty to preserve records
    purpose = D.Element("purpose", "required", "Purpose of the request", "2.2-3704", "A",
                        "shall take all necessary precautions for their preservation",
                        fields=(D.Field("purpose", "Purpose of the request"),), letter="My purpose: {purpose}")
    problems = D.check(_plus(D.VA_FOIA, purpose, letter=True), _va_texts())
    assert any("purpose" in p and "does not put the mandatory words on the person" in p for p in problems)
    assert any("purpose" in p and "label 'Purpose of the request' shares no word" in p for p in problems)
    assert any("field purpose shares no word with its quote" in p for p in problems)
    # a duty of the public body is not a requirement of the requester
    estimate = D.Element("estimate", "required", "Cost estimate", "2.2-3704", "F",
                         "The public body shall provide the requester with a cost estimate if requested.")
    assert any("estimate" in p and "on the person" in p for p in D.check(_plus(D.VA_FOIA, estimate), _va_texts()))
    # and a requirement of the requester is not a duty of the public body
    duty = D.Element("records_duty", "duty", "Records identified", "2.2-3704", "B",
                     "A request for public records shall identify the requested records with reasonable specificity.")
    assert any("records_duty" in p and "on the other side" in p for p in D.check(_plus(D.VA_FOIA, duty), _va_texts()))
    # a right whose field has nothing to do with its quote
    bad = _with(D.VA_FOIA, "medium", fields=(D.Field("phone", "Phone number"),), letter="Phone: {phone}",
                when="phone")
    assert any("field phone shares no word with its quote" in p for p in D.check(bad, _va_texts()))


def _ca_texts():
    return {ref: t["text"] for ref, t in texts_for(D.CA_HEARING).items()}


def _refused(spec, texts, element_id, words):
    problems = D.check(spec, texts)
    assert any(p.startswith(f"{spec.id}/{element_id}:") and words in p for p in problems), problems
    with pytest.raises(D.DraftError):
        D.build(spec, texts)


ON_THE_PERSON = "does not put the mandatory words on the person as a duty"


def test_a_required_element_rests_on_a_duty_of_the_person():
    # the re-check's cases, with the real section text: none of these sentences puts a duty on the person
    ca, va = _ca_texts(), _va_texts()
    voluntary = D.Element(
        "mitigating", "required", "Mitigating information about your criminal history", D.BPC["480"], "f.2",
        "However, a board may request mitigating information from an applicant regarding the applicant’s criminal "
        "history for purposes of determining substantial relation or demonstrating evidence of rehabilitation, "
        "provided that the applicant is informed that disclosure is voluntary and that the applicant’s decision not "
        "to disclose any information shall not be a factor in a board’s decision to grant or deny an application "
        "for licensure.",
        fields=(D.Field("mitigating_information", "Mitigating information about your criminal history",
                        "textarea"),), letter="{mitigating_information}")
    bad = _plus(D.CA_HEARING, voluntary, letter=True)
    _refused(bad, ca, "mitigating", ON_THE_PERSON)
    _refused(bad, ca, "mitigating", "says the act is voluntary or optional ('voluntary')")
    # the possessive "applicant's decision ... shall not" alone is not a duty of the applicant either
    short = dataclasses.replace(voluntary, quote="the applicant’s decision not to disclose any information shall not "
                                                 "be a factor in a board’s decision to grant or deny an application "
                                                 "for licensure")
    _refused(_plus(D.CA_HEARING, short, letter=True), ca, "mitigating", ON_THE_PERSON)
    # § 487 is the board's duty; "unless the applicant shall request ..." is an exception to it
    s487 = ("If a hearing is requested by the applicant, the board shall conduct such hearing within 90 days from the "
            "date the hearing is requested unless the applicant shall request or agree in writing to a postponement "
            "or continuance of the hearing.")
    for quote in (s487, "unless the applicant shall request or agree in writing to a postponement or continuance "
                        "of the hearing"):
        hearing = D.Element("hearing_90", "required", "A hearing within 90 days", D.BPC["487"], None, quote)
        _refused(_plus(D.CA_HEARING, hearing), ca, "hearing_90", ON_THE_PERSON)
    # Virginia's deemed denial and deemed withdrawal are consequences, not duties of the requester
    for element_id, sub, quote in (
            ("deemed_denial_req", "E", "Failure to respond to a request for records shall be deemed a denial of the "
                                       "request and shall constitute a violation of this chapter."),
            ("withdrawn_req", "F", "If the public body receives no response from the requester within 30 days of "
                                   "sending the cost estimate, the request shall be deemed to be withdrawn.")):
        el = D.Element(element_id, "required", "Request for records, and the cost estimate", "2.2-3704", sub, quote)
        _refused(_plus(D.VA_FOIA, el), va, element_id, ON_THE_PERSON)
    # the drafts' own required elements still pass: each is a duty of the person, or the person's request
    for spec, texts in ((D.VA_FOIA, va), (D.CA_HEARING, ca)):
        for el in spec.elements:
            if el.level == "required":
                assert D.bearer(spec, el, texts[el.section]) is None, el.id


def test_the_bearer_of_a_required_element_heads_the_subject():
    # the same rules on a made-up section, so each one is pinned on its own
    spec = dataclasses.replace(D.VA_FOIA, parties={"person": ("requester", "request"), "other": ("public body",)})
    text = ("A. The requester shall pay the fee. A request shall be made in writing. The requester's list shall be "
            "short. A copy shall be sent to the requester. The public body may request that the requester shall "
            "wait. The public body shall answer unless the requester shall agree otherwise. The requester shall not "
            "be charged. The requester shall be deemed to have asked. The requester shall have ten days. Unless the "
            "requester pays within ten days, the request lapses. Unless the requester pays, the public body keeps "
            "the records. Disclosure by the requester is voluntary, and the requester shall sign.\n\nB. Other.")

    def ok(quote):
        el = D.Element("x", "required", "x", "2.2-3704", "A", quote)
        return D.bearer(spec, el, text) is None

    assert ok("The requester shall pay the fee.")                      # the person heads the subject
    assert ok("A request shall be made in writing.")                   # the person's request heads it
    assert ok("Unless the requester pays within ten days, the request lapses.")   # a condition on the person
    assert not ok("The requester's list shall be short.")              # possessive
    assert not ok("A copy shall be sent to the requester.")            # after a preposition, and after the verb
    assert not ok("may request that the requester shall wait")         # a verb, then a subordinate clause
    assert not ok("The public body shall answer unless the requester shall agree otherwise.")
    assert not ok("unless the requester shall agree otherwise")        # an exception to the other side's duty
    assert not ok("The requester shall not be charged.")               # a prohibition protecting the person
    assert not ok("The requester shall be deemed to have asked.")      # a legal consequence
    assert not ok("The requester shall have ten days.")                # a grant
    assert not ok("Unless the requester pays, the public body keeps the records.")   # consequence on the other side
    el = D.Element("x", "required", "Signature", "2.2-3704", "A",
                   "Disclosure by the requester is voluntary, and the requester shall sign.")
    problems = D.check(_plus(spec, el), {"2.2-3704": text})
    assert any("/x:" in p and "voluntary" in p for p in problems)


def test_level_shifted_variants_are_refused():
    # the same sentences moved to another level, or turned around, on a made-up section
    spec = dataclasses.replace(D.VA_FOIA, parties={"person": ("requester", "request"), "other": ("public body",)})
    text = ("A. A request shall be made in writing. A request shall be answered by the public body. A request to "
            "the public body shall name the records. The requester, if the public body asks, shall pay. The public "
            "body shall have ten more days. The public body shall answer. The public body shall not charge the "
            "requester. Unless the requester objects, the request is granted. Unless the requester answers, the "
            "request is withdrawn. The public body may request a fee from the requester. The public body may "
            "require the requester to pay.\n\nB. Other.")

    def ok(level, quote):
        return D.bearer(spec, D.Element("x", level, "x", "2.2-3704", "A", quote), text) is None

    assert ok("required", "A request shall be made in writing.")      # the person's own act, in the passive
    assert not ok("required", "A request shall be answered by the public body.")   # the other side's act
    assert ok("required", "The requester, if the public body asks, shall pay.")    # the subject, past the aside
    assert not ok("required", "Unless the requester objects, the request is granted.")   # no loss: an option
    assert ok("required", "Unless the requester answers, the request is withdrawn.")     # a loss: a requirement
    # a duty is the other side's: not the person's request, not a grant
    assert not ok("duty", "A request to the public body shall name the records.")
    assert not ok("duty", "The public body shall have ten more days.")
    assert ok("duty", "The public body shall answer.") and ok("duty", "The public body shall not charge the requester.")
    # if_asked rests on "may require" only: "may request" asks without requiring
    assert not ok("if_asked", "The public body may request a fee from the requester.")
    assert ok("if_asked", "The public body may require the requester to pay.")


def test_the_voluntary_disclosure_sentence_is_never_if_asked():
    ca = _ca_texts()
    el = D.Element("mitigating", "if_asked", "Mitigating information about your criminal history", D.BPC["480"],
                   "f.2", "However, a board may request mitigating information from an applicant regarding the "
                          "applicant’s criminal history for purposes of determining substantial relation or "
                          "demonstrating evidence of rehabilitation, provided that the applicant is informed that "
                          "disclosure is voluntary")
    bad = _plus(D.CA_HEARING, el)
    _refused(bad, ca, "mitigating", "an if_asked element must quote words such as")
    _refused(bad, ca, "mitigating", "says the act is voluntary or optional ('voluntary'), so the element cannot be "
                                    "'if_asked'")
    # Virginia's extra seven work days are a grant to the public body, not its duty
    va = _va_texts()
    ext = _with(D.VA_FOIA, "extension", level="duty")
    _refused(ext, va, "extension", "not a grant, a legal consequence or an exemption")


def test_context_and_notice_elements_add_no_fields():
    va = _va_texts()
    date_quote = "within five working days of receiving a request"
    # the re-check's cases: a phone or purpose field in a context element resting on the date rule
    for name, label in (("phone", "Phone number"), ("purpose", "Purpose of the request")):
        el = D.Element(name, "context", label, "2.2-3704", "B", date_quote, fields=(D.Field(name, label),),
                       letter=f"{{{name}}}")
        _refused(_plus(D.VA_FOIA, el, letter=True), va, name, f"field {name} of a context element shares no word")
        _refused(_plus(D.VA_FOIA, el, letter=True), va, name, f"the label of field {name} of a context element")
    # a notice carries no field and is not part of the letter; a duty carries no field either
    note = D.Element("phone", "notice", "Phone number", "2.2-3704", "B", date_quote,
                     fields=(D.Field("phone", "Phone number"),), letter="Phone: {phone}")
    _refused(_plus(D.VA_FOIA, note, letter=True), va, "phone", "a notice element is a note and carries no fields")
    _refused(_plus(D.VA_FOIA, note, letter=True), va, "phone", "a notice element is not part of the letter")
    bad = _with(D.VA_FOIA, "response_duty", fields=(D.Field("records_wanted", "Records you want provided"),))
    _refused(bad, va, "response_duty", "a duty element is a note and carries no fields")
    # the letter's own date and the sender's name need no quote support, by name, type and label only
    assert [f.name for e in D.SPECS["va-foia-request"].elements if e.level == "context" for f in e.fields] == [
        "date_sent", "custodian", "custodian_address"]
    dated = _with(D.VA_FOIA, "date", fields=(D.Field("date_sent", "Your phone number", "text"),))
    _refused(dated, va, "date", "field date_sent of a context element shares no word")
    # a context field naming the other side rests on a quote naming it
    assert not [p for p in D.check(D.VA_FOIA, va) if "/custodian:" in p]


@pytest.mark.parametrize("label", ["Your name and phone number", "Name, phone and date of birth",
                                   "Your name (and phone)"])
def test_the_sender_name_exemption_reads_the_whole_label(label):
    # the second re-check's case: an exempt field whose label also asks for something else
    ca = _ca_texts()
    applicant = next(e for e in D.CA_HEARING.elements if e.id == "applicant")
    bad = _with(D.CA_HEARING, "applicant", fields=(D.Field("name", label),) + applicant.fields[1:])
    _refused(bad, ca, "applicant", "field name of a context element shares no word with its quote")


def test_the_letter_date_exemption_reads_the_whole_field():
    va = _va_texts()
    for field in (D.Field("date_sent", "Date you send it and your date of birth", "date"),
                  D.Field("date_sent", "Date of birth", "date"),
                  # a placeholder or an option could ask for more, so an exempt field has neither
                  D.Field("date_sent", "Date you send it", "date", placeholder="and your phone number"),
                  D.Field("date_sent", "Date you send it", "date", options=("today", "phone"))):
        _refused(_with(D.VA_FOIA, "date", fields=(field,)), va, "date",
                 "field date_sent of a context element shares no word with its quote")
    # the drafts' own exempt fields hold only those words
    for spec in (D.VA_FOIA, D.CA_HEARING):
        exempt = [f for e in spec.elements if e.level == "context" for f in e.fields if D._letter_field(f)]
        assert [(f.name, f.label) for f in exempt] == (
            [("date_sent", "Date you send it")] + ([("name", "Your name")] if spec is D.CA_HEARING else []))


def _without_letter(spec, element_id, **changes):
    """The element taken out of the letter (no fields, no sentence, not in the layout), with the changes."""
    spec = _with(spec, element_id, fields=(), letter=None, when=None, **changes)
    return dataclasses.replace(spec, layout=tuple(x for x in spec.layout if x != element_id))


REQUIREMENTS = [("ca", "hearing_request"), ("ca", "dismissal_proof"), ("va", "records")]


@pytest.mark.parametrize("state, element_id", REQUIREMENTS)
def test_a_requirement_of_the_person_is_never_a_choice_context_or_note(state, element_id):
    # the second re-check's cases: each real requirement, with its real quote, put at a lower level
    spec, texts = (D.CA_HEARING, _ca_texts()) if state == "ca" else (D.VA_FOIA, _va_texts())
    el = next(e for e in spec.elements if e.id == element_id)
    assert D.passes(spec, el, texts[el.section], "required")
    for level in ("right", "context"):
        _refused(_with(spec, element_id, level=level), texts, element_id,
                 f"passes the 'required' test), so the element cannot be '{level}'")
    for level in ("notice", "duty"):
        _refused(_without_letter(spec, element_id, level=level), texts, element_id,
                 f"passes the 'required' test), so the element cannot be '{level}'")
    # nor may a requirement be left out of the letter
    _refused(_without_letter(spec, element_id), texts, element_id,
             "a required element is part of the letter, but it is not in the layout")


def test_what_the_other_side_may_require_is_never_a_choice_or_context():
    va = _va_texts()
    name_address = next(e for e in D.VA_FOIA.elements if e.id == "name_address")
    assert D.passes(D.VA_FOIA, name_address, va["2.2-3704"], "if_asked")
    for level in ("right", "context"):
        _refused(_with(D.VA_FOIA, "name_address", level=level), va, "name_address",
                 f"passes the 'if_asked' test), so the element cannot be '{level}'")
    _refused(_without_letter(D.VA_FOIA, "name_address"), va, "name_address",
             "an if_asked element is part of the letter, but it is not in the layout")
    # a note may tell of a demand the other side may make outside the request: (I), earlier unpaid bills, stays a
    # notice (it has no field and is not in the letter, and its help names no obligation)
    unpaid = next(e for e in D.VA_FOIA.elements if e.id == "unpaid")
    assert unpaid.level == "notice" and D.passes(D.VA_FOIA, unpaid, va["2.2-3704"], "if_asked")
    assert not [p for p in D.check(D.VA_FOIA, va) if "/unpaid:" in p]


def test_no_element_of_the_drafts_hides_a_requirement():
    # every element of both drafts, against the level tests: only required elements rest on a requirement, and
    # only name_address (if_asked) and unpaid (a notice) rest on what the other side may require
    found = {}
    for spec, texts in ((D.VA_FOIA, _va_texts()), (D.CA_HEARING, _ca_texts())):
        for e in spec.elements:
            for level in ("required", "if_asked"):
                if D.passes(spec, e, texts[e.section], level):
                    found[e.id] = (e.level, level)
            if e.level in ("required", "if_asked"):
                assert e.id in spec.layout, e.id
    assert found == {"records": ("required", "required"), "name_address": ("if_asked", "if_asked"),
                     "unpaid": ("notice", "if_asked"), "hearing_request": ("required", "required"),
                     "dismissal_proof": ("required", "required")}


def test_a_spec_without_parties_is_refused():
    bad = dataclasses.replace(D.VA_FOIA, parties={})
    assert "va-foia-request: the spec names no parties, so no element's level can be checked" in \
        D.check(bad, _va_texts())


def test_the_limits_of_rule_3_are_refused():
    # the second re-check's made-up sentences: none is a requirement of the person or a duty of the other side
    spec = dataclasses.replace(D.VA_FOIA, parties={"person": ("requester", "request"), "other": ("public body",)})
    text = ("A. The requester shall receive a copy of the records. The requester shall obtain a refund. Unless the "
            "requester agrees, the request shall not be denied. A request for public records that the public body "
            "shall answer within five days is valid. The public body or the requester shall decide. However, a "
            "public body shall not be required to create a new record. The public body shall not be obliged to "
            "answer. The requester and the public body shall agree on a date. The requester may ask for a hearing "
            "and shall pay the fee. The public body may charge a fee, but shall answer within five days.\n\nB. Other.")

    def ok(level, quote):
        return D.bearer(spec, D.Element("x", level, "x", "2.2-3704", "A", quote), text) is None

    assert not ok("required", "The requester shall receive a copy of the records.")    # a benefit
    assert not ok("required", "The requester shall obtain a refund.")
    assert not ok("required", "Unless the requester agrees, the request shall not be denied.")   # negated loss
    # the "shall" belongs to the public body in a relative clause, not to the request before it
    assert not ok("required", "A request for public records that the public body shall answer within five days is "
                              "valid.")
    assert not ok("duty", "A request for public records that the public body shall answer within five days is valid.")
    assert not ok("required", "The public body or the requester shall decide.")        # a joint subject
    assert not ok("duty", "The public body or the requester shall decide.")
    assert not ok("duty", "The requester and the public body shall agree on a date.")
    assert not ok("duty", "However, a public body shall not be required to create a new record.")   # exemptions
    assert not ok("duty", "The public body shall not be obliged to answer.")
    # a second verb of the same subject keeps its bearer
    assert ok("required", "The requester may ask for a hearing and shall pay the fee.")
    assert ok("duty", "The public body may charge a fee, but shall answer within five days.")


def test_a_mandatory_word_whose_subject_is_not_a_party_has_no_bearer():
    # § 480(f)(2): "the applicant's decision ... shall not be a factor". The party heading a subject before it is
    # "a board may request", which has its own verb, so it does not bear the later "shall"
    ca = _ca_texts()
    f2 = ("However, a board may request mitigating information from an applicant regarding the applicant’s criminal "
          "history for purposes of determining substantial relation or demonstrating evidence of rehabilitation, "
          "provided that the applicant is informed that disclosure is voluntary and that the applicant’s decision "
          "not to disclose any information shall not be a factor in a board’s decision to grant or deny an "
          "application for licensure.")
    el = D.Element("f2", "duty", "Mitigating information and the board's decision", D.BPC["480"], "f.2", f2)
    _refused(_plus(D.CA_HEARING, el), ca, "f2", "does not put the mandatory words on the other side")
    # while the same pattern with a second verb of the same subject, in the real Virginia text, is a duty
    va = _va_texts()
    for sub, quote in (("F", "a public body may make reasonable charges not to exceed its actual cost incurred in "
                             "accessing, duplicating, supplying, or searching for the requested records and shall "
                             "make all reasonable efforts to supply the requested records at the lowest possible "
                             "cost"),
                       ("G", "the public body may provide access to the exempt records if not otherwise prohibited "
                             "by law, but shall provide access to the nonexempt records as provided by this chapter")):
        assert D.bearer(D.VA_FOIA, D.Element("x", "duty", "x", "2.2-3704", sub, quote), va["2.2-3704"]) is None, sub


@pytest.mark.parametrize("word", [
    "need", "needed", "necessary", "compulsory", "obligatory", "mandated", "expected to", "needs to", "required",
    "mandatory",
    # the second re-check's gaps
    "should", "ought to", "requiring", "essential", "compelled", "obliges", "obligate", "necessity", "needful",
    "req.", "please provide", "is to be given"])
def test_more_obligation_words_are_caught(word):
    va = _va_texts()
    medium = next(e for e in D.VA_FOIA.elements if e.id == "medium")
    for change in ({"fields": (dataclasses.replace(medium.fields[0], label=f"Medium ({word})"),)},
                   {"fields": (dataclasses.replace(medium.fields[0], placeholder=f"a medium is {word}"),)},
                   {"help": f"You {word} name a medium."}):
        _refused(_with(D.VA_FOIA, "medium", **change), va, "medium",
                 f"states an obligation ('{word.split()[0].rstrip('.')}")


@pytest.mark.parametrize("label, words", [
    ("Medium (ｍｕｓｔ)", "states an obligation ('must')"),                # full-width letters
    ("Medium (re\u00adquired)", "states an obligation ('required')"),      # a soft hyphen inside the word
    ("Medium (ne\u200bed)", "states an obligation ('need')"),              # a zero-width space inside the word
    ("Medium (requir\u0435d)", "a letter outside the Latin script"),       # a Cyrillic "\u0435"
    ("Medium (\u043cust)", "a letter outside the Latin script")])          # a Cyrillic "\u043c"
def test_obligation_words_hidden_by_unicode_are_caught(label, words):
    va = _va_texts()
    medium = next(e for e in D.VA_FOIA.elements if e.id == "medium")
    _refused(_with(D.VA_FOIA, "medium", fields=(dataclasses.replace(medium.fields[0], label=label),)), va, "medium",
             words)


@pytest.mark.parametrize("mark", ["*", "＊", "∗", "✱", "﹡", "⁎", "✳"])
def test_a_star_marker_is_caught(mark):
    va = _va_texts()
    medium = next(e for e in D.VA_FOIA.elements if e.id == "medium")
    shown = unicodedata.normalize("NFKC", mark)          # the full-width and small asterisks fold to "*"
    for field in (dataclasses.replace(medium.fields[0], label=f"Medium {mark}"),
                  dataclasses.replace(medium.fields[0], placeholder=f"e.g. CSV {mark}")):
        _refused(_with(D.VA_FOIA, "medium", fields=(field,)), va, "medium", f"uses a {shown!r} mark")
    # in a required element too, whose quote has no such mark, and in the spec's own texts
    records = next(e for e in D.VA_FOIA.elements if e.id == "records")
    _refused(_with(D.VA_FOIA, "records", fields=(dataclasses.replace(records.fields[0], label=f"Records {mark}"),)),
             va, "records", f"uses a {shown!r} mark")
    bad = dataclasses.replace(D.VA_FOIA, title=f"Request for public records {mark}")
    assert any(p.startswith(f"va-foia-request: the title uses a {shown!r} mark") for p in D.check(bad, va))


def test_the_spec_texts_state_no_obligation(monkeypatch):
    va, ca = _va_texts(), _ca_texts()
    for attr in ("title", "summary", "scope"):
        bad = dataclasses.replace(D.VA_FOIA, **{attr: "You must give your phone number."})
        assert f"va-foia-request: the {attr} states an obligation ('must')" in D.check(bad, va)
    bad = dataclasses.replace(D.CA_HEARING, related=(("ca", "record_sealing", "Forms you are required to file"),))
    assert "ca-bpc-485-hearing-request: the heading of related forms 1 states an obligation ('required')" in \
        D.check(bad, ca)
    bad = dataclasses.replace(D.VA_FOIA, closing="Sincerely (signature needed),\n{name}")
    assert any("the closing states an obligation ('needed')" in p for p in D.check(bad, va))
    # the fixture's no-form note is shown in the official box, so it is checked too
    data = json.loads(json.dumps(R.registry().data))
    for n in data["no_form"]:
        if (n["state"], n["process"]) == ("va", "records"):
            n["note"] = "You must use the county's own form."
    monkeypatch.setattr(D.R, "registry", lambda path=None: R.Registry(data))
    assert "va-foia-request: the fixture's no-form note states an obligation ('must')" in D.check(D.VA_FOIA, va)


def test_a_form_the_fixture_links_to_no_step_of_the_process_is_at_most_related():
    # CR-180 is linked only under record sealing, so on the licence-conviction draft it can only be related
    ca = _ca_texts()
    assert not any(R.step_file_key(s["file"]) == ("ca", "license_conviction")
                   for s in R.registry().form("ca-jc-cr-180")["steps"])
    bad = _with(D.CA_HEARING, "dismissed", forms=(D.FormLink("ca-jc-cr-180", "partial", "What it is: x"),))
    _refused(bad, ca, "dismissed", "links it to no step of ca/license_conviction, so it is at most 'related'")
    ok = _with(D.CA_HEARING, "dismissed", forms=(D.FormLink("ca-jc-cr-180", "related", "What it is: x"),))
    assert not [p for p in D.check(ok, ca) if "/dismissed:" in p]


def test_a_default_value_is_refused():
    for element_id, default in (("cost_estimate", True), ("reference", True),
                                ("access", "receive copies of the records")):
        el = next(e for e in D.VA_FOIA.elements if e.id == element_id)
        bad = _with(D.VA_FOIA, element_id, fields=(dataclasses.replace(el.fields[0], default=default),))
        assert any(element_id in p and "has a default value" in p for p in D.check(bad, _va_texts())), element_id


def test_locate_follows_the_section_layout():
    paren = ("Opening words.\n\n(a) First rule:\n\n(1) One.\n\n(2) Two.\n\n(A) Two A.\n\n(i) Two A i.\n\n"
             "(b) Second rule.\n\nClosing words.")
    assert D.locate(paren, "Opening words.", None) is None
    assert D.locate(paren, "Closing words.", None) is None
    # an unlettered paragraph after the subdivisions is the section's own text, not part of (b)
    assert D.locate(paren, "Closing words.", "b") == "quote found, but not under subsection (b)"
    assert "inside a lettered subsection" in D.locate(paren, "Second rule.", None)
    assert D.locate(paren, "Two.", "a.2") is None and D.locate(paren, "Two.", "a") is None
    assert D.locate(paren, "Two.", "a.1") == "quote found, but not under subsection (a)(1)"
    assert D.locate(paren, "Two A i.", "a.2.A.i") is None
    assert D.locate(paren, "Two A i.", "a.2.B") == "quote found, but not under subsection (a)(2)(B)"
    assert D.locate(paren, "First rule: (1) One.", "a.1") is None          # from (a) into (a)(1)
    assert D.locate(paren, "One. (2) Two.", "a.1") is not None             # runs on into (a)(2)
    dot = "A. First.\n\nB. Second:\n\n1. Item one.\n\n2. Item two.\n\nMore of B.\n\nC. Third."
    # in the A. style an unlettered paragraph continues the subsection above it, but not its numbered item
    assert D.locate(dot, "More of B.", "B") is None
    assert D.locate(dot, "More of B.", "B.2") == "quote found, but not under subsection (B)(2)"
    assert D.locate(dot, "Item two.", "B.2") is None and D.locate(dot, "Item two.", "C") is not None
    assert D.locate("No letters at all.\n\nA second paragraph.", "A second paragraph.", None) is None
    # an unlettered paragraph between two subdivisions may be the section's text or the end of the one above:
    # no citation is accepted for it, while the opening and closing words stay the section's own
    mid = "Opening words.\n\n(a) First rule.\n\nA flush paragraph.\n\n(b) Second rule.\n\nClosing words."
    for sub in (None, "a", "b"):
        assert "between two subdivisions" in D.locate(mid, "A flush paragraph.", sub), sub
    assert D.locate(mid, "Opening words.", None) is None and D.locate(mid, "Closing words.", None) is None
    assert D.locate(mid, "First rule.", "a") is None


def test_locate_keeps_the_closing_words_of_section_485_out_of_subsection_b():
    ca = texts_for(D.CA_HEARING)
    s485 = ca["Cal. BPC § 485"]["text"]
    quote = "Service by mail is complete on the date of mailing."
    assert D.locate(s485, quote, "b") == "quote found, but not under subsection (b)"
    assert D.locate(s485, quote, None) is None
    bad = _with(D.CA_HEARING, "service_date", subsection="b")
    assert any("service_date" in p and "not under subsection (b)" in p
               for p in D.check(bad, {ref: t["text"] for ref, t in ca.items()}))
    s480 = ca["Cal. BPC § 480"]["text"]
    assert D.locate(s480, "The processes for the applicant to request a copy", "f.3.D") is None
    assert D.locate(s480, "The processes for the applicant to request a copy", "f.3.C") is not None
    assert D.locate(s480, "This section does not in any way modify", "i") is None   # (i) after (h) is (i)
    assert D.locate(s480, "Chapter 6 (commencing with Section 6500) of Division 3.", "i") is not None


PLAN = ROOT / "docs" / "design" / "forms-plan.md"


def _plan_rule(n: int) -> str:
    """Rule n of §6 in docs/design/forms-plan.md, up to the next rule."""
    text = PLAN.read_text(encoding="utf-8")
    rules = text.split("\n## 6. Rules for generated drafts", 1)[1].split("\n## 7. ", 1)[0]
    return re.search(rf"\n{n}\. (.*?)(?=\n{n + 1}\. |\n\*\*What the checks cannot do)", rules, re.S)[1]


def test_the_docs_say_what_the_code_does():
    # rule 11 quotes the review status the code writes
    d = D.build(D.VA_FOIA, _va_texts(), as_of="2026-10-10")
    assert f"\"{d['review']}\"" in " ".join(_plan_rule(11).split())
    # rule 3 and the docstring name every word and mark after which a party heads a subject
    rule3 = " ".join(_plan_rule(3).split())
    doc = " ".join(D.__doc__.split())
    for word in sorted(D._JOINERS):
        assert f"\"{word}\"" in rule3 and f"\"{word}\"" in doc, word
    for mark in ("a comma, semicolon or colon", "a paragraph mark"):
        assert mark in rule3 and mark in doc, mark
    # and the exempt letter fields, as LETTER_FIELDS has them
    rule4 = " ".join(_plan_rule(4).split())
    for name, (_, word, allowed) in D.LETTER_FIELDS.items():
        assert f"`{name}`" in rule4 and ", ".join(f"\"{w}\"" for w in sorted(allowed)) in rule4, name


def test_no_draft_for_a_step_with_an_official_form():
    bad = dataclasses.replace(D.VA_FOIA, question="record_sealing", step="file_petition")
    assert any("has an official form" in p for p in D.check(bad, _va_texts()))


# ------------------------------------------------------------------------------------- worked examples
@pytest.mark.parametrize("spec_id", sorted(D.SPECS))
def test_the_worked_examples_are_current(spec_id):
    path = OUT / f"{spec_id}.json"
    if not path.exists():
        pytest.skip(f"{OUT} not here: out/ is not mounted in the app container; set LEXFLOW_FORMS_OUT to a copy "
                    "(or run python -m lexflow.forms.draft)")
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert {s["ref"] for s in saved["sources"]} == set(D.SPECS[spec_id].sections)
    for s in saved["sources"]:
        assert hashlib.sha256(s["text"].encode("utf-8")).hexdigest() == s["sha256"]
    fresh = D.build(spec_id, D.read_sources([str(path)]), as_of=saved["made"])
    # rebuilt from its own saved sources, each file is byte for byte what out/forms holds
    assert json.dumps(fresh, ensure_ascii=False, indent=1) + "\n" == path.read_text(encoding="utf-8")
    for kind, render in (("form", D.render_form), ("letter", D.render_letter)):
        page = (OUT / f"{spec_id}.{kind}.html").read_text(encoding="utf-8")
        assert page == render(fresh), kind
        assert D.BANNER in page
    letter = (OUT / f"{spec_id}.letter.html").read_text(encoding="utf-8")
    assert letter.index("Official form first") < letter.index("<div class=\"letter\">")
    index = (OUT / "index.html").read_text(encoding="utf-8")
    assert f"{len(fresh['elements'])} elements" in index and D.BANNER in index


def _loaded(spec):
    try:
        return D.load_texts(spec)
    except Exception as exc:  # noqa: BLE001 - no local statute store here
        pytest.skip(f"no statute text for {spec.id} here ({type(exc).__name__}); California needs the local store")


@pytest.mark.parametrize("spec_id", sorted(D.SPECS))
def test_the_statute_texts_are_the_ones_the_examples_were_built_from(spec_id):
    # runs by default wherever the texts load (Virginia from fixtures/statutes; California from the local store),
    # without out/forms: the hashes are those in the worked examples' "sources"
    spec = D.SPECS[spec_id]
    texts = _loaded(spec)
    assert set(texts) == set(BUILT_FROM[spec_id]) == set(spec.sections)
    for ref, t in texts.items():
        assert hashlib.sha256(t["text"].encode("utf-8")).hexdigest() == BUILT_FROM[spec_id][ref], ref
    saved = OUT / f"{spec_id}.json"
    if saved.exists():
        assert {s["ref"]: s["sha256"] for s in json.loads(saved.read_text(encoding="utf-8"))["sources"]} == \
            BUILT_FROM[spec_id]


@pytest.mark.parametrize("spec_id", sorted(D.SPECS))
def test_the_draft_records_its_provenance(spec_id):
    # rule 11: each section's text, URL, origin and SHA-256, the date made and the review status
    spec = D.SPECS[spec_id]
    d = D.build(spec, _loaded(spec), as_of="2026-10-10")
    assert d["made"] == "2026-10-10" and d["generator"] == "lexflow.forms.draft"
    assert d["review"] == "draft, machine-checked (quotes and rules); not reviewed by a lawyer"
    assert [s["ref"] for s in d["sources"]] == list(spec.sections)
    for s in d["sources"]:
        assert s["citation"] == spec.citations[s["ref"]]
        assert s["sha256"] == hashlib.sha256(s["text"].encode("utf-8")).hexdigest()
        assert s["url"].startswith("https://") and "open-us-law" in s["retrieved_from"], s["ref"]
        assert s["license_note"], s["ref"]
    if spec.state == "va":
        (s,) = d["sources"]
        assert s["url"] == "https://law.lis.virginia.gov/vacode/2.2-3704/"
        assert s["retrieved_from"].startswith("fixtures/statutes/va_sections.json (open-us-law ")
    for e in d["elements"]:
        assert e["url"] == next(s["url"] for s in d["sources"] if s["ref"] == e["section"])
    assert "Made 2026-10-10 by lexflow from " in D.render_letter(d) and d["review"] in D.render_form(d)


@pytest.mark.parametrize("spec_id", sorted(D.SPECS))
def test_the_worked_examples_match_the_statute_text(spec_id):
    spec = D.SPECS[spec_id]
    checked = 0
    for ref in spec.sections:
        snap = snapshot_text(spec_id, ref)
        live = fixture_text(spec.state, ref) or store_text(spec.state, ref)
        if snap is None or live is None:
            continue
        from lexflow.municipal.statutes import strip_history
        assert norm(strip_history(live)) == norm(snap), ref
        checked += 1
    if not checked:
        pytest.skip("no snapshot or statute text to compare here")
