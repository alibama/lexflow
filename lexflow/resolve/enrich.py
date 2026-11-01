"""More about a record with nothing on Wikidata: its website, Instagram account and city, from a web search.

For the records the Glass Database's lookup left with no Wikidata item (``none``, and ``rejected`` by a person)
that lack a website, an Instagram account or a place: a query or two through SearXNG; the hits sifted first
without a model (candidate sites that are not social networks, marketplaces or encyclopaedias, ranked by the name
in the host; Instagram handles that appear in the hits); a local model asked to pick among those candidates and
to read the town from the snippets; and every proposal checked against the evidence before it is kept.  A
website must be a site the hits showed, a handle must appear in the hits, a town must appear in a title or
snippet.  What passes goes to the Glass Database as a proposal (``POST /api/wikibase/items/{key}`` with
``{"enrich": …}``) that its review page shows with an *Add* button; nothing enters a record without a person.

``check`` measures it.  Records that already carry the fields are run with those fields hidden, and each
proposal is compared with what the record says: a website by host, a handle exactly, a town by name.  The
number to read is precision when proposed, per field and per model.

Without a model (``no_llm``) only the deterministic part runs: the one site whose host carries the record's
name, the one handle that does; no town.
"""
from __future__ import annotations

import hashlib
import re
import time
import unicodedata
from pathlib import Path
from urllib.parse import urlparse

from .. import config
from ..store import db
from . import evidence as E
from . import judge as J
from .source import Case, GlassDatabase

FIELDS = ("website", "instagram", "city")
KINDS = ("person", "studio", "school", "museum")
# sites that are never a record's own website
SOCIAL = ("instagram.com", "facebook.com", "twitter.com", "x.com", "tiktok.com", "youtube.com", "youtu.be", "pinterest.",
          "linkedin.com", "etsy.com", "ebay.", "amazon.", "wikipedia.org", "wikidata.org", "wikimedia.org",
          "glassdatabase.org", "yelp.com", "tripadvisor.", "threads.net", "vimeo.com", "flickr.com", "tumblr.com",
          "patreon.com", "linktr.ee", "saatchiart.com", "artsy.net", "artnet.com", "mutualart.com", "askart.com",
          "invaluable.com", "liveauctioneers.com", "1stdibs.com", "chairish.com", "google.", "bing.com", "duckduckgo.com",
          "reddit.com", "imdb.com", "findagrave.com", "ancestry.", "whitepages", "spokeo", "zillow", "yellowpages",
          "bbb.org", "manta.com", "dnb.com", "crunchbase", "opencorporates", "glassart.org", "cmog.org",
          "museumofglass.org", "pilchuck.org", "archive.org", "scribd.com", "issuu.com", "eventbrite.", "meetup.com")
# hosts where the first path segment is the site (a page on a shared platform)
PLATFORMS = ("wixsite.com", "squarespace.com", "weebly.com", "wordpress.com", "blogspot.com", "carrd.co", "github.io",
             "webs.com", "godaddysites.com", "format.com", "cargo.site", "myportfolio.com", "bigcartel.com", "shopify.com")
STOP = {"glass", "studio", "studios", "art", "arts", "the", "of", "and", "llc", "inc", "co", "glassworks", "hot", "shop",
        "school", "museum", "gallery", "works", "design", "designs", "for", "at", "in"}
RESERVED_HANDLES = {"p", "explore", "reel", "reels", "stories", "accounts", "tv", "s", "about", "legal", "directory",
                    "tags", "locations", "web", "share", "developer", "press", "api", "privacy", "terms"}
MAX_HITS = 24
METRIC_VERSION = 1
CODE = ("resolve/enrich.py", "resolve/evidence.py")

SYSTEM = (
    "You read web search results about one record from the Glass Database (a register of glass artists, studios, "
    "schools and museums) and report what the results show about it: its own website, its Instagram account and "
    "the town or city it works in. Use only the results shown. The website must be one of the candidate sites and "
    "must be the record's own site, not a shop, a gallery, a museum or a directory page about it. The Instagram "
    "account must be one of the candidate handles. The town must be named in a result about this record. When a "
    "result is about a different person or place of the same name, leave that field empty. Confidence is how sure "
    "the results make you, from 0 to 1, per field."
)
SHAPE = ('Answer with one JSON object and nothing else, shaped like this: {"website": "<one candidate site, or an '
         'empty string>", "instagram": "<one candidate handle without the @, or an empty string>", "city": "<the town '
         'or city, or an empty string>", "region": "<its state, province or region, or empty>", "country": "<its '
         'country, or empty>", "confidence": {"website": <0 to 1>, "instagram": <0 to 1>, "city": <0 to 1>}, '
         '"because": "<one or two sentences naming the results that decided it>"}')


def version() -> str:
    root = Path(__file__).resolve().parents[1]
    h = hashlib.sha256()
    for p in sorted({p for pat in CODE for p in root.glob(pat)}):
        h.update(p.name.encode() + b"\0" + p.read_bytes())
    return f"{METRIC_VERSION}-{h.hexdigest()[:12]}"


# ------------------------------------------------------------------------------------------------ the hits, sifted
def host(u: str) -> str:
    try:
        return (urlparse(u).netloc or "").lower().split("@")[-1].split(":")[0].removeprefix("www.")
    except ValueError:
        return ""


def site_of(u: str) -> str:
    """The site a page belongs to: the host's root, or the first path segment on a shared platform."""
    p = urlparse(u)
    h = host(u)
    if any(h == x or h.endswith("." + x) for x in PLATFORMS):
        seg = (p.path or "/").split("/")[1] if (p.path or "/").count("/") >= 1 else ""
        return f"{p.scheme}://{p.netloc}/{seg}/" if seg else f"{p.scheme}://{p.netloc}/"
    return f"{p.scheme}://{p.netloc}/"


def _norm(s: str) -> str:
    """Lower-case ASCII words: accents, case and punctuation dropped."""
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return " ".join(re.findall(r"[a-z0-9]+", s))


def name_tokens(label: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", _norm(label)) if t not in STOP and len(t) > 1]


def website_candidates(case: Case, hits: list[dict]) -> list[dict]:
    """Distinct sites from the hits that could be the record's own, best first."""
    toks = name_tokens(case.label)
    joined = "".join(toks)
    out: dict[str, dict] = {}
    for i, hit in enumerate(hits):
        u = hit.get("url") or ""
        h = host(u)
        if not h or any(h == s or h.endswith("." + s) or s in h for s in SOCIAL):
            continue
        site = site_of(u)
        hay = (h + " " + (hit.get("title") or "")).lower()
        hay_norm = _norm(h.replace(".", " ") + " " + (hit.get("title") or ""))
        score = 0.0
        if joined and joined in h.replace("-", "").replace(".", ""):
            score += 4
        score += sum(1.5 for t in toks if len(t) > 3 and t in h)
        if toks and all(t in hay_norm.split() for t in toks):
            score += 1.5
        if "glass" in hay:
            score += 1
        score -= i * 0.05
        if site not in out or out[site]["score"] < score:
            out[site] = {"url": site, "host": h, "title": (hit.get("title") or "")[:160], "snippet": (hit.get("snippet") or "")[:240],
                         "score": round(score, 2), "from": u}
    return sorted(out.values(), key=lambda c: -c["score"])[:5]


_IG_URL = re.compile(r"instagram\.com/([A-Za-z0-9_.]{2,30})")
_IG_AT = re.compile(r"(?<![\w.])@([A-Za-z0-9_.]{3,30})")


def instagram_candidates(case: Case, hits: list[dict]) -> list[dict]:
    """Instagram handles that appear in the hits (URLs first, then @mentions in the text), best first."""
    toks = name_tokens(case.label)
    found: dict[str, dict] = {}
    for hit in hits:
        u, text = hit.get("url") or "", f"{hit.get('title') or ''} {hit.get('snippet') or ''}"
        for m in _IG_URL.finditer(u):
            handle = m.group(1).rstrip(".")
            if handle.lower() in RESERVED_HANDLES:
                continue
            d = found.setdefault(handle.lower(), {"handle": handle, "score": 0.0, "evidence": [], "where": "url"})
            d["score"] += 2
            if u not in d["evidence"]:
                d["evidence"].append(u)
        for m in _IG_URL.finditer(text):
            handle = m.group(1).rstrip(".")
            if handle.lower() in RESERVED_HANDLES:
                continue
            d = found.setdefault(handle.lower(), {"handle": handle, "score": 0.0, "evidence": [], "where": "text"})
            d["score"] += 1
            if u and u not in d["evidence"]:
                d["evidence"].append(u)
        if "instagram" in text.lower() or "instagram.com" in u:
            for m in _IG_AT.finditer(text):
                handle = m.group(1).rstrip(".")
                if handle.lower() in RESERVED_HANDLES or "." == handle[-1:]:
                    continue
                d = found.setdefault(handle.lower(), {"handle": handle, "score": 0.0, "evidence": [], "where": "mention"})
                d["score"] += 0.5
                if u and u not in d["evidence"]:
                    d["evidence"].append(u)
    for d in found.values():
        flat = d["handle"].lower().replace(".", "").replace("_", "")
        d["score"] += sum(1.5 for t in toks if len(t) > 2 and t in flat)
        if "glass" in flat:
            d["score"] += 0.5
        d["score"] = round(d["score"], 2)
    return sorted(found.values(), key=lambda c: -c["score"])[:5]


def queries_for(case: Case, hidden: set[str] = frozenset()) -> list[str]:
    name = case.label.strip()
    if not name:
        return []
    place = "" if "city" in hidden else ((case.facts.get("work location") or case.facts.get("located in") or [""])[0])
    if case.kind == "person":
        qs = [f'"{name}" glass artist', f'"{name}" glass instagram']
        if place:
            qs.insert(1, f'"{name}" {place} glass')
        return qs
    qs = [f'"{name}" glass']
    if place:
        qs.append(f'"{name}" {place}')
    return qs


# ------------------------------------------------------------------------------------------------ the model
def prompt(case: Case, hits: list[dict], webs: list[dict], igs: list[dict], hidden: set[str] = frozenset()) -> list[dict]:
    facts = {k: v for k, v in case.facts.items() if not (
        (k == "official website" and "website" in hidden) or (k == "Instagram username" and "instagram" in hidden)
        or (k in ("work location", "located in") and "city" in hidden))}
    shown = Case(case.key, case.kind, case.label, case.description if "city" not in hidden else "", case.aliases, facts)
    parts = [J.record_text(shown), "", "CANDIDATE SITES (the website, if any, is one of these)"]
    parts += [f"  - {w['url']}  title: {w['title']}" + (f"  snippet: {w['snippet']}" if w.get("snippet") else "") for w in webs] or ["  (none)"]
    parts += ["", "CANDIDATE INSTAGRAM HANDLES (the account, if any, is one of these)"]
    parts += [f"  - {g['handle']}  seen at: {', '.join(g['evidence'][:2])}" for g in igs] or ["  (none)"]
    parts += ["", "SEARCH RESULTS"]
    budget = J.MAX_CHARS - sum(len(p) for p in parts)
    for hit in hits:
        line = f"  - {hit.get('title') or ''} <{hit.get('url') or ''}>: {hit.get('snippet') or ''}"
        if len(line) > budget:
            break
        parts.append(line)
        budget -= len(line) + 1
    parts += ["", "QUESTION: What do these results show about the record's own website, its Instagram account and the "
                  "town or city it works in? " + SHAPE]
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": "\n".join(parts)}]


def parse(text: str) -> dict:
    obj = J._first_object(text or "") or {}
    conf = obj.get("confidence") if isinstance(obj.get("confidence"), dict) else {}

    def c(f):
        try:
            v = float((conf or {}).get(f, obj.get(f"{f}_confidence", 0)) or 0)
        except (TypeError, ValueError):
            v = 0.0
        return max(0.0, min(1.0, v / 100 if v > 1 else v))
    return {"website": str(obj.get("website") or "").strip(), "instagram": str(obj.get("instagram") or "").strip().lstrip("@"),
            "city": str(obj.get("city") or "").strip(), "region": str(obj.get("region") or "").strip(),
            "country": str(obj.get("country") or "").strip(), "confidence": {f: c(f) for f in FIELDS},
            "because": str(obj.get("because") or "").strip()[:400], "ok": bool(obj)}


def _in_text(word: str, hits: list[dict]) -> list[str]:
    """The hit URLs whose title or snippet carry ``word`` as a whole word, case apart."""
    if not word:
        return []
    pat = re.compile(r"(?<![A-Za-z])" + re.escape(word) + r"(?![A-Za-z])", re.I)
    return [h["url"] for h in hits if h.get("url") and pat.search(f"{h.get('title') or ''} {h.get('snippet') or ''}")]


def verify(case: Case, answer: dict, hits: list[dict], webs: list[dict], igs: list[dict]) -> dict:
    """Keep only what the evidence shows; each kept field carries the pages it rests on."""
    out: dict = {}
    w = answer.get("website") or ""
    if w:
        wh = host(w)
        match = next((c for c in webs if c["host"] == wh or host(c["url"]) == wh), None)
        if match:
            ev = [h["url"] for h in hits if host(h.get("url") or "") == match["host"]][:3]
            out["website"] = {"value": match["url"], "confidence": answer["confidence"]["website"], "because": answer["because"],
                              "evidence": ev or [match["from"]]}
    g = (answer.get("instagram") or "").lower().rstrip("/").rsplit("/", 1)[-1]
    if g:
        match = next((c for c in igs if c["handle"].lower() == g), None)
        if match:
            out["instagram"] = {"value": match["handle"], "confidence": answer["confidence"]["instagram"],
                                "because": answer["because"], "evidence": match["evidence"][:3]}
    city = answer.get("city") or ""
    if city and len(city) <= 60 and _norm(city) not in ("", "unknown", "none", "n a"):
        ev = _in_text(city, hits)
        if ev:
            entry = {"value": city, "confidence": answer["confidence"]["city"], "because": answer["because"], "evidence": ev[:3]}
            for k in ("region", "country"):
                v = answer.get(k) or ""
                if v and _in_text(v, hits):
                    entry[k] = v
            out["city"] = entry
    return out


def deterministic(case: Case, webs: list[dict], igs: list[dict]) -> dict:
    """Without a model: the one site whose host carries the name and whose page says glass (a namesake's campaign
    site carries the name too), the one handle that carries the name."""
    answer = {"website": "", "instagram": "", "city": "", "region": "", "country": "",
              "confidence": {"website": 0.7, "instagram": 0.7, "city": 0.0}, "because": "the name is in the address and the page says glass", "ok": True}
    strong = [w for w in webs if w["score"] >= 4 and "glass" in f"{w['host']} {w['title']} {w.get('snippet') or ''}".lower()]
    if len(strong) == 1:
        answer["website"] = strong[0]["url"]
    toks = name_tokens(case.label)
    named = [g for g in igs if any(len(t) > 2 and t in g["handle"].lower().replace(".", "").replace("_", "") for t in toks)]
    if len(named) == 1:
        answer["instagram"] = named[0]["handle"]
    return answer


def propose(client, case: Case, hits: list[dict], hidden: set[str] = frozenset()) -> tuple[dict, dict]:
    """``(fields, meta)``: the verified proposal and what the model said and how long it took."""
    webs, igs = website_candidates(case, hits), instagram_candidates(case, hits)
    t0 = time.time()
    if client is None or not hits:                 # nothing to ask about, or nobody to ask: the sifting alone
        answer = deterministic(case, webs, igs)
        meta = {"model": client.model if client is not None else "", "seconds": 0.0, "node": "", "no_hits": not hits}
    else:
        since = len(client.log)
        text = client.chat(prompt(case, hits, webs, igs, hidden), schema="json", temperature=0.0, max_tokens=J.MAX_TOKENS)
        answer = parse(text)
        used = client.nodes_used(since)
        meta = {"model": client.model, "seconds": round(time.time() - t0, 1), "node": ",".join(sorted(used)), "raw": answer}
    fields = verify(case, answer, hits, webs, igs)
    meta["candidates"] = {"websites": [w["url"] for w in webs], "instagram": [g["handle"] for g in igs]}
    return fields, meta


# ------------------------------------------------------------------------------------------------ the run
def _client(model: str, node: str | None):
    from .bench import client_for
    return client_for(model, node)


def _has(case: Case) -> dict[str, list[str]]:
    return {"website": case.facts.get("official website") or [], "instagram": case.facts.get("Instagram username") or [],
            "city": (case.facts.get("work location") or []) + (case.facts.get("located in") or [])}


def _matches(field: str, proposed: str, actual: list[str]) -> bool:
    if field == "website":
        return host(proposed) in {host(a) for a in actual}
    if field == "instagram":
        return proposed.lower() in {a.lower().lstrip("@") for a in actual}
    return any(_norm(proposed) == _norm(a) or _norm(proposed) in _norm(a).split() for a in actual)


def run(con, models: list[str], *, fields=FIELDS, kinds=KINDS, limit: int | None = None, node: str | None = None,
        check: bool = False, no_llm: bool = False, search: bool = True, log=print, progress=None,
        src: GlassDatabase | None = None) -> dict:
    """Live: records with nothing on Wikidata that lack a field get a proposal, written back when a token is set.
    ``check``: records that have the fields, run with them hidden, the proposals scored against them."""
    fields = tuple(f for f in (fields or FIELDS) if f in FIELDS) or FIELDS
    kinds = tuple(k for k in (kinds or KINDS) if k in KINDS) or KINDS
    src = src or GlassDatabase(log=log)
    ver = version()
    if not (search and config.SEARXNG_URL):
        log("no SEARXNG_URL: the enrich step is a web search, so there is nothing to do without one (docker compose "
            "--profile search up -d, then SEARXNG_URL=http://searxng:8080)")
        return {"cases": 0, "proposed": {}, "suggested": 0, "version": ver, "searched": False, "error": "no SEARXNG_URL"}
    from .bench import cached_cases, remember_cases
    statuses = ("none", "rejected", "matched", "confirmed", "unsure", "known") if check else ("none", "rejected")
    cases = src.cases(statuses, kinds=list(kinds), known=cached_cases(con))
    remember_cases(con, cases)
    if check:
        cases = [c for c in cases if any(_has(c)[f] for f in fields)]
    else:
        cases = [c for c in cases if any(not _has(c)[f] for f in fields)]
    if limit:
        cases = cases[:int(limit)]
    model = "" if no_llm else (models[0] if models else config.RESOLVE_MODELS[0])
    log(f"{'check: ' if check else ''}{len(cases)} record(s) of kind {', '.join(kinds)} "
        + ("that have " if check else "that lack ") + ", ".join(fields) + f"; model {model or 'none (deterministic only)'}"
        + ("" if src.can_write() or check else "; no GLASSDB_ADMIN_TOKEN, so nothing is written back"))
    if not cases:
        return {"cases": 0, "proposed": {}, "suggested": 0, "version": ver, "searched": True}
    client = None if no_llm else _client(model, node)
    counts: dict = {"cases": len(cases), "proposed": {f: 0 for f in fields}, "suggested": 0, "version": ver, "searched": True,
                    "check": {f: {"had": 0, "proposed": 0, "right": 0} for f in fields} if check else None}
    for i, case in enumerate(cases):
        has = _has(case)
        hidden = {f for f in fields if has[f]} if check else set()
        hits: list[dict] = []
        for q in queries_for(case, hidden):
            for hit in E.hits(con, q):
                if hit.get("url") and hit["url"] not in {h["url"] for h in hits}:
                    hits.append(hit)
            if len(hits) >= MAX_HITS:
                break
        try:
            proposal, meta = propose(client, case, hits[:MAX_HITS], hidden)
        except Exception as e:  # noqa: BLE001 - a failed call is a record with no proposal
            proposal, meta = {}, {"model": model, "error": f"{type(e).__name__}: {e}", "seconds": 0.0, "node": ""}
            log(f"  {case.label}: {meta['error']}")
        want = {f: proposal[f] for f in fields if f in proposal and (check or not has[f])}
        row = {"key": case.key, "kind": case.kind, "label": case.label, "fields": want, "hits": hits[:MAX_HITS],
               "model": meta.get("model") or "", "searched": 1, "version": ver, "check_json": None, "updated_at": db.now()}
        for f in want:
            counts["proposed"][f] += 1
        if check:
            res = {}
            for f in fields:
                if has[f]:
                    counts["check"][f]["had"] += 1
                    if f in want:
                        ok = _matches(f, want[f]["value"], has[f])
                        counts["check"][f]["proposed"] += 1
                        counts["check"][f]["right"] += int(ok)
                        res[f] = {"proposed": want[f]["value"], "actual": has[f][:3], "match": ok}
                    else:
                        res[f] = {"proposed": "", "actual": has[f][:3], "match": None}
            row["check_json"] = res
        elif want and src.can_write():
            try:
                src.enrich(case.key, {"fields": want, "model": row["model"], "searched": True, "version": ver})
                row["suggested_at"] = db.now()
                counts["suggested"] += 1
            except Exception as e:  # noqa: BLE001
                log(f"  {case.key}: proposal not written ({e})")
        db.upsert(con, "resolve_enrich", [row], keys=("key",), stamp=False)
        con.commit()
        said = ", ".join(f"{f}={v['value']}@{v['confidence']:.2f}" for f, v in want.items()) or "nothing"
        marks = ("  " + " ".join(f"{f}:{'✓' if r['match'] else ('✗' if r['match'] is False else '·')}" for f, r in row["check_json"].items())
                 ) if check and row["check_json"] else ""
        log(f"  {case.label[:28]:<28} {said[:110]}{marks}" + (f"  ({meta.get('seconds')}s)" if meta.get("seconds") else ""))
        if progress:
            progress((i + 1) / len(cases))
    if check:
        for f, c in counts["check"].items():
            c["precision"] = round(c["right"] / c["proposed"], 3) if c["proposed"] else None
            c["recall"] = round(c["right"] / c["had"], 3) if c["had"] else None
            log(f"{f}: had {c['had']}, proposed {c['proposed']}, right {c['right']}; precision when proposed "
                f"{c['precision'] if c['precision'] is not None else '-'}, recall {c['recall'] if c['recall'] is not None else '-'}")
    else:
        log("proposed: " + ", ".join(f"{f} {n}" for f, n in counts["proposed"].items())
            + (f"; {counts['suggested']} written back" if counts["suggested"] else ""))
    return counts


def rows(con, limit: int = 300) -> list[dict]:
    out = db.rows(con, f"SELECT * FROM resolve_enrich ORDER BY updated_at DESC LIMIT {int(limit)}")
    for r in out:
        r["fields"] = db.loads(r.get("fields"), {})
        r["check"] = db.loads(r.pop("check_json", None), None)
        hits = db.loads(r.pop("hits", None), [])
        r["hits"] = [{"url": h.get("url"), "title": h.get("title")} for h in hits[:6]]
    return out


def check_summary(rs: list[dict]) -> dict:
    """Precision when proposed and recall per field over the stored check rows, per model."""
    out: dict = {}
    for r in rs:
        if not r.get("check"):
            continue
        arm = f"enrich@{r.get('model') or 'rules'}"
        a = out.setdefault(arm, {f: {"had": 0, "proposed": 0, "right": 0} for f in FIELDS} | {"cases": 0})
        a["cases"] += 1
        for f, res in r["check"].items():
            if f not in FIELDS:
                continue
            a[f]["had"] += 1
            if res.get("proposed"):
                a[f]["proposed"] += 1
                a[f]["right"] += int(bool(res.get("match")))
    for a in out.values():
        for f in FIELDS:
            c = a[f]
            c["precision"] = round(c["right"] / c["proposed"], 3) if c["proposed"] else None
            c["recall"] = round(c["right"] / c["had"], 3) if c["had"] else None
    return out
