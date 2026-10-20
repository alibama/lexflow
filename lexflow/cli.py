"""Command line: ``python -m lexflow <command>`` (inside Docker: ``docker compose exec app lexflow ...``).

    lexflow status                         the setup checklist, with checkboxes
    lexflow run <step> [--states va,dc]    run one step now (see `lexflow status` for ids)
    lexflow run quickstart --states va     every required step for the states you name
    lexflow serve                          the dashboard and API on :8000
    lexflow sync push|pull [--states va]   share through Turso (only the shared tables: --tables refuses any other)
    lexflow import-contacts file.csv       gov_id,question,kind,value,label
    lexflow export-status docs/status.json the snapshot the README charts are drawn from
    lexflow index --regulations [--states] the state regulations' search indexes (statutes without the flag)
    lexflow reviewer add|list|token|remove the reviewer list the operator keeps (pages name reviewers only from it;
                                           it is this copy's own: sync refuses the table)
    lexflow qs write|resolve|check         QuickStatements batches for Claude in Chrome (out/wikibase/)
    lexflow wikibase lint|push [...]       the cleanliness gate, then the direct API push (dry run by default)
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


def cmd_compute(args) -> int:
    """``nodes``: the configured nodes and their last check; ``check``: probe every node now (read-only);
    ``relabel``: the one-time relabel of benchmark rows made before the pool (lexflow.compute.migrate)."""
    from .compute import nodes as CN
    if args.action == "relabel":
        from .compute import migrate
        return migrate.main(args.cp_args)
    if not CN.pool_on():
        print("no pool: LEXFLOW_LLM_NODES is not set (every call goes to OLLAMA_URL); see docs/compute.md")
        return 0
    from .compute import health as CH
    con = CN.connect()
    try:
        CN.sync_env(con)
        if args.action == "check":
            for n in CN.load_nodes(con):
                CH.check(con, n["name"])
        for n in CN.load_nodes(con):
            models = ", ".join(m["name"] for m in (n.get("models") or [])) or "-"
            print(f"{n['name']:<12} {n['status']:<8} {n['url']:<36} v{n.get('version') or '?':<8} max {n['max_concurrency']} "
                  f"threads {n.get('threads') or '-'} {'draining ' if n.get('draining') else ''}{'' if n.get('enabled') else 'disabled '}"
                  f"models: {models}" + (f"  ({n['last_error']})" if n.get("last_error") else ""))
        return 0
    finally:
        con.close()


def cmd_run(args) -> int:
    import os
    from .pipeline.jobs import JobContext
    from .pipeline.steps import get_step
    config.ensure_dirs()
    step = get_step(args.step)
    params = json.loads(args.args) if args.args else {}
    if args.job:                         # the compute pool's calls log records the job and its step
        os.environ.setdefault("LEXFLOW_JOB_ID", str(args.job))
        os.environ.setdefault("LEXFLOW_JOB_STEP", args.step)
    for k in ("states", "questions", "direction", "tables", "cases", "strategies", "models", "places", "arm", "node",
              "run", "llm_cells", "model"):
        v = getattr(args, k, None)
        if v:
            params[k] = v
    for k in ("force", "no_llm", "regulations", "full", "dry_run", "local", "fill"):
        if getattr(args, k, False):
            params[k] = True
    from .store.turso import SyncTableError
    con = db.connect()
    ctx = JobContext(args.job, con)
    ctx.log(f"{step.title} {json.dumps(params) if params else ''}".strip())
    try:
        result = step.run(con, params, ctx.log, ctx.progress)
        con.commit()
        ctx.log("result: " + json.dumps(result, default=str)[:2000])
        ctx.finish(result, True, "Finished")
        return 0
    except SyncTableError as e:          # a table sync does not take: say so, without a traceback
        print(f"sync: {e}", file=sys.stderr)
        ctx.finish(None, False, f"refused: {e}")
        return 2
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
    """Push or pull the shared tables (db.SYNCED).  Any other table named in --tables (the reviewer list, the review
    log ...) is refused before the shared database is reached: exit status 2 and one line saying why."""
    from .store import turso as T
    try:
        T.check_tables(args.tables)
    except T.SyncTableError as e:
        print(f"sync {args.direction}: {e}", file=sys.stderr)
        return 2
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


def cmd_ask_search(args) -> int:
    """Full-text search of one state's statutes (or, with --regulations, its regulations): each argument is a
    concept, synonyms separated by '|'."""
    from .ask import index as I
    from .municipal import states as S
    st = S.normalise(args.state)
    corpus = "regulations" if getattr(args, "regulations", False) else I.CORPUS
    if not I.ensure(st, log=lambda *_: None, corpus=corpus):
        print(f"{st}: {corpus} not downloaded")
        return 1
    groups = [[t.strip() for t in c.split("|") if t.strip()] for c in args.concepts]
    expr = args.fts or I.match(groups, "or" if args.any else "and", columns="title" if args.title else None)
    hits = I.search(st, expr, limit=args.limit, corpus=corpus) if expr else []
    for h in hits:
        print(f"{h['ref']:<34} {int(h['words'] or 0):>6}w  {h['title'][:100]}")
    print(f"({len(hits)} shown; query {expr})")
    return 0


def cmd_check_ask(args) -> int:
    """Check a reference answer in curated_ask/<question>/<state>.json."""
    from .ask import reference as R
    from .municipal import states as S
    st = S.normalise(args.state)
    alt = getattr(args, "alt", False)
    try:
        spec = R.load(args.question, st, alt)
    except (OSError, ValueError) as e:
        print(json.dumps({"ok": False, "problems": [f"cannot read {R.path(args.question, st, alt)}: {e}"]}, indent=1))
        return 1
    out = R.check(spec, args.question, st)
    print(json.dumps(out, indent=1, default=str))
    return 0 if out["ok"] else 1


def cmd_ask_bench(args) -> int:
    """Score the ask pipeline against Claude's references; writes docs/askbench.json."""
    from .ask import bench as AB
    from .ask import reference as R
    from .store import db
    cases = R.cases()
    if args.cases:
        want = {w.strip() for w in args.cases.split(",") if w.strip()}
        unknown = sorted(w for w in want if not any(w in (f"{q}.{s}", q) for q, s in cases))
        cases = [c for c in cases if f"{c[0]}.{c[1]}" in want or c[0] in want]
        if unknown or not cases:                 # never fall back to running every case
            print(f"no reference matches {', '.join(unknown) or repr(args.cases)} "
                  f"(curated_ask/<question>/<state>.json; --cases qid.state,... or question ids)")
            return 1
    con = db.connect()
    rows = AB.run(con, tuple(args.arms.split(",")), cases, use_llm=args.llm, llm_plan=args.llm_plan,
                  model=getattr(args, "model", None), node=getattr(args, "node", None))
    print(json.dumps(AB.summary(rows), indent=1))
    # docs/askbench.json: the arms stored so far from the current code and metrics, each scored against the current
    # version of its reference; "cases" counts the references, each arm in the summary its own cases
    stored, excluded = AB.stored(con)
    if any(excluded.values()):
        print(f"docs/askbench.json leaves out {excluded['stale_reference']} rows scored against an older reference "
              f"and {excluded['stale_code']} from older code or metrics")
    ceil = AB.ceiling()
    ok = [c for c in ceil if c.get("mean") is not None]
    out = {"cases": len(R.cases()), "version": AB.version(), "excluded": excluded,
           "summary": AB.summary(stored), "rows": stored,
           "claude_vs_claude": {"cases": ceil, "mean": round(sum(c["mean"] for c in ok) / len(ok), 3) if ok else None}}
    (config.ROOT / "docs" / "askbench.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    return 0


def cmd_al_queue(args) -> int:
    """Write the sentences the selector is least sure of (per state and question) for Claude to label."""
    from .extract import active as AL
    from .municipal import states as S
    from .store import db
    out = AL.write_queue(db.connect(), config.ROOT / "curated_labels" / "queue", S.parse_states(args.states),
                         args.questions.split(","), n=args.n)
    print("\n".join(out))
    return 0


def cmd_check_labels(args) -> int:
    from .extract import active as AL
    from .municipal import states as S
    st = S.normalise(args.state)
    path = config.ROOT / "curated_labels" / st / f"{args.question}.json"
    try:
        spec = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        print(json.dumps({"ok": False, "problems": [f"cannot read {path}: {e}"]}))
        return 1
    problems = AL.check(spec)
    print(json.dumps({"ok": not problems, "labels": len(spec.get("labels") or []), "problems": problems}, indent=1))
    return 0 if not problems else 1


def cmd_index(args) -> int:
    from .ask import index as I
    from .municipal import states as S
    from .municipal import statutes
    if getattr(args, "regulations", False):
        return _index_regulations(args)
    sts = S.parse_states(args.states) if args.states else [s for s, _, _ in S.STATES if statutes.have(s)]
    for st in sts:
        if args.force or not I.ready(st):
            I.build(st)
    return 0


def _index_regulations(args) -> int:
    """lexflow index --regulations: every state with a regulations file on disk, or those --states names (a named
    state with no file makes the exit status 1)."""
    from .corpus import regulations as R
    from .municipal import states as S
    named = args.states and args.states.strip().lower() != "all"
    out = R.build_all(S.parse_states(args.states) if named else None, force=args.force)
    for st, v in out.items():
        print(f"{st:<4} {v['sections']:>8,} sections {v['seconds']:>7.1f}s {v['mb']:>8.1f} MB" if isinstance(v, dict)
              else f"{st:<4} {v}")
    return 1 if any(v == "no file" for v in out.values()) else 0


def cmd_ceiling(args) -> int:
    """How far two independent Claude drafts agree (curated/ vs curated_alt/), and what perfect selection over
    each candidate generator would score: the bounds the local strategies are measured against."""
    from .extract import benchmark as BM
    rows = BM.ceiling()
    ok = [r for r in rows if "value" in r]
    oracle = {}
    for case in BM.cases():
        try:
            oracle[case] = {k: v["value"] for k, v in BM.oracle(case).items()}
        except Exception as e:  # noqa: BLE001
            oracle[case] = {"error": str(e)[:120]}
    vals = [o for o in oracle.values() if "wide" in o]
    out = {"claude_vs_claude": {"mean": round(sum(r["value"] for r in ok) / len(ok), 3) if ok else None,
                                "cases": [{"case": r["case"], "value": r.get("value"), "steps": r.get("steps")}
                                          for r in rows]},
           "oracle": {"rules": round(sum(o["rules"] for o in vals) / len(vals), 3) if vals else None,
                      "wide": round(sum(o["wide"] for o in vals) / len(vals), 3) if vals else None,
                      "cases": oracle}}
    path = config.ROOT / "docs" / "ceiling.json"
    path.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"Claude vs Claude: {out['claude_vs_claude']['mean']} over {len(ok)} cases; perfect selection: "
          f"rules {out['oracle']['rules']}, wide {out['oracle']['wide']} over {len(vals)} cases -> {path}")
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
    base = config.ROOT / "curated_alt" if getattr(args, "alt", False) else config.CURATED_DIR
    path = base / st / f"{args.question}.json"
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


def cmd_review_hash(args) -> int:
    """Print the text_hash a reviewer records in a curated file's reviewed_by (lexflow/signoff.py): the file without
    its sign-offs, and, for a place file, each answer on its own."""
    from pathlib import Path
    from . import signoff
    from .municipal import places as P
    for name in args.paths:
        path = Path(name)
        spec = json.loads(path.read_text(encoding="utf-8"))
        print(f"{path}  text_hash {signoff.file_hash(spec)}  (the whole file)")
        for qid, ans in (spec.get("answers") or {}).items():
            row = P.local_row(ans, spec)
            print(f"{path}  answers.{qid}  text_hash {signoff.text_hash(signoff.row_text(row, signoff.LOCAL_TEXT))}")
    print('Record it with the review: "reviewed_by": {"reviewer": "<the id `lexflow reviewer list` gives>", '
          '"date": "YYYY-MM-DD", "attested": true, "text_hash": "<the hash>"}, where attested is the reviewer\'s own '
          "statement that they, a person, read this exact text, and the reviewer is someone the operator has put on "
          "the list (`lexflow reviewer add`). Any later edit to the text needs a new review.")
    return 0


TOKEN_NOTE = ("reviewer token (shown this once; lexflow keeps only its hash): {token}\n"
              "Give it to the reviewer alone. The review API records or removes a review only with it, in the "
              "X-Lexflow-Reviewer-Token header, and keeps which reviewer's token was used. "
              "`lexflow reviewer token <id>` makes a new one.")


def cmd_reviewer(args) -> int:
    """The reviewer list (lexflow/reviewers.py): the people the operator vouches for.  lexflow cannot check that a
    reviewer is a person; a page names a reviewer only from this list."""
    from . import reviewers as RV
    from . import signoff
    with db.session() as con:
        try:
            if args.action == "add":
                r = RV.add(con, args.name, args.role, licensed_in=args.licensed_in, added_by=args.added_by,
                           confirm_person=args.confirm_person)
                print(f"added {r['id']}: {r['name']}, {r['role']}"
                      + (f" licensed in {r['licensed_in']}" if r["licensed_in"] else "")
                      + f" (added by {r['added_by']}). You vouch that this reviewer is a person: lexflow cannot "
                        "check it. A review names them as \"reviewer\": \"" + r["id"] + "\".")
                print(TOKEN_NOTE.format(token=r["token"]))
                if signoff.is_ai_name(r["name"]):
                    print("warning: the name contains the name of an AI system or product; added because you "
                          "confirmed the reviewer is a person (--confirm-person)")
            elif args.action == "token":
                token = RV.rotate_token(con, args.id)
                print(f"new token for {args.id}; the old one no longer works.")
                print(TOKEN_NOTE.format(token=token))
            elif args.action == "remove":
                r = RV.remove(con, args.id)
                print(f"removed {r['id']}: {r['name']}; their token no longer works, and pages they signed will say "
                      "\"Not yet reviewed by a person\" at the next render")
            else:
                rows = RV.listing(con, removed=args.all)
                for r in rows:
                    print(f"{r['id']}  {r['name']}  {r['role']}"
                          + (f" licensed in {r['licensed_in']}" if r["licensed_in"] else "")
                          + f"  added by {r['added_by']} on {r['added_at'][:10]}"
                          + (f"  removed on {r['removed_at'][:10]}" if r["removed_at"] else
                             "" if r.get("token_hash") else f"  no token yet (`lexflow reviewer token {r['id']}`)"))
                print(f"{len(rows)} reviewer{'s' if len(rows) != 1 else ''} on the list"
                      + (" (with those removed)" if args.all else ""))
        except RV.ReviewerError as e:
            print(f"reviewer {args.action}: {e}", file=sys.stderr)
            return 1
    return 0


def cmd_deadline_words(args) -> int:
    """Read every curated deadline in the words of its quote; list those whose stored unit or number the quote does
    not bear out (relabelled units, figures only lexflow's count gives, figures not in the deadline's own quote)."""
    from .law import wording as W
    rows = W.audit(config.CURATED_DIR)
    odd = [r for r in rows if r["wording"] != "agrees" or not r["in_deadline_quote"]]
    for r in (rows if args.all else odd):
        flag = r["wording"] + ("" if r["in_deadline_quote"] or r["wording"] in ("derived", "no figure", "not stated")
                               else ", not in the deadline's own quote")
        print(f"{r['model']:14} {r['step']:28} stored {r['amount']} {r['unit']:<14} {flag:<42} {r['text']}")
    print(f"{len(rows)} deadlines; {len(odd)} where the stored unit or figure is lexflow's, not the quote's")
    return 0


def cmd_qs(args) -> int:
    from .publish import qs
    return qs.main(args.qs_args)


def cmd_wikibase(args) -> int:
    """``lint``: the cleanliness gate (out/wikibase/lint-report.md); ``push``: the graph through the API."""
    if args.action == "push":
        from .publish import push
        return push.main(args.wb_args)
    from .publish import lint
    return lint.main(args.wb_args)


def cmd_sparql(args) -> int:
    """Run a SPARQL query (a canned name, a .rq file or text) on the local Wikibase copy, or live with --live."""
    from .publish import ids as I
    from .publish import rdf
    from .publish import sparql as SQ
    if args.build:
        config.ensure_dirs()
        con = db.connect()
        try:
            rdf.build(con, states=args.states.split(",") if args.states else None, drafts=not args.no_drafts)
        finally:
            con.close()
        if not args.query:
            return 0
    if not args.query:
        print("canned queries (lexflow sparql <name> [--param k=v]):\n")
        for q in SQ.catalogue():
            ps = ", ".join(f"{k}={v}" if v else k for k, v in q.params.items())
            print(f"  {q.name:16} {q.question}" + (f"\n{'':19}params: {ps}" if ps else ""))
        return 0
    q = SQ.resolve(args.query)
    params = {}
    for p in args.param or []:
        if "=" not in p:
            print(f"--param wants name=value, not {p!r}", file=sys.stderr)
            return 2
        k, v = p.split("=", 1)
        params[k.strip()] = v.strip()
    idmap = I.IdMap() if args.live else I.IdMap.for_turtle()
    if not args.live and I.IdMap.turtle_stale():
        print("note: out/wikibase/ids.json is newer than the local Turtle; run `lexflow sparql --build` to use the "
              "wiki's ids locally", file=sys.stderr)
    try:
        text = SQ.prepare(q, params, idmap, live=args.live)
    except KeyError as e:
        print(str(e), file=sys.stderr)
        return 2
    if args.show:
        print(text)
        return 0
    if q.live_only and not args.live:
        print(f"{q.name} is live-only (federated); add --live", file=sys.stderr)
        return 2
    try:
        store = None if args.live else rdf.open_store()
        rows = rdf.query(store, text, live=args.live, limit=args.limit)
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        return 1
    except Exception as e:
        print(f"query failed: {e}", file=sys.stderr)
        return 1
    if idmap.unresolved:
        print("unresolved tokens (provisional ids used): " + ", ".join(sorted(set(idmap.unresolved))), file=sys.stderr)
    if args.json:
        print(json.dumps({"head": {"vars": rows.vars}, "results": {"bindings": list(rows)}, "truncated": rows.truncated},
                         indent=1, ensure_ascii=False))
        return 0
    simple = rows.simple()
    cols = rows.vars or sorted({k for r in simple for k in r})
    widths = {c: min(60, max([len(c)] + [len(str(r.get(c, ""))) for r in simple])) for c in cols}
    print("  ".join(c.ljust(widths[c]) for c in cols))
    print("  ".join("-" * widths[c] for c in cols))
    for r in simple:
        print("  ".join(str(r.get(c, "")).replace("\n", " ")[:60].ljust(widths[c]) for c in cols))
    print(f"\n{len(rows):,} row{'s' if len(rows) != 1 else ''}{' (truncated)' if rows.truncated else ''}"
          f" from {'the live endpoint' if args.live else 'the local store'}")
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
    r.add_argument("--arm", help="coverage: coverage (probe only) or ollama (probe, answer and score)")
    r.add_argument("--node", help="coverage, ask, benchmark, models: the node of the pool (LEXFLOW_LLM_NODES) to run "
                                  "the model calls on")
    r.add_argument("--run", help="coverage: a run id to resume (default: the date and time)")
    r.add_argument("--llm-cells", help="coverage: Ollama answers for this many state cells per state")
    r.add_argument("--model", help="coverage: the chat model (default LEXFLOW_ASK_MODEL)")
    r.add_argument("--fill", action="store_true", help="coverage: answer the gap cells of the run with the ask pipeline "
                                                       "and store the drafts (--llm-cells caps the cells per state)")
    for flag in ("--force", "--no-llm", "--regulations", "--full", "--dry-run", "--local"):
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
    rh = sub.add_parser("review-hash", help="the text_hash a reviewer records in a curated file's reviewed_by")
    rh.add_argument("paths", nargs="+")
    rh.set_defaults(fn=cmd_review_hash)
    rv = sub.add_parser("reviewer", help="the reviewer list the operator keeps (this copy's own, not synced): add, "
                                         "list, remove a reviewer, or give one a new token")
    rvs = rv.add_subparsers(dest="action", required=True)
    ra = rvs.add_parser("add", help="put a person you vouch for on the list")
    ra.add_argument("name")
    ra.add_argument("--role", required=True, help="one of: attorney, paralegal, law student, clerk, records officer, "
                                                   "planner, municipal attorney, researcher, student, volunteer, other person")
    ra.add_argument("--licensed-in", help="for an attorney: the state where they are licensed (va or Virginia)")
    ra.add_argument("--added-by", required=True, help="who vouches for this reviewer (the operator)")
    ra.add_argument("--confirm-person", action="store_true",
                    help="add a name that contains the name of an AI system or product: you confirm the reviewer is a person")
    rvs.add_parser("list", help="the reviewers on the list").add_argument("--all", action="store_true",
                                                                         help="with those removed")
    rr = rvs.add_parser("remove", help="take a reviewer off the list")
    rr.add_argument("id")
    rt = rvs.add_parser("token", help="print a new token for a reviewer (the old one stops working)")
    rt.add_argument("id")
    rv.set_defaults(fn=cmd_reviewer)
    dw = sub.add_parser("deadline-words", help="re-check curated deadlines against the words of their quotes")
    dw.add_argument("--all", action="store_true", help="list every deadline, not only those that differ")
    dw.set_defaults(fn=cmd_deadline_words)
    an = sub.add_parser("answer", help="one place's answers as Markdown: lexflow answer va:charlottesville")
    an.add_argument("place")
    an.add_argument("--out", help="directory to write <state>-<place>.md files into")
    an.set_defaults(fn=cmd_answer)
    sub.add_parser("export-fixtures", help="write fixtures/statutes/<state>_sections.json for the tests").set_defaults(
        fn=cmd_export_fixtures)
    asr = sub.add_parser("ask-search", help="full-text search a state's statutes: lexflow ask-search va 'expunge|seal' "
                                            "'record|conviction'")
    asr.add_argument("state")
    asr.add_argument("concepts", nargs="*", help="one argument per concept; synonyms separated by |")
    asr.add_argument("--any", action="store_true", help="any concept instead of all of them")
    asr.add_argument("--title", action="store_true", help="search headings only")
    asr.add_argument("--fts", help="a raw SQLite FTS5 MATCH expression instead of concepts")
    asr.add_argument("--regulations", action="store_true", help="search the state's regulations instead")
    asr.add_argument("--limit", type=int, default=25)
    asr.set_defaults(fn=cmd_ask_search)
    ca = sub.add_parser("check-ask", help="check a reference answer in curated_ask/<question>/<state>.json")
    ca.add_argument("question")
    ca.add_argument("state")
    ca.add_argument("--alt", action="store_true", help="check the independent second draft in curated_ask_alt/")
    ca.set_defaults(fn=cmd_check_ask)
    ab = sub.add_parser("ask-bench", help="score the ask pipeline against curated_ask/ (Claude's references)")
    ab.add_argument("--arms", default="local,oracle", help="local (full pipeline), oracle (gold sections)")
    ab.add_argument("--cases", help="qid.state,... or question ids")
    ab.add_argument("--llm", action="store_true", help="the local model plans the search and writes the summary")
    ab.add_argument("--llm-plan", action="store_true", help="the local model plans the search only")
    ab.add_argument("--model", help="the chat model for the LLM arms (default LEXFLOW_ASK_MODEL); the arm is named <arm>@<model>")
    ab.add_argument("--node", help="pin the model calls to this node of the pool (LEXFLOW_LLM_NODES)")
    ab.set_defaults(fn=cmd_ask_bench)
    cp = sub.add_parser("compute", help="the compute pool (lexflow/compute, docs/compute.md): nodes, check, relabel")
    cp.add_argument("action", choices=["nodes", "check", "relabel"])
    cp.add_argument("cp_args", nargs=argparse.REMAINDER, help="relabel: --model, --node, --db, --dry (lexflow.compute.migrate)")
    cp.set_defaults(fn=cmd_compute)
    alq = sub.add_parser("al-queue", help="sentences for Claude to label (active learning) -> curated_labels/queue/")
    alq.add_argument("--states", required=True)
    alq.add_argument("--questions", default="records,business")
    alq.add_argument("--n", type=int, default=40)
    alq.set_defaults(fn=cmd_al_queue)
    cl = sub.add_parser("check-labels", help="check curated_labels/<state>/<question>.json")
    cl.add_argument("state")
    cl.add_argument("question")
    cl.set_defaults(fn=cmd_check_labels)
    ix = sub.add_parser("index", help="build the statute search index (all downloaded states, or --states); with "
                                      "--regulations, the regulations indexes (every state with a file on disk)")
    ix.add_argument("--states")
    ix.add_argument("--force", action="store_true")
    ix.add_argument("--regulations", action="store_true",
                    help="index the regulations files already on disk (data/index/regulations_<state>.sqlite)")
    ix.set_defaults(fn=cmd_index)
    sub.add_parser("ceiling", help="Claude-vs-Claude agreement and perfect-selection bounds -> docs/ceiling.json"
                   ).set_defaults(fn=cmd_ceiling)
    ka = sub.add_parser("check-curated-alt", help="check an independent second draft in curated_alt/")
    ka.add_argument("state")
    ka.add_argument("question")
    ka.set_defaults(fn=cmd_check_curated, alt=True)
    k = sub.add_parser("check-curated", help="check curated/<state>/<question>.json like a build would")
    k.add_argument("state")
    k.add_argument("question")
    k.set_defaults(fn=cmd_check_curated)
    q = sub.add_parser("qs", help="QuickStatements batches for Claude in Chrome -> out/wikibase/: lexflow qs write "
                                  "[--pass 2] | resolve | check (see lexflow.publish.qs)")
    q.add_argument("qs_args", nargs=argparse.REMAINDER, help="arguments passed to lexflow.publish.qs")
    q.set_defaults(fn=cmd_qs)
    wb = sub.add_parser("wikibase", help="the Lexipedia Wikibase through the API: lexflow wikibase lint [--no-ollama] "
                                         "writes out/wikibase/lint-report.md; lexflow wikibase push [--really] "
                                         "executes the graph (dry run by default; see lexflow.publish.push)")
    wb.add_argument("action", choices=["lint", "push"])
    wb.add_argument("wb_args", nargs=argparse.REMAINDER, help="arguments passed to lexflow.publish.lint or .push")
    wb.set_defaults(fn=cmd_wikibase)
    sq = sub.add_parser("sparql", help="run SPARQL on the local Wikibase copy (data/wikibase/) or, with --live, on "
                                       "lexipedia.wikibase.cloud: lexflow sparql process-steps --param "
                                       "process=lexflow:process:va.records; no argument lists the canned queries")
    sq.add_argument("query", nargs="?", help="a canned query name, a .rq file, or SPARQL text ({P:label} and {Q:key} "
                                             "tokens are expanded)")
    sq.add_argument("--live", action="store_true", help="query the public endpoint instead of the local store")
    sq.add_argument("--param", action="append", metavar="NAME=VALUE", help="set a VALUES parameter (repeatable)")
    sq.add_argument("--json", action="store_true", help="print SPARQL JSON results instead of a table")
    sq.add_argument("--build", action="store_true", help="regenerate the Turtle and store from the database first")
    sq.add_argument("--states", help="with --build: only these states (va,dc)")
    sq.add_argument("--no-drafts", action="store_true", help="with --build: leave draft (single-tier) models and "
                                                             "the asked answers' drafts out")
    sq.add_argument("--limit", type=int, default=None, help="keep at most this many rows")
    sq.add_argument("--show", action="store_true", help="print the expanded query and stop")
    sq.set_defaults(fn=cmd_sparql)
    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
