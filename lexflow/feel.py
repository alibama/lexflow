"""A small, strict FEEL subset for decision-table cells.

Canonical Lexipedia DMN is written in standard FEEL (DMN 1.3) so it renders
and lints in dmn-js / DokuWiki bpmnio.  SpiffWorkflow evaluates table cells as
Python, so :func:`unary_to_python` / :func:`literal_to_python` translate the
subset below.  :func:`evaluate_unary` is an independent reference evaluator
used by the tests to cross-check SpiffWorkflow.

Supported unary tests:  ``-``, literals (``"x"``, ``12``, ``true``,
``false``, ``null``), comparisons (``< 5``, ``>= 22``), intervals
(``[0..5]``, ``(1..3]``, ``]1..3[``), comma-separated disjunctions of these and
``not(...)``.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

_TOKEN = re.compile(
    r'\s*(?:(?P<str>"(?:[^"\\]|\\.)*")|(?P<num>-?\d+(?:\.\d+)?)|(?P<op><=|>=|<|>|\.\.)'
    r'|(?P<punct>[\[\]\(\),])|(?P<word>[A-Za-z_][A-Za-z0-9_]*))'
)


class FeelError(ValueError):
    pass


def _tokens(text: str) -> list[tuple[str, str]]:
    pos, out = 0, []
    text = text.strip()
    while pos < len(text):
        m = _TOKEN.match(text, pos)
        if not m or m.end() == pos:
            raise FeelError(f"cannot parse FEEL near: {text[pos:]!r}")
        kind = m.lastgroup
        out.append((kind, m.group(kind)))
        pos = m.end()
    return out


@dataclass
class _Test:
    kind: str            # literal | cmp | interval | not | any
    value: object = None
    op: str = ""
    low: object = None
    high: object = None
    low_closed: bool = True
    high_closed: bool = True
    inner: list | None = None


def _literal(tok: tuple[str, str]):
    kind, val = tok
    if kind == "str":
        return bytes(val[1:-1], "utf-8").decode("unicode_escape")
    if kind == "num":
        return float(val) if "." in val else int(val)
    if kind == "word" and val in ("true", "false", "null"):
        return {"true": True, "false": False, "null": None}[val]
    raise FeelError(f"expected a literal, got {val!r}")


def parse_unary(text: str) -> list[_Test] | None:
    """Return a disjunction of tests, or None for the '-' wildcard."""
    text = text.strip()
    if text in ("", "-"):
        return None
    toks = _tokens(text)
    tests, i = [], 0

    def one(i):
        kind, val = toks[i]
        if kind == "word" and val == "not":
            if toks[i + 1] != ("punct", "("):
                raise FeelError("not must be followed by (")
            depth, j = 0, i + 1
            while j < len(toks):
                if toks[j] == ("punct", "("):
                    depth += 1
                elif toks[j] == ("punct", ")"):
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            inner_text = text_from(toks[i + 2:j])
            return _Test("not", inner=parse_unary(inner_text)), j + 1
        if kind == "op" and val in ("<", "<=", ">", ">="):
            return _Test("cmp", op=val, value=_literal(toks[i + 1])), i + 2
        if (kind == "punct" and val in "[(]"):
            low_closed = val == "["
            low = _literal(toks[i + 1])
            if toks[i + 2] != ("op", ".."):
                raise FeelError("interval needs '..'")
            high = _literal(toks[i + 3])
            close = toks[i + 4][1]
            if close not in ("]", ")", "["):
                raise FeelError("bad interval end")
            return _Test("interval", low=low, high=high, low_closed=low_closed,
                         high_closed=close == "]"), i + 5
        return _Test("literal", value=_literal(toks[i])), i + 1

    while i < len(toks):
        test, i = one(i)
        tests.append(test)
        if i < len(toks):
            if toks[i] != ("punct", ","):
                raise FeelError(f"expected ',' in {text!r}")
            i += 1
    return tests


def text_from(toks):
    parts = []
    for kind, val in toks:
        parts.append(val)
    return " ".join(parts).replace("[ ", "[").replace(" ]", "]").replace(" ..", "..").replace(".. ", "..")


def _match(test: _Test, value) -> bool:
    if test.kind == "literal":
        return value == test.value
    if test.kind == "cmp":
        if value is None:
            return False
        return {"<": value < test.value, "<=": value <= test.value,
                ">": value > test.value, ">=": value >= test.value}[test.op]
    if test.kind == "interval":
        if value is None:
            return False
        lo = value >= test.low if test.low_closed else value > test.low
        hi = value <= test.high if test.high_closed else value < test.high
        return lo and hi
    if test.kind == "not":
        return not any(_match(t, value) for t in (test.inner or []))
    raise FeelError(test.kind)


def evaluate_unary(text: str, value) -> bool:
    tests = parse_unary(text)
    return True if tests is None else any(_match(t, value) for t in tests)


def evaluate_literal(text: str):
    toks = _tokens(text)
    if len(toks) != 1:
        raise FeelError(f"only single literals are supported as outputs: {text!r}")
    return _literal(toks[0])


# --------------------------------------------------------------- python dialect
def _py(v) -> str:
    return repr(v)


def _test_to_python(t: _Test) -> str:
    if t.kind == "literal":
        return f"? == {_py(t.value)}"
    if t.kind == "cmp":
        return f"? {t.op} {_py(t.value)}"
    if t.kind == "interval":
        lo = "<=" if t.low_closed else "<"
        hi = "<=" if t.high_closed else "<"
        return f"{_py(t.low)} {lo} ? {hi} {_py(t.high)}"
    if t.kind == "not":
        return "not (" + " or ".join(f"({_test_to_python(x)})" for x in t.inner or []) + ")"
    raise FeelError(t.kind)


def unary_to_python(text: str) -> str:
    """Translate a FEEL unary test into SpiffWorkflow's Python cell dialect."""
    tests = parse_unary(text)
    if tests is None:
        return "-"
    if all(t.kind == "literal" for t in tests):
        if len(tests) == 1:
            return _py(tests[0].value)
        return "? in [" + ", ".join(_py(t.value) for t in tests) + "]"
    return " or ".join(f"({_test_to_python(t)})" for t in tests)


def literal_to_python(text: str) -> str:
    return _py(evaluate_literal(text))
