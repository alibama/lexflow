"""Links between process models (lexflow.law.links): a model provides a status another model's decision requires.

The cross-references are mocked in the two shapes the module reads: the gold fixtures' (fixtures/xref/gold_*.json)
and lexflow.law.xref.Reference's.  Matching is offline (normalised citations), so no statute index is needed.

The last section pins fixes to the worked example's decision model, out/design/bpc_480.dmn, through its checker
out/design/check_bpc_480.py.  out/ is not bind-mounted into the container, so those tests run where out/design is
present, or where LEXFLOW_BPC480_DIR names a directory holding copies of both files; otherwise they are skipped.
"""
import dataclasses
import importlib.util
import inspect
import json
import os
import tempfile
from pathlib import Path

import pytest

from lexflow.law import links as LK
from lexflow.law.links import ModelEntry, ProvidedStatus, RequiredInput, SectionRef, XRef

ROOT = Path(__file__).resolve().parents[1]
B480 = "Cal. BPC § 480"
DISMISSALS = ["Cal. PEN § 1203.4", "Cal. PEN § 1203.4a", "Cal. PEN § 1203.41", "Cal. PEN § 1203.42",
              "Cal. PEN § 1203.425"]


def gold_ref(span, role, targets, unit=None, list_span=None):
    """A reference in the gold fixtures' shape (gold_b.json)."""
    return {"span": span, "role": role, "target_sections": targets, "target_unit": unit, "list_span": list_span,
            "kind": "section"}


@dataclasses.dataclass
class FakeReference:
    """The fields of lexflow.law.xref.Reference that links.py reads."""
    span: str
    start: int
    end: int
    kind: str
    code: str | None
    sections: list
    pinpoint: str | None
    role: str
    confidence: float
    unit: dict | None = None
    list_group: int | None = None


def entry(mid, sections, quoted=(), statuses=()):
    state, q = mid.split(".", 1)
    return ModelEntry(f"lexflow:process:{mid}", mid, state, q, "curated_ask", mid, tuple(sections), tuple(quoted),
                      tuple(statuses))


DISMISSED = ProvidedStatus("lexflow:status:ca.record_sealing:dismissed", "lexflow:process:ca.record_sealing",
                           "dismissed", "Conviction dismissed", sections=("1203.4",))
CATALOG = [
    entry("ca.record_sealing", [("1203.4", "primary"), ("1203.4a", "primary"), ("1203.41", "primary"),
                                ("1203.425", "primary"), ("1203.42", "supporting"), (B480, "supporting")],
          quoted=("1203.4", "1203.42"), statuses=(DISMISSED,)),
    entry("ca.license_conviction", [(B480, "primary"), ("Cal. BPC § 482", "primary"),
                                    ("Cal. PEN § 4852.01", "supporting"), ("Cal. BPC § 7.5", "definition")],
          quoted=("480", "481")),
    entry("ca.court_debt", [("Cal. PEN § 1205", "primary")]),
    entry("va.record_sealing", [("19.2-392.12", "primary")]),
]
LC = "lexflow:process:ca.license_conviction"
RS = "lexflow:process:ca.record_sealing"


def bpc_480_refs():
    """The § 480 references of role prerequisite_process / definition (gold_b.json), plus a scope one."""
    out = [gold_ref("Section 1192.7 of the Penal Code", "definition", ["Cal. PEN § 1192.7"])]
    # (a)(2) and the first sentence of (c) cite all five dismissal sections; the second sentence of (c) cites four
    # (it omits § 1203.425): 5 + 5 + 4 = 14 references, as in gold_b.json
    for group, cited in (("a2", DISMISSALS), ("c1", DISMISSALS), ("c2", DISMISSALS[:4])):
        out += [gold_ref(n.split("§ ")[1], "prerequisite_process", [n], list_span=f"Section 1203.4, ... ({group})")
                for n in cited]
    out += [gold_ref("Chapter 3.5 (commencing with Section 4852.01) of Title 6 of Part 3 of the Penal Code",
                     "prerequisite_process", ["Cal. PEN § 4852.01"],
                     unit="California Code / Code pen / Part 3 / Title 6 / Chapter 3.5"),
            gold_ref("Section 482", "prerequisite_process", ["Cal. BPC § 482"]),
            gold_ref("Section 7.5", "definition", ["Cal. BPC § 7.5"]),
            gold_ref("this section", "scope", [B480])]
    return out


# ------------------------------------------------------------------ citations
@pytest.mark.parametrize("ref,want", [
    ("Cal. PEN § 1203.4", ("pen", "1203.4")),
    ("1203.4", (None, "1203.4")),
    ("Penal Code § 4852.01 et seq.", ("pen", "4852.01")),
    ("Cal. Penal Code § 4852.01 et seq.", ("pen", "4852.01")),
    ("Va. Code Ann. § 54.1-204", ("va", "54.1-204")),
    ("Cal. BPC § 480(a)(1)", ("bpc", "480")),
])
def test_parse_cite(ref, want):
    assert LK.parse_cite(ref) == want


def test_same_section_is_code_aware():
    s = lambda c, a=None: SectionRef("ca", c, a)   # noqa: E731
    assert LK.same_section(s("Cal. PEN § 1203.4"), s("1203.4"))            # a bare number matches any code
    assert not LK.same_section(s("Cal. PEN § 482"), s("Cal. BPC § 482"))    # two codes, one number
    assert not LK.same_section(s("Cal. PEN § 1203.4"), s("Cal. PEN § 1203.4a"))
    assert LK.same_section(s("x", "A1"), s("y", "A1"))                      # act_id wins when both have one
    assert not LK.same_section(s("Cal. PEN § 1203.4", "A1"), s("Cal. PEN § 1203.4", "A2"))
    assert not LK.same_section(SectionRef("ca", "1203.4"), SectionRef("va", "1203.4"))


def test_as_xref_reads_gold_and_xref_module_shapes():
    g = LK.as_xref(gold_ref("Section 482", "prerequisite_process", ["Cal. BPC § 482"]), state="ca", source=B480)
    assert (g.state, g.source, g.targets, g.role) == ("ca", B480, ("Cal. BPC § 482",), "prerequisite_process")
    a = LK.as_xref({"span": "this subtitle", "role": "definition", "target_sections": None,
                    "target_unit": {"index_path": "Virginia Code / Title 54.1 / Subtitle II"}}, state="va")
    assert a.unit == "Virginia Code / Title 54.1 / Subtitle II" and a.targets == ()
    r = LK.as_xref(FakeReference("Section 1203.4", 2684, 2698, "list_item", "Cal. PEN § ",
                                 [{"id": 105745, "citation": "Cal. PEN § 1203.4"}], None, "prerequisite_process", 0.9,
                                 unit={"path": "California Code / Code pen / Part 2", "first": None}, list_group=3),
                   state="ca", source=B480)
    assert r.targets == ("Cal. PEN § 1203.4",) and r.unit == "California Code / Code pen / Part 2"
    assert r.list_group == "3" and r.start == 2684


# ------------------------------------------------------------------ the worked example
def test_bpc_480_proposes_one_link_from_the_dismissal_model():
    rep = LK.propose_links("ca.license_conviction", bpc_480_refs(), CATALOG, state="ca", source=B480,
                           requires=LK.BPC_480_INPUTS,
                           terms=[{"term": "serious felony", "defined_in": "Cal. PEN § 1192.7"}])
    assert rep.consumer == LC and rep.skipped == 1                       # the scope reference
    assert sum(1 for r in bpc_480_refs() if r["role"] == "prerequisite_process"
               and r["target_sections"][0] in DISMISSALS) == 14          # 5 + 5 + 4
    assert len(rep.links) == 1                                           # 14 references, one link
    ln = rep.links[0]
    assert (ln.kind, ln.provider, ln.consumer, ln.role) == ("provides-input", RS, LC, "prerequisite_process")
    assert set(ln.via) == set(DISMISSALS) and ln.match == "section" and ln.coverage == 1.0
    assert ln.score == 1.0                                               # primary gold sections
    assert ln.status == DISMISSED.key                                    # the outcome quoted from § 1203.4
    assert ln.required == "lexflow:input:ca.license_conviction:conviction_dismissed"
    assert ln.status_type == "lexflow:status:ca:conviction-dismissed"    # the type out/design/bpc_480.dmn requires
    assert ln.rendering == "dataStoreReference"                          # read from the DOJ record
    assert ln.id == f"{RS}->{LC}:prerequisite_process"
    internal = {v for i in rep.internal for v in i.via}
    assert internal == {"Cal. BPC § 482", "Cal. BPC § 7.5"}              # the licensing model has both
    assert [m.via for m in rep.missing] == [("Cal. PEN § 4852.01",)]    # background only: a model to build
    assert rep.missing[0].suggested_key == "lexflow:process:ca.pen_4852_01"
    d = rep.definitions[0]
    assert (d.defined_in, d.term, d.key) == ("Cal. PEN § 1192.7", "serious felony",
                                             "lexflow:term:ca:Cal. PEN § 1192.7:serious-felony")
    json.dumps(rep.to_dict())                                            # serialisable as is


def test_only_named_definitions_get_term_keys():
    """§ 480 borrows three definitions; the gold terms name two (PEN 1192.7, BPC 729), so only those get keys."""
    refs = [gold_ref("Section 1192.7 of the Penal Code", "definition", ["Cal. PEN § 1192.7"]),
            gold_ref("Section 726", "definition", ["Cal. BPC § 726"]),
            gold_ref("subdivision (a) of Section 729", "definition", ["Cal. BPC § 729"])]
    terms = [{"term": "serious felony", "defined_in": "Cal. PEN § 1192.7"},
             {"term": "sexual exploitation", "defined_in": "Cal. BPC § 729"}]
    rep = LK.propose_links(LC, refs, CATALOG, state="ca", source=B480, terms=terms)
    got = {d.defined_in: (d.term, d.key) for d in rep.definitions}
    assert got == {"Cal. PEN § 1192.7": ("serious felony", "lexflow:term:ca:Cal. PEN § 1192.7:serious-felony"),
                   "Cal. BPC § 729": ("sexual exploitation", "lexflow:term:ca:Cal. BPC § 729:sexual-exploitation"),
                   "Cal. BPC § 726": (None, None)}
    assert sum(1 for d in rep.definitions if d.key) == 2


GOLD_B = ROOT / "fixtures" / "xref" / "gold_b.json"


@pytest.mark.skipif(not GOLD_B.exists(), reason="no gold fixtures")
def test_gold_480_has_14_dismissal_references_in_three_lists():
    s = next(x for x in json.loads(GOLD_B.read_text(encoding="utf-8"))["sections"] if x["citation"] == B480)
    dism = [r for r in s["references"] if r["role"] == "prerequisite_process"
            and (r.get("target_sections") or [None])[0] in DISMISSALS]
    assert len(dism) == 14
    lists, prev_end = [], None                     # split the references into the lists they stand in
    for r in sorted(dism, key=lambda r: r["start"]):
        if prev_end is None or r["start"] - prev_end > 20:
            lists.append([])
        lists[-1].append(r["target_sections"][0])
        prev_end = r["end"]
    assert [len(x) for x in lists] == [5, 5, 4]                   # (a)(2), (c) first sentence, (c) second sentence
    assert lists[2] == DISMISSALS[:4]                              # the second sentence omits § 1203.425
    named = [t for t in s["terms"] if t.get("defined_in") in ("Cal. PEN § 1192.7", "Cal. BPC § 726", "Cal. BPC § 729")]
    assert sorted(t["defined_in"] for t in named) == ["Cal. BPC § 729", "Cal. PEN § 1192.7"]   # § 726 is unnamed


@pytest.mark.skipif(not (GOLD_B.exists() and (ROOT / "curated_ask" / "record_sealing" / "ca.json").exists()),
                    reason="no gold fixtures or curated_ask data")
def test_gold_480_on_the_repository_models_gives_one_link_and_two_term_keys():
    s = next(x for x in json.loads(GOLD_B.read_text(encoding="utf-8"))["sections"] if x["citation"] == B480)
    rep = LK.propose_links("ca.license_conviction", s["references"], LK.load_catalog(ROOT), state="ca", source=B480,
                           requires=LK.BPC_480_INPUTS, terms=s["terms"])
    assert [(ln.provider, set(ln.via), ln.coverage) for ln in rep.links] == [(RS, set(DISMISSALS), 1.0)]
    assert {v for i in rep.internal for v in i.via} == {"Cal. BPC § 482", "Cal. BPC § 7.5"}
    assert [m.via for m in rep.missing] == [("Cal. PEN § 4852.01",)]
    assert {d.defined_in: d.key for d in rep.definitions} == {
        "Cal. PEN § 1192.7": "lexflow:term:ca:Cal. PEN § 1192.7:serious-felony",
        "Cal. BPC § 726": None,
        "Cal. BPC § 729": "lexflow:term:ca:Cal. BPC § 729:sexual-exploitation"}


def test_reference_module_shape_gives_the_same_link():
    refs = [FakeReference(n.split("§ ")[1], 0, 0, "list_item", "Cal. PEN § ", [{"id": i, "citation": n}], None,
                          "prerequisite_process", 0.9, list_group=1) for i, n in enumerate(DISMISSALS)]
    rep = LK.propose_links(LC, refs, CATALOG, state="ca", source=B480)
    assert [ln.provider for ln in rep.links] == [RS] and set(rep.links[0].via) == set(DISMISSALS)
    assert rep.links[0].required is None and rep.links[0].rendering == "dataStoreReference"


def test_requirements_bind_only_to_their_own_consumer():
    rep = LK.propose_links("ca.court_debt", bpc_480_refs(), CATALOG, state="ca", source=B480,
                           requires=LK.BPC_480_INPUTS)
    assert rep.links and all(ln.required is None for ln in rep.links)


# ------------------------------------------------------------------ matching rules
def test_background_provider_scores_lower_and_says_why():
    cat = [entry("ca.a", [("Cal. PEN § 100", "supporting")]), entry("ca.b", [("Cal. PEN § 100", "primary")])]
    rep = LK.propose_links(None, [gold_ref("Section 100", "prerequisite_process", ["Cal. PEN § 100"])], cat,
                           state="ca", source="Cal. BPC § 1")
    by = {ln.provider: ln for ln in rep.links}
    assert by["lexflow:process:ca.b"].score == 1.0
    assert by["lexflow:process:ca.a"].score == LK.BACKGROUND and "background" in by["lexflow:process:ca.a"].note
    assert [ln.provider for ln in rep.links][0] == "lexflow:process:ca.b"     # best first


def test_unit_reference_matches_a_section_inside_the_unit():
    unit = "California Code / Code pen / Part 3 / Title 6 / Chapter 3.5"
    resolver = lambda st, ref: [SectionRef(st, ref, unit=unit if "4852" in ref else None)]   # noqa: E731
    cat = [entry("ca.certificate", [("Cal. PEN § 4852.06", "primary")])]
    x = gold_ref("Chapter 3.5 (commencing with Section 4852.01)", "prerequisite_process", ["Cal. PEN § 4852.01"],
                 unit=unit)
    rep = LK.propose_links(None, [x], cat, state="ca", source=B480, resolver=resolver)
    assert rep.links[0].match == "unit" and rep.links[0].score == LK.UNIT_FACTOR


def test_self_and_relative_references_are_skipped():
    refs = [gold_ref("subsection B", "prerequisite_process", ["Va. Code Ann. § 54.1-204"]),
            {"span": "this subtitle", "role": "definition", "target_sections": None,
             "target_unit": {"index_path": "Virginia Code / Title 54.1 / Subtitle II"}}]
    rep = LK.propose_links(None, refs, CATALOG, state="va", source="Va. Code Ann. § 54.1-204")
    assert rep.skipped == 2 and not (rep.links or rep.missing or rep.definitions)


def test_what_the_consumer_models_is_not_offered_by_another_model():
    cat = [entry("va.court_debt", [("19.2-354", "primary")]), entry("va.prison_wages", [("19.2-354", "supporting")])]
    rep = LK.propose_links("va.court_debt", [gold_ref("§ 19.2-354", "prerequisite_process", ["Va. Code Ann. § 19.2-354"])],
                           cat, state="va", source="Va. Code Ann. § 19.2-349")
    assert not rep.links and [i.via for i in rep.internal] == [("Va. Code Ann. § 19.2-354",)]


def test_other_states_never_match():
    rep = LK.propose_links(None, [gold_ref("§ 1203.4", "prerequisite_process", ["1203.4"])], CATALOG, state="va",
                           source="Va. Code Ann. § 1")
    assert not rep.links and rep.missing


def test_call_cue_suggests_a_call_activity():
    cat = [entry("ca.hearing", [("Cal. GOV § 11500", "primary")])]
    x = gold_ref("in the manner provided in Section 11500", "prerequisite_process", ["Cal. GOV § 11500"])
    rep = LK.propose_links(None, [x], cat, state="ca", source="Cal. BPC § 485")
    assert rep.links[0].rendering == "callActivity"


def test_definition_links_carry_no_status():
    cat = [entry("ca.license_conviction", [("Cal. BPC § 7.5", "definition")],
                 statuses=(ProvidedStatus("lexflow:status:x", "m", "o", "", sections=("7.5",)),))]
    rep = LK.propose_links(None, [gold_ref("Section 7.5", "definition", ["Cal. BPC § 7.5"])], cat, state="ca",
                           source="Cal. BPC § 480")
    ln = rep.links[0]
    assert (ln.kind, ln.status, ln.rendering, ln.score) == ("definition-from", None, None, 1.0)


def test_shared_sections_and_units():
    unit = "Virginia Code / Title 19.2 / Chapter 23.2"
    resolver = lambda st, ref: [SectionRef(st, ref, unit=unit if "392" in ref else None)]   # noqa: E731
    cat = [entry("va.license_conviction", [("19.2-392.15", "supporting"), ("54.1-204", "primary")]),
           entry("va.record_sealing", [("19.2-392.12", "primary")]),
           entry("ca.license_conviction", [(B480, "primary")]), entry("ca.record_sealing", [(B480, "supporting")])]
    out = {ln.id: ln for ln in LK.shared_sections(cat, resolver=resolver)}
    ca = out[f"{LC}<->{RS}"]
    assert (ca.role, ca.score) == ("shared-section", 0.6)
    va = out["lexflow:process:va.license_conviction<->lexflow:process:va.record_sealing"]
    assert (va.role, va.score, va.via) == ("shared-unit", 0.3, (unit,))


# ------------------------------------------------------------------ the real catalog
@pytest.mark.skipif(not (ROOT / "curated_ask" / "record_sealing" / "ca.json").exists(), reason="no curated_ask data")
def test_catalog_and_the_480_example_on_the_repository_models():
    cat = LK.load_catalog(ROOT)
    keys = {m.model_id: m for m in cat}
    assert {"ca.record_sealing", "ca.license_conviction", "va.license_conviction", "fl.business"} <= set(keys)
    rs = keys["ca.record_sealing"]
    assert ("1203.4", "primary") in rs.sections and "1203.4" in rs.quoted
    assert any(s.key == "lexflow:status:ca.record_sealing:dismissed" for s in rs.statuses)
    assert all(r == "primary" for _, r in keys["fl.business"].sections)
    rep = LK.propose_links("ca.license_conviction", bpc_480_refs(), cat, state="ca", source=B480,
                           requires=LK.BPC_480_INPUTS)
    top = rep.links[0]
    assert (top.provider, top.status, top.required) == (
        RS, "lexflow:status:ca.record_sealing:dismissed", "lexflow:input:ca.license_conviction:conviction_dismissed")


def test_records_are_frozen_and_keyed():
    r = RequiredInput("lexflow:input:m:v", "lexflow:process:ca.m", "v")
    with pytest.raises(dataclasses.FrozenInstanceError):
        r.variable = "w"
    assert SectionRef("ca", B480).key == "lexflow:statute:ca:Cal. BPC § 480"
    assert XRef("ca", B480, "x", "definition", ()).unit is None


# ------------------------------------------------------------------ the § 480 DMN (out/design)
def _design_dir() -> Path | None:
    for d in (os.environ.get("LEXFLOW_BPC480_DIR"), ROOT / "out" / "design"):
        if d and (Path(d) / "bpc_480.dmn").exists() and (Path(d) / "check_bpc_480.py").exists():
            return Path(d)
    return None


DESIGN = _design_dir()
needs_design = pytest.mark.skipif(DESIGN is None, reason="out/design/bpc_480.dmn and check_bpc_480.py not reachable")


@pytest.fixture(scope="module")
def chk():
    """The checker as a module (its main() is not run)."""
    spec = importlib.util.spec_from_file_location("check_bpc_480", DESIGN / "check_bpc_480.py")
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except ImportError as e:                       # lxml, SpiffWorkflow or the statute index missing here
        pytest.skip(f"the checker's dependencies are missing: {e}")
    return mod


@pytest.fixture(scope="module")
def model(chk):
    from lxml import etree
    raw = (DESIGN / "bpc_480.dmn").read_bytes()
    return raw, chk.DRD(etree.fromstring(raw))


def _mutation(chk, label_start):
    hits = [m for m in chk.SEMANTIC_MUTATIONS if m[0].startswith(label_start)]
    assert len(hits) == 1, label_start
    return hits[0]


# the seven one-line changes the re-check of docs/design/verify-dmn-links.md found passing every check, the two
# windows its second re-check found could be widened by under seven months, the three the single-change sweep found,
# and the applicant added to catch each one
RESIDUAL = {
    "the 'presently incarcerated' limb removed": "Y",
    "a release after the application counts": "Z",
    "the Professional Fiduciaries Act ((i)) dropped": "D1",
    "the Private Investigator Act ((iii)) dropped": "D3",
    "funeral directors ((iv)) dropped": "D4",
    "cemetery managers ((iv)) dropped": "D5",
    "discipline_older alone widened": "R'",
    "conviction_recent alone widened by one month": "J'",
    "incarceration_recent alone widened by one month": "I'",
    "the date of application itself excluded from conviction_recent": "L'",
    "the date of application itself excluded from incarceration_recent": "Z'",
    "the date of application itself excluded from discipline_recent": "S'",
}


@needs_design
def test_480_unmutated_model_passes_groups_4_to_6(chk, model):
    _, drd = model
    fails, top = chk.semantic_failures(drd)
    assert fails == [] and top == []
    n, diff = chk.equivalence(drd)
    assert (n, diff) == (2 * 2 * 4 * 6 * 7, [])                    # dismissed x related x rehab x window x lookback


@needs_design
def test_480_residual_mutations_change_may_deny_for_the_applicant_added_for_them(chk, model):
    raw, _ = model
    assert sum(1 for m in chk.SEMANTIC_MUTATIONS if m[1] == "re-check") == 7
    assert sum(1 for m in chk.SEMANTIC_MUTATIONS if m[1] == "re-check 2") == 2
    assert {m[0] for m in chk.SEMANTIC_MUTATIONS if m[1] in ("re-check", "re-check 2", "sweep")} == {
        _mutation(chk, k)[0] for k in RESIDUAL}
    with tempfile.TemporaryDirectory() as tmp:
        for start, aid in RESIDUAL.items():
            label, _, mutate = _mutation(chk, start)
            changed, fails, top = chk.run_mutant(raw, mutate, Path(tmp) / "mutant.dmn")
            assert changed and fails, label
            assert aid in top, (label, top)                          # may_deny or basis changes for that applicant


@needs_design
def test_480_curated_comparison_evaluates_the_date_decisions(chk, model):
    """Group 6 no longer overrides the four date decisions: it realises within_seven_years by dates and present
    incarceration, so changes to the date literals reach it even where no applicant would see them."""
    from lxml import etree
    raw, _ = model
    assert "overrides" not in inspect.signature(chk.DRD.evaluate).parameters
    for did, old, new in (("d_incarceration_recent", "P7Y", "P8Y"), ("d_conviction_recent", "P7Y", "P8Y"),
                          ("d_incarceration_recent", "presently_incarcerated = true or ", "")):
        root = etree.fromstring(raw)
        chk.edit_literal(root, did, old, new)
        _, diff = chk.equivalence(chk.DRD(etree.fromstring(etree.tostring(root))))
        assert diff, (did, old, new)


@needs_design
def test_480_rule_annotations_mark_readings(chk, model):
    """discipline_ground r9 (no date, or a date after the application) rests on two implied readings; its Source
    annotation says so, as every rule with an implied source does."""
    from lxml import etree
    raw, drd = model
    root = etree.fromstring(raw)
    r9 = next(r for r in drd.tables["d_discipline_ground"].rules if r.id == "d_discipline_ground_r9")
    assert [s.grounding for s in r9.sources] == ["implied", "implied"]
    assert r9.annotation.startswith("Reading, not stated in the text:")
    for t in drd.tables.values():
        for r in t.rules:
            ann = root.xpath(f"//d:rule[@id='{r.id}']/d:annotationEntry/d:text/text()", namespaces=chk.NS)[0]
            assert ann == chk.annotation_for(r.sources), r.id
            assert (" (reading)" in ann) == any(s.grounding == "implied" for s in r.sources), r.id
    note = (ROOT / "docs" / "design" / "bpc-480-decision.md").read_text(encoding="utf-8")
    row9 = next(line for line in note.splitlines() if line.startswith("| 9 | `true` | `true` | `true` | `false` |"))
    assert "Q12 (reading)" in row9 and "Q17 (reading)" in row9


@needs_design
@pytest.mark.parametrize("did,aid", [("d_conviction_recent", "J'"), ("d_incarceration_recent", "I'")])
def test_480_windows_widened_by_under_seven_months_fail(chk, model, did, aid):
    """The second re-check of docs/design/verify-dmn-links.md widened the conviction and release windows to P7Y1M
    and P7Y6M with every check passing: no applicant was dated between 2019-03-02 and 2019-09-30.  J' and I' (the
    day before the anniversary) now catch every such widening, and with may_deny."""
    raw, _ = model
    with tempfile.TemporaryDirectory() as tmp:
        for new in ("P7Y1M", "P7Y3M", "P7Y6M"):
            changed, fails, top = chk.run_mutant(raw, lambda r: chk.edit_literal(r, did, "P7Y", new),
                                                 Path(tmp) / "mutant.dmn")
            assert changed and fails, (did, new)
            assert aid in top, (did, new, top)


@needs_design
def test_480_sweep_covers_months_signs_date_names_and_list_cells(chk, model):
    """The sweep moves each duration by every whole month up to a year either way (not only by a year), swaps the
    sign and the date names of the date literals, and negates and substitutes list cells as well as boolean ones;
    the month moves of the conviction and release windows are all caught."""
    from lxml import etree
    raw, drd = model
    changes = dict(chk.single_changes(drd))
    labels = set(changes)
    for did in drd.literals:
        months = {lb.split(" -> ")[1] for lb in labels if lb.startswith(f"{did}: P7Y -> ")}
        assert months == {chk._ym(84 + d) for d in [*range(-12, 0), *range(1, 13)]}, did
        assert {"P6Y", "P6Y11M", "P7Y1M", "P7Y6M", "P8Y"} <= months
        assert any(lb.startswith(f"{did}: - at ") and lb.endswith("-> +") for lb in labels), did
        assert any(lb.startswith(f"{did}: application_date at ") for lb in labels), did
    # every input cell that is not "-" has its negation in the sweep, list cells included (the checker's docstring)
    for t in drd.tables.values():
        for k, inp in enumerate(t.inputs):
            for r in t.rules:
                cell = r.inputs[k].strip()
                if cell == "-":
                    continue
                if inp.type_ref == "boolean":
                    neg = {"true": "false", "false": "true"}[cell]
                else:
                    neg = cell[4:-1] if cell.startswith("not(") else f"not({cell})"
                assert f"{r.id}[{inp.expression}]: {cell[:40]} -> {neg[:40]}" in labels, (r.id, inp.expression)
    assert 'd_conviction_ground_r2[disposition]: "conviction" -> "other"' in labels               # replaced
    assert 'd_exception_a_r2/d_exception_a_r3[sex_offender_tier]: "tier_two" replaced by "tier_one" in both' in labels
    doc = chk.__doc__
    assert "a boolean cell negated" in doc and "a list cell negated" in doc
    assert 'each input cell set to "-", negated' not in doc                       # the wording the verifier faulted
    for did in ("d_conviction_recent", "d_incarceration_recent"):
        for new in ("P7Y1M", "P7Y2M", "P7Y4M", "P7Y6M", "P6Y11M"):
            root = etree.fromstring(raw)
            changes[f"{did}: P7Y -> {new}"](root)
            assert chk.first_failure(chk.DRD(etree.fromstring(etree.tostring(root)))), (did, new)


@needs_design
def test_480_run_mutant_reports_a_mutation_whose_target_is_missing(chk, model, monkeypatch):
    """On a model edited so that a mutation's target text is gone (here the release bound that semantic mutation
    18 removes), run_mutant used to stop the whole checker with a LookupError traceback.  It now reports the mutant
    as not applied, check 9 prints it as a failing check, and the sweep counts such a change as not caught."""
    raw, _ = model
    label, _, mutate = _mutation(chk, "a release after the application counts")
    edited = raw.replace(b" and release_date &lt;= application_date", b"")
    assert edited != raw
    with tempfile.TemporaryDirectory() as tmp:
        changed, fails, top = chk.run_mutant(edited, mutate, Path(tmp) / "mutant.dmn")
    assert (changed, top) == (False, [])
    assert "cannot be applied" in fails[0] and "LookupError" in fails[0]
    ok, detail = chk.mutation_verdict(changed, fails, top)
    assert not ok and detail.startswith("the copy is unchanged: the mutation cannot be applied")
    assert chk.mutation_verdict(True, [], []) == (False, "NOT CAUGHT")
    assert chk.mutation_verdict(True, ["group 5"], ["Z"]) == (True, "caught by group 5; may_deny or basis changes for Z")
    bogus = ("d_conviction_recent: no such text", lambda r: chk.edit_literal(r, "d_conviction_recent", "nope", "x"))
    monkeypatch.setattr(chk, "single_changes", lambda drd: [bogus])
    n, caught, missed = chk.sweep(raw)
    assert (n, caught) == (1, {}) and missed[0].startswith("d_conviction_recent: no such text (cannot be applied")
