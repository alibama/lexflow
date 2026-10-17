"""lexflow.law.headings: unit keys as schema mints them, the corpus names, the numbering stripped, and the
extractors on saved official pages (fixtures/law/headings_samples/)."""
import json
from pathlib import Path

import pytest

from lexflow.law import headings as H
from lexflow.publish import schema as SC

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "fixtures" / "law" / "headings_samples"


# ---- keys

def _row(act_id, path, url="https://example.test/x", citation="X § 1"):
    return {"act_id": act_id, "path": path, "url": url, "citation": citation}


def test_units_of_matches_schema_unit_keys():
    r = _row("STATE_VA_T2.2_SII_PB_C37_S2.2-3704",
             "Virginia Code / Title 2.2 / Subtitle II / Part B / Chapter 37 / Section 2.2-3704")
    units = H.units_of("va", r)
    assert [u.key for u in units] == [
        SC.key_for("unit", "va", SC.unit_prefix(r["act_id"], d)) for d in (1, 2, 3, 4)]
    assert units[-1].key == "lexflow:unit:va:t2.2-sii-pb-c37"
    assert [u.level for u in units] == ["title", "subtitle", "part", "chapter"]
    assert [u.num for u in units] == ["2.2", "II", "B", "37"]
    assert units[-1].nums() == {"title": "2.2", "subtitle": "II", "part": "B", "chapter": "37"}
    assert units[-1].elems == ["Virginia Code", "Title 2.2", "Subtitle II", "Part B", "Chapter 37"]


def test_units_of_skips_code_tokens_and_keeps_their_prefix():
    r = _row("STATE_CA_Cgov_T1_D7_C3.5_S7922.535",
             "California Code / Code gov / Title 1 / Division 7 / Chapter 3.5 / Section 7922.535")
    keys = [u.key for u in H.units_of("ca", r)]
    assert keys == ["lexflow:unit:ca:cgov-t1", "lexflow:unit:ca:cgov-t1-d7", "lexflow:unit:ca:cgov-t1-d7-c3.5"]
    assert H.units_of("ca", r)[-1].code() == "gov"
    r = _row("STATE_NY_APBO_A6_S87", "New York Code / Act PBO / Article 6 / Section 87")
    assert [u.key for u in H.units_of("ny", r)] == ["lexflow:unit:ny:apbo-a6"]


def test_units_of_when_path_and_act_id_disagree():
    # Utah: "Chapter 48-3a" is no act_id token; the units are named from the tokens, as the graph names them
    r = _row("STATE_UT_T48_S48_3a_1103", "Utah Code / Title 48 / Chapter 48-3a / § 48-3a-1103")
    units = H.units_of("ut", r)
    assert [u.key for u in units] == ["lexflow:unit:ut:t48"]
    assert units[0].elem == "Title 48" and units[0].level == "title"
    # Minnesota's part token with an underscore and Puerto Rico's alphabetic act
    r = _row("STATE_MN_P13_13C_C13_S13.03", "MN Code / Part 13_13C / Chapter 13 / Section 13.03")
    assert [u.key for u in H.units_of("mn", r)] == ["lexflow:unit:mn:p13_13c", "lexflow:unit:mn:p13_13c-c13"]
    r = _row("STATE_PR_TRANSPARENCIA_ART1", "Ley de Transparencia (2019) / Ley de Transparencia / Art. 1")
    units = H.units_of("pr", r)
    assert [u.key for u in units] == ["lexflow:unit:pr:transparencia"] and units[0].level == "act"


# ---- the numbering stripped

@pytest.mark.parametrize("name, level, num, elem, want", [
    ("Chapter 37. Virginia Freedom of Information Act", "chapter", "37", "Chapter 37", "Virginia Freedom of Information Act"),
    ("CHAPTER 119 PUBLIC RECORDS", "chapter", "119", "Chapter 119", "PUBLIC RECORDS"),
    ("Chapter 37.1 Something Else", "chapter", "37", "Chapter 37", None),          # 37 is not 37.1
    ("Title 11", "title", "11", "Title 11", None),                                 # Ohio: the level and number only
    ("Title 29 - Partnership", "title", "29", "Title 29", "Partnership"),           # a name that starts with a level word
    ("TITLE IV EXECUTIVE BRANCH Ch.14-24", "title", "IV", "Title IV", "EXECUTIVE BRANCH"),
    ("Title 1 | State Government", "title", "1", "Title 1", "State Government"),
    ("Title 1 - General Provisions Read Title", "title", "1", "Title 1", "General Provisions"),
    ("Title 15 - The Official Website of the Pennsylvania General Assembly", "title", "15", "Title 15", None),
    ("Chapter 1 – Idaho State Legislature", "chapter", "1", "Chapter 1", None),
    ("Chapter 2 - Legislature", "chapter", "2", "Chapter 2", "Legislature"),
    ("Article 2 Searches and Copies", "article", "2", "Article 2", "Searches and Copies"),
    ("Chapter 2 PRINTING AND PUBLICATION Sec: 39-201-39-221", "chapter", "2", "Chapter 2", "PRINTING AND PUBLICATION"),
    ("Ch. 13 MS-Word", "chapter", "13", "Chapter 13", None),
    ("Chapter 1 PUBLIC RECORDS Sec: 39-101-39-178", "chapter", "1", "Chapter 1", "PUBLIC RECORDS"),
    ("Chapter 610 Governmental Bodies and Records ✹ ⚿", "chapter", "610", "Chapter 610", "Governmental Bodies and Records"),
    ("TITLE X PUBLIC OFFICERS, EMPLOYEES, AND RECORDS", "title", "X", "Title X", "PUBLIC OFFICERS, EMPLOYEES, AND RECORDS"),
    ("Title 42 RCW PUBLIC OFFICERS AND AGENCIES", "title", "42", "Title 42", "PUBLIC OFFICERS AND AGENCIES"),
    ("Chapter 42.56 RCW", "chapter", "42.56", "Chapter 42.56", None),
    ("CHAPTER 3.5. Inspection of Public Records [7920.000 - 7931.000]", "chapter", "3.5", "Chapter 3.5", "Inspection of Public Records"),
    ("Article 6 - (84 - 90) FREEDOM OF INFORMATION LAW", "article", "6", "Article 6", "FREEDOM OF INFORMATION LAW"),
    ("PART I GENERAL PROVISIONS (ss. 465.001-465.0244)", "part", "I", "Part I", "GENERAL PROVISIONS"),
    ("Chapter 16C. Retail Natural Gas Supplier Licensing and Consumer Protection.", "chapter", "16C", "Chapter 16C",
     "Retail Natural Gas Supplier Licensing and Consumer Protection."),
    ("Business Organizations. [Enacted title]", "title", "29", "Title 29", "Business Organizations."),
    ("Chapter 75.—STATE DEPARTMENTS; PUBLIC OFFICERS AND EMPLOYEES", "chapter", "75", "Chapter 75",
     "STATE DEPARTMENTS; PUBLIC OFFICERS AND EMPLOYEES"),
    ("Title 1 : General Provisions", "title", "1", "Title 1", "General Provisions"),
    ("Chapter 10-20 Municipal Land Use", "chapter", "10-20", "Chapter 10-20", "Municipal Land Use"),
    ("Chapter 37 § 2.2-3700", "chapter", "37", "Chapter 37", None),               # a section line, not a name
    ("Ley de Transparencia y Acceso a la Información Pública (2019)", "act", "TRANSPARENCIA", "Ley de Transparencia",
     "Ley de Transparencia y Acceso a la Información Pública (2019)"),
])
def test_strip_prefix(name, level, num, elem, want):
    assert H.strip_prefix(name, level, num, elem) == want


def test_strip_prefix_with_the_parents_number_and_leading_zeros():
    assert H.strip_prefix("Chapter 18.100 RCW", "chapter", "100", "Chapter 100", parent="18") is None
    assert H.strip_prefix("Chapter 18.100 RCW PUBLIC RECORDS", "chapter", "100", "Chapter 100", parent="18") == "PUBLIC RECORDS"
    assert H.strip_prefix("CHAPTER 1-27 PUBLIC RECORDS AND FILES", "chapter", "27", "Chapter 27", parent="1") == "PUBLIC RECORDS AND FILES"
    assert H.strip_prefix("Chapter 005 : Common Law; General Rights", "chapter", "5", "Chapter 5") == "Common Law; General Rights"
    assert H.strip_prefix("EXAMINATION OF PUBLIC RECORDS (OPEN RECORDS) Sections PDF PDF RTF XML", "chapter", "22", "Chapter 22")         == "EXAMINATION OF PUBLIC RECORDS (OPEN RECORDS)"


def test_strip_prefix_drops_the_code_name_and_cuts_long_names():
    assert H.strip_prefix("Utah Code Title 38: Liens", "title", "38", "Title 38", "Utah Code") == "Liens"
    long = "Chapter 1. " + "word " * 100
    out = H.strip_prefix(long, "chapter", "1", "Chapter 1")
    assert out and len(out) <= H.NAME_MAX and out.startswith("word word")


# ---- the corpus

def test_from_corpus_on_a_small_parquet(tmp_path, monkeypatch):
    pq = pytest.importorskip("pyarrow.parquet")
    import pyarrow as pa
    rows = [
        # DC: breadcrumb names, the chapter's repeating its numbering; the title's editorial note
        dict(act_id="STATE_DC_T2_C5_S2-531", display_path="DC Code / Title 2 / Chapter 5 / § 2-531",
             title_name="DC Code", chapter_name="Chapter 5. Administrative Procedure.",
             breadcrumb=json.dumps([{"type": "title", "num": "2", "label": "Title 2", "name": "Government Administration. [Enacted title]"},
                                    {"type": "chapter", "num": "5", "label": "Chapter 5", "name": "Chapter 5. Administrative Procedure."},
                                    {"type": "section", "num": "2-531", "label": "§ 2-531", "name": ""}])),
        dict(act_id="STATE_DC_T2_C5_S2-532", display_path="DC Code / Title 2 / Chapter 5 / § 2-532",
             title_name="DC Code", chapter_name="Chapter 5. Administrative Procedure.",
             breadcrumb=json.dumps([{"type": "title", "num": "2", "label": "Title 2", "name": "Government Administration. [Enacted title]"},
                                    {"type": "chapter", "num": "5", "label": "Chapter 5", "name": "Chapter 5. Administrative Procedure."},
                                    {"type": "section", "num": "2-532", "label": "§ 2-532", "name": ""}])),
        # Ohio: "Title 11" is not a name; the chapter_name column is
        dict(act_id="STATE_OH_T11_C1101_S1101.01", display_path="Ohio Revised Code / Title 11 / Chapter 1101 / § 1101.01",
             title_name="Title 11", chapter_name="Banks - General Provisions",
             breadcrumb=json.dumps([{"type": "title", "num": "11", "label": "Title 11", "name": "Title 11"},
                                    {"type": "chapter", "num": "1101", "label": "Chapter 1101", "name": "Banks - General Provisions"},
                                    {"type": "section", "num": "1101.01", "label": "§ 1101.01", "name": ""}])),
        # Utah: the chapter is no act_id token; the title comes from title_name with the code's prefix stripped
        dict(act_id="STATE_UT_T63G_S63G_2_201", display_path="Utah Code / Title 63G / Chapter 63G-2 / § 63G-2-201",
             title_name="Utah Code Title 63G: General Government", chapter_name="Government Records Access and Management Act",
             breadcrumb=json.dumps([{"type": "title", "num": "63G", "label": "Title 63G", "name": "General Government"},
                                    {"type": "chapter", "num": "63G-2", "label": "Chapter 63G-2", "name": "Government Records Access and Management Act"},
                                    {"type": "section", "num": "63G-2-201", "label": "§ 63G-2-201", "name": ""}])),
        # California: a named display_path element, no breadcrumb names, the code token no unit
        dict(act_id="STATE_CA_Cbpc_D2_C10.5_S4600", display_path="California Code / Code bpc / Division 2 - HEALING ARTS / Chapter 10.5 - Massage Therapy Act / Section 4600",
             title_name="California Code", chapter_name="Massage Therapy Act",
             breadcrumb=json.dumps([{"type": "code", "num": "bpc", "label": "Code bpc", "name": ""},
                                    {"type": "division", "num": "2", "label": "Division 2", "name": ""},
                                    {"type": "chapter", "num": "10.5", "label": "Chapter 10.5", "name": ""},
                                    {"type": "section", "num": "4600", "label": "Section 4600", "name": ""}])),
        # Puerto Rico: the act's name is the code crumb's label
        dict(act_id="STATE_PR_TRANSPARENCIA_ART1", display_path="Ley de Transparencia (2019) / Ley de Transparencia / Art. 1",
             title_name="Ley de Transparencia (2019)", chapter_name="Ley de Transparencia",
             breadcrumb=json.dumps([{"type": "code", "num": "transparencia", "label": "Ley de Transparencia (2019)", "name": "Ley de Transparencia (2019)"},
                                    {"type": "part", "num": "", "label": "Ley de Transparencia", "name": "Ley de Transparencia"},
                                    {"type": "article", "num": "1", "label": "Art. 1", "name": "Nombre"}])),
    ]
    raw = tmp_path / "raw" / "open-us-law"
    raw.mkdir(parents=True)
    for st in ("dc", "oh", "ut", "ca", "pr"):
        pq.write_table(pa.Table.from_pylist([r for r in rows if r["act_id"].startswith(f"STATE_{st.upper()}_")]),
                       raw / f"us_{st}_statutes.parquet")
    monkeypatch.setattr(H.config, "RAW_DIR", tmp_path / "raw")
    assert H.from_corpus("dc") == {"lexflow:unit:dc:t2": "Government Administration.",
                                   "lexflow:unit:dc:t2-c5": "Administrative Procedure."}
    assert H.from_corpus("oh") == {"lexflow:unit:oh:t11-c1101": "Banks - General Provisions"}   # no "Title 11"
    assert H.from_corpus("ut") == {"lexflow:unit:ut:t63g": "General Government"}
    assert H.from_corpus("ca") == {"lexflow:unit:ca:cbpc-d2": "HEALING ARTS", "lexflow:unit:ca:cbpc-d2-c10.5": "Massage Therapy Act"}
    assert H.from_corpus("pr") == {"lexflow:unit:pr:transparencia": "Ley de Transparencia (2019)"}
    assert H.from_corpus("dc", keys=["lexflow:unit:dc:t2"]) == {"lexflow:unit:dc:t2": "Government Administration."}
    assert H.from_corpus("xx", log=lambda s: None) == {}


# ---- the extractors on saved official pages

def _samples():
    man = SAMPLES / "samples.json"
    if not man.exists():
        return []
    return [pytest.param(s, id=s["file"]) for s in json.loads(man.read_text(encoding="utf-8"))]


@pytest.mark.parametrize("sample", _samples())
def test_extractors_on_saved_pages(sample):
    html = (SAMPLES / sample["file"]).read_text(encoding="utf-8")
    for case in sample["units"]:
        units = {u.key: u for u in H.units_of(sample["state"], _row(case["act_id"], case["path"]))}
        assert case["key"] in units, (sample["file"], case["key"], sorted(units))
        assert H.extract(html, units[case["key"]]) == case["name"], (sample["file"], case["key"])


def test_samples_cover_three_extractors():
    man = SAMPLES / "samples.json"
    assert man.exists(), "fixtures/law/headings_samples/samples.json"
    states = {s["state"] for s in json.loads(man.read_text(encoding="utf-8"))}
    assert len(states) >= 3


def test_generic_extractor_reads_split_and_listed_headings():
    html = """<html><body><h1><span class="n">CHAPTER 119</span><span class="t">PUBLIC RECORDS</span></h1>
    <ul><li><a href="x">Chapter 36.</a> Something<br>Chapter 37. Virginia Freedom of Information Act</li>
    <li>Chapter 37.1 Not this one</li></ul>
    <p>See Chapter 37 of this title.</p></body></html>"""
    fl = H.units_of("fl", _row("STATE_FL_TXXXII_C119_S119.01", "Florida Code / Title XXXII / Chapter 119 / Section 119.01"))[-1]
    assert H.extract(html, fl) == "PUBLIC RECORDS"
    va = H.units_of("va", _row("STATE_VA_T2.2_C37_S2.2-3704", "Virginia Code / Title 2.2 / Chapter 37 / Section 2.2-3704"))[-1]
    assert H.extract(html, va) == "Virginia Freedom of Information Act"
    va36 = H.units_of("va", _row("STATE_VA_T2.2_C36_S2.2-3600", "Virginia Code / Title 2.2 / Chapter 36 / Section 2.2-3600"))[-1]
    assert H.extract(html, va36) == "Something"
    assert H.blocks("<p>not html at all") == ["not html at all"]
    # the window title is read last, and a breadcrumb before the unit's own level goes
    html = "<html><head><title>Title 1, Chapter 13: PUBLIC RECORDS AND PROCEEDINGS</title></head><body><p>Ch. 13 PDF</p></body></html>"
    me = H.units_of("me", _row("STATE_ME_T1_C13_S401", "ME Code / Title 1 / Chapter 13 / Section 401"))[-1]
    assert H.extract(html, me) == "PUBLIC RECORDS AND PROCEEDINGS"


# ---- the fixture and the hook

def test_fixture_get_and_save(tmp_path):
    p = tmp_path / "unit_headings.json"
    H.save({"units": {"lexflow:unit:va:t2.2-c37": {"name": "Virginia Freedom of Information Act",
                                                   "source": "https://law.lis.virginia.gov/vacode/title2.2/chapter37/",
                                                   "retrieved": "2026-10-15"}},
            "refused": [{"key": "lexflow:unit:oh:t1", "url": "https://codes.ohio.gov/x", "why": "robots.txt disallows"}],
            "unmatched": []}, p)
    H.reset()
    assert H.get("lexflow:unit:va:t2.2-c37", p) == "Virginia Freedom of Information Act"
    assert H.get("lexflow:unit:va:t2.2", p) is None
    H.reset()
    d = H.load(p)
    assert d["refused"][0]["key"] == "lexflow:unit:oh:t1" and d["built"]


def test_shipped_fixture_is_well_formed():
    d = H.load()
    assert d["units"], "fixtures/law/unit_headings.json is empty"
    for key, e in d["units"].items():
        assert key.startswith("lexflow:unit:") and key == key.lower() or ":" in key
        assert e["name"] and len(e["name"]) <= H.NAME_MAX
        assert e["source"] == "corpus" or e["source"].startswith("http")
        assert e["retrieved"]
    for e in d["refused"]:
        assert e["key"] and e["why"]
