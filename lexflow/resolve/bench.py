"""ResolveBench, and the live run that uses the same judge on the open queue.

**The bench** (``run_bench``).  Gold cases are rows the Glass Database has already decided: a person's
``confirmed`` and ``rejected`` rows (the trusted gold), and the lookup's own ``matched`` and ``none`` rows that
had candidates to choose between (its narrow rules are right far more often than not, and there are hundreds of
them, so they make a floor to measure on; the summary reports the two apart).  Each model is an arm,
``judge@<model>[+search][+schema]``; every case x arm row is stored in ``resolve_bench`` with ``version()`` (a
hash of this package), like AskBench's rows, and ``docs/resolvebench.json`` keeps the current rows.  Per arm:

* ``accuracy``             how often the verdict equals the gold (``unsure`` is never equal);
* ``decided``              the share of cases the arm would settle on its own: a verdict other than unsure with
                           confidence at or above the threshold;
* ``precision_decided``    how often those settled answers are right.  **This is the 95% number**: a model's
                           answers are applied without a person only when its precision at the threshold is
                           there, and then only for the cases it decides;
* the same three on the human-decided rows alone, mean seconds, and a breakdown by kind.

**The live run** (``run_live``).  The unsure queue, a panel of models, one verdict each (fanned out over the
compute pool), then a consensus: settled when every model names the same answer and the least confident is at
or above the threshold.  With ``GLASSDB_ADMIN_TOKEN`` set, every case's panel answer is written back to the
Glass Database as a suggestion the reviewer sees beside the candidates; with ``apply`` (and only then) a settled
case at or above ``apply_above`` is decided.  Without a token the run is a report.
"""
from __future__ import annotations

import hashlib
import json
import statistics as st
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .. import config
from ..store import db
from . import evidence as E
from . import judge as J
from .source import Case, GlassDatabase

METRIC_VERSION = 1
# the code behind an answer: what is asked, what is shown, how the reply is read.  Summaries (this file) and the
# API are not in it, so a change to the reporting does not make the stored rows stale.
CODE = ("resolve/source.py", "resolve/evidence.py", "resolve/judge.py")
GOLD_STATUSES = ("confirmed", "rejected", "matched", "none")
DOCS = config.ROOT / "docs" / "resolvebench.json"


def version() -> str:
    root = Path(__file__).resolve().parents[1]
    h = hashlib.sha256()
    for p in sorted({p for pat in CODE for p in root.glob(pat)}):
        h.update(p.name.encode() + b"\0" + p.read_bytes())
    return f"{METRIC_VERSION}-{h.hexdigest()[:12]}"


def arm_name(model: str, searched: bool, mode: str = "json") -> str:
    return f"judge@{model}" + ("+search" if searched else "") + ("" if mode == "json" else f"+{mode}")


def client_for(model: str, node: str | None = None):
    from ..extract.ollama import OllamaClient
    return OllamaClient(base_url=config.OLLAMA_URL, model=model, num_ctx=config.NUM_CTX, timeout=900,
                        think=(True if config.RESOLVE_THINK else False), node=node)


# ------------------------------------------------------------------------------------------------ cases
def cached_cases(con) -> dict[str, Case]:
    return {r["key"]: Case.from_row(r) for r in db.rows(con, "SELECT * FROM resolve_cases")}


def remember_cases(con, cases: list[Case]) -> None:
    db.upsert(con, "resolve_cases", [{**c.to_row(), "fetched_at": db.now()} for c in cases], keys=("key",), stamp=False)
    con.commit()


def fetch_cases(con, statuses, *, kinds: list[str] | None = None, limit: int | None = None, log=print,
                src: GlassDatabase | None = None) -> list[Case]:
    """Cases from the Glass Database for these statuses, their statements read once and kept in the store."""
    src = src or GlassDatabase(log=log)
    cases = src.cases(tuple(statuses), kinds=kinds, limit=limit, known=cached_cases(con))
    remember_cases(con, cases)
    return cases


def gold_hash(case: Case) -> str:
    body = json.dumps([case.label, case.gold(), case.candidate_ids()], ensure_ascii=False)
    return hashlib.sha1(body.encode("utf-8")).hexdigest()[:12]


def _workers(models: list[str], node: str | None) -> int:
    from ..extract.benchmark import workers_for
    return max(1, min(len(models), workers_for(models, node)))


# ------------------------------------------------------------------------------------------------ the bench
def judge_case(model: str, case: Case, evidence: dict, node: str | None, mode: str) -> J.Verdict:
    return J.judge(client_for(model, node), case, evidence, mode=mode)


def row_for(case: Case, v: J.Verdict, *, arm: str, ver: str, threshold: float, searched: bool) -> dict:
    gold = case.gold()
    decided = v.verdict != "unsure" and v.confidence >= threshold
    return {"case": case.key, "kind": case.kind, "label": case.label, "arm": arm, "model": v.model, "node": v.node,
            "gold": gold, "gold_source": "human" if case.human() else "rule", "verdict": v.verdict,
            "confidence": round(v.confidence, 3), "correct": bool(gold is not None and v.verdict == gold),
            "decided": bool(decided), "ok": v.ok, "flags": v.flags, "because": v.because, "seconds": v.seconds,
            "prompt_tokens": v.prompt_tokens, "tokens": v.tokens, "candidates": len(case.candidates),
            "searched": searched, "version": ver, "threshold": threshold}


def _partial(ev: dict) -> bool:
    return bool((ev or {}).get("partial"))


def run_bench(con, models: list[str], cases: list[Case], *, node: str | None = None, search: bool = True,
              mode: str = "json", threshold: float | None = None, force: bool = False, log=print, progress=None) -> dict:
    """Every gold case x every model; rows stored, docs/resolvebench.json rewritten, the summary returned.  A row
    already stored by this code for this case and arm is kept, not judged again, unless ``force``: a run that
    died halfway continues where it stopped."""
    threshold = config.RESOLVE_THRESHOLD if threshold is None else float(threshold)
    ver = version()
    cases = [c for c in cases if c.gold() is not None and c.candidates]
    if not cases:
        log("no gold cases: nothing the Glass Database has decided has candidates to choose between")
        return {"version": ver, "cases": 0, "arms": {}}
    searched = bool(search and config.SEARXNG_URL)
    already: set[tuple[str, str]] = set()           # (case, arm) rows this code stored before: kept, not judged again
    if not force:
        gold = {c.key: gold_hash(c) for c in cases}
        for r in db.rows(con, "SELECT case_id, arm, metrics, gold_hash FROM resolve_bench"):
            m = db.loads(r["metrics"], {})
            if m.get("version") == ver and gold.get(r["case_id"]) == r["gold_hash"]:
                already.add((r["case_id"], r["arm"]))
    jobs = [(m, c) for m in models for c in cases if (c.key, arm_name(m, searched, mode)) not in already]
    need = {c.key for _m, c in jobs}
    log(f"ResolveBench {ver}: {len(cases)} gold cases ({sum(1 for c in cases if c.human())} decided by a person) x "
        f"{len(models)} model(s), threshold {threshold}" + ("" if searched else "; no web search")
        + (f"; {len(models) * len(cases) - len(jobs)} row(s) already judged by this code are kept" if len(jobs) < len(models) * len(cases) else ""))
    ev: dict[str, dict] = {}
    todo_ev = [c for c in cases if c.key in need]
    for i, c in enumerate(todo_ev):                 # the main thread reads the evidence (and fills the cache)
        ev[c.key] = E.gather(con, c, use_search=search, log=log)
        if progress:
            progress(0.3 * (i + 1) / max(1, len(todo_ev)))
    if any(_partial(e) for e in ev.values()):
        log(f"  Wikidata facts could not be read for {sum(_partial(e) for e in ev.values())} case(s); their rows say partial_evidence")
    workers = _workers(models, node)
    if workers > 1:
        log(f"  fanning out over {workers} workers (the pool's free slots)")
    rows: list[dict] = []
    done = 0

    def one(model: str, case: Case) -> dict:
        try:
            v = judge_case(model, case, ev[case.key], node, mode)
        except Exception as e:  # noqa: BLE001 - a failed call is a row that says so
            v = J.Verdict(verdict="unsure", confidence=0.0, because=f"call failed: {type(e).__name__}: {e}", ok=False,
                          model=model, flags=["call failed"])
        row = row_for(case, v, arm=arm_name(model, searched, mode), ver=ver, threshold=threshold, searched=searched)
        row["partial_evidence"] = _partial(ev[case.key])
        return row

    def keep(row: dict) -> None:
        nonlocal done
        rows.append(row)
        case = next(c for c in cases if c.key == row["case"])
        db.upsert(con, "resolve_bench", [{"case_id": row["case"], "arm": row["arm"], "metrics": json.dumps(row, ensure_ascii=False),
                                          "gold_hash": gold_hash(case), "created_at": db.now()}],
                  keys=("case_id", "arm"), stamp=False)
        con.commit()
        done += 1
        mark = "✓" if row["correct"] else ("·" if row["verdict"] == "unsure" else "✗")
        log(f"  {mark} {row['label'][:28]:<28} {row['arm'][:34]:<34} {row['verdict']:<10} {row['confidence']:.2f} "
            f"gold {row['gold']:<10} {row['seconds']}s" + (f" [{'; '.join(row['flags'])}]" if row["flags"] else ""))
        if progress:
            progress(0.3 + 0.7 * done / len(jobs))

    if workers <= 1:
        for m, c in jobs:
            keep(one(m, c))
    else:
        with ThreadPoolExecutor(max_workers=workers) as ex:
            for fut in [ex.submit(one, m, c) for m, c in jobs]:
                keep(fut.result())
    if already:                                     # the kept rows count in this run's summary too
        wanted = {(c.key, arm_name(m, searched, mode)) for m in models for c in cases}
        rows += [m for m in stored(con) if (m["case"], m["arm"]) in wanted and (m["case"], m["arm"]) in already]
    summary = summarize(rows, threshold)
    for arm, s in summary.items():
        log(f"{arm}: accuracy {s['accuracy']:.3f}, decides {s['decided']:.0%} of cases at ≥{threshold}, "
            f"precision there {s['precision_decided'] if s['precision_decided'] is not None else float('nan'):.3f}"
            + (f"; on the {s['human_cases']} human-decided: accuracy {s['human_accuracy']:.3f}" if s["human_cases"] else "")
            + f"; {s['mean_seconds']}s a case")
    write_docs(con, threshold)
    return {"version": ver, "cases": len(cases), "threshold": threshold, "arms": summary, "docs": str(DOCS)}


def panel_rows(rows: list[dict], threshold: float | None = None) -> list[dict]:
    """The panel as an arm of its own, from the stored rows and no new calls: for every case that two or more arms
    judged, the consensus of those arms (``consensus``: settled only when all agree at or above the threshold).
    Named ``panel(<arm>+<arm>)``; it says what agreement buys in precision and costs in coverage."""
    threshold = config.RESOLVE_THRESHOLD if threshold is None else threshold
    arms = sorted({r["arm"] for r in rows})
    if len(arms) < 2:
        return []
    by_case: dict[str, dict[str, dict]] = {}
    for r in rows:
        by_case.setdefault(r["case"], {})[r["arm"]] = r
    out = []
    for case, per in by_case.items():
        if len(per) < 2:
            continue
        verdicts = [J.Verdict(verdict=r["verdict"], confidence=float(r["confidence"] or 0), because=r.get("because") or "",
                              model=arm) for arm, r in sorted(per.items())]
        cons = consensus(verdicts, threshold)
        first = next(iter(per.values()))
        verdict = cons["verdict"] if cons["settled"] else "unsure"
        out.append({**first, "arm": "panel(" + "+".join(sorted(per)) + ")", "model": "+".join(sorted(per)), "verdict": verdict,
                    "confidence": cons["confidence"] if cons["settled"] else 0.0, "correct": verdict == first.get("gold"),
                    "decided": cons["settled"], "ok": True, "flags": [], "because": cons["because"],
                    "seconds": round(sum(float(r.get("seconds") or 0) for r in per.values()), 1)})
    return out


def summarize(rows: list[dict], threshold: float | None = None) -> dict:
    threshold = config.RESOLVE_THRESHOLD if threshold is None else threshold
    rows = list(rows) + panel_rows(rows, threshold)
    out: dict = {}
    for arm in sorted({r["arm"] for r in rows}):
        rs = [r for r in rows if r["arm"] == arm]
        dec = [r for r in rs if r["verdict"] != "unsure" and r["confidence"] >= threshold]
        hum = [r for r in rs if r.get("gold_source") == "human"]
        hdec = [r for r in hum if r["verdict"] != "unsure" and r["confidence"] >= threshold]
        by_kind: dict = {}
        for k in sorted({r["kind"] for r in rs}):
            ks = [r for r in rs if r["kind"] == k]
            by_kind[k] = {"cases": len(ks), "accuracy": round(sum(r["correct"] for r in ks) / len(ks), 3)}
        out[arm] = {"cases": len(rs), "accuracy": round(sum(r["correct"] for r in rs) / len(rs), 3),
                    "decided": round(len(dec) / len(rs), 3),
                    "precision_decided": round(sum(r["correct"] for r in dec) / len(dec), 3) if dec else None,
                    "human_cases": len(hum),
                    "human_accuracy": round(sum(r["correct"] for r in hum) / len(hum), 3) if hum else None,
                    "human_precision_decided": round(sum(r["correct"] for r in hdec) / len(hdec), 3) if hdec else None,
                    "unsure": round(sum(r["verdict"] == "unsure" for r in rs) / len(rs), 3),
                    "failed": sum(1 for r in rs if not r.get("ok")),
                    "mean_seconds": round(st.mean(r["seconds"] for r in rs), 1) if rs else None,
                    "by_kind": by_kind, "threshold": threshold}
    return out


def stored(con) -> list[dict]:
    """The stored rows of the current code, each still matching its case's gold."""
    ver = version()
    gold = {c.key: gold_hash(c) for c in cached_cases(con).values()}
    out = []
    for r in db.rows(con, "SELECT case_id, arm, metrics, gold_hash FROM resolve_bench"):
        m = db.loads(r["metrics"], {})
        if m.get("version") == ver and gold.get(r["case_id"]) == r["gold_hash"]:
            out.append(m)
    return out


def write_docs(con, threshold: float | None = None, path: Path | None = None) -> dict:
    rows = stored(con)
    out = {"version": version(), "threshold": config.RESOLVE_THRESHOLD if threshold is None else threshold,
           "cases": len({r["case"] for r in rows}), "summary": summarize(rows, threshold), "rows": rows,
           "written_at": db.now()}
    p = path or DOCS
    try:
        p.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass
    return out


# ------------------------------------------------------------------------------------------------ the live run
def consensus(verdicts: list[J.Verdict], threshold: float) -> dict:
    """The panel's answer.  Settled: every model names the same verdict (not unsure) and the least confident of
    them is at or above the threshold.  Otherwise the most common non-unsure verdict is the suggestion, unsettled."""
    models = {v.model: {"verdict": v.verdict, "confidence": round(v.confidence, 3), "because": v.because, "flags": v.flags}
              for v in verdicts}
    usable = [v for v in verdicts if v.verdict != "unsure"]
    if not usable:
        return {"verdict": "unsure", "confidence": 0.0, "settled": False, "because": "no model named an answer", "models": models}
    agreed = len({v.verdict for v in verdicts}) == 1 and len(usable) == len(verdicts)
    best = max(usable, key=lambda v: v.confidence)
    if agreed and min(v.confidence for v in verdicts) >= threshold:
        return {"verdict": best.verdict, "confidence": round(min(v.confidence for v in verdicts), 3), "settled": True,
                "because": best.because, "models": models}
    counts: dict[str, list[J.Verdict]] = {}
    for v in usable:
        counts.setdefault(v.verdict, []).append(v)
    top = sorted(counts.items(), key=lambda kv: (-len(kv[1]), -max(x.confidence for x in kv[1])))
    if len(top) > 1 and len(top[0][1]) == len(top[1][1]):
        return {"verdict": "unsure", "confidence": 0.0, "settled": False,
                "because": "the models disagree: " + "; ".join(f"{k} ({len(vs)})" for k, vs in top), "models": models}
    verdict, vs = top[0]
    return {"verdict": verdict, "confidence": round(st.mean(x.confidence for x in vs), 3), "settled": False,
            "because": max(vs, key=lambda x: x.confidence).because, "models": models}


def _prior_verdicts(old: dict | None, case: Case, models: list[str], ver: str) -> list[J.Verdict] | None:
    """The panel's earlier verdicts on this case when the same code, the same models and the same label and
    candidates produced them: a run that died, or one started without a token, need not ask the models again."""
    if not old or old.get("version") != ver or old.get("label") != case.label:
        return None
    prior = db.loads(old.get("verdicts"), {})
    if set(prior) != set(models):
        return None
    cands = set(case.candidate_ids())
    for d in prior.values():
        v = d.get("verdict", "")
        if v.startswith("Q") and v not in cands:
            return None
    return [J.Verdict(verdict=d.get("verdict") or "unsure", confidence=float(d.get("confidence") or 0),
                      because=d.get("because") or "", flags=list(d.get("flags") or []), model=m) for m, d in prior.items()]


def run_live(con, models: list[str], *, node: str | None = None, search: bool = True, mode: str = "json",
             threshold: float | None = None, apply: bool = False, apply_above: float | None = None,
             limit: int | None = None, kinds: list[str] | None = None, force: bool = False, log=print, progress=None,
             src: GlassDatabase | None = None) -> dict:
    """The open queue through the panel; suggestions back when a token is set; decisions only with ``apply``.
    A case this code and this panel judged before is reused, not judged again, unless ``force``; a suggestion
    not yet written (no token last time) is written from the stored verdicts."""
    threshold = config.RESOLVE_THRESHOLD if threshold is None else float(threshold)
    apply_above = max(threshold, 0.9) if apply_above is None else float(apply_above)
    src = src or GlassDatabase(log=log)
    ver = version()
    cases = fetch_cases(con, ("unsure",), kinds=kinds, limit=limit, log=log, src=src)
    log(f"{len(cases)} open question(s) on {src.base}; panel: {', '.join(models)}; threshold {threshold}"
        + ("" if src.can_write() else "; no GLASSDB_ADMIN_TOKEN, so nothing is written back")
        + (f"; decisions at ≥{apply_above} will be applied" if apply and src.can_write() else ""))
    if not cases:
        return {"cases": 0, "settled": 0, "open": 0, "suggested": 0, "applied": 0, "reused": 0, "version": ver}
    existing = {r["key"]: r for r in db.rows(con, "SELECT * FROM resolve_queue")}
    prior = {} if force else {c.key: _prior_verdicts(existing.get(c.key), c, models, ver) for c in cases}
    prior = {k: v for k, v in prior.items() if v}
    if prior:
        log(f"  {len(prior)} case(s) judged before by this code and panel are reused; the rest go to the models")
    ev = {c.key: E.gather(con, c, use_search=search, log=log) for c in cases if c.key not in prior}
    if any(_partial(e) for e in ev.values()):
        log(f"  Wikidata facts could not be read for {sum(_partial(e) for e in ev.values())} case(s): those are judged from the "
            "lookup's own candidate descriptions, with less to go on")
    searched = bool(search and config.SEARXNG_URL)
    workers = _workers(models, node)
    counts = {"cases": len(cases), "settled": 0, "open": 0, "suggested": 0, "applied": 0, "reused": len(prior),
              "by_kind": {}, "version": ver}

    def panel(case: Case) -> list[J.Verdict]:
        def one(m):
            try:
                return judge_case(m, case, ev[case.key], node, mode)
            except Exception as e:  # noqa: BLE001
                return J.Verdict(verdict="unsure", confidence=0.0, because=f"call failed: {type(e).__name__}: {e}",
                                 ok=False, model=m, flags=["call failed"])
        if workers <= 1 or len(models) == 1:
            return [one(m) for m in models]
        with ThreadPoolExecutor(max_workers=workers) as ex:
            return list(ex.map(one, models))

    for i, case in enumerate(cases):
        old = existing.get(case.key) or {}
        reused = case.key in prior
        vs = prior[case.key] if reused else panel(case)
        cons = consensus(vs, threshold)
        kind = counts["by_kind"].setdefault(case.kind, {"settled": 0, "open": 0})
        kind["settled" if cons["settled"] else "open"] += 1
        counts["settled" if cons["settled"] else "open"] += 1
        row = {"key": case.key, "kind": case.kind, "label": case.label, "verdict": cons["verdict"],
               "confidence": cons["confidence"], "settled": int(cons["settled"]), "because": cons["because"],
               "verdicts": cons["models"], "searched": int(old.get("searched") or 0) if reused else int(searched),
               "version": ver, "updated_at": db.now(),
               "suggested_at": old.get("suggested_at") if reused else None,
               "applied_at": old.get("applied_at") if reused else None,
               "applied_qid": old.get("applied_qid") if reused else None}
        suggestion = {"qid": cons["verdict"] if cons["verdict"].startswith("Q") else "", "verdict": cons["verdict"],
                      "confidence": cons["confidence"], "because": cons["because"], "settled": cons["settled"],
                      "models": cons["models"], "searched": bool(row["searched"]), "version": ver, "at": db.now()}
        if src.can_write():
            if not row.get("suggested_at"):
                try:
                    src.suggest(case.key, suggestion)
                    row["suggested_at"] = db.now()
                    counts["suggested"] += 1
                except Exception as e:  # noqa: BLE001
                    log(f"  {case.key}: suggestion not written ({e})")
            if apply and cons["settled"] and cons["confidence"] >= apply_above and cons["verdict"] != "unsure" \
                    and not row.get("applied_at"):
                try:
                    src.decide(case.key, suggestion["qid"])
                    row["applied_at"], row["applied_qid"] = db.now(), suggestion["qid"]
                    counts["applied"] += 1
                except Exception as e:  # noqa: BLE001
                    log(f"  {case.key}: decision not applied ({e})")
        db.upsert(con, "resolve_queue", [row], keys=("key",), stamp=False)
        con.commit()
        mark = "settled" if cons["settled"] else "open"
        log(f"  {case.label[:30]:<30} {mark:<8} {cons['verdict']:<10} {cons['confidence']:.2f}  "
            + "  ".join(f"{m.split(':')[0]}={d['verdict']}@{d['confidence']:.2f}" for m, d in cons["models"].items())
            + ("  (reused)" if reused else "") + ("  applied" if row.get("applied_at") else ""))
        if progress:
            progress((i + 1) / len(cases))
    log(f"settled {counts['settled']}, open {counts['open']}"
        + (f"; {counts['reused']} reused from the last run" if counts["reused"] else "")
        + (f"; {counts['suggested']} suggestion(s) written back" if counts["suggested"] else "")
        + (f"; {counts['applied']} decision(s) applied" if counts["applied"] else ""))
    return counts


def queue_rows(con, state: str = "all", limit: int = 300) -> list[dict]:
    """What the live run last concluded per case, with the case's own details for the page."""
    where = {"open": "WHERE q.settled=0", "settled": "WHERE q.settled=1", "applied": "WHERE q.applied_at IS NOT NULL"}.get(state, "")
    rows = db.rows(con, f"SELECT q.*, c.description, c.candidates, c.url, c.status AS case_status FROM resolve_queue q "
                        f"LEFT JOIN resolve_cases c ON c.key=q.key {where} ORDER BY q.settled DESC, q.confidence DESC, q.label "
                        f"LIMIT {int(limit)}")
    for r in rows:
        r["verdicts"] = db.loads(r.get("verdicts"), {})
        r["candidates"] = db.loads(r.get("candidates"), [])
    return rows
