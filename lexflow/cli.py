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
    for k in ("states", "questions", "direction", "tables", "cases", "strategies", "models", "places"):
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


def cmd_statute(args) -> int:
    from .municipal import states as S
    from .municipal import statutes
    st = S.normalise(args.state)
    for t in statutes.section_texts(st, args.sections):
        print(f"=== {t.code} § {t.section}. {t.title}\n{t.url}\n\n{t.text}\n")
    return 0


def cmd_statute_search(args) -> int:
    import re
    from .municipal import states as S
    from .municipal import statutes
    df = statutes.load(S.normalise(args.state))
    pat = re.compile(args.pattern, re.I)
    col = df["text"] if args.text else df["section_title"]
    hits = df[col.str.contains(pat, regex=True)]
    for _, r in hits.head(args.limit).iterrows():
        print(f"{r['section_number']:<16} {int(r['word_count'] or 0):>6}w  {r['section_title'][:110]}")
    print(f"({len(hits)} sections match; showing {min(len(hits), args.limit)})")
    return 0


def cmd_check_curated(args) -> int:
    """Check a curated facts file the way the build does, and print the problems and quality numbers."""
    from .extract.ollama import check_facts
    from .extract.schema import LegalProcessFacts
    from .ir import Provenance
    from .municipal import build as B
    from .municipal import states as S
    from .municipal import statutes
    from .municipal.quality import assess
    st = S.normalise(args.state)
    path = config.CURATED_DIR / st / f"{args.question}.json"
    spec = json.loads(path.read_text(encoding="utf-8"))
    texts = statutes.section_texts(st, spec["sections"])
    text = statutes.combined_text(texts)
    try:
        facts = LegalProcessFacts.model_validate(spec["facts"])
    except Exception as e:  # noqa: BLE001
        print(json.dumps({"ok": False, "schema_error": str(e)[:4000]}, indent=1))
        return 1
    problems = check_facts(facts, text)
    out = {"ok": not problems, "problems": problems, "steps": len(facts.steps),
           "decisions": [{"id": d.id, "rules": len(d.rules)} for d in facts.decisions]}
    if not problems:
        model = B._compile(facts, st, args.question, texts, Provenance(method="gold-manual"))
        model.texts = texts
        res = assess(model, agreement=1.0)
        out.update(validated=res["validated"], quality=res["quality"], metrics=res["metrics"], errors=res["errors"])
        out["ok"] = res["validated"]
    print(json.dumps(out, indent=1, default=str))
    return 0 if out["ok"] else 1


def cmd_export_fixtures(args) -> int:
    """Write fixtures/statutes/<state>_sections.json with every section the curated files cite, so the tests
    can check each curated quote without the statute downloads."""
    from .municipal import statutes
    by_state: dict[str, list[str]] = {}
    for p in sorted(config.CURATED_DIR.glob("*/*.json")):
        if p.parent.name == "places":
            continue
        spec = json.loads(p.read_text(encoding="utf-8"))
        by_state.setdefault(p.parent.name, [])
        by_state[p.parent.name] += [s for s in spec["sections"] if s not in by_state[p.parent.name]]
    out_dir = config.ROOT / "fixtures" / "statutes"
    out_dir.mkdir(parents=True, exist_ok=True)
    for st, refs in by_state.items():
        df = statutes.load(st)
        secs = []
        for ref in refs:
            hit = statutes.find(df, ref)
            if hit.empty:
                raise SystemExit(f"{st}: {ref} not found")
            r = hit.iloc[0]
            secs.append({"state": st, "section_number": r["section_number"], "citation": r["citation"],
                         "section_title": r["section_title"], "source_url": r["source_url"], "act_id": r["act_id"],
                         "act_status": "in_force", "text": r["text"]})
        data = {"dataset": "open-us-law v2026.09.1 (Vaquill AI)",
                "license": "Statute text is a government edict (public domain); the open-us-law compilation is "
                           "CC BY-NC 4.0",
                "note": f"Every section cited by curated/{st}/*.json; lets the tests check each curated quote offline",
                "sections": secs}
        (out_dir / f"{st}_sections.json").write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"{st}: {len(secs)} sections")
    return 0


def cmd_answer(args) -> int:
    """Print (or write) one place's answers as Markdown."""
    from .municipal import places
    from .municipal.answer import markdown
    with db.session() as con:
        for g in places.resolve_all(con, args.place):
            text = markdown(con, g["gov_id"])
            if args.out:
                from pathlib import Path
                path = Path(args.out) / f"{g['state']}-{places.place_slug(g)}.md"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text, encoding="utf-8")
                print(f"wrote {path}")
            else:
                print(text)
    return 0


def cmd_wiki_pages(args) -> int:
    """Write the lexipedia.xyz pages (DokuWiki syntax) to a directory for review before posting."""
    from pathlib import Path
    from .publish.lexipedia import all_pages
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    with db.session() as con:
        pages = all_pages(con)
    for pid, text in pages.items():
        (out / (pid.replace(":", "__") + ".txt")).write_text(text, encoding="utf-8")
        print(f"{pid}  ({len(text):,} chars)")
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
    r.add_argument("--cases", help="benchmark: va.records,dc.business ...")
    r.add_argument("--strategies", help="benchmark: rules,hybrid,outline_review ...")
    r.add_argument("--models", help="benchmark: qwen3:1.7b,gemma3:1b")
    r.add_argument("--places", help="va:charlottesville,dc,md:baltimore")
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
    t = sub.add_parser("statute", help="print sections of a downloaded state's statutes")
    t.add_argument("state")
    t.add_argument("sections", nargs="+")
    t.set_defaults(fn=cmd_statute)
    ts = sub.add_parser("statute-search", help="find sections whose heading (or text) matches a regex")
    ts.add_argument("state")
    ts.add_argument("pattern")
    ts.add_argument("--text", action="store_true", help="search the section text instead of the heading")
    ts.add_argument("--limit", type=int, default=40)
    ts.set_defaults(fn=cmd_statute_search)
    wp = sub.add_parser("wiki-pages", help="write lexipedia.xyz pages to a directory for review")
    wp.add_argument("--out", default="/data/wiki")
    wp.set_defaults(fn=cmd_wiki_pages)
    an = sub.add_parser("answer", help="one place's answers as Markdown: lexflow answer va:charlottesville")
    an.add_argument("place")
    an.add_argument("--out", help="directory to write <state>-<place>.md files into")
    an.set_defaults(fn=cmd_answer)
    sub.add_parser("export-fixtures", help="write fixtures/statutes/<state>_sections.json for the tests").set_defaults(
        fn=cmd_export_fixtures)
    k = sub.add_parser("check-curated", help="check curated/<state>/<question>.json like a build would")
    k.add_argument("state")
    k.add_argument("question")
    k.set_defaults(fn=cmd_check_curated)
    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
