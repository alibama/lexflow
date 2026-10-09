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
    want = [config.MODEL_A, config.MODEL_B]
    have = [m for m in want if B._has(o["models"], m)]
    if not o["reachable"]:
        return {"status": "todo", "done": 0, "total": 2,
                "detail": f"Ollama not reachable at {config.OLLAMA_URL} (start it with the 'llm' profile)"}
    missing = [m for m in want if m not in have]
    parts = ([f"Ready: {', '.join(have)}"] if have else []) + ([f"Not pulled yet: {', '.join(missing)}"] if missing else [])
    return {"status": "done" if not missing else "partial" if have else "todo", "done": len(have), "total": 2,
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
def _states(args, con=None) -> list[str]:
    return S.parse_states(args.get("states"))


def run_governments(con, args, log, progress):
    return governments.load(con, log=log, progress=progress)


def run_statutes(con, args, log, progress):
    kinds = ("statutes", "regulations") if args.get("regulations") else ("statutes",)
    sts = _states(args)
    out = {}
    for i, st in enumerate(sts):
        out[st] = statutes.fetch_state(con, st, kinds=kinds, log=log)
        progress((i + 1) / len(sts))
    db.bump(con)
    con.commit()
    return {"downloaded": sum(v == "downloaded" for v in out.values()),
            "not_in_release": [k for k, v in out.items() if v != "downloaded"]}


def run_locate(con, args, log, progress):
    sts = [s for s in _states(args)]
    out = {}
    for i, qid in enumerate(QUESTIONS if not args.get("questions") else args["questions"].split(",")):
        out[qid] = locator.run(con, get_question(qid), sts, log=log)
        progress((i + 1) / len(QUESTIONS))
    return out


def run_contacts(con, args, log, progress):
    sts = [s for s in _states(args) if s in set(_gov_states(con))]
    out = {}
    for i, st in enumerate(sts):
        out[st] = contacts.wikidata(con, st, log=log)
        _mark_scan(con, "wikidata", st, matched=out[st]["matched"])
        progress((i + 1) / len(sts))
    return out


def run_crawl(con, args, log, progress):
    sts = [s for s in _states(args) if s in set(_gov_states(con))]
    out = {}
    for i, st in enumerate(sts):
        out[st] = crawl.run(con, st, force=bool(args.get("force")), log=log,
                            progress=lambda p, i=i: progress((i + p) / len(sts)))
        _mark_scan(con, "crawl", st, rows=out[st]["sites"], matched=out[st]["records"] + out[st]["business"])
    return out


def run_locus(con, args, log, progress):
    sts = [s for s in _states(args) if s in set(_gov_states(con))]
    out = {}
    for i, st in enumerate(sts):
        out[st] = locus_scan.run(con, st, log=log)
        progress((i + 1) / len(sts))
    return out


def run_models(con, args, log, progress):
    out = {}
    for i, name in enumerate((config.MODEL_A, config.MODEL_B)):
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
                    progress((i + msg["completed"] / msg["total"]) / 2)
                if status != last:
                    log(f"{name}: {status}")
                    last = status
        out[name] = "ready"
    return out


def run_build(con, args, log, progress):
    sts = _states(args)
    located = {r["state"] for r in db.rows(con, "SELECT DISTINCT state FROM located_law WHERE status='found'")}
    sts = [s for s in sts if s in located or args.get("states")]
    qs = args.get("questions").split(",") if args.get("questions") else list(QUESTIONS)
    return B.run(con, sts, qs, use_llm=not args.get("no_llm"), force=bool(args.get("force")), log=log,
                 progress=progress)


def run_score(con, args, log, progress):
    sts = [s for s in _states(args) if s in set(_gov_states(con))]
    out = {}
    for i, st in enumerate(sts):
        out[st] = scoring.run(con, st, log=log)
        progress((i + 1) / len(sts))
    return {"states": len(out)}


def run_publish(con, args, log, progress):
    from ..publish.dokuwiki import DokuWiki, publish
    wiki = DokuWiki(config.DOKUWIKI_URL, token=config.DOKUWIKI_TOKEN, dry_run=bool(args.get("dry_run")))
    rows = db.rows(con, "SELECT model_id, bpmn, dmn, stages FROM process_models WHERE tier IN ('reviewed','agreed') "
                        "AND bpmn IS NOT NULL")
    done = 0
    for i, r in enumerate(rows):
        model = B.rebuild(con, r["model_id"])
        res = publish(model, wiki, r["bpmn"], r["dmn"])
        stages = db.loads(r["stages"], {})
        if not args.get("dry_run"):
            stages["published"] = db.now()
            done_n = sum(1 for v in stages.values() if v)
            con.execute("UPDATE process_models SET stages=?, completion=?, updated_at=? WHERE model_id=?",
                        (json.dumps(stages), round(done_n / len(M.STAGES), 3), db.now(), r["model_id"]))
        log(f"{r['model_id']}: {res['process_page']} ({len(res['law_pages'])} law pages)")
        done += 1
        progress((i + 1) / len(rows))
    db.bump(con)
    con.commit()
    return {"published": done, "dry_run": bool(args.get("dry_run"))}


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


def run_quickstart(con, args, log, progress):
    """Tick every required box in order: governments, statutes, locate, build, score."""
    plan = [("governments", run_governments), ("statutes", run_statutes), ("locate", run_locate),
            ("contacts", run_contacts), ("build", run_build), ("score", run_score)]
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
    Step("locate", "Find the state law for each question",
         "Ranks every section by title, chapter and text; a known section number is used only if it is found, in "
         "force and on topic. The method and a confidence score are stored with each result.",
         "required", st_locate, run_locate, needs=["statutes"], params=["states", "questions"], cost="seconds per state"),
    Step("contacts", "Find contacts on Wikidata",
         "Official websites, emails and phone numbers from Wikidata (the data behind govdirectory.org), matched by "
         "FIPS code.", "recommended", st_contacts, run_contacts, needs=["governments"], params=["states"],
         cost="two queries per state"),
    Step("models", "Pull two local models",
         f"Two model families ({config.MODEL_A} and {config.MODEL_B}) extract the steps independently; a model "
         "only reaches 'two models agree' when they match. Needs the Ollama service ('llm' profile).",
         "recommended", st_models, run_models, cost="about 2.2 GB for the default pair; a GPU helps a lot"),
    Step("build", "Build the state process models",
         "Curated (checked) facts first; otherwise both local models extract quote-anchored facts, compiled to "
         "BPMN and DMN and checked (schemas, bpmnlint, quotes, Petri-net soundness).",
         "required", st_build, run_build, needs=["locate"], params=["states", "questions", "force", "no_llm"],
         cost="minutes per state on CPU"),
    Step("score", "Score every government and refresh the maps",
         "Confidence = state law + local law + contacts, with the weights on the Method page.",
         "required", st_score, run_score, needs=["governments"], params=["states"], cost="seconds"),
    Step("crawl", "Look for records and licence pages on official websites",
         "Reads each government's home page (robots.txt respected) for a public-records page, a business-licence "
         "page, and email or phone links.", "optional", st_crawl, run_crawl, needs=["governments"],
         params=["states", "force"], cost="about 1 request per government; a few minutes per state"),
    Step("locus", "Scan local ordinances (LOCUS-v1)",
         "Finds local ordinances on public records and business licences for each city and county. LOCUS is "
         "CC BY-NC and machine-labelled, so it is used to find law, never to cite it.",
         "optional", st_locus, run_locus, needs=["governments"], params=["states"],
         cost="ranged reads of a 1.8 GB dataset"),
    Step("publish", "Publish to Lexipedia",
         "Writes law and process pages to DokuWiki over JSON-RPC (bot account, API limited to @bots).",
         "optional", st_publish, run_publish, needs=["build"], params=["dry_run"]),
    Step("sync", "Share through Turso",
         "Push your results to a shared Turso (libSQL) database, or pull states other people have built.",
         "optional", st_sync, run_sync, params=["direction", "states", "tables", "full"]),
]}

COMPOSITE = {"quickstart": Step("quickstart", "Run all required steps", "Governments, statutes, law, contacts, "
                                "models and scores in one job.", "required", lambda con: {}, run_quickstart,
                                params=["states", "no_llm"])}


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
