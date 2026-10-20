"""National legislation beside the US statutes: one adapter per country (lexflow/corpus/countries/<cc>.py), index
rows in the US shape, one SQLite per country at ``data/index/countries_<cc>.sqlite``.

    from lexflow.corpus import countries as C
    C.get("cl").fetch_document("141599")            # one law, read-only, paced
    C.rows_for("cl", doc)                           # index rows (base.Country.to_rows)
    C.load_fixture("jp")                            # fixtures/corpus/jp/sample.json as index rows

As a corpus for lexflow/ask/index.py (``index.build("jp", corpus="countries")``) this package serves ``have``,
``load`` and ``path_for``: the rows come from ``data/raw/countries/<cc>.jsonl`` (one row per line, as
``Country.to_rows`` wrote them), which a pull step writes after approval (docs/design/global-sources.md §6).  Until
then only the fixtures exist, and ``load`` falls back to the fixture so the index can be built for tests.

The adapters are prototypes for Chile (LeyChile XML) and Japan (e-Gov 法令API), and stubs for Peru, Australia,
Romania and Ghana that carry the verified source metadata and raise NotImplementedError with the reason
(``Country.note``).  The registry proposal for municipal/states.py is ``JURISDICTIONS`` below.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from ... import config
from .base import COLUMNS, EXTRA as _EXTRA, Country, Document, Node, Source, act_id, eli_uri  # noqa: F401

CORPUS = "countries"
VERSION = "1"                                   # bump to rebuild the country indexes only (index._stamp)
EXTRA = (*_EXTRA, "norm_eli")                    # sec columns after the statute ones (a CITES column is one too)
CITES = ("norm_eli",)                            # index.lookup() tries the normalised ELI after the citation
DIR = config.RAW_DIR / "countries"
FIXTURES = config.ROOT / "fixtures" / "corpus"


def _adapters() -> dict[str, Country]:
    from .australia import Australia
    from .chile import Chile
    from .ghana import Ghana
    from .japan import Japan
    from .peru import Peru
    from .romania import Romania
    return {c.code: c for c in (Peru(), Chile(), Australia(), Romania(), Ghana(), Japan())}


ADAPTERS: dict[str, Country] = _adapters()
CODES = list(ADAPTERS)
NAME = {c: a.name for c, a in ADAPTERS.items()}
WIKIDATA = {c: a.wikidata for c, a in ADAPTERS.items()}

# the registry entries proposed for municipal/states.py (docs/design/global-sources.md §5): code, name, Wikidata
# item (verified read-only against the item pages on 19 October 2026), legal-code label, language tag of the law
JURISDICTIONS: list[dict] = [
    {"code": "pe", "name": "Peru", "wikidata": "Q419", "code_label": "Legislación peruana (SPIJ)", "language": "es",
     "other_languages": ["qu", "ay"]},
    {"code": "cl", "name": "Chile", "wikidata": "Q298", "code_label": "Legislación chilena (Ley Chile)", "language": "es"},
    {"code": "au", "name": "Australia", "wikidata": "Q408", "code_label": "Commonwealth Acts (Federal Register of "
     "Legislation)", "language": "en", "subnational": ["nsw", "vic", "qld", "wa", "sa", "tas", "act", "nt"]},
    {"code": "ro", "name": "Romania", "wikidata": "Q218", "code_label": "Legislația României (Portal Legislativ)",
     "language": "ro"},
    {"code": "gh", "name": "Ghana", "wikidata": "Q117", "code_label": "Acts of the Parliament of Ghana", "language": "en"},
    {"code": "jp", "name": "Japan", "wikidata": "Q17", "code_label": "日本の法令 (e-Gov法令検索)", "language": "ja"},
]


def get(code: str) -> Country:
    try:
        return ADAPTERS[code.lower()]
    except KeyError:
        raise ValueError(f"unknown country: {code!r}") from None


def rows_for(code: str, doc: Document) -> list[dict]:
    return get(code).to_rows(doc)


# ------------------------------------------------------------------ the corpus interface (ask/index._source)
def path_for(code: str) -> Path:
    return DIR / f"{code.lower()}.jsonl"


def fixture_path(code: str) -> Path:
    return FIXTURES / code.lower() / "sample.json"


def have(code: str) -> bool:
    return path_for(code).exists() or fixture_path(code).exists()


def states() -> list[str]:
    """The countries with rows on disk, in registry order."""
    return [c for c in CODES if have(c)]


@lru_cache(maxsize=None)
def load_document(code: str) -> Document | None:
    """The fixture's law as a Document (None when the country has no fixture)."""
    p = fixture_path(code)
    if not p.exists():
        return None
    return Document.from_json(json.loads(p.read_text(encoding="utf-8"))["document"])


def load_fixture(code: str):
    doc = load_document(code)
    return prepare(rows_for(code, doc)) if doc else None


def load(code: str):
    """Every row of a country as a DataFrame in the shape statutes.load() gives, plus the EXTRA columns, ``ref``
    and ``norm_eli``: from the pulled rows when they exist, else from the fixture."""
    p = path_for(code)
    if p.exists():
        rows = [json.loads(ln) for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]
        return prepare(rows)
    df = load_fixture(code)
    if df is None:
        raise FileNotFoundError(f"{NAME.get(code, code)}: no rows on disk and no fixture")
    return df


def prepare(rows: list[dict]):
    """Rows -> DataFrame as municipal/statutes._prepare leaves them (in force only, norm_section), with the country
    columns kept and the normalised ELI for lookup."""
    import pandas as pd
    from ...municipal import statutes
    df = pd.DataFrame(rows)
    for c in [*COLUMNS, *EXTRA, "ref", "effective_from", "effective_until"]:
        if c not in df:
            df[c] = None
    df = statutes._prepare(df)
    df["norm_eli"] = df["eli"].fillna("").map(lambda e: statutes._norm_cite(work_iri(e)))
    return df


def work_iri(eli: str) -> str:
    """The ELI work IRI of an expression IRI: ``.../art_4/es@2022-11-10`` -> ``.../art_4`` (index.lookup() finds a
    row by the work IRI, whatever version is indexed)."""
    head, _, last = (eli or "").rpartition("/")
    return head if "@" in last else eli
