"""The shared id map for Lexipedia's Wikibase: which ``P`` a property label is and which ``Q`` a lexflow key is.

Four layers, in order of precedence:

1. The database tables the push writes as it creates or finds each entity (``lexflow wikibase push --really``,
   lexflow/publish/push.py): ``wikibase_items`` (key -> Q) and ``wikibase_props`` (label -> P).  They are read with a
   short read-only connection (``database_ids``), so local SPARQL and the Query page use the real ids as the push
   records them, even while a long push is still running; a locked or missing database gives nothing, never an
   error.
2. ``out/wikibase/ids.json``, written by ``python -m lexflow.publish.qs --resolve`` after pass 1 of the Claude in
   Chrome packet (docs/design/wikibase-schema.md section 5): every ``P25 legal identifier`` key -> Q and every
   property label -> P, read from the public API.  Either ``{"items": {...}, "properties": {...}}`` or one flat
   object (values starting with ``P`` are properties) is accepted.
3. The ids the wiki already has: the 25 existing properties (``schema.EXISTING``) and the existing class items
   (``schema.CLASSES`` entries with a ``qid``), with a copy of each here so the map works before ``schema.py`` lands.
4. Provisional ids for everything else: ``P900+`` and ``Q900000+``, assigned deterministically by sorted label or key
   (``assign``), so the Turtle written by ``rdf.py`` and the tokens in ``sparql/*.rq`` agree run after run.  The
   assignment made when the Turtle was last written is kept in ``data/wikibase/provisional-ids.json`` so a query can
   be expanded later without rebuilding the graph.

``expand(text)`` replaces ``{P:label}`` and ``{Q:key}`` tokens by bare ids (``P17``, ``Q24``), so a query writes
``lxt:{P:bearer}`` and ``lx:{Q:lexflow:jurisdiction:va}``.  With ``live=True`` a token the map cannot resolve is looked
up on the public SPARQL endpoint (``P25`` for keys, the English label for properties), one request per second, and
remembered in ``data/wikibase/live-ids.json``; nothing is ever written to the wiki.
"""
from __future__ import annotations

import json
import re
import sqlite3
import time
from pathlib import Path

import requests

from .. import config

ENTITY = "https://lexipedia.wikibase.cloud/entity/"
ENDPOINT = "https://lexipedia.wikibase.cloud/query/sparql"
USER_AGENT = "lexflow-research/0.1"
IDS_PATH = config.ROOT / "out" / "wikibase" / "ids.json"
P_BASE = 900
Q_BASE = 900_000

# The wiki's own properties and classes (P1-P4, Q5-Q6 are the sandbox's and are left alone).
EXISTING_PROPERTIES: dict[str, str] = {
    "instance of": "P5", "subclass of": "P6", "equivalent property": "P7", "exact match": "P8", "part of": "P9",
    "has part": "P10", "follows": "P11", "followed by": "P12", "references": "P13", "based on": "P14",
    "applies to jurisdiction": "P15", "deontic modality": "P16", "bearer": "P17", "condition": "P18",
    "governed by norm": "P19", "sanction": "P20", "defeated by": "P21", "citation": "P22", "official text": "P23",
    "effective date": "P24", "legal identifier": "P25",
}
EXISTING_CLASSES: dict[str, str] = {
    "legal process": "Q7", "legal process step": "Q8", "decision point": "Q9", "statute or legal provision": "Q10",
    "norm": "Q11", "deontic specification": "Q12", "Obligation": "Q13", "Permission": "Q14", "Prohibition": "Q15",
    "Right": "Q16", "weak permission": "Q17", "strong permission": "Q18", "achievement obligation": "Q19",
    "maintenance obligation": "Q20", "jurisdiction": "Q21", "court decision": "Q22", "legal role": "Q23",
}

TOKEN = re.compile(r"\{(P|Q):([^{}]+)\}")
_ID = re.compile(r"^[PQ]\d+$")


def _schema():
    try:
        from . import schema
    except ImportError:          # written by another hand; the copies above carry the map until then
        return None
    return schema


def _provisional_path() -> Path:
    return config.DATA_DIR / "wikibase" / "provisional-ids.json"


def _live_cache_path() -> Path:
    return config.DATA_DIR / "wikibase" / "live-ids.json"


def _turtle_path() -> Path:
    return config.DATA_DIR / "wikibase" / "turtle-ids.json"


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except (OSError, ValueError):
        return {}


def _split(raw: dict) -> tuple[dict[str, str], dict[str, str]]:
    """``(properties, items)`` from either ids.json layout."""
    if "items" in raw or "properties" in raw:
        props = raw.get("properties") or raw.get("P") or {}
        items = raw.get("items") or raw.get("Q") or {}
        return {str(k): str(v) for k, v in props.items()}, {str(k): str(v) for k, v in items.items()}
    props = {k: v for k, v in raw.items() if isinstance(v, str) and v.startswith("P")}
    items = {k: v for k, v in raw.items() if isinstance(v, str) and v.startswith("Q")}
    return props, items


DB_TIMEOUT = 2.0


def database_ids(db_path: Path | str | None = None, timeout: float = DB_TIMEOUT) -> tuple[dict[str, str], dict[str, str]]:
    """``(properties, items)`` from ``wikibase_props`` and ``wikibase_items``: the ids the push recorded.  A short
    read-only connection (WAL readers never wait on the writer; a lock or a missing table waits ``timeout`` seconds
    at most); a database that cannot be read gives two empty maps."""
    path = Path(db_path or config.DB_PATH)
    if not path.exists():
        return {}, {}
    try:
        con = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True, timeout=timeout)
    except sqlite3.Error:
        return {}, {}
    props: dict[str, str] = {}
    items: dict[str, str] = {}
    try:
        try:
            for label, pid in con.execute("SELECT label, pid FROM wikibase_props WHERE pid IS NOT NULL"):
                if label and pid and _ID.match(str(pid)) and str(pid).startswith("P"):
                    props[str(label)] = str(pid)
        except sqlite3.Error:
            pass
        try:
            for key, qid in con.execute("SELECT key, qid FROM wikibase_items WHERE qid IS NOT NULL"):
                if key and qid and _ID.match(str(qid)) and str(qid).startswith("Q"):
                    items[str(key)] = str(qid)
        except sqlite3.Error:
            pass
    finally:
        con.close()
    return props, items


class IdMap:
    def __init__(self, ids_path: Path | str | None = None, *, provisional: bool = True, database: bool = True,
                 db_path: Path | str | None = None):
        self.properties: dict[str, str] = dict(EXISTING_PROPERTIES)
        self.items: dict[str, str] = {}
        self.class_labels: dict[str, str] = dict(EXISTING_CLASSES)     # existing class label -> Q
        self.resolved_properties: set[str] = set(EXISTING_PROPERTIES)
        self.resolved_items: set[str] = set()
        self.unresolved: list[str] = []
        sch = _schema()
        if sch is not None:
            for label, pid in getattr(sch, "EXISTING", {}).items():
                self.properties[label] = pid
                self.resolved_properties.add(label)
            for c in _classes(sch):
                if c.get("qid") and c.get("label"):
                    self.class_labels[c["label"]] = c["qid"]
                    if c.get("key"):
                        self.items[c["key"]] = c["qid"]
                        self.resolved_items.add(c["key"])
        for label, qid in self.class_labels.items():
            self.items.setdefault(_class_key(label), qid)
        # layer 1: what the push recorded in the database (wins over ids.json)
        db_props, db_items = database_ids(db_path) if database else ({}, {})
        self.from_database: int = len(db_props) + len(db_items)
        self.properties.update(db_props)
        self.resolved_properties |= set(db_props)
        self.items.update(db_items)
        self.resolved_items |= set(db_items)
        # layer 2: ids.json, for what the database does not record
        self.ids_path = Path(ids_path) if ids_path else IDS_PATH
        self.resolved = self.ids_path.exists() or bool(self.from_database)
        props, items = _split(_read_json(self.ids_path))
        for label, pid in props.items():
            if label not in db_props:
                self.properties[label] = pid
                self.resolved_properties.add(label)
        for key, qid in items.items():
            if key not in db_items:
                self.items[key] = qid
                self.resolved_items.add(key)
        if provisional:
            prov = _read_json(_provisional_path())
            for label, pid in (prov.get("properties") or {}).items():
                self.properties.setdefault(label, pid)
            for key, qid in (prov.get("items") or {}).items():
                self.items.setdefault(key, qid)
        self._live: dict | None = None
        self.turtle = False

    # ------------------------------------------------------------ assignment
    def assign(self, keys=(), labels=()) -> None:
        """Give provisional ids to the keys and property labels that have none, in sorted order after the ones already
        assigned, so a key keeps its id when others are added."""
        used_p = {int(v[1:]) for v in self.properties.values() if _ID.match(v)}
        used_q = {int(v[1:]) for v in self.items.values() if _ID.match(v)}
        n = P_BASE
        for label in sorted(set(labels) - set(self.properties)):
            while n in used_p:
                n += 1
            self.properties[label] = f"P{n}"
            used_p.add(n)
        n = Q_BASE
        for key in sorted(set(keys) - set(self.items)):
            while n in used_q:
                n += 1
            self.items[key] = f"Q{n}"
            used_q.add(n)

    def save_provisional(self) -> Path:
        path = _provisional_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {"properties": {k: v for k, v in self.properties.items() if k not in self.resolved_properties},
                "items": {k: v for k, v in self.items.items() if k not in self.resolved_items}}
        path.write_text(json.dumps(data, indent=1, sort_keys=True), encoding="utf-8")
        return path

    def save_turtle_map(self) -> Path:
        """Every id the Turtle was written with (resolved and provisional alike), so local queries keep matching the
        store even after ``ids.json`` changes under it (``for_turtle``)."""
        path = _turtle_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"properties": self.properties, "items": self.items}, indent=1, sort_keys=True),
                        encoding="utf-8")
        return path

    @classmethod
    def for_turtle(cls, ids_path: Path | str | None = None, **kw) -> "IdMap":
        """The map for querying the local store: the ids its Turtle was written with win over everything."""
        m = cls(ids_path, **kw)
        used = _read_json(_turtle_path())
        for label, pid in (used.get("properties") or {}).items():
            m.properties[label] = pid
            m.resolved_properties.add(label)
        for key, qid in (used.get("items") or {}).items():
            m.items[key] = qid
            m.resolved_items.add(key)
        m.turtle = bool(used)
        return m

    @staticmethod
    def turtle_stale(ttl_path: Path | None = None) -> bool:
        """Whether ``ids.json`` is newer than the Turtle, so the local store still carries provisional ids for keys
        the wiki has since minted (rebuild with ``lexflow sparql --build``)."""
        ttl = ttl_path or (config.DATA_DIR / "wikibase" / "lexipedia.ttl")
        return IDS_PATH.exists() and ttl.exists() and IDS_PATH.stat().st_mtime > ttl.stat().st_mtime

    # --------------------------------------------------------------- lookups
    def pid(self, label: str, live: bool = False) -> str:
        if _ID.match(label):
            return label
        if label in self.resolved_properties or (label in self.properties and not live):
            return self.properties[label]
        if live:
            found = self._lookup_live_property(label)
            if found:
                self.properties[label] = found
                self.resolved_properties.add(label)
                return found
        if label not in self.properties:
            self.assign(labels=[label])
        self.unresolved.append(f"P:{label}")
        return self.properties[label]

    def qid(self, key: str, live: bool = False) -> str:
        if _ID.match(key):
            return key
        if key in self.class_labels:
            return self.class_labels[key]
        if key in self.resolved_items or (key in self.items and not live):
            return self.items[key]
        if live:
            found = self._lookup_live_item(key)
            if found:
                self.items[key] = found
                self.resolved_items.add(key)
                return found
        if key not in self.items:
            self.assign(keys=[key])
        self.unresolved.append(f"Q:{key}")
        return self.items[key]

    def expand(self, text: str, live: bool = False) -> str:
        """``{P:label}`` -> ``P17`` and ``{Q:key}`` -> ``Q24`` throughout ``text``."""
        def sub(m):
            kind, name = m.group(1), m.group(2).strip()
            return self.pid(name, live) if kind == "P" else self.qid(name, live)
        return TOKEN.sub(sub, text)

    def label_of(self, pid: str) -> str | None:
        for label, p in self.properties.items():
            if p == pid:
                return label
        return None

    # ------------------------------------------------------------------ live
    def _live_cache(self) -> dict:
        if self._live is None:
            raw = _read_json(_live_cache_path())
            self._live = {"properties": dict(raw.get("properties") or {}), "items": dict(raw.get("items") or {})}
        return self._live

    def _save_live(self) -> None:
        path = _live_cache_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self._live, indent=1, sort_keys=True), encoding="utf-8")

    def _lookup_live_property(self, label: str) -> str | None:
        cache = self._live_cache()
        if label in cache["properties"]:
            return cache["properties"][label] or None
        q = ('PREFIX wikibase: <http://wikiba.se/ontology#> PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> '
             'SELECT ?p WHERE { ?p a wikibase:Property ; rdfs:label %s@en } LIMIT 1' % _literal(label))
        found = _entity_of(live_select(q), "p")
        cache["properties"][label] = found or ""
        self._save_live()
        return found

    def _lookup_live_item(self, key: str) -> str | None:
        cache = self._live_cache()
        if key in cache["items"]:
            return cache["items"][key] or None
        q = ('SELECT ?s WHERE { ?s <%sprop/direct/P25> %s } LIMIT 1'
             % ("https://lexipedia.wikibase.cloud/", _literal(key)))
        found = _entity_of(live_select(q), "s")
        cache["items"][key] = found or ""
        self._save_live()
        return found


def _classes(sch) -> list[dict]:
    classes = getattr(sch, "CLASSES", None) or []
    out = []
    for c in (classes.values() if isinstance(classes, dict) else classes):
        if isinstance(c, dict):
            d = dict(c)
        else:
            d = {k: getattr(c, k, None) for k in ("slug", "label", "qid", "key")}
        d.setdefault("key", f"lexflow:class:{d['slug']}" if d.get("slug") else None)
        out.append(d)
    return out


def _class_key(label: str) -> str:
    return "lexflow:class:" + re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")


def _literal(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'


def _entity_of(rows: list[dict], var: str) -> str | None:
    for r in rows:
        v = r.get(var, {}).get("value", "")
        if v.startswith(ENTITY):
            return v[len(ENTITY):]
    return None


_last_request = 0.0


def throttle() -> None:
    """Wait so that requests to the public endpoint (from any module) start at least one second apart."""
    global _last_request
    wait = _last_request + 1.0 - time.monotonic()
    if wait > 0:
        time.sleep(wait)
    _last_request = time.monotonic()


def live_select(query: str, timeout: int = 30) -> list[dict]:
    """POST a query to the public endpoint (at most one request a second) and return the JSON bindings."""
    throttle()
    r = requests.post(ENDPOINT, data={"query": query}, timeout=timeout,
                      headers={"Accept": "application/sparql-results+json", "User-Agent": USER_AGENT})
    r.raise_for_status()
    return r.json().get("results", {}).get("bindings", [])


_default: IdMap | None = None


def default(reload: bool = False) -> IdMap:
    global _default
    if _default is None or reload:
        _default = IdMap()
    return _default


def pid(label: str) -> str:
    return default().pid(label)


def qid(key: str) -> str:
    return default().qid(key)


def expand(query_text: str, live: bool = False) -> str:
    return default().expand(query_text, live=live)
