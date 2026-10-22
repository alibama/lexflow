"""Read-only helpers for writing the benefits fixtures: search a state's statute index, print a section, read an
official page politely, and check a quote the way the loaders will.

    python -m lexflow.benefits.research search va "Virginia Retirement System" ["established"] [--any] [--limit 20]
    python -m lexflow.benefits.research section va 51.1-153 [--grep "Rule of 90"] [--chars 4000]
    python -m lexflow.benefits.research check va 51.1-153 "the quote, word for word"
    python -m lexflow.benefits.research page https://www.varetire.org/ [--grep retire] [--chars 3000]
    python -m lexflow.benefits.research pagecheck https://www.varetire.org/ "the quote, word for word"

``page`` uses lexflow's quote fetch (``lexflow.municipal.quotes.fetch``): GET only, the lexflow-research
User-Agent, robots.txt obeyed, at least 1.5 seconds between two requests to one host, nothing behind a login, an
Internet Archive capture when the live host refuses automated readers; the text is cached under
``<LEXFLOW_DATA>/cache/quote_pages`` so a page is read once.  A quote checked here with ``check`` or ``pagecheck``
is matched by the same code that grounds the fixtures (``lexflow.benefits.ground``).
"""
from __future__ import annotations

import argparse
import re
import sys


def _out(s: str) -> None:
    sys.stdout.write(s + "\n")


def search(state: str, phrases: list[str], any_: bool = False, limit: int = 20) -> list[dict]:
    from ..ask import index as I
    expr = I.match([[p] for p in phrases], mode="or" if any_ else "and")
    return I.search(state, expr, limit=limit) if expr else []


def section(state: str, ref: str) -> list[dict]:
    from ..ask import index as I
    return I.lookup(state, ref, with_text=True)


def check(state: str, ref: str, quote: str) -> bool:
    from .. import validate
    return any(validate.quote_in(quote, r.get("text") or "") for r in section(state, ref))


def page(url: str, quotes: list[str] | None = None, log=print) -> dict | None:
    """The page as lexflow's quote fetch read it (fetched once, politely, when it is not cached)."""
    from ..municipal import quotes as Q
    if Q.cached(url) is None:
        Q.fetch({Q.key(url): list(quotes or [])}, log=log, workers=1, archive_workers=1)
    return Q.cached(url)


def pagecheck(url: str, quote: str) -> bool | None:
    from ..municipal import quotes as Q
    return Q.has(page(url, [quote]), quote)


def _grep(text: str, word: str, width: int = 500) -> list[str]:
    """The passages around each match of ``word`` (a regular expression, case-insensitive), overlapping passages
    merged."""
    spans: list[list[int]] = []
    for m in re.finditer(word, text, re.I):
        a, b = max(0, m.start() - width // 2), min(len(text), m.end() + width // 2)
        if spans and a <= spans[-1][1]:
            spans[-1][1] = b
        else:
            spans.append([a, b])
    return [" ".join(text[a:b].split()) for a, b in spans]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m lexflow.benefits.research", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("search")
    p.add_argument("state")
    p.add_argument("phrases", nargs="+")
    p.add_argument("--any", action="store_true", help="any phrase (default: all)")
    p.add_argument("--limit", type=int, default=20)
    p = sub.add_parser("section")
    p.add_argument("state")
    p.add_argument("ref")
    p.add_argument("--grep")
    p.add_argument("--chars", type=int, default=6000)
    p = sub.add_parser("check")
    p.add_argument("state")
    p.add_argument("ref")
    p.add_argument("quote")
    p = sub.add_parser("page")
    p.add_argument("url")
    p.add_argument("--grep")
    p.add_argument("--chars", type=int, default=4000)
    p = sub.add_parser("pagecheck")
    p.add_argument("url")
    p.add_argument("quote")
    p = sub.add_parser("units", help="a state's Census pension units (state-administered first) and lexflow's "
                                     "automatic statute search for each")
    p.add_argument("state")
    p.add_argument("--local", action="store_true", help="also list the locally administered units")
    p = sub.add_parser("checkfile", help="read the pages a fixture cites (politely, once) and match every quote")
    p.add_argument("path")
    p.add_argument("--no-fetch", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd == "units":
        import json
        from ..store import db
        from . import systems as SY
        con = db.connect()
        try:
            rows = db.rows(con, "SELECT id, name, census_name, level, membership, covers_local, members_active, "
                                "beneficiaries, admin_gov_id FROM pension_systems WHERE state=? ORDER BY level DESC, "
                                "name", a.state)
        finally:
            con.close()
        for r in rows:
            if r["level"] != "state" and not a.local:
                continue
            m = ",".join(x["type"] for x in json.loads(r["membership"] or "[]"))
            _out(f"{r['id']} | {r['level']} | {r['census_name']} | {r['name']} | {m} | "
                 f"{'open to local employers' if r['covers_local'] else ''} | active {r['members_active']}")
            if r["level"] == "state":
                s = SY.best_section(a.state, r["name"])
                _out(f"    auto search: {s['ref'] + ' | ' + s['quote'][:160] if s else 'nothing found'}")
        return 0
    if a.cmd == "checkfile":
        import json
        from pathlib import Path
        from . import ground as G
        doc = json.loads(Path(a.path).read_text(encoding="utf-8"))
        if not a.no_fetch:
            _out(json.dumps(G.fetch(doc, log=lambda m: print(m, file=sys.stderr))))
        rep = G.ground_all(doc, doc.get("state") if isinstance(doc, dict) else None)
        _out(f"{rep['matched']} of {rep['sources']} sources matched {rep['by']}")
        for u in rep["unmatched"]:
            _out(f"UNMATCHED {u['ref']}: {u['why']} | {u['quote']}")
        return 0 if not rep["unmatched"] else 1
    if a.cmd == "search":
        for r in search(a.state, a.phrases, a.any, a.limit):
            _out(f"{r['ref']} | {r['citation']} | {(r['title'] or '')[:110]} | {r['url']}")
    elif a.cmd == "section":
        rows = section(a.state, a.ref)
        if not rows:
            _out(f"no section {a.ref} in the {a.state} index")
            return 1
        for r in rows:
            _out(f"== {r['ref']} | {r['citation']} | {r['title']} | {r['url']} | effective {r.get('effective_from')}"
                 f"..{r.get('effective_until')}")
            text = r.get("text") or ""
            if a.grep:
                for g in _grep(text, a.grep):
                    _out("  ... " + g)
            else:
                _out(text[:a.chars])
    elif a.cmd == "check":
        ok = check(a.state, a.ref, a.quote)
        _out("MATCHED" if ok else "NOT MATCHED")
        return 0 if ok else 1
    elif a.cmd == "page":
        e = page(a.url, log=lambda m: print(m, file=sys.stderr))
        if not e:
            _out("not read")
            return 1
        _out(f"== {e.get('url')} via {e.get('via')} {e.get('capture') or ''} fetched {e.get('fetched')} "
             f"{'ERROR ' + e['error'] if e.get('error') else ''}")
        text = e.get("text") or ""
        if not text and not e.get("error"):
            _out("(the site's terms forbid keeping its words: only quote fingerprints are kept)")
        if a.grep:
            for g in _grep(text, a.grep):
                _out("  ... " + g)
        else:
            _out(text[:a.chars])
    elif a.cmd == "pagecheck":
        ok = pagecheck(a.url, a.quote)
        _out({True: "MATCHED", False: "NOT MATCHED", None: "PAGE NOT READ"}[ok])
        return 0 if ok else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
