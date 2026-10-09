"""Look at each government's home page for its records page, business-licence page and contacts.

One request per site for the home page (plus robots.txt), a 12-second timeout, at most
1.5 MB read, and robots.txt respected.  Links are matched on their text and URL by each
question's ``page_link`` pattern; ``mailto:`` and ``tel:`` links become direct contacts.
"""
from __future__ import annotations

import html
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib import robotparser
from urllib.parse import urljoin, urlparse

import requests

from .. import config
from ..store import db
from .contacts import BUSINESS_EMAIL, RECORDS_EMAIL
from .fetch import Log
from .questions import QUESTIONS

LINK = re.compile(r"<a\b[^>]*?href\s*=\s*[\"']([^\"'#][^\"']*)[\"'][^>]*>(.*?)</a>", re.I | re.S)
TAG = re.compile(r"<[^>]+>")
MAX_BYTES = 1_500_000


def _get(session: requests.Session, url: str, timeout: int = 12) -> tuple[int, str, str]:
    with session.get(url, timeout=timeout, stream=True, allow_redirects=True) as r:
        ctype = r.headers.get("Content-Type", "")
        if "html" not in ctype and "xml" not in ctype and ctype:
            return r.status_code, r.url, ""
        body = b""
        for chunk in r.iter_content(65536):
            body += chunk
            if len(body) > MAX_BYTES:
                break
        return r.status_code, r.url, body.decode(r.encoding or "utf-8", errors="replace")


def _allowed(session: requests.Session, url: str) -> bool:
    p = urlparse(url)
    rp = robotparser.RobotFileParser()
    try:
        r = session.get(f"{p.scheme}://{p.netloc}/robots.txt", timeout=8)
        if r.status_code >= 400:
            return True
        rp.parse(r.text.splitlines())
        return rp.can_fetch(config.USER_AGENT, url)
    except requests.RequestException:
        return True


def scan_page(url: str) -> dict:
    s = requests.Session()
    s.headers.update({"User-Agent": config.USER_AGENT, "Accept": "text/html,application/xhtml+xml"})
    out = {"status": "ok", "url": url, "pages": {}, "emails": [], "phones": []}
    try:
        if not _allowed(s, url):
            return {**out, "status": "robots"}
        code, final, body = _get(s, url)
        out["url"] = final
        if code >= 400:
            return {**out, "status": f"http-{code}"}
    except requests.RequestException as e:
        return {**out, "status": "error", "error": type(e).__name__}
    for href, inner in LINK.findall(body):
        text = html.unescape(TAG.sub(" ", inner)).strip()
        href = html.unescape(href.strip())
        if href.lower().startswith("mailto:"):
            email = href[7:].split("?")[0].strip()
            if "@" in email and email not in out["emails"] and len(out["emails"]) < 6:
                out["emails"].append(email)
            continue
        if href.lower().startswith("tel:"):
            phone = re.sub(r"[^\d+]", "", href[4:])
            if len(phone) >= 10 and phone not in out["phones"] and len(out["phones"]) < 3:
                out["phones"].append(phone)
            continue
        absolute = urljoin(final, href)
        if not absolute.startswith("http"):
            continue
        for q in QUESTIONS.values():
            if q.page_link and (q.page_link.search(text) or q.page_link.search(href)):
                pages = out["pages"].setdefault(q.id, [])
                if absolute not in [p["url"] for p in pages] and len(pages) < 2:
                    pages.append({"url": absolute, "text": text[:120]})
    return out


def run(con, state: str, *, force: bool = False, workers: int = 16, log: Log = print, progress=None) -> dict:
    where = "" if force else " AND (c.checked_at IS NULL OR c.checked_at < datetime('now','-30 days'))"
    targets = db.rows(con, f"""
        SELECT g.gov_id, g.state, COALESCE(g.website, (SELECT value FROM contacts k WHERE k.gov_id=g.gov_id
               AND k.kind='website' LIMIT 1)) AS url
        FROM governments g LEFT JOIN crawl_log c ON c.gov_id = g.gov_id
        WHERE g.state=?{where}""", state)
    targets = [t for t in targets if t["url"]]
    log(f"{state}: checking {len(targets)} websites")
    found = {"records": 0, "business": 0, "direct": 0}
    done = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(scan_page, t["url"]): t for t in targets}
        for fut in as_completed(futures):
            t = futures[fut]
            res = fut.result()
            ts = db.now()
            rows = []
            for qid, pages in res["pages"].items():
                for p in pages:
                    rows.append(dict(gov_id=t["gov_id"], state=state, question=qid, kind="page", value=p["url"],
                                     label=p["text"] or "Page on the official website", source="site-scan", updated_at=ts))
                found[qid] += 1
            for e in res["emails"]:
                local = e.split("@")[0]
                q = "records" if RECORDS_EMAIL.match(local) else "business" if BUSINESS_EMAIL.match(local) else "general"
                rows.append(dict(gov_id=t["gov_id"], state=state, question=q, kind="email", value=e,
                                 label="Email on the official website", source="site-scan", updated_at=ts))
            for ph in res["phones"]:
                rows.append(dict(gov_id=t["gov_id"], state=state, question="general", kind="phone", value=ph,
                                 label="Phone on the official website", source="site-scan", updated_at=ts))
            if res["emails"] or res["phones"]:
                found["direct"] += 1
            db.upsert(con, "contacts", rows)
            con.execute("INSERT INTO crawl_log(gov_id, state, url, status, found, checked_at) VALUES (?,?,?,?,?,?) "
                        "ON CONFLICT(gov_id) DO UPDATE SET url=excluded.url, status=excluded.status, "
                        "found=excluded.found, checked_at=excluded.checked_at",
                        (t["gov_id"], state, res["url"], res["status"], json.dumps(res["pages"]), ts))
            done += 1
            if done % 50 == 0:
                con.commit()
                db.bump(con)
                log(f"{state}: {done}/{len(targets)} sites, records pages {found['records']}, "
                    f"business pages {found['business']}")
                if progress:
                    progress(done / max(1, len(targets)))
    db.bump(con)
    con.commit()
    log(f"{state}: done - records pages {found['records']}, business pages {found['business']}, "
        f"direct contacts {found['direct']} of {len(targets)} sites")
    return {"sites": len(targets), **found}
