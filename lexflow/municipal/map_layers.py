"""What lexflow holds, per state and per locality, for the home map's "holdings" layers.

``holdings(con)`` answers five questions with one query per table and a cheap stat of the statute indexes:

* processes modelled per state: reviewed or agreed state models plus the asked answers that go up as drafts
  (the same rule as ``publish.graph.Build.asked_rows``), with the tier breakdown;
* coverage per state and per researched locality: the latest coverage run's verdicts (adequate / partial /
  draft / none, where draft is a partial cell resting on drafts alone) and the kinds most often missing;
* local processes researched per locality (``place_processes``: count and verified count), keyed by county;
* items on the Wikibase per state (``wikibase_items``: the key's third segment is a state, a model id or a
  gov_id), by kind;
* the statute index: sections indexed per state, and regulations where present, read from the ``meta`` table of
  each ``data/index/<corpus>_<state>.sqlite``.

The result is cached for ten minutes, keyed by the database path and its version, so a write shows at once
and a page reload costs nothing.
"""
from __future__ import annotations

import re
import sqlite3
import threading
import time
from collections import Counter

from .. import config
from ..store import db
from . import states as S

TTL = 600
_CACHE: dict[tuple, tuple[float, dict]] = {}
_LOCK = threading.Lock()
_GOV = re.compile(r"^\d{14}$")
_MODEL = re.compile(r"^([a-z]{2})\.[a-z_]+$")
_ASKED_FILTER = """
    gov_id IS NULL AND target = state AND status IN ('answered', 'partial') AND facts IS NOT NULL
    AND coalesce(json_extract(metrics, '$.quotes_checked'), 0) > 0
    AND coalesce(json_extract(metrics, '$.quote_misses'), 0) = 0
    AND json_valid(facts) AND json_type(facts, '$.steps') = 'array' AND json_array_length(facts, '$.steps') > 0"""


def clear():
    """Forget the cache (the tests, and anything that wants the next call fresh)."""
    with _LOCK:
        _CACHE.clear()


def holdings(con) -> dict:
    key = (str(config.DB_PATH), db.version(con))
    now = time.time()
    with _LOCK:
        hit = _CACHE.get(key)
        if hit and now - hit[0] < TTL:
            return hit[1]
    out = _compute(con)
    with _LOCK:
        _CACHE.clear()
        _CACHE[key] = (now, out)
    return out


def _state_entry(states: dict, st: str) -> dict:
    fips = S.FIPS.get(st)
    if not fips:
        return {}
    return states.setdefault(fips, {"state": st, "name": S.NAME[st],
                                    "processes": {"value": 0, "tiers": {}, "asked": 0},
                                    "coverage": None, "wikibase": {"value": 0, "kinds": {}},
                                    "index": {"value": 0, "sections": 0, "regulations": 0}})


def _compute(con) -> dict:
    states: dict[str, dict] = {}
    gov_state: dict[str, str] = {}

    # 1. processes modelled: state models by tier, plus asked drafts
    for r in db.rows(con, "SELECT state, tier, count(*) AS n FROM process_models WHERE scope='state' GROUP BY state, tier"):
        e = _state_entry(states, r["state"])
        if not e:
            continue
        e["processes"]["tiers"][r["tier"]] = r["n"]
        if r["tier"] in ("reviewed", "agreed"):
            e["processes"]["value"] += r["n"]
    try:
        asked = db.rows(con, f"SELECT state, count(*) AS n FROM asked_answers WHERE {_ASKED_FILTER} GROUP BY state")
    except sqlite3.OperationalError:            # no JSON1 (very old SQLite): count nothing rather than fail
        asked = []
    for r in asked:
        e = _state_entry(states, r["state"])
        if e:
            e["processes"]["asked"] = r["n"]
            e["processes"]["value"] += r["n"]

    # 2. localities with researched processes (place_processes), keyed by their county
    places: dict[str, dict] = {}
    for r in db.rows(con, """SELECT p.gov_id, p.state, count(*) AS n, coalesce(sum(p.verified), 0) AS verified,
                                    g.name, g.kind, g.county_fips, g.population
                             FROM place_processes p LEFT JOIN governments g ON g.gov_id = p.gov_id
                             GROUP BY p.gov_id ORDER BY g.population DESC"""):
        gov_state[r["gov_id"]] = r["state"]
        fips = r["county_fips"] or ""
        if not fips:
            continue
        places.setdefault(fips, {"govs": []})["govs"].append({
            "gov_id": r["gov_id"], "name": r["name"] or r["gov_id"], "kind": r["kind"], "state": r["state"],
            "processes": r["n"], "verified": r["verified"], "coverage": None})

    # 3. coverage: the latest run, one cell per (question, state, place) with the coverage arm first
    run = db.scalar(con, "SELECT run_id FROM coverage_runs ORDER BY updated_at DESC LIMIT 1") if _has(con, "coverage_runs") else None
    coverage_total = {"run": run, "cells": 0, "adequate": 0, "partial": 0, "draft": 0, "none": 0, "questions": 0}
    if run:
        cells: dict[tuple, dict] = {}
        for r in db.rows(con, """SELECT qid, state, gov_id, arm, verdict, missing,
                                        coalesce(json_extract(probe, '$.drafts_only'), 0) AS drafts_only
                                 FROM coverage_runs WHERE run_id=? ORDER BY arm = 'coverage' DESC""", run):
            k = (r["qid"], r["state"], r["gov_id"] or "")
            if k in cells:
                continue
            v = r["verdict"] or "none"
            if v == "partial" and r["drafts_only"]:
                v = "draft"
            cells[k] = {"verdict": v, "missing": db.loads(r["missing"], []) or []}
        by_col: dict[tuple, dict] = {}
        for (qid, st, gov), c in cells.items():
            col = by_col.setdefault((st, gov), {"cells": 0, "adequate": 0, "partial": 0, "draft": 0, "none": 0, "missing": Counter()})
            col["cells"] += 1
            col[c["verdict"]] = col.get(c["verdict"], 0) + 1
            col["missing"].update(c["missing"])
        gov_rows = {g["gov_id"]: g for p in places.values() for g in p["govs"]}
        for (st, gov), col in by_col.items():
            summary = {"run": run, "cells": col["cells"], "adequate": col["adequate"], "partial": col["partial"],
                       "draft": col["draft"], "none": col["none"],
                       "share": round(col["adequate"] / col["cells"], 3) if col["cells"] else None,
                       "missing": col["missing"].most_common(4)}
            if gov:
                if gov in gov_rows:
                    gov_rows[gov]["coverage"] = summary
                continue
            e = _state_entry(states, st)
            if e:
                e["coverage"] = summary
            coverage_total["questions"] = max(coverage_total["questions"], col["cells"])
            for k in ("cells", "adequate", "partial", "draft", "none"):
                coverage_total[k] += col[k]

    # 4. the Wikibase: items per state, by kind
    wikibase_total = 0
    wikibase_countries: dict[str, int] = {}
    kinds_shared: Counter = Counter()
    for r in db.rows(con, "SELECT key FROM wikibase_items"):
        wikibase_total += 1
        parts = r["key"].split(":")
        if len(parts) < 3 or parts[0] != "lexflow":
            kinds_shared[parts[1] if len(parts) > 1 else parts[0]] += 1
            continue
        kind, third = parts[1], parts[2]
        st = None
        if third in S.NAME:
            st = third
        elif _MODEL.match(third):
            st = _MODEL.match(third).group(1)
        elif _GOV.match(third):
            st = gov_state.get(third)
            if st is None:
                st = gov_state[third] = db.scalar(con, "SELECT state FROM governments WHERE gov_id=?", third) or ""
        elif third == "asked" and len(parts) > 3 and parts[3] in S.NAME:
            st = parts[3]
        elif third in S.COUNTRY:                     # a country's items (lexflow:unit:jpn:...): counted apart
            wikibase_countries[third] = wikibase_countries.get(third, 0) + 1
            continue
        e = _state_entry(states, st) if st else {}
        if e:
            e["wikibase"]["value"] += 1
            e["wikibase"]["kinds"][kind] = e["wikibase"]["kinds"].get(kind, 0) + 1
        else:
            kinds_shared[kind] += 1

    # 5. the statute index: sections per state (and regulations), from each index file's meta table
    # countries' indexes (statutes_jpn.sqlite) are counted apart, under totals.countries: articles, laws, name
    index_total = {"sections": 0, "regulations": 0, "states": 0}
    countries: dict[str, dict] = {}
    for st, corpus, n in _index_sizes():
        if st in S.COUNTRY:
            if corpus == "statutes":
                countries[st] = {"name": S.COUNTRY[st]["name"], "sections": n, "laws": _laws_of(st),
                                 "wikibase": wikibase_countries.get(st, 0)}
            continue
        e = _state_entry(states, st)
        if not e:
            continue
        if corpus == "statutes":
            e["index"]["sections"] = n
            e["index"]["value"] = n
            index_total["sections"] += n
            index_total["states"] += 1
        elif corpus == "regulations":
            e["index"]["regulations"] = n
            index_total["regulations"] += n

    models_states = sum(1 for e in states.values() if e["processes"]["value"] > 0)
    localities = sum(len(p["govs"]) for p in places.values())
    return {"states": states, "places": places,
            "totals": {"states_with_models": models_states, "localities": localities,
                       "local_processes": sum(g["processes"] for p in places.values() for g in p["govs"]),
                       "coverage": coverage_total, "wikibase": wikibase_total, "wikibase_shared": dict(kinds_shared),
                       "index": index_total, "countries": countries,
                       "international_sections": sum(c["sections"] for c in countries.values())}}


def _has(con, table: str) -> bool:
    return bool(db.scalar(con, "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", table))


def _laws_of(code: str) -> int:
    """How many laws a country's index holds (its meta ``laws``), 0 when unrecorded."""
    p = config.DATA_DIR / "index" / f"statutes_{code}.sqlite"
    try:
        c = sqlite3.connect(p.resolve().as_uri() + "?mode=ro", uri=True, timeout=2)
        try:
            r = c.execute("SELECT value FROM meta WHERE key='laws'").fetchone()
        finally:
            c.close()
        return int(r[0]) if r else 0
    except (sqlite3.Error, ValueError, OSError):
        return 0


def _index_sizes() -> list[tuple[str, str, int]]:
    """``(state, corpus, sections)`` for every ``<corpus>_<state>.sqlite`` under data/index whose meta table says how
    many sections it holds (``max(id)`` of ``sec`` when the meta row is missing).  A file being built is skipped."""
    d = config.DATA_DIR / "index"
    out = []
    if not d.is_dir():
        return out
    for p in sorted(d.glob("*_*.sqlite")):
        m = re.fullmatch(r"([a-z]+)_([a-z]{2,3})\.sqlite", p.name)
        if not m or (m.group(2) not in S.NAME and m.group(2) not in S.COUNTRY):
            continue
        try:
            c = sqlite3.connect(p.resolve().as_uri() + "?mode=ro", uri=True, timeout=2)
            try:
                n = c.execute("SELECT value FROM meta WHERE key='sections'").fetchone()
                n = int(n[0]) if n else (c.execute("SELECT max(id) FROM sec").fetchone()[0] or 0)
            finally:
                c.close()
        except (sqlite3.Error, ValueError):
            continue
        out.append((m.group(2), m.group(1), n))
    return out
