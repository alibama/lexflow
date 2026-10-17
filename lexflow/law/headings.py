"""Headings (names) for the statutory units lexflow writes to Wikibase: titles, subtitles, parts, chapters,
subchapters, articles and acts above the sections.

A unit's key is the one ``lexflow.publish.schema`` mints, ``lexflow:unit:<st>:<act_id tokens below the state,
lower-cased, joined by ->`` (``lexflow:unit:va:t2.2-sii-pb-c37`` for ``STATE_VA_T2.2_SII_PB_C37``); the units
of a section are derived from its index row exactly as ``graph.Build._units`` derives them (``units_of``).

Two sources, in order:

1. ``from_corpus(state)``: the open-us-law parquet's breadcrumbs (``name`` on each level; DC, Utah and Puerto
   Rico carry them), its ``title_name``/``chapter_name`` columns (Oregon, Wyoming, Ohio's chapters, Utah's titles)
   and the ``display_path`` where it spells ``Division 2 - HEALING ARTS`` (some California rows).  A name that
   merely repeats the level and number (Ohio's ``Title 11``) is not a name and is dropped.
2. ``from_official(state, units)``: the unit's page in the state's official code site (its own table-of-contents
   page, or the parent's page that lists it), read with the project's polite reader (``payroll.sources.Http``:
   GET only, the research User-Agent, robots.txt obeyed, at least 1.5 s between requests to one host, a 20 s
   timeout, every reply cached under ``data/cache/headings/<st>/``).  A site that refuses automated reading (its
   robots.txt disallows the page, or answers 401/403/429) is recorded under ``refused`` and left alone; the
   Internet Archive is asked only then, and only a capture from the last year is used (its URL is recorded as
   the source).  The heading is taken verbatim from the page, with the numbering that repeats the unit
   (``Chapter 37.``) and a trailing section range (``[7920.000 - 7931.000]``) stripped, and cut at 250 chars.

``fixtures/law/unit_headings.json`` holds the result: ``{"units": {key: {"name", "source", "retrieved"}},
"refused": [...], "unmatched": [...]}``; ``get(key)`` reads it (the hook for ``graph.Build._units``).

    python -m lexflow.law.headings                      # report the units of the graph and the corpus names
    python -m lexflow.law.headings --fetch [--states va fl] [--units file.json|-] [--graph] [--no-archive] [--redo]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import sys
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Callable, Iterable
from urllib.parse import quote, urlsplit, urlunsplit

from .. import config
from ..publish import schema as SC

Log = Callable[[str], None]

USER_AGENT = "lexflow-research/0.1 (https://github.com/alibama/lexflow)"
MIN_INTERVAL = 1.5          # seconds between two requests to one host
TIMEOUT = 20                # seconds per request
MAX_BYTES = 12_000_000      # a whole-title page (Indiana, Nevada) can be large
NAME_MAX = 250
ARCHIVE = "web.archive.org"
ARCHIVE_INTERVAL = 5.0
ARCHIVE_MAX_AGE_DAYS = 365
FIXTURE = config.ROOT / "fixtures" / "law" / "unit_headings.json"
CACHE = config.DATA_DIR / "cache" / "headings"
REFUSED_CODES = (401, 403, 429)

# the words a page may use for a level, by the vocabulary slug
LEVEL_WORDS: dict[str, tuple[str, ...]] = {
    "title": ("title", "tit", "título", "titulo"), "subtitle": ("subtitle", "subt"),
    "chapter": ("chapter", "chap", "ch", "capítulo", "capitulo"), "subchapter": ("subchapter", "subch"),
    "part": ("part", "pt", "parte"), "subpart": ("subpart",), "division": ("division", "div"),
    "subdivision": ("subdivision",), "article": ("article", "art", "artículo", "articulo"),
    "act": ("act", "ley"), "code": ("code",),
}
_LEVEL_LETTERS = {"T": "title", "S": "subtitle", "P": "part", "D": "division", "C": "chapter", "A": "article"}
_ROMAN = re.compile(r"^[IVXLCDM]+$", re.I)


# --------------------------------------------------------------------------- units

@dataclass
class Unit:
    key: str
    state: str
    prefix: str                       # the act_id prefix (``STATE_VA_T2.2_SII_PB_C37``)
    toks: list[str]                   # the unit tokens below the state, this unit's last
    elems: list[str]                  # the path elements, the code first, this unit's last
    level: str | None                 # unit-level vocabulary slug, when known
    num: str                          # the unit's number as the token spells it (``37``, ``II``, ``B``)
    url: str | None = None            # one section's official URL (the base for the unit's page)
    act_id: str | None = None         # that section's act_id
    citation: str | None = None       # that section's citation

    @property
    def tok(self) -> str:
        return self.toks[-1]

    @property
    def elem(self) -> str:
        return self.elems[-1]

    def nums(self) -> dict[str, str]:
        """``{level: number}`` for this unit and its ancestors, by level letter when the level is unknown."""
        out: dict[str, str] = {}
        for tok, el in zip(self.toks, self.elems[1:]):
            lvl = SC.unit_level(el, tok) or _LEVEL_LETTERS.get(tok[:1].upper(), tok[:1].lower())
            out[lvl] = _num(tok, el)
        return out

    def at(self, level: str) -> str | None:
        return self.nums().get(level)

    def code(self) -> str | None:
        """The code token's body (``gov`` for California's ``Cgov``, ``PBO`` for New York's ``APBO``)."""
        return SC.code_token(self.prefix + "_S0")


def _num(tok: str, elem: str | None = None) -> str:
    """The number of a unit from its token (``C37`` -> ``37``, ``SII`` -> ``II``, ``AAct-442-of-1976`` ->
    ``Act-442-of-1976``), or from its path element when the token has none (``LEY_26_1941`` -> ``26-1941``)."""
    head, _, rest = tok.partition("_")
    if len(head) > 1 and head[:1].upper() in _LEVEL_LETTERS and (
            not head.isalpha() or _ROMAN.match(head[1:]) or len(head) == 2):
        return head[1:] + ("-" + rest.replace("_", "-") if rest else "")
    if rest:                                              # LEY_26_1941 -> 26-1941
        return rest.replace("_", "-")
    return tok                                            # TRANSPARENCIA


def _token_name(tok: str) -> str:
    """As ``graph._token_name``: a path element made from an act_id token when the index's path does not match
    the act_id (``T48`` -> ``Title 48``, ``S48_3a_1103`` -> ``§ 48-3a-1103``)."""
    level = SC.unit_level(None, tok)
    body = tok[1:] if len(tok) > 1 and tok[:1].isalpha() and not tok.isalpha() else tok
    if tok[:1] == "S" and "_" in tok:
        return "§ " + body.replace("_", "-")
    return f"{level.capitalize()} {body}" if level else tok


def units_of(state: str, row: dict) -> list[Unit]:
    """The units above an index row's section, outermost first, keyed exactly as ``graph.Build._units`` keys
    them: a code token (``Cgov``, ``APBO``: a letter and an alphabetic body) is a legal code, not a unit."""
    st = state.lower()
    act_id = row.get("act_id") or ""
    toks = SC.unit_tokens(act_id)
    elems = [e for e in (row.get("path") or "").split(" / ") if e]
    if not toks:
        return []
    if len(elems) != len(toks) + 1:
        elems = [elems[0] if elems else f"{st.upper()} Code"] + [_token_name(t) for t in toks]
    out: list[Unit] = []
    for i, (tok, el) in enumerate(zip(toks[:-1], elems[1:-1])):
        if tok[:1] in ("C", "A") and tok[1:].isalpha():
            continue
        prefix = SC.unit_prefix(act_id, i + 1)
        out.append(Unit(SC.key_for("unit", st, prefix), st, prefix, toks[:i + 1], elems[:i + 2],
                        SC.unit_level(el, tok), _num(tok, el), row.get("url"), act_id, row.get("citation")))
    return out


def _index(state: str) -> sqlite3.Connection | None:
    from ..ask import index as I
    p = I.path(state)
    if not p.exists():
        return None
    con = sqlite3.connect(f"file:{p}?mode=ro", uri=True, timeout=60)
    con.row_factory = sqlite3.Row
    return con


def units_for_sections(state: str, refs: Iterable[str], log: Log = print) -> dict[str, Unit]:
    """The units above the given sections (index refs), from the state's index."""
    from ..ask import index as I
    out: dict[str, Unit] = {}
    if not I.ready(state):
        log(f"{state}: no statute index")
        return out
    for ref in refs:
        try:
            hits = I.lookup(state, ref)
        except Exception as e:  # noqa: BLE001 - a locked or missing index
            log(f"{state}: index lookup failed for {ref!r}: {e}")
            continue
        if hits:
            for u in units_of(state, hits[0]):
                out.setdefault(u.key, u)
    return out


def units_for_prefixes(state: str, prefixes: Iterable[str], log: Log = print) -> dict[str, Unit]:
    """The units with the given act_id prefixes (the graph's ``act identifier`` of a unit, or a unit key's slug),
    described from one section of each in the state's index."""
    out: dict[str, Unit] = {}
    con = _index(state)
    if con is None:
        log(f"{state}: no statute index")
        return out
    try:
        for p in prefixes:
            prefix = p if p.upper().startswith("STATE_") else f"STATE_{state.upper()}_" + p.replace("-", "_")
            like = prefix.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "\\_%"
            r = con.execute("SELECT * FROM sec WHERE act_id LIKE ? ESCAPE '\\' ORDER BY id LIMIT 1",
                            (like,)).fetchone()
            if r is None:
                log(f"{state}: no section under {prefix}")
                continue
            depth = len(SC.unit_tokens(prefix))
            for u in units_of(state, dict(r)):
                if len(u.toks) <= depth:
                    out.setdefault(u.key, u)
    finally:
        con.close()
    return out


def units_in_wikibase(con, states: Iterable[str] | None = None, log: Log = print) -> dict[str, Unit]:
    """The units above every section in ``wikibase_items`` (``lexflow:statute:<st>:<ref>``) plus the unit items
    it already holds (``lexflow:unit:<st>:<slug>``)."""
    from ..store import db
    want = {s.lower() for s in states} if states else None
    refs: dict[str, list[str]] = {}
    slugs: dict[str, list[str]] = {}
    for r in db.rows(con, "SELECT key FROM wikibase_items WHERE key LIKE 'lexflow:statute:%' "
                          "OR key LIKE 'lexflow:unit:%'"):
        kind, st, rest = r["key"].split(":", 3)[1:]
        if want and st not in want:
            continue
        (refs if kind == "statute" else slugs).setdefault(st, []).append(rest)
    out: dict[str, Unit] = {}
    for st in sorted(set(refs) | set(slugs)):
        out.update(units_for_sections(st, refs.get(st, ()), log))
        missing = [s for s in slugs.get(st, ()) if SC.key_for("unit", st, "STATE_X_" + s.replace("-", "_")) not in out]
        out.update(units_for_prefixes(st, missing, log))
    return out


def units_in_graph(con, drafts: bool = True, states=None, log: Log = print) -> dict[str, Unit]:
    """The statutory units the graph builds (``graph.build``, read-only), described from the index."""
    from ..publish import graph
    items = graph.build(con, states=states, drafts=drafts, log=log)
    by_state: dict[str, list[str]] = {}
    for it in items:
        if not str(it.cls).endswith("statutory-unit"):
            continue
        st = it.key.split(":")[2]
        prefix = next((c.value.value for c in it.claims if c.prop == "act identifier"), None)
        by_state.setdefault(st, []).append(prefix or it.key.split(":", 3)[3])
    out: dict[str, Unit] = {}
    for st, prefixes in sorted(by_state.items()):
        out.update(units_for_prefixes(st, prefixes, log))
    return out


# --------------------------------------------------------------------------- names

_WS = re.compile(r"\s+")


def _ws(s: str) -> str:
    return _WS.sub(" ", (s or "").replace("\xa0", " ")).strip()


def _words(level: str | None, elem: str | None = None) -> list[str]:
    words = list(LEVEL_WORDS.get(level or "", ()))
    first = (elem or "").split()[0].lower().strip(".:") if (elem or "").split() else ""
    if first and first not in words and first.isalpha():
        words.append(first)
    return words or ["chapter", "title", "article", "part"]


def _num_pattern(num: str) -> str:
    """The number, with its separators loose: ``10-20`` also matches ``10–20``; roman and letters either case."""
    parts = re.split(r"([-–—_.])", num)
    out = []
    for p in parts:
        if p in ("-", "–", "—", "_"):
            out.append(r"\s*[-–—_]\s*")
        elif p == ".":
            out.append(r"\.")
        else:
            out.append(re.escape(p))
    return "".join(out)


def prefix_re(level: str | None, num: str, elem: str | None = None, parent: str | None = None) -> re.Pattern:
    """``Chapter 37.``, ``CHAPTER 37 -``, ``Title X:``, ``Art. 5 —`` at the start of a line, the number followed
    by a separator or the end (so ``Chapter 37`` does not match ``Chapter 37.1``).  A site may spell the number
    with the parent's (``Chapter 18.100 RCW``, ``CHAPTER 1-27``) or with leading zeros (``Chapter 005``)."""
    words = "|".join(re.escape(w) for w in sorted(_words(level, elem), key=len, reverse=True))
    lead = rf"(?:{_num_pattern(parent)}\s*[.\-–—:]\s*)?" if parent else ""
    zeros = "0*" if num[:1].isdigit() else ""
    return re.compile(rf"^(?:{words})\.?\s*(?:no\.?\s*)?{lead}{zeros}{_num_pattern(num)}"
                      rf"(?:(?=\s|$)|[.:;,](?=\s|$|[-–—|A-Za-z(\[\"'“‘]))\s*[.:;,]?\s*[-–—|]*\s*", re.I)


_TRAIL_RANGE = re.compile(r"\s*[\[(]\s*(?:§§?|ss?\.|sections?|secs?\.?)?\s*[\w.\-–—:]+\s*(?:[-–—]|to|through|et seq\.?)"
                          r"\s*[\w.\-–—:]*\s*[\])]\s*$", re.I)
_TRAIL_SECS = re.compile(r"(?:^|\s)(?:§§?|secs?\.?:?|sections?:?|ss\.|chs?\.?|chapters)\s*\d[\w.\-–—:]*"
                         r"(?:\s*(?:[-–—]|to|through)\s*[\w.\-–—:]+)?\s*$", re.I)   # ``Sec: 29-3101-29-4202``, ``Ch.14-24``
_INLINE_SECS = re.compile(r"^(.{3,}?)\s+\d+(?:[.\-:]\d+)+[A-Za-z]?(?:\s|$).*$")   # ``Name 29-1011 First section ...``
# navigation and site text that is never a heading: a window title's site name, a menu entry, a link's label
_JUNK = re.compile(r"^(?:menu|pdf|ms-word|print(?: friendly| page| this page)?|skip to .*|authenticate|toggle navigation"
                   r"|text size.*|download .*|view (?:statute|document|chapter|title|all).*|back to .*|(?:statute |advanced )?search"
                   r"|section headnote|home|chapters?|sections?|titles?|articles?|parts?)$"
                   r"|(?:\w+\s+(?:legislature|general assembly)|official website.*|ohio laws|code annotated \d{4}"
                   r"|revised statutes|table of contents.*|maine revised statutes)$", re.I)
_TRAIL_LINKS = re.compile(r"(?:\s+Read\s+(?:Title|Chapter|Subtitle|Part|Article))+$|\s+Sections\s+PDF\b.*$"
                          r"|\s*[-–—]\s*Table of Contents\b.*$|\s*\|.*$", re.I)      # law.lis.virginia.gov, legis.iowa.gov, legmt.gov
_CRUMB = re.compile(r"^(?:Title|Chapter|Subtitle|Subchapter|Part|Division|Article)\s+[\w.\-]+\s*[,>»:]\s*")
_TRAIL_DECOR = re.compile(r"[^\w.)\]\"'”’!?%]+$")               # revisor.mo.gov's ``✹ ⚿`` icons, ``»``
_TRAIL_NOTE = re.compile(r"\s*\[[^\]\d]*\]\s*$")               # DC's ``[Enacted title]``
_LEAD_RANGE = re.compile(r"^\(\s*(?:§§?|ss?\.|sections?)?\s*[\w.\-–—:]+\s*(?:[-–—]|to|through)\s*[\w.\-–—:]*\s*\)\s*")
_NOT_A_NAME = re.compile(r"^(?:§|sec(?:tion|s)?\b|ss?\.|\d|[-–—.:]*$|rcw\b\s*$|of\b|\(repealed\)?|\[repealed\]?|repealed\b)", re.I)
_LEVEL_ONLY = re.compile(r"^(?:" + "|".join(sorted({w for ws in LEVEL_WORDS.values() for w in ws}, key=len, reverse=True))
                         + r")\b\.?\s*(?:no\.?\s*)?[\w.\-–—]*\.?$", re.I)      # ``Title 11``, not ``Partnership``
_ANY_LEVEL = re.compile(r"^(?:" + "|".join(sorted({w for ws in LEVEL_WORDS.values() for w in ws}, key=len, reverse=True))
                        + r")\.?\s+[\w.\-–—]+", re.I)
# a site's own words before the numbering on a heading line: nebraskalegislature.gov's ``Revised Statutes Chapter 21 -``
_LINE_PREFIX = re.compile(r"^(?:(?:the\s+)?(?:revised|general|consolidated)\s+(?:statutes|laws)|MCL\s*-|RSMo|RCW|NRS|ORS)"
                          r"\s*[-:,]?\s*", re.I)
_SITE_WORDS = re.compile(r"^(?:RCW|NRS|ORS|HRS|ILCS|RSA|MCL|CGS)\b\s*[-–—:.]*\s*", re.I)


def strip_prefix(name: str, level: str | None, num: str, elem: str | None = None,
                 code_name: str | None = None, parent: str | None = None) -> str | None:
    """A heading with the numbering that repeats the unit removed (``Chapter 37. Virginia Freedom of Information
    Act`` -> ``Virginia Freedom of Information Act``; ``Utah Code Title 38: Liens`` -> ``Liens``), the site's
    code word (``RCW PUBLIC RECORDS ACT`` -> ``PUBLIC RECORDS ACT``) and a section range (``[7920 - 7931]``,
    ``(ss. 465.001-465.0244)``) taken off; None when nothing but the numbering is left."""
    s = _ws(name)
    if s[:1] == "[" and s[-1:] == "]":                   # capitol.hawaii.gov's ``[TITLE 23A. OTHER BUSINESS ENTITIES]``
        s = s[1:-1].strip()
    if not s:
        return None
    if code_name:
        s2 = re.sub(r"^" + re.escape(_ws(code_name)) + r"\s*[,:.\-–—]*\s*", "", s, flags=re.I)
        s = s2 if s2.strip() else s                      # the name is the code's own name (Puerto Rico's acts)
    pat = prefix_re(level, num, elem, parent)
    for _ in range(2):                                   # ``Title 10 - Title 10. Name``
        m = pat.match(s)
        if not m:
            break
        s = s[m.end():]
    s = _SITE_WORDS.sub("", s)
    s = _LEAD_RANGE.sub("", s)
    for _ in range(3):
        s2 = _TRAIL_NOTE.sub("", _TRAIL_SECS.sub("", _TRAIL_RANGE.sub("", s)))
        if s2 == s:
            break
        s = s2
    m = _INLINE_SECS.match(s)
    if m:
        s = m.group(1)
    s = _TRAIL_DECOR.sub("", _TRAIL_LINKS.sub("", s)).strip(" -–—:;,|")
    if not s or _NOT_A_NAME.match(s) or _LEVEL_ONLY.match(s) or _JUNK.search(s) or len(s) < 2:
        return None
    if len(s) > NAME_MAX:
        s = s[:NAME_MAX].rstrip()
    return s


# --------------------------------------------------------------------------- the corpus

def _parquet(state: str) -> Path:
    return config.RAW_DIR / "open-us-law" / f"us_{state.lower()}_statutes.parquet"


def _breadcrumb_units(act_id: str, crumbs: list[dict], elems: list[str] | None = None) -> list[tuple[Unit, dict]]:
    """Breadcrumb elements paired with the units they name: by position when the breadcrumb and the act_id have
    the same shape, else by level letter and number (Utah's ``Chapter 10-20`` is no token: dropped).  ``elems``
    is the display_path, whose elements name the units as the graph names them when its shape matches."""
    toks = SC.unit_tokens(act_id)
    levels = [c for c in crumbs if (c.get("type") or "").lower() != "section"]
    pairs: list[tuple[Unit, dict]] = []
    if not toks:
        return pairs
    st = act_id.split("_")[1].lower() if act_id.count("_") >= 2 else ""
    path_ok = bool(elems) and len(elems) == len(toks) + 1

    def elem_at(i: int) -> str:
        if path_ok:
            return elems[i + 1]
        if i < len(levels):
            return f"{(levels[i].get('type') or '').capitalize()} {levels[i].get('num') or ''}".strip()
        return _token_name(toks[i])

    def unit_at(i: int) -> Unit | None:
        tok = toks[i]
        if i >= len(toks) - 1 or (tok[:1] in ("C", "A") and tok[1:].isalpha()):
            return None
        prefix = SC.unit_prefix(act_id, i + 1)
        chain = [elems[0] if elems else ""] + [elem_at(j) for j in range(i + 1)]
        el = chain[-1]
        return Unit(SC.key_for("unit", st, prefix), st, prefix, toks[:i + 1], chain, SC.unit_level(el, tok), _num(tok, el))

    if len(levels) == len(toks) - 1:
        for i, c in enumerate(levels):
            u = unit_at(i)
            if u:
                pairs.append((u, c))
        return pairs
    letters = {"title": "T", "subtitle": "S", "part": "P", "division": "D", "chapter": "C", "article": "A",
               "subchapter": "S"}
    for c in levels:                                     # align by letter and number
        typ, num = (c.get("type") or "").lower(), (c.get("num") or "").lower()
        letter = letters.get(typ)
        for i, tok in enumerate(toks[:-1]):
            hit = (letter and tok[:1] == letter and tok[1:].lower() == num) or                   (typ in ("code", "act") and tok.isalpha() and tok.lower() == num.replace("_", ""))
            if hit:
                u = unit_at(i)
                if u:
                    pairs.append((u, c))
                break
    return pairs


_DISPLAY_NAME = re.compile(r"^(\w+\.?\s+[\w.\-]+)\s+[-–—:]\s+(.+)$")


def from_corpus(state: str, keys: Iterable[str] | None = None, log: Log = print) -> dict[str, str]:
    """``{unit key: name}`` from the open-us-law parquet: breadcrumb names, the title_name/chapter_name columns
    and named display_path elements, with the numbering stripped and names that only repeat the level and number
    dropped.  When several rows name one unit differently, the most common name wins."""
    import pyarrow.parquet as pq
    st = state.lower()
    p = _parquet(st)
    if not p.exists():
        log(f"{st}: no parquet file")
        return {}
    want = set(keys) if keys is not None else None
    cols = ["act_id", "breadcrumb", "display_path", "title_name", "chapter_name"]
    table = pq.read_table(p, columns=[c for c in cols if c in pq.read_schema(p).names])
    data = {c: table.column(c).to_pylist() for c in table.schema.names}
    votes: dict[str, dict[str, int]] = {}

    def vote(key: str, name: str | None):
        if name:
            votes.setdefault(key, {})[name] = votes.get(key, {}).get(name, 0) + 1

    for i in range(table.num_rows):
        act_id = data["act_id"][i] or ""
        toks = SC.unit_tokens(act_id)
        if len(toks) < 2:
            continue
        if want is not None and not any(SC.key_for("unit", st, SC.unit_prefix(act_id, d)) in want
                                        for d in range(1, len(toks))):
            continue
        raw = data.get("breadcrumb", [None])[i] if "breadcrumb" in data else None
        try:
            crumbs = json.loads(raw) if isinstance(raw, str) else (raw or [])
        except ValueError:
            crumbs = []
        path = data.get("display_path", [None])[i] if "display_path" in data else None
        elems = [e for e in (path or "").split(" / ") if e]
        code_name = elems[0] if elems else None
        pairs = _breadcrumb_units(act_id, crumbs if isinstance(crumbs, list) else [], elems)
        for u, c in pairs:
            name = c.get("name") or ""
            label = c.get("label") or ""
            if name and name != label:
                vote(u.key, strip_prefix(name, u.level, u.num, u.elem, code_name))
            elif label and (c.get("type") or "").lower() in ("code", "act", "part"):
                # Puerto Rico's acts: the label is the act's name (``Act PBO``, ``Code hsc`` strip to nothing)
                vote(u.key, strip_prefix(label, u.level, u.num, u.elem, code_name))
        # the columns: title_name for the title token, chapter_name for the chapter token
        by_level = {u.level: u for u, _ in pairs}
        if not pairs:
            for i2, tok in enumerate(toks[:-1]):
                if tok[:1] in ("C", "A") and tok[1:].isalpha():
                    continue
                prefix = SC.unit_prefix(act_id, i2 + 1)
                el = _token_name(tok)
                u = Unit(SC.key_for("unit", st, prefix), st, prefix, toks[:i2 + 1], [code_name or ""] + [_token_name(t) for t in toks[:i2 + 1]],
                         SC.unit_level(el, tok), _num(tok, el))
                by_level.setdefault(u.level, u)
        for col, lvl in (("title_name", "title"), ("chapter_name", "chapter")):
            u = by_level.get(lvl)
            val = data.get(col, [None])[i] if col in data else None
            if u and val and val != code_name and val.lower() != "none":
                vote(u.key, strip_prefix(val, u.level, u.num, u.elem, code_name))
        # display_path elements that carry a name: ``Division 2 - HEALING ARTS``
        if elems and len(elems) == len(toks) + 1:
            for i2, (tok, el) in enumerate(zip(toks[:-1], elems[1:-1])):
                m = _DISPLAY_NAME.match(el)
                if not m or (tok[:1] in ("C", "A") and tok[1:].isalpha()):
                    continue
                prefix = SC.unit_prefix(act_id, i2 + 1)
                key = SC.key_for("unit", st, prefix)
                lvl = SC.unit_level(m.group(1), tok)
                vote(key, strip_prefix(m.group(2), lvl, _num(tok, m.group(1)), m.group(1), code_name))
    out: dict[str, str] = {}
    for key, names in votes.items():
        if want is None or key in want:
            out[key] = max(names.items(), key=lambda kv: (kv[1], -len(kv[0])))[0]
    return out


# --------------------------------------------------------------------------- the official pages

def http(log: Log = print, **kw):
    """The project's polite reader with this module's spacing and timeout (``payroll.sources.Http``)."""
    from urllib.parse import urljoin
    from ..payroll import sources as SRC

    class Http(SRC.Http):
        @staticmethod
        def _next_hop(url, r, hosts):                     # noqa: ARG004 - any https host; each hop is checked
            loc = r.headers.get("Location")
            r.close()
            if not loc:
                return None, f"{url} redirected without a Location"
            nxt = urljoin(url, loc)
            if urlsplit(url).scheme == "https" and urlsplit(nxt).scheme != "https":
                return None, f"redirect from {url} to {nxt} refused: it leaves https"
            return nxt, None

    h = Http(min_interval=MIN_INTERVAL, timeout=TIMEOUT, log=log, **kw)
    h._gap[ARCHIVE] = ARCHIVE_INTERVAL
    return h


def _cache_path(state: str, url: str) -> Path:
    return CACHE / state.lower() / (hashlib.sha1(url.encode()).hexdigest()[:20] + ".json")


@dataclass
class Page:
    url: str
    status: str                       # ok | refused | error | missing
    code: int | None = None
    text: str = ""
    final_url: str | None = None
    retrieved: str = ""
    why: str | None = None
    cached: bool = False


class Fetcher:
    """Reads official pages through the polite reader, remembering every reply (and refusal) under the cache so
    a second run makes no request.  A host that refused once is not asked again in the run."""

    def __init__(self, log: Log = print, reader=None, cache: Path | None = None, archive: bool = True):
        self.log, self.cache_dir, self.archive = log, cache or CACHE, archive
        self._reader = reader
        self.refused_hosts: dict[str, str] = {}
        self.requests = 0

    @property
    def reader(self):
        if self._reader is None:
            self._reader = http(self.log)
        return self._reader

    def _load(self, state: str, url: str) -> Page | None:
        p = self.cache_dir / state.lower() / (hashlib.sha1(url.encode()).hexdigest()[:20] + ".json")
        if not p.exists():
            return None
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        return Page(d["url"], d["status"], d.get("code"), d.get("text", ""), d.get("final_url"),
                    d.get("retrieved", ""), d.get("why"), cached=True)

    def _save(self, state: str, page: Page) -> None:
        p = self.cache_dir / state.lower() / (hashlib.sha1(page.url.encode()).hexdigest()[:20] + ".json")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"url": page.url, "status": page.status, "code": page.code, "final_url": page.final_url,
                                 "retrieved": page.retrieved, "why": page.why, "text": page.text},
                                ensure_ascii=False), encoding="utf-8")

    def get(self, state: str, url: str, hosts: Iterable[str] = ()) -> Page:
        hit = self._load(state, url)
        if hit is not None and (hit.status == "ok" or hit.status == "refused"):
            return hit
        host = urlsplit(url).netloc.lower()
        if host in self.refused_hosts:
            return Page(url, "refused", why=self.refused_hosts[host], retrieved=_today())
        import requests
        page = Page(url, "error", retrieved=_today())
        try:
            r = self.reader.get(url, stream=True, hosts=hosts)
            self.requests += 1
            try:
                chunks, size = [], 0
                for chunk in r.iter_content(1 << 16):
                    chunks.append(chunk)
                    size += len(chunk)
                    if size >= MAX_BYTES:
                        break
                data = b"".join(chunks)
                page.code, page.final_url = r.status_code, r.url
                enc = r.encoding or "utf-8"
            finally:
                r.close()
            try:
                page.text = data.decode("utf-8")           # a page declared ISO-8859-1 but written in UTF-8
            except UnicodeDecodeError:
                try:
                    page.text = data.decode(enc, errors="replace")
                except LookupError:
                    page.text = data.decode("utf-8", errors="replace")
            page.status = "ok"
        except PermissionError as e:                       # robots.txt disallows, or a refused redirect
            if "unreachable" in str(e):                    # a TLS chain the client cannot verify, a timeout:
                page.status, page.why = "error", str(e)    # not a refusal, so no archive either
            else:
                page.status, page.why = "refused", str(e)
            self.refused_hosts[host] = str(e)
        except requests.HTTPError as e:
            code = e.response.status_code if e.response is not None else None
            page.code = code
            if code in REFUSED_CODES:
                page.status, page.why = "refused", f"HTTP {code}"
                self.refused_hosts[host] = f"HTTP {code}"
            elif code == 404:
                page.status, page.why = "missing", "HTTP 404"
            else:
                page.status, page.why = "error", f"HTTP {code}"
        except requests.RequestException as e:
            page.status, page.why = "error", f"{type(e).__name__}"
        self.log(f"{state}: {page.status} {url}" + (f" ({page.why})" if page.why else ""))
        self._save(state, page)
        return page

    def archived(self, state: str, url: str) -> Page | None:
        """The Internet Archive's most recent capture of a page the live site refused, when it is less than a
        year old; the capture's URL is the page's ``url``."""
        if not self.archive:
            return None
        import requests
        probe = f"https://archive.org/wayback/available?url={quote(url, safe='')}&timestamp={date.today():%Y%m%d}"
        try:
            r = self.reader.get(probe)
            self.requests += 1
            try:
                snap = (r.json().get("archived_snapshots") or {}).get("closest") or {}
            finally:
                r.close()
        except (PermissionError, requests.RequestException, ValueError) as e:
            self.log(f"{state}: archive lookup failed for {url}: {e}")
            return None
        ts = snap.get("timestamp") or ""
        if not snap.get("available") or len(ts) < 8:
            return None
        when = datetime.strptime(ts[:8], "%Y%m%d").date()
        if (date.today() - when).days > ARCHIVE_MAX_AGE_DAYS:
            self.log(f"{state}: archive capture of {url} is from {when}: too old")
            return None
        capture = f"https://{ARCHIVE}/web/{ts}id_/{url}"
        page = self.get(state, capture, hosts=(ARCHIVE,))
        return page if page.status == "ok" else None


# ---- page candidates per state: the unit's own TOC page, or the parent's page that lists it

def _base(u: Unit) -> tuple[str, str]:
    parts = urlsplit(u.url or "")
    return f"{parts.scheme}://{parts.netloc}", parts.path


def _nofrag(url: str) -> str:
    p = urlsplit(url)
    return urlunsplit((p.scheme, p.netloc, p.path, p.query, ""))


def _roman_int(s: str) -> int | None:
    if not _ROMAN.match(s):
        return None
    vals = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    total, prev = 0, 0
    for ch in reversed(s.upper()):
        v = vals[ch]
        total = total - v if v < prev else total + v
        prev = max(prev, v)
    return total


def _path_prefix(u: Unit, depth_from_tokens: bool = True) -> list[str]:
    """The section URL's path parts."""
    return [p for p in urlsplit(u.url or "").path.split("/") if p]


def pages_va(u: Unit) -> list[str]:
    t, c = u.at("title"), u.at("chapter")
    if u.level == "title" or u.level in ("subtitle", "part") or (u.level == "chapter" and not c):
        return [f"https://law.lis.virginia.gov/vacode/title{t}/"]
    if u.level == "chapter":
        return [f"https://law.lis.virginia.gov/vacode/title{t}/chapter{c}/", f"https://law.lis.virginia.gov/vacode/title{t}/"]
    if u.level == "article" and c:
        return [f"https://law.lis.virginia.gov/vacode/title{t}/chapter{c}/"]
    return [f"https://law.lis.virginia.gov/vacode/title{t}/"]


def pages_az(u: Unit) -> list[str]:
    return [f"https://www.azleg.gov/arsDetail/?title={u.at('title')}"]


def pages_fl(u: Unit) -> list[str]:
    m = re.search(r"URL=(\d{4}-\d{4})/(\d{4})/", u.url or "")
    base = "http://www.leg.state.fl.us/statutes/index.cfm?App_mode=Display_Statute&URL="
    out = []
    if u.level == "title":
        out.append(f"http://www.leg.state.fl.us/statutes/index.cfm?App_mode=Display_Index&Title_Request={u.num}")
    if m:
        out.append(f"{base}{m.group(1)}/{m.group(2)}/{m.group(2)}.html")
    return out


def pages_ca(u: Unit) -> list[str]:
    code = (u.code() or "").upper()
    n = u.nums()
    q = "&".join(f"{k}={quote(n[k] + '.') if n.get(k) else ''}" for k in ("division", "title", "part", "chapter", "article"))
    return [f"https://leginfo.legislature.ca.gov/faces/codes_displayexpandedbranch.xhtml?tocCode={code}&{q}",
            f"https://leginfo.legislature.ca.gov/faces/codes_displayText.xhtml?lawCode={code}&{q}"]


def pages_ny(u: Unit) -> list[str]:
    code = (u.code() or "").upper()
    a = u.at("article")
    out = [f"https://www.nysenate.gov/legislation/laws/{code}"]
    if a and u.level != "article":
        out.insert(0, f"https://www.nysenate.gov/legislation/laws/{code}/A{a}")
    return out


def pages_tx(u: Unit) -> list[str]:
    code = (u.code() or "").upper()
    c = u.at("chapter")
    out = []
    if c:
        out += [f"https://statutes.capitol.texas.gov/Docs/{code}/htm/{code}.{c}.htm", _nofrag(u.url or "")]
    if u.level in ("title", "subtitle"):
        out = [f"https://statutes.capitol.texas.gov/?link={code}"] + out
    return [x for x in out if x]


def pages_il(u: Unit) -> list[str]:
    return ["https://www.ilga.gov/legislation/ilcs/ilcs.asp", "https://www.ilga.gov/Legislation/ILCS"]


def pages_md(u: Unit) -> list[str]:
    return [_nofrag(u.url or "")]                         # the section page carries the title and subtitle names


def pages_dc(u: Unit) -> list[str]:
    t, c = u.at("title"), u.at("chapter")
    if u.level == "title":
        return [f"https://code.dccouncil.gov/us/dc/council/code/titles/{t}"]
    return [f"https://code.dccouncil.gov/us/dc/council/code/titles/{t}/chapters/{c}", f"https://code.dccouncil.gov/us/dc/council/code/titles/{t}"]


def pages_wa(u: Unit) -> list[str]:
    cite = u.at("title") if u.level == "title" else f"{u.at('title')}.{u.at('chapter')}"
    return [f"https://app.leg.wa.gov/rcw/default.aspx?cite={cite}"]


def pages_oh(u: Unit) -> list[str]:
    if u.level == "title":
        return [f"https://codes.ohio.gov/ohio-revised-code/title-{u.num}"]
    return [f"https://codes.ohio.gov/ohio-revised-code/chapter-{u.num}"]


def pages_nc(u: Unit) -> list[str]:
    c = u.at("chapter")
    return [f"https://www.ncleg.gov/EnactedLegislation/Statutes/HTML/ByChapter/Chapter_{c}.html"]


def pages_in(u: Unit) -> list[str]:
    m = re.search(r"/ic/(\d{4})/", u.url or "")
    year = m.group(1) if m else "2026"
    return [f"https://iga.in.gov/ic/{year}/Title_{u.at('title')}.html"]


def pages_mn(u: Unit) -> list[str]:
    if u.level == "chapter":
        return [f"https://www.revisor.mn.gov/statutes/cite/{u.num}"]
    return ["https://www.revisor.mn.gov/statutes/"]


def pages_ut(u: Unit) -> list[str]:
    t = u.at("title")
    return [f"https://le.utah.gov/xcode/Title{t}/{t}.html"]


def pages_ak(u: Unit) -> list[str]:
    return [f"https://www.akleg.gov/basis/statutes.asp?title={u.at('title')}"]


def pages_al(u: Unit) -> list[str]:
    return [f"https://alison.legislature.state.al.us/code-of-alabama/?title={u.at('title')}"]


def pages_ct(u: Unit) -> list[str]:
    if u.level == "chapter":
        return [_nofrag(u.url or "")]
    t = u.at("title")
    return [f"https://www.cga.ct.gov/current/pub/title_{int(t):02d}.htm" if t and t.isdigit() else
            f"https://www.cga.ct.gov/current/pub/title_{t}.htm"]


def pages_de(u: Unit) -> list[str]:
    parts = _path_prefix(u)                               # title7 / c041 / sc03 / index.html
    depth = len(u.toks)
    return ["https://delcode.delaware.gov/" + "/".join(parts[:depth]) + "/index.html"]


def pages_hi(u: Unit) -> list[str]:
    parts = _path_prefix(u)                               # hrscurrent / Vol09_Ch0431-0435H / HRS0431 / HRS_0431-0004-0211.htm
    base = "https://www.capitol.hawaii.gov/"
    if len(parts) >= 3:                                   # the chapter's heading page also names the title
        return [base + "/".join(parts[:3]) + f"/HRS_{parts[2][3:]}-.htm"]
    return []


def pages_ia(u: Unit) -> list[str]:
    return ["https://www.legis.iowa.gov/law/iowaCode/chapters?title=" + (u.at("title") or ""),
            "https://www.legis.iowa.gov/law/iowaCode"]


def pages_id(u: Unit) -> list[str]:
    parts = _path_prefix(u)                               # statutesrules / idstat / Title36 / T36CH9 / SECT36-901
    depth = 2 + len(u.toks)
    return ["https://legislature.idaho.gov/" + "/".join(parts[:depth]) + "/"]


def pages_ks(u: Unit) -> list[str]:
    parts = _path_prefix(u)                               # b2025_26 / laws / 075_000_0000_chapter / 075_059_0000_article / ...
    depth = 1 + len(u.toks)                               # the parent's page lists the unit with its name
    return ["https://www.kslegislature.gov/" + "/".join(parts[:depth]) + "/"]


def pages_ky(u: Unit) -> list[str]:
    return ["https://apps.legislature.ky.gov/law/statutes/"]


def pages_la(u: Unit) -> list[str]:
    return ["https://legis.la.gov/Legis/LawSearchList.aspx"]


def pages_ma(u: Unit) -> list[str]:
    parts = _path_prefix(u)                               # Laws / GeneralLaws / PartI / TitleXVI / Chapter112 / Section235
    depth = 2 + len(u.toks)
    return ["https://malegislature.gov/" + "/".join(parts[:depth])]


def pages_me(u: Unit) -> list[str]:
    t = u.at("title")
    if u.level == "chapter":
        return [f"https://legislature.maine.gov/legis/statutes/{t}/title{t}ch{u.num}sec0.html"]
    return [f"https://legislature.maine.gov/legis/statutes/{t}/title{t}ch0sec0.html"]


def pages_mi(u: Unit) -> list[str]:
    if u.level == "act":
        return [f"https://www.legislature.mi.gov/Laws/MCL?objectName=mcl-{u.num}"]
    return [f"https://www.legislature.mi.gov/Laws/MCL?objectName=mcl-chap{u.num}"]


def pages_mo(u: Unit) -> list[str]:
    return [f"https://revisor.mo.gov/main/OneChapter.aspx?chapter={u.num}"]


def pages_mt(u: Unit) -> list[str]:
    parts = _path_prefix(u)                               # bills / mca / title_0370 / chapter_0470 / part_0030 / ...
    depth = 2 + len(u.toks)
    tail = {"title": "chapters_index.html", "chapter": "parts_index.html", "part": "sections_index.html"}.get(u.level or "", "")
    return ["https://mca.legmt.gov/" + "/".join(parts[:depth]) + "/" + tail]


def pages_nd(u: Unit) -> list[str]:
    tt = (u.at("title") or "").replace(".", "-")           # the code's one listing names every title and chapter
    return ["https://ndlegis.gov/general-information/north-dakota-century-code", f"https://ndlegis.gov/cencode/t{tt}.html"]


def pages_ne(u: Unit) -> list[str]:
    return [f"https://nebraskalegislature.gov/laws/browse-chapters.php?chapter={u.num}"]


def pages_nh(u: Unit) -> list[str]:
    t = u.at("title")
    if u.level == "chapter":
        return [f"https://www.gencourt.state.nh.us/rsa/html/NHTOC/NHTOC-{t}-{u.num}.htm"]
    return [f"https://www.gencourt.state.nh.us/rsa/html/NHTOC/NHTOC-{t}.htm"]


def pages_nj(u: Unit) -> list[str]:
    return ["https://lis.njleg.state.nj.us/nxt/gateway.dll?f=templates&fn=default.htm&vid=Publish:10.1048/Enu"]


def pages_nm(u: Unit) -> list[str]:
    return ["https://nmonesource.com/nmos/nmsa/en/nav_date.do"]


def pages_nv(u: Unit) -> list[str]:
    if u.level == "chapter":
        m = re.match(r"^(\d+)(.*)$", u.num)
        num = f"{int(m.group(1)):03d}{m.group(2)}" if m else u.num
        return [f"https://www.leg.state.nv.us/NRS/NRS-{num}.html", "https://www.leg.state.nv.us/NRS/"]
    return ["https://www.leg.state.nv.us/NRS/"]


def pages_ok(u: Unit) -> list[str]:
    return ["https://www.oklegislature.gov/osStatuesTitle.html"]


def pages_or(u: Unit) -> list[str]:
    if u.level == "chapter":
        return [f"https://www.oregonlegislature.gov/bills_laws/ors/ors{u.num.lower()}.html"]
    return ["https://www.oregonlegislature.gov/bills_laws/Pages/ORS.aspx"]


def pages_pa(u: Unit) -> list[str]:
    return [f"https://www.palegis.us/statutes/consolidated/view-statute?txtType=HTM&ttl={u.at('title')}"]


def pages_pr(u: Unit) -> list[str]:
    return []


def pages_ri(u: Unit) -> list[str]:
    t = u.at("title")
    title = f"https://webserver.rilegislature.gov/Statutes/TITLE{t}/INDEX.htm"
    if u.level == "chapter":                              # the title's index lists the chapters with their names
        return [f"https://webserver.rilegislature.gov/Statutes/TITLE{t}/{u.num}/INDEX.htm", title]
    return [title]


def pages_sc(u: Unit) -> list[str]:
    t, c = u.at("title"), u.at("chapter")
    if u.level == "title":
        return [f"https://www.scstatehouse.gov/code/title{t}.php"]
    return [f"https://www.scstatehouse.gov/code/t{int(t):02d}c{int(c):03d}.php" if t.isdigit() and c.isdigit()
            else _nofrag(u.url or "")]


def pages_sd(u: Unit) -> list[str]:
    if u.level == "chapter":
        return [f"https://sdlegislature.gov/api/Statutes/{u.at('title')}-{u.num}.html?all=true"]
    return [f"https://sdlegislature.gov/api/Statutes/{u.num}.html?all=true"]


def pages_vt(u: Unit) -> list[str]:
    t = u.at("title")
    if u.level == "chapter":
        return [f"https://legislature.vermont.gov/statutes/chapter/{int(t):02d}/{int(u.num):03d}" if u.num.isdigit() else
                f"https://legislature.vermont.gov/statutes/chapter/{int(t):02d}/{u.num}"]
    return [f"https://legislature.vermont.gov/statutes/title/{int(t):02d}"]


def pages_wi(u: Unit) -> list[str]:
    return [f"https://docs.legis.wisconsin.gov/statutes/statutes/{u.num}"]


def pages_wv(u: Unit) -> list[str]:
    c = u.at("chapter")
    if u.level == "article":
        return [f"https://code.wvlegislature.gov/{c}-{u.num}/"]
    return [f"https://code.wvlegislature.gov/{c}/"]


def pages_wy(u: Unit) -> list[str]:
    return ["https://wyoleg.gov/statutes/compress/title" + u.at("title").zfill(2) + ".pdf"] if u.level == "chapter" else []


PAGES: dict[str, Callable[[Unit], list[str]]] = {
    "ak": pages_ak, "al": pages_al, "az": pages_az, "ca": pages_ca, "ct": pages_ct, "dc": pages_dc, "de": pages_de,
    "fl": pages_fl, "hi": pages_hi, "ia": pages_ia, "id": pages_id, "il": pages_il, "in": pages_in, "ks": pages_ks,
    "ky": pages_ky, "la": pages_la, "ma": pages_ma, "md": pages_md, "me": pages_me, "mi": pages_mi, "mn": pages_mn,
    "mo": pages_mo, "mt": pages_mt, "nc": pages_nc, "nd": pages_nd, "ne": pages_ne, "nh": pages_nh, "nj": pages_nj,
    "nm": pages_nm, "nv": pages_nv, "ny": pages_ny, "oh": pages_oh, "ok": pages_ok, "or": pages_or, "pa": pages_pa,
    "pr": pages_pr, "ri": pages_ri, "sc": pages_sc, "sd": pages_sd, "tx": pages_tx, "ut": pages_ut, "va": pages_va,
    "vt": pages_vt, "wa": pages_wa, "wi": pages_wi, "wv": pages_wv, "wy": pages_wy,
}


# ---- extraction

_BR = re.compile(r"<\s*br\s*/?\s*>", re.I)
_XML_DECL = re.compile(r"^\s*<\?xml[^>]*\?>")
_SENTINEL = " "


_ATOMIC = {"h1", "h2", "h3", "h4", "h5", "h6"}      # a heading is one line whatever it holds (azleg's divs)
_BLOCKS = {"html", "head", "body", "title", "div", "p", "li", "ul", "ol", "dl", "dt", "dd", "h1", "h2", "h3", "h4",
           "h5", "h6", "table", "thead", "tbody", "tfoot", "tr", "caption", "section", "article", "header", "footer",
           "nav", "main", "aside", "pre", "blockquote", "center", "form", "fieldset", "legend", "hr", "option",
           "address", "details", "summary", "figure", "figcaption"}


def _mojibake(text: str) -> str:
    """UTF-8 read as Latin-1 (``â`` for an em dash) put right; anything else is left alone."""
    if "â" in text or "Â" in text or "Ã" in text:
        try:
            return text.encode("latin-1").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            return text
    return text


def blocks(html: str) -> list[str]:
    """The page's lines in document order, each once: block elements and ``<br>`` bound a line, inline elements
    and table cells join with a space, so a heading split over spans or cells (``CHAPTER 119`` + ``PUBLIC
    RECORDS``) comes out whole and a list's entries come out one by one.  Lines over 400 characters are dropped."""
    import lxml.html
    html = _BR.sub(_SENTINEL, _XML_DECL.sub("", html or "", count=1))   # leginfo's XHTML carries an XML declaration
    try:
        doc = lxml.html.fromstring(html)
    except Exception:  # noqa: BLE001 - an empty or unparseable reply has no lines
        return []
    for bad in doc.xpath("//script|//style|//noscript"):
        bad.drop_tree()
    parts: list[str] = []
    titles: list[str] = []

    def walk(el, atomic: bool = False):
        tag = el.tag.lower() if isinstance(el.tag, str) else ""
        if tag == "title":                                # the window title comes last: a body heading is better
            titles.append(" ".join(el.itertext()))
            return
        block = tag in _BLOCKS and not atomic
        atomic = atomic or tag in _ATOMIC
        parts.append(_SENTINEL if block else " ")
        if el.text:
            parts.append(el.text)
        for ch in el:
            if isinstance(ch.tag, str):
                walk(ch, atomic)
            if ch.tail:
                parts.append(ch.tail)
        parts.append(_SENTINEL if block else " ")

    walk(doc)
    out, seen = [], set()
    for line in "".join(parts + [_SENTINEL] + titles).split(_SENTINEL):
        line = _ws(_mojibake(line))
        if not line or len(line) > 400 or line in seen:
            continue
        seen.add(line)
        out.append(line)
    return out


def find_heading(lines: Iterable[str], u: Unit, code_name: str | None = None) -> str | None:
    """The line that starts with the unit's numbering and carries a name after it, or, when no line does, the
    line after a bare ``CHAPTER 428``.  On a page that lists a whole title, the scan starts after the lines of
    the unit's ancestors (the chapter's line before its articles), so ``Article 2`` is the right chapter's."""
    lines = list(lines)
    parent = _num(u.toks[-2], u.elems[-2]) if len(u.toks) > 1 else None
    pat = prefix_re(u.level, u.num, u.elem, parent)
    clean = []
    for line in lines:
        line = _LINE_PREFIX.sub("", s_bracket(line) or line)
        while not pat.match(line):                         # ``Title 1, Chapter 13: ...``, ``Title 6 > Chapter 18``
            m = _CRUMB.match(line)
            if not m:
                break
            line = line[m.end():]
        clean.append(line)
    start = 0
    for tok, el in zip(u.toks[:-1], u.elems[1:-1]):
        if tok[:1] in ("C", "A") and tok[1:].isalpha():
            continue
        lvl = SC.unit_level(el, tok)
        if lvl == u.level:
            continue
        anchor = prefix_re(lvl, _num(tok, el), el)
        for i in range(start, len(clean)):
            if anchor.match(clean[i]) and any(pat.match(x) for x in clean[i + 1:]):
                start = i + 1
                break
    for line in clean[start:]:                             # the name on the unit's own line
        if pat.match(line):
            name = strip_prefix(line, u.level, u.num, u.elem, code_name, parent)
            if name:
                return name
    for i in range(start, len(clean) - 1):                 # ``CHAPTER 428`` on one line and the name on the next
        if not pat.match(clean[i]):
            continue
        nxt = clean[i + 1]
        if nxt and not _ANY_LEVEL.match(nxt) and not _NOT_A_NAME.match(nxt) and len(nxt) <= NAME_MAX:
            name = strip_prefix(nxt, u.level, u.num, u.elem, code_name, parent)
            if name:
                return name
    return None


def s_bracket(line: str) -> str:
    return line[1:-1].strip() if line[:1] == "[" and line[-1:] == "]" else ""


def extract(html: str, u: Unit) -> str | None:
    """The unit's heading from an official page: a state's own extractor where it has one, else the generic
    scan of the page's lines for ``<Level> <num> <name>``."""
    fn = EXTRACTORS.get(u.state)
    name = fn(html, u) if fn else None
    if name is None and fn is not generic:
        name = generic(html, u)
    return name


def generic(html: str, u: Unit) -> str | None:
    return find_heading(blocks(html), u)


def extract_ny(html: str, u: Unit) -> str | None:
    """nysenate.gov lists ``Article 6 - (84 - 90) FREEDOM OF INFORMATION LAW``; the leading range goes."""
    return find_heading(blocks(html), u)


def extract_ca(html: str, u: Unit) -> str | None:
    """leginfo spells ``CHAPTER 3.5. Inspection of Public Records [7920.000 - 7931.000]``; the generic scan
    strips the range, but the page also repeats a unit's number inside its parents' headings, so only lines
    whose own level matches are read."""
    return find_heading(blocks(html), u)


def extract_mn(html: str, u: Unit) -> str | None:
    """revisor.mn.gov's ``Part 13_13C`` is the chapter group ``13 - 13C`` on the statutes TOC."""
    if u.level == "chapter" or u.tok[:1] != "P":
        return find_heading(blocks(html), u)
    lo, hi = (u.tok[1:].split("_") + [""])[:2]
    pat = re.compile(rf"^(?:chapters?\s+)?{re.escape(lo)}\s*[-–—]\s*{re.escape(hi)}\b\s*[-–—:.]*\s*(.+)$", re.I)
    for line in blocks(html):
        m = pat.match(line)
        if m:
            return strip_prefix(m.group(1), "part", u.num) or None
    return None


def extract_va(html: str, u: Unit) -> str | None:
    """law.lis.virginia.gov lists ``Chapter 37. Virginia Freedom of Information Act`` and, on a title page,
    ``Subtitle II. Administration`` and ``Part B. Transition of ...``; the generic scan reads them."""
    return find_heading(blocks(html), u)


def extract_mi(html: str, u: Unit) -> str | None:
    """legislature.mi.gov puts an act's name on the line before ``Act 442 of 1976``; a chapter's on the line
    after ``Chapter 15`` (the generic scan reads that one)."""
    lines = blocks(html)
    if u.level != "act":
        return find_heading(lines, u)
    num = re.sub(r"^Act-", "", u.num, flags=re.I).replace("-", " ")
    pat = re.compile(rf"^Act\s+{re.escape(num)}\s*$", re.I)
    for i, line in enumerate(lines):
        if pat.match(line) and i and not _ANY_LEVEL.match(lines[i - 1]) and not lines[i - 1].startswith("MCL"):
            return strip_prefix(lines[i - 1], u.level, u.num, u.elem)
    return None


_DE_CRUMB = re.compile(r"^(?:(?:Title|Chapter|Subchapter)\s+\S+\s*>\s*)+")
_DE_PDF = re.compile(r"\s*Authenticated PDF\s*$")


def extract_de(html: str, u: Unit) -> str | None:
    """delcode.delaware.gov heads a page ``Title 6 > Chapter 18 Authenticated PDF`` with the name on the next
    line: the breadcrumb and the PDF link go, then the generic scan reads it."""
    lines = [_DE_PDF.sub("", _DE_CRUMB.sub("", line)) for line in blocks(html)]
    return find_heading([line for line in lines if line], u)


def extract_nh(html: str, u: Unit) -> str | None:
    """gencourt.state.nh.us heads a title's table of contents ``XXVIII: PARTNERSHIPS``, without the word."""
    lines = blocks(html)
    if u.level == "title":
        pat = re.compile(rf"^{_num_pattern(u.num)}\s*:\s*(.+)$", re.I)
        for line in lines:
            m = pat.match(line)
            if m:
                return strip_prefix(m.group(1), u.level, u.num, u.elem)
    return find_heading(lines, u)


EXTRACTORS: dict[str, Callable[[str, Unit], str | None]] = {
    "ny": extract_ny, "ca": extract_ca, "mn": extract_mn, "va": extract_va, "mi": extract_mi, "de": extract_de,
    "nh": extract_nh,
}


# --------------------------------------------------------------------------- the fixture

def _today() -> str:
    return date.today().isoformat()


def load(path: Path = FIXTURE) -> dict:
    try:
        d = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"units": {}, "refused": [], "unmatched": []}
    d.setdefault("units", {})
    d.setdefault("refused", [])
    d.setdefault("unmatched", [])
    return d


def save(data: dict, path: Path = FIXTURE) -> None:
    out = {"built": _today(), "units": dict(sorted(data.get("units", {}).items())),
           "refused": sorted(data.get("refused", []), key=lambda e: (e.get("key") or "", e.get("url") or "")),
           "unmatched": sorted(data.get("unmatched", []), key=lambda e: (e.get("key") or "", e.get("url") or ""))}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


_LOADED: dict | None = None


def get(key: str, path: Path = FIXTURE) -> str | None:
    """The heading of a unit from ``fixtures/law/unit_headings.json``, or None (the hook for the graph)."""
    global _LOADED
    if _LOADED is None:
        _LOADED = load(path)
    e = _LOADED["units"].get(key)
    return e.get("name") if e else None


def reset() -> None:
    global _LOADED
    _LOADED = None


# --------------------------------------------------------------------------- the runs

def from_official(state: str, units: Iterable[Unit], fetcher: Fetcher | None = None, log: Log = print) -> dict:
    """``{"units": {key: {"name", "source", "retrieved"}}, "refused": [...], "unmatched": [...]}`` for one
    state's units from its official code site."""
    st = state.lower()
    fetcher = fetcher or Fetcher(log)
    pages = PAGES.get(st)
    out: dict = {"units": {}, "refused": [], "unmatched": []}
    for u in units:
        if u.state != st:
            continue
        urls = pages(u) if pages else []
        if not urls:
            out["unmatched"].append({"key": u.key, "url": None, "why": "no official page known for this unit"})
            continue
        last: Page | None = None
        found = False
        for url in urls:
            page = fetcher.get(st, url)
            last = page
            if page.status == "refused":
                arch = fetcher.archived(st, url)
                if arch is None:
                    break
                page = arch
            if page.status != "ok":
                continue
            name = extract(page.text, u)
            if name:
                out["units"][u.key] = {"name": name, "source": page.url, "retrieved": page.retrieved or _today()}
                found = True
                break
        if found:
            continue
        if last is not None and last.status == "refused":
            out["refused"].append({"key": u.key, "url": last.url, "why": last.why})
        else:
            out["unmatched"].append({"key": u.key, "url": (last.url if last else None),
                                     "why": (last.why or "no heading found on the page") if last else "no page"})
    return out


def build(units: dict[str, Unit], *, fetch: bool = False, states: Iterable[str] | None = None, archive: bool = True,
          data: dict | None = None, path: Path = FIXTURE, log: Log = print, fetcher: Fetcher | None = None) -> dict:
    """Name ``units`` from the corpus, then (``fetch``) the official pages for the rest; the fixture is written
    after each state so an interrupted run keeps what it found."""
    data = data if data is not None else load(path)
    want = {s.lower() for s in states} if states else None
    by_state: dict[str, list[Unit]] = {}
    for u in units.values():
        if want is None or u.state in want:
            by_state.setdefault(u.state, []).append(u)
    fetcher = fetcher or Fetcher(log, archive=archive)
    for st in sorted(by_state):
        todo = by_state[st]
        corpus = from_corpus(st, [u.key for u in todo], log)
        for key, name in corpus.items():
            prev = data["units"].get(key)
            if prev is None or prev.get("source") == "corpus":
                data["units"][key] = {"name": name, "source": "corpus", "retrieved": _today()}
        left = [u for u in todo if u.key not in data["units"]]
        log(f"{st}: {len(todo)} units, {len(corpus)} named from the corpus, {len(left)} to fetch")
        if fetch and left:
            keys = {u.key for u in left}
            data["refused"] = [e for e in data["refused"] if e.get("key") not in keys]
            data["unmatched"] = [e for e in data["unmatched"] if e.get("key") not in keys]
            res = from_official(st, left, fetcher, log)
            data["units"].update(res["units"])
            data["refused"] += res["refused"]
            data["unmatched"] += res["unmatched"]
            log(f"{st}: {len(res['units'])} named from official pages, {len(res['refused'])} refused, "
                f"{len(res['unmatched'])} unmatched")
        save(data, path)
    return data


def report(units: dict[str, Unit], data: dict, examples: int = 5) -> str:
    lines = []
    by_state: dict[str, list[Unit]] = {}
    for u in units.values():
        by_state.setdefault(u.state, []).append(u)
    refused = {e["key"] for e in data.get("refused", [])}
    total = {"units": 0, "corpus": 0, "official": 0, "refused": 0, "unmatched": 0}
    for st in sorted(by_state):
        us = by_state[st]
        named = {u.key: data["units"][u.key] for u in us if u.key in data["units"]}
        corpus = sum(1 for e in named.values() if e["source"] == "corpus")
        official = len(named) - corpus
        ref = sum(1 for u in us if u.key not in named and u.key in refused)
        unm = len(us) - len(named) - ref
        for k, v in zip(total, (len(us), corpus, official, ref, unm)):
            total[k] += v
        lines.append(f"{st}: {len(us)} units, {corpus} from corpus, {official} from official pages, {ref} refused, "
                     f"{unm} unmatched")
        for key, e in list(named.items())[:examples]:
            lines.append(f"    {key}: {e['name']!r}  [{e['source']}]")
    lines.append(f"all: {total['units']} units, {total['corpus']} from corpus, {total['official']} from official "
                 f"pages, {total['refused']} refused, {total['unmatched']} unmatched")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--fetch", action="store_true", help="read the official pages for units the corpus does not name")
    ap.add_argument("--states", nargs="*", help="only these states")
    ap.add_argument("--units", help="a JSON file {unit key: act_id prefix} (the graph's units) instead of wikibase_items")
    ap.add_argument("--graph", action="store_true", help="the units of graph.build (read-only) as well")
    ap.add_argument("--no-drafts", action="store_true", help="with --graph: reviewed and agreed models only")
    ap.add_argument("--no-archive", action="store_true", help="never ask the Internet Archive for a refused page")
    ap.add_argument("--redo", action="store_true", help="read the official pages again (from the cache where they are "
                    "cached) for every unit the corpus does not name")
    ap.add_argument("--fixture", default=str(FIXTURE))
    ap.add_argument("--examples", type=int, default=5)
    a = ap.parse_args(argv)
    log = lambda s: print(s, file=sys.stderr)  # noqa: E731
    units: dict[str, Unit] = {}
    if a.units:
        given = json.loads(sys.stdin.read() if a.units == "-" else Path(a.units).read_text(encoding="utf-8"))
        by_state: dict[str, list[str]] = {}
        for key, prefix in (given.items() if isinstance(given, dict) else ((k, None) for k in given)):
            st = key.split(":")[2]
            by_state.setdefault(st, []).append(prefix or key.split(":", 3)[3])
        for st, prefixes in sorted(by_state.items()):
            if not a.states or st in {s.lower() for s in a.states}:
                units.update(units_for_prefixes(st, prefixes, log))
    else:
        from ..store import db
        con = db.connect()
        try:
            units.update(units_in_wikibase(con, a.states, log))
            if a.graph:
                units.update(units_in_graph(con, drafts=not a.no_drafts, states=a.states, log=log))
        finally:
            con.close()
    log(f"{len(units)} units")
    data = load(Path(a.fixture))
    if a.redo:
        keep = {s.lower() for s in a.states} if a.states else None
        drop = {k for k, e in data["units"].items() if e.get("source") != "corpus"
                and (keep is None or k.split(":")[2] in keep)}
        data["units"] = {k: e for k, e in data["units"].items() if k not in drop}
    data = build(units, fetch=a.fetch, states=a.states, archive=not a.no_archive, data=data, path=Path(a.fixture),
                 log=log)
    print(report(units, data, a.examples))
    return 0


if __name__ == "__main__":
    sys.exit(main())
