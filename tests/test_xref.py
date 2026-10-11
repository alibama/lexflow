"""Statute cross-references (lexflow.law.xref).

The parser is tested on literal text, without an index (the ``con`` fixture points the data directory at an
empty temp dir): every gold reference of the two user-example sections, Cal. BPC § 480 and Va. Code § 54.1-204
(fixtures/xref/gold_b.json and gold_a.json), and focused snippets.  Resolution is tested on the fixture statutes
(``va_statutes`` serves fixtures/statutes/*_sections.json; I.ensure builds a temp index from them), on sections
whose references point at other fixture sections, and on small hand-made indexes (``mini_index``) that hold the
very sections a wrong reading would land on (the citing code's § 4 for "Section 4 of Article VII of the
California Constitution").
"""
import json
import re
from pathlib import Path

import pytest

from lexflow.law import xref

ROOT = Path(__file__).resolve().parents[1]
GOLD = ROOT / "fixtures" / "xref"

# I.text_of for the two user-example sections (the gold's offsets are into exactly these strings)
BPC_480 = (
    '(a) Notwithstanding any other provision of this code, a board may deny a license regulated b'
    'y this code on the grounds that the applicant has been convicted of a crime or has been subj'
    'ect to formal discipline only if either of the following conditions are met:\n'
    '\n(1) The applicant has been convicted of a crime within the preceding seven years from the '
    'date of application that is substantially related to the qualifications, functions, or dutie'
    's of the business or profession for which the application is made, regardless of whether the'
    ' applicant was incarcerated for that crime, or the applicant has been convicted of a crime t'
    'hat is substantially related to the qualifications, functions, or duties of the business or '
    'profession for which the application is made and for which the applicant is presently incarc'
    'erated or for which the applicant was released from incarceration within the preceding seven'
    ' years from the date of application. However, the preceding seven-year limitation shall not '
    'apply in either of the following situations:\n'
    '\n(A) The applicant was convicted of a serious felony, as defined in Section 1192.7 of the P'
    'enal Code or a crime for which registration is required pursuant to paragraph (2) or (3) of '
    'subdivision (d) of Section 290 of the Penal Code.\n'
    '\n(B) The applicant was convicted of a financial crime currently classified as a felony that'
    ' is directly and adversely related to the fiduciary qualifications, functions, or duties of '
    'the business or profession for which the application is made, pursuant to regulations adopte'
    'd by the board, and for which the applicant is seeking licensure under any of the following:'
    '\n\n(i) Chapter 6 (commencing with Section 6500) of Division 3.\n'
    '\n(ii) Chapter 9 (commencing with Section 7000) of Division 3.\n'
    '\n(iii) Chapter 11.3 (commencing with Section 7512) of Division 3.\n'
    '\n(iv) Licensure as a funeral director or cemetery manager under Chapter 12 (commencing with'
    ' Section 7600) of Division 3.\n\n(v) Division 4 (commencing with Section 10000).\n'
    '\n(2) The applicant has been subjected to formal discipline by a licensing board in or outsi'
    'de California within the preceding seven years from the date of application based on profess'
    'ional misconduct that would have been cause for discipline before the board for which the pr'
    'esent application is made and that is substantially related to the qualifications, functions'
    ', or duties of the business or profession for which the present application is made. However'
    ', prior disciplinary action by a licensing board within the preceding seven years shall not '
    'be the basis for denial of a license if the basis for that disciplinary action was a convict'
    'ion that has been dismissed pursuant to Section 1203.4, 1203.4a, 1203.41, 1203.42, or 1203.4'
    '25 of the Penal Code or a comparable dismissal or expungement. Formal discipline that occurr'
    'ed earlier than seven years preceding the date of application may be grounds for denial of a'
    ' license only if the formal discipline was for conduct that, if committed in this state by a'
    ' physician and surgeon licensed pursuant to Chapter 5 (commencing with Section 2000) of Divi'
    'sion 2, would have constituted an act of sexual abuse, misconduct, or relations with a patie'
    'nt pursuant to Section 726 or sexual exploitation as defined in subdivision (a) of Section 7'
    '29.\n\n(b) Notwithstanding any other provision of this code, a person shall not be denied a '
    'license on the basis that the person has been convicted of a crime, or on the basis of acts '
    'underlying a conviction for a crime, if that person has obtained a certificate of rehabilita'
    'tion under Chapter 3.5 (commencing with Section 4852.01) of Title 6 of Part 3 of the Penal C'
    'ode, has been granted clemency or a pardon by a state or federal executive, or has made a sh'
    'owing of rehabilitation pursuant to Section 482.\n'
    '\n(c) Notwithstanding any other provision of this code, a person shall not be denied a licen'
    'se on the basis of any conviction, or on the basis of the acts underlying the conviction, th'
    'at has been dismissed pursuant to Section 1203.4, 1203.4a, 1203.41, 1203.42, or 1203.425 of '
    'the Penal Code, or a comparable dismissal or expungement. An applicant who has a conviction '
    'that has been dismissed pursuant to Section 1203.4, 1203.4a, 1203.41, or 1203.42 of the Pena'
    'l Code shall provide proof of the dismissal if it is not reflected on the report furnished b'
    'y the Department of Justice.\n\n(d) Notwithstanding any other provision of this code, a boar'
    'd shall not deny a license on the basis of an arrest that resulted in a disposition other th'
    'an a conviction, including an arrest that resulted in an infraction, citation, or a juvenile'
    ' adjudication.\n\n(e) A board may deny a license regulated by this code on the ground that t'
    'he applicant knowingly made a false statement of fact that is required to be revealed in the'
    ' application for the license. A board shall not deny a license based solely on an applicant’'
    's failure to disclose a fact that would not have been cause for denial of the license had it'
    ' been disclosed.\n\n(f) A board shall follow the following procedures in requesting or actin'
    'g on an applicant’s criminal history information:\n'
    '\n(1) A board issuing a license pursuant to Chapter 3 (commencing with Section 5500), Chapte'
    'r 3.5 (commencing with Section 5615), Chapter 10 (commencing with Section 7301), Chapter 20 '
    '(commencing with Section 9800), or Chapter 20.3 (commencing with Section 9880), of Division '
    '3, or Chapter 3 (commencing with Section 19000) or Chapter 3.1 (commencing with Section 1922'
    '5) of Division 8 may require applicants for licensure under those chapters to disclose crimi'
    'nal conviction history on an application for licensure.\n'
    '\n(2) Except as provided in paragraph (1), a board shall not require an applicant for licens'
    'ure to disclose any information or documentation regarding the applicant’s criminal history.'
    ' However, a board may request mitigating information from an applicant regarding the applica'
    'nt’s criminal history for purposes of determining substantial relation or demonstrating evid'
    'ence of rehabilitation, provided that the applicant is informed that disclosure is voluntary'
    ' and that the applicant’s decision not to disclose any information shall not be a factor in '
    'a board’s decision to grant or deny an application for licensure.\n'
    '\n(3) If a board decides to deny an application for licensure based solely or in part on the'
    ' applicant’s conviction history, the board shall notify the applicant in writing of all of t'
    'he following:\n\n(A) The denial or disqualification of licensure.\n'
    '\n(B) Any existing procedure the board has for the applicant to challenge the decision or to'
    ' request reconsideration.\n\n(C) That the applicant has the right to appeal the board’s deci'
    'sion.\n\n(D) The processes for the applicant to request a copy of the applicant’s complete c'
    'onviction history and question the accuracy or completeness of the record pursuant to Sectio'
    'ns 11122 to 11127 of the Penal Code.\n\n(g) (1) For a minimum of three years, each board und'
    'er this code shall retain application forms and other documents submitted by an applicant, a'
    'ny notice provided to an applicant, all other communications received from and provided to a'
    'n applicant, and criminal history reports of an applicant.\n'
    '\n(2) Each board under this code shall retain the number of applications received for each l'
    'icense and the number of applications requiring inquiries regarding criminal history. In add'
    'ition, each licensing authority shall retain all of the following information:\n'
    '\n(A) The number of applicants with a criminal record who received notice of denial or disqu'
    'alification of licensure.\n\n(B) The number of applicants with a criminal record who provide'
    'd evidence of mitigation or rehabilitation.\n'
    '\n(C) The number of applicants with a criminal record who appealed any denial or disqualific'
    'ation of licensure.\n\n(D) The final disposition and demographic information, consisting of '
    'voluntarily provided information on race or gender, of any applicant described in subparagra'
    'ph (A), (B), or (C).\n\n(3) (A) Each board under this code shall annually make available to '
    'the public through the board’s internet website and through a report submitted to the approp'
    'riate policy committees of the Legislature deidentified information collected pursuant to th'
    'is subdivision. Each board shall ensure confidentiality of the individual applicants.\n'
    '\n(B) A report pursuant to subparagraph (A) shall be submitted in compliance with Section 97'
    '95 of the Government Code.\n\n(h) “Conviction” as used in this section shall have the same m'
    'eaning as defined in Section 7.5.\n\n(i) This section does not in any way modify or otherwis'
    'e affect the existing authority of the following entities in regard to licensure:\n'
    '\n(1) The State Athletic Commission.\n\n(2) The Bureau for Private Postsecondary Education.\n'
    '\n(3) The California Horse Racing Board.')
VA_54_1_204 = (
    'A. A person shall not be refused a license, certificate, or registration to practice, pursue'
    ', or engage in any regulated occupation or profession solely because of a prior criminal con'
    'viction, unless the criminal conviction directly relates to the occupation or profession for'
    ' which the license, certificate, or registration is sought. A regulatory board shall not use'
    ' vague or arbitrary terms, including "good moral character" or "moral turpitude" to refuse a'
    ' license, certificate, or registration.\n\n'
    'B. In determining whether a criminal conviction directly relates to an occupation or profess'
    'ion, the regulatory board shall consider the following criteria:\n'
    '\n1. The nature and seriousness of the crime;\n'
    '\n2. The relationship of the crime to the purpose for requiring a license to engage in the o'
    'ccupation;\n\n3. The extent to which the occupation or profession might offer an opportunity'
    ' to engage in further criminal activity of the same type as that in which the person had bee'
    'n involved;\n\n4. The relationship of the crime to the ability, capacity, or fitness require'
    'd to perform the duties and discharge the responsibilities of the occupation or profession;\n'
    "\n5. The extent and nature of the person's past criminal activity;\n"
    '\n6. The age of the person at the time of the commission of the crime;\n'
    "\n7. The amount of time that has elapsed since the person's last involvement in the commissi"
    'on of a crime;\n\n8. The conduct and work activity of the person prior to and following the '
    "criminal activity; and\n\n9. Evidence of the person's rehabilitation or rehabilitative effor"
    't while incarcerated or following release.\n'
    '\nC. A regulatory board may require any applicant for registration, licensure, or certificat'
    'ion to submit to fingerprinting and to provide personal descriptive information to be forwar'
    "ded along with the applicant's fingerprints through the Central Criminal Records Exchange to"
    ' the Federal Bureau of Investigation for the purpose of obtaining criminal history record in'
    'formation regarding such applicant. Such applicant shall pay the cost of the fingerprinting '
    'or a criminal records check or both.\n\nThe regulatory board may enter into a contract to ob'
    'tain the fingerprints and descriptive information as required for submission to the Central '
    'Criminal Records Exchange in a manner and format approved by the Central Criminal Records Ex'
    "change.\n\nThe Central Criminal Records Exchange, upon receipt of an applicant's record or n"
    'otification that no record exists, shall make a report to the regulatory board or its design'
    'ee, who must belong to a governmental entity. If an applicant is denied a registration, lice'
    'nse, or certificate because of the information appearing in his criminal history record, the'
    ' regulatory board shall notify the applicant in writing of the specific offense or offenses '
    'that contributed to such denial, how the criminal history directly relates to the occupation'
    ' pursuant to subsection B, and how the regulatory board weighed the rehabilitation factors i'
    'n subsection B when making its decision. The information shall not be disseminated except as'
    ' provided for in this section.\n\nD. A regulatory board shall consider the criminal informat'
    "ion as contained in the applicant's state or national criminal history in lieu of the applic"
    'ant providing certified copies of such court records in determining whether a criminal convi'
    'ction directly relates to an occupation or profession or if an applicant is unfit or unsuite'
    'd to engage in an occupation or profession. The regulatory board may request additional info'
    'rmation from the applicant in making such determination.\n'
    '\n1979, c. 408, § 54-1.21; 1988, c. 765; 2003, c. 582 ; 2009, c. 667 ; 2025, c. 505 .')
BPC_ROW = {"id": 5, "citation": "Cal. BPC § 480",
           "path": "California Code / Code bpc / Division 1.5 / Chapter 2 / Section 480"}
VA_ROW = {"id": 22341, "citation": "Va. Code Ann. § 54.1-204",
          "path": "Virginia Code / Title 54.1 / Subtitle II / Chapter 2 / Section 54.1-204"}


def gold_refs(name: str, citation: str) -> list[dict]:
    d = json.loads((GOLD / name).read_text(encoding="utf-8"))
    return next(s for s in d["sections"] if s["citation"] == citation)["references"]


def overlap(g: dict, r) -> int:
    return max(0, min(g["end"], r.end) - max(g["start"], r.start))


def one_to_one(gold: list[dict], refs: list) -> dict[int, int]:
    pairs = sorted(((overlap(g, r), gi, ri) for gi, g in enumerate(gold) for ri, r in enumerate(refs)
                    if overlap(g, r)), reverse=True)
    out, used = {}, set()
    for _, gi, ri in pairs:
        if gi not in out and ri not in used:
            out[gi] = ri
            used.add(ri)
    return out


def pin(p) -> tuple:
    return tuple(re.findall(r"[A-Za-z0-9]+(?:-\d+)?", p or ""))


def refs_in(text: str, state: str = "ca", row: dict | None = None):
    row = row or {"id": 1, "citation": {"ca": "Cal. BPC § 1", "va": "Va. Code Ann. § 1-1", "fl": "Fla. Stat. § 1.01",
                                        "ny": "N.Y. LLC Law § 1", "il": "805 ILCS 180/1-1", "tx": "Tex. Government Code § 1.001",
                                        "md": "Md. Code, Transportation § 26-204", "dc": "D.C. Code § 1-1",
                                        "wa": "RCW 1.01.010", "nc": "N.C. Gen. Stat. § 1-1"}[state], "path": ""}
    return xref.references(state, row, text=text)


def by_span(refs, span: str):
    hits = [r for r in refs if r.span == span]
    assert hits, f"{span!r} not among {[r.span for r in refs]}"
    return hits[0]


def mini_index(state: str, rows: list[tuple]) -> dict[str, int]:
    """A statute index of just these (citation, path, text) rows, where xref reads the state's index (the ``con``
    fixture's temp data dir).  Returns citation -> row id."""
    import sqlite3
    from lexflow.ask import index as I
    from lexflow.municipal import statutes
    p = I.path(state)
    p.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(str(p))
    c.executescript("""
        CREATE TABLE sec(id INTEGER PRIMARY KEY, ref TEXT, citation TEXT, title TEXT, chapter TEXT, path TEXT,
                         url TEXT, words INTEGER, head TEXT, section_number TEXT, norm_section TEXT, norm_cite TEXT,
                         act_id TEXT, original_title TEXT, effective_from TEXT, effective_until TEXT);
        CREATE TABLE body(id INTEGER PRIMARY KEY, text TEXT);
        CREATE VIRTUAL TABLE fts USING fts5(title, chapter, body, content='');""")
    for i, (cite, path, text) in enumerate(rows, 1):
        num = re.split(r"§\s*|/|\s", cite)[-1]
        c.execute("INSERT INTO sec(id, citation, path, section_number, norm_cite) VALUES (?,?,?,?,?)",
                  (i, cite, path, num, statutes._norm_cite(cite)))
        c.execute("INSERT INTO body VALUES (?,?)", (i, text))
        c.execute("INSERT INTO fts(rowid, title, chapter, body) VALUES (?,?,?,?)", (i, "", "", text))
    c.commit()
    c.close()
    return {cite: i for i, (cite, _, _) in enumerate(rows, 1)}


def row_of(ids: dict, citation: str, path: str = "") -> dict:
    return {"id": ids[citation], "citation": citation, "path": path}


# ------------------------------------------------------------------ the user examples, every reference
def test_bpc_480_every_gold_reference(con):
    gold = gold_refs("gold_b.json", "Cal. BPC § 480")
    assert all(BPC_480[g["start"]:g["end"]] == g["span"] for g in gold)
    refs = xref.references("ca", BPC_ROW, text=BPC_480)
    m = one_to_one(gold, refs)
    assert len(m) == len(gold) == 53                       # each gold reference has its own predicted reference
    extra = [r.span for i, r in enumerate(refs) if i not in m.values()]
    assert extra == ["subparagraph (A)", "(B)", "(C)"]     # (g)(2) 'described in subparagraph (A), (B), or (C)'
    for gi, g in enumerate(gold):
        r = refs[m[gi]]
        if g.get("pinpoint"):
            assert pin(r.pinpoint) == pin(g["pinpoint"]), (g["span"], r.pinpoint)
        if g["target_code"] in ("Penal Code", "Government Code"):
            assert r.code == g["target_code"], (g["span"], r.code)     # named, though no index resolves it here
        elif g["target_code"] in ("this code", "this section", "this subdivision"):
            assert r.code == "Cal. BPC § ", g["span"]
        if g.get("self") or g["target_code"] == "this section":
            assert r.ids == [5], g["span"]


def test_bpc_480_structure_and_roles(con):
    refs = xref.references("ca", BPC_ROW, text=BPC_480)
    # 'paragraph (2) or (3) of subdivision (d) of Section 290 of the Penal Code': two items, one tail
    p2 = by_span(refs, "paragraph (2)")
    p3 = next(r for r in refs if r.span.startswith("(3) of subdivision (d)"))
    assert (p2.pinpoint, p3.pinpoint, p2.code, p3.code) == ("(d)(2)", "(d)(3)", "Penal Code", "Penal Code")
    assert p2.list_group == p3.list_group is not None
    # 'Section 1203.4, 1203.4a, 1203.41, 1203.42, or 1203.425 of the Penal Code' (twice) and the four-item list
    dismissed = [r for r in refs if r.code == "Penal Code" and r.role == "prerequisite_process"
                 and re.match(r"(Section )?1203\.4", r.span)]
    assert len(dismissed) == 14 and len({r.list_group for r in dismissed}) == 3
    chapter6 = by_span(refs, "Chapter 6 (commencing with Section 6500) of Division 3")
    assert chapter6.kind == "container" and chapter6.code == "Cal. BPC § "
    rng = by_span(refs, "Sections 11122 to 11127 of the Penal Code")
    assert rng.kind == "range" and rng.code == "Penal Code"
    roles = {r.span: r.role for r in refs}
    other = [r for r in refs if r.span == "this code" and BPC_480[:r.start].endswith("any other provision of ")]
    assert [(r.role, r.kind, r.ids) for r in other] == [("override", "internal_relative", [])] * 4
    assert roles["Section 1192.7 of the Penal Code"] == roles["subdivision (a) of Section 729"] == "definition"
    assert roles["Section 7.5"] == "definition"
    assert roles["Section 482"] == "prerequisite_process"          # 'has made a showing of rehabilitation pursuant to'
    assert by_span(refs, "paragraph (1)").role == "exception"      # 'Except as provided in paragraph (1)'
    assert by_span(refs, "paragraph (1)").pinpoint == "(f)(1)"
    assert by_span(refs, "this subdivision").pinpoint == "(g)"
    assert by_span(refs, "those chapters").kind == "container"     # an anaphor for the seven chapters before it


def test_va_54_1_204_every_gold_reference(con):
    gold = gold_refs("gold_a.json", "Va. Code Ann. § 54.1-204")
    assert all(VA_54_1_204[g["start"]:g["end"]] == g["span"] for g in gold)
    refs = xref.references("va", VA_ROW, text=VA_54_1_204)
    assert [(r.span, r.kind, r.pinpoint, r.ids) for r in refs] == [
        ("subsection B", "pinpoint", "B", [22341]), ("subsection B", "pinpoint", "B", [22341]),
        ("this section", "internal_relative", None, [22341])]
    assert [r.start for r in refs] == [g["start"] for g in gold]
    assert refs[1].role == "condition"                             # 'weighed the rehabilitation factors in'
    assert refs[2].role == "exception"                             # 'except as provided for in this section'
    assert not any("54-1.21" in r.span for r in refs)              # the history line '1979, c. 408, § 54-1.21'


# ------------------------------------------------------------------ the grammar on snippets
def test_other_codes_and_acts_are_named(con):
    r = refs_in("as defined in section 50-g of the civil rights law, the", "ny")
    assert [(x.span, x.code, x.role) for x in r] == [("section 50-g of the civil rights law", "civil rights law",
                                                      "definition")]
    r = refs_in("pursuant to Section 5-5-3 of the Unified Code of Corrections.", "il")
    assert (r[0].kind, r[0].code) == ("other_code", "Unified Code of Corrections")
    r = refs_in("under the Code of Criminal Procedure of 1963 (725 ILCS 5/) and (20 ILCS 2630/).", "il")
    assert [x.code for x in r if x.kind == "named_act"] == ["725 ILCS 5/", "20 ILCS 2630/"]
    r = refs_in("a payment plan under § 7–504.1 of the Courts Article, if", "md")
    assert (r[0].span, r[0].code, r[0].role) == ("§ 7–504.1 of the Courts Article", "Courts Article",
                                                 "prerequisite_process")
    r = refs_in("as provided in Article 6 of the Education Article.", "md")
    assert (r[0].kind, r[0].code) == ("container", "Education Article")
    r = refs_in("an offense under Section 20.02, 20.03, or 20.04, Penal Code, or", "tx")
    assert [(x.span, x.code) for x in r] == [("Section 20.02", "Penal Code"), ("20.03", "Penal Code"),
                                              ("20.04, Penal Code", "Penal Code")]
    r = refs_in("as provided in Article 14.06(b) of this code", "tx",
                {"citation": "Tex. Code of Criminal Procedure § 45A.254", "path": ""})
    assert (r[0].kind, r[0].pinpoint) == ("pinpoint", "(b)")


def test_this_unit_follows_the_citing_path(con):
    row = {"id": 9, "citation": "Va. Code Ann. § 54.1-201",
           "path": "Virginia Code / Title 54.1 / Subtitle II / Chapter 2 / Section 54.1-201"}
    r = xref.references("va", row, text="licensed under this subtitle and the intent of this chapter or this title")
    assert [x.unit["path"] for x in r] == ["Virginia Code / Title 54.1 / Subtitle II",
                                          "Virginia Code / Title 54.1 / Subtitle II / Chapter 2",
                                          "Virginia Code / Title 54.1"]
    assert all(x.kind == "internal_relative" and x.sections == [] for x in r)


@pytest.mark.parametrize("state,text,expect", [
    # lists: one reference per item, the keyword only on the first
    ("fl", "subject to ss. 605.2402 and 605.2404, the laws", [("ss. 605.2402", None), ("605.2404", None)]),
    ("dc", "Subject to subsections (c), (d), and (e) of this section and", [("subsections (c)", "(c)"), ("(d)", "(d)"),
                                                                         ("(e) of this section", "(e)")]),
    ("fl", "except as provided in s. 119.071(2)(h) or (o).", [("s. 119.071(2)(h)", "(2)(h)"), ("(o)", "(2)(o)")]),
    ("va", "subject to § 2.2-3706.1 , 60 work days after", [("§ 2.2-3706.1", None)]),
    ("va", "provided under subsection B or C, on at least", [("subsection B", "B"), ("C", "C")]),
    ("ny", "pursuant to section two hundred five of this chapter, twenty dollars.",
     [("section two hundred five of this chapter", None)]),
    ("ny", "pursuant to paragraph two of subdivision (e) of section three\nhundred one of this chapter.",
     [("paragraph two of subdivision (e) of section three\nhundred one of this chapter", "(e)(2)")]),
    ("ny", "in accordance with subdivision (e) of this section, (ii) executing such articles",
     [("subdivision (e) of this section", "(e)")]),
    ("wa", "would violate RCW 42.56.070 (8) or 42.56.240 (14), or", [("RCW 42.56.070 (8)", "(8)"),
                                                                    ("42.56.240 (14)", "(14)")]),
    # pinpoints chained with 'of'
    ("ca", "under subparagraph (B) of paragraph (5) of subdivision (h) of Section 1170, the court",
     [("subparagraph (B) of paragraph (5) of subdivision (h) of Section 1170", "(h)(5)(B)")]),
    # ranges are one reference
    ("ca", "pursuant to Sections 11122 to 11127, inclusive.", [("Sections 11122 to 11127, inclusive", None)]),
    ("fl", "(5) Sections 605.0903-605.0912 apply", [("Sections 605.0903-605.0912", None)]),
    ("ny", "in subdivisions (a) through (p) of this section, not", [("subdivisions (a) through (p) of this section",
                                                                     "(a)-(p)")]),
    # a list item's designators replace the cited ones from its own level, not always the last one
    ("wa", "RCW 48.110.030 (2)(a) and (b), (3), and (4), 48.110.040 , and 48.110.073 (2) do not apply",
     [("RCW 48.110.030 (2)(a)", "(2)(a)"), ("(b)", "(2)(b)"), ("(3)", "(3)"), ("(4)", "(4)"), ("48.110.040", None),
      ("48.110.073 (2)", "(2)")]),
    ("wa", "RCW 48.110.030 (2)(a) through (c), (3), and (4), 48.110.040 do not apply",
     [("RCW 48.110.030 (2)(a) through (c)", "(2)(a)-(c)"), ("(3)", "(3)"), ("(4)", "(4)"), ("48.110.040", None)]),
    ("md", "for any of the reasons provided under subsection (c)(2), (3), or (4) of this section:",
     [("subsection (c)(2)", "(c)(2)"), ("(3)", "(c)(3)"), ("(4) of this section", "(c)(4)")]),
    ("fl", "is protected under s. 119.071(1)(a)(iv), (v), or (b).",
     [("s. 119.071(1)(a)(iv)", "(1)(a)(iv)"), ("(v)", "(1)(a)(v)"), ("(b)", "(1)(b)")]),
    # a pinpoint after a comma is the section's just cited, not the citing section's
    ("nc", "under the provisions of G.S. 59-68, subdivision (b)(2), either alone", [("G.S. 59-68, subdivision (b)(2)",
                                                                                   "(b)(2)")]),
    # New York's Uniform Commercial Code numbers with a double hyphen
    ("ny", "a registration of transfer under Section 8--404 or a claim under Section 8--405.",
     [("Section 8--404", None), ("Section 8--405", None)]),
    # 'or one of its affiliates' is not a list item 'section one'
    ("ny", "a banking institution, as defined in section nine-f of the banking law, or one of\nits affiliates.",
     [("section nine-f of the banking law", None)]),
])
def test_spans_and_pinpoints(con, state, text, expect):
    r = refs_in(text, state)
    assert [(x.span, x.pinpoint) for x in r] == expect


def test_containers_lists_and_kinds(con):
    r = refs_in("under Chapter 3.5 (commencing with Section 4852.01) of Title 6 of Part 3 of the Penal Code, or")
    assert (len(r), r[0].kind, r[0].code) == (1, "container", "Penal Code")
    r = refs_in("in accordance with Chapter 2 of Title 44 and subchapter I of Chapter 5 of Title 3 [ § 3-501 et seq.].",
                "dc")
    assert [x.kind for x in r] == ["container", "container"]
    r = refs_in("subchapters VI , VII , VIII-A , or VIII-G of this chapter, as applicable", "dc")
    assert [x.span for x in r] == ["subchapters VI", "VII", "VIII-A", "VIII-G of this chapter"]
    assert len({x.list_group for x in r}) == 1
    r = refs_in("pursuant to Chapter 118 or 233, Local Government Code, or", "tx")
    assert [(x.span, x.code) for x in r] == [("Chapter 118", "Local Government Code"),
                                             ("233, Local Government Code", "Local Government Code")]


def test_federal_constitutional_and_generic_references_have_no_index_target(con):
    r = refs_in("as defined by 22 U.S.C. Section 7102(9); or regulations, 45 CFR Parts 160 and 164. Notwithstanding "
                "any other provision of law, the laws of the United States apply.", "tx")
    assert [(x.kind, x.sections) for x in r] == [("federal", []), ("federal", []), ("generic", []), ("federal", [])]
    assert r[0].role == "definition" and r[2].role == "override"
    r = refs_in("the access requirements of s. 119.07(1), s. 286.011, or s. 24, Art. I of the State Constitution.",
                "fl")
    assert [x.kind for x in r][-1] == "constitution" and r[-1].span == "s. 24, Art. I of the State Constitution"
    r = refs_in("supersedes the federal Electronic Signatures in Global and National Commerce Act, 15 U.S.C. § 7001 "
                "et seq., but does not modify section 101(c) of that act", "nc")
    assert [x.kind for x in r] == ["federal", "federal", "federal"] and r[0].role == "override"


@pytest.mark.parametrize("state,text,span,kind", [
    ("ca", "Section 3 of, and subdivisions (b) and (c) of Section 4 of, Article XIII of the California Constitution.",
     "Section 3 of, and subdivisions (b) and (c) of Section 4 of, Article XIII of the California Constitution",
     "constitution"),
    ("ca", "of the tax under Article XIII  D of the California Constitution", "Article XIII  D of the California "
     "Constitution", "constitution"),
    ("il", "under subsection (h) of Section 6 of Article VII of the Illinois Constitution of 1970, that any",
     "subsection (h) of Section 6 of Article VII of the Illinois Constitution of 1970", "constitution"),
    ("il", "pursuant to Article IX, Section 5(c) of the Constitution of the State of Illinois, or",
     "Article IX, Section 5(c) of the Constitution of the State of Illinois", "constitution"),
    ("il", "under Article VII, Section 6, subsection (h) of the Illinois Constitution, of the power",
     "Article VII, Section 6, subsection (h) of the Illinois Constitution", "constitution"),
    ("tx", "is authorized by Section 59, Article XVI, Texas Constitution, and", "Section 59, Article XVI, Texas "
     "Constitution", "constitution"),
    ("wa", "as provided in Article VIII, section 7 of the state Constitution.", "Article VIII, section 7 of the state "
     "Constitution", "constitution"),
    ("ny", "consistent with section one of article seven of the state constitution and", "section one of article "
     "seven of the state constitution", "constitution"),
    ("ca", "the amendments made by Section 4 of Chapter 354 of the Statutes of 2004 shall apply", "Section 4 of "
     "Chapter 354 of the Statutes of 2004", "session_law"),
    ("ca", "See Sec. 7, Chapter 913 (pp. 73–76), Statutes of 2014.", "Sec. 7, Chapter 913 (pp. 73–76), Statutes of "
     "2014", "session_law"),
    ("ny", "the lobbying act as enacted by section 1 of chapter 1040 of the laws of 1981. A new", "section 1 of "
     "chapter 1040 of the laws of 1981", "session_law"),
    ("ny", "as added by chapter ninety-six of the laws of nineteen hundred ninety-five, and", "chapter ninety-six of "
     "the laws of nineteen hundred ninety-five", "session_law"),
    ("wa", "Where necessary to implement chapter 521, Laws of 2009, gender-specific terms", "chapter 521, Laws of "
     "2009", "session_law"),
    ("tx", "described by Section 4, Chapter 697, Acts of the 62nd Legislature, Regular Session, 1971 (as",
     "Section 4, Chapter 697, Acts of the 62nd Legislature, Regular Session, 1971", "session_law"),
    ("fl", "(2) Nothing contained in s. 5, chapter 73-129, Laws of Florida, shall be", "s. 5, chapter 73-129, Laws of "
     "Florida", "session_law"),
    ("il", "after August 25, 2009 (the effective date of Public Act 96-731) shall be", "Public Act 96-731",
     "session_law"),
    ("nc", "(18) Repealed by Session Laws 2006-220, s. 1, effective for taxable years", "Session Laws 2006-220, s. 1",
     "session_law"),
    ("dc", "effective December 13, 1977 (D.C. Law 2-38; D.C. Official Code § 2-1403.01 et seq.)", "D.C. Law 2-38",
     "session_law"),
    ("md", "EFFECTIVE UNTIL JUNE 30, 2035 PER CHAPTER 386 OF 2024 // (a) In this subtitle", "CHAPTER 386 OF 2024",
     "session_law"),
    ("tx", "(Article 8280-581, Vernon's Texas Civil Statutes), as that territory", "Article 8280-581, Vernon's Texas "
     "Civil Statutes", "other_code"),
    # New York's budget bills cut into parts: the whole citation is the session law, not 'section 3' of the citing
    # law and a container 'part A of chapter 57'
    ("ny", "as amended by section 3 of part A of chapter 57 of the laws of 2009, the commissioner",
     "section 3 of part A of chapter 57 of the laws of 2009", "session_law"),
    ("ny", "pursuant to subdivision one of section ninety-two of part H of chapter fifty-nine of the laws of two "
     "thousand eleven.", "subdivision one of section ninety-two of part H of chapter fifty-nine of the laws of two "
     "thousand eleven", "session_law"),
    ("ny", "by section one of subpart F of part EE of chapter fifty-six of the laws of two thousand fifteen which",
     "section one of subpart F of part EE of chapter fifty-six of the laws of two thousand fifteen", "session_law"),
    ("ny", "and to section three\nof the part of the chapter of the laws of two thousand twenty-five which amended",
     "section three\nof the part of the chapter of the laws of two thousand twenty-five", "session_law"),
    ("ny", "under section fifteen of chapter forty-three of the laws of New Jersey of nineteen hundred forty-seven, as",
     "section fifteen of chapter forty-three of the laws of New Jersey of nineteen hundred forty-seven", "session_law"),
    # a California bill's own sections
    ("ca", "on the date that Section 8 of the act that added this section becomes operative", "Section 8 of the act "
     "that added this section", "session_law"),
    ("ca", "as specified in subdivision (n) of Section 1 of the act adding this section, the", "subdivision (n) of "
     "Section 1 of the act adding this section", "session_law"),
    ("ca", "pursuant to Section 1 of Assembly Bill 2257 of the 2021–22 Regular Session, to", "Section 1 of Assembly "
     "Bill 2257 of the 2021–22 Regular Session", "session_law"),
    ("ca", "Section 9 of Senate Bill 1344 of the 1989–90 Regular Session applies", "Section 9 of Senate Bill 1344 of "
     "the 1989–90 Regular Session", "session_law"),
    # a California initiative's own sections
    ("ca", "(a) Notwithstanding Section 2 of Proposition 184, as adopted at the November 8, 1994, statewide general",
     "Section 2 of Proposition 184", "session_law"),
    ("ca", "In accordance with Section 11 of the initiative act approved by a majority of the voters at the general "
     "election held on November 4, 1930, (Statutes of 1931, p. lxxxiii) and entitled", "Section 11 of the initiative "
     "act approved by a majority of the voters at the general election held on November 4, 1930", "session_law"),
    # New York's 'a chapter of the laws of ...' (the chapter not yet numbered when the text was written)
    ("ny", "pursuant to\nsection four of a chapter of the laws of two thousand five known as the\nrebuild and renew",
     "section four of a chapter of the laws of two thousand five", "session_law"),
    ("ny", "as provided in\nparagraph (e) of section one of a chapter of the laws of two thousand\nfive which added this",
     "paragraph (e) of section one of a chapter of the laws of two thousand\nfive", "session_law"),
    ("ny", "of this chapter by sections three and four of a chapter\nof the laws of nineteen hundred eighty-two. Specialty",
     "sections three and four of a chapter\nof the laws of nineteen hundred eighty-two", "session_law"),
])
def test_constitutions_and_session_laws_are_taken_whole(con, state, text, span, kind):
    refs = refs_in(text, state)
    start = text.index(span)
    inside = [r for r in refs if r.start < start + len(span) and start < r.end]
    assert [(r.span, r.kind, r.sections, r.unit) for r in inside] == [(span, kind, [], None)]


def test_constitutions_and_session_laws_get_no_target_in_the_citing_code(con):
    ids = mini_index("ca", [(f"Cal. BPC § {n}", f"California Code / Code bpc / Division 1 / Section {n}", "x")
                            for n in (3, 4, 5, 7, 100)])
    row = row_of(ids, "Cal. BPC § 100")
    assert xref.references("ca", row, text="as provided in Section 4.")[0].ids == [ids["Cal. BPC § 4"]]   # control
    text = ("is exempt under subdivision (e) of Section 4 of Article VII of the California Constitution, subject to "
            "Article XIII B of the California Constitution. The amendments made by Section 7 of Chapter 129 of the "
            "Statutes of 1999, and Section 5 and Section 7 of Chapter 130 of the Statutes of 2000, and subdivision (c) "
            "of Section 3 or paragraph (1) of subdivision (a) of Section 4 of Article XIII D of the California "
            "Constitution apply.")
    refs = xref.references("ca", row, text=text)
    assert [(r.kind, r.ids, r.unit) for r in refs] == [("constitution", [], None)] * 2 + [("session_law", [], None)] * 3 \
        + [("constitution", [], None)] * 2
    assert [r.span for r in refs][3:5] == ["Section 5", "Section 7 of Chapter 130 of the Statutes of 2000"]
    # the list rule needs the same numbering: Florida's statute sections stay sections
    r = refs_in("the access requirements of s. 119.07(1), s. 286.011, or s. 24, Art. I of the State Constitution.",
                "fl")
    assert [x.kind for x in r] == ["list_item", "list_item", "constitution"]


def test_california_bill_sections_get_no_target_in_the_citing_code(con):
    ids = mini_index("ca", [(f"Cal. HSC § {n}", f"California Code / Code hsc / Division 1 / Section {n}", "x")
                            for n in (1, 4, 8, 1366)])
    row = row_of(ids, "Cal. HSC § 1366")
    assert xref.references("ca", row, text="as provided in Section 8.")[0].ids == [ids["Cal. HSC § 8"]]   # control
    text = ("It is repealed on the date that Section 8 of the act that added this section becomes operative, as "
            "specified in subdivision (a) of Section 4 of the act adding this section, or Section 1 of Assembly Bill "
            "2257 of the 2021–22 Regular Session, and Section 4 and Section 8 of Senate Bill 1344 of the 1989–90 "
            "Regular Session.")
    refs = xref.references("ca", row, text=text)
    assert [(r.span, r.kind, r.ids) for r in refs] == [
        ("Section 8 of the act that added this section", "session_law", []),
        ("subdivision (a) of Section 4 of the act adding this section", "session_law", []),
        ("Section 1 of Assembly Bill 2257 of the 2021–22 Regular Session", "session_law", []),
        ("Section 4", "session_law", []),
        ("Section 8 of Senate Bill 1344 of the 1989–90 Regular Session", "session_law", [])]
    # without a bill section, 'the act adding this section' leaves 'this section' a reference to the section
    r = xref.references("ca", row, text="the effective date of the act adding this section, the board")
    assert [(x.span, x.kind, x.ids) for x in r] == [("this section", "internal_relative", [ids["Cal. HSC § 1366"]])]


def test_new_york_session_laws_and_double_hyphen_numbers_resolve(con):
    ids = mini_index("ny", [("N.Y. RLA Law § 1", "New York Code / Act RLA / Section 1", "x"),
                            ("N.Y. RLA Law § 7", "New York Code / Act RLA / Section 7", "x"),
                            ("N.Y. UCC Law § 8-404", "New York Code / Act UCC / Article 8 / Part 4 / Section 8-404", "x"),
                            ("N.Y. UCC Law § 8-406", "New York Code / Act UCC / Article 8 / Part 4 / Section 8-406", "x")])
    r = xref.references("ny", row_of(ids, "N.Y. RLA Law § 7"),
                        text="the lobbying act as enacted by section 1 of chapter 1040 of the laws of 1981.")
    assert [(x.span, x.kind, x.ids) for x in r if "chapter" in x.span] == [
        ("section 1 of chapter 1040 of the laws of 1981", "session_law", [])]
    # through a part of the chapter, and a list of spelled-out sections before one: still the session law's
    r = xref.references("ny", row_of(ids, "N.Y. RLA Law § 7"),
                        text="as added by section 1 of part A of chapter 57 of the laws of 2009, and section one or "
                             "section seven of chapter seven hundred seventy-two of the laws of nineteen hundred "
                             "sixty-six, and section one of this chapter.")
    assert [(x.span, x.kind, x.ids) for x in r] == [
        ("section 1 of part A of chapter 57 of the laws of 2009", "session_law", []),
        ("section one", "session_law", []),
        ("section seven of chapter seven hundred seventy-two of the laws of nineteen hundred sixty-six", "session_law",
         []),
        ("section one of this chapter", "section", [ids["N.Y. RLA Law § 1"]])]           # control
    r = xref.references("ny", row_of(ids, "N.Y. UCC Law § 8-406"),
                        text="under Section 8--404 or a claim, and see section 5--to the extent applicable")
    assert [(x.span, x.ids) for x in r] == [("Section 8--404", [ids["N.Y. UCC Law § 8-404"]]), ("section 5", [])]
    assert xref.norm_num("8--404") == "8-404"


def ny_index():
    """N.Y. State Finance Law, Family Court Act, Social Services Law and Public Authorities Law rows, in two
    articles each (so each law's root is the law, as in the real index), with the second versions of § 92-GG and
    § 1199-GGGG and the repeated-letter numbers § 1199-HHHH and Exec. Law § 160-AAA."""
    rows = [(f"N.Y. STF Law § {n}", f"New York Code / Act STF / Article {a} / Section {n}", "x")
            for a, n in ((1, 1), (1, 2), (1, 4), (1, 7), (6, "92-GG"), (6, "92-GG*2"))]
    rows += [(f"N.Y. FCT Law § {n}", f"New York Code / Act FCT / Article {a} / Section {n}", "x")
             for a, n in (("1", 111), ("6 / Part 1", 634), ("6 / Part 1-A", 635), ("6 / Part 1-A", 636))]
    rows += [(f"N.Y. SOS Law § {n}", f"New York Code / Act SOS / Article {a} / Section {n}", "x")
             for a, n in ((1, 2), (6, "384-B"))]
    rows += [(f"N.Y. PBA Law § {n}", f"New York Code / Act PBA / Article {a} / Section {n}", "x")
             for a, n in ((1, 2), (8, 1199), (8, "1199-AAAA"), (8, "1199-GGGG*2"), (8, "1199-HHHH"))]
    rows += [(f"N.Y. EXC Law § {n}", f"New York Code / Act EXC / Article {a} / Section {n}", "x")
             for a, n in ((1, 1), (6, 160), (6, "160-AAA"))]
    return mini_index("ny", rows)


def test_new_york_sessions_laws_of_a_chapter_get_no_target_in_the_citing_law(con):
    # 'section four of a chapter of the laws of two thousand five' (with 'a', not 'the'): N.Y. STF § 4 is not cited
    ids = ny_index()
    row = row_of(ids, "N.Y. STF Law § 7", "New York Code / Act STF / Article 1 / Section 7")
    r = xref.references("ny", row, text="pursuant to section four of a chapter of the laws of two thousand five known "
                                        "as the rebuild and renew New York transportation bond act, and section one of "
                                        "this chapter.")
    assert [(x.span, x.kind, x.ids) for x in r] == [
        ("section four of a chapter of the laws of two thousand five", "session_law", []),
        ("section one of this chapter", "section", [ids["N.Y. STF Law § 1"]])]              # control


def test_section_of_such_part_is_the_part_cited_before(con):
    # N.Y. STF § 92-GG*2: 'such part' is part VV of a session law; its label, '* § 92-gg.', and the editor's note
    # '* NB There are 2 § 92-gg's' are not references
    ids = ny_index()
    gg2 = row_of(ids, "N.Y. STF Law § 92-GG*2", "New York Code / Act STF / Article 6 / Section 92-GG*2")
    text = ("* § 92-gg. Subway assistance fund. 1. There is hereby established a fund.\n  2. The fund shall consist "
            "of any monies directed\nthereto pursuant to the provisions of section four of part VV of the\nchapter of "
            "the laws of two thousand eighteen which added this section.\n  3. All monies deposited pursuant to\npart "
            "VV of the chapter of the laws of two thousand eighteen shall be paid in the same manner as the "
            "payments\nrequired by subdivision (b) of section two of such part, as soon as\npracticable.\n  * NB There "
            "are 2 § 92-gg's")
    r = xref.references("ny", gg2, text=text)
    assert [(x.span, x.kind, x.ids) for x in r] == [
        ("section four of part VV of the\nchapter of the laws of two thousand eighteen", "session_law", []),
        ("this section", "internal_relative", [ids["N.Y. STF Law § 92-GG*2"]]),
        ("part VV of the chapter of the laws of two thousand eighteen", "session_law", []),
        ("subdivision (b) of section two of such part", "session_law", [])]
    # without a part cited before it: no target, not the citing law's § 2
    r = xref.references("ny", row_of(ids, "N.Y. STF Law § 7"), text="the payments required by section two of such "
                                                                       "part, as soon as practicable")
    assert [(x.span, x.ids, x.note) for x in r] == [("section two of such part", [], "anaphor")]
    # a code's part: that code's section, only when the index holds it inside that part (§ 635 is in Part 1-A of
    # Article 6 of the Family Court Act, § 634 in Part 1)
    sos = row_of(ids, "N.Y. SOS Law § 384-B", "New York Code / Act SOS / Article 6 / Section 384-B")
    for n, want in (("thirty-five", [ids["N.Y. FCT Law § 635"]]), ("thirty-four", [])):
        r = xref.references("ny", sos, text="may be brought in accordance with part one-A of article six of the "
                                            f"family court act where the conditions enumerated in section six hundred "
                                            f"{n} of such\npart have been met.")
        assert [(x.kind, x.ids) for x in r] == [("container", []), ("other_code", want)]
        assert r[0].unit["path"] == "New York Code / Act FCT / Article 6 / Part 1-A"


def test_a_second_version_of_a_new_york_section_cites_its_own_law(con):
    # 'N.Y. STF Law § 92-GG*2': the star is part of the number, so 'section two of this chapter' is STF § 2, not
    # § 92-GG*2 itself (the prefix was 'N.Y. STF Law § 92-GG*')
    assert xref._prefix("N.Y. STF Law § 92-GG*2") == "N.Y. STF Law § "
    assert xref._prefix("N.Y. LAB Law § 850*") == "N.Y. LAB Law § "
    ids = ny_index()
    gg2 = row_of(ids, "N.Y. STF Law § 92-GG*2", "New York Code / Act STF / Article 6 / Section 92-GG*2")
    r = xref.references("ny", gg2, text="as provided in section two of this chapter.")
    assert [(x.span, x.ids) for x in r] == [("section two of this chapter", [ids["N.Y. STF Law § 2"]])]
    assert "N.Y. STF Law § 92-GG*" not in xref.table("ny").prefixes


def test_new_york_numbers_with_a_repeated_letter(con):
    # '§ 160-aaa', 'section eleven hundred ninety-nine-hhhh': not § 160 or § 1199
    ids = ny_index()
    row = row_of(ids, "N.Y. PBA Law § 1199-AAAA", "New York Code / Act PBA / Article 8 / Section 1199-AAAA")
    r = xref.references("ny", row, text="a trustee appointed pursuant to section eleven hundred ninety-nine-hhhh of\n"
                                        "this title, as defined in section 160-aaa of the executive law, and section "
                                        "1199 of this title.")
    assert [(x.span, x.ids) for x in r] == [
        ("section eleven hundred ninety-nine-hhhh of\nthis title", [ids["N.Y. PBA Law § 1199-HHHH"]]),
        ("section 160-aaa", [ids["N.Y. EXC Law § 160-AAA"]]),     # a list's first item: its qualifier is in no span
        ("section 1199 of this title", [ids["N.Y. PBA Law § 1199"]])]                     # control
    assert xref.words_to_num("eleven hundred ninety-nine-hhhh") == "1199-HHHH"
    assert xref.words_to_num("three hundred one-a") == "301-A"


def test_list_items_before_a_session_law_follow_its_own_first_section(con):
    # the session law's first section is read inside its span: 'part A of chapter 57 of the laws of 2009' has none,
    # so the 'section 3' that follows it does not make 'section 5' the session law's
    ids = mini_index("ny", [(f"N.Y. RLA Law § {n}", f"New York Code / Act RLA / Section {n}", "x") for n in (3, 5, 7)])
    row = row_of(ids, "N.Y. RLA Law § 7")
    r = xref.references("ny", row, text="as amended by section 5 or part A of chapter 57 of the laws of 2009, as "
                                        "amended by section 3 of this chapter, the")
    assert [(x.span, x.kind, x.ids) for x in r] == [
        ("section 5", "section", [ids["N.Y. RLA Law § 5"]]),
        ("part A of chapter 57 of the laws of 2009", "session_law", []),
        ("section 3 of this chapter", "section", [ids["N.Y. RLA Law § 3"]])]
    r = xref.references("ny", row, text="as amended by section 5 or section 3 of part A of chapter 57 of the laws of "
                                        "2009, the")
    assert [(x.span, x.kind, x.ids) for x in r] == [                                     # control
        ("section 5", "session_law", []), ("section 3 of part A of chapter 57 of the laws of 2009", "session_law", [])]


def test_such_subdivision_is_the_pinpoint_cited_last(con):
    text = ('shall be governed by the provisions of subdivision six of section one hundred twenty-w of the general '
            'municipal law and the term "municipality" as used in such subdivision six shall mean the agency.')
    r = refs_in(text, "ny", {"id": 7, "citation": "N.Y. PBA Law § 2050-P", "path": ""})
    assert [(x.span, x.pinpoint, x.code) for x in r] == [
        ("subdivision six of section one hundred twenty-w of the general municipal law", "(6)", "general municipal law"),
        ("subdivision six", "(6)", "general municipal law")]
    assert r[1].note == "anaphor" and r[1].ids != [7]


def test_survey_sections_and_federal_or_state_programs_are_not_law(con):
    assert refs_in("lying in Section 23, Township 14 South, Range 29 East; thence along", "fl") == []
    assert refs_in("under a federal or State program allowing a law enforcement agency to obtain equipment", "il") == []
    assert [(x.span, x.kind) for x in refs_in("as required by federal law.", "il")] == [("federal law", "federal")]


@pytest.mark.parametrize("text,refs", [
    # federal law named together with state law keeps its federal reference
    ("is prohibited by federal and/or state law or rule.", [("federal and/or state law", "federal")]),
    ("required by federal or state law, the agency", [("federal or state law", "federal")]),
    ("shall comply with all federal and state laws governing the use", [("federal and state laws", "federal")]),
    ("if it meets federal and state requirements for the program", [("federal and state requirements", "federal")]),
    # police, not law; agencies, not law
    ("shared with federal or state law enforcement agencies", []),
    ("federal law enforcement agencies and state law", [("state law", "generic")]),
    ("to federal or state agencies authorized by law to receive it", [("authorized by law", "generic")]),
    # the hyphenated form is police too, and so is 'other law enforcement'
    ("shared with a federal or State law-enforcement agency for", []),
    ("notify any other law-enforcement agency or other law enforcement agencies", []),
    ("as required by law enforcement officials, the", []),
    # a verb, a preposition or an article ends a federal name; courts make court rules
    ("The federal grant funds are subject to State law.", [("State law", "generic")]),
    ("reported by the federal agency in accordance with State law.", [("State law", "generic")]),
    ("authorizes the federal agency to act on the request", []),
    ("under federal or State court rules, the", []),
    # ... except between capitalised words, and an act's name ends at 'Act'
    ("under federal Department of Labor regulations, the", [("federal Department of Labor regulations", "federal")]),
    ("the federal Americans with Disabilities Act applies", [("federal Americans with Disabilities Act", "federal")]),
    ("pursuant to the federal Social Security Act and federal regulations", [("federal Social Security Act", "federal"),
                                                                            ("federal regulations", "federal")]),
])
def test_federal_and_state_law_is_federal(con, text, refs):
    assert [(x.span, x.kind) for x in refs_in(text, "il")] == refs


@pytest.mark.parametrize("state,text,refs", [
    # a federal act's name written in lower case keeps its prepositions; a year may be part of it
    ("wa", "if it has complied with section 13402 of the federal health information technology for economic and "
           "clinical health act, P.L. 111-5 as it existed", [("section 13402 of the federal health information "
                                                             "technology for economic and clinical health act",
                                                             "federal"), ("P.L. 111-5", "federal")]),
    ("il", "being sold under Regulation D, Section 506 of the Federal 1933 Act) after", [("Section 506 of the Federal "
                                                                                         "1933 Act", "federal")]),
])
def test_federal_act_names_in_a_section_citation(con, state, text, refs):
    assert [(x.span, x.kind) for x in refs_in(text, state)] == refs


@pytest.mark.parametrize("state,text,kinds", [
    # general patterns, not phrases of one gold sentence
    ("ca", "in accordance with procedures adopted by the Judicial Council.",
     [("procedures adopted by the Judicial Council", "court_rule")]),
    ("ca", "under rules adopted by the Judicial Council, the", [("rules adopted by the Judicial Council", "court_rule")]),
    ("ca", "except regulations adopted by the city council", [("regulations adopted by the city council", "regulation")]),
    ("nc", "are supplemented by the principles of law and equity.", [("the principles of law and equity", "generic")]),
    ("dc", "deprived of a constitutional right, power, privilege, or immunity", [("constitutional right", "constitution")]),
    # removed: phrases that occur in one to a few sections of the corpus
    ("fl", "software that is protected by copyright or trade secret laws.", []),
    ("ny", "shall, in accordance with its published rules, make available", []),
])
def test_generic_and_rule_patterns(con, state, text, kinds):
    assert [(x.span, x.kind) for x in refs_in(text, state)] == kinds


def test_history_labels_and_source_notes_are_not_references(con):
    assert refs_in("(b) Section 119.105 commits a felony.\n\nHistory: s. 10, ch. 67-125; s. 74, ch. 71-136.",
                   "fl")[0].span == "Section 119.105"
    assert len(refs_in("(b) Section 119.105 commits a felony.\n\nHistory: s. 10, ch. 67-125.", "fl")) == 1
    assert refs_in("§ 1101. Fees. Except as otherwise provided, the fees pursuant to this chapter:", "ny")[0].span \
        == "Except as otherwise provided"
    assert [x.span for x in refs_in("(5 ILCS 140/2) (from Ch. 116, par. 202) Sec. 2. Definitions. As used in this "
                                    "Act: (Source: P.A. 103-554, eff. 1-1-24.)", "il")] == ["this Act"]
    assert refs_in("Code 1950, § 18.1-27; 1960, c. 358; 1975, cc. 14, 15.", "va") == []
    # a New York section with two versions: the starred label and the editor's note on the versions
    assert refs_in("* § 92-gg. Subway assistance fund. 1. There is hereby established a fund.\n  * NB There are 2 "
                   "§ 92-gg's", "ny") == []


@pytest.mark.parametrize("text,span,role", [
    ("a serious felony, as defined in Section 1192.7 of the Penal Code", "Section 1192.7 of the Penal Code",
     "definition"),
    ("(b) Notwithstanding subsection (a) of this section, unless", "subsection (a) of this section", "override"),
    ("(a) Except as specified in subdivision (b), a person", "subdivision (b)", "exception"),
    ("(a) Subject to Section 37-36, a plan of merger", "Section 37-36", "exception"),
    ("a misdemeanor, punishable as provided in Section 775.082 or", "Section 775.082", "penalty"),
    ("a conviction that has been dismissed pursuant to Section 1203.4, the", "Section 1203.4", "prerequisite_process"),
    ("pursuant to rules and regulations adopted pursuant to Section 9.1-128 and", "Section 9.1-128", "authority"),
    ("the case decision in accordance with Section 2.2-4026.", "Section 2.2-4026", "procedure"),
    ("demonstrate their compliance with Section 54.1-3006.2 upon", "Section 54.1-3006.2", "condition"),
    ("As used in this chapter, the term", "this chapter", "scope"),
    ("The provisions of this chapter prohibiting the practice shall not apply:", "this chapter", "exception"),
])
def test_roles_from_cue_words(con, text, span, role):
    assert by_span(refs_in(text), span).role == role


@pytest.mark.parametrize("state,text,span,role", [
    # a fee schedule's item (a clause that begins 'For ...' and names an amount): the reference is the fee's scope
    ("ny", "(b) For filing a certificate of amendment pursuant to section two hundred eleven of this chapter, sixty "
           "dollars.", "section two hundred eleven of this chapter", "scope"),
    ("tx", "(11) for filing a report under Chapter 22, $5; (12) for", "Chapter 22", "scope"),
    ("ca", "(b) For an applicant licensed under Section 5, fifty dollars.", "Section 5", "scope"),
    ("ca", "(b) For an applicant licensed under Section 5, the board shall", "Section 5", "prerequisite_process"),
    # 'For purposes of ...' is not a fee schedule's item: the reference keeps its own cue's role
    ("ca", "(h) For purposes of making the computations required by Section 8 of Article XVI of the California "
           "Constitution, two billion dollars ($2,000,000,000).",
     "Section 8 of Article XVI of the California Constitution", "authority"),
    ("ca", "(b) For the purposes of an applicant licensed under Section 5, fifty dollars.", "Section 5",
     "prerequisite_process"),
    # 'violation of X' is scope (a cue that never matched before)
    ("ca", "for a violation of 18 U.S.C. 1030, the court", "18 U.S.C. 1030", "scope"),
    # session-law citations are history: other
    ("ca", "as amended by Chapter 857 of the Statutes of 1965.", "Chapter 857 of the Statutes of 1965", "other"),
])
def test_roles_of_fee_items_violations_and_session_laws(con, state, text, span, role):
    assert by_span(refs_in(text, state), span).role == role


# ------------------------------------------------------------------ the code table
def test_a_code_root_survives_a_few_rows_with_odd_paths(con):
    # 'Tex. Insurance Code - Not Codified': 64 of its 68 rows under 'TX Code / Code i1', 4 under 'Texas Code / Code
    # i1'; no prefix reaches the 95% share, which left the root empty
    rows = [(f"Tex. Penal Code § {c}.0{k}", f"TX Code / Code pe / Chapter {c} / Section {c}.0{k}", "x")
            for c in (1, 2, 3, 4) for k in (1, 2, 3)]
    rows += [(f"Tex. Insurance Code - Not Codified § {k}", f"TX Code / Code i1 / Chapter 5 / Section {k}", "x")
             for k in range(1, 17)]
    rows += [(f"Tex. Insurance Code - Not Codified § {k}", f"Texas Code / Code i1 / Chapter 21 / Section {k}", "x")
             for k in (30, 31)]
    mini_index("tx", rows)
    tab = xref.table("tx")
    assert tab.prefixes["Tex. Insurance Code - Not Codified § "]["root"] == "TX Code / Code i1"
    assert tab.prefixes["Tex. Penal Code § "]["root"] == "TX Code / Code pe"
    assert all(e["root"] for e in tab.prefixes.values())


def test_a_law_named_by_a_short_title_resolves_to_it(con):
    # 'Titles 11 through 27 of this article may be cited as the Maryland Vehicle Law': the law is those titles,
    # anchored at the short-title section, not the whole Transportation Article read as another code
    ids = mini_index("md", [
        ("Md. Code, Transportation § 11-206", "MD Code / Article gtr / Title 11 / Subtitle 2 / Section 11-206",
         "Titles 11 through 27 of this article may be cited as the Maryland Vehicle Law."),
        ("Md. Code, Transportation § 12-101", "MD Code / Article gtr / Title 12 / Subtitle 1 / Section 12-101", "x"),
        ("Md. Code, Transportation § 26-202", "MD Code / Article gtr / Title 26 / Subtitle 2 / Section 26-202", "x"),
        ("Md. Code, Transportation § 27-101", "MD Code / Article gtr / Title 27 / Subtitle 1 / Section 27-101", "x"),
        ("Md. Code, Transportation § 28-101", "MD Code / Article gtr / Title 28 / Subtitle 1 / Section 28-101", "x"),
        ("Md. Code, Criminal Law § 1-101", "MD Code / Article gcr / Title 1 / Subtitle 1 / Section 1-101", "x")])
    e = xref.table("md").names["maryland vehicle law"]
    assert (e["kind"], e["anchor"][1]) == ("act", "Md. Code, Transportation § 11-206")
    assert [p.rsplit(" / ", 1)[-1] for p in e["units"]] == ["Title 11", "Title 12", "Title 26", "Title 27"]
    r = xref.references("md", row_of(ids, "Md. Code, Transportation § 26-202"),
                        text="arrest a person for a violation of the Maryland Vehicle Law, if")
    assert [(x.span, x.kind, x.ids, x.role) for x in r] == [
        ("the Maryland Vehicle Law", "named_act", [ids["Md. Code, Transportation § 11-206"]], "scope")]
    assert (r[0].unit["path"], r[0].unit["through"], r[0].unit["sections"], r[0].unit["exact"]) == (
        "MD Code / Article gtr / Title 11", "MD Code / Article gtr / Title 27", 4, False)


def test_a_code_name_ending_a_sentence_leaves_the_full_stop_out(con):
    # 'of the general municipal law.': the name is read from the table, its last word without the sentence's full
    # stop
    ids = mini_index("ny", [("N.Y. GMU Law § 120-W", "New York Code / Act GMU / Article 6 / Section 120-W", "x"),
                            ("N.Y. PBA Law § 2050-P", "New York Code / Act PBA / Article 8 / Section 2050-P", "x")])
    r = xref.references("ny", row_of(ids, "N.Y. PBA Law § 2050-P"),
                        text="as provided in subdivision six of section one hundred twenty-w of the general municipal "
                             "law. The term")
    assert [(x.span, x.ids) for x in r] == [("subdivision six of section one hundred twenty-w of the general "
                                             "municipal law", [ids["N.Y. GMU Law § 120-W"]])]
    ids = mini_index("ca", [("Cal. GOV § 11270", "California Code / Code gov / Title 2 / Section 11270", "x"),
                            ("Cal. BPC § 25761", "California Code / Code bpc / Division 9 / Section 25761", "x")])
    r = xref.references("ca", row_of(ids, "Cal. BPC § 25761"),
                        text="in accordance with Section 11270 and following of the Government Code. A hearing")
    assert [(x.span, x.ids) for x in r] == [
        ("Section 11270 and following of the Government Code", [ids["Cal. GOV § 11270"]])]


# ------------------------------------------------------------------ resolution against the fixture index
@pytest.fixture()
def fixture_index(con, va_statutes):
    from lexflow.ask import index as I

    def build(state):
        assert I.ensure(state)
        return I
    return build


def fixture_refs(I, state: str, citation: str):
    row = I.lookup(state, citation)[0]
    return row, xref.references(state, row)


def test_florida_s_citations_resolve_and_history_is_skipped(fixture_index):
    I = fixture_index("fl")
    row, refs = fixture_refs(I, "fl", "Fla. Stat. § 607.193")
    resolved = {s["citation"] for r in refs for s in r.sections}
    assert resolved == {"Fla. Stat. § 605.0213", "Fla. Stat. § 607.0122", "Fla. Stat. § 620.1109"}
    fees = [r for r in refs if r.list_group and r.sections]
    assert [r.span for r in fees] == ["ss. 605.0213", "607.0122", "620.1109"]
    unresolved = [r for r in refs if r.span in ("s. 605.0212", "s. 607.1622", "s. 620.1210")]
    assert unresolved and all(r.note == "not in index" and r.sections == [] for r in unresolved)
    assert not any("ch. 92-319" in r.span or r.start > row_text_history(I, row) for r in refs)
    from lexflow.ask import retrieve
    assert retrieve.cited("fl", row, limit=100) == []              # the current resolver needs '§' or 'section'


def row_text_history(I, row) -> int:
    return I.text_of("fl", row["id"]).index("History:")


def test_north_carolina_gs_citations_and_roles(fixture_index):
    I = fixture_index("nc")
    row, refs = fixture_refs(I, "nc", "N.C. Gen. Stat. § 132-9")
    got = {r.span: ([s["citation"] for s in r.sections], r.role) for r in refs if r.sections and r.kind == "section"}
    assert got == {"G.S. 7A-38.3E": (["N.C. Gen. Stat. § 7A-38.3E"], "prerequisite_process"),
                   "G.S. 132-6": (["N.C. Gen. Stat. § 132-6"], "prerequisite_process")}
    this = [r for r in refs if r.span == "this section"]
    assert len(this) == 4 and all(r.ids == [row["id"]] for r in this)
    article = by_span(refs, "Article 2 of Chapter 131E of the General Statutes")
    assert article.kind == "container" and article.sections == []


def test_lists_ranges_and_missing_sections_in_texas(fixture_index):
    I = fixture_index("tx")
    row, refs = fixture_refs(I, "tx", "Tex. Business Organizations Code § 3.001")
    items = [r for r in refs if r.list_group]
    assert [(r.span, [s["citation"] for s in r.sections]) for r in items][:3] == [
        ("Sections 3.003", []), ("3.004", ["Tex. Business Organizations Code § 3.004"]),
        ("3.005", ["Tex. Business Organizations Code § 3.005"])]
    assert by_span(refs, "Subsection (a)").ids == [row["id"]]


def test_illinois_this_act_and_new_york_articles(fixture_index):
    I = fixture_index("il")
    _, refs = fixture_refs(I, "il", "5 ILCS 140/9")
    assert {r.span: [s["citation"] for s in r.sections] for r in refs if "Section" in r.span} == {
        "Section 11 of this Act": [], "Section 7 of this Act": [], "Section 3 of this Act": ["5 ILCS 140/3"]}
    assert by_span(refs, "Section 11 of this Act").role == "procedure"   # 'right to judicial review under'
    I = fixture_index("ny")
    _, refs = fixture_refs(I, "ny", "N.Y. PTR Law § 121-1300")
    assert ["N.Y. PTR Law § 121-201"] in [[s["citation"] for s in r.sections] for r in refs]
    assert all(r.role == "scope" for r in refs if "121-201" in r.span)   # a fee schedule's items


def test_other_code_by_name_and_no_fallback_across_codes(fixture_index):
    I = fixture_index("ca")
    _, refs = fixture_refs(I, "ca", "Cal. GOV § 12190")
    corp = by_span(refs, "Section 17702.09 of the Corporations Code")
    assert (corp.kind, corp.code, [s["citation"] for s in corp.sections]) == (
        "other_code", "Cal. CORP § ", ["Cal. CORP § 17702.09"])
    gov = I.lookup("ca", "Cal. GOV § 12190")[0]
    bare = xref.references("ca", gov, text="pursuant to Section 17702.09, twenty dollars")
    assert bare[0].sections == [] and bare[0].code == "Cal. GOV § "   # a bare number stays in the citing code
    assert xref.table("ca").names["corporations code"]["prefix"] == "Cal. CORP § "
