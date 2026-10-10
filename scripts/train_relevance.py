"""Train the section-relevance model on AskBench's gold sections, evaluated leaving one question out.

    python scripts/train_relevance.py        -> data/ask_relevance.json, docs/ask_relevance.json (the evaluation)
"""
from __future__ import annotations

import json
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lexflow import config  # noqa: E402
from lexflow.ask import index as I  # noqa: E402
from lexflow.ask import reference as R  # noqa: E402
from lexflow.ask import relevance as RV  # noqa: E402
from lexflow.ask.plan import plan as make_plan  # noqa: E402
from lexflow.ask.retrieve import fused, rerank  # noqa: E402
from lexflow.extract.selector import Embedder  # noqa: E402


def recall_at(order: list[int], gold: list[set[int]], k: int) -> float | None:
    if not gold:
        return None
    top = set(order[:k])
    return sum(1 for g in gold if g & top) / len(gold)


def main() -> int:
    emb = Embedder()
    cases = []
    for qid, state in R.cases():
        ref = R.load(qid, state)
        if not ref.get("gold_sections"):
            continue
        p = make_plan(ref["question"])
        cands, concepts = fused(state, p)
        ranked = rerank(p.text, cands[:80], emb)
        gold = [{r["id"] for r in I.lookup(state, g["ref"])} for g in ref["gold_sections"]]
        ids = [c["id"] for c in ranked]
        labels = [int(any(c in g for g in gold)) for c in ids]
        cases.append({"case": f"{qid}.{state}", "qid": qid, "ranked": ranked, "concepts": concepts, "gold": gold,
                      "ids": ids, "labels": labels, "X": RV.features(ranked, concepts)})
        print(f"{qid}.{state}: {len(ranked)} candidates, {sum(labels)} gold among them of {len(gold)}", flush=True)
    evals = []
    for q in sorted({c["qid"] for c in cases}):
        train = [(c["X"], c["labels"], c["qid"]) for c in cases if c["qid"] != q and sum(c["labels"])]
        model = RV.fit(train)
        RV.loqo_path(q).parent.mkdir(parents=True, exist_ok=True)
        RV.loqo_path(q).write_text(json.dumps(model), encoding="utf-8")
        for c in (c for c in cases if c["qid"] == q):
            p = RV.score(c["ranked"], c["concepts"], model)
            learned = [c["ids"][i] for i in sorted(range(len(p)), key=lambda i: -p[i])]
            row = {"case": c["case"]}
            for k in (5, 10):
                row[f"heuristic@{k}"] = recall_at(c["ids"], c["gold"], k)
                row[f"learned@{k}"] = recall_at(learned, c["gold"], k)
            row["top_p"] = round(max(p), 3)
            evals.append(row)
    summary = {k: round(st.mean(r[k] for r in evals if r[k] is not None), 3)
               for k in ("heuristic@5", "learned@5", "heuristic@10", "learned@10")}
    print(json.dumps(summary, indent=1))
    final = RV.fit([(c["X"], c["labels"], c["qid"]) for c in cases if sum(c["labels"])])
    RV.model_path().write_text(json.dumps(final), encoding="utf-8")
    (ROOT / "docs" / "ask_relevance.json").write_text(json.dumps({"summary": summary, "cases": evals}, indent=1),
                                                     encoding="utf-8")
    print("wrote", RV.model_path(), "trained on", final["trained_on"], "cases; data dir", config.DATA_DIR)
    return 0


if __name__ == "__main__":
    sys.exit(main())
