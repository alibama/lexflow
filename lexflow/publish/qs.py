"""QuickStatements batches for Claude in Chrome (docs/design/wikibase-schema.md section 5).

Claude Code cannot sign in to Wikibase Cloud, so every write to https://lexipedia.wikibase.cloud goes through
QuickStatements batches that Claude in Chrome pastes while signed in as the operator.  This module writes those
batches to ``out/wikibase/`` from ``lexflow.publish.schema`` (the one table of classes and properties) and
``lexflow.publish.graph`` (the items and claims built from lexflow's database), resolves the ids the batches
created through the public read API, and checks coverage against the live SPARQL endpoint.  It never writes to the
wiki.

    python -m lexflow.publish.qs write              pass 1: 01-properties.qs, 02-classes.qs, 03-items-<kind>.qs,
                                                    README.md, check.rq
    python -m lexflow.publish.qs --resolve          ids.json: every property label -> P-id, every item key -> Q-id
    python -m lexflow.publish.qs write --pass 2     04-claims-<kind>.qs, 05-updates.qs (needs ids.json)
    python -m lexflow.publish.qs --check            coverage.rq against the live endpoint vs the generated counts

The same three run as ``lexflow qs write|resolve|check``.

**QuickStatements V1 rules this module follows** (read from the parser, ``importDataFromV1`` and
``parseValueV1`` in quickstatements.php):

* commands are tab-separated; a row with no tab has its ``|`` turned into tabs, so a comment line never holds one;
* a row that is only ``/* ... */`` yields no command, so each file starts with such a header;
* ``CREATE`` then ``LAST<TAB>Len<TAB>"label"`` (exactly three columns; one ``Aen`` line per alias: ``|``-joined
  aliases are not a V1 form);
* ``CREATE_PROPERTY<TAB><datatype>`` with Wikibase's datatype ids (``wikibase-item``, ``monolingualtext``, ...);
* a statement is ``<id><TAB>P<n><TAB><value>`` followed by ``P<n><TAB><value>`` pairs (qualifiers) and
  ``S<n><TAB><value>`` pairs (one reference group per line, so a claim with several references repeats the claim,
  one line per reference);
* strings are ``"..."``: the parser takes everything between the first and the last quote, so an inner quote passes
  as it is and a backslash would be stored literally; tabs and newlines cannot appear (they are turned into spaces
  here) and ``/*`` or ``*/`` inside a value would be read as a summary (they are broken up here);
* time is ``+YYYY-MM-DDT00:00:00Z/<precision>``, quantity ``5`` or ``75U<numeric id of the unit item>`` (the unit is
  the number only: ``U12``, not ``UQ12``), monolingual text ``en:"..."``, URL and external-id a quoted string;
* Wikibase's string limits: labels, descriptions and aliases 250 characters, strings and monolingual text 400,
  URLs 500.

Items of pass 1 carry only label, description, aliases and ``P25 legal identifier`` (the key); nothing in a pass-1
file refers to a new item, which is why pass 2 exists.  ``ids.json`` between the passes is the only state.
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
import time
from collections import Counter, OrderedDict
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .. import config

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "out" / "wikibase"
SPARQL_DIR = Path(__file__).resolve().parent / "sparql"

SITE = config.WIKIBASE_URL.rstrip("/")
API = SITE + "/w/api.php"
SPARQL_ENDPOINT = SITE + "/query/sparql"
QUICKSTATEMENTS_URL = SITE + "/tools/quickstatements/#/batch"
USER_AGENT = "lexflow-research/0.1"
MIN_INTERVAL = 1.0          # seconds between requests to the public API and the SPARQL endpoint

MAX_LINES = 2000            # a QuickStatements batch, header included
MAX_LABEL = 250             # labels, descriptions, aliases
MAX_STRING = 400            # strings, monolingual text, external ids
MAX_URL = 500

KEY_PROPERTY = "P25"        # legal identifier = the lexflow key
INSTANCE_OF = "P5"
SUBCLASS_OF = "P6"
EQUIVALENT_PROPERTY = "P7"
EXACT_MATCH = "P8"
LANG = "en"

PREFIXES = {
    "lx": SITE + "/entity/", "lxt": SITE + "/prop/direct/", "lxp": SITE + "/prop/", "lxps": SITE + "/prop/statement/",
    "lxpq": SITE + "/prop/qualifier/", "lxpr": SITE + "/prop/reference/",
}
SPARQL_PREFIXES = "\n".join(f"PREFIX {k}: <{v}>" for k, v in PREFIXES.items()) + (
    "\nPREFIX wikibase: <http://wikiba.se/ontology#>\nPREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n"
    "PREFIX schema: <http://schema.org/>\nPREFIX skos: <http://www.w3.org/2004/02/skos/core#>\n")

# QuickStatements datatype ids (wikibase.php's list) from the shorter names the schema table uses
DATATYPES = {"item": "wikibase-item", "wikibase-item": "wikibase-item", "property": "wikibase-property",
             "wikibase-property": "wikibase-property", "string": "string", "url": "url", "external-id": "external-id",
             "externalid": "external-id", "time": "time", "quantity": "quantity", "monolingual": "monolingualtext",
             "monolingualtext": "monolingualtext"}

ENTITY_ID = re.compile(r"^[PQ]\d+$")
QID = re.compile(r"^Q\d+$")
PID = re.compile(r"^P\d+$")
_WS = re.compile(r"[\s  ]+")


class QSError(ValueError):
    pass


class Unresolved(QSError):
    """A value whose item, unit or property has no id yet (the claim is skipped and listed)."""


# ----------------------------------------------------------------------------------------------- record access
def _get(obj: Any, name: str, default: Any = None) -> Any:
    """A field of a dataclass, namedtuple, object or dict (the schema and graph records may be any of these)."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _records(table: Any) -> list:
    """The records of a schema table, whether it is a list or a dict keyed by slug or label."""
    if table is None:
        return []
    if isinstance(table, dict):
        return list(table.values())
    return list(table)


def _first(obj: Any, *names: str, default: Any = None) -> Any:
    for n in names:
        v = _get(obj, n)
        if v not in (None, ""):
            return v
    return default


# ----------------------------------------------------------------------------------------------- text and values
def clean_text(text: Any) -> str:
    """One line of text QuickStatements can carry: whitespace (tabs and newlines included) collapsed to spaces,
    comment delimiters broken up, stripped."""
    s = _WS.sub(" ", str(text if text is not None else "")).strip()
    return s.replace("/*", "/ *").replace("*/", "* /")


def fit(text: str, limit: int) -> str:
    """``text`` within ``limit`` characters, cut at a word with an ellipsis when longer."""
    if len(text) <= limit:
        return text
    cut = text[:limit - 1].rstrip()
    if " " in cut[limit // 2:]:
        cut = cut[:cut.rfind(" ")].rstrip()
    return cut + "…"


def qs_string(text: Any, limit: int = MAX_STRING) -> str:
    """A quoted V1 string.  Inner quotes stay as they are (the parser takes everything between the first and the
    last quote; there is no escape), so only the outer quotes are added."""
    return '"' + fit(clean_text(text), limit) + '"'


def qs_time(value: Any, precision: int | None = None) -> str:
    """``+YYYY-MM-DDT00:00:00Z/<precision>`` from a date, datetime, or a ``YYYY``, ``YYYY-MM``, ``YYYY-MM-DD`` or
    ISO timestamp string.  Precision defaults to the granularity given (9 year, 10 month, 11 day)."""
    if isinstance(value, (date, datetime)):
        y, m, d, prec = value.year, value.month, value.day, 11
    else:
        s = clean_text(value)
        mt = re.match(r"^([+-]?)(\d{4})(?:-(\d{2})(?:-(\d{2}))?)?(?:[T ].*)?$", s)
        if not mt:
            raise QSError(f"not a date: {value!r}")
        y = int(mt.group(2))
        m = int(mt.group(3) or 0)
        d = int(mt.group(4) or 0)
        prec = 11 if d else 10 if m else 9
        if (m and not 1 <= m <= 12) or (d and not 1 <= d <= 31):
            raise QSError(f"not a date: {value!r}")
        if mt.group(1) == "-":
            y = -y
    prec = int(precision) if precision else prec
    if prec not in (9, 10, 11):
        raise QSError(f"unsupported time precision {prec}")
    if prec < 11:
        d = 0
    if prec < 10:
        m = 0
    return f"{'-' if y < 0 else '+'}{abs(y):04d}-{m:02d}-{d:02d}T00:00:00Z/{prec}"


def qs_quantity(value: Any, unit_qid: str | None = None) -> str:
    """``5``, ``75.50`` or ``75U<n>`` with the unit item's numeric id."""
    s = clean_text(value).replace(",", "").replace("$", "").replace("USD", "").strip()
    if not re.fullmatch(r"[+-]?\d+(\.\d+)?", s):
        raise QSError(f"not a quantity: {value!r}")
    if unit_qid:
        if not QID.match(unit_qid):
            raise QSError(f"unit is not an item id: {unit_qid!r}")
        return f"{s}U{unit_qid[1:]}"
    return s


def qs_monolingual(text: Any, lang: str | None = None) -> str:
    lang = (lang or LANG).lower()
    if not re.fullmatch(r"[a-z_-]+", lang):
        raise QSError(f"bad language code {lang!r}")
    return f"{lang}:{qs_string(text, MAX_STRING)}"


def qs_url(url: Any) -> str:
    """A quoted URL.  A ``mailto:`` address is written only when it is an office mailbox (``privacy.py``); a
    personal-looking one raises, so the claim is skipped and listed."""
    s = clean_text(url).replace(" ", "%20")
    if len(s) > MAX_URL:
        raise QSError(f"URL over {MAX_URL} characters: {s[:60]}...")
    if s.lower().startswith("mailto:"):
        from .. import privacy
        if not privacy.is_office_mailbox(s[7:]):
            raise QSError("mailbox is not an office mailbox (lexflow.privacy)")
    elif "@" in s:
        raise QSError("a URL with an e-mail address is not written")
    return '"' + s + '"'


def no_reprint(url: Any) -> bool:
    """Whether a page's words may not be reposted (``lexflow.municipal.quotes.NO_REPRINT``)."""
    from ..municipal import quotes
    return quotes.policy(str(url or "")) is not None


# ----------------------------------------------------------------------------------------------- ids
@dataclass
class Ids:
    """The ids ``--resolve`` wrote (``ids.json``) plus the schema's existing ids, with lookups by key or label."""
    properties: dict[str, str] = field(default_factory=dict)      # property label -> P-id
    items: dict[str, str] = field(default_factory=dict)           # item key -> Q-id
    labels: dict[str, str] = field(default_factory=dict)          # existing item label -> Q-id (classes, vocab)
    unresolved: dict[str, list[str]] = field(default_factory=lambda: {"properties": [], "items": []})
    methods: dict[str, str] = field(default_factory=dict)         # key -> how it was resolved

    def prop(self, label_or_id: str) -> str:
        if PID.match(label_or_id or ""):
            return label_or_id
        pid = self.properties.get(label_or_id)
        if not pid:
            raise Unresolved(f"property {label_or_id!r}")
        return pid

    def item(self, key_or_id: str) -> str:
        if QID.match(key_or_id or ""):
            return key_or_id
        qid = self.items.get(key_or_id) or self.labels.get(key_or_id)
        if not qid:
            raise Unresolved(f"item {key_or_id!r}")
        return qid

    def has_item(self, key_or_id: str) -> bool:
        try:
            self.item(key_or_id)
            return True
        except Unresolved:
            return False

    @classmethod
    def load(cls, path: Path, schema=None) -> "Ids":
        ids = cls()
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            ids.properties.update(data.get("properties") or {})
            ids.items.update(data.get("items") or {})
            ids.labels.update(data.get("labels") or {})
            ids.unresolved = data.get("unresolved") or ids.unresolved
            ids.methods = data.get("methods") or {}
        if schema is not None:
            ids.add_schema(schema)
        return ids

    def add_schema(self, schema) -> None:
        """The ids the schema already knows: ``EXISTING`` (label -> id for the live properties and class items) and
        the ``qid`` of any class record that is live."""
        for label, eid in (getattr(schema, "EXISTING", None) or {}).items():
            if PID.match(eid):
                self.properties.setdefault(label, eid)
            elif QID.match(eid):
                self.labels.setdefault(label, eid)
        for c in _records(getattr(schema, "CLASSES", None)):
            qid = _first(c, "qid", "id")
            if qid and QID.match(str(qid)):
                self.items.setdefault(class_key(c), qid)
                self.labels.setdefault(_get(c, "label"), qid)
        for p in _records(getattr(schema, "PROPERTIES", None)):
            pid = _first(p, "pid", "id")
            if pid and PID.match(str(pid)):
                self.properties.setdefault(_get(p, "label"), pid)

    def dump(self) -> dict:
        return {"site": SITE, "generated": _now(), "properties": dict(sorted(self.properties.items())),
                "items": dict(sorted(self.items.items())), "labels": dict(sorted(self.labels.items())),
                "unresolved": self.unresolved, "methods": self.methods}


def class_key(c: Any) -> str:
    key = _get(c, "key")
    if key:
        return key
    slug = _first(c, "slug", "key_slug")
    return f"lexflow:class:{slug}" if slug else f"lexflow:class:{_get(c, 'label')}"


# ----------------------------------------------------------------------------------------------- value formatting
def format_value(value: Any, ids: Ids) -> str:
    """One V1 value from a ``Value(kind, value, unit, lang, precision)`` record.  Raises ``Unresolved`` when an item
    or unit has no id yet."""
    kind = (_get(value, "kind") or "string").lower()
    v = _get(value, "value")
    if kind == "item":
        return ids.item(str(v))
    if kind == "string":
        return qs_string(v)
    if kind in ("external-id", "externalid"):
        return qs_string(v)
    if kind == "url":
        return qs_url(v)
    if kind == "time":
        return qs_time(v, _get(value, "precision"))
    if kind == "quantity":
        unit = _get(value, "unit")
        return qs_quantity(v, ids.item(str(unit)) if unit else None)
    if kind in ("monolingual", "monolingualtext"):
        return qs_monolingual(v, _get(value, "lang"))
    if kind in ("novalue", "somevalue"):
        return kind
    raise QSError(f"unknown value kind {kind!r}")


def _pairs(pairs: Iterable, ids: Ids, prefix: str) -> list[str]:
    pairs = list(pairs or [])
    if prefix == "S" and any(lbl == "source URL" and no_reprint(_get(val, "value")) for lbl, val in pairs):
        pairs = [(lbl, val) for lbl, val in pairs if lbl != "quoted text"]      # the site's words stay off the wiki
    out = []
    for label, val in pairs:
        pid = ids.prop(label)
        out += [prefix + pid[1:], format_value(val, ids)]
    return out


def claim_lines(subject: str, claim: Any, ids: Ids) -> list[str]:
    """The V1 lines of one claim: the statement with its qualifiers and first reference, then one line per further
    reference (QuickStatements adds a reference to a statement it finds already present)."""
    pid = ids.prop(_get(claim, "prop"))
    base = [subject, pid, format_value(_get(claim, "value"), ids)]
    quals = _pairs(_get(claim, "qualifiers") or [], ids, "P")
    refs = [_pairs(r, ids, "S") for r in (_get(claim, "references") or []) if r]
    lines = ["\t".join(base + quals + (refs[0] if refs else []))]
    for r in refs[1:]:
        lines.append("\t".join(base + r))
    return lines


# ----------------------------------------------------------------------------------------------- batches
@dataclass
class Batch:
    name: str                      # file stem without the part suffix, e.g. "03-items-agencies"
    pass_no: int
    groups: list[list[str]] = field(default_factory=list)       # lines that must stay in one file
    skipped: list[str] = field(default_factory=list)            # claims left out, with the reason
    notes: list[str] = field(default_factory=list)

    def add(self, lines: list[str]) -> None:
        if lines:
            self.groups.append(lines)

    @property
    def lines(self) -> list[str]:
        return [l for g in self.groups for l in g]


def command_counts(lines: Iterable[str]) -> Counter:
    """Counts by command type as QuickStatements will show them: ``CREATE``, ``CREATE_PROPERTY``, ``Len``, ``Den``,
    ``Aen``, ``statement``, ``qualifier`` and ``reference`` (a run of S-pairs on one line is one reference), plus
    ``commands``: the number QuickStatements' preview reports."""
    c: Counter = Counter()
    for line in lines:
        if line.startswith("/*") or not line.strip():
            continue
        cols = line.split("\t")
        first = cols[0]
        if first in ("CREATE", "CREATE_PROPERTY"):
            c[first] += 1
            c["commands"] += 1
        elif len(cols) == 3 and re.fullmatch(r"[LDA][a-z_-]+", cols[1]):
            c[cols[1]] += 1
            c["commands"] += 1
        else:
            c["statement"] += 1
            c["commands"] += 1
            rest = cols[3:]
            in_ref = False
            for i in range(0, len(rest) - 1, 2):
                k = rest[i]
                if k.startswith("S") or k.startswith("!S"):
                    if not in_ref or k.startswith("!S"):
                        c["reference"] += 1
                        c["commands"] += 1
                    in_ref = True
                else:
                    c["qualifier"] += 1
                    c["commands"] += 1
                    in_ref = False
    return c


def header(name: str, pass_no: int, counts: Counter, commit: str, part: str | None = None, parts: int = 1,
           skipped: list[str] | None = None, notes: list[str] | None = None) -> list[str]:
    """The comment header every batch starts with: the pass, the counts by command type, the git commit."""
    order = ["CREATE_PROPERTY", "CREATE", "Len", "Den", "Aen", "statement", "qualifier", "reference"]
    shown = [f"{k} {counts[k]}" for k in order if counts.get(k)]
    for k in sorted(counts):
        if k not in order and k != "commands":
            shown.append(f"{k} {counts[k]}")
    lines = [f"/* lexflow QuickStatements batch {name}.qs" + (f", part {part} of {parts}" if part else "") + " */",
             f"/* pass {pass_no}; QuickStatements preview must show {counts.get('commands', 0)} commands */",
             "/* counts: " + ("; ".join(shown) if shown else "none") + " */",
             f"/* generated {_now()} from lexflow commit {commit} by lexflow.publish.qs */"]
    for n in notes or []:
        lines.append(f"/* {clean_text(n).replace('|', '/')} */")
    if skipped:
        lines.append(f"/* skipped {len(skipped)} claims whose target or subject has no id yet: */")
        for s in skipped[:200]:
            lines.append(f"/* skipped: {clean_text(s).replace('|', '/')} */")
        if len(skipped) > 200:
            lines.append(f"/* ... and {len(skipped) - 200} more; see the generation log */")
    return lines


def split_groups(groups: list[list[str]], limit: int) -> list[list[list[str]]]:
    """Consecutive runs of groups whose line total stays within ``limit``; a group longer than the limit stands
    alone."""
    parts: list[list[list[str]]] = [[]]
    size = 0
    for g in groups:
        if size and size + len(g) > limit:
            parts.append([])
            size = 0
        parts[-1].append(g)
        size += len(g)
    return [p for p in parts if p]


def part_suffix(i: int) -> str:
    """``a``..``z``, then ``aa``, ``ab``..."""
    s = ""
    i += 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(97 + r) + s
    return s


def render(batch: Batch, commit: str) -> list[tuple[str, str]]:
    """``(file name, text)`` pairs: one file, or ``-a``, ``-b``... parts when the batch exceeds ``MAX_LINES``."""
    header_len = 4 + len(batch.notes) + (min(len(batch.skipped), 200) + 1 + (1 if len(batch.skipped) > 200 else 0)
                                         if batch.skipped else 0)
    parts = split_groups(batch.groups, MAX_LINES - header_len) or [[]]
    out = []
    for i, part in enumerate(parts):
        lines = [l for g in part for l in g]
        suffix = f"-{part_suffix(i)}" if len(parts) > 1 else ""
        head = header(batch.name + suffix, batch.pass_no, command_counts(lines), commit,
                      part_suffix(i) if len(parts) > 1 else None, len(parts), batch.skipped, batch.notes)
        out.append((batch.name + suffix + ".qs", "\n".join(head + lines) + "\n"))
    return out


# ----------------------------------------------------------------------------------------------- pass 1
def _label_lines(item: Any, subject: str = "LAST") -> list[str]:
    lines = [f"{subject}\tL{LANG}\t{qs_string(_get(item, 'label'), MAX_LABEL)}"]
    desc = clean_text(_get(item, "description") or "")
    if desc:
        lines.append(f"{subject}\tD{LANG}\t{qs_string(desc, MAX_LABEL)}")
    seen = {clean_text(_get(item, "label"))}
    for a in _get(item, "aliases") or []:
        a = clean_text(a)
        if a and a not in seen:
            seen.add(a)
            lines.append(f"{subject}\tA{LANG}\t{qs_string(a, MAX_LABEL)}")
    return lines


def create_lines(item: Any, ids: Ids | None = None, with_class: bool = False) -> list[str]:
    """``CREATE`` and the ``LAST`` lines of one new item: label, description, one line per alias, the key.  With
    ``with_class`` (02-classes.qs) also ``P5``/``P6`` when the target is already live."""
    lines = ["CREATE"] + _label_lines(item)
    lines.append(f"LAST\t{KEY_PROPERTY}\t{qs_string(_get(item, 'key'), MAX_STRING)}")
    if with_class and ids is not None:
        for prop, target in class_edges(item):
            if target and ids.has_item(target):
                lines.append(f"LAST\t{prop}\t{ids.item(target)}")
        wd = _get(item, "wikidata")
        if wd and QID.match(str(wd)):
            lines.append(f"LAST\t{EXACT_MATCH}\t{qs_url('http://www.wikidata.org/entity/' + wd)}")
        for iri in _get(item, "exact") or ():
            lines.append(f"LAST\t{EXACT_MATCH}\t{qs_url(iri)}")
        # close match (property 60) is a new property: its lines wait for pass 2 (schema_items' claims)
    return lines


def class_edges(item: Any) -> list[tuple[str, str | None]]:
    """The ``(P5, cls)`` and, for class records, ``(P6, subclass_of)`` edges an item carries by construction."""
    edges = [(INSTANCE_OF, _get(item, "cls"))]
    sup = _get(item, "subclass_of")
    if sup:
        edges.append((SUBCLASS_OF, sup))
    return edges


def properties_batch(schema) -> Batch:
    """01-properties.qs: ``CREATE_PROPERTY`` for every new property of section 3, with label, description, and
    ``P7 equivalent property`` / formatter claims on ``LAST``."""
    b = Batch("01-properties", 1)
    existing = Ids()
    existing.add_schema(schema)
    props = sorted(_records(getattr(schema, "PROPERTIES")), key=lambda p: _first(p, "order", "number", default=0))
    for p in props:
        label = _get(p, "label")
        if label in existing.properties:
            continue                                   # P1-P25: reused unchanged
        dt = DATATYPES.get(str(_get(p, "datatype", "string")).lower())
        if not dt:
            raise QSError(f"property {label!r}: unknown datatype {_get(p, 'datatype')!r}")
        lines = [f"CREATE_PROPERTY\t{dt}", f"LAST\tL{LANG}\t{qs_string(label, MAX_LABEL)}"]
        desc = clean_text(_get(p, "description") or "")
        if desc:
            lines.append(f"LAST\tD{LANG}\t{qs_string(desc, MAX_LABEL)}")
        for a in _get(p, "aliases") or []:
            lines.append(f"LAST\tA{LANG}\t{qs_string(a, MAX_LABEL)}")
        wd = _get(p, "wikidata")
        if wd and re.fullmatch(r"P\d+", str(wd)):
            lines.append(f"LAST\t{EQUIVALENT_PROPERTY}\t{qs_url('http://www.wikidata.org/entity/' + wd)}")
        for iri in _get(p, "equivalents") or ():
            lines.append(f"LAST\t{EQUIVALENT_PROPERTY}\t{qs_url(iri)}")
        b.add(lines)
    # formatter URL / formatter URI for RDF resource are new properties themselves: their ids are unknown in
    # pass 1, so the formatter claims go to 05-updates.qs in pass 2 (see updates_for_properties)
    return b


def updates_for_properties(schema, ids: Ids) -> tuple[list[list[str]], list[str]]:
    """Pass 2: the formatter claims on the property items (``formatter URL`` and ``formatter URI for RDF resource``
    are themselves new properties) and the ``P7 equivalent property`` ontology IRIs of the existing properties
    (``schema.EXISTING_EQUIVALENTS``; the new properties carry theirs from 01-properties.qs)."""
    groups, skipped = [], []
    for label, iris in (getattr(schema, "EXISTING_EQUIVALENTS", None) or {}).items():
        for iri in iris:
            try:
                groups.append([f"{ids.prop(label)}\t{EQUIVALENT_PROPERTY}\t{qs_url(iri)}"])
            except Unresolved as e:
                skipped.append(f"{label} equivalent property: {e}")
    for p in _records(getattr(schema, "PROPERTIES")):
        label = _get(p, "label")
        for fprop, attrs in (("formatter URL", ("formatter", "formatter_url")),
                             ("formatter URI for RDF resource", ("formatter_rdf", "formatter_uri_rdf"))):
            tpl = _first(p, *attrs)
            if not tpl:
                continue
            try:
                groups.append([f"{ids.prop(label)}\t{ids.prop(fprop)}\t{qs_string(tpl)}"])
            except Unresolved as e:
                skipped.append(f"{label} {fprop}: {e}")
    return groups, skipped


def classes_batch(schema, class_items: list[Any]) -> Batch:
    """02-classes.qs: the class items of section 2 then the vocabulary items, each with label, description, key,
    and ``P5``/``P6`` only when the target already has a live id."""
    b = Batch("02-classes", 1)
    ids = Ids()
    ids.add_schema(schema)
    for it in class_items:
        if _get(it, "exists") or ids.has_item(_get(it, "key")):
            continue
        b.add(create_lines(it, ids, with_class=True))
    return b


def schema_items(schema) -> list[Any]:
    """Class and vocabulary records of the schema as pass-1 items (classes first, since vocabularies point at
    them)."""
    out = []
    for c in _records(getattr(schema, "CLASSES", None)):
        qid = _first(c, "qid", "id")
        sup = _get(c, "subclass_of")
        if sup and ":" not in sup:
            sup = f"lexflow:class:{sup}"                      # a slug: the parent class's key
        out.append(PlainItem(key=class_key(c), label=_get(c, "label"), description=_get(c, "description") or "",
                             aliases=list(_get(c, "aliases") or []), cls=None, subclass_of=sup, exists=bool(qid),
                             kind="class", wikidata=_get(c, "wikidata"), exact=tuple(_get(c, "exact") or ()),
                             close=tuple(_get(c, "close") or ()),
                             claims=[PlainClaim("close match", PlainValue("url", iri)) for iri in _get(c, "close") or ()]))
    for set_name, v in vocab_records(schema):
        key = _get(v, "key") or f"lexflow:vocab:{set_name}:{_get(v, 'slug')}"
        cls = _first(v, "cls", "class", "vocabulary") or f"lexflow:class:{set_name}"
        out.append(PlainItem(key=key, label=_get(v, "label"), description=_get(v, "description") or "",
                             aliases=list(_get(v, "aliases") or []), cls=cls, exists=bool(_get(v, "qid")),
                             kind="vocab"))
    return out


def vocab_records(schema) -> list[tuple[str, Any]]:
    """``(set, record)`` pairs from ``schema.VOCAB``: a dict of set -> records, or a flat list whose records carry
    ``set``."""
    table = getattr(schema, "VOCAB", None)
    out = []
    if isinstance(table, dict):
        for set_name, vs in table.items():
            if isinstance(vs, (list, tuple)):
                out += [(set_name, v) for v in vs]
            else:
                out.append((_get(vs, "set") or set_name, vs))
    else:
        out = [(_get(v, "set"), v) for v in table or []]
    return out


@dataclass
class PlainItem:
    """The item shape this module reads (``graph.Item`` has the same fields; this one is for the schema's class
    and vocabulary records)."""
    key: str
    label: str
    description: str = ""
    aliases: list = field(default_factory=list)
    cls: str | None = None
    claims: list = field(default_factory=list)
    exists: bool = False
    kind: str = ""
    subclass_of: str | None = None
    wikidata: str | None = None
    exact: tuple = ()                 # P8 exact match IRIs (ontology_map.CLASS_MATCH), written in pass 1
    close: tuple = ()                 # close match IRIs (ontology_map.CLASS_CLOSE), written as claims in pass 2


@dataclass
class PlainValue:
    kind: str
    value: str
    unit: str | None = None
    lang: str | None = None
    precision: int | None = None


@dataclass
class PlainClaim:
    prop: str
    value: PlainValue
    qualifiers: list = field(default_factory=list)
    references: list = field(default_factory=list)


def merge_schema_items(class_items: list[PlainItem], items: list[Any]) -> list[PlainItem]:
    """The schema's class and vocabulary items with the claims the graph gives the same keys (the graph may carry
    ``P8 exact match`` or descriptions of its own for them)."""
    by_key = {_get(it, "key"): it for it in items if is_schema_item(it)}
    out = []
    for ci in class_items:
        g = by_key.get(ci.key)
        if g is not None:
            ci = PlainItem(key=ci.key, label=_get(g, "label") or ci.label, description=_get(g, "description") or
                           ci.description, aliases=list(_get(g, "aliases") or ci.aliases), cls=ci.cls or _get(g, "cls"),
                           claims=list(_get(g, "claims") or []), exists=bool(ci.exists or _get(g, "exists")),
                           kind=ci.kind, subclass_of=ci.subclass_of, wikidata=ci.wikidata, exact=ci.exact,
                           close=ci.close)
        out.append(ci)
    return out


def is_schema_item(item: Any) -> bool:
    k = _get(item, "key") or ""
    return k.startswith("lexflow:class:") or k.startswith("lexflow:vocab:")


def items_batches(by_kind: "OrderedDict[str, list]") -> list[Batch]:
    """03-items-<kind>.qs: every new item of section 4 with label, description, aliases and key."""
    out = []
    for kind, items in by_kind.items():
        b = Batch(f"03-items-{slug(kind)}", 1)
        for it in items:
            if _get(it, "exists") or is_schema_item(it):
                continue
            b.add(create_lines(it))
        if b.groups:
            out.append(b)
    return out


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-") or "items"


# ----------------------------------------------------------------------------------------------- pass 2
def item_claim_groups(item: Any, ids: Ids, live1: Ids | None = None) -> tuple[list[list[str]], list[str]]:
    """Every claim of one item as V1 line groups, with the ``P5`` (and ``P6``) edge first.  ``live1`` (the ids the
    schema knew in pass 1) marks the class edges 02-classes.qs wrote already.  Returns the groups and the skipped
    claims (an unresolved subject skips the whole item)."""
    key = _get(item, "key")
    try:
        subject = ids.item(key)
    except Unresolved:
        n = 1 + len(_get(item, "claims") or [])
        return [], [f"{key}: subject has no id ({n} claims)"]
    groups, skipped = [], []
    for prop, target in ([] if _get(item, "exists") else class_edges(item)):
        if not target:
            continue
        if live1 is not None and live1.has_item(target):
            continue                                   # written in 02-classes.qs already (target was live)
        try:
            groups.append([f"{subject}\t{prop}\t{ids.item(target)}"])
        except Unresolved as e:
            skipped.append(f"{key} {prop}: {e}")
    for c in _get(item, "claims") or []:
        try:
            groups.append(claim_lines(subject, c, ids))
        except Unresolved as e:
            skipped.append(f"{key} {_get(c, 'prop')}: {e}")
        except QSError as e:
            skipped.append(f"{key} {_get(c, 'prop')}: {e}")
    return groups, skipped


def claims_batches(by_kind: "OrderedDict[str, list]", ids: Ids, schema=None,
                   class_items: list | None = None) -> tuple[list[Batch], Batch]:
    """04-claims-<kind>.qs for the new items and 05-updates.qs for the items that already existed (and the
    property formatters)."""
    out = []
    updates = Batch("05-updates", 2)
    if schema is not None:
        groups, skipped = updates_for_properties(schema, ids)
        for g in groups:
            updates.add(g)
        updates.skipped += skipped
    if class_items:
        live1 = Ids()
        if schema is not None:
            live1.add_schema(schema)
        b = Batch("04-claims-classes", 2)
        for it in class_items:
            groups, skipped = item_claim_groups(it, ids, live1)
            target = updates if _get(it, "exists") else b
            for g in groups:
                target.add(g)
            target.skipped += skipped
        if b.groups:
            out.append(b)
    for kind, items in by_kind.items():
        b = Batch(f"04-claims-{slug(kind)}", 2)
        for it in items:
            if is_schema_item(it) and class_items:
                continue
            groups, skipped = item_claim_groups(it, ids)
            target = updates if _get(it, "exists") else b
            for g in groups:
                target.add(g)
            target.skipped += skipped
        if b.groups or b.skipped:
            out.append(b)
    return out, updates


# ----------------------------------------------------------------------------------------------- README, check.rq
def readme(files: list[tuple[str, Counter]], pass_no: int, commit: str, unresolved: int = 0) -> str:
    """The instructions for Claude in Chrome (section 5.1), with this run's files and their preview counts."""
    files = sorted(files)
    rows = "\n".join(f"| `{name}` | {c.get('commands', 0)} | {c.get('CREATE_PROPERTY', 0) + c.get('CREATE', 0)} "
                     f"| {c.get('statement', 0)} |" for name, c in files)
    p1 = [n for n, _ in files if n[:2] in ("01", "02", "03")]
    p2 = [n for n, _ in files if n[:2] in ("04", "05")]
    first_count = next((c.get("commands", 0) for n, c in files if n.startswith("01-")), 0)
    first_creates = next((c.get("CREATE_PROPERTY", 0) for n, c in files if n.startswith("01-")), 0)
    text = f"""# Lexipedia QuickStatements packet (for Claude in Chrome)

Generated {_now()} from lexflow commit `{commit}` by `python -m lexflow.publish.qs` (pass {pass_no} files present).
The contract is `docs/design/wikibase-schema.md` section 5.  Nothing here deletes, merges or relabels anything.

## Files in this packet

| File | Commands the preview must show | Creations (CREATE / CREATE_PROPERTY) | Statements |
|---|---|---|---|
{rows}

Every `.qs` file starts with `/* ... */` comment lines that repeat these numbers.  QuickStatements ignores those
lines.  A file with a `-a`, `-b` suffix is one batch split in parts: run the parts in letter order.

## Steps

1. The operator signs in at https://lexipedia.wikibase.cloud with their own account before you start.  You never
   type, see or ask for the password.  If a page asks you to sign in, stop and tell the operator.
2. Open https://lexipedia.wikibase.cloud/tools/quickstatements/#/batch in a tab.  If it shows "Not logged in",
   click "Log in" (OAuth with the operator's wiki account), then come back to the same URL.
3. Pass 1 files, in name order: {", ".join(f"`{n}`" for n in p1) or "(none yet)"}.
   For each file:
   a. Read the file's header comment and note the number after "preview must show".
   b. Click "New batch" if the page does not already show the empty command box.
   c. Paste the whole file (header lines included) into the command box and press "Import V1 commands" (never
      "Import CSV commands").
   d. The preview must show exactly that number of commands and, for `01-properties.qs`, {first_creates}
      `CREATE_PROPERTY` rows ({first_count} commands in all) and nothing that is not a property creation,
      label, description, alias or `P7` claim.  For the `02-` and `03-` files every row is `CREATE`, a label,
      description, alias or `P25` (the key), a `P8` Wikidata link, or a `P5`/`P6` to an item that already
      exists.  If the count differs
      or a row shows an error such as "Unknown V1 value format", do not run it: stop and paste the file name and
      the error rows back to Claude Code.
   e. Press "Run in background" (not "Run"), one batch at a time; wait until the batch page shows every command
      done before pasting the next file.  Note the P-ids that `01-properties.qs` created, but do not retype them:
      Claude Code reads them from the wiki.
4. Tell Claude Code "pass 1 is done".  It runs `python -m lexflow.publish.qs --resolve` (reads only) and then
   `write --pass 2`, which writes the `04-*.qs` and `05-*.qs` files into this folder.
5. Pass 2 files, in name order: {", ".join(f"`{n}`" for n in p2) or "(written after pass 1)"}.  Paste each the same
   way (steps 3a-3e).  Every row is a statement, qualifier or reference on an existing Q or P id; no `CREATE` rows.
   The header of each file lists the claims that were skipped because an id was still missing; that is expected
   and is not an error.
6. Tell Claude Code "pass 2 is done".  It runs `python -m lexflow.publish.qs --check`, the coverage query against
   the live endpoint, and reports what is missing.
7. Never: delete an item, merge items, edit `Project:` pages, change a label by hand, run a batch whose preview
   count differs from the file's header, or paste a file twice.  If QuickStatements shows errors on any row, stop
   there and paste the error rows (with the file name) back to Claude Code; do not retry or edit the file.

## Before pass 1: the wiki pages the hosting policy needs

Wikibase Cloud's hosting policy needs `Project:Copyrights` to say the structured data is CC0 and `Project:People`
to state the rule that the wiki holds organisations and office channels only (no office holders, staff names,
personal mailboxes or direct lines).  These are wiki pages, not QuickStatements; the operator writes them by hand
and tells you when they are in place.  If either page is missing, say so before running the first batch.
"""
    if unresolved:
        text += (f"\nNote: {unresolved} items or properties had no id when the pass 2 files were written; their "
                 "claims are listed in the file headers and will be written on the next pass 2 run.\n")
    return text


COVERAGE_QUERY = SPARQL_PREFIXES + """
# coverage: items by class, with their review status where one is stated
SELECT ?class ?classLabel ?status ?statusLabel (COUNT(DISTINCT ?item) AS ?n) WHERE {
  ?item lxt:P5 ?class .
  ?class rdfs:label ?classLabel . FILTER(LANG(?classLabel) = "en")
  OPTIONAL { ?item lxt:{P:review status} ?status . ?status rdfs:label ?statusLabel . FILTER(LANG(?statusLabel) = "en") }
}
GROUP BY ?class ?classLabel ?status ?statusLabel
ORDER BY DESC(?n)
"""


def expected_counts(items: list[Any], schema=None) -> tuple[Counter, Counter]:
    """What the generated items say the wiki should hold: items by class label and by review status label."""
    labels = {}
    for c in _records(getattr(schema, "CLASSES", None)):
        labels[class_key(c)] = _get(c, "label")
    by_class: Counter = Counter()
    by_status: Counter = Counter()
    for it in items:
        cls = _get(it, "cls")
        if cls:
            by_class[labels.get(cls, cls)] += 1
        for c in _get(it, "claims") or []:
            if _get(c, "prop") == "review status":
                v = _get(_get(c, "value"), "value") or ""
                by_status[v.rsplit(":", 1)[-1]] += 1
    return by_class, by_status


def check_rq(items: list[Any], schema, ids: Ids) -> str:
    """``check.rq``: the coverage query with the expected counts in its header."""
    by_class, by_status = expected_counts(items, schema)
    head = ["# expected counts from the generated items (lexflow.publish.qs write):"]
    head += [f"#   class {label}: {n}" for label, n in by_class.most_common()]
    head += [f"#   review status {label}: {n}" for label, n in by_status.most_common()]
    q = coverage_query()
    return "\n".join(head) + "\n" + fill_tokens(q, ids, strict=False)


def coverage_query() -> str:
    path = SPARQL_DIR / "coverage.rq"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return COVERAGE_QUERY


def fill_tokens(query: str, ids: Ids, strict: bool = True) -> str:
    """Replace ``{P:label}`` and ``{Q:key}`` tokens from the ids."""
    def p(m):
        try:
            return ids.prop(m.group(1))
        except Unresolved:
            if strict:
                raise
            return m.group(0)

    def q(m):
        try:
            return ids.item(m.group(1))
        except Unresolved:
            if strict:
                raise
            return m.group(0)
    return re.sub(r"\{Q:([^}]+)\}", q, re.sub(r"\{P:([^}]+)\}", p, query))


# ----------------------------------------------------------------------------------------------- the public API
class Client:
    """Read-only access to the wiki's API and SPARQL endpoint, one request per second at most."""

    def __init__(self, api: str = API, sparql: str = SPARQL_ENDPOINT, interval: float = MIN_INTERVAL, log=None):
        import requests
        self.api, self.sparql_url, self.interval = api, sparql, interval
        self.session = requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT
        self.last = 0.0
        self.requests = 0
        self.log = log or (lambda *a: None)

    def _pace(self):
        wait = self.last + self.interval - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        self.last = time.monotonic()
        self.requests += 1

    def get(self, **params) -> dict:
        self._pace()
        r = self.session.get(self.api, params={**params, "format": "json"}, timeout=60)
        r.raise_for_status()
        data = r.json()
        if "error" in data:
            raise QSError(f"{params.get('action')}: {data['error'].get('code')}: {data['error'].get('info')}")
        return data

    def sparql(self, query: str) -> list[dict]:
        self._pace()
        r = self.session.post(self.sparql_url, data={"query": query},
                              headers={"Accept": "application/sparql-results+json"}, timeout=120)
        r.raise_for_status()
        rows = []
        for b in r.json()["results"]["bindings"]:
            rows.append({k: v.get("value") for k, v in b.items()})
        return rows

    # --- lookups
    def entities(self, ids: list[str], props: str = "labels|claims") -> dict:
        out = {}
        for i in range(0, len(ids), 50):
            res = self.get(action="wbgetentities", ids="|".join(ids[i:i + 50]), props=props, languages=LANG)
            out.update({k: v for k, v in res.get("entities", {}).items() if "missing" not in v})
        return out

    def search_property(self, label: str) -> list[str]:
        res = self.get(action="wbsearchentities", search=label, type="property", language=LANG, limit=20)
        return [h["id"] for h in res.get("search", [])
                if (h.get("label") or "").strip().lower() == label.strip().lower()]

    def search_item_by_key(self, key: str) -> list[str]:
        """CirrusSearch ``haswbstatement:P25=<key>``."""
        res = self.get(action="query", list="search", srsearch=f"haswbstatement:{KEY_PROPERTY}={key}", srlimit=10,
                       srnamespace=120)
        return [h["title"].split(":")[-1] for h in res.get("query", {}).get("search", [])]

    def search_item_by_label(self, label: str) -> list[str]:
        res = self.get(action="wbsearchentities", search=label, type="item", language=LANG, limit=20)
        return [h["id"] for h in res.get("search", [])
                if (h.get("label") or "").strip().lower() == label.strip().lower()]

    def keys_by_sparql(self) -> dict[str, str]:
        """Every ``P25`` value on the wiki -> Q-id, in one paged query (the query service may lag edits by minutes;
        callers confirm with ``wbgetentities``)."""
        out, offset, page = {}, 0, 5000
        while True:
            rows = self.sparql(f"PREFIX lxt: <{PREFIXES['lxt']}>\nSELECT ?item ?key WHERE {{ ?item lxt:{KEY_PROPERTY} "
                               f"?key }} LIMIT {page} OFFSET {offset}")
            for r in rows:
                qid = r["item"].rsplit("/", 1)[-1]
                out.setdefault(r["key"], qid)
            if len(rows) < page:
                return out
            offset += page


def _key_of(entity: dict) -> str | None:
    for c in entity.get("claims", {}).get(KEY_PROPERTY, []):
        dv = c.get("mainsnak", {}).get("datavalue", {})
        if dv.get("type") == "string":
            return dv["value"]
    return None


def resolve(items: list[Any], prop_labels: list[str], ids: Ids, client: Client, log=print,
            fresh: bool = False, schema=None, search: bool = True, hints: dict[str, str] | None = None) -> Ids:
    """Fill ``ids`` with every property label -> P-id (``wbsearchentities`` type=property, confirmed by label with
    ``wbgetentities``) and every item key -> Q-id (``haswbstatement:P25=<key>`` through CirrusSearch, the paged
    SPARQL map of P25 values, the ``hints`` lexflow's own ``wikibase_items`` table holds, and a label search, each
    confirmed by reading the item's P25 with ``wbgetentities``; the query service can lag the wiki by days, which
    is why the hints and the confirmation exist).  Already-resolved ids are kept unless ``fresh``."""
    if fresh:
        ids.properties.clear()
        ids.items.clear()
        ids.methods.clear()
        if schema is not None:
            ids.add_schema(schema)
    # --- properties
    todo = [l for l in prop_labels if l not in ids.properties]
    candidates: dict[str, list[str]] = {}
    for label in todo:
        try:
            candidates[label] = client.search_property(label)
        except Exception as e:                                     # noqa: BLE001
            log(f"property search failed for {label!r}: {e}")
            candidates[label] = []
    cand_ids = sorted({p for ps in candidates.values() for p in ps})
    found = client.entities(cand_ids, props="labels") if cand_ids else {}
    for label, cands in candidates.items():
        hit = [p for p in cands if (found.get(p, {}).get("labels", {}).get(LANG, {}).get("value") or "") == label]
        if hit:
            ids.properties[label] = hit[0]
            ids.methods[label] = "wbsearchentities"
            if len(hit) > 1:
                log(f"property {label!r}: several ids {hit}; keeping {hit[0]}")
    ids.unresolved["properties"] = [l for l in prop_labels if l not in ids.properties]
    log(f"properties: {len(prop_labels) - len(ids.unresolved['properties'])}/{len(prop_labels)} resolved, "
        f"{len(ids.unresolved['properties'])} unresolved")
    # --- items
    keys = list(dict.fromkeys(_get(it, "key") for it in items if _get(it, "key")))
    labels = {_get(it, "key"): _get(it, "label") for it in items}
    todo = [k for k in keys if k not in ids.items]
    proposed: dict[str, tuple[str, str]] = {}                       # key -> (qid, method)
    if todo:
        try:
            by_key = client.keys_by_sparql()
        except Exception as e:                                     # noqa: BLE001
            log(f"SPARQL key map failed: {e}")
            by_key = {}
        for k in todo:
            if k in by_key:
                proposed[k] = (by_key[k], "sparql")
            elif hints and hints.get(k):
                proposed[k] = (hints[k], "wikibase_items")
        rest = [k for k in todo if k not in proposed]
        from_hints = sum(1 for v in proposed.values() if v[1] == "wikibase_items")
        log(f"items: {len(keys) - len(todo)} cached, {len(proposed) - from_hints} from SPARQL, {from_hints} from "
            f"wikibase_items, {len(rest)} to search" + ("" if search else " (skipped: --no-search)"))
        for n, k in enumerate(rest if search else [], 1):
            try:
                hits = client.search_item_by_key(k)
                method = "cirrussearch"
                if not hits and labels.get(k):
                    hits = client.search_item_by_label(labels[k])
                    method = "label"
            except Exception as e:                                 # noqa: BLE001
                log(f"search failed for {k!r}: {e}")
                hits = []
            if hits:
                proposed[k] = (hits[0], method)
                if len(hits) > 1:
                    proposed[k] = ("|".join(hits), method)
            if n % 100 == 0:
                log(f"  searched {n}/{len(rest)}")
    # --- confirm every proposed id by reading its P25
    cand = sorted({q for v, _ in proposed.values() for q in v.split("|")})
    found = client.entities(cand, props="claims") if cand else {}
    by_key_live = {}
    for qid, ent in found.items():
        k = _key_of(ent)
        if k:
            by_key_live.setdefault(k, qid)
    for k, (qids, method) in proposed.items():
        for q in qids.split("|"):
            if by_key_live.get(k) == q:
                ids.items[k] = q
                ids.methods[k] = method
                break
        else:
            log(f"{k}: candidate {qids} does not carry P25={k!r}; left unresolved")
    ids.unresolved["items"] = [k for k in keys if k not in ids.items]
    log(f"items: {len(keys) - len(ids.unresolved['items'])}/{len(keys)} resolved, "
        f"{len(ids.unresolved['items'])} unresolved; {client.requests} requests")
    return ids


def check(items: list[Any], schema, ids: Ids, client: Client, log=print) -> dict:
    """Run the coverage query live and compare with the generated items' counts; returns the comparison."""
    query = fill_tokens(coverage_query(), ids, strict=False)
    if "{P:" in query or "{Q:" in query:
        missing = sorted(set(re.findall(r"\{[PQ]:[^}]+\}", query)))
        log(f"coverage query has unresolved tokens {missing}; those parts are dropped")
        query = re.sub(r"^.*\{[PQ]:[^}]+\}.*$", "", query, flags=re.M)
    rows = client.sparql(query)
    live_class: Counter = Counter()
    live_status: Counter = Counter()
    for r in rows:
        n = int(float(r.get("n") or r.get("count") or 0))
        cl = r.get("classLabel") or r.get("class", "").rsplit("/", 1)[-1]
        if cl:
            live_class[cl] += n
        st = r.get("statusLabel") or r.get("status")
        if st:
            live_status[st.rsplit("/", 1)[-1]] += n
    exp_class, exp_status = expected_counts(items, schema)
    missing = [c for c in exp_class if live_class.get(c, 0) == 0]
    short = {c: (exp_class[c], live_class.get(c, 0)) for c in exp_class if 0 < live_class.get(c, 0) < exp_class[c]}
    log(f"{'class':40} {'expected':>9} {'live':>9}")
    for c, n in exp_class.most_common():
        log(f"{c:40} {n:>9} {live_class.get(c, 0):>9}")
    for c, n in live_class.most_common():
        if c not in exp_class:
            log(f"{c:40} {'-':>9} {n:>9}")
    if exp_status:
        log(f"\n{'review status':40} {'expected':>9} {'live':>9}")
        for s, n in exp_status.most_common():
            log(f"{s:40} {n:>9} {live_status.get(s, 0):>9}")
    log(f"\nmissing kinds (expected, nothing live): {', '.join(missing) if missing else 'none'}")
    if short:
        log("short: " + ", ".join(f"{c} {have}/{want}" for c, (want, have) in short.items()))
    return {"expected": dict(exp_class), "live": dict(live_class), "missing": missing, "short": short,
            "status_expected": dict(exp_status), "status_live": dict(live_status)}


# ----------------------------------------------------------------------------------------------- data access
def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def git_commit() -> str:
    """The short commit of the working tree: ``LEXFLOW_GIT_COMMIT`` (set it when running inside Docker, where
    ``.git`` is not mounted), else the nearest ``.git`` above the package, else ``unknown``."""
    import os
    env = os.environ.get("LEXFLOW_GIT_COMMIT")
    if env:
        return env.strip()[:12]
    for d in [ROOT, *ROOT.parents]:
        git = d / ".git"
        if not git.exists():
            continue
        try:
            if git.is_file():                                    # a worktree: "gitdir: <path>"
                git = Path(git.read_text().split(":", 1)[1].strip())
            head = (git / "HEAD").read_text().strip()
            if head.startswith("ref:"):
                ref = head.split(" ", 1)[1].strip()
                f = git / ref
                if f.exists():
                    return f.read_text().strip()[:7]
                packed = git / "packed-refs"
                if packed.exists():
                    for line in packed.read_text().splitlines():
                        if line.endswith(" " + ref):
                            return line.split()[0][:7]
                return "unknown"
            return head[:7]
        except OSError:
            return "unknown"
    return "unknown"


def open_db(path: str | Path | None = None) -> sqlite3.Connection:
    """The lexflow database, read-only (nothing here writes to it)."""
    p = Path(path or config.DB_PATH)
    con = sqlite3.connect(f"file:{p.as_posix()}?mode=ro", uri=True, timeout=60)
    con.row_factory = sqlite3.Row
    return con


def load_graph(con, states=None, places=None, drafts=True):
    """``(schema, items, by_kind)`` from the schema and graph modules."""
    from . import graph, schema
    items = graph.build(con, states=states, places=places, drafts=drafts)
    grouped = graph.by_kind(items)
    if isinstance(grouped, dict):
        by_kind = OrderedDict(grouped.items())
    else:
        by_kind = OrderedDict()
        for kind, its in grouped:
            by_kind.setdefault(kind, []).extend(its)
    return schema, items, by_kind


def property_labels(schema) -> list[str]:
    return [_get(p, "label") for p in _records(getattr(schema, "PROPERTIES"))]


# ----------------------------------------------------------------------------------------------- writing
def write_pass1(schema, items: list[Any], by_kind, out_dir: Path, commit: str, log=print) -> list[tuple[str, Counter]]:
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("0[123]-*.qs"):
        old.unlink()
    files: list[tuple[str, Counter]] = []
    class_items = merge_schema_items(schema_items(schema), items)
    batches = [properties_batch(schema), classes_batch(schema, class_items)] + items_batches(by_kind)
    for b in batches:
        for name, text in render(b, commit):
            (out_dir / name).write_text(text, encoding="utf-8")
            files.append((name, command_counts(text.splitlines())))
    (out_dir / "check.rq").write_text(check_rq(items + class_items, schema, Ids.load(out_dir / "ids.json", schema)),
                                      encoding="utf-8")
    (out_dir / "README.md").write_text(readme(files, 1, commit), encoding="utf-8")
    _report(files, out_dir, log)
    return files


def write_pass2(schema, items: list[Any], by_kind, out_dir: Path, commit: str, log=print) -> list[tuple[str, Counter]]:
    ids_path = out_dir / "ids.json"
    if not ids_path.exists():
        raise QSError(f"{ids_path} is missing: run --resolve after pass 1")
    ids = Ids.load(ids_path, schema)
    for old in out_dir.glob("0[45]-*.qs"):
        old.unlink()
    class_items = merge_schema_items(schema_items(schema), items)
    batches, updates = claims_batches(by_kind, ids, schema, class_items)
    files: list[tuple[str, Counter]] = []
    for name in sorted(out_dir.glob("0[123]-*.qs")):
        files.append((name.name, command_counts(name.read_text(encoding="utf-8").splitlines())))
    skipped_total = 0
    for b in batches + [updates]:
        skipped_total += len(b.skipped)
        for name, text in render(b, commit):
            (out_dir / name).write_text(text, encoding="utf-8")
            files.append((name, command_counts(text.splitlines())))
    (out_dir / "check.rq").write_text(check_rq(items + class_items, schema, ids), encoding="utf-8")
    (out_dir / "README.md").write_text(readme(files, 2, commit, skipped_total), encoding="utf-8")
    _report([f for f in files if f[0][:2] in ("04", "05")], out_dir, log)
    if skipped_total:
        log(f"{skipped_total} claims skipped for missing ids (listed in the file headers)")
    return files


def _report(files, out_dir: Path, log) -> None:
    for name, c in files:
        size = (out_dir / name).stat().st_size
        parts = ", ".join(f"{k} {c[k]}" for k in ("CREATE_PROPERTY", "CREATE", "Len", "Den", "Aen", "statement",
                                                  "qualifier", "reference") if c.get(k))
        log(f"{name:32} {size:>9,} bytes  {c.get('commands', 0):>6} commands  ({parts})")


# ----------------------------------------------------------------------------------------------- command line
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m lexflow.publish.qs", description=__doc__.split("\n\n")[0])
    ap.add_argument("command", nargs="?", choices=["write", "resolve", "check"], default=None)
    ap.add_argument("--pass", dest="pass_no", type=int, default=1, choices=[1, 2],
                    help="1: creations (default); 2: claims and updates from ids.json")
    ap.add_argument("--resolve", action="store_true", help="write ids.json from the public API (reads only)")
    ap.add_argument("--check", action="store_true", help="run the coverage query live and compare")
    ap.add_argument("--fresh", action="store_true", help="with --resolve: ignore the cached ids")
    ap.add_argument("--no-search", action="store_true",
                    help="with --resolve: the SPARQL key map only, no per-key search (two requests per missing key)")
    ap.add_argument("--states", help="comma-separated state codes to limit the graph")
    ap.add_argument("--places", help="comma-separated place ids to limit the graph")
    ap.add_argument("--no-drafts", action="store_true", help="leave draft (single-tier) models out")
    ap.add_argument("--db", help="path of the lexflow database (opened read-only)")
    ap.add_argument("--out", help=f"output directory (default {OUT_DIR})")
    args = ap.parse_args(argv)
    command = args.command or ("resolve" if args.resolve else "check" if args.check else None)
    if not command:
        ap.error("give a command: write [--pass 2], --resolve or --check")
    out_dir = Path(args.out) if args.out else OUT_DIR
    states = args.states.split(",") if args.states else None
    places = args.places.split(",") if args.places else None
    commit = git_commit()
    with open_db(args.db) as con:
        schema, items, by_kind = load_graph(con, states=states, places=places, drafts=not args.no_drafts)
    print(f"{len(items)} items in {len(by_kind)} kinds from the graph; commit {commit}", file=sys.stderr)
    log = lambda *a: print(*a, file=sys.stderr)                     # noqa: E731
    if command == "write":
        if args.pass_no == 1:
            write_pass1(schema, items, by_kind, out_dir, commit, log)
        else:
            write_pass2(schema, items, by_kind, out_dir, commit, log)
        return 0
    client = Client(log=log)
    ids = Ids.load(out_dir / "ids.json", schema)
    if command == "resolve":
        with open_db(args.db) as con:                           # the ids lexflow's own table remembers, as hints
            hints = {r["key"]: r["qid"] for r in con.execute("SELECT key, qid FROM wikibase_items") if r["qid"]}
        resolve(items + schema_items(schema), property_labels(schema), ids, client, log, fresh=args.fresh,
                schema=schema, search=not args.no_search, hints=hints)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "ids.json").write_text(json.dumps(ids.dump(), indent=1, ensure_ascii=False) + "\n",
                                          encoding="utf-8")
        log(f"wrote {out_dir / 'ids.json'}")
        if ids.unresolved["properties"] or ids.unresolved["items"]:
            log("unresolved properties: " + ", ".join(ids.unresolved["properties"][:50]))
            log("unresolved items: " + ", ".join(ids.unresolved["items"][:50]) +
                (" ..." if len(ids.unresolved["items"]) > 50 else ""))
        return 0
    result = check(items + schema_items(schema), schema, ids, client, log)
    return 0 if not result["missing"] else 1


if __name__ == "__main__":
    sys.exit(main())
