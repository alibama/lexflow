"""The local layer of an answer: what a city or county adds to its state's law, and whom to contact.

LOCUS-v1 (LocalLaws' Local Ordinance Corpus for the United States) is read once per state and cached on disk, so a
batch over every place in a state reads it once.  Its headings are matched against the question's concepts.
LOCUS is CC BY-NC and machine-labelled: it is used to point at local provisions, never quoted as law.
"""
from __future__ import annotations

import re

from .. import config
from ..municipal import locus_scan
from ..store import db
from .plan import Plan


def cache_path(state: str):
    return config.RAW_DIR / "locus" / f"{state}.parquet"


def locus_rows(state: str, log=print) -> list[dict]:
    """Every LOCUS heading for a state (city, county, header, function, topic), cached as parquet."""
    import pyarrow as pa
    import pyarrow.parquet as pq
    p = cache_path(state)
    if p.exists():
        return pq.read_table(p).to_pylist()
    rows = locus_scan.read_state(state, log)
    p.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.Table.from_pylist(rows or [{c: None for c in locus_scan.COLUMNS}]), p)
    return rows


def by_place(rows: list[dict]) -> dict[str, list[dict]]:
    """LOCUS rows grouped by their place key, so a batch over every place in a state reads each row once."""
    out: dict[str, list[dict]] = {}
    for r in rows:
        key = r.get("city") or r.get("county")
        if key:
            out.setdefault(key, []).append(r)
    return out


def local_hits(con, state: str, gov_id: str, plan: Plan, limit: int = 8, rows: list[dict] | None = None,
               grouped: dict[str, list[dict]] | None = None, keys: dict[str, str] | None = None) -> list[dict]:
    """LOCUS headings of one government that mention the question's concepts, best first.  ``grouped`` (from
    by_place) and ``keys`` (from locus_scan.gov_keys) can be passed in once for a whole batch."""
    keys = keys if keys is not None else locus_scan.gov_keys(con, state)
    places = {k for k, g in keys.items() if g == gov_id}
    if not places:
        return []
    pats = [re.compile(r"\b(?:" + "|".join(re.escape(t) for t in g if len(t) > 2) + r")", re.I) for g in plan.groups]
    pats = [p for p in pats if p.pattern != r"\b(?:)"]
    if grouped is None:
        grouped = by_place(rows if rows is not None else locus_rows(state))
    out = []
    for r in (r for place in places for r in grouped.get(place, [])):
        header = (r.get("header") or "").lstrip("# ").strip()
        hits = sum(1 for p in pats if p.search(header))
        if hits:
            out.append({"header": header[:300], "function": r.get("function"), "topic": r.get("topic"),
                        "score": hits + (0.5 if r.get("function") == "Process" else 0.0)})
    out.sort(key=lambda x: -x["score"])
    seen, uniq = set(), []
    for o in out:
        if o["header"].lower() not in seen:
            seen.add(o["header"].lower())
            uniq.append(o)
    return uniq[:limit]


def web_pages(g: dict, plan: Plan, limit: int = 5, log=print) -> list[dict]:
    """Official pages about the question on the place's own website, via SearXNG (only when SEARXNG_URL is set):
    procedures, forms and fee schedules often live there rather than in any code."""
    from urllib.parse import urlparse
    if not config.SEARXNG_URL or not g.get("website"):
        return []
    from ..extract.searx import SearX
    site = g["website"] if "//" in g["website"] else f"http://{g['website']}"
    host = (urlparse(site).hostname or "").removeprefix("www.")
    if not host:
        return []
    words = " ".join(grp[0] for grp in plan.groups[:4])
    try:
        hits = SearX(config.SEARXNG_URL).search(f"{words} site:{host}")
    except Exception as e:  # noqa: BLE001 - search is optional
        log(f"{g['name']}: web search failed ({type(e).__name__})")
        return []
    return [{"title": h["title"][:200], "url": h["url"], "snippet": h["snippet"][:300]}
            for h in hits if _on_site(h["url"], host)][:limit]


def _on_site(url: str, host: str) -> bool:
    """True for a page on the host or one of its subdomains ('charlottesville.gov-payments.com' is neither)."""
    from urllib.parse import urlparse
    try:
        h = (urlparse(url).hostname or "").removeprefix("www.")
    except ValueError:
        return False
    return h == host or h.endswith("." + host)


def court_decisions(state: str, refs: list[str], limit: int = 8, log=print) -> list[dict]:
    """Opinions that cite the answer's sections (CourtListener, only with COURTLISTENER_TOKEN: anonymous searches
    are rate limited to a crawl)."""
    if not config.COURTLISTENER_TOKEN:
        return []
    from ..municipal import caselaw
    out = []
    for ref in refs[:2]:
        try:
            for x in caselaw.search(state, ref, pages=1, log=log):
                out.append({"section": ref, "case_name": (x.get("caseName") or "")[:200], "court": x.get("court"),
                            "date_filed": x.get("dateFiled"), "cite_count": x.get("citeCount") or 0,
                            "url": "https://www.courtlistener.com" + (x.get("absolute_url") or "")})
        except caselaw.RateLimited as e:
            log(str(e))
            break
    return sorted(out, key=lambda c: -(c["cite_count"] or 0))[:limit]


def contacts(con, gov_id: str) -> list[dict]:
    """The government's best contacts (website, email, phone, records or licence pages)."""
    g = db.one(con, "SELECT website FROM governments WHERE gov_id=?", gov_id) or {}
    out = [{"kind": "website", "value": g["website"]}] if g.get("website") else []
    for c in db.rows(con, "SELECT DISTINCT kind, value, label FROM contacts WHERE gov_id=? ORDER BY kind", gov_id):
        if c["value"] and c["value"] not in {o["value"] for o in out}:
            out.append({"kind": c["kind"], "value": c["value"], "label": c.get("label")})
    return out[:8]
