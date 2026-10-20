"""lexflow's software match of a researched local process's quotes against the pages and PDFs they cite, and the
quote policy for the sites whose terms forbid reprinting their words.

A researched process file (``curated/places/<state>/<place>/<process>.json``) quotes two kinds of source.  Quotes
from the state code are matched to Open US Law's copy of the statute text (``places.check_quotes``).  The rest
quote web pages and PDFs: the place's own pages and forms, other agencies' pages, ordinances on Legistar and the
like.  Those are matched here, against the page each quote cites (``cited_urls``); a quote that cites no page, or
whose page does not have it, is looked for in the other pages the file cites (``file_urls``).

**Fetching** (``fetch``) is its own step (``python -m lexflow.municipal.quotes --fetch``).  Loading the files only
reads what it cached, so a load never goes to the network.  It uses the project's polite reader
(``payroll.sources.Http``): GET only, the lexflow-research User-Agent, robots.txt obeyed, at least 1.5 seconds
between two requests to one host, no form posts, and nothing behind a login (a 401 or a redirect to a sign-in page
is not read).  Where the live host refuses automated clients (HTTP 403 or 429 for the page or its robots.txt, or a
bot-challenge page instead of content), or the page is gone or failing (404, 410, 5xx, no connection), the newest
Internet Archive capture with HTTP 200 is read instead, and its timestamp is kept.  A web.archive.org address that
a file cites is read as that capture.  No browser is used.  Each page's text is cached under
``<LEXFLOW_DATA>/cache/quote_pages`` with the date it was fetched and whether it was live or an archive capture, so
a re-run does not fetch it again.  Internet Archive downloads are slow, so a few readers overlap them, on one clock
per host: requests to one host still start at least its interval apart.  For a site in ``NO_REPRINT`` the cache
keeps no words: only which of the files' quotes the page held when it was read.

**Matching** (``match``): text from HTML (scripts and styles dropped, block elements on lines of their own), PDF
(``pdftotext`` in reading order, raw, layout and table passes, else ``pypdf``; also with line-end hyphens joined),
Word (.docx: as it stands and, for a redlined ordinance, in its adopted reading with struck text dropped) and JSON
(every string, as the Legistar and CivicClerk APIs give them); whitespace, curly quotes, non-breaking and
zero-width spaces, soft hyphens and ligatures normalised; then ``validate.quote_in``, the check every state model's
quotes pass.

**Quote policy** (``NO_REPRINT``): some sites' terms forbid reposting their content without permission.  Their
pages are cited and linked, and their words stay in the files as the evidence the match is made against, but a
wiki page prints lexflow's own short paraphrase and the link instead, and says why (``reprint_note``).
"""
from __future__ import annotations

import hashlib
import io
import json
import queue
import re
import shutil
import subprocess
import tempfile
import threading
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable
from urllib.parse import urljoin, urlsplit

from .. import config

Log = Callable[[str], None]

MIN_INTERVAL = 1.5              # seconds between two requests to one host, at least
ARCHIVE_INTERVAL = 5.0          # the Internet Archive answers 503 to more than about a dozen requests a minute
BUSY_WAIT = 60.0                # seconds to wait when the Internet Archive answers 503 or 429 all the same
TIMEOUT = 40                    # seconds per request (PDFs and the Internet Archive are slow)
MAX_BYTES = 150_000_000         # read no more of one response than this (a city's development code PDF is ~45 MB)
ARCHIVE = "web.archive.org"
CDX = "https://web.archive.org/cdx/search/cdx"
CAPTURES = 6                    # the newest captures tried, newest first, when one is a bot challenge
REFUSED = (403, 429)            # the host refuses automated clients: read an Internet Archive capture instead
UNAVAILABLE = (404, 410)        # gone: read an Internet Archive capture instead
LOGIN = re.compile(r"/(?:log-?in|sign-?in|signon|sso|oauth2?|account/log-?in|users?/sign_in)(?:\b|/|$)", re.I)
WAYBACK = re.compile(r"https?://web\.archive\.org/web/(\d{4,14})(?:[a-z]{2}_|\*)?/(.+)$", re.I)
# a bot check or block page in place of the content (Cloudflare, Akamai, Imperva and the like)
CHALLENGE = re.compile(r"Just a moment\.\.\.|cf-browser-verification|challenge-platform|Attention Required! \| "
                       r"Cloudflare|Access Denied.{0,200}Reference #|Pardon Our Interruption|Request unsuccessful\. "
                       r"Incapsula|Please enable JS and disable any ad blocker|bot-?detection|captcha-delivery",
                       re.I | re.S)

# ---- the quote policy -----------------------------------------------------------------------------------------
# Sites whose terms forbid reposting their pages' content without permission.  Their pages are cited and linked
# and their words are matched, but a page prints lexflow's paraphrase and the link instead of the words.  ``fetch``
# False: lexflow never fetches the site (docs/design/credits-research.md: Municode is link-only).
NO_REPRINT: dict[str, dict] = {
    "library.municode.com": {
        "site": "Municode Library", "publisher": "Municode (CivicPlus)", "fetch": False,
        "terms": "https://www.municode.com/code/page/terms-use",
        "reason": "Municode's terms of use forbid republishing the codes it hosts, so lexflow links to them and "
                  "never copies their text"},
    "ecode360.com": {
        "site": "eCode360", "publisher": "General Code", "fetch": True,
        "terms": "https://ecode360.com/docs/TOS.html",
        "reason": "General Code's Terms and Conditions of Use limit eCode360's content to personal use and forbid "
                  "reproducing or republishing it for public purposes"},
    "albemarle.org": {
        "site": "albemarle.org", "publisher": "Albemarle County", "fetch": True,
        "terms": "https://www.albemarle.org/government/terms-and-conditions",
        "reason": "Albemarle County's Terms and Conditions allow browsing its site for information but forbid "
                  "reposting its content without the County's written permission"},
}


def original(url: str) -> str:
    """The page an Internet Archive address is a capture of (the address itself otherwise)."""
    m = WAYBACK.match(url or "")
    if not m:
        return url
    return m.group(2) if re.match(r"https?://", m.group(2), re.I) else "http://" + m.group(2)


def capture_of(url: str) -> str | None:
    """The capture timestamp in an Internet Archive address, or None."""
    m = WAYBACK.match(url or "")
    return m.group(1) if m else None


def host_of(url: str) -> str:
    return (urlsplit(original(url)).hostname or "").lower()


def policy(url: str | None) -> dict | None:
    """The quote policy for the site a page (or an Internet Archive copy of it) belongs to, or None."""
    host = host_of(url or "")
    for h, p in NO_REPRINT.items():
        if host == h or host.endswith("." + h):
            return dict(p, host=h)
    return None


def reprint_note(url: str | dict | None) -> str | None:
    """Why a page prints a paraphrase and the link instead of a quote from ``url``'s site (or for a policy from
    ``withheld``), or None when it may quote it."""
    p = url if isinstance(url, dict) else policy(url)
    return f"{p['publisher']}'s words are not reprinted here: {p['reason']}" if p else None


def withheld(item: dict | None, cites: Iterable[str] = ()) -> dict | None:
    """The ``NO_REPRINT`` policy that keeps a researched quote's words off a page, or None when the page may print
    them.  ``item`` is the quote's match (``places.check_quotes``), ``cites`` its citation fields.  A quote matched to
    the state code, or on a page of a site that allows it, is printed; one matched on a page of a site in
    ``NO_REPRINT`` (or an Internet Archive copy of one) is not; and one that did not match is not printed when any
    page it cites is on such a site, since its words may be that site's."""
    item = item or {}
    if item.get("by") == "code":
        return None
    if item.get("by"):
        return policy(item.get("url"))
    for u in [item.get("url")] + cited_urls(cites):
        p = policy(u) if u else None
        if p:
            return p
    return None


def method_label() -> str:
    """lexflow:method's sentence on what the label of a researched local process says (for its list of the three
    facts every page opens with)."""
    return ("A researched local process gives one count, made by lexflow's software: how many of its quotes it found "
            "word for word, how many of those in Open US Law's copy of the Code of Virginia or the D.C. Code and how "
            "many in the pages they cite (and of those, how many in Internet Archive copies), and on what dates. A "
            "quote it did not find is listed on the page as not matched, and the process is then not published as "
            "checked. An AI verifier also checked these files before they were loaded, but no page gives an AI "
            "system's count.")


def method_check() -> str:
    """lexflow:method's sentence on how the quotes of a researched local process are matched (for "What the machine
    checks do")."""
    return ("On a researched local process, lexflow's software matches every quote, spacing and curly quotation marks "
            "aside: one that cites a section of the Code of Virginia or the D.C. Code to Open US Law's copy of that "
            "section, with the same check (it reads no other state's citations yet); any other to the page or PDF it "
            "cites, or failing that to another page the process cites. An ordinance published as a redline is matched "
            "as adopted, with its struck text dropped. Those pages are fetched read-only, with robots.txt obeyed, at "
            "least 1.5 seconds apart on one site, never through a form or a login, and never in a browser. Where a "
            "site refuses automated readers, or the page is gone, the newest Internet Archive copy is read instead, "
            "and the page says how many quotes were matched that way and on what dates. A scanned page with no text "
            "layer cannot be matched. A process is published as checked only when every one of its quotes matched, "
            "an AI verifier passed it, and either that check or lexflow's match was made on or after the day each of "
            "its sources was retrieved.")


def method_policy() -> str:
    """lexflow:method's sentence on the sites whose words are cited and linked but not reprinted, with the reason
    and the terms page for each (``NO_REPRINT``)."""
    hosts = "; ".join(f"[[{p['terms']}|{p['site']}]]: {p['reason']}" for p in NO_REPRINT.values())
    unread = [p["site"] for p in NO_REPRINT.values() if not p["fetch"]]
    return ("Some sites' terms forbid reposting their content. Their pages are cited and linked, and lexflow's software "
            "matches their words where it reads them (lexflow keeps no copy of those words, only which quotes each "
            "page held" + (f"; it never reads {' or '.join(unread)}, so quotes from there stay not matched" if unread
                           else "") + "), but the pages here give lexflow's own short paraphrase and the link instead "
            "of the quote, and say why. They are " + hosts + ".")


def method_lines() -> list[str]:
    """The three sentences above, for a page that prints them together."""
    return [method_label(), method_check(), method_policy()]


# ---- which pages a quote cites ---------------------------------------------------------------------------------
URL = re.compile(r"https?://[^\s<>\"'\]]+")


def _trim(u: str) -> str:
    u = u.rstrip(".,;:'\"")
    while u.endswith(")") and u.count(")") > u.count("("):
        u = u[:-1].rstrip(".,;:'\"")
    return u


def cited_urls(cites: Iterable[str]) -> list[str]:
    """The web addresses a quote's citation fields give: a field that is one address, else each address in it."""
    out: list[str] = []
    for c in cites or []:
        c = str(c or "").strip()
        found = [c] if re.fullmatch(r"https?://\S+", c) else [_trim(u) for u in URL.findall(c)]
        out += [u for u in found if u and u not in out]
    return out


def file_urls(spec: dict) -> list[str]:
    """Every page a process file cites: its sources, then the addresses of its law, steps, forms and contacts."""
    out: list[str] = []
    for x in spec.get("sources") or []:
        if isinstance(x, dict):
            out += [u for u in cited_urls([x.get("url")]) if u not in out]
    for k in ("legal_basis", "steps", "forms", "contacts", "fees", "escalation"):
        for x in spec.get(k) or []:
            if isinstance(x, dict):
                out += [u for u in cited_urls([x.get("url"), x.get("source"), x.get("basis")]) if u not in out]
    return out


def key(url: str) -> str:
    """The address a page is fetched and cached by: without its #fragment."""
    return (url or "").split("#", 1)[0].strip()


# ---- text ------------------------------------------------------------------------------------------------------
_TRANS = str.maketrans({
    "‘": "'", "’": "'", "‚": "'", "‛": "'", "′": "'", "´": "'",
    "“": '"', "”": '"', "„": '"', "‟": '"', "″": '"', "«": '"', "»": '"',
    " ": " ", " ": " ", " ": " ", " ": " ", " ": " ", " ": " ", " ": " ",
    "　": " ", "­": None, "​": None, "‌": None, "‍": None, "⁠": None, "﻿": None,
    "ﬀ": "ff", "ﬁ": "fi", "ﬂ": "fl", "ﬃ": "ffi", "ﬄ": "ffl"})


def norm(text: str | None) -> str:
    """Text as the matcher compares it: curly quotation marks straight, odd spaces as spaces, invisible characters
    and soft hyphens dropped, ligatures spelt out, whitespace runs as one space."""
    return re.sub(r"\s+", " ", str(text or "").translate(_TRANS)).strip()


# a PDF page break (form feed) with the page number printed beside it, as a footer before it or a header after it
PAGE_BREAK = re.compile(r"(?:\r?\n[ \t]*(?:Page[ \t]+)?\d{1,4}(?:[ \t]+of[ \t]+\d{1,4})?[ \t]*)?(?:\r?\n[ \t]*)*\f"
                        r"[ \t]*(?:(?:Page[ \t]+)?\d{1,4}(?:[ \t]+of[ \t]+\d{1,4})?[ \t]*\r?\n)?", re.I)


def variants(raw: str | None) -> list[str]:
    """A page's text as matched: as extracted; with words broken by a line-end hyphen joined again (PDFs); and with
    the page numbers at a PDF page break dropped, so a sentence that runs on to the next page reads whole."""
    raw = str(raw or "")
    joined = re.sub(r"(\w)-[ \t]*\r?\n[ \t\f]*(\w)", r"\1\2", raw)
    paged = PAGE_BREAK.sub("\n", joined) if "\f" in joined else joined
    out = []
    for t in (raw, joined, paged):
        if t not in out:
            out.append(t)
    return [norm(t) for t in out]


def _plain_quote_in(quote: str, text: str) -> bool:
    """validate.quote_in as it is written there, for a fetch run where validate cannot be imported (it needs
    pydantic); tests/test_place_processes.py checks that the two agree."""
    def n(s):
        return re.sub(r"\s+", " ", s.replace("’", "'")).strip()
    return bool(quote) and n(quote) in n(text or "")


def _quote_in():
    try:
        from ..validate import quote_in
        return quote_in
    except ImportError:
        return _plain_quote_in


def match(quote: str, text: str | list[str] | None) -> bool:
    """Whether ``quote`` is in a page's text word for word, with the state models' check (validate.quote_in) on
    both normalised (``norm``)."""
    quote_in = _quote_in()
    q = norm(quote)
    texts = text if isinstance(text, list) else variants(text)
    return bool(q) and any(quote_in(q, t) for t in texts)


def qhash(quote: str) -> str:
    """A quote's fingerprint in the cache of a page whose words are not kept (``NO_REPRINT``)."""
    return hashlib.sha256(norm(quote).encode("utf-8")).hexdigest()[:24]


BLOCK = {"p", "div", "li", "ul", "ol", "td", "th", "tr", "table", "tbody", "thead", "tfoot", "h1", "h2", "h3", "h4",
         "h5", "h6", "br", "section", "article", "header", "footer", "nav", "aside", "main", "dt", "dd", "dl",
         "blockquote", "pre", "option", "select", "form", "fieldset", "legend", "label", "figure", "figcaption",
         "address", "hr", "caption", "summary", "details", "title", "button", "img"}


def html_text(data: bytes | str, encoding: str | None = None) -> str:
    """The visible text of an HTML page (and its title and description), block elements on lines of their own."""
    import lxml.html
    from lxml import etree
    if isinstance(data, bytes):
        text = None
        for enc in [e for e in (encoding, "utf-8") if e]:
            try:
                text = data.decode(enc)
                break
            except (UnicodeDecodeError, LookupError):
                continue
        data = text if text is not None else data
    if isinstance(data, str):
        data = re.sub(r"^\s*<\?xml[^>]*\?>", "", data)
    if not data or not str(data).strip():
        return ""
    try:
        doc = lxml.html.document_fromstring(data)
    except (etree.ParserError, ValueError):
        return ""
    for bad in doc.xpath("//script|//style|//noscript|//template|//svg|//comment()"):
        parent = bad.getparent()
        if parent is None:
            continue
        prev, tail = bad.getprevious(), bad.tail or ""
        parent.remove(bad)                                   # the text that followed it stays where it was
        if prev is not None:
            prev.tail = (prev.tail or "") + tail
        else:
            parent.text = (parent.text or "") + tail
    for el in doc.iter():
        if isinstance(el.tag, str) and el.tag.lower() in BLOCK:
            if el.tag.lower() == "img" and el.get("alt"):
                el.text = el.get("alt")
            el.text = "\n" + (el.text or "")
            el.tail = "\n" + (el.tail or "")
    meta = [m.get("content") for m in doc.xpath("//meta[@name='description' or @property='og:description']")
            if m.get("content")]
    return "\n".join(meta + [doc.text_content()])


def pdf_text(data: bytes) -> str | None:
    """A PDF's text layer: pdftotext in reading order, in content-stream order (-raw), with its layout kept and,
    where the tool has it (xpdf), as a table, so a table row or a column reads as it does in one of them; else
    pypdf.  None when neither is installed or the file has no text layer."""
    exe = shutil.which("pdftotext")
    outs = []
    if exe:
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "page.pdf"
            p.write_bytes(data)
            for flags in ([], ["-raw"], ["-layout"], ["-table"]):
                try:
                    r = subprocess.run([exe, *flags, "-enc", "UTF-8", str(p), "-"], capture_output=True, timeout=180)
                except (OSError, subprocess.SubprocessError):
                    continue
                if r.returncode == 0:
                    outs.append(r.stdout.decode("utf-8", "replace"))
    if not outs:
        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(data))
            outs.append("\n".join(page.extract_text() or "" for page in reader.pages))
        except Exception:                                          # noqa: BLE001 - no pypdf, or a broken file
            return None
    text = "\n\f\n".join(outs)
    return text if text.strip() else None


W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def _struck(el) -> bool:
    """Whether a Word text run is struck through, hidden, or a tracked deletion: text a redline drops."""
    node = el.getparent()
    while node is not None and node.tag != f"{W_NS}p":
        if node.tag in (f"{W_NS}del", f"{W_NS}moveFrom"):
            return True
        if node.tag == f"{W_NS}r":
            rpr = node.find(f"{W_NS}rPr")
            for tag in ("strike", "dstrike", "vanish"):
                x = rpr.find(f"{W_NS}{tag}") if rpr is not None else None
                if x is not None and (x.get(f"{W_NS}val") or "true").lower() not in ("false", "0", "off", "none"):
                    return True
        node = node.getparent()
    return False


def docx_text(data: bytes) -> str | None:
    """A Word file's paragraphs, one a line.  An ordinance on Legistar is often a redline (struck text to go,
    underlined text to come in): its text is then given twice, as it stands and in its adopted reading (struck,
    hidden and deleted text dropped), so that a quote of the ordinance as adopted matches."""
    from lxml import etree
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            xml = z.read("word/document.xml")
        root = etree.fromstring(xml)
    except (KeyError, zipfile.BadZipFile, etree.XMLSyntaxError):
        return None
    w = W_NS
    paras, adopted = [], []
    for p in root.iter(f"{w}p"):
        parts, kept = [], []
        for el in p.iter():
            if el.tag == f"{w}t":
                parts.append(el.text or "")
                if not _struck(el):
                    kept.append(el.text or "")
            elif el.tag == f"{w}tab":
                parts.append(" ")
                kept.append(" ")
            elif el.tag in (f"{w}br", f"{w}cr"):
                parts.append("\n")
                kept.append("\n")
        paras.append("".join(parts))
        adopted.append("".join(kept))
    text, reading = "\n".join(paras), "\n".join(adopted)
    return text if reading == text else f"{text}\n\f\n{reading}"


def json_text(value) -> str:
    """Every string in a JSON reply (HTML in one read as text), one a line."""
    out: list[str] = []

    def walk(v):
        if isinstance(v, dict):
            for x in v.values():
                walk(x)
        elif isinstance(v, list):
            for x in v:
                walk(x)
        elif isinstance(v, str) and v.strip() and not v.lstrip().startswith("{\\rtf"):
            out.append(html_text(v) if re.search(r"<(?:p|div|br|span|li|table|td)\b", v, re.I) else v)
    walk(value)
    return "\n".join(out)


def extract(data: bytes, ctype: str = "") -> tuple[str, str | None]:
    """(kind, text) of a fetched body: pdf, docx, json, text or html."""
    head = data[:1024]
    ctype = (ctype or "").lower()
    if b"%PDF" in head or "pdf" in ctype:
        return "pdf", pdf_text(data)
    if head.startswith(b"PK\x03\x04"):
        return "docx", docx_text(data)
    if "json" in ctype or head.lstrip()[:1] in (b"{", b"["):
        try:
            return "json", json_text(json.loads(data.decode("utf-8", "replace")))
        except ValueError:
            pass
    enc = re.search(r"charset=([\w.-]+)", ctype)
    if "text/plain" in ctype:
        return "text", data.decode(enc.group(1) if enc else "utf-8", "replace")
    return "html", html_text(data, enc.group(1) if enc else None)


# ---- the cache -------------------------------------------------------------------------------------------------
def cache_dir() -> Path:
    return config.DATA_DIR / "cache" / "quote_pages"


def _path(url: str) -> Path:
    return cache_dir() / f"{hashlib.sha256(key(url).encode('utf-8')).hexdigest()[:32]}.json"


_MEMO: dict[str, tuple[float, dict]] = {}
_LOCK = threading.Lock()


def cached(url: str) -> dict | None:
    """What lexflow's fetch read for ``url`` (``fetch``), or None when it has not been read."""
    p = _path(url)
    try:
        mtime = p.stat().st_mtime
    except OSError:
        return None
    hit = _MEMO.get(str(p))
    if hit and hit[0] == mtime:
        return hit[1]
    try:
        entry = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if entry.get("text") is not None:
        entry["_texts"] = variants(entry["text"])
    _MEMO[str(p)] = (mtime, entry)
    return entry


def _save(entry: dict) -> None:
    p = _path(entry["url"])
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".part")
    tmp.write_text(json.dumps({k: v for k, v in entry.items() if not k.startswith("_")}, ensure_ascii=False),
                   encoding="utf-8")
    tmp.replace(p)


def has(entry: dict | None, quote: str) -> bool | None:
    """Whether a cached page holds ``quote`` word for word: True, False, or None when it cannot be told (the page
    was not read, or its words are not kept and this quote was not checked when it was read)."""
    if not entry or entry.get("error"):
        return None
    if entry.get("_texts") is not None:
        return match(quote, entry["_texts"])
    if entry.get("text") is not None:
        return match(quote, entry["text"])
    h = qhash(quote)
    if h in set(entry.get("found") or []):
        return True
    return False if h in set(entry.get("checked") or []) else None


def describe(entry: dict | None) -> str:
    """How a page was read, in a reader's words: 'the cited page as read on 11 October 2026' or 'an Internet
    Archive copy of 14 August 2026 of the cited page, read on 11 October 2026'."""
    from ..signoff import long_date
    if not entry:
        return "the cited page, which lexflow's software has not read"
    when = long_date(entry.get("fetched")) or entry.get("fetched") or "an unrecorded date"
    if entry.get("via") == "archive":
        ts = str(entry.get("capture") or "")
        cap = long_date(f"{ts[:4]}-{ts[4:6]}-{ts[6:8]}") if len(ts) >= 8 else None
        return f"the Internet Archive copy{' of ' + cap if cap else ''} of the cited page, read on {when}"
    return f"the cited page as read on {when}"


# ---- fetching --------------------------------------------------------------------------------------------------
def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _clock() -> dict:
    """One fetch run's per-host clock, shared by all its readers, so that two threads never send two requests to
    one host less than its interval apart."""
    return {"lock": threading.Lock(), "locks": {}, "last": {}, "gap": {}}


def _http(log: Log, sleep: Callable[[float], None] | None = None, shared: dict | None = None):
    """The project's polite reader with lexflow-research's User-Agent, 1.5 s per host, and redirects followed to
    any host (each hop checked against that host's robots.txt), never from https to http or to a sign-in page.
    ``shared`` (``_clock``) is the run's per-host clock, when several readers work at once."""
    from ..payroll import sources as SRC

    class Http(SRC.Http):
        def _wait(self, host):
            if shared is None:
                return super()._wait(host)
            with shared["lock"]:
                lock = shared["locks"].setdefault(host, threading.Lock())
            with lock:                                             # wait, then stamp the request, as one step
                return super()._wait(host)

        def _next_hop(self, url, r, hosts):                       # noqa: ARG002 - any host, each hop checked
            loc = r.headers.get("Location")
            r.close()
            if not loc:
                return None, f"{url} redirected without a Location"
            nxt = urljoin(url, loc)
            if urlsplit(url).scheme == "https" and urlsplit(nxt).scheme != "https":
                return None, f"redirect from {url} to {nxt} refused: it leaves https"
            if LOGIN.search(urlsplit(nxt).path or ""):
                return None, f"{url} redirects to a sign-in page ({nxt}); not read"
            return nxt, None

    import time
    http = Http(min_interval=MIN_INTERVAL, timeout=TIMEOUT, log=log, sleep=sleep or time.sleep)
    if shared is not None:
        http._last, http._gap = shared["last"], shared["gap"]     # one clock, and one Crawl-delay, per host
    http._gap[ARCHIVE] = ARCHIVE_INTERVAL
    return http


def _read(http, url: str, params: dict | None = None) -> tuple[int, str, str, bytes]:
    r = http.get(url, params=params, stream=True)
    try:
        chunks, size = [], 0
        for chunk in r.iter_content(1 << 16):
            chunks.append(chunk)
            size += len(chunk)
            if size >= MAX_BYTES:
                break
        return r.status_code, r.url, r.headers.get("Content-Type") or "", b"".join(chunks)
    finally:
        r.close()


def _body(entry: dict, data: bytes, ctype: str, quotes: list[str], keep: bool = False) -> dict:
    """Fill ``entry`` with a page's text, or for a NO_REPRINT site only the fingerprints of the quotes it holds
    (``keep`` True keeps the words in the entry for the evidence rebuild, which never saves it to the cache)."""
    if len(data) >= MAX_BYTES:
        return dict(entry, bytes=len(data), error=f"larger than {MAX_BYTES // 1_000_000} MB, so not read in full")
    kind, text = extract(data, ctype)
    entry.update(type=kind, bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
    if text is None or not text.strip():
        entry["error"] = ("the PDF has no text layer lexflow can read" if kind == "pdf"
                          else f"no text in the {kind} reply")
        return entry
    if CHALLENGE.search(text[:5000]) and len(norm(text)) < 6000:
        entry["error"] = "a bot-check page instead of the content"
        entry["challenge"] = True
        return entry
    if policy(entry["url"]) and not keep:
        texts = variants(text)
        entry["checked"] = sorted({qhash(q) for q in quotes})
        entry["found"] = sorted({qhash(q) for q in quotes if match(q, texts)})
        entry["chars"] = len(text)
    else:
        entry["text"] = text
    return entry


def _live(http, url: str, quotes: list[str], keep: bool = False) -> tuple[dict | None, str | None]:
    """(entry, None) when the live page was read; (None, why) when an archive capture should be tried instead;
    (entry with an error, None) when it may not be read at all."""
    import requests
    base = {"url": key(url), "via": "live", "fetched": _today(), "at": _now(), "capture": None}
    try:
        status, final, ctype, data = _read(http, key(url))
    except PermissionError as e:
        why = str(e)
        host = urlsplit(key(url)).netloc.lower()
        if host in getattr(http, "_why", {}):                      # robots.txt answered 401/403/429/5xx: refused
            return None, why
        return dict(base, via=None, error=why), None               # robots.txt disallows it, or a sign-in page
    except requests.HTTPError as e:
        code = e.response.status_code if e.response is not None else 0
        if code == 401:
            return dict(base, via=None, status=code, error="behind a login (HTTP 401); not read"), None
        return None, f"HTTP {code}"
    except requests.RequestException as e:
        return None, f"no answer ({type(e).__name__})"
    if LOGIN.search(urlsplit(final).path or ""):
        return dict(base, via=None, error="behind a login; not read"), None
    entry = _body(dict(base, status=status, fetched_url=final), data, ctype, quotes, keep)
    if entry.get("challenge"):
        return None, "a bot-check page instead of the content"
    return entry, None


def _capture(http, ts: str, orig_url: str, base: dict, quotes: list[str],
             keep: bool = False) -> tuple[dict | None, str | None]:
    """(entry, None) for a usable Internet Archive capture (the one at or nearest before ``ts``: the archive
    redirects to it), or (None, why not)."""
    import requests
    cap = f"https://{ARCHIVE}/web/{ts}id_/{orig_url}"
    for attempt in range(3):
        try:
            status, final, ctype, data = _read(http, cap)
            break
        except (requests.RequestException, PermissionError) as e:
            code = getattr(getattr(e, "response", None), "status_code", None)
            if (code in (429, 503) or isinstance(e, (requests.Timeout, requests.ConnectionError))) and attempt < 2:
                http.log(f"the Internet Archive is busy; waiting {BUSY_WAIT:.0f} s")
                http.sleep(BUSY_WAIT)
                continue
            return None, (f"the Internet Archive copy could not be read "
                          f"({f'HTTP {code}' if code else type(e).__name__})")
    got = capture_of(final) or ts
    entry = _body(dict(base, status=status, fetched_url=final, capture=got), data, ctype, quotes, keep)
    if entry.get("challenge"):
        return None, f"the Internet Archive copy {got} holds a bot-check page"
    if entry.get("error"):
        return None, entry["error"]
    return entry, None


def _archive(http, url: str, quotes: list[str], live_error: str | None, log: Log, keep: bool = False) -> dict:
    """The newest Internet Archive capture of ``url`` that is not an error or a bot-check page (or the capture an
    archive address names).  The newest is asked for by a timestamp of today, which the archive redirects to its
    latest capture; only when that one is unusable is the archive's index (CDX) asked for the older captures with
    HTTP 200, newest first."""
    import requests
    orig, want = original(key(url)), capture_of(url)
    base = {"url": key(url), "via": "archive", "fetched": _today(), "at": _now(), "live_error": live_error}
    first = want or datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    entry, why = _capture(http, first, orig, base, quotes, keep)
    if entry:
        return entry
    tried, rows = {first}, None
    for attempt in range(3):
        try:
            rows = http.get(CDX, params={"url": orig, "output": "json", "fl": "timestamp,original",
                                         "filter": "statuscode:200", "limit": f"-{CAPTURES}"}).json()
            break
        except (requests.RequestException, ValueError, PermissionError) as e:
            busy = isinstance(e, (requests.Timeout, requests.ConnectionError)) or (
                isinstance(e, requests.HTTPError) and e.response is not None and e.response.status_code >= 500)
            if busy and attempt < 2:
                log(f"the Internet Archive index is busy; waiting {BUSY_WAIT:.0f} s")
                http.sleep(BUSY_WAIT)
                continue
            return dict(base, via=None, error=f"{live_error or 'not read'}; {why}; the Internet Archive index did "
                                               f"not answer ({type(e).__name__})")
    for ts, orig_url in reversed([(r[0], r[1]) for r in (rows or [])[1:]]):
        if ts in tried:
            continue
        tried.add(ts)
        entry, why = _capture(http, ts, orig_url, base, quotes, keep)
        if entry:
            return entry
    if (not rows or len(rows) < 2) and not want:
        why = f"{why}, and the Internet Archive lists no other copy" if why else "the Internet Archive has no copy"
    return dict(base, via=None, error=f"{live_error or 'not read'}; {why or 'no usable Internet Archive copy'}")


def wanted(specs: Iterable[dict], state: str | None = None) -> dict[str, list[str]]:
    """The pages to read for a set of process files: every page a quote cites that is not the official state code
    (its quotes are matched to Open US Law's copy), and every page a file cites, for the quotes that cite none or
    are not on theirs; with the quotes of the files that cite each page (for a page whose words are not kept)."""
    from . import places as P
    out: dict[str, set[str]] = {}
    for spec in specs:
        restore(spec)
        st = state or P.state_of(spec)
        qs = [q for _, q, _ in P.process_quotes(spec)]
        for _, q, cites in P.process_quotes(spec):
            for u in cited_urls(cites):
                if not P.official_code_url(st, u):
                    out.setdefault(key(u), set()).add(q)
        for u in file_urls(spec):
            if not P.official_code_url(st, u):
                out.setdefault(key(u), set()).update(qs)
    return {u: sorted(q) for u, q in out.items() if u.startswith("http")}


def fetch(pages: dict[str, list[str]], *, retry: bool = False, log: Log = print, workers: int = 8,
          sleep: Callable[[float], None] | None = None, refetch: Iterable[str] = (), archive: bool = True,
          archive_workers: int = 3) -> dict:
    """Read each page (``wanted``) not yet in the cache, politely (see the module docstring), and cache what was
    read.  ``retry`` reads again pages whose last read failed; ``refetch`` reads again cached pages of these kinds
    ("pdf", or "pdf:live" for those read live); ``archive`` False leaves alone the pages that would need an
    Internet Archive copy.  One reader works per live host; ``archive_workers`` readers share the Internet Archive,
    whose slow downloads they overlap, but every reader keeps to one clock per host (``_clock``), so requests to
    one host still start at least its interval apart.  Returns counts."""
    again = set(refetch or ())
    todo = {}
    for u, qs in pages.items():
        have = cached(u)
        kinds = {have.get("type"), f"{have.get('type')}:{have.get('via')}"} if have else set()
        # a page whose words are not kept was checked only for the quotes the files had then: read it again for new ones
        unchecked = bool(have and not have.get("error") and have.get("text") is None and have.get("checked") is not None
                         and {qhash(q) for q in qs} - set(have.get("checked") or []))
        if have and not (retry and have.get("error")) and not (kinds & again and not have.get("error")) \
                and not unchecked:
            continue
        p = policy(u)
        if p and not p["fetch"]:
            if not have:
                _save({"url": key(u), "via": None, "fetched": _today(), "at": _now(),
                       "error": f"not fetched: {p['reason']}"})
            continue
        todo[u] = qs
    archive_q: queue.Queue = queue.Queue()
    shared = _clock()
    counts = {"live": 0, "archive": 0, "failed": 0, "skipped": len(pages) - len(todo)}
    say_lock = threading.Lock()

    def say(m):
        with say_lock:
            log(m)

    def done(entry):
        _save(entry)
        with _LOCK:
            counts["failed" if entry.get("error") else entry["via"]] += 1

    by_host: dict[str, list[str]] = {}
    for u in todo:
        (archive_q.put((u, None)) if capture_of(u) else by_host.setdefault(urlsplit(u).netloc.lower(), []).append(u))

    def live_worker(urls):
        http = _http(say, sleep, shared)
        for u in urls:
            try:
                entry, why = _live(http, u, todo[u])
            except Exception as e:                                 # noqa: BLE001 - one page never stops the rest
                entry, why = {"url": key(u), "via": None, "fetched": _today(), "at": _now(),
                              "error": f"could not be read ({type(e).__name__})"}, None
            if entry is not None:
                done(entry)
                say(f"live {'ok' if not entry.get('error') else 'FAILED ' + entry['error']}: {u}")
            else:
                archive_q.put((u, why))

    def archive_worker():
        http = _http(say, sleep, shared)
        while True:
            item = archive_q.get()
            if item is None:
                return
            u, why = item
            if not archive:
                continue
            try:
                entry = _archive(http, u, todo[u], why, say)
            except Exception as e:                                 # noqa: BLE001 - one page never stops the rest
                entry = {"url": key(u), "via": None, "fetched": _today(), "at": _now(),
                         "error": f"{why or 'not read'}; the Internet Archive copy could not be read "
                                  f"({type(e).__name__})"}
            done(entry)
            say(f"archive {entry.get('capture') or ''} {'ok' if not entry.get('error') else 'FAILED ' + entry['error']}"
                f": {u}")

    arch = [threading.Thread(target=archive_worker, daemon=True) for _ in range(max(1, archive_workers))]
    for t in arch:
        t.start()
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=workers) as ex:
        list(ex.map(live_worker, by_host.values()))
    for _ in arch:
        archive_q.put(None)
    for t in arch:
        t.join()
    return counts


# ---- the evidence store ----------------------------------------------------------------------------------------
# Words from a NO_REPRINT site never sit verbatim in a committed file.  ``withhold`` moves each such quote's text
# out of a researched file (or a fixture) into its evidence file under data/evidence/<state>/<place>/<process>.json
# (git-ignored), leaving the quote's fingerprint, its length in words, lexflow's paraphrase, the page and the
# Internet Archive capture it was read from.  ``restore`` puts the words back in memory, for the loader, the matcher
# and the tests, when the evidence file is present; ``rebuild`` makes the evidence files again from the pages (the
# cache keeps no words of those sites, so the pages are read again, in memory only, and each quote is found as the
# run of ``quote_words`` words whose fingerprint is the quote's); ``leaks`` is the scan that proves no committed
# file holds ``MIN_RUN`` or more consecutive words of a withheld quote.
EVIDENCE_DIR = config.ROOT / "data" / "evidence"
MIN_RUN = 8                     # consecutive words of a withheld quote that count as reprinting it
HELD = ("quote_sha256", "quote_words", "paraphrase", "url", "capture")
SPEC_LISTS = ("legal_basis", "steps", "fees", "escalation")


def evidence_path(state: str, place: str, process: str) -> Path:
    """The evidence file of a researched process (``place`` is its directory under curated/places/<state>/) or of a
    fixture (place ``fixtures``)."""
    return EVIDENCE_DIR / state / place / f"{process}.json"


def evidence_name(spec: dict, path: str | Path | None = None) -> str | None:
    """``<state>/<place>/<process>`` for a spec: from its path (curated/places/<state>/<place>/<process>.json or
    fixtures/places/<state>/<name>.json), its ``evidence`` field (a fixture), or its place and process."""
    ev = spec.get("evidence") if isinstance(spec, dict) else None
    if isinstance(ev, str) and re.fullmatch(r"[a-z]{2}/[\w-]+/[\w.-]+", ev):
        return ev
    if path is not None:
        p = Path(path)
        if p.parent.parent.name == "places":
            return f"{p.parent.name}/fixtures/{p.stem}"
        if p.parent.parent.parent.name == "places":
            return f"{p.parent.parent.name}/{p.parent.name}/{p.stem}"
    if not isinstance(spec, dict) or not isinstance(spec.get("process"), str):
        return None
    from . import places as P
    st, pid = P.state_of(spec), spec["process"]
    if not st:
        return None
    for cand in sorted((P.PLACES_DIR / st).glob(f"*/{pid}.json")):
        try:
            other = json.loads(cand.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if other.get("gov_id") == spec.get("gov_id"):
            return f"{st}/{cand.parent.name}/{pid}"
    name = re.sub(r"[^a-z0-9]+", "_", (spec.get("place") or "").partition(":")[2].lower()).strip("_")
    return f"{st}/{name.removesuffix('_county')}/{pid}" if name else None


def evidence_file(spec: dict, path: str | Path | None = None) -> Path | None:
    name = evidence_name(spec, path)
    return EVIDENCE_DIR / f"{name}.json" if name else None


def load_evidence(spec: dict, path: str | Path | None = None) -> dict[str, str]:
    """The withheld words of a file, by fingerprint; {} when its evidence file is not present."""
    p = evidence_file(spec, path)
    try:
        return dict((json.loads(p.read_text(encoding="utf-8")) if p else {}).get("quotes") or {})
    except (OSError, ValueError):
        return {}


def save_evidence(name: str, quotes: dict[str, str], source: str | None = None, merge: bool = True) -> Path:
    """Write (``merge`` False) or add to (True) an evidence file."""
    p = EVIDENCE_DIR / f"{name}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    have = {}
    if merge:
        try:
            have = json.loads(p.read_text(encoding="utf-8")).get("quotes") or {}
        except (OSError, ValueError):
            pass
    have.update(quotes)
    p.write_text(json.dumps({"file": source, "written": _today(), "note": "words from sites whose terms forbid "
                             "reposting them (lexflow.municipal.quotes.NO_REPRINT), kept here as the evidence lexflow's "
                             "match is made against; never committed", "quotes": dict(sorted(have.items()))},
                            indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return p


def full_hash(quote: str) -> str:
    """A withheld quote's fingerprint: sha256 of its normalised text (``norm``)."""
    return hashlib.sha256(norm(quote).encode("utf-8")).hexdigest()


def _strings(d: dict) -> list[str]:
    return [v for v in d.values() if isinstance(v, str)]


def quote_dicts(value, path: tuple = ()):
    """Every dict in a file that holds a quote (``quote``, or ``text`` beside a page address) or a withheld one
    (``quote_sha256``): (path, dict, key or None when withheld)."""
    if isinstance(value, dict):
        key = None
        for k in ("quote", "text"):
            if isinstance(value.get(k), str) and value[k].strip():
                if k == "quote" or any(URL.search(v) for kk, v in value.items() if kk != k and isinstance(v, str)):
                    key = k
                break
        if key:
            yield path, value, key
        elif isinstance(value.get("quote_sha256"), str):
            yield path, value, None
        for k, v in value.items():
            yield from quote_dicts(v, path + (k,))
    elif isinstance(value, list):
        for i, v in enumerate(value):
            yield from quote_dicts(v, path + (i,))


def _where(path: tuple) -> str | None:
    """A process file's name for a quote's place: steps[3]."""
    return f"{path[0]}[{path[1]}]" if len(path) == 2 and path[0] in SPEC_LISTS and isinstance(path[1], int) else None


def is_process_file(spec) -> bool:
    return isinstance(spec, dict) and isinstance(spec.get("process"), str) and any(k in spec for k in SPEC_LISTS)


def _place(d: dict, key: str, value, after: str) -> None:
    """Put ``key`` in ``d`` right after ``after`` (first when ``after`` is None; last when it is not a key)."""
    items = [(k, v) for k, v in d.items() if k != key]
    out, done = ({key: value}, True) if after is None else ({}, False)
    for k, v in items:
        out[k] = v
        if k == after:
            out[key] = value
            done = True
    if not done:
        out[key] = value
    d.clear()
    d.update(out)


ADDRESS = re.compile(r"\b\d{1,6}\s+\S.{0,60}\b(?:Road|Rd|Street|St|Avenue|Ave|Drive|Dr|Lane|Ln|Way|Court|Ct|Boulevard|"
                     r"Blvd|Highway|Hwy|Suite|Room|Floor)\b|\(?\d{3}\)?[ .-]\d{3}[ .-]\d{4}|\bAttn:?\b|"
                     r"\b(?:Suite|Ste|Room)\s+\d+\b|\bVA\s+\d{5}\b", re.I)
_FREE_PAGES: tuple[str, dict[str, list[str]]] | None = None


def _free_pages() -> dict[str, list[str]]:
    """The text of every cached page of a site that allows reprinting, by address (read once a run)."""
    global _FREE_PAGES
    if _FREE_PAGES is None or _FREE_PAGES[0] != str(cache_dir()):
        out = {}
        for p in sorted(cache_dir().glob("*.json")) if cache_dir().exists() else []:
            try:
                e = json.loads(p.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if e.get("text") and not e.get("error") and not policy(e.get("url")):
                out[e["url"]] = [canon(v) for v in variants(e["text"])]
        _FREE_PAGES = (str(cache_dir()), out)
    return _FREE_PAGES[1]


def canon(text: str) -> str:
    """Words only, lower case, punctuation at word ends dropped: how the scan compares runs of words."""
    return " ".join(w for w in (re.sub(r"^\W+|\W+$", "", w).lower() for w in norm(text).split()) if w)


def free_words(quote: str, state: str | None = "va") -> str | None:
    """Why a quote found on a NO_REPRINT page need not be withheld, or None: its words are the state code's (Open US
    Law's index has them), a free official page's (the quote fetch read them there), or an address or phone number
    (a fact, not the site's prose)."""
    q = canon(quote)
    if not q:
        return None
    if len(q.split()) <= 24 and ADDRESS.search(q):
        return "an address or phone number"
    if state:
        try:
            from ..ask import index as I
            words = re.findall(r"[A-Za-z0-9]+", q)
            expr = I.phrase(" ".join(words[:12]))
            for row in I.search(state, expr, limit=5) if expr else []:
                if q in canon(I.text_of(state, row["id"])):
                    return f"the words of {row.get('citation') or row.get('ref')}"
        except Exception:                                          # noqa: BLE001 - no index here
            pass
    for url, texts in _free_pages().items():                       # the texts are normalised already (variants)
        if any(q in t for t in texts):
            return f"the words of {url}"
    return None


def withhold(spec: dict, qc: dict | None = None, path: str | Path | None = None) -> dict[str, str]:
    """Move every quote from a NO_REPRINT site out of ``spec`` (in place) and return the words by fingerprint, for
    the evidence file.  A quote goes when ``withheld`` says so: matched on a page of such a site (``qc``, lexflow's
    match, made here for a process file when not given), or not matched and citing one.  What stays in the file:
    ``quote_sha256``, ``quote_words``, ``paraphrase``, ``url`` (the page, never the archive address), ``capture``
    (the Internet Archive timestamp it was read from, when known) and, for a ``text`` field, ``quote_key``.  A quote
    whose words are the state code's, a free official page's or an address stays (``free_words``)."""
    items = {}
    state = None
    try:
        from . import places as P
        state = P.state_of(spec) or (evidence_name(spec, path) or "va/")[:2]
        if is_process_file(spec) and qc is None:
            qc = P.check_quotes(spec, state)
    except Exception:                                              # noqa: BLE001 - no statutes, no pydantic: cite rule
        qc = qc
    if qc:
        items = qc.get("items") or {}
    out: dict[str, str] = {}
    for p, d, key in list(quote_dicts(spec)):
        if key is None:
            continue
        where = _where(p)
        hit = items.get(where) if where else None
        pol = withheld(hit, _strings(d))
        if pol and free_words(d[key], state):
            pol = None
        if not pol:
            for k in ("quote_sha256", "quote_words", "capture", "quote_key"):   # once withheld, now free: plain again
                d.pop(k, None)
            continue
        keys = list(d)
        anchor = keys[keys.index(key) - 1] if keys.index(key) else None   # the fingerprint takes the quote's place
        text = d.pop(key)
        sha = full_hash(text)
        out[sha] = text
        urls = [original(u) for u in cited_urls(_strings(d)) if policy(u)]
        url = (hit or {}).get("url") if hit and hit.get("by") else None
        cap = (hit or {}).get("capture") or next((capture_of(u) for u in cited_urls(_strings(d)) if capture_of(u)), None)
        _place(d, "quote_sha256", sha, anchor)
        _place(d, "quote_words", len(norm(text).split()), "quote_sha256")
        last = "quote_words"
        for k, v in (("paraphrase", None), ("url", url or (urls[0] if urls else None)), ("capture", cap),
                     ("quote_key", key if key != "quote" else None)):
            if k in d or (k == "quote_key" and not v):                 # a field the item has stays where it is
                continue
            _place(d, k, v, last)
            last = k
    if out:
        runs = {s for text in out.values() for s in shingles(text)}
        for p, d, key in list(quote_dicts(spec)):                  # the same words quoted again, cited to no page
            if key and shingles(d[key]) & runs and not free_words(d[key], state):
                text = d.pop(key)
                sha = full_hash(text)
                out[sha] = text
                anchor = list(d)[0] if d else None
                _place(d, "quote_sha256", sha, anchor)
                _place(d, "quote_words", len(norm(text).split()), "quote_sha256")
                for k, v in (("paraphrase", None), ("url", None), ("capture", None),
                             ("quote_key", key if key != "quote" else None)):
                    if k not in d and (v is not None or k != "quote_key"):
                        _place(d, k, v, "quote_words" if k == "paraphrase" else list(d)[-1])
        _unquote(spec, out)
    return out


def _unquote(value, words: dict[str, str], parent: dict | None = None) -> None:
    """Prose that repeats a withheld quote whole (a fee amount, a deadline, a how) keeps the item's paraphrase or a
    pointer to the page in its place, so the words sit only in the evidence file."""
    if isinstance(value, dict):
        for k, v in list(value.items()):
            if isinstance(v, str) and k not in ("quote", "text", "quote_sha256"):
                for sha, text in words.items():
                    if len(norm(text).split()) >= MIN_RUN and norm(text) in norm(v):
                        rep = value.get("paraphrase") or (parent or {}).get("paraphrase") or "see the cited page"
                        value[k] = norm(v).replace(norm(text), rep)
            else:
                _unquote(v, words, value)
    elif isinstance(value, list):
        for v in value:
            _unquote(v, words, parent)


def restore(spec: dict, path: str | Path | None = None, evidence: dict[str, str] | None = None) -> dict:
    """Put the withheld words back in ``spec`` (in place), from ``evidence`` or the file's evidence file; the spec
    unchanged when neither is present.  A quote whose words are not found stays withheld, and lexflow's match
    counts it as not matched (``places.check_quotes``)."""
    if not isinstance(spec, dict):
        return spec
    held = [(p, d) for p, d, key in quote_dicts(spec) if key is None]
    if not held:
        return spec
    ev = evidence if evidence is not None else load_evidence(spec, path)
    for _, d in held:
        text = ev.get(d["quote_sha256"])
        if isinstance(text, str) and text:
            _place(d, d.get("quote_key") or "quote", text, "quote_sha256")
    return spec


def withheld_quotes(spec: dict) -> list[dict]:
    """The withheld quotes of a file: {where, sha, words, url, capture, restored}."""
    out = []
    for p, d, key in quote_dicts(spec):
        if "quote_sha256" in d:
            out.append({"where": _where(p) or ".".join(str(x) for x in p), "sha": d["quote_sha256"],
                        "words": d.get("quote_words"), "url": d.get("url"), "capture": d.get("capture"),
                        "restored": isinstance(d.get(d.get("quote_key") or "quote"), str)})
    return out


def withhold_file(path: str | Path, log: Log = print) -> dict:
    """Withhold a committed file's NO_REPRINT words into its evidence file and rewrite it.  Counts."""
    p = Path(path)
    spec = json.loads(p.read_text(encoding="utf-8"))
    name = evidence_name(spec, p)
    if not name:
        raise ValueError(f"{p}: no evidence file name (not a researched process or a places fixture)")
    restore(spec, p)                                               # words already withheld come back first
    words = withhold(spec, path=p)
    save_evidence(name, words, str(p.as_posix()).split("/app/", 1)[-1], merge=False)   # exactly what is withheld now
    if not is_process_file(spec):
        spec["evidence"] = name
    text = json.dumps(spec, indent=1, ensure_ascii=False) + "\n"
    p.write_text(text, encoding="utf-8")
    n = len(withheld_quotes(spec))
    log(f"{p.name}: {len(words)} quotes withheld this time, {n} withheld in all, evidence {name}")
    return {"file": str(p), "withheld": len(words), "held": n, "evidence": name}


def shingles(text: str, n: int = MIN_RUN) -> set[str]:
    """Every run of ``n`` consecutive words of a text (lower case, punctuation at word ends dropped)."""
    words = canon(text).split()
    return {" ".join(words[i:i + n]) for i in range(len(words) - n + 1)}


def file_text(path: Path) -> str:
    """A committed file's text as a reader sees it (JSON decoded, so escapes do not hide a run of words)."""
    raw = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix == ".json":
        try:
            return json.dumps(json.loads(raw), ensure_ascii=False)
        except ValueError:
            pass
    return raw


def leaks(paths: Iterable[Path], evidence: dict[str, str], n: int = MIN_RUN) -> list[dict]:
    """The runs of ``n`` or more consecutive words of a withheld quote found in the files: {file, sha, words}."""
    want: dict[str, str] = {}
    for sha, text in evidence.items():
        for s in shingles(text, n):
            want.setdefault(s, sha)
    out = []
    free: dict[str, bool] = {}
    for p in paths:
        p = Path(p)
        try:
            hits = shingles(file_text(p), n) & want.keys()
        except OSError:
            continue
        for s in sorted(hits):
            if s not in free:                                      # a run the Code or a free page also has is no leak
                free[s] = bool(free_words(s))
            if not free[s]:
                out.append({"file": str(p), "sha": want[s], "words": s})
    return out


def committed_files(root: Path | None = None) -> list[Path]:
    """The text files a commit would carry (data/, out/, caches and environments left out)."""
    root = root or config.ROOT
    skip = {"data", "out", ".git", ".venv", "node_modules", "__pycache__", ".pytest_cache", ".mypy_cache"}
    exts = {".json", ".md", ".py", ".txt", ".rq", ".ttl", ".yml", ".yaml", ".html", ".csv", ".toml", ".cfg", ".ini"}
    out = []
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root).parts
        if not p.is_file() or set(rel[:-1]) & skip or p.suffix.lower() not in exts:
            continue
        out.append(p)
    return out


def all_evidence() -> dict[str, str]:
    """Every withheld quote's words, by fingerprint, from the evidence files."""
    out: dict[str, str] = {}
    for p in sorted(EVIDENCE_DIR.rglob("*.json")) if EVIDENCE_DIR.exists() else []:
        try:
            out.update(json.loads(p.read_text(encoding="utf-8")).get("quotes") or {})
        except (OSError, ValueError):
            continue
    return out


def held_shas(paths: Iterable[Path]) -> set[str]:
    """The fingerprints of the quotes the committed files withhold (the scan looks for these words, not for
    words an evidence file may keep from an earlier state of a file)."""
    out: set[str] = set()
    for p in paths:
        p = Path(p)
        if p.suffix != ".json":
            continue
        try:
            spec = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        out.update(q["sha"] for q in withheld_quotes(spec))
    return out


def _page_words(url: str, capture: str | None, log: Log) -> list[str] | None:
    """A page's text as matched (``variants``), from the cache where it keeps words, else read again in memory (the
    live page, or the Internet Archive capture named or the newest) and never saved."""
    e = cached(url)
    if e and e.get("_texts"):
        return e["_texts"]
    p = policy(url)
    if p and not p["fetch"]:
        return None
    http = _http(log)
    want = f"https://{ARCHIVE}/web/{capture}/{original(url)}" if capture else url
    entry = None
    if not capture:
        entry, why = _live(http, url, [], keep=True)
        if entry is not None and entry.get("error"):
            return None
    else:
        why = None
    if entry is None:
        entry = _archive(http, want, [], why, log, keep=True)
    return variants(entry["text"]) if entry.get("text") else None


_EDGE = ".,;:!?\"'()[]{}"


def _runs(words: list[str]) -> list[str]:
    """A run of a page's words as a quote may have cut it: as it stands, and with the punctuation around its first
    and last words dropped."""
    firsts = dict.fromkeys([words[0], words[0].lstrip(_EDGE)])
    lasts = dict.fromkeys([words[-1], words[-1].rstrip(_EDGE)])
    mid = words[1:-1]
    out = []
    for f in firsts:
        for la in lasts:
            run = " ".join([f] + mid + [la]) if len(words) > 1 else (f if f == la else f.rstrip(_EDGE))
            if run and run not in out:
                out.append(run)
    return out


def rebuild(files: Iterable[tuple[Path, dict]], log: Log = print) -> dict:
    """Make the evidence files again for ``files`` from their pages: each withheld quote is the run of
    ``quote_words`` words of the page whose fingerprint is ``quote_sha256``.  Counts."""
    todo: dict[tuple[str, str | None], list[tuple[str, int]]] = {}
    names: dict[str, tuple[str, str]] = {}
    for p, spec in files:
        name = evidence_name(spec, p)
        for q in withheld_quotes(spec):
            if not q["url"] or not q["words"] or not name:
                continue
            todo.setdefault((key(q["url"]), q["capture"]), []).append((q["sha"], int(q["words"])))
            names[q["sha"]] = (name, str(p))
    found: dict[str, str] = {}
    counts = {"pages": len(todo), "read": 0, "quotes": len(names), "found": 0}
    for (url, cap), wants in sorted(todo.items()):
        try:
            texts = _page_words(url, cap, log)
        except Exception as e:                                     # noqa: BLE001 - one page never stops the rest
            texts = None
            log(f"{url}: could not be read ({type(e).__name__})")
        if not texts:
            log(f"not read: {url}{' (' + cap + ')' if cap else ''}")
            continue
        counts["read"] += 1
        for t in texts:
            words = t.split()
            for n in {w for _, w in wants}:
                need = {sha for sha, w in wants if w == n and sha not in found}
                for i in range(len(words) - n + 1):
                    if not need:
                        break
                    for run in _runs(words[i:i + n]):
                        h = full_hash(run)
                        if h in need:
                            found[h] = run
                            need.discard(h)
    by_name: dict[str, dict[str, str]] = {}
    for sha, text in found.items():
        name, src = names[sha]
        by_name.setdefault(name, {})[sha] = text
    for name, qs in by_name.items():
        save_evidence(name, qs, names[next(iter(qs))][1])
    counts["found"] = len(found)
    missing = [sha for sha in names if sha not in found]
    if missing:
        log(f"{len(missing)} withheld quotes were not found on their pages")
    return counts


# ---- the command -----------------------------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    """python -m lexflow.municipal.quotes [--fetch] [--retry] [--state va] [--report] [--withhold] [--evidence]
    [--scan] [paths ...]"""
    import argparse
    from . import places as P
    ap = argparse.ArgumentParser(prog="python -m lexflow.municipal.quotes", description=__doc__.split("\n\n")[0])
    ap.add_argument("paths", nargs="*", help="process files (default: every curated/places/<state>/<place>/*.json)")
    ap.add_argument("--state", help="only this state's files")
    ap.add_argument("--withhold", action="store_true", help="move the files' NO_REPRINT words to data/evidence/")
    ap.add_argument("--evidence", action="store_true", help="rebuild the evidence files from the pages")
    ap.add_argument("--scan", action="store_true", help="find runs of withheld words in the files a commit carries")
    ap.add_argument("--fetch", action="store_true", help="read the cited pages not yet cached")
    ap.add_argument("--retry", action="store_true", help="with --fetch, read again pages whose last read failed")
    ap.add_argument("--refetch", action="append", default=[], metavar="KIND",
                    help="with --fetch, read again cached pages of this kind (pdf, or pdf:live, pdf:archive)")
    ap.add_argument("--no-archive", action="store_true", help="with --fetch, leave pages that need an archive copy")
    ap.add_argument("--archive-workers", type=int, default=3, metavar="N",
                    help="with --fetch, Internet Archive readers at once (they share one clock: 5 s between requests)")
    ap.add_argument("--report", action="store_true", help="match every file's quotes and print the counts")
    a = ap.parse_args(argv)
    paths = [Path(p) for p in a.paths] or P.process_files()
    if a.withhold:
        for p in paths:
            withhold_file(p)
    specs = []
    for p in paths:
        try:
            spec = json.loads(Path(p).read_text(encoding="utf-8"))
        except ValueError:
            continue
        if not a.state or P.state_of(spec) == a.state or not is_process_file(spec):
            specs.append((Path(p), restore(spec, Path(p))))
    if a.evidence:
        print(json.dumps(rebuild(specs)))
    if a.scan:
        files = committed_files()
        held = held_shas(files)
        found = leaks(files, {sha: text for sha, text in all_evidence().items() if sha in held})
        for x in found:
            print(json.dumps(x, ensure_ascii=False))
        print(f"{len(found)} runs of {MIN_RUN} or more withheld words in {len({x['file'] for x in found})} files")
        return 1 if found else 0
    if a.fetch:
        print(json.dumps(fetch(wanted([s for _, s in specs]), retry=a.retry, refetch=a.refetch,
                               archive=not a.no_archive, archive_workers=a.archive_workers)))
    if a.report:
        for p, spec in specs:
            qc = P.check_quotes(spec, P.state_of(spec))
            print(json.dumps({"file": f"{p.parent.name}/{p.name}", "verified": P.is_verified(spec, qc),
                              **{k: qc.get(k) for k in ("quotes", "matched", "by_code", "by_page", "by_archive")},
                              "unmatched": len(qc.get("unmatched") or [])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
