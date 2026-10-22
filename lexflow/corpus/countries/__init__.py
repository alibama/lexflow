"""National legislation beside the US statutes: one adapter per country (lexflow/corpus/countries/<name>.py), index
rows in the US shape.

**Keys.**  A country's lexflow key is its ISO 3166-1 alpha-3 code in lower case (``jpn``; later ``chl``, ``aus``,
``rou``, ``gha``, ``per``), so it never collides with a US state's two-letter postal code (``co``, ``de``, ``in``,
``md``, ``pa`` ...) in index file names, jurisdiction pickers or wiki keys (``lexflow:code:jpn``).  ``get`` also
accepts the alpha-2 code (``jp``) as an alias; the ELI IRIs keep the alpha-2 jurisdiction (``/eli/jp/...``), as ELI
publishers write it (docs/design/global-sources.md §4.1).

    from lexflow.corpus import countries as C
    C.get("jpn").fetch_document("405AC0000000088")  # one law, read-only, paced
    C.rows_for("jpn", doc)                          # index rows (base.Country.to_rows)
    C.load_fixture("jpn")                           # fixtures/corpus/jpn/sample.json as index rows

As a corpus for lexflow/ask/index.py this package serves ``have``, ``load``, ``iter_rows`` and ``path_for``, under
two names: ``index.build("jpn")`` writes ``data/index/statutes_jpn.sqlite`` (a country with its law on disk is a
jurisdiction like a state: the Ask flow, the dashboard and the Query page read it there), and
``index.build("jpn", corpus="countries")`` writes ``countries_jpn.sqlite`` (the tests).  The rows come from the
country's own download when it is on disk (Japan: the official bulk zip, streamed one law at a time by
``japan.iter_documents``), else from ``data/raw/countries/<key>.jsonl`` (one row per line, as ``Country.to_rows``
wrote them), else from the fixture.  ``tokenizer`` names the FTS5 tokenizer per language (``trigram`` for Japanese,
the statutes' ``porter unicode61`` otherwise) and ``post_build`` writes the per-law table (``law``) the wiki graph
reads.

The adapters are prototypes for Chile (LeyChile XML) and Japan (e-Gov 法令標準XML and 法令API), and stubs for Peru,
Australia, Romania and Ghana that carry the verified source metadata and raise NotImplementedError with the reason
(``Country.note``).  The registry is ``JURISDICTIONS`` below (and lexflow/municipal/states.py ``COUNTRIES``).
"""
from __future__ import annotations

import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from types import SimpleNamespace
from typing import Iterator

from ... import config
from .base import COLUMNS, EXTRA as _EXTRA, Country, Document, Node, Source, act_id, eli_uri  # noqa: F401

CORPUS = "countries"
VERSION = "2"                                   # bump to rebuild the country indexes only (index._stamp)
EXTRA = (*_EXTRA, "norm_eli", "norm_num")        # sec columns after the statute ones (the CITES columns too)
CITES = ("norm_eli", "norm_num")                 # index.lookup() tries the ELI work IRI, then the numeral-free cite
DIR = config.RAW_DIR / "countries"
FIXTURES = config.ROOT / "fixtures" / "corpus"
CJK_LANGUAGES = {"ja", "zh", "ko"}
TRIGRAM = "trigram"
HEAD_CHARS = {"ja": 250, "zh": 250, "ko": 300}   # characters of each article kept in sec.head (index.HEAD otherwise)

# ISO 3166-1 alpha-2 -> alpha-3 for the registry's countries: the alias table of ``key_of``
ISO3 = {"pe": "per", "cl": "chl", "au": "aus", "ro": "rou", "gh": "gha", "jp": "jpn", "br": "bra"}


def key_of(code: str) -> str:
    """The lexflow key of a country: ``jp`` or ``JPN`` -> ``jpn``."""
    c = (code or "").strip().lower()
    return ISO3.get(c, c)


def _adapters() -> dict[str, Country]:
    from .australia import Australia
    from .australia_states import STATES as AUS_STATES     # aus-nsw, aus-vic ... (subnational, parent "aus")
    from .chile import Chile
    from .ghana import Ghana
    from .japan import Japan
    from .peru import Peru
    from .romania import Romania
    from .brazil import Brazil
    return {key_of(c.code): c for c in (Peru(), Chile(), Australia(), *AUS_STATES, Romania(), Ghana(), Japan(),
                                        Brazil())}


ADAPTERS: dict[str, Country] = _adapters()
CODES = list(ADAPTERS)
NAME = {c: a.name for c, a in ADAPTERS.items()}
WIKIDATA = {c: a.wikidata for c, a in ADAPTERS.items()}

# the registry (docs/design/global-sources.md §5): key (alpha-3), alpha-2, name, Wikidata item (verified read-only
# against the item pages on 19 October 2026), legal-code label (per language for the implemented ones), language
# tags of the law, official site
JURISDICTIONS: list[dict] = [
    {"code": "per", "iso2": "pe", "name": "Peru", "wikidata": "Q419", "code_label": "Legislación peruana (SPIJ)",
     "language": "es", "languages": ["es"], "other_languages": ["qu", "ay"], "website": "https://spij.minjus.gob.pe/"},
    {"code": "chl", "iso2": "cl", "name": "Chile", "wikidata": "Q298", "code_label": "Legislación chilena (Ley Chile)",
     "language": "es", "languages": ["es"], "website": "https://www.bcn.cl/leychile/"},
    {"code": "aus", "iso2": "au", "name": "Australia", "wikidata": "Q408", "code_label": "Commonwealth Acts (Federal "
     "Register of Legislation)", "language": "en", "languages": ["en"],
     "subnational": ["aus-nsw", "aus-vic", "aus-qld", "aus-wa", "aus-sa", "aus-tas", "aus-act", "aus-nt"],
     "website": "https://www.legislation.gov.au/"},
    {"code": "rou", "iso2": "ro", "name": "Romania", "wikidata": "Q218", "code_label": "Legislația României (Portal "
     "Legislativ)", "language": "ro", "languages": ["ro"], "website": "https://legislatie.just.ro/"},
    {"code": "gha", "iso2": "gh", "name": "Ghana", "wikidata": "Q117", "code_label": "Acts of the Parliament of Ghana",
     "language": "en", "languages": ["en"], "website": "https://repository.parliament.gh/"},
    {"code": "jpn", "iso2": "jp", "name": "Japan", "wikidata": "Q17", "code_label": "日本の法令 (e-Gov法令検索)",
     "code_labels": {"ja": "日本の法令", "en": "Laws of Japan"}, "language": "ja", "languages": ["ja"],
     "website": "https://laws.e-gov.go.jp/"},
    {"code": "bra", "iso2": "br", "name": "Brazil", "wikidata": "Q155", "code_label": "Legislação federal brasileira",
     "code_labels": {"pt": "Legislação federal brasileira", "en": "Federal legislation of Brazil"}, "language": "pt",
     "languages": ["pt"], "website": "https://normas.leg.br/",
     "official_sites": ["https://normas.leg.br/", "https://legis.senado.leg.br/dadosabertos/",
                        "https://www.lexml.gov.br/", "https://www.planalto.gov.br/ccivil_03/"]},
]
# Australia's states and territories (australia_states.py) follow Australia, in the adapters' order; Wikidata items
# verified read-only against the item pages on 22 October 2026
_AUS = next(i for i, j in enumerate(JURISDICTIONS) if j["code"] == "aus")
JURISDICTIONS[_AUS + 1:_AUS + 1] = [
    {"code": a.code, "parent": "aus", "iso3166_2": a.code.upper().replace("AUS-", "AU-"), "name": a.name,
     "wikidata": a.wikidata, "code_label": a.code_label, "language": "en", "languages": ["en"],
     "website": a.sources[0].url, "status": a.status}
    for a in ADAPTERS.values() if getattr(a, "parent", "") == "aus"]
BY_KEY = {j["code"]: j for j in JURISDICTIONS}


def get(code: str) -> Country:
    try:
        return ADAPTERS[key_of(code)]
    except KeyError:
        raise ValueError(f"unknown country: {code!r}") from None


def is_country(code: str) -> bool:
    """Whether a jurisdiction key names a country of the registry (alpha-3; never a US postal code)."""
    return (code or "").strip().lower() in ADAPTERS


def rows_for(code: str, doc: Document) -> list[dict]:
    return get(code).to_rows(doc)


def language(code: str) -> str:
    a = get(code)
    return a.languages[0] if a.languages else ""


def tokenizer(code: str) -> str | None:
    """The FTS5 tokenizer of a country's index: ``trigram`` for a CJK language (substring search, no segmenter
    needed; index.phrase/search handle terms shorter than three characters), else the adapter's own ``tokenize``
    when it names one (Brazil: ``unicode61 remove_diacritics 2``, accent-insensitive and without the English porter
    stemmer), else None (the statutes' own)."""
    if language(code) in CJK_LANGUAGES:
        return TRIGRAM
    return getattr(get(code), "tokenize", None) or None


def head_chars(code: str) -> int | None:
    return HEAD_CHARS.get(language(code))


def licence_note(code: str) -> str:
    """What an answer quoting this country's law says about its source and licence."""
    a = get(code)
    mod = _module(code)
    att = getattr(mod, "ATTRIBUTION_EN", "") or (a.sources[0].licence if a.sources else "")
    return att + ((" " + getattr(mod, "EDIT_NOTE_EN")) if getattr(mod, "EDIT_NOTE_EN", "") else "")


def _module(code: str):
    import importlib
    return importlib.import_module(type(get(code)).__module__)


# ------------------------------------------------------------------ the corpus interface (ask/index._source)
def path_for(code: str) -> Path:
    """The file a country's index is stamped with: its own download (Japan's bulk zip) when it is on disk, else
    ``data/raw/countries/<key>.jsonl``."""
    a = ADAPTERS.get(key_of(code))
    name = getattr(a, "raw_name", "") if a is not None else ""
    if name and (DIR / name).exists():
        return DIR / name
    return DIR / f"{key_of(code)}.jsonl"


def fixture_path(code: str) -> Path:
    """``fixtures/corpus/<key>/sample.json``, or under the adapter's own code or the alpha-2 code while an adapter
    still uses it."""
    key = key_of(code)
    cands = [key]
    a = ADAPTERS.get(key)
    if a is not None:
        cands += [a.code, getattr(a, "iso2", "") or ""]
    cands += [k for k, v in ISO3.items() if v == key]
    for c in dict.fromkeys(x.lower() for x in cands if x):
        p = FIXTURES / c / "sample.json"
        if p.exists():
            return p
    return FIXTURES / key / "sample.json"


def have(code: str) -> bool:
    if key_of(code) not in ADAPTERS:
        return False
    return path_for(code).exists() or fixture_path(code).exists()


def states() -> list[str]:
    """The countries with rows on disk, in registry order."""
    return [c for c in CODES if have(c)]


def bulk(code: str) -> bool:
    """Whether a country's own download is on disk (not only the fixture)."""
    return path_for(code).exists()


@lru_cache(maxsize=None)
def load_document(code: str) -> Document | None:
    """The fixture's law as a Document (None when the country has no fixture); its ``country`` is the adapter's."""
    p = fixture_path(code)
    if not p.exists():
        return None
    doc = Document.from_json(json.loads(p.read_text(encoding="utf-8"))["document"])
    doc.country = get(code).code
    return doc


def load_fixture(code: str):
    doc = load_document(code)
    return prepare(rows_for(code, doc)) if doc else None


def load(code: str):
    """Every row of a country as a DataFrame in the shape statutes.load() gives, plus the EXTRA columns, ``ref``
    and the normalised cites: from the pulled rows when they exist, else from the fixture.  (A country with a bulk
    download is indexed by ``iter_rows``, which never holds the whole corpus.)"""
    p = DIR / f"{key_of(code)}.jsonl"
    if p.exists():
        rows = [json.loads(ln) for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]
        return prepare(rows)
    if path_for(code).is_dir():                     # one file per law (Australia): the whole corpus as a frame
        rows = []
        for f in sorted(path_for(code).glob("*.jsonl")):
            with open(f, encoding="utf-8") as fh:
                rows += [json.loads(ln) for ln in fh if ln.strip()]
        return prepare(rows)
    df = load_fixture(code)
    if df is None:
        raise FileNotFoundError(f"{NAME.get(key_of(code), code)}: no rows on disk and no fixture")
    return df


_LAWS: dict[str, list[dict]] = {}               # key -> the per-law summary of the last iter_rows (post_build)


def iter_rows(code: str, log=print) -> Iterator[SimpleNamespace] | None:
    """The rows of a country with a bulk download, one law at a time, prepared as ``prepare`` prepares a frame
    (in force only, ``norm_section``, the normalised cites); None for a country without one (``load`` serves it).
    The per-law summary is kept for ``post_build``."""
    key = key_of(code)
    if not bulk(key) or path_for(key).suffix == ".jsonl":
        return None
    if path_for(key).is_dir():
        return _iter_dir(key, log)
    if key != "jpn":
        return None
    from . import japan as J

    def gen():
        jp = get(key)
        laws: list[dict] = []
        _LAWS[key] = laws
        n = 0
        for doc in J.iter_documents(path_for(key), log=log):
            rows = jp.to_rows(doc)
            kept = 0
            for r in rows:
                r = prepare_row(r)
                if r is None:
                    continue
                kept += 1
                yield SimpleNamespace(**r)
            laws.append(law_summary(doc, rows, kept))
            n += 1
            if n % 1000 == 0:
                log(f"{key}: {n:,} laws read")
    return gen()


def _iter_dir(key: str, log=print) -> Iterator[SimpleNamespace]:
    """A country pulled one law per file (the adapter's ``raw_name`` is a directory of ``<law>.jsonl`` files, as
    ``Country.to_rows`` wrote them: Australia's ``aus/rows``): the files in name order, one law in memory at a
    time; the adapter module's ``law_summary(rows, kept)`` gives the ``law`` table's row for each."""
    summary = getattr(_module(key), "law_summary", None)

    def gen():
        laws: list[dict] = []
        _LAWS[key] = laws
        for n, f in enumerate(sorted(path_for(key).glob("*.jsonl")), 1):
            with open(f, encoding="utf-8") as fh:
                rows = [json.loads(ln) for ln in fh if ln.strip()]
            kept = 0
            for r in rows:
                r = prepare_row(r)
                if r is None:
                    continue
                kept += 1
                yield SimpleNamespace(**r)
            if summary is not None and rows:
                laws.append(summary(rows, kept))
            if n % 500 == 0:
                log(f"{key}: {n:,} laws read")
    return gen()


def law_summary(doc: Document, rows: list[dict], kept: int) -> dict:
    from .japan import LAW_TYPE_OF, law_kind_en, law_number_en
    e = dict(doc.extra or {})
    e["law_type"] = e.get("law_type") or LAW_TYPE_OF.get(doc.kind, "")
    return {"law_id": doc.native_id, "title": doc.title, "law_num": doc.number, "law_type": e.get("law_type") or "",
            "kind_en": law_kind_en(doc.number, e.get("law_type") or ""),
            "kind": doc.kind, "category": e.get("category") or "", "abbrev": e.get("abbrev") or "",
            "kana": e.get("law_title_kana") or "", "promulgated": doc.promulgated or "",
            "enforced": doc.version_date or "", "revision_id": e.get("law_revision_id") or "", "url": doc.url,
            "revision_url": e.get("revision_url") or "", "status": doc.status, "rows": kept,
            "articles": sum(1 for r in rows if r["level"] == "条" and "附則" not in r["display_path"]),
            "suppl": sum(1 for r in rows if "附則" in r["display_path"]),
            "main_only": int(any(r["level"] == "本則" for r in rows)), "revisions": e.get("revisions") or 1,
            "future_revisions": e.get("future_revisions") or 0, "in_api_list": int(bool(e.get("in_api_list"))),
            "number_en": law_number_en(doc.number, e.get("law_type") or ""), "eli_work": _law_work(rows)}


def _law_work(rows: list[dict]) -> str:
    """The ELI work IRI of the law itself (its first row's IRI without the unit and the expression)."""
    if not rows:
        return ""
    head = work_iri(rows[0]["eli"])
    return head.rsplit("/", 1)[0]


LAW_TABLE = """CREATE TABLE law(law_id TEXT PRIMARY KEY, title TEXT, law_num TEXT, law_type TEXT, kind TEXT,
    category TEXT, abbrev TEXT, kana TEXT, promulgated TEXT, enforced TEXT, revision_id TEXT, url TEXT,
    revision_url TEXT, status TEXT, rows INTEGER, articles INTEGER, suppl INTEGER, main_only INTEGER,
    revisions INTEGER, future_revisions INTEGER, in_api_list INTEGER, number_en TEXT, eli_work TEXT, kind_en TEXT)"""
LAW_COLUMNS = ["law_id", "title", "law_num", "law_type", "kind", "category", "abbrev", "kana", "promulgated",
               "enforced", "revision_id", "url", "revision_url", "status", "rows", "articles", "suppl", "main_only",
               "revisions", "future_revisions", "in_api_list", "number_en", "eli_work", "kind_en"]


def post_build(code: str, con) -> list[tuple[str, str]]:
    """After the rows: the ``law`` table (one row per law, for the wiki graph and the dashboard) and the meta
    entries (laws, licence, attribution) of a country index."""
    key = key_of(code)
    laws = _LAWS.pop(key, None)
    if laws is None:                                # built from the fixture: its one law
        doc = load_document(key) if not (DIR / f"{key}.jsonl").exists() else None
        rows = rows_for(key, doc) if doc else []
        laws = [law_summary(doc, rows, sum(1 for r in rows if prepare_row(r) is not None))] if doc else []
    con.execute(LAW_TABLE)
    con.executemany(f"INSERT OR REPLACE INTO law VALUES ({','.join('?' * len(LAW_COLUMNS))})",
                    [tuple(x.get(c) for c in LAW_COLUMNS) for x in laws])
    mod = _module(key)
    meta = [("country", key), ("language", language(key)), ("laws", str(len(laws))),
            ("attribution", getattr(mod, "ATTRIBUTION", "")), ("edit_note", getattr(mod, "EDIT_NOTE", "")),
            ("licence_url", get(key).sources[0].licence_url if get(key).sources else "")]
    if key == "jpn":
        from . import japan as J
        b = J.manifest().get("bulk") or {}
        meta += [("source_sha256", b.get("sha256") or ""), ("source_fetched", b.get("fetched") or "")]
    return meta


def laws(code: str, corpus: str = "statutes") -> list[dict]:
    """The ``law`` table of a country's index (empty when the index is not built or has none)."""
    import sqlite3
    from ...ask import index as I
    p = I.path(key_of(code), corpus)
    if not p.exists():
        return []
    con = sqlite3.connect(str(p))
    con.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in con.execute("SELECT * FROM law ORDER BY law_id")]
    except sqlite3.Error:
        return []
    finally:
        con.close()


# ------------------------------------------------------------------ preparing rows
def prepare(rows: list[dict]):
    """Rows -> DataFrame as municipal/statutes._prepare leaves them (in force only, norm_section), with the country
    columns kept and the normalised cites for lookup."""
    import pandas as pd
    from ...municipal import statutes
    df = pd.DataFrame(rows)
    for c in [*COLUMNS, *EXTRA, "ref", "effective_from", "effective_until"]:
        if c not in df:
            df[c] = None
    df = statutes._prepare(df)
    df["norm_eli"] = df["eli"].fillna("").map(lambda e: statutes._norm_cite(work_iri(e)))
    df["norm_num"] = df["citation"].fillna("").map(norm_num)
    return df


_STUB_TITLE = re.compile(r"[–\-]?[\w.\-–]*\d[\w.\-–]*\.?")


def prepare_row(r: dict) -> dict | None:
    """One row as ``prepare`` leaves a frame's rows (statutes._prepare's rules), or None when it is not in force."""
    from ...municipal import statutes
    if r.get("act_status") not in ("in_force", None):
        return None
    out = {c: r.get(c) for c in [*COLUMNS, *_EXTRA, "ref", "effective_from", "effective_until"]}
    title = re.sub(r"^§\s*[\w.:\-/]+\.?\s*", "", out["section_title"] or "")
    out["section_title"] = "" if _STUB_TITLE.fullmatch(title) else title
    out["chapter_name"] = out["chapter_name"] or ""
    out["text"] = out["text"] or ""
    out["norm_section"] = statutes.norm_section(out["section_number"])
    out["norm_eli"] = statutes._norm_cite(work_iri(out["eli"] or ""))
    out["norm_num"] = norm_num(out["citation"] or "")
    return out


def work_iri(eli: str) -> str:
    """The ELI work IRI of an expression IRI: ``.../art_4/es@2022-11-10`` -> ``.../art_4`` (index.lookup() finds a
    row by the work IRI, whatever version is indexed)."""
    head, _, last = (eli or "").rpartition("/")
    return head if "@" in last else eli


_KANJI_NUM = re.compile(r"(第|の)([〇一二三四五六七八九十百千]+)(?=[条項号編章節款目の]|$)")


def norm_num(cite: str) -> str:
    """A citation with its numerals made comparable: NFKC (full-width digits and brackets), no whitespace, kanji
    numerals after 第 or の as digits, lower case.  ``行政手続法 第十三条`` and ``行政手続法第13条`` both give
    ``行政手続法第13条``; ``第三十六条の二`` gives ``第36条の2``.  A Brazilian citation (it opens with Lei, Decreto-Lei,
    Emenda Constitucional, Constituição ...) gets Brazil's own form, ``Lei nº 13.709/2018, art. 5º`` and ``lei 13709/2018
    art 5`` -> ``lei13709/2018art5`` (brazil.cite_key); no other country's citation opens with those words."""
    from .brazil import cite_key
    pt = cite_key(cite)
    if pt is not None:
        return pt
    from .japan import kanji_number
    s = unicodedata.normalize("NFKC", cite or "")
    s = re.sub(r"\s+", "", s)
    s = _KANJI_NUM.sub(lambda m: m.group(1) + str(kanji_number(m.group(2))), s)
    return s.lower()


def normalise(column: str, ref: str) -> str | None:
    """How index.lookup() normalises a reference for one of the CITES columns (None: the statutes' own rule)."""
    if column == "norm_num":
        return norm_num(ref)
    return None
