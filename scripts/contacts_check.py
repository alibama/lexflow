"""Contact freshness pilot: a read-only check of a stratified sample of organisational contacts.

    python scripts/contacts_check.py OUT.json [--db PATH] [--states va,md,dc,ca,tx,oh,me]
        [--quota va=4,md=3,dc=9,*=2] [--workers 6] [--no-wikidata] [--no-fallback] [--plan]

Read-only by design. The database is opened with ``mode=ro`` and ``query_only`` and is never
written; nothing is posted anywhere. The script prints a report and writes the per-contact
results as JSON to OUT.json. ``--plan`` prints the sample without touching the network.

Sample: websites of governments (``governments.website`` plus ``contacts`` rows of kind website),
stratified by state and population tier (large >= 50k, mid >= 5k, small), ordered within each
stratum by a hash of ``gov_id`` so the draw is deterministic; plus every record/licence page,
office email and phone row of those states, and the home pages of the governments they belong to.

Checks
  website/page  one GET per URL with redirects followed by hand (15 s timeout, at most one request
                per second per domain): final status, final domain, whether the domain changed,
                the page title, parked/default-page/bot-wall markers and whether the place name
                appears. On a failure one fallback is tried (http -> https, or www. toggled), and a
                certificate failure is retried once without verification; both are flagged.
  email         DNS only: the MX record of the domain, else an A record. Nothing is sent and no
                SMTP connection is made.
  phone         NANP shape, and whether the number appears in the HTML of the government's own
                home page fetched above (or, second best, another official page fetched for it).
  Wikidata      P856 (official website) for governments with a QID, read with wbgetentities in
                batches of 50 and compared with the stored and the live domain.

Classes: ok; moved (the stored address leads to a working one elsewhere: a redirect to a new domain,
or only its www/https variant answers), broken (DNS failure, 4xx/5xx, unreachable, parked, default
server page or gambling/spam content on a lapsed domain, invalid number), unverifiable (bot wall,
no URL stored, place name absent, number not found on the site). Moved and broken count as stale.

Privacy: organisational channels only. An email address is checked only when its local part names
an office (a role word, or an acronym spelled out in the same row); other addresses are skipped
and only counted. Raw contact text is not copied into the output, only the parsed URL, office
mailbox or number.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
import random
import re
import socket
import sqlite3
import statistics
import struct
import sys
import threading
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import requests
import urllib3

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lexflow import config  # noqa: E402  (only DB_PATH is read)

UA = "lexflow-research/0.1 (https://github.com/alibama/lexflow)"
TIMEOUT = 15.0
INTERVAL = 1.0           # seconds between requests to one registrable domain
MAX_HOPS = 8
MAX_BYTES = 1_500_000
WIKIDATA_API = "https://www.wikidata.org/w/api.php"
WD_BATCH = 50
DEFAULT_STATES = "va,md,dc,ca,tx,oh,me"
DEFAULT_QUOTA = "va=4,md=3,dc=9,*=2"
TIERS = (("large", 50_000), ("mid", 5_000), ("small", 0))
SALT = "contacts-pilot-v1:"

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --------------------------------------------------------------------------- text helpers

URL_RE = re.compile(r"https?://[^\s;,<>\"')]+", re.I)
DOMAIN_RE = re.compile(r"\b((?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+(?:gov|us|org|com|net|edu|info|io))"
                       r"((?:/[^\s;,<>\"')]*)?)", re.I)
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?<![\d])(?:\+?1[\s.\-]?)?\(?(\d{3})\)?[\s.\-]?(\d{3})[\s.\-](\d{4})(?!\d)")
PHONE_HTML_RE = re.compile(r"(?<![\d])(?:\+?1[\s.\-]?)?\(?(\d{3})\)?[\s.\-]?(\d{3})[\s.\-]?(\d{4})(?!\d)")
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
META_REFRESH_RE = (
    re.compile(r"<meta[^>]+http-equiv=[\"']?refresh[\"']?[^>]*content=[\"']?\s*(\d+)\s*;\s*url\s*=\s*[\"']?([^\"'>\s]+)", re.I),
    re.compile(r"<meta[^>]+content=[\"']?\s*(\d+)\s*;\s*url\s*=\s*[\"']?([^\"'>\s]+)[^>]*http-equiv=[\"']?refresh", re.I),
)
JS_REDIRECT_RE = re.compile(r"(?:window|document|top|self)\.location(?:\.href)?\s*=\s*[\"']([^\"']+)[\"']"
                            r"|location\.(?:replace|assign)\(\s*[\"']([^\"']+)[\"']", re.I)

ROLE_WORDS = ("info", "foia", "record", "clerk", "mpia", "licens", "business", "council", "appeal",
              "contact", "office", "admin", "help", "service", "permit", "cityhall", "townhall",
              "mayor", "manager", "planning", "zoning", "finance", "treasur", "assessor", "revenue",
              "mail", "webmaster", "general", "public", "request", "inquir", "citizen", "customer",
              "support", "media", "press", "communication", "court", "police", "fire", "utilit",
              "water", "billing", "dept", "department", "board", "commission", "city", "town",
              "county", "village", "boro", "township", "govt", "government")
ROLE_SHORT = ("pia", "oig", "biz", "tax", "hr", "cor", "dpw", "it")

PARKED_MARKERS = ("domain is for sale", "domain may be for sale", "buy this domain", "domain for sale",
                  "this domain is for sale", "hugedomains", "sedoparking", "sedo domain parking",
                  "parkingcrew", "bodis.com", "afternic", "undeveloped.com", "domainmarket",
                  "this domain has expired", "domain has expired", "renew this domain",
                  "parked free", "parked domain", "domain parking")
PARKED_HOSTS = ("hugedomains.com", "dan.com", "sedo.com", "afternic.com", "godaddy.com", "bodis.com",
                "parkingcrew.net", "uniregistry.com", "sav.com", "namecheap.com", "porkbun.com",
                "domainmarket.com", "undeveloped.com", "parklogic.com")
DEAD_MARKERS = ("account suspended", "account has been suspended", "website is no longer available",
                "apache2 ubuntu default page", "apache2 debian default page", "welcome to nginx",
                "iis windows server", "test page for the apache", "default web site page",
                "web server's default page", "this site is currently unavailable",
                "website expired", "site has expired", "hosting account has expired")
# a lapsed municipal domain re-registered for gambling/SEO spam: the title gives it away
SPAM_TITLE_RE = re.compile(r"\b(slot|slots|situs|gacor|togel|judi|casino|poker|bandar|bokep|jasa|bisnis|sbobet|"
                           r"toto|viagra|cialis|escort|porn|betting|maxwin)\b|[぀-ヿ一-鿿가-힯]", re.I)
BLOCK_MARKERS = ("just a moment", "attention required", "captcha", "access denied", "incapsula",
                 "pardon our interruption", "are you a robot", "request unsuccessful",
                 "checking your browser", "ddos protection", "bot verification", "request rejected")


def hkey(s: str) -> str:
    return hashlib.sha1((SALT + s).encode()).hexdigest()


def tier_of(pop) -> str:
    pop = pop or 0
    for name, floor in TIERS:
        if pop >= floor:
            return name
    return "small"


def host_of(url: str) -> str:
    try:
        return (urlsplit(url).hostname or "").lower().rstrip(".")
    except ValueError:
        return ""


def base_domain(host: str) -> str:
    """Registrable domain, approximately: strip www., keep locality .us names whole."""
    host = (host or "").lower().rstrip(".")
    if host.startswith("www."):
        host = host[4:]
    labels = host.split(".")
    if len(labels) <= 2:
        return host
    if labels[-1] == "us" and len(labels[-2]) == 2:          # ci.x.va.us, co.x.al.us, x.va.us
        return ".".join(labels[-4:])
    if len(labels[-1]) == 2 and labels[-2] in ("co", "com", "org", "gov", "net", "ac", "edu"):
        return ".".join(labels[-3:])
    return ".".join(labels[-2:])


def norm_url(u: str) -> str:
    u = u.strip()
    if not re.match(r"^[a-z][a-z0-9+.-]*://", u, re.I):
        u = "http://" + u
    try:
        p = urlsplit(u)
    except ValueError:
        return u.lower()
    host = (p.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return host + (p.path.rstrip("/") or "")


def to_url(value: str, scheme: str) -> str | None:
    v = (value or "").strip()
    m = URL_RE.search(v)
    if m:
        return m.group(0)
    if scheme == "http" and re.match(r"^[\w.-]+\.[a-z]{2,}(/\S*)?$", v, re.I):
        return "http://" + v
    m = DOMAIN_RE.search(v)
    if m:
        return f"{scheme}://{m.group(1)}{m.group(2) or ''}"
    return None


def norm_text(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def core_name(name: str) -> str:
    n = name.strip()
    n = re.sub(r"^(city and county|consolidated government|unified government|charter township|city|town|"
               r"village|borough|township|county|municipality|plantation|parish) of\s+", "", n, flags=re.I)
    n = re.sub(r"\s+(charter township|county|city|town|township|village|borough|parish|municipality|"
               r"plantation|government|dc)$", "", n, flags=re.I)
    return n.strip()


def visible_text(body: str) -> str:
    body = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", body[:600_000])
    return html.unescape(re.sub(r"<[^>]+>", " ", body))


def name_present(gov_name: str, title: str, body: str, host: str) -> bool:
    """The place name in the title or the visible text; the host name counts only for near-empty (JS-only) pages."""
    core = norm_text(core_name(gov_name))
    if not core:
        return True
    text = visible_text(body)
    hay = " " + norm_text(title + " " + text) + " "
    if f" {core} " in hay:
        return True
    alt = core.replace("saint ", "st ") if core.startswith("saint ") else core.replace("st ", "saint ", 1)
    if alt != core and f" {alt} " in hay:
        return True
    squashed = core.replace(" ", "")
    return len(norm_text(text)) < 1500 and len(squashed) >= 4 and squashed in host.replace("-", "")


def nanp_valid(area: str, exch: str, line: str) -> bool:
    if area[0] in "01" or area[1:] == "11" or area[1] == "9":      # N11 service codes, N9X reserved
        return False
    if exch[0] in "01" or exch[1:] == "11":
        return False
    if exch == "555" and line.startswith("01"):                                      # fictional range
        return False
    return True


def phones_in(text: str) -> set[str]:
    return {a + e + s for a, e, s in PHONE_HTML_RE.findall(html.unescape(text))}


def is_office_mailbox(addr: str, row_text: str) -> bool:
    local = addr.split("@", 1)[0].lower()
    if any(w in local for w in ROLE_WORDS):
        return True
    tokens = re.split(r"[._+-]", local)
    if local in ROLE_SHORT or any(t in ROLE_SHORT for t in tokens):
        return True
    # an office acronym spelled out in capitals in the same row, e.g. "BMZA"
    return local.isalpha() and len(local) <= 6 and re.search(rf"\b{re.escape(local.upper())}\b", row_text) is not None


# --------------------------------------------------------------------------- DNS (read-only lookups)

def _nameservers() -> list[str]:
    out = []
    try:
        with open("/etc/resolv.conf", encoding="utf-8") as fh:
            for line in fh:
                parts = line.split()
                if len(parts) >= 2 and parts[0] == "nameserver":
                    out.append(parts[1])
    except OSError:
        pass
    return out


NAMESERVERS = _nameservers()


def _read_name(buf: bytes, off: int, depth: int = 0) -> str:
    labels = []
    while off < len(buf):
        n = buf[off]
        if n == 0:
            break
        if n & 0xC0 == 0xC0:
            if depth > 16:
                raise ValueError("compression loop")
            labels.append(_read_name(buf, struct.unpack(">H", buf[off:off + 2])[0] & 0x3FFF, depth + 1))
            break
        labels.append(buf[off + 1:off + 1 + n].decode("ascii", "replace"))
        off += 1 + n
    return ".".join(x for x in labels if x)


def _skip_name(buf: bytes, off: int) -> int:
    while True:
        n = buf[off]
        if n == 0:
            return off + 1
        if n & 0xC0 == 0xC0:
            return off + 2
        off += 1 + n


def dns_query(name: str, qtype: int, timeout: float = 5.0):
    """One recursive query to the system resolver. Returns (rcode, answers) or (None, error)."""
    try:
        labels = name.rstrip(".").encode("idna").split(b".")
    except UnicodeError as e:
        return None, f"idna: {e}"
    question = b"".join(struct.pack("B", len(x)) + x for x in labels) + b"\0" + struct.pack(">HH", qtype, 1)
    last = "no resolver in /etc/resolv.conf"
    for server in NAMESERVERS[:3]:
        tid = random.randrange(65536)
        msg = struct.pack(">HHHHHH", tid, 0x0100, 1, 0, 0, 0) + question
        fam = socket.AF_INET6 if ":" in server else socket.AF_INET
        try:
            with socket.socket(fam, socket.SOCK_DGRAM) as s:
                s.settimeout(timeout)
                s.sendto(msg, (server, 53))
                deadline = time.monotonic() + timeout
                while True:
                    data, _ = s.recvfrom(4096)
                    if len(data) >= 12 and struct.unpack(">H", data[:2])[0] == tid:
                        break
                    if time.monotonic() > deadline:
                        raise socket.timeout()
            if struct.unpack(">H", data[2:4])[0] & 0x0200:          # truncated: ask again over TCP
                with socket.create_connection((server, 53), timeout=timeout) as s:
                    s.sendall(struct.pack(">H", len(msg)) + msg)
                    raw = b""
                    while len(raw) < 2 or len(raw) < 2 + struct.unpack(">H", raw[:2])[0]:
                        chunk = s.recv(65535)
                        if not chunk:
                            break
                        raw += chunk
                    data = raw[2:]
        except OSError as e:
            last = f"{type(e).__name__}: {e}"
            continue
        try:
            flags = struct.unpack(">H", data[2:4])[0]
            qd, an = struct.unpack(">HH", data[4:8])
            off = 12
            for _ in range(qd):
                off = _skip_name(data, off) + 4
            answers = []
            for _ in range(an):
                off = _skip_name(data, off)
                t, _c, _ttl, rdlen = struct.unpack(">HHIH", data[off:off + 10])
                off += 10
                rd = off
                off += rdlen
                if t == 15:
                    answers.append(("MX", struct.unpack(">H", data[rd:rd + 2])[0], _read_name(data, rd + 2)))
                elif t == 1 and rdlen == 4:
                    answers.append(("A", socket.inet_ntoa(data[rd:rd + 4])))
                elif t == 5:
                    answers.append(("CNAME", _read_name(data, rd)))
            return flags & 0xF, answers
        except (struct.error, IndexError, ValueError) as e:
            last = f"parse: {e}"
    return None, last


_resolve_cache: dict[str, tuple[bool, str]] = {}
_resolve_lock = threading.Lock()


def resolve(host: str) -> tuple[bool, str]:
    with _resolve_lock:
        if host in _resolve_cache:
            return _resolve_cache[host]
    try:
        socket.getaddrinfo(host, None)
        res = (True, "")
    except socket.gaierror as e:
        res = (False, "nxdomain" if e.errno in (socket.EAI_NONAME, getattr(socket, "EAI_NODATA", -5)) else "dns_temp")
    except (UnicodeError, OSError):
        res = (False, "dns_temp")
    with _resolve_lock:
        _resolve_cache[host] = res
    return res


# --------------------------------------------------------------------------- polite HTTP

class Throttle:
    """At most one request start per INTERVAL seconds for each registrable domain."""

    def __init__(self, interval: float = INTERVAL):
        self.interval = interval
        self.next: dict[str, float] = {}
        self.lock = threading.Lock()

    def wait(self, key: str) -> float:
        with self.lock:
            now = time.monotonic()
            slot = max(now, self.next.get(key, 0.0))
            self.next[key] = slot + self.interval
        if slot > now:
            time.sleep(slot - now)
        return max(0.0, slot - now)


class Fetcher:
    def __init__(self, fallback: bool = True):
        self.throttle = Throttle()
        self.local = threading.local()
        self.fallback = fallback
        self.count = Counter()
        self.lock = threading.Lock()

    def session(self) -> requests.Session:
        s = getattr(self.local, "s", None)
        if s is None:
            s = requests.Session()
            s.headers.update({"User-Agent": UA, "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.5",
                              "Accept-Language": "en-US,en;q=0.8"})
            self.local.s = s
        return s

    def _get(self, url: str, verify: bool, out: dict):
        key = base_domain(host_of(url))
        out["wait_s"] += self.throttle.wait(key)
        t = time.monotonic()
        out["requests"] += 1
        with self.lock:
            self.count[key] += 1
        try:
            return self.session().get(url, allow_redirects=False, stream=True, timeout=(TIMEOUT, TIMEOUT), verify=verify)
        finally:
            out["net_s"] += time.monotonic() - t

    def fetch(self, url: str) -> dict:
        t0 = time.monotonic()
        out = {"url": url, "final_url": None, "status": None, "hops": [], "requests": 0, "wait_s": 0.0,
               "net_s": 0.0, "title": "", "error": None, "tls_unverified": False, "content_type": "",
               "bytes": 0, "client_redirect": None, "fallback": None, "first_error": None,
               "server": "", "challenge_header": False, "_body": ""}
        self._chain(url, out)
        if out["error"] and self.fallback and not out["hops"]:
            alt = self._fallback_url(url, out["error"])
            if alt:
                out["first_error"], out["fallback"] = out["error"], alt
                out["error"] = None
                self._chain(alt, out)
        out["client_redirect_followed"] = False
        if not out["error"] and out["_body"] and (out["status"] or 999) < 400:
            target = self._client_redirect(out)
            if target and norm_url(target) != norm_url(out["final_url"] or ""):
                out["client_redirect"] = target
                if len(re.sub(r"<[^>]+>|\s+", "", out["_body"])) < 4000:
                    sub = {**out, "hops": [], "_body": "", "title": "", "error": None, "status": None}
                    self._chain(target, sub)
                    if not sub["error"] and sub["status"] and sub["status"] < 400:
                        for k in ("final_url", "status", "title", "content_type", "bytes", "_body", "server",
                                  "challenge_header", "tls_unverified"):
                            out[k] = sub[k]
                        out["hops"] += [[h[0], h[1], "client"] for h in sub["hops"]]
                        out["client_redirect_followed"] = True
                    else:
                        out["client_redirect_error"] = sub["error"] or f"http_{sub['status']}"
                    out["requests"], out["wait_s"], out["net_s"] = sub["requests"], sub["wait_s"], sub["net_s"]
        out["elapsed_s"] = round(time.monotonic() - t0, 2)
        out["net_s"] = round(out["net_s"], 2)
        out["wait_s"] = round(out["wait_s"], 2)
        return out

    @staticmethod
    def _fallback_url(url: str, error: str) -> str | None:
        p = urlsplit(url)
        host = (p.hostname or "").lower()
        if error.startswith("dns"):
            if host.startswith("www."):
                return url.replace(host, host[4:], 1)
            if host.count(".") == 1:
                return url.replace(host, "www." + host, 1)
        if error in ("connect", "timeout") and p.scheme == "http":
            return "https" + url[4:]
        return None

    def _chain(self, url: str, out: dict) -> None:
        cur, verify, seen = url, True, Counter()
        for _ in range(MAX_HOPS + 1):
            host = host_of(cur)
            if not host:
                out["error"] = "bad_url"
                return
            ok, why = resolve(host)
            if not ok:
                out["error"] = "dns" if why == "nxdomain" else "dns_temp"
                out["failed_host"] = host
                return
            seen[cur] += 1
            if seen[cur] > 2:
                out["error"] = "redirect_loop"
                return
            try:
                r = self._get(cur, verify, out)
            except requests.exceptions.SSLError:
                if verify:
                    verify, out["tls_unverified"] = False, True
                    try:
                        r = self._get(cur, False, out)
                    except requests.exceptions.RequestException as e:
                        out["error"] = _req_error(e)
                        return
                else:
                    out["error"] = "tls"
                    return
            except requests.exceptions.RequestException as e:
                out["error"] = _req_error(e)
                return
            out["hops"].append([r.status_code, cur])
            if r.status_code in (301, 302, 303, 307, 308) and r.headers.get("location"):
                nxt = urljoin(cur, r.headers["location"].strip())
                r.close()
                cur = nxt
                continue
            out["final_url"], out["status"] = cur, r.status_code
            out["content_type"] = r.headers.get("content-type", "")
            out["server"] = r.headers.get("server", "")
            out["challenge_header"] = any(h in r.headers for h in ("cf-ray", "cf-mitigated", "x-sucuri-id", "x-iinfo")) \
                or bool(re.search(r"cloudflare|akamai|incapsula|sucuri", out["server"], re.I))
            body = b""
            ct = out["content_type"].lower()
            if not ct or "html" in ct or "text" in ct or "xml" in ct:
                t = time.monotonic()
                try:
                    for chunk in r.iter_content(65536):
                        body += chunk
                        if len(body) >= MAX_BYTES or time.monotonic() - t > TIMEOUT:
                            break
                except requests.exceptions.RequestException:
                    pass
            r.close()
            out["bytes"] = len(body)
            m = re.search(r"charset=([\w-]+)", ct) or re.search(rb"<meta[^>]+charset=[\"']?([\w-]+)", body[:4096], re.I)
            enc = m.group(1) if m else "utf-8"
            enc = enc.decode("ascii", "ignore") if isinstance(enc, bytes) else enc
            try:
                text = body.decode(enc, errors="replace")
            except LookupError:
                text = body.decode("utf-8", errors="replace")
            out["_body"] = text
            tm = TITLE_RE.search(text[:400_000])
            out["title"] = re.sub(r"\s+", " ", html.unescape(tm.group(1))).strip()[:200] if tm else ""
            return
        out["error"] = "too_many_redirects"

    @staticmethod
    def _client_redirect(out: dict) -> str | None:
        body = out["_body"][:200_000]
        for rx in META_REFRESH_RE:
            m = rx.search(body)
            if m and int(m.group(1)) <= 10:
                return urljoin(out["final_url"], html.unescape(m.group(2)))
        if len(re.sub(r"<[^>]+>|\s+", "", body)) < 4000:
            m = JS_REDIRECT_RE.search(body)
            if m:
                target = m.group(1) or m.group(2)
                if target and not target.startswith(("#", "javascript:")):
                    return urljoin(out["final_url"], target)
        return None


def _req_error(e: Exception) -> str:
    if isinstance(e, requests.exceptions.Timeout):
        return "timeout"
    if isinstance(e, requests.exceptions.SSLError):
        return "tls"
    if isinstance(e, requests.exceptions.TooManyRedirects):
        return "too_many_redirects"
    if isinstance(e, requests.exceptions.ConnectionError):
        msg = str(e).lower()
        if "name or service not known" in msg or "nodename nor servname" in msg or "getaddrinfo" in msg:
            return "dns"
        return "connect"
    return "other"


# --------------------------------------------------------------------------- classification

def classify_web(item: dict, f: dict) -> tuple[str, str, list[str]]:
    flags = []
    if f.get("tls_unverified"):
        flags.append("tls_unverified")
    if f.get("fallback"):
        flags.append("fallback_" + ("https" if f["fallback"].startswith("https") and f["url"].startswith("http:") else "www"))
    err = f.get("error")
    if err == "no_url":
        return "unverifiable", "no_url_stored", flags
    if err == "dns_temp":
        return "unverifiable", "dns_temporary", flags
    if err:
        return "broken", {"dns": "dns_nxdomain"}.get(err, err), flags
    st = f["status"] or 0
    text = (f["title"] + " " + f["_body"][:30_000]).lower()
    final_host = host_of(f.get("final_url") or "")
    blocked = st in (401, 403, 406, 418, 429, 999) or (st >= 500 and (f["challenge_header"] or any(m in text for m in BLOCK_MARKERS))) \
        or (st < 300 and any(m in f["title"].lower() for m in BLOCK_MARKERS))
    if blocked:
        return "unverifiable", f"blocked_http_{st}", flags
    if st >= 400:
        return "broken", f"http_{st}", flags
    if base_domain(final_host) in PARKED_HOSTS or any(m in text for m in PARKED_MARKERS):
        return "broken", "parked", flags
    if any(m in text for m in DEAD_MARKERS):
        return "broken", "default_or_suspended_page", flags
    if SPAM_TITLE_RE.search(f["title"] or ""):
        return "broken", "hijacked_spam", flags
    start = base_domain(host_of(f["url"]))
    landed = base_domain(final_host)
    if f.get("client_redirect"):
        flags.append("client_redirect" if f.get("client_redirect_followed") else "client_redirect_not_followed")
        if not f.get("client_redirect_followed") and base_domain(host_of(f["client_redirect"])) != start:
            flags.append("client_redirect_offsite")
    if (f.get("final_url") or "").startswith("https:") and f["url"].startswith("http:"):
        flags.append("https_upgrade")
    named = name_present(item["gov"], f["title"], f["_body"], final_host)
    if not named:
        flags.append("name_absent")
    if landed and landed != start:
        return "moved", "domain_changed", flags
    if f.get("fallback"):          # the stored address fails, a variant of it works: stale but fixable
        return "moved", "stored_host_dead" if f["first_error"].startswith("dns") else "http_dead_https_works", flags
    if item["kind"] == "website" and not named:
        return "unverifiable", "name_absent", flags
    return "ok", "live", flags


def check_email(addr: str) -> dict:
    domain = addr.split("@", 1)[1].lower()
    t = time.monotonic()
    rcode, ans = dns_query(domain, 15)
    res = {"domain": domain, "rcode": rcode, "mx": [], "a_only": False}
    if rcode is None:
        res.update(cls="unverifiable", reason="dns_error", error=str(ans))
    elif rcode == 3:
        res.update(cls="broken", reason="dns_nxdomain")
    elif rcode != 0:
        res.update(cls="unverifiable", reason=f"dns_rcode_{rcode}")
    else:
        mx = sorted((a[1], a[2]) for a in ans if a[0] == "MX")
        res["mx"] = [h for _p, h in mx][:5]
        if mx and all(h in ("", ".") for _p, h in mx):
            res.update(cls="broken", reason="null_mx")
        elif mx:
            res.update(cls="ok", reason="mx")
        else:
            ok, _ = resolve(domain)
            res.update(cls="ok" if ok else "broken", reason="a_record_only" if ok else "no_mail_host", a_only=ok)
    res["elapsed_s"] = round(time.monotonic() - t, 3)
    return res


def mail_provider(mx: list[str]) -> str:
    j = " ".join(mx).lower()
    for key, name in (("outlook.com", "microsoft365"), ("google.com", "google"), ("googlemail", "google"),
                      ("pphosted", "proofpoint"), ("mimecast", "mimecast"), ("barracuda", "barracuda"),
                      ("iphmx", "cisco"), ("messagelabs", "broadcom"), ("secureserver", "godaddy")):
        if key in j:
            return name
    return "self/other" if mx else ""


# --------------------------------------------------------------------------- sampling

def open_ro(path) -> sqlite3.Connection:
    uri = Path(path).resolve().as_uri() + "?mode=ro"
    con = sqlite3.connect(uri, uri=True, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA query_only=ON")
    return con


def parse_quota(spec: str) -> dict[str, int]:
    out = {}
    for part in spec.split(","):
        if "=" in part:
            k, v = part.split("=", 1)
            out[k.strip().lower()] = int(v)
    out.setdefault("*", 2)
    return out


def build_sample(con: sqlite3.Connection, states: list[str], quota: dict[str, int]) -> tuple[list[dict], dict, dict]:
    ph = ",".join("?" * len(states))
    govs = {r["gov_id"]: dict(r) for r in con.execute(
        f"SELECT gov_id, state, name, kind, population, website, wikidata FROM governments WHERE state IN ({ph})", states)}
    contacts = [dict(r) for r in con.execute(
        f"SELECT gov_id, state, question, kind, value, label, source FROM contacts "
        f"WHERE kind IN ('website','page','email','phone') AND state IN ({ph})", states)]

    web: dict[str, dict[str, dict]] = defaultdict(dict)
    for g in govs.values():
        if g["website"] and g["website"].strip():
            web[g["gov_id"]].setdefault(norm_url(g["website"]), {"url": g["website"].strip(), "sources": {"governments.website"},
                                                                 "labels": set()})
    for c in contacts:
        if c["kind"] != "website":
            continue
        url = to_url(c["value"], "http")
        if not url:
            continue
        e = web[c["gov_id"]].setdefault(norm_url(url), {"url": url, "sources": set(), "labels": set()})
        e["sources"].add(c["source"] or "")
        e["labels"].add(c["label"] or "")

    def base(g: dict, stratum: str) -> dict:
        return {"stratum": stratum, "gov_id": g["gov_id"], "state": g["state"], "gov": g["name"], "gov_kind": g["kind"],
                "population": g["population"], "tier": tier_of(g["population"]), "wikidata": g["wikidata"]}

    items: list[dict] = []
    picked: set[str] = set()
    strata = Counter()

    def add_websites(gid: str, stratum: str) -> None:
        if gid in picked or gid not in web:
            return
        picked.add(gid)
        for key, e in sorted(web[gid].items()):
            srcs = sorted(s for s in e["sources"] if s)
            items.append({**base(govs[gid], stratum), "kind": "website", "question": "general",
                          "source": "+".join(srcs), "label": "; ".join(sorted(l for l in e["labels"] if l)) or None,
                          "value": e["url"], "url": e["url"]})
            strata[stratum] += 1

    for st in states:
        q = quota.get(st, quota["*"])
        for tname, _floor in TIERS:
            cands = sorted((gid for gid in web if govs[gid]["state"] == st and tier_of(govs[gid]["population"]) == tname),
                           key=hkey)
            for gid in cands[:q]:
                add_websites(gid, f"{st}/{tname}")

    skipped_personal = 0
    seen_mail: set[str] = set()
    for c in sorted(contacts, key=lambda c: (hkey(c["gov_id"]), c["kind"], c["question"], c["value"])):
        g = govs.get(c["gov_id"])
        if not g or c["kind"] == "website":
            continue
        if c["kind"] == "page":
            url = to_url(c["value"], "https")
            items.append({**base(g, "pages"), "kind": "page", "question": c["question"], "source": c["source"],
                          "label": c["label"], "value": url or "(no URL stored)", "url": url,
                          "stored_as_url": bool(URL_RE.match(c["value"].strip()))})
            strata["pages"] += 1
        elif c["kind"] == "email":
            row_text = f"{c['value']} {c['label'] or ''}"
            for addr in EMAIL_RE.findall(c["value"]):
                if not is_office_mailbox(addr, row_text):
                    skipped_personal += 1
                    continue
                if addr.lower() in seen_mail:
                    continue
                seen_mail.add(addr.lower())
                items.append({**base(g, "emails"), "kind": "email", "question": c["question"], "source": c["source"],
                              "label": c["label"], "value": addr})
                strata["emails"] += 1
        elif c["kind"] == "phone":
            nums = PHONE_RE.findall(c["value"])
            items.append({**base(g, "phones"), "kind": "phone", "question": c["question"], "source": c["source"],
                          "label": c["label"], "value": "; ".join(f"{a}-{e}-{s}" for a, e, s in nums) or "(unparseable)",
                          "numbers": ["".join(n) for n in nums]})
            strata["phones"] += 1
        add_websites(c["gov_id"], "anchor")      # the home page that phones/emails are matched against

    for i, it in enumerate(items):
        it["id"] = hkey(f"{it['gov_id']}|{it['kind']}|{it['question']}|{it['value']}")[:12]
    meta = {"strata": dict(strata), "skipped_personal_mailboxes": skipped_personal,
            "governments": len({i["gov_id"] for i in items})}
    return items, govs, meta


# --------------------------------------------------------------------------- Wikidata (read-only)

def wikidata_p856(fetcher: Fetcher, qids: list[str]) -> tuple[dict, int]:
    out: dict[str, dict] = {}
    sess = requests.Session()
    sess.headers.update({"User-Agent": UA})
    n = 0
    for i in range(0, len(qids), WD_BATCH):
        batch = qids[i:i + WD_BATCH]
        data, err = None, None
        # maxlag=5 first (bot etiquette); when the servers are lagged, wait as told and finally ask without it
        for attempt, maxlag in enumerate(("5", "5", None)):
            fetcher.throttle.wait("wikidata.org")
            n += 1
            params = {"action": "wbgetentities", "ids": "|".join(batch), "props": "claims|labels", "languages": "en",
                      "format": "json"}
            if maxlag:
                params["maxlag"] = maxlag
            try:
                r = sess.get(WIKIDATA_API, timeout=TIMEOUT, params=params)
                body = r.json()
            except (requests.exceptions.RequestException, ValueError) as e:
                err = type(e).__name__
                continue
            if "entities" in body:
                data, err = body["entities"], None
                break
            err = (body.get("error") or {}).get("code", f"http_{r.status_code}")
            if err == "maxlag" and attempt < 2:
                time.sleep(min(10.0, float(r.headers.get("retry-after", 5))))
        if data is None:
            for q in batch:
                out[q] = {"error": err or "no_entities"}
            continue
        for q in batch:
            ent = data.get(q) or next((v for v in data.values() if v.get("redirects", {}).get("from") == q), None)
            if not ent or "missing" in ent:
                out[q] = {"error": "missing"}
                continue
            urls = []
            for c in ent.get("claims", {}).get("P856", []):
                if c.get("rank") == "deprecated":
                    continue
                v = (c.get("mainsnak", {}).get("datavalue") or {}).get("value")
                if isinstance(v, str):
                    urls.append({"url": v, "rank": c.get("rank")})
            urls.sort(key=lambda u: u["rank"] != "preferred")
            out[q] = {"label": ent.get("labels", {}).get("en", {}).get("value"), "p856": urls,
                      "redirected_to": ent.get("id") if ent.get("id") != q else None}
    return out, n


# --------------------------------------------------------------------------- run

def run(args) -> dict:
    t_start = time.monotonic()
    con = open_ro(args.db or config.DB_PATH)
    states = [s.strip().lower() for s in args.states.split(",") if s.strip()]
    items, govs, meta = build_sample(con, states, parse_quota(args.quota))
    if args.plan:
        for it in items:
            print(f"{it['stratum']:10} {it['kind']:7} {it['state']} {it['gov'][:34]:34} {it['value'][:70]}")
        print(meta, len(items))
        return {}
    fetcher = Fetcher(fallback=not args.no_fallback)

    # 1. websites and pages
    web_items = [i for i in items if i["kind"] in ("website", "page")]
    for it in web_items:
        if not it.get("url"):
            it["_fetch"] = {"url": None, "error": "no_url", "requests": 0, "_body": "", "title": "", "hops": []}
    todo = sorted((i for i in web_items if i.get("url")), key=lambda i: hkey(i["id"]))
    def safe_fetch(it: dict) -> dict:
        try:
            return fetcher.fetch(it["url"])
        except Exception as e:          # one odd site must not end the run
            return {"url": it["url"], "error": "other", "detail": type(e).__name__, "requests": 0, "_body": "",
                    "title": "", "hops": []}

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for it, f in zip(todo, pool.map(safe_fetch, todo)):
            it["_fetch"] = f
    bodies: dict[str, list[tuple[str, str]]] = defaultdict(list)     # gov_id -> [(kind, html)]
    for it in web_items:
        f = it["_fetch"]
        cls, reason, flags = classify_web(it, f)
        it["result"] = {"class": cls, "reason": reason, "flags": flags, "status": f.get("status"),
                        "final_url": f.get("final_url"), "final_domain": base_domain(host_of(f.get("final_url") or "")) or None,
                        "start_domain": base_domain(host_of(it.get("url") or "")) or None,
                        "domain_changed": cls == "moved", "title": f.get("title") or None,
                        "hops": f.get("hops", []),
                        "client_redirect": f.get("client_redirect"), "fallback": f.get("fallback"),
                        "first_error": f.get("first_error"), "error": f.get("error"),
                        "requests": f.get("requests", 0), "elapsed_s": f.get("elapsed_s"), "net_s": f.get("net_s"),
                        "wait_s": f.get("wait_s"), "bytes": f.get("bytes")}
        if f.get("_body") and (f.get("status") or 999) < 400:
            bodies[it["gov_id"]].append((it["kind"], f["_body"]))

    # 2. office emails: DNS only
    for it in items:
        if it["kind"] != "email":
            continue
        r = check_email(it["value"])
        sites = [i["result"] for i in web_items if i["gov_id"] == it["gov_id"] and i["kind"] == "website"]
        site_domains = {s["final_domain"] for s in sites if s.get("final_domain")}
        old_domains = {s["start_domain"] for s in sites if s["class"] in ("moved", "broken")} - site_domains
        flags = []
        if base_domain(r["domain"]) in site_domains:
            flags.append("domain_matches_gov_site")
        elif base_domain(r["domain"]) in old_domains:
            flags.append("domain_of_retired_site")       # the website left this domain; mail may follow
        if any(it["value"].lower() in b.lower() for _k, b in bodies.get(it["gov_id"], [])):
            flags.append("on_fetched_official_page")
        it["result"] = {"class": r["cls"], "reason": r["reason"], "flags": flags, "domain": r["domain"],
                        "mx": r["mx"], "mail_provider": mail_provider(r["mx"]), "elapsed_s": r["elapsed_s"],
                        **({"error": r["error"]} if r.get("error") else {})}

    # 3. phones: shape + presence on the government's own home page
    for it in items:
        if it["kind"] != "phone":
            continue
        nums = it.get("numbers") or []
        home = [b for k, b in bodies.get(it["gov_id"], []) if k == "website"]
        other = [b for k, b in bodies.get(it["gov_id"], []) if k == "page"]
        home_nums = set().union(*(phones_in(b) for b in home)) if home else set()
        other_nums = set().union(*(phones_in(b) for b in other)) if other else set()
        per = [{"number": n, "nanp_valid": nanp_valid(n[:3], n[3:6], n[6:]), "on_home_page": n in home_nums,
                "on_other_official_page": n in other_nums} for n in nums]
        if not nums:
            cls, reason = "broken", "unparseable"
        elif not all(p["nanp_valid"] for p in per):
            cls, reason = "broken", "invalid_nanp"
        elif any(p["on_home_page"] for p in per):
            cls, reason = "ok", "on_home_page"
        elif any(p["on_other_official_page"] for p in per):
            cls, reason = "ok", "on_other_official_page"
        elif not home:
            cls, reason = "unverifiable", "home_page_unavailable"
        else:
            cls, reason = "unverifiable", "not_on_home_page"
        it["result"] = {"class": cls, "reason": reason, "flags": [], "numbers": per,
                        "home_page_numbers_found": len(home_nums)}

    # 4. Wikidata P856
    wd_info, wd_requests, wd_extra = {}, 0, 0
    if not args.no_wikidata:
        qids = sorted({m.group(0) for it in items if it.get("wikidata") for m in [re.search(r"Q\d+", it["wikidata"])] if m})
        wd_info, wd_requests = wikidata_p856(fetcher, qids)
        by_gov = defaultdict(list)
        for it in web_items:
            if it["kind"] == "website":
                by_gov[it["gov_id"]].append(it)
        for gid, its in by_gov.items():
            m = re.search(r"Q\d+", its[0].get("wikidata") or "")
            if not m:
                continue
            info = wd_info.get(m.group(0), {})
            wd_domains = [base_domain(host_of(u["url"])) for u in info.get("p856", [])]
            for it in its:
                r = it["result"]
                it["result"]["wikidata"] = {
                    "qid": m.group(0), "label": info.get("label"), "p856": [u["url"] for u in info.get("p856", [])],
                    "error": info.get("error"),
                    "matches_stored": bool(wd_domains) and r["start_domain"] in wd_domains,
                    "matches_live": bool(wd_domains) and r.get("final_domain") in wd_domains}
            # Wikidata names a domain that neither the stored URL nor its live target uses: is it alive?
            known = {d for it in its for d in (it["result"]["start_domain"], it["result"].get("final_domain")) if d}
            fresh = [u["url"] for u in info.get("p856", []) if base_domain(host_of(u["url"])) not in known]
            if fresh:
                wd_extra += 1
                f = fetcher.fetch(fresh[0])
                probe = {"kind": "website", "gov": its[0]["gov"]}
                cls, reason, flags = classify_web(probe, f)
                for it in its:
                    it["result"]["wikidata"]["p856_probe"] = {
                        "url": fresh[0], "class": cls, "reason": reason, "status": f.get("status"),
                        "final_domain": base_domain(host_of(f.get("final_url") or "")) or None, "title": f.get("title") or None}

    for it in items:
        it.pop("_fetch", None)
        it.pop("url", None)

    report = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "tool": "scripts/contacts_check.py",
        "read_only": True,
        "params": {"states": states, "quota": args.quota, "workers": args.workers, "timeout_s": TIMEOUT,
                   "min_interval_per_domain_s": INTERVAL, "user_agent": UA, "fallback": not args.no_fallback,
                   "wikidata": not args.no_wikidata, "salt": SALT},
        "sample": {**meta, "items": len(items)},
        "requests": {"http": sum(fetcher.count.values()), "wikidata_batches": wd_requests,
                     "wikidata_p856_probes": wd_extra, "dns_mx_queries": sum(1 for i in items if i["kind"] == "email"),
                     "max_per_domain": max(fetcher.count.values(), default=0)},
        "elapsed_s": round(time.monotonic() - t_start, 1),
    }
    report["summary"] = summarize(items)
    report["wikidata"] = summarize_wikidata(items)
    report["sweep_estimate"] = sweep_estimate(con, items, report)
    report["items"] = items
    return report


def _rates(c: Counter) -> dict:
    n = sum(c.values())
    ver = c["ok"] + c["moved"] + c["broken"]
    return {"n": n, **{k: c[k] for k in ("ok", "moved", "broken", "unverifiable")},
            "stale_rate": round((c["moved"] + c["broken"]) / n, 3) if n else None,
            "stale_rate_of_verifiable": round((c["moved"] + c["broken"]) / ver, 3) if ver else None,
            "broken_rate_of_verifiable": round(c["broken"] / ver, 3) if ver else None}


def summarize(items: list[dict]) -> dict:
    def group(key):
        g = defaultdict(Counter)
        for it in items:
            g[key(it)][it["result"]["class"]] += 1
        return {k: _rates(v) for k, v in sorted(g.items())}
    reasons = Counter(f"{it['kind']}:{it['result']['class']}:{it['result']['reason']}" for it in items)
    flags = Counter(f"{it['kind']}:{fl}" for it in items for fl in it["result"].get("flags", []))
    web = [it for it in items if it["kind"] in ("website", "page") and it["result"].get("requests")]
    per_gov = defaultdict(set)
    for it in items:
        if it["kind"] == "website":
            per_gov[it["gov_id"]].add(it["result"]["class"])
    gov_level = Counter()
    for classes in per_gov.values():
        if classes == {"ok"}:
            gov_level["all_stored_websites_ok"] += 1
        elif "ok" in classes:
            gov_level["one_ok_one_stale_or_unverifiable"] += 1
        elif "moved" in classes:
            gov_level["only_a_redirect_works"] += 1
        elif "broken" in classes and classes <= {"broken"}:
            gov_level["nothing_works"] += 1
        else:
            gov_level["unverifiable"] += 1
    hard = {"dns_nxdomain", "http_404", "http_410", "hijacked_spam", "parked", "default_or_suspended_page"}
    broken = [it["result"]["reason"] for it in items if it["result"]["class"] == "broken"]
    fb = [it["result"] for it in items if it["kind"] in ("website", "page") and it["result"].get("fallback")]
    return {
        "governments_by_website_state": dict(gov_level),
        "broken_hard": sum(r in hard for r in broken),
        "broken_soft": sum(r not in hard for r in broken),
        "fallbacks": {"tried": len(fb), "answered": sum(r.get("status") is not None for r in fb),
                      "led_to_ok_or_moved": sum(r["class"] in ("ok", "moved") for r in fb)},
        "overall": _rates(Counter(it["result"]["class"] for it in items)),
        "by_kind": group(lambda i: i["kind"]),
        "by_state": group(lambda i: i["state"]),
        "by_tier_websites": {k: v for k, v in group(lambda i: i["tier"] if i["kind"] == "website" else "-").items() if k != "-"},
        "by_source_websites": {k: v for k, v in group(lambda i: i["source"] if i["kind"] == "website" else "-").items() if k != "-"},
        "reasons": dict(reasons.most_common()),
        "flags": dict(flags.most_common()),
        "web_timing": {
            "fetched": len(web),
            "mean_requests": round(statistics.mean(i["result"]["requests"] for i in web), 2) if web else None,
            "mean_elapsed_s": round(statistics.mean(i["result"]["elapsed_s"] for i in web), 2) if web else None,
            "median_elapsed_s": round(statistics.median(i["result"]["elapsed_s"] for i in web), 2) if web else None,
            "mean_net_s": round(statistics.mean(i["result"]["net_s"] for i in web), 2) if web else None,
            "p90_elapsed_s": round(sorted(i["result"]["elapsed_s"] for i in web)[int(0.9 * (len(web) - 1))], 2) if web else None,
        },
    }


def summarize_wikidata(items: list[dict]) -> dict:
    govs = defaultdict(list)
    for it in items:
        if it["kind"] == "website" and it["result"].get("wikidata"):
            govs[it["gov_id"]].append(it)
    out = Counter()
    for its in govs.values():
        wd = its[0]["result"]["wikidata"]
        out["governments_with_qid"] += 1
        if wd.get("error"):
            out[f"error_{wd['error']}"] += 1
            continue
        if not wd["p856"]:
            out["no_p856"] += 1
            continue
        out["has_p856"] += 1
        stored = any(i["result"]["wikidata"]["matches_stored"] for i in its)
        live = any(i["result"]["wikidata"]["matches_live"] for i in its)
        out["p856_matches_a_stored_domain"] += stored
        out["p856_matches_a_live_domain"] += live
        out["p856_matches_neither"] += not (stored or live)
        if any(i["result"]["class"] == "moved" for i in its):
            out["moved_govs"] += 1
            out["moved_and_p856_has_new_domain"] += live
        if any(i["result"]["class"] == "broken" for i in its):
            out["broken_govs"] += 1
            probe = wd.get("p856_probe")
            if probe and probe["class"] in ("ok", "moved"):
                out["broken_but_p856_alive"] += 1
        probe = wd.get("p856_probe")
        if probe:
            out[f"p856_probe_{probe['class']}"] += 1
        census = [i for i in its if "census" in (i["source"] or "")]
        wdsrc = [i for i in its if "wikidata" in (i["source"] or "")]
        if census and wdsrc and census[0]["value"] != wdsrc[0]["value"]:
            out["census_and_wikidata_rows_differ"] += 1
    return dict(out)


def sweep_estimate(con: sqlite3.Connection, items: list[dict], report: dict) -> dict:
    urls: set[str] = set()
    for (w,) in con.execute("SELECT website FROM governments WHERE website IS NOT NULL AND trim(website) != ''"):
        u = to_url(w, "http")
        if u:
            urls.add(norm_url(u))
    pages_no_url = 0
    for kind, v in con.execute("SELECT kind, value FROM contacts WHERE kind IN ('website','page')"):
        u = to_url(v, "http" if kind == "website" else "https")
        if u:
            urls.add(norm_url(u))
        else:
            pages_no_url += 1
    per_domain = Counter(base_domain(u.split("/", 1)[0]) for u in urls)
    n_email_rows = con.execute("SELECT count(*) FROM contacts WHERE kind='email'").fetchone()[0]
    n_phone_rows = con.execute("SELECT count(*) FROM contacts WHERE kind='phone'").fetchone()[0]
    n_qids = con.execute("SELECT count(DISTINCT wikidata) FROM governments WHERE wikidata IS NOT NULL AND wikidata != ''").fetchone()[0]
    t = report["summary"]["web_timing"]
    mean_s, mean_req = t["mean_elapsed_s"] or 3.0, t["mean_requests"] or 1.5
    n = len(urls)
    serial_s = n * mean_s
    floor_s = per_domain.most_common(1)[0][1] * mean_req * INTERVAL if per_domain else 0
    est = {"distinct_urls": n, "distinct_domains": len(per_domain),
           "busiest_domains": per_domain.most_common(5),
           "page_rows_without_url": pages_no_url, "email_rows": n_email_rows, "phone_rows": n_phone_rows,
           "wikidata_qids": n_qids, "wikidata_batches": math.ceil(n_qids / WD_BATCH),
           "assumed_mean_s_per_url": mean_s, "assumed_requests_per_url": mean_req,
           "http_requests": round(n * mean_req),
           "per_domain_floor_h": round(floor_s / 3600, 2)}
    for w in (1, 4, 8, 16):
        est[f"hours_with_{w}_workers"] = round(max(serial_s / w, floor_s) / 3600, 2)
    return est


def print_report(rep: dict) -> None:
    s = rep["summary"]
    o = s["overall"]
    print(f"\nContact freshness pilot: {rep['sample']['items']} contacts, {rep['sample']['governments']} governments, "
          f"{rep['requests']['http']} HTTP requests, {rep['elapsed_s']} s")
    print(f"  strata: {rep['sample']['strata']}  (personal mailboxes skipped: {rep['sample']['skipped_personal_mailboxes']})")
    print(f"  overall: ok {o['ok']}  moved {o['moved']}  broken {o['broken']}  unverifiable {o['unverifiable']}  "
          f"stale {o['stale_rate']:.0%} of all, {o['stale_rate_of_verifiable']:.0%} of verifiable")
    for title, key in (("by kind", "by_kind"), ("by state", "by_state"), ("websites by tier", "by_tier_websites"),
                       ("websites by source", "by_source_websites")):
        print(f"  {title}:")
        for k, v in s[key].items():
            sr = "-" if v["stale_rate_of_verifiable"] is None else f"{v['stale_rate_of_verifiable']:.0%}"
            print(f"    {k:28} n={v['n']:3}  ok {v['ok']:2}  moved {v['moved']:2}  broken {v['broken']:2}  "
                  f"unverif {v['unverifiable']:2}  stale/verifiable {sr}")
    print(f"  broken: hard {s['broken_hard']}, soft {s['broken_soft']};  fallbacks {s['fallbacks']}")
    print("  governments by website state:", s["governments_by_website_state"])
    print("  reasons:", s["reasons"])
    print("  flags:", s["flags"])
    print("  web timing:", s["web_timing"])
    print("  wikidata:", rep["wikidata"])
    print("  full sweep estimate:", {k: v for k, v in rep["sweep_estimate"].items() if k != "busiest_domains"})
    print("  busiest domains:", rep["sweep_estimate"]["busiest_domains"])
    print("\n  not ok:")
    for it in rep["items"]:
        r = it["result"]
        if r["class"] == "ok":
            continue
        extra = ""
        if it["kind"] in ("website", "page"):
            extra = f"{r.get('status')} -> {r.get('final_domain')} | {(r.get('title') or '')[:60]}"
            wd = r.get("wikidata")
            if wd:
                extra += f" | WD {','.join(wd['p856'])[:60]}"
                if wd.get("p856_probe"):
                    extra += f" ({wd['p856_probe']['class']})"
        elif it["kind"] == "email":
            extra = r.get("domain", "")
        print(f"    {r['class']:12} {r['reason']:24} {it['kind']:7} {it['state']} {it['gov'][:30]:30} {it['value'][:55]} {extra}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("out", nargs="?", help="where to write the JSON results")
    ap.add_argument("--db", help="SQLite store (default: lexflow config DB_PATH); opened read-only")
    ap.add_argument("--states", default=DEFAULT_STATES)
    ap.add_argument("--quota", default=DEFAULT_QUOTA, help="websites per population tier per state, e.g. va=4,*=2")
    ap.add_argument("--workers", type=int, default=6, help="concurrent fetches (each domain still 1 req/s)")
    ap.add_argument("--no-wikidata", action="store_true")
    ap.add_argument("--no-fallback", action="store_true", help="do not retry https:// or a www. toggle on failure")
    ap.add_argument("--plan", action="store_true", help="print the sample and exit without network access")
    args = ap.parse_args(argv)
    if not args.plan and not args.out:
        ap.error("OUT.json is required unless --plan")
    rep = run(args)
    if args.plan:
        return 0
    print_report(rep)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rep, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
