"""Credits on the Setup page: every step says which outside data, services, models and libraries it uses.

The second half pins the fixes from docs/design/verify-credits.md: the licences and links it found wrong, the
citations labelled as the maker's own wording or lexflow's format, the model credits that follow config, the
case-law step paced to CourtListener's limits, and the bpmn.io watermark left fully visible in the viewer.
"""
import importlib.metadata as md
import json
import re
from pathlib import Path
from urllib.parse import urlparse

import pytest

from lexflow import config
from lexflow.municipal import caselaw
from lexflow.pipeline import credits as C
from lexflow.pipeline import steps
from lexflow.pipeline.steps import COMPOSITE, STEPS
from lexflow.store import db

ROOT = Path(__file__).resolve().parents[1]
KEYS = {"name", "by", "licence", "url", "use", "licence_url", "cite", "cite_by", "note"}
NOT_ENDORSED = "Credit is not endorsement: the people and projects listed here have not reviewed lexflow."
POLICY = "https://free.law/membership/allowed-api-usage/"


def _all_steps():
    return [*STEPS.values(), *COMPOSITE.values()]


def _all_credits():
    return [c for s in _all_steps() for c in s.credits] + C.GENERAL


def _check(c: dict, where: str):
    assert set(c) <= KEYS, f"{where}: unknown keys {set(c) - KEYS}"
    for k in ("name", "by", "licence", "url", "use"):
        assert isinstance(c.get(k), str) and c[k].strip(), f"{where}: {k} missing"
    for k in ("cite", "note", "licence_url"):
        assert k not in c or (isinstance(c[k], str) and c[k].strip()), f"{where}: empty {k}"
    for k in ("url", "licence_url"):
        if k in c:
            u = urlparse(c[k])
            assert u.scheme == "https" and u.netloc, f"{where}: {c[k]} is not an https URL"
    # a citation always says whose wording it is; one without a citation has no label
    assert ("cite" in c) == ("cite_by" in c), f"{where}: cite and cite_by go together"
    assert c.get("cite_by", "lexflow") in C.CITE_BY, f"{where}: cite_by {c.get('cite_by')!r}"


def test_every_step_has_credits_or_an_empty_list_with_a_reason():
    for s in _all_steps():
        assert s.credits is not None, f"{s.id}: credits not filled in"
        assert isinstance(s.credits, list)
        if not s.credits:
            assert s.credits_note.strip(), f"{s.id}: an empty credits list needs credits_note to say why"


def test_every_credit_has_a_name_licence_and_https_url():
    for s in _all_steps():
        for c in s.credits:
            _check(c, f"{s.id}/{c.get('name')}")
        names = [c["name"] for c in s.credits]
        assert len(names) == len(set(names)), f"{s.id}: a credit is listed twice"
    assert C.GENERAL
    for c in C.GENERAL:
        _check(c, f"general/{c.get('name')}")
    names = [c["name"] for c in C.GENERAL]
    assert len(names) == len(set(names))


def test_conditions_the_makers_ask_for_are_shown():
    assert C.GEMMA3["note"] == ("Gemma is provided under and subject to the Gemma Terms of Use found at "
                                "ai.google.dev/gemma/terms")
    assert "Commercial use needs a licence from Vaquill AI" in C.OPEN_US_LAW["note"]
    assert any("watermark" in c.get("note", "") for c in C.GENERAL if c["name"] == "bpmn-js")
    js = (ROOT / "dashboard" / "app.js").read_text(encoding="utf-8")
    assert NOT_ENDORSED in js


def test_used_for_changes_only_the_use():
    c = C.used_for(C.WIKIDATA, "Items link to Wikidata", note="")
    assert c["use"] == "Items link to Wikidata" and "note" not in c and c["licence"] == C.WIKIDATA["licence"]
    assert C.WIKIDATA["use"] != c["use"] and "note" in C.WIKIDATA


def test_setup_api_returns_the_credits(con, monkeypatch):
    from fastapi.testclient import TestClient
    from lexflow.api import app as A
    monkeypatch.setattr(config, "JOB_RUNNER", False)
    offline = lambda: {"reachable": False, "models": []}  # noqa: E731 - no Ollama in tests
    monkeypatch.setattr(A, "ollama_state", offline)
    monkeypatch.setattr(steps, "ollama_state", offline)
    with TestClient(A.app) as client:
        body = client.get("/api/setup").json()
    by_id = {s["id"]: s for s in body["steps"]}
    assert set(by_id) == set(STEPS)
    for sid, s in by_id.items():
        assert s["credits"] == STEPS[sid].credits
        assert s["credits"] or s["credits_note"]
    assert by_id["statutes"]["credits"][0]["name"].startswith("Open US Law")
    assert by_id["statutes"]["credits"][0]["licence"].startswith("CC BY-NC 4.0")
    assert by_id["local"]["credits"] == [] and by_id["local"]["credits_note"]
    assert body["credits"] == C.GENERAL


# ------------------------------------------------------------- fixes from verify-credits.md
def test_pulp_is_mit_and_its_bundled_cbc_is_epl_1_0():
    assert C.PULP["licence"] == "MIT" and "BSD" not in C.PULP["licence"]
    # the EPL-1.0 is the bundled binaries' licence; the CBC README on the linked page gives EPL-2.0
    assert C.CBC["licence"].startswith("EPL-1.0") and "bundled" in C.CBC["licence"] and C.CBC["by"] == "COIN-OR"
    assert "EPL-2.0" in C.CBC["note"]
    # lexflow's requirements install PuLP; pm4py's metadata does not require it
    assert "installed with pm4py" not in C.CBC["use"] and "Needed by pm4py" not in C.PULP["use"]
    assert "requirements" in C.PULP["use"]
    req = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    assert re.search(r"^pulp<3\b", req, re.M)
    build = [c["name"] for c in STEPS["build"].credits]
    assert build.index("CBC") == build.index("PuLP") + 1
    try:
        dist = md.distribution("pulp")
    except md.PackageNotFoundError:
        pytest.skip("PuLP is not installed here")
    try:
        needs = [r for r in md.requires("pm4py") or [] if r.lower().startswith("pulp")]
        assert needs == [], needs
    except md.PackageNotFoundError:
        pass
    files = {str(f): f for f in dist.files or []}
    lic = next(f for name, f in files.items() if name.endswith(".dist-info/LICENSE"))
    assert "Permission is hereby granted, free of charge" in dist.locate_file(lic).read_text()   # the MIT licence
    coin = [f for name, f in files.items()
            if name.startswith("pulp/solverdir/cbc/") and name.endswith("coin-license.txt")]
    assert coin and all(dist.locate_file(f).read_text(errors="replace").startswith("Eclipse Public License - v 1.0")
                        for f in coin)


def test_courtlistener_shows_its_usage_restrictions_and_links_the_policy():
    cl = C.COURTLISTENER
    assert cl["licence_url"] == POLICY
    note = cl["note"]
    for must in ("commercial product", "for-profit or non-profit", "One account per person",
                 "API keys may not be shared", "5 requests a minute, 50 an hour and 125 a day", "linked"):
        assert must in note, must
    assert STEPS["cases"].credits == [cl]
    # the cases step runs without a token (caselaw.search sends one only when it is set); Ask needs one
    assert "Needs a CourtListener account" not in note
    assert "COURTLISTENER_TOKEN" in note and "was not checked" in note
    src = (ROOT / "lexflow" / "municipal" / "caselaw.py").read_text(encoding="utf-8")
    assert "if config.COURTLISTENER_TOKEN:" in src
    ask = " ".join((ROOT / "lexflow" / "ask" / "local.py").read_text(encoding="utf-8").split())
    assert "if not config.COURTLISTENER_TOKEN: return []" in ask


def test_citations_say_whose_wording_they_are():
    cited = {c["name"]: c for c in _all_credits() if "cite" in c}
    # only the Open US Law BibTeX was found to match the maker's own word for word
    assert {n for n, c in cited.items() if c["cite_by"] == "maker"} == {"Open US Law"}
    for name in ("LOCUS-v1", "nomic-embed-text v1.5", "Qwen3 1.7B", "Gemma 3 1B", "POWL", "SpiffWorkflow",
                 "pm4py", "2022 Census of Governments: Government Units Listing"):
        assert cited[name]["cite_by"] == "lexflow", name
    # unless a credit says otherwise, its citation is labelled lexflow's format
    assert C.credit("x", "x", "x", "https://x.org", "x", cite="c")["cite_by"] == "lexflow"
    with pytest.raises(ValueError):
        C.credit("x", "x", "x", "https://x.org", "x", cite="c", cite_by="exact")
    js = (ROOT / "dashboard" / "app.js").read_text(encoding="utf-8")
    assert 'c.cite_by === "maker"' in js and "lexflow's format" in js


def test_spiffworkflow_citation_has_the_authors_and_version_of_its_citation_cff():
    cite = C.SPIFFWORKFLOW["cite"]
    # CITATION.cff (sartography/SpiffWorkflow, read 10 October 2026): version 3.1.1, released 2025-03-04, these
    # authors in this order (one is listed with family-names "Jon"), and the concept DOI
    authors = ["Esswein, E.", "Abels, S.", "Funk, D.", "Jon, H.", "McDonald, K."]
    assert [cite.index(a) for a in authors] == sorted(cite.index(a) for a in authors)
    assert "(2025)" in cite and "Version 3.1.1" in cite and "https://doi.org/10.5281/zenodo.14966563" in cite


def test_or_later_licences_are_named_consistently():
    assert C.SPIFFWORKFLOW["licence"] == "LGPL-3.0-or-later"
    assert C.SEARXNG["licence"] == "AGPL-3.0-or-later"
    assert "GPL-2.0-or-later" in C.WIKIBASE_CLOUD["licence"]
    plain = {c["name"] for c in _all_credits() if re.search(r"\bA?L?GPL-\d\.\d(?!-or-later|-only)\b", c["licence"])}
    assert plain <= {"DokuWiki"}, plain          # DokuWiki's files say GPL 2 with no "or later"
    try:
        import SpiffWorkflow
    except ImportError:
        return
    header = (Path(SpiffWorkflow.__file__).parent / "workflow.py").read_text()[:1500]
    assert "or (at your option) any later version" in header


def test_moved_and_renamed_pages():
    assert C.POWL["url"] == "https://github.com/fit-process-mining/POWL"
    assert C.GOV_DIRECTORY["name"] == "Govdirectory" and C.GOV_DIRECTORY["url"] == "https://www.govdirectory.org/about/"
    assert "RF-RAND" not in C.OMG_SCHEMAS["licence"] and "patent" in C.OMG_SCHEMAS["note"]


def test_the_module_docstring_does_not_claim_every_credit_was_checked():
    doc = " ".join(C.__doc__.split())
    assert "Each one was checked" not in doc
    assert "The data, service and model credits were checked against the maker's own page" not in doc
    assert "package metadata only" in doc and "were not checked" in doc
    # models: only the default tags were checked; any other tag config names says so on the page
    assert "only the Ollama tags in ``MODELS``" in doc
    assert "not checked" in C.model_credit("other:7b", "x")["licence"].lower()
    # the terms the re-check found unread are named
    for unread in ("Hugging Face", "Turso", "Wikibase.cloud", "CourtListener's site terms", "DMN 1.3", "us-atlas"):
        assert unread in doc, unread
    assert NOT_ENDORSED in doc


def test_the_page_tells_links_apart_and_does_not_repeat_the_maker():
    js = (ROOT / "dashboard" / "app.js").read_text(encoding="utf-8")
    fn = js[js.index("function creditList"):js.index("function serviceCard")]
    assert '"aria-label"' in fn and "opens in a new tab" in fn
    assert "c.by.toLowerCase() !== String(c.name).toLowerCase()" in fn       # "Ollama (Ollama)" no more
    assert "c.licence_url" in fn


def test_searxng_is_credited_on_the_setup_page():
    assert any(c["name"] == "SearXNG" and c["licence"] == "AGPL-3.0-or-later" for c in C.GENERAL)


def test_open_us_law_does_not_fix_the_release_in_its_name():
    assert C.OPEN_US_LAW["name"] == "Open US Law"
    assert "v2026" not in C.OPEN_US_LAW["name"] and "release" in C.OPEN_US_LAW["note"]
    assert C.OPEN_US_LAW["cite_by"] == "maker"


def test_model_credits_follow_config():
    assert C.model_credit("qwen3:1.7b", "x")["name"] == "Qwen3 1.7B"
    assert C.model_credit("nomic-embed-text:latest", "x")["licence"] == "Apache-2.0"
    g = C.model_credit("gemma3:1b", "Scored")
    assert g["use"] == "Scored" and g["note"] == C.GEMMA3["note"]
    other = C.model_credit("llama3.2:3b", "Writes answers")
    assert other["name"] == "llama3.2:3b" and other["licence"].startswith("Not checked")
    assert other["url"] == "https://ollama.com/library/llama3.2" and "not checked" in other["note"]
    assert C.model_credit("hf.co/org/model-GGUF:Q4_K_M", "x")["url"] == "https://huggingface.co/org/model-GGUF"
    assert C.model_credit("someone/model", "x")["url"] == "https://ollama.com/someone/model"
    twice = C.model_credits([("qwen3:1.7b", "One"), ("qwen3:1.7b", "One"), ("qwen3:1.7b", "Two")])
    assert len(twice) == 1 and twice[0]["use"] == "One; two"
    assert C.QWEN3["use"] != "One; two"                       # the shared credit is not changed
    # the Setup steps name the models config names
    want = {C.model_credit(t, "x")["name"] for t in (config.EMBED_MODEL, config.MODEL_A, config.MODEL_B)}
    assert {c["name"] for c in STEPS["models"].credits} == {"Ollama"} | want
    assert C.model_credit(config.ASK_MODEL, "x")["name"] in {c["name"] for c in COMPOSITE["ask"].credits}


# --------------------------------------------------------------- CourtListener pacing
class Clock:
    def __init__(self, t=1_000_000.0):
        self.t, self.slept = t, []

    def __call__(self):
        return self.t

    def sleep(self, s):
        self.slept.append(s)
        self.t += s


def _pacer(tmp_path, clock):
    return caselaw.Pacer(path=tmp_path / "cl.json", clock=clock, sleep=clock.sleep)


def _within_limits(times):
    times = sorted(times)
    for window, cap, _ in caselaw.LIMITS:
        for i, t in enumerate(times):
            assert sum(1 for u in times[i:] if u - t < window) <= cap, (window, cap)


def test_limits_are_courtlisteners_documented_ones():
    caps = {w: n for w, n, _ in caselaw.LIMITS}
    assert caps[60.0] == 5 and caps[3600.0] == 50 and caps[86400.0] == 125


def test_wait_for_counts_each_window():
    assert caselaw.wait_for([], 100.0) == (0.0, "")
    need, why = caselaw.wait_for([50.0, 60.0, 70.0, 80.0, 90.0], 100.0)
    assert need == pytest.approx(10.0 + caselaw.MARGIN) and "5 requests a minute" in why   # 50 + 60 s + margin - 100
    assert caselaw.wait_for([50.0, 60.0, 70.0, 80.0, 90.0], 100.0, margin=0)[0] == pytest.approx(10.0)
    assert caselaw.wait_for([99.5], 100.0)[0] == pytest.approx(0.5)                # lexflow's own second: no margin
    assert caselaw.MARGIN > 0


def test_the_pacer_keeps_a_days_requests_within_every_limit(tmp_path):
    clock = Clock()
    p = _pacer(tmp_path, clock)
    sent = []
    for _ in range(125):
        p.acquire(caselaw.STEP_MAX_WAIT, log=lambda *_: None)
        sent.append(clock())
    _within_limits(sent)
    assert sent[-1] - sent[0] >= 2 * 3600                    # 125 requests need at least two hourly windows
    with pytest.raises(caselaw.RateLimited, match="125 requests a day"):
        p.acquire(caselaw.STEP_MAX_WAIT, log=lambda *_: None)
    clock.t = sent[0] + 86400.0 + caselaw.MARGIN + 1         # a day (and the margin) after the first, one more fits
    assert p.acquire(caselaw.STEP_MAX_WAIT, log=lambda *_: None) <= 1.0


def test_a_search_waits_a_minute_at_most_and_the_step_waits_out_the_hour(tmp_path):
    clock = Clock()
    p = _pacer(tmp_path, clock)
    for _ in range(50):
        p.acquire(caselaw.STEP_MAX_WAIT, log=lambda *_: None)
    with pytest.raises(caselaw.RateLimited, match="50 requests an hour"):
        p.acquire(log=lambda *_: None)                       # the default: what Ask's one search allows
    logs = []
    waited = p.acquire(caselaw.STEP_MAX_WAIT, log=logs.append)
    assert 60 < waited <= 3600 and logs and "50 requests an hour" in logs[0]


def test_processes_on_one_data_folder_share_the_allowance(tmp_path):
    clock = Clock()
    a, b = _pacer(tmp_path, clock), _pacer(tmp_path, clock)
    for _ in range(3):
        a.acquire(log=lambda *_: None)
    for _ in range(2):
        b.acquire(log=lambda *_: None)
    shared = json.loads((tmp_path / "cl.json").read_text())
    assert len(shared) == 5
    assert caselaw.wait_for(sorted(shared), clock())[0] > 50     # a sixth would wait for the minute window


def test_every_search_request_goes_through_the_pacer(con, monkeypatch):
    clock = Clock()
    pacer = caselaw.Pacer(clock=clock, sleep=clock.sleep)      # DATA_DIR is the test's temp folder
    monkeypatch.setattr(caselaw, "PACER", pacer)
    calls = []

    class Resp:
        status_code, headers = 200, {}

        def __init__(self, page):
            self.page = page

        def raise_for_status(self):
            pass

        def json(self):
            nxt = "https://www.courtlistener.com/next" if self.page == 1 else None
            return {"results": [{"cluster_id": self.page}], "next": nxt}

    def get(url, **kw):
        calls.append(clock())
        return Resp(len(calls))

    monkeypatch.setattr(caselaw.requests, "get", get)
    for ref in ("2.2-3704", "2.2-3705", "2.2-3706"):
        caselaw.search("va", ref, log=lambda *_: None, max_wait=caselaw.STEP_MAX_WAIT)
    assert len(calls) == 4                                     # two pages for the first ref, one for the others
    _within_limits(calls)
    assert (Path(config.DATA_DIR) / caselaw.PACE_FILE).exists()


def test_the_cases_step_goes_on_from_the_states_not_searched_yet(con, monkeypatch):
    rows = [{"state": st, "question": "records", "status": "found", "section": "1-1", "method": "seed",
             "updated_at": db.now()} for st in ("va", "md")]
    db.upsert(con, "located_law", rows)
    con.commit()
    searched = []

    def run(con, st, log=None, progress=None):
        searched.append(st)
        return {"sections": 1, "opinions": 0}

    monkeypatch.setattr(caselaw, "run", run)
    logs = []
    steps.run_cases(con, {}, logs.append, lambda p: None)
    assert sorted(searched) == ["md", "va"]
    searched.clear()
    steps.run_cases(con, {}, logs.append, lambda p: None)
    assert searched == [] and any("skipping 2 states" in m for m in logs)
    steps.run_cases(con, {"states": "all"}, logs.append, lambda p: None)     # 'all' is not a way round the skip
    assert searched == []
    steps.run_cases(con, {"force": True}, logs.append, lambda p: None)
    assert sorted(searched) == ["md", "va"]
    searched.clear()
    # a done state named is searched again only with Redo, as in the other steps (index, crawl)
    steps.run_cases(con, {"states": "va"}, logs.append, lambda p: None)
    assert searched == []
    steps.run_cases(con, {"states": "va", "force": True}, logs.append, lambda p: None)
    assert searched == ["va"]


def test_the_cases_step_states_its_real_cost():
    s = STEPS["cases"]
    assert "one request a second" not in s.cost
    for must in ("5 requests a minute", "50 an hour", "125 a day", "about four states an hour and ten a day",
                 "failed is searched again", "oldest search first"):
        assert must in s.cost, must
    assert "a few minutes a state" not in s.cost                 # 50 an hour is about four states an hour
    assert "force" in s.params
    assert "free to use" not in caselaw.__doc__ and "125 a day" in caselaw.__doc__
    assert POLICY in caselaw.__doc__
    doc = " ".join(steps.run_cases.__doc__.split())
    assert "goes on the next day from the states not redone yet" in doc and "recorded as done only when" in doc


# ------------------------------------------------------------------- the process viewer
def _css(html: str) -> str:
    css = "\n".join(re.findall(r"<style>(.*?)</style>", html, re.S))
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


def test_the_viewer_leaves_the_bpmn_io_watermark_alone_and_flags_its_cdn_links():
    html = (ROOT / "scripts" / "viewer_template.html").read_text(encoding="utf-8")
    assert "bjs-powered-by" not in _css(html)
    assert "fonts.googleapis.com" in html and "cdn.jsdelivr.net" in html     # still loaded, so still flagged
    comments = " ".join(re.findall(r"<!--(.*?)-->", html, re.S))
    assert "IP address" in comments and "TODO" in comments
    assert "Google Fonts" in comments and "jsdelivr" in comments.lower()


def test_the_built_viewer_has_the_same_fix():
    # out/viewer/lexipedia-viewer.html was edited to match the template (no rebuild); build_viewer.py would give
    # the same lines, since it only fills in the CSS and data placeholders
    path = ROOT / "out" / "viewer" / "lexipedia-viewer.html"
    if path.stat().st_dev != (ROOT / "scripts").stat().st_dev:
        # in the app container only lexflow/, scripts/, tests/ and the like are mounted from the checkout; out/ is
        # the image's own copy, built before this fix
        pytest.skip("out/ here is not the checkout's own folder")
    built = path.read_text(encoding="utf-8")
    template = (ROOT / "scripts" / "viewer_template.html").read_text(encoding="utf-8")
    assert "bjs-powered-by" not in _css(built) and "opacity: .55" not in built
    for part in ("No rule may touch .bjs-powered-by", "TODO (privacy)", "send every viewer's IP address"):
        assert part in built, part
    foot = lambda h: re.search(r"<footer>(.*?)</footer>", h, re.S).group(1)  # noqa: E731
    assert foot(built) == foot(template)


def test_the_viewer_does_not_present_locus_text_as_citable():
    template = (ROOT / "scripts" / "viewer_template.html").read_text(encoding="utf-8")
    foot = " ".join(re.search(r"<footer>(.*?)</footer>", template, re.S).group(1).split())
    assert "not the official text" in foot and "never to cite it" in foot and "machine-labelled" in foot
    # the LOCUS credit no longer says, without qualification, that LOCUS is never cited anywhere
    assert "this step uses it to find law, never to cite it" in C.LOCUS["use"]
    assert "gold.py" in C.LOCUS["note"] and "viewer" in C.LOCUS["note"]
    assert "this step uses it to find law, never to cite it" in STEPS["locus"].why


# ------------------------------------------------------------------- the research note
def test_the_research_note_has_no_stale_lines():
    note = (ROOT / "docs" / "design" / "credits-research.md").read_text(encoding="utf-8")
    assert "Gov Directory" not in note
    assert "github.com/humam-kourani/POWL" not in note and "github.com/fit-process-mining/POWL" in note
    pulp = next(line for line in note.splitlines() if line.startswith("| PuLP |"))
    assert "| MIT (" in pulp and "BSD |" not in pulp
    assert "Each entry was checked on 10 October 2026 against the maker's own page" not in note
    # licences the makers grant "or later" are named that way
    for plain in (r"\*\*AGPL-3\.0\*\*", r"\*\*LGPL-3\.0\*\*", r"Wikibase software: GPL-2\.0 ",
                  r"\(AGPL-3\.0\)", r"LGPL-3\.0\)", r"\bare AGPL-3\.0\.", r"is LGPL-3\.0,", r"is AGPL-3\.0,"):
        assert not re.search(plain, note), plain
    # the old one-request-a-second pacing is described as the past, not as what the step does now
    finding = next(p for p in note.split("\n") if p.startswith("1. **CourtListener"))
    assert "sleeps 1 s between requests" not in finding and "`caselaw.py` now paces every request" in finding
