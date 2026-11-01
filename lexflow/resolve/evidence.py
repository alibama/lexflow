"""What the judge reads about one case, gathered once and cached in the store (``resolve_evidence``).

* **Wikidata** for every candidate: ``wbgetentities`` (labels, descriptions, aliases, claims, sitelinks), with the
  labels of what the claims point at fetched in one more batch.  The facts kept are the ones that tell namesakes
  apart: what it is, occupation, citizenship, birth and death years, work location, residence, education,
  employer, affiliation, collections holding its work, awards, website, Instagram, where a place is.
* **English Wikipedia** summary (the REST ``page/summary``) when the candidate has an English article.
* **Web search** through SearXNG (``SEARXNG_URL``; the compose ``search`` profile): a query or two per case, the
  first five hits each (title, URL, snippet).  Off when SearXNG is not configured, and the rows say so.

Nothing here is written anywhere but the local store.  Wikidata and Wikipedia are read with lexflow's
User-Agent and at most a few requests a second.
"""
from __future__ import annotations

import json
import re
import time
from datetime import datetime, timedelta, timezone

import requests

from .. import config
from ..store import db
from .source import Case

WD_API = "https://www.wikidata.org/w/api.php"
WP_SUMMARY = "https://en.wikipedia.org/api/rest_v1/page/summary/"
TTL_DAYS = 30
PACE = {"www.wikidata.org": 1.0, "en.wikipedia.org": 0.3}   # seconds between requests to a host: one at a time, as asked
RETRIES = 5
COOLDOWN = 600                  # seconds a host is left alone after it kept answering 429 (a throttled address)
_last: dict[str, float] = {}
_cool: dict[str, float] = {}
PROPS = {"P31": "instance of", "P279": "subclass of", "P106": "occupation", "P27": "citizenship", "P569": "born",
         "P570": "died", "P19": "born in", "P937": "work location", "P551": "residence", "P69": "educated at",
         "P108": "employer", "P1416": "affiliation", "P6379": "has works in the collection", "P166": "award",
         "P856": "website", "P2003": "instagram", "P131": "located in", "P17": "country", "P571": "inception",
         "P361": "part of", "P159": "headquarters", "P740": "formed in", "P1001": "applies to", "P2079": "technique"}
ITEM_PROPS = {"P31", "P279", "P106", "P27", "P19", "P937", "P551", "P69", "P108", "P1416", "P6379", "P166", "P131",
              "P17", "P361", "P159", "P740", "P1001", "P2079"}
MAX_VALUES = 6
SEARCH_HITS = 5
_session: requests.Session | None = None


def session() -> requests.Session:
    global _session
    if _session is None:
        _session = requests.Session()
        _session.headers["User-Agent"] = config.USER_AGENT
    return _session


def _host(url: str) -> str:
    return url.split("/")[2] if "://" in url else url


def _pace(url: str) -> None:
    h = _host(url)
    wait = _last.get(h, 0.0) + PACE.get(h, 0.5) - time.monotonic()
    if wait > 0:
        time.sleep(wait)
    _last[h] = time.monotonic()


def _get(url: str, log=None, **params) -> dict:
    """One read, paced per host.  A 429 or 5xx waits what ``Retry-After`` says (at least 10, 20, 40 … seconds) and
    tries again up to RETRIES times; a host that still answers 429 is left alone for COOLDOWN seconds, so a
    throttled address does not stall every case for minutes.  Raises RuntimeError when the host will not answer."""
    h = _host(url)
    if _cool.get(h, 0.0) > time.monotonic():
        raise RuntimeError(f"{h} is being left alone for {int(_cool[h] - time.monotonic())} s after answering 429")
    last: Exception | None = None
    throttled = False
    for attempt in range(RETRIES):
        _pace(url)
        try:
            r = session().get(url, params=params or None, timeout=60)
            if r.status_code == 404:
                return {}
            if r.status_code == 429 or r.status_code >= 500:
                try:
                    wait = float(r.headers.get("Retry-After") or 0)
                except ValueError:
                    wait = 0.0
                wait = min(max(wait, 10.0 * (2 ** attempt)), 120.0)
                throttled = r.status_code == 429
                last = RuntimeError(f"{r.status_code} from {h}")
                if log:
                    log(f"  {h} answered {r.status_code}; waiting {wait:.0f} s")
                time.sleep(wait)
                continue
            r.raise_for_status()
            return r.json()
        except (requests.ConnectionError, requests.Timeout, requests.HTTPError, ValueError) as e:
            last = e
            time.sleep(2.0 * (attempt + 1))
    if throttled:
        _cool[h] = time.monotonic() + COOLDOWN
    raise RuntimeError(f"no answer from {url} ({last})")


# ------------------------------------------------------------------------------------------------ Wikidata
def _year(v: dict) -> str:
    t = str((v or {}).get("time") or "")
    m = re.match(r"^([+-]?\d{1,16})-", t)
    if not m:
        return ""
    y = int(m.group(1))
    return f"{abs(y)} BC" if y < 0 else str(y)


def _value(snak: dict) -> tuple[str, str]:
    """``(kind, value)`` of a main snak: item ids are returned as ``("item", "Q…")`` for the label pass."""
    dv = (snak or {}).get("datavalue") or {}
    t, v = dv.get("type"), dv.get("value")
    if t == "wikibase-entityid":
        return "item", (v or {}).get("id") or ""
    if t == "time":
        return "text", _year(v)
    if t == "string":
        return "text", str(v)
    if t == "monolingualtext":
        return "text", str((v or {}).get("text") or "")
    if t == "quantity":
        return "text", str((v or {}).get("amount") or "").lstrip("+")
    if t == "globecoordinate":
        return "text", f"{float(v.get('latitude')):.3f}, {float(v.get('longitude')):.3f}" if v else ""
    return "text", ""


def entity_facts(ids: list[str], log=None) -> dict[str, dict]:
    """Facts per Wikidata id: ``{label, description, aliases, facts: {name: [values]}, enwiki}``.  Two kinds of
    request: the entities (50 a call), then the labels of every item their kept claims point at (50 a call)."""
    ids = [i for i in dict.fromkeys(ids) if re.fullmatch(r"Q\d+", i or "")]
    out: dict[str, dict] = {}
    pending: dict[str, list[tuple[str, str]]] = {}        # qid -> [(prop name, referenced item)]
    for i in range(0, len(ids), 50):
        data = _get(WD_API, log, action="wbgetentities", ids="|".join(ids[i:i + 50]), format="json", languages="en",
                    props="labels|descriptions|aliases|claims|sitelinks")
        for qid, e in (data.get("entities") or {}).items():
            if "missing" in e:
                continue
            facts: dict[str, list[str]] = {}
            for pid, name in PROPS.items():
                for claim in (e.get("claims") or {}).get(pid) or []:
                    if claim.get("rank") == "deprecated":
                        continue
                    kind, val = _value(claim.get("mainsnak") or {})
                    if not val:
                        continue
                    if kind == "item":
                        pending.setdefault(qid, []).append((name, val))
                    elif val not in facts.setdefault(name, []):
                        facts[name].append(val)
            out[qid] = {"label": ((e.get("labels") or {}).get("en") or {}).get("value") or qid,
                        "description": ((e.get("descriptions") or {}).get("en") or {}).get("value") or "",
                        "aliases": [a.get("value") for a in ((e.get("aliases") or {}).get("en") or [])][:6],
                        "facts": facts, "enwiki": ((e.get("sitelinks") or {}).get("enwiki") or {}).get("title") or ""}
    refs = sorted({q for pairs in pending.values() for _n, q in pairs})
    labels: dict[str, str] = {}
    for i in range(0, len(refs), 50):
        data = _get(WD_API, log, action="wbgetentities", ids="|".join(refs[i:i + 50]), format="json", languages="en",
                    props="labels")
        for q, e in (data.get("entities") or {}).items():
            labels[q] = ((e.get("labels") or {}).get("en") or {}).get("value") or q
    for qid, pairs in pending.items():
        facts = out[qid]["facts"]
        for name, q in pairs:
            label = labels.get(q, q)
            vals = facts.setdefault(name, [])
            if label not in vals and len(vals) < MAX_VALUES:
                vals.append(label)
    if log:
        log(f"  Wikidata: {len(out)} of {len(ids)} candidate items read")
    return out


def wikipedia_summary(title: str) -> str:
    """The English article's lead, cut to a paragraph; '' without an article."""
    if not title:
        return ""
    try:
        j = _get(WP_SUMMARY + requests.utils.quote(title.replace(" ", "_"), safe=""))
    except RuntimeError:
        return ""
    text = str(j.get("extract") or "")
    return text[:700].rsplit(". ", 1)[0] + "." if len(text) > 700 else text


# ------------------------------------------------------------------------------------------------ search
def search(q: str, limit: int = SEARCH_HITS) -> list[dict]:
    """SearXNG hits for ``q``: ``[{title, url, snippet}]``; ``[]`` without SEARXNG_URL or when it does not answer."""
    if not config.SEARXNG_URL:
        return []
    from ..extract.searx import SearX
    try:
        hits = SearX(config.SEARXNG_URL).search(q)
    except Exception:  # noqa: BLE001 - search is a help, never a stop
        return []
    out = []
    for hit in hits:
        if not hit.get("url"):
            continue
        out.append({"title": (hit.get("title") or "")[:160], "url": hit["url"][:300], "snippet": (hit.get("snippet") or "")[:400]})
        if len(out) >= limit:
            break
    return out


def queries_for(case: Case) -> list[str]:
    """What to search for one case: the name with the field, and the name with its place."""
    name = case.label.strip()
    if not name:
        return []
    if case.kind == "person":
        qs = [f'"{name}" glass']
        where = (case.facts.get("work location") or case.facts.get("located in") or [])[:1]
        if where:
            qs.append(f'"{name}" {where[0]} glass artist')
        return qs
    if case.kind in ("studio", "school", "museum", "funder", "show", "award"):
        where = (case.facts.get("located in") or case.facts.get("country") or [])[:1]
        return [f'"{name}" {where[0] if where else "glass"}']
    if case.kind == "place":
        tail = [p.strip() for p in case.description.split(",") if p.strip() and p.strip().lower() != "place"]
        return [f'"{name}" {" ".join(tail[:2])}'] if tail else []
    return [f'"{name}" glass']


# ------------------------------------------------------------------------------------------------ the cache
def _cached(con, kind: str, ident: str, fresh_days: int = TTL_DAYS):
    r = db.one(con, "SELECT json, fetched_at FROM resolve_evidence WHERE kind=? AND ident=?", kind, ident)
    if not r:
        return None
    try:
        when = datetime.fromisoformat(r["fetched_at"])
    except (TypeError, ValueError):
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) - when > timedelta(days=fresh_days):
        return None
    return db.loads(r["json"])


def _remember(con, kind: str, ident: str, value) -> None:
    con.execute("INSERT INTO resolve_evidence (kind, ident, json, fetched_at) VALUES (?,?,?,?) "
                "ON CONFLICT(kind, ident) DO UPDATE SET json=excluded.json, fetched_at=excluded.fetched_at",
                (kind, ident, json.dumps(value, ensure_ascii=False), db.now()))


def hits(con, q: str, fresh_days: int = TTL_DAYS) -> list[dict]:
    """Search hits for one query, from the cache when younger than ``fresh_days``."""
    found = _cached(con, "q", q, fresh_days)
    if found is None:
        found = search(q)
        _remember(con, "q", q, found)
        con.commit()
    return found


def gather(con, case: Case, *, use_search: bool = True, fresh_days: int = TTL_DAYS, log=None) -> dict:
    """Everything the judge is shown for ``case``: ``{"candidates": {qid: facts + wikipedia}, "search": {query:
    hits}, "searched": bool, "partial": bool}``.  Each piece comes from the cache when it is younger than
    ``fresh_days``.  When Wikidata will not answer (a throttled address), the candidates keep the label, description
    and classes the lookup itself saw, the row is marked partial, and nothing of that is cached, so the next run
    reads the facts."""
    cands: dict[str, dict] = {}
    missing = []
    partial = False
    for qid in case.candidate_ids():
        hit = _cached(con, "wd", qid, fresh_days)
        if hit is None:
            missing.append(qid)
        else:
            cands[qid] = hit
    if missing:
        try:
            read = entity_facts(missing, log)
        except RuntimeError as e:
            read = {}
            partial = True
            if log:
                log(f"  {case.label}: Wikidata facts not read ({e}); judging from the lookup's own candidate descriptions")
        for qid, facts in read.items():
            facts["wikipedia"] = wikipedia_summary(facts.get("enwiki") or "")
            _remember(con, "wd", qid, facts)
            cands[qid] = facts
        for qid in missing:
            if qid in cands:
                continue
            if partial:                          # what the lookup saw: label, description, classes; not cached
                c = next((x for x in case.candidates if x.get("qid") == qid), {})
                cands[qid] = {"label": c.get("label") or qid, "description": c.get("description") or "",
                              "facts": {"instance of": list(c.get("types") or [])}, "wikipedia": ""}
            else:                                # an id Wikidata no longer has: remember that too
                cands[qid] = {"label": qid, "description": "(no such item on Wikidata)", "facts": {}, "wikipedia": ""}
                _remember(con, "wd", qid, cands[qid])
    searched: dict[str, list[dict]] = {}
    if use_search and config.SEARXNG_URL:
        for q in queries_for(case):
            hits = _cached(con, "q", q, fresh_days)
            if hits is None:
                hits = search(q)
                _remember(con, "q", q, hits)
            searched[q] = hits
    con.commit()
    return {"candidates": cands, "search": searched, "searched": bool(use_search and config.SEARXNG_URL), "partial": partial}
