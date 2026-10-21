"""A deterministic evaluator for lexflow's decision shape, and a reader for DMN 1.3 decision tables.

lexflow's decision shape is the one ``process_models.facts.decisions`` holds (``lexflow.extract.schema.FDecision``)::

    {"id": "response_type", "question": "...", "hit_policy": "FIRST",
     "inputs":  [{"name": "practical", "label": "...", "type": "boolean"}, ...],
     "outputs": [{"name": "response", "label": "...", "type": "string"}, ...],
     "rules":   [{"when": ["false", "-", "-", "-"], "then": ["\\"Not practically possible\\"", "true", "false"],
                  "source": {"section": "2.2-3704", "subsection": "B.4", "quote": "..."}}, ...]}

``when`` cells are FEEL unary tests (``lexflow.feel``: ``-`` for any value, literals ``true``/``false``/``"x"``/``12``,
comparisons ``>= 50`` or ``<50``, intervals ``[1..49]``, comma lists ``"a","b"`` and ``not(...)``); ``then`` cells are
FEEL literals.  Hit policies: FIRST (the first matching rule), UNIQUE (exactly one may match; two is an error),
ANY (several may match only if they agree), COLLECT and RULE ORDER (every matching rule, in order).

The evaluator is independent of SpiffWorkflow and of ``lexflow.dmn_eval`` (which evaluates the compiled IR);
``tests/test_hypotheticals.py`` reconciles the two over every curated decision's whole input grid, the way two
implementations of one rule set should be checked against each other.  ``from_dmn`` reads the decision tables of
a DMN 1.3 file (out/design/bpc_480.dmn is the test case) into the same shape, with each rule's ``lex:grounding``
sources.
"""
from __future__ import annotations

import itertools
import re
import xml.etree.ElementTree as ET
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Iterator

from .. import feel

ENGINE = "lexflow.scenarios.dmn/1"
HIT_POLICIES = ("FIRST", "UNIQUE", "ANY", "COLLECT", "RULE ORDER")
TYPES = ("boolean", "string", "number")


class DecisionError(ValueError):
    """A table that cannot be evaluated as written (a bad cell, a missing input, a UNIQUE or ANY violation)."""


# ------------------------------------------------------------------------------------------------------ cells
@lru_cache(maxsize=8192)
def _tests(cell: str):
    try:
        return feel.parse_unary(cell)
    except (feel.FeelError, IndexError) as e:
        raise DecisionError(f"cannot read the cell {cell!r}: {e}") from e


@lru_cache(maxsize=8192)
def literal(cell: str):
    """A ``then`` cell's value (a FEEL literal: a string in quotes, a number, true, false or null)."""
    text = (cell or "").strip()
    if text in ("", "-"):
        return None
    try:
        return feel.evaluate_literal(text)
    except (feel.FeelError, IndexError) as e:
        raise DecisionError(f"cannot read the output {cell!r}: {e}") from e


def matches(cell: str, value) -> bool:
    """Whether ``value`` passes the unary test ``cell``.  A missing value matches only ``-``."""
    tests = _tests((cell or "").strip() or "-")
    if tests is None:
        return True
    if value is None:
        return False
    try:
        return any(feel._match(t, value) for t in tests)
    except TypeError as e:          # a comparison between a number and a string: a modelling error
        raise DecisionError(f"the cell {cell!r} cannot be compared with {value!r}") from e


def values_in(cell: str) -> list:
    """The literal values a cell names (for building finite domains): ``"a","b"`` -> ["a", "b"]; ``>= 2`` -> [2]."""
    out = []
    for t in _tests((cell or "").strip() or "-") or []:
        if t.kind == "literal":
            out.append(t.value)
        elif t.kind == "cmp":
            out.append(t.value)
        elif t.kind == "interval":
            out += [t.low, t.high]
        elif t.kind == "not":
            for x in t.inner or []:
                if x.kind == "literal":
                    out.append(x.value)
    return out


# ---------------------------------------------------------------------------------------------------- shape
def check(decision: dict) -> list[str]:
    """Every problem with a decision's shape (an empty list means it can be evaluated)."""
    problems = []
    did = decision.get("id") or "?"
    hp = decision.get("hit_policy") or "UNIQUE"
    if hp not in HIT_POLICIES:
        problems.append(f"{did}: hit policy {hp!r} is not one of {HIT_POLICIES}")
    ins, outs = decision.get("inputs") or [], decision.get("outputs") or []
    names = [i.get("name") for i in ins]
    if len(set(names)) != len(names) or not all(names):
        problems.append(f"{did}: input names must be present and distinct")
    for i in ins + outs:
        if i.get("type", "string") not in TYPES:
            problems.append(f"{did}: column {i.get('name')!r} has type {i.get('type')!r}")
    for n, r in enumerate(decision.get("rules") or [], 1):
        when, then = r.get("when") or [], r.get("then") or []
        if len(when) != len(ins):
            problems.append(f"{did} rule {n}: {len(when)} input cells for {len(ins)} inputs")
        if len(then) != len(outs):
            problems.append(f"{did} rule {n}: {len(then)} output cells for {len(outs)} outputs")
        for c in when:
            try:
                _tests((c or "").strip() or "-")
            except DecisionError as e:
                problems.append(f"{did} rule {n}: {e}")
        for c in then:
            try:
                literal(c)
            except DecisionError as e:
                problems.append(f"{did} rule {n}: {e}")
    return problems


def rule_matches(decision: dict, rule: dict, data: dict) -> bool:
    return all(matches(c, data.get(i["name"])) for c, i in zip(rule.get("when") or [], decision.get("inputs") or []))


def _outputs(decision: dict, rule: dict) -> dict:
    return {o["name"]: literal(c) for o, c in zip(decision.get("outputs") or [], rule.get("then") or [])}


def evaluate(decision: dict, data: dict, *, strict: bool = True) -> dict:
    """Evaluate one table.  Returns ``{"decision", "hit_policy", "hits": [rule indices, 0-based], "outputs"}``:
    ``outputs`` is one dict for FIRST, UNIQUE and ANY (empty when nothing matches) and a list of dicts for COLLECT
    and RULE ORDER.  With ``strict``, an input the table names but ``data`` lacks is an error (a value of None is
    given, and matches only ``-``)."""
    hp = decision.get("hit_policy") or "UNIQUE"
    if hp not in HIT_POLICIES:
        raise DecisionError(f"{decision.get('id')}: unknown hit policy {hp!r}")
    if strict:
        missing = [i["name"] for i in decision.get("inputs") or [] if i["name"] not in data]
        if missing:
            raise DecisionError(f"{decision.get('id')}: no value for {', '.join(missing)}")
    rules = decision.get("rules") or []
    hits = []
    for n, r in enumerate(rules):
        if rule_matches(decision, r, data):
            hits.append(n)
            if hp == "FIRST":
                break
    if hp == "UNIQUE" and len(hits) > 1:
        raise DecisionError(f"{decision.get('id')}: UNIQUE violated by rules {[h + 1 for h in hits]} for {data}")
    if hp in ("COLLECT", "RULE ORDER"):
        return {"decision": decision.get("id"), "hit_policy": hp, "hits": hits,
                "outputs": [_outputs(decision, rules[h]) for h in hits]}
    if not hits:
        return {"decision": decision.get("id"), "hit_policy": hp, "hits": [], "outputs": {}}
    out = _outputs(decision, rules[hits[0]])
    if hp == "ANY" and any(_outputs(decision, rules[h]) != out for h in hits[1:]):
        raise DecisionError(f"{decision.get('id')}: ANY violated: rules {[h + 1 for h in hits]} disagree for {data}")
    return {"decision": decision.get("id"), "hit_policy": hp, "hits": hits if hp == "ANY" else hits[:1],
            "outputs": out}


# ------------------------------------------------------------------------------------------- finite domains
def domain_of(decision: dict, name: str, extra: Iterable = ()) -> list:
    """A finite domain for one input that reaches every rule boundary: booleans as [True, False]; strings as the
    values the cells name plus one other; numbers as each named value, one below and one above."""
    col = next(i for i in decision["inputs"] if i["name"] == name)
    k = [i["name"] for i in decision["inputs"]].index(name)
    if col.get("type") == "boolean":
        return [True, False]
    seen = list(dict.fromkeys(list(extra) + [v for r in decision.get("rules") or [] for v in values_in(r["when"][k])]))
    if col.get("type") == "number":
        nums = sorted({x for v in seen if isinstance(v, (int, float)) for x in (v - 1, v, v + 1)})
        return nums or [0]
    return [v for v in seen if isinstance(v, str)] + ["(other)"]


def grid(decision: dict, domains: dict | None = None) -> Iterator[dict]:
    """Every combination of the inputs' domains (``domains`` overrides ``domain_of`` per input)."""
    names = [i["name"] for i in decision.get("inputs") or []]
    doms = [(domains or {}).get(n) or domain_of(decision, n) for n in names]
    for combo in itertools.product(*doms):
        yield dict(zip(names, combo))


def gaps(decision: dict, domains: dict | None = None) -> list[dict]:
    """Points of the grid no rule matches (Catala's *empty* check)."""
    return [g for g in grid(decision, domains) if not any(rule_matches(decision, r, g) for r in decision["rules"])]


def conflicts(decision: dict, domains: dict | None = None) -> list[tuple[dict, list[int]]]:
    """Points two or more rules match (a defect for UNIQUE: Catala's *conflict* check)."""
    out = []
    for g in grid(decision, domains):
        hits = [n for n, r in enumerate(decision["rules"]) if rule_matches(decision, r, g)]
        if len(hits) > 1:
            out.append((g, hits))
    return out


def to_ir(decision: dict):
    """The decision as ``lexflow.ir.Decision`` (what ``lexflow.dmn_eval`` and the DMN writer take)."""
    from ..ir import Decision, InputClause, OutputClause, Rule
    did = decision["id"]
    return Decision(id=did, name=did, question=decision.get("question"), hit_policy=decision.get("hit_policy", "UNIQUE"),
                    inputs=[InputClause(id=f"{did}_in_{c['name']}", label=c.get("label") or c["name"], expression=c["name"],
                                        type_ref=c.get("type", "string")) for c in decision["inputs"]],
                    outputs=[OutputClause(id=f"{did}_out_{c['name']}", label=c.get("label") or c["name"], name=c["name"],
                                          type_ref=c.get("type", "string")) for c in decision["outputs"]],
                    rules=[Rule(id=f"{did}_r{n + 1}", inputs=list(r["when"]), outputs=list(r["then"]))
                           for n, r in enumerate(decision["rules"])])


# ---------------------------------------------------------------------------------------------- DMN import
DMN_NS = "https://www.omg.org/spec/DMN/20191111/MODEL/"
LEX_NS = "https://lexipedia.xyz/ns/lex/1.0"


def _ns(tag: str) -> str:
    return f"{{{DMN_NS}}}{tag}"


def _text(el, path: str) -> str | None:
    found = el.find(path)
    return None if found is None or found.text is None else found.text.strip()


def _type(t: str | None) -> str:
    return t if t in TYPES else "string"


def from_dmn(source: str | Path) -> dict:
    """The decision tables of a DMN 1.3 file in lexflow's decision shape.  Returns ``{"tables": [decision, ...],
    "literals": {decision name: FEEL text}, "requires": {decision name: [names it reads]}}``.  A table's input
    names are its input expressions; an output without a name takes the decision's name; each rule keeps its
    ``lex:grounding`` sources (``sources``) and the first one as ``source``."""
    text = Path(source).read_text(encoding="utf-8") if isinstance(source, Path) or (
        isinstance(source, str) and not source.lstrip().startswith("<")) else source
    root = ET.fromstring(text)
    ids = {el.get("id"): el.get("name") for el in root.iter() if el.get("id") and el.get("name")}
    tables, literals, requires = [], {}, {}
    for dec in root.findall(_ns("decision")):
        name = dec.get("name")
        req = []
        for r in dec.findall(_ns("informationRequirement")):
            for child in r:
                href = (child.get("href") or "").lstrip("#")
                if href in ids:
                    req.append(ids[href])
        requires[name] = req
        lit = dec.find(_ns("literalExpression"))
        if lit is not None:
            literals[name] = _text(lit, _ns("text")) or ""
        table = dec.find(_ns("decisionTable"))
        if table is None:
            continue
        inputs = []
        for i in table.findall(_ns("input")):
            expr = i.find(_ns("inputExpression"))
            vals = _text(i, f"{_ns('inputValues')}/{_ns('text')}")
            inputs.append({"name": _text(expr, _ns("text")), "label": i.get("label") or "", "type": _type(expr.get("typeRef")),
                           **({"values": [v.strip() for v in re.findall(r'"[^"]*"|[^,]+', vals)]} if vals else {})})
        outputs = [{"name": o.get("name") or name, "label": o.get("label") or "", "type": _type(o.get("typeRef"))}
                   for o in table.findall(_ns("output"))]
        rules = []
        for r in table.findall(_ns("rule")):
            srcs = []
            for s in r.iter(f"{{{LEX_NS}}}source"):
                srcs.append({**dict(s.attrib), "quote": _text(s, f"{{{LEX_NS}}}quote")})
            rules.append({"id": r.get("id"), "when": [_text(e, _ns("text")) or "-" for e in r.findall(_ns("inputEntry"))],
                          "then": [_text(e, _ns("text")) or "null" for e in r.findall(_ns("outputEntry"))],
                          "annotation": _text(r, _ns("description")), "sources": srcs,
                          "source": srcs[0] if srcs else None})
        tables.append({"id": dec.get("id"), "name": name, "question": _text(dec, _ns("question")),
                       "hit_policy": table.get("hitPolicy", "UNIQUE"), "inputs": inputs, "outputs": outputs,
                       "rules": rules})
    return {"tables": tables, "literals": literals, "requires": requires}


def evaluate_all(tables: Iterable[dict], data: dict, **kw) -> dict[str, dict]:
    """Evaluate several tables on one set of facts: decision id -> result of ``evaluate``."""
    return {t["id"]: evaluate(t, data, **kw) for t in tables}


def as_value(text: Any):
    """A scenario value as a FEEL literal for a ``then`` or a test: True -> 'true', 'x' -> '"x"', 3 -> '3'."""
    if isinstance(text, bool):
        return "true" if text else "false"
    if isinstance(text, (int, float)):
        return str(text)
    if text is None:
        return "null"
    return '"' + str(text).replace('"', '\\"') + '"'
