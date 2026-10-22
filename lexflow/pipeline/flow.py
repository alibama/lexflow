"""The Pipeline page's payload (``GET /api/pipeline``): lexflow drawn as a Petri net.

Places are stores holding tokens (counts): the questions people ask, the statute files, the statute index, the law
located, the researched local processes, the draft maps, the quote-matched processes, the coverage test, the benefit
programs, what is ready to push, the Wikibase, the wiki, the shared database, and the compute pool underneath.
Transitions are the jobs that move tokens between them: one per step of the registry (``lexflow.pipeline.steps``)
that does, the external writers among them, each with the places it reads and writes, its status from the jobs
table, the work waiting for it and the actions it offers (a dry run where the step has one, a run for a local step,
and for the Wikibase push the chained lint, pass 1 and pass 2 behind a confirmation of the dry run's numbers).

The counts are cached for 60 s, and dropped as soon as a job finishes; the job statuses are read fresh on every
call, so a running job's progress shows without waiting for the cache.  The live Wikibase's item count is read in
the background at most every ten minutes and fails soft.  Logs in the jobs directory written in the last ten
minutes that belong to no dashboard job are listed by name only: other work running in the container.
"""
from __future__ import annotations

import json
import sqlite3
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

from .. import config
from ..store import db
from . import steps as ST

TTL = 60                      # seconds the counts are kept
LIVE_TTL = 600                # seconds between reads of the live Wikibase's item count
OTHER_WORK_MINUTES = 10
_LOCK = threading.Lock()
_CACHE: dict = {}
_LIVE: dict = {"at": 0.0, "value": None, "busy": False}
_PLAN: dict = {}

# ------------------------------------------------------------------------------------------------ the net
# Places: label, one-line meaning, the page that lists them, and the cell they are drawn in (col: sources 0,
# index and research 1, drafts 2, verified 3, ready 4, published 5; row: top to bottom).  compute is the band
# underneath.
PLACES: dict[str, dict] = {
    "questions": {"label": "Questions", "col": 0, "row": 0, "href": "#/ask",
                  "meaning": "Questions people ask: typed on the Ask page, and the coverage test's questions"},
    "sources": {"label": "Statute files", "col": 0, "row": 2, "href": "#/setup",
                "meaning": "Each state's official statute file (Open US Law), downloaded"},
    "index": {"label": "Statute index", "col": 1, "row": 1, "href": "#/map?layer=index",
              "meaning": "Sections searchable by full text, per state and per country"},
    "located": {"label": "Law located", "col": 1, "row": 2.75, "href": "#/processes",
                "meaning": "The sections found for the built-in questions, per state"},
    "local": {"label": "Local research", "col": 1, "row": 4, "href": "#/places",
              "meaning": "Local processes researched from a place's official pages, loaded from the research files"},
    "drafts": {"label": "Draft maps", "col": 2, "row": 0.6, "href": "#/processes",
               "meaning": "Process maps drafted once: asked answers with a map, and single-extraction state models"},
    "coverage": {"label": "Coverage", "col": 2, "row": 3.4, "href": "#/coverage",
                 "meaning": "The latest coverage test: question x state cells answered adequately"},
    "verified": {"label": "Quote-matched", "col": 3, "row": 2, "href": "#/processes",
                 "meaning": "Processes whose quotes match the statute: reviewed or agreed state models, checked local "
                            "processes"},
    "benefits": {"label": "Benefit programs", "col": 3, "row": 4, "href": "#/retirement",
                 "meaning": "Public pension systems and the governments they cover (retirement benefits)"},
    "ready": {"label": "Ready to push", "col": 4, "row": 1, "href": "#/pipeline?open=wikibase",
              "meaning": "Graph items whose content differs from what the Wikibase holds, less those the lint holds"},
    "wikibase": {"label": "On the Wikibase", "col": 5, "row": 0.4, "href": "#/query",
                 "meaning": "Items lexflow has written to lexipedia.wikibase.cloud"},
    "wiki": {"label": "On the wiki", "col": 5, "row": 2, "href": "#/processes",
             "meaning": "Pages on the Lexipedia wiki (lexipedia.xyz, the lexflow: namespace)"},
    "turso": {"label": "Shared database", "col": 5, "row": 3.4, "href": "#/data",
              "meaning": "Rows pushed to the shared Turso database for other copies to pull"},
    "compute": {"label": "Compute pool", "band": True, "href": "#/compute",
                "meaning": "The model servers the model-using jobs send work to"},
}

# Transitions: the step behind each, the places it reads and writes, where it is drawn, and whether it sends work
# to the compute pool.  ``mode`` splits the wikibase step into its plan (dry runs) and its push (real runs).
TRANSITIONS: list[dict] = [
    {"id": "statutes", "step": "statutes", "label": "Download statutes", "reads": [], "writes": ["sources"],
     "col": -0.5, "row": 2},
    {"id": "index", "step": "index", "label": "Index statutes", "reads": ["sources"], "writes": ["index"],
     "col": 0.5, "row": 1.0},
    {"id": "regulations", "step": "regulations", "label": "Index regulations", "reads": ["sources"],
     "writes": ["index"], "col": 0.5, "row": 1.9},
    {"id": "locate", "step": "locate", "label": "Locate the law", "reads": ["sources"], "writes": ["located"],
     "col": 0.5, "row": 2.75},
    {"id": "local", "step": "local", "label": "Load local research", "reads": [], "writes": ["local"],
     "col": 0.5, "row": 4},
    {"id": "ask", "step": "ask", "label": "Answer questions", "reads": ["questions", "index"], "writes": ["drafts"],
     "col": 1.5, "row": 0.3, "model": True},
    {"id": "build", "step": "build", "label": "Build state models", "reads": ["located"],
     "writes": ["drafts", "verified"], "col": 1.5, "row": 1.95, "model": True},
    {"id": "coverage", "step": "coverage", "label": "Coverage test", "reads": ["questions", "index", "wikibase"],
     "writes": ["coverage", "drafts"], "col": 1.5, "row": 3.4, "model": True},
    {"id": "plan", "step": "wikibase", "mode": "dry", "label": "Lint and plan", "reads": ["verified", "local"],
     "writes": ["ready"], "col": 3.5, "row": 1.25, "model": "optional"},
    {"id": "wikibase", "step": "wikibase", "mode": "real", "label": "Push to Wikibase", "reads": ["ready"],
     "writes": ["wikibase"], "col": 4.5, "row": 0.7},
    {"id": "publish", "step": "publish", "label": "Publish the wiki", "reads": ["verified"], "writes": ["wiki"],
     "col": 4.5, "row": 2},
    {"id": "sync", "step": "sync", "label": "Share (Turso)", "reads": ["verified"], "also": ["drafts", "local"],
     "writes": ["turso"], "col": 4.5, "row": 3.4},
]
# ``also``: places a transition reads that the chart leaves undrawn (long arrows that would cross the net); the
# side panel lists them with the rest
QUICKSTART = {"governments", "statutes", "locate", "contacts", "crawl", "local", "build", "score"}
RUN_TEXT = ("states", "places", "questions")
RUN_FLAGS = ("force", "no_llm", "regulations", "full")


def clear() -> None:
    """Forget every cache (the tests)."""
    with _LOCK:
        _CACHE.clear()
        _PLAN.clear()
        _LIVE.update(at=0.0, value=None, busy=False)


def _now() -> float:
    return time.time()


def _iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _secs(a: str | None, b: str | None) -> float | None:
    try:
        fa = datetime.strptime(a, "%Y-%m-%dT%H:%M:%SZ")
        fb = datetime.strptime(b, "%Y-%m-%dT%H:%M:%SZ")
        return max(0.0, (fb - fa).total_seconds())
    except (TypeError, ValueError):
        return None


def _has(con, table: str) -> bool:
    return bool(db.scalar(con, "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", table))


def _n(con, sql: str, *args) -> int:
    try:
        return int(db.scalar(con, sql, *args, default=0) or 0)
    except sqlite3.Error:
        return 0


def _safe(fn, *args) -> dict:
    try:
        return fn(*args)
    except Exception as e:  # noqa: BLE001 - one store's count failing never fails the page
        return {"count": None, "detail": f"could not count: {type(e).__name__}: {str(e)[:160]}", "error": True}


# --------------------------------------------------------------------------------------------- the places
def _questions(con) -> dict:
    from ..ask import coverage as CV
    asked = {r["id"] for r in db.rows(con, "SELECT id FROM asked_questions")} if _has(con, "asked_questions") else set()
    cov = {q["id"] for q in CV.questions()}
    unanswered = len(asked - {r["question_id"] for r in db.rows(con, "SELECT DISTINCT question_id FROM asked_answers")})
    return {"count": len(asked | cov), "parts": {"asked": len(asked), "coverage": len(cov), "both": len(asked & cov),
                                                 "unanswered": unanswered},
            "detail": f"{len(asked):,} asked on the Ask page · {len(cov):,} in the coverage test"
                      + (f" ({len(asked & cov):,} in both)" if asked & cov else "")}


def _sources(con) -> dict:
    c = {r["status"]: r["n"] for r in db.rows(con, "SELECT status, count(*) AS n FROM statute_files GROUP BY status")}
    have, missing = c.get("downloaded", 0), c.get("not-in-release", 0)
    return {"count": have, "parts": {"downloaded": have, "not_in_release": missing},
            "detail": f"{have:,} states downloaded" + (f" · {missing} not in the current release" if missing else "")}


def _index(con) -> dict:
    from ..municipal import map_layers as ML
    from ..municipal import states as S
    juris: dict[str, dict] = {}
    for st, corpus, n in ML._index_sizes():
        country = st in S.COUNTRY
        e = juris.setdefault(st, {"code": st, "kind": "country" if country else "state",
                                  "name": S.COUNTRY[st]["name"] if country else S.NAME.get(st, st.upper()),
                                  "sections": 0, "regulations": 0})
        e["sections" if corpus == "statutes" else "regulations" if corpus == "regulations" else corpus] = n
    us = [e for e in juris.values() if e["kind"] == "state"]
    intl = sorted((e for e in juris.values() if e["kind"] == "country"), key=lambda e: -e["sections"])
    us_sec = sum(e["sections"] for e in us)
    us_reg = sum(e["regulations"] for e in us)
    intl_sec = sum(e["sections"] for e in intl)
    states = sum(1 for e in us if e["sections"])
    return {"count": us_sec + intl_sec,
            "parts": {"us": {"states": states, "sections": us_sec, "regulations": us_reg,
                             "regulation_states": sum(1 for e in us if e["regulations"])},
                      "international": [{k: e[k] for k in ("code", "name", "sections")} for e in intl],
                      "jurisdictions": sorted(juris.values(), key=lambda e: (e["kind"], -e["sections"]))},
            "detail": f"US: {us_sec:,} sections in {states} states" + (f" (+{us_reg:,} regulation sections)" if us_reg
                                                                        else "")
                      + (" · international: " + ", ".join(f"{e['name']} {e['sections']:,}" for e in intl) if intl
                         else " · no country indexed yet")}


def _located(con) -> dict:
    c = {r["status"]: r["n"] for r in db.rows(con, "SELECT status, count(*) AS n FROM located_law GROUP BY status")}
    found = c.get("found", 0)
    return {"count": found, "parts": c,
            "detail": f"{found:,} state and question pairs found" + (f" · {c['not-found']} not found" if c.get(
                "not-found") else "") + (f" · {c['no-statutes']} without statutes" if c.get("no-statutes") else "")}


def _local(con) -> dict:
    from ..municipal import places as P
    n = _n(con, "SELECT count(*) FROM place_processes")
    ok = _n(con, "SELECT coalesce(sum(verified), 0) FROM place_processes")
    govs = _n(con, "SELECT count(DISTINCT gov_id) FROM place_processes")
    files = len(P.process_files())
    return {"count": n, "parts": {"processes": n, "verified": ok, "localities": govs, "files": files,
                                  "unloaded": max(0, files - n), "unverified": n - ok},
            "detail": f"{ok:,} of {n:,} quote-checked · {govs:,} localities · {files:,} research files"}


def _drafts(con) -> dict:
    maps = _n(con, "SELECT count(DISTINCT question_id || char(1) || target) FROM asked_answers WHERE bpmn IS NOT NULL")
    single = _n(con, "SELECT count(*) FROM process_models WHERE tier='single'")
    return {"count": maps + single, "parts": {"asked_maps": maps, "single_models": single},
            "detail": f"{maps:,} asked answers with a draft map · {single:,} single-extraction state models"}


def _verified(con) -> dict:
    tiers = {r["tier"]: r["n"] for r in db.rows(con, "SELECT tier, count(*) AS n FROM process_models GROUP BY tier")}
    pp = _n(con, "SELECT count(*) FROM place_processes WHERE verified=1")
    rv, ag = tiers.get("reviewed", 0), tiers.get("agreed", 0)
    return {"count": rv + ag + pp, "parts": {"reviewed": rv, "agreed": ag, "local_verified": pp},
            "detail": f"{rv:,} reviewed and {ag:,} agreed state models · {pp:,} quote-checked local processes"}


def _coverage(con) -> dict:
    from ..ask import coverage as CV
    run = CV.latest_run(con)
    if not run:
        return {"count": None, "parts": {"run": None}, "detail": "No coverage run yet", "gaps": 0}
    cells: dict[tuple, str] = {}
    for r in db.rows(con, """SELECT qid, state, gov_id, verdict,
                                    coalesce(json_extract(probe, '$.drafts_only'), 0) AS drafts_only
                             FROM coverage_runs WHERE run_id=? ORDER BY arm = 'coverage' DESC""", run):
        k = (r["qid"], r["state"], r["gov_id"] or "")
        if k not in cells:
            v = r["verdict"] or "none"
            cells[k] = "draft" if v == "partial" and r["drafts_only"] else v
    counts = {v: sum(1 for x in cells.values() if x == v) for v in ("adequate", "partial", "draft", "none")}
    states = sorted({k[1] for k in cells})
    gaps = len(CV.gap_cells(con, run, states))
    return {"count": counts["adequate"], "parts": {"run": run, "cells": len(cells), **counts, "gaps": gaps,
                                                    "states": states},
            "detail": f"run {run}: {counts['adequate']} adequate · {counts['partial']} partial · {counts['draft']} on "
                      f"drafts · {counts['none']} none, of {len(cells)} cells", "gaps": gaps}


def _benefits(con) -> dict | None:
    if not _has(con, "pension_systems"):
        return None
    n = _n(con, "SELECT count(*) FROM pension_systems")
    govs = _n(con, "SELECT count(DISTINCT gov_id) FROM pension_coverage") if _has(con, "pension_coverage") else 0
    fx = config.ROOT / "fixtures" / "benefits"
    files = len(list(fx.rglob("*.json"))) if fx.is_dir() else 0
    return {"count": n, "parts": {"systems": n, "governments": govs, "fixtures": files},
            "detail": f"{n:,} public pension systems (Census) · {govs:,} governments covered"
                      + (f" · {files} program files" if files else "")}


def _wikibase(con, live: dict | None) -> dict:
    n = _n(con, "SELECT count(*) FROM wikibase_items")
    live = live or {}
    if live.get("count") is not None:
        lv = f"the live site counts {live['count']:,} items ({live.get('source')}, read {live.get('checked_at')})"
    elif live.get("error"):
        lv = f"the live count could not be read ({live['error']})"
    else:
        lv = "the live count is being read"
    return {"count": n, "parts": {"recorded": n, "live": live}, "external": config.WIKIBASE_URL,
            "detail": f"{n:,} recorded here · {lv}"}


def _wiki(con) -> dict:
    models = sum(1 for r in db.rows(con, "SELECT stages FROM process_models WHERE tier IN ('reviewed','agreed')")
                 if (db.loads(r["stages"], {}) or {}).get("published"))
    asked = _n(con, "SELECT count(DISTINCT question_id || char(1) || target) FROM asked_answers WHERE published=1")
    ok = bool(config.DOKUWIKI_URL and config.DOKUWIKI_TOKEN)
    last = next((j for j in db.rows(con, "SELECT id, args, finished_at FROM jobs WHERE step='publish' AND status='done' "
                                         "ORDER BY id DESC LIMIT 20")
                 if not (db.loads(j["args"], {}) or {}).get("dry_run")), None)
    return {"count": models + asked, "parts": {"models": models, "asked": asked, "configured": ok,
                                               "last_publish": last and {"job": last["id"], "at": last["finished_at"]}},
            "external": config.DOKUWIKI_URL or None,
            "detail": f"{models:,} state models marked published · {asked:,} asked answers marked for the wiki"
                      + (f" · last publish job #{last['id']} {last['finished_at']}" if last else "")
                      + ("" if ok else " · DOKUWIKI_URL or DOKUWIKI_TOKEN not set")}


def _turso(con) -> dict:
    last = db.one(con, "SELECT direction, rows, ok, finished_at FROM sync_log WHERE direction='push' "
                       "ORDER BY id DESC LIMIT 1") if _has(con, "sync_log") else None
    if not config.TURSO_URL:
        return {"count": None, "parts": {"configured": False}, "detail": "TURSO_DATABASE_URL not set"}
    if not last:
        return {"count": 0, "parts": {"configured": True}, "detail": "configured; never pushed"}
    return {"count": last["rows"], "parts": {"configured": True, **last},
            "detail": f"last push {last['finished_at']}: {last['rows']:,} rows" + ("" if last["ok"] else " (failed)")}


def _compute(_con) -> dict:
    from ..compute import api as CA
    snap = CA.snapshot(limit=1)
    t = snap.get("totals") or {}
    return {"count": t.get("online"), "parts": {"pool": snap.get("pool"), **t},
            "detail": f"{t.get('online', 0)} of {t.get('nodes', 0)} nodes online · {t.get('busy', 0)} of "
                      f"{t.get('slots', 0)} slots busy" + ("" if snap.get("pool") else " · no pool: one Ollama")}


# ------------------------------------------------------------------------------------- push plan and lint
def plan_info(out_dir: Path) -> dict | None:
    """What push-plan.json in ``out_dir`` says, read once per change of the file: its numbers, and the keys it
    would write (``_keys``, kept out of the payload)."""
    from ..publish import push as P
    p = out_dir / P.PLAN_NAME
    try:
        st = p.stat()
    except OSError:
        return None
    key = (str(p), st.st_mtime_ns, st.st_size)
    with _LOCK:
        if _PLAN.get("key") == key:
            return _PLAN["value"]
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        return {"path": str(p), "error": f"{type(e).__name__}: {str(e)[:120]}", "_keys": set()}
    writes = d.get("writes") or []
    keys = {w.get("key") for w in writes if w.get("kind") != "property" and w.get("action") in ("create", "update",
                                                                                                   "clear")}
    info = {"path": str(p), "generated": d.get("generated"), "dry_run": d.get("dry_run"), "pass": d.get("pass"),
            "items": d.get("items"), "states": d.get("states"), "drafts": d.get("drafts"), "resume": d.get("resume"),
            "live": d.get("live"), "creates": d.get("creates"), "updates": d.get("updates"),
            "held_skipped": len(d.get("held_skipped") or ()), "dropped_snaks": d.get("dropped_snaks"),
            "failures_by_code": d.get("failures_by_code") or {}, "api_writes": d.get("api_writes"),
            "would_write": len(keys), "_keys": keys}
    with _LOCK:
        _PLAN.update(key=key, value=info)
    return info


def lint_info(out_dir: Path) -> dict | None:
    from ..publish import push as P
    r = P.read_lint(out_dir / P.LINT_NAME)
    if r is None:
        return None
    return {"path": str(out_dir / P.LINT_NAME), "generated": r.get("generated"), "items": r.get("items"),
            "new": r.get("new"), "held_count": r.get("held_count", len(r.get("held") or ())),
            "held_by_kind": r.get("held_by_kind") or {}, "findings_by_code": r.get("findings_by_code") or {},
            "_held": P.held_keys(r)}


def _changed_since(con, since: str | None) -> int:
    """Rows of what the graph is built from written after ``since``: a hint that a plan is out of date."""
    if not since:
        return 0
    return sum(_n(con, f"SELECT count(*) FROM {t} WHERE updated_at > ?", since)
               for t in ("process_models", "place_processes", "case_law", "wikibase_items") if _has(con, t))


def _ready(con, plan: dict | None, lint: dict | None) -> dict:
    held = (lint or {}).get("_held") or set()
    if not plan or plan.get("error"):
        return {"count": None, "parts": {"plan": None},
                "detail": "run a dry run to count" + (f" ({plan['error']})" if plan and plan.get("error") else "")}
    if not plan.get("dry_run"):
        return {"count": None, "parts": {"plan": "real"},
                "detail": f"a real push wrote the last plan ({plan.get('generated')}): run a dry run to count what is "
                          "left"}
    keys = plan.get("_keys") or set()
    n = len(keys - held)
    changed = _changed_since(con, plan.get("generated"))
    return {"count": n, "parts": {"would_write": len(keys), "held": len(keys & held), "lint_held": len(held),
                                  "plan_generated": plan.get("generated"), "changed_since": changed},
            "detail": f"from the dry run of {plan.get('generated')}: {n:,} items to create or update"
                      + (f", {len(held):,} held by the lint" if held else "")
                      + (f" · {changed:,} rows changed since: the count may be out of date" if changed else "")}


# -------------------------------------------------------------------------------- the live Wikibase count
def _fetch_live_count() -> tuple[int, str]:
    """The live site's item count, read only: the query service's count of items, else the wiki's content-page
    count (siteinfo statistics, which counts items among other pages)."""
    from ..publish import ids as I
    headers = {"Accept": "application/sparql-results+json", "User-Agent": I.USER_AGENT}
    q = "PREFIX wikibase: <http://wikiba.se/ontology#>\nSELECT (COUNT(?i) AS ?n) WHERE { ?i a wikibase:Item }"
    try:
        r = requests.post(I.ENDPOINT, data={"query": q}, headers=headers, timeout=8)
        r.raise_for_status()
        return int(r.json()["results"]["bindings"][0]["n"]["value"]), "query service"
    except (requests.RequestException, ValueError, KeyError, IndexError) as first:
        try:
            r = requests.get(config.WIKIBASE_URL.rstrip("/") + "/w/api.php", timeout=8,
                             params={"action": "query", "meta": "siteinfo", "siprop": "statistics", "format": "json"},
                             headers={"User-Agent": I.USER_AGENT})
            r.raise_for_status()
            return int(r.json()["query"]["statistics"]["articles"]), "content pages"
        except (requests.RequestException, ValueError, KeyError) as e:
            raise RuntimeError(f"{type(first).__name__} from the query service, {type(e).__name__} from the API") from e


def live_items(fetch=None, wait: bool = False) -> dict | None:
    """The live count, cached ten minutes; a stale value is refreshed in the background (``wait`` refreshes now)."""
    fetch = fetch or _fetch_live_count

    def refresh():
        try:
            n, source = fetch()
            val = {"count": n, "source": source, "error": None, "checked_at": db.now()}
        except Exception as e:  # noqa: BLE001 - fails soft: the page says the count could not be read
            val = {"count": None, "source": None, "error": str(e)[:160] or type(e).__name__, "checked_at": db.now()}
        with _LOCK:
            _LIVE.update(at=_now(), value=val, busy=False)
    with _LOCK:
        stale = _now() - _LIVE["at"] >= LIVE_TTL
        start = stale and not _LIVE["busy"]
        if start:
            _LIVE["busy"] = True
    if start:
        if wait:
            refresh()
        else:
            threading.Thread(target=refresh, daemon=True, name="lexflow-live-count").start()
    return _LIVE["value"]


# -------------------------------------------------------------------------------------------- the jobs
def _jobs(con) -> list[dict]:
    rows = db.rows(con, "SELECT id, step, args, status, progress, message, created_at, started_at, finished_at "
                        "FROM jobs ORDER BY id DESC LIMIT 600")
    for r in rows:
        r["args"] = db.loads(r["args"], {}) or {}
    return rows


def _real(j: dict) -> bool:
    a = j["args"]
    if j["step"] == "wikibase":
        # before ``really`` (the v1 loader's jobs, such as job 77) ``dry_run: false`` was a real write
        return (bool(a.get("really")) and not a.get("dry_run")) or ("really" not in a and a.get("dry_run") is False)
    if j["step"] == "publish":
        return not a.get("dry_run")
    return True


def _belongs(j: dict, t: dict) -> bool:
    if j["step"] != t["step"]:
        return False
    if t.get("mode") == "dry":
        return not _real(j)
    if t.get("mode") == "real":
        return _real(j)
    return True


def _brief(j: dict | None, via: str | None = None) -> dict | None:
    if not j:
        return None
    end = j["finished_at"] or (db.now() if j["status"] == "running" else None)
    return {"id": j["id"], "step": j["step"], "status": j["status"], "progress": j["progress"],
            "message": (j["message"] or "")[:300], "created_at": j["created_at"], "started_at": j["started_at"],
            "finished_at": j["finished_at"], "seconds": _secs(j["started_at"], end), "real": _real(j),
            "args": {k: v for k, v in j["args"].items() if v not in (None, "", False)}, "via": via}


def _status(jobs: list[dict], t: dict) -> dict:
    mine = [j for j in jobs if _belongs(j, t)]
    active = next((j for j in mine if j["status"] in ("running", "queued")), None)
    last = next((j for j in mine if j["status"] in ("done", "failed", "cancelled")), None)
    via = None
    if active is None and t["step"] in QUICKSTART:
        active = next((j for j in jobs if j["step"] == "quickstart" and j["status"] in ("running", "queued")), None)
        via = "quickstart" if active else None
    return {"state": active["status"] if active else last["status"] if last else "never",
            "active": _brief(active, via), "last": _brief(last)}


def other_work(con, minutes: int = OTHER_WORK_MINUTES) -> list[dict]:
    """Log files in the jobs directory written in the last ``minutes`` that belong to no dashboard job (``<id>.log``
    of a jobs row): names only."""
    d = config.JOBS_DIR
    if not d.is_dir():
        return []
    known = {str(r["id"]) for r in db.rows(con, "SELECT id FROM jobs")}
    now = _now()
    out = []
    for p in d.glob("*.log"):
        try:
            m = p.stat().st_mtime
        except OSError:
            continue
        if now - m > minutes * 60 or (p.stem.isdigit() and p.stem in known):
            continue
        out.append({"name": p.name, "modified": _iso(m), "ago_s": int(max(0, now - m))})
    return sorted(out, key=lambda x: x["ago_s"])


# ----------------------------------------------------------------------------------- work and actions
def _step_waiting(fn, con, what: str) -> dict:
    s = fn(con)
    left = max(0, (s.get("total") or 0) - (s.get("done") or 0))
    return {"count": left, "text": f"{left:,} {what}" if left else f"nothing waiting ({s.get('detail')})"}


def _waiting(con, places: dict, wb: dict, pub: dict) -> dict[str, dict]:
    def one(fn, *a):
        try:
            return fn(*a)
        except Exception as e:  # noqa: BLE001
            return {"count": None, "text": f"could not count: {type(e).__name__}"}
    out = {
        "statutes": one(_step_waiting, ST.st_statutes, con, "states not downloaded yet"),
        "index": one(_step_waiting, ST.st_index, con, "downloaded states not searchable yet"),
        "regulations": one(_step_waiting, ST.st_regulations, con, "regulations files not indexed yet"),
        "locate": one(_step_waiting, ST.st_locate, con, "state and question pairs not searched yet"),
        "build": one(_step_waiting, ST.st_build, con, "located pairs without a model yet"),
    }
    lp = (places.get("local") or {}).get("parts") or {}
    n = (lp.get("unloaded") or 0) + (lp.get("unverified") or 0)
    out["local"] = {"count": n, "text": f"{lp.get('unloaded', 0):,} research files not loaded · "
                                        f"{lp.get('unverified', 0):,} loaded processes not quote-checked"}
    qp = (places.get("questions") or {}).get("parts") or {}
    out["ask"] = {"count": qp.get("unanswered"), "text": f"{qp.get('unanswered', 0):,} asked questions without an "
                                                       "answer"}
    gaps = (places.get("coverage") or {}).get("gaps")
    out["coverage"] = {"count": gaps, "text": f"{gaps:,} gap cells in the latest run (none, or partial without steps "
                                              "or who)" if gaps is not None else "no coverage run yet"}
    rec = wb.get("dry_run")
    plan = wb.get("plan") or {}
    ch = _changed_since(con, (rec or plan).get("generated")) if (rec or plan) else None
    out["plan"] = {"count": ch, "text": (f"{ch:,} rows of the graph's inputs changed since the last dry run "
                                         f"({(rec or plan).get('generated')})" if ch else
                                         f"nothing changed since the last dry run ({(rec or plan).get('generated')})")
                   if (rec or plan) else "no dry run yet"}
    rd = places.get("ready") or {}
    out["wikibase"] = {"count": rd.get("count"), "text": rd.get("detail") or ""}
    try:
        s = ST.st_publish(con)
        left = max(0, (s.get("total") or 0) - (s.get("done") or 0))
        out["publish"] = {"count": left if s["status"] != "optional" else None,
                          "text": f"{left:,} reviewed or agreed models not on the wiki yet" if s["status"] != "optional"
                          else s.get("detail")}
    except Exception as e:  # noqa: BLE001
        out["publish"] = {"count": None, "text": f"could not count: {type(e).__name__}"}
    tp = (places.get("turso") or {})
    out["sync"] = {"count": None, "text": tp.get("detail") or ""}
    return out


def _actions(t: dict) -> list[dict]:
    step = ST.STEPS.get(t["step"]) or ST.COMPOSITE.get(t["step"])
    tid = t["id"]
    if tid == "ask":
        return [{"kind": "link", "label": "Ask a question", "href": "#/ask"}]
    if tid == "coverage":
        return [{"kind": "run", "label": "Run the coverage test", "args": {"arm": "coverage"},
                 "params": ["states", "questions", "force"]},
                {"kind": "run", "label": "Fill the gap cells", "args": {"fill": True}, "params": ["states"]},
                {"kind": "link", "label": "Coverage matrix", "href": "#/coverage"}]
    if tid in ("plan", "wikibase"):
        dry = {"kind": "dry_run", "label": "Dry run: lint → plan", "args": {"passes": "1,2"},
               "params": ["states", "drafts", "full", "single_pass"]}
        if tid == "plan":
            return [dry]
        return [dict(dry, label="Dry run first: lint → plan"),
                {"kind": "push", "label": "Push: lint → pass 1 → pass 2", "confirm": "wikibase",
                 "args": {"really": True, "passes": "1,2", "skip_held": True}, "params": ["bot"]}]
    if tid == "publish":
        return [{"kind": "dry_run", "label": "Dry run", "args": {"dry_run": True}, "params": []},
                {"kind": "publish", "label": "Publish", "confirm": "publish", "args": {}}]
    if tid == "sync":
        return [{"kind": "link", "label": "Data & sync", "href": "#/data"}]
    if step is None or step.run is None:
        return []
    return [{"kind": "run", "label": "Run", "args": {},
             "params": [p for p in step.params if p in RUN_TEXT or p in RUN_FLAGS]}]


# ----------------------------------------------------------------------------------- dry-run records
def _record_view(rec: dict | None, refusal: str | None) -> dict | None:
    if not rec:
        return None
    age = ST.record_age(rec)
    return {**rec, "age_s": None if age is None else int(age),
            "expires_in_s": None if age is None else int(ST.DRY_RUN_TTL - age), "refusal": refusal}


def _wikibase_section(con, out_dir: Path) -> dict:
    rec = ST.read_record(out_dir / ST.DRY_RUN_NAME)
    refusal = None
    if rec:
        sc = rec.get("scope") or {}
        args = {"really": True, "dry_run_id": rec.get("id"), "states": ",".join(sc.get("states") or []),
                "drafts": bool(sc.get("drafts")), "full": bool(sc.get("full")),
                "single_pass": bool(sc.get("single_pass"))}
        refusal = ST.wikibase_dry_run_refusal(con, out_dir, args)
    plan = plan_info(out_dir)
    lint = lint_info(out_dir)
    return {"dir": str(out_dir), "site": config.WIKIBASE_URL, "dry_run": _record_view(rec, refusal),
            "plan": {k: v for k, v in plan.items() if not k.startswith("_")} if plan else None,
            "lint": {k: v for k, v in lint.items() if not k.startswith("_")} if lint else None,
            "credentials": bool(config.WIKIBASE_BOT_USER and config.WIKIBASE_BOT_PASSWORD),
            "_plan": plan, "_lint": lint}


def _publish_section() -> dict:
    from ..publish import lexipedia as LX
    rec = ST.read_record(ST.publish_dir() / ST.DRY_RUN_NAME)
    refusal = ST.publish_dry_run_refusal({"dry_run_id": rec.get("id")}) if rec else None
    return {"site": config.DOKUWIKI_URL or None, "namespace": LX.NS, "corrections_set": LX.corrections_set(),
            "corrections": LX.corrections_address(), "corrections_problem": LX.corrections_problem(),
            "configured": bool(config.DOKUWIKI_URL and config.DOKUWIKI_TOKEN),
            "dry_run": _record_view(rec, refusal)}


# ---------------------------------------------------------------------------------------- the payload
def _heavy(con) -> dict:
    live = live_items()
    out_dir = ST.wikibase_dir()
    try:
        wb = _wikibase_section(con, out_dir)
    except Exception as e:  # noqa: BLE001
        wb = {"dir": str(out_dir), "site": config.WIKIBASE_URL, "dry_run": None, "plan": None, "lint": None,
              "error": f"{type(e).__name__}: {str(e)[:160]}", "_plan": None, "_lint": None}
    pub = _safe(_publish_section)
    places: dict[str, dict] = {
        "questions": _safe(_questions, con), "sources": _safe(_sources, con), "index": _safe(_index, con),
        "located": _safe(_located, con), "local": _safe(_local, con), "drafts": _safe(_drafts, con),
        "coverage": _safe(_coverage, con), "verified": _safe(_verified, con),
        "ready": _safe(_ready, con, wb["_plan"], wb["_lint"]), "wikibase": _safe(_wikibase, con, live),
        "wiki": _safe(_wiki, con), "turso": _safe(_turso, con), "compute": _safe(_compute, con),
    }
    b = _safe(_benefits, con)
    if b is not None:
        places["benefits"] = b
    waiting = _waiting(con, places, wb, pub)
    wb = {k: v for k, v in wb.items() if not k.startswith("_")}
    return {"places": places, "waiting": waiting, "wikibase": wb, "publish": pub, "cached_at": db.now()}


def _marker(con) -> tuple:
    """Changes whenever a job finishes or starts: the counts are recomputed then, not only every TTL seconds."""
    r = db.one(con, "SELECT count(*) AS n, max(finished_at) AS f, max(started_at) AS s FROM jobs") or {}
    return (str(config.DB_PATH), r.get("n"), r.get("f"), r.get("s"))


def payload(con) -> dict:
    marker = _marker(con)
    now = _now()
    with _LOCK:
        hit = _CACHE.get("value")
        fresh = hit is not None and _CACHE.get("marker") == marker and now - _CACHE.get("at", 0) < TTL
    if not fresh:
        hit = _heavy(con)
        with _LOCK:
            _CACHE.update(value=hit, marker=marker, at=now)
    jobs = _jobs(con)
    places = []
    for pid, meta in PLACES.items():
        if pid not in hit["places"]:
            continue
        places.append({"id": pid, **meta, **hit["places"][pid]})
    known = {p["id"] for p in places}
    transitions = []
    for t in TRANSITIONS:
        step = ST.STEPS.get(t["step"]) or ST.COMPOSITE.get(t["step"])
        if step is None:
            continue
        transitions.append({
            **t, "reads": [p for p in t["reads"] if p in known], "writes": [p for p in t["writes"] if p in known],
            "also": [p for p in t.get("also", []) if p in known],
            "title": step.title, "why": step.why, "cost": step.cost, "params": step.params,
            # the plan is the wikibase step's dry runs: they read the live wiki and write nothing outside lexflow
            "external": t["step"] in ST.EXTERNAL_WRITERS and t.get("mode") != "dry", "model": t.get("model", False),
            "status": _status(jobs, t), "waiting": hit["waiting"].get(t["id"]) or {"count": None, "text": ""},
            "actions": _actions(t)})
    on_chart = {t["step"] for t in TRANSITIONS}
    others = [{"id": s.id, "title": s.title} for s in list(ST.STEPS.values()) + list(ST.COMPOSITE.values())
              if s.id not in on_chart]
    running = [_brief(j) for j in jobs if j["status"] in ("running", "queued")]
    return {"generated": db.now(), "cached_at": hit["cached_at"], "ttl": TTL, "places": places,
            "transitions": transitions, "other_steps": others, "running": running,
            "other_work": other_work(con), "wikibase": hit["wikibase"], "publish": hit["publish"],
            "external_writers": sorted(ST.EXTERNAL_WRITERS), "dry_run_ttl": ST.DRY_RUN_TTL}
