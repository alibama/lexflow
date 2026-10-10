"""How much does each additional Claude reference help?  Score the stacked selector with only k training states
(k = 2, 4, ... all), several random draws per k, every case held out by state as usual.

    python scripts/learning_curve.py [vectors] [draws]      -> docs/learning_curve.json
"""
from __future__ import annotations

import json
import random
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lexflow.extract import benchmark as B  # noqa: E402
from lexflow.extract import selector as SEL  # noqa: E402
from lexflow.extract import strategies as ST  # noqa: E402
from lexflow.extract.segment import segment  # noqa: E402


def main(vectors: str = "combo", draws: str = "3") -> int:
    cases = B.cases()
    loaded = {c: B.load_case(c) for c in cases}
    states = sorted({c.split(".")[0] for c in cases})
    out = []
    for k in list(range(2, len(states) - 1, 2)) + [len(states) - 1]:
        vals = []
        for draw in range(int(draws) if k < len(states) - 1 else 1):
            rng = random.Random(1000 * k + draw)
            for c in cases:
                state, q, texts, text, gold, _ = loaded[c]
                others = [s for s in states if s != state]
                only = set(rng.sample(others, min(k, len(others))))
                clauses = segment(text)
                drafts = ST.stacked_drafts(clauses, q, state, vectors=vectors, only_states=only)
                vals.append(B.equivalence(ST.assemble(drafts, clauses, texts[0].section, q, "x"), gold)["value"]
                            if drafts else 0.0)
        row = {"training_states": k, "mean": round(st.mean(vals), 3), "runs": len(vals),
               "sd": round(st.pstdev(vals), 3)}
        out.append(row)
        print(row, flush=True)
    path = ROOT / "docs" / "learning_curve.json"
    path.write_text(json.dumps({"vectors": vectors, "cases": len(cases), "curve": out}, indent=1), encoding="utf-8")
    print("wrote", path)
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
