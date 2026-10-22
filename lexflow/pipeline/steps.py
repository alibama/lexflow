"""The setup checklist: every pipeline step, what it needs, and a checkbox status computed from the data.

Status values: ``done`` (checked), ``partial``, ``todo``, ``blocked`` (a step it needs is not
done), ``optional`` (not needed for a working map).  The dashboard's Setup page and
``python -m lexflow status`` both render this list, so a new user sees which boxes to tick
and in what order.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Callable

import requests

from .. import config
from . import credits as C
from ..municipal import build as B
from ..municipal import contacts, crawl, governments, locator, locus_scan, scoring, statutes
from ..municipal import method as M
from ..municipal import states as S
from ..municipal.questions import QUESTIONS, get as get_question
from ..store import db
from ..store import turso as T

Log = Callable[[str], None]


@dataclass
class Step:
    id: str
    title: str
    why: str
    level: str                      # required | recommended | optional
    status: Callable
    run: Callable | None = None
    needs: list[str] = field(default_factory=list)
    params: list[str] = field(default_factory=list)   # states, questions, force, no_llm, regulations, full
    cost: str = ""
    # outside data, services, models and libraries the step uses: dicts with name, by, licence, url, use and
    # optionally licence_url, cite with cite_by ("maker" only for the maker's own wording, else "lexflow") and
    # note (see credits.py).  None means not filled in yet; an empty list needs credits_note to say why.
    credits: list[dict] | None = None
    credits_note: str = ""


def _scan_count(con, source: str) -> int:
    return db.scalar(con, "SELECT count(*) FROM scans WHERE source=? AND status='done'", source, default=0)


def _mark_scan(con, source: str, state: str, rows: int = 0, matched: int = 0, status: str = "done"):
    db.upsert(con, "scans", [{"source": source, "state": state, "rows": rows, "matched": matched,
                              "status": status[:300], "scanned_at": db.now()}], keys=("source", "state"), stamp=False)
    con.commit()


def plural(n: int, word: str) -> str:
    return f"{n:,} {word}{'' if n == 1 else 's'}"


def _gov_states(con) -> list[str]:
    return [r["state"] for r in db.rows(con, "SELECT DISTINCT state FROM governments ORDER BY state")]


# --------------------------------------------------------------------- status
def st_governments(con):
    n = db.scalar(con, "SELECT count(*) FROM governments", default=0)
    k = db.scalar(con, "SELECT count(DISTINCT state) FROM governments", default=0)
    return {"status": "done" if n >= 30_000 else "partial" if n else "todo", "done": n, "total": 38_736,
            "detail": f"{n:,} governments in {k} states" if n else "Not loaded yet"}


def st_statutes(con):
    rows = db.rows(con, "SELECT status, count(*) AS n FROM statute_files GROUP BY status")
    c = {r["status"]: r["n"] for r in rows}
    have, missing = c.get("downloaded", 0), c.get("not-in-release", 0)
    total = len(S.CODES)
    status = "done" if have + missing >= total else "partial" if have else "todo"
    return {"status": status, "done": have + missing, "total": total,
            "detail": f"{have} states downloaded" + (f", {missing} not in the release" if missing else "")}


def st_locate(con):
    have = db.scalar(con, "SELECT count(*) FROM statute_files WHERE status='downloaded'", default=0)
    rows = db.rows(con, "SELECT question, status, count(*) AS n FROM located_law GROUP BY question, status")
    found = sum(r["n"] for r in rows if r["status"] == "found")
    tried = sum(r["n"] for r in rows if r["status"] != "no-statutes")
    total = have * len(QUESTIONS)
    if not have:
        return {"status": "blocked", "done": 0, "total": 0, "detail": "Download statutes first"}
    per_q = {q: sum(r["n"] for r in rows if r["question"] == q and r["status"] == "found") for q in QUESTIONS}
    return {"status": "done" if tried >= total else "partial" if tried else "todo", "done": tried, "total": total,
            "detail": "; ".join(f"{QUESTIONS[q].short}: {n} states" for q, n in per_q.items())}


def st_contacts(con):
    n = _scan_count(con, "wikidata")
    k = len(_gov_states(con))
    if not k:
        return {"status": "blocked", "done": 0, "total": 0, "detail": "Load governments first"}
    direct = db.scalar(con, "SELECT count(DISTINCT gov_id) FROM contacts WHERE kind IN ('email','phone')", default=0)
    return {"status": "done" if n >= k else "partial" if n else "todo", "done": n, "total": k,
            "detail": f"{n} of {k} states checked; {plural(direct, 'government')} with an email or phone"}


def st_crawl(con):
    n = _scan_count(con, "crawl")
    k = len(_gov_states(con))
    pages = db.scalar(con, "SELECT count(DISTINCT gov_id) FROM contacts WHERE kind='page'", default=0)
    return {"status": "done" if k and n >= k else "partial" if n else "optional", "done": n, "total": k,
            "detail": f"{n} of {k} states scanned; {plural(pages, 'government')} with a records or licence page"}


def st_locus(con):
    n = _scan_count(con, "locus")
    k = len(_gov_states(con))
    govs = db.scalar(con, "SELECT count(DISTINCT gov_id) FROM local_law WHERE score > 0", default=0)
    return {"status": "done" if k and n >= k else "partial" if n else "optional", "done": n, "total": k,
            "detail": f"{n} of {k} states scanned; local law found for {plural(govs, 'government')}"}


def ollama_state() -> dict:
    from ..compute import nodes as CN
    if CN.pool_on():                       # the Setup card: "2 of 3 nodes online, see Compute"
        from ..compute import api as CA
        try:
            summ = CA.summary() or {}
            return {"reachable": summ.get("online", 0) > 0, "models": B.ollama_models(), "pool": summ}
        except Exception as e:  # noqa: BLE001
            return {"reachable": False, "models": [], "error": type(e).__name__, "pool": {"nodes": 0, "online": 0}}
    try:
        r = requests.get(f"{config.OLLAMA_URL.rstrip('/')}/api/tags", timeout=4)
        r.raise_for_status()
        names = [m["name"] for m in r.json().get("models", [])]
        return {"reachable": True, "models": names}
    except requests.RequestException as e:
        return {"reachable": False, "models": [], "error": type(e).__name__}


def st_models(con):
    o = ollama_state()
    want = list(dict.fromkeys((config.EMBED_MODEL, config.MODEL_A, config.MODEL_B)))
    have = [m for m in want if B._has(o["models"], m)]
    if not o["reachable"]:
        return {"status": "todo", "done": 0, "total": len(want),
                "detail": f"Ollama not reachable at {config.OLLAMA_URL} (start it with the 'llm' profile)"}
    missing = [m for m in want if m not in have]
    parts = ([f"Ready: {', '.join(have)}"] if have else []) + ([f"Not pulled yet: {', '.join(missing)}"] if missing else [])
    return {"status": "done" if not missing else "partial" if have else "todo", "done": len(have), "total": len(want),
            "detail": "; ".join(parts)}


def st_build(con):
    located = db.rows(con, "SELECT state, question FROM located_law WHERE status='found'")
    if not located:
        return {"status": "blocked", "done": 0, "total": 0, "detail": "Locate the law first"}
    models = {(r["state"], r["question"]): r["tier"] for r in db.rows(con, "SELECT state, question, tier FROM "
                                                                          "process_models")}
    modelled = sum(1 for r in located if models.get((r["state"], r["question"])) in ("reviewed", "agreed", "single"))
    tried = sum(1 for r in located if (r["state"], r["question"]) in models)
    tiers: dict[str, int] = {}
    for t in models.values():
        tiers[t] = tiers.get(t, 0) + 1
    detail = "; ".join(f"{M.TIER_LABEL[t]}: {n}" for t, n in sorted(tiers.items(), key=lambda x: -M.TIERS.index(x[0])))
    return {"status": "done" if modelled >= len(located) else "partial" if tried else "todo",
            "done": modelled, "total": len(located), "detail": detail or "No models yet"}


def st_score(con):
    govs = db.scalar(con, "SELECT count(*) FROM governments", default=0)
    if not govs:
        return {"status": "blocked", "done": 0, "total": 0, "detail": "Load governments first"}
    n = db.scalar(con, "SELECT count(*) FROM answers", default=0)
    # a state is out of date when any of its inputs changed after its oldest answer was scored
    stale = [r["state"] for r in db.rows(con, """
        SELECT a.state FROM (SELECT state, min(updated_at) AS scored FROM answers GROUP BY state) a
        JOIN (SELECT state, max(updated_at) AS changed FROM (
                SELECT state, updated_at FROM process_models UNION ALL SELECT state, updated_at FROM contacts
                UNION ALL SELECT state, updated_at FROM local_law UNION ALL SELECT state, updated_at FROM located_law
                UNION ALL SELECT state, updated_at FROM governments) GROUP BY state) i ON i.state = a.state
        WHERE i.changed > a.scored ORDER BY a.state""")]
    total = govs * len(QUESTIONS)
    status = "done" if n >= total and not stale else "partial" if n else "todo"
    if not n:
        detail = "Not scored yet"
    elif stale:
        detail = f"{plural(n, 'answer')} scored; re-score {', '.join(s.upper() for s in stale[:8])}" + (
            f" and {len(stale) - 8} more" if len(stale) > 8 else "") + " (inputs changed since)"
    else:
        detail = f"{plural(n, 'answer')} scored"
    return {"status": status, "done": n, "total": total, "detail": detail, "stale": stale}


def st_local(con):
    from ..municipal import places as P
    files = len(P.local_files())
    n = db.scalar(con, "SELECT count(DISTINCT gov_id) FROM local_answers", default=0)
    if not files:
        return {"status": "optional", "done": 0, "total": 0, "detail": "No researched places yet"}
    return {"status": "done" if n >= files else "partial" if n else "todo", "done": n, "total": files,
            "detail": f"{plural(n, 'place')} loaded of {plural(files, 'researched place')}"}


def st_index(con):
    from ..ask import index as I
    have = [r["state"] for r in db.rows(con, "SELECT state FROM statute_files WHERE status='downloaded'")]
    if not have:
        return {"status": "blocked", "done": 0, "total": 0, "detail": "Download statutes first"}
    n = sum(1 for st in have if I.ready(st))
    return {"status": "done" if n >= len(have) else "partial" if n else "todo", "done": n, "total": len(have),
            "detail": f"{n} of {plural(len(have), 'state')} searchable"}


def run_index(con, args, log, progress):
    from ..ask import index as I
    have = [r["state"] for r in db.rows(con, "SELECT state FROM statute_files WHERE status='downloaded'")]
    sts = [s for s in _states(args, con) if s in have] if args.get("states") else have
    out = {}
    for i, st in enumerate(sts):
        if args.get("force") or not I.ready(st):
            out[st] = I.build(st, log=log)
        progress((i + 1) / max(1, len(sts)))
    return {"built": len(out), "states": len(sts)}


def st_regulations(con):
    """Done when every regulations file on disk (us_<st>_regulations.parquet) has a current index."""
    from ..corpus import regulations as R
    have = R.states()
    if not have:
        return {"status": "optional", "done": 0, "total": 0,
                "detail": "No regulations file on disk: run Download state statutes with + regulations first"}
    n = sum(1 for st in have if R.ready(st))
    return {"status": "done" if n >= len(have) else "partial" if n else "todo", "done": n, "total": len(have),
            "detail": f"{n} of {plural(len(have), 'state')} with a regulations file searchable"}


def run_regulations(con, args, log, progress):
    """Index the regulations files already on disk: every one, or those of the states named.  Never downloads."""
    from ..corpus import regulations as R
    have = R.states()
    named = _states(args, con) if args.get("states") or args.get("places") else have
    sts = [s for s in named if s in have]
    if len(sts) < len(named):
        log(f"no regulations file on disk for {_upper_list([s for s in named if s not in have])}")
    out = R.build_all(sts, force=bool(args.get("force")), log=log, progress=progress)
    built = [v for v in out.values() if isinstance(v, dict)]
    return {"built": len(built), "states": len(sts), "sections": sum(v["sections"] for v in built),
            "mb": round(sum(v["mb"] for v in built), 1)}


def run_ask(con, args, log, progress):
    """Answer a new question for the chosen states and places (lexflow/ask)."""
    from ..ask import pipeline as AP
    targets = args.get("targets") or []
    if isinstance(targets, str):
        targets = [t for t in targets.split(",") if t.strip()]
    return AP.run(con, args["question"], targets, model=args.get("model"), use_llm=not args.get("no_llm"),
                  log=log, progress=progress, question_id=args.get("question_id"), node=args.get("node") or None)


def st_ontology(con):
    """Done when every state with a statute index has a section_tags row for every section."""
    from ..ask import index as I
    from ..law import ontology as O
    have = [r["state"] for r in db.rows(con, "SELECT state FROM statute_files WHERE status='downloaded'")]
    have = [st for st in have if I.ready(st)]
    if not have:
        return {"status": "optional", "done": 0, "total": 0, "detail": "Make the statutes searchable first"}
    tagged = O.status(con, have)
    full = sum(1 for st in have if sum(tagged.get(st, {}).values()) >= O.section_count(st))
    return {"status": "done" if full >= len(have) else "partial" if full else "optional", "done": full,
            "total": len(have), "detail": f"{full} of {plural(len(have), 'state')} tagged"}


def run_ontology(con, args, log, progress):
    """Tag every section of each named state's index (lexflow.law.ontology): structure and ELI id by rules; norm
    types by rules, plus the decision model when ``model`` is set (``decision`` or ``chat``) and ``no_llm`` is not.
    ``budget`` caps the model calls per run (default 200), ``pace`` sleeps between them, ``limit`` stops a state
    after that many sections (a trial)."""
    from ..ask import index as I
    from ..law import ontology as O
    have = [r["state"] for r in db.rows(con, "SELECT state FROM statute_files WHERE status='downloaded'")]
    sts = [s for s in (_states(args, con) if args.get("states") else have) if I.ready(s)]
    decider = None
    if args.get("model") and not args.get("no_llm"):
        from ..extract import decide as D
        decider = D.Decider()
        if decider.backend["kind"] == "none":
            log("no decision model and no chat model is pulled: rules only")
            decider = None
        elif args.get("model") == "chat" and decider.backend["kind"] == "decision":
            decider = D.Decider(backend_info={"kind": "chat", "model": decider.chat_model, "models": []})
    budget = int(args.get("budget") or 200)
    out = {}
    for i, st in enumerate(sts):
        out[st] = O.run_state(con, st, decider=decider, force=bool(args.get("force")), budget=budget,
                              pace=float(args.get("pace") or 0), limit=args.get("limit"), log=log,
                              progress=lambda p, i=i: progress((i + p) / max(1, len(sts))))
        if decider is not None:
            budget -= out[st]["model_calls"]
        _mark_scan(con, "ontology", st, rows=out[st]["tagged"], matched=out[st]["model_calls"])
        progress((i + 1) / max(1, len(sts)))
    return {"states": len(sts), "tagged": sum(v["tagged"] for v in out.values()),
            "model_calls": sum(v["model_calls"] for v in out.values()),
            "seconds": round(sum(v["seconds"] for v in out.values()), 1)}


def _upper_list(states: list[str], limit: int = 8, why=None) -> str:
    shown = [f"{s.upper()} ({why(s)})" if why else s.upper() for s in states[:limit]]
    return ", ".join(shown) + (f" and {len(states) - limit} more" if len(states) > limit else "")


def st_cases(con):
    models = db.rows(con, "SELECT DISTINCT state FROM process_models WHERE tier IN ('reviewed','agreed','single')")
    if not models:
        return {"status": "blocked", "done": 0, "total": 0, "detail": "Build state models first"}
    # the same states and the same definition of done as run_cases: a state is done when its scans row says its
    # latest search ran to the end, even when no opinion cites its sections
    sts = sorted(_cases_targets(con))
    where = _cases_progress(con, sts)
    n = db.scalar(con, "SELECT count(*) FROM case_law", default=0)
    by = {k: [s for s in sts if where[s]["status"] == k] for k in ("done", "failed", "stopped", "stored", "skipped")}
    parts = [f"{plural(n, 'court decision')} found; {len(by['done'])} of {plural(len(sts), 'state')} searched to the "
             "end"]
    if by["stopped"]:
        parts.append(f"stopped by a rate limit, searched first next time: {_upper_list(by['stopped'])}")
    if by["failed"]:
        parts.append("search failed, tried again on the next run: "
                     + _upper_list(by["failed"], 4, lambda s: where[s]["reason"][:80]))
    if by["skipped"]:
        parts.append("not searched, looked at again on the next run: "
                     + _upper_list(by["skipped"], 4, lambda s: where[s]["reason"][:80]))
    if by["stored"]:
        parts.append(f"opinions stored but no finished search recorded: {_upper_list(by['stored'])} (searched "
                     "again after the states never searched)")
    have = len(by["done"])
    return {"status": "done" if have >= len(sts) else "partial" if have or n else "todo", "done": have,
            "total": len(sts), "detail": "; ".join(parts)}


def st_publish(con):
    from ..publish import lexipedia as LX
    if not (config.DOKUWIKI_URL and config.DOKUWIKI_TOKEN):
        return {"status": "optional", "done": 0, "total": 0,
                "detail": "Set DOKUWIKI_URL and DOKUWIKI_TOKEN (a bot account) to enable"}
    if not LX.corrections_set():
        return {"status": "optional", "done": 0, "total": 0,
                "detail": "Set LEXFLOW_CORRECTIONS (the e-mail address or URL readers write to, on a real domain) to "
                          f"enable: every page links lexflow:method, which gives it (now {LX.corrections_problem()})"}
    n = sum(1 for r in db.rows(con, "SELECT stages FROM process_models") if db.loads(r["stages"], {}).get("published"))
    k = db.scalar(con, "SELECT count(*) FROM process_models WHERE tier IN ('reviewed','agreed')", default=0)
    return {"status": "done" if k and n >= k else "partial" if n else "todo", "done": n, "total": k,
            "detail": f"{n} of {k} reviewed or agreed models published to {config.DOKUWIKI_URL}"}


def st_sync(con):
    if not config.TURSO_URL:
        return {"status": "optional", "done": 0, "total": 0,
                "detail": "Set TURSO_DATABASE_URL (and TURSO_AUTH_TOKEN) or start the 'shared' profile"}
    last = db.one(con, "SELECT direction, finished_at, ok, rows FROM sync_log ORDER BY id DESC LIMIT 1")
    if not last:
        return {"status": "todo", "done": 0, "total": 1, "detail": f"Configured ({config.TURSO_URL}); never synced"}
    return {"status": "done" if last["ok"] else "partial", "done": 1, "total": 1,
            "detail": f"Last {last['direction']} {last['finished_at']}: {last['rows']:,} rows"
                      + ("" if last["ok"] else " (failed)")}


# ----------------------------------------------------------------------- runs
def _places(con, args) -> list[dict] | None:
    from ..municipal import places as P
    return P.resolve_all(con, args["places"]) if args.get("places") else None


def _states(args, con=None) -> list[str]:
    """States named directly, or the states of the places named (``places`` narrows a run to a few governments)."""
    if args.get("places") and not args.get("states") and con is not None:
        return sorted({g["state"] for g in _places(con, args)})
    return S.parse_states(args.get("states"))


def run_governments(con, args, log, progress):
    return governments.load(con, log=log, progress=progress)


def run_statutes(con, args, log, progress):
    kinds = ("statutes", "regulations") if args.get("regulations") else ("statutes",)
    sts = _states(args, con)
    out = {}
    for i, st in enumerate(sts):
        out[st] = statutes.fetch_state(con, st, kinds=kinds, log=log)
        progress((i + 1) / len(sts))
    db.bump(con)
    con.commit()
    return {"downloaded": sum(v == "downloaded" for v in out.values()),
            "not_in_release": [k for k, v in out.items() if v != "downloaded"]}


def run_locate(con, args, log, progress):
    sts = [s for s in _states(args, con)]
    out = {}
    for i, qid in enumerate(QUESTIONS if not args.get("questions") else args["questions"].split(",")):
        out[qid] = locator.run(con, get_question(qid), sts, log=log)
        progress((i + 1) / len(QUESTIONS))
    return out


def run_contacts(con, args, log, progress):
    sts = [s for s in _states(args, con) if s in set(_gov_states(con))]
    out = {}
    for i, st in enumerate(sts):
        out[st] = contacts.wikidata(con, st, log=log)
        _mark_scan(con, "wikidata", st, matched=out[st]["matched"])
        progress((i + 1) / len(sts))
    return out


def run_crawl(con, args, log, progress):
    sts = [s for s in _states(args, con) if s in set(_gov_states(con))]
    govs = _places(con, args)
    out = {}
    for i, st in enumerate(sts):
        ids = [g["gov_id"] for g in govs if g["state"] == st] if govs else None
        out[st] = crawl.run(con, st, force=bool(args.get("force")), log=log, gov_ids=ids,
                            progress=lambda p, i=i: progress((i + p) / len(sts)))
        if ids is None:
            _mark_scan(con, "crawl", st, rows=out[st]["sites"], matched=out[st]["records"] + out[st]["business"])
    return out


def run_locus(con, args, log, progress):
    sts = [s for s in _states(args, con) if s in set(_gov_states(con))]
    out = {}
    for i, st in enumerate(sts):
        out[st] = locus_scan.run(con, st, log=log)
        progress((i + 1) / len(sts))
    return out


def run_models(con, args, log, progress):
    """Pull the wanted models (``args.models``, else the embed and the two chat models) into Ollama: with
    ``args.node``, into that node of the pool (the Compute page's "Pull a model")."""
    out = {}
    url = config.OLLAMA_URL
    if args.get("node"):
        from ..compute import nodes as CN
        url = CN.url_of(args["node"])
        if not url:
            raise ValueError(f"unknown node {args['node']!r}: the configured nodes are {', '.join(CN.names()) or 'none'}")
    want = [m.strip() for m in (args.get("models") or "").split(",") if m.strip()] or \
        list(dict.fromkeys((config.EMBED_MODEL, config.MODEL_A, config.MODEL_B)))
    for i, name in enumerate(want):
        log(f"pulling {name} into Ollama at {url}" + (f" (node {args['node']})" if args.get("node") else ""))
        with requests.post(f"{url.rstrip('/')}/api/pull", json={"model": name, "stream": True},
                           stream=True, timeout=3600) as r:
            r.raise_for_status()
            last = ""
            for line in r.iter_lines():
                if not line:
                    continue
                msg = json.loads(line)
                if msg.get("error"):
                    raise RuntimeError(f"{name}: {msg['error']}")
                status = msg.get("status", "")
                if msg.get("total") and msg.get("completed"):
                    progress((i + msg["completed"] / msg["total"]) / len(want))
                if status != last:
                    log(f"{name}: {status}")
                    last = status
        out[name] = "ready"
    return out


def run_build(con, args, log, progress):
    sts = _states(args, con)
    located = {r["state"] for r in db.rows(con, "SELECT DISTINCT state FROM located_law WHERE status='found'")}
    sts = [s for s in sts if s in located or args.get("states")]
    qs = args.get("questions").split(",") if args.get("questions") else list(QUESTIONS)
    govs = _places(con, args)
    return B.run(con, sts, qs, use_llm=not args.get("no_llm"), force=bool(args.get("force")), log=log,
                 progress=progress, gov_ids=[g["gov_id"] for g in govs] if govs else None)


def run_score(con, args, log, progress):
    sts = [s for s in _states(args, con) if s in set(_gov_states(con))]
    govs = _places(con, args)
    out = {}
    for i, st in enumerate(sts):
        ids = [g["gov_id"] for g in govs if g["state"] == st] if govs else None
        out[st] = scoring.run(con, st, log=log, gov_ids=ids)
        progress((i + 1) / len(sts))
    return {"states": len(out)}


CASES = "courtlistener"      # the cases step's source in the scans table
# where a state stands with the cases step, in the order a run searches them: its latest search stopped (a rate
# limit) or failed; never searched; opinions stored but no finished search recorded here; done
# a state stopped by a rate limit goes on first; one that failed goes after the states never searched, so a section
# that fails the same way on every run cannot hold back every other state
CASES_RANK = {"stopped": 0, "new": 1, "failed": 2, "stored": 3, "skipped": 4, "done": 4}


def _cases_targets(con) -> set[str]:
    """The states the cases step searches: those with a process model or a seed or verified located section."""
    return {r["state"] for r in db.rows(con, "SELECT DISTINCT state FROM process_models")} | \
        {r["state"] for r in db.rows(con, "SELECT DISTINCT state FROM located_law WHERE status='found' "
                                          "AND method IN ('seed','verified')")}


def _cases_progress(con, states) -> dict[str, dict]:
    """Where each state stands with the cases step, for both st_cases and run_cases: ``status``, ``reason``,
    ``when`` and ``rank`` (CASES_RANK).  The scans row is the record: 'done' when a search of every section answered,
    'stopped: <why>' when a rate limit or the day's allowance stopped it, 'failed: <why>' when a search failed
    (caselaw.SearchFailed).  Opinions stored with no scans row at all (searched before lexflow recorded searches, as
    CA, DC and MD were, or pulled through Turso) are 'stored': not done, since nothing says every section was
    searched, but searched again only after the states never searched; ``when`` is then the newest opinion row."""
    from ..municipal import caselaw
    rec = {r["state"]: r for r in db.rows(con, "SELECT state, status, rows, scanned_at FROM scans WHERE source=?",
                                          CASES)}
    stored = {r["state"]: r["at"] for r in db.rows(
        con, "SELECT state, max(updated_at) AS at FROM case_law WHERE source=? GROUP BY state", CASES)}
    out = {}
    for st in states:
        r = rec.get(st)
        if r:
            status, _, reason = (r["status"] or "").partition(":")
            status = status.strip() if status.strip() in ("done", "stopped", "skipped") else "failed"
            if status == "done" and not r["rows"] and not caselaw.COURTS.get(st):
                status = "skipped"          # recorded as done before skips had their own status: never searched
            out[st] = {"status": status, "reason": reason.strip(), "when": r["scanned_at"] or ""}
        elif st in stored:
            out[st] = {"status": "stored", "reason": "", "when": stored[st] or ""}
        else:
            out[st] = {"status": "new", "reason": "", "when": ""}
        out[st]["rank"] = CASES_RANK[out[st]["status"]]
    return out


def run_cases(con, args, log, progress):
    """Search CourtListener state by state, paced to its limits (5 requests a minute, 50 an hour, 125 a day; see
    municipal/caselaw.py).  The day's allowance covers only part of the states, so a run searches the states that
    are not done yet, of those named or of all (an empty states box, or 'all'): first those a rate limit
    stopped, then those never searched, then those whose last search failed, then those with opinions stored but no
    finished search recorded (see _cases_progress).  ``force`` (Redo) also searches the done states again, after those and oldest search
    first, so a Redo stopped by the day's limit goes on the next day from the states not redone yet.

    A state is recorded as done only when the search of every section answered.  A failed search records it as
    failed, with the reason, so later runs search it again; a rate limit records it as stopped.  A state already
    done keeps its record (and its date) when a Redo of it stops or fails.  The run stops at a rate limit, the day's
    allowance, or a failure every other state would most likely share (401, 403, 5xx, a timeout), unless that
    state failed last time too (then the fault is its own, and the run goes on); after another error answer it goes
    on with the next state."""
    from ..municipal import caselaw
    targets = _cases_targets(con)
    named = bool(args.get("states") or args.get("places"))
    sts = [s for s in _states(args, con) if s in targets] if named else sorted(targets)
    where = _cases_progress(con, sts)
    redo = bool(args.get("force"))
    done = [s for s in sts if where[s]["status"] == "done"]
    if done and not redo:
        log(f"skipping {plural(len(done), 'state')} already searched to the end (tick Redo to search them again)")
    queue = sorted((s for s in dict.fromkeys(sts) if redo or where[s]["status"] != "done"),
                   key=lambda s: (where[s]["rank"], where[s]["when"], s))
    if queue:
        log(f"searching {plural(len(queue), 'state')} in this order: {', '.join(s.upper() for s in queue)}")
    out = {}
    for i, st in enumerate(queue):
        name, was_done = S.NAME.get(st, st), where[st]["status"] == "done"
        try:
            out[st] = caselaw.run(con, st, log=log, progress=lambda p, i=i: progress((i + p) / len(queue)))
            _mark_scan(con, CASES, st, rows=out[st]["sections"], matched=out[st]["opinions"])
        except caselaw.Skipped as e:
            out[st] = {"skipped": e.reason, "sections": e.sections_done, "opinions": e.opinions}
            if not was_done:
                _mark_scan(con, CASES, st, rows=e.sections_done, matched=e.opinions, status=e.reason)
            log(f"{name}: not searched ({e.reason.removeprefix('skipped: ')}); recorded as skipped, not as done")
        except caselaw.SearchFailed as e:
            out[st] = {"failed": e.reason, "sections": e.sections_done, "opinions": e.opinions}
            if was_done:
                log(f"{name}: search failed ({e.reason}); its earlier complete search stays on record")
            else:
                _mark_scan(con, CASES, st, rows=e.sections_done, matched=e.opinions, status=f"failed: {e.reason}")
                log(f"{name}: search failed ({e.reason}); recorded as failed, so the next run searches it again")
            if e.stops_run and where[st]["status"] == "failed":
                # it failed last time too: a fault in this state's searches, not CourtListener as a whole
                log(f"{name}: failed again; going on with the next state")
                continue
            if e.stops_run:
                out["stopped"] = f"{name}: {e.reason}"
                log("stopped: the other states would most likely fail the same way. Run this step again once "
                    "CourtListener answers (or the token is fixed).")
                break
        except caselaw.RateLimited as e:
            if not was_done:
                _mark_scan(con, CASES, st, rows=e.sections_done, matched=e.opinions, status=f"stopped: {e}")
            log(f"stopped: {e}. Run this step again later: it goes on from {name}, and sections already searched "
                "keep their results.")
            out["stopped"] = str(e)
            break
    return out


# Steps that write to an outside site.  None of them is ever part of a chain: "run everything" (the quickstart
# composite and the dashboard's run-all button) runs the required local steps only, and each of these runs as a
# job of its own that the operator starts on purpose.  The wikibase step writes nothing unless its job says so.
EXTERNAL_WRITERS = frozenset({"wikibase", "publish", "sync"})


def st_wikibase(con):
    if not (config.WIKIBASE_BOT_USER and config.WIKIBASE_BOT_PASSWORD):
        return {"status": "optional", "done": 0, "total": 0,
                "detail": f"Set WIKIBASE_BOT_USER and WIKIBASE_BOT_PASSWORD (a bot password on {config.WIKIBASE_URL})"}
    n = db.scalar(con, "SELECT count(*) FROM wikibase_items", default=0)
    return {"status": "done" if n else "todo", "done": n, "total": n,
            "detail": f"{plural(n, 'item')} on {config.WIKIBASE_URL}" if n else f"Ready to plan a push to {config.WIKIBASE_URL}"}


def wikibase_push_refusal(out_dir, skip_held: bool = False) -> str | None:
    """Why a real push may not run now: the lint report (``lexflow wikibase lint``) is missing from ``out_dir``, or
    it holds items and the operator did not choose ``skip_held``.  None when it passes.  The step passes
    ``allow_held`` only when the report holds items and the operator chose ``skip_held``, so the pusher's own gate
    (``push.run``) asks the same question a second time.  Held items are never written either way: the pusher skips
    them and drops any statement that names one."""
    from ..publish import push as P
    report = P.read_lint(out_dir / P.LINT_NAME)
    if report is None:
        return f"{out_dir / P.LINT_NAME} is missing: run `lexflow wikibase lint` first"
    held = P.held_keys(report)
    if held and not skip_held:
        return (f"the lint report holds {len(held)} items: fix them and re-run the lint, or push with skip_held "
                "(held items are never written either way)")
    return None


# ------------------------------------------------------------- dry runs before real writes
# A real Wikibase push or DokuWiki publish follows a dry run of the same graph (pages).  Each dry run writes a record
# (DRY_RUN_NAME) with its numbers, the scope it planned and a fingerprint of what it planned; a real job is refused
# unless that record is under DRY_RUN_TTL old, planned the same scope, has not been used by a real job since, and
# still fits what the real job builds (the graph hash and the Wikibase record for a push, the pages for a publish).
# The dashboard's confirmation dialog shows the record's numbers and sends its id (``dry_run_id``): a newer dry run
# than the one the operator read is refused too, and /api/jobs asks for that id before a real job is queued.
DRY_RUN_TTL = 24 * 3600
DRY_RUN_NAME = "dry-run.json"


def wikibase_dir(args: dict | None = None):
    """Where the wikibase step keeps its plan, lint report and dry-run record: the job's ``out``, else
    LEXFLOW_WIKIBASE_OUT, else <data>/wikibase-push (the operator's directory; out/wikibase in the checkout is
    the CLI's default, where the scoped plans of other runs also land)."""
    import os
    from pathlib import Path
    if args and args.get("out"):
        return Path(args["out"])
    env = os.environ.get("LEXFLOW_WIKIBASE_OUT", "").strip()
    return Path(env) if env else config.DATA_DIR / "wikibase-push"


def publish_dir():
    """Where the publish step keeps its dry-run record."""
    return config.DATA_DIR / "dokuwiki-publish"


def flag(value, default: bool) -> bool:
    """A job arg as a boolean: missing or None is ``default``; "", "0", "false", "no" and "off" are False."""
    if value is None:
        return default
    if isinstance(value, str):
        return value.strip().lower() not in ("", "0", "false", "no", "off")
    return bool(value)


def parse_passes(value) -> list[str] | None:
    """The wikibase step's ``passes``: None (both passes in one plan or push, no lint: the CLI's shape), or the
    passes to run after a fresh lint, in order: "1,2" (also "all" or [1, 2]), "1" or "2"."""
    if value in (None, "", False):
        return None
    parts = [str(p).strip() for p in (value if isinstance(value, (list, tuple)) else str(value).split(","))]
    parts = [p for p in parts if p]
    if parts == ["all"]:
        parts = ["1", "2"]
    if not parts or parts not in (["1", "2"], ["1"], ["2"]):
        raise ValueError(f"passes is 1,2 or 1 or 2, not {value!r}")
    return parts


def read_record(path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
    except (OSError, ValueError):
        return None


def write_record(path, rec: dict) -> None:
    import os
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(rec, indent=1, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


def new_record_id() -> tuple[str, str]:
    """(id, generated) for a dry-run record: the time, and a few random characters so two runs never share one."""
    import secrets
    ts = db.now()
    return f"{ts}-{secrets.token_hex(3)}", ts


def record_age(rec: dict, now: float | None = None) -> float | None:
    import time
    from datetime import datetime, timezone
    try:
        t = datetime.strptime(rec["generated"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()
    except (KeyError, TypeError, ValueError):
        return None
    return (now if now is not None else time.time()) - t


def use_record(path, rec: dict) -> None:
    """Mark a dry-run record used by the real job starting now (one dry run, one real job), before its first write."""
    import os
    rec = dict(rec, used={"at": db.now(), "job": os.environ.get("LEXFLOW_JOB_ID") or None})
    write_record(path, rec)


def _digest(lines) -> str:
    import hashlib
    h = hashlib.sha256()
    for line in lines:
        h.update(line.encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()[:24]


def graph_hash(items) -> str:
    """A fingerprint of the graph a push would write: every item's key and content hash (``push.content_hash``)."""
    from ..publish import push as P
    return _digest(sorted(f"{it.key}={P.content_hash(it)}" for it in items))


def held_hash(keys) -> str:
    return _digest(sorted(keys or ()))


def ids_mark(con) -> str:
    """What the local Wikibase record looks like now (rows, hashes, last write of wikibase_items and wikibase_props):
    only the pusher writes these tables, so a change means a push ran since."""
    a = db.one(con, "SELECT count(*) AS n, count(content_hash) AS h, max(updated_at) AS t FROM wikibase_items") or {}
    try:
        b = db.one(con, "SELECT count(*) AS n, max(updated_at) AS t FROM wikibase_props") or {}
    except Exception:  # noqa: BLE001 - no such table yet
        b = {}
    return f"{a.get('n') or 0}:{a.get('h') or 0}:{a.get('t') or ''}|{b.get('n') or 0}:{b.get('t') or ''}"


def wikibase_scope(args: dict) -> dict:
    """The part of a wikibase job's args a dry run and its push must share."""
    sts = sorted(S.parse_states(args["states"])) if args.get("states") else None
    return {"states": sts, "drafts": bool(args.get("drafts")), "full": bool(args.get("full"))}


def _scope_words(scope: dict | None) -> str:
    s = scope or {}
    return (f"{'states ' + ','.join(s['states']) if s.get('states') else 'every state'}"
            f"{', with drafts' if s.get('drafts') else ''}{', a full resend' if s.get('full') else ''}")


def _record_refusal(rec: dict | None, args: dict, what: str, now: float | None = None) -> str | None:
    if rec is None:
        return f"no dry run of the {what} has been recorded: run a dry run first (it shows what would be written)"
    age = record_age(rec, now)
    if age is None or age > DRY_RUN_TTL:
        return f"the last dry run ({rec.get('generated')}) is older than 24 hours: run a dry run again"
    if rec.get("used"):
        return (f"the dry run of {rec.get('generated')} was used by the real job of {rec['used'].get('at')}: run a dry "
                "run again")
    if args.get("dry_run_id") and args["dry_run_id"] != rec.get("id"):
        return (f"the dry run confirmed ({args['dry_run_id']}) is not the latest one ({rec.get('id')}): look at the "
                "latest numbers and confirm again")
    return None


def wikibase_dry_run_refusal(con, out_dir, args: dict, *, graph: str | None = None, held=None,
                             now: float | None = None) -> str | None:
    """Why a real push may not follow the dry run recorded in ``out_dir``, or None.  Without ``graph`` (the API,
    before a job is queued) only what needs nothing built is asked: a record under 24 hours old, not used, the one
    confirmed, of the same scope, with the Wikibase record unchanged since; the job also gives the hash of the graph
    it built and the keys its lint report holds."""
    rec = read_record(out_dir / DRY_RUN_NAME)
    why = _record_refusal(rec, args, "push", now)
    if why:
        return why
    if rec.get("scope") != wikibase_scope(args):
        return (f"the dry run planned {_scope_words(rec.get('scope'))}, not {_scope_words(wikibase_scope(args))}: run "
                "a dry run of the same states and options")
    if con is not None and rec.get("ids_mark") != ids_mark(con):
        return "the Wikibase record changed since the dry run (a push ran): run a dry run again"
    if graph is not None and rec.get("graph_hash") != graph:
        return "the graph changed since the dry run: run a dry run again"
    if held is not None and rec.get("held_hash") != held_hash(held):
        return (f"the lint report now holds {len(held)} items and the dry run planned with {rec.get('held_count')}: "
                "run a dry run again")
    return None


def publish_dry_run_refusal(args: dict, *, pages: str | None = None, now: float | None = None) -> str | None:
    """Why a real publish may not follow the recorded dry run, or None; the job also gives the hash of its pages."""
    rec = read_record(publish_dir() / DRY_RUN_NAME)
    why = _record_refusal(rec, args, "publish", now)
    if why:
        return why
    if pages is not None and rec.get("pages_hash") != pages:
        return "the pages changed since the dry run: run a dry run again"
    return None


def pages_hash(pages: dict) -> str:
    return _digest(f"{pid}\t{(text or '').strip()}" for pid, text in sorted(pages.items()))


NEEDS_CONFIRM = ("a real {what} is started from the Pipeline page, which shows the dry run's numbers and sends the "
                 "id of the dry run confirmed (dry_run_id)")
NO_BOT = "WIKIBASE_BOT_USER and WIKIBASE_BOT_PASSWORD (or LEXI_USER and LEXI_PASS) are not set"


def real_run_refusal(con, step: str, args: dict) -> str | None:
    """Why /api/jobs does not queue a job: a real push or publish needs the id of the latest dry run's record (as
    the Pipeline page's confirmation sends it) and that dry run must still allow it; None for any other job.  A bad
    ``passes`` raises ValueError.  The job asks again, with the graph or pages it builds."""
    if step == "wikibase":
        parse_passes(args.get("passes"))
        if args.get("really") and not args.get("dry_run"):
            if not args.get("dry_run_id"):
                return NEEDS_CONFIRM.format(what="push")
            if not (config.WIKIBASE_BOT_USER and config.WIKIBASE_BOT_PASSWORD):
                return NO_BOT
            return wikibase_dry_run_refusal(con, wikibase_dir(args), args)
    if step == "publish" and not args.get("dry_run"):
        if not args.get("dry_run_id"):
            return NEEDS_CONFIRM.format(what="publish")
        return publish_dry_run_refusal(args)
    return None


def wikibase_api(on_write=None):
    """The API client of a real push (``push.Api``, the bot password from the environment), calling ``on_write``
    after each write so the job can show its progress through a pass."""
    from ..publish import push as P
    api = P.Api(config.WIKIBASE_URL, config.WIKIBASE_BOT_USER, config.WIKIBASE_BOT_PASSWORD, dry_run=False)
    if on_write is not None:
        edit = api.edit

        def counted(*a, **k):
            res = edit(*a, **k)
            on_write()
            return res
        api.edit = counted
    return api


def _pass_writes(summary: dict, pass_no: str) -> int:
    counts = (summary.get("counts") or {}).get(pass_no) or {}
    keep = ("create",) if pass_no == "1" else ("update", "clear")
    return sum(n for c in counts.values() for a, n in c.items() if a in keep)


def run_wikibase(con, args, log, progress):
    """Plan, or with ``really`` perform, the two-pass API push of the schema-v2 graph (``lexflow.publish.push``,
    the same code as ``lexflow wikibase push``), in ``wikibase_dir`` (``out`` names another directory).

    A job is a dry run unless its args carry ``really: true`` (a ``dry_run`` flag wins over it): the plan goes to
    ``push-plan.json``, nothing is POSTed, and a record of the dry run (``dry-run.json``: its numbers, its scope, the
    graph hash, the Wikibase record and the held keys it planned with) goes beside it.  ``passes`` ("1,2", "1" or
    "2") runs a fresh lint first (``lexflow wikibase lint``, deterministic, keeping the model's flags of the last
    report unless ``lint_model``), then the plan (a dry run) or those passes one after the other (a real push), with
    progress through each pass.  Without ``passes`` a real push runs both passes against the lint report already
    there, as the CLI does.

    A real push is refused, before anything is written, unless: the bot password is set; a lint report is there (or
    this job made one); it
    holds nothing, or ``skip_held`` (the default) is on, and held items are never written either way; and a dry run of
    the same scope (states, drafts, full) was recorded in the last 24 hours, was not used by a push since, was the one
    confirmed (``dry_run_id``, when given), and still fits: the same graph hash, the same Wikibase record (no other
    push since) and the same held keys.  The dry run's record is marked used before the first write.  Draft
    (single-tier) models stay out unless ``drafts`` is set; ``full`` resends every item instead of skipping those
    whose content hash is already recorded (``--resume``).  Nothing here deletes or merges an item.

    The v1 loader this step used to run (``wikibase_lexipedia.Loader``: ``clear`` with the v1 statement set, then
    ``retire_drafts``) is gone.  Job 77 (2026-10-18) ran it over 1,795 items the v2 pusher had written and wiped
    their schema-v2 claims; nothing reachable from a job writes the v1 shape any more.
    """
    import os
    from ..publish import graph as G
    from ..publish import lint as L
    from ..publish import push as P
    sts = S.parse_states(args["states"]) if args.get("states") else None
    out_dir = wikibase_dir(args)
    really = bool(args.get("really")) and not args.get("dry_run")
    skip_held = flag(args.get("skip_held"), True)
    passes = parse_passes(args.get("passes"))
    drafts, resume = bool(args.get("drafts")), not args.get("full")
    lint_model = flag(args.get("lint_model"), False)
    site = config.WIKIBASE_URL

    def refused(why):
        log(f"push refused: nothing was written to {site}, because {why}")
        progress(1.0)
        return {"refused": why, "dry_run": True, "really": False, "plan": None, "api_writes": 0}

    if really:
        # what needs nothing built: the bot password, a lint report (unless this job makes one) and a recent dry run
        why = (NO_BOT if not (config.WIKIBASE_BOT_USER and config.WIKIBASE_BOT_PASSWORD) else None) or (
            None if passes else wikibase_push_refusal(out_dir, skip_held)) or wikibase_dry_run_refusal(con, out_dir,
                                                                                                        args)
        if why:
            return refused(why)
    else:
        log(f"dry run: the plan goes to {out_dir / P.PLAN_NAME} and nothing is written to {site} (a push may follow "
            "this dry run for 24 hours, once its numbers are confirmed)")
    progress(0.01)
    items = G.build(con, states=sts, drafts=drafts, log=log)
    ghash = graph_hash(items)
    log(f"graph: {len(items):,} items, hash {ghash}")
    progress(0.05)
    lint_out = None
    if passes:
        log("== lint" + (" (with the model pass)" if lint_model else " (rules; the model's flags of the last report kept)"))
        report = L.run(con, ollama=lint_model, reuse=not lint_model, states=sts, drafts=drafts, items=items,
                       out_dir=out_dir, log=log)
        lint_out = {"held": report.get("held_count"), "findings_by_code": report.get("findings_by_code") or {},
                    "generated": report.get("generated")}
        progress(0.15)
    held = P.held_keys(P.read_lint(out_dir / P.LINT_NAME))
    start = 0.15 if passes else 0.05
    if not really:
        mark = ids_mark(con)
        out = P.run(con, dry_run=True, items=items, states=sts, drafts=drafts, resume=resume, allow_held=False,
                    out_dir=out_dir, log=log)
        progress(1.0)
        s = out.get("summary") or {}
        rid, generated = new_record_id()
        lint_report = P.read_lint(out_dir / P.LINT_NAME) or {}
        rec = {"id": rid, "generated": generated, "kind": "wikibase", "site": site, "scope": wikibase_scope(args),
               "graph_hash": ghash, "ids_mark": mark, "held_hash": held_hash(held), "held_count": len(held),
               "held_examples": sorted(held)[:20], "linted": bool(passes), "lint_generated": lint_report.get("generated"),
               "items": out.get("items", len(items)), "creates": s.get("creates"), "updates": s.get("updates"),
               "held_skipped": len(s.get("held_skipped") or ()), "dropped_snaks": s.get("dropped_snaks"),
               "failures_by_code": s.get("failures_by_code") or {},
               "properties_to_create": len(s.get("properties_to_create") or ()),
               "pass1_writes": _pass_writes(s, "1"), "pass2_writes": _pass_writes(s, "2"), "plan": out.get("plan"),
               "job": os.environ.get("LEXFLOW_JOB_ID") or None}
        write_record(out_dir / DRY_RUN_NAME, rec)
        log(f"dry run {rid}: {rec['creates']} creates, {rec['updates']} updates, {len(held)} held by the lint, "
            f"{rec['dropped_snaks']} statements dropped for want of an id; a push of this scope may follow for 24 hours")
        return {"dry_run": out.get("dry_run", True), "really": False, "items": out.get("items"), "plan": out.get("plan"),
                "creates": s.get("creates"), "updates": s.get("updates"), "held_skipped": rec["held_skipped"],
                "dropped_snaks": s.get("dropped_snaks"), "failures_by_code": s.get("failures_by_code"),
                "api_writes": out.get("api_writes"), "seconds": out.get("seconds"), "dry_run_id": rid,
                "lint": lint_out}
    why = wikibase_push_refusal(out_dir, skip_held) or wikibase_dry_run_refusal(con, out_dir, args, graph=ghash,
                                                                                held=held)
    if why:
        return refused(why)
    rec_path = out_dir / DRY_RUN_NAME
    rec = read_record(rec_path)
    use_record(rec_path, rec)                     # one dry run, one push: marked before the first write
    log(f"real push to {site} after the dry run of {rec['generated']} ({rec.get('creates')} creates, "
        f"{rec.get('updates')} updates)" + (f"; {len(held)} held items are skipped and never written" if held else
                                            "; the lint report holds nothing"))
    todo = passes or ["all"]
    expect = {"1": rec.get("pass1_writes") or 0, "2": rec.get("pass2_writes") or 0}
    expect["all"] = expect["1"] + expect["2"]
    # each pass's share of the progress bar: its writes in the dry run's plan (equal shares when it gave none)
    weights = [expect[p] for p in todo] if any(expect[p] for p in todo) else [1] * len(todo)
    bounds, at = [], start
    for w in weights:
        bounds.append((at, at + (1.0 - start) * w / sum(weights)))
        at = bounds[-1][1]
    results = {}
    for p, (lo, hi) in zip(todo, bounds):
        n = [0]

        def tick(lo=lo, hi=hi, want=expect[p], n=n):
            n[0] += 1
            if want:
                progress(lo + (hi - lo) * min(1.0, n[0] / want))
        log(f"== pass {p}" + (f": about {expect[p]:,} writes planned" if expect[p] else ""))
        out = P.run(con, dry_run=False, pass_no=p, items=items, states=sts, drafts=drafts, resume=resume,
                    allow_held=bool(held) and skip_held, out_dir=out_dir, api=wikibase_api(tick), log=log)
        progress(hi)
        s = out.get("summary") or {}
        results[p] = {"creates": s.get("creates"), "updates": s.get("updates"),
                      "held_skipped": len(s.get("held_skipped") or ()), "dropped_snaks": s.get("dropped_snaks"),
                      "failures_by_code": s.get("failures_by_code") or {}, "api_writes": out.get("api_writes"),
                      "seconds": out.get("seconds"), "plan": out.get("plan")}
    fails: dict[str, int] = {}
    for r in results.values():
        for k, v in r["failures_by_code"].items():
            fails[k] = fails.get(k, 0) + v
    last = results[todo[-1]]
    return {"dry_run": False, "really": True, "items": len(items), "plan": last["plan"], "passes": results,
            "creates": sum(r["creates"] or 0 for r in results.values()),
            "updates": sum(r["updates"] or 0 for r in results.values()),
            "held_skipped": max(r["held_skipped"] for r in results.values()),
            "dropped_snaks": max(r["dropped_snaks"] or 0 for r in results.values()), "failures_by_code": fails,
            "api_writes": sum(r["api_writes"] or 0 for r in results.values()),
            "seconds": round(sum(r["seconds"] or 0 for r in results.values()), 1), "dry_run_id": rec["id"],
            "lint": lint_out}


def run_publish(con, args, log, progress):
    """Post the lexflow: pages to the wiki (lexipedia.xyz) over JSON-RPC.  Only the lexflow: namespace is ever
    written (dokuwiki.require_namespace, the same rule the DokuWiki client enforces); a dry run renders and checks
    every page and reports what would change, without saving.  Nothing at all is written (a dry run included) while
    lexflow:method's corrections line is still the operator's placeholder: every page links lexflow:method for its
    sources, licences and corrections, so the operator sets LEXFLOW_CORRECTIONS (an e-mail address or a URL)
    first.

    A dry run reads the current text of each page (reads only, when a token is set and ``compare`` is not off) to
    count the pages that would change, and records its numbers and the hash of the pages (``dry-run.json`` in
    ``publish_dir``).  A real publish is refused, before anything is written, unless such a dry run was recorded in
    the last 24 hours, was not used by a publish since, was the one confirmed (``dry_run_id``, when given) and was of
    the same pages; its record is marked used before the first write.  No page is ever deleted."""
    import os
    from ..publish import lexipedia as LX
    from ..publish.dokuwiki import DokuWiki, require_namespace
    dry = bool(args.get("dry_run"))
    pages = LX.all_pages(con)
    for pid in pages:                       # every id before the first write, so nothing is half-published
        require_namespace(pid, LX.NS)
    if not LX.corrections_set():
        what = LX.corrections_problem()
        log(f"publish refused: no page {'would be' if dry else 'was'} written, because LEXFLOW_CORRECTIONS is {what} "
            f"and every page links {LX.METHOD}, whose corrections line would read "
            f"'{LX.CORRECTIONS_PLACEHOLDER}'; set it to the address readers should write to (an e-mail address or "
            f"an http(s) URL on a real domain), then publish again.")
        progress(1.0)
        return {"written": [], "unchanged": [], "refused": sorted(pages), "dry_run": dry,
                "reason": f"LEXFLOW_CORRECTIONS is {what}", "index": None}
    # the operator sees the address every page sends readers to before anything is written
    log(f"{LX.METHOD} {'would print' if dry else 'prints'} '{LX.corrections()}': readers will write to "
        f"{LX.corrections_address()}")
    phash = pages_hash(pages)
    rec_path = publish_dir() / DRY_RUN_NAME
    if not dry:
        why = publish_dry_run_refusal(args, pages=phash)
        if why:
            log(f"publish refused: no page was written to {config.DOKUWIKI_URL or 'the wiki'}, because {why}")
            progress(1.0)
            return {"written": [], "unchanged": [], "refused": sorted(pages), "dry_run": False, "reason": why,
                    "index": None}
    wiki = DokuWiki(config.DOKUWIKI_URL, token=config.DOKUWIKI_TOKEN, dry_run=dry)
    reader = None
    if dry and flag(args.get("compare"), True) and config.DOKUWIKI_URL and config.DOKUWIKI_TOKEN:
        reader = DokuWiki(config.DOKUWIKI_URL, token=config.DOKUWIKI_TOKEN)     # get_page only: never saves
        log(f"reading the current text of {len(pages):,} pages from {config.DOKUWIKI_URL} to count what would change "
            "(reads only)")
    if not dry:
        who = wiki.whoami()
        log(f"signed in to {config.DOKUWIKI_URL} as {who.get('login') if isinstance(who, dict) else who}")
        use_record(rec_path, read_record(rec_path))      # one dry run, one publish: marked before the first write
    todo = sorted(pages.items())
    done, unchanged, unread = [], [], []
    misses = 0
    for i, (pid, text) in enumerate(todo):
        current = None
        if not dry:
            current = wiki.get_page(pid)
        elif reader is not None and misses < 3:
            try:
                current, misses = reader.get_page(pid), 0
            except Exception as e:  # noqa: BLE001 - a dry run counts what it can read
                misses += 1
                unread.append(pid)
                if misses == 3:
                    log(f"could not read {pid} ({type(e).__name__}): the pages left are counted as would-write")
        elif reader is not None:
            unread.append(pid)
        if current is not None and current.strip() == text.strip():
            unchanged.append(pid)
        else:
            wiki.save_page(pid, text, summary="lexflow: drafted with an AI system; quotes matched to Open US Law's "
                                              "copy of the statute text")
            done.append(pid)
        log(f"{'unchanged' if pid not in done else 'would write' if dry else 'wrote'} {pid} ({len(text):,} chars)")
        progress((i + 1) / len(todo))
    if dry:
        rid, generated = new_record_id()
        write_record(rec_path, {
            "id": rid, "generated": generated, "kind": "publish", "site": config.DOKUWIKI_URL or None,
            "namespace": LX.NS, "corrections": LX.corrections_address(), "pages": len(pages), "pages_hash": phash,
            "would_write": len(done), "unchanged": len(unchanged), "unread": len(unread), "compared": reader is not None,
            "job": os.environ.get("LEXFLOW_JOB_ID") or None})
        log(f"dry run {rid}: {len(done):,} of {len(pages):,} pages would be written"
            + (f", {len(unchanged):,} unchanged" if reader is not None else " (the current pages were not read)")
            + (f", {len(unread):,} could not be read" if unread else "") + "; a publish may follow for 24 hours")
    else:
        ts = db.now()
        for r in db.rows(con, "SELECT model_id, stages FROM process_models WHERE tier IN ('reviewed','agreed')"):
            stages = db.loads(r["stages"], {})
            stages["published"] = stages.get("published") or ts
            done_n = sum(1 for v in stages.values() if v)
            con.execute("UPDATE process_models SET stages=?, completion=?, updated_at=? WHERE model_id=?",
                        (json.dumps(stages), round(done_n / len(M.STAGES), 3), ts, r["model_id"]))
        db.bump(con)
        con.commit()
    return {"written": done, "unchanged": unchanged, "refused": [], "dry_run": dry, "unread": unread,
            "dry_run_id": rid if dry else None,
            "index": f"{config.DOKUWIKI_URL.rstrip('/')}/doku.php?id={LX.NS}:start" if config.DOKUWIKI_URL else None}


def run_sync(con, args, log, progress):
    """Push or pull the shared tables.  Only the tables in db.SYNCED are taken: any other (the reviewer list, the
    review log, jobs ...) is refused before the shared database is reached (turso.check_tables)."""
    direction = args.get("direction", "push")
    if direction not in ("push", "pull"):
        raise ValueError(f"direction is push or pull, not {direction!r}")
    tables = T.check_tables(args.get("tables"))
    client = T.Turso.from_env()
    if client is None:
        raise RuntimeError("TURSO_DATABASE_URL is not set")
    sts = S.parse_states(args["states"]) if args.get("states") else None
    started = db.now()
    try:
        fn = T.push if direction == "push" else T.pull
        counts = fn(con, client, tables=tables, states=sts, full=bool(args.get("full")), log=log)
        T.log_sync(con, direction, tables, sts, counts, True, "ok", started)
        return counts
    except Exception as e:
        T.log_sync(con, direction, tables, sts, None, False, str(e)[:500], started)
        raise


def run_local(con, args, log, progress):
    """Load checked local answers (curated/places/*/*.json) for the places named, or all of them."""
    from ..municipal import places as P
    out = P.load_local(con, _places(con, args), log=log)
    progress(1.0)
    return out


def run_quickstart(con, args, log, progress):
    """Tick every required box in order: governments, statutes, locate, build, score.
    With ``places``, also scan those governments' websites and load their local answers."""
    plan = [("statutes", run_statutes), ("locate", run_locate), ("contacts", run_contacts)]
    if not db.scalar(con, "SELECT count(*) FROM governments", default=0) or not args.get("places"):
        plan.insert(0, ("governments", run_governments))
    if args.get("places"):
        plan += [("crawl", run_crawl), ("local", run_local)]
    plan += [("build", run_build), ("score", run_score)]
    out = {}
    for i, (name, fn) in enumerate(plan):
        log(f"== {STEPS[name].title}")
        out[name] = fn(con, args, log, lambda p, i=i: progress((i + p) / len(plan)))
    return out


STEPS: dict[str, Step] = {s.id: s for s in [
    Step("governments", "Load every county, city and town",
         "The Census of Governments 2022 list: 38,736 general-purpose governments with an official's title, "
         "address, website and FIPS codes. Everything else is keyed to it.",
         "required", st_governments, run_governments, cost="11.5 MB download, under a minute",
         credits=[C.CENSUS_GUS, C.OPENPYXL]),
    Step("statutes", "Download state statutes",
         "open-us-law (Vaquill AI): one verified parquet file per state, each section with the URL of its government "
         "publisher. Arkansas, Colorado, Georgia, Mississippi and Tennessee are not in the current release.",
         "required", st_statutes, run_statutes, params=["states", "regulations"],
         cost="867 MB for all states (VA 17 MB); regulations add 2.1 GB",
         credits=[C.OPEN_US_LAW]),
    Step("index", "Make the statutes searchable",
         "A full-text index (SQLite FTS5) over every downloaded section, one file per state, so new questions can be "
         "answered for any state: search by heading, chapter and text, and read any section without loading the "
         "whole statute file.", "recommended", st_index, run_index, needs=["statutes"], params=["states", "force"],
         cost="about 4 GB on disk for all states; seconds per state",
         credits=[C.SQLITE_FTS5]),
    Step("regulations", "Make the state regulations searchable",
         "The same full-text index as the statutes', over each state's regulations in force from open-us-law's "
         "regulations add-on: building codes, tax and licensing rules, each section with the URL of its official "
         "publisher, so a question such as whether a shed needs a building permit can find the rule. Superseded "
         "versions and repealed stubs are left out, and no model-code text is stored. Reads only the files already "
         "on disk.", "optional", st_regulations, run_regulations, needs=["statutes"], params=["states", "force"],
         cost="no download where the regulations add-on is already on disk; seconds per state (under a minute for "
              "the largest, Puerto Rico), about 4.4 GB on disk for the 39 states with a file. On a fresh install, run "
              "Download state statutes with + regulations first: about 640 MB of regulations files for those 39 "
              "states",
         credits=[C.OPEN_US_LAW_REGS,
                  C.used_for(C.SQLITE_FTS5, "The regulations index, one file per state beside the statutes', ranked "
                                            "with BM25")]),
    Step("locate", "Find the state law for each question",
         "Ranks every section by title, chapter and text; a known section number is used only if it is found, in "
         "force and on topic. The method and a confidence score are stored with each result.",
         "required", st_locate, run_locate, needs=["statutes"], params=["states", "questions"], cost="seconds per state",
         credits=[C.used_for(C.OPEN_US_LAW, "The sections it ranks; each result cites the section's official "
                                            "publisher")]),
    Step("contacts", "Find contacts on Wikidata",
         "Official websites, emails and phone numbers from Wikidata (the data behind govdirectory.org), matched by "
         "FIPS code.", "recommended", st_contacts, run_contacts, needs=["governments"], params=["states"],
         cost="two queries per state",
         credits=[C.WIKIDATA, C.GOV_DIRECTORY]),
    Step("models", "Pull the local models",
         f"{config.EMBED_MODEL} gives the learned selector its clause embeddings; {config.MODEL_A} writes plain-"
         f"language answers to new questions and makes the independent second extraction ({config.MODEL_B} is the "
         "other family). Needs the Ollama service ('llm' profile).",
         "recommended", st_models, run_models, cost="about 2.5 GB; a GPU helps a lot",
         # the models config names (LEXFLOW_EMBED_MODEL, LEXFLOW_MODEL_A, LEXFLOW_MODEL_B), not fixed ones
         credits=[C.OLLAMA, *C.model_credits([
             (config.EMBED_MODEL, "Clause embeddings for the learned selector; similarity in Ask"),
             (config.MODEL_A, "Plain-language answers and the independent second extraction"),
             (config.MODEL_B, "The other model family for the second extraction and the benchmark")])]),
    Step("build", "Build the state process models",
         "Claude's reference facts first; otherwise the learned selector (trained on the references for the other "
         "states) picks quote-anchored steps from the located and related sections, compiled to BPMN and DMN and "
         "checked (schemas, bpmnlint, quotes, Petri-net soundness). With a chat model, an independent second "
         "extraction cross-checks it.",
         "required", st_build, run_build, needs=["locate"], params=["states", "places", "questions", "force", "no_llm"],
         cost="minutes per state on CPU",
         credits=[C.CLAUDE, C.OMG_SCHEMAS, C.BPMNLINT, C.CAMUNDA_COMPAT, C.DMNLINT, C.BPMN_AUTO_LAYOUT, C.MODDLE,
                  C.PM4PY, C.PULP, C.CBC, C.POWL, C.SPIFFWORKFLOW]),
    Step("local", "Load checked local answers",
         "Local procedures researched for particular places (curated/places/<state>/<place>.json): portals, "
         "offices, local ordinances and fees, each with its source. Scored as local law and contacts.",
         "optional", lambda con: st_local(con), run_local, needs=["governments"], params=["places"],
         cost="seconds",
         credits=[], credits_note="No outside dataset: each answer was researched from the place's own official "
                                  "pages and carries the URL it came from."),
    Step("score", "Score every government and refresh the maps",
         "Confidence = state law + local law + contacts, with the weights on the Method page.",
         "required", st_score, run_score, needs=["governments"], params=["states", "places"], cost="seconds",
         credits=[C.US_ATLAS]),
    Step("crawl", "Look for records and licence pages on official websites",
         "Reads each government's home page (robots.txt respected) for a public-records page, a business-licence "
         "page, and email or phone links.", "optional", st_crawl, run_crawl, needs=["governments"],
         params=["states", "places", "force"], cost="about 1 request per government; a few minutes per state",
         credits=[], credits_note="No outside dataset: it reads each government's own official website, with "
                                  "robots.txt respected."),
    Step("locus", "Scan local ordinances (LOCUS-v1)",
         "Finds local ordinances on public records and business licences for each city and county. LOCUS is "
         "CC BY-NC and machine-labelled, so this step uses it to find law, never to cite it.",
         "optional", st_locus, run_locus, needs=["governments"], params=["states"],
         cost="ranged reads of a 1.8 GB dataset",
         credits=[C.LOCUS, C.HF_HUB, C.HF_HUB_LIB]),
    Step("cases", "Find court decisions that cite the law",
         "Searches CourtListener (Free Law Project) for opinions in each state's appellate courts that cite the "
         "sections behind its models. Shown on model pages, the wiki and the Wikibase.",
         "optional", st_cases, run_cases, needs=["build"], params=["states", "places", "force"],
         cost="paced to CourtListener's limits for an account (5 requests a minute, 50 an hour, 125 a day): one or "
              "two requests per section, about 12 for a typical state, so about four states an hour and ten a day; "
              "a run stops when the day's 125 are used, and the next run (states box empty, or 'all') goes on from "
              "the states not done yet. A state whose search failed is searched again; Redo also searches the done "
              "states again, oldest search first",
         credits=[C.COURTLISTENER]),
    Step("wikibase", "Push the graph to the Lexipedia Wikibase",
         "Plans the two-pass API push of the schema-v2 graph (the same as lexflow wikibase push): statutes and "
         "codes, the reviewed and agreed processes with their roles, steps, decisions, outcomes, forms and "
         "escalation rungs, agencies, jurisdictions and the court decisions that cite the sections. A job is a dry "
         "run, with the plan in data/wikibase-push/push-plan.json, unless it is started with 'Write to the wiki'; a "
         "real push needs a dry run of the same graph from the last 24 hours, its numbers confirmed on the Pipeline "
         "page, and a lint report (lexflow wikibase lint): items the lint holds are skipped and never written. "
         "Drafts from one extraction stay out unless asked for. Never part of a run-all chain.",
         "optional", st_wikibase, run_wikibase, needs=["build"],
         params=["states", "really", "drafts", "full", "skip_held", "passes"],
         cost="dry run: about a minute of reads; a real push about 1.5 s a write (pass 1 creates, pass 2 claims)",
         credits=[C.WIKIBASE_CLOUD, C.used_for(C.WIKIDATA, "Items link to their Wikidata entities", note="")]),
    Step("publish", "Publish to Lexipedia",
         "Writes the lexflow: pages (process maps, places, start and method) to DokuWiki over JSON-RPC (bot account, "
         "API limited to @bots), and no page outside that namespace. Nothing is written until the operator sets "
         "the corrections address (LEXFLOW_CORRECTIONS, an e-mail address or a URL), which lexflow:method gives "
         "and every page links. A real publish needs a dry run of the same pages from the last 24 hours, its "
         "numbers confirmed on the Pipeline page.",
         "optional", st_publish, run_publish, needs=["build"], params=["dry_run"],
         credits=[C.DOKUWIKI, C.BPMNIO_PLUGIN]),
    Step("ontology", "Tag sections with ontology types",
         "For every section of a state's statute index: its place in the code's hierarchy as an Akoma Ntoso "
         "element (title, chapter, article, section), its ELI-style identifier, and which LKIF norm types it "
         "carries (definition, obligation, permission, prohibition, power, penalty, procedure). Rules give the "
         "structure and identifier; the norm types come from cue phrases, with the local decision model's yes/no "
         "answers on the section head and first 1,500 characters when asked for. Kept in this copy's own "
         "section_tags table (docs/design/legal-ontologies.md).",
         "optional", st_ontology, run_ontology, needs=["index"], params=["states", "force", "no_llm"],
         cost="rules: about a minute per state, every state in under an hour; with the decision model about "
              "12 s per section on this CPU (seven yes/no questions in one call; budget 200 calls per run by default), so a "
              "model pass over a whole state is days and over all states months; see the doc's estimate",
         credits=[C.used_for(C.SQLITE_FTS5, "The index whose sections and paths are tagged"),
                  C.credit("LKIF-Core", "Hoekstra, Breuker, Di Bello, Boer (ESTRELLA project)", "CC BY 4.0",
                           "https://github.com/RinkeHoekstra/lkif-core", "The norm types a section is tagged with "
                           "(Obligation, Permission, Prohibition, Definitional_Expression, Hohfeldian_Power)",
                           licence_url="https://github.com/RinkeHoekstra/lkif-core/blob/master/LICENSE"),
                  C.credit("Akoma Ntoso 1.0 (LegalDocML)", "OASIS LegalDocML TC", "OASIS RF on Limited Terms",
                           "https://docs.oasis-open.org/legaldocml/akn-core/v1.0/os/part1-vocabulary/"
                           "akn-core-v1.0-os-part1-vocabulary.html",
                           "The hierarchy element names a section's structure is tagged with",
                           licence_url="https://www.oasis-open.org/policies-guidelines/ipr/"),
                  C.credit("European Legislation Identifier (ELI) ontology", "Publications Office of the EU",
                           "EU reuse policy (Commission Decision 2011/833/EU)", "https://data.europa.eu/eli/ontology",
                           "The identifier template and the LegalResource / LegalResourceSubdivision types",
                           licence_url="https://op.europa.eu/en/web/eu-vocabularies/eli"),
                  *C.model_credits([(config.DECIDE_MODEL, "Yes/no norm-type answers when the model pass is asked for"),
                                    (config.DECIDE_FALLBACK, "The chat fallback for the same answers")])]),
    Step("sync", "Share through Turso",
         "Push your results to a shared Turso (libSQL) database, or pull states other people have built.",
         "optional", st_sync, run_sync, params=["direction", "states", "tables", "full"],
         credits=[C.LIBSQL, C.TURSO_CLOUD]),
]}

def run_benchmark(con, args, log, progress):
    """Score extraction strategies x local models against Claude's reference models."""
    from ..extract import benchmark as BM
    from ..extract.strategies import STRATEGIES
    case_list = [c.strip() for c in (args.get("cases") or "").split(",") if c.strip()] or BM.cases()
    strategy_list = [s.strip() for s in (args.get("strategies") or "").split(",") if s.strip()] or \
        [s for s in STRATEGIES if s != "oneshot"]
    model_list = [m.strip() for m in (args.get("models") or "").split(",") if m.strip()] or \
        [config.MODEL_A, config.MODEL_B]
    log(f"benchmark: {len(case_list)} cases x {len(strategy_list)} strategies x {len(model_list)} models")
    return BM.run(con, case_list, strategy_list, model_list, log=log, progress=progress, node=args.get("node") or None)


def run_coverage(con, args, log, progress):
    """The coverage test (lexflow.ask.coverage): for every question people ask x state (x place), the Wikibase
    probe, the Ollama answer scored against the gold, and a verdict; writes docs/coverage-<run>.json and
    docs/coverage.md.  ``arm``: coverage | ollama; ``llm_cells``: Ollama answers for that many state cells per
    state; ``node``: a node of LEXFLOW_LLM_NODES; ``run``: a run id to resume; ``local``: probe the local store;
    ``fill``: answer the gap cells of the run with the ask pipeline instead (``llm_cells`` caps the cells per state);
    ``cells``: gaps | filled (the cells another model filled, for a comparison) | all | named (the ``questions``
    cells, filled or not)."""
    from ..ask import coverage as CV
    sts = _states(args, con)
    qids = [q.strip() for q in (args.get("questions") or "").split(",") if q.strip()] or None
    llm = args.get("llm_cells")
    if args.get("fill"):
        # the gap-filling loop: answer the gap cells of the run (the latest unless ``run`` names one) with the
        # ask pipeline; ``llm_cells`` caps the cells per state
        return CV.fill(con, sts, run_id=args.get("run") or None, qids=qids,
                       llm_cells=int(llm) if llm not in (None, "") else None, node=args.get("node") or None,
                       model=args.get("model") or None, force=bool(args.get("force")), log=log, progress=progress,
                       cells=args.get("cells") or "gaps")
    return CV.run(con, sts, _places(con, args), qids, arm=args.get("arm") or "ollama",
                  llm_cells=int(llm) if llm not in (None, "") else None, run_id=args.get("run") or None,
                  node=args.get("node") or None, live=not args.get("local"), force=bool(args.get("force")),
                  model=args.get("model") or None, log=log, progress=progress,
                  computed=bool(args.get("computed")), docs_dir=args.get("docs_dir") or None)


COMPOSITE = {
    "coverage": Step("coverage", "Test coverage of the questions people ask",
                     "For each of the 36 plain-language questions (fixtures/coverage/questions.json) and each state "
                     "or place: is there a Wikibase process for the topic, with bearers, bodies, channels, deadlines, "
                     "forms, fees and escalation; can the local model answer it from the statute index plus those "
                     "facts; how does the answer score against the gold (curated_ask/coverage/). Writes the matrix "
                     "docs/coverage.md and shows it on the Coverage page.", "optional", lambda con: {}, run_coverage,
                     params=["states", "places", "questions", "arm", "node", "force", "fill", "cells"],
                     cost="coverage-only: seconds per cell (the live endpoint, one request a second); with the Ollama "
                          "answer a few minutes per cell on this CPU; --fill answers each gap cell with the ask "
                          "pipeline (a minute or two per cell)",
                     credits=[C.used_for(C.OPEN_US_LAW, "The statutes it searches and quotes"),
                              C.used_for(C.SQLITE_FTS5, "Searches each state's statutes"),
                              *C.model_credits([(config.ASK_MODEL, "Writes the plain-language summary that is scored"),
                                                (config.EMBED_MODEL, "Similarity between the question and each clause")]),
                              C.used_for(C.CLAUDE, "Wrote the gold the answers are scored against")]),
    "quickstart": Step("quickstart", "Run all required steps", "Governments, statutes, law, contacts, "
                       "models and scores in one job.", "required", lambda con: {}, run_quickstart,
                       params=["states", "places", "no_llm", "node"],
                       credits=[], credits_note="Runs the steps above; their credits apply."),
    "ask": Step("ask", "Answer a new question", "Searches each state's statutes for the question, quotes the "
                "sections that answer it, extracts the steps, and adds each place's local layer.", "optional",
                lambda con: {}, run_ask, params=["question", "targets", "model", "no_llm", "node"],
                credits=[C.used_for(C.OPEN_US_LAW, "The statutes it searches and quotes"),
                         C.used_for(C.SQLITE_FTS5, "Searches each state's statutes"), C.SEARXNG,
                         *C.model_credits([(config.ASK_MODEL, "Writes the plain-language answers"),
                                           (config.EMBED_MODEL, "Similarity between the question and each clause")]),
                         C.used_for(C.CLAUDE, "Wrote the reference answers AskBench scores against")]),
    "benchmark": Step("benchmark", "Benchmark local models against Claude",
                      "Runs each extraction strategy with each local model on every curated case and scores it "
                      "against Claude's reference model.", "optional", lambda con: {}, run_benchmark,
                      params=["cases", "strategies", "models", "node"],
                      credits=[C.used_for(C.CLAUDE, "Wrote the reference models every run is scored against"),
                               *C.model_credits([(config.MODEL_A, "One of the local models scored"),
                                                 (config.MODEL_B, "One of the local models scored")]),
                               C.OLLAMA]),
}


def checklist(con) -> list[dict]:
    out = []
    statuses = {}
    for s in STEPS.values():
        try:
            st = s.status(con)
        except Exception as e:  # noqa: BLE001
            st = {"status": "todo", "done": 0, "total": 0, "detail": f"status check failed: {e}"}
        statuses[s.id] = st["status"]
        if st["status"] in ("todo", "optional") and any(statuses.get(n) not in ("done", "partial") for n in s.needs):
            st["status"] = "blocked" if s.level == "required" else st["status"]
        out.append({"id": s.id, "title": s.title, "why": s.why, "level": s.level, "needs": s.needs,
                    "params": s.params, "cost": s.cost, "runnable": s.run is not None, **st})
    return out


def get_step(step_id: str) -> Step:
    if step_id in STEPS:
        return STEPS[step_id]
    if step_id in COMPOSITE:
        return COMPOSITE[step_id]
    raise KeyError(step_id)
