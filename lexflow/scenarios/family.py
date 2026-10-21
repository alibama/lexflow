"""A question family: the enumerated dimensions of a kind of hypothetical, its decision tables, and their grounding.

A family file (``fixtures/families/<id>.json``) holds:

* ``dimensions``: the inputs a fact pattern is made of, each a small vocabulary (``values``) or numeric ``bins``
  with a representative value, a ``code`` for the scenario-ID grammar, a label, a provenance tag (``SRC`` a matched
  quote or a published figure with its URL, ``ASM`` lexflow's assumption with an ``ASM-xx`` id) and the section that
  defines it.  A value may be ``scope``d to other dimensions' values (a zoning district belongs to one locality) and
  may carry attributes that ``derived`` inputs read (a district's ``class``: by right, special use, determination
  needed, not allowed).
* ``constraints``: combinations that cannot occur (``when`` these values, ``require_any`` of these), used by the
  expansion to prune.
* ``tables``: decision tables in lexflow's decision shape (``lexflow.scenarios.dmn``), one per requirement area,
  hit policy COLLECT.  Each rule decides that one requirement applies (``then``: the requirement id and its status)
  and carries the requirement itself: ``title``, ``office`` (an id in ``offices``), ``fee`` (``usd``, ``min_usd``
  or only a ``rule``; ``kind`` fee or tax), ``deadline``, ``lead_days``, ``tags`` for ordering, ``stage``, the ``tag``
  and ``assumptions`` it rests on, and its ``source``: a pointer (``from``: ``<file>#<path>``) into one of the
  verified place files or the state backbone, with the quote copied from there and lexflow's match of it
  (``grounding``).  ``fee_source`` grounds the fee when another quote does.
* ``order``: ordering constraints between tags and milestones (``m:lease``, ``m:construction``, ``m:occupancy``,
  ``m:opening``), each with its own grounded source; ``appeals``: where a refusal goes, per table and locality.
* ``personas`` (named input bundles), ``variants`` (alternative rule readings evaluated against the same
  population: ``class_overrides`` re-map a derived attribute), ``assumptions`` (``ASM-xx``: text, direction of
  error, range) and ``serves`` (the coverage questions the family answers, with the tables each one reads).

``fill`` copies each source's quote, URL and citation from its pointer and records lexflow's match
(``places.check_quotes`` for a place file: the statute index for a Code quote, the quote fetch's cached page for
the rest; the same matcher over a one-entry spec for a backbone section; for a quote whose words are withheld
under ``quotes.NO_REPRINT`` and absent here, the page's recorded fingerprint).  A rule whose source does not match
is dropped when the family loads, and listed (``Family.dropped``).  Words from a site whose terms forbid reposting
never enter the file: a withheld quote is copied as its fingerprint and paraphrase, and ``quotes.withhold`` moves
any such words that a pointer restored into the evidence store.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from .. import config
from . import dmn

FAMILIES_DIR = config.ROOT / "fixtures" / "families"
TAGS = ("SRC", "ASM", "SCN")
STATUSES = ("required", "may be required", "recommended", "ask first", "not required", "blocked")
COUNTED = ("required", "may be required", "recommended", "ask first")      # statuses an output lists as to do
MILESTONES = ("m:lease", "m:construction", "m:occupancy", "m:opening")
_WHERE = re.compile(r"([A-Za-z_]\w*)(?:\[(\d+)\])?")


class FamilyError(ValueError):
    pass


# ----------------------------------------------------------------------------------------------- pointers
def split_pointer(ptr: str) -> tuple[str, str]:
    """``curated/places/va/x/y.json#steps[3]`` -> (file, path)."""
    if "#" not in (ptr or ""):
        raise FamilyError(f"a source pointer is <file>#<path>, not {ptr!r}")
    f, _, where = ptr.partition("#")
    return f, where


def resolve(doc: Any, where: str) -> Any:
    """The value at ``topics[3].sections[12]`` in a loaded JSON document."""
    cur = doc
    for part in where.split("."):
        m = _WHERE.fullmatch(part)
        if not m:
            raise FamilyError(f"bad path part {part!r} in {where!r}")
        cur = cur[m.group(1)]
        if m.group(2) is not None:
            cur = cur[int(m.group(2))]
    return cur


_DOCS: dict[str, dict] = {}


def source_doc(file: str, restore: bool = True) -> dict:
    """A pointer's file (a researched place file or a fixture), with withheld words restored when the evidence
    store is present."""
    key = f"{file}|{restore}"
    if key not in _DOCS:
        p = config.ROOT / file
        doc = json.loads(p.read_text(encoding="utf-8"))
        if restore:
            from ..municipal import quotes as Q
            Q.restore(doc, p)
        _DOCS[key] = doc
    return _DOCS[key]


def is_place_file(file: str) -> bool:
    return file.startswith("curated/places/")


# ---------------------------------------------------------------------------------------------- dimensions
@dataclass
class Dimension:
    spec: dict

    @property
    def name(self) -> str:
        return self.spec["name"]

    @property
    def type(self) -> str:
        return self.spec.get("type", "string")

    @property
    def label(self) -> str:
        return self.spec.get("label") or self.name

    @property
    def binned(self) -> bool:
        return bool(self.spec.get("bins"))

    @property
    def options(self) -> list[dict]:
        """Values or bins, each with ``code``, ``label`` and ``value``."""
        return self.spec.get("bins") or self.spec.get("values") or []

    def by_code(self, code: str) -> dict:
        for o in self.options:
            if o["code"] == code:
                return o
        raise FamilyError(f"{self.name}: no value with code {code!r}")

    def option_of(self, value) -> dict:
        """The value or bin a scenario value falls in (a number falls in a bin; a code or a value names one)."""
        if self.binned:
            if isinstance(value, str):
                try:
                    return self.by_code(value)
                except FamilyError:
                    try:
                        value = float(value)
                    except ValueError:
                        raise FamilyError(f"{self.name}: {value!r} is neither a bin code nor a number") from None
            for b in self.spec["bins"]:
                lo, hi = b.get("min"), b.get("max")
                if (lo is None or value >= lo) and (hi is None or value <= hi):
                    return b
            raise FamilyError(f"{self.name}: {value!r} is in no bin")
        for o in self.options:
            if o.get("value") == value or o["code"] == value:
                return o
        if self.type == "boolean" and isinstance(value, str) and value.lower() in ("true", "false", "yes", "no"):
            return self.option_of(value.lower() in ("true", "yes"))
        raise FamilyError(f"{self.name}: {value!r} is not one of {[o.get('value') for o in self.options]}")

    def canonical(self, value):
        """The value a table sees: the value itself for an enumeration, the number for a bin (the representative
        number when a code is given)."""
        o = self.option_of(value)
        if self.binned and isinstance(value, (int, float)) and not isinstance(value, bool):
            return value
        return o["value"]

    def in_scope(self, option: dict, inputs: dict) -> bool:
        for dim, allowed in (option.get("scope") or {}).items():
            if dim in inputs and inputs[dim] not in (allowed if isinstance(allowed, list) else [allowed]):
                return False
        return True


# --------------------------------------------------------------------------------------------------- family
@dataclass
class Family:
    spec: dict
    path: Path | None = None
    dropped: list[dict] = field(default_factory=list)

    def __post_init__(self):
        self.id = self.spec["family"]
        self.version = self.spec.get("version", "0")
        self.dims = [Dimension(d) for d in self.spec["dimensions"]]
        self.dim = {d.name: d for d in self.dims}
        self.slots = list((self.spec.get("grammar") or {}).get("slots") or [d.name for d in self.dims])
        self.derived = list(self.spec.get("derived") or [])
        self.constraints = list(self.spec.get("constraints") or [])
        self.offices = dict(self.spec.get("offices") or {})
        self.personas = {p["id"]: p for p in self.spec.get("personas") or []}
        self.variants = {v["id"]: v for v in self.spec.get("variants") or []}
        self.assumptions = {a["id"]: a for a in self.spec.get("assumptions") or []}
        self.order = []
        self.tables = []
        self.dropped = []
        for t in self.spec.get("tables") or []:
            t = copy.deepcopy(t)
            keep = []
            for r in t.get("rules") or []:
                g = (r.get("source") or {}).get("grounding") or {}
                if g.get("matched"):
                    keep.append(r)
                else:
                    self.dropped.append({"table": t["id"], "rule": r.get("id"), "why": g.get("why") or "not grounded",
                                         "from": (r.get("source") or {}).get("from")})
            t["rules"] = keep
            self.tables.append(t)
        for o in self.spec.get("order") or []:
            # a grounded ordering rule, or lexflow's own advice (tag ASM, with the assumption it rests on)
            if ((o.get("source") or {}).get("grounding") or {}).get("matched") or (
                    o.get("tag") == "ASM" and not o.get("source") and o.get("assumption") in self.assumptions):
                self.order.append(o)
            else:
                self.dropped.append({"order": o.get("id"), "why": ((o.get("source") or {}).get("grounding") or {}).get(
                    "why") or "not grounded", "from": (o.get("source") or {}).get("from")})
        self.appeals = [a for a in self.spec.get("appeals") or []
                        if ((a.get("source") or {}).get("grounding") or {}).get("matched")]
        self.table = {t["id"]: t for t in self.tables}

    # ---- loading
    @classmethod
    def from_file(cls, path: str | Path) -> "Family":
        p = Path(path)
        return cls(json.loads(p.read_text(encoding="utf-8")), p)

    @classmethod
    def load(cls, family_id: str) -> "Family":
        p = FAMILIES_DIR / f"{family_id}.json"
        if not p.exists():
            raise FamilyError(f"no family {family_id!r} (looked for {p})")
        return cls.from_file(p)

    def content_hash(self) -> str:
        """sha256 of the parts that decide an output (dimensions, derived inputs, constraints, tables as loaded,
        order, variants), in canonical JSON: a run records it, so a stored run says which tables made it."""
        body = {"dimensions": self.spec["dimensions"], "derived": self.derived, "constraints": self.constraints,
                "tables": self.tables, "order": self.order, "variants": self.spec.get("variants") or []}
        return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()

    # ---- values
    def normalise(self, inputs: dict) -> dict:
        """Every dimension's canonical value from a map of names to values, codes or numbers; a dimension left out
        takes its ``default``.  Raises FamilyError on an unknown name or value."""
        out = {}
        unknown = [k for k in inputs if k not in self.dim]
        if unknown:
            raise FamilyError(f"unknown dimensions: {', '.join(unknown)}")
        loc_dim = (self.spec.get("grammar") or {}).get("locality", "locality")
        for d in self.dims:
            v = inputs.get(d.name, d.spec.get("default"))
            if v is None and d.spec.get("default_by"):        # a default that depends on the locality
                v = d.spec["default_by"].get(out.get(loc_dim) or inputs.get(loc_dim))
            if v is None:
                raise FamilyError(f"no value for {d.name}")
            out[d.name] = d.canonical(v)
        return out

    def code_of(self, name: str, value) -> str:
        return self.dim[name].option_of(value)["code"]

    def attributes(self, inputs: dict, variant: str | None = None) -> dict:
        """The derived inputs (``derived``: an attribute of another dimension's value), with a variant's overrides."""
        out = {}
        for dv in self.derived:
            opt = self.dim[dv["from"]].option_of(inputs[dv["from"]])
            out[dv["name"]] = opt.get(dv["attribute"])
        if variant:
            v = self.variants.get(variant)
            if not v:
                raise FamilyError(f"no variant {variant!r}")
            for ov in v.get("class_overrides") or []:
                if all(inputs.get(k) in (w if isinstance(w, list) else [w]) for k, w in (ov.get("when") or {}).items()):
                    key = str(inputs[ov["dimension"]])
                    if key in ov["map"]:
                        out[ov["attribute"]] = ov["map"][key]
                    elif "*" in ov["map"]:
                        out[ov["attribute"]] = ov["map"]["*"]
        return out

    def data(self, inputs: dict, variant: str | None = None) -> dict:
        """What the tables see: the canonical inputs plus the derived ones."""
        return {**inputs, **self.attributes(inputs, variant)}

    def violations(self, inputs: dict) -> list[str]:
        """The constraints a (possibly partial) assignment breaks: a value out of scope, or a ``when`` that holds
        with none of its ``require_any`` alternatives possible."""
        bad = []
        for d in self.dims:
            if d.name in inputs:
                try:
                    opt = d.option_of(inputs[d.name])
                except FamilyError:
                    bad.append(f"{d.name}: unknown value {inputs[d.name]!r}")
                    continue
                if not d.in_scope(opt, inputs):
                    bad.append(f"{d.name}={opt['code']} is out of scope for {opt.get('scope')}")
        for c in self.constraints:
            when = c.get("when") or {}
            if not all(k in inputs and self._is(k, inputs[k], w) for k, w in when.items()):
                continue
            alts = c.get("require_any") or []
            possible = False
            for alt in alts:
                if all((k not in inputs) or self._is(k, inputs[k], w) for k, w in alt.items()):
                    possible = True
                    break
            if not possible:
                bad.append(c["id"])
        return bad

    def _is(self, name: str, value, allowed) -> bool:
        allowed = allowed if isinstance(allowed, list) else [allowed]
        d = self.dim[name]
        try:
            o = d.option_of(value)
        except FamilyError:
            return False
        return o["code"] in allowed or o.get("value") in allowed

    # ---- the scenario-ID grammar
    def scenario_id(self, inputs: dict, variant: str | None = None) -> str:
        """``{LOC}-{DIST}-{BLD}-...`` in ``grammar.slots`` order, then ``-R{variant code}`` for a policy variant."""
        sep = (self.spec.get("grammar") or {}).get("separator", "-")
        parts = [self.code_of(s, inputs[s]) for s in self.slots]
        if variant:
            parts.append(self.variants[variant]["code"])
        return sep.join(parts)

    def parse_id(self, sid: str) -> tuple[dict, str | None]:
        """A scenario id back into inputs (each bin's representative value) and the variant, if any."""
        sep = (self.spec.get("grammar") or {}).get("separator", "-")
        parts = sid.strip().split(sep)
        variant = None
        codes = {v["code"]: k for k, v in self.variants.items()}
        if len(parts) == len(self.slots) + 1 and parts[-1] in codes:
            variant = codes[parts.pop()]
        if len(parts) != len(self.slots):
            raise FamilyError(f"{sid!r}: {len(parts)} slots, the grammar has {len(self.slots)} ({sep.join(self.slots)})")
        inputs = {}
        for name, code in zip(self.slots, parts):
            inputs[name] = self.dim[name].by_code(code)["value"]
        return inputs, variant

    def grammar_text(self) -> str:
        sep = (self.spec.get("grammar") or {}).get("separator", "-")
        return sep.join("{" + (self.dim[s].spec.get("slot") or s.upper()) + "}" for s in self.slots) + "[-{RULE}]"

    # ---- personas
    def persona_inputs(self, persona: str, locality: str | None = None) -> dict:
        """A persona's inputs in a locality: a value given per locality (``{"charlottesville": "CX-8", ...}``)
        takes that locality's entry."""
        p = self.personas.get(persona)
        if not p:
            raise FamilyError(f"no persona {persona!r}; the family has {', '.join(self.personas)}")
        loc_dim = (self.spec.get("grammar") or {}).get("locality", "locality")
        out = {}
        loc = locality or p["inputs"].get(loc_dim)
        for k, v in p["inputs"].items():
            if isinstance(v, dict):
                if loc not in v:
                    raise FamilyError(f"persona {persona}: no {k} for {loc}")
                v = v[loc]
            out[k] = v
        if loc:
            out[loc_dim] = loc
        return self.normalise(out)

    def localities(self) -> list[str]:
        loc_dim = (self.spec.get("grammar") or {}).get("locality", "locality")
        return [o["value"] for o in self.dim[loc_dim].options]

    def table_inputs(self) -> set[str]:
        return {i["name"] for t in self.tables for i in t["inputs"]}

    def check(self) -> list[str]:
        """Structural problems: table shapes, inputs that are neither dimensions nor derived, offices, statuses,
        order tags, codes, tags and assumption ids."""
        problems = []
        names = {d.name for d in self.dims} | {d["name"] for d in self.derived}
        for d in self.dims:
            codes = [o["code"] for o in d.options]
            if len(set(codes)) != len(codes):
                problems.append(f"{d.name}: repeated codes")
            for o in d.options:
                if o.get("tag") and o["tag"] not in TAGS:
                    problems.append(f"{d.name}={o['code']}: tag {o['tag']!r}")
                for a in o.get("assumptions") or []:
                    if a not in self.assumptions:
                        problems.append(f"{d.name}={o['code']}: unknown assumption {a}")
        tags = set(MILESTONES)
        for t in self.spec.get("tables") or []:
            problems += dmn.check(t)
            for i in t["inputs"]:
                if i["name"] not in names:
                    problems.append(f"{t['id']}: input {i['name']!r} is not a dimension or a derived input")
            for r in t["rules"]:
                tags.update(r.get("tags") or [])
                if r.get("office") not in self.offices:
                    problems.append(f"{t['id']}/{r.get('id')}: office {r.get('office')!r} is not in offices")
                st = dmn.literal(r["then"][1]) if len(r["then"]) > 1 else None
                if st not in STATUSES:
                    problems.append(f"{t['id']}/{r.get('id')}: status {st!r}")
                if r.get("tag") not in TAGS:
                    problems.append(f"{t['id']}/{r.get('id')}: tag {r.get('tag')!r}")
                for a in r.get("assumptions") or []:
                    if a not in self.assumptions:
                        problems.append(f"{t['id']}/{r.get('id')}: unknown assumption {a}")
                if not (r.get("source") or {}).get("from"):
                    problems.append(f"{t['id']}/{r.get('id')}: no source pointer")
        for o in self.spec.get("order") or []:
            for k in ("first", "then"):
                if o.get(k) not in tags:
                    problems.append(f"order {o.get('id')}: {k} {o.get(k)!r} is no rule's tag or milestone")
        for p in self.personas.values():
            for loc in self.localities():
                try:
                    inp = self.persona_inputs(p["id"], loc)
                    bad = self.violations(inp)
                    if bad:
                        problems.append(f"persona {p['id']} in {loc}: {bad}")
                except FamilyError as e:
                    problems.append(f"persona {p['id']} in {loc}: {e}")
        return problems

    def summary(self) -> dict:
        return {"id": self.id, "title": self.spec.get("title"), "version": self.version, "state": self.spec.get("state"),
                "dimensions": len(self.dims), "tables": len(self.tables),
                "rules": sum(len(t["rules"]) for t in self.tables), "dropped": len(self.dropped),
                "personas": list(self.personas), "variants": list(self.variants), "grammar": self.grammar_text(),
                "serves": sorted(self.spec.get("serves") or {}), "hash": self.content_hash()}


def families() -> list[Family]:
    return [Family.from_file(p) for p in sorted(FAMILIES_DIR.glob("*.json"))] if FAMILIES_DIR.exists() else []


def family_for_question(qid: str) -> Family | None:
    """The family whose ``serves`` names a coverage question."""
    for f in families():
        if qid in (f.spec.get("serves") or {}):
            return f
    return None


# ------------------------------------------------------------------------------------------------ grounding
GROUND_KEYS = ("quote", "quote_sha256", "quote_words", "paraphrase", "url", "capture", "citation", "level")
_QC: dict[str, dict] = {}


def _place_check(file: str) -> dict:
    """lexflow's match of a place file's quotes (``places.check_quotes``), once per file."""
    if file not in _QC:
        from ..municipal import places as P
        spec = copy.deepcopy(source_doc(file, restore=False))     # check_quotes restores what it can itself
        _QC[file] = P.check_quotes(spec, P.state_of(spec) or "va")
    return _QC[file]


def _entry_quote(entry: dict) -> tuple[str | None, str | None]:
    return entry.get("quote"), entry.get("quote_sha256")


def _cites(entry: dict) -> str:
    return " ".join(str(entry.get(k) or "") for k in ("citation", "basis", "source", "item", "step"))


def _fingerprint_match(sha: str, urls: Iterable[str]) -> tuple[bool, str | None]:
    """A withheld quote matched by its fingerprint: the quote fetch recorded that the cited page held it."""
    from ..municipal import quotes as Q
    for u in urls:
        if not u:
            continue
        e = Q.cached(u)
        if e and sha[:24] in set(e.get("found") or []):
            return True, u
    return False, None


def ground_source(src: dict, today: str | None = None) -> dict:
    """Fill one source from its pointer and match it.  Returns the filled source with ``grounding``:
    ``{matched, by, where, why, on}``."""
    from ..municipal import quotes as Q
    from ..store import db
    file, where = split_pointer(src["from"])
    out = {k: v for k, v in src.items() if k not in GROUND_KEYS and k != "grounding"}
    try:
        # the committed form: a quote the place file withholds stays withheld here, whatever this copy holds
        entry = resolve(source_doc(file, restore=False), where)
    except (KeyError, IndexError, TypeError, FamilyError, OSError, ValueError) as e:
        out["grounding"] = {"matched": False, "why": f"the pointer does not resolve: {type(e).__name__}: {e}"}
        return out
    quote, sha = _entry_quote(entry)
    url = entry.get("url") or next((u for u in Q.cited_urls([_cites(entry)])), None)
    out.update({k: v for k, v in (("url", url), ("citation", entry.get("citation") or entry.get("basis") or
                                                  entry.get("source")), ("level", entry.get("level")))
                if v})
    if sha:
        # the words of a site that forbids reposting: the fingerprint and lexflow's paraphrase only
        out["quote_sha256"] = sha
        out["quote_words"] = entry.get("quote_words")
        out["paraphrase"] = entry.get("paraphrase")
        if entry.get("capture"):
            out["capture"] = entry["capture"]
    elif quote:
        out["quote"] = quote
        if Q.policy(url):
            # a quote the place file keeps plain on a NO_REPRINT page: printable only when its words are free
            # (the state code's, a free official page's, an address); otherwise pages show the citation and link
            out["free"] = Q.free_words(quote, "va")
    else:
        out["grounding"] = {"matched": False, "why": "the entry at the pointer holds no quote"}
        return out
    day = (today or db.now())[:10]
    if is_place_file(file):
        item = (_place_check(file).get("items") or {}).get(where) or {}
        if item.get("by"):
            out["grounding"] = {"matched": True, "by": item["by"], "where": item.get("section") or item.get("url"),
                                "on": item.get("on") or day}
            return out
        if out.get("quote_sha256"):
            ok, u = _fingerprint_match(out["quote_sha256"], [entry.get("url"), url] + Q.cited_urls([_cites(entry)]))
            if ok:
                out["grounding"] = {"matched": True, "by": "fingerprint", "where": u, "on": day}
                return out
        out["grounding"] = {"matched": False, "why": item.get("why") or "not matched by lexflow's software"}
        return out
    # a fixture entry (the state backbone): the same matcher over a one-entry process spec
    from ..municipal import places as P
    mini = {"place": "va:state", "process": "backbone_check",
            "legal_basis": [{"citation": entry.get("citation"), "url": entry.get("url"), "quote": quote}]}
    if not quote:
        out["grounding"] = {"matched": False, "why": "a withheld backbone quote cannot be matched here"}
        return out
    qc = P.check_quotes(mini, "va")
    item = (qc.get("items") or {}).get("legal_basis[0]") or {}
    if item.get("by"):
        out["grounding"] = {"matched": True, "by": item["by"], "where": item.get("section") or item.get("url"),
                            "on": item.get("on") or day}
    else:
        out["grounding"] = {"matched": False, "why": item.get("why") or "not matched by lexflow's software"}
    return out


def _sources(spec: dict):
    """Every source in a family spec: (where, holder dict, key)."""
    for t in spec.get("tables") or []:
        for r in t.get("rules") or []:
            for k in ("source", "fee_source", "deadline_source"):
                if isinstance(r.get(k), dict) and r[k].get("from"):
                    yield f"{t['id']}/{r.get('id')}.{k}", r, k
    for o in spec.get("order") or []:
        if isinstance(o.get("source"), dict):
            yield f"order/{o.get('id')}", o, "source"
    for a in spec.get("appeals") or []:
        if isinstance(a.get("source"), dict):
            yield f"appeal/{a.get('id')}", a, "source"
    for d in spec.get("dimensions") or []:
        for o in (d.get("values") or []) + (d.get("bins") or []):
            if isinstance(o.get("source"), dict) and o["source"].get("from"):
                yield f"{d['name']}={o['code']}", o, "source"
    for v in spec.get("variants") or []:
        for i, ov in enumerate(v.get("class_overrides") or []):
            if isinstance(ov.get("source"), dict):
                yield f"variant/{v['id']}[{i}]", ov, "source"


def fill(spec: dict, path: Path | None = None, log=print) -> dict:
    """Copy every source's quote from its pointer and match it (in place); then move any NO_REPRINT words a
    pointer restored into the evidence store (``quotes.withhold``) so the file keeps only fingerprints.  Returns
    the grounding report: ``{sources, matched, by, unmatched: [{where, from, why}], fees_unknown: [...]}``."""
    from ..municipal import quotes as Q
    report = {"sources": 0, "matched": 0, "by": {}, "unmatched": []}
    for where, holder, key in list(_sources(spec)):
        report["sources"] += 1
        holder[key] = ground_source(holder[key])
        g = holder[key]["grounding"]
        if g.get("matched"):
            report["matched"] += 1
            report["by"][g["by"]] = report["by"].get(g["by"], 0) + 1
        else:
            report["unmatched"].append({"where": where, "from": holder[key].get("from"), "why": g.get("why")})
            if key == "fee_source":                      # an ungrounded fee is not a known fee
                holder.setdefault("fee", {})["grounded"] = False
            elif key == "deadline_source":
                holder["deadline_grounded"] = False
        if key == "fee_source" and g.get("matched"):
            holder.setdefault("fee", {}).pop("grounded", None)
    if path is not None:
        words = Q.withhold(spec, path=path)
        if words:
            name = spec.get("evidence")
            if name:
                Q.save_evidence(name, words, str(path), merge=True)
            log(f"{len(words)} withheld quotes moved to the evidence store")
    spec["grounding"] = {k: v for k, v in report.items()}
    return report


def write(spec: dict, path: Path) -> None:
    path.write_text(json.dumps(spec, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def main(argv=None) -> int:
    """python -m lexflow.scenarios.family [--fill] [--check] <family file or id>"""
    import argparse
    ap = argparse.ArgumentParser(prog="python -m lexflow.scenarios.family")
    ap.add_argument("family", help="a family id (fixtures/families/<id>.json) or a path")
    ap.add_argument("--fill", action="store_true", help="copy the quotes from the pointers, match them, write the file")
    ap.add_argument("--check", action="store_true", help="structural check and the grounding summary")
    a = ap.parse_args(argv)
    p = Path(a.family) if a.family.endswith(".json") else FAMILIES_DIR / f"{a.family}.json"
    spec = json.loads(p.read_text(encoding="utf-8"))
    if a.fill:
        rep = fill(spec, p)
        write(spec, p)
        print(json.dumps({k: v for k, v in rep.items() if k != "unmatched"}, indent=1))
        for u in rep["unmatched"]:
            print("unmatched:", json.dumps(u, ensure_ascii=False))
    fam = Family(spec, p)
    if a.check or not a.fill:
        probs = fam.check()
        for x in probs:
            print("problem:", x)
        print(json.dumps(fam.summary(), indent=1))
        for d in fam.dropped:
            print("dropped:", json.dumps(d, ensure_ascii=False))
        return 1 if probs else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
