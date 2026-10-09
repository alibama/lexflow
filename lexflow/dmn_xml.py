"""LPIR decisions -> DMN 1.3 XML.

``dialect="feel"`` (canonical) writes standard FEEL cells for dmn-js / DokuWiki.
``dialect="python"`` rewrites the same cells for SpiffWorkflow's engine.
Each rule carries its legal citation twice: as a visible annotation column
("Source") and as machine-readable lex:source extension elements.
"""
from __future__ import annotations

from lxml import etree

from .bpmn_xml import LEX, NS as BPMN_NS, _lex_sources, slug
from .feel import literal_to_python, parse_unary, unary_to_python, evaluate_literal
from .ir import Decision, LegalProcessModel

DMN = "https://www.omg.org/spec/DMN/20191111/MODEL/"
NS = {
    None: DMN,
    "dmndi": "https://www.omg.org/spec/DMN/20191111/DMNDI/",
    "dc": "http://www.omg.org/spec/DMN/20180521/DC/",
    "lex": BPMN_NS["lex"],
}
D = "{%s}" % DMN


def _sub(parent, tag, attrib=None, text=None):
    node = etree.SubElement(parent, D + tag, {k: v for k, v in (attrib or {}).items() if v is not None})
    if text is not None:
        node.text = text
    return node


def _text(parent, tag, value, attrib=None):
    node = _sub(parent, tag, attrib)
    _sub(node, "text", text=value)
    return node


def write_dmn(model: LegalProcessModel, decisions: list[Decision] | None = None,
              dialect: str = "feel") -> str:
    decisions = decisions if decisions is not None else model.decisions
    root = etree.Element(D + "definitions", nsmap=NS)
    root.set("id", f"dmn_{slug(model.id)}")
    root.set("name", f"{model.title} - decisions")
    root.set("namespace", f"https://lexipedia.xyz/ns/decision/{slug(model.id)}")
    root.set("exporter", "lexflow")
    for d in decisions:
        for rule in d.rules:          # fail early on cells outside the supported FEEL subset
            for cell in rule.inputs:
                parse_unary(cell)
            for cell in rule.outputs:
                evaluate_literal(cell)
        dec = _sub(root, "decision", {"id": d.id, "name": d.name})
        cites = "; ".join(s.citation for s in d.sources)
        if cites:
            _sub(dec, "description", text=f"Grounded in {cites}")
        if d.sources:
            ext = _sub(dec, "extensionElements")
            _lex_sources(ext, d.sources)
        if d.question:
            _sub(dec, "question", text=d.question)
        table = _sub(dec, "decisionTable", {"id": f"{d.id}_table", "hitPolicy": d.hit_policy})
        for inp in d.inputs:
            ic = _sub(table, "input", {"id": inp.id, "label": inp.label})
            _text(ic, "inputExpression", inp.expression, {"id": f"{inp.id}_expr", "typeRef": inp.type_ref})
            if inp.values:
                vals = ",".join(inp.values) if dialect == "feel" else None
                if vals:
                    _text(ic, "inputValues", vals, {"id": f"{inp.id}_values"})
        for out in d.outputs:
            oc = _sub(table, "output", {"id": out.id, "label": out.label, "name": out.name,
                                        "typeRef": out.type_ref})
            if out.values and dialect == "feel":
                _text(oc, "outputValues", ",".join(out.values), {"id": f"{out.id}_values"})
        if dialect == "feel":  # SpiffWorkflow rejects DMN 1.3 annotation columns
            _sub(table, "annotation", {"name": "Source"})
        for rule in d.rules:
            r = _sub(table, "rule", {"id": rule.id})
            desc = "; ".join(s.citation for s in rule.sources)
            if rule.annotation or desc:
                _sub(r, "description", text=(rule.annotation or desc))
            if rule.sources:
                ext = _sub(r, "extensionElements")
                _lex_sources(ext, rule.sources)
            for i, cell in enumerate(rule.inputs):
                value = cell if dialect == "feel" else unary_to_python(cell)
                _text(r, "inputEntry", value, {"id": f"{rule.id}_in{i}"})
            for i, cell in enumerate(rule.outputs):
                value = cell if dialect == "feel" else literal_to_python(cell)
                _text(r, "outputEntry", value, {"id": f"{rule.id}_out{i}"})
            if dialect == "feel":
                _text(r, "annotationEntry", desc or "-")
    # DMNDI: one shape per decision so dmn-js can show the requirements diagram
    dmndi = etree.SubElement(root, "{%s}DMNDI" % NS["dmndi"])
    diagram = etree.SubElement(dmndi, "{%s}DMNDiagram" % NS["dmndi"], {"id": f"dmndi_{slug(model.id)}"})
    for i, d in enumerate(decisions):
        shape = etree.SubElement(diagram, "{%s}DMNShape" % NS["dmndi"],
                                 {"id": f"{d.id}_shape", "dmnElementRef": d.id})
        etree.SubElement(shape, "{%s}Bounds" % NS["dc"], {
            "x": str(160 + 240 * i), "y": "100", "width": "200", "height": "80"})
    return etree.tostring(root, pretty_print=True, xml_declaration=True, encoding="UTF-8").decode()


def write_dmn_split(model: LegalProcessModel, dialect: str = "python") -> dict[str, str]:
    """One decision per file (SpiffWorkflow supports a single decision per DMN document)."""
    return {d.id: write_dmn(model, [d], dialect=dialect) for d in model.decisions}
