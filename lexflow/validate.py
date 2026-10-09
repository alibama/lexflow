"""Validation harness: OMG XSDs, bpmnlint/dmnlint, SpiffWorkflow, Lexipedia checks."""
from __future__ import annotations

import re
import subprocess
from collections import Counter
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from lxml import etree

from .bpmn_xml import NS
from .ir import ACTIVITY_TYPES, LegalProcessModel

ROOT = Path(__file__).resolve().parents[1]
NODE_DIR = ROOT / "tools" / "node"
ISO_DURATION = re.compile(r"^-?P(?!$)(\d+Y)?(\d+M)?(\d+W)?(\d+D)?(T(?=\d)(\d+H)?(\d+M)?(\d+(\.\d+)?S)?)?$")


# ------------------------------------------------------------------------- XSD
@lru_cache(maxsize=None)
def _schema(path: str) -> etree.XMLSchema:
    return etree.XMLSchema(etree.parse(path))


def xsd_errors(xml: str, kind: str = "bpmn") -> list[str]:
    path = ROOT / "schemas" / ("bpmn/BPMN20.xsd" if kind == "bpmn" else "dmn/DMN13.xsd")
    schema = _schema(str(path))
    doc = etree.fromstring(xml.encode())
    if schema.validate(doc):
        return []
    return [f"line {e.line}: {e.message}" for e in schema.error_log]


# ---------------------------------------------------------------- lint (node)
def _lint(tool: str, path: Path) -> tuple[int, str]:
    path = Path(path).resolve()
    if not path.exists():
        raise FileNotFoundError(path)
    proc = subprocess.run(["npx", "--no-install", tool, str(path)], cwd=NODE_DIR,
                          capture_output=True, text=True, timeout=180)
    out = (proc.stdout + proc.stderr).strip()
    if "Error:" in out and "problem" not in out:
        raise RuntimeError(f"{tool} could not lint {path}: {out[:500]}")
    return proc.returncode, out


def bpmnlint(path: Path) -> dict:
    code, out = _lint("bpmnlint", path)
    problems = re.findall(r"^\s+(\S+)\s+(error|warning)\s+(.+?)\s{2,}(\S+)\s*$", out, re.M)
    return {"ok": code == 0, "problems": [dict(element=e, level=l, message=m, rule=r) for e, l, m, r in problems],
            "raw": out}


def dmnlint(path: Path) -> dict:
    code, out = _lint("dmnlint", path)
    problems = re.findall(r"^\s+(\S+)\s+(error|warning)\s+(.+?)\s{2,}(\S+)\s*$", out, re.M)
    return {"ok": code == 0, "problems": [dict(element=e, level=l, message=m, rule=r) for e, l, m, r in problems],
            "raw": out}


# ------------------------------------------------------------- spiff dialect
def spiff_dialect(bpmn_xml: str, timer_override: dict[str, str] | None = None) -> str:
    """Quote ISO timer values so SpiffWorkflow's Python engine can evaluate them.

    ``timer_override`` maps event ids to replacement values (e.g. ``PT0S``) to
    simulate a deadline passing without waiting 30 days.
    """
    doc = etree.fromstring(bpmn_xml.encode())
    for ev in doc.iter():
        tag = etree.QName(ev).localname if isinstance(ev.tag, str) else ""
        if tag not in ("timeDuration", "timeDate", "timeCycle"):
            continue
        owner = ev.getparent().getparent()
        value = (ev.text or "").strip()
        if timer_override and owner.get("id") in timer_override:
            value = timer_override[owner.get("id")]
        if not value.startswith('"'):
            value = f'"{value}"'
        ev.text = value
    return etree.tostring(doc, xml_declaration=True, encoding="UTF-8").decode()


def spiff_parser(bpmn_files: list[Path], dmn_files: list[Path]):
    from SpiffWorkflow.spiff.parser.process import SpiffBpmnParser
    from SpiffWorkflow.bpmn.parser.BpmnParser import BpmnValidator
    parser = SpiffBpmnParser(validator=BpmnValidator())
    for f in bpmn_files:
        parser.add_bpmn_file(str(f))
    for f in dmn_files:
        parser.add_dmn_file(str(f))
    return parser


# ------------------------------------------------------------ lexipedia checks
@dataclass
class LexReport:
    quotes_checked: int = 0
    quote_misses: list[str] = field(default_factory=list)
    grounding: Counter = field(default_factory=Counter)
    ungrounded: list[str] = field(default_factory=list)
    bad_timers: list[str] = field(default_factory=list)
    rules_without_source: list[str] = field(default_factory=list)
    deontic: Counter = field(default_factory=Counter)

    @property
    def ok(self) -> bool:
        return not (self.quote_misses or self.ungrounded or self.bad_timers)

    def summary(self) -> dict:
        total = sum(self.grounding.values())
        return {
            "quotes_checked": self.quotes_checked, "quote_misses": len(self.quote_misses),
            "grounding": dict(self.grounding),
            "explicit_share": round(self.grounding["explicit"] / total, 3) if total else None,
            "ungrounded": self.ungrounded, "bad_timers": self.bad_timers,
            "rules_without_source": self.rules_without_source, "deontic": dict(self.deontic),
        }


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.replace("’", "'")).strip()


def lex_checks(model: LegalProcessModel) -> LexReport:
    rep = LexReport()
    texts = {(t.section, t.code): _norm(t.text) for t in model.texts}

    def check_sources(owner: str, sources):
        for s in sources:
            rep.grounding[s.grounding] += 1
            if s.quote:
                rep.quotes_checked += 1
                text = texts.get((s.section, s.code))
                if text is None or _norm(s.quote) not in text:
                    rep.quote_misses.append(f"{owner}: {s.citation}: {s.quote[:60]}")

    for _, _, n in model.iter_nodes():
        check_sources(n.id, n.sources)
        needs = n.type in ACTIVITY_TYPES or n.type in ("intermediateCatchEvent", "boundaryEvent") or (
            n.type == "startEvent" and n.event not in (None, "none"))
        if needs and not n.sources:
            rep.ungrounded.append(n.id)
        if n.timer and n.timer.kind == "duration" and not ISO_DURATION.match(n.timer.value):
            rep.bad_timers.append(f"{n.id}: {n.timer.value}")
        if n.deontic:
            rep.deontic[n.deontic] += 1
    for proc in model.processes():
        for d in proc.data:
            check_sources(d.id, d.sources)
    for mf in model.message_flows:
        check_sources(mf.id, mf.sources)
    for d in model.decisions:
        check_sources(d.id, d.sources)
        for r in d.rules:
            check_sources(f"{d.id}.{r.id}", r.sources)
            if not r.sources and not r.annotation:
                rep.rules_without_source.append(f"{d.id}.{r.id}")
    return rep
