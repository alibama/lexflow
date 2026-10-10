"""Mean benchmark components per strategy (latest run per case, scored against the current references).

    python scripts/bench_summary.py [strategy,strategy,...]
"""
from __future__ import annotations

import statistics as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lexflow.extract import benchmark as B  # noqa: E402
from lexflow.store import db  # noqa: E402

KEYS = ("equivalence", "step_f1", "step_recall", "step_precision", "actors", "deadlines", "modality")


def main(which: str = "", write: str = "") -> int:
    rows = B.best(db.connect())
    if which == "--write":
        which, write = "", "docs/benchmark.json"
    want = which.split(",") if which else sorted({(r["strategy"], r["model"]) for r in rows})
    groups = {}
    for r in rows:
        key = f"{r['strategy']}/{r['model']}" if r["model"] != "-" else r["strategy"]
        if which and r["strategy"] not in want:
            continue
        groups.setdefault(key, []).append(r)
    n_cases = len(B.cases())
    print(f"{'strategy':28} {'n':>3} " + " ".join(f"{k[:9]:>9}" for k in KEYS) + "  records business")
    summary = []
    for key, rs in sorted(groups.items(), key=lambda kv: -st.mean(r["equivalence"] for r in kv[1])):
        m = [st.mean((r.get(k) or 0) for r in rs) for k in KEYS]
        by_q = [st.mean(r["equivalence"] for r in rs if r["case"].endswith(q)) if any(r["case"].endswith(q) for r in rs)
                else float("nan") for q in (".records", ".business")]
        print(f"{key:28} {len(rs):>3} " + " ".join(f"{v:9.3f}" for v in m)
              + f"  {by_q[0]:7.3f} {by_q[1]:8.3f}" + ("" if len(rs) == n_cases else "  (partial)"))
        if len(rs) == n_cases:
            summary.append({"strategy": key, **{k: round(v, 3) for k, v in zip(KEYS, m)},
                            "records": round(by_q[0], 3), "business": round(by_q[1], 3),
                            "seconds": round(st.mean(r["seconds"] or 0 for r in rs), 1)})
    if write:
        import json
        from datetime import date
        out = Path(write) if Path(write).is_absolute() else Path(__file__).resolve().parents[1] / write
        out.write_text(json.dumps({"generated": str(date.today()), "cases": n_cases, "strategies": summary},
                                  indent=1), encoding="utf-8")
        print("wrote", out)
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
