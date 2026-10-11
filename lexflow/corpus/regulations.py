"""State regulations (open-us-law's regulations add-on) as search indexes beside the statutes.

    data/index/regulations_<state>.sqlite
      the statute index's tables and ranking (lexflow/ask/index.py: sec, body and fts, the BM25 weights, synthetic
      headings and effective dates), with three more columns at the end of sec:
      kind              'regulation' (the file's document_type), so results put together from several corpora say
                        what each hit is (docs/design/data-expansion.md E1)
      citation_short    the file's short citation: '13VAC5-63-80', '12-A DCMR 105', 'COMAR 09.12.51.04'
      norm_short        the same normalised, which index.lookup() tries after the full citation

The rows come from ``us_<state>_regulations.parquet`` where the statutes step has already downloaded it (``lexflow
run statutes --regulations``).  Nothing is downloaded here, and the federal file is never read.  As for the
statutes (statutes._prepare), only the rows in force, or with no status at all, are kept.  Superseded versions and
repealed, reserved and transferred stubs are left out (data-expansion.md §2.3).

The text is the state's own, as the official publisher's page gives it and the file records it, with that page's
URL.  Where a regulation adopts a model code by reference, the index holds only the state's text.  No model-code text
is ever added (data-expansion.md E5).

Every index.py helper takes the corpus:

    from lexflow.ask import index as I
    I.search("va", I.match([["shed"], ["deck"]]), corpus="regulations")
    I.lookup("va", "13VAC5-63-80", with_text=True, corpus="regulations")
"""
from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Callable

from ..ask import index as I
from ..municipal import states as S
from ..municipal import statutes
from ..municipal.fetch import Log

CORPUS = "regulations"          # the index files' prefix, and open-us-law's name for the file kind
KIND = "regulation"             # sec.kind where the file gives no document_type
VERSION = "1"                   # this corpus's own columns: bumping it rebuilds the regulations indexes only
EXTRA = ("kind", "citation_short", "norm_short")     # sec columns after the statute ones (index._build)
CITES = ("norm_short",)                              # normalised citations index.lookup() tries
COLUMNS = [*statutes.COLUMNS, "citation_short", "document_type"]
FILE = re.compile(r"us_([a-z]{2})_regulations\.parquet")
# a number at the start of a heading, with the word before it: 'Section 300. ', 'Rule 109:1-1-08. ', 'Ch. 860: ',
# 'Ch. 1, § 4. ', '11D-10.003. ', 'Section 1305.110  ' (two spaces).  The number starts with a digit and has no run
# of three letters, so 'COVID-19', 'PM-10' and 'S-275—Definition' are headings, not numbers
LABEL = re.compile(r"^(?:(?:section|sec\.|rule|chapter|ch\.|§+)\s*)?(?!\S*[a-z]{3})[-–.]?\d[\w.\-–:/]*"
                   r"(?:,?\s*§+\s*\d[\w.\-–]*)?\s*(?:[.:]\s+|\s{2,}|$)", re.I)


def path_for(state: str) -> Path:
    return statutes.path_for(state, CORPUS)


def have(state: str) -> bool:
    return path_for(state).exists()


def states() -> list[str]:
    """The states (DC and Puerto Rico among them) whose regulations file is on disk, in the usual order.  One
    directory listing, not a stat per state: the raw files sit on a bind mount from the host."""
    try:
        names = {m.group(1) for p in statutes.DIR.iterdir() if (m := FILE.fullmatch(p.name))}
    except OSError:
        return []
    return [s for s in S.CODES if s in names]


def load(state: str):
    """One state's regulations in force, in the shape statutes.load() gives, plus ``ref``, ``kind``,
    ``citation_short`` and ``norm_short``.  Not cached: only a build reads the whole file."""
    import pandas as pd
    import pyarrow.parquet as pq
    p = path_for(state)
    if not p.exists():
        raise FileNotFoundError(f"regulations for {state} are not downloaded")
    names = set(pq.ParquetFile(p).schema_arrow.names)
    return prepare(pd.read_parquet(p, columns=[c for c in COLUMNS if c in names]))


def prepare(df):
    """Rows as statutes._prepare() leaves them, then four more steps:

    * the citation or number each heading starts with is taken off, as _prepare does for '§ 2.2-3704.';
    * ``kind`` is the file's document_type;
    * ``norm_short`` is the normalised short citation;
    * ``ref`` is the short citation where no other row in force has it ('13VAC5-63-80').  Otherwise it is the bare
      number where that is unique, else the full citation.  DC numbers its sections within each title ('105'), so
      the statutes' one-code rule would make refs ambiguous here."""
    df = df.copy()
    for c in COLUMNS:
        if c not in df:
            df[c] = None
    df = statutes._prepare(df)
    df["citation_short"] = df["citation_short"].fillna("").astype(str).str.strip()
    df["section_title"] = [_title(t, (s, n, c)) for t, s, n, c in
                           zip(df["section_title"], df["citation_short"], df["section_number"], df["citation"])]
    df["kind"] = df["document_type"].fillna(KIND).replace("", KIND)
    df["norm_short"] = [statutes._norm_cite(s) or None for s in df["citation_short"]]
    shorts, numbers = df["norm_short"].value_counts(), df["norm_section"].value_counts()
    df["ref"] = [s if ns and shorts.get(ns, 0) == 1
                 else num if isinstance(num, str) and num and numbers.get(n, 0) == 1 else cite
                 for s, ns, num, n, cite in zip(df["citation_short"], df["norm_short"], df["section_number"],
                                                df["norm_section"], df["citation"])]
    return df


def _title(title, prefixes) -> str:
    """A heading without the citation or number it starts with: '13VAC5-63-80. Application for permit' ->
    'Application for permit'; 'ARSD 02:01:08:01. 2:01:08:01. Reserve officer certification' -> 'Reserve officer
    certification'.  A heading left with no word ('-', or the number alone) becomes '', which index._heading()
    replaces with the code's name and the section's first sentence."""
    t = str(title or "").strip()
    for p in prefixes:
        p = str(p or "").strip()        # only a citation or number: Connecticut numbers some rows 'APPENDIX C'
        if re.search(r"\d", p) and t.lower().startswith(p.lower()) and (len(t) == len(p) or not t[len(p)].isalnum()):
            t = t[len(p):].lstrip(" .:;-–—\t")
            break
    for _ in range(2):
        t, n = LABEL.subn("", t, count=1)
        if not n:
            break
    return t.strip() if re.search(r"[^\W\d_]", t) else ""


def ready(state: str) -> bool:
    return I.ready(state, corpus=CORPUS)


def build_all(only: list[str] | None = None, force: bool = False, log: Log = print,
              progress: Callable[[float], None] | None = None) -> dict:
    """Build the regulations index of every state with a file on disk (or of those in ``only``), where it is
    missing or stale, or always with ``force``.  Per state, the result is index.build()'s numbers (sections,
    seconds, MB), "ready" when it was current, or "no file"."""
    have = states()
    sts = have if only is None else list(dict.fromkeys(only))
    out: dict[str, dict | str] = {}
    t0 = time.time()
    for i, st in enumerate(sts):
        if st not in have:
            out[st] = "no file"
            log(f"{S.NAME.get(st, st)}: no regulations file on disk (run the statutes step with regulations)")
        elif force or not ready(st):
            out[st] = I.build(st, log=log, corpus=CORPUS)
        else:
            out[st] = "ready"
        if progress:
            progress((i + 1) / max(1, len(sts)))
    built = [v for v in out.values() if isinstance(v, dict)]
    if built:
        log(f"regulations: {len(built)} indexes built, {sum(v['sections'] for v in built):,} sections, "
            f"{sum(v['mb'] for v in built):,.0f} MB, in {time.time() - t0:.0f}s")
    return out
