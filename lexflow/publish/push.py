"""Write lexflow's graph to lexipedia.wikibase.cloud through the API (``wbeditentity``), in two passes.

``graph.build(con)`` gives items whose claims name properties by label and other items by key; this module
resolves those to ``P`` and ``Q`` ids and executes them with the ``Wikibase`` client of
``wikibase_lexipedia`` (login, csrf token, retries and back-off on ``maxlag`` / ``ratelimited``).  Every write
sends ``maxlag=5`` and is followed by a half-second pause (``--pause``); ``bot=1`` is sent only with ``--bot`` (the
account has no bot right today; docs/design/wikidata-laws.md §7 says what granting it takes).

**Pass 1, entities.**  New properties (``schema.PROPERTIES`` not on the wiki; label -> P recorded in the local
table ``wikibase_props``), then class and vocabulary items, then every other new item, each with its labels,
descriptions, aliases and ``P25 legal identifier`` only (plus ``P5 instance of`` when the class item's id is
already known).  Find-before-create: ``wikibase_items`` (key -> Q) first, then a one-time paged SPARQL map of
every ``P25`` value on the live endpoint, then the API's "already has label" answer, whose item is reused only
when its ``P25`` equals the key (as the old loader's ``owner`` did); otherwise the key's tail is appended to the
description and the create is retried once.  Items that already exist are left to pass 2.

**Pass 2, claims.**  Every item gets its full statement set (qualifiers and references; item, string, url,
time, quantity, monolingual and external-id values; a fee's unit is the entity IRI of the ``US dollar`` vocab
item).  An item lexflow owns (its key starts with ``lexflow:``, except the class items the wiki held before
lexflow and the jurisdictions) is written with ``clear=1`` so a re-run replaces instead of appending; the other
items (the existing class items Q7-Q23, the jurisdictions, the CourtListener clusters, the property items) are
read first and only the statements they lack are appended.  A successful pass-2 write stores the item's
``content_hash`` in ``wikibase_items``, so ``--resume`` skips what is already up to date.

``--dry-run`` (the default; ``--really`` turns it off) performs no POST at all: it reads the live wiki (SPARQL
and ``wbgetentities``, one request a second), gives new entities placeholder ids (``P900+``, ``Q900000+``), prints
the counts per pass by kind with creates against updates and the first request bodies per kind, and writes the
full plan to ``out/wikibase/push-plan.json`` (bodies in ``push-plan.bodies.jsonl``).

``--really`` refuses to run while ``out/wikibase/lint-report.json`` is missing or lists HELD items, unless
``--allow-held`` is given; HELD items are never pushed in any case (``lexflow wikibase lint`` writes the report).
Writes are serialised; a failure on one entity is logged and the run goes on; the summary lists failures by API
error code.  ``--check`` after a real run compares ``sparql/coverage.rq`` on the live endpoint with the plan.

**Single pass** (``--single-pass``).  A new item whose referenced items all have ids when its turn comes is
created with its whole statement set in pass 1 (``wbeditentity`` with ``new=item`` takes claims as well as labels),
its content hash is recorded, and pass 2 skips it: one write instead of two.  Items wait for what they name (Kahn's
order over the kind order); a cycle is broken by creating its first item bare, which pass 2 completes.  The
result on the wiki is the same as two passes; only the number of writes changes.

    lexflow wikibase push [--dry-run|--really] [--pass 1|2|all] [--limit N] [--kinds a,b] [--states va,dc]
                          [--places gid,...] [--no-drafts] [--resume] [--single-pass] [--pause S] [--bot]
                          [--allow-held] [--check] [--no-live]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import sys
import time
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .. import config
from ..store import db
from . import graph
from . import ids as I
from . import schema as SC
from .wikibase_lexipedia import Wikibase, WikibaseError

OUT_DIR = config.ROOT / "out" / "wikibase"
PLAN_NAME = "push-plan.json"
BODIES_NAME = "push-plan.bodies.jsonl"
LINT_NAME = "lint-report.json"
SITE = config.WIKIBASE_URL.rstrip("/")
ENTITY = SITE + "/entity/"
SPARQL = SITE + "/query/sparql"
USER_AGENT = I.USER_AGENT
LANG = "en"
KEY_PROP = "legal identifier"           # P25
MAXLAG = 5
PAUSE = 0.5                             # seconds between writes
GREGORIAN = "http://www.wikidata.org/entity/Q1985727"
LABEL_MAX, STRING_MAX, URL_MAX = SC.LABEL_MAX, SC.STRING_MAX, 500
DATATYPES = {"item": "wikibase-item", "string": "string", "url": "url", "external-id": "external-id",
             "time": "time", "quantity": "quantity", "monolingualtext": "monolingualtext",
             "monolingual": "monolingualtext"}
# the order kinds are written in: what others point at comes first
KIND_ORDER = ["class", "vocab", "jurisdiction", "source", "code", "unit", "statute", "regulation", "gov", "agency",
              "office-type", "position", "position-type", "private-party", "power", "role", "process",
              "decision", "outcome", "step", "rung", "form", "cluster"]
EXAMPLES_PER_KIND = 3
EXAMPLE_CHARS = 1500

Log = Callable[[str], None]

TABLES = """
CREATE TABLE IF NOT EXISTS wikibase_props (
  label TEXT PRIMARY KEY,
  pid TEXT,
  datatype TEXT,
  updated_at TEXT
);
"""


class PushError(RuntimeError):
    pass


class Unresolved(KeyError):
    """A key or label that has no id yet."""


class HeldError(PushError):
    """The lint report holds items (or is missing) and ``--allow-held`` was not given."""


# --------------------------------------------------------------------------- local tables


def ensure_tables(con: sqlite3.Connection) -> None:
    """``wikibase_props`` and the ``content_hash`` column of ``wikibase_items``; both are this copy's own (never
    synced)."""
    con.executescript(TABLES)
    try:
        con.execute("ALTER TABLE wikibase_items ADD COLUMN content_hash TEXT")
    except sqlite3.OperationalError:
        pass
    con.commit()


def content_hash(it: graph.Item) -> str:
    """A stable digest of everything the writer would send for an item."""
    payload = {"label": it.label, "description": it.description, "aliases": sorted(it.aliases), "cls": it.cls,
               "claims": [[c.prop, list(c.value.sig()), [[q, list(v.sig())] for q, v in c.qualifiers],
                           [[[q, list(v.sig())] for q, v in r] for r in c.references]] for c in it.claims]}
    # other languages only when the item has them, so an English-only item keeps the digest it was pushed with
    for k in ("labels", "descriptions", "lang_aliases"):
        if getattr(it, k, None):
            payload[k] = getattr(it, k)
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:32]


def owned(key: str) -> bool:
    """Whether lexflow owns the item (its statements are replaced wholesale): every ``lexflow:`` key except the
    class items the wiki held before lexflow (Q7-Q23) and the jurisdictions."""
    if not key.startswith("lexflow:"):
        return False
    kind = SC.kind_of(key)
    if kind == "jurisdiction":
        return False
    if kind == "class":
        c = SC.CLASS_BY_SLUG.get(key.split(":", 2)[-1])
        return not (c and c.qid)
    return True


# --------------------------------------------------------------------------- values -> snaks


def time_value(value: str, precision: int) -> dict:
    m = re.fullmatch(r"([+-]?)(\d{4})-(\d{2})-(\d{2})", (value or "").strip())
    if not m:
        raise ValueError(f"not a date: {value!r}")
    sign = "-" if m.group(1) == "-" else "+"
    y, mo, d = int(m.group(2)), int(m.group(3)), int(m.group(4))
    p = int(precision or 11)
    if p < 11:
        d = 0
    if p < 10:
        mo = 0
    return {"time": f"{sign}{y:04d}-{mo:02d}-{d:02d}T00:00:00Z", "timezone": 0, "before": 0, "after": 0,
            "precision": p, "calendarmodel": GREGORIAN}


def quantity_amount(value: str) -> str:
    s = str(value).strip().replace(",", "")
    if not re.fullmatch(r"[+-]?\d+(\.\d+)?", s):
        raise ValueError(f"not a quantity: {value!r}")
    return s if s[0] in "+-" else "+" + s


def snak(pid: str, v: graph.Value, qid_of: Callable[[str], str]) -> dict:
    """One Wikibase snak from a graph value; ``qid_of`` resolves an item key (raises ``Unresolved``)."""
    kind = v.kind
    if kind == "item":
        q = qid_of(v.value)
        dv = {"type": "wikibase-entityid", "value": {"entity-type": "item", "numeric-id": int(q[1:]), "id": q}}
    elif kind in ("string", "external-id"):
        dv = {"type": "string", "value": str(v.value)[:STRING_MAX]}
    elif kind == "url":
        dv = {"type": "string", "value": str(v.value)[:URL_MAX]}
    elif kind == "time":
        dv = {"type": "time", "value": time_value(v.value, v.precision)}
    elif kind == "quantity":
        unit = ENTITY + qid_of(v.unit) if v.unit else "1"
        dv = {"type": "quantity", "value": {"amount": quantity_amount(v.value), "unit": unit}}
    elif kind in ("monolingual", "monolingualtext"):
        dv = {"type": "monolingualtext", "value": {"text": str(v.value)[:STRING_MAX], "language": v.lang or LANG}}
    else:
        raise ValueError(f"unknown value kind {kind!r}")
    return {"snaktype": "value", "property": pid, "datavalue": dv}


def statement(c: graph.Claim, pid_of: Callable[[str], str], qid_of: Callable[[str], str],
              dropped: list[str] | None = None) -> dict:
    """One statement with its qualifiers and references.  A qualifier or reference snak whose item has no id is
    dropped (and listed in ``dropped``); a main value without one raises ``Unresolved``."""
    st = {"mainsnak": snak(pid_of(c.prop), c.value, qid_of), "type": "statement", "rank": "normal"}
    if c.qualifiers:
        quals: dict[str, list] = {}
        order: list[str] = []
        for q, v in c.qualifiers:
            try:
                pid = pid_of(q)
                s = snak(pid, v, qid_of)
            except Unresolved as e:
                if dropped is not None:
                    dropped.append(f"{c.prop} qualifier {q}: {e}")
                continue
            quals.setdefault(pid, []).append(s)
            if pid not in order:
                order.append(pid)
        if quals:
            st["qualifiers"], st["qualifiers-order"] = quals, order
    if c.references:
        refs = []
        for r in c.references:
            snaks: dict[str, list] = {}
            order = []
            for q, v in r:
                try:
                    pid = pid_of(q)
                    s = snak(pid, v, qid_of)
                except Unresolved as e:
                    if dropped is not None:
                        dropped.append(f"{c.prop} reference {q}: {e}")
                    continue
                snaks.setdefault(pid, []).append(s)
                if pid not in order:
                    order.append(pid)
            if snaks:
                refs.append({"snaks": snaks, "snaks-order": order})
        if refs:
            st["references"] = refs
    return st


def equivalent_claims(label: str, wikidata: str | None) -> list[graph.Claim]:
    """The ``P7 equivalent property`` claims of a property item: the Wikidata property first, then one per
    ontology IRI of ``schema.equivalents_of`` (docs/design/legal-ontologies.md section 2)."""
    out = []
    if wikidata:
        out.append(graph.Claim("equivalent property", graph.url(SC.WIKIDATA_ENTITY + wikidata)))
    out += [graph.Claim("equivalent property", graph.url(iri)) for iri in SC.equivalents_of(label)]
    return out


def snak_sig(s: dict) -> tuple:
    """What makes two main snaks the same statement for the append-only diff."""
    dv = s.get("datavalue") or {}
    t, v = dv.get("type"), dv.get("value")
    if t == "wikibase-entityid":
        return (s.get("property"), "entity", (v or {}).get("id"))
    if t == "time":
        return (s.get("property"), "time", (v or {}).get("time"), (v or {}).get("precision"))
    if t == "quantity":
        amount = str((v or {}).get("amount", ""))
        try:
            amount = f"{float(amount):g}"
        except ValueError:
            pass
        return (s.get("property"), "quantity", amount, (v or {}).get("unit"))
    if t == "monolingualtext":
        return (s.get("property"), "mono", (v or {}).get("text"), (v or {}).get("language"))
    return (s.get("property"), "string", v if isinstance(v, str) else json.dumps(v, sort_keys=True))


def labels_body(it: graph.Item, *, add_aliases: bool = False) -> dict:
    """Labels, descriptions and aliases in English and in every other language the item carries (``ja``)."""
    body: dict[str, Any] = {"labels": {}}
    if it.label:                            # a law without an official English title has its own language's only
        body["labels"][LANG] = {"language": LANG, "value": it.label[:LABEL_MAX]}
    if it.description:
        body["descriptions"] = {LANG: {"language": LANG, "value": it.description[:LABEL_MAX]}}
    if it.aliases:
        body["aliases"] = {LANG: [dict({"language": LANG, "value": a[:LABEL_MAX]}, **({"add": ""} if add_aliases
                                                                                     else {}))
                                  for a in it.aliases]}
    for lg, v in sorted((getattr(it, "labels", None) or {}).items()):
        if lg != LANG and v:
            body["labels"][lg] = {"language": lg, "value": v[:LABEL_MAX]}
    for lg, v in sorted((getattr(it, "descriptions", None) or {}).items()):
        if lg != LANG and v:
            body.setdefault("descriptions", {})[lg] = {"language": lg, "value": v[:LABEL_MAX]}
    for lg, vs in sorted((getattr(it, "lang_aliases", None) or {}).items()):
        if lg != LANG and vs:
            body.setdefault("aliases", {})[lg] = [dict({"language": lg, "value": a[:LABEL_MAX]},
                                                       **({"add": ""} if add_aliases else {})) for a in vs]
    return body


# --------------------------------------------------------------------------- the API client


class Api(Wikibase):
    """``Wikibase`` with ``maxlag``, a pause after every write and, unless ``bot`` is set (``--bot``: the account is
    in the wiki's bot group and its bot password has the high-volume grant), no ``bot`` flag."""

    def __post_init__(self):
        super().__post_init__()
        self.session.headers["User-Agent"] = USER_AGENT
        self.pause = PAUSE
        self.bot = False
        self.relogins = 0
        self.log = None                     # run() hands its log here, for the sign-ins after a lapsed session

    attempts = 8                            # a multi-hour run must outlast a rate-limit window or a lagging replica

    def post(self, **params):
        """The base client's POST (token, JSON, error folding) with ``maxlag`` and ``assert=user``, longer back-off
        on ``ratelimited`` / ``maxlag``, a fresh sign-in when the session lapses, retries on a dropped connection,
        and the pause.

        A session lapses on a long run (the 2026-10-23 Japan push lost it after 90 minutes): the wiki answers
        ``badtoken``, and a token fetched then is an anonymous one, so every later write was refused
        (``permissiondenied``).  ``assert=user`` makes such a write fail as ``assertuserfailed`` instead of ever
        being taken as an anonymous edit, and either code signs in again (twice at most per write)."""
        import requests
        last: Exception | None = None
        signed_in = 0
        for attempt in range(self.attempts):
            try:
                data = super().post(maxlag=MAXLAG, **({"assert": "user"} if self.user else {}), **params)
            except WikibaseError as e:
                code = error_code(e)
                if code in ("ratelimited", "maxlag", "readonly") or str(e) == "rate limited":
                    last = e
                    time.sleep(15 * (attempt + 1))
                    continue
                if code in ("badtoken", "assertuserfailed", "assertnameduserfailed") and self.user and signed_in < 2:
                    signed_in += 1
                    self.relogins += 1
                    if self.log:
                        self.log(f"the session lapsed ({code}): signing in again")
                    self.login()
                    last = e
                    continue
                raise
            except (requests.ConnectionError, requests.Timeout) as e:
                last = e
                time.sleep(15 * (attempt + 1))
                continue
            if self.pause:
                time.sleep(self.pause)
            return data
        raise WikibaseError(f"{params.get('action')}: gave up after {self.attempts} attempts: {last}")

    def edit(self, data: dict, *, qid: str | None = None, new: str | None = None, clear: bool = False,
             summary: str = "lexflow") -> dict:
        params = {"action": "wbeditentity", "data": json.dumps(data, ensure_ascii=False), "summary": summary}
        if qid:
            params["id"] = qid
            if clear:
                params["clear"] = 1
        else:
            params["new"] = new or "item"
        if getattr(self, "bot", False):
            params["bot"] = 1
        res = self.post(**params)
        self.writes += 1
        return res


def error_code(e: Exception) -> str:
    """The API error code the ``Wikibase`` client folded into its message (``wbeditentity: <code>: <info>``)."""
    parts = str(e).split(": ", 2)
    return parts[1] if len(parts) >= 2 and re.fullmatch(r"[a-z0-9_-]+", parts[1]) else "error"


def owner_of(error: str) -> str | None:
    """The item an "already has label" message names."""
    if "already has label" not in error:
        return None
    m = re.search(r"\bQ\d+\b", error.split("already has label")[0])
    return m.group(0) if m else None


# --------------------------------------------------------------------------- ids


class Resolver:
    """Key -> Q and label -> P: the local tables, then the live wiki (one paged SPARQL map of every ``P25`` and
    the property labels), then placeholders for what a dry run would create."""

    def __init__(self, con: sqlite3.Connection | None = None):
        self.qids: dict[str, str] = {}
        self.pids: dict[str, str] = dict(SC.EXISTING)
        self.pdatatypes: dict[str, str] = {}
        self.class_labels: dict[str, str] = {c.label: c.qid for c in SC.CLASSES if c.qid}
        for c in SC.CLASSES:
            if c.qid:
                self.qids[SC.key_for("class", c.slug)] = c.qid
        self.placeholders: set[str] = set()
        self.source: dict[str, str] = {}
        self.live_keys: dict[str, str] = {}
        self._next_q = I.Q_BASE
        self._next_p = I.P_BASE
        if con is not None:
            self.load_local(con)

    # --- sources
    def load_local(self, con: sqlite3.Connection) -> None:
        for r in db.rows(con, "SELECT key, qid FROM wikibase_items WHERE qid IS NOT NULL"):
            if r["qid"] and re.fullmatch(r"Q\d+", r["qid"]):
                self.qids.setdefault(r["key"], r["qid"])
                self.source.setdefault(r["key"], "wikibase_items")
        try:
            for r in db.rows(con, "SELECT label, pid, datatype FROM wikibase_props"):
                if r["pid"]:
                    self.pids.setdefault(r["label"], r["pid"])
                    self.pdatatypes[r["label"]] = r["datatype"]
        except sqlite3.OperationalError:
            pass

    def load_live(self, session, log: Log = print) -> None:
        """The live ``P25`` map (paged, one request a second) and the property labels of namespace 122."""
        offset, page = 0, 5000
        while True:
            I.throttle()
            q = (f"PREFIX lxt: <{SITE}/prop/direct/>\nSELECT ?item ?key WHERE {{ ?item lxt:{SC.EXISTING[KEY_PROP]} "
                 f"?key }} LIMIT {page} OFFSET {offset}")
            r = session.get(SPARQL, params={"query": q}, headers={"Accept": "application/sparql-results+json"},
                            timeout=120)
            r.raise_for_status()
            rows = r.json().get("results", {}).get("bindings", [])
            for b in rows:
                qid = b["item"]["value"].rsplit("/", 1)[-1]
                self.live_keys.setdefault(b["key"]["value"], qid)
            if len(rows) < page:
                break
            offset += page
        for key, qid in self.live_keys.items():
            if key not in self.qids:
                self.qids[key] = qid
                self.source[key] = "sparql"
        log(f"live: {len(self.live_keys)} keys on the wiki")
        I.throttle()
        r = session.get(SITE + "/w/api.php", params={"action": "query", "list": "allpages", "apnamespace": 122,
                                                     "aplimit": 500, "format": "json"}, timeout=60)
        r.raise_for_status()
        pids = [p["title"].split(":")[-1] for p in r.json().get("query", {}).get("allpages", [])]
        for i in range(0, len(pids), 50):
            I.throttle()
            r = session.get(SITE + "/w/api.php", params={"action": "wbgetentities", "ids": "|".join(pids[i:i + 50]),
                                                         "props": "labels|datatype", "languages": LANG,
                                                         "format": "json"}, timeout=60)
            r.raise_for_status()
            for pid, e in r.json().get("entities", {}).items():
                lab = (e.get("labels", {}).get(LANG) or {}).get("value")
                if lab and lab not in self.pids:
                    self.pids[lab] = pid
                    self.pdatatypes[lab] = e.get("datatype") or ""
        log(f"live: {len(pids)} properties on the wiki")

    # --- lookups
    def qid(self, ref: str) -> str:
        if ref in self.class_labels:
            return self.class_labels[ref]
        if re.fullmatch(r"Q\d+", ref or ""):
            return ref
        q = self.qids.get(ref)
        if not q:
            raise Unresolved(f"item {ref!r} has no id")
        return q

    def pid(self, label: str) -> str:
        if re.fullmatch(r"P\d+", label or ""):
            return label
        p = self.pids.get(label)
        if not p:
            raise Unresolved(f"property {label!r} has no id")
        return p

    def has(self, ref: str) -> bool:
        try:
            self.qid(ref)
            return True
        except Unresolved:
            return False

    def placeholder_q(self, key: str) -> str:
        used = {int(v[1:]) for v in self.qids.values()}
        while self._next_q in used:
            self._next_q += 1
        q = f"Q{self._next_q}"
        self._next_q += 1
        self.qids[key] = q
        self.placeholders.add(key)
        self.source[key] = "placeholder"
        return q

    def placeholder_p(self, label: str) -> str:
        used = {int(v[1:]) for v in self.pids.values()}
        while self._next_p in used:
            self._next_p += 1
        p = f"P{self._next_p}"
        self._next_p += 1
        self.pids[label] = p
        self.placeholders.add(label)
        return p


# --------------------------------------------------------------------------- the plan


@dataclass
class Write:
    pass_no: int
    kind: str
    key: str
    action: str                       # create | update | clear | skip-exists | skip-held | skip-resume |
    #                                   skip-current | skip-unresolved | fail
    qid: str | None = None
    new: str | None = None            # "item" or "property" on a create
    clear: bool = False
    body: dict | None = None
    note: str = ""
    error: str | None = None
    code: str | None = None
    placeholder: bool = False
    full: bool = False                # single pass: the create carried every statement (pass 2 skips the item)

    def row(self) -> dict:
        d = {"pass": self.pass_no, "kind": self.kind, "key": self.key, "action": self.action, "qid": self.qid,
             "new": self.new, "clear": self.clear, "note": self.note, "error": self.error, "code": self.code,
             "placeholder": self.placeholder}
        if self.full:
            d["full"] = True
        if self.body is not None:
            d["claims"] = len(self.body.get("claims") or [])
            d["bytes"] = len(json.dumps(self.body, ensure_ascii=False))
        return d


def example_text(body: dict | None, limit: int = EXAMPLE_CHARS) -> str:
    s = json.dumps(body, ensure_ascii=False, sort_keys=True)
    return s if len(s) <= limit else s[:limit] + f"… ({len(s)} chars)"


# --------------------------------------------------------------------------- lint gate


def read_lint(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
    except (OSError, ValueError):
        return None


def held_keys(report: dict | None) -> set[str]:
    return {h["key"] for h in (report or {}).get("held", []) if h.get("key")}


# --------------------------------------------------------------------------- the pusher


class Pusher:
    def __init__(self, con: sqlite3.Connection, items: list[graph.Item], *, api: Api | None = None,
                 dry_run: bool = True, resume: bool = False, held: set[str] | None = None, log: Log = print,
                 single_pass: bool = False):
        self.con, self.items, self.api, self.dry_run, self.resume, self.log = con, items, api, dry_run, resume, log
        self.held = set(held or ())
        self.single_pass = single_pass
        self.complete: set[str] = set()       # keys created with every statement in this run (pass 2 skips them)
        self.ids = Resolver(con)
        self.writes: list[Write] = []
        self.failures: Counter = Counter()
        self.dropped: list[str] = []
        self.by_key = {it.key: it for it in items}
        self.hashes: dict[str, str] = {}
        if con is not None:
            try:
                self.hashes = {r["key"]: r["content_hash"] for r in
                               db.rows(con, "SELECT key, content_hash FROM wikibase_items WHERE content_hash IS NOT NULL")}
            except sqlite3.OperationalError:
                pass
        self.live_entities: dict[str, dict] = {}
        self.session = api.session if api is not None else None

    # ---- helpers
    def record(self, w: Write) -> Write:
        self.writes.append(w)
        if w.action == "fail":
            self.failures[w.code or "error"] += 1
        return w

    def remember_item(self, key: str, qid: str, label: str, content: str | None = None) -> None:
        self.ids.qids[key] = qid
        if self.dry_run or self.con is None:
            return
        self.con.execute("INSERT INTO wikibase_items(key, qid, label, updated_at, content_hash) VALUES (?,?,?,?,?) "
                         "ON CONFLICT(key) DO UPDATE SET qid=excluded.qid, label=excluded.label, "
                         "updated_at=excluded.updated_at, content_hash=COALESCE(excluded.content_hash, "
                         "wikibase_items.content_hash)", (key, qid, label, db.now(), content))
        self.con.commit()

    def remember_prop(self, label: str, pid: str, datatype: str) -> None:
        self.ids.pids[label] = pid
        if self.dry_run or self.con is None:
            return
        self.con.execute("INSERT INTO wikibase_props(label, pid, datatype, updated_at) VALUES (?,?,?,?) "
                         "ON CONFLICT(label) DO UPDATE SET pid=excluded.pid, datatype=excluded.datatype, "
                         "updated_at=excluded.updated_at", (label, pid, datatype, db.now()))
        self.con.commit()

    def qid_of(self, ref: str) -> str:
        if ref in self.held:
            raise Unresolved(f"item {ref!r} is held by the lint report")
        return self.ids.qid(ref)

    def fetch_live(self, qids: list[str]) -> None:
        """``wbgetentities`` for the ids not fetched yet, 50 a request, through GET (reads only)."""
        todo = [q for q in dict.fromkeys(qids) if q not in self.live_entities and q]
        for i in range(0, len(todo), 50):
            I.throttle()
            r = self.session.get(SITE + "/w/api.php", params={
                "action": "wbgetentities", "ids": "|".join(todo[i:i + 50]), "props": "labels|descriptions|aliases|claims",
                "languages": LANG, "format": "json"}, timeout=120)
            r.raise_for_status()
            for q, e in r.json().get("entities", {}).items():
                self.live_entities[q] = {} if "missing" in e else e

    def live_key_of(self, qid: str) -> str | None:
        self.fetch_live([qid])
        ent = self.live_entities.get(qid) or {}
        for s in (ent.get("claims") or {}).get(SC.EXISTING[KEY_PROP], []):
            dv = (s.get("mainsnak") or {}).get("datavalue") or {}
            if dv.get("value"):
                return dv["value"]
        return None

    # ---- pass 1
    def pass1(self, props: bool = True) -> None:
        if props:
            self.create_properties()
        order = {k: i for i, k in enumerate(KIND_ORDER)}
        todo = sorted(self.items, key=lambda i: (order.get(SC.kind_of(i.key), 99), i.key))
        if self.single_pass:
            self._pass1_single(todo)
            return
        for it in todo:
            self.create_item(it)

    def pending_refs(self, it: graph.Item) -> set[str]:
        """The keys an item's full body names (class, values, qualifiers, references, quantity units) that are in
        this push and have no id yet: what a create with every statement must wait for.  A key that is not in the
        push (or is held) and has no id never gets one in this run, so it does not wait: its snak is dropped, as
        pass 2 would drop it.  An item that names itself waits on itself (it needs its own id: two writes)."""
        refs: set[str] = {it.cls} if it.cls else set()
        for c in it.claims:
            for v in [c.value, *(v for _, v in c.qualifiers), *(v for r in c.references for _, v in r)]:
                if v.kind == "item":
                    refs.add(v.value)
                if v.kind == "quantity" and v.unit:
                    refs.add(v.unit)
        return {r for r in refs if r in self.by_key and r not in self.held and (r == it.key or not self.ids.has(r))}

    def _pass1_single(self, todo: list[graph.Item]) -> None:
        """Single pass (``--single-pass``): every new item whose referenced items all have ids when its turn comes
        is created with its full statement set in one write, and pass 2 leaves it alone; the order is the kind
        order, except that an item waits until what it names exists (Kahn's order).  When every remaining item
        waits on another (a cycle: a law repealed by a law that repeals it), the first of them in kind order is
        created bare and completed by pass 2 as before, which frees the others.  Items that exist, are held or are
        resumed are recorded as in the two-pass mode."""
        import heapq
        new: list[graph.Item] = []
        for it in todo:
            if it.key in self.held or self.ids.has(it.key) or \
                    (self.resume and self.hashes.get(it.key) and self.hashes[it.key] == content_hash(it)):
                self.create_item(it)
            else:
                new.append(it)
        pos = {it.key: i for i, it in enumerate(new)}
        waiting = {it.key: self.pending_refs(it) for it in new}
        dependents: dict[str, set[str]] = {}
        for k, refs in waiting.items():
            for r in refs:
                dependents.setdefault(r, set()).add(k)
        ready = [(pos[k], k) for k, refs in waiting.items() if not refs]
        heapq.heapify(ready)
        done: set[str] = set()
        while len(done) < len(new):
            if ready:
                _, k = heapq.heappop(ready)
                if k in done:
                    continue
                self.create_item(self.by_key[k], full=True)
            else:
                # every remaining item waits on another: break the cycle at the item the most others wait for
                # (a greedy small feedback set: each bare create costs a second write in pass 2)
                k = min((x for x in pos if x not in done),
                        key=lambda x: (-sum(1 for d in dependents.get(x, ()) if d not in done), pos[x]))
                self.create_item(self.by_key[k], full=not waiting[k])
            done.add(k)
            # created, found or failed: either way nothing will wait on it longer (a failed create's snaks drop)
            for d in sorted(dependents.get(k, ())):
                if d in done:
                    continue
                waiting[d].discard(k)
                if not waiting[d]:
                    heapq.heappush(ready, (pos[d], d))

    def create_properties(self) -> None:
        for p in SC.PROPERTIES:
            if p.label in self.ids.pids:
                self.record(Write(1, "property", p.label, "skip-exists", qid=self.ids.pids[p.label]))
                continue
            body: dict[str, Any] = {"datatype": DATATYPES[p.datatype],
                                    "labels": {LANG: {"language": LANG, "value": p.label}},
                                    "descriptions": {LANG: {"language": LANG, "value": p.description[:LABEL_MAX]}}}
            claims = [statement(c, self.ids.pid, self.qid_of) for c in equivalent_claims(p.label, p.wikidata)]
            if claims:
                body["claims"] = claims
            w = Write(1, "property", p.label, "create", new="property", body=body)
            if self.dry_run:
                w.qid, w.placeholder = self.ids.placeholder_p(p.label), True
                self.record(w)
                continue
            try:
                res = self.api.edit(body, new="property", summary=f"lexflow: property {p.label}")
                w.qid = res["entity"]["id"]
                self.remember_prop(p.label, w.qid, p.datatype)
            except (WikibaseError, KeyError, ValueError) as e:
                w.action, w.error, w.code = "fail", str(e)[:300], error_code(e)
                self.log(f"property {p.label}: {e}")
            self.record(w)

    def create_body(self, it: graph.Item) -> dict:
        body = labels_body(it)
        claims = [statement(graph.Claim(KEY_PROP, graph.ext(it.key)), self.ids.pid, self.qid_of)]
        if it.cls:
            try:
                claims.append(statement(graph.Claim("instance of", graph.item(it.cls)), self.ids.pid, self.qid_of))
            except Unresolved:
                pass                                            # pass 2 adds it once the class item has an id
        body["claims"] = claims
        return body

    def create_item(self, it: graph.Item, full: bool = False) -> Write:
        """Pass 1's create of a new item: labels, descriptions, aliases, the key and the class only, or with
        ``full`` (single pass, when every item it names has an id) its whole statement set, after which pass 2
        skips it and the content hash is recorded for ``--resume``."""
        kind = SC.kind_of(it.key)
        if it.key in self.held:
            return self.record(Write(1, kind, it.key, "skip-held"))
        if self.resume and self.hashes.get(it.key) and self.hashes[it.key] == content_hash(it):
            return self.record(Write(1, kind, it.key, "skip-resume", qid=self.ids.qids.get(it.key)))
        if self.ids.has(it.key):
            return self.record(Write(1, kind, it.key, "skip-exists", qid=self.ids.qid(it.key),
                                     note="pass 2 " + ("replaces" if owned(it.key) else "appends")))
        dropped: list[str] = []
        if full:
            try:
                body, dropped = self.full_body(it)
            except (ValueError, Unresolved) as e:         # a malformed value: create bare, pass 2 reports it
                self.log(f"{it.key}: full create refused ({e}); created bare")
                body, full = self.create_body(it), False
        else:
            body = self.create_body(it)
        w = Write(1, kind, it.key, "create", new="item", body=body, full=full)
        if dropped:
            w.note = f"{len(dropped)} snaks dropped (no id): " + "; ".join(dropped[:3])
            self.dropped += [f"{it.key}: {d}" for d in dropped]
        if self.dry_run:
            w.qid, w.placeholder = self.ids.placeholder_q(it.key), True
            if full:
                self.complete.add(it.key)
            return self.record(w)
        suffixed = False
        while True:
            try:
                res = self.api.edit(body, new="item", summary=f"lexflow: {it.key}")
                w.qid = res["entity"]["id"]
                self.remember_item(it.key, w.qid, it.label, content_hash(it) if full else None)
                if full:
                    self.complete.add(it.key)
                break
            except WikibaseError as e:
                other = owner_of(str(e))
                if other and self.live_key_of(other) == it.key:
                    # the item an earlier run created for this key (wikibase_items was lost): reuse it
                    w.action, w.qid, w.note = "skip-exists", other, "found by label clash; pass 2 updates"
                    self.remember_item(it.key, other, it.label)
                    break
                if other and not suffixed:
                    tail = it.key.rsplit(":", 1)[-1]
                    desc = (it.description or "")[:LABEL_MAX - len(tail) - 3]
                    body["descriptions"] = {LANG: {"language": LANG, "value": f"{desc} [{tail}]"}}
                    w.note, suffixed = f"description suffixed after a label clash with {other}", True
                    continue
                w.action, w.error, w.code = "fail", str(e)[:300], error_code(e)
                self.log(f"{it.key}: {e}")
                break
            except (KeyError, ValueError, Unresolved) as e:
                w.action, w.error, w.code = "fail", str(e)[:300], "error"
                self.log(f"{it.key}: {e}")
                break
        return self.record(w)

    # ---- pass 2
    def full_body(self, it: graph.Item) -> tuple[dict, list[str]]:
        dropped: list[str] = []
        body = labels_body(it)
        claims = [statement(graph.Claim(KEY_PROP, graph.ext(it.key)), self.ids.pid, self.qid_of)]
        if it.cls:
            try:
                claims.append(statement(graph.Claim("instance of", graph.item(it.cls)), self.ids.pid, self.qid_of))
            except Unresolved as e:
                dropped.append(f"instance of: {e}")
        for c in it.claims:
            if c.prop == KEY_PROP and c.value.value == it.key:
                continue                                        # written first, above
            try:
                claims.append(statement(c, self.ids.pid, self.qid_of, dropped))
            except Unresolved as e:
                dropped.append(f"{c.prop}: {e}")
        body["claims"] = claims
        return body, dropped

    def append_body(self, it: graph.Item, qid: str) -> tuple[dict, list[str]]:
        """Only what the live entity lacks: labels or descriptions it has none of, aliases it lacks (``add``), and
        statements whose main snak it does not carry."""
        full, dropped = self.full_body(it)
        self.fetch_live([qid])
        live = self.live_entities.get(qid) or {}
        body: dict[str, Any] = {}
        if not (live.get("labels") or {}).get(LANG):
            body["labels"] = full["labels"]
        if full.get("descriptions") and not (live.get("descriptions") or {}).get(LANG):
            body["descriptions"] = full["descriptions"]
        have_aliases = {a["value"] for a in (live.get("aliases") or {}).get(LANG, [])}
        live_label = ((live.get("labels") or {}).get(LANG) or {}).get("value")
        new_aliases = [a for a in it.aliases if a not in have_aliases and a != live_label]
        if new_aliases:
            body["aliases"] = {LANG: [{"language": LANG, "value": a[:LABEL_MAX], "add": ""} for a in new_aliases]}
        have = {snak_sig(s.get("mainsnak") or {}) for ss in (live.get("claims") or {}).values() for s in ss}
        missing = [s for s in full["claims"] if snak_sig(s["mainsnak"]) not in have]
        if missing:
            body["claims"] = missing
        return body, dropped

    def pass2(self, props: bool = True) -> None:
        if props:
            self.update_properties()
        order = {k: i for i, k in enumerate(KIND_ORDER)}
        todo = sorted(self.items, key=lambda i: (order.get(SC.kind_of(i.key), 99), i.key))
        if self.session is not None:
            # one batched read for every item that is appended to, before the writes start
            self.fetch_live([self.ids.qids[it.key] for it in todo
                             if not owned(it.key) and it.key in self.ids.qids and it.key not in self.ids.placeholders])
        for n, it in enumerate(todo, 1):
            self.update_item(it)
            if n % 200 == 0:
                self.log(f"  pass 2: {n}/{len(todo)}")

    def update_properties(self) -> None:
        """The formatter claims of the new properties (their properties are new too, so they wait for pass 2) and
        the ``P7 equivalent property`` claims (Wikidata and the ontology IRIs of ``schema.equivalents_of``) when
        the create did not carry them: appended when missing.  The 21 existing properties (P5-P25) get their
        ``P7`` claims the same way: the Wikidata property of ``schema.EXISTING_WIKIDATA`` first, then the ontology
        IRIs."""
        existing = [(label, pid) for label, pid in SC.EXISTING.items()
                    if SC.EXISTING_EQUIVALENTS.get(label) or SC.EXISTING_WIKIDATA.get(label)]
        pids = [pid for _, pid in existing] + [self.ids.pids[p.label] for p in SC.PROPERTIES if p.label in self.ids.pids
                                              and p.label not in self.ids.placeholders]
        if self.session is not None and pids:
            self.fetch_live(pids)
        for label, pid in existing:
            claims = [statement(c, self.ids.pid, self.qid_of)
                      for c in equivalent_claims(label, SC.EXISTING_WIKIDATA.get(label))]
            self._append_property_claims(label, pid, claims, "ontology equivalents")
        for p in SC.PROPERTIES:
            if p.label not in self.ids.pids:
                self.record(Write(2, "property", p.label, "skip-unresolved", note="not created in pass 1"))
                continue
            pid = self.ids.pids[p.label]
            claims, dropped = [], []
            for fprop, tpl in (("formatter URL", p.formatter_url), ("formatter URI for RDF resource", p.formatter_rdf)):
                if tpl:
                    try:
                        claims.append(statement(graph.Claim(fprop, graph.string(tpl)), self.ids.pid, self.qid_of))
                    except Unresolved as e:
                        dropped.append(f"{p.label} {fprop}: {e}")
            claims += [statement(c, self.ids.pid, self.qid_of) for c in equivalent_claims(p.label, p.wikidata)]
            self.dropped += dropped
            self._append_property_claims(p.label, pid, claims, "formatters")

    def _append_property_claims(self, label: str, pid: str, claims: list[dict], what: str) -> None:
        """Append to a property item the statements of ``claims`` it does not carry (one ``Write`` either way)."""
        live = self.live_entities.get(pid) or {}
        have = {snak_sig(s.get("mainsnak") or {}) for ss in (live.get("claims") or {}).values() for s in ss}
        missing = [s for s in claims if snak_sig(s["mainsnak"]) not in have] if live else claims
        if not missing:
            self.record(Write(2, "property", label, "skip-current", qid=pid))
            return
        w = Write(2, "property", label, "update", qid=pid, body={"claims": missing},
                  placeholder=label in self.ids.placeholders)
        if self.dry_run:
            self.record(w)
            return
        try:
            self.api.edit(w.body, qid=pid, summary=f"lexflow: property {label} {what}")
        except (WikibaseError, KeyError, ValueError) as e:
            w.action, w.error, w.code = "fail", str(e)[:300], error_code(e)
            self.log(f"property {label}: {e}")
        self.record(w)

    def update_item(self, it: graph.Item) -> Write:
        kind = SC.kind_of(it.key)
        if it.key in self.held:
            return self.record(Write(2, kind, it.key, "skip-held"))
        if it.key in self.complete:
            return self.record(Write(2, kind, it.key, "skip-complete", qid=self.ids.qids.get(it.key),
                                     note="created with every statement in pass 1 (single pass)"))
        digest = content_hash(it)
        if self.resume and self.hashes.get(it.key) == digest:
            return self.record(Write(2, kind, it.key, "skip-resume", qid=self.ids.qids.get(it.key)))
        if not self.ids.has(it.key):
            return self.record(Write(2, kind, it.key, "skip-unresolved", note="no id: pass 1 did not create it"))
        qid = self.ids.qid(it.key)
        own = owned(it.key)
        try:
            if own:
                body, dropped = self.full_body(it)
                w = Write(2, kind, it.key, "clear", qid=qid, clear=True, body=body)
            else:
                if it.key in self.ids.placeholders:
                    body, dropped = self.full_body(it)
                    body.pop("labels", None), body.pop("descriptions", None), body.pop("aliases", None)
                else:
                    body, dropped = self.append_body(it, qid)
                if not body:
                    return self.record(Write(2, kind, it.key, "skip-current", qid=qid))
                w = Write(2, kind, it.key, "update", qid=qid, body=body)
        except (ValueError, Unresolved) as e:
            w = Write(2, kind, it.key, "fail", qid=qid, error=str(e)[:300], code="error")
            self.log(f"{it.key}: {e}")
            return self.record(w)
        w.placeholder = it.key in self.ids.placeholders
        if dropped:
            w.note = f"{len(dropped)} snaks dropped (no id): " + "; ".join(dropped[:3])
            self.dropped += [f"{it.key}: {d}" for d in dropped]
        if self.dry_run:
            return self.record(w)
        try:
            self.api.edit(body, qid=qid, clear=w.clear, summary=f"lexflow: {it.key} ({'replace' if own else 'append'})")
            self.remember_item(it.key, qid, it.label, digest)
        except WikibaseError as e:
            w.action, w.error, w.code = "fail", str(e)[:300], error_code(e)
            self.log(f"{it.key}: {e}")
        return self.record(w)

    # ---- the summary
    def summary(self) -> dict:
        per_pass: dict[str, dict[str, Counter]] = {}
        for w in self.writes:
            per_pass.setdefault(str(w.pass_no), {}).setdefault(w.kind, Counter())[w.action] += 1
        creates = sum(1 for w in self.writes if w.action == "create")
        full = sum(1 for w in self.writes if w.action == "create" and w.full)
        updates = sum(1 for w in self.writes if w.action in ("update", "clear"))
        examples: dict[str, list[dict]] = {}
        for w in self.writes:
            if w.body is None:
                continue
            ex = examples.setdefault(f"{w.pass_no}:{w.kind}:{w.action}", [])
            if len(ex) < EXAMPLES_PER_KIND:
                ex.append({"key": w.key, "qid": w.qid, "new": w.new, "clear": w.clear, "body": example_text(w.body)})
        return {
            "counts": {p: {k: dict(c) for k, c in kinds.items()} for p, kinds in per_pass.items()},
            "creates": creates, "creates_full": full, "updates": updates, "single_pass": self.single_pass,
            "total_writes": creates + updates,
            "properties_to_create": [w.key for w in self.writes if w.kind == "property" and w.action == "create"],
            "failures_by_code": dict(self.failures),
            "failures": [w.row() for w in self.writes if w.action == "fail"][:500],
            "held_skipped": sorted({w.key for w in self.writes if w.action == "skip-held"}),
            "dropped_snaks": len(self.dropped), "dropped_examples": self.dropped[:50],
            "examples": examples,
        }


# --------------------------------------------------------------------------- the run


def print_summary(s: dict, log: Log = print) -> None:
    for p in sorted(s["counts"]):
        log(f"pass {p}:")
        log(f"  {'kind':16} {'create':>7} {'update':>7} {'clear':>7} {'exists':>7} {'held':>6} {'resume':>7} "
            f"{'current':>8} {'unres.':>7} {'fail':>5} {'done':>5}")
        for kind, c in sorted(s["counts"][p].items(), key=lambda kv: (KIND_ORDER.index(kv[0])
                                                                      if kv[0] in KIND_ORDER else 99, kv[0])):
            log(f"  {kind:16} {c.get('create', 0):>7} {c.get('update', 0):>7} {c.get('clear', 0):>7} "
                f"{c.get('skip-exists', 0):>7} {c.get('skip-held', 0):>6} {c.get('skip-resume', 0):>7} "
                f"{c.get('skip-current', 0):>8} {c.get('skip-unresolved', 0):>7} {c.get('fail', 0):>5} "
                f"{c.get('skip-complete', 0):>5}")
    log(f"creates {s['creates']}" + (f" ({s.get('creates_full', 0)} with every statement: single pass)"
                                      if s.get("single_pass") else "")
        + f", updates {s['updates']}; properties to create: {len(s['properties_to_create'])}"
        + (f"; held items skipped: {len(s['held_skipped'])}" if s["held_skipped"] else "")
        + (f"; snaks dropped for want of an id: {s['dropped_snaks']}" if s["dropped_snaks"] else ""))
    if s["failures_by_code"]:
        log("failures by code: " + ", ".join(f"{k} {n}" for k, n in sorted(s["failures_by_code"].items())))
    for name, exs in sorted(s["examples"].items()):
        log(f"examples {name}:")
        for ex in exs:
            log(f"  {ex['key']} -> {ex['qid']}{' (new ' + ex['new'] + ')' if ex['new'] else ''}"
                f"{' clear' if ex['clear'] else ''}: {ex['body'][:400]}")


def write_plan(pusher: Pusher, summary: dict, out_dir: Path, meta: dict) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    plan = dict(meta, generated=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), site=SITE,
                writes=[w.row() for w in pusher.writes], **summary)
    (out_dir / PLAN_NAME).write_text(json.dumps(plan, indent=1, ensure_ascii=False), encoding="utf-8")
    with (out_dir / BODIES_NAME).open("w", encoding="utf-8") as f:
        for w in pusher.writes:
            if w.body is not None:
                f.write(json.dumps({"pass": w.pass_no, "key": w.key, "qid": w.qid, "action": w.action, "new": w.new,
                                    "clear": w.clear, "body": w.body}, ensure_ascii=False) + "\n")
    return out_dir / PLAN_NAME


def check_live(items: list[graph.Item], pusher: Pusher, log: Log = print) -> dict:
    """``sparql/coverage.rq`` on the live endpoint against the plan's counts (``qs.check``)."""
    from . import qs
    ids = qs.Ids(properties=dict(pusher.ids.pids), items=dict(pusher.ids.qids), labels=dict(pusher.ids.class_labels))
    return qs.check(items, SC, ids, qs.Client(log=log), log)


def run(con: sqlite3.Connection, *, dry_run: bool = True, pass_no: str = "all", limit: int | None = None,
        kinds: list[str] | None = None, states=None, places=None, drafts: bool = True, asked_drafts: bool = False,
        resume: bool = False, allow_held: bool = False, check: bool = False, live: bool = True,
        out_dir: Path | None = None, single_pass: bool = False, pause: float | None = None, bot: bool = False,
        items: list[graph.Item] | None = None, api: Api | None = None, session=None, log: Log = print) -> dict:
    out_dir = out_dir or OUT_DIR
    ensure_tables(con)
    report = read_lint(out_dir / LINT_NAME)
    held = held_keys(report)
    if not dry_run:
        if report is None and not allow_held:
            raise HeldError(f"{out_dir / LINT_NAME} is missing: run `lexflow wikibase lint` first (or --allow-held)")
        if held and not allow_held:
            raise HeldError(f"the lint report holds {len(held)} items: fix them and re-run the lint, or --allow-held "
                            f"(held items are never pushed either way)")
        # a report linted for some jurisdictions does not clear a push of others (a `--states jpn` lint left in the
        # default directory must not wave through a push of every state)
        linted = ((report or {}).get("scope") or {}).get("states")
        if linted is not None and not allow_held:
            want = {str(s).strip().lower() for s in (states or [])}
            have = {str(s).strip().lower() for s in linted}
            if not want or not want <= have:
                raise HeldError(f"the lint report covers {', '.join(sorted(have)) or 'nothing'} only: run `lexflow "
                                f"wikibase lint` for this push's states first (or --allow-held)")
    if items is None:
        items = graph.build(con, states=states, places=places, drafts=drafts, asked_drafts=asked_drafts, log=log)
    if kinds:
        items = [it for it in items if SC.kind_of(it.key) in kinds]
    if limit:
        order = {k: i for i, k in enumerate(KIND_ORDER)}
        items = sorted(items, key=lambda i: (order.get(SC.kind_of(i.key), 99), i.key))[:limit]
    if api is None:
        api = Api(config.WIKIBASE_URL, config.WIKIBASE_BOT_USER, config.WIKIBASE_BOT_PASSWORD, dry_run=dry_run)
        if session is not None:
            api.session = session
            api.session.headers["User-Agent"] = USER_AGENT
    if getattr(api, "log", "") is None:
        api.log = log
    if pause is not None:                   # the operator's choice once the account may write faster (wikidata-laws.md)
        api.pause = max(0.0, float(pause))
    if bot:
        api.bot = True
    if not dry_run:
        if not (api.user and api.password):
            raise PushError("set LEXI_USER / LEXI_PASS (or WIKIBASE_BOT_USER / WIKIBASE_BOT_PASSWORD)")
        log(f"signed in to {SITE} as {api.login()}")
    pusher = Pusher(con, items, api=api, dry_run=dry_run, resume=resume, held=held, log=log, single_pass=single_pass)
    if live:
        pusher.ids.load_live(api.session, log)
    else:
        pusher.session = None
    t = time.monotonic()
    if pass_no in ("1", "all"):
        pusher.pass1()
    if pass_no in ("2", "all"):
        pusher.pass2()
    summary = pusher.summary()
    meta = {"dry_run": dry_run, "pass": pass_no, "items": len(items), "limit": limit, "kinds": kinds, "states": states,
            "places": places, "drafts": drafts, "asked_drafts": asked_drafts, "resume": resume, "live": live,
            "single_pass": single_pass,
            "held": sorted(held),
            "seconds": round(time.monotonic() - t, 1), "api_writes": api.writes,
            "placeholders": sorted(pusher.ids.placeholders)[:20], "placeholder_count": len(pusher.ids.placeholders)}
    path = write_plan(pusher, summary, out_dir, meta)
    print_summary(summary, log)
    log(f"plan written to {path}" + (" (dry run: nothing was written to the wiki)" if dry_run else ""))
    result = dict(meta, summary=summary, plan=str(path))
    if check and not dry_run:
        result["check"] = check_live(items, pusher, log)
    return result


# --------------------------------------------------------------------------- command line


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="lexflow wikibase push", description=__doc__.split("\n\n")[0])
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--dry-run", action="store_true", default=True, help="plan only (the default)")
    g.add_argument("--really", action="store_true", help="write to the wiki")
    ap.add_argument("--pass", dest="pass_no", choices=["1", "2", "all"], default="all")
    ap.add_argument("--limit", type=int, help="only the first N items (in write order)")
    ap.add_argument("--kinds", help="comma-separated kinds (statute,step,...)")
    ap.add_argument("--states", help="comma-separated state codes to limit the graph")
    ap.add_argument("--places", help="comma-separated government ids to limit the graph")
    ap.add_argument("--no-drafts", action="store_true", help="leave draft (single-tier) models out")
    ap.add_argument("--asked-drafts", action="store_true", help="include asked answers as draft process items "
                                                               "(lexflow:process:asked:<state>:<question>)")
    ap.add_argument("--resume", action="store_true", help="skip items whose content hash is already recorded")
    ap.add_argument("--single-pass", action="store_true", help="create a new item with every statement in one write "
                                                              "when every item it names already has an id (pass 2 "
                                                              "then skips it); the rest as before")
    ap.add_argument("--pause", type=float, help=f"seconds between writes (default {PAUSE}); lower it only when the "
                                                 "account is in the bot group with the high-volume grant and the "
                                                 "wiki answers without maxlag or ratelimited errors")
    ap.add_argument("--bot", action="store_true", help="send bot=1 (only once the account is in the bot group and "
                                                       "its bot password has the high-volume grant)")
    ap.add_argument("--allow-held", action="store_true", help="run --really although the lint report holds items "
                                                             "(held items are still skipped)")
    ap.add_argument("--check", action="store_true", help="after a real run, compare coverage.rq live with the plan")
    ap.add_argument("--no-live", action="store_true", help="do not read the live wiki (offline plan)")
    ap.add_argument("--db", help="path of the lexflow database")
    ap.add_argument("--out", help=f"output directory (default {OUT_DIR})")
    args = ap.parse_args(argv)
    log = lambda *a: print(*a, file=sys.stderr, flush=True)       # noqa: E731
    con = db.connect(args.db) if args.db else db.connect()
    try:
        result = run(con, dry_run=not args.really, pass_no=args.pass_no, limit=args.limit,
                     kinds=args.kinds.split(",") if args.kinds else None,
                     states=args.states.split(",") if args.states else None,
                     places=args.places.split(",") if args.places else None, drafts=not args.no_drafts,
                     asked_drafts=args.asked_drafts, resume=args.resume, allow_held=args.allow_held,
                     check=args.check, live=not args.no_live, single_pass=args.single_pass, pause=args.pause,
                     bot=args.bot,
                     out_dir=Path(args.out) if args.out else None, log=log)
    except HeldError as e:
        log(f"refused: {e}")
        return 3
    except PushError as e:
        log(str(e))
        return 2
    finally:
        con.close()
    return 1 if result["summary"]["failures_by_code"] else 0


if __name__ == "__main__":
    sys.exit(main())
