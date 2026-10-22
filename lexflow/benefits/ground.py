"""lexflow's match of a benefits fixture's quotes: a statute quote against the statute index, a page quote against
the page as lexflow's quote fetch read it.

A source in a fixture under ``fixtures/benefits/`` is one of::

    {"kind": "statute", "state": "va", "ref": "51.1-153", "quote": "<verbatim words of the section>"}
    {"kind": "page", "url": "https://www.varetire.org/...", "quote": "<verbatim words of the page>"}

``state`` defaults to the fixture's state.  ``ref`` is the index's reference: the bare section number where the
state's index has one code (Virginia, D.C.), else the full citation as the index prints it ("Md. Code, State
Personnel and Pensions § 21-102", "Cal. GOV § 100032", "ORS 178.200").  ``ground(src)`` returns a copy with the
row's ``citation`` and ``url`` (for a statute) and ``grounding``: ``{matched, by, where, on, why}`` where ``by`` is
``code`` (the quote is word for word in the indexed section: ``validate.quote_in``), ``live`` or ``archive`` (word
for word on the cited page as lexflow's quote fetch read it live or from an Internet Archive capture).  Nothing is
fetched here: ``fetch(sources)`` reads the pages not yet cached, politely (``municipal.quotes.fetch``).  A fact
whose sources all fail to match is not shown as grounded anywhere.
"""
from __future__ import annotations

import re
from typing import Iterable

KINDS = ("statute", "page")


def _today() -> str:
    from ..store import db
    return db.now()[:10]


def statute_rows(state: str, ref: str) -> list[dict]:
    from ..ask import index as I
    try:
        if not I.ready(state):
            return []
        return I.lookup(state, ref, with_text=True)
    except Exception:  # noqa: BLE001 - no index on this copy
        return []


def ground(src: dict, state: str | None = None, today: str | None = None) -> dict:
    """One source, matched (see the module docstring)."""
    from .. import validate
    out = {k: v for k, v in (src or {}).items() if k != "grounding"}
    quote = (out.get("quote") or "").strip()
    day = today or _today()
    kind = out.get("kind")
    if kind not in KINDS:
        out["grounding"] = {"matched": False, "why": f"kind must be one of {KINDS}"}
        return out
    if len(quote.split()) < 3:
        out["grounding"] = {"matched": False, "why": "no quote, or too short to check"}
        return out
    if kind == "statute":
        st = (out.get("state") or state or "").lower()
        ref = out.get("ref") or ""
        rows = statute_rows(st, ref)
        if not rows:
            out["grounding"] = {"matched": False, "why": f"{ref!r} is not in this copy's {st} statute index"}
            return out
        hit = next((r for r in rows if validate.quote_in(quote, r.get("text") or "")), None)
        r = hit or rows[0]
        out.setdefault("citation", r.get("citation"))
        out.setdefault("url", r.get("url"))
        out["state"] = st
        out["grounding"] = ({"matched": True, "by": "code", "where": r.get("ref"), "on": day} if hit else
                            {"matched": False, "why": f"not word for word in Open US Law's copy of {r.get('citation')}"})
        return out
    from ..municipal import quotes as Q
    url = out.get("url") or ""
    e = Q.cached(url) if url else None
    if not e:
        out["grounding"] = {"matched": False, "why": "the page has not been read by lexflow's quote fetch yet"}
        return out
    if e.get("error"):
        out["grounding"] = {"matched": False, "why": f"the page could not be read: {e['error']}"}
        return out
    ok = Q.has(e, quote)
    if ok:
        out["grounding"] = {"matched": True, "by": "archive" if e.get("via") == "archive" else "live",
                            "where": e.get("url"), "on": e.get("fetched") or day,
                            **({"capture": e["capture"]} if e.get("capture") else {})}
    else:
        out["grounding"] = {"matched": False, "why": "not word for word on the page as lexflow read it"
                            if ok is False else "the page's words are not kept and this quote was not checked"}
    return out


def matched(src: dict | None) -> bool:
    return bool(((src or {}).get("grounding") or {}).get("matched"))


def sources_in(doc) -> Iterable[dict]:
    """Every source dict in a fixture (any dict with ``kind`` statute/page and a ``quote``)."""
    if isinstance(doc, dict):
        if doc.get("kind") in KINDS and "quote" in doc:
            yield doc
            return
        for v in doc.values():
            yield from sources_in(v)
    elif isinstance(doc, list):
        for v in doc:
            yield from sources_in(v)


def ground_all(doc, state: str | None = None) -> dict:
    """Ground every source of a fixture in place; returns ``{sources, matched, by, unmatched: [...]}``."""
    rep = {"sources": 0, "matched": 0, "by": {}, "unmatched": []}
    day = _today()

    def walk(d, st):
        if isinstance(d, dict):
            st = d.get("state") if isinstance(d.get("state"), str) and re.fullmatch(r"[a-z]{2}", d["state"]) else st
            for k, v in list(d.items()):
                if isinstance(v, dict) and v.get("kind") in KINDS and "quote" in v:
                    d[k] = ground(v, st, day)
                    count(d[k])
                elif isinstance(v, list):
                    for i, x in enumerate(v):
                        if isinstance(x, dict) and x.get("kind") in KINDS and "quote" in x:
                            v[i] = ground(x, st, day)
                            count(v[i])
                        else:
                            walk(x, st)
                else:
                    walk(v, st)
        elif isinstance(d, list):
            for x in d:
                walk(x, st)

    def count(s):
        rep["sources"] += 1
        g = s["grounding"]
        if g.get("matched"):
            rep["matched"] += 1
            rep["by"][g["by"]] = rep["by"].get(g["by"], 0) + 1
        else:
            rep["unmatched"].append({"ref": s.get("ref") or s.get("url"), "why": g.get("why"),
                                     "quote": (s.get("quote") or "")[:90]})
    walk(doc, state)
    return rep


def pages_wanted(doc) -> dict[str, list[str]]:
    """url -> the quotes a fixture cites it for (the page sources only)."""
    out: dict[str, list[str]] = {}
    for s in sources_in(doc):
        if s.get("kind") == "page" and s.get("url"):
            out.setdefault(s["url"], []).append(s["quote"])
    return out


def fetch(doc, log=print) -> dict:
    """Read the pages a fixture cites that lexflow's quote fetch has not read yet (politely; see
    ``municipal.quotes``)."""
    from ..municipal import quotes as Q
    want = {Q.key(u): q for u, q in pages_wanted(doc).items()}
    todo = {u: q for u, q in want.items() if Q.cached(u) is None}
    if not todo:
        return {"pages": len(want), "fetched": 0}
    counts = Q.fetch(todo, log=log, workers=2, archive_workers=1)
    return {"pages": len(want), **counts}
