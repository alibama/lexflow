"""The country adapter: one national legislation source -> index rows in the shape of the US ones.

A ``Country`` names a jurisdiction (ISO 3166-1 alpha-2 code, name, Wikidata item, languages) and its verified
primary sources (``Source``: publisher, URL, what it holds, format, machine access, identifier scheme, licence as
the source states it).  An adapter implements three steps:

    fetch_list(limit)      -> the ids of the laws the source publishes (paced, read-only; a few per call)
    fetch_document(id)     -> one law as a ``Document``: metadata plus a tree of ``Node``s, each level named as the
                              country names it (Título / Capítulo / Artículo; 章 / 節 / 条; Part / Division / Section)
    to_rows(doc)           -> one row per leaf unit (article or section), the columns municipal/statutes.py reads from
                              open-us-law plus the country columns (``EXTRA``), so lexflow/ask/index.py builds the
                              same tables from them (docs/design/global-sources.md §3)

``parse(raw)`` is the pure half of ``fetch_document``: the saved fixture (fixtures/corpus/<cc>/sample.json) is a
``Document`` as ``parse`` returned it, so the tests and the index build need no network.

Identifiers.  Every row carries the source's own id (``native_id``: LeyChile's ``normaId`` and ``idParte``, e-Gov's
``law_id`` and the article number) and an ELI-style work IRI minted as ontology_map.eli_uri does for the states, in
the ELI pattern ``/eli/{jurisdiction}/{type}/{year}/{number}/{unit}`` with the expression ``/{lang}@{date}`` when the
version date is known.  Romania's portal mints real ELIs; where a country does, ``Document.eli`` carries that one and
the minted IRI is not used (global-sources.md §3.2).

act_id keeps open-us-law's token shape (``STATE_CL_LEY19628_TI_A4``) so that ``publish/schema.unit_tokens``,
``publish/ontology_map.eli_uri`` and ``law/ontology.structure`` work unchanged; the ``STATE_`` prefix for a country is
one of the schema decisions listed in global-sources.md §5.

Fetching is read-only and polite: ``config.USER_AGENT``, at least ``pace`` seconds between requests to one host (the
source's crawl-delay where it states one), robots.txt honoured by the caller's choice of endpoints (the endpoints
here are the documented API ones).  Nothing here downloads in bulk: a full pull is a separate, approved step
(global-sources.md §6).
"""
from __future__ import annotations

import datetime as dt
import re
import threading
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Iterable

from ... import config

ELI_BASE = "https://lexipedia.wikibase.cloud/eli"          # the same base ontology_map.eli_uri mints under
COLUMNS = ["act_id", "citation", "section_number", "section_title", "chapter_name", "display_path", "act_status",
           "text", "source_url", "word_count", "last_amended_year"]        # municipal/statutes.COLUMNS, verbatim
EXTRA = ("kind", "language", "eli", "native_id", "level", "country")       # the country columns after them
_PACE: dict[str, float] = {}
_LOCK = threading.Lock()


@dataclass(frozen=True)
class Source:
    """One verified primary source, as docs/design/global-sources.md describes it."""
    name: str
    publisher: str
    url: str
    holds: str                      # consolidated acts, gazette, codes ...
    format: str                     # HTML, XML, JSON, Akoma Ntoso, PDF
    access: str                     # API, bulk export, OAI-PMH, sitemap, none
    identifier: str                 # ELI, national id scheme
    licence: str                    # the licence or terms, quoted from the source
    licence_url: str = ""
    languages: tuple[str, ...] = ()
    verified: str = ""              # date the source was read
    automated_reading: str = ""     # what the terms say about automated reading and reuse
    note: str = ""


@dataclass
class Node:
    """One structural unit of a law in the country's own vocabulary: ``level`` is the source's word for the level
    (``Título``, ``Artículo``, ``章``, ``条``), ``label`` the unit's own label as written (``Título I``, ``第一条``),
    ``number`` the bare number (``I``, ``4``, ``1``), ``heading`` its heading when it has one, ``text`` the text of
    a leaf unit (an article), ``token`` the act_id token (``TI``, ``A4``, ``C1``), ``native_id`` the source's own id."""
    level: str
    label: str
    number: str = ""
    heading: str = ""
    text: str = ""
    token: str = ""
    native_id: str = ""
    status: str = "in_force"        # in_force, repealed, not_yet_in_force
    effective_from: str | None = None
    effective_until: str | None = None
    children: list["Node"] = field(default_factory=list)

    def leaves(self, path: tuple["Node", ...] = ()) -> Iterable[tuple[tuple["Node", ...], "Node"]]:
        """Every leaf unit with the chain of units above it."""
        if not self.children:
            yield path, self
            return
        for c in self.children:
            yield from c.leaves(path + (self,))


@dataclass
class Document:
    """One law as the source gives it: metadata, the tree, and where it came from."""
    country: str                    # ISO 3166-1 alpha-2, lower case
    native_id: str                  # the source's id for the law (LeyChile normaId, e-Gov law_id)
    kind: str                       # the source's type word: ley, act, decreto, 政令 ...
    kind_token: str                 # the act_id token of the law: LEY19628, 354AC0000000043
    number: str                     # the law's number as cited: 19.628, 昭和五十四年法律第四十三号
    title: str                      # the law's title
    short_title: str = ""           # a usual name when the source gives one
    language: str = ""              # BCP 47 of the text
    year: str = ""                  # of promulgation (the ELI year)
    eli_type: str = ""              # the ELI type token: ley, act, decreto
    eli_number: str = ""            # the ELI natural number (19628), where ``number`` is the cited form (19.628)
    eli: str = ""                   # the source's own ELI, when it mints one
    url: str = ""                   # the law's page at the source
    status: str = "in_force"
    version_date: str | None = None     # the consolidated version's date
    promulgated: str | None = None
    published: str | None = None
    last_amended_year: int | None = None
    fetched: str = ""               # ISO date of the read
    source: str = ""                # Source.name
    licence: str = ""               # Source.licence, kept with the sample
    root: Node | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> dict:
        return asdict(self)

    @classmethod
    def from_json(cls, data: dict) -> "Document":
        d = dict(data)
        root = d.pop("root", None)
        doc = cls(**d)
        doc.root = _node_from_json(root) if root else None
        return doc


def _node_from_json(d: dict) -> Node:
    kids = [_node_from_json(c) for c in d.get("children", [])]
    return Node(**{k: v for k, v in d.items() if k != "children"}, children=kids)


def eli_uri(country: str, eli_type: str, year: str, number: str, unit: str = "", lang: str = "",
            date: str | None = None, base: str = ELI_BASE) -> str:
    """``/eli/cl/ley/1999/19628/art_4`` and, with a language and date, ``.../art_4/es@2022-11-10`` (the expression):
    the ELI pattern of jurisdiction, type, year, natural number, subdivision, point in time, language."""
    parts = [base, country.lower(), _slug(eli_type), _slug(year), _slug(number)]
    if unit:
        parts.append(_slug(unit))
    work = "/".join(p for p in parts if p)
    if lang and date:
        return f"{work}/{lang}@{date}"
    return work


def _slug(s: str) -> str:
    s = re.sub(r"[\s]+", "_", str(s or "").strip())
    return re.sub(r"[^\w.\-]+", "", s).strip("_").lower()


def act_id(country: str, law_token: str, tokens: Iterable[str]) -> str:
    """``STATE_CL_LEY19628_TI_A4``: open-us-law's shape, so the schema's token helpers apply."""
    toks = [t for t in [law_token, *tokens] if t]
    return "_".join(["STATE", country.upper(), *toks])


class Country:
    """The adapter base.  Subclasses set the class attributes and implement ``fetch_list``, ``fetch_document`` and
    ``parse``; ``to_rows`` is shared and reads the tree.  ``pace`` is the seconds between requests to the source."""
    code: str = ""                  # ISO 3166-1 alpha-2, lower case
    name: str = ""
    wikidata: str = ""              # Qid, verified read-only against the item page
    languages: tuple[str, ...] = ()
    code_label: str = ""            # the legal-code label for the jurisdiction's code item (lexflow:code:<cc>)
    sources: tuple[Source, ...] = ()
    pace: float = 1.5
    citation_template: str = "{title}, {label}"     # how the country cites a unit
    status: str = "prototype"       # prototype | stub

    # ------------------------------------------------------------------ to implement
    def fetch_list(self, limit: int = 20) -> list[dict]:
        raise NotImplementedError(f"{self.name}: no adapter yet ({self.note})")

    def fetch_document(self, native_id: str) -> Document:
        raise NotImplementedError(f"{self.name}: no adapter yet ({self.note})")

    def parse(self, raw: bytes | str, native_id: str = "") -> Document:
        raise NotImplementedError(f"{self.name}: no adapter yet ({self.note})")

    note: str = ""

    # ------------------------------------------------------------------ shared
    def get(self, url: str, accept: str = "*/*", timeout: int = 60):
        """One paced, read-only GET with lexflow's user agent."""
        import requests
        from urllib.parse import urlsplit
        host = urlsplit(url).netloc
        with _LOCK:
            wait = _PACE.get(host, 0) + self.pace - time.time()
            if wait > 0:
                time.sleep(wait)
            _PACE[host] = time.time()
        r = requests.get(url, timeout=timeout, headers={"User-Agent": config.USER_AGENT, "Accept": accept})
        r.raise_for_status()
        return r

    def citation(self, doc: Document, path: tuple[Node, ...], leaf: Node) -> str:
        return self.citation_template.format(title=doc.short_title or doc.title, number=doc.number,
                                             label=leaf.label, n=leaf.number, kind=doc.kind)

    def unit_slug(self, leaf: Node, path: tuple[Node, ...] = ()) -> str:
        """The ELI subdivision token of a leaf: ``art_4``, ``sec_12`` (``path`` is the chain of units above it, for
        countries whose article numbers restart inside a unit)."""
        word = {"artículo": "art", "articulo": "art", "article": "art", "条": "art", "section": "sec", "§": "sec",
                "articol": "art"}.get(leaf.level.lower(), _slug(leaf.level)[:4] or "u")
        return f"{word}_{_slug(leaf.number) or _slug(leaf.label)}"

    def to_rows(self, doc: Document) -> list[dict]:
        """One row per leaf unit, in document order, in the shape index._build reads (COLUMNS, then EXTRA, then
        ``ref``).  ``display_path`` starts with the law's title and names every level as the country does."""
        if doc.root is None:
            return []
        rows: list[dict] = []
        lang = doc.language or (self.languages[0] if self.languages else "")
        for path, leaf in doc.root.leaves():
            units = [n for n in path if n is not doc.root]
            tokens = [n.token for n in units if n.token] + ([leaf.token] if leaf.token else [])
            chapter = next((n.heading or n.label for n in reversed(units) if n.level), "")
            elements = [doc.short_title or doc.title] + [_element(n) for n in units] + [_element(leaf, leaf=True)]
            text = (leaf.text or "").strip()
            status = leaf.status if leaf.status != "in_force" else doc.status
            eli = doc.eli or eli_uri(doc.country, doc.eli_type or doc.kind, doc.year, doc.eli_number or doc.number,
                                     self.unit_slug(leaf, path))
            date = leaf.effective_from or doc.version_date
            rows.append({
                "act_id": act_id(doc.country, doc.kind_token, tokens),
                "citation": self.citation(doc, path, leaf),
                "section_number": leaf.number or leaf.label,
                "section_title": leaf.heading or "",
                "chapter_name": chapter,
                "display_path": " / ".join(e for e in elements if e),
                "act_status": status,
                "text": text,
                "source_url": doc.url,
                "word_count": len(text.split()) if " " in text else len(text),   # characters for Japanese
                "last_amended_year": doc.last_amended_year,
                "kind": doc.kind,
                "language": lang,
                "eli": f"{eli}/{lang}@{date}" if lang and date and not doc.eli else eli,
                "native_id": f"{doc.native_id}#{leaf.native_id}" if leaf.native_id else doc.native_id,
                "level": leaf.level,
                "country": doc.country,
                "ref": self.citation(doc, path, leaf),
                "effective_from": leaf.effective_from or doc.version_date,
                "effective_until": leaf.effective_until,
            })
        return rows

    def today(self) -> str:
        return dt.date.today().isoformat()


def _element(n: Node, leaf: bool = False) -> str:
    """A path element in the country's words: ``Título I`` (the label), with the heading for a unit above the leaf
    (``Título I De la utilización de datos personales`` would be long: the label alone, as open-us-law's paths)."""
    return n.label or (f"{n.level} {n.number}".strip())
