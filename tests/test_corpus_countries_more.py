"""The adapters added on 22 October 2026 (lexflow/corpus/countries/): Australia's Federal Register of Legislation,
the state registers (Tasmania's EnAct XML, South Australia's SAOPC XML, Western Australia's Word-exported HTML, and
the stubs that say what permission is missing), Romania's Portal Legislativ web service, Chile's interim
per-question mode, and the corpus interface that streams a country pulled one law per file.  The fixtures
(fixtures/corpus/<key>/sample.json) were made from the pulls of that day; the parsers are also tested on small
inline documents written in each source's own markup.  No network."""
import io
import json
import zipfile

import pytest

from lexflow import config
from lexflow.ask import index as I
from lexflow.corpus import countries as C
from lexflow.corpus.countries import australia as A
from lexflow.corpus.countries import australia_states as S
from lexflow.corpus.countries import base
from lexflow.corpus.countries import chile as CH
from lexflow.corpus.countries import romania as R
from lexflow.municipal import statutes

STATUTE_COLUMNS = set(statutes.COLUMNS)
MINE = ["aus", "aus-tas", "aus-sa", "aus-wa", "rou"]


@pytest.fixture()
def tmp_index(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(C, "DIR", tmp_path / "raw" / "countries")
    I._STAMPS.clear(), I._READY.clear()
    return tmp_path


# ---------------------------------------------------------------------- keys and registry
def test_keys_are_alpha3_and_the_states_sit_under_australia():
    for key, iso2 in (("aus", "au"), ("chl", "cl"), ("rou", "ro"), ("gha", "gh"), ("per", "pe")):
        a = C.get(key)
        assert a.code == key and a.iso2 == iso2 and a.eli_jurisdiction == iso2 and C.get(iso2) is a
    states = [c for c in C.CODES if c.startswith("aus-")]
    assert states == ["aus-nsw", "aus-vic", "aus-qld", "aus-wa", "aus-sa", "aus-tas", "aus-act", "aus-nt"]
    assert C.BY_KEY["aus"]["subnational"] == states
    for k in states:
        a, j = C.get(k), C.BY_KEY[k]
        assert a.parent == "aus" and a.eli_jurisdiction == "au-" + k[4:] and j["parent"] == "aus"
        assert j["iso3166_2"] == "AU-" + k[4:].upper() and j["wikidata"].startswith("Q")
        assert a.raw_name == f"{k}/rows"
    assert {k: C.get(k).status for k in states} == {
        "aus-nsw": "stub", "aus-vic": "stub", "aus-qld": "stub", "aus-wa": "prototype", "aus-sa": "prototype",
        "aus-tas": "prototype", "aus-act": "stub", "aus-nt": "stub"}
    assert C.get("aus").status == C.get("rou").status == "prototype"
    assert C.get("gha").status == C.get("per").status == "stub"


@pytest.mark.parametrize("key", ["aus-nsw", "aus-vic", "aus-qld", "aus-act", "aus-nt", "gha", "per"])
def test_what_needs_permission_says_why(key):
    a = C.get(key)
    with pytest.raises(NotImplementedError, match=a.name):
        a.fetch_document("x")
    with pytest.raises(NotImplementedError):
        a.fetch_list()
    words = {"aus-nsw": "403", "aus-vic": "personal use only", "aus-qld": "account", "aus-act": "All rights reserved",
             "aus-nt": "approval list", "gha": "written permission", "per": "paid licence"}[key]
    assert words in a.note


# ---------------------------------------------------------------------- the fixtures as rows
def _rows(key):
    doc = C.load_document(key)
    assert doc is not None and doc.fetched == "2026-10-22"
    return doc, C.rows_for(key, doc)


@pytest.mark.parametrize("key", MINE)
def test_fixture_rows_have_the_us_shape(key):
    a = C.get(key)
    doc, rows = _rows(key)
    fx = json.loads(C.fixture_path(key).read_text(encoding="utf-8"))
    assert fx["row_count"] == len(rows) and fx["licence"] == doc.licence and fx["attribution"]
    for r in rows:
        assert STATUTE_COLUMNS <= set(r) and set(base.EXTRA) <= set(r)
        assert r["act_id"].startswith(f"STATE_{a.code.upper()}_")
        assert r["eli"].startswith(f"{base.ELI_BASE}/{a.eli_jurisdiction}/") and "@" in r["eli"]
        assert r["text"] and r["word_count"] > 0 and r["source_url"].startswith("https://")
        assert r["country"] == a.code and r["language"] == a.languages[0] and r["ref"] == r["citation"]
    for col in ("citation", "eli", "act_id"):
        assert len({r[col] for r in rows}) == len(rows), col


def test_federal_fixture():
    doc, rows = _rows("aus")
    assert doc.title == "Electronic Transactions Act 1999" and doc.native_id == "C2004A00553"
    assert doc.year == "1999" and doc.eli_number == "162" and doc.number == "No. 162, 1999"
    assert doc.extra["register_id"].startswith("C20") and doc.extra["attribution"].startswith(
        "Sourced from the Federal Register of Legislation at 22 October 2026.")
    first = rows[0]
    assert first["citation"] == "Electronic Transactions Act 1999 s 1" and first["section_title"] == "Short title"
    assert first["display_path"] == "Electronic Transactions Act 1999 / Part 1 / Section 1"
    assert first["act_id"] == "STATE_AUS_C2004A00553_P1_S1"
    assert first["eli"].startswith(f"{base.ELI_BASE}/au/act/1999/162/sec_1/en@")
    assert first["source_url"].startswith("https://www.legislation.gov.au/C2004A00553/")
    assert {"title_id", "register_id", "compilation_date", "fetched"} <= set(first)
    sched = [r for r in rows if " sch " in r["citation"]]
    assert sched and all(" cl " in r["citation"] and r["level"] == "Clause" for r in sched)
    assert all("\xa0" not in r["text"] and "‑" not in r["text"] for r in rows)


def test_state_fixtures():
    _, tas = _rows("aus-tas")
    assert tas[0]["citation"] == "Natural Resource Management Act 2002 s 1"
    assert tas[0]["source_url"].startswith("https://www.legislation.tas.gov.au/view/whole/html/inforce/")
    assert any(r["level"] == "Clause" and " sch " in r["citation"] for r in tas)
    _, sa = _rows("aus-sa")
    assert sa[0]["citation"] == "Small Business Commission Act 2011 s 1" and sa[0]["act_id"].startswith("STATE_AUS-SA_A2011.41_")
    _, wa = _rows("aus-wa")
    assert wa[0]["text"] == "This Act may be cited as the Carers Recognition Act 2004."      # footnote mark dropped
    assert [r["citation"] for r in wa if "sch 2" in r["citation"]] == ["Carers Recognition Act 2004 sch 2 div 1",
                                                                        "Carers Recognition Act 2004 sch 2 div 2"]
    for key, start in (("aus-tas", "Based on material from the Tasmanian Legislation website at 22 October 2026."),
                       ("aus-wa", "Based on content from the Western Australian Legislation website at 22 October 2026."),
                       ("aus-sa", "Based on the South Australian Legislative Database Update Package (XML)")):
        assert C.load_document(key).extra["attribution"].startswith(start)


def test_romania_fixture_and_splitter():
    doc, rows = _rows("rou")
    assert doc.short_title == "Legea nr. 190/2020" and doc.native_id == "229509" and doc.version_date == "2020-08-27"
    assert rows[0]["citation"] == "Legea nr. 190/2020, art. 1" and rows[0]["chapter_name"] == "Dispoziții generale"
    assert rows[0]["display_path"] == "Legea nr. 190/2020 / Capitolul I / Articolul 1"
    assert rows[0]["text"].startswith("(1) Prezenta lege are ca obiect") and "\n(2) " in rows[0]["text"]
    assert rows[0]["eli"] == f"{base.ELI_BASE}/ro/lege/2020/190/art_1/ro@2020-08-27"
    assert any(r["citation"].startswith("Legea nr. 190/2020, anexa nr. ") for r in rows)
    # the service's own text, split again, gives the same rows
    rec = {"Text": doc.extra["text"], "Titlu": doc.extra["titlu"], "TipAct": "LEGE", "Numar": "190",
           "DataVigoare": "2020-08-27", "LinkHtml": "http://legislatie.just.ro/Public/DetaliiDocument/229509"}
    again = R.Romania().to_rows(R.Romania().parse(rec))
    assert [r["citation"] for r in again] == [r["citation"] for r in rows]


def test_romania_amending_law_is_one_article():
    text = (" LEGE nr. 9 din 1 martie 2026 pentru modificarea art. 17 din Legea nr. 1/2000     EMITENT     PARLAMENTUL"
            "\n\t\t\t\t\xa0+\xa0\n\t\t\t  ARTICOL UNIC      Articolul 17 din Legea nr. 1/2000 se modifică şi va avea "
            "următorul cuprins:  "
            "\n\t\t\t\t\xa0+\xa0\n\t\t\t  Articolul 17      (1)    Colegiul este compus din 13 membri.    (2)    "
            "Membrii sunt numiţi pe 5 ani.\n")
    doc = R.Romania().parse({"Text": text, "Titlu": "LEGE nr. 9 din 1 martie 2026 pentru modificarea art. 17",
                             "TipAct": "LEGE", "Numar": "9", "DataVigoare": "2026-03-04",
                             "LinkHtml": "http://legislatie.just.ro/Public/DetaliiDocument/1"})
    rows = R.Romania().to_rows(doc)
    assert [r["citation"] for r in rows] == ["Legea nr. 9/2026, articol unic"]
    assert rows[0]["text"].endswith("(1) Colegiul este compus din 13 membri.\n(2) Membrii sunt numiţi pe 5 ani.")
    assert R.Romania().parse({"Text": " LEGE nr. 1 din 1 mai 2026 privind ceva", "Titlu": "LEGE nr. 1 din 1 mai 2026",
                              "TipAct": "LEGE", "Numar": "1"}).root is None            # no text: no rows


# ---------------------------------------------------------------------- the federal parser on inline XHTML
def _p(cls, *spans, id_=""):
    inner = "".join(f'<span class="{c}">{t}</span>' if c else f"<span>{t}</span>" for c, t in spans)
    return f'<p class="{cls}"{f" id={chr(34)}{id_}{chr(34)}" if id_ else ""}>{inner}</p>'


def _head(level, word, no, text):
    k = {"Part": "Part", "Division": "Div", "Chapter": "Chap", "Schedule": "Chap"}[word]
    return (f'<p class="ActHead{level}" id="navPoint_{no}"><a><span class="Char{k}No">{word}</span>'
            f'<span class="Char{k}No">&#xa0;</span><span class="Char{k}No">{no}</span><span>—</span>'
            f'<span class="Char{k}Text">{text}</span></a></p>')


def _sec(no, text):
    return (f'<p class="ActHead5" id="navPoint_s{no}"><a><span class="CharSectno">{no}</span><span>&#xa0; </span>'
            f"<span>{text}</span></a></p>")


XHTML = ('<?xml version="1.0" encoding="utf-8"?><html xmlns="http://www.w3.org/1999/xhtml"><body>'
         + _p("ShortT", ("", "Test Act 2020")) + _p("TOC2", ("", "Part 1—Preliminary")) + _p("TOC5", ("", "1 Short title"))
         + _p("LongT", ("", "An Act for testing"))
         + _head(2, "Part", "1", "Preliminary") + _p("Header", ("CharDivNo", "&#xa0;"))
         + _sec("1", "Short title") + _p("subsection", ("", "&#xa0;"), ("", "This Act may be cited as the Test Act 2020."))
         + _head(3, "Division", "2", "Rules") + _sec("2", "Duties")
         + _p("subsection", ("", "(1)"), ("", "&#xa0;"), ("", "A person must&#xa0;not do the thing:"))
         + _p("paragraph", ("", "(a)"), ("", "&#xa0;"), ("", "in the Governor&#x2011;General’s name."))
         + '<table><tr><td><p class="Tabletext"><span>Item</span></p></td><td><p class="Tabletext"><span>Fee</span>'
           "</p></td></tr></table>"
         + _head(2, "Part", "3", "Guide") + _sec("1", "What this Part is about")
         + _p("subsection", ("", "This Part is a guide."))
         + _head(1, "Schedule", "1", "Forms") + _sec("1", "Form of notice") + _p("subsection", ("", "Notice text."))
         + _head(1, "Schedule", "2", "The Code") + _head(2, "Chapter", "1", "Introduction") + _sec("1", "Application")
         + _p("subsection", ("", "This Code applies."))
         + _p("ENotesHeading1", ("", "Endnotes")) + _p("ENoteTableText", ("", "amended by No. 1, 2021"))
         + "</body></html>")


def test_federal_parser_reads_the_opc_styles():
    a = A.Australia()
    meta = {"title_id": "C2020A00001", "name": "Test Act 2020", "year": 2020, "number": 1, "start": "2026-01-01",
            "register_id": "C2026C00001", "principal": True}
    doc = a.parse(XHTML.encode("utf-8"), "C2020A00001", meta)
    rows = {r["citation"]: r for r in a.to_rows(doc)}
    assert list(rows) == ["Test Act 2020 s 1", "Test Act 2020 s 2", "Test Act 2020 pt 3 s 1",
                          "Test Act 2020 sch 1 cl 1", "Test Act 2020 sch 2 s 1"]
    assert rows["Test Act 2020 s 2"]["display_path"] == "Test Act 2020 / Part 1 / Division 2 / Section 2"
    assert rows["Test Act 2020 s 2"]["text"] == ("(1) A person must not do the thing:\n(a) in the Governor-General’s name."
                                                 "\nItem | Fee")
    assert rows["Test Act 2020 s 2"]["chapter_name"] == "Rules"
    assert rows["Test Act 2020 pt 3 s 1"]["eli"].split("/")[-2] == "pt_3_sec_1"      # a number used twice
    assert rows["Test Act 2020 sch 1 cl 1"]["act_id"] == "STATE_AUS_C2020A00001_SCH1_C1"
    assert rows["Test Act 2020 sch 2 s 1"]["display_path"] == "Test Act 2020 / Schedule 2 / Chapter 1 / Section 1"
    assert doc.extra["long_title"] == "An Act for testing" and "amended by" not in json.dumps(list(rows.values()))
    assert rows["Test Act 2020 s 1"]["source_url"] == "https://www.legislation.gov.au/C2020A00001/2026-01-01/2026-01-01/text"


def test_federal_parser_reads_an_epub_and_old_heading_tags():
    old = ('<html><body><p class="TOC5"><span>1 Short title</span></p><p class="LongT"><span>An Act</span></p>'
           '<h5 id="navPoint_1"><a><span>Preamble</span></a></h5><p class="subsection"><span>WHEREAS it is so.</span></p>'
           '<h5 id="navPoint_2"><a><span class="CharSectno">1</span><span>&#xa0; </span><span>Short title</span></a></h5>'
           '<p class="subsection"><span>This Act may be cited as the Old Act 1922.</span></p>'
           '<h2 id="navPoint_3"><a><span>The First Schedule</span><span>&#xa0;</span><span>Agreement</span></a></h2>'
           '<p><span>AGREEMENT made the second day.</span></p>'
           '<p class="NotesSection"><span>Notes to the Old Act 1922</span></p><p><span>Table of Acts</span></p>'
           "</body></html>")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("OEBPS/document_2/document_2.html", '<html><body><p class="ENotesHeading1">Endnotes</p></body></html>')
        z.writestr("OEBPS/document_1/document_1.html", old)
    doc = A.Australia().parse(buf.getvalue(), "C1922A00099", {"name": "Old Act 1922", "year": 1922, "number": 99})
    rows = A.Australia().to_rows(doc)
    assert [r["citation"] for r in rows] == ["Old Act 1922 preamble", "Old Act 1922 s 1", "Old Act 1922 sch 1"]
    assert rows[2]["text"] == "AGREEMENT made the second day." and rows[2]["section_title"] == "Agreement"
    assert doc.url == "https://www.legislation.gov.au/C1922A00099/latest/text" and doc.extra["documents"] == 2


def test_federal_amending_schedule_is_one_row_per_amended_act():
    amend = ('<html><body><p class="TOC5"><span>1 Short title</span></p>' + _sec("1", "Short title")
             + _p("subsection", ("", "This Act may be cited as the Test Amendment Act 2004."))
             + '<p class="ActHead6" id="navPoint_9"><a><span class="CharAmSchNo">Schedule 1</span><span>—</span>'
               '<span class="CharAmSchText">Amendments</span></a></p>'
             + '<p class="ActHead9" id="navPoint_10"><a><span>Social Security Act 1991</span></a></p>'
             + _p("ItemHead", ("", "1 After section 12A")) + _p("Item", ("", "Insert:"))
             + _sec("12AA", "One-off payment") + _p("subsection", ("", "A claim is not required."))
             + "</body></html>")
    doc = A.Australia().parse(amend.encode("utf-8"), "C2004A09999", {"name": "Test Amendment Act 2004", "year": 2004,
                                                                     "number": 9})
    rows = A.Australia().to_rows(doc)
    assert [r["citation"] for r in rows] == ["Test Amendment Act 2004 s 1",
                                             "Test Amendment Act 2004 sch 1, Social Security Act 1991"]
    assert rows[1]["text"] == "1 After section 12A\nInsert:\n12AA One-off payment\nA claim is not required."


def test_federal_list_entry_and_attribution():
    e = A.list_entry({"id": "C1901A00002", "name": "Acts Interpretation Act 1901", "isPrincipal": True, "year": 1901,
                      "number": 2, "makingDate": "1901-07-12T00:00:00"},
                     {"start": "2026-03-28T00:00:00", "retrospectiveStart": "2026-03-28T00:00:00",
                      "registerId": "C2026C00117", "compilationNumber": "39"})
    assert e["start"] == "2026-03-28" and e["register_id"] == "C2026C00117" and e["principal"]
    assert A.list_entry({"id": "C1"}, None)["register_id"] == ""
    assert A.ATTRIBUTION_TEMPLATE.format(date=A._long_date("2026-10-22")).startswith(
        "Sourced from the Federal Register of Legislation at 22 October 2026. For the latest information")
    assert "Office of Parliamentary Counsel" in A.EDIT_NOTE


# ---------------------------------------------------------------------- the states' parsers on inline documents
ENACT = """<!DOCTYPE ACT SYSTEM "act.dtd"[]>
<ACT YEAR="2001" ACTNO="7" TITLE="Test Act 2001" ID="act-2001-007" FIRST.VALID.DATE="2025-07-01"><FRONT><TITLE>Test Act
2001</TITLE><LONGTITLE><TEXT>An Act to test</TEXT></LONGTITLE></FRONT><BODY><PART PARTNO="1" OMITTED="NOOMIT"><HEADING>Preliminary
</HEADING><SECTION SECNO="1" OMITTED="NOOMIT"><HEADNOTE>Short title</HEADNOTE><TEXT>This Act may be cited as the <ACTREF>Test Act
2001</ACTREF>.</TEXT></SECTION><SECTION SECNO="2" OMITTED="NOOMIT"><HEADNOTE>Interpretation</HEADNOTE><HOWAFFECTED><FRAGSPEC>Section
2</FRAGSPEC><TEXT>Amended by No. 1 of 2010</TEXT></HOWAFFECTED><SUBSECTION SUBSECNO="1"><TEXT>In this Act&#160;&#150;</TEXT>
<DEFINITION><DEFINEDTERM>owner</DEFINEDTERM><TEXT> means the owner;</TEXT></DEFINITION></SUBSECTION><SUBSECTION SUBSECNO="2">
<TEXT>A person must not &#150;</TEXT><PARAGRAPH PARANO="a"><TEXT>sell; or</TEXT></PARAGRAPH><PENALTY><TEXT>Fine not exceeding 50
penalty units.</TEXT></PENALTY></SUBSECTION></SECTION><SECTION SECNO="3" OMITTED="YESOMIT"><HEADNOTE>Old</HEADNOTE><TEXT>.</TEXT>
</SECTION></PART></BODY><TAIL><SCHEDULE SCHEDULENO="1" OMITTED="NOOMIT"><HEADING>Savings</HEADING><S.CLAUSE CLAUSENO="1">
<HEADNOTE>Continuation</HEADNOTE><TEXT>Things continue.</TEXT></S.CLAUSE></SCHEDULE></TAIL></ACT>"""


def test_tasmania_reads_enact_xml():
    a = S.Tasmania()
    doc = a.parse(ENACT.encode("utf-8"), "act-2001-007", {"native_id": "act-2001-007", "name": "Test Act 2001",
                                                          "year": "2001", "number": "7", "start": "2025-07-01"})
    rows = a.to_rows(doc)
    live = [r for r in rows if r["act_status"] == "in_force"]
    assert [r["citation"] for r in live] == ["Test Act 2001 s 1", "Test Act 2001 s 2", "Test Act 2001 sch 1 cl 1"]
    s2 = live[1]
    assert s2["text"] == ("(1) In this Act –\nowner means the owner;\n(2) A person must not –\n(a) sell; or\n"
                          "Penalty: Fine not exceeding 50 penalty units.")
    assert s2["display_path"] == "Test Act 2001 / Part 1 / Section 2" and s2["chapter_name"] == "Preliminary"
    assert s2["act_id"] == "STATE_AUS-TAS_ACT2001007_P1_S2"
    assert s2["source_url"] == "https://www.legislation.tas.gov.au/view/whole/html/inforce/2025-07-01/act-2001-007"
    assert s2["eli"].startswith(f"{base.ELI_BASE}/au-tas/act/2001/7/sec_2/en@")
    assert any(r["act_status"] == "repealed" for r in rows)                  # OMITTED: not indexed (statutes._prepare)


SAOPC = """<?xml version="1.0" encoding="us-ascii"?><exdoc title="Test Act&#x00A0;2010" year="2010" number="5"
enact.or.made.date="2010-05-01" first.valid.date="2024-07-01" doc.class="act"><metadata class="metadata"><metacontent
class="principal">true</metacontent><metadata class="versioninfo"><metadata class="inforce"><metacontent class="status">all.in.force
</metacontent></metadata></metadata></metadata><content type="front"><tier type="longtitle"><block><txt>An Act to test.</txt>
</block></tier></content><content type="body"><level type="part"><head><no><b>Part&#x00A0;1</b></no><heading><b>Preliminary</b>
</heading></head><level type="clause"><head><no><b>3</b></no><heading><b>Duty</b></heading></head><tier type="subclause"><head>
<no>(1)</no></head><block><txt>An owner must&#x2014;</txt><list><li><no>(a)</no><block><txt>pay; and</txt></block></li></list>
</block><tier type="penalty"><head><heading><b>Maximum penalty:</b></heading></head><block><txt>$10&#x00A0;000.</txt></block>
</tier></tier></level></level></content><content type="schedules"><level type="schedule"><head><no><b>Schedule&#x00A0;1</b></no>
<heading><b>The Law</b></heading></head><level type="indoc"><content type="body"><level type="chapter"><head><no><b>Chapter 1</b>
</no><heading><b>Start</b></heading></head><level type="clause"><head><no><b>1</b></no><heading><b>Citation</b></heading></head>
<block><txt>This Law may be cited as the Test Law.</txt></block></level></level></content></level></level></content>
<content type="editorial"><level type="leghistory"><head><heading><b>Legislative history</b></heading></head></level></content>
</exdoc>"""


def test_south_australia_reads_saopc_xml_and_filters_by_the_title_index(tmp_path, monkeypatch):
    a = S.SouthAustralia()
    doc = a.parse(SAOPC.encode("ascii"), "2010.5", {"native_id": "2010.5", "version": "2026-10-09"})
    rows = a.to_rows(doc)
    assert [r["citation"] for r in rows] == ["Test Act 2010 s 3", "Test Act 2010 sch 1 s 1"]
    assert rows[0]["text"] == "(1) An owner must—\n(a) pay; and\nMaximum penalty: $10 000."
    assert rows[1]["display_path"] == "Test Act 2010 / Schedule 1 / Chapter 1 / Section 1"
    assert doc.version_date == "2024-07-01" and doc.extra["inforce"] == "all.in.force"
    monkeypatch.setattr(S, "raw_dir", lambda _a: tmp_path)
    (tmp_path / "titleindex-2026-10-09.json").write_text(json.dumps({"items": [
        {"section": "South Australian Acts", "title": "Aged and Infirm Persons' Property Act 1940", "version": "2025-01-01"},
        {"section": "South Australian Acts", "title": "Biosecurity Act 2025", "version": "2025-02-13",
         "note": "uncommenced"},
        {"section": "South Australian Subordinate Legislation", "title": "Test Regulations 2020", "version": "2020-01-01"}]}))
    index = a.title_index()
    assert list(index) == [S._norm_title("Aged and Infirm Persons Property Act 1940")]     # folder names drop "'"


WA_HTML = """<html><body><p class="TOC2-P"><span class="TOC2-H">Part 1 — Preliminary</span></p>
<p class="NameofActReg-P"><span>Test Act 2004</span></p><p class="LongTitle-P"><span>An Act to test.</span></p>
<p class="Heading2-P"><span class="Heading2-H"><span class="CharPartNo-H">Part 1</span> — <span class="CharPartText-H">Preliminary</span>
</span></p><p class="Heading5-P"><span class="Heading5-H"><span class="CharSectno-H">1</span>.Short title</span></p>
<p class="Subsection-P"><span class="Subsection-H">This Act may be cited as the <span>Test Act 2004 </span><span
style="position: relative; top: -0.4em;"><span>1</span></span>.</span></p>
<p class="Heading5-P"><span class="Heading5-H"><span class="CharSectno-H">2</span>.Terms used</span></p>
<p class="Subsection-P"><span>(1)In this Act —</span></p><p class="Indenta-P"><span>(a)a thing; and</span></p>
<p class="Footnotesection-P"><span>[Section 2 amended: No. 1 of 2010 s. 3.]</span></p>
<p class="Ednotesection-P"><span>[3.Deleted: No. 1 of 2010 s. 4.]</span></p>
<p class="yScheduleHeading-P"><span>Schedule 1 — Forms</span></p><p class="yShoulderClause-P"><span>[s. 2]</span></p>
<p class="yHeading5-P"><span><span class="CharSectno-H">1</span>.Form</span></p><p class="ySubsection-P"><span>A form.</span></p>
<p class="nHeading2-P"><span>Notes</span></p><p class="nTable-P"><span>Compilation table</span></p></body></html>"""


def test_western_australia_reads_the_word_html():
    a = S.WesternAustralia()
    law = ("<h1>Test Act 2004</h1><th>Act No:</th><td>037 of 2004</td><tr><td>Test Act 2004</td><td>1 Jul 2016</td>"
           "<td class='current'>Current</td><td>01-c0-00</td>")
    env = json.dumps({"law": law, "doc": WA_HTML, "mrdoc": "123"}).encode("utf-8")
    doc = a.parse(env, "a1", {"native_id": "a1"})
    rows = a.to_rows(doc)
    assert [r["citation"] for r in rows] == ["Test Act 2004 s 1", "Test Act 2004 s 2", "Test Act 2004 sch 1 cl 1"]
    assert rows[0]["text"] == "This Act may be cited as the Test Act 2004."
    assert rows[1]["text"] == "(1) In this Act —\n(a) a thing; and"
    assert doc.version_date == "2016-07-01" and doc.number == "No. 37 of 2004" and doc.extra["version_suffix"] == "01-c0-00"
    assert rows[0]["eli"].startswith(f"{base.ELI_BASE}/au-wa/act/2004/37/sec_1/en@2016-07-01")


# ---------------------------------------------------------------------- Chile's interim mode (no network)
LEYCHILE = """<?xml version="1.0" encoding="utf-8"?><Norma xmlns="http://www.leychile.cl/esquemas" normaId="{id}"
fechaVersion="2020-01-01" derogado="no derogado"><Identificador fechaPromulgacion="2019-12-01" fechaPublicacion="2019-12-05">
<TiposNumeros><TipoNumero><Tipo>Ley</Tipo><Numero>2100{id}</Numero></TipoNumero></TiposNumeros></Identificador><Metadatos>
<TituloNorma>PRUEBA</TituloNorma></Metadatos><EstructurasFuncionales><EstructuraFuncional idParte="1" tipoParte="Artículo"
fechaVersion="2020-01-01" derogado="no derogado"><Texto>Artículo 1.- Esta ley rige.</Texto></EstructuraFuncional>
</EstructurasFuncionales></Norma>"""


def test_chile_interim_mode_caps_fetches_per_question_and_per_day(tmp_path, monkeypatch):
    calls = []

    class Resp:
        def __init__(self, body):
            self.content = body.encode("utf-8")

    def fake_get(self, url, accept="*/*", timeout=60, ua=None):
        calls.append(url)
        return Resp(LEYCHILE.format(id=url.rsplit("=", 1)[1]))
    monkeypatch.setattr(CH.Chile, "get", fake_get)
    c = CH.Chile()
    docs = c.on_demand(["1", "2", "3", "4", "5"], cache=tmp_path)
    assert len(calls) == CH.PER_QUESTION == 3 and [d.native_id for d in docs] == ["1", "2", "3"]
    assert json.loads((tmp_path / "quota.json").read_text())["used"] == 3
    again = c.on_demand(["1", "2", "3"], cache=tmp_path)                # cached: no new request
    assert len(calls) == 3 and len(again) == 3
    assert c.on_demand(["9"], cache=tmp_path, per_day=3) == [] and len(calls) == 3      # the day's budget is spent
    rows = c.rows_on_demand(["1"], cache=tmp_path)
    assert rows[0]["citation"] == "Ley 21.001, art. 1" and rows[0]["act_id"].startswith("STATE_CHL_")
    assert rows[0]["attribution"].startswith("Texto: Ley Chile, Biblioteca del Congreso Nacional de Chile, Ley 21.001")
    CH._trim(tmp_path, 2)
    assert len(list(tmp_path.glob("*.xml"))) == 2


# ---------------------------------------------------------------------- the corpus interface and the index
def test_index_builds_from_the_new_fixtures(tmp_index):
    for key in MINE:
        doc = C.load_document(key)
        out = I.build(key, log=lambda *_: None, corpus=C.CORPUS)
        assert out["sections"] == len(C.rows_for(key, doc)) and I.ready(key, corpus=C.CORPUS)
    hit = I.lookup("aus", "Electronic Transactions Act 1999 s 1", with_text=True, corpus=C.CORPUS)
    assert hit and hit[0]["text"] == "This Act may be cited as the Electronic Transactions Act 1999."
    by_eli = I.lookup("aus", f"{base.ELI_BASE}/au/act/1999/162/sec_1", corpus=C.CORPUS)
    assert by_eli and by_eli[0]["citation"] == "Electronic Transactions Act 1999 s 1"
    found = I.search("aus", I.match([["electronic communication"]]), corpus=C.CORPUS)
    assert found and all(r["country"] == "aus" for r in found)
    assert I.lookup("aus-tas", "Natural Resource Management Act 2002 s 1", corpus=C.CORPUS)
    assert I.lookup("rou", "Legea nr. 190/2020, art. 1", corpus=C.CORPUS)


def test_rows_pulled_one_file_per_law_are_streamed(tmp_index):
    doc = C.load_document("aus")
    rows = C.rows_for("aus", doc)
    d = tmp_index / "raw" / "countries" / "aus" / "rows"
    d.mkdir(parents=True)
    with open(d / "C2004A00553.jsonl", "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    assert C.path_for("aus") == d and C.bulk("aus") and C.have("aus")
    streamed = list(C.iter_rows("aus", log=lambda *_: None))
    assert len(streamed) == len(rows) and streamed[0].citation == rows[0]["citation"]
    assert C._LAWS["aus"][0]["law_id"] == "C2004A00553" and C._LAWS["aus"][0]["rows"] == len(rows)
    assert len(C.load("aus")) == len(rows)
    out = I.build("aus", log=lambda *_: None, corpus=C.CORPUS)
    assert out["sections"] == len(rows)
    laws = C.laws("aus", C.CORPUS)
    assert [x["law_id"] for x in laws] == ["C2004A00553"] and laws[0]["title"] == "Electronic Transactions Act 1999"
