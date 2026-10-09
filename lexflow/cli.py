"""Command line: ``python -m lexflow <command>`` (inside Docker: ``docker compose exec app lexflow ...``).

    lexflow status                         the setup checklist, with checkboxes
    lexflow run <step> [--states va,dc]    run one step now (see `lexflow status` for ids)
    lexflow run quickstart --states va     every required step for the states you name
    lexflow serve                          the dashboard and API on :8000
    lexflow sync push|pull [--states va]   share through Turso
    lexflow import-contacts file.csv       gov_id,question,kind,value,label
    lexflow export-status docs/status.json the snapshot the README charts are drawn from
"""
from __future__ import annotations

import argparse
import json
import sys
import traceback

from . import config
from .store import db

BOX = {"done": "[x]", "partial": "[~]", "todo": "[ ]", "blocked": "[!]", "optional": "[ ]"}


def cmd_status(_args) -> int:
    from .pipeline.steps import checklist
    with db.session() as con:
        items = checklist(con)
    print("lexflow setup checklist\n")
    for i, s in enumerate(items, 1):
        frac = f" {s['done']:,}/{s['total']:,}" if s.get("total") else ""
        print(f"{BOX.get(s['status'], '[ ]')} {i:>2}. {s['title']}  ({s['level']}{frac})")
        print(f"        {s['detail']}")
    print("\n[x] done  [~] partly done  [ ] to do  [!] needs an earlier step")
    return 0


def cmd_run(args) -> int:
    from .pipeline.jobs import JobContext
    from .pipeline.steps import get_step
    config.ensure_dirs()
    step = get_step(args.step)
    params = json.loads(args.args) if args.args else {}
    for k in ("states", "questions", "direction", "tables"):
        v = getattr(args, k, None)
        if v:
            params[k] = v
    for k in ("force", "no_llm", "regulations", "full", "dry_run"):
        if getattr(args, k, False):
            params[k] = True
    con = db.connect()
    ctx = JobContext(args.job, con)
    ctx.log(f"{step.title} {json.dumps(params) if params else ''}".strip())
    try:
        result = step.run(con, params, ctx.log, ctx.progress)
        con.commit()
        ctx.log("result: " + json.dumps(result, default=str)[:2000])
        ctx.finish(result, True, "Finished")
        return 0
    except Exception as e:  # noqa: BLE001
        traceback.print_exc()
        ctx.finish(None, False, f"{type(e).__name__}: {e}")
        return 1
    finally:
        con.close()


def cmd_serve(args) -> int:
    import uvicorn
    uvicorn.run("lexflow.api.app:app", host=args.host, port=args.port, log_level="info")
    return 0


def cmd_sync(args) -> int:
    ns = argparse.Namespace(step="sync", job=None, args=json.dumps({"direction": args.direction}),
                            states=args.states, tables=args.tables, full=args.full, questions=None)
    return cmd_run(ns)


def cmd_import_contacts(args) -> int:
    from .municipal.contacts import import_csv
    with db.session() as con:
        import_csv(con, args.path)
    return 0


def cmd_export_status(args) -> int:
    from .municipal import stats
    from .pipeline.steps import checklist
    from .municipal import method as M
    bins = (0.2, 0.35, 0.5, 0.65)
    with db.session() as con:
        data = {"generated": db.now(), "overview": stats.overview(con), "states": stats.state_table(con),
                "checklist": checklist(con), "models": stats.models(con), "confidence_bins": {}}
        for qid in data["overview"]["questions"]:
            counts = [0] * (len(bins) + 1)
            for (v,) in con.execute("SELECT confidence FROM answers WHERE question=?", (qid,)):
                counts[sum(v >= b for b in bins)] += 1
            data["confidence_bins"][qid] = counts
        # the state whose models are furthest along gets a county-level chart
        rank = {t: i for i, t in enumerate(M.TIERS)}
        best = max(data["states"], key=lambda r: (rank.get(r["tier"], 0), r["governments"]), default=None)
        if best and best["governments"]:
            data["focus_state"] = best["fips"]
            data["county_confidence"] = {
                qid: {r["county_fips"]: round(r["v"], 4) for r in db.rows(
                    con, "SELECT county_fips, avg(confidence) AS v FROM answers WHERE question=? AND state=? "
                         "GROUP BY county_fips", qid, best["state"])}
                for qid in data["overview"]["questions"]}
    for m in data["models"]:
        m.pop("origin", None)        # machine names stay out of a snapshot meant for a public README
        m["metrics"] ={k: v for k, v in m["metrics"].items() if not isinstance(v, (list, dict)) or k == "agreement_detail"}
    with open(args.path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, default=str)
    print(f"wrote {args.path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="lexflow", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status").set_defaults(fn=cmd_status)
    r = sub.add_parser("run")
    r.add_argument("step")
    r.add_argument("--states")
    r.add_argument("--questions")
    r.add_argument("--direction", choices=["push", "pull"])
    r.add_argument("--tables")
    for flag in ("--force", "--no-llm", "--regulations", "--full", "--dry-run"):
        r.add_argument(flag, action="store_true")
    r.add_argument("--job", type=int)
    r.add_argument("--args")
    r.set_defaults(fn=cmd_run)
    s = sub.add_parser("serve")
    s.add_argument("--host", default="0.0.0.0")
    s.add_argument("--port", type=int, default=8000)
    s.set_defaults(fn=cmd_serve)
    y = sub.add_parser("sync")
    y.add_argument("direction", choices=["push", "pull"])
    y.add_argument("--states")
    y.add_argument("--tables")
    y.add_argument("--full", action="store_true")
    y.set_defaults(fn=cmd_sync)
    c = sub.add_parser("import-contacts")
    c.add_argument("path")
    c.set_defaults(fn=cmd_import_contacts)
    e = sub.add_parser("export-status")
    e.add_argument("path", nargs="?", default="docs/status.json")
    e.set_defaults(fn=cmd_export_status)
    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
