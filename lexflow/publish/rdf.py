"""Lexipedia's items as RDF, for SPARQL before (and beside) the wiki.

``write(items, path)`` serialises the ``Item`` objects that ``graph.build`` makes (docs/design/wikibase-schema.md
section 4) as Turtle in the Wikibase RDF layout, so a query written for https://lexipedia.wikibase.cloud/query/sparql
runs unchanged on the local copy (section 7):

- entity IRIs ``https://lexipedia.wikibase.cloud/entity/Qn`` (``lx:``), typed ``wikibase:Item``, with ``rdfs:label``,
  ``skos:prefLabel``, ``schema:name``, ``schema:description`` and ``skos:altLabel`` in English;
- direct claims ``lxt:Pn`` (``prop/direct/``) for every statement, and the full form ``lxp:Pn`` -> statement node
  with ``lxps:Pn`` (the value), ``lxpq:Pn`` (qualifiers), ``wikibase:rank`` and ``prov:wasDerivedFrom`` -> reference
  node with ``lxpr:Pn``;
- ``lxn:Pn`` (``prop/direct-normalized/``) and ``lxpsn:Pn`` for external ids whose property has a *formatter URI for
  RDF resource*, so ``Wikidata item ID`` becomes ``<http://www.wikidata.org/entity/Q812>`` and joins Wikidata in
  ``SERVICE`` queries; P25 gets the same when the schema gives it a formatter;
- quantities and times also as value nodes (``lxpsv:``) with unit and precision, as Wikibase writes them;
- the properties themselves as ``wikibase:Property`` entities with their type and the ``wikibase:directClaim`` /
  ``wikibase:claim`` / ... links, so label lookups work locally.

Ids come from ``lexflow.publish.ids`` (resolved from ``out/wikibase/ids.json`` when it exists, provisional ``P900+``
/ ``Q900000+`` otherwise).  ``load(path)`` puts the Turtle into a ``pyoxigraph.Store`` persisted under
``data/wikibase/store/``; ``query(store_or_live, text, live=False)`` runs a query locally or on the public endpoint
(read-only, ``User-Agent: lexflow-research/0.1``, one request a second).
"""
from __future__ import annotations

import hashlib
import re
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

import requests

from .. import config
from . import ids as I

BASE = "https://lexipedia.wikibase.cloud/"
PREFIXES: dict[str, str] = {
    "lx": BASE + "entity/",
    "lxs": BASE + "entity/statement/",
    "lxref": BASE + "reference/",
    "lxv": BASE + "value/",
    "lxt": BASE + "prop/direct/",
    "lxn": BASE + "prop/direct-normalized/",
    "lxp": BASE + "prop/",
    "lxps": BASE + "prop/statement/",
    "lxpsv": BASE + "prop/statement/value/",
    "lxpsn": BASE + "prop/statement/value-normalized/",
    "lxpq": BASE + "prop/qualifier/",
    "lxpqv": BASE + "prop/qualifier/value/",
    "lxpr": BASE + "prop/reference/",
    "lxprv": BASE + "prop/reference/value/",
    "wikibase": "http://wikiba.se/ontology#",
    "schema": "http://schema.org/",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "prov": "http://www.w3.org/ns/prov#",
    "wd": "http://www.wikidata.org/entity/",
    "wdt": "http://www.wikidata.org/prop/direct/",
}
# the prefixes every query file declares, in this order (section 6), with the ones references and dates need
QUERY_PREFIX_NAMES = ("lx", "lxt", "lxp", "lxps", "lxpq", "lxpr", "lxn", "wikibase", "schema", "rdfs", "skos",
                      "xsd", "prov", "wd", "wdt", "lxpsv", "lxpsn")
QUERY_PREFIXES = "\n".join(f"PREFIX {p}: <{PREFIXES[p]}>" for p in QUERY_PREFIX_NAMES)

DATATYPES = {"item": "WikibaseItem", "string": "String", "url": "Url", "time": "Time", "quantity": "Quantity",
             "monolingual": "Monolingualtext", "external-id": "ExternalId"}
# external-id properties whose value is also written as an IRI (the schema's formatter_rdf wins when present)
FORMATTER_RDF = {"Wikidata item ID": "http://www.wikidata.org/entity/$1"}
TTL_PATH = config.DATA_DIR / "wikibase" / "lexipedia.ttl"
STORE_DIR = config.DATA_DIR / "wikibase" / "store"
ENDPOINT = I.ENDPOINT
USER_AGENT = I.USER_AGENT


# ----------------------------------------------------------------------------------------------------- shapes
# The same shapes as lexflow.publish.schema / graph (duck-typed there); these copies let the tests build items by
# hand before the graph exists.
@dataclass
class Value:
    kind: str                   # item, string, url, time, quantity, monolingual, external-id
    value: str
    unit: str | None = None     # quantity: a key, label or Q of the unit item
    lang: str | None = None     # monolingual
    precision: int | None = None  # time: 9 year, 10 month, 11 day


@dataclass
class Claim:
    prop: str                   # the property's label
    value: Value
    qualifiers: list = field(default_factory=list)      # [(label, Value)]
    references: list = field(default_factory=list)      # [[(label, Value)], ...]


@dataclass
class Item:
    key: str
    label: str
    description: str = ""
    aliases: list = field(default_factory=list)
    cls: str | None = None      # class key or existing class label
    claims: list = field(default_factory=list)
    exists: bool = False


# ------------------------------------------------------------------------------------------------ serialising
def _esc(s: str) -> str:
    return (str(s).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "\\r")
            .replace("\t", "\\t"))


def _lit(s: str, lang: str | None = None, dt: str | None = None) -> str:
    out = f'"{_esc(s)}"'
    if lang:
        return f"{out}@{lang}"
    if dt:
        return f"{out}^^{dt}"
    return out


def _iri(s: str) -> str:
    s = str(s).strip()
    s = re.sub(r"[\x00-\x20<>\"{}|^`\\]", lambda m: "%%%02X" % ord(m.group(0)), s)
    return f"<{s}>"


_TIME = re.compile(r"^\+?(-?\d{4,})(?:-(\d{2})(?:-(\d{2}))?)?(?:T(\d{2}):(\d{2}):(\d{2}))?Z?(?:/(\d+))?$")


def _time(value: str, precision: int | None = None) -> tuple[str, int]:
    """``(xsd:dateTime text, precision)`` from ``2026-10-15``, ``+2026-10-15T00:00:00Z/11``, ``2026`` or an ISO stamp."""
    m = _TIME.match(str(value).strip())
    if not m:
        raise ValueError(f"not a date: {value!r}")
    y, mo, d, hh, mm, ss, p = m.groups()
    prec = precision or (int(p) if p else 11 if d else 10 if mo else 9)
    return f"{int(y):04d}-{mo or '01'}-{d or '01'}T{hh or '00'}:{mm or '00'}:{ss or '00'}Z", prec


def _quantity(value: str) -> str:
    s = str(value).strip().replace(",", "")
    if not re.match(r"^[+-]?\d+(\.\d+)?$", s):
        raise ValueError(f"not a number: {value!r}")
    return s


class Writer:
    def __init__(self, ids: I.IdMap, formatters: dict[str, str] | None = None, datatypes: dict[str, str] | None = None):
        self.ids = ids
        self.formatters = dict(FORMATTER_RDF)
        self.datatypes: dict[str, str] = {}       # property label -> kind
        self.descriptions: dict[str, str] = {}
        self.lines: list[str] = []
        self.values: dict[str, str] = {}          # value node id -> its triples
        self.refs: dict[str, str] = {}
        self._schema_properties(formatters, datatypes)

    def _schema_properties(self, formatters, datatypes):
        for label in I.EXISTING_PROPERTIES:
            self.datatypes[label] = "item"
        self.datatypes.update({"equivalent property": "url", "exact match": "url", "citation": "string",
                               "official text": "url", "effective date": "time", "legal identifier": "external-id"})
        sch = I._schema()
        for p in _properties(sch):
            if p.get("label"):
                self.datatypes[p["label"]] = _kind(p.get("datatype") or "string")
                if p.get("formatter_rdf"):
                    self.formatters[p["label"]] = p["formatter_rdf"]
                if p.get("description"):
                    self.descriptions[p["label"]] = p["description"]
        self.formatters.update(formatters or {})
        self.datatypes.update(datatypes or {})

    # ------------------------------------------------------------------ terms
    def q(self, ref: str) -> str:
        return "lx:" + self.ids.qid(ref)

    def p(self, label: str) -> str:
        return self.ids.pid(label)

    def term(self, v: Value, prop: str) -> str:
        kind = getattr(v, "kind", "string")
        val = getattr(v, "value", "")
        if kind == "item":
            return self.q(val)
        if kind == "url":
            return _iri(val)
        if kind == "time":
            t, _ = _time(val, getattr(v, "precision", None))
            return _lit(t, dt="xsd:dateTime")
        if kind == "quantity":
            return _lit(_quantity(val), dt="xsd:decimal")
        if kind == "monolingual":
            return _lit(val, lang=getattr(v, "lang", None) or "en")
        return _lit(val)

    def normalised(self, v: Value, prop: str) -> str | None:
        """The IRI an external id maps to through the property's RDF formatter, or None."""
        if getattr(v, "kind", None) != "external-id" or prop not in self.formatters:
            return None
        return _iri(self.formatters[prop].replace("$1", str(v.value)))

    def value_node(self, v: Value) -> str | None:
        """A ``lxv:`` node for a quantity with a unit or a time with a precision, created once per distinct value."""
        kind = getattr(v, "kind", None)
        if kind == "quantity" and getattr(v, "unit", None):
            amount = _quantity(v.value)
            unit = self.q(v.unit)
            body = (f"a wikibase:QuantityValue ;\n    wikibase:quantityAmount {_lit(amount, dt='xsd:decimal')} ;\n"
                    f"    wikibase:quantityUnit {unit}")
        elif kind == "time":
            t, prec = _time(v.value, getattr(v, "precision", None))
            body = (f"a wikibase:TimeValue ;\n    wikibase:timeValue {_lit(t, dt='xsd:dateTime')} ;\n"
                    f"    wikibase:timePrecision {prec} ;\n    wikibase:timeTimezone 0 ;\n"
                    f"    wikibase:timeCalendarModel wd:Q1985727")
        else:
            return None
        node = "lxv:" + hashlib.sha1(body.encode("utf-8")).hexdigest()[:32]
        self.values.setdefault(node, body)
        return node

    def snaks(self, pairs: Iterable, prefix: str, vprefix: str, nprefix: str | None = None) -> list[str]:
        out = []
        for label, v in pairs:
            pid = self.p(label)
            out.append(f"{prefix}:{pid} {self.term(v, label)}")
            n = self.normalised(v, label)
            if n and nprefix:
                out.append(f"{nprefix}:{pid} {n}")
            node = self.value_node(v)
            if node:
                out.append(f"{vprefix}:{pid} {node}")
        return out

    def reference(self, snaks: list) -> str:
        parts = self.snaks(snaks, "lxpr", "lxprv")
        body = " ;\n    ".join(["a wikibase:Reference"] + parts)
        node = "lxref:" + hashlib.sha1(body.encode("utf-8")).hexdigest()[:40]
        self.refs.setdefault(node, body)
        return node

    # ------------------------------------------------------------------ items
    def item(self, it: Item) -> None:
        qid = self.ids.qid(it.key)
        head = [f"lx:{qid} a wikibase:Item"]
        label = getattr(it, "label", "") or it.key
        head += [f"rdfs:label {_lit(label, 'en')}", f"skos:prefLabel {_lit(label, 'en')}", f"schema:name {_lit(label, 'en')}"]
        if getattr(it, "description", None):
            head.append(f"schema:description {_lit(it.description, 'en')}")
        for a in getattr(it, "aliases", None) or []:
            if a and a != label:
                head.append(f"skos:altLabel {_lit(a, 'en')}")
        claims = list(getattr(it, "claims", None) or [])
        cls = getattr(it, "cls", None)
        if cls and not any(c.prop == "instance of" and c.value.value == cls for c in claims):
            claims.insert(0, Claim("instance of", Value("item", cls)))
        if not any(c.prop == "legal identifier" for c in claims):
            claims.append(Claim("legal identifier", Value("external-id", it.key)))
        statements: list[str] = []
        for n, c in enumerate(claims):
            pid = self.p(c.prop)
            term = self.term(c.value, c.prop)
            head.append(f"lxt:{pid} {term}")
            norm = self.normalised(c.value, c.prop)
            if norm:
                head.append(f"lxn:{pid} {norm}")
            sid = "lxs:" + qid + "-" + str(uuid.uuid5(uuid.NAMESPACE_URL, f"{it.key}|{c.prop}|{n}|{c.value.kind}|{c.value.value}"))
            head.append(f"lxp:{pid} {sid}")
            body = ["a wikibase:Statement, wikibase:BestRank", "wikibase:rank wikibase:NormalRank", f"lxps:{pid} {term}"]
            if norm:
                body.append(f"lxpsn:{pid} {norm}")
            node = self.value_node(c.value)
            if node:
                body.append(f"lxpsv:{pid} {node}")
            body += self.snaks(getattr(c, "qualifiers", None) or [], "lxpq", "lxpqv")
            for ref in getattr(c, "references", None) or []:
                if ref:
                    body.append(f"prov:wasDerivedFrom {self.reference(ref)}")
            statements.append(f"{sid} " + " ;\n    ".join(body) + " .")
        self.lines.append(" ;\n    ".join(head) + " .")
        self.lines.extend(statements)
        self.lines.append("")

    def properties(self) -> None:
        for label in sorted(self.datatypes, key=lambda l: int(self.p(l)[1:])):
            pid = self.p(label)
            kind = self.datatypes[label]
            parts = [f"lx:{pid} a wikibase:Property", f"rdfs:label {_lit(label, 'en')}",
                     f"skos:prefLabel {_lit(label, 'en')}", f"schema:name {_lit(label, 'en')}",
                     f"wikibase:propertyType wikibase:{DATATYPES.get(kind, 'String')}",
                     f"wikibase:directClaim lxt:{pid}", f"wikibase:claim lxp:{pid}",
                     f"wikibase:statementProperty lxps:{pid}", f"wikibase:statementValue lxpsv:{pid}",
                     f"wikibase:qualifier lxpq:{pid}", f"wikibase:qualifierValue lxpqv:{pid}",
                     f"wikibase:reference lxpr:{pid}", f"wikibase:referenceValue lxprv:{pid}"]
            if label in self.formatters:
                parts.append(f"wikibase:directClaimNormalized lxn:{pid}")
                parts.append(f"wikibase:statementValueNormalized lxpsn:{pid}")
            if label in self.descriptions:
                parts.append(f"schema:description {_lit(self.descriptions[label], 'en')}")
            self.lines.append(" ;\n    ".join(parts) + " .")
        self.lines.append("")

    def text(self) -> str:
        out = [f"@prefix {p}: <{iri}> ." for p, iri in PREFIXES.items()] + [""]
        out += self.lines
        for node, body in self.values.items():
            out.append(f"{node} {body} .")
        for node, body in self.refs.items():
            out.append(f"{node} {body} .")
        return "\n".join(out) + "\n"


def _kind(datatype: str) -> str:
    d = str(datatype).lower().replace("_", "-")
    return {"wikibase-item": "item", "monolingualtext": "monolingual", "externalid": "external-id",
            "external-id": "external-id"}.get(d, d)


def _properties(sch) -> list[dict]:
    props = getattr(sch, "PROPERTIES", None) or []
    out = []
    for p in (props.values() if isinstance(props, dict) else props):
        if isinstance(p, dict):
            out.append(p)
        else:
            out.append({k: getattr(p, k, None) for k in ("order", "label", "datatype", "wikidata", "description",
                                                          "formatter", "formatter_rdf")})
    return out


def collect_keys(items: Iterable[Item]) -> tuple[set[str], set[str]]:
    """Every item key and item-valued target, and every property label, the Turtle will need ids for."""
    keys, labels = set(), set()
    for it in items:
        keys.add(it.key)
        if getattr(it, "cls", None):
            keys.add(it.cls)
        for c in getattr(it, "claims", None) or []:
            labels.add(c.prop)
            for label, v in _all_values(c):
                labels.add(label)
                if getattr(v, "kind", None) == "item":
                    keys.add(v.value)
                if getattr(v, "kind", None) == "quantity" and getattr(v, "unit", None):
                    keys.add(v.unit)
    return keys, labels


def _all_values(c: Claim):
    yield c.prop, c.value
    for label, v in getattr(c, "qualifiers", None) or []:
        yield label, v
    for ref in getattr(c, "references", None) or []:
        for label, v in ref:
            yield label, v


def write(items: Iterable[Item], path: Path | str | None = None, ids: I.IdMap | None = None) -> Path:
    """Serialise the items as Turtle at ``path`` (default ``data/wikibase/lexipedia.ttl``); assigns and saves the
    provisional ids the file uses."""
    items = list(items)
    idmap = ids or I.default(reload=True)
    keys, labels = collect_keys(items)
    sch = I._schema()
    for p in _properties(sch):
        if p.get("label"):
            labels.add(p["label"])
    for c in I._classes(sch) if sch else []:
        if c.get("key"):
            keys.add(c["key"])
    keys = {k for k in keys if not I._ID.match(k) and k not in idmap.class_labels}
    idmap.assign(keys=keys, labels=labels)
    idmap.save_provisional()
    idmap.save_turtle_map()
    w = Writer(idmap)
    written = set()
    for it in items:
        w.item(it)
        written.add(idmap.qid(it.key))
    for label, qid in sorted(idmap.class_labels.items(), key=lambda kv: int(kv[1][1:])):
        if qid not in written:          # the wiki's own class items, so class labels resolve locally
            w.lines.append(f"lx:{qid} a wikibase:Item ;\n    rdfs:label {_lit(label, 'en')} ;\n"
                           f"    skos:prefLabel {_lit(label, 'en')} .")
    w.lines.append("")
    w.properties()
    out = Path(path) if path else TTL_PATH
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(w.text(), encoding="utf-8")
    return out


# --------------------------------------------------------------------------------------------------- the store
def load(path: Path | str | None = None, store_dir: Path | str | None = None):
    """Load the Turtle at ``path`` into a persisted ``pyoxigraph.Store`` under ``store_dir`` (default
    ``data/wikibase/store/``), replacing what was there, and return it."""
    import pyoxigraph as ox
    src = Path(path) if path else TTL_PATH
    where = Path(store_dir) if store_dir else STORE_DIR
    where.parent.mkdir(parents=True, exist_ok=True)
    store = ox.Store(str(where))
    store.clear()
    store.bulk_load(path=str(src), format=ox.RdfFormat.TURTLE)
    store.flush()
    return store


def memory_store(path: Path | str | None = None):
    """An in-memory store loaded from the Turtle (for tests and for readers that cannot open the shared store)."""
    import pyoxigraph as ox
    src = Path(path) if path else TTL_PATH
    store = ox.Store()
    store.bulk_load(path=str(src), format=ox.RdfFormat.TURTLE)
    return store


_cache: dict[str, Any] = {}


def open_store(store_dir: Path | str | None = None, path: Path | str | None = None):
    """The local store for reading: the persisted one when it is at least as new as the Turtle (opened read-only, so
    an API worker and the CLI can share it), else the Turtle loaded into memory and cached by its modification time."""
    import pyoxigraph as ox
    where = Path(store_dir) if store_dir else STORE_DIR
    src = Path(path) if path else TTL_PATH
    if not src.exists():
        raise FileNotFoundError(f"{src} is missing: run `lexflow sparql --build` first")
    stamp = src.stat().st_mtime
    if where.exists() and where.stat().st_mtime >= stamp - 1:
        try:
            return ox.Store.read_only(str(where))
        except Exception:        # locked by a writer, or an older on-disk format: fall back to memory
            pass
    key = str(src)
    if _cache.get(key, (None, None))[0] != stamp:
        _cache[key] = (stamp, memory_store(src))
    return _cache[key][1]


# ---------------------------------------------------------------------------------------------------- queries
class Rows(list):
    """SPARQL JSON bindings (``{var: {"type": ..., "value": ...}}`` per row) with the column order in ``vars``."""
    vars: list[str] = []
    truncated: bool = False

    def simple(self) -> list[dict[str, str]]:
        return [{k: shorten(b.get("value", "")) if b.get("type") == "uri" else b.get("value", "") for k, b in r.items()}
                for r in self]


def shorten(iri: str) -> str:
    """``https://lexipedia.wikibase.cloud/entity/Q24`` -> ``lx:Q24``; other IRIs unchanged."""
    for p, base in PREFIXES.items():
        if iri.startswith(base) and p in ("lx", "lxt", "lxp", "lxps", "lxpq", "lxpr", "lxn", "wd", "wdt", "wikibase"):
            rest = iri[len(base):]
            if re.match(r"^[A-Za-z0-9_\-]+$", rest):
                return f"{p}:{rest}"
    return iri


_PROJ = re.compile(r"\bSELECT\b\s*(?:DISTINCT|REDUCED)?\s*(.*?)\s*(?:\bWHERE\b|\{)", re.I | re.S)
_PROJ_VAR = re.compile(r"\((?:[^()]|\([^()]*(?:\([^()]*\)[^()]*)*\))*?\s+AS\s+\?(\w+)\s*\)|\?(\w+)", re.I | re.S)


def projection(text: str) -> list[str] | None:
    """The variables a SELECT projects, in order; None for ``SELECT *`` or a non-SELECT query."""
    m = _PROJ.search(_strip_comments(text))
    if not m or m.group(1).strip() == "*":
        return None
    out = []
    for alias, bare in _PROJ_VAR.findall(m.group(1)):
        v = alias or bare
        if v not in out:
            out.append(v)
    return out


def _strip_comments(text: str) -> str:
    return "\n".join(re.sub(r'(?<!["<])#.*$', "", line) for line in text.splitlines())


def _binding(term) -> dict:
    import pyoxigraph as ox
    if isinstance(term, ox.NamedNode):
        return {"type": "uri", "value": term.value}
    if isinstance(term, ox.BlankNode):
        return {"type": "bnode", "value": term.value}
    if isinstance(term, ox.Literal):
        b = {"type": "literal", "value": term.value}
        if term.language:
            b["xml:lang"] = term.language
        elif term.datatype and term.datatype.value != "http://www.w3.org/2001/XMLSchema#string":
            b["datatype"] = term.datatype.value
        return b
    return {"type": "literal", "value": str(term)}


def query(store_or_live, text: str, live: bool = False, timeout: int = 30, limit: int | None = None) -> Rows:
    """Run ``text`` (tokens already expanded) on a local store, or on the public endpoint with ``live=True``.  Rows
    beyond ``limit`` are dropped and ``rows.truncated`` set."""
    import pyoxigraph as ox
    rows = Rows()
    rows.vars = projection(text) or []
    if live:
        I.throttle()
        r = requests.post(ENDPOINT, data={"query": text}, timeout=timeout,
                          headers={"Accept": "application/sparql-results+json", "User-Agent": USER_AGENT})
        if r.status_code >= 400:
            raise RuntimeError(f"the endpoint answered {r.status_code}: {r.text[:600]}")
        data = r.json()
        if "boolean" in data:
            rows.vars = ["result"]
            rows.append({"result": {"type": "literal", "value": str(data["boolean"]).lower()}})
            return rows
        rows.vars = data.get("head", {}).get("vars", rows.vars)
        for i, b in enumerate(data.get("results", {}).get("bindings", [])):
            if limit is not None and i >= limit:
                rows.truncated = True
                break
            rows.append(b)
        return rows
    store = store_or_live
    result = store.query(text)
    if isinstance(result, ox.QueryBoolean):
        rows.vars = ["result"]
        rows.append({"result": {"type": "literal", "value": str(bool(result)).lower()}})
        return rows
    if isinstance(result, ox.QueryTriples):
        rows.vars = ["subject", "predicate", "object"]
        for i, t in enumerate(result):
            if limit is not None and i >= limit:
                rows.truncated = True
                break
            rows.append({"subject": _binding(t.subject), "predicate": _binding(t.predicate), "object": _binding(t.object)})
        return rows
    names = [v.value for v in result.variables]
    if not rows.vars:
        rows.vars = names
    for i, sol in enumerate(result):
        if limit is not None and i >= limit:
            rows.truncated = True
            break
        row = {}
        for v in names:
            term = sol[v]
            if term is not None:
                row[v] = _binding(term)
        rows.append(row)
    return rows


def build(con=None, path: Path | str | None = None, states=None, places=None, drafts: bool = True, log=print) -> dict:
    """Regenerate the Turtle from the database (``graph.build``) and reload the store."""
    from . import graph
    from ..store import db
    own = con is None
    con = con or db.connect()
    try:
        items = graph.build(con, states=states, places=places, drafts=drafts)
    finally:
        if own:
            con.close()
    out = write(items, path)
    log(f"wrote {len(items):,} items to {out}")
    store = load(out)
    n = next(iter(store.query("SELECT (COUNT(*) AS ?n) WHERE { ?s ?p ?o }")))["n"].value
    log(f"loaded {int(n):,} triples into {STORE_DIR}")
    return {"items": len(items), "triples": int(n), "turtle": str(out), "store": str(STORE_DIR)}
