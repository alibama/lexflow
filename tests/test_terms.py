"""lexflow.law.terms: defined terms in literal statute text (sections of fixtures/xref/gold_*.json, Fla. Stat.
§ 607.0201 (Lexipedia Q168), and excerpts of the held-out and re-check sections in docs/design/verify-terms.md),
keys, and the review-only Wikidata classifier on fixed rows.  No index, network or model server."""
import hashlib
import importlib.util
import json
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from lexflow.law import terms as T

FL_119_011 = {"citation": "Fla. Stat. § 119.011", "original_title": "119.011 Definitions.",
              "path": "Florida Code / Title X / Chapter 119 / Section 119.011"}
FL_119_011_TEXT = (
    "As used in this chapter, the term:\n\n(1) “Actual cost of duplication” means the cost of the material and "
    "supplies used to duplicate the public record, but does not include labor cost or overhead cost associated with "
    "such duplication.\n\n(2) “Agency” means any state, county, district, authority, or municipal officer, "
    "department, division, board, bureau, commission, or other separate unit of government created or established "
    "by law.")

FL_607_0201 = {"citation": "Fla. Stat. § 607.0201", "original_title": "607.0201 Incorporators.",
               "path": "Florida Code / Title XXXVI / Chapter 607 / Part I / Section 607.0201"}
FL_607_0201_TEXT = ("One or more persons may act as the incorporator or incorporators of a corporation by delivering "
                    "articles of incorporation to the department for filing.\n\nHistory: s. 16, ch. 89-154; s. 16, "
                    "ch. 2019-90.")


def by_term(terms):
    out = {}
    for t in terms:
        out.setdefault(T.norm_term(t.term), []).append(t)
    return out


def test_chapter_lead_in_scopes_every_definition():
    got = by_term(T.definitions("fl", FL_119_011, FL_119_011_TEXT))
    assert set(got) == {"actual cost of duplication", "agency"}
    for t in (got["actual cost of duplication"][0], got["agency"][0]):
        assert t.kind == "means" and t.scope == "this chapter"
        assert t.scope_unit == "Florida Code / Title X / Chapter 119"
        assert FL_119_011_TEXT[t.start:t.end] == t.definition_span
    assert got["agency"][0].definition_span.startswith("“Agency” means any state")
    assert got["agency"][0].definition_span.endswith("established by law.")
    assert got["agency"][0].category == "role"


def test_incorporators_heading_and_acts_as_make_one_role():
    """Q168: the heading names the role and the text defines it by what the person does."""
    got = T.definitions("fl", FL_607_0201, FL_607_0201_TEXT)
    assert [(t.term, t.kind, t.source, t.category) for t in got] == [
        ("incorporator", "acts_as", "heading+text", "role")]
    t = got[0]
    assert t.scope_unit == "Florida Code / Title XXXVI / Chapter 607"
    assert t.definition_span.startswith("One or more persons may act as the incorporator")
    assert T.term_key("fl", "607.0201", t.term) == "lexflow:term:fl:607.0201:incorporator"
    assert T.concept_key("incorporator") == "lexflow:concept:incorporator"
    assert T.unit_key("fl", t.scope_unit) == "lexflow:unit:fl:florida-code-title-xxxvi-chapter-607"
    assert t.scope_basis == "path"


def test_role_heading_without_a_definition():
    row = {"citation": "Fla. Stat. § 605.0113", "original_title": "605.0113 Registered agent.",
           "path": "Florida Code / Title XXXVI / Chapter 605 / Section 605.0113"}
    text = ("(1) Each limited liability company and each foreign limited liability company that has a certificate of "
            "authority under s. 605.0902 shall designate and continuously maintain in this state: (a) A registered "
            "office, which may be the same as its place of business in this state; and (b) A registered agent, who "
            "must be: 1. An individual who resides in this state.")
    got = T.definitions("fl", row, text)
    assert [(t.term, t.kind, t.category) for t in got] == [("registered agent", "heading", "role")]
    assert got[0].start is None and got[0].term_start == text.index("registered agent")
    # a generic heading is not a term
    generic = dict(row, original_title="605.0112 Name.")
    assert T.definitions("fl", generic, "The name of a company must contain the words ...") == []


def test_subsection_scope_takes_the_enclosing_subsection():
    row = {"citation": "D.C. Code § 2-1402.66", "original_title": "Arrest records.",
           "path": "DC Code / Title 2 / Chapter 14 / § 2-1402.66"}
    text = ("(a) (1) (A) An individual may request production of his or her arrest record for the purposes of "
            "determining eligibility for sealing or expunging that record.\n    (B) The District may charge the "
            "individual a nominal fee for processing this request.\n    (C) For the purposes of this subsection, an "
            "“arrest record” shall contain a listing of all adult arrests, regardless of the disposition of each "
            "arrest.\n  (2) A person may request a copy.")
    t = by_term(T.definitions("dc", row, text))["arrest record"][0]
    assert (t.kind, t.scope, t.scope_unit, t.scope_pinpoint) == ("contents", "this subsection", row["path"], "(a)")
    assert t.source == "heading+text"


def test_explicit_subsection_and_section_of_this_act():
    row = {"citation": "5 ILCS 140/2", "original_title": "Section 2",
           "path": "Illinois Code / Chapter 5 / Act 140 / Section 2"}
    text = ('(g) "Recurrent requester", as used in Section 3.2 of this Act, means a person that, in the 12 months '
            'immediately preceding the request, has submitted to the same public body (i) a minimum of 50 requests for '
            'records. For the purposes of this subsection (g), "request" means a written document (or oral request, if '
            'the public body chooses to honor oral requests) that is submitted to a public body.')
    got = by_term(T.definitions("il", row, text))
    rr, req = got["recurrent requester"][0], got["request"][0]
    assert rr.scope_unit == "Illinois Code / Chapter 5 / Act 140 / Section 3.2"
    assert (req.scope_unit, req.scope_pinpoint) == (row["path"], "(g)")
    # the section part is the statute item's own key part (lexflow:statute:il:5 ILCS 140/2), so one derives the other
    assert T.term_key("il", "5 ILCS 140/2", req.term, req.scope_pinpoint) == "lexflow:term:il:5 ILCS 140/2:request@g"


def test_definitions_heading_unquoted_term_and_herein():
    row = {"citation": "N.C. Gen. Stat. § 132-1", "original_title": '"Public records" defined.',
           "path": "North Carolina Code / Chapter 132 / Section 132-1"}
    text = ('§ 132-1. "Public records" defined.\n\n(a) "Public record" or "public records" shall mean all documents, '
            'papers, letters, maps, books, photographs, films, sound recordings, made or received pursuant to law or '
            'ordinance in connection with the transaction of public business by any agency of North Carolina '
            'government or its subdivisions. Agency of North Carolina government or its subdivisions shall mean and '
            'include every public office, public officer or official (State or local, elected or appointed), '
            'institution, board, commission, bureau, council, department, authority or other unit of government of '
            'the State.\n\n(b) The people may obtain copies of their public records and public information free '
            'or at minimal cost unless otherwise specifically provided by law. As used herein, "minimal cost" shall '
            'mean the actual cost of reproducing the public record or public information.')
    got = by_term(T.definitions("nc", row, text))
    assert set(got) == {"public record", "agency of north carolina government or its subdivision", "minimal cost"}
    assert len(got["public record"]) == 1                      # "Public record" or "public records": one term
    assert got["public record"][0].scope_unit == "North Carolina Code / Chapter 132"   # from the heading
    assert got["agency of north carolina government or its subdivision"][0].kind == "means"
    assert got["minimal cost"][0].scope == "herein" and got["minimal cost"][0].scope_unit == row["path"]


def test_by_reference_list_definition_and_span_end():
    row = {"citation": "Tex. Government Code § 501.010", "original_title": "VISITORS.",
           "path": "TX Code / Code gv / Chapter 501 / Section 501.010"}
    text = ('(a) In this section:\n\n(1) "Guardian" has the meaning assigned by Section 1002.012, Estates Code.\n\n'
            '(2) "Letters of guardianship" means a certificate issued under Section 1106.001(a), Estates Code.\n\n'
            '(b) A visitor may enter at proper hours.')
    got = by_term(T.definitions("tx", row, text))
    g = got["guardian"][0]
    assert g.kind == "by_reference" and g.defined_in.startswith("Section 1002.012")
    assert g.definition_span == '"Guardian" has the meaning assigned by Section 1002.012, Estates Code.'
    assert got["letter of guardianship"][0].scope == "this section"
    assert got["visitor"][0].kind == "heading"

    md = {"citation": "Md. Code, Criminal Procedure § 6-219", "original_title": "",
          "path": "MD Code / Article gcp / Title 6 / Subtitle 2 / Section 6-219"}
    md_text = ("(a) In this section, “custodial confinement” means:\n\n(1) home detention;\n\n(2) a corrections "
               "options program established under law; or\n\n(3) inpatient drug or alcohol treatment.\n\n(b) "
               "Subject to subsection (c) of this section, a defendant shall receive credit.")
    (t,) = T.definitions("md", md, md_text)
    assert t.definition_span.endswith("inpatient drug or alcohol treatment.")


def test_the_words_construction_rules_and_parenthetical():
    row = {"citation": "N.C. Gen. Stat. § 57D-10-02",
           "original_title": "Rules of construction; coordination with other law.",
           "path": "North Carolina Code / Chapter 57D / Section 57D-10-02"}
    text = ('(e) In this Chapter, unless otherwise specified or indicated by the context, including as may otherwise '
            'be provided in the operating agreement under Part 3 of Article 2 of this Chapter, without the need for '
            'repetitious use of qualifiers, further statement, or clarification in the text of any provision of this '
            'Chapter, the following rules of construction shall apply:\n\n(3) The words "this Chapter," "hereof," '
            '"hereby," "hereunder," "herein," and words of similar impact are to be read to refer to Chapter 57D of '
            'the General Statutes as a whole.\n\n(5) The words "or" and "any" are not exclusive.')
    got = by_term(T.definitions("nc", row, text))
    assert {"this chapter", "hereof", "hereby", "hereunder", "herein", "or", "any"} <= set(got)
    assert {t.scope_unit for ts in got.values() for t in ts} == {"North Carolina Code / Chapter 57D"}

    dc = {"citation": "D.C. Code § 47-2853.04", "original_title": "Regulated non-health related occupations.",
          "path": "DC Code / Title 47 / Chapter 28 / § 47-2853.04"}
    dc_text = ("and teachers and instructional employees of the University of the District of Columbia "
               "(“University”) by the Board.")
    (u,) = [t for t in T.definitions("dc", dc, dc_text) if t.kind == "parenthetical"]
    assert u.term == "University" and u.definition_span == "University of the District of Columbia (“University”)"


@pytest.mark.parametrize("path,citation,phrase,want", [
    ("New York Code / Act LLC / Article 2 - Formation / Section 203", "N.Y. LLC Law § 203", "this chapter",
     "New York Code / Act LLC"),
    ("TX Code / Code cr / Chapter 42 / Section 42.21", "Tex. Code of Criminal Procedure § 42.21", "this article",
     "TX Code / Code cr / Chapter 42 / Section 42.21"),
    ("MD Code / Article gtr / Title 26 / Subtitle 2 / Section 26-204", "Md. Code, Transportation § 26-204",
     "this article", "MD Code / Article gtr"),
    ("California Code / Code pen / Part 3 / Title 6 / Chapter 3.5 / Section 4852.01", "Cal. PEN § 4852.01",
     "this code", "California Code / Code pen"),
    ("DC Code / Title 47 / Chapter 28 / § 47-2853.48", "D.C. Code § 47-2853.48", "this part", None),
])
def test_scope_path(path, citation, phrase, want):
    assert T.scope_path({"path": path, "citation": citation}, phrase)[0] == want


# ------------------------------------------------------------------ held-out forms (docs/design/verify-terms.md)
def test_plural_the_terms_include():
    """Fla. Stat. § 627.652 lost seven terms: bare plural 'include' was not a definition verb."""
    row = {"citation": "Fla. Stat. § 627.652", "original_title": "627.652 Group health insurance; definitions.",
           "path": "Florida Code / Title XXXVII / Chapter 627 / Part VII / Section 627.652", "section_number": "627.652"}
    text = ("As used in this part:\n\n(1) Group health insurance is that form of health insurance covering groups of "
            "persons under a master group health insurance policy.\n\n(2)(a) The terms “policy,” “insurance policy,” "
            "“health insurance policy,” “group health policy,” and “group health insurance policy” include plans of "
            "self-insurance providing health insurance benefits. (b) The terms “amount of insurance” and “insurance” "
            "include the benefits provided under a plan of self-insurance. (c) The term “insurer” includes any person "
            "or governmental unit providing a plan of self-insurance.")
    got = by_term(T.definitions("fl", row, text))
    part = "Florida Code / Title XXXVII / Chapter 627 / Part VII"
    assert set(got) == {"group health insurance", "policy", "insurance policy", "health insurance policy",
                        "group health policy", "group health insurance policy", "amount of insurance", "insurance",
                        "insurer"}
    assert all(t.kind == "includes" and t.scope_unit == part for n, ts in got.items() for t in ts
               if n != "group health insurance")
    # 'and' lists share a definition; they are not synonyms of each other
    assert got["policy"][0].alternatives == []
    # the heading term is defined as item (1) under the lead-in, so it governs the part too
    (g,) = got["group health insurance"]
    assert (g.kind, g.scope, g.scope_unit) == ("heading", "this part", part)
    assert T.definitions("fl", row, 'As used in this part, "plan" and "program" do not include a trust.')[0].kind \
        == "excludes"


def test_in_construing_this_chapter():
    row = {"citation": "Fla. Stat. § 585.001", "original_title": "585.001 Definitions.",
           "path": "Florida Code / Title XXXV / Chapter 585 / Part I / Section 585.001"}
    text = ("In construing this chapter, where the context permits, the term “department” means the Department of "
            "Agriculture and Consumer Services.")
    (t,) = T.definitions("fl", row, text)
    assert (t.scope, t.scope_unit, t.scope_basis) == ("this chapter", "Florida Code / Title XXXV / Chapter 585", "path")


@pytest.mark.parametrize("state,row,text,phrase,unit", [
    ("dc", {"citation": "D.C. Code § 2-1561", "original_title": "Definitions.", "section_number": "2-1561",
            "path": "DC Code / Title 2 / Chapter 15 / § 2-1561"},
     "For the purposes of this subchapter, the term:\n(1) “Youth” means an individual who is at least 13 years of "
     "age.\n(2) “Youth Council” means the District of Columbia Youth Advisory Council.",
     "this subchapter", "DC Code / Title 2 / Chapter 15 / Subchapter containing § 2-1561"),
    ("tx", {"citation": "Tex. Education Code § 21.032", "original_title": "DEFINITION.", "section_number": "21.032",
            "path": "TX Code / Code ed / Chapter 21 / Section 21.032"},
     'In this subchapter, "board" means the State Board for Educator Certification.',
     "this subchapter", "TX Code / Code ed / Chapter 21 / Subchapter containing § 21.032"),
    ("nc", {"citation": "N.C. Gen. Stat. § 143B-1241", "original_title": "Definition.", "section_number": "143B-1241",
            "path": "North Carolina Code / Chapter 143B / Section 143B-1241"},
     '§ 143B-1241. Definition.\n\nAs used in this Part, "veteran" means any person who may be entitled to any '
     "benefits or rights under the laws of the United States.",
     "this Part", "North Carolina Code / Chapter 143B / Part containing § 143B-1241"),
    ("fl", {"citation": "Fla. Stat. § 606.03", "original_title": "606.03 Definitions.", "section_number": "606.03",
            "path": "Florida Code / Title XXXVI / Chapter 606 / Section 606.03"},
     "As used in this act:\n\n(1) “Business entity” means any form of corporation.\n\n(2) “Department” means the "
     "Department of State.",
     "this act", "Florida Code / Title XXXVI / Chapter 606 / Act containing § 606.03"),
])
def test_a_level_the_path_lacks_is_anchored_to_the_section(state, row, text, phrase, unit):
    """These scopes were None: the index path has no subchapter, Article, Part or act level.  An act, whose extent
    is unknown, is anchored under the section's own enclosing unit."""
    got = T.definitions(state, row, text)
    assert got and {(t.scope, t.scope_unit, t.scope_basis) for t in got} == {(phrase, unit, "anchored")}


def test_nc_following_definitions_apply_and_dash_items():
    """N.C. Gen. Stat. § 160D-1202: 'The following definitions apply in this Article:' and 'Owner. - The holder'."""
    row = {"citation": "N.C. Gen. Stat. § 160D-1202", "original_title": "Definitions.", "section_number": "160D-1202",
           "path": "North Carolina Code / Chapter 160D / Section 160D-1202"}
    text = ("§ 160D-1202. Definitions.\n\nThe following definitions apply in this Article:\n\n(1) Owner. - The holder "
            "of the title in fee simple and every mortgagee of record.\n\n(2) Parties in interest. - All individuals, "
            "associations, and corporations that have interests of record in a dwelling.\n\n(3) Public officer. - The "
            "officer authorized by ordinances adopted under this Article.")
    got = T.definitions("nc", row, text)
    assert [t.term for t in got] == ["Owner", "Parties in interest", "Public officer"]
    unit = "North Carolina Code / Chapter 160D / Article containing § 160D-1202"
    assert all((t.kind, t.scope, t.scope_unit) == ("means", "this Article", unit) for t in got)
    assert got[0].definition_span == "Owner. - The holder of the title in fee simple and every mortgagee of record."
    # a caption outside a definitions list is no term
    plain = {"citation": "N.C. Gen. Stat. § 160D-1203", "original_title": "Powers.",
             "path": "North Carolina Code / Chapter 160D / Section 160D-1203"}
    assert T.definitions("nc", plain, "(a) Applicability. - This Article applies to dwellings.\n\n(b) Repairs. - "
                                      "The officer may order repairs.") == []
    # "shall be defined to include" (N.C. Gen. Stat. § 14-58.1)
    row2 = {"citation": "N.C. Gen. Stat. § 14-58.1", "original_title": 'Definition of "house" and "building."',
            "section_number": "14-58.1", "path": "North Carolina Code / Chapter 14 / Section 14-58.1"}
    got2 = T.definitions("nc", row2, 'As used in this Article, the terms "house" and "building" shall be defined to '
                                     "include mobile and manufactured-type housing.")
    assert [(t.term, t.kind) for t in got2] == [("house", "includes"), ("building", "includes")]


def test_definitions_in_this_section_apply_throughout_this_chapter():
    row = {"citation": "RCW 43.150.030", "original_title": "",
           "path": "Washington Code / Title 43 / Chapter 150 / Section 030"}
    text = ('Unless the context clearly requires otherwise, the definitions in this section apply throughout this '
            'chapter. (1) "Volunteer" means a person who is willing to work without expectation of salary. (2) '
            '"Center" means the state center for volunteerism and citizen service.')
    got = T.definitions("wa", row, text)
    assert {(t.scope, t.scope_unit, t.scope_basis) for t in got} == {
        ("this chapter", "Washington Code / Title 43 / Chapter 150", "path")}


def test_maryland_ucc_general_definitions_scope_to_the_maryland_ucc():
    """Md. Code, Com. Law § 1-201 governs Titles 1-10 of the article (§ 1-101(a)), not 'this section'; and one key
    keeps all three definitions of "Security interest"."""
    row = {"citation": "Md. Code, Commercial Law § 1-201", "original_title": "", "section_number": "1-201",
           "ref": "Md. Code, Commercial Law § 1-201",
           "path": "MD Code / Article gcl / Title 1 / Subtitle 2 / Section 1-201"}
    text = ("(a) Unless the context otherwise requires, words or phrases defined in this section, or in the additional "
            "definitions contained in other titles of the Maryland Uniform Commercial Code that apply to particular "
            "titles or parts of titles of the Maryland Uniform Commercial Code, have the meanings stated.\n\n(b) "
            "Subject to definitions contained in other articles of the Maryland Uniform Commercial Code that apply to "
            "particular titles or parts of titles of the Maryland Uniform Commercial Code:\n\n(2) “Aggrieved party” "
            "means a party entitled to pursue a remedy.\n\n(3) “Agreement”, as distinguished from “contract”, means "
            "the bargain of the parties in fact.\n\n(8) “Burden of establishing” a fact means the burden of "
            "persuading the trier of fact.\n\n(35) “Security interest” means an interest in personal property or "
            "fixtures that secures payment or performance of an obligation. “Security interest” includes any "
            "interest of a consignor. “Security interest” does not include the special property interest of a buyer "
            "of goods.\n\n(36) “Send” in connection with a writing, record, or notice means to deposit in the mail.")
    got = T.definitions("md", row, text)
    assert {T.norm_term(t.term) for t in got} == {"aggrieved party", "agreement", "burden of establishing",
                                                   "security interest", "send"}
    assert {(t.scope, t.scope_unit, t.scope_basis) for t in got} == {
        ("the Maryland Uniform Commercial Code", "MD Code / Article gcl / Titles 1-10", "named")}
    keys = T.group_by_key("md", row["ref"], got)
    si = keys["lexflow:term:md:Md. Code, Commercial Law § 1-201:security-interest"]
    assert [t.kind for t in si] == ["means", "includes", "excludes"]
    assert len(keys) == 5 and sum(len(v) for v in keys.values()) == len(got) == 7
    # the name is read only inside the unit it names
    other = dict(row, path="MD Code / Article gcl / Title 13 / Subtitle 1 / Section 13-101")
    assert T.resolve_scope("md", other, "the Maryland Uniform Commercial Code") == (None, None, None)


@pytest.mark.parametrize("state,path,phrase,want", [
    ("fl", "Florida Code / Title XXXIX / Chapter 671 / Part II / Section 671.201", "this code",
     ("Florida Code / Title XXXIX / Chapters 669-680", None, "named")),
    ("fl", "Florida Code / Title XLVII / Chapter 945 / Section 945.01", "this code", ("Florida Code", None, "path")),
    ("va", "Virginia Code / Title 8.1A / Part 2 / Section 8.1A-201", "the Uniform Commercial Code",
     ("Virginia Code / Titles 8.1A-8.9A", None, "named")),
    ("dc", "DC Code / Title 47 / Chapter 28 / § 47-2853.48", "this part",
     ("DC Code / Title 47 / Chapter 28 / Part containing § 47-2853.48", None, "anchored")),
    ("tx", "TX Code / Code bc / Chapter 1 / Section 1.201", "this title",
     ("TX Code / Code bc / Title containing § 1.201", None, "anchored")),
    ("ny", "New York Code / Act GOB / Article 13 / Title 1 / Section 13-109", "sections 13-101, 13-103 and 13-107",
     (None, None, None)),
    # anchored under the right parent (re-check, item 5): Maryland's "Article" is a whole code, so its part lies in
    # the subtitle; an Illinois article lies in its Act; an act under the section's own unit; a Texas subtitle in
    # its code
    ("md", "MD Code / Article ggp / Title 5 / Subtitle 8 / Section 5-857", "this part",
     ("MD Code / Article ggp / Title 5 / Subtitle 8 / Part containing § 5-857", None, "anchored")),
    ("il", "Illinois Code / Chapter 105 / Act 5 / Section 34-1.1", "this Article",
     ("Illinois Code / Chapter 105 / Act 5 / Article containing § 34-1.1", None, "anchored")),
    ("va", "Virginia Code / Title 15.2 / Subtitle IV / Chapter 66 / Section 15.2-6602", "this act",
     ("Virginia Code / Title 15.2 / Subtitle IV / Chapter 66 / Act containing § 15.2-6602", None, "anchored")),
    ("tx", "TX Code / Code bc / Chapter 1 / Section 1.201", "this subtitle",
     ("TX Code / Code bc / Subtitle containing § 1.201", None, "anchored")),
    ("nc", "North Carolina Code / Chapter 143 / Section 143-212",
     "this Article and Articles 21A and 21B of this Chapter", (None, None, "compound")),
])
def test_resolve_scope(state, path, phrase, want):
    assert T.resolve_scope(state, {"path": path}, phrase) == want


def test_a_list_of_sections_is_no_unit_and_hard_wrapped_lines_keep_the_scope():
    """N.Y. Gen. Oblig. Law § 13-109 was scoped to its title from the heading; the text names four sections."""
    row = {"citation": "N.Y. GOB Law § 13-109", "original_title": 'Definition of "transfer',
           "path": "New York Code / Act GOB / Article 13 / Title 1 / Section 13-109"}
    text = ('§ 13-109. Definition of "transfer." As used in sections 13-101,\n13-103, 13-105 and 13-107, the term '
            '"transfer" includes sale,\nassignment, conveyance, deed and gift.')
    (t,) = T.definitions("ny", row, text)
    assert (t.term, t.kind, t.scope_unit, t.scope_basis) == ("transfer", "includes", None, None)
    assert t.scope == "sections 13-101, 13-103, 13-105 and 13-107"
    # a section number in words (N.Y. Educ. Law § 6901); it was scoped to the article from the heading
    edn = {"citation": "N.Y. EDN Law § 6901", "original_title": "Definitions",
           "path": "New York Code / Act EDN / Title 8 / Article 139 / Section 6901"}
    got = T.definitions("ny", edn, '§ 6901. Definitions.  As used in section sixty-nine hundred two:\n  2. "Treating" '
                                   "means selection and performance of those therapeutic measures.")
    assert [(t.term, t.scope, t.scope_unit, t.scope_basis) for t in got] == [
        ("Treating", "section sixty-nine hundred two", None, None)]
    # "For purposes of this article, the following terms shall have the following meanings:" is a lead-in
    row2 = {"citation": "N.Y. ENV Law § 19-1101", "original_title": "Definitions",
            "path": "New York Code / Act ENV / Article 19 / Title 11 / Section 19-1101"}
    text2 = ('§ 19-1101. Definitions.\n  For purposes of this article, the following terms shall have the\n'
             'following meanings:\n  1. "motor vehicle" shall mean a passenger vehicle; and\n  2. "motor vehicle '
             'global warming gases" or "global warming gases"\nshall mean carbon dioxide and methane.')
    got = by_term(T.definitions("ny", row2, text2))
    assert {t.scope_unit for ts in got.values() for t in ts} == {"New York Code / Act ENV / Article 19"}
    # '"X" or "Y" means': each names the other as an alternative
    assert got["global warming gas"][0].alternatives == ["motor vehicle global warming gases"]
    assert got["motor vehicle global warming gas"][0].alternatives == ["global warming gases"]


def test_norm_term_folds_quotes_case_and_plurals():
    assert T.norm_term("“Public records”") == T.norm_term("public record") == "public record"
    assert T.norm_term("Incorporators") == "incorporator"
    # not the crude "drop the s": these were 'gase', 'statuse' and 'damage'
    assert T.norm_term("Motor vehicle global warming gases") == "motor vehicle global warming gas"
    assert T.norm_term("statuses") == "status" and T.norm_term("analyses") == "analysis"
    assert T.norm_term("Damages") == "damages" and T.norm_term("premises") == "premises"


def test_keys_are_frozen_and_never_fold_plurals():
    """Keys do not go through norm_term: a quoted term keys as written."""
    assert T.KEY_VERSION == 1
    assert T.slug("gases") == "gases" and T.slug("Damages") == "damages" and T.slug("statuses") == "statuses"
    assert T.slug("Owner’s agent") == "owner-s-agent"         # literal, like lexflow.law.links' definition keys
    assert T.concept_key("damages") != T.concept_key("damage")
    assert T.term_key("ny", "N.Y. ENV Law § 19-1101", "global warming gases") == \
        "lexflow:term:ny:N.Y. ENV Law § 19-1101:global-warming-gases"
    # a homonym gets the reviewer's sense as a suffix; agency law keeps the bare key
    assert T.concept_key("agency", "public records") == "lexflow:concept:agency--public-records"
    assert T.concept_key("agency") == "lexflow:concept:agency"
    assert T.concept_key("agency", "") == "lexflow:concept:agency"


# ------------------------------------------------------------------ the link classifier
INCORPORATOR_PROPBANK = {"qid": "Q140403634", "label": "incorporator", "label_lang": "en", "sitelinks": 0, "rank": 1,
                         "description": 'prototypical agent (PAG) for predicate "mainstream.01": incorporate into '
                                        "popular culture", "aliases": [], "p31": [],
                         "p279": [{"qid": "Q134480019", "label": "proto-agent"}], "jurisdiction": []}
REGISTERED_AGENT = {"qid": "Q7309406", "label": "registered agent", "label_lang": "en", "sitelinks": 2, "rank": 1,
                    "description": "in the US, receives service of process for a party in a legal action",
                    "aliases": [], "p31": [], "p279": [{"qid": "Q835173", "label": "legal agent"}], "jurisdiction": []}
FEDERAL_APA = {"qid": "Q25344901", "label": "Administrative Procedure Act", "label_lang": "en", "sitelinks": 4,
               "rank": 1, "description": "United States statute enacted in 1946",
               "aliases": ["Administrative Procedure Act of 1946", "Administrative Procedures Act"],
               "p31": [{"qid": "Q476068", "label": "Act of Congress in the United States"}], "p279": [],
               "jurisdiction": [{"qid": "Q30", "label": "United States"}]}


def row(**on):
    base = {f: 0.0 for f in T.FEATURES}
    base.update({"rank_recip": 1.0, "sitelinks": 0.5, "most_sitelinks_match": 1.0, "jaccard": 1.0})
    base.update(on)
    return base


def test_model_constant_matches_the_feature_list():
    m = T.LINK_MODEL
    assert m["features"] == T.FEATURES and len(m["mu"]) == len(m["sd"]) == len(T.FEATURES) == len(m["beta"]) - 1
    # review-only: one threshold, for the review queue; none claims to make unreviewed links safe.  It is the fixed
    # even-odds point, not a value tuned on the survey's scores (the 0.90-precision threshold, 0.7607, was placed by
    # the incorporator's own label)
    assert "threshold" not in m and m["review_threshold"] == T.REVIEW_THRESHOLD == 0.5
    assert T.default_model() is m


def test_no_cue_list_names_propbank():
    """The PropBank tokens encoded the survey's answers (5 pairs, all wrong); general features decide now."""
    desc = INCORPORATOR_PROPBANK["description"] + " | proto-agent | proto-patient | PropBank semantic role"
    assert not T._JUNK.search(desc) and not T._CLASS_NEG.search(desc)
    f = T.candidate_features("incorporator", INCORPORATOR_PROPBANK, peers=[INCORPORATOR_PROPBANK])
    assert f["desc_junk"] == 0.0 and f["class_neg"] == 0.0 and f["desc_legal"] == 0.0 and f["sitelinks"] == 0.0


def test_fixed_feature_rows():
    legal = row(lm_exact=1.0, desc_legal=1.0, desc_person=1.0, class_pos=0.5, class_position=1.0, jur_us=1.0)
    junk = row(lm_exact=1.0, desc_junk=1.0, class_neg=1.0, sitelinks=0.0)
    statute = row(lm_exact=1.0, desc_legal=1.0, p31_statute=1.0, desc_law_instance=1.0)
    foreign = row(lm_exact=1.0, desc_legal=1.0, desc_foreign=1.0, jur_foreign=1.0)
    p_legal, p_junk, p_statute, p_foreign = T.predict(T.LINK_MODEL, [legal, junk, statute, foreign])
    assert p_legal > T.LINK_MODEL["review_threshold"]
    assert p_junk < 0.15
    assert p_statute < p_legal and p_foreign < p_legal
    assert T.predict(T.LINK_MODEL, [row(lm_partial=1.0, jaccard=0.3, most_sitelinks_match=0.0)])[0] < 0.2


def test_link_is_a_review_suggestion():
    # the default threshold is the review threshold
    qid, p = T.link("registered agent", [REGISTERED_AGENT])
    assert qid == "Q7309406" and p > 0.9
    assert T.link("registered agent", [REGISTERED_AGENT], threshold=0.999)[0] is None
    assert T.suggest is T.link
    # with no PropBank rule, the PropBank "incorporator" scores 0.69 from general features: above the fixed review
    # threshold, so it is queued, and the reviewer, not the score, keeps it out
    qid, p = T.link("incorporator", [INCORPORATOR_PROPBANK])
    assert qid == "Q140403634" and T.LINK_MODEL["review_threshold"] < p < 0.75
    # the federal 1946 Act is a specific statute, not Texas's Administrative Procedure Act.  As the only hit it
    # reaches the queue (p 0.66), and the reviewer rejects it; among the survey's real search results, four other
    # countries' same-label Acts, it scores 0.25 and is not queued
    qid, p = T.link("Administrative Procedure Act", [FEDERAL_APA])
    assert qid == "Q25344901" and p < T.link("registered agent", [REGISTERED_AGENT])[1]
    hits = [x["cand"] for x in T.survey_pairs() if x["term"] == "Administrative Procedure Act"]
    assert hits[0]["qid"] == "Q25344901" and T.link("Administrative Procedure Act", hits)[0] is None
    assert T.link("anything", []) == (None, 0.0)


def test_bare_items_are_never_linked():
    bare = {"qid": "Q11497746", "label": "Ability-to-pay", "description": None, "aliases": [], "p31": [], "p279": [],
            "sitelinks": 1, "rank": 1}
    assert T.unlinkable(bare)
    assert T.link("ability to pay", [bare], threshold=0.0)[1] == 0.0


def test_candidate_from_entity_reads_wbgetentities():
    entity = {"labels": {"mul": {"language": "mul", "value": "registered agent"}},
              "descriptions": {"en": {"language": "en", "value": "in the US, receives service of process"}},
              "aliases": {"en": [{"language": "en", "value": "statutory agent"}]},
              "claims": {"P279": [{"mainsnak": {"datavalue": {"value": {"id": "Q835173"}}}}],
                         "P17": [{"mainsnak": {"datavalue": {"value": {"id": "Q30"}}}}]},
              "sitelinks": {"enwiki": {}, "dewiki": {}}}
    c = T.candidate_from_entity("Q7309406", entity, {"Q835173": "legal agent", "Q30": "United States"})
    assert c["label"] == "registered agent" and c["label_lang"] == "mul" and c["sitelinks"] == 2
    assert c["p279"] == [{"qid": "Q835173", "label": "legal agent"}]
    assert c["jurisdiction"] == [{"qid": "Q30", "label": "United States"}]
    f = T.candidate_features("statutory agent", c, peers=[c])
    assert f["lm_alias"] == 1.0 and f["jur_us"] == 1.0 and f["label_mul_only"] == 1.0


def test_fit_lr_learns_the_sign():
    import numpy as np
    rng = np.random.default_rng(0)
    x = rng.normal(size=(200, 2))
    y = (x[:, 0] > 0).astype(float)
    beta, mu, sd = T.fit_lr(x, y, l2=1.0)
    assert beta[0] > 2 and abs(beta[1]) < 1


# ------------------------------------------------------------------ re-check fixes (docs/design/verify-terms.md)
ROOT = Path(__file__).resolve().parents[1]
NC_14_107_1_REASONS = (
    "(e) The reason for dishonor may be indicated with terms that include, but are not limited to, the following: "
    '"insufficient funds," "no account," "account closed," "NSF," "uncollected," "unable to locate," "stale dated," '
    '"postdated," "endorsement irregular," "signature irregular," "nonnegotiable," "altered," "unable to process," '
    '"refer to maker," "duplicate presentment," "forgery," "noncompliant," or "UCD noncompliant." The fact that the '
    "check or draft was returned dishonored may be received as evidence.")


def test_long_quoted_lists_take_linear_time():
    """N.C. Gen. Stat. § 14-107.1's 18 quoted reasons for dishonor, with no definition verb, never finished: the
    old separator split each space three ways and a failed match retried every split.  Run in a child process, so
    a regression fails on the timeout instead of hanging the suite."""
    code = textwrap.dedent(f"""
        import sys, time
        sys.path.insert(0, {str(ROOT)!r})
        from lexflow.law import terms as T
        row = {{"citation": "N.C. Gen. Stat. § 14-107.1", "path": "North Carolina Code / Chapter 14 / Section 14-107.1",
               "original_title": "Prima facie evidence in worthless check cases."}}
        long = "The terms that apply are: " + ", ".join(f'"item {{k}},"' for k in range(60)) + " and others."
        t = time.time()
        a = T.definitions("nc", row, {NC_14_107_1_REASONS!r})
        b = T.definitions("nc", row, long)
        print(len(a), len(b), time.time() - t)
    """)
    try:
        out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=60, cwd=ROOT)
    except subprocess.TimeoutExpired:
        pytest.fail("definitions() did not finish a long quoted list in 60 s")
    assert out.returncode == 0, out.stderr
    n_a, n_b, elapsed = out.stdout.split()
    assert (n_a, n_b) == ("0", "0") and float(elapsed) < 2.0          # no verb: no terms, and quickly


@pytest.mark.parametrize("text,listed", [
    ('"Public record" or "public records" means', '"Public record" or "public records"'),
    ('"Alpha," "beta," and "gamma" mean', '"Alpha," "beta," and "gamma"'),
    ('"A", "B", or "C" means', '"A", "B", or "C"'),
    ('"A" and/or "B" means', '"A" and/or "B"'),
    ('"A"; "B"; and "C" mean', '"A"; "B"; and "C"'),
    ('“A” or“B” means', '“A” or“B”'),
])
def test_the_list_separator_still_matches_the_same_lists(text, listed):
    assert T.DEF_A.match(text).group("list") == listed


NC_14_150_3 = {"citation": "N.C. Gen. Stat. § 14-150.3", "original_title": "Injuring manufacturing facility.",
               "path": "North Carolina Code / Chapter 14 / Section 14-150.3"}
NC_14_150_3_TEXT = (
    "§ 14-150.3. Injuring manufacturing facility.\n\n(a) Injuring a Manufacturing Facility. - It is unlawful to "
    "knowingly and willfully damage the property or equipment of a manufacturing facility. For purposes of this "
    'section: (i) the term "manufacturing facility" means a facility used for the lawful production or '
    'manufacturing of goods; and (ii) the term "property or equipment" shall include hardware, software, or other '
    "digital infrastructure.\n\n(b) Punishment. - A person who violates subsection (a) of this section is guilty of a "
    "Class C felony.\n\n(c) Merger. - Each violation of this section constitutes a separate offense.\n\n(d) Civil "
    "Remedies. - Any person whose property is injured by reason of a violation of subsection (a) of this section "
    "shall have a right of action.")


def test_a_lead_ins_list_ends_so_later_captions_are_no_terms():
    """Re-check item 1: 'For purposes of this section:' inside (a) used to make every later caption a definition."""
    got = T.definitions("nc", NC_14_150_3, NC_14_150_3_TEXT)
    assert {t.term for t in got if t.kind != "heading"} == {"manufacturing facility", "property or equipment"}
    doc = T._Doc(NC_14_150_3_TEXT)
    assert doc.list_lead_at(NC_14_150_3_TEXT.index("(i) the term")) == "this section"
    assert doc.list_lead_at(NC_14_150_3_TEXT.index("Punishment")) is None
    assert doc.lead_at(NC_14_150_3_TEXT.index("Punishment")) == "this section"     # a quoted scope still inherits


def test_definitions_under_a_caption_keep_their_list_and_lose_the_captions_after_it():
    """N.C. Gen. Stat. § 105-130.46: '(b) Definitions. - The following definitions apply in this section:' and then
    the captions (c) Credit, (d) Allocation."""
    row = {"citation": "N.C. Gen. Stat. § 105-130.46", "original_title": "Credit for manufacturing cigarettes for "
           "exportation while increasing employment and utilizing State Ports.",
           "path": "North Carolina Code / Chapter 105 / Section 105-130.46"}
    text = ("(a) Purpose. - The credit authorized by this section is intended to enhance the economy of this State.\n\n"
            "(b) Definitions. - The following definitions apply in this section:\n\n(1) Employment level. - The total "
            "number of full-time jobs and part-time jobs converted into full-time equivalences.\n\n(2) Exportation. - "
            "The shipment of cigarettes manufactured in the United States to a foreign country.\n\n(c) Credit. - A "
            "taxpayer that manufactures cigarettes for exportation is allowed a credit.\n\n(d) Allocation. - The "
            "credit is allocated to the State.")
    got = T.definitions("nc", row, text)
    assert [(t.term, t.kind, t.scope) for t in got] == [("Employment level", "means", "this section"),
                                                        ("Exportation", "means", "this section")]
    # a list item's own inner lead-in ends at the next item: '(2) Undue hardship' is the Chapter's, not '(1)'s
    # (N.C. Gen. Stat. § 168A-3 has this layout at its items (10) and (11))
    row2 = {"citation": "N.C. Gen. Stat. § 168A-3", "original_title": "Definitions.",
            "path": "North Carolina Code / Chapter 168A / Section 168A-3"}
    text2 = ("§ 168A-3. Definitions.\n\nThe following definitions apply in this Chapter:\n\n(1) Reasonable "
             "accommodations. - Making facilities accessible. As used in this subdivision, the following terms "
             'apply:\n\na. "Readily accessible" means usable by persons with disabilities.\n\n(2) Undue hardship. - '
             "A significant difficulty or expense.")
    got2 = {t.term: t for t in T.definitions("nc", row2, text2)}
    assert (got2["Readily accessible"].scope, got2["Readily accessible"].scope_pinpoint) == ("this subdivision",
                                                                                            "(1)")
    assert (got2["Undue hardship"].scope, got2["Undue hardship"].scope_unit) == ("this Chapter",
                                                                                 "North Carolina Code / Chapter 168A")


@pytest.mark.parametrize("title,text", [
    ("Definitions; description of boundaries.",
     '(a) As used in this Article, "district" means a water district.\n\n(b) Description of Boundaries. - Whenever '
     "this Article requires that the boundaries of a district be described, a map suffices."),
    ("Definition of service districts.",
     "(a) Standards. - The board of commissioners may define a county service district.\n\n(b) Hearing and Notice. "
     "- The board shall hold a public hearing."),
    ("Definitions and administration.",
     "(a) The following words have the listed meaning in this Article:\n\n(1) Supervisee. - A person released from "
     "incarceration.\n\n(b) Administration. - The Commission shall administer post-release supervision."),
])
def test_a_heading_not_about_definitions_alone_lists_nothing(title, text):
    """Captions under 'Definitions; X.' and 'Definition of X.' headings are no terms; N.C. Gen. Stat. § 15A-1368's
    'The following words have the listed meaning in this Article:' is a lead-in, so (b) is outside its list."""
    row = {"citation": "N.C. Gen. Stat. § 1-1", "original_title": title,
           "path": "North Carolina Code / Chapter 1 / Section 1-1"}
    dash = {t.term for t in T.definitions("nc", row, text)
            if t.kind == "means" and not any(q in (t.definition_span or "") for q in '“"')}
    assert dash == ({"Supervisee"} if "listed meaning" in text else set())


def test_a_dash_caption_that_quotes_its_term_gives_one_term():
    """D.C. Code § 38-2704: '(3) Mayor. — The term “Mayor” means' is the quoted definition, not a second Term."""
    row = {"citation": "D.C. Code § 38-2704", "original_title": "Private school program.",
           "path": "DC Code / Title 38 / Chapter 27 / § 38-2704"}
    text = ("(e) Definitions. — For purposes of this section:\n  (3) Mayor. — The term “Mayor” means the Mayor of the "
            "District of Columbia.\n  (4) Secretary. — The term “Secretary” means the Secretary of Education.")
    got = T.definitions("dc", row, text)
    assert [(t.term, t.kind) for t in got] == [("Mayor", "means"), ("Secretary", "means")]
    assert got[0].definition_span.startswith("The term “Mayor” means")          # the quoted one, not the caption


def test_a_dash_item_that_quotes_its_term_with_no_definition_verb_is_kept():
    """Re-check 2, item 1: N.C. Gen. Stat. § 81A-9 lost all 22 such items, and § 20-286 its "Sell": the quoted term
    is followed by "is" or "are synonymous", no definition verb, so the dash item is the only Term."""
    row = {"citation": "N.C. Gen. Stat. § 81A-9", "original_title": "Definitions.", "section_number": "81A-9",
           "path": "North Carolina Code / Chapter 81A / Section 81A-9"}
    text = ("§ 81A-9. Definitions.\n\nThe following words and phrases as used in this Chapter, unless a different "
            "meaning is plainly required by the context, shall have the following meanings:\n\n(1) Adjustment. - "
            '"Adjustment" is an act involving the tightening or loosening of any part of a weighing or measuring '
            'device.\n\n(3) Barrel. - The term "barrel," when used in connection with beer, ale, porter, and other '
            'similar fermented liquor is a unit of 31 liquid gallons.\n\n(9) Correct. - "Correct" is conformance to '
            "all applicable requirements of this Chapter.")
    got = T.definitions("nc", row, text)
    assert [(t.term, t.kind, t.scope_unit) for t in got] == [
        (w, "means", "North Carolina Code / Chapter 81A") for w in ("Adjustment", "Barrel", "Correct")]
    assert got[0].definition_span.startswith('Adjustment. - "Adjustment" is an act')
    row2 = {"citation": "N.C. Gen. Stat. § 20-286", "original_title": "Definitions.", "section_number": "20-286",
            "path": "North Carolina Code / Chapter 20 / Section 20-286"}
    text2 = ("§ 20-286. Definitions.\n\nThe following definitions apply in this Article:\n\n(15) Retail installment "
             "sale. - A sale of one or more motor vehicles to a buyer for the buyer's use.\n\n(15a) Sell. - The terms "
             '"sell," "retail sales," "selling activities," and "lease" and their cognates are synonymous.\n\n(16) '
             "Used motor vehicle dealer. - A motor vehicle dealer who buys used motor vehicles.")
    assert [t.term for t in T.definitions("nc", row2, text2)] == ["Retail installment sale", "Sell",
                                                                  "Used motor vehicle dealer"]


def test_a_letter_i_ends_the_list_and_a_roman_i_does_not():
    """Re-check 2, item 3: N.C. Gen. Stat. § 58-68-60's "(h) Other Definitions. - As used in this section:" list
    ended only at "(j)", because "(i)" was read as a roman numeral, so the caption "(i) Rights of ..." was a term.
    (An excerpt; its item (1) is written without the section's quotation marks, so the list has a dash term.)"""
    row = {"citation": "N.C. Gen. Stat. § 58-68-60", "section_number": "58-68-60",
           "original_title": "Guaranteed availability of individual health insurance coverage to certain individuals "
                             "with prior group coverage.",
           "path": "North Carolina Code / Chapter 58 / Section 58-68-60"}
    text = ('(h) Other Definitions. - As used in this section:\n\n(1) Church plan. - The meaning given the term under '
            "section 3(33) of the Employee Retirement Income Security Act of 1974.\n\n(i) Rights of Replacement Coverage "
            "Upon Termination. - Subsection (a) of this section shall apply to an eligible individual whose coverage "
            "is terminated.\n\n(j) Waiting Period. - In determining the length of any break in coverage, a "
            "significant break in coverage does not occur during the waiting period.")
    assert [(t.term, t.scope) for t in T.definitions("nc", row, text) if t.kind != "heading"] == [
        ("Church plan", "this section")]
    # a roman list under "(h)": "(ii)" comes before "(j)", so "(i)" is roman one and the list ends at "(j)"
    roman = ("(h) Definitions. - As used in this subsection:\n(i) Covered plan. - A plan that meets subsection (a).\n"
             "(ii) Eligible person. - A person enrolled in a covered plan.\n(j) Reports. - The Commissioner shall "
             "report annually.")
    assert [(t.term, t.scope) for t in T.definitions("nc", row, roman) if t.kind != "heading"] == [
        ("Covered plan", "this subsection"), ("Eligible person", "this subsection")]


def test_an_items_inner_lead_in_does_not_end_the_headings_list():
    """Re-check 2, item 4: under a definitions-only heading with no lead-in of its own, an item's "As used in this
    subdivision, the following terms apply:" made every later item 'after a lead-in', so they were dropped.  A
    top-level lead-in still ends the heading's list."""
    row = {"citation": "N.C. Gen. Stat. § 1-1", "original_title": "Definitions.", "section_number": "1-1",
           "path": "North Carolina Code / Chapter 1 / Section 1-1"}
    text = ("§ 1-1. Definitions.\n\n(1) Reasonable accommodations. - Making facilities accessible. As used in this "
            'subdivision, the following terms apply:\n\na. "Readily accessible" means usable by persons with '
            "disabilities.\n\n(2) Undue hardship. - A significant difficulty or expense.\n\n(3) Employer. - A person "
            "who employs 15 or more persons.")
    got = {t.term: t for t in T.definitions("nc", row, text)}
    assert list(got) == ["Reasonable accommodations", "Readily accessible", "Undue hardship", "Employer"]
    assert got["Readily accessible"].scope == "this subdivision"
    assert {got[w].scope_unit for w in ("Reasonable accommodations", "Undue hardship", "Employer")} == {
        "North Carolina Code / Chapter 1"}
    top = ("§ 1-1. Definitions.\n\n(a) As used in this Article:\n\n(1) Owner. - The holder of the title.\n\n(b) "
           "Inspections. - The officer may inspect a dwelling.")
    assert [t.term for t in T.definitions("nc", row, top)] == ["Owner"]


def test_lead_ins_after_a_caption_or_ending_in_a_dash():
    """N.C. Gen. Stat. § 87-21 '(a) Definitions. - For the purpose of this Article:' and D.C. Code § 38-1805.50
    'For purposes of this subchapter —' (it was scoped to the chapter from the heading)."""
    nc = {"citation": "N.C. Gen. Stat. § 87-21", "section_number": "87-21",
          "original_title": "Definitions; contractors licensed by Board; examination; posting license, etc.",
          "path": "North Carolina Code / Chapter 87 / Section 87-21"}
    text = ('(a) Definitions. - For the purpose of this Article:\n(3) The phrase "heating, group number two" means an '
            "integral system for heating or cooling a building.")
    (t,) = T.definitions("nc", nc, text)
    assert (t.scope, t.scope_unit) == ("this Article", "North Carolina Code / Chapter 87 / Article containing § 87-21")
    dc = {"citation": "D.C. Code § 38-1805.50", "original_title": "Definitions.", "section_number": "38-1805.50",
          "path": "DC Code / Title 38 / Chapter 18 / § 38-1805.50"}
    text = ("For purposes of this subchapter —\n(1) The term “facilities” means buildings, structures, and real "
            "property of the District of Columbia public schools; and\n(2) The term “repair and improvement” includes "
            "administration, construction, and renovation.")
    got = T.definitions("dc", dc, text)
    assert {(t.scope, t.scope_unit, t.scope_basis) for t in got} == {
        ("this subchapter", "DC Code / Title 38 / Chapter 18 / Subchapter containing § 38-1805.50", "anchored")}


@pytest.mark.parametrize("state,row,text,phrase,parts", [
    ("fl", {"citation": "Fla. Stat. § 605.1061", "original_title": "605.1061 Appraisal rights; definitions.",
            "path": "Florida Code / Title XXXVI / Chapter 605 / Section 605.1061"},
     "The following definitions apply to this section and to ss. 605.1006 and 605.1062-605.1072:\n\n(1) “Accrued "
     "interest” means interest from the effective date of the appraisal event.",
     "this section and to ss. 605.1006 and 605.1062-605.1072",
     [("this section", "Florida Code / Title XXXVI / Chapter 605 / Section 605.1061"),
      ("ss. 605.1006 and 605.1062-605.1072", None)]),
    ("nc", {"citation": "N.C. Gen. Stat. § 143-212", "original_title": "Definitions.", "section_number": "143-212",
            "path": "North Carolina Code / Chapter 143 / Section 143-212"},
     "Unless a different meaning is required by the context, the following definitions apply to this Article and "
     'Articles 21A and 21B of this Chapter:\n\n(2) "Commission" means the North Carolina Environmental Management '
     "Commission.",
     "this Article and Articles 21A and 21B of this Chapter",
     [("this Article", "North Carolina Code / Chapter 143 / Article containing § 143-212"),
      ("Articles 21A and 21B of this Chapter", None)]),
    ("nc", {"citation": "N.C. Gen. Stat. § 115C-563", "original_title": "Definitions.", "section_number": "115C-563",
            "path": "North Carolina Code / Chapter 115C / Section 115C-563"},
     'As used in this Part or Parts 1 and 2 of this Article:\n\n(a) "Home school" means a nonpublic school.',
     "this Part or Parts 1 and 2 of this Article",
     [("this Part", "North Carolina Code / Chapter 115C / Part containing § 115C-563"),
      ("Parts 1 and 2 of this Article", None)]),
    ("wa", {"citation": "RCW 24.03A.710", "original_title": "",
            "path": "Washington Code / Title 24 / Chapter 03A / Section 710"},
     "The definitions in this section apply throughout this section and RCW 24.03A.715 through 24.03A.740 unless the "
     'context clearly requires otherwise.\n(1) "Member" means a member.',
     "this section and RCW 24.03A.715 through 24.03A.740",
     [("this section", "Washington Code / Title 24 / Chapter 03A / Section 710"),
      ("RCW 24.03A.715 through 24.03A.740", None)]),
    ("va", {"citation": "Va. Code Ann. § 63.2-1000", "original_title": "Definitions",
            "path": "Virginia Code / Title 63.2 / Subtitle III / Chapter 10 / Section 63.2-1000"},
     'As used in this chapter and Chapter 11 (§ 63.2-1100 et seq.) of this title:\n"Child" means a person under 18.',
     "this chapter and Chapter 11 (§ 63.2-1100 et seq.) of this title",
     [("this chapter", "Virginia Code / Title 63.2 / Subtitle III / Chapter 10"),
      ("Chapter 11 (§ 63.2-1100 et seq.) of this title", None)]),
    # re-check 2, item 5: four or more comma parts (the shape of Fla. Stat. § 253.025's "this chapter, chapter 259,
    # chapter 260, or chapter 375"), number words (N.Y. LLC Law § 1106) and footnote asterisks (RCW 43.216.157)
    ("va", {"citation": "Va. Code Ann. § 63.2-100", "original_title": "Definitions",
            "path": "Virginia Code / Title 63.2 / Subtitle I / Chapter 1 / Section 63.2-100"},
     'As used in this chapter, Chapter 4, Chapter 5, and Chapter 6 of this title:\n"Board" means the State Board.',
     "this chapter, Chapter 4, Chapter 5, and Chapter 6 of this title",
     [("this chapter", "Virginia Code / Title 63.2 / Subtitle I / Chapter 1"), ("Chapter 4", None),
      ("Chapter 5", None), ("Chapter 6 of this title", None)]),
    ("ny", {"citation": "N.Y. LLC Law § 1106", "original_title": "Definitions",
            "path": "New York Code / Act LLC / Article 11 - Miscellaneous / Section 1106"},
     "§ 1106. Definitions. For the purposes of this section and sections\neleven hundred seven and eleven hundred "
     'eight of this article:\n  (a) "Beneficial owner" shall have the same meaning as defined in 31\nU.S.C. § '
     '5336(a)(3).\n  (c) "Exempt company" shall mean a limited liability company.',
     "this section and sections eleven hundred seven and eleven hundred eight of this article",
     [("this section", "New York Code / Act LLC / Article 11 - Miscellaneous / Section 1106"),
      ("sections eleven hundred seven and eleven hundred eight of this article", None)]),
    ("wa", {"citation": "RCW 43.216.157", "original_title": "",
            "path": "Washington Code / Title 43 / Chapter 216 / Section 157"},
     "The definitions in this section apply throughout this section and RCW * 43.215.145 , * 43.215.147 , and ** "
     '43.121.185 unless the context clearly requires otherwise. (1) "Home visitation" means providing services in '
     "the residence of the family.",
     "this section and RCW * 43.215.145 , * 43.215.147 , and ** 43.121.185",
     [("this section", "Washington Code / Title 43 / Chapter 216 / Section 157"),
      ("RCW * 43.215.145 , * 43.215.147 , and ** 43.121.185", None)]),
])
def test_a_compound_scope_keeps_every_part(state, row, text, phrase, parts):
    """Re-check item 6: these were cut to their first unit.  No one unit expresses them, so scope_unit is None and
    scope_parts lists the parts, each with its own unit."""
    got = [t for t in T.definitions(state, row, text) if t.kind != "heading"]
    assert got and all((t.scope, t.scope_unit, t.scope_basis, t.scope_parts) == (phrase, None, "compound", parts)
                       for t in got)
    assert T.scope_parts(phrase) == [p for p, _ in parts]


def test_a_comma_run_is_compound_only_when_and_or_or_ends_it():
    """Cal. Rev. & Tax. Code § 17021.7's run of parts with parentheticals is one compound scope; a comma run that
    no "and"/"or" closes stays one unit."""
    phrase = ("this part, Part 10.2 (commencing with Section 18401), Part 10.7 (commencing with Section 21001), and "
              "Part 11 (commencing with Section 23001)")
    assert T.scope_parts(phrase) == ["this part", "Part 10.2 (commencing with Section 18401)",
                                     "Part 10.7 (commencing with Section 21001)",
                                     "Part 11 (commencing with Section 23001)"]
    text = "this chapter, chapter 2, chapter 3, the rules adopted under it"
    assert T._also_parts(text, len("this chapter")) == ([], len("this chapter"))


def test_a_unit_followed_by_other_words_is_not_compound():
    row = {"citation": "Fla. Stat. § 2.1", "original_title": "2.1 Definitions.",
           "path": "Florida Code / Title I / Chapter 2 / Section 2.1"}
    (t,) = T.definitions("fl", row, 'As used in this chapter and in any rule adopted under it:\n(1) "Board" means '
                                    "the board.")
    assert (t.scope, t.scope_unit, t.scope_basis, t.scope_parts) == (
        "this chapter", "Florida Code / Title I / Chapter 2", "path", [])
    assert T.scope_parts("this chapter") == ["this chapter"]


def test_key_singular_is_frozen_so_the_matcher_can_change(monkeypatch):
    """Re-check item 4: heading, 'may act as' and 'defined as' terms are made singular by key_singular, a frozen copy
    of the tables; changing the matcher's _singular (as the fix to 'Bonuses.' did) moves no key."""
    snapshot = json.dumps([sorted(T._KEY_NO_SINGULAR), [list(x) for x in T._KEY_IRREGULAR]])
    assert hashlib.sha256(snapshot.encode()).hexdigest() == \
        "6cd5eaeb0803f0205bfe13ab7e50fda230602bd4185d2dcf945b18fc9a7aeb5b", "a key-form change needs a new KEY_VERSION"
    assert [T.key_singular(w) for w in ("Incorporators", "Bonuses", "Analyses", "gases", "Damages", "premises",
                                        "policies", "boxes", "status")] == \
        ["Incorporator", "Bonus", "Analysis", "gas", "Damages", "premises", "policy", "box", "status"]
    row = {"citation": "Fla. Stat. § 1.01", "original_title": "1.01 Bonuses.",
           "path": "Florida Code / Title I / Chapter 1 / Section 1.01"}
    text = "Bonuses may be paid to employees. Any person may act as the trustees of the fund."

    def keys():
        return sorted(T.group_by_key("fl", "1.01", T.definitions("fl", row, text)))

    before = keys()
    assert before == ["lexflow:term:fl:1.01:bonus", "lexflow:term:fl:1.01:trustee"]
    monkeypatch.setattr(T, "_IRREGULAR", {})                 # the matcher's singulariser changes ...
    monkeypatch.setattr(T, "_NO_SINGULAR", set())
    monkeypatch.setattr(T, "_singular", lambda w: w[:-1] if w.endswith("s") else w)
    assert keys() == before                                  # ... and no key moves


def test_pinned_lead_ins_and_forms():
    """Fixes the re-check probed but no test pinned (its item 8).  The lead-in rows have no heading, so the
    fallback is the section itself and only the lead-in can give the chapter (re-check 2, item 2: under a
    "Definitions." heading the fallback gave the same chapter, and the rows pinned nothing)."""
    def scopes(state, title, path, text):
        row = {"citation": "X", "original_title": title, "path": path}
        return {(t.term, t.kind, t.scope, t.scope_unit) for t in T.definitions(state, row, text)}

    wa = "Washington Code / Title 9 / Chapter 9A / Section 1"
    assert scopes("wa", "", wa, 'When used in this chapter:\n(1) "Bail" means security.') == {
        ("Bail", "means", "this chapter", "Washington Code / Title 9 / Chapter 9A")}
    md = "MD Code / Article gle / Title 11 / Subtitle 5 / Section 11-503"
    assert scopes("md", "", md, '(a) In this subtitle the following words have the meanings indicated.\n\n(b) "Fund" '
                                'means the Fund.') == {
        ("Fund", "means", "this subtitle", "MD Code / Article gle / Title 11 / Subtitle 5")}
    fl = "Florida Code / Title I / Chapter 1 / Section 1.1"
    assert scopes("fl", "", fl, 'For the purposes of this chapter, the following terms mean:\n(1) "Board" means the '
                                'board.') == {("Board", "means", "this chapter", "Florida Code / Title I / Chapter 1")}
    # a section range keeps its own colon out of the number, and names no unit
    assert scopes("fl", "876.36 Definitions.", "Florida Code / Title XLVI / Chapter 876 / Section 876.36",
                  "For the purposes of ss. 876.37-876.50:\n(1) “Organization” means a group.") == {
        ("Organization", "means", "ss. 876.37-876.50", None)}
    # another unit than the section's own: no unit, the words kept
    assert scopes("va", "Definitions", "Virginia Code / Title 63.2 / Subtitle III / Chapter 11 / Section 63.2-1100",
                  "For the purposes of Chapter 10 (§ 63.2-1000 et seq.) of this title, the following words shall have "
                  'the meaning ascribed to them by this section:\nA. "Appropriate public authorities" as used in '
                  "Article III of the compact means the Department.") == {
        ("Appropriate public authorities", "means", "Chapter 10 (§ 63.2-1000 et seq.) of this title", None)}
    # '"Woodland" means woodland as defined in ...' is one by-reference definition (re-check item 7)
    row = {"citation": "N.C. Gen. Stat. § 106-1", "original_title": "Definitions.",
           "path": "North Carolina Code / Chapter 106 / Section 106-1"}
    (t,) = T.definitions("nc", row, '"Woodland" means woodland as defined in G.S. 105-277.2.')
    assert (t.term, t.kind, t.defined_in) == ("Woodland", "by_reference", "G.S. 105-277.2")
    # "(2) Record. - Information that ..." is a term, not a caption
    row = {"citation": "N.C. Gen. Stat. § 132-1.1", "original_title": "Definitions.",
           "path": "North Carolina Code / Chapter 132 / Section 132-1.1"}
    got = T.definitions("nc", row, "The following definitions apply in this Article:\n(1) Custodian. - The person who "
                                   "has custody.\n(2) Record. - Information that is inscribed on a tangible medium.")
    assert [t.term for t in got] == ["Custodian", "Record"]


def test_headings_that_name_no_term():
    """Each text repeats its heading, as N.C. texts do, so the mention check passes and only the heading rules keep
    it out (re-check 2, item 2: the old row never mentioned "Definition and purposes.").  "Definition and regulation
    of auctioneers." is not generic, so only the "definition" word rule keeps it out; "Statement of purpose and
    authorization." (N.C. Gen. Stat. § 106-1041, re-check 2, item 6) opens with a generic phrase; every part of
    "Powers and duties." is generic."""
    for title in ("Definition and purposes.", "Definition and regulation of auctioneers.", "Declaration of policy.",
                  "Statement of purpose and authorization.", "Powers and duties."):
        row = {"citation": "N.C. Gen. Stat. § 1-1", "original_title": title,
               "path": "North Carolina Code / Chapter 1 / Section 1-1"}
        text = f"§ 1-1. {title}\n\nThe {title[:-1].lower()} of this Article are to protect the public."
        assert [t for t in T.definitions("nc", row, text) if t.kind == "heading"] == [], title
    # a role heading still names its term
    row = {"citation": "N.C. Gen. Stat. § 1-2", "original_title": "Guardian and ward.",
           "path": "North Carolina Code / Chapter 1 / Section 1-2"}
    assert [t.term for t in T.definitions("nc", row, "§ 1-2. Guardian and ward.\n\nA guardian and ward may agree.")] \
        == ["guardian and ward"]


def test_means_tested_is_no_definition_verb():
    """Re-check 2, item 6: N.C. Gen. Stat. § 108A-25.3 gave the false term "Public assistance program. - Any"."""
    row = {"citation": "N.C. Gen. Stat. § 108A-25.3", "original_title": "Garnishment of wages.",
           "path": "North Carolina Code / Chapter 108A / Section 108A-25.3"}
    got = T.definitions("nc", row, "(a) The following definitions apply in this section:\n\n(4) Public assistance "
                                   "program. - Any means-tested benefit program administered by a county department "
                                   "of social services.\n\n(b) A judge may enter an order of garnishment.")
    assert [t.term for t in got] == ["Public assistance program"]
    assert T.DEF_A.search('"Program" means-tested benefits') is None


def _eval_module():
    spec = importlib.util.spec_from_file_location("terms_eval", ROOT / "scripts" / "terms_eval.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_eval_rule_baseline_counts_rejudged_pairs_and_held_out_units_match():
    """Re-check item 7: the rule baseline counts 8 different things by the survey's labels, 9 with REJUDGED (the
    custodian of records); the held-out act unit is the one resolve_scope gives."""
    E = _eval_module()
    pairs = T.survey_pairs()
    base = E.rule_baseline(pairs, T.pair_features(pairs))
    assert (base["linked"], base["correct"], base["different_thing_survey"], base["different_thing"]) == \
        (107, 80, 8, 9)
    (unit,) = [u for st, cit, u, _ in E.HELD_OUT if cit == "Fla. Stat. § 606.03"]
    assert T.resolve_scope("fl", {"path": "Florida Code / Title XXXVI / Chapter 606 / Section 606.03",
                                  "section_number": "606.03"}, "this act")[0] == unit
    tab = {"a": (0.9, "exact", True, "Q1"), "b": (0.7, "wrong", False, "Q2")}
    assert E.next_below(tab, 0.8) == "b (p 0.700, wrong)" and E.next_below(tab, 0.5) is None
