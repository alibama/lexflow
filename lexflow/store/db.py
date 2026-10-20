"""The local store: one SQLite file (WAL mode) that every step reads and writes.

Tables listed in ``SYNCED`` carry ``updated_at``, ``origin`` and ``state`` columns, so they can
be shared through Turso (see :mod:`lexflow.store.turso`): rows are upserted last-writer-wins on
``updated_at`` and can be pulled one state at a time.  Push and pull take only these tables and
refuse any other (``turso.check_tables``).  The reviewer list (``reviewers``) and the review log
(``review_log``) are this copy's own and are never synced: a page names only reviewers the
operator of this copy put on its list, and only for a review this copy recorded in its own
``review_log`` or a sign-off in this copy's own curated file (lexflow/reviewers.py).
"""
from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .. import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS governments (
  gov_id TEXT PRIMARY KEY,
  state TEXT NOT NULL,
  name TEXT NOT NULL,
  kind TEXT NOT NULL,
  county_fips TEXT,
  county_name TEXT,
  place_fips TEXT,
  population INTEGER,
  website TEXT,
  address TEXT,
  wikidata TEXT,
  source TEXT,
  updated_at TEXT NOT NULL,
  origin TEXT
);
CREATE INDEX IF NOT EXISTS governments_state ON governments(state);
CREATE INDEX IF NOT EXISTS governments_county ON governments(county_fips);

CREATE TABLE IF NOT EXISTS contacts (
  gov_id TEXT NOT NULL,
  state TEXT NOT NULL,
  question TEXT NOT NULL,
  kind TEXT NOT NULL,
  value TEXT NOT NULL,
  label TEXT,
  source TEXT,
  updated_at TEXT NOT NULL,
  origin TEXT,
  PRIMARY KEY (gov_id, question, kind, value)
);
CREATE INDEX IF NOT EXISTS contacts_state ON contacts(state);

CREATE TABLE IF NOT EXISTS located_law (
  state TEXT NOT NULL,
  question TEXT NOT NULL,
  status TEXT NOT NULL,
  citation TEXT,
  section TEXT,
  heading TEXT,
  act TEXT,
  url TEXT,
  method TEXT,
  score REAL,
  text TEXT,
  related TEXT,
  candidates TEXT,
  dataset_version TEXT,
  updated_at TEXT NOT NULL,
  origin TEXT,
  PRIMARY KEY (state, question)
);

CREATE TABLE IF NOT EXISTS process_models (
  model_id TEXT PRIMARY KEY,
  state TEXT NOT NULL,
  question TEXT NOT NULL,
  scope TEXT NOT NULL DEFAULT 'state',
  title TEXT,
  tier TEXT NOT NULL,
  built_by TEXT,
  stages TEXT NOT NULL,
  completion REAL,
  quality REAL,
  metrics TEXT,
  facts TEXT,
  bpmn TEXT,
  dmn TEXT,
  svg TEXT,
  citation TEXT,
  source_url TEXT,
  updated_at TEXT NOT NULL,
  origin TEXT
);
CREATE INDEX IF NOT EXISTS process_models_state ON process_models(state);

CREATE TABLE IF NOT EXISTS extractions (
  model_id TEXT NOT NULL,
  llm TEXT NOT NULL,
  state TEXT NOT NULL,
  ok INTEGER,
  rounds INTEGER,
  problems TEXT,
  facts TEXT,
  seconds REAL,
  prompt_hash TEXT,
  updated_at TEXT NOT NULL,
  origin TEXT,
  PRIMARY KEY (model_id, llm)
);

CREATE TABLE IF NOT EXISTS local_law (
  gov_id TEXT NOT NULL,
  state TEXT NOT NULL,
  question TEXT NOT NULL,
  source TEXT NOT NULL,
  ref TEXT NOT NULL,
  header TEXT,
  function TEXT,
  topic TEXT,
  score REAL,
  updated_at TEXT NOT NULL,
  origin TEXT,
  PRIMARY KEY (gov_id, question, source, ref)
);
CREATE INDEX IF NOT EXISTS local_law_state ON local_law(state);

CREATE TABLE IF NOT EXISTS answers (
  gov_id TEXT NOT NULL,
  state TEXT NOT NULL,
  question TEXT NOT NULL,
  county_fips TEXT,
  confidence REAL NOT NULL,
  state_score REAL,
  local_score REAL,
  contact_score REAL,
  tier TEXT,
  built_by TEXT,
  contact_level TEXT,
  model_id TEXT,
  summary TEXT,
  updated_at TEXT NOT NULL,
  origin TEXT,
  PRIMARY KEY (gov_id, question)
);
CREATE INDEX IF NOT EXISTS answers_state ON answers(state, question);
CREATE INDEX IF NOT EXISTS answers_county ON answers(county_fips, question);

-- one researched process of one place (curated/places/<state>/<place>/<process>.json): the whole checked file in
-- spec, with the fields that pages and searches need beside it
CREATE TABLE IF NOT EXISTS place_processes (
  gov_id TEXT NOT NULL,
  state TEXT NOT NULL,
  process TEXT NOT NULL,
  title TEXT,
  question TEXT,
  category TEXT,
  kind TEXT,
  office TEXT,
  verified INTEGER,
  spec TEXT,
  updated_at TEXT NOT NULL,
  origin TEXT,
  PRIMARY KEY (gov_id, process)
);

CREATE TABLE IF NOT EXISTS local_answers (
  gov_id TEXT NOT NULL,
  state TEXT NOT NULL,
  question TEXT NOT NULL,
  summary TEXT,
  steps TEXT,
  contacts TEXT,
  local_law TEXT,
  fees TEXT,
  caveats TEXT,
  sources TEXT,
  built_by TEXT,
  verified INTEGER,
  researched TEXT,
  updated_at TEXT NOT NULL,
  origin TEXT,
  reviewed_by TEXT,
  PRIMARY KEY (gov_id, question)
);

-- the people the operator of this copy vouches for as reviewers (lexflow reviewer add / list / remove / token,
-- lexflow/reviewers.py, lexflow/signoff.py): a page names a reviewer only from this list, by the id a review
-- records.  It is this copy's own and is never synced.  A removed reviewer keeps the row, with removed_at.
-- token_hash is the scrypt hash of the reviewer's own token (the token itself is printed once and not stored).
CREATE TABLE IF NOT EXISTS reviewers (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  role TEXT NOT NULL,
  licensed_in TEXT,
  added_by TEXT NOT NULL,
  added_at TEXT NOT NULL,
  removed_at TEXT,
  updated_at TEXT NOT NULL,
  origin TEXT,
  token_hash TEXT
);

-- who recorded or removed a review through the API, by the reviewer whose token was used (never synced).  A page
-- names the reviewer of an asked answer only while the last entry here for that answer is the review its
-- reviewed_by holds (same reviewer, text_hash and date): a review pulled from another copy has no entry here.
CREATE TABLE IF NOT EXISTS review_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  at TEXT NOT NULL,
  action TEXT NOT NULL,
  question_id TEXT NOT NULL,
  target TEXT NOT NULL,
  reviewer TEXT NOT NULL,
  text_hash TEXT
);

CREATE TABLE IF NOT EXISTS case_law (
  state TEXT NOT NULL,
  section TEXT NOT NULL,
  question TEXT,
  cluster_id TEXT NOT NULL,
  case_name TEXT,
  court TEXT,
  court_id TEXT,
  date_filed TEXT,
  citation TEXT,
  cite_count INTEGER,
  url TEXT,
  source TEXT,
  updated_at TEXT NOT NULL,
  origin TEXT,
  PRIMARY KEY (state, section, cluster_id)
);

CREATE TABLE IF NOT EXISTS asked_questions (
  id TEXT PRIMARY KEY,
  text TEXT NOT NULL,
  kind TEXT,
  terms TEXT,
  created_at TEXT,
  updated_at TEXT NOT NULL,
  origin TEXT
);

CREATE TABLE IF NOT EXISTS asked_answers (
  question_id TEXT NOT NULL,
  target TEXT NOT NULL,
  state TEXT NOT NULL,
  gov_id TEXT,
  question_text TEXT,
  status TEXT,
  sections TEXT,
  facts TEXT,
  bpmn TEXT,
  answer TEXT,
  local TEXT,
  metrics TEXT,
  model TEXT,
  seconds REAL,
  published INTEGER DEFAULT 0,
  updated_at TEXT NOT NULL,
  origin TEXT,
  reviewed_by TEXT,
  PRIMARY KEY (question_id, target)
);
CREATE INDEX IF NOT EXISTS asked_answers_state ON asked_answers(state);

CREATE TABLE IF NOT EXISTS ask_bench (
  case_id TEXT NOT NULL,
  arm TEXT NOT NULL,
  metrics TEXT,
  ref_hash TEXT,
  created_at TEXT,
  PRIMARY KEY (case_id, arm)
);

CREATE TABLE IF NOT EXISTS wikibase_items (
  key TEXT PRIMARY KEY,
  qid TEXT,
  label TEXT,
  updated_at TEXT
);

CREATE TABLE IF NOT EXISTS wikibase_props (
  label TEXT PRIMARY KEY,
  pid TEXT,
  datatype TEXT,
  updated_at TEXT
);

CREATE TABLE IF NOT EXISTS statute_files (
  state TEXT PRIMARY KEY,
  file TEXT,
  url TEXT,
  bytes INTEGER,
  sha256 TEXT,
  version TEXT,
  sections INTEGER,
  status TEXT,
  downloaded_at TEXT
);

CREATE TABLE IF NOT EXISTS crawl_log (
  gov_id TEXT PRIMARY KEY,
  state TEXT NOT NULL,
  url TEXT,
  status TEXT,
  found TEXT,
  checked_at TEXT
);
CREATE INDEX IF NOT EXISTS crawl_log_state ON crawl_log(state);

CREATE TABLE IF NOT EXISTS scans (
  source TEXT NOT NULL,
  state TEXT NOT NULL,
  rows INTEGER,
  matched INTEGER,
  status TEXT,
  scanned_at TEXT,
  PRIMARY KEY (source, state)
);

CREATE TABLE IF NOT EXISTS benchmarks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  "case" TEXT NOT NULL,
  strategy TEXT NOT NULL,
  model TEXT NOT NULL,
  gold_hash TEXT,
  equivalence REAL,
  raw_equivalence REAL,
  lexical REAL,
  step_f1 REAL,
  actors REAL,
  deadlines REAL,
  modality REAL,
  step_recall REAL,
  step_precision REAL,
  quote_validity REAL,
  steps INTEGER,
  gold_steps INTEGER,
  valid INTEGER,
  seconds REAL,
  calls INTEGER,
  notes TEXT,
  problems TEXT,
  facts TEXT,
  created_at TEXT
);

CREATE TABLE IF NOT EXISTS jobs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  step TEXT NOT NULL,
  args TEXT,
  status TEXT NOT NULL,
  progress REAL DEFAULT 0,
  message TEXT,
  pid INTEGER,
  created_at TEXT NOT NULL,
  started_at TEXT,
  finished_at TEXT
);

CREATE TABLE IF NOT EXISTS settings (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL,
  updated_at TEXT
);

CREATE TABLE IF NOT EXISTS sync_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  direction TEXT NOT NULL,
  tables TEXT,
  states TEXT,
  rows INTEGER,
  ok INTEGER,
  message TEXT,
  started_at TEXT,
  finished_at TEXT
);

CREATE TABLE IF NOT EXISTS sync_marks (
  table_name TEXT NOT NULL,
  direction TEXT NOT NULL,
  scope TEXT NOT NULL,
  last_at TEXT,
  PRIMARY KEY (table_name, direction, scope)
);

CREATE TABLE IF NOT EXISTS meta (
  key TEXT PRIMARY KEY,
  value TEXT
);

-- lexflow.law.ontology: one row per section of a state's statute index (structure, norm types, ELI id).  Local,
-- never synced: derived from this copy's index files and rebuilt here (1.7 million rows for 47 states).
CREATE TABLE IF NOT EXISTS section_tags (
  state TEXT NOT NULL,
  ref TEXT NOT NULL,
  act_id TEXT,
  structure TEXT,
  norm_types TEXT,
  method TEXT,
  model TEXT,
  confidence TEXT,
  updated_at TEXT,
  origin TEXT,
  PRIMARY KEY (state, ref)
);
CREATE INDEX IF NOT EXISTS section_tags_state_method ON section_tags(state, method);
INSERT OR IGNORE INTO meta(key, value) VALUES ('version', '0');
"""

# Shared tables: primary key columns.  Every one has updated_at, origin and a state.  Push and pull take only these
# (turso.check_tables refuses any other table).  The reviewer list is not one of them: it is the operator's own
# (LOCAL_KEYS), so a pull never adds, renames or removes a reviewer here.
SYNCED: dict[str, tuple[str, ...]] = {
    "governments": ("gov_id",),
    "contacts": ("gov_id", "question", "kind", "value"),
    "located_law": ("state", "question"),
    "process_models": ("model_id",),
    "extractions": ("model_id", "llm"),
    "local_law": ("gov_id", "question", "source", "ref"),
    "answers": ("gov_id", "question"),
    "local_answers": ("gov_id", "question"),
    "place_processes": ("gov_id", "process"),
    "case_law": ("state", "section", "cluster_id"),
    "asked_answers": ("question_id", "target"),     # carries its question's text, so asked_questions stays local
}
# this copy's own tables that upsert() writes: primary key columns (never synced)
LOCAL_KEYS: dict[str, tuple[str, ...]] = {"reviewers": ("id",), "section_tags": ("state", "ref")}

# columns added after a table first shipped (ALTER TABLE is a no-op error when the column exists).  Those on shared
# tables are also applied to the shared database (turso.ensure_schema).  reviewed_by is a person's sign-off, JSON
# {reviewer, date, attested, text_hash} (lexflow/signoff.py: the reviewer is an id on the reviewers list), the hash
# being that of the row's text when it was signed: an asked answer goes on the wiki only with one that still fits
# its text.  quote_check is lexflow's software match of a researched process's quotes from the state code
# (lexflow/municipal/places.py), with the hash of the file it was made for.
MIGRATIONS = ["ALTER TABLE benchmarks ADD COLUMN lexical REAL", "ALTER TABLE jobs ADD COLUMN runner TEXT",
              "ALTER TABLE asked_answers ADD COLUMN reviewed_by TEXT",
              "ALTER TABLE local_answers ADD COLUMN reviewed_by TEXT",
              "ALTER TABLE place_processes ADD COLUMN quote_check TEXT",
              "ALTER TABLE reviewers ADD COLUMN token_hash TEXT",
              # the compute node(s) that ran a benchmark row (lexflow/compute; this copy's own)
              "ALTER TABLE benchmarks ADD COLUMN node TEXT",
              # the digest of what lexflow.publish.push last wrote for the key (this copy's own; never synced)
              "ALTER TABLE wikibase_items ADD COLUMN content_hash TEXT"]

_ready: set[str] = set()
_lock = threading.Lock()


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def connect(path: Path | str | None = None) -> sqlite3.Connection:
    path = Path(path or config.DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(path), timeout=60, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=NORMAL")
    con.execute("PRAGMA busy_timeout=60000")
    key = str(path.resolve())
    if key not in _ready:
        with _lock:
            con.executescript(SCHEMA)
            for m in MIGRATIONS:
                try:
                    con.execute(m)
                except sqlite3.OperationalError:
                    pass
            _ready.add(key)
    return con


@contextmanager
def session(path: Path | str | None = None):
    con = connect(path)
    try:
        yield con
        con.commit()
    finally:
        con.close()


def columns(con: sqlite3.Connection, table: str) -> list[str]:
    return [r[1] for r in con.execute(f"PRAGMA table_info({table})")]


def upsert(con: sqlite3.Connection, table: str, rows: Iterable[dict], keys: tuple[str, ...] | None = None,
           *, stamp: bool = True, newer_only: bool = False) -> int:
    """Insert or update rows.  ``newer_only`` keeps the stored row when it is newer (sync)."""
    rows = list(rows)
    if not rows:
        return 0
    keys = keys or SYNCED.get(table) or LOCAL_KEYS[table]
    cols = columns(con, table)
    ts, origin = now(), config.ORIGIN
    prepared = []
    for r in rows:
        r = dict(r)
        if stamp:
            if "updated_at" in cols:
                r["updated_at"] = r.get("updated_at") or ts
            if "origin" in cols:
                r["origin"] = r.get("origin") or origin
        for k, v in list(r.items()):
            if isinstance(v, (dict, list)):
                r[k] = json.dumps(v, ensure_ascii=False)
        prepared.append(r)
    use = [c for c in cols if c in prepared[0]]
    update = [c for c in use if c not in keys]
    sql = (f"INSERT INTO {table} ({', '.join(use)}) VALUES ({', '.join('?' for _ in use)}) "
           f"ON CONFLICT ({', '.join(keys)}) DO ")
    if update:
        sql += "UPDATE SET " + ", ".join(f"{c}=excluded.{c}" for c in update)
        if newer_only and "updated_at" in cols:
            sql += f" WHERE excluded.updated_at >= {table}.updated_at"
    else:
        sql += "NOTHING"
    con.executemany(sql, [tuple(r.get(c) for c in use) for r in prepared])
    return len(prepared)


def bump(con: sqlite3.Connection) -> None:
    """Tell the dashboard that something it shows has changed."""
    con.execute("UPDATE meta SET value = CAST(value AS INTEGER) + 1 WHERE key = 'version'")


def version(con: sqlite3.Connection) -> int:
    row = con.execute("SELECT value FROM meta WHERE key='version'").fetchone()
    return int(row[0]) if row else 0


def rows(con: sqlite3.Connection, sql: str, *args: Any) -> list[dict]:
    return [dict(r) for r in con.execute(sql, args)]


def one(con: sqlite3.Connection, sql: str, *args: Any) -> dict | None:
    r = con.execute(sql, args).fetchone()
    return dict(r) if r else None


def scalar(con: sqlite3.Connection, sql: str, *args: Any, default: Any = None) -> Any:
    r = con.execute(sql, args).fetchone()
    return r[0] if r and r[0] is not None else default


def loads(value: str | None, default: Any = None) -> Any:
    if value in (None, ""):
        return default
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return default
