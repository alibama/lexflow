"""Full-text search over every downloaded statute section: SQLite FTS5, one index file per state.

Each index is built once (seconds for a small state, a minute or two for a large one) and rebuilt when the
statute file changes.  The index is contentless: the text stays in the parquet file, and a small table keeps
each section's reference, heading, path and opening words for display and reranking.

    data/index/statutes_<state>.sqlite
      sec(id, ref, citation, title, chapter, path, url, words, head)
      fts(title, chapter, body)          porter-stemmed, ranked with BM25 (heading weighted most)
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


def path(state: str):
    return index_dir() / f"statutes_{state}.sqlite"


_STAMPS: dict[str, tuple[float, str]] = {}


def _stamp(state: str) -> str:
    """The statute file's identity.  Remembered for a minute: the raw downloads sit on a bind mount from the host,
    where each stat costs tens of milliseconds, and the setup page checks every state."""
    hit = _STAMPS.get(state)
    if hit and time.time() - hit[0] < 60:
        return hit[1]
    p = statutes.path_for(state)
    if not p.exists():
        s = f"{VERSION}:no-file"                    # sections served some other way (the tests' fixtures)
    else:
        st = p.stat()
        s = f"{VERSION}:{st.st_size}:{int(st.st_mtime)}"
    _STAMPS[state] = (time.time(), s)
    return s


def connect(state: str) -> sqlite3.Connection:
    con = sqlite3.connect(str(path(state)), timeout=60, check_same_thread=False)
    con.row_factory = sqlite3.Row
    return con


_READY: dict[tuple, bool] = {}


def ready(state: str) -> bool:
    """True when the state's index exists and matches its statute file (remembered until either file changes)."""
    try:
        mtime = path(state).stat().st_mtime         # the index lives on the Docker volume: a cheap stat
    except OSError:
        return False
    stamp = _stamp(state)
    if stamp.endswith(":no-file") and not statutes.have(state):
        return False
    key = (state, mtime, stamp)
    if key not in _READY:
        _READY[key] = _check(state)
    return _READY[key]


def _check(state: str) -> bool:
    try:
        con = connect(state)
        try:
            row = con.execute("SELECT value FROM meta WHERE key='stamp'").fetchone()
        finally:
            con.close()
        return bool(row) and row[0] == _stamp(state)
    except sqlite3.Error:
        return False


_LOCKS: dict[str, threading.Lock] = {}


@contextlib.contextmanager
def _exclusive(state: str):
    """One build of a state at a time: a lock for this process's threads, and flock for other processes."""
    index_dir().mkdir(parents=True, exist_ok=True)
    with _LOCKS.setdefault(state, threading.Lock()), open(index_dir() / f"statutes_{state}.lock", "a") as f:
        try:
            import fcntl
        except ImportError:                         # Windows: threads only
            fcntl = None
        if fcntl:
            fcntl.flock(f, fcntl.LOCK_EX)           # released when the file closes
            for old in index_dir().glob(f"statutes_{state}.building*"):
                old.unlink(missing_ok=True)         # left by a build that was killed
        yield


def _identity(state: str):
    try:
        st = path(state).stat()
        return st.st_ino, st.st_mtime_ns
    except OSError:
        return None


def build(state: str, log: Log = print) -> dict:
    """(Re)build one state's index from its statute file; written to a temporary file and swapped in.  A build
    that had to wait for another build of the state keeps that one's index when it is current."""
    if not statutes.have(state):
        raise FileNotFoundError(f"statutes for {state} are not downloaded")
    before = _identity(state)
    with _exclusive(state):
        _STAMPS.pop(state, None)
        for k in list(_READY):
            if k[0] == state:
                _READY.pop(k, None)
        if _identity(state) != before and ready(state):
            con = connect(state)
            try:
                n = int(con.execute("SELECT value FROM meta WHERE key='sections'").fetchone()[0])
            finally:
                con.close()
            log(f"{state}: index built by another job")
            return {"state": state, "sections": n, "seconds": 0.0,
                    "mb": round(path(state).stat().st_size / 2**20, 1)}
        return _build(state, log)


def _build(state: str, log: Log) -> dict:
    t0 = time.time()
    _STAMPS.pop(state, None)
    stamp = _stamp(state)               # taken before reading: a file replaced mid-build leaves the index stale
    if hasattr(statutes.load, "cache_clear"):
        statutes.load.cache_clear()
    df = statutes.load(state)
    counts = df["norm_section"].value_counts().to_dict()
    tmp = path(state).with_name(f"statutes_{state}.building.{os.getpid()}.{threading.get_ident()}")
    con = sqlite3.connect(str(tmp))
    con.executescript("""
        PRAGMA journal_mode=OFF; PRAGMA synchronous=OFF;
        CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE sec(id INTEGER PRIMARY KEY, ref TEXT, citation TEXT, title TEXT, chapter TEXT, path TEXT,
                         url TEXT, words INTEGER, head TEXT, section_number TEXT, norm_section TEXT, norm_cite TEXT,
                         act_id TEXT, original_title TEXT, effective_from TEXT, effective_until TEXT);
        CREATE TABLE body(id INTEGER PRIMARY KEY, text TEXT);
        CREATE VIRTUAL TABLE fts USING fts5(title, chapter, body, content='',
                                            tokenize='porter unicode61 remove_diacritics 2');
    """)
    secs, bodies, fts = [], [], []
    single = state in statutes.SINGLE_CODE

    def flush():
        con.executemany(f"INSERT INTO sec VALUES ({','.join('?' * 16)})", secs)
        con.executemany("INSERT INTO body VALUES (?,?)", bodies)
        con.executemany("INSERT INTO fts(rowid, title, chapter, body) VALUES (?,?,?,?)", fts)
        secs.clear(), bodies.clear(), fts.clear()

    for i, r in enumerate(df.itertuples(index=False), 1):
        # the same reference statutes.ref_of() gives: the bare number where it is unique, else the citation
        ref = r.section_number if single or counts.get(r.norm_section, 0) == 1 else r.citation
        text = r.text or ""
        heading = _heading(r.section_title, r.citation, r.chapter_name, text)
        start, until = effective(r.section_title)
        secs.append((i, ref, r.citation, heading, r.chapter_name or "", r.display_path or "", r.source_url or "",
                     int(r.word_count or len(text.split())), text[:HEAD], r.section_number, r.norm_section,
                     statutes._norm_cite(r.citation), r.act_id, r.section_title or "", start, until))
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
    con.executemany("INSERT INTO meta VALUES (?,?)", [("stamp", stamp), ("sections", str(len(df))),
                                                      ("built", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))])
    con.commit()
    con.close()
    tmp.replace(path(state))
    mb = path(state).stat().st_size / 2**20
    log(f"{state}: indexed {len(df):,} sections in {time.time() - t0:.0f}s ({mb:.0f} MB)")
    return {"state": state, "sections": len(df), "seconds": round(time.time() - t0, 1), "mb": round(mb, 1)}


def ensure(state: str, log: Log = print) -> bool:
    """Build the index if it is missing or stale; False when the state has no statute file."""
    if not statutes.have(state):
        return False
    if not ready(state):
        build(state, log=log)
    return True


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


def search(state: str, expr: str, limit: int = 50) -> list[dict]:
    """Sections matching an FTS5 expression, best BM25 first (score: higher is better)."""
    con = connect(state)
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


def in_units(state: str, units: list[str], limit: int = 400) -> list[dict]:
    """Every section directly in the given units, in file order: each unit gets an equal share of ``limit``, and
    what a small unit leaves goes to the larger ones."""
    if not units:
        return []
    con = connect(state)
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


def neighbours(state: str, sec_id: int, span: int = 2) -> list[dict]:
    """The sections just before and after one section in the file (statutes put a procedure's parts together)."""
    con = connect(state)
    try:
        return [dict(r) for r in con.execute("SELECT * FROM sec WHERE id BETWEEN ? AND ? ORDER BY id",
                                             (sec_id - span, sec_id + span)).fetchall()]
    finally:
        con.close()


def by_ref(state: str, ref: str) -> dict | None:
    rows = lookup(state, ref)
    return rows[0] if rows else None


def lookup(state: str, ref: str, with_text: bool = False) -> list[dict]:
    """Rows for a section reference, by the rules of statutes.find(): the full citation first, then an article-
    qualified 'General Provisions § 4-203', then the bare number.  Rows carry the file's own columns; versions in
    force today come first, then those not yet in force, then expired ones."""
    import datetime as dt
    con = connect(state)
    cols = ("s.*, b.text AS text" if with_text else "s.*")
    join = "JOIN body b ON b.id = s.id" if with_text else ""
    today = dt.date.today().isoformat()
    order = (" ORDER BY (s.effective_until IS NOT NULL AND s.effective_until <= ?),"
             " (s.effective_from IS NOT NULL AND s.effective_from > ?), s.id")
    try:
        q = f"SELECT {cols} FROM sec s {join} WHERE "
        rows = con.execute(q + "s.norm_cite=?" + order, (statutes._norm_cite(ref), today, today)).fetchall()
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


def by_id(state: str, sec_id: int, with_text: bool = False) -> dict | None:
    """One row of the index by its id: the exact version and section retrieval chose, where a reference can name
    several (an expired version, or two sections that share a citation)."""
    con = connect(state)
    try:
        r = con.execute("SELECT s.*, b.text AS text FROM sec s JOIN body b ON b.id = s.id WHERE s.id=?" if with_text
                        else "SELECT * FROM sec WHERE id=?", (sec_id,)).fetchone()
        return dict(r) if r else None
    finally:
        con.close()


def text_of(state: str, sec_id: int) -> str:
    con = connect(state)
    try:
        r = con.execute("SELECT text FROM body WHERE id=?", (sec_id,)).fetchone()
        return r[0] if r else ""
    finally:
        con.close()
