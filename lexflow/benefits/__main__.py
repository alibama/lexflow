"""``python -m lexflow.benefits``: load the Census pension data, check the fixtures, look up programs.

    python -m lexflow.benefits census [--dry-run]           ASPP unit files -> pension_systems, pension_coverage
    python -m lexflow.benefits check                         match every quote of every benefits fixture
    python -m lexflow.benefits stats [--json]                coverage of each layer by state
    python -m lexflow.benefits lookup <gov_id|state|place> <person> [--json]
    python -m lexflow.benefits ask <gov_id|state|place> <person>   the "who do I ask" answer as text
    python -m lexflow.benefits family-va                     write fixtures/families/retirement_va.json (then fill it)
    python -m lexflow.benefits wikidata [--states va,md] [--write]  exact Wikidata matches for the systems' bodies
    python -m lexflow.benefits wikibase                      the proposed Wikibase items, as a dry run (nothing sent)
"""
from __future__ import annotations

import argparse
import json
import sys

from ..store import db


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m lexflow.benefits", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("census")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--download", action="store_true", help="fetch the unit files first (once)")
    sub.add_parser("check")
    p = sub.add_parser("stats")
    p.add_argument("--json", action="store_true")
    for name in ("lookup", "ask"):
        p = sub.add_parser(name)
        p.add_argument("place")
        p.add_argument("person")
        p.add_argument("--json", action="store_true")
    sub.add_parser("family-va")
    p = sub.add_parser("wikidata")
    p.add_argument("--states")
    p.add_argument("--write", action="store_true")
    sub.add_parser("wikibase")
    a = ap.parse_args(argv)
    if a.cmd == "census":
        from . import census as C
        if a.download:
            C.download()
        con = db.connect()
        try:
            print(json.dumps(C.load(con, dry_run=a.dry_run), indent=1))
        finally:
            con.close()
        return 0
    if a.cmd == "check":
        from . import programs as PR
        from . import ground as G
        bad = 0
        files = sorted(PR.SYSTEMS_DIR.glob("*.json")) + sorted(PR.TAX_DIR.glob("*.json")) + [PR.AUTO_IRA, PR.FEDERAL]
        tot = {"sources": 0, "matched": 0}
        for f in files:
            doc = json.loads(f.read_text(encoding="utf-8"))
            rep = G.ground_all(doc, doc.get("state") if isinstance(doc, dict) else None)
            tot["sources"] += rep["sources"]
            tot["matched"] += rep["matched"]
            for u in rep["unmatched"]:
                bad += 1
                print(f"{f.relative_to(PR.FIX)}: UNMATCHED {u['ref']}: {u['why']}")
        print(f"{tot['matched']} of {tot['sources']} sources matched in {len(files)} files")
        return 1 if bad else 0
    if a.cmd == "stats":
        from . import programs as PR
        s = PR.stats()
        if a.json:
            print(json.dumps(s, indent=1))
        else:
            for k in ("systems_summary", "auto_ira_summary", "tax_summary"):
                print(k, json.dumps(s[k]))
        return 0
    if a.cmd in ("lookup", "ask"):
        from . import lookup as L
        out = L.lookup(a.place, a.person)
        if a.cmd == "ask":
            out = L.ask(a.place, a.person)
            print(json.dumps(out, indent=1, ensure_ascii=False) if a.json else L.render(out))
        else:
            print(json.dumps(out, indent=1, ensure_ascii=False, default=str) if a.json else L.render_lookup(out))
        return 0
    if a.cmd == "family-va":
        from . import family_va as F
        print(json.dumps(F.write()))
        print("now: python -m lexflow.scenarios.family --fill retirement_va", file=sys.stderr)
        return 0
    if a.cmd == "wikidata":
        from . import systems as SY
        print(json.dumps(SY.wikidata_all([s for s in (a.states or "").split(",") if s] or None, write=a.write),
                         indent=1))
        return 0
    if a.cmd == "wikibase":
        from . import wikibase as WB
        print(json.dumps(WB.dry_run(), indent=1, ensure_ascii=False))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
