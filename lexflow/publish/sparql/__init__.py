"""The canned queries of docs/design/wikibase-schema.md section 6, and the runner that prepares one.

Each ``*.rq`` file here starts with the prefixes of ``rdf.QUERY_PREFIXES`` and a comment header::

    # question: every section of Va. Code Title 2.2 Chapter 37 in the code's order
    # params: unit=lexflow:unit:va:t2.2-sii-pb-c37
    # live-only: yes            (federated queries the local store cannot run)
    # status: ...               (which store returns rows today)

A parameter is a ``VALUES ?name { ... }`` line in the body; ``prepare`` replaces its value with the one given
(``--param name=value``), formatting a lexflow key as an item (``lx:{Q:key}``), ``Q24`` as ``lx:Q24``, a date as
``xsd:dateTime``, a number as a number and anything else as a string literal.  ``{P:label}`` and ``{Q:key}`` tokens
are then expanded by ``lexflow.publish.ids`` (resolved, provisional, or looked up live).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from .. import ids as I

DIR = Path(__file__).resolve().parent
_BRACES = r"\{(?:[^{}]|\{[^{}]*\})*\}"          # one VALUES block, whose terms may hold {P:...}/{Q:...} tokens
_VALUES = re.compile(r"VALUES\s+\?(\w+)\s*" + _BRACES)
_KEY = re.compile(r"^[a-z][a-z0-9]*:[^\s\"<>{}]+$")


@dataclass
class Query:
    name: str
    question: str
    params: dict[str, str] = field(default_factory=dict)     # name -> default (as written in the file)
    live_only: bool = False
    status: str = ""
    text: str = ""

    @property
    def path(self) -> Path:
        return DIR / f"{self.name}.rq"

    def as_dict(self) -> dict:
        return {"name": self.name, "question": self.question, "params": dict(self.params),
                "live_only": self.live_only, "status": self.status, "text": self.text}


def parse(text: str, name: str = "") -> Query:
    q = Query(name=name, question="", text=text)
    for line in text.splitlines():
        m = re.match(r"^#\s*(question|params|live-only|status)\s*:\s*(.*)$", line.strip(), re.I)
        if not m:
            continue
        kind, val = m.group(1).lower(), m.group(2).strip()
        if kind == "question":
            q.question = val
        elif kind == "params":
            for part in re.split(r"\s*[,;]\s*", val):
                if "=" in part:
                    k, v = part.split("=", 1)
                    q.params[k.strip()] = v.strip()
                elif part:
                    q.params[part.strip()] = ""
        elif kind == "live-only":
            q.live_only = val.lower() in ("yes", "true", "1")
        elif kind == "status":
            q.status = val
    for m in _VALUES.finditer(text):
        q.params.setdefault(m.group(1), _default_of(m.group(0)))
    return q


def _default_of(values_line: str) -> str:
    inner = values_line[values_line.index("{") + 1:values_line.rindex("}")].strip()
    if inner.upper() == "UNDEF":
        return ""
    m = I.TOKEN.search(inner)
    if m:
        return m.group(2).strip()
    return inner.strip('"').split("^^")[0].strip('"')


def catalogue() -> list[Query]:
    return [parse(p.read_text(encoding="utf-8"), p.stem) for p in sorted(DIR.glob("*.rq"))]


def exists(name: str) -> bool:
    return bool(re.fullmatch(r"[a-z0-9\-]+", name)) and (DIR / f"{name}.rq").exists()


def get(name: str) -> Query:
    p = DIR / f"{name.removesuffix('.rq')}.rq"
    if not p.exists() or p.parent != DIR:
        raise KeyError(name)
    return parse(p.read_text(encoding="utf-8"), p.stem)


def resolve(file_or_text: str) -> Query:
    """A query from a path, a catalogue name, or SPARQL text."""
    s = file_or_text.strip()
    p = Path(s)
    if s.endswith(".rq") and p.exists():
        return parse(p.read_text(encoding="utf-8"), p.stem)
    if re.match(r"^[a-z0-9\-]+$", s) and (DIR / f"{s}.rq").exists():
        return get(s)
    return parse(s, "")


def term(value: str) -> str:
    """A parameter value as a SPARQL term (see the module docstring)."""
    v = str(value).strip()
    if not v:
        return "UNDEF"
    if re.match(r"^Q\d+$", v):
        return f"lx:{v}"
    if v.startswith("<") and v.endswith(">"):
        return v
    if v.startswith('"'):
        return v
    if _KEY.match(v) and not v.startswith(("http:", "https:")):
        return "lx:{Q:%s}" % v
    if re.match(r"^\d{4}-\d{2}-\d{2}$", v):
        return f'"{v}T00:00:00Z"^^xsd:dateTime'
    if re.match(r"^-?\d+(\.\d+)?$", v):
        return v
    return '"' + v.replace("\\", "\\\\").replace('"', '\\"') + '"'


def prepare(q: Query | str, params: dict[str, str] | None = None, ids: I.IdMap | None = None, live: bool = False) -> str:
    """The query text with its ``VALUES`` parameters set and its tokens expanded, ready to run."""
    text = q.text if isinstance(q, Query) else str(q)
    for name, value in (params or {}).items():
        if value in (None, ""):
            continue
        pat = re.compile(r"VALUES\s+\?%s\s*" % re.escape(name) + _BRACES)
        text, n = pat.subn(f"VALUES ?{name} {{ {term(value)} }}", text, count=1)
        if not n:
            raise KeyError(f"the query has no VALUES ?{name} line to set")
    idmap = ids or I.default()
    if "PREFIX lx:" not in text and "prefix lx:" not in text.lower():
        from ..rdf import QUERY_PREFIXES
        text = QUERY_PREFIXES + "\n" + text
    return idmap.expand(text, live=live)
