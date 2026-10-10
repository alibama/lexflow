"""Regressions from the review of the statute index, retrieval, the planner and the local layer: units' shares,
cross-references in their own code, in-force versions first, both effective dates, one build at a time, the
build's stamp, official pages by host, and plural thesaurus lookups."""
import threading
import time

import pytest

from lexflow import config
from lexflow.ask import index as I
from lexflow.ask import plan as PL
from lexflow.ask import retrieve as RT
from lexflow.municipal import statutes


def _frame(rows):
    import pandas as pd
    out = [dict(act_id=f"A{i}", citation=r["citation"], section_number=r["number"],
                section_title=r.get("title", f"Heading {i} of a section"), chapter_name="",
                display_path=r.get("path", ""), act_status="in_force",
                text=r.get("text", "The words of this section, long enough to be a section."),
                source_url=f"https://example.test/{i}", word_count=None, last_amended_year=2020)
           for i, r in enumerate(rows)]
    df = pd.DataFrame(out)
    df["norm_section"] = df["section_number"].map(statutes.norm_section)
    return df


@pytest.fixture()
def zz(con, monkeypatch):
    """Serve a synthetic statute frame as state 'zz' (rows set by the test) and forget cached stamps."""
    frames = {}
    monkeypatch.setattr(statutes, "load", lambda state: frames[state])
    monkeypatch.setattr(statutes, "have", lambda state: state in frames)
    for cache in (I._STAMPS, I._READY):
        for k in list(cache):
            if (k if isinstance(k, str) else k[0]) == "zz":
                cache.pop(k)

    def make(rows):
        frames["zz"] = _frame(rows)
        I.build("zz", log=lambda *_: None)
        return frames["zz"]
    return make


def test_in_units_gives_every_unit_its_share_of_direct_children(zz):
    rows = [{"citation": f"Z § 1-{i}", "number": f"1-{i}", "path": f"Z Code / Chapter 1 / Section 1-{i}"}
            for i in range(10)]
    rows += [{"citation": "Z § 1-99", "number": "1-99", "path": "Z Code / Chapter 1 / Article 9 / Section 1-99"}]
    rows += [{"citation": f"Z § 2-{i}", "number": f"2-{i}", "path": f"Z Code / Chapter 2 / Section 2-{i}"}
             for i in range(10)]
    rows += [{"citation": f"Z § 3-{i}", "number": f"3-{i}", "path": f"Z Code / Chapter 3 / Section 3-{i}"}
             for i in range(2)]
    zz(rows)
    a, b, c = "Z Code / Chapter 1", "Z Code / Chapter 2", "Z Code / Chapter 3"
    got = I.in_units("zz", [a, b], limit=8)
    assert [I.parent(r) for r in got].count(a) == 4 and [I.parent(r) for r in got].count(b) == 4
    every = I.in_units("zz", [a, b])
    assert len(every) == 20 and "1-99" not in [r["section_number"] for r in every]     # direct children only
    # what a small unit leaves goes to the larger ones; rows stay in file order
    got = I.in_units("zz", [a, b, c], limit=9)
    assert [I.parent(r) for r in got] == [a] * 3 + [b] * 4 + [c] * 2
    assert [r["id"] for r in got] == sorted(r["id"] for r in got)


def test_cited_resolves_in_the_citing_sections_own_code(zz):
    def sec(citation, number, text=None):
        return {"citation": citation, "number": number, **({"text": text} if text else {})}
    zz([
        # Illinois: one chapter holds many acts, each numbering its own sections
        sec("725 ILCS 5/102-6", "102-6",
            "As in Section 9 of Article I of the Illinois Constitution, and as provided in Section 102-7."),
        sec("725 ILCS 5/102-7", "102-7"), sec("725 ILCS 105/9", "9"), sec("725 ILCS 120/9", "9"),
        # California: 'Article 2' is a part of the code, not section 2
        sec("Cal. HSC § 79240", "79240",
            "Article 2 (commencing with Section 13320), Article 3 and Article 5 of this chapter apply."),
        sec("Cal. HSC § 2", "2"), sec("Cal. HSC § 3", "3"), sec("Cal. HSC § 13320", "13320"),
        # New York: a letter suffix is part of the number
        sec("N.Y. CVR Law § 50-G", "50-G", "§ 50-g. Records. The clerk shall act as provided in section 51-a."),
        sec("N.Y. CVR Law § 50", "50"), sec("N.Y. CVR Law § 51-A", "51-A"), sec("N.Y. AGM Law § 51-A", "51-A"),
        # Louisiana's civil code is numbered in articles, and Texas criminal procedure cites 'Article 55.01'
        sec("La. Civ. Code art. 2316", "2316", "Every person is responsible as provided in Article 2315."),
        sec("La. Civ. Code art. 2315", "2315"),
        sec("Tex. Code of Criminal Procedure § 55.02", "55.02",
            "A person entitled to expunction under Article 55.01 may file a petition."),
        sec("Tex. Code of Criminal Procedure § 55.01", "55.01"),
    ])

    def cites(citation):
        row = next(r for r in I.lookup("zz", citation) if r["citation"] == citation)
        return [r["citation"] for r in RT.cited("zz", row)]
    assert cites("725 ILCS 5/102-6") == ["725 ILCS 5/102-7"]
    assert cites("Cal. HSC § 79240") == ["Cal. HSC § 13320"]
    assert cites("N.Y. CVR Law § 50-G") == ["N.Y. CVR Law § 51-A"]
    assert cites("La. Civ. Code art. 2316") == ["La. Civ. Code art. 2315"]
    assert cites("Tex. Code of Criminal Procedure § 55.02") == ["Tex. Code of Criminal Procedure § 55.01"]
    assert RT._code({"citation": "A.R.S. § 13-1204; Version 2"}) == RT._code({"citation": "A.R.S. § 13-1205"})


def test_lookup_puts_the_version_in_force_first(zz):
    zz([{"citation": "Z. Stat. § 105-1", "number": "105-1", "title": "(Effective until January 1, 2020) Tax rates."},
        {"citation": "Z. Stat. § 105-1", "number": "105-1", "title": "(Effective January 1, 2020) Tax rates."},
        {"citation": "Z. Stat. § 105-1", "number": "105-1", "title": "(Effective January 1, 2999) Tax rates."}])
    rows = I.lookup("zz", "Z. Stat. § 105-1")
    assert [r["original_title"][:31] for r in rows] == ["(Effective January 1, 2020) Tax",
                                                       "(Effective January 1, 2999) Tax",
                                                       "(Effective until January 1, 202"]
    assert I.by_ref("zz", "105-1")["id"] == rows[0]["id"]
    assert statutes.section_texts("zz", ["Z. Stat. § 105-1"])[0].title.startswith("(Effective January 1, 2020)")
    expired = rows[-1]["id"]
    by_id = statutes.section_texts_by_id("zz", [expired])[0]
    assert by_id.title.startswith("(Effective until January 1, 2020)") and by_id.section == "105-1"
    assert I.by_id("zz", expired)["id"] == expired and I.by_id("zz", 999) is None


def test_effective_reads_both_dates():
    assert I.effective("(Effective July 1, 2026; Effective until October 1, 2026) Modernized IGT") \
        == ("2026-07-01", "2026-10-01")
    assert I.effective("(Effective January 1, 2027, until January 1, 2031) Affordable housing") \
        == ("2027-01-01", "2031-01-01")
    assert I.effective("(Effective October 1, 2024 until October 30, 2030 - see editor's note) Report") \
        == ("2024-10-01", "2030-10-30")
    assert I.effective("(Effective until December 1, 2026) Expungement") == (None, "2026-12-01")
    assert I.effective("(Effective January 1, 2027) Definitions") == ("2027-01-01", None)
    assert I.effective("(Eff. Jan. 1, 2025) Fees") == ("2025-01-01", None)
    assert I.effective("(Effective until contingency met) Supplemental") == (None, None)
    assert I.effective("Definitions (effective until 2026)") == (None, None)
    from lexflow.ask.retrieve import in_force
    start, until = I.effective("(Effective July 1, 2026; Effective until October 1, 2026) X")
    assert in_force({"effective_from": start, "effective_until": until}, "2026-10-10") == -1


def test_concurrent_builds_of_a_state_build_once(zz, monkeypatch):
    rows = [{"citation": f"Z § 1-{i}", "number": f"1-{i}"} for i in range(50)]
    zz(rows)
    frame = statutes.load("zz")
    inside, calls = threading.Event(), []

    def slow(state):
        calls.append(state)
        inside.set()
        time.sleep(0.5)
        return frame
    monkeypatch.setattr(statutes, "load", slow)
    (I.index_dir() / "statutes_zz.building").write_text("left by a killed build")
    out, errors = {}, []

    def run(name):
        try:
            out[name] = I.build("zz", log=lambda *_: None)
        except Exception as e:  # noqa: BLE001
            errors.append(e)
    a = threading.Thread(target=run, args=("a",))
    a.start()
    assert inside.wait(5)
    b = threading.Thread(target=run, args=("b",))
    b.start()
    a.join(10), b.join(10)
    assert not errors and len(calls) == 1                     # the waiting build kept the other's index
    assert out["a"]["sections"] == out["b"]["sections"] == 50 and out["b"]["seconds"] == 0.0
    assert I.ready("zz") and len(I.lookup("zz", "1-49")) == 1
    assert not list(I.index_dir().glob("statutes_zz.building*"))
    # a forced build with nobody else building still rebuilds
    I.build("zz", log=lambda *_: None)
    assert len(calls) == 2


def test_build_stamps_the_file_it_read(zz, monkeypatch, tmp_path):
    rows = [{"citation": f"Z § 1-{i}", "number": f"1-{i}"} for i in range(5)]
    frame = zz(rows)
    f = tmp_path / "us_zz_statutes.parquet"
    f.write_bytes(b"old release")
    monkeypatch.setattr(statutes, "path_for", lambda state, kind="statutes": f)

    def load_then_replace(state):
        f.write_bytes(b"a newer release, replaced while the index was being built")
        return frame
    monkeypatch.setattr(statutes, "load", load_then_replace)
    I._STAMPS.pop("zz", None)
    I.build("zz", log=lambda *_: None)
    I._STAMPS.pop("zz", None)                                 # a minute later
    assert not I.ready("zz")                                  # built from the old rows: stale, so rebuilt


def test_web_pages_keep_only_the_places_own_host(monkeypatch):
    from lexflow.ask import local as L
    from lexflow.extract import searx
    monkeypatch.setattr(config, "SEARXNG_URL", "http://searx.test")
    asked = []

    def search(self, q, **kw):
        asked.append(q)
        return [{"title": t, "url": u, "snippet": ""} for t, u in [
            ("Fees", "https://www.charlottesville.gov/123/Court-Fees"),
            ("Parks", "https://parks.charlottesville.gov/fees"),
            ("Lookalike", "https://charlottesville.gov-payments.com/court-fees"),
            ("Prefix", "https://notcharlottesville.gov/fees"),
            ("Query", "https://example.com/?u=charlottesville.gov")]]
    monkeypatch.setattr(searx.SearX, "search", search)
    plan = PL.Plan(text="court fees", groups=[["court"], ["fee"]])
    for site in ("https://www.charlottesville.gov", "https://www.Charlottesville.gov:443/", "charlottesville.gov"):
        pages = L.web_pages({"name": "Charlottesville", "website": site}, plan, log=lambda *_: None)
        assert [p["title"] for p in pages] == ["Fees", "Parks"], site
        assert asked.pop() == "court fee site:charlottesville.gov"


def test_synonyms_find_short_plurals():
    assert PL.synonyms("fees") == PL.THESAURUS["fee"]
    assert PL.synonyms("taxes") == PL.THESAURUS["tax"]
    assert PL.synonyms("records") == PL.THESAURUS["records"]
    assert PL.synonyms("prisons") == PL.THESAURUS["prison"]
    assert PL.synonyms("expunged") == PL.THESAURUS["expunge"]
    assert PL.synonyms("waived") == PL.THESAURUS["waive"]
    assert PL.synonyms("process") == []
    flat = [t for g in PL.plan("What court fees can I get waived?").groups for t in g]
    assert "charge" in flat and "remit" in flat
