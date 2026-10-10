"""Court decisions that cite the statutes behind each process model (CourtListener, Free Law Project).

For every section a state model rests on (its curated or located sections), the search API is asked
for opinions in that state's courts that quote the section number.  One request a second, at most two
pages per section.  Results go to ``case_law`` (shared through Turso) and show on model pages, the
wiki and the Wikibase.  Court opinions are public domain; CourtListener's metadata is free to use.
"""
from __future__ import annotations

import re
import time

import requests

from .. import config
from ..store import db
from . import states as S
from .fetch import Log

API = "https://www.courtlistener.com/api/rest/v4/search/"
# CourtListener court ids for each state's appellate courts (high court first; Delaware adds the Court of
# Chancery, where most LLC law is made).  The ids for VA, DC and MD returned opinions here; the rest follow
# CourtListener's naming and are checked by the first search (a wrong id is a 400, logged, not "0 opinions").
COURTS = {
    "al": ["ala", "alacivapp", "alacrimapp"], "ak": ["alaska", "alaskactapp"], "az": ["ariz", "arizctapp"],
    "ar": ["ark", "arkctapp"], "ca": ["cal", "calctapp"], "co": ["colo", "coloctapp"], "ct": ["conn", "connappct"],
    "de": ["del", "delch", "delsuperct"], "dc": ["dc"], "fl": ["fla", "fladistctapp"], "ga": ["ga", "gactapp"],
    "hi": ["haw", "hawapp"], "id": ["idaho", "idahoctapp"], "il": ["ill", "illappct"], "in": ["ind", "indctapp"],
    "ia": ["iowa", "iowactapp"], "ks": ["kan", "kanctapp"], "ky": ["ky", "kyctapp"], "la": ["la", "lactapp"],
    "me": ["me"], "md": ["md", "mdctspecapp"], "ma": ["mass", "massappct"], "mi": ["mich", "michctapp"],
    "mn": ["minn", "minnctapp"], "ms": ["miss", "missctapp"], "mo": ["mo", "moctapp"], "mt": ["mont"],
    "ne": ["neb", "nebctapp"], "nv": ["nev", "nevapp"], "nh": ["nh"], "nj": ["nj", "njsuperctappdiv"],
    "nm": ["nm", "nmctapp"], "ny": ["ny", "nyappdiv"], "nc": ["nc", "ncctapp"], "nd": ["nd", "ndctapp"],
    "oh": ["ohio", "ohioctapp"], "ok": ["okla", "oklacivapp", "oklacrimapp"], "or": ["or", "orctapp"],
    "pa": ["pa", "pasuperct", "pacommwct"], "ri": ["ri"], "sc": ["sc", "scctapp"], "sd": ["sd"],
    "tn": ["tenn", "tennctapp"], "tx": ["tex", "texapp", "texcrimapp"], "ut": ["utah", "utahctapp"], "vt": ["vt"],
    "va": ["va", "vactapp"], "wa": ["wash", "washctapp"], "wv": ["wva"], "wi": ["wis", "wisctapp"], "wy": ["wyo"],
}


class RateLimited(RuntimeError):
    """CourtListener kept answering 429: the section was not searched (which is not the same as no opinions)."""


def courts_for(state: str) -> list[str]:
    return COURTS.get(state, [])


# the dataset's abbreviations of New York's consolidated laws, as opinions write them
NY_LAWS = {"PBO Law": "Public Officers Law", "LLC Law": "Limited Liability Company Law",
           "BSC Law": "Business Corporation Law", "PTR Law": "Partnership Law", "GBS Law": "General Business Law"}


def query_for(state: str, ref: str) -> str:
    """'2.2-3704' -> "2.2-3704".  A distinctive number ('40.25.110', '39-121.01') is searched alone, since
    opinions cite it in many styles ('AS 40.25.110'); a short one, and Maryland's numbers, which repeat across
    articles ('General Provisions § 4-203'), also need the code's name."""
    if "§" not in ref:
        return f'"{ref}"'
    article, number = (x.strip() for x in ref.rsplit("§", 1))
    distinctive = bool(re.search(r"[.\-]", number)) and len(number) >= 5
    if distinctive and state != "md":
        return f'"{number}"'
    article = re.sub(r"^(Md\. Code,|Tex\.|Cal\.|N\.Y\.)\s*", "", article).strip(" ,")
    article = NY_LAWS.get(article, article)
    return f'"{number}" AND "{article}"' if article else f'"{number}"'


def search(state: str, ref: str, pages: int = 2, log: Log = print) -> list[dict]:
    params = {"q": query_for(state, ref), "type": "o", "court": " ".join(courts_for(state)), "order_by": "score desc"}
    headers = {"User-Agent": config.USER_AGENT}
    if config.COURTLISTENER_TOKEN:
        headers["Authorization"] = f"Token {config.COURTLISTENER_TOKEN}"
    out, url = [], API
    for _ in range(pages):
        try:
            for attempt in range(5):
                r = requests.get(url, params=params if url == API else None, headers=headers, timeout=90)
                if r.status_code != 429:
                    break
                wait = r.headers.get("Retry-After", "")
                time.sleep(min(int(wait), 300) if wait.isdigit() else 30 * (attempt + 1))
            else:
                raise RateLimited(f"{state} {ref}: CourtListener is rate limiting (add COURTLISTENER_TOKEN to .env)")
            r.raise_for_status()
        except requests.RequestException as e:
            log(f"{state} {ref}: CourtListener search failed: {e}")
            break
        data = r.json()
        out += data.get("results", [])
        url = data.get("next")
        time.sleep(1.0)
        if not url:
            break
    return out


def sections_for(con, state: str) -> list[tuple[str, str]]:
    """(question, section ref) for every section a state's models rest on."""
    refs: list[tuple[str, str]] = []
    for r in db.rows(con, "SELECT question, metrics FROM process_models WHERE state=?", state):
        for ref in (db.loads(r["metrics"], {}) or {}).get("sections") or []:
            if (r["question"], ref) not in refs:
                refs.append((r["question"], ref))
    for r in db.rows(con, "SELECT question, section FROM located_law WHERE state=? AND status='found' "
                          "AND method IN ('seed','verified')", state):
        if r["section"] and (r["question"], r["section"]) not in refs:
            refs.append((r["question"], r["section"]))
    return refs


def run(con, state: str, log: Log = print, progress=None) -> dict:
    """Search every section of one state.  A rate limit stops the run (RateLimited) instead of recording the
    remaining sections as having no opinions."""
    refs = sections_for(con, state)
    if not courts_for(state):
        log(f"{S.NAME.get(state, state)}: no CourtListener court ids for this jurisdiction; skipped")
        return {"sections": 0, "opinions": 0}
    total = 0
    for i, (qid, ref) in enumerate(refs):
        rows, ts = [], db.now()
        for x in search(state, ref, log=log):
            cites = [c for c in (x.get("citation") or []) if c]
            rows.append({"state": state, "section": ref, "question": qid, "cluster_id": str(x.get("cluster_id")),
                         "case_name": (x.get("caseName") or "")[:300], "court": x.get("court"),
                         "court_id": x.get("court_id"), "date_filed": x.get("dateFiled"),
                         "citation": "; ".join(cites)[:200] or None, "cite_count": x.get("citeCount") or 0,
                         "url": "https://www.courtlistener.com" + (x.get("absolute_url") or ""),
                         "source": "courtlistener", "updated_at": ts})
        db.upsert(con, "case_law", rows)
        con.commit()
        total += len(rows)
        log(f"{S.NAME[state]} § {ref}: {len(rows)} opinions")
        if progress:
            progress((i + 1) / max(1, len(refs)))
    db.bump(con)
    con.commit()
    return {"sections": len(refs), "opinions": total}


def for_model(con, state: str, sections: list[str], limit: int = 25) -> list[dict]:
    if not sections:
        return []
    q = ",".join("?" for _ in sections)
    return db.rows(con, f"""SELECT section, case_name, court, court_id, date_filed, citation, cite_count, url, cluster_id
                            FROM case_law WHERE state=? AND section IN ({q})
                            ORDER BY cite_count DESC, date_filed DESC LIMIT ?""", state, *sections, limit)
