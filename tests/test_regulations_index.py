"""The regulations index (lexflow/corpus/regulations.py): the statute index's tables at
data/index/regulations_<state>.sqlite with a kind column, rows in force only, the short-citation lookup, the Setup
card and the CLI, all on a small synthetic regulations file.  The statute index must not change.

The rows below are synthetic test rows in the shape of open-us-law's regulations files.  Their wording is abridged
from state regulations (13VAC5-63-80, 12-A DCMR 105.2) and is not a copy of any section.
"""
import sqlite3

import pandas as pd
import pytest

from lexflow import cli
from lexflow.ask import index as I
from lexflow.corpus import regulations as R
from lexflow.municipal import statutes
from lexflow.pipeline import steps

VA_URL = "https://law.lis.virginia.gov/admincode/title13/agency5/chapter63/section{}/"
SHED = ("2. One story detached structures used as tool and storage sheds, playhouses, or similar uses, provided the "
        "building area does not exceed 256 square feet.")
MINOR = ("13. Construction work deemed by the building official to be minor and ordinary and that does not adversely "
         "affect public health or general safety.")
ROOF = "14.6. Replacement of 256 square feet or less of roof decking in Group R-3, R-4, or R-5."
PERMIT_TEXT = ("A. Section 108.1 When applications are required. Application for a permit shall be made to the "
               "building official and a permit shall be obtained prior to the commencement of any of the following "
               "activities.\n"
               "B. Section 108.2 Exemptions from application for permit. Application for a permit and any related "
               f"inspections shall not be required for the following:\n{SHED}\n{MINOR}\n{ROOF}")
STATUTE_COLUMNS = ["id", "ref", "citation", "title", "chapter", "path", "url", "words", "head", "section_number",
                   "norm_section", "norm_cite", "act_id", "original_title", "effective_from", "effective_until"]


def _row(state, short, citation, number, title, text, status="in_force", path="", url=None, chapter=""):
    return dict(act_id=f"STATE_{state.upper()}_{short}", citation=citation, citation_short=short, section_number=number,
                section_title=title, chapter_name=chapter, display_path=path, act_status=status, text=text,
                source_url=url or f"https://example.test/{state}/{number}", word_count=len(text.split()),
                last_amended_year=2024, document_type="regulation")


def _va_path(n):
    return f"Virginia Administrative Code / Title 13 Housing / Agency 5 / Chapter 63 / 13VAC5-63-{n}"


VA = [
    _row("va", "13VAC5-63-70", "13 Va. Admin. Code § 5-63-70", "13VAC5-63-70", "13VAC5-63-70. Section 107 Fees",
         "The local governing body shall establish a fee schedule for permits.", path=_va_path(70),
         url=VA_URL.format(70)),
    _row("va", "13VAC5-63-80", "13 Va. Admin. Code § 5-63-80", "13VAC5-63-80",
         "13VAC5-63-80. Section 108 Application for permit", PERMIT_TEXT, path=_va_path(80), url=VA_URL.format(80)),
    # an older version of the same section, and a repealed stub: neither is indexed
    _row("va", "13VAC5-63-80", "13 Va. Admin. Code § 5-63-80", "13VAC5-63-80", "13VAC5-63-80. Old permit rules",
         "Garden sheds and decks under the superseded rules.", status="superseded", path=_va_path(80)),
    _row("va", "13VAC5-63-90", "13 Va. Admin. Code § 5-63-90", "13VAC5-63-90", "13VAC5-63-90. Repealed",
         "Repealed. Sheds and decks.", status="repealed", path=_va_path(90)),
    # a heading that is the citation alone gets the code's name and the first sentence instead
    _row("va", "13VAC5-63-100", "13 Va. Admin. Code § 5-63-100", "13VAC5-63-100", "13VAC5-63-100",
         "Construction documents shall be submitted with the application. More follows.", path=_va_path(100)),
    # a row the file gives no status (as a few real ones are): kept, as for the statutes
    _row("va", "9VAC25-720-60", "9 Va. Admin. Code § 25-720-60", "9VAC25-720-60", None,
         "Total maximum daily loads for the river basin.", status=None),
]
DC = [  # DC numbers sections within each title: two rows share the number 105
    _row("dc", "12-A DCMR 105", "D.C. Mun. Regs. tit. 12-A, § 105", "105", "105. PERMITS",
         "105.2 Work exempt from permit. 8. A single garden storage shed that does not exceed 50 square feet."),
    _row("dc", "11-B DCMR 105", "D.C. Mun. Regs. tit. 11-B, § 105", "105", "105. SETBACKS",
         "A rear yard shall be provided for each building."),
]


@pytest.fixture()
def regs(con, monkeypatch, tmp_path):
    """Synthetic regulations files for VA and DC in a temporary open-us-law folder (the real files are never read),
    with this module's caches emptied.  Returns a function that writes a state's file."""
    raw = tmp_path / "open-us-law"
    raw.mkdir()
    monkeypatch.setattr(statutes, "DIR", raw)
    monkeypatch.setattr(I, "_STAMPS", {})
    monkeypatch.setattr(I, "_READY", {})

    def write(state, rows):
        pd.DataFrame(rows).to_parquet(raw / f"us_{state}_regulations.parquet", index=False)
    write("va", VA)
    write("dc", DC)
    write("federal", DC)                        # the federal file is not a state's and is never indexed
    return write


def _columns(con, table):
    return [r[1] for r in con.execute(f"PRAGMA table_info({table})")]


def test_the_index_has_the_statute_tables_and_a_kind_column(regs):
    assert sorted(R.states()) == ["dc", "va"]                           # never the federal file
    out = R.build_all(log=lambda *_: None)
    assert set(out) == {"va", "dc"} and out["va"]["sections"] == 4 and out["dc"]["sections"] == 2
    assert I.path("va", "regulations").name == "regulations_va.sqlite" and I.ready("va", corpus="regulations")
    con = sqlite3.connect(str(I.path("va", "regulations")))
    try:
        assert _columns(con, "sec") == STATUTE_COLUMNS + list(R.EXTRA)
        assert _columns(con, "body") == ["id", "text"]
        assert _columns(con, "fts") == ["title", "chapter", "body"]
        meta = dict(con.execute("SELECT key, value FROM meta"))
        assert meta["sections"] == "4" and meta["corpus"] == "regulations"
        assert meta["stamp"].startswith(f"{I.VERSION}-regulations{R.VERSION}:")
        assert {r[0] for r in con.execute("SELECT DISTINCT kind FROM sec")} == {"regulation"}
    finally:
        con.close()


def test_only_rows_in_force_are_searchable(regs):
    R.build_all(["va"], log=lambda *_: None)
    refs = [r["ref"] for r in I.search("va", I.match([["shed", "sheds"]]), corpus="regulations")]
    assert refs == ["13VAC5-63-80"]                                     # not the superseded or repealed rows
    assert not I.search("va", I.match([["superseded"]]), corpus="regulations")
    assert I.lookup("va", "13VAC5-63-90", corpus="regulations") == []
    assert I.by_ref("va", "9VAC25-720-60", corpus="regulations")        # no status in the file: kept


def test_a_search_for_sheds_and_decks_finds_the_permit_exemptions(regs):
    R.build_all(["va"], log=lambda *_: None)
    hits = I.search("va", I.match([["shed", "sheds"], ["deck", "decks"]], "and"), corpus="regulations")
    top = hits[0]
    assert top["ref"] == "13VAC5-63-80" and top["kind"] == "regulation" and top["url"] == VA_URL.format(80)
    assert top["title"] == "Section 108 Application for permit"         # the citation is not repeated
    # the text comes back exactly as the file has it, so the items can be quoted word for word
    row = I.lookup("va", "13VAC5-63-80", with_text=True, corpus="regulations")[0]
    assert row["text"] == PERMIT_TEXT and SHED in row["text"] and MINOR in row["text"]
    assert I.text_of("va", top["id"], corpus="regulations") == PERMIT_TEXT
    # the statute search is untouched: no statute index exists here
    assert not I.ready("va")


def test_lookup_by_short_citation_full_citation_and_number(regs):
    R.build_all(log=lambda *_: None)
    assert [r["ref"] for r in I.lookup("va", "13VAC5-63-80", corpus="regulations")] == ["13VAC5-63-80"]
    assert I.by_ref("va", "13 Va. Admin. Code § 5-63-80", corpus="regulations")["ref"] == "13VAC5-63-80"
    # DC: the short citation picks one title's section 105; the bare number names both
    one = I.lookup("dc", "12-A DCMR 105", corpus="regulations")
    assert [r["citation"] for r in one] == ["D.C. Mun. Regs. tit. 12-A, § 105"] and one[0]["ref"] == "12-A DCMR 105"
    assert {r["ref"] for r in I.lookup("dc", "105", corpus="regulations")} == {"12-A DCMR 105", "11-B DCMR 105"}
    assert I.by_ref("dc", "D.C. Mun. Regs. tit. 11-B, § 105", corpus="regulations")["title"] == "SETBACKS"
    row = I.by_ref("va", "13VAC5-63-80", corpus="regulations")
    assert I.by_id("va", row["id"], corpus="regulations")["citation_short"] == "13VAC5-63-80"
    assert [r["ref"] for r in I.neighbours("va", row["id"], span=1, corpus="regulations")] == \
        ["13VAC5-63-70", "13VAC5-63-80", "13VAC5-63-100"]
    unit = "Virginia Administrative Code / Title 13 Housing / Agency 5 / Chapter 63"
    assert len(I.in_units("va", [unit], corpus="regulations")) == 3


def test_headings_drop_the_citation_and_numbers():
    t = R._title
    assert t("13VAC5-63-80. Section 108 Application for permit", ("13VAC5-63-80",)) == \
        "Section 108 Application for permit"
    assert t("ARSD 02:01:08:01. 2:01:08:01. Reserve officer certification", ("ARSD 02:01:08:01",)) == \
        "Reserve officer certification"
    assert t("Section 1305.110  Horse Ambulance", ()) == "Horse Ambulance"
    assert t("Ch. 1, § 4. Filing Procedures", ()) == "Filing Procedures"
    assert t("Rule 109:1-1-08. Notice of revocation", ("109:1-1-08",)) == "Notice of revocation"
    assert t("1412. AC-4 SHARED STEWARDSHIP", ("10-A DCMR 1412", "1412")) == "AC-4 SHARED STEWARDSHIP"
    # words with digits are headings, and a section numbered with words is not a citation
    assert t("WAC 246-924-011. COVID-19", ("WAC 246-924-011",)) == "COVID-19"
    assert t("Section 211.4770  PM-10", ()) == "PM-10"
    assert t("Appendix C", ("APPENDIX C",)) == "Appendix C"
    assert t("Section 150", ()) == "" and t("-", ()) == ""
    # an empty heading becomes the code's name and the first sentence, as for the statutes
    df = R.prepare(pd.DataFrame(VA))
    row = df[df["citation_short"] == "13VAC5-63-100"].iloc[0]
    assert I._heading(row.section_title, row.citation, row.chapter_name, row.text) == \
        "13 Va. Admin. Code: Construction documents shall be submitted with the application."


def test_ready_follows_the_file_and_build_all_skips_current_indexes(regs):
    first = R.build_all(["va"], log=lambda *_: None)
    assert isinstance(first["va"], dict) and R.ready("va")
    assert R.build_all(["va"], log=lambda *_: None) == {"va": "ready"}
    assert R.build_all(["tx"], log=lambda *_: None) == {"tx": "no file"}
    assert R.build_all([], log=lambda *_: None) == {}                    # nothing named builds nothing
    regs("va", VA + [_row("va", "13VAC5-63-110", "13 Va. Admin. Code § 5-63-110", "13VAC5-63-110",
                          "13VAC5-63-110. Section 110 Permits", "The building official shall act on an application.")])
    I._STAMPS.clear()                                                   # a minute later
    assert not R.ready("va")
    assert R.build_all(["va"], log=lambda *_: None)["va"]["sections"] == 5 and R.ready("va")


def test_the_statute_index_is_unchanged(regs, va_statutes):
    assert I.ensure("va") and R.build_all(["va"], log=lambda *_: None)["va"]["sections"] == 4
    assert I.path("va").name == "statutes_va.sqlite" and I.ready("va") and I.ready("va", corpus="regulations")
    assert I._stamp("va") == f"{I.VERSION}:no-file"                     # the statute stamp keeps its form
    con = I.connect("va")
    try:
        assert _columns(con, "sec") == STATUTE_COLUMNS                  # no kind column in the statute index
        assert "corpus" not in dict(con.execute("SELECT key, value FROM meta").fetchall())
    finally:
        con.close()
    statute = I.search("va", I.match([["public records"], ["request", "inspection"]], "and"))
    assert statute and statute[0]["ref"] == "2.2-3704" and "kind" not in statute[0]
    assert not I.search("va", I.match([["public records"], ["request", "inspection"]], "and"), corpus="regulations")
    assert I.by_ref("va", "2.2-3704")["ref"] == "2.2-3704" and I.by_ref("va", "2.2-3704", corpus="regulations") is None


def test_the_setup_card_and_the_cli(regs, con):
    card = steps.STEPS["regulations"]
    ids = list(steps.STEPS)
    assert ids.index("regulations") == ids.index("index") + 1 and card.level == "optional"
    assert card.needs == ["statutes"] and card.params == ["states", "force"]
    assert [c["name"] for c in card.credits] == ["Open US Law", "SQLite FTS5"]
    assert "Commercial use needs a licence from Vaquill AI" in card.credits[0]["note"]
    st = steps.st_regulations(con)
    assert st["status"] == "todo" and (st["done"], st["total"]) == (0, 2)
    out = steps.run_regulations(con, {"states": "dc"}, lambda *_: None, lambda p: None)
    assert out["built"] == 1 and out["sections"] == 2
    assert steps.st_regulations(con)["status"] == "partial"
    assert cli.main(["index", "--regulations", "--states", "va"]) == 0
    assert steps.st_regulations(con)["status"] == "done"
    assert cli.main(["index", "--regulations", "--states", "tx"]) == 1   # named, but no file on disk
    for p in statutes.DIR.glob("us_*_regulations.parquet"):
        p.unlink()
    assert steps.st_regulations(con)["status"] == "optional"
