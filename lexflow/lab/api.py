"""The process lab's API, as a FastAPI ``APIRouter`` that is not mounted yet (docs/design/lab-plan.md says how).

What reaches the server, and what it keeps:

* ``GET /models``, ``/models/{id}/steps``, ``/calendars/{key}``: the state and process the user chose.
* ``GET /states/{state}/places``: every government of one state with the office channels in the store that pass
  ``lexflow.privacy``'s checks, so the page can search places and show where to send things without sending the
  place.  The path carries only the state.  There is no place search and no per-place lookup on the server any
  more: both sent the place (and each keystroke of the search) to the server, where the access log recorded it.
* ``POST /timeline``: a case's event types, dates and step ids (no notes, label or place), used to count its
  deadlines and then dropped.  Nothing is stored; uvicorn's access log records the request line, not the body.
* ``POST /outcomes``: the one write, opt-in.  It accepts exactly six fields (state, place, question, step, days
  taken, outcome category), refuses any other field and any query-string parameter, and refuses a cross-site
  request.  The report is kept in ``lab_outcomes``, a ``WITHOUT ROWID`` table keyed by a random 128-bit value: there
  is no rowid, the table's order is the random key's order rather than arrival order, and no date (not even a
  coarse one), time or sender detail is stored.  Reports leave the table only as the aggregates of
  ``GET /outcomes/summary``, where no group of fewer than ``K_MIN`` reports is shown or can be worked out from the
  others.  Two limits remain and are stated, not hidden: the web server's access log records the
  time and client address of each ``POST /outcomes`` (the row cannot be matched to a log line by its position, but
  the log itself should be off or short-lived on any shared host), and until SQLite checkpoints its write-ahead
  log, the log's page images still reflect the order of recent writes.  There is no authentication; a global rate
  limit (no per-client record) caps reports.
"""
from __future__ import annotations

import datetime as dt
import secrets
import sqlite3
import threading
import time
from collections import deque
from statistics import median
from typing import Annotated, Literal
from urllib.parse import urlsplit

from fastapi import APIRouter, HTTPException, Path, Query, Request
from pydantic import BaseModel, ConfigDict, Field

from .. import privacy
from ..store import db
from . import deadlines as D
from . import instances as I

router = APIRouter(prefix="/api/lab", tags=["lab"])

Outcome = Literal["answered_in_time", "answered_late", "extension_notice", "denied", "no_answer", "estimate_tolled",
                  "withdrawn", "still_open"]
K_MIN = 10          # a summary cell, and an outcome count inside it, needs this many reports (lab-research.md §4.2)
RATE = (30, 60.0)   # at most 30 shared outcomes a minute, from everyone together; nothing about a client is kept
FIELDS = ("state", "place", "question", "step", "days_taken", "outcome")
OUTCOME_TABLE = """CREATE TABLE IF NOT EXISTS lab_outcomes (
  k TEXT PRIMARY KEY,
  state TEXT NOT NULL,
  place TEXT,
  question TEXT NOT NULL,
  step TEXT NOT NULL,
  days_taken INTEGER NOT NULL,
  outcome TEXT NOT NULL
) WITHOUT ROWID"""


def _con():
    return db.connect()


# ------------------------------------------------------------------------- request bodies
Key = Annotated[str, Field(pattern=r"^[a-z0-9_]{1,40}$")]


class LabEvent(BaseModel):
    model_config = ConfigDict(extra="ignore")         # a note on an event is the user's own and is dropped here
    type: str = Field(max_length=40)
    date: dt.date
    step: str | None = Field(default=None, max_length=80)
    until: dt.date | None = None


class LabOptions(BaseModel):
    """Per-case calendar choices: days the office was closed, optional holidays observed, holidays it was open (by
    holiday key) and a variant reading."""
    model_config = ConfigDict(extra="ignore")
    closures: list[dt.date] = Field(default_factory=list, max_length=200)
    observes: list[Key] = Field(default_factory=list, max_length=20)
    opens: list[Key] = Field(default_factory=list, max_length=60)
    variant: Key | None = None


class LabInstance(BaseModel):
    model_config = ConfigDict(extra="ignore")         # a place or label sent by another client is dropped too
    state: str = Field(pattern=r"^[A-Za-z]{2}$")
    question: str = Field(pattern=r"^[a-z_]{1,40}$")
    model_id: str | None = Field(default=None, pattern=r"^[a-z]{2}\.[a-z_]{1,40}$")
    started: dt.date | None = None
    events: list[LabEvent] = Field(default_factory=list, max_length=300)
    options: LabOptions = Field(default_factory=LabOptions)


class OutcomeIn(BaseModel):
    """An anonymised outcome: these six fields and nothing else (any other field is a 422)."""
    model_config = ConfigDict(extra="forbid")
    state: str = Field(pattern=r"^[a-z]{2}$")
    place: str | None = Field(default=None, pattern=r"^[0-9A-Za-z:._-]{1,64}$")
    question: str = Field(pattern=r"^[a-z_]{1,40}$")
    step: str = Field(pattern=r"^[A-Za-z0-9_]{1,80}$")
    days_taken: int = Field(ge=0, le=3660)
    outcome: Outcome


# ------------------------------------------------------------------------- models and calendars
@router.get("/models")
def models(state: str | None = Query(None, pattern=r"^[A-Za-z]{2}$")):
    """Models a case can start from (built ones in the store, then curated ones), with their calendar."""
    c = _con()
    try:
        return I.list_models(c, state.lower() if state else None)
    finally:
        c.close()


@router.get("/models/{model_id}/steps")
def model_steps(model_id: str):
    """A model's steps in BPMN order, each deadline with its rule, section and quote, for starting a case."""
    c = _con()
    try:
        m = I.load_model(model_id, c)
    finally:
        c.close()
    if m is None:
        raise HTTPException(404, f"no model {model_id}")
    return I.model_steps(m)


@router.get("/calendars/{key}")
def calendar(key: str, year: int | None = Query(None, ge=1990, le=2100)):
    """A holiday table with its sources, and its dates for one year (this year by default)."""
    if key.lower() not in D.CALENDARS:
        raise HTTPException(404, f"no calendar {key}; there are {sorted(D.CALENDARS)}")
    return D.describe_calendar(key.lower(), year or dt.date.today().year)


# ------------------------------------------------------------------------- timeline
@router.post("/timeline")
def timeline(instance: LabInstance, today: dt.date | None = None):
    """The current step, every deadline (how it was counted, its section and quote) and on time / overdue.
    Nothing posted here is stored."""
    c = _con()
    try:
        return I.timeline(instance.model_dump(mode="json"), today=today, con=c)
    except LookupError as e:
        raise HTTPException(404, str(e)) from e
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    finally:
        c.close()


# ------------------------------------------------------------------------- one state's places and office channels
PLACE_COLUMNS = ("gov_id", "name", "kind", "county_name", "population", "website")
PLACES_NOTE = ("Every government of the state with the office channels in this lexflow's store that pass its "
               "office-only checks: websites, records pages, office addresses and labelled office lines. An office "
               "mailbox is shown only once a check has found it on the office's own page. Search and choose in the "
               "browser; the place you choose is not sent. Use the government's own website for anything else.")
MAILBOX_FRESH_DAYS = 90     # entities-contacts.md §2.2: an "ok" older than this is treated as unverifiable


def _found_mailboxes(c, state: str) -> set[tuple[str, str, str]]:
    """(owner, question, lower-cased address) of the mailboxes a check found on the office's own page within the
    last ``MAILBOX_FRESH_DAYS`` days: ``contact_status`` rows with status ``ok`` and method ``page-contains``
    (entities-contacts.md §5.2 rule 5, §2.1-2.2).  Empty while that table does not exist (as now), so every
    mailbox stays hidden until the contact checks land."""
    since = (dt.date.today() - dt.timedelta(days=MAILBOX_FRESH_DAYS)).isoformat()
    try:
        if not c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='contact_status'").fetchone():
            return set()
        rows = c.execute("SELECT owner, question, norm_value FROM contact_status WHERE state=? AND kind='email' "
                         "AND status='ok' AND method='page-contains' AND verified_at >= ?", (state, since))
        return {(r[0], r[1], (r[2] or "").strip().lower()) for r in rows}
    except sqlite3.Error:                   # a different or unfinished schema: show none
        return set()


@router.get("/states/{state}/places")
def state_places(state: str = Path(pattern=r"^[A-Za-z]{2}$")):
    """All governments of one state (largest first) and their office channels, in one response, so the page looks
    up a place without sending it.  What is left out or cut (``lexflow.privacy``):

    * a website or page link that ``is_office_url`` refuses (a scheme other than http or https, an e-mail address or
      ``~``, also percent-encoded, a staff, people or directory page);
    * an e-mail address that is not role-shaped by the whole-token rule, and every role-shaped one that a check has
      not found on the office's own page in the last 90 days (§5.2 rule 5; with no check state yet, all of them);
    * a phone without an office label, and a phone whose value has anything beside the number but office or line
      words (``office_phone_value``: "434-555-0100 Jane Doe" is left out whole);
    * every piece of an office value that the checks cannot account for (``office_value``: a staff name before or
      after a room number, P.O. box or phone number included); a street's name and the city before a state and ZIP
      code are kept unchecked, as that function says;
    * a label that is not office or page vocabulary (``office_label``: the row is then shown under its kind), and a
      source that is not a writer's tag or an accepted link (``office_source``).

    A website row that repeats the government's own website is left out."""
    st = state.lower()
    c = _con()
    try:
        govs = db.rows(c, "SELECT gov_id, name, kind, county_name, population, website FROM governments "
                          "WHERE state=? ORDER BY population IS NULL, population DESC, name", st)
        rows = db.rows(c, "SELECT gov_id, question, kind, value, label, source FROM contacts WHERE state=? "
                          "AND kind IN ('website','page','office','email','phone') "
                          "ORDER BY gov_id, question DESC, kind, value", st)
        found = _found_mailboxes(c, st)
    finally:
        c.close()
    for g in govs:
        if g.get("website") and not privacy.is_office_url(g["website"]):
            g["website"] = None
    by_id = {g["gov_id"]: g for g in govs}
    channels: dict[str, list[dict]] = {}
    for r in rows:
        g = by_id.get(r["gov_id"])
        if g is None:
            continue
        if r["kind"] == "website" and r["value"] == g.get("website"):
            continue
        if not privacy.is_office_channel(r["kind"], r["value"], r["label"], g["name"]):
            continue
        if r["kind"] == "email" and (r["gov_id"], r["question"], (r["value"] or "").strip().lower()) not in found:
            continue
        value = (privacy.office_value(r["value"], g["name"]) if r["kind"] == "office"
                 else privacy.office_phone_value(r["value"], g["name"]) if r["kind"] == "phone" else r["value"])
        channels.setdefault(r["gov_id"], []).append({
            "question": r["question"], "kind": r["kind"], "value": value,
            "label": privacy.office_label(r["label"], g["name"]), "source": privacy.office_source(r["source"])})
    return {"state": st, "columns": list(PLACE_COLUMNS),
            "governments": [[g[k] for k in PLACE_COLUMNS] for g in govs], "channels": channels, "note": PLACES_NOTE}


# ------------------------------------------------------------------------- opt-in outcomes
_recent: deque[float] = deque()
_rate_lock = threading.Lock()


def _rate_ok() -> bool:
    """A global sliding window: no client address or other per-sender record is kept."""
    n, window = RATE
    now = time.monotonic()
    with _rate_lock:
        while _recent and now - _recent[0] > window:
            _recent.popleft()
        if len(_recent) >= n:
            return False
        _recent.append(now)
        return True


def _same_origin(request: Request) -> bool:
    """Refuse a report sent from another site's page (a browser says so in ``Sec-Fetch-Site`` or ``Origin``)."""
    site = request.headers.get("sec-fetch-site")
    if site and site not in ("same-origin", "none"):
        return False
    origin = request.headers.get("origin")
    if origin is None:
        return True
    return origin != "null" and urlsplit(origin).netloc == request.headers.get("host")


def _table_sql(c, name: str = "lab_outcomes") -> str | None:
    r = c.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone()
    return r[0] if r else None


ORPHAN = "lab_outcomes_rowid"       # left behind by an interrupted run of the first, non-atomic migration
INSERT = f"INSERT INTO lab_outcomes (k, {', '.join(FIELDS)}) VALUES (?,?,?,?,?,?,?)"


def _ensure(c) -> None:
    """Create ``lab_outcomes``, or rebuild a table from the first prototype (which had an implicit, sequential rowid)
    under random keys.  It must run inside the caller's transaction (``share_outcome`` opens ``BEGIN IMMEDIATE``):
    SQLite's DDL is transactional, so the drop, the create and the copy commit together or not at all, and a second
    first report waits for the lock and then finds the table rebuilt.  Rows of a ``lab_outcomes_rowid`` table left
    by an interrupted run of the earlier migration (which renamed the table before copying it) are moved in the
    same way.  The caller turns on SQLite's secure delete, so the dropped pages are overwritten."""
    sql, orphan = _table_sql(c), _table_sql(c, ORPHAN) is not None
    current = sql is not None and "WITHOUT ROWID" in sql.upper()
    if current and not orphan:
        return
    cols = ", ".join(FIELDS)
    old = [tuple(r) for r in c.execute(f"SELECT {cols} FROM {ORPHAN}")] if orphan else []
    if sql is not None and not current:
        old += [tuple(r) for r in c.execute(f"SELECT {cols} FROM lab_outcomes")]
        c.execute("DROP TABLE lab_outcomes")
    c.execute(OUTCOME_TABLE)
    c.executemany(INSERT, [(secrets.token_hex(16), *r) for r in old])
    if orphan:
        c.execute(f"DROP TABLE {ORPHAN}")


@router.post("/outcomes", status_code=201)
def share_outcome(o: OutcomeIn, request: Request):
    """Store one anonymised outcome the user chose to share, under a random key.  No date, time, order or sender
    detail is kept, and the row is never returned on its own."""
    if request.query_params:
        raise HTTPException(422, "no query-string parameters are accepted here")
    if not _same_origin(request):
        raise HTTPException(403, "outcomes are accepted only from this lexflow's own page")
    c = _con()
    try:
        m = I.load_model(f"{o.state}.{o.question}", c)
        if m is None:
            raise HTTPException(422, f"no model {o.state}.{o.question}")
        if not m.step(o.step):
            raise HTTPException(422, f"{o.step!r} is not a step of {m.model_id}")
        if o.place is not None:
            g = db.one(c, "SELECT state FROM governments WHERE gov_id=?", o.place)
            if not g or g["state"] != o.state:
                raise HTTPException(422, "place must be a government id in the same state, or left out")
        if not _rate_ok():
            raise HTTPException(429, "too many shared outcomes in the last minute; try again later")
        if c.in_transaction:
            c.commit()
        c.execute("PRAGMA secure_delete=ON")
        c.execute("BEGIN IMMEDIATE")            # the table's creation or rebuild and the report: all or nothing
        try:
            _ensure(c)
            c.execute(INSERT, (secrets.token_hex(16), o.state, o.place, o.question, o.step, o.days_taken, o.outcome))
            c.commit()
        except BaseException:
            c.rollback()
            raise
    finally:
        c.close()
    return {"stored": o.model_dump(), "kept": "only these six fields, under a random key; no date, time, order or "
                                              "sender detail"}


@router.get("/outcomes/summary")
def outcome_summary(state: str | None = Query(None, pattern=r"^[a-z]{2}$"),
                    question: str | None = Query(None, pattern=r"^[a-z_]{1,40}$")):
    """Shared outcomes by state, question and step, only where a cell has at least ``K_MIN`` reports.  Inside a
    cell an outcome is named only when ``K_MIN`` reports share it; the rest are pooled as ``other`` without naming
    them.  A pool of fewer than ``K_MIN`` would still show that so few reports differ (ten "answered in time" and
    an ``other`` of 1), so the smallest named outcome is moved into the pool until the pool is empty or holds at
    least ``K_MIN``: every count shown, and every count that follows from ``n`` and the others, is 0 or at least
    ``K_MIN``.  Places are never broken out.  This only reads: it does not create the table."""
    c = _con()
    try:
        if _table_sql(c) is None:
            rows = []
        else:
            where, args = [], []
            if state:
                where.append("state=?")
                args.append(state)
            if question:
                where.append("question=?")
                args.append(question)
            rows = db.rows(c, "SELECT state, question, step, outcome, days_taken FROM lab_outcomes"
                              + (" WHERE " + " AND ".join(where) if where else ""), *args)
    finally:
        c.close()
    cells: dict[tuple, list[dict]] = {}
    for r in rows:
        cells.setdefault((r["state"], r["question"], r["step"]), []).append(r)
    out = []
    for (st, qu, step), rs in sorted(cells.items()):
        if len(rs) < K_MIN:
            continue
        counts: dict[str, int] = {}
        for r in rs:
            counts[r["outcome"]] = counts.get(r["outcome"], 0) + 1
        shown = {k: n for k, n in counts.items() if n >= K_MIN}
        other = len(rs) - sum(shown.values())
        while 0 < other < K_MIN and shown:      # complementary suppression: no pool smaller than k
            other += shown.pop(min(shown, key=lambda k: (shown[k], k)))
        cell = {"state": st, "question": qu, "step": step, "n": len(rs), "outcomes": dict(sorted(shown.items())),
                "median_days": median(r["days_taken"] for r in rs)}
        if other:
            cell["other"] = other
        out.append(cell)
    return {"k": K_MIN, "cells": out, "label": "self-reported; not a sample; days in the model's own units; an "
                                               "outcome shared by fewer than k reports is pooled as 'other', and "
                                               "more outcomes join the pool until it holds at least k"}
