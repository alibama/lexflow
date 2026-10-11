"""Validate and evaluate out/design/bpc_480.dmn, the DMN 1.3 decision requirements for Cal. Bus. & Prof. Code § 480.

``out/`` is not bind-mounted into the container, so copy the model into a fresh directory there first, and remove it
afterwards (Git Bash; ``TMPDIR`` keeps this script's temporary files inside that directory; about five minutes):

    D=$(MSYS_NO_PATHCONV=1 docker exec lexflow-app-1 mktemp -d /tmp/bpc480_run_XXXXXX)
    MSYS_NO_PATHCONV=1 docker cp out/design/bpc_480.dmn lexflow-app-1:$D/bpc_480.dmn
    MSYS_NO_PATHCONV=1 docker exec -i -e TMPDIR=$D lexflow-app-1 python -u - $D/bpc_480.dmn < out/design/check_bpc_480.py
    MSYS_NO_PATHCONV=1 docker exec lexflow-app-1 rm -rf $D

Checks, in order (the script exits 1 if any fails):

1. Schema and tools: the OMG DMN 1.3 XSD (``lexflow.validate.xsd_errors``), dmnlint, and bpmn.io's dmn-moddle import
   (the reader dmn-js and the DokuWiki bpmnio plugin use), which must report no warnings.
2. DRD integrity: every ``href`` resolves; information requirements point at decisions or input data and authority
   requirements at knowledge sources; each table's input columns are exactly the decision's information
   requirements (and a literal expression names exactly them); variable names equal element names; no cycles;
   every decision has an authority requirement to a subdivision of § 480; nothing is left unused; every element
   and requirement has a DMNDI shape or edge.
3. Words: every rule and literal decision quotes the statute verbatim, and the quote sits inside the subdivision it
   cites; each rule's "Source" annotation names its citations, marks each one whose grounding is ``implied`` with
   "(reading)", and quotes its first source; every knowledge source's citation resolves in the index to the
   recorded ``act_id``, and its span equals the gold cross-reference at the same offsets in
   ``fixtures/xref/gold_b.json``, with the same role.
4. Catala's two checks per table, over each table's whole input domain: *conflict* (two UNIQUE rules match) and
   *empty* (no rule matches).
5. Evaluation of the applicants in ``APPLICANTS`` (and their counterfactuals) through the whole DRD with lexflow's
   reference evaluator (``lexflow.dmn_eval``).  Each applicant states, independently of the model, the value of
   every decision (``holds`` names the boolean decisions that are true; every other one must be false), the
   ``basis`` and the rule each table must hit (``path``).  Together the paths reach every rule of every table, and
   the check says so.  Each table is evaluated again by SpiffWorkflow's DMN engine (Python dialect,
   ``lexflow.dmn_xml.write_dmn_split``), and the two must agree.  The four date decisions are FEEL literal
   expressions, which neither engine evaluates; the small FEEL evaluator below handles exactly the grammar they
   use (names, null, booleans, ``date``/``duration`` literals, date minus a years-and-months duration,
   comparisons, ``and``/``or``, parentheses).
6. Equivalence: with no discipline record, the DRD's ``may_deny`` equals ``denial_permitted`` of the FIRST table
   ``conviction_ground`` in ``curated_ask/license_conviction/ca.json`` at every point of that table's grid.  Each
   point is realised by concrete facts (``WINDOW_WAYS``: dates, and present incarceration), and the whole DRD is
   evaluated on them, the four FEEL date decisions included: no decision is overridden.  The dates lie five months
   or more from the seventh anniversary and never after the application, so the curated boolean
   ``within_seven_years`` is not taken to settle the boundary readings; the applicants pin those.
7. Links: the ``RequiredInput`` records in ``lexflow.law.links`` match the DRD's ``lex:requires``, and
   ``propose_links`` run on the gold references of § 480 proposes the DRD's provider for ``conviction_dismissed``.
8. Virginia: the quotes the design note uses for Va. Code § 54.1-204 (and §§ 19.2-392.4, 19.2-392.15) are verbatim
   and sit in the subsection cited.
9. Mutations: copies of the model, each with one semantic mutation (``SEMANTIC_MUTATIONS``: a reading or a date
   boundary changed, a limb of a date decision removed, a row removed, a listed licence dropped, ...) or with one
   rule's output flipped (every rule of every table), are re-checked with groups 4-6.  Every mutant must fail at
   least one of them, and must change the top decision (``may_deny`` or ``basis``) for some applicant; the script
   reports which check caught it and for which applicants the top decision changed.  A mutation that cannot be
   applied (its rule, cell or literal text is not in the model, as after an edit of the model) is reported as a
   failing check, with the reason, and the run goes on.  Then a sweep (``single_changes``) makes every single change
   of these families, each on its own copy:
   * in the four date literals: each comparison operator and connective swapped, ``-`` and ``+`` swapped, each
     duration made shorter and longer by every whole number of months from 1 to 12, each ``*_date`` name replaced
     by each other ``*_date`` name of the same literal, and each conjunct or disjunct dropped;
   * in the tables' input cells: each cell set to "-"; a boolean cell negated, or a "-" boolean cell set to true and
     to false; a list cell negated (put into, or taken out of, ``not(...)``), and each of its values dropped or
     replaced by another allowed value, or another allowed value added;
   * in each complementary pair of list cells (a list and its ``not(...)``): one allowed value dropped from, added
     to, or put in place of another in, both.
   Every one must fail group 4, 5 or 6.  A change outside these families (an output, which the flips cover; two
   unrelated cells at once; a new row; a reworded basis) is not covered.

Nothing is written anywhere except temporary files (SpiffWorkflow's tables and the mutated copies).
"""
from __future__ import annotations

import calendar
import datetime as dt
import itertools
import json
import re
import sys
import tempfile
from pathlib import Path

APP = Path("/app") if Path("/app/lexflow").exists() else Path(__file__).resolve().parents[2]
sys.path.insert(0, str(APP))

from lxml import etree  # noqa: E402

from lexflow.ask import index as I  # noqa: E402
from lexflow.dmn_eval import completeness_gaps, decide, overlaps  # noqa: E402
from lexflow.dmn_xml import write_dmn_split  # noqa: E402
from lexflow.ir import Decision, InputClause, LegalProcessModel, OutputClause, Rule, Source  # noqa: E402
from lexflow.validate import dmnlint, spiff_parser, xsd_errors  # noqa: E402

DMN = "https://www.omg.org/spec/DMN/20191111/MODEL/"
LEX = "https://lexipedia.xyz/ns/lex/1.0"
NS = {"d": DMN, "lex": LEX, "dmndi": "https://www.omg.org/spec/DMN/20191111/DMNDI/"}
B480 = "Cal. BPC § 480"
FAILED: list[str] = []


def check(name: str, ok: bool, detail="") -> bool:
    print(f"  [{'ok' if ok else 'FAIL'}] {name}" + (f": {detail}" if detail not in ("", None) else ""))
    if not ok:
        FAILED.append(name)
    return ok


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.replace("’", "'")).strip()


# ----------------------------------------------------------------- a FEEL subset for the literal decisions
class YM:
    """A FEEL years-and-months duration."""
    def __init__(self, months: int):
        self.months = months


def _duration(text: str) -> YM:
    m = re.fullmatch(r"P(?:(\d+)Y)?(?:(\d+)M)?", text)
    if not m or not any(m.groups()):
        raise ValueError(f"only years-and-months durations are supported: {text!r}")
    return YM(int(m.group(1) or 0) * 12 + int(m.group(2) or 0))


def _shift(d: dt.date, months: int) -> dt.date:
    """date + months, the day clamped to the month's end (XPath/FEEL: 2024-02-29 - P7Y = 2017-02-28)."""
    y, m = divmod(d.year * 12 + d.month - 1 + months, 12)
    return dt.date(y, m + 1, min(d.day, calendar.monthrange(y, m + 1)[1]))


_TOK = re.compile(r'\s*(?:(?P<str>"[^"]*")|(?P<num>\d+(?:\.\d+)?)|(?P<op>!=|<=|>=|=|<|>|\+|-|\(|\)|,)'
                  r'|(?P<name>[A-Za-z_][A-Za-z0-9_]*))')


def feel(expr: str, env: dict):
    toks, pos = [], 0
    while pos < len(expr.rstrip()):
        m = _TOK.match(expr, pos)
        if not m or m.end() == pos:
            raise ValueError(f"cannot parse FEEL near {expr[pos:]!r}")
        toks.append((m.lastgroup, m.group(m.lastgroup)))
        pos = m.end()
    i = 0

    def peek():
        return toks[i] if i < len(toks) else (None, None)

    def take(val=None):
        nonlocal i
        t = toks[i]
        if val is not None and t[1] != val:
            raise ValueError(f"expected {val!r}, got {t[1]!r}")
        i += 1
        return t

    def disj():
        v = conj()
        while peek() == ("name", "or"):
            take()
            w = conj()
            v = True if v is True or w is True else (False if v is False and w is False else None)
        return v

    def conj():
        v = comp()
        while peek() == ("name", "and"):
            take()
            w = comp()
            v = False if v is False or w is False else (True if v is True and w is True else None)
        return v

    def comp():
        a = add()
        if peek()[0] == "op" and peek()[1] in ("=", "!=", "<", "<=", ">", ">="):
            op = take()[1]
            b = add()
            if op in ("=", "!="):
                eq = (a is None and b is None) or (a is not None and b is not None and a == b)
                return eq if op == "=" else not eq
            if a is None or b is None:
                return None
            return {"<": a < b, "<=": a <= b, ">": a > b, ">=": a >= b}[op]
        return a

    def add():
        v = prim()
        while peek() in (("op", "-"), ("op", "+")):
            sign = -1 if take()[1] == "-" else 1
            w = prim()
            if v is None or w is None:
                v = None
            elif isinstance(v, dt.date) and isinstance(w, YM):
                v = _shift(v, sign * w.months)
            else:
                raise ValueError("only date +/- years-and-months duration is supported")
        return v

    def prim():
        kind, val = take()
        if kind == "op" and val == "(":
            v = disj()
            take(")")
            return v
        if kind == "str":
            return val[1:-1]
        if kind == "num":
            return float(val) if "." in val else int(val)
        if kind == "name":
            if val in ("true", "false"):
                return val == "true"
            if val == "null":
                return None
            if val in ("date", "duration") and peek() == ("op", "("):
                take("(")
                arg = take()[1][1:-1]
                take(")")
                return dt.date.fromisoformat(arg) if val == "date" else _duration(arg)
            if val not in env:
                raise KeyError(f"FEEL name {val!r} is not bound")
            return env[val]
        raise ValueError(f"unexpected {val!r}")

    v = disj()
    if i != len(toks):
        raise ValueError(f"trailing tokens in {expr!r}")
    return v


# ----------------------------------------------------------------- reading the model
def ref_id(el) -> str:
    href = el.get("href", "")
    return href[1:] if href.startswith("#") else href


def lex_sources(el) -> list[dict]:
    out = []
    for s in el.findall("d:extensionElements/lex:grounding/lex:source", NS):
        out.append({**dict(s.attrib), "quote": s.findtext("lex:quote", namespaces=NS),
                    "note": s.findtext("lex:note", namespaces=NS)})
    return out


def split_values(text: str | None) -> list[str] | None:
    if not text:
        return None
    return [v.strip() for v in re.findall(r'"[^"]*"|[^,]+', text)]


def to_ir(dec) -> Decision:
    table = dec.find("d:decisionTable", NS)
    inputs = [InputClause(id=i.get("id"), label=i.get("label") or "", expression=i.findtext("d:inputExpression/d:text", namespaces=NS),
                          type_ref=i.find("d:inputExpression", NS).get("typeRef") or "string",
                          values=split_values(i.findtext("d:inputValues/d:text", namespaces=NS)))
              for i in table.findall("d:input", NS)]
    outputs = [OutputClause(id=o.get("id"), label=o.get("label") or "", name=o.get("name") or dec.get("name"),
                            type_ref=o.get("typeRef") or "string") for o in table.findall("d:output", NS)]
    rules = []
    for r in table.findall("d:rule", NS):
        srcs = [Source(citation=s["citation"], section=s["section"], subsection=s.get("subsection"), code=s.get("code", ""),
                       jurisdiction=s.get("jurisdiction", ""), quote=s["quote"], url=s.get("url"),
                       grounding=s.get("grounding", "explicit"), note=s.get("note")) for s in lex_sources(r)]
        rules.append(Rule(id=r.get("id"), inputs=[e.findtext("d:text", namespaces=NS) for e in r.findall("d:inputEntry", NS)],
                          outputs=[e.findtext("d:text", namespaces=NS) for e in r.findall("d:outputEntry", NS)],
                          annotation=r.findtext("d:description", namespaces=NS), sources=srcs))
    return Decision(id=dec.get("id"), name=dec.get("name"), question=dec.findtext("d:question", namespaces=NS),
                    hit_policy=table.get("hitPolicy", "UNIQUE"), inputs=inputs, outputs=outputs, rules=rules)


def annotation_for(sources: list[Source]) -> str:
    """The "Source" annotation a rule shows in dmn-js: its distinct citations, in order, each marked "(reading)"
    when one of its sources has grounding ``implied``, then the first source's quote."""
    cites: dict[str, bool] = {}
    for s in sources:
        cites[s.citation] = cites.get(s.citation, False) or s.grounding == "implied"
    return "; ".join(c + (" (reading)" if implied else "") for c, implied in cites.items()) + f": “{sources[0].quote}”"


def literal_value(text: str):
    t = text.strip()
    if t in ("true", "false"):
        return t == "true"
    if t.startswith('"'):
        return t[1:-1]
    return t


def domain(inp: InputClause) -> list:
    if inp.type_ref == "boolean":
        return [True, False]
    if inp.values:
        return [literal_value(v) for v in inp.values]
    raise ValueError(f"no finite domain for column {inp.id}")


# ----------------------------------------------------------------- § 480 structure, for the subdivision check
ROMAN = {"i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x"}


def outline(text: str) -> list[tuple[int, list[str]]]:
    """(offset, path) for each paragraph of a California section: (a) -> (1) -> (A) -> (i)."""
    out, path, pos = [], [], 0
    for para in text.split("\n\n"):
        start = text.index(para, pos)
        pos = start + len(para)
        marks = re.match(r"^((?:\([A-Za-z0-9.]+\)\s*)+)", para)
        if marks:
            for tok in re.findall(r"\(([A-Za-z0-9.]+)\)", marks.group(1)):
                if tok.isdigit():
                    level = 1
                elif tok.isupper():
                    level = 2
                elif tok in ROMAN and len(path) >= 3:
                    level = 3
                else:
                    level = 0
                path = path[:level] + [tok]
        out.append((start, list(path)))
    return out


def subdivision_of(text: str, offset: int) -> list[str]:
    best = []
    for start, path in outline(text):
        if start <= offset:
            best = path
    return best


def quote_offsets(text: str, quote: str) -> list[int]:
    pattern = r"\s+".join(re.escape(w) for w in quote.replace("’", "'").split())
    return [m.start() for m in re.finditer(pattern, text.replace("’", "'"))]


# ----------------------------------------------------------------- SpiffWorkflow
class _FakeWorkflow:
    def __init__(self):
        from SpiffWorkflow.bpmn.script_engine import PythonScriptEngine
        self.script_engine = PythonScriptEngine()


class _FakeTask:
    def __init__(self, data):
        self.data = dict(data)
        self.workflow = _FakeWorkflow()


class Spiff:
    def __init__(self, decisions: list[Decision]):
        from SpiffWorkflow.dmn.engine.DMNEngine import DMNEngine
        model = LegalProcessModel(id="ca-bpc-480", title="Cal. BPC § 480", jurisdiction="ca",
                                  jurisdiction_name="California", decisions=decisions)
        self.dir = Path(tempfile.mkdtemp(prefix="bpc480_"))
        files = []
        for did, xml in write_dmn_split(model, "python").items():
            p = self.dir / f"{did}.dmn"
            p.write_text(xml, encoding="utf-8")
            files.append(p)
        parser = spiff_parser([], files)
        self.engines = {}
        try:
            for d in decisions:
                dp = parser.dmn_parsers[d.id]
                dp.parse()
                self.engines[d.id] = DMNEngine(dp.decision.decisionTables[0])
        finally:                                # the engines hold the parsed tables; the files are not needed
            import shutil
            shutil.rmtree(self.dir, ignore_errors=True)

    def result(self, did: str, data: dict) -> dict:
        return self.engines[did].result(_FakeTask(data))


# ----------------------------------------------------------------- the DRD as an evaluator
class DRD:
    def __init__(self, root):
        self.root = root
        self.decisions = {d.get("id"): d for d in root.findall("d:decision", NS)}
        self.inputs = {i.get("id"): i for i in root.findall("d:inputData", NS)}
        self.ks = {k.get("id"): k for k in root.findall("d:knowledgeSource", NS)}
        self.name = {**{k: v.get("name") for k, v in self.decisions.items()},
                     **{k: v.get("name") for k, v in self.inputs.items()}}
        self.reqs = {k: [ref_id(r) for r in d.findall("d:informationRequirement/*", NS)]
                     for k, d in self.decisions.items()}
        self.tables = {k: to_ir(d) for k, d in self.decisions.items() if d.find("d:decisionTable", NS) is not None}
        self.literals = {k: d.findtext("d:literalExpression/d:text", namespaces=NS)
                         for k, d in self.decisions.items() if d.find("d:literalExpression", NS) is not None}
        self.findings = [k for k in self.decisions if k not in self.tables and k not in self.literals]
        self.order = self._topo()
        self.spiff = None

    def _topo(self) -> list[str]:
        order, state = [], {}

        def visit(n):
            if state.get(n) == 1:
                raise ValueError(f"cycle through {n}")
            if state.get(n) == 2:
                return
            state[n] = 1
            for r in self.reqs.get(n, []):
                if r in self.decisions:
                    visit(r)
            state[n] = 2
            order.append(n)
        for n in self.decisions:
            visit(n)
        return order

    def evaluate(self, case: dict, spiff: bool = False) -> tuple[dict, dict]:
        """Returns (values by name, rule hit per table decision).  Every decision except a finding is evaluated:
        nothing can be overridden, so no check can bypass a date decision."""
        env = dict(case["inputs"])
        hits = {}
        for did in self.order:
            name = self.name[did]
            if did in self.findings:
                env[name] = case["findings"][name]
            elif did in self.literals:
                env[name] = feel(self.literals[did], env)
            else:
                t = self.tables[did]
                data = {i.expression: env.get(i.expression) for i in t.inputs}
                res = decide(t, data)
                if not res:
                    raise ValueError(f"{did}: no rule matches {data}")
                hits[did] = res.pop("_rule")
                if spiff and self.spiff:
                    sp = self.spiff.result(did, data)
                    if sp != res:
                        raise AssertionError(f"{did}: SpiffWorkflow {sp} != lexflow {res} for {data}")
                env[name] = res[t.outputs[0].name] if len(t.outputs) == 1 else res
        return env, hits


# ----------------------------------------------------------------- the applicants
APPLIED = dt.date(2026, 10, 1)            # every applicant applies on this date; seven years before is 2019-10-01
NO_CONVICTION = dict(offense="(none)", disposition="other", conviction_date=None, conviction_final=False,
                     presently_incarcerated=False, release_date=None, substantially_related=False,
                     sex_offender_tier="none", profession="other")
NO_RELIEF = dict(certificate_of_rehabilitation=False, pardon_or_clemency=False, showing_of_rehabilitation=False,
                 conviction_dismissed=False)
NO_DISCIPLINE = dict(formal_discipline=False, discipline_date=None, misconduct_cause_for_discipline=False,
                     discipline_substantially_related=False, discipline_rests_on_conviction=False,
                     sexual_misconduct_726_729=False)
NO_FINDINGS = dict(serious_felony=False, fiduciary_financial_felony=False)
# the tables, in the order of an applicant's ``path`` (the rule number each must hit)
PATH_TABLES = ("exception_a", "exception_b", "lookback_lifted", "conviction_ground", "discipline_ground",
               "rehabilitation_bar", "dismissal_bar", "conviction_barred", "may_deny")
# every boolean decision; an applicant's ``holds`` names those that must be true, and all others must be false
BOOLEAN_DECISIONS = ("conviction_recent", "incarceration_recent", "discipline_recent", "discipline_older",
                     "exception_a", "exception_b", "lookback_lifted", "conviction_ground", "discipline_ground",
                     "rehabilitation_bar", "dismissal_bar", "conviction_barred", "may_deny")
# the basis each may_deny rule must give: the expected basis of an applicant follows from its may_deny rule
BASIS = {1: "Barred by 480(b) or (c); no discipline ground",
         2: "Barred: the discipline rests on the acts underlying the barred conviction",
         3: "May deny on prior discipline (480(a)(2)) only; the conviction is barred",
         4: "May deny: conviction ground (480(a)(1))",
         5: "May deny: conviction (480(a)(1)) and discipline (480(a)(2)) grounds",
         6: "May deny: prior discipline (480(a)(2))",
         7: "No ground under 480(a)"}
D = dt.date
CONVICTED = dict(disposition="conviction", conviction_final=True, substantially_related=True)


def applicant(aid: str, title: str, holds: str, path: tuple, findings: dict | None = None, **inputs) -> dict:
    return dict(id=aid, title=title, holds=set(holds.split()), path=path,
                inputs={"application_date": APPLIED, **NO_CONVICTION, **NO_RELIEF, **NO_DISCIPLINE, **inputs},
                findings={**NO_FINDINGS, **(findings or {})})


def counterfactual(aid: str, title: str, of: str, holds: str, path: tuple, **change) -> dict:
    return dict(id=aid, title=title, counterfactual_of=of, change=change, holds=set(holds.split()), path=path)


# Each rule of each table is on the path of at least one applicant, and each mutation of check 9 (every rule-output
# flip and every entry of SEMANTIC_MUTATIONS) changes may_deny or basis for at least one applicant (checks 5 and 9
# verify these).  The facts are illustrations, not findings about anyone; F and the both-exceptions row it exercises are
# hypothetical.
APPLICANTS = [
    applicant("A", "Grand theft three years before applying for a contractor's license",
              "conviction_recent conviction_ground may_deny", (3, 3, 4, 3, 1, 4, 2, 4, 4),
              **CONVICTED, offense="PEN 487(a) grand theft", conviction_date=D(2022, 6, 15),
              profession="bpc_d3_ch9_contractor"),
    applicant("B", "Robbery in 2009, released 2014, certificate of rehabilitation, real estate license",
              "exception_a lookback_lifted conviction_ground rehabilitation_bar conviction_barred",
              (1, 3, 2, 5, 1, 1, 2, 2, 1), findings=dict(serious_felony=True),
              **CONVICTED, offense="PEN 211 robbery (PEN 1192.7(c)(19))", conviction_date=D(2009, 3, 2),
              release_date=D(2014, 8, 29), profession="bpc_d4_real_estate", certificate_of_rehabilitation=True),
    counterfactual("B'", "Counterfactual: applicant B without the certificate", "B",
                   "exception_a lookback_lifted conviction_ground may_deny", (1, 3, 2, 5, 1, 4, 2, 4, 4),
                   certificate_of_rehabilitation=False),
    applicant("C", "DUI conviction in 2021, dismissed under PEN 1203.4; Nevada board discipline for it in 2022",
              "conviction_recent conviction_ground discipline_recent dismissal_bar conviction_barred",
              (3, 3, 4, 3, 4, 4, 1, 3, 1),
              **CONVICTED, offense="VEH 23152(a) driving under the influence", conviction_date=D(2021, 1, 11),
              conviction_dismissed=True, formal_discipline=True, discipline_date=D(2022, 5, 2),
              misconduct_cause_for_discipline=True, discipline_substantially_related=True,
              discipline_rests_on_conviction=True),
    applicant("D", "Embezzlement in 2015 that the board's regulations class as a fiduciary financial felony; "
                   "real estate license (listed in (a)(1)(B)(v))",
              "exception_b lookback_lifted conviction_ground may_deny", (3, 1, 3, 5, 1, 4, 2, 4, 4),
              findings=dict(fiduciary_financial_felony=True),
              **CONVICTED, offense="PEN 503 embezzlement (felony)", conviction_date=D(2015, 5, 20),
              profession="bpc_d4_real_estate"),
    # D under each other unit of (a)(1)(B): dropping any one unit from the list changes may_deny for one of them
    *[counterfactual(aid, f"Counterfactual: applicant D, applying for {what}", "D",
                     "exception_b lookback_lifted conviction_ground may_deny", (3, 1, 3, 5, 1, 4, 2, 4, 4),
                     profession=unit)
      for aid, unit, what in (
          ("D1", "bpc_d3_ch6_professional_fiduciary", "a professional fiduciary license ((a)(1)(B)(i), BPC 6500 et seq.)"),
          ("D2", "bpc_d3_ch9_contractor", "a contractor's license ((a)(1)(B)(ii), BPC 7000 et seq.)"),
          ("D3", "bpc_d3_ch11_3_private_investigator",
           "a private investigator license ((a)(1)(B)(iii), BPC 7512 et seq.)"),
          ("D4", "bpc_d3_ch12_funeral_director", "a funeral director license ((a)(1)(B)(iv), BPC 7600 et seq.)"),
          ("D5", "bpc_d3_ch12_cemetery_manager", "a cemetery manager license ((a)(1)(B)(iv), BPC 7600 et seq.)"))],
    applicant("E", "The same kind of felony in 2017, released 2018-06-01, for a license (B) does not list",
              "", (3, 2, 4, 6, 1, 4, 2, 4, 7), findings=dict(fiduciary_financial_felony=True),
              **CONVICTED, offense="PEN 503 embezzlement (felony)", conviction_date=D(2017, 3, 1),
              release_date=D(2018, 6, 1), profession="other"),
    applicant("F", "Hypothetical: a 2013 conviction that is both a serious felony and, under the board's regulations, "
                   "a fiduciary financial felony; contractor's license",
              "exception_a exception_b lookback_lifted conviction_ground may_deny", (1, 1, 1, 5, 1, 4, 2, 4, 4),
              findings=dict(serious_felony=True, fiduciary_financial_felony=True),
              **CONVICTED, offense="(hypothetical)", conviction_date=D(2013, 7, 1), release_date=D(2016, 2, 1),
              profession="bpc_d3_ch9_contractor"),
    applicant("G", "Misdemeanor PEN 647.6(a) in 2012; tier three because of a SARATSO risk level of well above "
                   "average at release (PEN 290(d)(3)(D)), not because of the offense",
              "exception_a lookback_lifted conviction_ground may_deny", (2, 3, 2, 5, 1, 4, 2, 4, 4),
              **CONVICTED, offense="PEN 647.6(a) (misdemeanor)", conviction_date=D(2012, 4, 10),
              release_date=D(2012, 10, 10), sex_offender_tier="tier_three"),
    counterfactual("G'", "Counterfactual: applicant G at tier one (PEN 290(d)(1): a registrable misdemeanor)", "G",
                   "", (3, 3, 4, 6, 1, 4, 2, 4, 7), sex_offender_tier="tier_one"),
    counterfactual("G''", "Counterfactual: applicant G at tier two (PEN 290(d)(2))", "G",
                   "exception_a lookback_lifted conviction_ground may_deny", (2, 3, 2, 5, 1, 4, 2, 4, 4),
                   sex_offender_tier="tier_two"),
    applicant("H", "Arrest in 2024 that ended in a citation, not a conviction (480(d))",
              "", (3, 3, 4, 1, 1, 4, 2, 4, 7), offense="arrest; citation", disposition="other"),
    applicant("I", "Second-degree burglary in 2010; released on 2019-10-01, the seventh anniversary",
              "incarceration_recent conviction_ground may_deny", (3, 3, 4, 4, 1, 4, 2, 4, 4),
              **CONVICTED, offense="PEN 459 burglary (second degree)", conviction_date=D(2010, 5, 5),
              release_date=D(2019, 10, 1)),
    # I' and J' pin the day before the anniversary for a release and a conviction, as R' and T' do for discipline:
    # widening either window by any whole number of months (P7Y1M, ..., P7Y6M, ...) brings that day inside it
    counterfactual("I'", "Counterfactual: applicant I released on 2019-09-30, the day before the seventh anniversary",
                   "I", "", (3, 3, 4, 6, 1, 4, 2, 4, 7), release_date=D(2019, 9, 30)),
    applicant("J", "Forgery conviction on 2019-10-01, the seventh anniversary; probation",
              "conviction_recent conviction_ground may_deny", (3, 3, 4, 3, 1, 4, 2, 4, 4),
              **CONVICTED, offense="PEN 470(d) forgery", conviction_date=D(2019, 10, 1)),
    counterfactual("J'", "Counterfactual: applicant J convicted on 2019-09-30, the day before the seventh anniversary",
                   "J", "", (3, 3, 4, 6, 1, 4, 2, 4, 7), conviction_date=D(2019, 9, 30)),
    applicant("K", "Conviction on 2026-08-20, appeal pending: not final for board action (BPC 7.5(a))",
              "conviction_recent", (3, 3, 4, 7, 1, 4, 2, 4, 7),
              **{**CONVICTED, "conviction_final": False}, offense="PEN 487(a) grand theft",
              conviction_date=D(2026, 8, 20)),
    applicant("L", "Conviction on 2026-10-05, after the application; probation ordered, imposition of sentence "
                   "suspended (final under BPC 7.5(a))",
              "", (3, 3, 4, 6, 1, 4, 2, 4, 7),
              **CONVICTED, offense="PEN 487(a) grand theft", conviction_date=D(2026, 10, 5)),
    counterfactual("L'", "Counterfactual: applicant L convicted on 2026-10-01, the date of application", "L",
                   "conviction_recent conviction_ground may_deny", (3, 3, 4, 3, 1, 4, 2, 4, 4),
                   conviction_date=D(2026, 10, 1)),
    applicant("M", "Reckless driving in 2023, found not substantially related to the license",
              "conviction_recent", (3, 3, 4, 2, 1, 4, 2, 4, 7),
              **{**CONVICTED, "substantially_related": False}, offense="VEH 23103 reckless driving",
              conviction_date=D(2023, 6, 1)),
    applicant("N", "False pretences in 2022; another state's board suspended the applicant's license in 2023 for the "
                   "same acts",
              "conviction_recent conviction_ground discipline_recent discipline_ground may_deny",
              (3, 3, 4, 3, 6, 4, 2, 4, 5),
              **CONVICTED, offense="PEN 532 false pretences", conviction_date=D(2022, 9, 9), formal_discipline=True,
              discipline_date=D(2023, 4, 4), misconduct_cause_for_discipline=True,
              discipline_substantially_related=True, discipline_rests_on_conviction=True),
    applicant("O", "No conviction; discipline in 2023 for conduct that would not be cause for discipline before this "
                   "board",
              "discipline_recent", (3, 3, 4, 1, 2, 4, 2, 4, 7), formal_discipline=True,
              discipline_date=D(2023, 3, 15), discipline_substantially_related=True),
    applicant("P", "No conviction; discipline in 2024, cause for discipline here but not substantially related",
              "discipline_recent", (3, 3, 4, 1, 3, 4, 2, 4, 7), formal_discipline=True,
              discipline_date=D(2024, 1, 10), misconduct_cause_for_discipline=True),
    applicant("Q", "Certificate of rehabilitation for a 2005 conviction; discipline on 2020-11-15 for billing fraud, "
                   "not based on the conviction",
              "discipline_recent discipline_ground rehabilitation_bar conviction_barred may_deny",
              (3, 3, 4, 6, 5, 1, 2, 2, 3),
              **CONVICTED, offense="PEN 459 burglary (second degree)", conviction_date=D(2005, 2, 1),
              certificate_of_rehabilitation=True, formal_discipline=True, discipline_date=D(2020, 11, 15),
              misconduct_cause_for_discipline=True, discipline_substantially_related=True),
    applicant("R", "No conviction; discipline in 2015 by another state's medical board for sexual misconduct with a "
                   "patient (BPC 726 conduct)",
              "discipline_older discipline_ground may_deny", (3, 3, 4, 1, 7, 4, 2, 4, 6), formal_discipline=True,
              discipline_date=D(2015, 6, 1), misconduct_cause_for_discipline=True,
              discipline_substantially_related=True, sexual_misconduct_726_729=True),
    counterfactual("R'", "Counterfactual: applicant R disciplined on 2019-09-30, the day before the seventh anniversary",
                   "R", "discipline_older discipline_ground may_deny", (3, 3, 4, 1, 7, 4, 2, 4, 6),
                   discipline_date=D(2019, 9, 30)),
    applicant("S", "No conviction; discipline on 2019-10-01, the seventh anniversary",
              "discipline_recent discipline_ground may_deny", (3, 3, 4, 1, 5, 4, 2, 4, 6), formal_discipline=True,
              discipline_date=D(2019, 10, 1), misconduct_cause_for_discipline=True,
              discipline_substantially_related=True),
    counterfactual("S'", "Counterfactual: applicant S disciplined on 2026-10-01, the date of application", "S",
                   "discipline_recent discipline_ground may_deny", (3, 3, 4, 1, 5, 4, 2, 4, 6),
                   discipline_date=D(2026, 10, 1)),
    applicant("T", "No conviction; discipline in 2016 for misconduct that is not BPC 726 / 729(a) conduct",
              "discipline_older", (3, 3, 4, 1, 8, 4, 2, 4, 7), formal_discipline=True, discipline_date=D(2016, 8, 1),
              misconduct_cause_for_discipline=True, discipline_substantially_related=True),
    counterfactual("T'", "Counterfactual: applicant T disciplined on 2019-09-30, the day before the seventh anniversary",
                   "T", "discipline_older", (3, 3, 4, 1, 8, 4, 2, 4, 7), discipline_date=D(2019, 9, 30)),
    applicant("U", "No conviction; discipline for BPC 726 conduct whose date is not known",
              "", (3, 3, 4, 1, 9, 4, 2, 4, 7), formal_discipline=True, discipline_date=None,
              misconduct_cause_for_discipline=True, discipline_substantially_related=True,
              sexual_misconduct_726_729=True),
    counterfactual("U'", "Counterfactual: applicant U disciplined on 2026-10-06, after the application", "U",
                   "", (3, 3, 4, 1, 9, 4, 2, 4, 7), discipline_date=D(2026, 10, 6)),
    applicant("V", "Conviction in 2021, pardoned by the Governor",
              "conviction_recent conviction_ground rehabilitation_bar conviction_barred", (3, 3, 4, 3, 1, 2, 2, 2, 1),
              **CONVICTED, offense="PEN 487(a) grand theft", conviction_date=D(2021, 4, 4), pardon_or_clemency=True),
    applicant("W", "Conviction in 2020 with a BPC 482 showing of rehabilitation; discipline in 2021 for the same acts",
              "conviction_recent conviction_ground discipline_recent discipline_ground rehabilitation_bar "
              "conviction_barred", (3, 3, 4, 3, 6, 3, 2, 2, 2),
              **CONVICTED, offense="PEN 532 false pretences", conviction_date=D(2020, 1, 15),
              showing_of_rehabilitation=True, formal_discipline=True, discipline_date=D(2021, 2, 2),
              misconduct_cause_for_discipline=True, discipline_substantially_related=True,
              discipline_rests_on_conviction=True),
    applicant("X", "Conviction in 2020, dismissed under PEN 1203.4 and pardoned",
              "conviction_recent conviction_ground rehabilitation_bar dismissal_bar conviction_barred",
              (3, 3, 4, 3, 1, 2, 1, 1, 1),
              **CONVICTED, offense="PEN 487(a) grand theft", conviction_date=D(2020, 7, 7), pardon_or_clemency=True,
              conviction_dismissed=True),
    applicant("Y", "Forgery convicted in 2017, more than seven years before applying; presently incarcerated for it "
                   "(on the date of application and still)",
              "incarceration_recent conviction_ground may_deny", (3, 3, 4, 4, 1, 4, 2, 4, 4),
              **CONVICTED, offense="PEN 470(d) forgery (several counts)", conviction_date=D(2017, 11, 20),
              presently_incarcerated=True),
    applicant("Z", "Grand theft in 2015 with probation; jailed for it from 2026-10-02 to 2026-10-09, after the "
                   "application; not incarcerated on the date of application, nor since the release",
              "", (3, 3, 4, 6, 1, 4, 2, 4, 7),
              **CONVICTED, offense="PEN 487(a) grand theft", conviction_date=D(2015, 4, 1),
              release_date=D(2026, 10, 9)),
    counterfactual("Z'", "Counterfactual: applicant Z jailed from 2026-09-25 and released on 2026-10-01, the date of "
                         "application", "Z", "incarceration_recent conviction_ground may_deny",
                   (3, 3, 4, 4, 1, 4, 2, 4, 4), release_date=D(2026, 10, 1)),
]


def resolved(applicants=APPLICANTS) -> list[dict]:
    """Applicants with counterfactuals spelled out."""
    by_id = {a["id"]: a for a in applicants}
    out = []
    for a in applicants:
        if a.get("counterfactual_of"):
            base = by_id[a["counterfactual_of"]]
            a = {**a, "inputs": {**base["inputs"], **a["change"]}, "findings": base["findings"]}
        out.append(a)
    return out


def mismatches(a: dict, env: dict, hits: dict) -> list[tuple[str, str]]:
    """(kind, detail) for each way the evaluation differs from what applicant ``a`` states; kind is ``top`` (may_deny
    or basis), ``value`` (another decision) or ``path`` (a table hit another rule)."""
    out = []
    top = env.get("may_deny") or {}
    want_rule = a["path"][-1]
    if top.get("may_deny") != ("may_deny" in a["holds"]):
        out.append(("top", f"may_deny={top.get('may_deny')}"))
    if top.get("basis") != BASIS[want_rule]:
        out.append(("top", f"basis={top.get('basis')!r}"))
    for name in BOOLEAN_DECISIONS:
        if name != "may_deny" and env.get(name) != (name in a["holds"]):
            out.append(("value", f"{name}={env.get(name)}"))
    for name, n in zip(PATH_TABLES, a["path"]):
        if hits.get(f"d_{name}") != f"d_{name}_r{n}":
            out.append(("path", f"{name} hit {hits.get(f'd_{name}')}, not r{n}"))
    return out


# ----------------------------------------------------------------- groups 4-6 as functions (re-run on mutants)
def table_defects(drd: "DRD") -> list[tuple[str, int, int, list, list]]:
    """(decision id, rules, grid points, conflicts, gaps) per table, over each table's whole input domain."""
    out = []
    for did, t in drd.tables.items():
        grid = [dict(zip([i.expression for i in t.inputs], combo))
                for combo in itertools.product(*[domain(i) for i in t.inputs])]
        conflicts = overlaps(t, grid) if t.hit_policy == "UNIQUE" else []
        out.append((did, len(t.rules), len(grid), conflicts, completeness_gaps(t, grid)))
    return out


def evaluate_applicants(drd: "DRD", spiff: bool = False) -> list[tuple[dict, dict | None, dict | None, list]]:
    """(applicant, values, rules hit, mismatches) per applicant; values None when the evaluation failed."""
    out = []
    for a in resolved():
        try:
            env, hits = drd.evaluate(a, spiff=spiff)
        except Exception as e:  # noqa: BLE001 - a gap, a conflict or a SpiffWorkflow disagreement
            out.append((a, None, None, [("error", repr(e)[:300])]))
            continue
        out.append((a, env, hits, mismatches(a, env, hits)))
    return out


_CURATED: list[Decision] = []


def curated_table() -> Decision:
    if not _CURATED:
        facts = json.load(open(APP / "curated_ask/license_conviction/ca.json", encoding="utf-8"))["steps"]
        cur = next(d for d in facts["decisions"] if d["id"] == "conviction_ground")
        _CURATED.append(Decision(
            id="cur", name="cur", hit_policy=cur["hit_policy"],
            inputs=[InputClause(id=f"c_{c['name']}", label=c["label"], expression=c["name"], type_ref=c["type"])
                    for c in cur["inputs"]],
            outputs=[OutputClause(id=f"o_{c['name']}", label=c["label"], name=c["name"], type_ref=c["type"])
                     for c in cur["outputs"]],
            rules=[Rule(id=f"cur_r{i}", inputs=r["when"], outputs=r["then"]) for i, r in enumerate(cur["rules"], 1)]))
    return _CURATED[0]


# The curated input within_seven_years ("Convicted, or released from incarceration (or still incarcerated), within
# seven years before applying"), realised by facts that the DRD's FEEL date decisions then evaluate.  Seven years
# before APPLIED is 2019-10-01; every date is five months or more from it and none is after the application, so the
# boundary readings (part 5, reading 3 of the design note) are left to the applicants.
WINDOW_WAYS = {
    True: [dict(conviction_date=D(2020, 3, 1)),                                   # convicted 6 years 7 months before
           dict(conviction_date=D(2012, 3, 1), release_date=D(2020, 3, 1)),       # released 6 years 7 months before
           dict(conviction_date=D(2012, 3, 1), presently_incarcerated=True),      # still incarcerated
           dict(conviction_date=D(2020, 3, 1), release_date=D(2021, 3, 1))],      # both
    False: [dict(conviction_date=D(2019, 3, 1)),                                  # convicted 7 years 7 months before
            dict(conviction_date=D(2012, 3, 1), release_date=D(2019, 3, 1))],     # released 7 years 7 months before
}


def equivalence(drd: "DRD") -> tuple[int, list]:
    """With no discipline record and a final conviction, may_deny against the curated FIRST table's
    denial_permitted at every realisation of its 32-point grid: (realisations, differences).  The whole DRD is
    evaluated on each realisation, the date decisions included (no override)."""
    cdec = curated_table()
    rehab_ways = {True: [(True, False, False), (False, True, False), (False, False, True)], False: [(False, False, False)]}
    window_ways = WINDOW_WAYS
    listed = "bpc_d4_real_estate"
    lookback_ways = {True: [(True, "none", False, "other"), (False, "tier_two", False, "other"),
                            (False, "tier_three", False, "other"), (False, "none", True, listed)],
                     False: [(False, "none", False, "other"), (False, "tier_one", False, listed),
                             (False, "none", True, "other")]}
    n, diff = 0, []
    for g in itertools.product([True, False], repeat=5):
        cur_in = dict(zip(["dismissed", "rehabilitated", "substantially_related", "within_seven_years",
                           "lookback_exception"], g))
        want = decide(cdec, cur_in)["denial_permitted"]
        for rw, ww, lw in itertools.product(rehab_ways[cur_in["rehabilitated"]], window_ways[cur_in["within_seven_years"]],
                                            lookback_ways[cur_in["lookback_exception"]]):
            case = {"inputs": {"application_date": APPLIED, **NO_CONVICTION, **NO_DISCIPLINE, **ww,
                               "offense": "x", "disposition": "conviction", "conviction_final": True,
                               "profession": lw[3], "substantially_related": cur_in["substantially_related"],
                               "sex_offender_tier": lw[1], "certificate_of_rehabilitation": rw[0],
                               "pardon_or_clemency": rw[1], "showing_of_rehabilitation": rw[2],
                               "conviction_dismissed": cur_in["dismissed"]},
                    "findings": dict(serious_felony=lw[0], fiduciary_financial_felony=lw[2])}
            try:
                env, _ = drd.evaluate(case)
                got = env["may_deny"]["may_deny"]
            except (ValueError, KeyError) as e:
                got = repr(e)[:120]
            n += 1
            if got != want:
                diff.append((cur_in, rw, ww, lw, got))
    return n, diff


def semantic_failures(drd: "DRD") -> tuple[list[str], list[str]]:
    """Groups 4-6, quietly: (the checks that fail, the applicants whose may_deny or basis differs from what they
    state).  A difference on the curated grid is a failing check, but it is not counted as an applicant's."""
    fails, top = [], []
    for did, _, _, conflicts, gaps in table_defects(drd):
        if conflicts or gaps:
            fails.append(f"Catala check on {did} ({'conflict' if conflicts else 'empty'})")
    for a, _, _, mm in evaluate_applicants(drd):
        if mm:
            fails.append(f"applicant {a['id']} ({mm[0][1]})")
            if any(kind == "top" for kind, _ in mm):
                top.append(a["id"])
    _, diff = equivalence(drd)
    if diff:
        fails.append(f"equivalence with the curated table ({len(diff)} realisations differ)")
    return fails, top


# ----------------------------------------------------------------- group 9: mutations of copies of the model
def _one(root, xpath: str):
    r = root.xpath(xpath, namespaces=NS)
    if len(r) != 1:
        raise LookupError(f"{xpath}: {len(r)} matches")
    return r[0]


def _rule(root, rid: str):
    return _one(root, f"//d:rule[@id='{rid}']")


def set_cell(root, rid: str, column: str, text: str) -> None:
    """Set the input entry of rule ``rid`` in the column whose input expression is ``column``."""
    rule = _rule(root, rid)
    exprs = [i.findtext("d:inputExpression/d:text", namespaces=NS) for i in rule.getparent().findall("d:input", NS)]
    rule.findall("d:inputEntry", NS)[exprs.index(column)].find("d:text", NS).text = text


def edit_cell(root, rid: str, column: str, old: str, new: str) -> None:
    rule = _rule(root, rid)
    exprs = [i.findtext("d:inputExpression/d:text", namespaces=NS) for i in rule.getparent().findall("d:input", NS)]
    t = rule.findall("d:inputEntry", NS)[exprs.index(column)].find("d:text", NS)
    if old not in t.text:
        raise LookupError(f"{rid}/{column}: {old!r} not in {t.text!r}")
    t.text = t.text.replace(old, new)


def drop_listed(root, rid: str, column: str, value: str) -> None:
    """Remove the string ``value`` from the list, or ``not(...)`` list, in rule ``rid``'s ``column`` cell."""
    rule = _rule(root, rid)
    exprs = [i.findtext("d:inputExpression/d:text", namespaces=NS) for i in rule.getparent().findall("d:input", NS)]
    t = rule.findall("d:inputEntry", NS)[exprs.index(column)].find("d:text", NS)
    text = t.text.strip()
    negated = text.startswith("not(") and text.endswith(")")
    items = [v.strip() for v in (text[4:-1] if negated else text).split(",")]
    if f'"{value}"' not in items or len(items) < 2:
        raise LookupError(f"{rid}/{column}: cannot drop {value!r} from {text!r}")
    items.remove(f'"{value}"')
    t.text = f"not({','.join(items)})" if negated else ",".join(items)


def set_output(root, rid: str, text: str, k: int = 0) -> None:
    _rule(root, rid).findall("d:outputEntry", NS)[k].find("d:text", NS).text = text


def drop_rule(root, rid: str) -> None:
    r = _rule(root, rid)
    r.getparent().remove(r)


def edit_literal(root, did: str, old: str, new: str) -> None:
    t = _one(root, f"//d:decision[@id='{did}']/d:literalExpression/d:text")
    if t.text.count(old) != 1:
        raise LookupError(f"{did}: {old!r} occurs {t.text.count(old)} times in {t.text!r}")
    t.text = t.text.replace(old, new)


def _steps(*fns):
    return lambda root: [f(root) for f in fns]


def drop_unit(unit: str):
    """Drop one licensing unit from the (a)(1)(B) list, in both rows that carry it (r1 and r2's not(...))."""
    return _steps(lambda r: drop_listed(r, "d_exception_b_r1", "profession", unit),
                  lambda r: drop_listed(r, "d_exception_b_r2", "profession", unit))


# (label, where the mutation comes from, mutation).  "verifier": one of the ten semantic mutations that the
# verifier's note (docs/design/verify-dmn-links.md) found passing the first checks and names; "re-check": one of
# the seven one-line changes its re-check found passing the revised checks; "re-check 2": a window widened by less
# than seven months, which its second re-check found passing; "sweep": a change that the single-change sweep
# (``single_changes``) found passing before the applicants that catch it were added; "": added here, to cover the
# rest of what the note found unchecked (the carve-out, the bar reaching discipline, the date edges, the readings of
# the design note) and the window of each date decision on its own.
SEMANTIC_MUTATIONS = [
    ("(a)(2) 'However' row removed: discipline resting on a dismissed conviction becomes a ground", "verifier",
     _steps(lambda r: drop_rule(r, "d_discipline_ground_r4"),
            lambda r: set_cell(r, "d_discipline_ground_r6", "conviction_dismissed", "-"))),
    ("older § 726 / § 729(a) discipline made a non-ground", "verifier",
     _steps(lambda r: drop_rule(r, "d_discipline_ground_r7"),
            lambda r: set_cell(r, "d_discipline_ground_r8", "sexual_misconduct_726_729", "-"))),
    ("anniversary excluded from conviction_recent (>= becomes >)", "verifier",
     lambda r: edit_literal(r, "d_conviction_recent", ">=", ">")),
    ("anniversary excluded from incarceration_recent (>= becomes >)", "verifier",
     lambda r: edit_literal(r, "d_incarceration_recent", ">=", ">")),
    ("anniversary excluded from discipline_recent (>= becomes >)", "verifier",
     lambda r: edit_literal(r, "d_discipline_recent", ">=", ">")),
    ("discipline window changed from 7 to 5 years", "verifier",
     _steps(lambda r: edit_literal(r, "d_discipline_recent", "P7Y", "P5Y"),
            lambda r: edit_literal(r, "d_discipline_older", "P7Y", "P5Y"))),
    ("incarceration window changed from 7 to 10 years", "verifier",
     lambda r: edit_literal(r, "d_incarceration_recent", "P7Y", "P10Y")),
    ("conviction window changed from 7 to 10 years", "",
     lambda r: edit_literal(r, "d_conviction_recent", "P7Y", "P10Y")),
    ("tier one added to (a)(1)(A)", "",
     _steps(lambda r: edit_cell(r, "d_exception_a_r2", "sex_offender_tier", '"tier_two"', '"tier_one","tier_two"'),
            lambda r: edit_cell(r, "d_exception_a_r3", "sex_offender_tier", 'not("tier_two"',
                                'not("tier_one","tier_two"'))),
    ("the Real Estate Law ((v)) dropped from the (a)(1)(B) list", "", drop_unit("bpc_d4_real_estate")),
    ("the (b)/(c) bar no longer reaches discipline that rests on the barred conviction (reading 2 dropped)", "",
     _steps(lambda r: drop_rule(r, "d_may_deny_r2"),
            lambda r: set_cell(r, "d_may_deny_r3", "discipline_rests_on_conviction", "-"))),
    ("a conviction after the application counts as within seven years", "",
     lambda r: edit_literal(r, "d_conviction_recent", " and conviction_date <= application_date", "")),
    ("discipline after the application counts as within seven years", "",
     lambda r: edit_literal(r, "d_discipline_recent", " and discipline_date <= application_date", "")),
    ("undated or post-application discipline counts as older (the date defect the verifier found)", "",
     _steps(lambda r: drop_rule(r, "d_discipline_ground_r9"),
            lambda r: set_cell(r, "d_discipline_ground_r7", "discipline_older", "-"),
            lambda r: set_cell(r, "d_discipline_ground_r8", "discipline_older", "-"))),
    ("BPC § 7.5(a) finality ignored", "",
     _steps(lambda r: drop_rule(r, "d_conviction_ground_r7"),
            *[(lambda n: lambda r: set_cell(r, f"d_conviction_ground_r{n}", "conviction_final", "-"))(n)
              for n in range(2, 7)])),
    ("(b) and (c) merged with 'and' instead of 'or'", "",
     _steps(lambda r: set_output(r, "d_conviction_barred_r2", "false"),
            lambda r: set_output(r, "d_conviction_barred_r3", "false"))),
    ("the 'presently incarcerated' limb removed from incarceration_recent", "re-check",
     lambda r: edit_literal(r, "d_incarceration_recent", "presently_incarcerated = true or ", "")),
    ("a release after the application counts as within seven years", "re-check",
     lambda r: edit_literal(r, "d_incarceration_recent", " and release_date <= application_date", "")),
    ("the Professional Fiduciaries Act ((i)) dropped from the (a)(1)(B) list", "re-check",
     drop_unit("bpc_d3_ch6_professional_fiduciary")),
    ("the Contractors State License Law ((ii)) dropped from the (a)(1)(B) list", "",
     drop_unit("bpc_d3_ch9_contractor")),
    ("the Private Investigator Act ((iii)) dropped from the (a)(1)(B) list", "re-check",
     drop_unit("bpc_d3_ch11_3_private_investigator")),
    ("funeral directors ((iv)) dropped from the (a)(1)(B) list", "re-check", drop_unit("bpc_d3_ch12_funeral_director")),
    ("cemetery managers ((iv)) dropped from the (a)(1)(B) list", "re-check", drop_unit("bpc_d3_ch12_cemetery_manager")),
    ("discipline_older alone widened from 7 to 10 years", "re-check",
     lambda r: edit_literal(r, "d_discipline_older", "P7Y", "P10Y")),
    ("discipline_recent alone widened from 7 to 10 years", "",
     lambda r: edit_literal(r, "d_discipline_recent", "P7Y", "P10Y")),
    ("the date of application itself excluded from conviction_recent (<= becomes <)", "sweep",
     lambda r: edit_literal(r, "d_conviction_recent", "conviction_date <= application_date",
                            "conviction_date < application_date")),
    ("the date of application itself excluded from incarceration_recent (<= becomes <)", "sweep",
     lambda r: edit_literal(r, "d_incarceration_recent", "release_date <= application_date",
                            "release_date < application_date")),
    ("the date of application itself excluded from discipline_recent (<= becomes <)", "sweep",
     lambda r: edit_literal(r, "d_discipline_recent", "discipline_date <= application_date",
                            "discipline_date < application_date")),
    ("tier two dropped from (a)(1)(A)", "",
     _steps(lambda r: drop_listed(r, "d_exception_a_r2", "sex_offender_tier", "tier_two"),
            lambda r: drop_listed(r, "d_exception_a_r3", "sex_offender_tier", "tier_two"))),
    ("conviction_recent alone widened by one month (P7Y becomes P7Y1M)", "re-check 2",
     lambda r: edit_literal(r, "d_conviction_recent", "P7Y", "P7Y1M")),
    ("incarceration_recent alone widened by one month (P7Y becomes P7Y1M)", "re-check 2",
     lambda r: edit_literal(r, "d_incarceration_recent", "P7Y", "P7Y1M")),
]


def first_failure(drd: "DRD") -> str | None:
    """Groups 4-6 like ``semantic_failures``, but stopping at the first check that fails (for the sweep)."""
    for did, _, _, conflicts, gaps in table_defects(drd):
        if conflicts or gaps:
            return f"group 4 ({did})"
    for a, _, _, mm in evaluate_applicants(drd):
        if mm:
            return f"group 5 (applicant {a['id']}{', may_deny or basis' if any(k == 'top' for k, _ in mm) else ''})"
    return "group 6" if equivalence(drd)[1] else None


_SWAP = {">=": (">", "<="), "<=": ("<", ">="), "<": ("<=",), ">": (">=",), "=": ("!=",), "!=": ("=",),
         "and": ("or",), "or": ("and",)}


def _set_literal(did: str, text: str):
    def apply(root):
        _one(root, f"//d:decision[@id='{did}']/d:literalExpression/d:text").text = text
    return apply


def _set_cells(*cells):
    return lambda root: [set_cell(root, rid, col, text) for rid, col, text in cells]


def _items(cell: str) -> tuple[bool, list[str]]:
    s = cell.strip()
    negated = s.startswith("not(") and s.endswith(")")
    return negated, [v.strip() for v in (s[4:-1] if negated else s).split(",")]


def _join(negated: bool, items: list[str]) -> str:
    return f"not({','.join(items)})" if negated else ",".join(items)


def _ym(months: int) -> str:
    """A years-and-months duration literal: 84 -> P7Y, 85 -> P7Y1M, 6 -> P6M."""
    y, m = divmod(months, 12)
    return "P" + (f"{y}Y" if y else "") + (f"{m}M" if m or not y else "")


def single_changes(drd: "DRD") -> list[tuple[str, object]]:
    """The single-change sweep: (label, mutation) for
    * each FEEL literal decision (the four date decisions): each comparison operator and connective swapped
      (``_SWAP``); each ``-`` and ``+`` between operands swapped; each ``duration("...")`` made shorter and longer by
      every whole number of months from 1 to 12, so that a window moved by less than a year (P7Y1M, P7Y6M, P6Y11M,
      ...) is tried, not only P6Y and P8Y; each ``*_date`` name replaced by each other ``*_date`` name of the same
      literal; and each conjunct or disjunct dropped where what is left still parses;
    * each input cell of each table: set to "-" (when it is not); a boolean cell negated, or a "-" boolean cell set
      to true and to false; a list cell negated (put into ``not(...)``, or taken out of it), each of its values
      dropped (when it has more than one) or replaced by each allowed value it does not list, and each allowed value
      it does not list added;
    * each pair of complementary list cells (a list and its ``not(...)`` in another row, the same column, as in
      exception_a r2/r3, exception_b r1/r2 and conviction_ground r1 against r2-r7): each allowed value dropped from
      both or added to both, and each listed value replaced in both by each allowed value they do not list.
    Outputs are left to the rule-output flips, and changes of two unrelated cells at once are not swept."""
    out = []
    for did, text in drd.literals.items():
        names = {n: None for n in re.findall(r"\b[a-z_][a-z0-9_]*\b", text)}

        def at(start: int, end: int, new: str) -> object:
            return _set_literal(did, text[:start] + new + text[end:])
        for m in re.finditer(r">=|<=|!=|=|<|>|\band\b|\bor\b", text):
            for n in _SWAP[m.group(0)]:
                out.append((f"{did}: {m.group(0)} at {m.start()} -> {n}", at(m.start(), m.end(), n)))
        for m in re.finditer(r"(?<= )[-+](?= )", text):
            n = "+" if m.group(0) == "-" else "-"
            out.append((f"{did}: {m.group(0)} at {m.start()} -> {n}", at(m.start(), m.end(), n)))
        for m in re.finditer(r'duration\("(P[0-9YM]+)"\)', text):
            months = _duration(m.group(1)).months
            for d in [*range(-12, 0), *range(1, 13)]:
                if months + d > 0:
                    out.append((f"{did}: {m.group(1)} -> {_ym(months + d)}",
                                at(m.start(1), m.end(1), _ym(months + d))))
        dates = sorted({n for n in names if n.endswith("_date")})
        for m in re.finditer(r"\b[a-z_][a-z0-9_]*_date\b", text):
            for n in dates:
                if n != m.group(0):
                    out.append((f"{did}: {m.group(0)} at {m.start()} -> {n}", at(m.start(), m.end(), n)))
        for sep in (" and ", " or "):
            parts = text.split(sep)
            for k in range(len(parts) if len(parts) > 1 else 0):
                rest = sep.join(parts[:k] + parts[k + 1:])
                try:
                    feel(rest, names)
                except (ValueError, KeyError, IndexError, TypeError):
                    continue
                out.append((f"{did}: {sep.strip()} part {k + 1} dropped", _set_literal(did, rest)))
    for did, t in drd.tables.items():
        for k, inp in enumerate(t.inputs):
            col, values = inp.expression, [v.strip() for v in (inp.values or [])]
            for r in t.rules:
                cell = r.inputs[k].strip()
                new = [] if cell == "-" else ["-"]
                if inp.type_ref == "boolean":
                    new += ["true", "false"] if cell == "-" else [{"true": "false", "false": "true"}[cell]]
                elif values and cell != "-":
                    negated, items = _items(cell)
                    new += [_join(not negated, items)]
                    new += [_join(negated, [x for x in items if x != v]) for v in items if len(items) > 1]
                    new += [_join(negated, [w if x == v else x for x in items])
                            for v in items for w in values if w not in items]
                    new += [_join(negated, items + [v]) for v in values if v not in items]
                out += [(f"{r.id}[{col}]: {cell[:40]} -> {n[:40]}", _set_cells((r.id, col, n))) for n in new]
            if not values:
                continue
            cells = {r.id: r.inputs[k].strip() for r in t.rules}
            for ra, ca in cells.items():
                for rb, cb in cells.items():
                    if cb != f"not({ca})":
                        continue
                    _, items = _items(ca)
                    pairs = []
                    for v in values:
                        both = [x for x in items if x != v] if v in items else items + [v]
                        pairs.append((f"{v} {'dropped from' if v in items else 'added to'} both", both))
                    pairs += [(f"{v} replaced by {w} in both", [w if x == v else x for x in items])
                              for v in items for w in values if w not in items]
                    out += [(f"{ra}/{rb}[{col}]: {what}", _set_cells((ra, col, _join(False, both)),
                                                                      (rb, col, _join(True, both))))
                            for what, both in pairs if both]
    return out


def sweep(original: bytes) -> tuple[int, dict, list[str]]:
    """Run every single change on a copy of the model: (changes, how many each group caught first, the changes not
    caught).  A change that cannot be applied counts as not caught, with the reason in its label."""
    changes = single_changes(DRD(etree.fromstring(original)))
    caught, survivors = {}, []
    for label, mutate in changes:
        root = etree.fromstring(original)
        try:
            mutate(root)
        except Exception as e:  # noqa: BLE001 - reported as a failure, never as caught
            survivors.append(f"{label} (cannot be applied: {type(e).__name__}: {e})")
            continue
        try:
            how = first_failure(DRD(etree.fromstring(etree.tostring(root))))
        except Exception as e:  # noqa: BLE001 - a model the evaluator cannot load counts as caught
            how = f"load ({type(e).__name__})"
        if how is None:
            survivors.append(label)
        else:
            caught[how.split(" (")[0]] = caught.get(how.split(" (")[0], 0) + 1
    return len(changes), caught, survivors


def flip(rid: str):
    """Flip the (first, boolean) output of rule ``rid``."""
    def apply(root):
        t = _rule(root, rid).findall("d:outputEntry", NS)[0].find("d:text", NS)
        t.text = {"true": "false", "false": "true"}[t.text.strip()]
    return apply


def run_mutant(original: bytes, mutate, path: Path) -> tuple[bool, list[str], list[str]]:
    """Apply ``mutate`` to a copy of the model saved at ``path`` and re-run groups 4-6 on it:
    (the copy differs from the original, the checks that fail, the applicants whose may_deny or basis changed).

    A mutation that cannot be applied - its rule, cell or literal text is not in the model, as after an edit of the
    model (``LookupError`` from the edit helpers), or the edit fails in another way - leaves no copy to re-check.
    The result is then (False, [the reason], []), which ``mutation_verdict`` reports as a failing check, so the run
    goes on and prints every other result and the final ``FAILED:`` line instead of stopping with a traceback."""
    root = etree.fromstring(original)
    try:
        mutate(root)
    except Exception as e:  # noqa: BLE001 - reported as a failing check, never as caught
        return False, [f"the mutation cannot be applied to this model ({type(e).__name__}: {e})"], []
    path.write_bytes(etree.tostring(root, encoding="UTF-8", xml_declaration=True))
    copy_ = path.read_bytes()
    try:
        fails, top = semantic_failures(DRD(etree.fromstring(copy_)))
    except Exception as e:  # noqa: BLE001 - a model the evaluator cannot load counts as caught
        fails, top = [f"the DRD does not load ({type(e).__name__})"], []
    return etree.tostring(etree.fromstring(copy_)) != etree.tostring(etree.fromstring(original)), fails, top


def mutation_verdict(changed: bool, fails: list[str], top: list[str]) -> tuple[bool, str]:
    """(passed, detail) of check 9's line for one mutant, from ``run_mutant``'s result.  A mutant passes only when
    its copy differs from the model and some check fails on it."""
    if not changed:
        return False, "the copy is unchanged" + (f": {fails[0]}" if fails else "")
    if not fails:
        return False, "NOT CAUGHT"
    return True, f"caught by {fails[0]}" + (f"; may_deny or basis changes for {', '.join(top)}" if top else "")


def mutation_test(root) -> None:
    import shutil
    original = etree.tostring(root, encoding="UTF-8", xml_declaration=True)
    fails, _ = semantic_failures(DRD(etree.fromstring(original)))
    check("control: the unmutated model passes groups 4-6", not fails, fails[:3] or "")
    tmp = Path(tempfile.mkdtemp(prefix="bpc480_mutants_"))
    try:
        quiet = []
        for k, (label, origin, mutate) in enumerate(SEMANTIC_MUTATIONS, 1):
            changed, fails, top = run_mutant(original, mutate, tmp / f"semantic_{k:02d}.dmn")
            if changed and fails and not top:
                quiet.append(k)
            check(f"semantic mutation {k:2}{f' ({origin})' if origin else ''}: {label}",
                  *mutation_verdict(changed, fails, top))
        check(f"every one of the {len(SEMANTIC_MUTATIONS)} semantic mutations changes may_deny or basis for some "
              "applicant", not quiet, quiet or "")
        flips = []
        for did, t in DRD(etree.fromstring(original)).tables.items():
            for r in t.rules:
                changed, fails, top = run_mutant(original, flip(r.id), tmp / f"flip_{r.id}.dmn")
                flips.append((r.id, changed and bool(fails), bool(top), fails[0] if fails else None))
        missed = [rid + (f" ({why})" if why else "") for rid, caught, _, why in flips if not caught]
        check(f"every one of the {len(flips)} rule-output flips is caught", not missed,
              missed or f"{len(flips)} flips, {len({f.split(' (')[0] for _, _, _, f in flips if f})} distinct "
                        "first-failing checks")
        hidden = [rid for rid, caught, top, _ in flips if caught and not top]
        check("every rule-output flip changes may_deny or basis for some applicant", not hidden, hidden or "")
        n, caught, survivors = sweep(original)
        check(f"every one of the {n} single changes of the sweep is caught", not survivors,
              survivors[:5] or "; ".join(f"{v} first caught by {k}" for k, v in sorted(caught.items())))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


VA_QUOTES = [
    ("54.1-204", "A", "A person shall not be refused a license, certificate, or registration to practice, pursue, or engage "
                      "in any regulated occupation or profession solely because of a prior criminal conviction, unless the "
                      "criminal conviction directly relates to the occupation or profession for which the license, "
                      "certificate, or registration is sought."),
    ("54.1-204", "A", 'A regulatory board shall not use vague or arbitrary terms, including "good moral character" or '
                      '"moral turpitude" to refuse a license, certificate, or registration.'),
    ("54.1-204", "B", "In determining whether a criminal conviction directly relates to an occupation or profession, the "
                      "regulatory board shall consider the following criteria:"),
    ("54.1-204", "C", "how the criminal history directly relates to the occupation pursuant to subsection B, and how the "
                      "regulatory board weighed the rehabilitation factors in subsection B when making its decision"),
    ("54.1-204", "D", "A regulatory board shall consider the criminal information as contained in the applicant's state or "
                      "national criminal history in lieu of the applicant providing certified copies of such court records"),
    ("19.2-392.15", "C", "Such an application may not be denied solely because of the applicant's refusal to disclose "
                         "information concerning any arrest, charge, or conviction against him that has been sealed."),
    ("19.2-392.4", "B", "Such an application may not be denied solely because of the applicant's refusal to disclose "
                        "information concerning any arrest, criminal charge against him, conviction, or civil offense that "
                        "has been expunged."),
]


def main(path: str) -> int:
    xml = Path(path).read_text(encoding="utf-8")
    root = etree.fromstring(xml.encode())
    drd = DRD(root)
    print(f"{path}: {len(drd.decisions)} decisions ({len(drd.tables)} tables, {len(drd.literals)} literal "
          f"expressions, {len(drd.findings)} findings), {len(drd.inputs)} input data, {len(drd.ks)} knowledge sources, "
          f"{sum(len(t.rules) for t in drd.tables.values())} rules")

    # 1 ---------------------------------------------------------------- schema and tools
    print("1. schema and tools")
    errs = xsd_errors(xml, "dmn")
    check("DMN 1.3 XSD", not errs, errs[:3] or "")
    lint = dmnlint(Path(path))
    check("dmnlint (recommended rules)", lint["ok"], lint["raw"][:300] or "")
    import subprocess
    js = ('import fs from "fs"; import { DmnModdle } from "dmn-moddle";'
          f'const r = await new DmnModdle().fromXML(fs.readFileSync({json.dumps(str(Path(path).resolve()))}, "utf8"));'
          'console.log(JSON.stringify({drg: r.rootElement.drgElement.length, warnings: r.warnings.map(w => w.message)}));')
    try:
        p = subprocess.run(["node", "--input-type=module", "-e", js], cwd=APP / "tools" / "node", capture_output=True,
                           text=True, timeout=120)
        res = json.loads(p.stdout.strip().splitlines()[-1]) if p.returncode == 0 else {"warnings": [p.stderr[:300]]}
        check("bpmn.io dmn-moddle import", not res["warnings"], res["warnings"][:3] or f"{res.get('drg')} DRG elements")
    except (OSError, ValueError, IndexError) as e:
        check("bpmn.io dmn-moddle import", False, repr(e))

    # 2 ---------------------------------------------------------------- DRD integrity
    print("2. DRD integrity")
    ids = {e.get("id") for e in root.iter() if isinstance(e.tag, str) and e.get("id")}
    bad = [(e.getparent().getparent().get("id"), e.get("href")) for e in root.iter()
           if isinstance(e.tag, str) and e.get("href") is not None
           and not (e.get("href").startswith("#") and e.get("href")[1:] in ids)
           and etree.QName(e).localname not in ("usingProcess", "usingTask")]
    check("every internal href resolves", not bad, bad[:5] or "")
    wrong = []
    for did, d in drd.decisions.items():
        for r in d.findall("d:informationRequirement/*", NS):
            if ref_id(r) not in (drd.decisions if etree.QName(r).localname == "requiredDecision" else drd.inputs):
                wrong.append((did, ref_id(r)))
        for r in d.findall("d:authorityRequirement/*", NS):
            if etree.QName(r).localname != "requiredAuthority" or ref_id(r) not in drd.ks:
                wrong.append((did, ref_id(r)))
    for kid, k in drd.ks.items():
        for r in k.findall("d:authorityRequirement/*", NS):
            if ref_id(r) not in drd.ks:
                wrong.append((kid, ref_id(r)))
    check("requirement kinds (decision/input <- information, knowledge source <- authority)", not wrong, wrong[:5] or "")
    mismatch = []
    for did in drd.decisions:
        need = {drd.name[r] for r in drd.reqs[did]}
        if did in drd.tables:
            used = {i.expression for i in drd.tables[did].inputs}
        elif did in drd.literals:
            used = set(re.findall(r"\b[a-z_][a-z0-9_]*\b", drd.literals[did])) - {"and", "or", "null", "true", "false",
                                                                                 "duration", "date", "not"}
        else:
            used = need       # a finding: its requirements are what the finder reads
        if used != need:
            mismatch.append((did, sorted(used ^ need)))
    check("table columns / literal names = information requirements", not mismatch, mismatch[:5] or "")
    var = [e.get("id") for e in list(drd.decisions.values()) + list(drd.inputs.values())
           if e.find("d:variable", NS) is None or e.find("d:variable", NS).get("name") != e.get("name")]
    check("variable name = element name", not var, var[:5] or "")
    check("no cycles", True, f"evaluation order {len(drd.order)} decisions")
    ungoverned = []
    for did, d in drd.decisions.items():
        subs = [ref_id(r) for r in d.findall("d:authorityRequirement/d:requiredAuthority", NS)]
        cites = [drd.ks[s].find("d:extensionElements/lex:reference", NS).get("citation") for s in subs]
        if B480 not in cites:
            ungoverned.append(did)
    check("every decision has an authority requirement to a § 480 subdivision", not ungoverned, ungoverned or "")
    used_in = {r for rs in drd.reqs.values() for r in rs}
    used_ks = {ref_id(e) for e in root.iter() if isinstance(e.tag, str) and etree.QName(e).localname == "requiredAuthority"}
    tops = [d for d in drd.decisions if d not in used_in]
    check("exactly one top decision", tops == ["d_may_deny"], tops)
    unused = [i for i in drd.inputs if i not in used_in] + [k for k in drd.ks if k not in used_ks]
    check("no unused input data or knowledge sources", not unused, unused or "")
    policies = sorted({t.hit_policy for t in drd.tables.values()})
    check("precedence lives in the DRD: every table is UNIQUE (no FIRST, no PRIORITY)", policies == ["UNIQUE"], policies)
    shapes = {s.get("dmnElementRef") for s in root.iterfind(".//dmndi:DMNShape", NS)}
    edges = {s.get("dmnElementRef") for s in root.iterfind(".//dmndi:DMNEdge", NS)}
    reqs = {e.get("id") for e in root.iter() if isinstance(e.tag, str)
            and etree.QName(e).localname in ("informationRequirement", "authorityRequirement")}
    missing = (set(drd.decisions) | set(drd.inputs) | set(drd.ks)) - shapes
    check("DMNDI: a shape per DRG element and an edge per requirement", not missing and reqs <= edges,
          f"{len(shapes)} shapes, {len(edges)} edges" if not missing and reqs <= edges else sorted(missing | (reqs - edges))[:5])

    # 3 ---------------------------------------------------------------- words
    print("3. quotes and references")
    texts: dict[str, tuple[dict, str]] = {}

    def text_for(citation):
        if citation not in texts:
            row = I.lookup("ca", citation)[0]
            texts[citation] = (row, I.text_of("ca", row["id"]))
        return texts[citation]
    n_q, bad_q, bad_sub = 0, [], []
    owners = [(f"{did}.{r.id}", r.sources) for did, t in drd.tables.items() for r in t.rules]
    owners += [(did, [Source(**{k: v for k, v in s.items() if k in Source.model_fields})
                      for s in lex_sources(drd.decisions[did])]) for did in drd.literals]
    no_src = [o for o, srcs in owners if not srcs or not all(s.quote for s in srcs)]
    for owner, srcs in owners:
        for s in srcs:
            n_q += 1
            cite = f"{s.code} § {s.section}"
            row, text = text_for(cite)
            offs = quote_offsets(text, s.quote)
            if not offs:
                bad_q.append(f"{owner}: {s.quote[:50]}")
                continue
            want = (s.subsection or "").split(".") if s.subsection else []
            if want and not any(subdivision_of(text, o)[:len(want)] == want for o in offs):
                bad_sub.append(f"{owner}: cites {s.subsection}, found in "
                               f"{['.'.join(subdivision_of(text, o)) for o in offs]}")
    check("every rule and literal decision has a quoted source", not no_src, no_src[:5] or "")
    check(f"quotes verbatim in the index text ({n_q} quotes)", not bad_q, bad_q[:5] or "")
    check("each quote lies in the subdivision it cites", not bad_sub, bad_sub[:5] or "")
    bad_ann, n_reading = [], 0
    for did, t in drd.tables.items():
        rules_el = {r.get("id"): r for r in drd.decisions[did].iterfind("d:decisionTable/d:rule", NS)}
        for r in t.rules:
            want = annotation_for(r.sources)
            n_reading += want.count(" (reading)")
            if rules_el[r.id].findtext("d:annotationEntry/d:text", namespaces=NS) != want:
                bad_ann.append(r.id)
    check(f"each rule's Source annotation = its citations, implied ones marked (reading) ({n_reading} marks), and "
          "its first quote", not bad_ann, bad_ann[:5] or "")
    gold = next(s for s in json.load(open(APP / "fixtures/xref/gold_b.json", encoding="utf-8"))["sections"]
                if s["citation"] == B480)
    gold_at = {(r["start"], r["end"]): r for r in gold["references"]}
    _, t480 = text_for(B480)
    bad_ks, n_span = [], 0
    for kid, k in drd.ks.items():
        ref = k.find("d:extensionElements/lex:reference", NS)
        if ref.get("citation"):
            row, _ = text_for(ref.get("citation"))
            if row["act_id"] != ref.get("actId"):
                bad_ks.append(f"{kid}: act_id {row['act_id']} != {ref.get('actId')}")
            if k.get("locationURI") != row["url"]:
                bad_ks.append(f"{kid}: locationURI is not the index URL")
        if ref.get("start"):
            n_span += 1
            a, b = int(ref.get("start")), int(ref.get("end"))
            g = gold_at.get((a, b))
            if t480[a:b] != ref.get("span") or not g or g["role"] != ref.get("goldRole"):
                bad_ks.append(f"{kid}: span/gold mismatch at {a}-{b}")
            elif ref.get("role") in ("definition", "prerequisite_process", "scope", "authority", "condition") \
                    and ref.get("role") != g["role"]:
                bad_ks.append(f"{kid}: role {ref.get('role')} != gold {g['role']}")
    check(f"knowledge sources resolve to their act_id; {n_span} spans equal the gold references", not bad_ks,
          bad_ks[:5] or "")
    roles = {}
    for k in drd.ks.values():
        r = k.find("d:extensionElements/lex:reference", NS).get("role")
        roles[r] = roles.get(r, 0) + 1
    print(f"     knowledge-source roles: {roles}")

    # 4 ---------------------------------------------------------------- conflict and empty, per table
    print("4. Catala checks per table (conflict = two UNIQUE rules match; empty = no rule matches)")
    for did, n_rules, n_points, conflicts, gaps in table_defects(drd):
        check(f"{did} ({drd.tables[did].hit_policy}, {n_rules} rules, {n_points} points)", not conflicts and not gaps,
              (f"conflicts {conflicts[:2]}" if conflicts else "") + (f" gaps {gaps[:2]}" if gaps else ""))

    # 5 ---------------------------------------------------------------- applicants
    print("5. applicants (lexflow reference evaluator; every table re-run in SpiffWorkflow)")
    try:
        drd.spiff = Spiff(list(drd.tables.values()))
        spiff_ok = True
    except Exception as e:  # noqa: BLE001 - report, do not hide
        spiff_ok = check("SpiffWorkflow parses every table", False, repr(e)[:300])
    check("the applicants' paths name exactly the DRD's tables", {f"d_{t}" for t in PATH_TABLES} == set(drd.tables),
          sorted(set(drd.tables) ^ {f"d_{t}" for t in PATH_TABLES}) or "")
    declared = {f"d_{t}_r{n}" for a in APPLICANTS for t, n in zip(PATH_TABLES, a["path"])}
    rules = {r.id for t in drd.tables.values() for r in t.rules}
    check(f"every rule of every table is on some applicant's path ({len(rules)} rules, {len(APPLICANTS)} applicants)",
          declared == rules, sorted(rules ^ declared) or "")
    records = []
    for a, env, hits, mm in evaluate_applicants(drd, spiff=spiff_ok):
        if env is None:
            check(f"applicant {a['id']}: {a['title']}", False, mm[0][1])
            continue
        top = env["may_deny"]
        path = " ".join(f"{t}.r{hits[f'd_{t}'].rsplit('_r', 1)[1]}" for t in PATH_TABLES)
        check(f"applicant {a['id']}: {a['title']}", not mm,
              f"may_deny={top['may_deny']} ({top['basis']}); {path}" if not mm else "; ".join(d for _, d in mm[:4]))
        records.append((a["id"], top["may_deny"], path))
    if spiff_ok:
        n, disagree = 0, []
        for did, t in drd.tables.items():      # whole-domain agreement, table by table
            for combo in itertools.product(*[domain(i) for i in t.inputs]):
                data = dict(zip([i.expression for i in t.inputs], combo))
                try:
                    mine = decide(t, data)
                except ValueError as e:
                    mine = repr(e)[:120]
                if isinstance(mine, dict):
                    mine.pop("_rule", None)
                if drd.spiff.result(did, data) != mine:
                    disagree.append((did, data))
                n += 1
        check("SpiffWorkflow and lexflow agree on every table's whole domain", not disagree,
              f"{n} evaluations" if not disagree else disagree[:3])

    # 6 ---------------------------------------------------------------- equivalence with the curated FIRST table
    print("6. equivalence with curated_ask/license_conviction/ca.json conviction_ground (FIRST)")
    n, diff = equivalence(drd)
    check("may_deny = curated denial_permitted on every realisation of its 32-point grid", not diff,
          f"{n} realisations" if not diff else diff[:3])

    # 7 ---------------------------------------------------------------- the link schema agrees with the DRD
    print("7. cross-process links (lexflow.law.links) against the DRD's lex:requires")
    from lexflow.law import links as LK
    needs = {}
    for i in drd.inputs.values():
        r = i.find("d:extensionElements/lex:requires", NS)
        if r is not None:
            needs[i.get("name")] = dict(r.attrib)
    spec = {r.variable: r for r in LK.BPC_480_INPUTS}
    clash = [v for v, r in spec.items() if v not in needs or needs[v].get("status") != r.status
             or needs[v].get("evidence") != r.evidence]
    check("RequiredInput records match the DRD (status type, evidence)", not clash, clash or f"{len(spec)} inputs")
    rep = LK.propose_links("ca.license_conviction", gold["references"], LK.load_catalog(APP), state="ca", source=B480,
                           resolver=LK.index_resolver(), requires=LK.BPC_480_INPUTS, terms=gold.get("terms") or ())
    proposed = {ln.required.rsplit(":", 1)[1]: ln for ln in rep.links if ln.required}
    agree = [v for v, n in needs.items() if n.get("providedBy") and n["providedBy"] != "lexflow:process:ca.license_conviction"
             and v in proposed and proposed[v].provider == n["providedBy"]]
    check("the proposed provider of conviction_dismissed is the DRD's providedBy", "conviction_dismissed" in agree,
          f"{proposed['conviction_dismissed'].provider}, status {proposed['conviction_dismissed'].status}"
          if "conviction_dismissed" in proposed else sorted(proposed))
    print(f"     links {[(ln.provider, ln.via) for ln in rep.links]}")
    print(f"     internal {[ln.via for ln in rep.internal]}; missing {[m.via for m in rep.missing]}; "
          f"definitions {[(d.defined_in, d.term) for d in rep.definitions]}")

    # 8 ---------------------------------------------------------------- the Virginia sketch in the design note
    print("8. Virginia: the quotes of the Va. Code § 54.1-204 sketch in docs/design/bpc-480-decision.md")
    bad_va = []
    for ref, sub, quote in VA_QUOTES:
        row = I.lookup("va", ref)[0]
        text = I.text_of("va", row["id"])
        offs = quote_offsets(text, quote)
        letters = {(re.findall(r"(?m)^([A-Z])\. ", text[:o]) or ["-"])[-1] for o in offs}
        if not offs or sub not in letters:
            bad_va.append(f"{ref}({sub}): {quote[:50]} -> {sorted(letters) or 'not found'}")
    check(f"{len(VA_QUOTES)} Virginia quotes verbatim and in the cited subsection", not bad_va, bad_va[:3] or "")

    # 9 ---------------------------------------------------------------- mutation test
    print("9. mutations: every mutated copy of the model must fail group 4, 5 or 6 (and the sweep of single changes)")
    mutation_test(root)

    print("applicants (id, may_deny, rule path):")
    for aid, md, path in records:
        print(f"     {aid:3} {str(md):5} {path}")
    print(f"\n{'ALL CHECKS PASSED' if not FAILED else 'FAILED: ' + '; '.join(FAILED)}")
    return 1 if FAILED else 0


if __name__ == "__main__":
    default = None                  # read from stdin, the script has no sibling model: the path must be given
    if "__file__" in globals() and Path(__file__).name == "check_bpc_480.py":
        default = str(Path(__file__).with_name("bpc_480.dmn"))
    if len(sys.argv) < 2 and default is None:
        sys.exit("usage: python - PATH/bpc_480.dmn < check_bpc_480.py")
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else default))
