"""Turn per-state verification results into curated/seeds.json, keeping only references that check out.

    python scripts/make_seeds.py results.json [curated/seeds.json]

Each result names a section reference and a quote for 'records' and 'business'.  A reference is kept only if
it resolves in the downloaded statutes and the quote appears word for word in that section.  Existing
entries are kept unless a new verified one replaces them.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lexflow.municipal import statutes  # noqa: E402


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").replace("’", "'").replace("“", '"').replace("”", '"')).strip().lower()


def main(src: str, dst: str = str(ROOT / "curated" / "seeds.json")) -> int:
    results = json.loads(Path(src).read_text(encoding="utf-8"))
    out = json.loads(Path(dst).read_text(encoding="utf-8")) if Path(dst).exists() else {
        "note": "Verified statute sections per state and question. Each was found by an agent reading the downloaded "
                "open-us-law text and is kept only if the reference resolves and the quote appears in the section.",
        "states": {}}
    kept, rejected = 0, []
    for r in results:
        st = r["state"]
        for q in ("records", "business"):
            v = r.get(q) or {}
            entry = {k: v.get(k) for k in ("found", "ref", "citation", "act", "quote", "alternates", "confidence", "why")}
            entry["checked"] = str(date.today())
            if not v.get("found"):
                out["states"].setdefault(st, {})[q] = {**entry, "found": False}
                continue
            df = statutes.load(st)
            row, used = None, None
            for ref in dict.fromkeys(x for x in (v.get("ref"), v.get("citation")) if x):
                try:
                    hit = statutes.find(df, ref)
                except Exception:  # noqa: BLE001
                    continue
                # several rows can share a number across acts: take the one that contains the quote
                match = hit[hit["text"].map(norm).str.contains(re.escape(norm(v.get("quote"))), regex=True)]
                if norm(v.get("quote")) and not match.empty:
                    row, used = match.iloc[0], ref
                    break
            if row is None:
                rejected.append(f"{st} {q}: {v.get('ref')}: the quote is not in any section the reference names")
                continue
            # store the most specific reference that resolves to exactly this section
            exact = statutes.find(df, row["citation"])
            entry["ref"] = row["citation"] if len(exact) == 1 else used
            entry["citation"] = row["citation"]
            out["states"].setdefault(st, {})[q] = entry
            kept += 1
    Path(dst).write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"kept {kept} verified sections; {len(rejected)} rejected")
    for x in rejected:
        print("  rejected:", x)
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
