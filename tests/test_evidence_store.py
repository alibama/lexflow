"""The evidence store (lexflow/municipal/quotes.py): words from sites whose terms forbid reprinting them
(quotes.NO_REPRINT) never sit verbatim in a committed file.  ``withhold`` moves them to data/evidence/ (git-ignored)
and leaves a fingerprint; ``restore`` puts them back in memory for the loader and the matcher; ``rebuild`` makes the
evidence files again from the pages; ``leaks`` is the scan that proves no committed file holds eight or more
consecutive words of a withheld quote."""
import json
from pathlib import Path

import pytest

from lexflow.municipal import places as P
from lexflow.municipal import quotes as Q
from lexflow.store import db
from test_place_processes import GOV, _files, _proc, law, page  # noqa: F401 - the law fixture

ALB = "https://www.albemarle.org/government/finance/dog-licenses"
ALB_WORDS = "Dog licenses are sold by the Department of Finance at the County Office Building on McIntire Road"
ECODE_WORDS = "No penalty shall exceed 10 percent of the tax due"


def _held_spec():
    """An Albemarle file: a Code quote (kept), an albemarle.org quote read from an archive copy, an eCode360 fee
    quote, and a free site's step quote (kept)."""
    return _proc(place="va:albemarle county", gov_id=GOV["gov_id"], process="dog_license",
                 legal_basis=[{"level": "state", "citation": "Va. Code § 3.2-6524",
                               "url": "https://law.lis.virginia.gov/vacode/3.2-6524/",
                               "quote": "It shall be unlawful for any person to own a dog four months old or older in "
                                        "this Commonwealth unless such dog is licensed"},
                              {"level": "local", "citation": "County Code § 4-200", "url": ALB, "quote": ALB_WORDS,
                               "paraphrase": "The County's finance office sells dog licences.", "role": "authority"}],
                 steps=[{"step": "Ask", "url": "https://www.charlottesville.gov/foia", "quote": "Submit a request online"}],
                 fees=[{"item": "Late penalty", "amount": "up to 10%", "basis": "https://ecode360.com/49100159",
                        "quote": ECODE_WORDS}],
                 escalation=[], sources=[{"url": ALB, "retrieved": "2026-10-11"}])


def _copy(spec):
    return json.loads(json.dumps(spec))


@pytest.fixture()
def evidence_dir(tmp_path, monkeypatch):
    d = tmp_path / "evidence"
    monkeypatch.setattr(Q, "EVIDENCE_DIR", d)
    return d


def _pages():
    page(ALB, None, via="archive", capture="20260814000000", found=[ALB_WORDS])
    page("https://ecode360.com/49100159", None, found=[ECODE_WORDS])
    page("https://www.charlottesville.gov/foia", "Submit a request online")


def test_withhold_moves_no_reprint_words_out_and_restore_puts_them_back(con, law, evidence_dir):
    _pages()
    spec = _held_spec()
    words = Q.withhold(spec)
    assert set(words.values()) == {ALB_WORDS, ECODE_WORDS}
    held = spec["legal_basis"][1]
    assert "quote" not in held and held["quote_sha256"] == Q.full_hash(ALB_WORDS) and held["quote_words"] == 17
    assert held["paraphrase"] == "The County's finance office sells dog licences." and held["url"] == ALB
    assert held["capture"] == "20260814000000"
    assert list(held)[:3] == ["level", "citation", "url"] and list(held).index("quote_sha256") == 3  # the quote's place
    fee = spec["fees"][0]
    assert "quote" not in fee and fee["url"] == "https://ecode360.com/49100159" and fee["capture"] is None
    assert spec["legal_basis"][0]["quote"].startswith("It shall be unlawful")          # the Code's words stay
    assert spec["steps"][0]["quote"] == "Submit a request online"                     # a free site's words stay
    assert ALB_WORDS not in json.dumps(spec) and ECODE_WORDS not in json.dumps(spec)
    # without the evidence file the withheld quotes count as not matched, so the file is not verified
    qc = P.check_quotes(_copy(spec), "va")
    assert qc["quotes"] == 4 and qc["matched"] == 2
    assert {x["where"] for x in qc["unmatched"]} == {"legal_basis[1]", "fees[0]"}
    assert all("evidence store" in x["why"] for x in qc["unmatched"])
    assert not P.is_verified(_copy(spec), qc)
    # with it, restore puts the words back where they were and every quote matches
    Q.save_evidence("va/albemarle/dog_license", words)
    back = Q.restore(_copy(spec))
    assert back["legal_basis"][1]["quote"] == ALB_WORDS and back["fees"][0]["quote"] == ECODE_WORDS
    assert list(back["legal_basis"][1]).index("quote") == 4                           # right after the fingerprint
    assert [q for _, q, _ in P.process_quotes(back)] == [q for _, q, _ in P.process_quotes(_held_spec())]
    qc = P.check_quotes(_copy(spec), "va")                                            # the matcher restores itself
    assert qc["matched"] == 4 and not qc["unmatched"] and P.is_verified(_copy(spec), qc)
    assert Q.withhold(back) == words                                                  # withholding again: the same


def test_withhold_file_rewrites_the_file_and_the_loader_reads_the_evidence(con, law, tmp_path, monkeypatch,
                                                                            evidence_dir):
    _pages()
    monkeypatch.setattr(P, "PLACES_DIR", tmp_path / "places")
    d = tmp_path / "places" / "va" / "albemarle"
    d.mkdir(parents=True)
    path = d / "dog_license.json"
    path.write_text(json.dumps(_held_spec()), encoding="utf-8")
    said = []
    r = Q.withhold_file(path, log=said.append)
    assert r["withheld"] == 2 and r["held"] == 2 and r["evidence"] == "va/albemarle/dog_license"
    ev = evidence_dir / "va" / "albemarle" / "dog_license.json"
    assert ev.exists()
    assert set(json.loads(ev.read_text(encoding="utf-8"))["quotes"].values()) == {ALB_WORDS, ECODE_WORDS}
    on_disk = path.read_text(encoding="utf-8")
    assert ALB_WORDS not in on_disk and ECODE_WORDS not in on_disk and '"quote_sha256"' in on_disk
    assert Q.withhold_file(path, log=said.append)["withheld"] == 2                    # again: restore, then withhold
    db.upsert(con, "governments", [GOV])
    out = P.load_processes(con, log=said.append)
    assert out["processes"] == 1 and out["verified"] == 1
    row = db.one(con, "SELECT * FROM place_processes WHERE process='dog_license'")
    assert json.loads(row["spec"])["legal_basis"][1]["quote"] == ALB_WORDS            # the words, restored in memory
    ev.unlink()                                                                      # a clone without the evidence
    out = P.load_processes(con, log=said.append)
    assert out["verified"] == 0 and any("2 of its 4 quotes were not matched" in m for m in said)
    # a fixture names its evidence file itself, and a "text" field comes back as "text"
    fx = tmp_path / "fixtures" / "places" / "va"
    fx.mkdir(parents=True)
    f = fx / "discovery-albemarle.json"
    f.write_text(json.dumps({"place": "va:albemarle county", "processes": [{"id": "dog", "quotes": [
        {"text": ALB_WORDS, "source": ALB, "read_via": f"https://web.archive.org/web/20260814000000/{ALB}"},
        {"text": "Submit a request online", "source": "https://www.charlottesville.gov/foia"}]}]}), encoding="utf-8")
    assert Q.withhold_file(f, log=said.append)["evidence"] == "va/fixtures/discovery-albemarle"
    got = json.loads(f.read_text(encoding="utf-8"))
    q0 = got["processes"][0]["quotes"][0]
    assert got["evidence"] == "va/fixtures/discovery-albemarle" and "text" not in q0 and q0["quote_key"] == "text"
    assert q0["capture"] == "20260814000000"
    assert got["processes"][0]["quotes"][1]["text"] == "Submit a request online"
    assert Q.restore(got)["processes"][0]["quotes"][0]["text"] == ALB_WORDS


def test_the_scan_finds_eight_withheld_words_in_a_row_and_not_seven(tmp_path):
    ev = {Q.full_hash(ALB_WORDS): ALB_WORDS}
    a = tmp_path / "a.md"
    a.write_text("The County says: dog licenses are sold by the Department of Finance at the office.", encoding="utf-8")
    b = tmp_path / "b.json"
    b.write_text(json.dumps({"x": "Dog licenses are sold by the Department of Finance."}), encoding="utf-8")
    c = tmp_path / "c.json"
    c.write_text(json.dumps({"x": "are sold by the Department of Finance"}), encoding="utf-8")       # seven words
    found = Q.leaks([a, b, c], ev)
    assert {x["file"] for x in found} == {str(a), str(b)}
    assert all(len(x["words"].split()) == Q.MIN_RUN for x in found)
    assert not Q.leaks([c], ev) and not Q.leaks([a, b], {})


def test_the_evidence_files_are_rebuilt_from_the_pages(monkeypatch, evidence_dir):
    """``rebuild`` reads each page again (in memory; nothing of a NO_REPRINT site is cached) and finds each withheld
    quote as the run of ``quote_words`` words whose fingerprint is the quote's."""
    pages = {ALB: Q.variants(f"Licences\n{ALB_WORDS}.\nTags never expire."),
             "https://ecode360.com/49100159": Q.variants(f"§ 4-201. {ECODE_WORDS}, plus interest.")}
    asked = []
    monkeypatch.setattr(Q, "_page_words", lambda url, cap, log: (asked.append((url, cap)), pages.get(url))[1])
    spec = _held_spec()
    words = Q.withhold(spec, qc={"items": {}})                       # no match made: the citation rule withholds
    assert set(words.values()) == {ALB_WORDS, ECODE_WORDS}
    counts = Q.rebuild([(Path("curated/places/va/albemarle/dog_license.json"), spec)], log=lambda *_: None)
    assert counts == {"pages": 2, "read": 2, "quotes": 2, "found": 2}
    assert (ALB, None) in asked
    ev = json.loads((evidence_dir / "va" / "albemarle" / "dog_license.json").read_text(encoding="utf-8"))
    assert ev["quotes"] == words
    assert Q.restore(spec)["legal_basis"][1]["quote"] == ALB_WORDS


def test_the_committed_albemarle_files_hold_no_no_reprint_words():
    """Every quote in the committed Albemarle files (and Staunton's zoning variance, which quotes eCode360) that
    cites a NO_REPRINT site is withheld; with the evidence files present the words come back in every file."""
    files = _files("albemarle") + [p for p in _files("staunton") if p[0].stem == "zoning_variance"]
    if len(files) < 21:
        pytest.skip("another workflow may be writing these files")
    if not Q.cache_dir().exists():
        pytest.skip("the quote fetch's cache is not present here, so what is withheld cannot be told apart")
    for path, spec in files:
        held = {q["where"] for q in Q.withheld_quotes(spec)}
        items = P.check_quotes(spec, "va")["items"]
        for where, q, cites in P.process_quotes(spec):             # a quote kept beside a NO_REPRINT cite: the Code's
            if where not in held and any(Q.policy(u) for u in Q.cited_urls(cites)):   # words, a free page's, or free
                hit = items.get(where) or {}
                assert hit.get("by") == "code" or (hit.get("by") and not Q.policy(hit.get("url"))) \
                    or Q.free_words(q), (path.name, where, q[:60])
        if path.parent.name == "albemarle" and path.stem != "traffic_ticket":   # the county's own pages, throughout
            assert Q.withheld_quotes(spec), path.name
    if not Q.EVIDENCE_DIR.exists():
        pytest.skip("the evidence files (data/evidence/) are not present here")
    for path, spec in files:
        Q.restore(spec, path)
        missing = [q for q in Q.withheld_quotes(spec) if not q["restored"]]
        assert not missing, (path.name, missing[:2])
