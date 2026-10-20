"""Researched local processes, one file each (curated/places/<state>/<place>/<process>.json): loading, wiki pages
(only verified ones, escaped), the API, lexflow's software match of their quotes (lexflow/municipal/quotes.py), the
rule that makes a file count as verified, the quote policy for sites whose terms forbid reprinting, and the wording
of the researched files."""
import hashlib
import json
import logging
import re

import pytest

from lexflow import config
from lexflow.municipal import places as P
from lexflow.municipal import quotes as Q
from lexflow.publish import lexipedia as LX
from lexflow.store import db

GOV = {"gov_id": "47100200200000", "state": "va", "name": "Albemarle County", "kind": "county", "population": 113535}
LAW = {"3.2-6524": "A. It shall be unlawful for any person to own a dog four months old or older in this Commonwealth "
                   "unless such dog is licensed, as required by the provisions of this article.",
       "2.2-3704": "B. Any public body that is subject to this chapter and that is the custodian of the requested "
                   "records shall promptly, but in all cases within five working days of receiving a request, "
                   "provide the requested records to the requester."}
LOCAL_LABEL = re.compile(r"\*\*(?:\d+ of \d+ quotes? matched by lexflow's software[^·]*|Sources retrieved[^·]*)"
                         r" · Drafted with an AI system · (?:Not yet reviewed by a person|Reviewed by [^*]+)\*\*")


@pytest.fixture()
def law(monkeypatch):
    """Open US Law's copy of the Code of Virginia, as far as these tests quote it."""
    from lexflow.ir import SectionText
    from lexflow.municipal import statutes

    def section_texts(state, numbers, code=None, df=None):
        out = []
        for n in numbers:
            if n not in LAW:
                raise KeyError(n)
            out.append(SectionText(section=n, title="t", code="Code of Virginia", jurisdiction=state, text=LAW[n]))
        return out
    monkeypatch.setattr(statutes, "section_texts", section_texts)


def page(url, text=None, *, via="live", fetched="2026-10-11", capture=None, error=None, found=None, checked=None):
    """Put a page in lexflow's quote cache as the quote fetch would (``Q.fetch``)."""
    entry = {"url": Q.key(url), "via": via if not error else None, "fetched": fetched, "capture": capture,
             "status": 200, "error": error}
    if text is not None:
        entry["text"] = text
    if found is not None:
        entry["found"] = sorted(Q.qhash(q) for q in found)
        entry["checked"] = sorted(Q.qhash(q) for q in (checked or found))
    Q._save(entry)


def _spec(verified=True, **kw):
    return {"place": "va:albemarle county", "gov_id": GOV["gov_id"], "process": "dog_license",
            "title": "License a dog", "question": "Do I need to license my dog, and how?", "category": "animals",
            "kind": "process", "office": "Treasurer", "summary": "Dogs four months and older need a licence.",
            "legal_basis": [{"level": "state", "citation": "Va. Code § 3.2-6524", "url": "https://law.lis.virginia.gov/vacode/3.2-6524/",
                             "quote": "It shall be unlawful for any person to own a dog four months old or older in this Commonwealth unless such dog is licensed",
                             "role": "authority"}],
            "steps": [{"id": "s1", "step": "Show a rabies certificate **and** pay", "who": "Owner", "how": "At the [[Treasurer]]",
                       "deadline": None, "fee": None, "form": "f1", "url": "https://www.example-county.gov/dog", "quote": None, "source": None}],
            "forms": [{"id": "f1", "title": "Dog licence application", "number": None, "url": "https://www.example-county.gov/f1.pdf",
                       "official": True, "fillable": False}],
            "fees": [], "contacts": [{"kind": "phone", "value": "434-296-5851", "label": "Treasurer's Office",
                                      "url": "https://www.example-county.gov/treasurer"}],
            "escalation": [], "caveats": [], "sources": [{"url": "https://www.example-county.gov/dog", "title": "Dog licences",
                                                          "retrieved": "2026-10-10"}],
            "researched_by": "an AI system", "verified": verified, "checks": {}, **kw}


def _write(tmp_path, spec, name="dog_license"):
    d = tmp_path / "va" / "albemarle_county"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{name}.json").write_text(json.dumps(spec), encoding="utf-8")


def test_processes_load_and_publish_only_when_verified(con, law, tmp_path, monkeypatch):
    monkeypatch.setattr(P, "PLACES_DIR", tmp_path)
    db.upsert(con, "governments", [GOV])
    con.commit()
    _write(tmp_path, _spec(verified=False))
    _write(tmp_path, _spec(verified=True, process="bpol_business_license", title="Get a business licence",
                           category="business"), name="bpol_business_license")
    (tmp_path / "va" / "albemarle_county" / "broken.json").write_text("{not json", encoding="utf-8")
    out = P.load_processes(con, log=lambda *_: None)
    assert out == {"processes": 2, "verified": 1, "process_contacts": 2}
    assert db.scalar(con, "SELECT count(*) FROM contacts WHERE gov_id=? AND question='dog_license'", GOV["gov_id"]) == 1
    pages = LX.all_pages(con)
    g = db.one(con, "SELECT * FROM governments WHERE gov_id=?", GOV["gov_id"])
    assert LX.local_process_page(g, "bpol_business_license", con) in pages
    assert LX.local_process_page(g, "dog_license", con) not in pages            # not verified: not published
    overview = pages[LX.place_page(g, con)]
    assert "Local processes" in overview and "Get a business licence" in overview and "License a dog" not in overview


def test_a_local_process_page_escapes_and_quotes(con, law):
    g = dict(GOV)
    db.upsert(con, "governments", [g])
    text = LX.render_local_process(con, g, {"process": "dog_license", "spec": _spec()})
    assert "Va. Code § 3.2-6524" in text and "four months old or older" in text
    assert "**and**" not in text and "[[Treasurer]]" not in text                 # markup in the text is escaped
    assert "Dog licence application" in text and "Information, not legal advice" in text
    assert LOCAL_LABEL.search(text)
    # a process id that a state model's sub-page uses gets a suffix
    assert LX.local_process_page(g, "records").endswith(":records_p")


def test_api_lists_places_and_processes(con, law, tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from lexflow.api import app as API
    monkeypatch.setattr(config, "JOB_RUNNER", False)
    monkeypatch.setattr(P, "PLACES_DIR", tmp_path)
    db.upsert(con, "governments", [GOV])
    con.commit()
    _write(tmp_path, _spec())
    P.load_processes(con, log=lambda *_: None)
    with TestClient(API.app) as c:
        listed = {r["gov_id"]: r for r in c.get("/api/places").json()}
        assert listed[GOV["gov_id"]]["processes"] == 1 and listed[GOV["gov_id"]]["processes_verified"] == 1
        procs = c.get(f"/api/places/{GOV['gov_id']}/processes").json()
        assert procs[0]["process"] == "dog_license" and procs[0]["verified"] == 1
        one = c.get(f"/api/places/{GOV['gov_id']}/processes/dog_license").json()
        assert one["spec"]["title"] == "License a dog" and one["government"]["name"] == "Albemarle County"
        assert c.get(f"/api/places/{GOV['gov_id']}/processes/nope").status_code == 404


# ---- the matcher ----------------------------------------------------------------------------------------------

def test_local_quotes_are_matched_with_the_state_models_matcher():
    """Quotes are matched with validate.quote_in, the state models' check, after whitespace, curly quotation marks,
    odd spaces, soft hyphens and ligatures are normalised; a PDF's line-end hyphens are also tried joined.  The
    stand-in used where validate cannot be imported agrees with it."""
    from lexflow.validate import quote_in
    text = "The Treasurer’s Office sells “dog tags”.\nLicenses are ofﬁcial and cost­ $10.\n"
    assert Q.match("The Treasurer's Office sells \"dog tags\".", text)
    assert Q.match("Licenses are official and cost $10.", text)
    assert not Q.match("the Treasurer's Office", text)                          # case is not normalised
    assert not Q.match("", text)
    assert Q.match("the probate tax", "the pro-\nbate tax") and Q.match("pro- bate", "the pro-\nbate tax")
    # a sentence that runs on to the next PDF page, past the page number printed at the break
    for page in ("staff time to access,\r\n4\r\n\r\n\fduplicate, supply", "staff time to access,\r\n\f5\r\nduplicate, supply",
                 "staff time to access,\n  Page 3 of 9\n\fduplicate, supply"):
        assert Q.match("staff time to access, duplicate, supply", page), page
    assert not Q.match("access, duplicate", "access, 4 duplicate")                  # a number in the text stays
    for q, t in [("a  b", "x a b y"), ("it’s", "it's"), ("ab", "a b"), ("", "x"), ("x", "")]:
        assert Q._plain_quote_in(q, t) == quote_in(q, t), (q, t)


def test_page_text_comes_from_html_pdf_word_and_json():
    html = (b"<html><head><title>Dogs</title><script>var x = 'Pay now';</script></head><body><nav>Home</nav>"
            b"<p>Pay the <b>Treasurer</b>'s Office by <a href='#'>June 5</a>.</p><ul><li>One</li><li>Two</li></ul>"
            b"<!-- hidden --></body></html>")
    kind, text = Q.extract(html, "text/html; charset=utf-8")
    assert kind == "html" and "Pay now" not in text and "hidden" not in text
    assert Q.match("Pay the Treasurer's Office by June 5.", text) and not Q.match("OneTwo", text)
    kind, text = Q.extract(json.dumps({"MatterTextPlain": "The rate is six percent.", "Id": 7}).encode(),
                           "application/json")
    assert kind == "json" and Q.match("The rate is six percent.", text)
    import io
    import zipfile
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("word/document.xml", '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/'
                   '2006/main"><w:body><w:p><w:r><w:t>Fees are </w:t></w:r><w:r><w:t>$25.</w:t></w:r></w:p>'
                   '</w:body></w:document>')
    kind, text = Q.extract(buf.getvalue(), "application/octet-stream")
    assert kind == "docx" and Q.match("Fees are $25.", text)
    assert Q.extract(b"%PDF-1.4 not really a pdf", "application/pdf")[0] == "pdf"


def test_a_redlined_ordinance_matches_in_its_adopted_reading():
    """Legistar ordinances are often Word redlines: struck text goes, underlined text comes in.  The page text is
    the document as it stands and, after it, its adopted reading (struck, hidden and deleted text dropped), so a
    quote of the ordinance as adopted matches, and so does one of the redline as printed."""
    import io
    import zipfile
    w = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
    body = (f'<w:document {w}><w:body><w:p><w:r><w:t xml:space="preserve">The rate of this tax is </w:t></w:r>'
            '<w:r><w:rPr><w:strike/></w:rPr><w:t>four</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r>'
            '<w:r><w:rPr><w:u w:val="single"/></w:rPr><w:t>six</w:t></w:r>'
            '<w:r><w:t xml:space="preserve"> percent</w:t></w:r><w:del><w:r><w:delText> or more</w:delText></w:r></w:del>'
            '<w:r><w:rPr><w:strike w:val="false"/></w:rPr><w:t xml:space="preserve"> of the amount paid.</w:t></w:r>'
            '</w:p></w:body></w:document>')
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("word/document.xml", body)
    kind, text = Q.extract(buf.getvalue(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    assert kind == "docx"
    assert Q.match("The rate of this tax is six percent of the amount paid.", text)       # as adopted
    assert Q.match("The rate of this tax is four six percent", text)                       # the redline
    assert not Q.match("four percent", text) and not Q.match("or more", text)


def test_which_pages_a_quote_cites():
    assert Q.cited_urls(["https://charlottesvilleva.api.civicclerk.com/v1/Meetings/GetMeetingFileStream(fileId=6502,"
                         "plainText=false)"]) == ["https://charlottesvilleva.api.civicclerk.com/v1/Meetings/"
                                                  "GetMeetingFileStream(fileId=6502,plainText=false)"]
    assert Q.cited_urls(["Va. Code § 1-2; see https://www.example.org/a (the page)."]) == ["https://www.example.org/a"]
    assert Q.original("https://web.archive.org/web/20260814172629/https://www.albemarle.org/x") == \
        "https://www.albemarle.org/x"
    assert Q.capture_of("https://web.archive.org/web/20260814172629id_/https://www.albemarle.org/x") == \
        "20260814172629"


# ---- the quote policy -----------------------------------------------------------------------------------------

def test_the_quote_policy_names_each_site_its_reason_and_its_terms():
    """Municode, eCode360 and albemarle.org forbid reposting their content: one table holds each one's reason and
    terms page, an Internet Archive copy of their pages counts as theirs, and the method page can say so."""
    assert set(Q.NO_REPRINT) == {"library.municode.com", "ecode360.com", "albemarle.org"}
    assert Q.NO_REPRINT["albemarle.org"]["terms"] == "https://www.albemarle.org/government/terms-and-conditions"
    assert Q.NO_REPRINT["ecode360.com"]["terms"] == "https://ecode360.com/docs/TOS.html"
    assert Q.NO_REPRINT["library.municode.com"]["terms"] == "https://www.municode.com/code/page/terms-use"
    assert all(p["reason"] and p["publisher"] for p in Q.NO_REPRINT.values())
    assert Q.NO_REPRINT["library.municode.com"]["fetch"] is False             # link only (credits-research.md)
    for url in ("https://www.albemarle.org/dogs", "https://lfweb.albemarle.org/x.pdf",
                "https://web.archive.org/web/20260814172629/https://www.albemarle.org/dogs",
                "https://ecode360.com/49100159", "https://library.municode.com/va/charlottesville"):
        assert Q.policy(url), url
    for url in ("https://albemarle.legistar.com/View.ashx", "https://www.charlottesville.gov/x", "Albemarle Code § 4"):
        assert Q.policy(url) is None, url
    assert Q.reprint_note("https://ecode360.com/1").startswith("General Code's words are not reprinted here: ")
    text = " ".join(Q.method_lines())
    for p in Q.NO_REPRINT.values():
        assert f"[[{p['terms']}|{p['site']}]]" in text
    assert "Internet Archive" in text and "not matched" in text and "AI system's count" in text


# ---- the match of a file's quotes, and the rule for verified ---------------------------------------------------

def _proc(**kw):
    """A verified file with a Code quote, a step quote from a live page, a fee quote from an archived page of a site
    that refuses automated readers, and an escalation quote that cites no page."""
    spec = {"place": "va:charlottesville", "process": "records_request", "title": "Ask for a record", "verified": True,
            "legal_basis": [{"level": "state", "citation": "Va. Code § 2.2-3704(B)",
                             "url": "https://law.lis.virginia.gov/vacode/2.2-3704/",
                             "quote": "provide the requested records to the requester"}],
            "steps": [{"step": "Ask", "url": "https://www.charlottesville.gov/foia",
                       "quote": "Submit a request online"}],
            "fees": [{"item": "Copies", "basis": "https://www.ci.staunton.va.us/fees", "quote": "10 cents a page"}],
            "escalation": [{"trigger": "No answer", "next": "Ask again", "basis": "City practice",
                            "quote": "Call the FOIA officer"}],
            "sources": [{"url": "https://www.charlottesville.gov/foia", "retrieved": "2026-10-09"},
                        {"url": "https://www.charlottesville.gov/contact", "retrieved": "2026-10-10"}],
            "checks": {"verified_by": "an AI verifier", "date": "2026-10-10"}}
    spec.update(kw)
    return spec


def _pages(fetched="2026-10-11"):
    page("https://www.charlottesville.gov/foia", "To ask, Submit a request online at any time.", fetched=fetched)
    page("https://www.ci.staunton.va.us/fees", "Copies cost 10 cents a page.", via="archive",
         capture="20260717000000", fetched=fetched)
    page("https://www.charlottesville.gov/contact", "No reply? Call the FOIA officer.", fetched=fetched)


def test_every_quote_is_matched_to_the_code_or_the_page_it_cites(con, law):
    _pages()
    spec = _proc()
    qc = P.check_quotes(spec, "va", "2026-10-12")
    assert (qc["quotes"], qc["matched"], qc["by_code"], qc["by_page"], qc["by_archive"]) == (4, 4, 1, 3, 1)
    assert qc["unmatched"] == [] and qc["code"] == "Code of Virginia" and qc["version"] == P.QC_VERSION
    assert qc["items"]["fees[0]"] == {"by": "archive", "url": "https://www.ci.staunton.va.us/fees", "cited": True,
                                      "on": "2026-10-11", "capture": "20260717000000"}
    assert qc["items"]["escalation[0]"]["url"] == "https://www.charlottesville.gov/contact"   # another cited page
    assert qc["items"]["escalation[0]"]["cited"] is False
    assert qc["pages"]["https://www.ci.staunton.va.us/fees"] == {"via": "archive", "capture": "20260717000000",
                                                                 "fetched": "2026-10-11", "error": None}
    assert qc["matched_on"] == ["2026-10-11", "2026-10-12"]
    assert P.is_verified(spec, qc) and P.verify_problem(spec, qc) is None
    # the label, as the page prints it
    text = LX.local_check(spec, ["2026-10-10"], qc)
    assert text == ("4 of 4 quotes matched by lexflow's software: 1 to Open US Law's copy of the Code of Virginia, "
                    "3 to the cited pages (1 from an Internet Archive copy) between 11 October 2026 and 12 October "
                    "2026")


def test_a_quote_that_does_not_match_is_listed_and_the_file_is_not_verified(con, law, tmp_path, monkeypatch):
    from test_places_strategies import _govs
    _govs(con)
    _pages()
    spec = _proc(fees=[{"item": "Copies", "basis": "https://www.ci.staunton.va.us/fees", "quote": "free of charge"}],
                 legal_basis=[{"level": "state", "citation": "Va. Code § 2.2-3704(B)",
                               "url": "https://law.lis.virginia.gov/vacode/2.2-3704/", "quote": "within ten days"}],
                 steps=[{"step": "Ask", "url": "https://www.charlottesville.gov/unread", "quote": "Ask in person"}])
    qc = P.check_quotes(spec, "va")
    why = {x["where"]: x["why"] for x in qc["unmatched"]}
    assert set(why) == {"legal_basis[0]", "steps[0]", "fees[0]"} and qc["matched"] == 1
    assert why["legal_basis[0]"] == "not found word for word in Open US Law's copy of § 2.2-3704"
    assert why["steps[0]"].startswith("the cited page has not been read by lexflow's software yet")
    assert why["fees[0]"].startswith("not found word for word in the Internet Archive copy of 17 July 2026 of the "
                                     "cited page, read on 11 October 2026")
    assert P.verify_problem(spec, qc) == "3 of its 4 quotes were not matched by lexflow's software"
    assert not P.is_verified(spec, qc)
    (tmp_path / "places" / "va" / "charlottesville").mkdir(parents=True)
    (tmp_path / "places" / "va" / "charlottesville" / "records_request.json").write_text(json.dumps(spec),
                                                                                       encoding="utf-8")
    monkeypatch.setattr(P, "PLACES_DIR", tmp_path / "places")
    said = []
    assert P.load_processes(con, log=said.append)["verified"] == 0
    assert any("records_request.json: 3 of its 4 quotes were not matched by lexflow's software, so it is loaded as "
               "not verified" in x for x in said)
    row = db.one(con, "SELECT * FROM place_processes")
    assert row["verified"] == 0 and len(json.loads(row["quote_check"])["unmatched"]) == 3
    assert "lexflow:va:charlottesville:records_request" not in LX.all_pages(con)
    # the page, rendered anyway, lists every quote that did not match and marks it where it stands
    g = db.one(con, "SELECT * FROM governments WHERE name='City of Charlottesville'")
    text = LX.render_local_process(con, g, {"process": "records_request", "spec": spec})
    head = text.split("\n")[2]
    assert head.startswith("**1 of 4 quotes matched by lexflow's software: 1 to the cited pages") and \
        "; 3 not matched (listed below) · Drafted with an AI system · Not yet reviewed by a person**" in head
    block = text.split("===== Quotes not matched =====")[1].split("=====")[0]
    for q in ("“within ten days”", "“Ask in person”", "“free of charge”"):
        assert q in block
    assert "//Ask in person// (not matched by lexflow's software: the cited page has not been read" in text
    assert "Every quote" not in text and "AI verifier" not in text


def test_the_ai_check_date_counts_only_with_the_software_match(con, law):
    """A file loads as verified when the AI verifier passed it and either its AI check is dated on or after every
    source's retrieval, or lexflow's software matched every quote on or after those dates; never with a quote that
    did not match, and an AI check dated in the future does not count."""
    _pages(fetched="2026-10-11")
    on_time = _proc()                                                          # AI 10-10, sources to 10-10
    late = _proc(sources=_proc()["sources"] + [{"url": "https://www.charlottesville.gov/x", "retrieved": "2026-10-11"}])
    assert P.check_date_problem(on_time) is None
    assert "dated 2026-10-10, before some of its sources were retrieved (the latest on 2026-10-11)" in \
        P.check_date_problem(late)
    assert P.is_verified(late)                     # the software matched every quote on 2026-10-11 and later
    later = _proc(sources=_proc()["sources"] + [{"url": "https://www.charlottesville.gov/x", "retrieved": "2026-10-12"}])
    assert not P.is_verified(later)                # the pages were read on 2026-10-11, before that source
    assert "did not match every quote on or after that" in P.verify_problem(later)
    future = _proc(checks={"verified_by": "an AI verifier", "date": "2099-01-01"})
    assert "in the future" in P.check_date_problem(future)
    assert P.is_verified(future)                   # the software match carries it, not the future AI date
    undated = _proc(checks={})
    assert P.check_date_problem(undated) == "its AI check is not dated" and P.is_verified(undated)
    assert not P.is_verified(_proc(verified=False))
    assert P.verify_problem(_proc(verified=False)) == "the AI verifier did not pass it"


def test_a_stored_match_is_used_only_for_the_file_it_was_made_from(con, law, tmp_path, monkeypatch):
    from test_places_strategies import _govs
    _govs(con)
    _pages()
    spec = _proc()
    (tmp_path / "places" / "va" / "charlottesville").mkdir(parents=True)
    (tmp_path / "places" / "va" / "charlottesville" / "records_request.json").write_text(json.dumps(spec),
                                                                                       encoding="utf-8")
    monkeypatch.setattr(P, "PLACES_DIR", tmp_path / "places")
    assert P.load_processes(con, log=lambda *_: None)["verified"] == 1
    stored = json.loads(db.one(con, "SELECT quote_check FROM place_processes")["quote_check"])
    assert stored["hash"] == __import__("lexflow.signoff", fromlist=["x"]).text_hash(spec)
    page_text = LX.all_pages(con)["lexflow:va:charlottesville:records_request"]
    assert LOCAL_LABEL.search(page_text) and "4 of 4 quotes matched by lexflow's software" in page_text
    # a forged count for another version of the file is not used: the page matches the quotes again
    con.execute("UPDATE place_processes SET quote_check=?", (json.dumps(dict(stored, matched=9, quotes=9,
                                                                             hash="0" * 64)),))
    con.commit()
    assert "4 of 4 quotes matched" in LX.all_pages(con)["lexflow:va:charlottesville:records_request"]


def test_words_from_a_site_that_forbids_reposting_are_paraphrased_and_linked(con, law):
    """An albemarle.org, eCode360 or Municode quote stays in the file as evidence and is matched (from what the
    fetch kept: no words, only which quotes the page held), but the page prints lexflow's paraphrase, the link and
    why, never the words."""
    alb = "https://www.albemarle.org/government/finance/dog-licenses"
    page(alb, None, via="archive", capture="20260814000000",
         found=["Dog licenses are sold by the Department of Finance"],
         checked=["Dog licenses are sold by the Department of Finance", "Tags never expire"])
    page("https://ecode360.com/49100159", None, found=["No penalty shall exceed 10 percent"])
    spec = _proc(place="va:albemarle county",
                 legal_basis=[{"level": "local", "citation": "County Code § 4-200", "url": alb, "role": "authority",
                               "quote": "Dog licenses are sold by the Department of Finance",
                               "paraphrase": "The County's finance office sells dog licences."}],
                 steps=[{"step": "Buy the tag from the finance office", "url": alb, "quote": "Tags never expire"}],
                 fees=[{"item": "Late penalty", "amount": "up to 10%", "basis": "https://ecode360.com/49100159",
                        "quote": "No penalty shall exceed 10 percent"}],
                 escalation=[], sources=[{"url": alb, "retrieved": "2026-10-11"}])
    qc = P.check_quotes(spec, "va")
    assert qc["matched"] == 2 and [x["where"] for x in qc["unmatched"]] == ["steps[0]"]
    text = LX.render_local_process(con, GOV, {"process": "dog_license", "spec": spec})
    for words in ("Dog licenses are sold by the Department of Finance", "Tags never expire",
                  "No penalty shall exceed 10 percent"):
        assert words not in text, words
    assert "in lexflow's words: The County's finance office sells dog licences." in text
    assert "Albemarle County's words are not reprinted here: Albemarle County's Terms and Conditions" in text
    assert "[[https://www.albemarle.org/government/terms-and-conditions|the terms]]" in text
    assert "(not matched by lexflow's software: " in text                     # the step quote, still not reprinted
    assert "===== Quotes not matched =====" in text
    # each site's reason and terms are given once, in their own section; each quote points to it
    block = text.split("===== Words not reprinted =====")[1].split("=====")[0]
    assert text.count("Terms and Conditions allow browsing") == 1 and "Terms and Conditions allow browsing" in block
    assert "General Code's Terms and Conditions of Use" in block
    assert text.count("words are not reprinted here; read them at the link") == 2


# ---- fetching -------------------------------------------------------------------------------------------------

def test_the_fetch_is_polite_falls_back_to_the_archive_and_is_cached(con):
    """GET only with the lexflow-research User-Agent and robots.txt obeyed, 1.5 s apart on a host; a host that
    refuses automated readers is read from its newest Internet Archive copy (timestamp kept); a site whose terms
    forbid reposting keeps no words in the cache; Municode is never fetched; a second run fetches nothing."""
    import responses
    waits = []
    with responses.RequestsMock(assert_all_requests_are_fired=False) as rs:
        rs.get("https://www.charlottesville.gov/robots.txt", body="User-agent: *\nDisallow: /private\n")
        rs.get("https://www.charlottesville.gov/foia", body="<p>Submit a request online.</p>",
               content_type="text/html")
        rs.get("https://www.charlottesville.gov/fees", body="<p>10 cents a page.</p>", content_type="text/html")
        rs.get("https://www.charlottesville.gov/private/x", body="secret")
        rs.get("https://www.albemarle.org/robots.txt", status=403)
        rs.get(re.compile(r"https://web\.archive\.org/web/(?!20260814172629)\d{14}id_/https://www\.albemarle\.org/dogs"),
               status=302, headers={"Location": "https://web.archive.org/web/20260814172629id_/"
                                                "https://www.albemarle.org/dogs"})
        rs.get("https://web.archive.org/web/20260814172629id_/https://www.albemarle.org/dogs",
               body="<p>Dog licenses are sold by the Department of Finance.</p>", content_type="text/html")
        rs.get("https://web.archive.org/robots.txt", status=404)
        pages = {"https://www.charlottesville.gov/foia": ["Submit a request online"],
                 "https://www.charlottesville.gov/fees": [],
                 "https://www.charlottesville.gov/private/x": [],
                 "https://www.albemarle.org/dogs": ["Dog licenses are sold by the Department of Finance", "Other"],
                 "https://library.municode.com/va/x": []}
        out = Q.fetch(pages, log=lambda *_: None, sleep=waits.append, workers=1)
        assert out == {"live": 2, "archive": 1, "failed": 1, "skipped": 1}
        agents = {c.request.headers["User-Agent"] for c in rs.calls}
        assert agents == {"lexflow-research/0.1 (https://github.com/alibama/lexflow)"}
        assert all(c.request.method == "GET" for c in rs.calls)
        assert not any("/private/" in c.request.url for c in rs.calls)        # robots.txt obeyed
        assert not any("municode" in c.request.url for c in rs.calls)         # never fetched
        # 1.5 s between two requests to one host, 5 s on the Internet Archive (it answers 503 to faster readers)
        assert waits and max(w for w in waits if w <= Q.MIN_INTERVAL) > 1.4
        assert all(w <= Q.MIN_INTERVAL or w <= Q.ARCHIVE_INTERVAL for w in waits) and max(waits) > 4.9
        n = len(rs.calls)
        assert Q.fetch(pages, log=lambda *_: None, sleep=waits.append) == {"live": 0, "archive": 0, "failed": 0,
                                                                           "skipped": 5}
        assert len(rs.calls) == n                                             # cached: nothing fetched again
    alb = Q.cached("https://www.albemarle.org/dogs")
    assert alb["via"] == "archive" and alb["capture"] == "20260814172629" and "text" not in alb
    assert Q.has(alb, "Dog licenses are sold by the Department of Finance") is True and Q.has(alb, "Other") is False
    assert Q.has(alb, "never checked") is None
    live = Q.cached("https://www.charlottesville.gov/foia")
    assert live["via"] == "live" and live["fetched"] and Q.has(live, "Submit a request online.")
    assert "robots.txt disallows" in Q.cached("https://www.charlottesville.gov/private/x")["error"]
    assert Q.cached("https://library.municode.com/va/x")["error"].startswith("not fetched: ")
    assert str(Q.cache_dir()).startswith(str(config.DATA_DIR / "cache"))


def test_several_archive_readers_keep_to_one_clock(con):
    """Internet Archive downloads are slow, so several readers overlap them, but they share one clock: every
    request to web.archive.org after the first waits its full 5 s, as with one reader."""
    import responses
    waits = []
    urls = [f"https://www.ci.staunton.va.us/page{i}" for i in range(4)]
    with responses.RequestsMock(assert_all_requests_are_fired=False) as rs:
        rs.get("https://www.ci.staunton.va.us/robots.txt", status=403)
        rs.get("https://web.archive.org/robots.txt", status=404)
        for i, u in enumerate(urls):
            rs.get(f"https://web.archive.org/web/2026081400000{i}id_/{u}", body=f"<p>Page {i}.</p>",
                   content_type="text/html")
            rs.get(re.compile(rf"https://web\.archive\.org/web/(?!2026081400000{i})\d{{14}}id_/{re.escape(u)}$"),
                   status=302, headers={"Location": f"https://web.archive.org/web/2026081400000{i}id_/{u}"})
        out = Q.fetch({u: [f"Page {i}."] for i, u in enumerate(urls)}, log=lambda *_: None, sleep=waits.append,
                      workers=1, archive_workers=3)
        archive_calls = [c for c in rs.calls if "web.archive.org" in c.request.url]
    assert out == {"live": 0, "archive": 4, "failed": 0, "skipped": 0}
    assert all(Q.cached(u)["via"] == "archive" and Q.cached(u)["capture"].startswith("2026081400000") for u in urls)
    assert len([w for w in waits if Q.ARCHIVE_INTERVAL - 0.5 < w <= Q.ARCHIVE_INTERVAL]) == len(archive_calls) - 1


# ---- the researched files' wording ----------------------------------------------------------------------------

QUOTES = {"albemarle": (2308, "ee94740ac5560ef91d2d2da8e52afa3fa46d17c7a577fd75292edd7178b59b0f"),
          "charlottesville": (1848, "74bceedb09a6f8933bdf417a94b247d863a5c95dd7075c0c2d35eff4d57eb69d"),
          "staunton": (2237, "c38c641b9ed25782069825c074193a1c512909f356eb177d84e6991fb52bc97c")}


def _quotes(value, out):
    if isinstance(value, dict):
        for k, v in value.items():
            if k == "quote" and isinstance(v, str):
                out.append(v)
            else:
                _quotes(v, out)
    elif isinstance(value, list):
        for v in value:
            _quotes(v, out)
    return out


def _files(place):
    out = []
    for p in sorted((config.CURATED_DIR / "places" / "va" / place).glob("*.json")):
        try:
            out.append((p, Q.restore(json.loads(p.read_text(encoding="utf-8")), p)))   # withheld words, if here
        except ValueError:
            continue
    return out


def _held_back(files):
    """Whether every withheld quote of the files has its words (the evidence files are present)."""
    return all(q["restored"] for _, spec in files for q in Q.withheld_quotes(spec))


def test_the_researched_files_describe_the_place_not_the_drafting_and_keep_every_quote():
    """Caveats and source titles in the 60 researched files say nothing about the drafting (the verifier, the
    modeller, the research client or User-Agent, lexflow's index rows, a browser pane, "the research"), and every
    quote is as it was (the hash of all quotes, file by file)."""
    seen = 0
    for place, (n, digest) in QUOTES.items():
        files = _files(place)
        if len(files) != 27:
            pytest.skip("another workflow may be writing these files")
        if not _held_back(files):
            pytest.skip("the evidence files (data/evidence/) are not present here")
        qs = [q for _, spec in files for q in _quotes(spec, [])]
        assert (len(qs), hashlib.sha256(json.dumps(qs, ensure_ascii=False).encode()).hexdigest()) == (n, digest), place
        for path, spec in files:
            texts = list(spec.get("caveats") or []) + [s.get("title") for s in spec.get("sources") or []]
            left = P.drafting_left(f"{place}/{path.name}", texts, log=lambda *_: None)
            assert not left, (path.name, left)
            assert not re.search(r"Claude|browser pane|desktop browser", json.dumps(
                {k: v for k, v in spec.items() if k not in ("checks", "researched_by")}), re.I), path.name
            seen += 1
    assert seen == 81


def test_the_dc_caveats_describe_the_place():
    spec = json.loads((config.CURATED_DIR / "places" / "dc" / "washington.json").read_text(encoding="utf-8"))
    caveats = [c for a in spec["answers"].values() for c in a.get("caveats") or []]
    assert not any(re.search(r"\bthe research\b|lexflow did not verify", c) for c in caveats)
    assert any("not described here" in c for c in caveats)                    # the warning stays
    assert hashlib.sha256(json.dumps(_quotes(spec, []), ensure_ascii=False).encode()).hexdigest() == \
        "7247c69ae9cedf9f45cd9eb503be261ba508ece60d948e5e556dcfe9657cf7f1"


def test_pages_print_caveats_as_written_and_log_drafting_words(con, law, caplog):
    """Pages no longer cut drafting notes out of a caveat (that took reader warnings with them); they print it as
    the file words it, and log any drafting words left so the file can be reworded."""
    spec = _spec(caveats=["The form has no text layer; the verifier rendered it, so its quotes cannot be confirmed.",
                          "Fees change each July."],
                 sources=[{"url": "https://www.example-county.gov/dog", "title": "Dog licences (lexflow index row 3)"}])
    with caplog.at_level(logging.WARNING, logger="lexflow.places"):
        text = LX.render_local_process(con, GOV, {"process": "dog_license", "spec": spec})
    assert "so its quotes cannot be confirmed" in text and "  * Fees change each July." in text
    assert sum("describes the drafting" in r.getMessage() for r in caplog.records) == 2
