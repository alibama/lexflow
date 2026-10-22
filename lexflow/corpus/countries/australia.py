"""Australia: the Federal Register of Legislation (Office of Parliamentary Counsel), every Commonwealth Act in force
as its current compilation, one row per section; the state and territory registers are in australia_states.py.

Verified 19 and 22 October 2026 (docs/design/global-sources.md §2.3 and "Progress"):

* OData v4 API at ``https://api.prod.legislation.gov.au/v1/`` (``$metadata`` served; entity sets ``titles``,
  ``versions``, ``documents``; ``$top`` at most 500).  ``titles?$filter=collection eq 'Act' and isInForce eq
  true`` lists the 4,776 Acts in force (22 Oct 2026; principal and amending: ``isPrincipal`` cannot be filtered on,
  the server throws, so it is read from ``$select``); ``versions?$filter=isCurrent eq true and contains(titleId,'A')``
  gives each Act's current compilation (``start``, ``registerId`` such as ``C2026C00117``, ``compilationNumber``);
  ``documents/find(titleid=..., asatspecification='Current', format='Epub', volumeNumber=0, ...)`` returns the
  current compilation as one ePub with every volume (``OEBPS/document_<n>/document_<n>.html``, XHTML generated from
  the OPC Word drafting styles), the most structured format the register offers (Word, ePub, PDF; no XML).
  ``robots.txt`` of www.legislation.gov.au: ``Crawl-delay: 10``; the API host has no robots.txt and is read at the
  same pace (one request per 10 s).
* Licence (terms of use, https://www.legislation.gov.au/terms-of-use): "all content on the Federal Register of
  Legislation ... is provided under Creative Commons Attribution 4.0 International (the CC BY 4.0 licence)", with the
  attribution "Sourced from the Federal Register of Legislation at [full date of download]. For the latest
  information on Australian Government law please go to https://www.legislation.gov.au." (``ATTRIBUTION_TEMPLATE``; the
  pull writes it with the download date to LICENSE-NOTICE.txt and MANIFEST.json, and every row carries its
  ``fetched`` date).

The compiled XHTML has no semantic markup of the hierarchy, only paragraph styles: ``ActHead1`` .. ``ActHead4``
are the heading depths (Chapter, Part, Division, Subdivision in the body, but a Schedule is an ``ActHead1`` and its
Chapters ``ActHead2``), ``ActHead5`` is a section (``CharSectno`` the number), ``ActHead6`` .. ``ActHead9`` the
amending-schedule headings; the unit word is read from the heading's own text (``Part 1—Preliminary``).  The text
of a section is every paragraph up to the next heading (subsection, paragraph, Definition, notes, penalties, the
simplified-outline boxes), tables row by row with ``" | "`` between cells; the table of contents, running headers
(``Header``), the tables of sections (``TofSects*``) and the endnotes (from ``ENotesHeading1``) are dropped.  The
text is the source's own except that no-break spaces become spaces and no-break hyphens (U+2011) become ``-``.
The oldest compilations use ``<h1>`` .. ``<h6>`` for the same depths and ``NotesSection`` for the endnotes.  In an
amending schedule (``ActHead6`` .. ``ActHead9``) the Parts and sections an item inserts into another Act are quoted
text: each amended Act's items are one row (``... Amendment Act 2004 sch 1, Social Security Act 1991``).

Rows: one per section, path ``Acts Interpretation Act 1901 / Part 1 / Section 1``, citation ``Acts Interpretation
Act 1901 s 15AA``; under a schedule ``Competition and Consumer Act 2010 sch 2 s 18`` (a schedule with Chapters or
Divisions numbers sections) or ``Privacy Act 1988 sch 1 cl 1`` (a schedule of clauses); a schedule or a unit with
text and no sections is one row (``... sch 3``).  act_id ``STATE_AUS_C1901A00002_P1_S15AA``; ELI
``.../eli/au/act/1901/2/sec_15aa/en@2026-03-28`` (the ELI keeps ISO alpha-2 ``au``; lexflow keys use ``aus``);
source URL the compilation's point-in-time page ``https://www.legislation.gov.au/C1901A00002/2026-03-28/2026-03-28/text``.
Each JSONL row also carries ``title_id``, ``register_id``, ``compilation_number``, ``compilation_date`` and
``fetched``.

The pull (``python -m lexflow.corpus.countries.australia pull``) is resumable: the list in ``list.jsonl``, one
ePub per compilation in ``epub/``, one rows file per Act in ``rows/<titleId>.jsonl`` (written whole, then renamed),
one line per Act in ``progress.jsonl``; a restart skips every Act whose current compilation is already done.
"""
from __future__ import annotations

import io
import json
import os
import re
import sys
import time
import zipfile
from pathlib import Path
from typing import Callable, Iterable, Iterator
from urllib.parse import quote

from ... import config
from .base import Country, Document, Node, Source

API = "https://api.prod.legislation.gov.au/v1/"
SITE = "https://www.legislation.gov.au/"
FIND = ("documents/find(titleid='{t}',asatspecification='Current',type='Primary',format='Epub',uniqueTypeNumber=0,"
        "volumeNumber=0,rectificationVersionNumber=0)")
TEXT_URL = SITE + "{t}/{start}/{retro}/text"
LATEST_URL = SITE + "{t}/latest/text"
TERMS_URL = "https://www.legislation.gov.au/terms-of-use"
ATTRIBUTION_TEMPLATE = ("Sourced from the Federal Register of Legislation at {date}. For the latest information on "
                        "Australian Government law please go to https://www.legislation.gov.au.")
EDIT_NOTE = ("lexflow split each compilation into sections and added the heading path for search; the section text "
             "is the Register's (no-break spaces and hyphens normalised). lexflow's index is not made or endorsed by "
             "the Office of Parliamentary Counsel.")
CODE = "aus"
RAW = config.RAW_DIR / "countries" / CODE
PAGE = 500                                  # the API's $top limit
Log = Callable[[str], None]


def attribution(raw: Path = RAW) -> str:
    """The prescribed attribution with the download dates of the rows on disk (MANIFEST.json ``fetched_from`` and
    ``fetched_to``), or today's date when nothing is pulled."""
    import datetime as dt
    try:
        m = json.loads((raw / "MANIFEST.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        m = {}
    a, b = m.get("fetched_from") or dt.date.today().isoformat(), m.get("fetched_to") or ""
    date = _long_date(a) if not b or b == a else f"{_long_date(a)} to {_long_date(b)}"
    return ATTRIBUTION_TEMPLATE.format(date=date)


# the unit words of the headings -> (act_id token prefix, ELI slug)
UNITS = {"chapter": ("CH", "ch"), "part": ("P", "pt"), "division": ("D", "div"), "subdivision": ("SD", "sdiv"),
         "schedule": ("SCH", "sch"), "appendix": ("APP", "app"), "preamble": ("PRE", "preamble")}
HEAD = re.compile(r"^ActHead([1-9])$")
TOC = re.compile(r"^TOC\d$")
HTAGS = tuple(f"h{i}" for i in range(1, 10))     # the oldest compilations' headings: <h5> a section, <h2> a Part
ORDINAL = {w: i for i, w in enumerate("first second third fourth fifth sixth seventh eighth ninth tenth eleventh "
                                      "twelfth thirteenth fourteenth fifteenth".split(), 1)}
SCHEDULE = re.compile(r"^(?:schedules\W+)?(?:the\s+)?(?:(?P<ord>" + "|".join(ORDINAL) + r")\s+)?schedule\b"
                      r"(?:\s+(?P<no>\d+[A-Z]?)\b)?(?P<head>.*)$", re.I)
SKIP_PREFIX = ("TOC", "SpecialTOC", "TofSects", "Header", "ShortT", "CompiledActNo", "ENote", "LongT", "Actno",
               "AssentDt", "UpdateDate", "Contents", "p1LinesBef")
REPEALED = re.compile(r"^[\[(]?(?:repealed|omitted)[\])]?\.?$", re.I)


class Australia(Country):
    code = CODE
    iso2 = "au"
    eli_jurisdiction = "au"
    name = "Australia"
    wikidata = "Q408"
    languages = ("en",)
    code_label = "Commonwealth Acts (Federal Register of Legislation)"
    pace = 10.0                     # robots.txt Crawl-delay of www.legislation.gov.au, kept for the API host too
    status = "prototype"
    raw_name = f"{CODE}/rows"       # countries.path_for: the pulled rows, one file per Act (countries._iter_dir)
    note = ("Federal Register of Legislation: OData listing plus one ePub per current compilation, split into "
            "sections; state registers in australia_states.py")
    sources = (
        Source(name="Federal Register of Legislation", publisher="Office of Parliamentary Counsel (Commonwealth)",
               url="https://www.legislation.gov.au/",
               holds="Commonwealth Acts, legislative and notifiable instruments, gazettes; as made and compiled "
                     "point-in-time versions; 132,636 titles, 4,776 Acts in force (22 Oct 2026)",
               format="ePub (XHTML from the OPC Word styles), DOCX, PDF per version; JSON (OData) metadata",
               access="OData v4 API https://api.prod.legislation.gov.au/v1/ (titles, versions, documents/find; "
                      "$top <= 500), sitemap; no bulk export",
               identifier="register id C1901A00002 (title), C2026C00117 (compilation); no ELI",
               licence="With the exception of the Commonwealth Coat of Arms, and where otherwise noted, all content "
                       "on the Federal Register of Legislation (the Legislation Register) is provided under Creative "
                       "Commons Attribution 4.0 International (the CC BY 4.0 licence).",
               licence_url=TERMS_URL, languages=("en",), verified="2026-10-22",
               automated_reading="allowed (CC BY 4.0, attribution wording prescribed); robots.txt Crawl-delay 10"),
    )

    # ------------------------------------------------------------------ the API
    def api(self, path: str, tries: int = 5) -> dict:
        r = self.fetch(API + path, accept="application/json", tries=tries)
        return r.json()

    def fetch(self, url: str, accept: str = "*/*", tries: int = 5, timeout: int = 180):
        """``Country.get`` with retries: 429 and 5xx and network errors back off (Retry-After when given), 404 and
        other 4xx raise at once."""
        import requests
        delay = 30.0
        for attempt in range(1, tries + 1):
            try:
                return self.get(url, accept=accept, timeout=timeout)
            except requests.HTTPError as e:
                code = e.response.status_code if e.response is not None else 0
                if code not in (429, 500, 502, 503, 504) or attempt == tries:
                    raise
                after = e.response.headers.get("Retry-After", "") if e.response is not None else ""
                time.sleep(float(after) if after.isdigit() else delay)
            except (requests.ConnectionError, requests.Timeout, requests.exceptions.ChunkedEncodingError):
                if attempt == tries:
                    raise
                time.sleep(delay)
            delay = min(delay * 2, 600)
        raise RuntimeError("unreachable")

    def _pages(self, path: str, log: Log | None = None) -> Iterator[dict]:
        skip = 0
        while True:
            sep = "&" if "?" in path else "?"
            data = self.api(f"{path}{sep}$top={PAGE}&$skip={skip}")
            vals = data.get("value", [])
            if log:
                log(f"  {path.split('?')[0]} skip={skip}: {len(vals)}")
            yield from vals
            if len(vals) < PAGE:
                return
            skip += PAGE

    def fetch_titles(self, log: Log | None = None) -> list[dict]:
        """Every Act in force (principal and amending) with its id, name, year, number and making date."""
        q = ("titles?$filter=" + quote("collection eq 'Act' and isInForce eq true", safe="'") +
             "&$select=id,name,isPrincipal,year,number,makingDate,status,seriesType&$orderby=id")
        return list(self._pages(q, log))

    def fetch_current_versions(self, log: Log | None = None) -> dict[str, dict]:
        """The current compilation of every Act, by title id."""
        q = ("versions?$filter=" + quote("isCurrent eq true and contains(titleId,'A')", safe="'(),") +
             "&$select=titleId,start,retrospectiveStart,registerId,compilationNumber,name,registeredAt,"
             "hasUnincorporatedAmendments&$orderby=titleId")
        return {v["titleId"]: v for v in self._pages(q, log)}

    def fetch_list(self, limit: int | None = 20, principal: bool | None = None, log: Log | None = None) -> list[dict]:
        """The Acts in force joined with their current compilations, principal Acts first (``principal=True`` keeps
        only those, ``False`` only the amending ones)."""
        titles = self.fetch_titles(log)
        versions = self.fetch_current_versions(log)
        out = []
        for t in titles:
            if principal is not None and bool(t.get("isPrincipal")) != principal:
                continue
            out.append(list_entry(t, versions.get(t["id"])))
        out.sort(key=lambda e: (not e["principal"], e["title_id"]))
        return out[:limit] if limit else out

    def fetch_version(self, title_id: str) -> dict | None:
        q = ("versions?$filter=" + quote(f"titleId eq '{title_id}' and isCurrent eq true", safe="'") +
             "&$select=titleId,start,retrospectiveStart,registerId,compilationNumber,name,registeredAt,"
             "hasUnincorporatedAmendments")
        vals = self.api(q).get("value", [])
        return vals[0] if vals else None

    def fetch_epub(self, title_id: str) -> tuple[bytes, str]:
        """The current compilation as an ePub, and the register id its file is named by."""
        r = self.fetch(API + FIND.format(t=title_id), accept="application/epub+zip")
        m = re.search(r'filename="?([A-Z0-9]+)\.epub', r.headers.get("content-disposition", ""))
        return r.content, (m.group(1) if m else "")

    def fetch_document(self, native_id: str, meta: dict | None = None) -> Document:
        if meta is None:
            t = self.api(f"titles('{native_id}')?$select=id,name,isPrincipal,year,number,makingDate,status")
            meta = list_entry(t, self.fetch_version(native_id))
        raw, register_id = self.fetch_epub(native_id)
        if register_id and not meta.get("register_id"):
            meta["register_id"] = register_id
        return self.parse(raw, native_id, meta)

    # ------------------------------------------------------------------ parsing
    def parse(self, raw: bytes | str, native_id: str = "", meta: dict | None = None) -> Document:
        """An ePub (zip bytes) or one XHTML document -> a Document with the Chapter / Part / Division / Subdivision
        / section tree.  ``meta`` is the ``list_entry`` of the Act (name, year, number, compilation)."""
        meta = dict(meta or {})
        htmls = list(_htmls(raw))
        name = meta.get("name") or ""
        start = meta.get("start") or None
        doc = Document(country=CODE, native_id=native_id or meta.get("title_id", ""), kind="Act",
                       kind_token=native_id or meta.get("title_id", ""), number="", title=name, short_title=name,
                       language="en", year=str(meta.get("year") or ""), eli_type="act",
                       eli_number=str(meta.get("number") or ""), url="", status="in_force", version_date=start,
                       promulgated=meta.get("making_date"), last_amended_year=int(start[:4]) if start else None,
                       fetched=self.today(), source=self.sources[0].name, licence=self.sources[0].licence)
        if meta.get("year") and meta.get("number"):
            doc.number = f"No. {meta['number']}, {meta['year']}"
        tid = doc.native_id
        if tid and start:
            doc.url = TEXT_URL.format(t=tid, start=start, retro=meta.get("retro_start") or start)
        elif tid:
            doc.url = LATEST_URL.format(t=tid)
        root = Node(level="Act", label=name, heading=name, native_id=tid)
        stats = {"dropped_chars": 0, "documents": len(htmls)}
        long_title = _build(root, htmls, stats)
        _finish(root)
        doc.root = root
        doc.extra = {"dups": _dups(root), "title_id": tid, "register_id": meta.get("register_id", ""),
                     "compilation_number": meta.get("compilation_number"), "compilation_date": start,
                     "retrospective_start": meta.get("retro_start"), "registered_at": meta.get("registered_at"),
                     "principal": meta.get("principal"), "long_title": long_title,
                     "latest_url": LATEST_URL.format(t=tid) if tid else "",
                     "attribution": ATTRIBUTION_TEMPLATE.format(date=_long_date(doc.fetched)), **stats}
        return doc

    _dups: frozenset = frozenset()

    def citation(self, doc: Document, path, leaf: Node) -> str:
        """``Acts Interpretation Act 1901 s 15AA``; ``... sch 2 s 18`` and ``... sch 1 cl 5`` under a schedule; a
        unit row is cited by its own words (``... sch 3``, ``... pt 2``); a section number that the Act uses a
        second time (the Corporations Act's small business guide in Part 1.5) is qualified by its unit
        (``Corporations Act 2001 pt 1.5 s 1``)."""
        act = doc.short_title or doc.title
        sch = next((n for n in path if n.level == "Schedule"), None)
        pre = f"{act} sch {sch.number}".rstrip() if sch is not None else act
        if leaf.level in ("Section", "Clause"):
            q = _qualifier(path) if _chain(path, leaf) in set(doc.extra.get("dups") or ()) else ""
            return f"{pre}{' ' + q if q else ''} {'s' if leaf.level == 'Section' else 'cl'} {leaf.number}".strip()
        if leaf is sch:
            return pre
        if leaf.level == "Preamble":
            return f"{act} preamble"
        if not leaf.level:
            return f"{pre}, {leaf.label}"
        return f"{pre} {UNITS.get(leaf.level.lower(), (None, leaf.level.lower()))[1]} {leaf.number}".strip()

    def unit_slug(self, leaf: Node, path=()) -> str:
        parts = []
        sch = next((n for n in path if n.level == "Schedule"), None)
        if sch is not None:
            parts.append(f"sch_{sch.number}" if sch.number else "sch")
        if leaf.level in ("Section", "Clause"):
            if _chain(path, leaf) in self._dups:
                parts.append(_qualifier(path).replace(" ", "_"))
            parts.append(f"{'sec' if leaf.level == 'Section' else 'cl'}_{leaf.number}")
        elif leaf.level == "Preamble":
            parts.append("preamble")
        elif not leaf.level:
            parts.append("h_" + re.sub(r"\W+", "_", leaf.label.lower()).strip("_")[:40])
        elif leaf is not sch:
            word = UNITS.get(leaf.level.lower(), (None, re.sub(r"\W+", "", leaf.level.lower())[:6] or "u"))[1]
            parts.append(f"{word}_{leaf.number}" if leaf.number else word)
        return "_".join(p for p in parts if p).lower().replace(".", "_")

    def to_rows(self, doc: Document) -> list[dict]:
        self._dups = frozenset((doc.extra or {}).get("dups") or ())
        try:
            rows = super().to_rows(doc)
        finally:
            self._dups = frozenset()
        x = doc.extra or {}
        seen: dict[str, int] = {}
        for r in rows:
            n = seen.get(r["citation"], 0)
            seen[r["citation"]] = n + 1
            if n:                       # still the same citation twice (a drafting slip in an old Act): keep both
                r["act_id"] += f"_{n + 1}"
                r["citation"] = r["ref"] = f"{r['citation']} ({n + 1})"
                head, sep, tail = r["eli"].rpartition("/")
                r["eli"] = f"{head}_{n + 1}{sep}{tail}" if "@" in tail else f"{r['eli']}_{n + 1}"
            r.update({"title_id": x.get("title_id"), "register_id": x.get("register_id"),
                      "compilation_number": x.get("compilation_number"), "compilation_date": x.get("compilation_date"),
                      "fetched": doc.fetched})
        return rows


def list_entry(t: dict, v: dict | None) -> dict:
    """One Act of the list: the title and its current compilation (None when the register has none)."""
    v = v or {}
    return {"title_id": t["id"], "name": t.get("name") or v.get("name") or "", "principal": bool(t.get("isPrincipal")),
            "year": t.get("year"), "number": t.get("number"), "making_date": (t.get("makingDate") or "")[:10] or None,
            "start": (v.get("start") or "")[:10] or None, "retro_start": (v.get("retrospectiveStart") or "")[:10] or None,
            "register_id": v.get("registerId") or "", "compilation_number": v.get("compilationNumber"),
            "registered_at": v.get("registeredAt"), "unincorporated": bool(v.get("hasUnincorporatedAmendments"))}


# ---------------------------------------------------------------------- the XHTML walk
def _htmls(raw: bytes | str) -> Iterator[bytes]:
    """The XHTML documents of an ePub in volume order, or the one document given."""
    if isinstance(raw, str):
        raw = raw.encode("utf-8")
    if raw[:2] != b"PK":
        yield raw
        return
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        names = [n for n in z.namelist() if re.search(r"document_\d+\.html?$", n)]
        for n in sorted(names, key=lambda s: int(re.search(r"document_(\d+)\.html?$", s).group(1))):
            yield z.read(n)


def _clean(s: str) -> str:
    s = s.replace("\xa0", " ").replace("‑", "-").replace("​", "").replace("﻿", "")
    return re.sub(r"\s+", " ", s).strip()


def _cls(el) -> str:
    return (el.get("class") or "").strip()


def _build(root: Node, htmls: Iterable[bytes], stats: dict) -> str:
    """Walk every volume's body into ``root``; returns the long title."""
    import lxml.html
    stack: list[tuple[int, Node]] = []
    current: Node | None = None
    lines: dict[int, list[str]] = {}          # id(node) -> its text lines
    nodes: dict[int, Node] = {}
    amending: set[int] = set()                # id(node) of the units an amending schedule opened (ActHead6-9)
    long_title = ""
    preamble: list[str] = []
    seen_head = False
    for raw in htmls:
        tree = lxml.html.fromstring(raw)
        blocks = []
        in_table = set()
        for t in tree.iter("table"):
            for p in t.iter("p"):
                in_table.add(p)
        for el in tree.iter("p", "tr", *HTAGS):
            if el.tag != "tr" and el in in_table:
                continue
            blocks.append(el)
        # the first heading of the body (older compilations have no navPoint ids, so the class alone decides; the
        # oldest use <h1> .. <h6> for the same levels)
        first = next((i for i, b in enumerate(blocks) if _depth(b)), None)
        if first is None:                          # an endnotes-only volume
            continue
        tocs = [i for i, b in enumerate(blocks[:first]) if b.tag == "p" and TOC.match(_cls(b))]
        begin = tocs[-1] + 1 if tocs else next((i for i, b in enumerate(blocks) if _cls(b) == "LongT"), first)
        for b in blocks[begin:]:
            c = _cls(b)
            if c.startswith(("ENotesHeading", "EndNotesHeading", "NotesSection")):     # the endnotes
                break
            if b.tag == "tr":
                cells = [_cell(td) for td in b if td.tag in ("td", "th")]
                text = " | ".join(x for x in cells if x)
                c = ""
            else:
                d = _depth(b)
                if d and d < 6 and any(id(n) in amending for _, n in stack):
                    # a heading quoted by an amending schedule (a Part or section the item inserts into another
                    # Act): the item's text, not a unit of this Act
                    d, current = 0, None
                    text = _clean(b.text_content())
                    if text:
                        lines.setdefault(id(stack[-1][1]), []).append(text)
                    continue
                if d:
                    seen_head = True
                    if d == 5:
                        parent = stack[-1][1] if stack else root
                        current = _section(b)
                        parent.children.append(current)
                        nodes[id(current)] = current
                        continue
                    depth = d if d < 5 else d - 5
                    while stack and stack[-1][0] >= depth:
                        stack.pop()
                    parent = stack[-1][1] if stack else root
                    unit = _unit(b)
                    parent.children.append(unit)
                    nodes[id(unit)] = unit
                    stack.append((depth, unit))
                    if d >= 6:                      # ActHead6-9: an amending schedule and its items' headings
                        amending.add(id(unit))
                    current = None
                    continue
                if c == "LongT" and not long_title:
                    long_title = _clean(b.text_content())
                    continue
                if c.startswith(SKIP_PREFIX):
                    continue
                text = _clean(b.text_content())
            if not text:
                continue
            if current is not None:
                lines.setdefault(id(current), []).append(text)
            elif stack:
                lines.setdefault(id(stack[-1][1]), []).append(text)
            elif not seen_head:
                preamble.append(text)
    for k, ls in lines.items():
        n = nodes[k]
        if n.level in ("Section", "Clause") or not n.children:
            n.text = "\n".join(ls)
        else:
            stats["dropped_chars"] += sum(len(x) for x in ls)
    if preamble and sum(len(x) for x in preamble) > 40:
        root.children.insert(0, Node(level="Preamble", label="Preamble", text="\n".join(preamble), token="PRE"))
    return long_title


def _depth(b) -> int:
    """A heading's depth (1-9: ActHead1 .. ActHead9, or <h1> .. <h9> in the oldest compilations), else 0."""
    if b.tag in HTAGS:
        return int(b.tag[1])
    if b.tag == "p":
        m = HEAD.match(_cls(b))
        return int(m.group(1)) if m else 0
    return 0


def _section(p) -> Node:
    nos = [s for s in p.iter("span") if _cls(s) == "CharSectno"]
    full = _clean(p.text_content())
    number = _clean("".join(s.text_content() for s in nos)) if nos else ""
    if not number:
        m = re.match(r"^(\d+[A-Za-z]*(?:[-.]\d+[A-Za-z]*)*)\s+(.*)$", full)
        number, heading = (m.group(1), m.group(2)) if m else ("", full)
    else:
        heading = full[len(number):].strip() if full.startswith(number) else full
    if not number and re.match(r"^preamble\b", heading, re.I):     # an old Act's preamble set as a heading
        return Node(level="Preamble", label="Preamble", heading="", token="PRE")
    n = Node(level="Section", label=f"Section {number}".strip(), number=number, heading=heading,
             token=f"S{_tok(number)}" if number else "S", native_id=f"s{number}" if number else "")
    if REPEALED.match(heading.strip()):
        n.status = "repealed"
    return n


def _unit(p) -> Node:
    full = _clean(p.text_content())
    nos = [s for s in p.iter("span") if _cls(s).startswith("Char") and _cls(s).endswith("No")]
    txts = [s for s in p.iter("span") if _cls(s).startswith("Char") and _cls(s).endswith("Text")]
    label = _clean("".join(s.text_content() for s in nos)) if nos else ""
    heading = _clean("".join(s.text_content() for s in txts)) if txts else ""
    if not label:
        label, _, rest = full.partition("—")
        label, heading = label.strip(), heading or rest.strip()
    elif not heading:
        heading = full.partition("—")[2].strip()
    word, _, number = label.partition(" ")
    number = number.strip()
    if word.lower() not in UNITS or " " in number:
        # older schedule headings: "The Schedule", "First Schedule—...", "Schedules—The First Schedule"
        m = SCHEDULE.match(full)
        if m:
            no = str(ORDINAL[m.group("ord").lower()]) if m.group("ord") else (m.group("no") or "")
            n = Node(level="Schedule", label=f"Schedule {no}".strip(), number=no,
                     heading=(m.group("head") or "").strip(" —-"), token=f"SCH{_tok(no)}")
            return n
    if word.lower() not in UNITS or " " in number:
        # a heading that is not a unit ("Guide to Division 245", "Operative provisions"): kept in the path, no
        # level (so it is never the chapter name) and no act_id token
        return Node(level="", label=full, heading="", token="")
    level = word.capitalize()
    n = Node(level=level, label=f"{level} {number}".strip(), number=number, heading=heading,
             token=f"{UNITS[level.lower()][0]}{_tok(number)}")
    if REPEALED.match(heading):
        n.status = "repealed"
    return n


def _cell(td) -> str:
    ps = [_clean(p.text_content()) for p in td.iter("p")]
    return " ".join(p for p in ps if p) if ps else _clean(td.text_content())


def _chain(path, leaf: Node) -> str:
    return "_".join([n.token for n in path if n.token] + [leaf.token])


def _qualifier(path) -> str:
    """The nearest unit above a leaf, in citation words: ``pt 1.5``."""
    for n in reversed(path):
        if n.level in ("Chapter", "Part", "Division", "Subdivision") and n.number:
            return f"{UNITS[n.level.lower()][1]} {n.number}"
    return ""


def _dups(root: Node) -> list[str]:
    """The leaves whose number the Act has used before (in document order, within the same schedule or body)."""
    seen: set[tuple] = set()
    out = []
    for path, leaf in root.leaves():
        if leaf.level not in ("Section", "Clause"):
            continue
        sch = next((n.number for n in path if n.level == "Schedule"), None)
        key = (sch, leaf.level, leaf.number)
        if key in seen:
            out.append(_chain(path, leaf))
        seen.add(key)
    return out


def _finish(root: Node) -> None:
    """Clauses for the leaves of a schedule that has no Chapters or Divisions (and no Division-style numbers such
    as 255-5); units and sections with no text at all (headings of repealed provisions) pruned."""
    def walk(n: Node) -> None:
        if n.level == "Schedule":
            desc = list(_descendants(n))
            sections = bool({d.level for d in desc} & {"Chapter", "Division", "Subdivision"}) or any(
                "-" in d.number for d in desc if d.level == "Section")
            for d in desc:
                if d.level != "Section":
                    continue
                if not sections:
                    d.level, d.label, d.token = "Clause", f"Clause {d.number}".strip(), "C" + d.token[1:]
                d.native_id = f"sch{n.number}/{'s' if d.level == 'Section' else 'cl'}{d.number}"
        for c in n.children:
            walk(c)
        n.children = [c for c in n.children if c.children or c.text]
    walk(root)


def _descendants(n: Node) -> Iterator[Node]:
    for c in n.children:
        yield c
        yield from _descendants(c)


def _tok(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9.\-]+", "", str(s or "")).upper()


def _long_date(iso: str) -> str:
    import datetime as dt
    d = dt.date.fromisoformat(iso[:10])
    return f"{d.day} {d.strftime('%B %Y')}"


ATTRIBUTION = attribution()
ATTRIBUTION_EN = ATTRIBUTION
EDIT_NOTE_EN = EDIT_NOTE


def law_summary(rows: list[dict], kept: int) -> dict:
    """One Act's row of the index's ``law`` table (countries.LAW_COLUMNS), from its rows file."""
    r = rows[0]
    title = (r.get("display_path") or "").split(" / ")[0]
    sections = sum(1 for x in rows if x.get("level") in ("Section", "Clause"))
    eli = r.get("eli") or ""
    head = eli.rpartition("/")[0] if "@" in eli.rpartition("/")[2] else eli
    return {"law_id": r.get("title_id") or (r.get("native_id") or "").split("#")[0], "title": title,
            "law_num": "", "law_type": "Act", "kind": r.get("kind") or "Act", "category": "", "abbrev": "",
            "kana": "", "promulgated": "", "enforced": r.get("compilation_date") or r.get("effective_from") or "",
            "revision_id": r.get("register_id") or "", "url": r.get("source_url") or "",
            "revision_url": LATEST_URL.format(t=r.get("title_id")) if r.get("title_id") else "",
            "status": "in_force", "rows": kept, "articles": sections, "suppl": 0, "main_only": 0, "revisions": 1,
            "future_revisions": 0, "in_api_list": 1, "number_en": "", "eli_work": head.rsplit("/", 1)[0]}


# ---------------------------------------------------------------------- the resumable pull
def _write_json(path: Path, data) -> None:
    tmp = path.with_name(path.name + ".part")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _write_lines(path: Path, items: Iterable[dict]) -> int:
    tmp = path.with_name(path.name + ".part")
    n = 0
    with open(tmp, "w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
            n += 1
    os.replace(tmp, path)
    return n


def read_lines(path: Path) -> Iterator[dict]:
    if not path.exists():
        return
    with open(path, encoding="utf-8") as f:
        for ln in f:
            ln = ln.strip()
            if ln:
                try:
                    yield json.loads(ln)
                except json.JSONDecodeError:            # a line cut by a kill: ignored, the Act is redone
                    continue


def write_notice(raw: Path = RAW, date: str | None = None) -> Path:
    import datetime as dt
    date = date or dt.date.today().isoformat()
    raw.mkdir(parents=True, exist_ok=True)
    p = raw / "LICENSE-NOTICE.txt"
    p.write_text(ATTRIBUTION_TEMPLATE.format(date=_long_date(date)) + "\n\nLicence: Creative Commons Attribution 4.0 "
                 "International (CC BY 4.0), https://creativecommons.org/licenses/by/4.0/ ; terms of use: " + TERMS_URL +
                 "\n\n" + EDIT_NOTE + "\n", encoding="utf-8")
    return p


def pull(limit: int | None = None, principal: bool | None = None, refresh_list: bool = False, raw: Path = RAW,
         log: Log = print, adapter: Australia | None = None, keep_epub: bool = True) -> dict:
    """Fetch and parse every Act in force (principal Acts first), one request per 10 s, resumable."""
    import datetime as dt
    a = adapter or Australia()
    for d in ("rows", "epub"):
        (raw / d).mkdir(parents=True, exist_ok=True)
    list_path = raw / "list.jsonl"
    if refresh_list or not list_path.exists():
        log("listing the Acts in force and their current compilations ...")
        acts = a.fetch_list(limit=None, log=log)
        _write_lines(list_path, acts)
        manifest(raw, list_fetched=a.today(), acts=len(acts), principal=sum(e["principal"] for e in acts))
    acts = list(read_lines(list_path))
    if principal is not None:
        acts = [e for e in acts if e["principal"] == principal]
    done: set[tuple[str, str]] = set()
    for p in read_lines(raw / "progress.jsonl"):
        if p.get("status") in ("ok", "empty", "no_compilation"):
            done.add((p["title_id"], p.get("register_id") or ""))
            if p.get("listed_register_id"):
                done.add((p["title_id"], p["listed_register_id"]))
    write_notice(raw)
    todo = [e for e in acts if (e["title_id"], e["register_id"]) not in done]
    left = len(todo)
    if limit:
        todo = todo[:limit]
    log(f"{len(acts)} Acts listed, {len(acts) - left} done, {left} left; fetching {len(todo)} at {a.pace:.0f} s "
        f"per request")
    t0 = time.time()
    n_ok = n_rows = n_bytes = 0
    with open(raw / "progress.jsonl", "a", encoding="utf-8") as prog:
        for i, e in enumerate(todo, 1):
            t1 = time.time()
            rec = {"title_id": e["title_id"], "register_id": e["register_id"], "name": e["name"],
                   "principal": e["principal"], "at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
            try:
                if not e["register_id"]:
                    rec.update(status="no_compilation")
                else:
                    ep = raw / "epub" / f"{e['register_id']}.epub"
                    if ep.exists() and ep.stat().st_size > 0:
                        body = ep.read_bytes()
                    else:
                        body, rid = a.fetch_epub(e["title_id"])
                        if rid and rid != e["register_id"]:         # a newer compilation since the list was read
                            rec["listed_register_id"] = e["register_id"]
                            e = {**e, "register_id": rid}
                            rec["register_id"] = rid
                            ep = raw / "epub" / f"{rid}.epub"
                        if keep_epub:
                            tmp = ep.with_name(ep.name + ".part")
                            tmp.write_bytes(body)
                            os.replace(tmp, ep)
                    doc = a.parse(body, e["title_id"], e)
                    rows = a.to_rows(doc)
                    out = raw / "rows" / f"{e['title_id']}.jsonl"
                    _write_lines(out, rows)
                    rec.update(status="ok" if rows else "empty", rows=len(rows), epub_bytes=len(body),
                               rows_bytes=out.stat().st_size, dropped_chars=doc.extra.get("dropped_chars", 0))
                    n_ok += 1
                    n_rows += len(rows)
                    n_bytes += len(body)
            except Exception as ex:                                  # recorded, retried on the next run
                rec.update(status="error", error=f"{type(ex).__name__}: {ex}"[:300])
            rec["secs"] = round(time.time() - t1, 1)
            prog.write(json.dumps(rec, ensure_ascii=False) + "\n")
            prog.flush()
            el = time.time() - t0
            log(f"[{i}/{len(todo)}] {e['title_id']} {rec.get('register_id', '')} {rec['status']} "
                f"rows={rec.get('rows', 0)} epub={rec.get('epub_bytes', 0)} {rec['secs']}s  {e['name'][:60]}")
            if i % 50 == 0 or i == len(todo):
                per = el / i
                log(f"-- {i} Acts in {el / 60:.1f} min ({per:.1f} s/Act), {n_rows} rows, {n_bytes / 2**20:.1f} MB "
                    f"ePub; {len(todo) - i} left, ETA {(len(todo) - i) * per / 3600:.1f} h")
                manifest(raw, **status(raw))
    summary = status(raw)
    manifest(raw, last_run=dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), **summary)
    return summary


def status(raw: Path = RAW) -> dict:
    latest: dict[str, dict] = {}
    for p in read_lines(raw / "progress.jsonl"):
        latest[p["title_id"]] = p
    acts = list(read_lines(raw / "list.jsonl"))
    by = {}
    for p in latest.values():
        by[p["status"]] = by.get(p["status"], 0) + 1
    ok = [p for p in latest.values() if p.get("status") == "ok"]       # (no stat per file: the bind mount is slow)
    dates = sorted((p.get("at") or "")[:10] for p in ok if p.get("at"))
    return {"listed": len(acts), "listed_principal": sum(e["principal"] for e in acts), "by_status": by,
            "fetched_from": dates[0] if dates else None, "fetched_to": dates[-1] if dates else None,
            "rows": sum(p.get("rows", 0) for p in latest.values() if p["status"] == "ok"),
            "rows_files": len(ok), "rows_mb": round(sum(p.get("rows_bytes", 0) for p in ok) / 2**20, 1),
            "epub_mb": round(sum(p.get("epub_bytes", 0) for p in latest.values()) / 2**20, 1),
            "errors": [p for p in latest.values() if p["status"] == "error"][:20]}


def manifest(raw: Path = RAW, **changes) -> dict:
    p = raw / "MANIFEST.json"
    m = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    m.update({"source": "Federal Register of Legislation", "licence": "CC BY 4.0", "terms": TERMS_URL,
              "attribution_template": ATTRIBUTION_TEMPLATE, "edit_note": EDIT_NOTE, "pace_seconds": Australia.pace},
             **changes)
    raw.mkdir(parents=True, exist_ok=True)
    _write_json(p, m)
    return m


def reparse(raw: Path = RAW, log: Log = print) -> dict:
    """Rebuild every rows file from the saved ePubs (no network): for a parser change."""
    a = Australia()
    acts = {e["title_id"]: e for e in read_lines(raw / "list.jsonl")}
    latest = {p["title_id"]: p for p in read_lines(raw / "progress.jsonl")}
    n = rows = 0
    with open(raw / "progress.jsonl", "a", encoding="utf-8") as prog:
        for p in latest.values():
            if p.get("status") not in ("ok", "empty"):
                continue
            ep = raw / "epub" / f"{p['register_id']}.epub"
            if not ep.exists():
                continue
            e = {**acts.get(p["title_id"], {}), "register_id": p["register_id"]}
            doc = a.parse(ep.read_bytes(), p["title_id"], e)
            doc.fetched = (p.get("at") or a.today())[:10]
            rs = a.to_rows(doc)
            out = raw / "rows" / f"{p['title_id']}.jsonl"
            _write_lines(out, rs)
            prog.write(json.dumps({**p, "status": "ok" if rs else "empty", "rows": len(rs),
                                   "rows_bytes": out.stat().st_size, "dropped_chars": doc.extra.get("dropped_chars", 0),
                                   "reparsed": a.today()}, ensure_ascii=False) + "\n")
            n += 1
            rows += len(rs)
    log(f"reparsed {n} Acts, {rows} rows")
    return {"acts": n, "rows": rows}


def main(argv: list[str] | None = None) -> int:
    """``python -m lexflow.corpus.countries.australia pull [--limit N] [--principal|--amending] [--refresh-list]``,
    ``status``, ``reparse``, ``sample <titleId>``."""
    import argparse
    ap = argparse.ArgumentParser(prog="lexflow.corpus.countries.australia")
    ap.add_argument("action", choices=["pull", "status", "reparse", "sample", "notice"])
    ap.add_argument("ids", nargs="*")
    ap.add_argument("--limit", type=int)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--principal", action="store_true")
    g.add_argument("--amending", action="store_true")
    ap.add_argument("--refresh-list", action="store_true")
    a = ap.parse_args(argv)

    def log(s: str) -> None:
        print(time.strftime("%H:%M:%S ") + s, flush=True)
    if a.action == "pull":
        out = pull(limit=a.limit, principal=True if a.principal else False if a.amending else None,
                   refresh_list=a.refresh_list, log=log)
        print(json.dumps(out, ensure_ascii=False, indent=1))
    elif a.action == "status":
        print(json.dumps(status(), ensure_ascii=False, indent=1))
    elif a.action == "reparse":
        reparse(log=log)
    elif a.action == "notice":
        print(write_notice())
    else:
        au = Australia()
        for tid in a.ids:
            doc = au.fetch_document(tid)
            rows = au.to_rows(doc)
            sys.stdout.write(json.dumps({"title_id": tid, "rows": len(rows), "first": rows[0] if rows else None},
                                        ensure_ascii=False)[:3000] + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
