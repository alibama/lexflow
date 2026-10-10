"""Selector round 2: compare ways of deciding which scored candidates to keep, on the 22 held-out-state cases.

    python scripts/selector_experiments.py [vectors]      -> docs/selector_experiments.json

V0  the per-question threshold tuned on the training states (the current rule)
V1  a per-case budget: keep the k best candidates that maximise expected F1 under the scores
V1d V1, skipping near-duplicates of a kept clause (cosine >= 0.92) unless they add a deadline
V2  a second-stage model over the clause sequence (stacked sequential learning): the score of the previous and
    next candidate, the best score among list siblings and in the section, rank within the case, the case size,
    and whether the next clause sets a deadline; trained on the training states' first-stage scores, with
    the V0-style threshold and the V1 budget as two cuts
Each variant is scored with the same actor assignment and the same equivalence as the benchmark.
"""
from __future__ import annotations

import json
import random
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402

from lexflow.extract import benchmark as B  # noqa: E402
from lexflow.extract import selector as SEL  # noqa: E402
from lexflow.extract import strategies as ST  # noqa: E402
from lexflow.extract.segment import segment  # noqa: E402


def context(cands: list[dict], p: np.ndarray) -> np.ndarray:
    """Second-stage columns for each candidate, from the first-stage scores of its neighbours."""
    n = len(cands)
    order = sorted(range(n), key=lambda i: cands[i]["clause"].start)
    pos = {i: k for k, i in enumerate(order)}
    rank = np.argsort(np.argsort(-p))
    cols = []
    for i, d in enumerate(cands):
        c = d["clause"]
        k = pos[i]
        prev_i = order[k - 1] if k > 0 and cands[order[k - 1]]["clause"].section == c.section else None
        next_i = order[k + 1] if k + 1 < n and cands[order[k + 1]]["clause"].section == c.section else None
        parent = (c.label or "").rsplit(".", 1)[0]
        sibs = [j for j in range(n) if j != i and (cands[j]["clause"].label or "").rsplit(".", 1)[0] == parent
                and cands[j]["clause"].section == c.section]
        sec = [j for j in range(n) if cands[j]["clause"].section == c.section]
        cols.append([p[i], p[prev_i] if prev_i is not None else 0.0, p[next_i] if next_i is not None else 0.0,
                     max((p[j] for j in sibs), default=0.0), max(p[j] for j in sec),
                     rank[i] / max(1, n - 1), np.log(n),
                     1.0 if next_i is not None and cands[next_i]["clause"].deadline else 0.0,
                     1.0 if d.get("origin") == "list" else 0.0])
    return np.array(cols, dtype=float)


def f1(keep: np.ndarray, y: np.ndarray, n_gold: int) -> float:
    tp = float((keep & (y > 0)).sum())
    p = tp / max(1, keep.sum())
    r = tp / max(1, n_gold)
    return 2 * p * r / (p + r) if p + r else 0.0


def budget_keep(p: np.ndarray) -> np.ndarray:
    k = ST.expected_f1_budget(p)
    keep = np.zeros(len(p), dtype=bool)
    keep[np.argsort(-p)[:k]] = True
    return keep


def dedupe(keep: np.ndarray, p: np.ndarray, x, cands, thr: float = 0.92) -> np.ndarray:
    if x is None:
        return keep
    out = np.zeros(len(p), dtype=bool)
    accepted: list[int] = []
    for i in np.argsort(-p):
        if not keep[i]:
            continue
        dup = any(float(x[i] @ x[j]) >= thr for j in accepted)
        adds_deadline = cands[i]["clause"].deadline and not any(cands[j]["clause"].deadline for j in accepted)
        if not dup or adds_deadline:
            out[i] = True
            accepted.append(i)
    return out


def main(vectors: str = "combo") -> int:
    rows = []
    for case in B.cases():
        state, q, texts, text, gold, _ = B.load_case(case)
        clauses = segment(text)
        cands = SEL.wide_drafts(clauses, q)
        emb = SEL.Combo(SEL.tfidf(), SEL.Embedder()) if vectors == "combo" else SEL.tfidf()
        sel = SEL.Selector(q, state, emb).fit()
        p = sel.predict(cands)
        x = getattr(sel, "_x", None)
        # stage 2, trained on the training cases' first-stage scores
        Xtr, ytr = [], []
        for pi, yi, r in sel.train_preds:
            Xtr.append(context(r.cands, pi))
            ytr.append(yi)
        Xtr, ytr = np.vstack(Xtr), np.concatenate(ytr)
        mu, sd = Xtr.mean(axis=0), Xtr.std(axis=0) + 1e-6
        beta2 = SEL._fit_lr((Xtr - mu) / sd, ytr, np.ones(len(ytr)))
        t2, best = 0.5, -1
        same = [(pi, yi, r) for pi, yi, r in sel.train_preds if r.question == q] or sel.train_preds
        p2_train = [(SEL._predict(beta2, (context(r.cands, pi) - mu) / sd), yi, r) for pi, yi, r in same]
        for t in np.arange(0.03, 0.7, 0.01):
            m = np.mean([f1(pp >= t, yi, len(r.quotes)) for pp, yi, r in p2_train])
            if m > best:
                best, t2 = m, float(t)
        p2 = SEL._predict(beta2, (context(cands, p) - mu) / sd)
        variants = {"V0": p >= sel.threshold, "V1": budget_keep(p), "V1d": dedupe(budget_keep(p), p, x, cands),
                    "V2": p2 >= t2, "V2b": budget_keep(p2)}
        res = {"case": case}
        for name, keep in variants.items():
            drafts = [d for d, k in zip(cands, keep) if k]       # the originals: assign_actors keys on them
            ST.assign_actors(drafts, cands, sel, q)
            drafts.sort(key=lambda d: d["clause"].start)
            if not drafts:
                res[name] = 0.0
                continue
            e = B.equivalence(ST.assemble(drafts, clauses, texts[0].section, q, "x"), gold)
            res[name] = e["value"]
            res[name + "_n"] = len(drafts)
        rows.append(res)
        print(json.dumps(res), flush=True)
    names = ["V0", "V1", "V1d", "V2", "V2b"]
    summary = {}
    for nm in names:
        vals = [r[nm] for r in rows]
        deltas = [r[nm] - r["V0"] for r in rows]
        rng = random.Random(7)
        boots = sorted(st.mean(rng.choice(deltas) for _ in deltas) for _ in range(2000))
        summary[nm] = {"mean": round(st.mean(vals), 4),
                       "records": round(st.mean(r[nm] for r in rows if r["case"].endswith("records")), 4),
                       "business": round(st.mean(r[nm] for r in rows if r["case"].endswith("business")), 4),
                       "delta_vs_V0": round(st.mean(deltas), 4),
                       "delta_90ci": [round(boots[100], 4), round(boots[1900], 4)]}
    print(json.dumps(summary, indent=1))
    (ROOT / "docs" / "selector_experiments.json").write_text(json.dumps({"vectors": vectors, "summary": summary,
                                                                         "rows": rows}, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
