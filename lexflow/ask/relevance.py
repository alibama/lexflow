"""Learned section relevance for new questions: which retrieved sections Claude's references actually rest on.

The hand-set reranker (fused rank and meaning) finds the topic but not always the procedure.  This model learns
from AskBench's gold sections what the right sections look like among the candidates: their fused rank and which
searches found them, their meaning, their length and heading, and their place in the reranked list.  It is
evaluated leaving one whole question out (a new question has no references), and its top score gates the answer.

    data/ask_relevance.json   {"beta": [...], "mu": [...], "sd": [...], "features": [...], "trained_on": n}
"""
from __future__ import annotations

import json
import math
import re

from .. import config

FEATURES = ["rrf_rel", "sim", "title_all", "all", "procedure", "rarest", "title_any", "any", "facet", "log_words",
            "rank_rel", "definitions", "title_concepts", "future_version"]
# Tried and left out (leave-one-question-out recall@10 on the same candidates, 0.235 without): which pass found a
# section through the code's structure (unit, cited) and whether it shares the best hit's chapter, 0.231 with all.
DEFINITIONS = re.compile(r"^\s*(definitions?|short title|purpose|applicability|construction)\b", re.I)


def model_path():
    return config.DATA_DIR / "ask_relevance.json"


def features(cands: list[dict], concepts: list[dict]) -> list[list[float]]:
    """One row per candidate (the reranked list from retrieve.rerank, best first)."""
    if not cands:
        return []
    top = max(c.get("rrf") or 0 for c in cands) or 1.0
    pats = [re.compile(r"\b(?:" + "|".join(re.escape(t) for t in x["terms"] if len(t) > 2) + r")", re.I)
            for x in concepts if any(len(t) > 2 for t in x["terms"])]
    rows = []
    for i, c in enumerate(cands):
        passes = set(c.get("passes") or [])
        rows.append([(c.get("rrf") or 0) / top, c.get("similarity") or 0.0,
                     *[1.0 if p in passes else 0.0 for p in ("title_all", "all", "procedure", "rarest", "title_any", "any",
                                                             "facet")],
                     math.log10(max(10, c.get("words") or 10)), i / max(1, len(cands) - 1),
                     1.0 if DEFINITIONS.match(c.get("title") or "") else 0.0,
                     float(sum(1 for p in pats if p.search(c.get("title") or ""))),
                     1.0 if c.get("version") else 0.0])
    return rows


OVERRIDE = None          # a model to use instead of the saved one (the benchmark's held-out-question models)


def loqo_path(qid: str):
    """The model trained without one question: the benchmark scores each question with the model that never saw it."""
    return config.DATA_DIR / "ask_relevance_loqo" / f"{qid}.json"


def load():
    if OVERRIDE is not None:
        return OVERRIDE
    p = model_path()
    if not p.exists():
        return None
    try:
        m = json.loads(p.read_text(encoding="utf-8"))
        return m if m.get("features") == FEATURES else None
    except ValueError:
        return None


def score(cands: list[dict], concepts: list[dict], model=None) -> list[float] | None:
    """The learned probability that each candidate is a section the answer rests on (None without a model)."""
    import numpy as np
    model = model or load()
    if model is None or not cands:
        return None
    X = np.asarray(features(cands, concepts), dtype=float)
    mu, sd, beta = (np.asarray(model[k], dtype=float) for k in ("mu", "sd", "beta"))
    Z = np.hstack([(X - mu) / sd, np.ones((len(X), 1))])
    return list(1 / (1 + np.exp(-Z @ beta)))


def fit(rows: list[tuple[list[list[float]], list[int], str]]):
    """rows: (features, labels, question id) per case -> the model fitted on all of them."""
    import numpy as np
    from ..extract.selector import _fit_lr
    X = np.vstack([np.asarray(f, dtype=float) for f, _, _ in rows])
    y = np.concatenate([np.asarray(l, dtype=float) for _, l, _ in rows])
    mu, sd = X.mean(axis=0), X.std(axis=0) + 1e-6
    beta = _fit_lr((X - mu) / sd, y, np.ones(len(y)), l2=2.0)
    return {"features": FEATURES, "mu": mu.tolist(), "sd": sd.tolist(), "beta": beta.tolist(), "trained_on": len(rows)}
