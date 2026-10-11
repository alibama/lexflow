"""Look at each government's home page for its records page, business-licence page and contacts.

One request per site for the home page (plus robots.txt), a 12-second timeout, at most
1.5 MB read, and robots.txt respected.  Links are matched on their text and URL by each
question's ``page_link`` pattern; ``mailto:`` and ``tel:`` links become direct contacts.

Website addresses come from the Census list and Wikidata, and some are not addresses at all
("www.cityofelginor.org..under.construction"): those are recorded as ``invalid-url`` and never fetched.
Redirects are followed one hop at a time, and only to public web hosts, so a lapsed or hijacked
domain cannot point the crawler at this machine's own services.  Only office mailboxes are kept
(lexflow/privacy.py): a personal-looking address on a home page, such as a member of staff's, is never stored.
"""
from __future__ import annotations

import html
import ipaddress
import json
import re
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib import robotparser
from urllib.parse import urljoin, urlparse

import requests

from .. import config
from ..privacy import is_office_mailbox
from ..store import db
from .contacts import BUSINESS_EMAIL, RECORDS_EMAIL
from .fetch import Log
from .questions import QUESTIONS

LINK = re.compile(r"<a\b[^>]*?href\s*=\s*[\"']([^\"'#][^\"']*)[\"'][^>]*>(.*?)</a>", re.I | re.S)
TAG = re.compile(r"<[^>]+>")
MAX_BYTES = 1_500_000
MAX_HOPS = 5
LABEL = re.compile(r"^(?!-)[a-z0-9-]{1,63}(?<!-)$")
INTERNAL = {"localhost", "app", "ollama", "libsql", "searxng"}       # names that reach this machine's services


class Refused(Exception):
    """A URL lexflow will not fetch: not a public web address."""


def clean_url(raw: str | None) -> str | None:
    """A fetchable http(s) URL for a stored website value, or None if it is not one."""
    url = (raw or "").strip()
    if not url or any(c.isspace() for c in url):
        return None
    if "://" not in url:
        url = "http://" + url
    try:
        p = urlparse(url)
        host = (p.hostname or "").rstrip(".")
        port = p.port
    except ValueError:                               # a malformed port or bracket
        return None
    if p.scheme not in ("http", "https") or port not in (None, 80, 443) or not host:
        return None
    try:
        host = host.encode("idna").decode("ascii").lower()
    except UnicodeError:
        return None
    labels = host.split(".")
    if len(host) > 253 or len(labels) < 2 or not all(LABEL.match(x) for x in labels) or not labels[-1].isalpha():
        return None
    return url


class NoHost(Exception):
    """The host name does not resolve (a lapsed domain)."""


def _check_host(url: str) -> None:
    """Raise unless the URL's host is a public web host: no internal service name, private or loopback address."""
    try:
        p = urlparse(url)
        host, port = (p.hostname or "").lower(), p.port
    except ValueError as e:
        raise Refused(url) from e
    if p.scheme not in ("http", "https") or port not in (None, 80, 443) or not host or host in INTERNAL:
        raise Refused(url)
    try:
        addrs = {a[4][0] for a in socket.getaddrinfo(host, port or (443 if p.scheme == "https" else 80))}
    except (socket.gaierror, UnicodeError) as e:
        raise NoHost(host) from e
    if not all(ipaddress.ip_address(a.split("%")[0]).is_global for a in addrs):
        raise Refused(url)


def _get(session: requests.Session, url: str, timeout: int = 12) -> tuple[int, str, str]:
    for _ in range(MAX_HOPS + 1):
        _check_host(url)
        with session.get(url, timeout=timeout, stream=True, allow_redirects=False) as r:
            if r.is_redirect and r.headers.get("Location"):
                url = clean_url(urljoin(url, r.headers["Location"])) or ""
                continue
            ctype = r.headers.get("Content-Type", "")
            if "html" not in ctype and "xml" not in ctype and ctype:
                return r.status_code, r.url, ""
            body = b""
            for chunk in r.iter_content(65536):
                body += chunk
                if len(body) > MAX_BYTES:
                    break
            return r.status_code, r.url, body.decode(r.encoding or "utf-8", errors="replace")
    raise Refused(f"more than {MAX_HOPS} redirects")


def _allowed(session: requests.Session, url: str) -> bool:
    p = urlparse(url)
    rp = robotparser.RobotFileParser()
    try:
        robots = f"{p.scheme}://{p.netloc}/robots.txt"
        _check_host(robots)                          # scan_page has checked this host already; a race is refused
        r = session.get(robots, timeout=8, allow_redirects=False)
        if r.status_code >= 500:
            return False                             # RFC 9309: a server error means assume complete disallow
        if r.status_code >= 300:
            return True
        rp.parse(r.text.splitlines())
        return rp.can_fetch(config.USER_AGENT, url)
    except (Refused, NoHost):
        return False
    except (requests.RequestException, ValueError, UnicodeError):
        return True


def scan_page(url: str) -> dict:
    s = requests.Session()
    s.headers.update({"User-Agent": config.USER_AGENT, "Accept": "text/html,application/xhtml+xml"})
    out = {"status": "ok", "url": url, "pages": {}, "emails": [], "phones": []}
    fetchable = clean_url(url)
    if not fetchable:
        return {**out, "status": "invalid-url"}
    try:
        _check_host(fetchable)
        if not _allowed(s, fetchable):
            return {**out, "status": "robots"}
        code, final, body = _get(s, fetchable)
        out["url"] = final
        if code >= 400:
            return {**out, "status": f"http-{code}"}
    except NoHost:
        return {**out, "status": "dns"}
    except Refused:
        return {**out, "status": "refused"}
    except (requests.RequestException, ValueError, UnicodeError, OSError) as e:
        # urllib3 raises LocationParseError (a ValueError) for a bad host at connect time, outside requests' errors
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


def run(con, state: str, *, force: bool = False, workers: int = 16, log: Log = print, progress=None,
        gov_ids: list[str] | None = None) -> dict:
    where = "" if force else " AND (c.checked_at IS NULL OR c.checked_at < datetime('now','-30 days'))"
    targets = db.rows(con, f"""
        SELECT g.gov_id, g.state, g.name, COALESCE(g.website, (SELECT value FROM contacts k WHERE k.gov_id=g.gov_id
               AND k.kind='website' LIMIT 1)) AS url
        FROM governments g LEFT JOIN crawl_log c ON c.gov_id = g.gov_id
        WHERE g.state=?{where}""", state)
    targets = [t for t in targets if t["url"] and (gov_ids is None or t["gov_id"] in gov_ids)]
    log(f"{state}: checking {len(targets)} websites")
    found = {"records": 0, "business": 0, "direct": 0, "invalid": 0, "failed": 0}
    done = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(scan_page, t["url"]): t for t in targets}
        for fut in as_completed(futures):
            t = futures[fut]
            try:
                res = fut.result()
            except Exception as e:  # noqa: BLE001 - one site's failure never ends the run
                res = {"status": "error", "error": type(e).__name__, "url": t["url"], "pages": {}, "emails": [],
                       "phones": []}
            if res["status"] == "invalid-url":
                found["invalid"] += 1
            elif res["status"] == "error":
                found["failed"] += 1
            ts = db.now()
            rows = []
            for qid, pages in res["pages"].items():
                for p in pages:
                    rows.append(dict(gov_id=t["gov_id"], state=state, question=qid, kind="page", value=p["url"],
                                     label=p["text"] or "Page on the official website", source="site-scan", updated_at=ts))
                found[qid] += 1
            for e in res["emails"]:
                if not is_office_mailbox(e, owner=t.get("name")):
                    continue                     # a personal-looking mailbox (a member of staff) is never stored
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
        f"direct contacts {found['direct']} of {len(targets)} sites"
        + (f"; {found['invalid']} stored website values are not web addresses" if found["invalid"] else "")
        + (f"; {found['failed']} sites failed" if found["failed"] else ""))
    return {"sites": len(targets), **found}
