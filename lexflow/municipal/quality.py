"""Turn a compiled model into artifacts and quality numbers (the same checks as scripts/build_all.py).

Each check is isolated: a failing tool lowers the score and is recorded, it never stops a build.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from ..bpmn_xml import to_bpmn_xml
from ..dmn_xml import write_dmn
from ..ir import LegalProcessModel
from ..validate import bpmnlint, lex_checks, xsd_errors


def assess(model: LegalProcessModel, agreement: float | None = None) -> dict:
    out: dict = {"errors": []}
    semantic = to_bpmn_xml(model)
    bpmn = semantic
    try:
        from ..layout import auto_layout
        bpmn, warnings = auto_layout(semantic)
        out["layout_warnings"] = len(warnings)
    except Exception as e:  # noqa: BLE001
        out["errors"].append(f"layout: {e}"[:300])
    out["bpmn"] = bpmn
    try:
        from ..render_svg import render
        out["svg"] = render(bpmn, title=model.title) if "BPMNDiagram" in bpmn else None
    except Exception as e:  # noqa: BLE001
        out["svg"] = None
        out["errors"].append(f"render: {e}"[:300])
    m: dict = {}
    m["bpmn_xsd_errors"] = len(xsd_errors(bpmn))
    if model.decisions:
        dmn = write_dmn(model)
        out["dmn"] = dmn
        m["dmn_xsd_errors"] = len(xsd_errors(dmn, "dmn"))
    else:
        out["dmn"] = None
    try:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "model.bpmn"
            p.write_text(bpmn, encoding="utf-8")
            lint = bpmnlint(p)
            m["lint_errors"] = sum(1 for x in lint["problems"] if x["level"] == "error")
            m["lint_warnings"] = sum(1 for x in lint["problems"] if x["level"] == "warning")
    except Exception as e:  # noqa: BLE001
        out["errors"].append(f"bpmnlint: {e}"[:300])
    lex = lex_checks(model).summary()
    m["quotes_checked"] = lex["quotes_checked"]
    m["quote_misses"] = lex["quote_misses"]
    m["explicit_share"] = lex["explicit_share"]
    m["ungrounded"] = len(lex["ungrounded"])
    nets = []
    try:
        from ..petri import analyse
        for proc in model.processes():
            r, *_ = analyse(proc)
            nets.append(bool(r.sound) and not r.error)
    except Exception as e:  # noqa: BLE001
        out["errors"].append(f"petri: {e}"[:300])
    m["nets"] = len(nets)
    m["nets_sound"] = sum(nets)
    types = {}
    for _, _, n in model.iter_nodes():
        types[n.type] = types.get(n.type, 0) + 1
    m["flow_nodes"] = sum(types.values())
    m["tasks"] = sum(v for k, v in types.items() if k.endswith("Task") or k == "task")
    m["timers"] = sum(1 for _, _, n in model.iter_nodes() if n.timer)
    m["decisions"] = len(model.decisions)
    m["rules"] = sum(len(d.rules) for d in model.decisions)
    if agreement is not None:
        m["agreement"] = round(agreement, 3)
    m["tool_errors"] = len(out["errors"])
    out["metrics"] = m
    out["quality"] = quality_score(m)
    out["validated"] = (m["bpmn_xsd_errors"] == 0 and m.get("dmn_xsd_errors", 0) == 0 and m["quote_misses"] == 0
                        and m.get("lint_errors", 1) == 0 and (not nets or all(nets)))
    return out


def quality_score(m: dict) -> float:
    parts = []
    if m.get("quotes_checked"):
        parts.append(1 - m["quote_misses"] / m["quotes_checked"])
    parts.append(1.0 if m.get("bpmn_xsd_errors", 1) == 0 and m.get("dmn_xsd_errors", 0) == 0 else 0.0)
    if "lint_errors" in m:
        parts.append(max(0.0, 1 - (m["lint_errors"] + 0.25 * m.get("lint_warnings", 0)) / 8))
    if m.get("nets"):
        parts.append(m["nets_sound"] / m["nets"])
    if m.get("explicit_share") is not None:
        parts.append(m["explicit_share"])
    if m.get("agreement") is not None:
        parts.append(m["agreement"])
    return round(sum(parts) / len(parts), 3) if parts else 0.0
