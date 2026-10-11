"""Full-text search over every downloaded statute section: SQLite FTS5, one index file per state.

Each index is built once (seconds for a small state, a minute or two for a large one) and rebuilt when the
statute file changes.  The index is contentless: the text stays in the parquet file, and a small table keeps
each section's reference, heading, path and opening words for display and reranking.

    data/index/statutes_<state>.sqlite
      sec(id, ref, citation, title, chapter, path, url, words, head)
      fts(title, chapter, body)          porter-stemmed, ranked with BM25 (heading weighted most)

Other corpora use the same tables in ``data/index/<corpus>_<state>.sqlite``: every function here takes an optional
``corpus`` (default ``"statutes"``, so a call without one reads and builds the statute index as always).  A corpus
other than the statutes is served by ``lexflow/corpus/<corpus>.py``, which loads its rows and may add columns after
the statute ones (``EXTRA``, such as ``kind``) and normalised citations that ``lookup`` tries (``CITES``).
"""
from __future__ import annotations

import contextlib
import os
import re
import sqlite3
import threading
import time

from .. import config
from ..municipal import statutes
from ..municipal.fetch import Log

VERSION = "2"
HEAD = 700                       # characters of each section kept for display and reranking
WEIGHTS = (10.0, 3.0, 1.0)       # BM25 column weights: heading, chapter, text
EFFECTIVE = re.compile(r"^\s*\((?:Effective|Eff\.)\s[^)]*\)", re.I)       # the heading's leading parenthetical
_DATE = r"([A-Z][a-z]+\.? \d{1,2}, \d{4})"
EFFECTIVE_FROM = re.compile(r"\b(?:Effective|Eff\.)\s+(?!until\b)" + _DATE, re.I)
EFFECTIVE_UNTIL = re.compile(r"\buntil\s+" + _DATE, re.I)
EMPTY_HEADING = re.compile(r"^\s*(?:§+\s*|section\s+)?[\w.:\-–]*\d[\w.:\-–]*\.?\s*$", re.I)


def _heading(title: str, citation: str, chapter: str, text: str) -> str:
    """The heading to index.  Maryland's and California's files carry only a number ('Section 2085.5'), so the
    heading weight would be wasted: use the code's name and the section's first sentence instead."""
    title = (title or "").strip()
    if title and not EMPTY_HEADING.match(title):
        return title
    code = (citation or "").rsplit("§", 1)[0].strip(" ,") or chapter or ""
    first = re.split(r"(?<=[.;:])\s", re.sub(r"^(?:\s*\([A-Za-z0-9]+\))+\s*", "", (text or "").strip()), maxsplit=1)[0]
    return f"{code}: {' '.join(first.split()[:24])}".strip(": ")


def effective(title: str) -> tuple[str | None, str | None]:
    """'(Effective until December 1, 2026) ...' -> (None, '2026-12-01'); '(Effective January 1, 2027) ...' ->
    ('2027-01-01', None); '(Effective July 1, 2026; Effective until October 1, 2026)' -> both.  Dates as ISO
    strings, or None."""
    m = EFFECTIVE.match(title or "")
    if not m:
        return None, None
    start, until = EFFECTIVE_FROM.search(m.group(0)), EFFECTIVE_UNTIL.search(m.group(0))
    return (_iso(start.group(1)) if start else None), (_iso(until.group(1)) if until else None)


def _iso(date: str) -> str | None:
    import datetime as dt
    for fmt in ("%B %d, %Y", "%b. %d, %Y", "%b %d, %Y"):
        try:
            return dt.datetime.strptime(date, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def index_dir():
    return config.DATA_DIR / "index"


CORPUS = "statutes"             # the default corpus: municipal/statutes.py serves it; lexflow/corpus/ the others


def _source(corpus: str):
    """The module that serves a corpus's rows: ``have(state)``, ``load(state)`` and ``path_for(state)`` (the file the
    index is stamped with).  The statutes come from municipal/statutes.py, any other corpus from
    lexflow/corpus/<corpus>.py, which also sets ``VERSION`` and may set ``EXTRA`` and ``CITES``."""
    if corpus == CORPUS:
        return statutes
    if not re.fullmatch(r"[a-z]+", corpus or ""):
        raise ValueError(f"unknown corpus: {corpus!r}")
    import importlib
    return importlib.import_module(f"..corpus.{corpus}", __package__)


def _key(state: str, corpus: str) -> str:
    """The key of a state's index in this module's caches: the bare state for the statutes, as before."""
    return state if corpus == CORPUS else f"{corpus}:{state}"


def path(state: str, corpus: str = CORPUS):
    return index_dir() / f"{corpus}_{state}.sqlite"


_STAMPS: dict[str, tuple[float, str]] = {}


def _stamp(state: str, corpus: str = CORPUS) -> str:
    """The statute file's identity.  Remembered for a minute: the raw downloads sit on a bind mount from the host,
    where each stat costs tens of milliseconds, and the setup page checks every state.  Another corpus's stamp
    also names the corpus and its own VERSION, so its schema can change without rebuilding the statute indexes."""
    key = _key(state, corpus)
    hit = _STAMPS.get(key)
    if hit and time.time() - hit[0] < 60:
        return hit[1]
    src = _source(corpus)
    p = src.path_for(state)
    version = VERSION if corpus == CORPUS else f"{VERSION}-{corpus}{src.VERSION}"
    if not p.exists():
        s = f"{version}:no-file"                    # sections served some other way (the tests' fixtures)
    else:
        st = p.stat()
        s = f"{version}:{st.st_size}:{int(st.st_mtime)}"
    _STAMPS[key] = (time.time(), s)
    return s


def connect(state: str, corpus: str = CORPUS) -> sqlite3.Connection:
    con = sqlite3.connect(str(path(state, corpus)), timeout=60, check_same_thread=False)
    con.row_factory = sqlite3.Row
    return con


_READY: dict[tuple, bool] = {}


def ready(state: str, corpus: str = CORPUS) -> bool:
    """True when the state's index exists and matches its statute file (remembered until either file changes)."""
    try:
        mtime = path(state, corpus).stat().st_mtime         # the index lives on the Docker volume: a cheap stat
    except OSError:
        return False
    stamp = _stamp(state, corpus)
    if stamp.endswith(":no-file") and not _source(corpus).have(state):
        return False
    key = (state, mtime, stamp)                 # stamps differ between corpora, so the key needs no corpus
    if key not in _READY:
        _READY[key] = _check(state, corpus)
    return _READY[key]


def _check(state: str, corpus: str = CORPUS) -> bool:
    try:
        con = connect(state, corpus)
        try:
            row = con.execute("SELECT value FROM meta WHERE key='stamp'").fetchone()
        finally:
            con.close()
        return bool(row) and row[0] == _stamp(state, corpus)
    except sqlite3.Error:
        return False


_LOCKS: dict[str, threading.Lock] = {}


@contextlib.contextmanager
def _exclusive(state: str, corpus: str = CORPUS):
    """One build of a state at a time: a lock for this process's threads, and flock for other processes."""
    index_dir().mkdir(parents=True, exist_ok=True)
    with _LOCKS.setdefault(_key(state, corpus), threading.Lock()), \
            open(index_dir() / f"{corpus}_{state}.lock", "a") as f:
        try:
            import fcntl
        except ImportError:                         # Windows: threads only
            fcntl = None
        if fcntl:
            fcntl.flock(f, fcntl.LOCK_EX)           # released when the file closes
            for old in index_dir().glob(f"{corpus}_{state}.building*"):
                old.unlink(missing_ok=True)         # left by a build that was killed
        yield


def _identity(state: str, corpus: str = CORPUS):
    try:
        st = path(state, corpus).stat()
        return st.st_ino, st.st_mtime_ns
    except OSError:
        return None


def _name(state: str, corpus: str) -> str:
    return state if corpus == CORPUS else f"{state} {corpus}"


def build(state: str, log: Log = print, corpus: str = CORPUS) -> dict:
    """(Re)build one state's index from its statute file; written to a temporary file and swapped in.  A build
    that had to wait for another build of the state keeps that one's index when it is current."""
    if not _source(corpus).have(state):
        raise FileNotFoundError(f"{corpus} for {state} are not downloaded")
    before = _identity(state, corpus)
    with _exclusive(state, corpus):
        _STAMPS.pop(_key(state, corpus), None)
        for k in list(_READY):
            if k[0] == state:
                _READY.pop(k, None)
        if _identity(state, corpus) != before and ready(state, corpus):
            con = connect(state, corpus)
            try:
                n = int(con.execute("SELECT value FROM meta WHERE key='sections'").fetchone()[0])
            finally:
                con.close()
            log(f"{_name(state, corpus)}: index built by another job")
            return {"state": state, "sections": n, "seconds": 0.0,
                    "mb": round(path(state, corpus).stat().st_size / 2**20, 1)}
        return _build(state, log, corpus)


def _build(state: str, log: Log, corpus: str = CORPUS) -> dict:
    t0 = time.time()
    _STAMPS.pop(_key(state, corpus), None)
    stamp = _stamp(state, corpus)       # taken before reading: a file replaced mid-build leaves the index stale
    src = _source(corpus)
    if hasattr(src.load, "cache_clear"):
        src.load.cache_clear()
    df = src.load(state)
    counts = df["norm_section"].value_counts().to_dict()
    # a corpus's own columns follow the statute ones (none for the statutes), and it may set each row's ref itself
    extra = () if corpus == CORPUS else tuple(getattr(src, "EXTRA", ()))
    if not all(re.fullmatch(r"[a-z_]+", c) for c in extra):
        raise ValueError(f"{corpus}: EXTRA must name plain columns, not {extra}")
    own_ref = corpus != CORPUS and "ref" in df.columns
    tmp = path(state, corpus).with_name(f"{corpus}_{state}.building.{os.getpid()}.{threading.get_ident()}")
    con = sqlite3.connect(str(tmp))
    con.executescript(f"""
        PRAGMA journal_mode=OFF; PRAGMA synchronous=OFF;
        CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE sec(id INTEGER PRIMARY KEY, ref TEXT, citation TEXT, title TEXT, chapter TEXT, path TEXT,
                         url TEXT, words INTEGER, head TEXT, section_number TEXT, norm_section TEXT, norm_cite TEXT,
                         act_id TEXT, original_title TEXT, effective_from TEXT, effective_until TEXT
                         {''.join(f', {c} TEXT' for c in extra)});
        CREATE TABLE body(id INTEGER PRIMARY KEY, text TEXT);
        CREATE VIRTUAL TABLE fts USING fts5(title, chapter, body, content='',
                                            tokenize='porter unicode61 remove_diacritics 2');
    """)
    secs, bodies, fts = [], [], []
    single = state in statutes.SINGLE_CODE

    def flush():
        con.executemany(f"INSERT INTO sec VALUES ({','.join('?' * (16 + len(extra)))})", secs)
        con.executemany("INSERT INTO body VALUES (?,?)", bodies)
        con.executemany("INSERT INTO fts(rowid, title, chapter, body) VALUES (?,?,?,?)", fts)
        secs.clear(), bodies.clear(), fts.clear()

    for i, r in enumerate(df.itertuples(index=False), 1):
        # the same reference statutes.ref_of() gives: the bare number where it is unique, else the citation
        ref = r.section_number if single or counts.get(r.norm_section, 0) == 1 else r.citation
        if own_ref and r.ref:
            ref = r.ref
        text = r.text or ""
        heading = _heading(r.section_title, r.citation, r.chapter_name, text)
        start, until = effective(r.section_title)
        secs.append((i, ref, r.citation, heading, r.chapter_name or "", r.display_path or "", r.source_url or "",
                     int(r.word_count or len(text.split())), text[:HEAD], r.section_number, r.norm_section,
                     statutes._norm_cite(r.citation), r.act_id, r.section_title or "", start, until,
                     *(getattr(r, c) for c in extra)))
        bodies.append((i, text))
        fts.append((i, heading, f"{r.chapter_name or ''} {r.display_path or ''}", text))
        if len(secs) >= 5000:
            flush()
    if secs:
        flush()
    con.execute("INSERT INTO fts(fts) VALUES('optimize')")
    con.execute("CREATE INDEX sec_ref ON sec(ref)")
    con.execute("CREATE INDEX sec_norm ON sec(norm_section)")
    con.execute("CREATE INDEX sec_cite ON sec(norm_cite)")
    for c in _cites(corpus):
        con.execute(f"CREATE INDEX sec_{c} ON sec({c})")
    meta = [("stamp", stamp), ("sections", str(len(df))), ("built", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))]
    con.executemany("INSERT INTO meta VALUES (?,?)", meta + ([] if corpus == CORPUS else [("corpus", corpus)]))
    con.commit()
    con.close()
    tmp.replace(path(state, corpus))
    mb = path(state, corpus).stat().st_size / 2**20
    log(f"{_name(state, corpus)}: indexed {len(df):,} sections in {time.time() - t0:.0f}s ({mb:.0f} MB)")
    return {"state": state, "sections": len(df), "seconds": round(time.time() - t0, 1), "mb": round(mb, 1)}


def ensure(state: str, log: Log = print, corpus: str = CORPUS) -> bool:
    """Build the index if it is missing or stale; False when the state has no statute file."""
    if not _source(corpus).have(state):
        return False
    if not ready(state, corpus):
        build(state, log=log, corpus=corpus)
    return True


def _cites(corpus: str) -> tuple[str, ...]:
    """A corpus's own normalised citation columns (indexed, and tried by lookup), such as a short citation."""
    if corpus == CORPUS:
        return ()
    cols = tuple(getattr(_source(corpus), "CITES", ()))
    if not all(re.fullmatch(r"norm_[a-z]+", c) for c in cols):
        raise ValueError(f"{corpus}: CITES must name norm_* columns, not {cols}")
    return cols


# ------------------------------------------------------------------ queries
def phrase(term: str) -> str | None:
    """One term as an FTS5 string: always quoted, so words like 'and' or 'near' are never operators."""
    words = re.findall(r"[A-Za-z0-9]+", term or "")
    return f'"{" ".join(words)}"' if words else None


def match(groups: list[list[str]], mode: str = "and", columns: str | None = None) -> str | None:
    """Concept groups -> an FTS5 MATCH expression: synonyms OR'ed within a group, groups AND'ed (or OR'ed)."""
    parts = []
    for g in groups:
        alts = [p for p in dict.fromkeys(phrase(t) for t in g) if p]
        if alts:
            parts.append("(" + " OR ".join(alts) + ")")
    if not parts:
        return None
    expr = (" AND " if mode == "and" else " OR ").join(parts)
    return f"{{{columns}}} : ({expr})" if columns else expr


def search(state: str, expr: str, limit: int = 50, corpus: str = CORPUS) -> list[dict]:
    """Sections matching an FTS5 expression, best BM25 first (score: higher is better)."""
    con = connect(state, corpus)
    try:
        rows = con.execute(f"""SELECT s.*, -bm25(fts, {WEIGHTS[0]}, {WEIGHTS[1]}, {WEIGHTS[2]}) AS score
                               FROM fts JOIN sec s ON s.id = fts.rowid WHERE fts MATCH ? ORDER BY bm25(fts,
                               {WEIGHTS[0]}, {WEIGHTS[1]}, {WEIGHTS[2]}) LIMIT ?""", (expr, limit)).fetchall()
        return [dict(r) for r in rows]
    except sqlite3.OperationalError:
        return []                                   # a malformed expression: no hits rather than an error
    finally:
        con.close()


def parent(row: dict) -> str:
    """The unit a section sits in (its path without the section: 'Virginia Code / Title 19.2 / Chapter 15'); most
    states leave ``chapter`` empty, but every path ends in the section."""
    parts = (row.get("path") or "").split(" / ")
    return " / ".join(parts[:-1]) if len(parts) > 1 else (row.get("chapter") or "")


def in_units(state: str, units: list[str], limit: int = 400, corpus: str = CORPUS) -> list[dict]:
    """Every section directly in the given units, in file order: each unit gets an equal share of ``limit``, and
    what a small unit leaves goes to the larger ones."""
    if not units:
        return []
    con = connect(state, corpus)
    try:
        esc = [u.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") for u in units]
        where = " OR ".join("(path LIKE ? ESCAPE '\\' AND path NOT LIKE ? ESCAPE '\\')" for _ in units)
        found: dict[str, list[dict]] = {u: [] for u in units}
        for r in map(dict, con.execute(f"SELECT * FROM sec WHERE {where} ORDER BY id",
                                       [a for e in esc for a in (e + " / %", e + " / % / %")])):
            got = found.get(parent(r))
            if got is not None and len(got) < limit:
                got.append(r)
    finally:
        con.close()
    out, left = [], limit
    for i, u in enumerate(sorted(found, key=lambda u: len(found[u]))):
        take = found[u][:left // (len(found) - i)]
        out += take
        left -= len(take)
    return sorted(out, key=lambda r: r["id"])


def neighbours(state: str, sec_id: int, span: int = 2, corpus: str = CORPUS) -> list[dict]:
    """The sections just before and after one section in the file (statutes put a procedure's parts together)."""
    con = connect(state, corpus)
    try:
        return [dict(r) for r in con.execute("SELECT * FROM sec WHERE id BETWEEN ? AND ? ORDER BY id",
                                             (sec_id - span, sec_id + span)).fetchall()]
    finally:
        con.close()


def by_ref(state: str, ref: str, corpus: str = CORPUS) -> dict | None:
    rows = lookup(state, ref, corpus=corpus)
    return rows[0] if rows else None


def lookup(state: str, ref: str, with_text: bool = False, corpus: str = CORPUS) -> list[dict]:
    """Rows for a section reference, by the rules of statutes.find(): the full citation first, then an article-
    qualified 'General Provisions § 4-203', then the bare number.  Rows carry the file's own columns; versions in
    force today come first, then those not yet in force, then expired ones.  A corpus with its own citation
    columns (``CITES``, such as the short '13VAC5-63-80') has them tried after the full citation."""
    import datetime as dt
    cites = _cites(corpus)
    con = connect(state, corpus)
    cols = ("s.*, b.text AS text" if with_text else "s.*")
    join = "JOIN body b ON b.id = s.id" if with_text else ""
    today = dt.date.today().isoformat()
    order = (" ORDER BY (s.effective_until IS NOT NULL AND s.effective_until <= ?),"
             " (s.effective_from IS NOT NULL AND s.effective_from > ?), s.id")
    try:
        q = f"SELECT {cols} FROM sec s {join} WHERE "
        rows = con.execute(q + "s.norm_cite=?" + order, (statutes._norm_cite(ref), today, today)).fetchall()
        for c in (() if rows else cites):
            rows = con.execute(q + f"s.{c}=?" + order, (statutes._norm_cite(ref), today, today)).fetchall()
            if rows:
                break
        if not rows and "§" in ref:
            article, number = (x.strip() for x in ref.rsplit("§", 1))
            rows = [r for r in con.execute(q + "s.norm_section=?" + order,
                                           (statutes.norm_section(number), today, today)).fetchall()
                    if article.lower() in (r["citation"] or "").lower()]
        elif not rows:
            rows = con.execute(q + "s.norm_section=?" + order, (statutes.norm_section(ref), today, today)).fetchall()
        return [dict(r) for r in rows]
    finally:
        con.close()


def by_id(state: str, sec_id: int, with_text: bool = False, corpus: str = CORPUS) -> dict | None:
    """One row of the index by its id: the exact version and section retrieval chose, where a reference can name
    several (an expired version, or two sections that share a citation)."""
    con = connect(state, corpus)
    try:
        r = con.execute("SELECT s.*, b.text AS text FROM sec s JOIN body b ON b.id = s.id WHERE s.id=?" if with_text
                        else "SELECT * FROM sec WHERE id=?", (sec_id,)).fetchone()
        return dict(r) if r else None
    finally:
        con.close()


def text_of(state: str, sec_id: int, corpus: str = CORPUS) -> str:
    con = connect(state, corpus)
    try:
        r = con.execute("SELECT text FROM body WHERE id=?", (sec_id,)).fetchone()
        return r[0] if r else ""
    finally:
        con.close()
