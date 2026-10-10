"""Active learning: which sentences Claude should label next.

The learning curve still rises with every state that has a reference, but a whole reference costs a full
draft-review-fix round.  Labelling only the sentences the selector is least sure of, in states that have no
reference yet, adds those states' drafting styles to the training data for a fraction of the cost.

    queue(con, state, question)   -> the n candidates nearest the keep threshold, de-duplicated, with context
    check(state, question)        -> problems with curated_labels/<state>/<question>.json (quotes must be exact)
"""
from __future__ import annotations

import json
import re

from ..store import db
from . import selector as SEL
from .segment import segment


def sections_for(con, state: str, question: str) -> list[str]:
    r = db.one(con, "SELECT metrics FROM process_models WHERE model_id=?", f"{state}.{question}")
    return list((db.loads(r["metrics"], {}) or {}).get("sections") or []) if r else []


def queue(con, state: str, question: str, n: int = 40, vectors: str = "tfidf") -> dict:
    from ..municipal import statutes
    refs = sections_for(con, state, question)
    if not refs:
        return {"state": state, "question": question, "items": [], "why": "no sections located"}
    texts = statutes.section_texts(state, refs)
    clauses = segment(statutes.combined_text(texts))
    cands = [d for d in SEL.wide_drafts(clauses, question) if d.get("origin") not in ("trigger", "second")]
    emb = SEL.tfidf() if vectors == "tfidf" else SEL.Combo(SEL.tfidf(), SEL.Embedder())
    sel = SEL.Selector(question, state, emb).fit()
    p = sel.predict(cands)
    x = getattr(sel, "_x", None)
    order = sorted(range(len(cands)), key=lambda i: abs(float(p[i]) - sel.threshold))
    chosen: list[int] = []
    for i in order:
        if len(chosen) >= n:
            break
        if x is not None and any(float(x[i] @ x[j]) >= 0.8 for j in chosen):
            continue                                   # one of each kind of sentence
        chosen.append(i)
    idx = {c.id: k for k, c in enumerate(clauses)}
    items = []
    for i in sorted(chosen, key=lambda i: cands[i]["clause"].start):
        c = cands[i]["clause"]
        k = idx[c.id]
        prev = clauses[k - 1].text if k > 0 and clauses[k - 1].section == c.section else ""
        items.append({"section": c.section or texts[0].section, "label": c.label, "quote": c.text,
                      "before": prev[-300:], "score": round(float(p[i]), 3)})
    return {"state": state, "question": question, "sections": refs, "threshold": round(sel.threshold, 3),
            "items": items}


def check(spec: dict) -> list[str]:
    """Every label's quote must be a whole clause of its section, as the segmenter cuts it."""
    from ..municipal import statutes
    problems = []
    try:
        texts = statutes.section_texts(spec["state"], spec["sections"])
    except Exception as e:  # noqa: BLE001
        return [f"sections: {e}"]
    clauses = {(SEL._norm(c.text), c.section) for c in segment(statutes.combined_text(texts))}
    plain = {t for t, _ in clauses}
    for i, lab in enumerate(spec.get("labels") or []):
        if not isinstance(lab.get("is_step"), bool):
            problems.append(f"label {i}: is_step must be true or false")
        if lab.get("is_step") and lab.get("actor_kind") not in ("public-body", "official", "private-party", "court",
                                                                "other-government"):
            problems.append(f"label {i}: a step needs actor_kind")
        q = SEL._norm(lab.get("quote"))
        if (q, lab.get("section")) not in clauses and q not in plain:
            problems.append(f"label {i}: the quote is not one whole clause of the text: {lab.get('quote', '')[:80]!r}")
        dl = lab.get("deadline")
        if dl:
            from .segment import DEADLINE, _amount
            amounts = {_amount(m.group("amount")) for m in DEADLINE.finditer(lab.get("quote", ""))}
            if dl.get("amount") not in amounts and not re.search(rf"\b{int(dl.get('amount') or -1)}\b",
                                                                  lab.get("quote", "")):
                problems.append(f"label {i}: deadline amount {dl.get('amount')} is not in the quote")
    return problems


def write_queue(con, out_dir, states: list[str], questions: list[str], n: int = 40) -> list[str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for st in states:
        for q in questions:
            data = queue(con, st, q, n=n)
            if data["items"]:
                p = out_dir / f"{st}_{q}.json"
                p.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
                written.append(str(p))
    return written
