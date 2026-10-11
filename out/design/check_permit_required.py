"""Validate and evaluate out/design/permit_required.dmn, the DMN 1.3 ``permit_required`` decision for small
residential projects (sheds, playhouses, decks, fences, walls, retaining walls, additions, play equipment, storage
containers, farm buildings, and wiring, plumbing, gas or mechanical work with them) in Virginia, the District of
Columbia and North Carolina, built from state-adopted text only.  The design note is docs/design/permit-required.md;
the verification it answers is docs/design/verify-permit-required.md (findings W1 to W5 and M1 to M6).

``out/`` is not bind-mounted into the container, so copy the model into a fresh directory there first and remove it
afterwards (Git Bash; ``docs/`` is mounted, so the design note is read in place; the run time is in the note's part 7):

    D=$(MSYS_NO_PATHCONV=1 docker exec lexflow-app-1 mktemp -d /tmp/permit_run_XXXXXX)
    MSYS_NO_PATHCONV=1 docker cp out/design/permit_required.dmn lexflow-app-1:$D/permit_required.dmn
    MSYS_NO_PATHCONV=1 docker exec -i -e TMPDIR=$D lexflow-app-1 python -u - $D/permit_required.dmn < out/design/check_permit_required.py
    MSYS_NO_PATHCONV=1 docker exec lexflow-app-1 rm -rf $D

Checks, in order (the script exits 1 if any fails):

1. Schema and tools: the OMG DMN 1.3 XSD (``lexflow.validate.xsd_errors``), dmnlint (recommended rules), and
   bpmn.io's dmn-moddle import (the reader dmn-js and the DokuWiki bpmnio plugin use), with no warnings.
2. DRD integrity: every ``href`` resolves; information requirements point at input data and authority requirements at
   knowledge sources; each table's columns are exactly its decision's information requirements; variable names equal
   element names; every decision has authority requirements and every rule cites only sections that are among them;
   no input data or knowledge source is unused; every table is UNIQUE (precedence is written row by row, never by
   rule order); declared output values cover every output entry; a DMNDI shape per element and an edge per
   requirement.
3. Words: every rule quotes its sources; each quote is verbatim in the lexflow index text of the section it cites
   (regulations or statutes corpus, open-us-law v2026.09.1) and lies in the subdivision it cites; each source's URL
   and act id are the index row's; each knowledge source resolves to its act id and official URL; each rule's
   "Source" annotation is its citations, implied ones marked "(reading)", then its first quote; every implied source
   explains its reading in a note; the readings the model rests on are checked against the text (no deck item in VA
   108.2 or DC 105.2, the items DC 105.2.5 lists, no shed rule in N.C. Gen. Stat. 160D-1110, and the premises of the
   fixes after the verification: the 102.3 whole-code exemptions, the VCC's "Construction", Section 429.5, DC item 7's
   list, wiring in VA 108.2 and DC 105.2.2, "single-family" in NC (c) and (b5)); the input and decision descriptions
   say what the verification asked them to (fence repair is repair in kind only, column caps, the local-amendment
   part, the rule for the officials' discretion); and nothing in the model points at model-code text: no ICC or
   UpCodes link, no IRC or IBC title, no "IRC R105" or "IBC 105" pinpoint.  State text's own references to model-code
   section numbers (VA item 5's "Section 3306", DC item 17's "Section 3103") and to "the IBC" (VA 101.7) are quoted as
   state text.
4. Catala's two checks per table over its whole input domain: *conflict* (two UNIQUE rules match) and *empty* (no
   rule matches).  The domain is exact, not sampled: a numeric column takes every threshold its cells use, the
   midpoints between them and a point beyond each end, so every interval the cells can tell apart is visited.  The
   grid is split by jurisdiction and project: a rule whose jurisdiction or project cell fails cannot match, and the
   columns every rule of a slice leaves "-" cannot change which of them match, so each slice is enumerated over its
   own columns only.  A random sample of the full product is checked as well.  The slices also give the questions an
   answer has to ask for each project (printed).
5. Cases: the projects in ``CASES`` (the four the task names first) through both decisions with lexflow's reference
   evaluator (``lexflow.dmn_eval.decide``).  Each case states, independently of the model, the permit answer, the
   exemption item and the rule it must hit, and what the other-approvals decision must mention; some also name words
   the basis must contain.  Together they hit every rule of both tables.  The cases marked with a finding id (W1 to
   W5, M1 to M6) pin the fixes after the verification: each fails on the model as it stood before them (2026-10-10,
   264,822 bytes, 51 + 12 rules).  Each case, and every point of every slice,
   is evaluated again by SpiffWorkflow's DMN engine (Python dialect, ``lexflow.dmn_xml.write_dmn_split``), and the
   two must agree.
6. The design note: every span in docs/design/permit-required.md inside curly double quotes (“…”) is verbatim state
   text from one of the model's knowledge sources or the few other sections the note quotes (``DOC_EXTRA``); an
   ellipsis inside a quote splits it into parts, each verbatim.  Text from local pages is quoted in straight quotes.
7. Mutations of copies of the model, re-checked with groups 4 and 5; every mutant must fail one of them:
   * each rule's outputs changed (the permit answer to each other value, the exemption, the other approvals; the
     basis text is left alone, since only some cases pin words of it);
   * every single input cell changed: set to "-", a boolean negated (or a "-" set to true and to false), a threshold
     moved by one, a comparison's bound opened or closed, a listed value dropped or another domain value added (or a
     "-" in a column with listed values set to each value);
   * consistent moves that keep the table a partition: each threshold moved by one, or opened or closed, in every
     cell of its column at once; and each boolean column negated in every rule of a slice at once.
   A change of two unrelated cells, a new row or a reworded basis is not covered.

Nothing is written anywhere except temporary files (SpiffWorkflow's tables).
"""
from __future__ import annotations

import functools
import itertools
import json
import random
import re
import sys
import tempfile
from pathlib import Path

APP = Path("/app") if Path("/app/lexflow").exists() else Path(__file__).resolve().parents[2]
sys.path.insert(0, str(APP))

from lxml import etree  # noqa: E402

from lexflow.ask import index as I  # noqa: E402
from lexflow.dmn_eval import decide  # noqa: E402
from lexflow.dmn_xml import write_dmn_split  # noqa: E402
from lexflow.feel import evaluate_unary, parse_unary  # noqa: E402
from lexflow.ir import Decision, InputClause, LegalProcessModel, OutputClause, Rule, Source  # noqa: E402
from lexflow.validate import dmnlint, spiff_parser, xsd_errors  # noqa: E402

DMN = "https://www.omg.org/spec/DMN/20191111/MODEL/"
LEX = "https://lexipedia.xyz/ns/lex/1.0"
NS = {"d": DMN, "lex": LEX, "dmndi": "https://www.omg.org/spec/DMN/20191111/DMNDI/"}
DOC = APP / "docs" / "design" / "permit-required.md"
FAILED: list[str] = []
SLICE_COLS = ("jurisdiction", "project")      # enumerated string columns the grid is split by
DEFAULTS = {"number": 0, "boolean": False}    # facts a case or grid point leaves unset


def check(name: str, ok: bool, detail="") -> bool:
    print(f"  [{'ok' if ok else 'FAIL'}] {name}" + (f": {detail}" if detail not in ("", None, [], {}) else ""))
    if not ok:
        FAILED.append(name)
    return ok


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").replace("’", "'").replace("“", '"').replace("”", '"')).strip()


# ----------------------------------------------------------------- reading the model
def ref_id(el) -> str:
    href = el.get("href", "")
    return href[1:] if href.startswith("#") else href


def lex_sources(el) -> list[dict]:
    return [{**dict(s.attrib), "quote": s.findtext("lex:quote", namespaces=NS), "note": s.findtext("lex:note", namespaces=NS)}
            for s in el.findall("d:extensionElements/lex:grounding/lex:source", NS)]


def split_values(text: str | None) -> list[str] | None:
    return [v.strip() for v in re.findall(r'"[^"]*"|[^,]+', text)] if text else None


def to_ir(dec) -> Decision:
    table = dec.find("d:decisionTable", NS)
    inputs = [InputClause(id=i.get("id"), label=i.get("label") or "",
                          expression=i.findtext("d:inputExpression/d:text", namespaces=NS),
                          type_ref=i.find("d:inputExpression", NS).get("typeRef") or "string",
                          values=split_values(i.findtext("d:inputValues/d:text", namespaces=NS)))
              for i in table.findall("d:input", NS)]
    outputs = [OutputClause(id=o.get("id"), label=o.get("label") or "", name=o.get("name"), type_ref=o.get("typeRef"),
                            values=split_values(o.findtext("d:outputValues/d:text", namespaces=NS)))
               for o in table.findall("d:output", NS)]
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
    cites: dict[str, bool] = {}
    for s in sources:
        cites[s.citation] = cites.get(s.citation, False) or s.grounding == "implied"
    return "; ".join(c + (" (reading)" if implied else "") for c, implied in cites.items()) + f": “{sources[0].quote}”"


def literal_value(text: str):
    t = text.strip()
    if t in ("true", "false"):
        return t == "true"
    return t[1:-1] if t.startswith('"') else t


# ----------------------------------------------------------------- the index texts and their outlines
_TEXTS: dict[tuple, tuple[dict, str]] = {}


def section(state: str, corpus: str, ref: str) -> tuple[dict, str]:
    key = (state, corpus, ref)
    if key not in _TEXTS:
        rows = I.lookup(state, ref, corpus=corpus)
        _TEXTS[key] = (rows[0], I.text_of(state, rows[0]["id"], corpus=corpus)) if rows else ({}, "")
    return _TEXTS[key]


def _lines(text: str):
    pos = 0
    for line in text.split("\n"):
        yield pos, line
        pos += len(line) + 1


def outline_vac(text: str) -> list[tuple[int, list[str]]]:
    """13VAC5-63-*: 'B. Section 108.2 ...' letters, '2. ' / '14.11. ' items, an 'Exceptions:' list."""
    out, letter, item, exc = [], None, None, False
    for start, line in _lines(text):
        if m := re.match(r"^([A-Z])\. ", line):
            letter, item, exc = m.group(1), None, False
        elif line.strip() == "Exceptions:":
            exc, item = True, None
        elif m := re.match(r"^(\d+(?:\.\d+)*)\. ", line):
            item = m.group(1)
        elif not line.startswith("Note"):
            item = None
        out.append((start, ([letter] if letter else []) + (["exceptions"] if exc else []) + ([item] if item else [])))
    return out


def outline_dcmr(text: str) -> list[tuple[int, list[str]]]:
    """DCMR: '105.2.5 ' or 'R101.2 ' section numbers, 'Building:' lists, '8. ' or '7.4 ' items, '(h)' paragraphs."""
    out, sec, lst, item, par = [], None, None, None, None
    for start, line in _lines(text):
        if m := re.match(r"^([A-Z]?\d{3}(?:\.\d+)+)\s", line):
            sec, lst, item, par = m.group(1), None, None, None
        elif line.strip() in ("Building:", "Electrical:", "Gas:", "Mechanical:", "Plumbing:"):
            lst, item, par = line.strip()[:-1].lower(), None, None
        elif m := re.match(r"^\(([a-z0-9]+)\)\s", line):
            par = m.group(1)
        elif m := re.match(r"^(\d{1,2}(?:\.\d+)?)\.?\s", line):
            item, par = m.group(1), None
        out.append((start, [x for x in (sec, lst, item, par) if x]))
    return out


ROMAN = {"i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x"}


def outline_paren(text: str) -> list[tuple[int, list[str]]]:
    """Statutes marked (a) -> (1) -> (A) -> (i), one paragraph each (North Carolina).  An inserted number such as
    '(2a)' is a numbered item; an inserted letter such as '(b5)' is a subsection."""
    out, path, pos = [], [], 0
    for para in text.split("\n\n"):
        start = text.index(para, pos)
        pos = start + len(para)
        marks = re.match(r"^((?:\([A-Za-z0-9.]+\)\s*)+)", para)
        if marks:
            for tok in re.findall(r"\(([A-Za-z0-9.]+)\)", marks.group(1)):
                level = 1 if tok[0].isdigit() else 2 if tok.isupper() else 3 if tok in ROMAN and len(path) >= 3 else 0
                path = path[:level] + [tok]
        out.append((start, list(path)))
    return out


def outline_vacode(text: str) -> list[tuple[int, list[str]]]:
    """Va. Code: 'A. ' subsections and '"Term" means' definitions."""
    out, path, pos = [], [], 0
    for para in text.split("\n\n"):
        start = text.index(para, pos)
        pos = start + len(para)
        if m := re.match(r'^\s*"([^"]+)" means', para):
            path = [m.group(1)]
        elif m := re.match(r"^\s*([A-Z])\. ", para):
            path = [m.group(1)]
        out.append((start, list(path)))
    return out


def outline_for(state: str, corpus: str):
    return {("va", "regulations"): outline_vac, ("dc", "regulations"): outline_dcmr,
            ("nc", "statutes"): outline_paren, ("va", "statutes"): outline_vacode}[(state, corpus)]


def path_at(outline, offset: int) -> list[str]:
    best = []
    for start, path in outline:
        if start <= offset:
            best = path
    return best


def quote_offsets(text: str, quote: str) -> list[int]:
    pattern = r"\s+".join(re.escape(w) for w in norm(quote).split())
    return [m.start() for m in re.finditer(pattern, norm_keep(text))]


def norm_keep(text: str) -> str:
    """The text with the quote characters norm() folds, same length (offsets stay valid)."""
    return text.replace("’", "'").replace("“", '"').replace("”", '"')


# ----------------------------------------------------------------- fast matching (groups 4 and 7) on lexflow's FEEL
match_cell = functools.lru_cache(maxsize=None, typed=True)(evaluate_unary)   # typed: True and 1 are different facts


def matching(t: Decision, data: dict, rules=None) -> list[Rule]:
    return [r for r in (t.rules if rules is None else rules)
            if all(match_cell(c, data.get(i.expression)) for c, i in zip(r.inputs, t.inputs))]


def _numbers(cell: str) -> list:
    out = []
    for tst in parse_unary(cell) or []:
        stack = [tst]
        while stack:
            x = stack.pop()
            if x.kind == "not":
                stack += x.inner or []
            for v in (x.value, x.low, x.high):
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    out.append(v)
    return out


def domain(t: Decision, k: int) -> list:
    inp = t.inputs[k]
    if inp.type_ref == "boolean":
        return [True, False]
    if inp.values:
        return [literal_value(v) for v in inp.values]
    if inp.type_ref == "number":
        ts = sorted({v for r in t.rules for v in _numbers(r.inputs[k])})
        if not ts:
            return [DEFAULTS["number"]]
        mids = [(a + b) / 2 for a, b in zip(ts, ts[1:])]
        return sorted(set(ts + mids + [ts[0] - 1, ts[-1] + 1]))
    raise ValueError(f"no finite domain for column {inp.expression}")


def slices(t: Decision):
    """(slice values, its rules, its columns, its grid) for every value of the slice columns the table has."""
    cols = [i.expression for i in t.inputs]
    keys = [k for k, c in enumerate(cols) if c in SLICE_COLS]
    for combo in itertools.product(*[domain(t, k) for k in keys]):
        fixed = {cols[k]: v for k, v in zip(keys, combo)}
        rules = [r for r in t.rules if all(match_cell(r.inputs[k], fixed[cols[k]]) for k in keys)]
        free = [k for k in range(len(cols)) if k not in keys and any(r.inputs[k].strip() != "-" for r in rules)]
        grid = [{**fixed, **{cols[k]: v for k, v in zip(free, pt)}}
                for pt in itertools.product(*[domain(t, k) for k in free])]
        yield fixed, rules, [cols[k] for k in free], grid


def table_defects(t: Decision, stop: bool = False) -> tuple[int, list, list]:
    """(grid points, conflicts, gaps) over the table's whole domain, slice by slice; ``stop`` returns at the first."""
    n, conflicts, gaps = 0, [], []
    for _, rules, _, grid in slices(t):
        for g in grid:
            n += 1
            hits = matching(t, g, rules)
            if len(hits) > 1:
                conflicts.append((g, [r.id for r in hits]))
            elif not hits:
                gaps.append(g)
            if stop and (conflicts or gaps):
                return n, conflicts, gaps
    return n, conflicts, gaps


def filled(t: Decision, data: dict) -> dict:
    """A grid point or case with every column given: unset numbers 0, booleans false (only "-" cells see them)."""
    out = dict(data)
    for i in t.inputs:
        if out.get(i.expression) is None:
            out[i.expression] = DEFAULTS.get(i.type_ref, "")
    return out


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
        import shutil
        from SpiffWorkflow.dmn.engine.DMNEngine import DMNEngine
        model = LegalProcessModel(id="permit-required", title="permit_required", jurisdiction="va",
                                  jurisdiction_name="Virginia, DC, North Carolina", decisions=decisions)
        d = Path(tempfile.mkdtemp(prefix="permit_spiff_"))
        try:
            files = []
            for did, xml in write_dmn_split(model, "python").items():
                p = d / f"{did}.dmn"
                p.write_text(xml, encoding="utf-8")
                files.append(p)
            parser = spiff_parser([], files)
            self.engines = {}
            for dec in decisions:
                dp = parser.dmn_parsers[dec.id]
                dp.parse()
                self.engines[dec.id] = DMNEngine(dp.decision.decisionTables[0])
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def result(self, did: str, data: dict) -> dict:
        return self.engines[did].result(_FakeTask(data))


# ----------------------------------------------------------------- the cases
def case(cid: str, title: str, jurisdiction: str, project: str, permit: str, exemption: str, rule: int,
         also: tuple[int, list[str]], says: tuple[str, ...] = (), **facts) -> dict:
    """``also``: the other_approvals rule and words its answer must contain; ``says``: words the basis must contain."""
    return dict(id=cid, title=title, facts={"jurisdiction": jurisdiction, "project": project, **facts},
                permit=permit, exemption=exemption, rule=rule, also=also, says=says)


VA_ZONING = (1, ["zoning"])
DC_LAW = (5, ["District", "DDOT"])                 # M3: 12-A DCMR 105.2.4, public space
NC_LAW = (9, ["zoning", "sedimentation"])          # M6: G.S. 160D-1110(e), erosion and sedimentation control plan
DC_HPO = (6, ["Historic Preservation Office", "DDOT"])
DC_FLOOD = (7, ["Floodplain Administrator", "DDOT"])
DC_BOTH = (8, ["Historic Preservation Office", "Floodplain Administrator", "DDOT"])
ONE = dict(one_story=True, attached_to_dwelling=False, group_f1_or_h=False)
# Each case states the answer the state text gives (not the model's), the exemption item and the rule it must hit.
# A finding id in the title (W1 ... M6, docs/design/verify-permit-required.md) marks a case that pins a fix made after
# the verification; each of those fails on the model as it stood before the fixes.
CASES = [
    # the four cases the task names
    case("A1", "Virginia: 200 sq ft one-story detached storage shed (M1: the 108.2 preamble)", "va", "shed", "no",
         "13VAC5-63-80 B item 2", 1, VA_ZONING,
         says=("256 sq ft or less", "owner may still ask for a permit", "must still meet the code", "trade_work"),
         floor_area_sqft=200, **ONE),
    case("A2", "Virginia: 300 sq ft one-story detached storage shed (M2: industrialized buildings)", "va", "shed",
         "yes", "none", 3, VA_ZONING, says=("Over 256 sq ft", "industrialized", "429.5"), floor_area_sqft=300, **ONE),
    case("A3", "Virginia: ground-level deck, 8 in above grade, 120 sq ft, freestanding (M5: 101.7)", "va", "deck",
         "yes", "none", 7, VA_ZONING, says=("No item of 108.2 covers decks", "height above grade", "minor and ordinary",
                                            "101.7"),
         height_ft=0.67, floor_area_sqft=120, attached_to_dwelling=False),
    case("B1", "DC: 48 sq ft garden storage shed, 8 ft high, in a historic district", "dc", "shed", "yes",
         "12-A DCMR 105.2 item 8, not available under 105.2.5", 22, DC_HPO,
         says=("subject only to historic preservation review", "Historic Preservation Office must approve"),
         floor_area_sqft=48, height_ft=8, historic=True),
    # Virginia
    case("A4", "Virginia: shed of exactly 256 sq ft ('does not exceed')", "va", "shed", "no", "13VAC5-63-80 B item 2", 1,
         VA_ZONING, floor_area_sqft=256, **ONE),
    case("A5", "Virginia: shed of 257 sq ft", "va", "shed", "yes", "none", 3, VA_ZONING, floor_area_sqft=257, **ONE),
    case("A6", "Virginia: 200 sq ft shed in a special flood hazard area", "va", "shed", "depends",
         "13VAC5-63-80 B item 2 and Exception 2", 2, (3, ["floodplain"]), says=("special flood hazard area",),
         floor_area_sqft=200, flood_hazard_area=True,
         **ONE),
    case("A7", "Virginia: two-story 200 sq ft shed", "va", "shed", "yes", "none", 4, VA_ZONING, floor_area_sqft=200,
         one_story=False),
    case("A8", "Virginia: 200 sq ft shed attached to the house", "va", "shed", "yes", "none", 5, VA_ZONING,
         floor_area_sqft=200, one_story=True, attached_to_dwelling=True),
    case("A9", "Virginia: 200 sq ft shed the building official classes as Group H", "va", "shed", "yes", "none", 6,
         VA_ZONING, floor_area_sqft=200, one_story=True, attached_to_dwelling=False, group_f1_or_h=True),
    case("A10", "Virginia: 120 sq ft playhouse", "va", "playhouse", "no", "13VAC5-63-80 B item 2", 1, VA_ZONING,
         floor_area_sqft=120, **ONE),
    case("A11", "Virginia: attached deck 6 ft above grade, in a local historic district", "va", "deck", "yes", "none",
         7, (2, ["historic district"]), height_ft=6, attached_to_dwelling=True, historic=True),
    case("A12", "Virginia: replacing deck boards and railings on the existing framing (W4: yes, 14.11 caveat)", "va",
         "deck_resurfacing", "yes", "none", 8, VA_ZONING,
         says=("includes repair", "13VAC5-63-200", "item 14.11", "Ask the building official")),
    case("A13", "Virginia: 6 ft wood privacy fence", "va", "fence", "no", "13VAC5-63-80 B item 5", 9, VA_ZONING,
         height_ft=6),
    case("A14", "Virginia: replacing fence boards", "va", "fence_repair", "no", "13VAC5-63-80 B item 5", 9, VA_ZONING),
    case("A15", "Virginia: 4 ft fence in a special flood hazard area and a historic district", "va", "fence",
         "depends", "13VAC5-63-80 B item 5 and Exception 2", 10, (4, ["historic district", "floodplain"]), height_ft=4,
         flood_hazard_area=True, historic=True),
    case("A16", "Virginia: new swimming-pool barrier fence", "va", "fence", "yes", "none", 11, VA_ZONING,
         safety_barrier=True),
    case("A17", "Virginia: repairing a swimming-pool barrier fence (W4: yes, 14.11 caveat)", "va", "fence_repair",
         "yes", "none", 12, VA_ZONING, says=("includes repair", "item 14.11"), safety_barrier=True),
    case("A18", "Virginia: 6 ft brick garden wall, not counting its column caps (M6)", "va", "masonry_wall", "no",
         "13VAC5-63-80 B item 6", 13, VA_ZONING, says=("column caps",), height_ft=6),
    case("A19", "Virginia: 4 ft masonry wall in a special flood hazard area", "va", "masonry_wall", "depends",
         "13VAC5-63-80 B item 6 and Exception 2", 14, (3, ["floodplain"]), height_ft=4, flood_hazard_area=True),
    case("A20", "Virginia: 7 ft masonry wall", "va", "masonry_wall", "yes", "none", 15, VA_ZONING, height_ft=7),
    case("A21", "Virginia: retaining wall holding back 2.5 ft of soil", "va", "retaining_wall", "no",
         "13VAC5-63-80 B item 7", 16, VA_ZONING, unbalanced_fill_ft=2.5),
    case("A22", "Virginia: 2 ft retaining wall in a special flood hazard area", "va", "retaining_wall", "depends",
         "13VAC5-63-80 B item 7 and Exception 2", 17, (3, ["floodplain"]), unbalanced_fill_ft=2, flood_hazard_area=True),
    case("A23", "Virginia: retaining wall holding back exactly 3 ft of soil ('less than three feet')", "va",
         "retaining_wall", "yes", "none", 18, VA_ZONING, unbalanced_fill_ft=3),
    case("A24", "Virginia: 2 ft retaining wall below a driveway (a surcharge)", "va", "retaining_wall", "yes", "none",
         19, VA_ZONING, unbalanced_fill_ft=2, surcharge_or_liquids=True),
    case("A25", "Virginia: 400 sq ft family-room addition", "va", "addition", "yes", "none", 20, VA_ZONING,
         floor_area_sqft=400),
    case("A26", "Virginia: 200 sq ft shed with a new electrical circuit (M1)", "va", "shed", "yes", "none (trade work)",
         56, VA_ZONING, says=("electric wiring", "trade_work false"), floor_area_sqft=200, trade_work=True, **ONE),
    case("A27", "Virginia: 320 sq ft shipping container used as a storage shed (M2)", "va", "storage_container", "no",
         "13VAC5-63-20 D item 11", 52, VA_ZONING, says=("Exempt from the USBC",), floor_area_sqft=320),
    case("A28", "Virginia: 400 sq ft farm equipment building (M2)", "va", "farm_building", "no",
         "13VAC5-63-20 D item 9", 53, VA_ZONING, says=("Exempt from the USBC",), floor_area_sqft=400),
    case("A29", "Virginia: farm building in a special flood hazard area (M2)", "va", "farm_building", "depends",
         "13VAC5-63-20 D item 9 (flood-proofing)", 54, (3, ["floodplain"]), says=("flood-proofing",),
         flood_hazard_area=True),
    case("A30", "Virginia: backyard swing set and climbing frame (M2)", "va", "playground_equipment", "no",
         "13VAC5-63-20 D item 7", 55, VA_ZONING),
    case("A31", "Virginia: lights wired into a farm building (M1, M2)", "va", "farm_building", "depends",
         "13VAC5-63-20 D item 7, 9 or 11 (the structure)", 57, VA_ZONING, trade_work=True),
    case("A32", "Virginia: 6 ft wood fence with a 120-volt light circuit on its posts (M1)", "va", "fence", "yes",
         "none (trade work)", 56, VA_ZONING, height_ft=6, trade_work=True),
    # District of Columbia
    case("B2", "DC: 50 sq ft garden shed, 9.5 ft high, not historic", "dc", "shed", "no",
         "12-A DCMR 105.2 Building item 8", 21, DC_LAW, floor_area_sqft=50, height_ft=9.5),
    case("B3", "DC: 51 sq ft garden shed", "dc", "shed", "yes", "none", 25, DC_LAW, floor_area_sqft=51, height_ft=8),
    case("B4", "DC: 40 sq ft shed in a Flood Hazard Area", "dc", "shed", "yes",
         "12-A DCMR 105.2 item 8, not available under 105.2.6", 23, DC_FLOOD,
         floor_area_sqft=40, height_ft=8, flood_hazard_area=True),
    case("B5", "DC: 40 sq ft shed, historic district and Flood Hazard Area", "dc", "shed", "yes",
         "12-A DCMR 105.2 item 8, not available under 105.2.5 and 105.2.6", 24, DC_BOTH, floor_area_sqft=40,
         height_ft=8, historic=True, flood_hazard_area=True),
    case("B6", "DC: 40 sq ft shed, 10 ft high ('less than ten feet')", "dc", "shed", "yes", "none", 26, DC_LAW,
         floor_area_sqft=40, height_ft=10),
    case("B7", "DC: a second 40 sq ft shed on a lot that already has an exempted one", "dc", "shed", "yes", "none", 27,
         DC_LAW, floor_area_sqft=40, height_ft=8, other_exempt_shed_on_lot=True),
    case("B8", "DC: 36 sq ft playhouse", "dc", "playhouse", "no", "12-A DCMR 105.2 Building item 13", 28, DC_LAW,
         floor_area_sqft=36),
    case("B9", "DC: 30 sq ft tree house in a historic district (M4: 10-C DCMR 303)", "dc", "playhouse", "depends",
         "12-A DCMR 105.2 Building item 13", 29, DC_HPO,
         says=("does not list item 13", "303.1", "303.3", "Ask the Historic Preservation Office"), floor_area_sqft=30,
         historic=True),
    case("B10", "DC: 30 sq ft playhouse in a Flood Hazard Area", "dc", "playhouse", "yes",
         "12-A DCMR 105.2 item 13, not available under 105.2.6", 30, DC_FLOOD,
         floor_area_sqft=30, flood_hazard_area=True),
    case("B11", "DC: 37 sq ft playhouse", "dc", "playhouse", "yes", "none", 31, DC_LAW, floor_area_sqft=37),
    case("B12", "DC: ground-level deck in a historic district", "dc", "deck", "yes", "none", 32, DC_HPO, height_ft=0.5,
         historic=True),
    case("B13", "DC: replacing deck boards", "dc", "deck_resurfacing", "depends", "12-A DCMR 105.2.2 (ordinary repairs)",
         33, DC_LAW),
    case("B13b", "DC: replacing deck boards in a Flood Hazard Area (W1)", "dc", "deck_resurfacing", "yes",
         "12-A DCMR 105.2.2, not available under 105.2.6", 58, DC_FLOOD, says=("either way", "Floodplain Administrator"),
         flood_hazard_area=True),
    case("B13c", "DC: replacing deck boards in a historic district (historic does not change it)", "dc",
         "deck_resurfacing", "depends", "12-A DCMR 105.2.2 (ordinary repairs)", 33, DC_HPO, historic=True),
    case("B14", "DC: new fence", "dc", "fence", "yes", "none", 34, DC_LAW, height_ft=4),
    case("B14b", "DC: replacing an existing fence in kind, answered as a new fence (W2)", "dc", "fence", "yes", "none",
         34, DC_LAW, says=("Replacing an existing fence, even in kind", "ask the code official"), height_ft=6),
    case("B15", "DC: repair in kind of an existing fence", "dc", "fence_repair", "no", "12-A DCMR 105.2 Building item 4",
         35, DC_LAW),
    case("B16", "DC: fence repair in a historic district", "dc", "fence_repair", "depends",
         "12-A DCMR 105.2 item 4, limited by 105.2.5", 36, DC_HPO, historic=True),
    case("B17", "DC: fence repair in a Flood Hazard Area", "dc", "fence_repair", "yes",
         "12-A DCMR 105.2 item 4, not available under 105.2.6", 37, DC_FLOOD, flood_hazard_area=True),
    case("B18", "DC: fence repair, historic district and Flood Hazard Area", "dc", "fence_repair", "yes",
         "12-A DCMR 105.2 item 4, not available under 105.2.6 (and 105.2.5)", 38, DC_BOTH, historic=True,
         flood_hazard_area=True),
    case("B19", "DC: brick garden wall", "dc", "masonry_wall", "yes", "none", 39, DC_LAW, height_ft=3),
    case("B20", "DC: 4 ft retaining wall (from the bottom of the footing) disturbing 50 sq ft", "dc", "retaining_wall",
         "no", "12-A DCMR 105.2 Building item 10", 40, DC_LAW, height_ft=4, land_disturbance_sqft=50),
    case("B21", "DC: 3 ft retaining wall in a historic district (M4: 10-C DCMR 304.2(e))", "dc", "retaining_wall", "yes",
         "12-A DCMR 105.2 item 10, not available under 105.2.5", 41, DC_HPO, says=("304.2(e)",), height_ft=3,
         land_disturbance_sqft=20, historic=True),
    case("B22", "DC: 3 ft retaining wall in a Flood Hazard Area", "dc", "retaining_wall", "yes",
         "12-A DCMR 105.2 item 10, not available under 105.2.6", 42, DC_FLOOD, height_ft=3,
         land_disturbance_sqft=20, flood_hazard_area=True),
    case("B23", "DC: 3 ft retaining wall, historic district and Flood Hazard Area (M4)", "dc", "retaining_wall", "yes",
         "12-A DCMR 105.2 item 10, not available under 105.2.5 and 105.2.6", 43, DC_BOTH, says=("304.2(e)",),
         height_ft=3, land_disturbance_sqft=20, historic=True, flood_hazard_area=True),
    case("B24", "DC: 5 ft retaining wall", "dc", "retaining_wall", "yes", "none", 44, DC_LAW, height_ft=5,
         land_disturbance_sqft=20),
    case("B25", "DC: 3 ft retaining wall disturbing 51 sq ft", "dc", "retaining_wall", "yes", "none", 45, DC_LAW,
         height_ft=3, land_disturbance_sqft=51),
    case("B26", "DC: rear addition", "dc", "addition", "yes", "none", 46, DC_LAW, floor_area_sqft=200),
    case("B27", "DC: swing set (M2: Building item 12)", "dc", "playground_equipment", "no",
         "12-A DCMR 105.2 Building item 12", 59, DC_LAW),
    case("B28", "DC: swing set in a historic district (M2)", "dc", "playground_equipment", "depends",
         "12-A DCMR 105.2 Building item 12", 60, DC_HPO, says=("does not list item 12", "303.3"), historic=True),
    case("B29", "DC: swing set in a Flood Hazard Area (M2)", "dc", "playground_equipment", "yes",
         "12-A DCMR 105.2 item 12, not available under 105.2.6", 61, DC_FLOOD, flood_hazard_area=True),
    case("B30", "DC: shipping container kept in the yard as storage (M2)", "dc", "storage_container", "depends",
         "none named in 12-A DCMR 105.2", 62, DC_LAW, says=("Ask the code official",), floor_area_sqft=160),
    case("B31", "DC: storage container in a Flood Hazard Area (M2)", "dc", "storage_container", "yes",
         "any 12-A DCMR 105.2 item, not available under 105.2.6", 63, DC_FLOOD, flood_hazard_area=True),
    case("B32", "DC: farm building (M2)", "dc", "farm_building", "yes", "none", 64, DC_LAW, floor_area_sqft=200),
    case("B33", "DC: 40 sq ft garden shed with a new outlet (M1)", "dc", "shed", "yes", "none (trade work)", 65,
         DC_LAW, says=("105.1 item 2",), floor_area_sqft=40, height_ft=8, trade_work=True),
    # North Carolina
    case("C1", "North Carolina: new 12 x 16 ft deck", "nc", "deck", "yes", "none", 47, NC_LAW, floor_area_sqft=192,
         cost_usd=9000),
    case("C2", "North Carolina: replacing deck boards and railings of a house for $8,000", "nc", "deck_resurfacing",
         "no", "G.S. 160D-1110(c)(1)", 48, NC_LAW, says=("$40,000 or less", "143-138(b5)", "single-family"),
         cost_usd=8000, dwelling="single_family"),
    case("C3", "North Carolina: replacing deck boards for exactly $40,000 ('or less')", "nc", "deck_resurfacing", "no",
         "G.S. 160D-1110(c)(1)", 48, NC_LAW, cost_usd=40000, dwelling="single_family"),
    case("C4", "North Carolina: replacing deck boards for $40,001", "nc", "deck_resurfacing", "yes", "none", 49, NC_LAW,
         cost_usd=40001),
    case("C2b", "North Carolina: replacing the deck boards of a duplex for $8,000 (W3)", "nc", "deck_resurfacing",
         "yes", "none", 66, NC_LAW, says=("two-family dwelling",), cost_usd=8000, dwelling="two_family"),
    case("C2c", "North Carolina: replacing the deck boards of a townhouse for $8,000 (W3)", "nc", "deck_resurfacing",
         "depends", "G.S. 160D-1110(c)(1), if a townhouse unit is a single-family residence", 67, NC_LAW,
         cost_usd=8000, dwelling="townhouse"),
    case("C5", "North Carolina: addition in a historic district", "nc", "addition", "yes", "none", 50,
         (10, ["certificate of appropriateness", "sedimentation"]), cost_usd=60000, historic=True),
    case("C6", "North Carolina: 120 sq ft detached storage shed", "nc", "shed", "depends", "not settled by statute", 51,
         NC_LAW, says=("do not settle", "not on disk"), floor_area_sqft=120, cost_usd=3000),
    case("C7", "North Carolina: fence in a flood hazard area", "nc", "fence", "depends", "not settled by statute", 51,
         (11, ["floodplain", "sedimentation"]), flood_hazard_area=True),
    case("C8", "North Carolina: retaining wall, historic district and flood hazard area", "nc", "retaining_wall",
         "depends", "not settled by statute", 51, (12, ["certificate of appropriateness", "floodplain",
                                                        "sedimentation"]),
         historic=True, flood_hazard_area=True),
    case("C9", "North Carolina: hay barn on a farm (M2: 143-138(b4))", "nc", "farm_building", "depends",
         "G.S. 143-138(b4), if the building qualifies and where it is", 68, NC_LAW, says=("143-138(b4)",),
         floor_area_sqft=600),
    case("C10", "North Carolina: deck resurfacing with new deck lighting wiring (M1)", "nc", "deck_resurfacing", "yes",
         "none (trade work)", 69, NC_LAW, says=("(c)(3)",), cost_usd=8000, dwelling="single_family", trade_work=True),
    case("C11", "North Carolina: shipping container kept as storage (M2: not settled)", "nc", "storage_container",
         "depends", "not settled by statute", 51, NC_LAW),
]
MAIN, OTHER = "d_permit_required", "d_other_approvals"


def case_mismatches(tables: dict[str, Decision], c: dict, fast: bool = False) -> list[str]:
    """How the evaluation of case ``c`` differs from what it states (empty when it agrees)."""
    out = []
    for did, want in ((MAIN, c["rule"]), (OTHER, c["also"][0])):
        t = tables[did]
        data = filled(t, c["facts"])
        if fast:
            hits = matching(t, data)
            if len(hits) != 1:
                out.append(f"{did}: {len(hits)} rules match")
                continue
            res = {o.name: literal_value(x) for o, x in zip(t.outputs, hits[0].outputs)} | {"_rule": hits[0].id}
        else:
            try:
                res = decide(t, data)
            except ValueError as e:
                out.append(f"{did}: {e}"[:200])
                continue
            if not res:
                out.append(f"{did}: no rule matches")
                continue
        if res["_rule"] != f"{did}_r{want}":
            out.append(f"{did} hit {res['_rule']}, not r{want}")
        if did == MAIN:
            if res.get("permit") != c["permit"]:
                out.append(f"permit={res.get('permit')!r}, not {c['permit']!r}")
            if res.get("exemption") != c["exemption"]:
                out.append(f"exemption={res.get('exemption')!r}")
            unsaid = [w for w in c["says"] if w.lower() not in (res.get("basis") or "").lower()]
            if unsaid:
                out.append(f"the basis does not say {unsaid}")
        else:
            missing = [w for w in c["also"][1] if w.lower() not in (res.get("also") or "").lower()]
            if missing:
                out.append(f"other approvals do not mention {missing}")
    return out


# ----------------------------------------------------------------- group 7: mutants of the IR
def _with_cell(t: Decision, rid: str, k: int, text: str) -> Decision:
    m = t.model_copy(deep=True)
    for r in m.rules:
        if r.id == rid:
            r.inputs[k] = text
    return m


def _with_output(t: Decision, rid: str, k: int, text: str) -> Decision:
    m = t.model_copy(deep=True)
    for r in m.rules:
        if r.id == rid:
            r.outputs[k] = text
    return m


_CMP = re.compile(r"^\s*(<=|>=|<|>)\s*(-?\d+(?:\.\d+)?)\s*$")
_OPEN = {"<=": "<", "<": "<=", ">=": ">", ">": ">="}


def _num(s: str):
    return float(s) if "." in s else int(s)


def single_changes(t: Decision):
    """(label, mutated table) for every single input-cell change of the families in the docstring (group 7)."""
    for k, inp in enumerate(t.inputs):
        values = inp.values or []
        for r in t.rules:
            cell = r.inputs[k].strip()
            new = [] if cell == "-" else ["-"]
            if inp.type_ref == "boolean":
                new += ["true", "false"] if cell == "-" else [{"true": "false", "false": "true"}[cell]]
            elif (m := _CMP.match(cell)) and inp.type_ref == "number":
                op, n = m.group(1), _num(m.group(2))
                new += [f"{op} {n + 1}", f"{op} {n - 1}", f"{_OPEN[op]} {n}"]
            elif values and cell != "-":
                items = [v.strip() for v in cell.split(",")]
                new += [",".join(x for x in items if x != v) for v in items if len(items) > 1]
                new += [",".join(items + [v]) for v in values if v not in items]
            elif values:
                new += values
            for n_ in new:
                yield f"{r.id}[{inp.expression}]: {cell[:30]} -> {n_[:30]}", _with_cell(t, r.id, k, n_)


def consistent_moves(t: Decision):
    """Changes that keep the table a partition: a threshold moved or opened/closed in every cell of its column, and a
    boolean column negated in every rule of a slice."""
    for k, inp in enumerate(t.inputs):
        if inp.type_ref == "number":
            ts = sorted({_num(m.group(2)) for r in t.rules if (m := _CMP.match(r.inputs[k]))})
            for th in ts:
                for label, fn in (("+1", lambda op, n: f"{op} {n + 1}"), ("-1", lambda op, n: f"{op} {n - 1}"),
                                  ("open/close", lambda op, n: f"{_OPEN[op]} {n}")):
                    m_ = t.model_copy(deep=True)
                    for r in m_.rules:
                        if (mm := _CMP.match(r.inputs[k])) and _num(mm.group(2)) == th:
                            r.inputs[k] = fn(mm.group(1), th)
                    yield f"{inp.expression} {th} {label} in every cell", m_
    for fixed, rules, cols, _ in slices(t):
        ids = {r.id for r in rules}
        for k, inp in enumerate(t.inputs):
            if inp.type_ref != "boolean" or inp.expression not in cols:
                continue
            m_ = t.model_copy(deep=True)
            for r in m_.rules:
                if r.id in ids and r.inputs[k].strip() in ("true", "false"):
                    r.inputs[k] = {"true": "false", "false": "true"}[r.inputs[k].strip()]
            yield f"{inp.expression} negated in the slice {fixed}", m_


def first_failure(tables: dict[str, Decision]) -> str | None:
    for did, t in tables.items():
        _, conflicts, gaps = table_defects(t, stop=True)
        if conflicts or gaps:
            return f"group 4 ({did}: {'conflict' if conflicts else 'empty'})"
    for c in CASES:
        if case_mismatches(tables, c, fast=True):
            return f"group 5 (case {c['id']})"
    return None


def mutation_test(tables: dict[str, Decision]) -> None:
    check("control: the unmutated model passes groups 4 and 5", first_failure(tables) is None, first_failure(tables))
    flips, survivors = 0, []
    for did, t in tables.items():
        for r in t.rules:
            for k, o in enumerate(t.outputs):
                if o.name == "basis":        # explanatory text: pinned by phrases in some cases only (docstring)
                    continue
                cur = literal_value(r.outputs[k])
                alts = [v for v in ("yes", "no", "depends") if v != cur] if o.name == "permit" else ["MUTATED"]
                for v in alts:
                    flips += 1
                    if first_failure({**tables, did: _with_output(t, r.id, k, f'"{v}"')}) is None:
                        survivors.append(f"{r.id}.{o.name} -> {v}")
    check(f"every one of the {flips} rule-output changes is caught", not survivors, survivors[:5] or "")
    for family, gen in (("single input-cell change", single_changes), ("consistent move", consistent_moves)):
        n, caught, survivors = 0, {}, []
        for did, t in tables.items():
            for label, m in gen(t):
                n += 1
                how = first_failure({**tables, did: m})
                if how is None:
                    survivors.append(label)
                else:
                    caught[how.split(" (")[0]] = caught.get(how.split(" (")[0], 0) + 1
        check(f"every one of the {n} mutants by {family} is caught", not survivors,
              survivors[:5] or "; ".join(f"{v} first caught by {k}" for k, v in sorted(caught.items())))


# ----------------------------------------------------------------- main
FORBIDDEN = ("iccsafe", "up.codes", "upcodes", "International Residential Code", "International Building Code",
             "IRC R105", "IBC 105")
# sections the design note quotes besides the model's knowledge sources (state, corpus, reference)
DOC_EXTRA = (("va", "regulations", "13VAC5-63-30"), ("va", "regulations", "13VAC5-63-40"),
             ("va", "regulations", "13VAC5-63-70"), ("va", "statutes", "36-98"), ("va", "statutes", "36-105"),
             ("dc", "regulations", "10-C DCMR 320"), ("nc", "statutes", "160D-1128"))


def main(path: str, doc: Path = DOC) -> int:
    xml = Path(path).read_text(encoding="utf-8")
    root = etree.fromstring(xml.encode())
    decisions = {d.get("id"): d for d in root.findall("d:decision", NS)}
    inputs = {i.get("id"): i for i in root.findall("d:inputData", NS)}
    kss = {k.get("id"): k for k in root.findall("d:knowledgeSource", NS)}
    tables = {did: to_ir(d) for did, d in decisions.items()}
    print(f"{path}: {len(decisions)} decisions, {len(inputs)} input data, {len(kss)} knowledge sources, "
          f"{sum(len(t.rules) for t in tables.values())} rules ({', '.join(f'{d}: {len(t.rules)}' for d, t in tables.items())})")

    # 1 ---------------------------------------------------------------- schema and tools
    print("1. schema and tools")
    errs = xsd_errors(xml, "dmn")
    check("DMN 1.3 XSD", not errs, errs[:3])
    lint = dmnlint(Path(path))
    check("dmnlint (recommended rules)", lint["ok"], lint["raw"][:300])
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
    bad = [e.get("href") for e in root.iter() if isinstance(e.tag, str) and e.get("href") is not None
           and not (e.get("href").startswith("#") and e.get("href")[1:] in ids)]
    check("every internal href resolves", not bad, bad[:5])
    wrong, mismatch, authority = [], [], {}
    for did, d in decisions.items():
        for r in d.findall("d:informationRequirement/*", NS):
            if etree.QName(r).localname != "requiredInput" or ref_id(r) not in inputs:
                wrong.append((did, ref_id(r)))
        for r in d.findall("d:authorityRequirement/*", NS):
            if etree.QName(r).localname != "requiredAuthority" or ref_id(r) not in kss:
                wrong.append((did, ref_id(r)))
        need = {inputs[ref_id(r)].get("name") for r in d.findall("d:informationRequirement/d:requiredInput", NS)}
        used = {i.expression for i in tables[did].inputs}
        if need != used:
            mismatch.append((did, sorted(need ^ used)))
        authority[did] = {kss[ref_id(r)].find("d:extensionElements/lex:reference", NS).get("citation")
                          for r in d.findall("d:authorityRequirement/d:requiredAuthority", NS)}
    check("requirement kinds (input <- information, knowledge source <- authority)", not wrong, wrong[:5])
    check("table columns = information requirements", not mismatch, mismatch)
    var = [e.get("id") for e in list(decisions.values()) + list(inputs.values())
           if e.find("d:variable", NS) is None or e.find("d:variable", NS).get("name") != e.get("name")]
    check("variable name = element name", not var, var)
    check("no cycles (no decision requires another)", not root.findall(".//d:requiredDecision", NS))
    outside = [f"{r.id}: {s.section}" for did, t in tables.items() for r in t.rules for s in r.sources
               if s.section not in authority[did]]
    check("every decision has authority requirements, and every rule cites only its decision's authorities",
          all(authority.values()) and not outside, outside[:5] or {d: len(a) for d, a in authority.items()})
    used_in = {ref_id(r) for d in decisions.values() for r in d.findall("d:informationRequirement/*", NS)}
    used_ks = {ref_id(r) for d in decisions.values() for r in d.findall("d:authorityRequirement/*", NS)}
    unused = [i for i in inputs if i not in used_in] + [k for k in kss if k not in used_ks]
    check("no unused input data or knowledge sources", not unused, unused)
    policies = sorted({t.hit_policy for t in tables.values()})
    check("every table is UNIQUE (no FIRST, no PRIORITY)", policies == ["UNIQUE"], policies)
    undeclared = [f"{r.id}.{o.name}={x}" for t in tables.values() for r in t.rules
                  for o, x in zip(t.outputs, r.outputs) if o.values and x not in o.values]
    check("declared output values cover every output entry", not undeclared, undeclared[:5])
    shapes = {s.get("dmnElementRef") for s in root.iterfind(".//dmndi:DMNShape", NS)}
    edges = {s.get("dmnElementRef") for s in root.iterfind(".//dmndi:DMNEdge", NS)}
    reqs = {e.get("id") for e in root.iter() if isinstance(e.tag, str)
            and etree.QName(e).localname in ("informationRequirement", "authorityRequirement")}
    missing = sorted(((set(decisions) | set(inputs) | set(kss)) - shapes) | (reqs - edges))
    check("DMNDI: a shape per DRG element and an edge per requirement", not missing,
          missing[:5] or f"{len(shapes)} shapes, {len(edges)} edges")

    # 3 ---------------------------------------------------------------- words
    print("3. quotes and references")
    n_q, bad_q, bad_sub, bad_url, no_note = 0, [], [], [], []
    for did, t in tables.items():
        rule_els = {r.get("id"): r for r in decisions[did].iterfind("d:decisionTable/d:rule", NS)}
        for r in t.rules:
            raw = lex_sources(rule_els[r.id])
            if not raw or not all(s.get("quote") for s in raw):
                bad_q.append(f"{r.id}: no quoted source")
            for s in raw:
                n_q += 1
                row, text = section(s["jurisdiction"], s["corpus"], s["section"])
                offs = quote_offsets(text, s["quote"]) if text else []
                if not offs:
                    bad_q.append(f"{r.id}: {s['citation']}: {s['quote'][:50]}")
                    continue
                ol = outline_for(s["jurisdiction"], s["corpus"])(text)
                want = s["subsection"].split("/") if s.get("subsection") else []
                found = [path_at(ol, o) for o in offs]
                if not any(f[:len(want)] == want for f in found):
                    bad_sub.append(f"{r.id}: {s['citation']} cites {s['subsection']}, found in {['/'.join(f) for f in found]}")
                if s.get("url") != row.get("url") or s.get("actId") != row.get("act_id"):
                    bad_url.append(f"{r.id}: {s['citation']}")
                if s.get("grounding") == "implied" and not (s.get("note") or "").startswith("Reading"):
                    no_note.append(f"{r.id}: {s['citation']}")
    check(f"quotes verbatim in the index text ({n_q} quotes)", not bad_q, bad_q[:5])
    check("each quote lies in the subdivision it cites", not bad_sub, bad_sub[:5])
    check("each source's URL and act id are the index row's", not bad_url, bad_url[:5])
    check("every implied source states its reading", not no_note, no_note[:5])
    bad_ann, n_reading = [], 0
    for did, t in tables.items():
        rule_els = {r.get("id"): r for r in decisions[did].iterfind("d:decisionTable/d:rule", NS)}
        for r in t.rules:
            want = annotation_for(r.sources)
            n_reading += want.count(" (reading)")
            if rule_els[r.id].findtext("d:annotationEntry/d:text", namespaces=NS) != want:
                bad_ann.append(r.id)
    check(f"each rule's Source annotation = its citations, implied ones marked (reading) ({n_reading} marks), and its "
          "first quote", not bad_ann, bad_ann[:5])
    bad_ks = []
    for kid, k in kss.items():
        ref = k.find("d:extensionElements/lex:reference", NS)
        row, _ = section(ref.get("state"), ref.get("corpus"), ref.get("citation"))
        kind = "regulation" if ref.get("corpus") == "regulations" else "statute"
        if not row or row["act_id"] != ref.get("actId") or k.get("locationURI") != row["url"] \
                or (row.get("kind") or "statute") != kind or k.findtext("d:type", namespaces=NS) != kind:
            bad_ks.append(kid)
    check(f"knowledge sources resolve to their act id, official URL and kind ({len(kss)})", not bad_ks, bad_ks)
    # the readings the model rests on, against the text
    _, va80 = section("va", "regulations", "13VAC5-63-80")
    ol = outline_vac(va80)
    decks = {"/".join(path_at(ol, m.start())) for m in re.finditer(r"(?i)deck", va80)
             if path_at(ol, m.start())[:1] == ["B"]}
    check("VA 108.2 names no deck: 'deck' occurs in 13VAC5-63-80 B only in item 14.6 (roof decking)",
          decks == {"B/14.6"}, sorted(decks))
    _, dc105 = section("dc", "regulations", "12-A DCMR 105")
    ol = outline_dcmr(dc105)
    dc_decks = [m.start() for m in re.finditer(r"(?i)\bdeck", dc105) if path_at(ol, m.start())[:2] == ["105.2", "building"]]
    check("DC 105.2's Building items name no deck", not dc_decks, dc_decks[:3])
    p5 = next(line for _, line in _lines(dc105) if line.startswith("105.2.5 "))
    listed = sorted({int(n) for n in re.findall(r"(?:: |; |and )(\d+)\. [A-Z]", p5)})
    check("DC 105.2.5 lists Building items 1, 4, 5, 7, 8, 9 and 10 (not 13, the playhouse item)",
          listed == [1, 4, 5, 7, 8, 9, 10], listed)
    _, nc1110 = section("nc", "statutes", "160D-1110")
    check("N.C. Gen. Stat. § 160D-1110 has no shed rule ('shed' does not occur)", not re.search(r"(?i)\bsheds?\b", nc1110))
    _, nc143 = section("nc", "statutes", "143-138")
    ol = outline_paren(nc143)
    sheds = sorted({"/".join(path_at(ol, m.start())) for m in re.finditer(r"(?i)\bsheds?\b", nc143)})
    check("N.C. Gen. Stat. § 143-138 mentions sheds only in its farm, equine and camping exemptions ((b4))",
          bool(sheds) and all(s.startswith("b4") for s in sheds), sheds)
    # premises of the fixes made after the verification (docs/design/verify-permit-required.md)
    _, va20 = section("va", "regulations", "13VAC5-63-20")
    ol20 = outline_vac(va20)
    d_items = {path_at(ol20, m.start())[1]: line for m in re.finditer(r"(?m)^(\d+)\. .*$", va20)
               for line in [m.group(0)] if path_at(ol20, m.start())[:1] == ["D"]}
    want_d = {"7": "Playground or recreational equipment", "8": "Industrialized buildings", "9": "Farm buildings",
              "11": "Off-site manufactured intermodal freight containers"}
    check("M2: 13VAC5-63-20 D (102.3) exempts from the code play equipment (7), industrialized buildings (8), farm "
          "buildings (9) and storage containers (11)",
          "The following are exempt from this code" in va20
          and all(d_items.get(k, "").split(". ", 1)[-1].startswith(v) for k, v in want_d.items()),
          {k: d_items.get(k, "")[:50] for k in want_d})
    _, va200 = section("va", "regulations", "13VAC5-63-200")
    check("W4: the VCC defines 'Construction' to include repair (13VAC5-63-200)",
          bool(re.search(r"(?m)^Construction\. The construction, reconstruction, alteration, repair, or conversion", va200)))
    _, va220 = section("va", "regulations", "13VAC5-63-220")
    p4295 = next((line for _, line in _lines(va220) if line.startswith("429.5 ")), "")
    check("M2: Section 429.5 applies the code's permit requirements to an industrialized building's site work",
          "industrialized building" in p4295 and "all administrative requirements of this code for permits" in p4295,
          p4295[:80])
    ol80 = outline_vac(va80)
    b_wiring = sorted({"/".join(path_at(ol80, m.start())) for m in re.finditer(r"(?i)\bwiring\b", va80)
                       if path_at(ol80, m.start())[:1] == ["B"]})
    check("M1: VA 108.2 names wiring only in item 1 (low-voltage, broadband, monitoring); 108.1 item 1 names electric "
          "wiring", b_wiring == ["B/1"] and "(vi) electric wiring" in va80, b_wiring)
    ol = outline_dcmr(dc105)
    item7 = [line for start, line in _lines(dc105)
             if re.match(r"^7\.\d ", line) and path_at(ol, start)[:3] == ["105.2", "building", line.split(" ")[0]]]
    check("W2: DC Building item 7's replacement-in-kind list (7.1 to 7.7) names no fence, and item 4 says 'Repair in "
          "kind'", len(item7) == 7 and not any("fence" in line.lower() for line in item7)
          and "4. Repair in kind of existing fences." in dc105, [line[:20] for line in item7])
    p22 = next(line for start, line in _lines(dc105) if line.startswith("Addition to, alteration of, replacement")
               and path_at(ol, start)[:1] == ["105.2.2"])
    check("M1: DC ordinary repairs (105.2.2) exclude piping, electric wiring and mechanical work", "electric wiring" in p22)
    check("M2: DC Building item 12 is playground equipment (105.2.5, checked above, does not list it)",
          "12. Swings and other playground equipment" in dc105)
    paras = nc1110.split("\n\n")
    olc = outline_paren(nc1110)
    pos, in_c = 0, []
    for para in paras:
        start = nc1110.index(para, pos)
        pos = start + len(para)
        if path_at(olc, start)[:1] == ["c"]:
            in_c.append(para)
    b5 = next(para for para in nc143.split("\n\n") if para.startswith("(b5)"))
    check("W3: NC's $40,000 exclusion ((c) and (b5)) names a single-family residence and no two-family dwelling",
          "single-family residence" in in_c[0] and "single family residence" in b5
          and not any("two-family" in x for x in in_c + [b5]), in_c[0][:60])
    hits = [w for w in FORBIDDEN if w.lower() in xml.lower()]
    check("no model-code text or link: no ICC or UpCodes link, no IRC or IBC title, no 'IRC R105' or 'IBC 105' "
          "pinpoint (state text's own references, such as 'Section 3306' and 'the IBC', are quoted as state text)",
          not hits, hits)
    # the descriptions the verification asked to correct
    desc = {i.get("name"): i.findtext("d:description", namespaces=NS) or "" for i in inputs.values()}
    fence_repair = re.search(r'"fence_repair": ([^"]*(?:"[^"]*"[^"]*)*?)"masonry_wall"', desc["project"])
    check("W2: the project input defines fence_repair as repair in kind only (a replacement is a fence)",
          bool(fence_repair) and "replacement" not in fence_repair.group(1).lower()
          and "replacement of an existing fence" in desc["project"], (fence_repair.group(1) if fence_repair else "")[:80])
    check("W5: the jurisdiction input points at the note's part 5 and states the NC local levers",
          "part 5" in desc["jurisdiction"] and "part 6" not in desc["jurisdiction"]
          and "cannot change the VA or NC answers" not in desc["jurisdiction"]
          and all(w in desc["jurisdiction"] for w in ("143-138(b5)", "143-138(e)", "160D-1128")))
    check("M6: height_ft excludes ornamental column caps (VA item 6)", "column caps" in desc["height_ft"])
    pdesc = decisions[MAIN].findtext("d:description", namespaces=NS) or ""
    check("W4: the permit_required description states one rule for the officials' discretion (items 13 and 14.11: "
          "yes; Exception 2 and unsettled questions: depends)",
          all(w in pdesc for w in ("items 13 and 14.11", "Exception 2", "does not settle", "would change")))

    # 4 ---------------------------------------------------------------- conflict and empty, per table
    print("4. Catala checks per table (conflict = two UNIQUE rules match; empty = no rule matches), whole domain")
    for did, t in tables.items():
        n, conflicts, gaps = table_defects(t)
        check(f"{did} ({len(t.rules)} rules, {n} grid points in {sum(1 for _ in slices(t))} slices)",
              not conflicts and not gaps, (conflicts[:2] or "") or (gaps[:2] or ""))
    rnd, sample_bad = random.Random(20261010), []
    for did, t in tables.items():
        doms = [domain(t, k) for k in range(len(t.inputs))]
        for _ in range(4000):
            g = {i.expression: rnd.choice(dm) for i, dm in zip(t.inputs, doms)}
            if len(matching(t, g)) != 1:
                sample_bad.append((did, g))
    check("a random sample of 4,000 points per table of the full product: exactly one rule each", not sample_bad,
          sample_bad[:2])
    print("     the questions each project needs answered (permit_required's columns read in its slice):")
    for fixed, rules, cols, grid in slices(tables[MAIN]):
        print(f"       {fixed['jurisdiction']} {fixed['project']:17} {len(rules):2} rules: {', '.join(cols) or '(none)'}")

    # 5 ---------------------------------------------------------------- cases
    print("5. cases (lexflow reference evaluator; every table re-run in SpiffWorkflow)")
    try:
        spiff = Spiff(list(tables.values()))
    except Exception as e:  # noqa: BLE001 - report, do not hide
        spiff = None
        check("SpiffWorkflow parses every table", False, repr(e)[:300])
    rows = []
    for c in CASES:
        mm = case_mismatches(tables, c)
        main_res = decide(tables[MAIN], filled(tables[MAIN], c["facts"]))
        other_res = decide(tables[OTHER], filled(tables[OTHER], c["facts"]))
        if spiff:
            for did, res in ((MAIN, main_res), (OTHER, other_res)):
                sp = spiff.result(did, filled(tables[did], c["facts"]))
                if sp != {k: v for k, v in res.items() if k != "_rule"}:
                    mm.append(f"SpiffWorkflow {did}: {sp}")
        check(f"case {c['id']}: {c['title']}", not mm,
              "; ".join(mm[:3]) if mm else f"{main_res.get('permit')} ({main_res.get('exemption')}); "
                                           f"{main_res.get('_rule', '').rsplit('_', 1)[-1]}, "
                                           f"{other_res.get('_rule', '').rsplit('_', 1)[-1]}")
        rows.append((c, main_res, other_res))
    want = {f"{MAIN}_r{c['rule']}" for c in CASES} | {f"{OTHER}_r{c['also'][0]}" for c in CASES}
    have = {r.id for t in tables.values() for r in t.rules}
    check(f"every rule of both tables is hit by some case ({len(have)} rules, {len(CASES)} cases)", want == have,
          sorted(have ^ want))
    if spiff:
        n, disagree = 0, []
        for did, t in tables.items():
            for _, _, _, grid in slices(t):
                for g in grid:
                    data = filled(t, g)
                    mine = {k: v for k, v in decide(t, data).items() if k != "_rule"}
                    if spiff.result(did, data) != mine:
                        disagree.append((did, g))
                    n += 1
        check("SpiffWorkflow and lexflow agree at every grid point of both tables", not disagree,
              f"{n} evaluations" if not disagree else disagree[:3])

    # 6 ---------------------------------------------------------------- the design note's quotes
    print(f"6. the design note's quotes ({doc})")
    if doc.exists():
        refs = [(r.get("state"), r.get("corpus"), r.get("citation"))
                for r in (k.find("d:extensionElements/lex:reference", NS) for k in kss.values())]
        texts = [norm(section(*ref)[1]) for ref in refs + list(DOC_EXTRA)]
        empty = [ref for ref in DOC_EXTRA if not section(*ref)[1]]
        check(f"the note's extra sections are in the index ({len(DOC_EXTRA)})", not empty, empty)
        quotes = re.findall(r"“([^”]+)”", doc.read_text(encoding="utf-8"))
        bad_doc = [q[:60] for q in quotes
                   if not all(any(norm(part) in t for t in texts) for part in re.split(r"\s*…\s*", q) if part.strip())]
        check(f"every “quoted” span of the note is verbatim state text ({len(quotes)} quotes)", bool(quotes) and not bad_doc,
              bad_doc[:5])
    else:
        check("the design note exists", False, str(doc))

    # 7 ---------------------------------------------------------------- mutations
    print("7. mutations: every mutated copy of the model must fail group 4 or 5")
    mutation_test(tables)

    print("cases (id, permit, exemption, rules hit):")
    for c, m, o in rows:
        print(f"     {c['id']:4} {m.get('permit', '?'):8} {m.get('exemption', '?'):60} "
              f"{m.get('_rule', '').rsplit('_', 1)[-1]:>4} {o.get('_rule', '').rsplit('_', 1)[-1]:>4}")
    print(f"\n{'ALL CHECKS PASSED' if not FAILED else 'FAILED: ' + '; '.join(FAILED)}")
    return 1 if FAILED else 0


if __name__ == "__main__":
    default = None
    if "__file__" in globals() and Path(__file__).name == "check_permit_required.py":
        default = str(Path(__file__).with_name("permit_required.dmn"))
    if len(sys.argv) < 2 and default is None:
        sys.exit("usage: python - PATH/permit_required.dmn [PATH/permit-required.md] < check_permit_required.py")
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else default,
                  Path(sys.argv[2]) if len(sys.argv) > 2 else DOC))
