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


def _scan_count(con, source: str) -> int:
    return db.scalar(con, "SELECT count(*) FROM scans WHERE source=? AND status='done'", source, default=0)


def _mark_scan(con, source: str, state: str, rows: int = 0, matched: int = 0):
    db.upsert(con, "scans", [{"source": source, "state": state, "rows": rows, "matched": matched, "status": "done",
                              "scanned_at": db.now()}], keys=("source", "state"), stamp=False)
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


def run_ask(con, args, log, progress):
    """Answer a new question for the chosen states and places (lexflow/ask)."""
    from ..ask import pipeline as AP
    targets = args.get("targets") or []
    if isinstance(targets, str):
        targets = [t for t in targets.split(",") if t.strip()]
    return AP.run(con, args["question"], targets, model=args.get("model"), use_llm=not args.get("no_llm"),
                  log=log, progress=progress, question_id=args.get("question_id"))


def st_cases(con):
    models = db.rows(con, "SELECT DISTINCT state FROM process_models WHERE tier IN ('reviewed','agreed','single')")
    if not models:
        return {"status": "blocked", "done": 0, "total": 0, "detail": "Build state models first"}
    done = {r["state"] for r in db.rows(con, "SELECT DISTINCT state FROM case_law")}
    n = db.scalar(con, "SELECT count(*) FROM case_law", default=0)
    k = len(models)
    have = sum(1 for r in models if r["state"] in done)
    return {"status": "done" if have >= k else "partial" if have else "todo", "done": have, "total": k,
            "detail": f"{plural(n, 'court decision')} found for {plural(have, 'state')} with models"}


def st_publish(con):
    if not (config.DOKUWIKI_URL and config.DOKUWIKI_TOKEN):
        return {"status": "optional", "done": 0, "total": 0,
                "detail": "Set DOKUWIKI_URL and DOKUWIKI_TOKEN (a bot account) to enable"}
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
    out = {}
    want = list(dict.fromkeys((config.EMBED_MODEL, config.MODEL_A, config.MODEL_B)))
    for i, name in enumerate(want):
        log(f"pulling {name} into Ollama at {config.OLLAMA_URL}")
        with requests.post(f"{config.OLLAMA_URL.rstrip('/')}/api/pull", json={"model": name, "stream": True},
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


def run_cases(con, args, log, progress):
    from ..municipal import caselaw
    have = {r["state"] for r in db.rows(con, "SELECT DISTINCT state FROM process_models")} |         {r["state"] for r in db.rows(con, "SELECT DISTINCT state FROM located_law WHERE status='found' "
                                          "AND method IN ('seed','verified')")}
    sts = [s for s in _states(args, con) if s in have] if (args.get("states") or args.get("places")) else sorted(have)
    out = {}
    for i, st in enumerate(sts):
        try:
            out[st] = caselaw.run(con, st, log=log, progress=lambda p, i=i: progress((i + p) / len(sts)))
        except caselaw.RateLimited as e:
            log(f"stopped: {e}. Run this step again later; sections already searched keep their results.")
            out["stopped"] = str(e)
            break
    return out


def st_wikibase(con):
    if not (config.WIKIBASE_BOT_USER and config.WIKIBASE_BOT_PASSWORD):
        return {"status": "optional", "done": 0, "total": 0,
                "detail": f"Set WIKIBASE_BOT_USER and WIKIBASE_BOT_PASSWORD (a bot password on {config.WIKIBASE_URL})"}
    n = db.scalar(con, "SELECT count(*) FROM wikibase_items", default=0)
    return {"status": "done" if n else "todo", "done": n, "total": n,
            "detail": f"{plural(n, 'item')} on {config.WIKIBASE_URL}" if n else f"Ready to load {config.WIKIBASE_URL}"}


def run_wikibase(con, args, log, progress):
    from ..publish import wikibase_lexipedia as WL
    sts = S.parse_states(args["states"]) if args.get("states") else None
    out = WL.run(con, dry_run=bool(args.get("dry_run")), states=sts, log=log)
    progress(1.0)
    return out


def run_publish(con, args, log, progress):
    """Post the lexflow: pages to the wiki (lexipedia.xyz) over JSON-RPC.  Only the lexflow: namespace is ever
    written; a dry run renders and checks every page and reports what would change, without saving."""
    from ..publish.dokuwiki import DokuWiki
    from ..publish.lexipedia import NS, all_pages
    dry = bool(args.get("dry_run"))
    wiki = DokuWiki(config.DOKUWIKI_URL, token=config.DOKUWIKI_TOKEN, dry_run=dry)
    if not dry:
        who = wiki.whoami()
        log(f"signed in to {config.DOKUWIKI_URL} as {who.get('login') if isinstance(who, dict) else who}")
    pages = all_pages(con)
    done, unchanged = [], []
    for i, (pid, text) in enumerate(sorted(pages.items())):
        if not pid.startswith(f"{NS}:"):
            raise RuntimeError(f"refusing to write {pid}: outside the {NS}: namespace")
        current = None if dry else wiki.get_page(pid)
        if current is not None and current.strip() == text.strip():
            unchanged.append(pid)
        else:
            wiki.save_page(pid, text, summary="lexflow: Claude-checked process model and local answers")
            done.append(pid)
        log(f"{'would write' if dry else 'wrote' if pid in done else 'unchanged'} {pid} ({len(text):,} chars)")
        progress((i + 1) / len(pages))
    if not dry:
        ts = db.now()
        for r in db.rows(con, "SELECT model_id, stages FROM process_models WHERE tier IN ('reviewed','agreed')"):
            stages = db.loads(r["stages"], {})
            stages["published"] = stages.get("published") or ts
            done_n = sum(1 for v in stages.values() if v)
            con.execute("UPDATE process_models SET stages=?, completion=?, updated_at=? WHERE model_id=?",
                        (json.dumps(stages), round(done_n / len(M.STAGES), 3), ts, r["model_id"]))
        db.bump(con)
        con.commit()
    return {"written": done, "unchanged": unchanged, "dry_run": dry,
            "index": f"{config.DOKUWIKI_URL.rstrip('/')}/doku.php?id={NS}:start" if config.DOKUWIKI_URL else None}


def run_sync(con, args, log, progress):
    client = T.Turso.from_env()
    if client is None:
        raise RuntimeError("TURSO_DATABASE_URL is not set")
    direction = args.get("direction", "push")
    sts = S.parse_states(args["states"]) if args.get("states") else None
    tables = args["tables"].split(",") if args.get("tables") else None
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
         "required", st_governments, run_governments, cost="11.5 MB download, under a minute"),
    Step("statutes", "Download state statutes",
         "open-us-law (Vaquill AI): one verified parquet file per state, each section with the URL of its government "
         "publisher. Arkansas, Colorado, Georgia, Mississippi and Tennessee are not in the current release.",
         "required", st_statutes, run_statutes, params=["states", "regulations"],
         cost="867 MB for all states (VA 17 MB); regulations add 2.1 GB"),
    Step("index", "Make the statutes searchable",
         "A full-text index (SQLite FTS5) over every downloaded section, one file per state, so new questions can be "
         "answered for any state: search by heading, chapter and text, and read any section without loading the "
         "whole statute file.", "recommended", st_index, run_index, needs=["statutes"], params=["states", "force"],
         cost="about 4 GB on disk for all states; seconds per state"),
    Step("locate", "Find the state law for each question",
         "Ranks every section by title, chapter and text; a known section number is used only if it is found, in "
         "force and on topic. The method and a confidence score are stored with each result.",
         "required", st_locate, run_locate, needs=["statutes"], params=["states", "questions"], cost="seconds per state"),
    Step("contacts", "Find contacts on Wikidata",
         "Official websites, emails and phone numbers from Wikidata (the data behind govdirectory.org), matched by "
         "FIPS code.", "recommended", st_contacts, run_contacts, needs=["governments"], params=["states"],
         cost="two queries per state"),
    Step("models", "Pull the local models",
         f"{config.EMBED_MODEL} gives the learned selector its clause embeddings; {config.MODEL_A} writes plain-"
         f"language answers to new questions and makes the independent second extraction ({config.MODEL_B} is the "
         "other family). Needs the Ollama service ('llm' profile).",
         "recommended", st_models, run_models, cost="about 2.5 GB; a GPU helps a lot"),
    Step("build", "Build the state process models",
         "Claude's reference facts first; otherwise the learned selector (trained on the references for the other "
         "states) picks quote-anchored steps from the located and related sections, compiled to BPMN and DMN and "
         "checked (schemas, bpmnlint, quotes, Petri-net soundness). With a chat model, an independent second "
         "extraction cross-checks it.",
         "required", st_build, run_build, needs=["locate"], params=["states", "places", "questions", "force", "no_llm"],
         cost="minutes per state on CPU"),
    Step("local", "Load checked local answers",
         "Local procedures researched for particular places (curated/places/<state>/<place>.json): portals, "
         "offices, local ordinances and fees, each with its source. Scored as local law and contacts.",
         "optional", lambda con: st_local(con), run_local, needs=["governments"], params=["places"],
         cost="seconds"),
    Step("score", "Score every government and refresh the maps",
         "Confidence = state law + local law + contacts, with the weights on the Method page.",
         "required", st_score, run_score, needs=["governments"], params=["states", "places"], cost="seconds"),
    Step("crawl", "Look for records and licence pages on official websites",
         "Reads each government's home page (robots.txt respected) for a public-records page, a business-licence "
         "page, and email or phone links.", "optional", st_crawl, run_crawl, needs=["governments"],
         params=["states", "places", "force"], cost="about 1 request per government; a few minutes per state"),
    Step("locus", "Scan local ordinances (LOCUS-v1)",
         "Finds local ordinances on public records and business licences for each city and county. LOCUS is "
         "CC BY-NC and machine-labelled, so it is used to find law, never to cite it.",
         "optional", st_locus, run_locus, needs=["governments"], params=["states"],
         cost="ranged reads of a 1.8 GB dataset"),
    Step("cases", "Find court decisions that cite the law",
         "Searches CourtListener (Free Law Project) for opinions in each state's appellate courts that cite the "
         "sections behind its models. Shown on model pages, the wiki and the Wikibase.",
         "optional", st_cases, run_cases, needs=["build"], params=["states", "places"],
         cost="one request a second; about a minute per state"),
    Step("wikibase", "Load the Lexipedia Wikibase",
         "Statutes, process models and their steps, jurisdictions and the court decisions that cite them, as linked "
         "items in the wiki's own ontology (part of, follows, deontic modality, bearer, references).",
         "optional", st_wikibase, run_wikibase, needs=["build"], params=["states", "dry_run"],
         cost="one edit per item; a few minutes"),
    Step("publish", "Publish to Lexipedia",
         "Writes law and process pages to DokuWiki over JSON-RPC (bot account, API limited to @bots).",
         "optional", st_publish, run_publish, needs=["build"], params=["dry_run"]),
    Step("sync", "Share through Turso",
         "Push your results to a shared Turso (libSQL) database, or pull states other people have built.",
         "optional", st_sync, run_sync, params=["direction", "states", "tables", "full"]),
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
    return BM.run(con, case_list, strategy_list, model_list, log=log, progress=progress)


COMPOSITE = {
    "quickstart": Step("quickstart", "Run all required steps", "Governments, statutes, law, contacts, "
                       "models and scores in one job.", "required", lambda con: {}, run_quickstart,
                       params=["states", "places", "no_llm"]),
    "ask": Step("ask", "Answer a new question", "Searches each state's statutes for the question, quotes the "
                "sections that answer it, extracts the steps, and adds each place's local layer.", "optional",
                lambda con: {}, run_ask, params=["question", "targets", "model", "no_llm"]),
    "benchmark": Step("benchmark", "Benchmark local models against Claude",
                      "Runs each extraction strategy with each local model on every curated case and scores it "
                      "against Claude's reference model.", "optional", lambda con: {}, run_benchmark,
                      params=["cases", "strategies", "models"]),
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
