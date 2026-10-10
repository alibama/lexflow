"""Ablate the active-learning labels (curated_labels/) and the list lead-in views on the 22 held-out-state cases.

    python scripts/selector_ablation.py        -> docs/selector_ablation.json
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

ARMS = {"base": (False, False), "labels": (True, False), "views": (False, True), "both": (True, True)}


def main() -> int:
    cases = B.cases()
    loaded = {c: B.load_case(c) for c in cases}
    per = {}
    for arm, (partial, views) in ARMS.items():
        SEL.USE_PARTIAL, SEL.VIEWS = partial, views
        SEL._references.cache_clear()
        SEL._TFIDF.clear()
        per[arm] = {}
        for c in cases:
            state, q, texts, text, gold, _ = loaded[c]
            r = ST.run("stack_combo", text, section=texts[0].section, title="", code="", jurisdiction=state,
                       question=q, state=state)
            per[arm][c] = B.equivalence(r.facts, gold)["value"] if r.facts else 0.0
        print(arm, round(st.mean(per[arm].values()), 4), flush=True)
    out = {}
    for arm in ARMS:
        deltas = [per[arm][c] - per["base"][c] for c in cases]
        rng = random.Random(11)
        boots = sorted(st.mean(rng.choice(deltas) for _ in deltas) for _ in range(2000))
        out[arm] = {"mean": round(st.mean(per[arm].values()), 4),
                    "records": round(st.mean(v for c, v in per[arm].items() if c.endswith("records")), 4),
                    "business": round(st.mean(v for c, v in per[arm].items() if c.endswith("business")), 4),
                    "delta": round(st.mean(deltas), 4), "delta_90ci": [round(boots[100], 4), round(boots[1900], 4)]}
    print(json.dumps(out, indent=1))
    (ROOT / "docs" / "selector_ablation.json").write_text(json.dumps({"summary": out, "cases": per}, indent=1),
                                                         encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
