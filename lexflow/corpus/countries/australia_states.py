"""Australia's states and territories: one adapter per register, keys ``aus-<abbr>`` (``aus-tas``, ``aus-sa`` ...),
rows in the Commonwealth's shape (australia.py: Part / Division / section, ``<Act> s <n>``, ``sch 1 cl 2``).

Read 22 October 2026 (docs/design/global-sources.md §2.3 and "Progress"):

* **Tasmania** (implemented, ``aus-tas``): https://www.legislation.tas.gov.au/ (the EnAct platform, as Queensland's
  and NSW's).  robots.txt disallows only ``/admin/`` and lists a sitemap and a crawler feed.  The browse page's own
  data source lists the Acts in force: ``/projectdata?ds=EnAct-BrowseDataSource&expression=PrintType=act.reprint
  AND Repealed<>Y AND Amending<>pure AND PitValid=@pointInTime(<yyyymmddhhmmss>)`` (609 on 22 Oct 2026), and every
  Act's current reprint is served as EnAct XML at ``/view/whole/xml/inforce/current/<id>`` (``act.dtd``: ``ACT >
  BODY / TAIL > PART / DIVISION / C.CHAPTER / SCHEDULE > SECTION / S.CLAUSE > SUBSECTION > PARAGRAPH``, numbers in
  attributes, amendment notes in ``HOWAFFECTED``).  Licence: "Unless otherwise noted, all material provided on this
  website is licensed under a Creative Commons Attribution 4.0 International licence (CC BY 4.0)"; changed material
  must say "Based on material from the Tasmanian Legislation website at [full date of download]. For the latest
  information on Tasmanian Government legislation please go to www.legislation.tas.gov.au." (``TAS_ATTRIBUTION``).
* **Western Australia** (``aus-wa``): https://www.legislation.wa.gov.au/ (Lotus Notes), CC BY 4.0 ("Based on
  content from the Western Australian Legislation website at [full date of download]. For the latest information on
  Western Australian legislation, visit www.legislation.wa.gov.au."), no robots.txt (404); Acts in force listed by
  letter (``actsif_<a..z>.html``), each Act's page (``law_<id>.html``) links its current consolidation as PDF, DOCX
  and Word-exported HTML (``RedirectURL?OpenAgent&query=mrdoc_<n>.htm``, one redirect to the file store).
* **South Australia** (``aus-sa``): the legislation site answers 403 to robots; DataSA (CKAN, CC BY 4.0) publishes
  the "Legislative Database Update Package (XML)": 236 fortnightly packages since 17 Nov 2017, each holding only the
  Acts and regulations changed since the last one as SAOPC exchange XML (``exdoc > content type=body > level
  type=part > level type=clause``); the whole database was published (RTF, not XML) until 23 Mar 2018 on DataSA and
  until July 2019 via Dropbox, then "To request an up-to-date version of this dataset, please email
  OPCWeb@sa.gov.au".  So the XML covers the Acts amended since November 2017; the rest needs the RTF snapshot or a
  request to the SA Parliamentary Counsel.
* **Queensland** (``aus-qld``): CC BY 4.0, but the API (https://api.legislation.qld.gov.au/) needs an account: not
  approved for lexflow; the sign-up steps are in docs/design/global-sources.md ("Progress").
* **New South Wales** (403 to every automated request), **Victoria** ("for personal use only"), **ACT** ("All
  rights reserved"; robots disallows ``/View/`` and ``/html/``), **Northern Territory** (own permission policy, not on
  the approval list): stubs that say what permission is needed.

The pull is resumable (``python -m lexflow.corpus.countries.australia_states pull aus-tas``): the list in
``data/raw/countries/<key>/list.jsonl``, the source files in ``src/``, one rows file per Act in ``rows/``, one line
per Act in ``progress.jsonl``; one request per 2 s.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Callable, Iterator

from ... import config
from .australia import Australia, UNITS, _dups, _finish, _long_date, _write_json, _write_lines, read_lines
from .base import Document, Node, Source

Log = Callable[[str], None]
TAS = "https://www.legislation.tas.gov.au"
TAS_ATTRIBUTION = ("Based on material from the Tasmanian Legislation website at {date}. For the latest information on "
                   "Tasmanian Government legislation please go to www.legislation.tas.gov.au.")
WA_ATTRIBUTION = ("Based on content from the Western Australian Legislation website at {date}. For the latest "
                  "information on Western Australian legislation, visit www.legislation.wa.gov.au.")
EDIT_NOTE = ("lexflow split each Act into sections and added the heading path for search; the section text is the "
             "register's, with the numbers of subsections and paragraphs written out as the register shows them. "
             "lexflow's index is not made or endorsed by the State.")
# C1 controls left by Windows-1252 numeric references in the EnAct XML (&#150; is an en dash)
_C1 = {i: bytes([i]).decode("cp1252", errors="ignore") or " " for i in range(0x80, 0xA0)}


class State(Australia):
    """A state or territory register: the Commonwealth adapter's citations, slugs and rows, its own source."""
    parent = "aus"
    status = "stub"
    pace = 2.0
    attribution_template = ""
    abbr = ""
    note = ""

    @property
    def raw_name(self) -> str:                  # countries.path_for: data/raw/countries/<key>/rows
        return f"{self.code}/rows"

    def _refuse(self):
        raise NotImplementedError(f"{self.name}: {self.note}")

    def fetch_list(self, limit: int | None = 20, **kw) -> list[dict]:
        self._refuse()

    def fetch_document(self, native_id: str, meta: dict | None = None) -> Document:
        self._refuse()

    def fetch_raw(self, entry: dict) -> bytes:
        self._refuse()

    def parse(self, raw, native_id: str = "", meta: dict | None = None) -> Document:
        self._refuse()

    def attribution(self, date: str) -> str:
        return self.attribution_template.format(date=_long_date(date)) if self.attribution_template else ""

    def src_path(self, entry: dict) -> Path:
        """Where the pull keeps an Act's source file: one file per version, so a reparse needs no network."""
        return raw_dir(self) / "src" / f"{_safe(entry['native_id'])}@{_safe(entry.get('version') or 'v')}{a_ext(self)}"

    def _doc(self, meta: dict, root: Node, url: str, extra: dict | None = None) -> Document:
        name = meta.get("name") or ""
        start = meta.get("start") or None
        token = _tok(meta["native_id"])
        token = f"A{token}" if token[:1].isdigit() else token       # a digit would join the state token
        doc = Document(country=self.code, native_id=meta["native_id"], kind="Act", kind_token=token,
                       number=f"No. {int(meta['number'])} of {meta['year']}" if str(meta.get("number") or "").isdigit()
                       and meta.get("year") else "", title=name, short_title=name, language="en",
                       year=str(meta.get("year") or ""), eli_type="act",
                       eli_number=str(int(meta["number"])) if str(meta.get("number") or "").isdigit() else "",
                       url=url, status="in_force", version_date=start, promulgated=meta.get("assent"),
                       last_amended_year=int(start[:4]) if start else None, fetched=self.today(),
                       source=self.sources[0].name, licence=self.sources[0].licence)
        _finish(root)
        doc.root = root
        doc.extra = {"dups": _dups(root), "title_id": meta["native_id"], "register_id": meta.get("version") or "",
                     "compilation_number": meta.get("suffix"), "compilation_date": start,
                     "attribution": self.attribution(doc.fetched), **(extra or {})}
        return doc


# ---------------------------------------------------------------------- the EnAct platform (Tasmania; QLD, NSW)
UNIT_TAGS = {"PART": ("Part", "PARTNO"), "DIVISION": ("Division", "DIVNO"), "SUBDIVISION": ("Subdivision", "SUBDIVNO"),
             "C.CHAPTER": ("Chapter", "CHAPNO"), "CHAPTER": ("Chapter", "CHAPNO"),
             "SCHEDULE": ("Schedule", "SCHEDULENO"), "APPENDIX": ("Appendix", "APPENDIXNO")}
LEAF_TAGS = {"SECTION": ("Section", "SECNO"), "S.CLAUSE": ("Clause", "CLAUSENO")}
NUMBERED = {"SUBSECTION": "SUBSECNO", "PARAGRAPH": "PARANO", "SUBPARAGRAPH": "SUBPARANO",
            "SUBSUBPARAGRAPH": "SUBSUBPARANO", "S.SUBCLAUSE": "SUBCLAUSENO", "S.PARAGRAPH": "PARANO",
            "S.SUBPARAGRAPH": "SUBPARANO", "S.SUBSUBPARAGRAPH": "SUBSUBPARANO"}
LABELS = {"PENALTY": "Penalty: ", "CHARGE": "Charge: "}
SKIP = {"HOWAFFECTED", "FRAGSPEC", "HEADNOTE", "HEADING", "GRAPHIC", "CREST", "SECTREF", "COLSPEC"}


class EnActState(State):
    """A register on the EnAct platform: the browse data source for the list, the whole Act as EnAct XML."""
    site = ""

    def fetch_list(self, limit: int | None = None, log: Log | None = None, **kw) -> list[dict]:
        when = dt.datetime.now().strftime("%Y%m%d") + "000000"
        expr = ("PrintType=act.reprint AND Repealed<>Y AND Amending<>pure AND PitValid=@pointInTime(" + when + ")")
        from urllib.parse import urlencode
        q = urlencode({"ds": "EnAct-BrowseDataSource", "expression": expr, "start": 1, "count": 5000,
                       "sortField": "new.sort.title", "sortDirection": "asc"})
        data = self.fetch(f"{self.site}/projectdata?{q}", accept="application/json").json()
        out = []
        for x in data.get("data", []):
            v = lambda k: (x.get(k) or {}).get("__value__") if isinstance(x.get(k), dict) else x.get(k)  # noqa: E731
            out.append({"native_id": v("id"), "name": (v("title") or "").strip(), "year": v("year"),
                        "number": v("no"), "assent": (v("assent.date") or "")[:10] or None,
                        "start": (v("first.valid.date") or "")[:10] or None, "version": v("version.desc.id"),
                        "series": v("version.series.id"), "published": (v("publication.date") or "")[:10] or None})
        if log:
            log(f"{self.name}: {len(out)} Acts in force listed (server count "
                f"{(data.get('totalCount') or {}).get('__value__')})")
        return out[:limit] if limit else out

    def fetch_raw(self, entry: dict) -> bytes:
        return self.fetch(f"{self.site}/view/whole/xml/inforce/current/{entry['native_id']}",
                          accept="application/xml").content

    def fetch_document(self, native_id: str, meta: dict | None = None) -> Document:
        meta = meta or next((e for e in self.fetch_list(None) if e["native_id"] == native_id), {"native_id": native_id})
        return self.parse(self.fetch_raw(meta), native_id, meta)

    def page_url(self, meta: dict) -> str:
        when = meta.get("start") or "current"
        return f"{self.site}/view/whole/html/inforce/{when}/{meta['native_id']}"

    def parse(self, raw, native_id: str = "", meta: dict | None = None) -> Document:
        import lxml.etree as ET
        parser = ET.XMLParser(load_dtd=False, no_network=True, resolve_entities=False, recover=True, huge_tree=True)
        act = ET.fromstring(raw if isinstance(raw, bytes) else raw.encode("utf-8"), parser)
        meta = dict(meta or {})
        meta.setdefault("native_id", native_id or act.get("ID") or "")
        meta.setdefault("name", _clean(act.get("TITLE") or ""))
        meta.setdefault("year", act.get("YEAR"))
        meta.setdefault("number", act.get("ACTNO"))
        meta.setdefault("start", act.get("FIRST.VALID.DATE"))
        meta.setdefault("assent", act.get("ASSENT.DATE"))
        meta.setdefault("version", act.get("VERSION.DESC.ID"))
        root = Node(level="Act", label=meta["name"], heading=meta["name"], native_id=meta["native_id"])
        for part in act:
            if part.tag in ("BODY", "TAIL"):
                _enact_walk(part, root)
        lt = act.find("FRONT/LONGTITLE")
        return self._doc(meta, root, self.page_url(meta),
                         {"long_title": _render(lt) if lt is not None else "", "print_type": act.get("PRINT.TYPE")})


def _enact_walk(el, parent: Node) -> None:
    for ch in el:
        t = ch.tag if isinstance(ch.tag, str) else ""
        if t in UNIT_TAGS:
            level, attr = UNIT_TAGS[t]
            no = (ch.get(attr) or "").strip()
            unit = Node(level=level, label=f"{level} {no}".strip(), number=no, heading=_inline(ch.find("HEADING")),
                        token=f"{UNITS[level.lower()][0]}{_tok(no)}", native_id=ch.get("ID") or "")
            if (ch.get("OMITTED") or "NOOMIT") != "NOOMIT":
                unit.status = "repealed"
            parent.children.append(unit)
            _enact_walk(ch, unit)
            if not unit.children:                       # a schedule of tables or forms: one row for the unit
                unit.text = _render(ch)
        elif t in LEAF_TAGS:
            level, attr = LEAF_TAGS[t]
            no = (ch.get(attr) or "").strip()
            leaf = Node(level=level, label=f"{level} {no}".strip(), number=no, heading=_inline(ch.find("HEADNOTE")),
                        text=_render(ch), token=f"{'S' if level == 'Section' else 'C'}{_tok(no)}",
                        native_id=ch.get("ID") or "")
            if (ch.get("OMITTED") or "NOOMIT") != "NOOMIT":
                leaf.status = "repealed"
            parent.children.append(leaf)
        elif t in ("BODY", "TAIL", "AMENDGROUP"):
            _enact_walk(ch, parent)


def _render(el) -> str:
    """The text of a provision as the register shows it, one line per block: ``(1) In this Act –``, ``(a) dies;
    or``, ``abandoned means ...``, ``Penalty: Fine not exceeding 50 penalty units.``, table rows ``a | b``."""
    lines: list[str] = []
    pending = [""]

    def emit(raw: str) -> None:
        s = _clean(pending[0] + raw)
        pending[0] = ""
        if s:
            lines.append(s)

    def go(e) -> None:
        for ch in e:
            t = ch.tag if isinstance(ch.tag, str) else ""
            if not t or t in SKIP:
                continue
            if t in NUMBERED:
                no = (ch.get(NUMBERED[t]) or "").strip()
                if no:
                    pending[0] += f"({no}) "
                go(ch)
            elif t in LABELS:
                pending[0] += LABELS[t]
                go(ch)
            elif t == "TEXT":
                emit("".join(ch.itertext()))
            elif t == "DEFINEDTERM":
                pending[0] += "".join(ch.itertext())
            elif t == "ROW":
                emit(" | ".join(_inline(x) for x in ch if isinstance(x.tag, str) and x.tag == "ENTRY"))
            elif len(ch):
                go(ch)
            else:
                emit("".join(ch.itertext()))
        return None

    go(el)
    if pending[0].strip():
        emit("")
    return "\n".join(lines)


def _inline(el) -> str:
    return _clean("".join(el.itertext())) if el is not None else ""


def _clean(s: str) -> str:
    s = (s or "").translate(_C1).replace("\xa0", " ").replace("‑", "-").replace("​", "")
    return re.sub(r"\s+", " ", s).strip()


def _tok(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9.\-]+", "", str(s or "")).upper().replace("-", "")


# ---------------------------------------------------------------------- the registers
class Tasmania(EnActState):
    code = "aus-tas"
    abbr = "tas"
    eli_jurisdiction = "au-tas"
    name = "Tasmania"
    wikidata = "Q34366"
    code_label = "Tasmanian Acts (Tasmanian Legislation Online)"
    site = TAS
    status = "prototype"
    attribution_template = TAS_ATTRIBUTION
    note = "Tasmanian Legislation Online: the EnAct browse data source for the list, EnAct XML per Act"
    sources = (
        Source(name="Tasmanian Legislation Online", publisher="Office of Parliamentary Counsel (Tasmania)",
               url="https://www.legislation.tas.gov.au/", holds="Tasmanian Acts and statutory rules in force, as made, "
               "repealed; 609 Acts in force (22 Oct 2026)", format="EnAct XML (act.dtd), HTML, PDF",
               access="browse data source /projectdata?ds=EnAct-BrowseDataSource; /view/whole/xml/inforce/current/<id>; "
                      "sitemap and crawler feed (/feed?id=crawler)",
               identifier="Tasmanian legislation id (act-1997-082)", licence="Unless otherwise noted, all material "
               "provided on this website is licensed under a Creative Commons Attribution 4.0 International licence "
               "(CC BY 4.0).", licence_url="https://www.legislation.tas.gov.au/copyrightanddisclaimer",
               languages=("en",), verified="2026-10-22",
               automated_reading="allowed with the prescribed attribution; robots.txt disallows /admin/ only"),
    )


WA = "https://www.legislation.wa.gov.au/legislation/statutes.nsf/"
WA_LEVEL = {"Heading1": 1, "Heading2": 2, "Heading3": 3, "Heading4": 4, "Heading5": 5, "yScheduleHeading": 1,
            "yHeading1": 2, "yHeading2": 2, "yHeading3": 3, "yHeading4": 4, "yHeading5": 5}
WA_SKIP = ("TOC", "Footnote", "yFootnote", "Ednote", "yEdnote", "yShoulderClause", "NoteHeading", "WA",
           "NameofAct", "Arrangement", "BlankOpen", "BlankClose", "LongTitle", "Footnotelongtitle", "CentredBaseLine")
ORDINAL = {w: i for i, w in enumerate(("first second third fourth fifth sixth seventh eighth ninth tenth eleventh "
                                       "twelfth thirteenth fourteenth fifteenth sixteenth seventeenth eighteenth "
                                       "nineteenth twentieth").split(), 1)}
_MARK = re.compile(r"^(\((?:[0-9]+[A-Za-z]*|[a-z]{1,2}[A-Z]?|[ivxlc]+|[A-Z]{1,2})\))(?=\S)")


class WesternAustralia(State):
    """Western Australian Legislation: the Acts-in-force letter pages for the list, each Act's page for the current
    consolidation (currency start, version suffix, Act number), the consolidation's Word-exported HTML for the text
    (the same paragraph styles as the Word file: ``Heading2`` Part, ``Heading3`` Division, ``Heading5`` section with
    ``CharSectno``, ``Subsection`` / ``Indenta`` / ``Defstart`` text, ``y*`` inside schedules, ``Footnote*`` and
    ``Ednote*`` the amendment notes, ``nHeading2`` the endnotes)."""
    code = "aus-wa"
    abbr = "wa"
    eli_jurisdiction = "au-wa"
    name = "Western Australia"
    wikidata = "Q3206"
    code_label = "Western Australian Acts (Western Australian Legislation)"
    status = "prototype"
    attribution_template = WA_ATTRIBUTION
    note = "Western Australian Legislation: letter pages, the Act's page and its consolidation's HTML"
    sources = (
        Source(name="Western Australian Legislation", publisher="Parliamentary Counsel's Office (WA)",
               url="https://www.legislation.wa.gov.au/", holds="WA Acts and subsidiary legislation, in force and ceased",
               format="HTML (Word export), PDF, DOCX", access="website (Lotus Notes .nsf pages: actsif_<letter>.html, "
               "law_<id>.html, RedirectURL?OpenAgent&query=mrdoc_<n>.htm); no API; robots.txt 404",
               identifier="WA law id (a1) and consolidation document id (mrdoc_49436), version suffix (05-e0-00)",
               licence="the State of Western Australia's copyright material available on this website (Licensed "
               "Material) is licensed under a Creative Commons Attribution 4.0 International Licence (CC BY 4.0).",
               licence_url="https://www.legislation.wa.gov.au/legislation/statutes.nsf/copyright.html",
               languages=("en",), verified="2026-10-22",
               automated_reading="allowed with the prescribed attribution; no robots.txt"),
    )

    def fetch_list(self, limit: int | None = None, log: Log | None = None, **kw) -> list[dict]:
        idx = self.fetch(WA + "actsif.html").content.decode("utf-8", "replace")
        letters = sorted(set(re.findall(r"actsif_([a-z])\.html", idx)))
        out, seen = [], set()
        for l in letters:
            t = self.fetch(WA + f"actsif_{l}.html").content.decode("utf-8", "replace")
            for lid, title, no, rest in re.findall(r"<tr><td><a href='law_([a-z]\d+)\.html[^']*'[^>]*>(.*?)</a></td>"
                                                   r"<td>(.*?)</td>(.*?)</tr>", t, flags=re.S):
                if lid in seen:
                    continue
                seen.add(lid)
                m = re.search(r"mrdoc_(\d+)\.htm", rest)
                n = re.match(r"\s*0*(\d+)\s+of\s+(\d{4})", _clean(_strip_tags(no)))
                out.append({"native_id": lid, "name": _clean(_strip_tags(title)), "act_no": _clean(_strip_tags(no)),
                            "number": n.group(1) if n else None, "year": n.group(2) if n else None,
                            "version": f"mrdoc_{m.group(1)}" if m else ""})
            if log:
                log(f"{self.name}: letter {l}: {len(out)} Acts so far")
        return out[:limit] if limit else out

    def fetch_raw(self, entry: dict) -> bytes:
        """The Act's page and its current consolidation's HTML, as one JSON envelope (the redirect to the file store
        is followed, then the pace is kept once more, so the average stays one request per ``pace`` seconds)."""
        law = self.fetch(WA + f"law_{entry['native_id']}.html&view=consolidated").content.decode("utf-8", "replace")
        m = re.search(r"mrdoc_(\d+)\.htm", law)
        doc_id = m.group(1) if m else (entry.get("version") or "").replace("mrdoc_", "")
        if not doc_id:
            raise ValueError("no current consolidation on the Act's page")
        r = self.fetch(WA + f"RedirectURL?OpenAgent&query=mrdoc_{doc_id}.htm", accept="text/html")
        time.sleep(self.pace)
        return json.dumps({"law": law, "doc": r.content.decode("utf-8", "replace"), "doc_url": r.url,
                           "mrdoc": doc_id}, ensure_ascii=False).encode("utf-8")

    def fetch_document(self, native_id: str, meta: dict | None = None) -> Document:
        meta = meta or {"native_id": native_id}
        return self.parse(self.fetch_raw(meta), native_id, meta)

    def parse(self, raw, native_id: str = "", meta: dict | None = None) -> Document:
        import lxml.html
        env = json.loads(raw) if (raw[:1] in (b"{", "{")) else {"law": "", "doc": raw.decode("utf-8", "replace")
                                                                    if isinstance(raw, bytes) else raw}
        meta = dict(meta or {}, native_id=native_id or (meta or {}).get("native_id", ""))
        law = env.get("law") or ""
        cur = re.search(r"<tr><td>[^<]*</td><td>(\d{1,2} \w{3} \d{4})</td><td class='current'>Current</td>"
                        r"<td>([^<]*)</td>", law)
        if cur:
            meta["start"] = dt.datetime.strptime(cur.group(1), "%d %b %Y").date().isoformat()
            meta["suffix"] = cur.group(2).strip()
        h1 = re.search(r"<h1>(.*?)</h1>", law)
        if h1 and not meta.get("name"):
            meta["name"] = _clean(_strip_tags(h1.group(1)))
        no = re.search(r"<th>Act No:</th><td>\s*0*(\d+) of (\d{4})</td>", law)
        if no:
            meta["number"], meta["year"] = no.group(1), no.group(2)
        ad = re.search(r"<th>Assent Date:</th><td>(\d{1,2} \w{3} \d{4})</td>", law)
        if ad:
            meta["assent"] = dt.datetime.strptime(ad.group(1), "%d %b %Y").date().isoformat()
        if env.get("mrdoc"):
            meta["version"] = f"mrdoc_{env['mrdoc']}"
        tree = lxml.html.fromstring(env["doc"].encode("utf-8"), parser=lxml.html.HTMLParser(encoding="utf-8"))
        root = Node(level="Act", label=meta.get("name", ""), heading=meta.get("name", ""), native_id=meta["native_id"])
        long_title = _wa_build(root, tree)
        url = WA + f"law_{meta['native_id']}.html&view=consolidated"
        return self._doc(meta, root, url, {"long_title": long_title, "doc_url": env.get("doc_url"),
                                           "version_suffix": meta.get("suffix")})


def _strip_tags(s: str) -> str:
    import html as H
    return H.unescape(re.sub(r"<[^>]+>", "", s or ""))


def _wa_cls(el) -> str:
    c = (el.get("class") or "").strip()
    return c[:-2] if c.endswith(("-P", "-H", "-C", "-R")) else c


def _wa_build(root: Node, tree) -> str:
    """Walk a WA consolidation's paragraphs into ``root``; returns the long title."""
    for s in list(tree.iter("span")):                 # raised footnote references ("Act 2004 ¹") are not text
        if re.search(r"top:\s*-", s.get("style") or ""):
            s.drop_tree()
    blocks, in_table = [], set()
    for t in tree.iter("table"):
        for p in t.iter("p"):
            in_table.add(p)
    for el in tree.iter("p", "tr"):
        if el.tag == "p" and el in in_table:
            continue
        blocks.append(el)
    cls = [_wa_cls(b) if b.tag == "p" else "" for b in blocks]
    first = next((i for i, c in enumerate(cls) if c in WA_LEVEL), None)
    if first is None:
        return ""
    tocs = [i for i, c in enumerate(cls[:first]) if re.match(r"TOC\d", c)]
    begin = tocs[-1] + 1 if tocs else 0
    long_title = next((_clean(b.text_content()) for b, c in zip(blocks, cls) if c == "LongTitle"), "")
    stack: list[tuple[int, Node]] = []
    current: Node | None = None
    lines: dict[int, list[str]] = {}
    nodes: dict[int, Node] = {}
    for b, c in zip(blocks[begin:], cls[begin:]):
        if c.startswith("nHeading"):                 # the endnotes
            break
        if b.tag == "tr":
            cells = [" ".join(_clean(p.text_content()) for p in td.iter("p")) or _clean(td.text_content())
                     for td in b if td.tag in ("td", "th")]
            text = " | ".join(x for x in cells if x)
        else:
            if c in WA_LEVEL:
                d = WA_LEVEL[c]
                if d == 5:
                    current = _wa_section(b)
                    (stack[-1][1] if stack else root).children.append(current)
                    nodes[id(current)] = current
                    continue
                while stack and stack[-1][0] >= d:
                    stack.pop()
                unit = _wa_unit(b, schedule=c == "yScheduleHeading")
                (stack[-1][1] if stack else root).children.append(unit)
                nodes[id(unit)] = unit
                stack.append((d, unit))
                current = None
                continue
            if c.startswith(WA_SKIP) or c.startswith("nz"):
                continue
            text = _clean(b.text_content())
        text = _MARK.sub(r"\1 ", text)
        text = re.sub(r" ([.,;:])(?=\s|$)", r"\1", text)         # the space a dropped footnote mark leaves
        if not text:
            continue
        target = current if current is not None else (stack[-1][1] if stack else None)
        if target is not None:
            lines.setdefault(id(target), []).append(text)
    for k, ls in lines.items():
        n = nodes[k]
        if n.level in ("Section", "Clause") or not n.children:
            n.text = "\n".join(ls)
    return long_title


def _wa_section(p) -> Node:
    nos = [s for s in p.iter("span") if _wa_cls(s) == "CharSectno"]
    full = _clean(p.text_content())
    number = _clean("".join(s.text_content() for s in nos)) if nos else ""
    if not number:
        m = re.match(r"^(\d+[A-Za-z]*(?:\.\d+[A-Za-z]*)?)\.", full)
        number = m.group(1) if m else ""
    heading = re.sub(r"^" + re.escape(number) + r"\.?\s*", "", full) if number else full
    return Node(level="Section", label=f"Section {number}".strip(), number=number, heading=heading.strip(),
                token=f"S{_tok(number)}" if number else "S", native_id=f"s{number}" if number else "")


def _wa_unit(p, schedule: bool = False) -> Node:
    full = _clean(p.text_content())
    label, _, heading = full.partition(" — ")
    if not heading:
        label, _, heading = full.partition("—")
    label, heading = label.strip(), heading.strip()
    words = label.split()
    level, number = "", ""
    if words and words[0].lower() in UNITS:
        level, number = words[0].capitalize(), " ".join(words[1:])
    elif len(words) >= 2 and words[1].lower() == "schedule" and words[0].lower() in ORDINAL:   # "First Schedule"
        level, number = "Schedule", str(ORDINAL[words[0].lower()])
    elif schedule and words and words[0].lower() == "schedule":
        level, number = "Schedule", " ".join(words[1:])
    elif schedule:
        level, number = "Schedule", ""
    if not level:
        return Node(level="", label=full, token="")
    return Node(level=level, label=label, number=number, heading=heading,
                token=f"{UNITS[level.lower()][0]}{_tok(number)}")


SA_PACKAGE = "https://data.sa.gov.au/data/api/3/action/package_show?id=database-update-package-xml"
SA_DATASET = "https://data.sa.gov.au/data/dataset/database-update-package-xml"
SA_ATTRIBUTION = ("Based on the South Australian Legislative Database Update Package (XML), Attorney-General's "
                  "Department (South Australia), data.sa.gov.au, licensed under CC BY 4.0, downloaded {date}.")
SA_UNITS = {"part": "Part", "division": "Division", "subdivision": "Subdivision", "chapter": "Chapter",
            "schedule": "Schedule", "appendix": "Appendix"}


class SouthAustralia(State):
    """South Australia from DataSA's fortnightly XML update packages (CC BY 4.0): every package is read in date
    order and the newest XML of each Act kept (``src/<year>.<number>.xml``); the Acts not amended since November 2017
    are in no package, so they are missing until the Parliamentary Counsel supplies a full export."""
    code = "aus-sa"
    abbr = "sa"
    eli_jurisdiction = "au-sa"
    name = "South Australia"
    wikidata = "Q35715"
    code_label = "South Australian Acts (Legislative Database, DataSA)"
    status = "prototype"
    attribution_template = SA_ATTRIBUTION
    note = ("DataSA XML update packages (deltas since 17 Nov 2017): the Acts amended since then; a full current export "
            "is to be requested from OPCWeb@sa.gov.au")
    sources = (
        Source(name="Legislative Database Update Package (XML)", publisher="Attorney-General's Department (SA)",
               url=SA_DATASET, holds="the SA Acts and regulations changed in each fortnight, as SAOPC exchange XML; 236 "
               "packages from 17 Nov 2017 to 9 Oct 2026", format="XML (zip in zip: A.zip Acts, R.zip regulations)",
               access="CKAN API (package_show) and direct download", identifier="SA Act year.number (2008.19)",
               licence="license_id cc-by: Creative Commons Attribution 4.0 (CKAN metadata)",
               licence_url="http://creativecommons.org/licenses/by/4.0", languages=("en",), verified="2026-10-22",
               automated_reading="allowed (CC BY 4.0); the legislation site itself returns 403 to robots.txt"),
    )

    def packages(self) -> list[dict]:
        res = self.fetch(SA_PACKAGE, accept="application/json").json()["result"]["resources"]
        out = []
        for r in res:
            m = re.match(r"\s*(\d{1,2})\.(\d{1,2})\.(\d{4})", r.get("name") or "")
            if m:
                out.append({"date": f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}", "url": r["url"],
                            "id": r["id"], "size": r.get("size")})
        return sorted(out, key=lambda x: x["date"])

    def sync(self, log: Log = print) -> dict:
        """Read every package not read yet, oldest first, keeping the newest XML of each Act."""
        import io
        import zipfile
        raw = raw_dir(self)
        (raw / "src").mkdir(parents=True, exist_ok=True)
        acts_path = raw / "acts.json"
        acts = json.loads(acts_path.read_text(encoding="utf-8")) if acts_path.exists() else {}
        done = {p["id"] for p in read_lines(raw / "packages.jsonl") if p.get("status") == "ok"}
        pk = self.packages()
        todo = [p for p in pk if p["id"] not in done]
        log(f"{self.name}: {len(pk)} packages, {len(done)} read, {len(todo)} to read")
        with open(raw / "packages.jsonl", "a", encoding="utf-8") as prog:
            for i, p in enumerate(todo, 1):
                rec = {**p, "at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
                try:
                    body = self.fetch(p["url"], timeout=600).content
                    outer = zipfile.ZipFile(io.BytesIO(body))
                    inner = [n for n in outer.namelist() if re.fullmatch(r"(?i)(.*/)?a\.zip", n)]
                    n_acts, other = 0, set()
                    for name in inner:
                        z = zipfile.ZipFile(io.BytesIO(outer.read(name)))
                        for n in z.namelist():
                            m = re.match(r"^(?P<title>[^/]+)/Current/(?P<id>\d{4}\.[^/]+?)(?:\.un)?\.xml$", n)
                            if not m:
                                if n.lower().endswith(".xml"):
                                    other.add(n.split("/")[1] if n.count("/") > 1 else n)
                                continue
                            dest = raw / "src" / f"{_safe(m.group('id'))}.xml"
                            tmp = dest.with_name(dest.name + ".part")
                            tmp.write_bytes(z.read(n))
                            os.replace(tmp, dest)
                            acts[m.group("id")] = {"title": m.group("title"), "package": p["date"], "resource": p["url"]}
                            n_acts += 1
                    rec.update(status="ok", bytes=len(body), acts=n_acts, inner=inner, other=sorted(other)[:20])
                except Exception as ex:
                    rec.update(status="error", error=f"{type(ex).__name__}: {ex}"[:300])
                prog.write(json.dumps(rec) + "\n")
                prog.flush()
                _write_json(acts_path, acts)
                log(f"[{i}/{len(todo)}] package {p['date']} {rec['status']} acts={rec.get('acts', 0)} "
                    f"bytes={rec.get('bytes', 0)} total acts={len(acts)}")
        return {"packages": len(pk), "acts": len(acts)}

    def fetch_list(self, limit: int | None = None, log: Log | None = None, **kw) -> list[dict]:
        """The Acts with an XML in the packages; with a title index on disk (``titleindex-<date>.json``, the
        package's ``titleindex.pdf`` read into JSON), only those in force on its date."""
        log = log or (lambda s: None)
        self.sync(log)
        acts = json.loads((raw_dir(self) / "acts.json").read_text(encoding="utf-8"))
        index = self.title_index()
        out, dropped = [], []
        for aid, x in sorted(acts.items()):
            year, _, number = aid.partition(".")
            e = {"native_id": aid, "name": x["title"], "year": year, "number": number,
                 "version": x["package"], "resource": x["resource"]}
            if index and _norm_title(x["title"]) not in index:
                dropped.append(x["title"])
                continue
            if index:
                e["index_version"] = index[_norm_title(x["title"])]
            out.append(e)
        # the Acts read from the 2018 RTF snapshot (sa_baseline), still in force: listed so a pull keeps their rows
        xml = {e["native_id"] for e in out}
        for p in read_lines(raw_dir(self) / "progress.jsonl"):
            rtf = str(p.get("source", "")).startswith("rtf-") and p.get("status") == "ok"
            if rtf and p["native_id"] not in xml and (not index or _norm_title(p.get("name", "")) in index):
                year, _, number = p["native_id"].partition(".")
                out.append({"native_id": p["native_id"], "name": p.get("name"), "year": year, "number": number,
                            "version": p["version"], "resource": SA_BASELINE})
                xml.add(p["native_id"])
        if index:
            have = {_norm_title(e["name"]) for e in out}
            missing = sorted(t for t in index if t not in have)
            log(f"{self.name}: {len(out)} Acts in force with a text (XML, or the 2018 RTF); {len(dropped)} with XML "
                f"no longer in force; {len(missing)} in force without a text")
            _write_json(raw_dir(self) / "coverage.json", {"in_force": len(index), "with_xml": len(out),
                                                          "not_in_force": dropped, "missing_xml": missing})
        return out[:limit] if limit else out

    def title_index(self) -> dict[str, str]:
        """The newest ``titleindex-<date>.json``: normalised title -> version date, Acts only."""
        files = sorted(raw_dir(self).glob("titleindex-*.json"))
        if not files:
            return {}
        data = json.loads(files[-1].read_text(encoding="utf-8"))
        return {_norm_title(i["title"]): i["version"] for i in data.get("items", [])
                if i.get("section") == "South Australian Acts" and i.get("note") != "uncommenced"}

    def src_path(self, entry: dict) -> Path:
        return raw_dir(self) / "src" / f"{_safe(entry['native_id'])}.xml"

    def fetch_raw(self, entry: dict) -> bytes:
        return self.src_path(entry).read_bytes()

    def parse(self, raw, native_id: str = "", meta: dict | None = None) -> Document:
        import lxml.etree as ET
        parser = ET.XMLParser(load_dtd=False, no_network=True, resolve_entities=False, recover=True, huge_tree=True)
        x = ET.fromstring(raw if isinstance(raw, bytes) else raw.encode("utf-8"), parser)
        meta = dict(meta or {})
        meta["native_id"] = native_id or meta.get("native_id") or f"{x.get('year')}.{x.get('number')}"
        meta["name"] = _clean(x.get("title") or "").replace("&#x00A0;", " ") or meta.get("name", "")
        meta.setdefault("year", x.get("year"))
        meta.setdefault("number", x.get("number"))
        meta["start"] = x.get("first.valid.date") or meta.get("start")
        meta["assent"] = x.get("enact.or.made.date")
        status = (x.findtext(".//metadata[@class='inforce']/metacontent[@class='status']") or "").strip()
        principal = (x.findtext(".//metacontent[@class='principal']") or "").strip()
        root = Node(level="Act", label=meta["name"], heading=meta["name"], native_id=meta["native_id"])
        for c in x.findall("content"):
            if c.get("type") in ("body", "schedules"):
                _sa_walk(c, root)
        lt = x.find("content[@type='front']/tier[@type='longtitle']")
        doc = self._doc(meta, root, meta.get("resource") or SA_DATASET,
                        {"long_title": _sa_render(lt) if lt is not None else "", "inforce": status,
                         "principal": principal, "package": meta.get("version")})
        if "repeal" in status.lower():
            doc.status = "repealed"
        return doc


def _norm_title(t: str) -> str:
    """Titles as the packages' folder names and the title index both write them: no apostrophes (folder names
    drop them), dashes and other punctuation as spaces."""
    t = (t or "").lower().replace("’", "").replace("'", "").replace("\xa0", " ")
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def _sa_head(el) -> tuple[str, str]:
    h = el.find("head")
    if h is None:
        return "", ""
    return _inline(h.find("no")), _inline(h.find("heading"))


def _sa_walk(el, parent: Node) -> None:
    for ch in el:
        if not isinstance(ch.tag, str) or ch.tag != "level":
            continue
        t = ch.get("type") or ""
        no, heading = _sa_head(ch)
        if t == "clause":
            leaf = Node(level="Section", label=f"Section {no}".strip(), number=no, heading=heading,
                        text=_sa_render(ch), token=f"S{_tok(no)}", native_id=ch.get("id") or "")
            if (ch.get("status") or "inforce") not in ("inforce", ""):
                leaf.status = "repealed"
            parent.children.append(leaf)
        elif t in SA_UNITS:
            level = SA_UNITS[t]
            number = re.sub(rf"^{level}\s*", "", no, flags=re.I).strip()
            unit = Node(level=level, label=f"{level} {number}".strip(), number=number, heading=heading,
                        token=f"{UNITS[level.lower()][0]}{_tok(number)}", native_id=ch.get("id") or "")
            parent.children.append(unit)
            _sa_walk(ch, unit)
            if not unit.children:
                unit.text = _sa_render(ch)
        elif t == "indoc":                                # a law set out in a schedule (the National Gas Law)
            for c in ch.findall("content"):
                _sa_walk(c, parent)
        # leghistory and the editorial notes are not law text


def _sa_render(el) -> str:
    """A SAOPC provision as lines: ``(1) An industry board—``, ``(a) is a body corporate; and``, ``Maximum civil
    penalty: $10 000.``, table rows ``a | b``; nested levels are rendered in place."""
    lines: list[str] = []
    pending = [""]

    def emit(raw: str) -> None:
        s = _clean(pending[0] + raw)
        pending[0] = ""
        if s:
            lines.append(s)

    def go(e, top: bool = False) -> None:
        for ch in e:
            t = ch.tag if isinstance(ch.tag, str) else ""
            if not t or t in ("parentattributes", "attrib", "colspec", "graphic"):
                continue
            if t == "head":
                if top:                                   # the provision's own number and heading
                    continue
                no, heading = _inline(ch.find("no")), _inline(ch.find("heading"))
                pending[0] += (f"{no} " if no else "") + (f"{heading} " if heading else "")
            elif t == "no":
                pending[0] += _inline(ch) + " "
            elif t == "txt":
                emit("".join(ch.itertext()))
            elif t == "row":
                emit(" | ".join(_inline(x) for x in ch if isinstance(x.tag, str) and x.tag == "entry"))
            elif t == "level":
                no, heading = _sa_head(ch)
                if no or heading:
                    emit(f"{no} {heading}".strip())
                go(ch, top=True)
            elif len(ch):
                go(ch)
            else:
                emit("".join(ch.itertext()))

    go(el, top=True)
    if pending[0].strip():
        emit("")
    return "\n".join(lines)


# ---------------------------------------------------------------------- South Australia: the 2018 RTF snapshot
SA_BASELINE = ("https://data.sa.gov.au/data/dataset/675635f9-6831-457a-ba2e-52b4d49701f5/resource/1481c4a5-a64b-46ce-"
               "9b40-beb43fb94a5c/download/23.03.2018-acts-policies-and-proclamations.zip")
SA_BASELINE_DATE = "2018-03-23"
SA_HEADS = {"partheadlevel1": ("Part", 1), "divisionheadlevel2": ("Division", 2),
            "subdivisionheadlevel3": ("Subdivision", 3), "schedulehead": ("Schedule", 1)}
_RTF_SKIP = {"fonttbl", "colortbl", "stylesheet", "info", "pict", "header", "footer", "headerl", "headerr", "footerl",
             "footerr", "headerf", "footerf", "fldinst", "listtable", "listoverridetable", "rsidtbl", "generator",
             "xmlnstbl", "mmathPr", "themedata", "colorschememapping", "latentstyles", "datastore", "pgdsctbl",
             "bkmkstart", "bkmkend", "object", "shp", "shpinst", "nonshppict", "datafield", "filetbl", "revtbl",
             "wgrffmtfilter", "pnseclvl", "listtext", "ftnsep", "ftnsepc", "aftnsep", "aftnsepc", "footnote"}
_RTF_TOK = re.compile(r"\\([a-zA-Z]+)(-?\d+)? ?|\\'([0-9a-fA-F]{2})|\\(.)|([{}])|([^\\{}\r\n]+)|[\r\n]+")
_RTF_CHARS = {"emdash": "\u2014", "endash": "\u2013", "lquote": "\u2018", "rquote": "\u2019", "ldblquote": "\u201c",
              "rdblquote": "\u201d", "tab": "\t", "line": " ", "cell": " | ", "bullet": "\u2022"}


def _rtf_styles(rtf: str) -> dict[int, str]:
    i = rtf.find("{\\stylesheet")
    if i < 0:
        return {}
    depth, j = 0, i
    while j < len(rtf):
        if rtf[j] == "{":
            depth += 1
        elif rtf[j] == "}":
            depth -= 1
            if depth == 0:
                break
        j += 1
    out = {}
    for m in re.finditer(r"\{[^{}]*?\\s(\d+)\b([^{}]*?);\}", rtf[i:j]):
        name = re.sub(r"\\[a-zA-Z]+-?\d* ?", " ", m.group(2)).split()
        out[int(m.group(1))] = name[-1] if name else ""
    return out


def rtf_paragraphs(rtf: str) -> list[tuple[str, str]]:
    """An RTF document as (style name, text) paragraphs, tables as ``("ROW", "a | b")``: control words read, the
    destinations that hold no text (font and style tables, fields' instructions, pictures, headers and footers)
    skipped, ``\\'xx`` as Windows-1252, ``\\uN`` as Unicode."""
    st = _rtf_styles(rtf)
    stack = [{"skip": False, "uc": 1}]
    cur: list[str] = []
    style, out, pending = 0, [], 0

    def flush(kind: str | None = None) -> None:
        t = re.sub(r"[ \t\xa0]+", " ", "".join(cur)).strip(" |")
        if t:
            out.append((kind or st.get(style, ""), t))
        cur.clear()

    for m in _RTF_TOK.finditer(rtf):
        word, arg, hexc, sym, brace, text = m.groups()
        top = stack[-1]
        if brace == "{":
            stack.append(dict(top))
            continue
        if brace == "}":
            if len(stack) > 1:
                stack.pop()
            continue
        if top["skip"]:
            continue
        if sym == "*" or (word and word in _RTF_SKIP):
            top["skip"] = True
        elif word:
            if word == "pard":
                style = 0
            elif word == "s" and arg is not None:
                style = int(arg)
            elif word in ("par", "sect"):
                flush()
            elif word == "row":
                flush("ROW")
            elif word == "uc" and arg is not None:
                top["uc"] = int(arg)
            elif word == "u" and arg is not None:
                cur.append(chr(int(arg) % 65536))
                pending = top["uc"]
            elif word in _RTF_CHARS:
                cur.append(_RTF_CHARS[word])
        elif hexc:
            if pending:
                pending -= 1
            else:
                cur.append(bytes([int(hexc, 16)]).decode("cp1252", errors="replace"))
        elif sym:
            cur.append({"~": "\xa0", "_": "-", "-": ""}.get(sym, sym if sym in "\\{}" else ""))
        elif text:
            if pending:
                text, pending = text[pending:], 0
            cur.append(text)
    flush()
    return out


def sa_rtf_tree(rtf: str, title: str, native_id: str) -> tuple[Node, str]:
    """An SA RTF (the 2018 snapshot) -> the Part / Division / section tree, and the long title.  Headings carry
    the OPC styles (``partheadlevel1``, ``divisionheadlevel2``, ``subdivisionheadlevel3``, ``clauseheadlevel1-4`` for
    sections ``3—Interpretation``); schedules are unstyled ``Schedule 1—...`` lines; the body ends at
    ``leghistoryheadlevel1`` (the legislative history)."""
    ps = rtf_paragraphs(rtf)
    root = Node(level="Act", label=title, heading=title, native_id=native_id)
    first = next((i for i, (s, _) in enumerate(ps) if s.startswith(("partheadlevel", "clausehead", "clausegroup",
                                                                     "preamblehead"))), None)
    if first is None:
        return root, ""
    long_title = next((t for s, t in ps[:first] if t.startswith("An Act")), "")
    stack: list[tuple[int, Node]] = []
    current: Node | None = None
    for s, t in ps[first:]:
        if s.startswith(("leghistory", "historyhead")) or t == "Legislative history":
            break
        sched = re.match(r"^Schedule\s*(\d+[A-Z]?)?\s*[\u2014\-]\s*(.+)$", t) if s in ("", "schedulehead") else None
        if s in SA_HEADS or sched:
            level, depth = SA_HEADS.get(s, ("Schedule", 1))
            if sched:
                level, depth, number, heading = "Schedule", 1, sched.group(1) or "", sched.group(2)
            else:
                label, _, heading = t.partition("\u2014")
                number = re.sub(rf"^{level}\s*", "", label.strip(), flags=re.I)
            while stack and stack[-1][0] >= depth:
                stack.pop()
            unit = Node(level=level, label=f"{level} {number}".strip(), number=number, heading=heading.strip(),
                        token=f"{UNITS[level.lower()][0]}{_tok(number)}")
            (stack[-1][1] if stack else root).children.append(unit)
            stack.append((depth, unit))
            current = None
            continue
        if s.startswith(("clausehead", "clausegroup")):
            no, _, heading = t.partition("\u2014")
            current = Node(level="Section", label=f"Section {no.strip()}", number=no.strip(), heading=heading.strip(),
                           token=f"S{_tok(no)}")
            if re.search(r"\brepealed\b", heading, re.I) and len(heading) < 40:
                current.status = "repealed"
            (stack[-1][1] if stack else root).children.append(current)
            continue
        if s == "preamblehead":
            current = Node(level="Preamble", label="Preamble", token="PRE")
            root.children.append(current)
            continue
        target = current if current is not None else (stack[-1][1] if stack else None)
        if target is not None:
            target.text = (target.text + "\n" + t).strip()
    for n in list(_walk_units(root)):                  # a unit with sections keeps no text of its own
        if n.children:
            n.text = ""
    return root, long_title


def _walk_units(n: Node):
    for c in n.children:
        yield c
        yield from _walk_units(c)


def sa_baseline(a: "SouthAustralia", log: Log = print) -> dict:
    """The Acts in force that no XML package holds, from DataSA's last full snapshot on DataSA (23 March 2018, RTF,
    CC BY 4.0): only those whose current version (the title index) is not newer than the snapshot, so the 2018 text
    is today's.  Rows in ``rows/`` like the XML Acts', ``source`` = ``rtf-2018-03-23`` in progress.jsonl."""
    import zipfile
    raw = raw_dir(a)
    zpath = raw / "baseline" / "23.03.2018-acts-policies-and-proclamations.zip"
    if not zpath.exists():
        zpath.parent.mkdir(parents=True, exist_ok=True)
        body = a.fetch(SA_BASELINE, timeout=900).content
        tmp = zpath.with_name(zpath.name + ".part")
        tmp.write_bytes(body)
        os.replace(tmp, zpath)
    cov = json.loads((raw / "coverage.json").read_text(encoding="utf-8"))
    index = a.title_index()
    want = {t for t in cov.get("missing_xml", []) if index.get(t, "9999") <= SA_BASELINE_DATE}
    z = zipfile.ZipFile(zpath)
    found, n_rows = 0, 0
    with open(raw / "progress.jsonl", "a", encoding="utf-8") as prog:
        for name in z.namelist():
            m = re.match(r"^A/(?P<title>[^/]+)/Current/(?P<id>\d{4}\.[^/]+?)(?:\.un)?\.rtf$", name)
            if not m or _norm_title(m.group("title")) not in want:
                continue
            aid = m.group("id")
            title = m.group("title")
            year, _, number = aid.partition(".")
            meta = {"native_id": aid, "name": title, "year": year, "number": number,
                    "version": f"rtf-{SA_BASELINE_DATE}", "start": index.get(_norm_title(title)),
                    "resource": SA_BASELINE}
            root, long_title = sa_rtf_tree(z.read(name).decode("latin-1"), title, aid)
            doc = a._doc(meta, root, SA_BASELINE, {"long_title": long_title, "source_format": "rtf",
                                                   "snapshot": SA_BASELINE_DATE})
            rows = a.to_rows(doc) if root.children else []
            out = raw / "rows" / f"{_safe(aid)}.jsonl"
            _write_lines(out, rows)
            prog.write(json.dumps({"native_id": aid, "version": meta["version"], "name": title,
                                   "at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                                   "status": "ok" if rows else "empty", "rows": len(rows),
                                   "rows_bytes": out.stat().st_size, "source": f"rtf-{SA_BASELINE_DATE}"}) + "\n")
            found += 1
            n_rows += len(rows)
    log(f"{a.name}: {found} of {len(want)} Acts read from the {SA_BASELINE_DATE} RTF snapshot, {n_rows} rows")
    return {"wanted": len(want), "found": found, "rows": n_rows}


class Queensland(EnActState):
    code = "aus-qld"
    abbr = "qld"
    eli_jurisdiction = "au-qld"
    name = "Queensland"
    wikidata = "Q36074"
    code_label = "Queensland Acts (Queensland Legislation)"
    site = "https://www.legislation.qld.gov.au"
    note = ("CC BY 4.0, but the machine access lexflow was approved for is the API at https://api.legislation.qld."
            "gov.au/, which needs an account: the operator registers (docs/design/global-sources.md, Progress), then "
            "this adapter reads the same EnAct XML as Tasmania's")

    def fetch_list(self, limit=None, **kw):
        self._refuse()

    def fetch_raw(self, entry):
        self._refuse()

    def fetch_document(self, native_id, meta=None):
        self._refuse()

    sources = (
        Source(name="Queensland Legislation", publisher="Office of the Queensland Parliamentary Counsel",
               url="https://www.legislation.qld.gov.au/", holds="Queensland Acts and subordinate legislation in force, "
               "as passed/made, repealed; reprints", format="EnAct XML, HTML, PDF", access="API with registration "
               "(https://api.legislation.qld.gov.au/, Swagger); the website on the EnAct platform",
               identifier="OQPC document id (act-1994-005)", licence="Unless otherwise noted, all copyright material "
               "available on or through this website is licensed under a Creative Commons Attribution 4.0 "
               "International licence (CC BY 4.0).", licence_url="https://www.legislation.qld.gov.au/copyright",
               languages=("en",), verified="2026-10-22",
               automated_reading="allowed with attribution; API needs an account (Queensland Legislation API Access "
                                 "Agreement)"),
    )


class NewSouthWales(State):
    code = "aus-nsw"
    abbr = "nsw"
    eli_jurisdiction = "au-nsw"
    name = "New South Wales"
    wikidata = "Q3224"
    code_label = "NSW Acts (NSW Legislation)"
    note = ("legislation.nsw.gov.au answers HTTP 403 to every automated request (robots.txt included), so neither its "
            "terms nor its machine access can be read: ask the NSW Parliamentary Counsel's Office for API or bulk "
            "access and a reuse licence (the site runs the EnAct platform, so the Tasmanian XML reader would apply)")
    sources = (
        Source(name="NSW Legislation", publisher="Parliamentary Counsel's Office (NSW)",
               url="https://legislation.nsw.gov.au/", holds="NSW Acts and statutory instruments (not verified)",
               format="HTML, XML, PDF (reported)", access="none: HTTP 403 to every automated request, robots.txt "
               "included", identifier="NSW legislation id", licence="not readable (403)", languages=("en",),
               verified="2026-10-19", automated_reading="blocked at the edge; ask the PCO for access"),
    )


class Victoria(State):
    code = "aus-vic"
    abbr = "vic"
    eli_jurisdiction = "au-vic"
    name = "Victoria"
    wikidata = "Q36687"
    code_label = "Victorian Acts (Victorian Legislation)"
    note = ("the Government Printer's copyright notice permits authorised versions \"for personal use only\": a "
            "written licence from the Office of the Chief Parliamentary Counsel (Victoria) to reproduce the Acts in "
            "an index that quotes them, and permission for automated access, are needed first")
    sources = (
        Source(name="Victorian Legislation", publisher="Office of the Chief Parliamentary Counsel (Victoria)",
               url="https://www.legislation.vic.gov.au/", holds="Victorian Acts and statutory rules in force, as made, "
               "historical (1851-1995)", format="HTML, PDF, DOCX", access="website (Drupal); robots.txt Crawl-delay 2",
               identifier="Victorian legislation id", licence="The information on this website is copyright. No part "
               "may be reproduced by any process except in accordance with the provisions of the Copyright Act 1968 "
               "of the Commonwealth. ... Authorised electronic versions are published on this website ... for "
               "personal use only.", licence_url="https://www.legislation.vic.gov.au/copyright", languages=("en",),
               verified="2026-10-19", automated_reading="not granted: permission needed from the OCPC"),
    )


class AustralianCapitalTerritory(State):
    code = "aus-act"
    abbr = "act"
    eli_jurisdiction = "au-act"
    name = "Australian Capital Territory"
    wikidata = "Q3258"
    code_label = "ACT Acts (ACT Legislation Register)"
    note = ("the register is \"All rights reserved\" under the JACS copyright policy and robots.txt disallows the "
            "document views (/View/, /html/): a licence from the ACT Parliamentary Counsel's Office to reproduce the "
            "Acts, and permission for automated access, are needed first")
    sources = (
        Source(name="ACT Legislation Register", publisher="Parliamentary Counsel's Office (ACT)",
               url="https://www.legislation.act.gov.au/", holds="ACT Acts, subordinate laws, instruments, gazettes",
               format="HTML, PDF, DOCX", access="website; robots.txt Crawl-delay 10, /View/ and /html/ disallowed",
               identifier="ACT legislation id (A2001-14)", licence="Use of material on the ACT Legislation Register "
               "should be in accordance with the JACS Copyright Policy ... Copyright 2001 ACT Government. All rights "
               "reserved.", licence_url="https://www.legislation.act.gov.au/Static/Footerlinks/Copyright/copyright.html",
               languages=("en",), verified="2026-10-19", automated_reading="document views disallowed by robots.txt"),
    )


class NorthernTerritory(State):
    code = "aus-nt"
    abbr = "nt"
    eli_jurisdiction = "au-nt"
    name = "Northern Territory"
    wikidata = "Q3235"
    code_label = "NT Acts (NT Legislation)"
    note = ("the Territory's copyright policy of 8 October 1996 permits publication of its legislation on stated "
            "conditions, but NT is not on the approval list: the operator reads the conditions and approves first")
    sources = (
        Source(name="Northern Territory Legislation", publisher="Office of the Parliamentary Counsel (NT)",
               url="https://legislation.nt.gov.au/", holds="NT Acts and subordinate legislation, reprints, gazettes",
               format="HTML, PDF, DOCX", access="website; no API found", identifier="NT legislation id",
               licence="The Northern Territory grants permission to any person to publish or deal with any legislation "
                       "of the Northern Territory in accordance with the following conditions (copyright policy of "
                       "8 October 1996)", licence_url="https://legislation.nt.gov.au/en/Footer/Terms-of-Use",
               languages=("en",), verified="2026-10-19", automated_reading="permitted under the policy's conditions "
               "(read the conditions before a full pull)"),
    )


# ---------------------------------------------------------------------- the resumable pull of a state
def raw_dir(a: State) -> Path:
    return config.RAW_DIR / "countries" / a.code


def pull(a: State, limit: int | None = None, refresh_list: bool = False, log: Log = print) -> dict:
    """Fetch and parse every Act in force of one register, paced, resumable (``data/raw/countries/<key>/``)."""
    raw = raw_dir(a)
    for d in ("rows", "src"):
        (raw / d).mkdir(parents=True, exist_ok=True)
    lp = raw / "list.jsonl"
    if refresh_list or not lp.exists():
        acts = a.fetch_list(None, log=log)
        _write_lines(lp, acts)
        manifest(a, list_fetched=a.today(), acts=len(acts))
    acts = list(read_lines(lp))
    keep = {_safe(e["native_id"]) for e in acts}
    for f in (raw / "rows-not-listed").glob("*.jsonl") if (raw / "rows-not-listed").exists() else ():
        if f.stem in keep:                     # listed again (a corrected title match): back into the index
            os.replace(f, raw / "rows" / f.name)
    stale = [f for f in (raw / "rows").glob("*.jsonl") if f.stem not in keep]
    if stale:                                  # rows of Acts no longer listed (repealed): set aside, not indexed
        (raw / "rows-not-listed").mkdir(exist_ok=True)
        for f in stale:
            os.replace(f, raw / "rows-not-listed" / f.name)
        log(f"{a.name}: {len(stale)} rows files of Acts no longer listed moved to rows-not-listed/")
    done = {(p["native_id"], p.get("version") or "") for p in read_lines(raw / "progress.jsonl")
            if p.get("status") in ("ok", "empty")}
    todo = [e for e in acts if (e["native_id"], e.get("version") or "") not in done]
    left = len(todo)
    todo = todo[:limit] if limit else todo
    log(f"{a.name}: {len(acts)} Acts listed, {len(acts) - left} done, {left} left; fetching {len(todo)} at "
        f"{a.pace:.0f} s per request")
    notice(a)
    t0 = time.time()
    n_rows = 0
    with open(raw / "progress.jsonl", "a", encoding="utf-8") as prog:
        for i, e in enumerate(todo, 1):
            t1 = time.time()
            rec = {"native_id": e["native_id"], "version": e.get("version") or "", "name": e.get("name"),
                   "at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
            try:
                src = a.src_path(e)
                if src.exists() and src.stat().st_size:
                    body = src.read_bytes()
                else:
                    body = a.fetch_raw(e)
                    tmp = src.with_name(src.name + ".part")
                    tmp.write_bytes(body)
                    os.replace(tmp, src)
                doc = a.parse(body, e["native_id"], e)
                rows = a.to_rows(doc)
                out = raw / "rows" / f"{_safe(e['native_id'])}.jsonl"
                _write_lines(out, rows)
                rec.update(status="ok" if rows else "empty", rows=len(rows), src_bytes=len(body),
                           rows_bytes=out.stat().st_size)
                n_rows += len(rows)
            except Exception as ex:                                       # recorded; retried on the next run
                rec.update(status="error", error=f"{type(ex).__name__}: {ex}"[:300])
            rec["secs"] = round(time.time() - t1, 1)
            prog.write(json.dumps(rec, ensure_ascii=False) + "\n")
            prog.flush()
            log(f"[{i}/{len(todo)}] {e['native_id']} {rec['status']} rows={rec.get('rows', 0)} "
                f"src={rec.get('src_bytes', 0)} {rec['secs']}s  {(e.get('name') or '')[:60]}")
            if i % 50 == 0 or i == len(todo):
                el = time.time() - t0
                log(f"-- {i} Acts in {el / 60:.1f} min ({el / i:.1f} s/Act), {n_rows} rows; "
                    f"ETA {(len(todo) - i) * el / i / 60:.0f} min")
                manifest(a, **status(a))
    s = status(a)
    manifest(a, last_run=dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), **s)
    return s


def a_ext(a: State) -> str:
    return ".xml" if isinstance(a, (EnActState, SouthAustralia)) else ".json" if isinstance(a, WesternAustralia) \
        else ".bin"


def _safe(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9.\-]+", "_", str(s or ""))[:120]


def status(a: State) -> dict:
    raw = raw_dir(a)
    listed = {e["native_id"] for e in read_lines(raw / "list.jsonl")}
    latest = {p["native_id"]: p for p in read_lines(raw / "progress.jsonl") if p["native_id"] in listed}
    by: dict[str, int] = {}
    for p in latest.values():
        by[p["status"]] = by.get(p["status"], 0) + 1
    ok = [p for p in latest.values() if p["status"] == "ok"]
    dates = sorted((p.get("at") or "")[:10] for p in ok if p.get("at"))
    return {"listed": len(listed), "by_status": by,
            "rows": sum(p.get("rows", 0) for p in ok),
            "rows_mb": round(sum(p.get("rows_bytes", 0) for p in ok) / 2**20, 1),
            "src_mb": round(sum(p.get("src_bytes", 0) for p in ok) / 2**20, 1),
            "fetched_from": dates[0] if dates else None, "fetched_to": dates[-1] if dates else None,
            "errors": [p for p in latest.values() if p["status"] == "error"][:20]}


def manifest(a: State, **changes) -> dict:
    raw = raw_dir(a)
    raw.mkdir(parents=True, exist_ok=True)
    p = raw / "MANIFEST.json"
    m = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    m.update({"source": a.sources[0].name, "licence": "CC BY 4.0", "terms": a.sources[0].licence_url,
              "attribution_template": a.attribution_template, "edit_note": EDIT_NOTE, "pace_seconds": a.pace}, **changes)
    _write_json(p, m)
    return m


def notice(a: State) -> Path:
    raw = raw_dir(a)
    raw.mkdir(parents=True, exist_ok=True)
    p = raw / "LICENSE-NOTICE.txt"
    p.write_text(a.attribution(a.today()) + "\n\nLicence: Creative Commons Attribution 4.0 International (CC BY 4.0), "
                 "https://creativecommons.org/licenses/by/4.0/ ; terms: " + a.sources[0].licence_url + "\n\n" +
                 EDIT_NOTE + "\n", encoding="utf-8")
    return p


def reparse(a: State, log: Log = print) -> dict:
    """Rebuild the rows files from the saved source files (no network)."""
    raw = raw_dir(a)
    acts = {e["native_id"]: e for e in read_lines(raw / "list.jsonl")}
    latest = {p["native_id"]: p for p in read_lines(raw / "progress.jsonl")}
    n = rows = 0
    with open(raw / "progress.jsonl", "a", encoding="utf-8") as prog:
        for p in latest.values():
            if p.get("status") not in ("ok", "empty"):
                continue
            e = acts.get(p["native_id"], {"native_id": p["native_id"]})
            src = a.src_path({**e, **p})
            if not src.exists():
                continue
            doc = a.parse(src.read_bytes(), p["native_id"], e)
            doc.fetched = (p.get("at") or a.today())[:10]
            rs = a.to_rows(doc)
            out = raw / "rows" / f"{_safe(p['native_id'])}.jsonl"
            _write_lines(out, rs)
            prog.write(json.dumps({**p, "status": "ok" if rs else "empty", "rows": len(rs),
                                   "rows_bytes": out.stat().st_size, "reparsed": a.today()}) + "\n")
            n += 1
            rows += len(rs)
    log(f"{a.name}: reparsed {n} Acts, {rows} rows")
    return {"acts": n, "rows": rows}


STATES: tuple[State, ...] = (NewSouthWales(), Victoria(), Queensland(), WesternAustralia(), SouthAustralia(),
                             Tasmania(), AustralianCapitalTerritory(), NorthernTerritory())
BY_KEY = {s.code: s for s in STATES}


def get(key: str) -> State:
    k = key.lower()
    k = k if k.startswith("aus-") else f"aus-{k}"
    return BY_KEY[k]


def main(argv: list[str] | None = None) -> int:
    """``python -m lexflow.corpus.countries.australia_states pull|status|reparse <key> [--limit N]``"""
    import argparse
    ap = argparse.ArgumentParser(prog="lexflow.corpus.countries.australia_states")
    ap.add_argument("action", choices=["pull", "status", "reparse", "list", "baseline"])
    ap.add_argument("key")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--refresh-list", action="store_true")
    o = ap.parse_args(argv)
    a = get(o.key)

    def log(s: str) -> None:
        print(time.strftime("%H:%M:%S ") + s, flush=True)
    if o.action == "pull":
        print(json.dumps(pull(a, limit=o.limit, refresh_list=o.refresh_list, log=log), indent=1))
    elif o.action == "status":
        s = status(a)
        manifest(a, **s)
        print(json.dumps(s, indent=1))
    elif o.action == "reparse":
        reparse(a, log=log)
    elif o.action == "baseline":                    # South Australia only: the 2018 RTF snapshot
        if not isinstance(a, SouthAustralia):
            raise SystemExit("baseline: South Australia only")
        print(json.dumps(sa_baseline(a, log=log), indent=1))
    else:
        for e in a.fetch_list(o.limit, log=log):
            sys.stdout.write(json.dumps(e) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
