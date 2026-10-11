"""Privacy of the research notes and research fixtures.

Covered: the design notes in ``DOCS`` and every file in fixtures/entities, fixtures/xref and fixtures/authority.
They may hold organisations, offices, official office channels, statute text and the authors of cited works.
They must not hold a personal or staff mailbox, a direct line, a staff name, an individual's pay, or anything else
that identifies a private individual.  A made-up example is written on a reserved domain (example.org, example.com)
or in the reserved number range 555-0100 to 555-0199.

The contact values in the fixtures are pinned to reviewed office channels, so a re-recorded fixture with a new
value fails here until a person has looked at it.  The Wikidata term survey (fixtures/xref/wikidata_terms.json)
keeps person items only where they are public figures, historical persons or a one-word label that is the searched
term itself; the one hit for an apparently private individual is withheld.
"""
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DESIGN = ROOT / "docs" / "design"

# The notes this privacy pass covers.  The other notes in docs/design have their own owners.
DOCS = ["entities-codebase.md", "entities-contacts.md", "entities-sources.md", "forms-research.md",
        "lab-research.md", "links-codebase-map.md", "links-literature.md", "verify-credits.md",
        "verify-dmn-links.md", "verify-entities.md", "verify-forms.md", "verify-lab.md", "verify-resolver.md",
        "verify-terms.md"]
FIXTURES = sorted([*(ROOT / "fixtures" / "entities").glob("*.json"), *(ROOT / "fixtures" / "xref").glob("*.json"),
                   *(ROOT / "fixtures" / "authority").glob("*.json")])
SURVEY = ROOT / "fixtures" / "xref" / "wikidata_terms.json"

EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")
# A NANP number (3-3-4 digits, optionally +1), not inside a longer run such as the DOI 10.1007/s00766-012-0152-5
PHONE = re.compile(r"(?<![\w/.-])(?:\+?1[-. ])?\(?\d{3}\)?[-. ]\d{3}[-. ]\d{4}(?![\w-])")

# Office mailboxes, each published by the office itself (or its Wikidata item) as its general channel.
OFFICE_MAILBOXES = {
    "mpd@dc.gov": "DC Metropolitan Police Department (Wikidata P968)",
    "CorpHelp@dos.myflorida.com": "Florida Division of Corporations (Wikidata P968)",
    "corporations@dos.ny.gov": "New York Division of Corporations (Wikidata P968)",
    "corps@sos.wa.gov": "Washington Corporations and Charities Division (Wikidata P968)",
    "citycorbiz@charlottesville.gov": "Charlottesville Commissioner of the Revenue, business tax",
    "FOIA@charlottesville.gov": "Charlottesville FOIA mailbox",
    "foiacouncil@dls.virginia.gov": "Virginia FOIA Council",
    "COBBusinessLicense@baltimorecity.gov": "Baltimore business licensing",
    "bmza@baltimorecity.gov": "Baltimore Board of Municipal and Zoning Appeals",
    "dhcd.mpia@baltimorecity.gov": "Baltimore Department of Housing & Community Development, MPIA requests",
    "oig@baltimorecity.gov": "Baltimore Office of the Inspector General",
    "foia.appeals@dc.gov": "DC FOIA appeals to the Mayor",
    "nccinfo@northchevychase.org": "Village of North Chevy Chase (Wikidata P968)",
}
# Main office lines (digits only), each labelled with an office, never a person.
OFFICE_LINES = {
    "2027279099": "DC Metropolitan Police Department (Wikidata P1329)",
    "8502456000": "Florida Division of Corporations (Wikidata P1329)",
    "3607250377": "Washington Corporations and Charities Division (Wikidata P1329)",
    "8042253056": "Virginia FOIA Council", "8664484100": "Virginia FOIA Council, toll-free",
    "4348250508": "Charlottesville Economic Development", "4349703170": "Charlottesville Commissioner of the Revenue",
    "4349703182": "Charlottesville Neighborhood Development Services", "4349726219": "Blue Ridge Health District",
    "4349703827": "Charlottesville FOIA officers directory, main number",
    "4103964544": "Baltimore Health Department plan review", "4103963100": "Baltimore city information",
    "4432632220": "Baltimore city information", "2026713500": "DC Department of Buildings",
    "2026714500": "DC DLCP Business Licensing Division", "2027274829": "DC Office of Tax and Revenue",
    "3016547084": "Village of North Chevy Chase (Wikidata P1329)",
}

# Person items (P31 human) the survey keeps, by QID, and why each is not a private individual's data.
REVIEWED_PERSON_ITEMS = {
    "Q76981523": "historical person (1844-1910, by the item's own dates)",
    "Q2627241": "historical person (a botanist, 1789-1874)",
    "Q131287612": "the label is one word, the searched term itself (a photographer, floruit 1958)",
    "Q155079": "public figure",
    "Q3068195": "public figure, known by a stage name; aliases withheld",
    "Q124775089": "public figure, known by a stage name; aliases withheld",
}
ALIASES_WITHHELD = {"Q3068195", "Q124775089"}
WITHHELD_QID, WITHHELD_LABEL = "Q-withheld", "[name withheld]"


def _strings(obj):
    if isinstance(obj, dict):
        for v in obj.values():
            yield from _strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _strings(v)
    elif isinstance(obj, str):
        yield obj


def _fixture_strings():
    for path in FIXTURES:
        for s in _strings(json.loads(path.read_text(encoding="utf-8"))):
            yield path.name, s


def _survey():
    return json.loads(SURVEY.read_text(encoding="utf-8"))


def _person_candidates(d):
    for t in d["terms"]:
        for c in t.get("candidates", []):
            if any((x.get("qid") if isinstance(x, dict) else x) == "Q5" for x in c.get("p31") or []):
                yield t["term"], c


def _reserved(address: str) -> bool:
    """example.org, example.com and example.net (RFC 2606) are reserved for examples: made-up addresses."""
    return re.search(r"@(?:[A-Za-z0-9-]+\.)*example\.(?:org|com|net)$", address, re.I) is not None


def _fictional(number: str) -> bool:
    """555-0100 to 555-0199 are reserved for fiction in the North American Numbering Plan: made-up examples."""
    digits = re.sub(r"\D", "", number)[-7:]
    return digits.startswith("55501")


@pytest.mark.parametrize("name", DOCS)
def test_design_note_reproduces_no_mailbox_or_phone_number(name):
    text = (DESIGN / name).read_text(encoding="utf-8")
    assert not [a for a in EMAIL.findall(text) if not _reserved(a)], f"{name} reproduces an e-mail address"
    assert not [p for p in PHONE.findall(text) if not _fictional(p)], f"{name} reproduces a phone number"


def test_example_addresses_are_the_reserved_domains_only():
    assert _reserved("records@example.org") and _reserved("will.page@example.com") and _reserved("a@x.example.net")
    assert not _reserved("records@charlottesville.gov") and not _reserved("a@example.org.evil.com")
    assert not _reserved("a@notexample.org")


def test_fictional_numbers_are_the_reserved_range_only():
    assert _fictional("434-555-0100") and _fictional("(434) 555-0199")
    assert not _fictional("434-555-0200") and not _fictional("434-970-3827")


def test_phone_pattern_skips_dois_and_dates():
    assert not PHONE.findall("doi:10.1007/s00766-012-0152-5, 2026-10-10, 10.1145/3473582")
    assert PHONE.findall('"434-970-3827"') and PHONE.findall('"+1-202-727-9099"')


def test_fixture_mailboxes_are_reviewed_office_mailboxes():
    found = {m for _, s in _fixture_strings() for m in EMAIL.findall(s)}
    assert found, "the scan found nothing; the fixtures moved?"
    assert found <= set(OFFICE_MAILBOXES), f"unreviewed addresses: {sorted(found - set(OFFICE_MAILBOXES))}"


def test_fixture_phone_numbers_are_reviewed_office_lines():
    found = {re.sub(r"\D", "", m)[-10:] for _, s in _fixture_strings() for m in PHONE.findall(s)}
    assert found, "the scan found nothing; the fixtures moved?"
    assert found <= set(OFFICE_LINES), "a phone number in the fixtures is not a reviewed office line"


def test_survey_keeps_only_reviewed_person_items():
    d = _survey()
    people = list(_person_candidates(d))
    withheld = [c for _, c in people if c["qid"] == WITHHELD_QID]
    assert len(withheld) == 1 and withheld[0]["label"] == WITHHELD_LABEL
    for term, c in people:
        if c["qid"] == WITHHELD_QID:
            continue
        assert c["qid"] in REVIEWED_PERSON_ITEMS, f"unreviewed person item for {term!r}: {c['qid']}"
        if c["qid"] in ALIASES_WITHHELD:
            assert c["aliases"] == [], f"{c['qid']}: aliases are withheld"
    assert {c["qid"] for _, c in people} == set(REVIEWED_PERSON_ITEMS) | {WITHHELD_QID}
    assert "withheld" in d["notes"]["privacy"]


def test_survey_redaction_leaves_the_fitted_features_unchanged():
    """The shipped link model was fitted on the survey: its per-feature mean and spread are the survey's.  They
    still are, so the withheld name and aliases changed no feature of any of the 714 pairs."""
    np = pytest.importorskip("numpy")
    from lexflow.law import terms as T
    m = T.LINK_MODEL
    if not m or m["features"] != T.FEATURES:
        pytest.skip("no shipped model for the current feature list")
    pairs = T.survey_pairs(SURVEY)
    assert len(pairs) == 714
    rows = T.pair_features(pairs)
    X = np.array([[r.get(f, 0.0) for f in m["features"]] for r in rows], dtype=float)
    assert np.allclose(np.round(X.mean(axis=0), 6), m["mu"], atol=2e-6)
    assert np.allclose(np.round(X.std(axis=0) + 1e-6, 6), m["sd"], atol=2e-6)


def test_verify_credits_names_no_personal_account():
    text = (DESIGN / "verify-credits.md").read_text(encoding="utf-8")
    owners = set(re.findall(r"github\.com/([A-Za-z0-9_.-]+)", text))
    assert owners <= {"fit-process-mining", "coin-or"}, owners
    assert not re.search(r'(?:family|given)-names\s+"', text)


def test_verify_entities_records_that_the_staff_mailboxes_were_removed():
    text = (DESIGN / "verify-entities.md").read_text(encoding="utf-8")
    assert "since removed from the current pages" in text
    assert "Status after this review (privacy pass, 2026-10-10)" in text
