"""LPIR -> BPMN 2.0 XML (semantic layer, schema-ordered).

Diagram interchange (DI) is added afterwards by :mod:`lexflow.layout`.
Child element order follows the OMG XSD content models, so the output
validates against BPMN20.xsd, not only against bpmn-js's lenient reader.
"""
from __future__ import annotations

import re
from typing import Iterable

from lxml import etree

from .ir import (ACTIVITY_TYPES, GATEWAY_TYPES, DataRef, LegalProcessModel, Node,
                 Process, SequenceFlow, Source)

NS = {
    "bpmn": "http://www.omg.org/spec/BPMN/20100524/MODEL",
    "bpmndi": "http://www.omg.org/spec/BPMN/20100524/DI",
    "dc": "http://www.omg.org/spec/DD/20100524/DC",
    "di": "http://www.omg.org/spec/DD/20100524/DI",
    "xsi": "http://www.w3.org/2001/XMLSchema-instance",
    "lex": "https://lexipedia.xyz/ns/lex/1.0",
    "spiffworkflow": "http://spiffworkflow.org/bpmn/schema/1.0/core",
    "camunda": "http://camunda.org/schema/1.0/bpmn",
}
B = "{%s}" % NS["bpmn"]
LEX = "{%s}" % NS["lex"]
XSI_TYPE = "{%s}type" % NS["xsi"]
NCNAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_.\-]*$")
EVENT_DEF = {
    "message": "messageEventDefinition", "timer": "timerEventDefinition",
    "signal": "signalEventDefinition", "error": "errorEventDefinition",
    "escalation": "escalationEventDefinition", "conditional": "conditionalEventDefinition",
    "link": "linkEventDefinition", "terminate": "terminateEventDefinition",
    "compensate": "compensateEventDefinition", "cancel": "cancelEventDefinition",
}
REF_ROOT = {"message": ("message", "messageRef"), "signal": ("signal", "signalRef"),
            "error": ("error", "errorRef"), "escalation": ("escalation", "escalationRef")}
VERSION = "0.3.0"


def slug(text: str) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_").lower()
    return s if s and not s[0].isdigit() else f"x_{s}"


def _el(parent, tag, attrib=None, text=None, ns=B):
    node = etree.SubElement(parent, ns + tag, {k: v for k, v in (attrib or {}).items() if v is not None})
    if text is not None:
        node.text = text
    return node


def _expr(parent, tag, text):
    node = _el(parent, tag, text=text)
    node.set(XSI_TYPE, "bpmn:tFormalExpression")
    return node


def _documentation(parent, text: str | None, sources: list[Source]):
    lines = []
    if text:
        lines.append(text.strip())
    for s in sources:
        q = f": “{s.quote}”" if s.quote else ""
        tag = "" if s.grounding == "explicit" else f" [{s.grounding}]"
        lines.append(f"{s.citation}{tag}{q}")
    if lines:
        doc = _el(parent, "documentation", {"textFormat": "text/plain"}, "\n".join(lines))
        return doc
    return None


def _lex_sources(ext, sources: Iterable[Source]):
    sources = list(sources)
    if not sources:
        return
    grounding = etree.SubElement(ext, LEX + "grounding")
    for s in sources:
        src = etree.SubElement(grounding, LEX + "source", {
            k: v for k, v in {
                "citation": s.citation, "section": s.section, "subsection": s.subsection,
                "code": s.code or None, "jurisdiction": s.jurisdiction or None,
                "grounding": s.grounding, "url": s.url,
            }.items() if v is not None
        })
        if s.quote:
            etree.SubElement(src, LEX + "quote").text = s.quote
        if s.note:
            etree.SubElement(src, LEX + "note").text = s.note


class BpmnWriter:
    def __init__(self, model: LegalProcessModel):
        self.m = model
        self.root = etree.Element(B + "definitions", nsmap=NS)
        self.messages: dict[str, str] = {}
        self.refs: dict[tuple[str, str], str] = {}
        self.stores: dict[str, str] = {}

    # ------------------------------------------------------------------ public
    def build(self) -> etree._Element:
        m = self.m
        r = self.root
        r.set("id", f"defs_{slug(m.id)}")
        r.set("name", m.title)
        r.set("targetNamespace", f"https://lexipedia.xyz/ns/process/{slug(m.id)}")
        r.set("exporter", "lexflow")
        r.set("exporterVersion", VERSION)
        self._check_ids()
        # root elements: shared definitions first, collaboration, then processes
        self._collect_refs()
        for name, ident in self.messages.items():
            _el(r, "message", {"id": ident, "name": name})
        for (kind, name), ident in self.refs.items():
            attrs = {"id": ident, "name": name}
            if kind == "error":
                attrs["errorCode"] = slug(name)
            if kind == "escalation":
                attrs["escalationCode"] = slug(name)
            _el(r, kind, attrs)
        for proc in m.processes():
            for d in self._all_data(proc):
                if d.kind == "store" and d.id not in self.stores:
                    ident = f"{d.id}_store"
                    self.stores[d.id] = ident
                    store = _el(r, "dataStore", {"id": ident, "name": d.name, "isUnlimited": "true"})
                    _documentation(store, None, d.sources)
        self._collaboration()
        for part in m.participants:
            if part.process is not None:
                self._process(part.process)
        self._seed_expansion()
        return r

    def _seed_expansion(self):
        """Seed DI with isExpanded so the layout engine keeps legally relevant sub-processes open."""
        subs = [(n.id, n.expanded) for _, _, n in self.m.iter_nodes()
                if n.type in ("subProcess", "transaction", "adHocSubProcess")]
        if not subs:
            return
        di = "{%s}" % NS["bpmndi"]
        dc = "{%s}" % NS["dc"]
        diagram = etree.SubElement(self.root, di + "BPMNDiagram", {"id": f"seed_{slug(self.m.id)}"})
        plane = etree.SubElement(diagram, di + "BPMNPlane", {"id": f"seed_plane_{slug(self.m.id)}",
                                                              "bpmnElement": f"collab_{slug(self.m.id)}"})
        for ident, expanded in subs:
            shape = etree.SubElement(plane, di + "BPMNShape", {"id": f"{ident}_seed", "bpmnElement": ident,
                                                               "isExpanded": "true" if expanded else "false"})
            etree.SubElement(shape, dc + "Bounds", {"x": "0", "y": "0", "width": "350", "height": "200"})

    def to_string(self) -> str:
        tree = self.build()
        return etree.tostring(tree, pretty_print=True, xml_declaration=True, encoding="UTF-8").decode()

    # ----------------------------------------------------------------- helpers
    def _check_ids(self):
        bad = [n.id for _, _, n in self.m.iter_nodes() if not NCNAME.match(n.id)]
        if bad:
            raise ValueError(f"ids are not XML NCNames: {bad}")

    def _all_data(self, proc: Process) -> list[DataRef]:
        out = list(proc.data)
        for _, _, n in self.m.iter_nodes():
            out.extend(n.data)
        return out

    def _collect_refs(self):
        for _, _, n in self.m.iter_nodes():
            ref = n.ref
            if n.event == "message" or n.type in ("sendTask", "receiveTask"):
                if ref:
                    self.messages.setdefault(ref, f"msg_{slug(ref)}")
            elif n.event in REF_ROOT and ref:
                kind = REF_ROOT[n.event][0]
                self.refs.setdefault((kind, ref), f"{kind}_{slug(ref)}")
        for mf in self.m.message_flows:
            if mf.message:
                self.messages.setdefault(mf.message, f"msg_{slug(mf.message)}")

    def _collaboration(self):
        m = self.m
        collab = _el(self.root, "collaboration", {"id": f"collab_{slug(m.id)}", "name": m.title})
        _documentation(collab, m.summary, [])
        ext = _el(collab, "extensionElements")
        meta = etree.SubElement(ext, LEX + "model", {
            "id": m.id, "jurisdiction": m.jurisdiction, "jurisdictionName": m.jurisdiction_name,
            **({"jurisdictionQid": m.jurisdiction_qid} if m.jurisdiction_qid else {}),
            "reviewStatus": m.review.status, "method": m.provenance.method,
        })
        for gap in m.review.gaps:
            etree.SubElement(meta, LEX + "gap").text = gap
        for a in m.actors:
            etree.SubElement(meta, LEX + "actor", {k: v for k, v in {
                "id": a.id, "name": a.name, "kind": a.kind, "wikidata": a.wikidata,
                "govdirectory": a.govdirectory}.items() if v})
        for part in m.participants:
            attrs = {"id": part.id, "name": part.name}
            if part.process is not None:
                attrs["processRef"] = part.process.id
            p = _el(collab, "participant", attrs)
            if part.actor:
                actor = next(a for a in m.actors if a.id == part.actor)
                pext = _el(p, "extensionElements")
                etree.SubElement(pext, LEX + "actor", {k: v for k, v in {
                    "ref": actor.id, "wikidata": actor.wikidata}.items() if v})
                p.insert(0, pext)
        for mf in m.message_flows:
            node = _el(collab, "messageFlow", {
                "id": mf.id, "name": mf.name or None, "sourceRef": mf.source, "targetRef": mf.target,
                "messageRef": self.messages.get(mf.message) if mf.message else None,
            })
            _documentation(node, None, mf.sources)
            if mf.sources:
                mext = _el(node, "extensionElements")
                _lex_sources(mext, mf.sources)

    def _process(self, proc: Process):
        p = _el(self.root, "process", {
            "id": proc.id, "name": proc.name, "isExecutable": "true" if proc.executable else "false",
        })
        _documentation(p, proc.documentation, [])
        if proc.lanes:
            lane_set = _el(p, "laneSet", {"id": f"{proc.id}_lanes"})
            host_lane = {n.id: n.lane for n in proc.nodes}
            for lane in proc.lanes:
                ln = _el(lane_set, "lane", {"id": lane.id, "name": lane.name})
                if lane.actor:
                    actor = next(a for a in self.m.actors if a.id == lane.actor)
                    lext = _el(ln, "extensionElements")
                    etree.SubElement(lext, LEX + "actor", {k: v for k, v in {
                        "ref": actor.id, "wikidata": actor.wikidata}.items() if v})
                for n in proc.nodes:
                    lane_id = n.lane or (host_lane.get(n.attached_to) if n.attached_to else None)
                    if lane_id == lane.id:
                        _el(ln, "flowNodeRef", text=n.id)
        self._data_index = {d.id: d for d in self._all_data(proc)}
        self._scope(p, proc.nodes, proc.flows, proc.data, scope_id=proc.id, top=True)
        for a in proc.annotations:
            ta = _el(p, "textAnnotation", {"id": a.id})
            _el(ta, "text", text=a.text)
        for a in proc.annotations:
            for i, target in enumerate(a.attached_to):
                _el(p, "association", {"id": f"{a.id}_assoc_{i}", "sourceRef": target,
                                       "targetRef": a.id, "associationDirection": "None"})

    def _scope(self, parent, nodes: list[Node], flows: list[SequenceFlow], data: list[DataRef],
               scope_id: str = "", top: bool = False):
        # data defined in an outer scope is reached through a local reference to the same
        # dataObject / dataStore (BPMN visibility rule) so every association stays in-scope
        local = {d.id for d in data}
        self._proxy: dict[str, str] = getattr(self, "_proxy", {})
        proxies: dict[str, str] = {}
        if not top:
            for n in nodes:
                for ref in n.data_inputs + n.data_outputs:
                    if ref not in local and ref not in proxies:
                        proxies[ref] = f"{ref}_in_{scope_id}"
        saved = dict(self._proxy)
        self._proxy.update({k: v for k, v in proxies.items()})
        for ref in local:
            self._proxy.pop(ref, None)
        incoming: dict[str, list[str]] = {n.id: [] for n in nodes}
        outgoing: dict[str, list[str]] = {n.id: [] for n in nodes}
        for f in flows:
            outgoing[f.source].append(f.id)
            incoming[f.target].append(f.id)
        for n in nodes:
            self._node(parent, n, incoming[n.id], outgoing[n.id])
        for f in flows:
            sf = _el(parent, "sequenceFlow", {"id": f.id, "name": f.name or None,
                                              "sourceRef": f.source, "targetRef": f.target})
            _documentation(sf, None, f.sources)
            if f.sources:
                _lex_sources(_el(sf, "extensionElements"), f.sources)
            if f.condition:
                _expr(sf, "conditionExpression", f.condition)
        for d in data:
            self._data(parent, d)
        for ref, proxy_id in proxies.items():
            d = self._data_index[ref]
            if d.kind == "object":
                _el(parent, "dataObjectReference", {"id": proxy_id, "name": d.name, "dataObjectRef": f"{d.id}_obj"})
            else:
                _el(parent, "dataStoreReference", {"id": proxy_id, "name": d.name, "dataStoreRef": self.stores[d.id]})
        self._proxy = saved

    def _data(self, parent, d: DataRef):
        if d.kind == "object":
            obj = _el(parent, "dataObject", {"id": f"{d.id}_obj", "name": d.name,
                                             "isCollection": "true" if d.collection else None})
            ref = _el(parent, "dataObjectReference", {"id": d.id, "name": d.name, "dataObjectRef": obj.get("id")})
        else:
            ref = _el(parent, "dataStoreReference", {"id": d.id, "name": d.name, "dataStoreRef": self.stores[d.id]})
        _documentation(ref, None, d.sources)
        if d.sources:
            _lex_sources(_el(ref, "extensionElements"), d.sources)
        if d.state:
            ref.append(etree.Element(B + "dataState", {"id": f"{d.id}_state", "name": d.state}))

    def _node(self, parent, n: Node, inc: list[str], out: list[str]):
        tag = n.type
        attrs: dict[str, str | None] = {"id": n.id, "name": n.name or None}
        if n.type in ("subProcess", "transaction", "adHocSubProcess") and n.triggered_by_event:
            attrs["triggeredByEvent"] = "true"
        if n.type == "boundaryEvent":
            attrs["attachedToRef"] = n.attached_to
            attrs["cancelActivity"] = "true" if n.interrupting else "false"
        if n.type == "startEvent" and not n.interrupting:
            attrs["isInterrupting"] = "false"
        if n.type == "callActivity":
            attrs["calledElement"] = n.called_element
        if n.type in ("exclusiveGateway", "inclusiveGateway", "complexGateway") and n.default:
            attrs["default"] = n.default
        if n.type in ACTIVITY_TYPES and n.default:
            attrs["default"] = n.default
        if n.type == "eventBasedGateway":
            attrs["instantiate"] = "true" if n.instantiate else "false"
            attrs["eventGatewayType"] = "Exclusive"
        if n.type in GATEWAY_TYPES:
            attrs["gatewayDirection"] = ("Diverging" if len(out) > 1 and len(inc) <= 1 else
                                         "Converging" if len(inc) > 1 and len(out) <= 1 else
                                         "Mixed" if len(inc) > 1 and len(out) > 1 else "Unspecified")
        if n.type in ("sendTask", "receiveTask") and n.ref:
            attrs["messageRef"] = self.messages[n.ref]
        if n.type == "businessRuleTask" and n.decision_ref:
            attrs["{%s}decisionRef" % NS["camunda"]] = n.decision_ref
        el = _el(parent, tag, attrs)
        # tBaseElement: documentation*, extensionElements?
        _documentation(el, n.documentation, n.sources)
        ext_needed = n.sources or n.deontic or n.timer or n.decision_ref
        if ext_needed:
            ext = _el(el, "extensionElements")
            _lex_sources(ext, n.sources)
            if n.deontic:
                etree.SubElement(ext, LEX + "norm", {k: v for k, v in {
                    "modality": n.deontic, "bearer": n.bearer}.items() if v})
            if n.timer:
                etree.SubElement(ext, LEX + "deadline", {k: v for k, v in {
                    "kind": n.timer.kind, "value": n.timer.value, "anchor": n.timer.anchor,
                    "strict": "true" if n.timer.strict else "false"}.items() if v})
            if n.decision_ref:
                etree.SubElement(ext, "{%s}calledDecisionId" % NS["spiffworkflow"]).text = n.decision_ref
        # tFlowNode: incoming*, outgoing*
        for f in inc:
            _el(el, "incoming", text=f)
        for f in out:
            _el(el, "outgoing", text=f)
        if n.type in ACTIVITY_TYPES:
            self._activity_body(el, n)
        else:
            self._event_body(el, n)

    def _activity_body(self, el, n: Node):
        # tActivity: ioSpecification?, property*, dataInputAssociation*, dataOutputAssociation*, ...
        if n.data_inputs:
            prop = _el(el, "property", {"id": f"{n.id}_in", "name": "__targetRef_placeholder"})
            for i, ref in enumerate(n.data_inputs):
                dia = _el(el, "dataInputAssociation", {"id": f"{n.id}_dia_{i}"})
                _el(dia, "sourceRef", text=self._proxy.get(ref, ref))
                _el(dia, "targetRef", text=prop.get("id"))
        for i, ref in enumerate(n.data_outputs):
            doa = _el(el, "dataOutputAssociation", {"id": f"{n.id}_doa_{i}"})
            _el(doa, "targetRef", text=self._proxy.get(ref, ref))
        if n.loop == "standard":
            _el(el, "standardLoopCharacteristics", {"id": f"{n.id}_loop"})
        elif n.loop in ("parallel", "sequential"):
            _el(el, "multiInstanceLoopCharacteristics", {
                "id": f"{n.id}_mi", "isSequential": "true" if n.loop == "sequential" else "false"})
        if n.type in ("subProcess", "transaction", "adHocSubProcess"):
            self._scope(el, n.nodes, n.flows, n.data, scope_id=n.id)

    def _event_body(self, el, n: Node):
        if n.type not in ("startEvent", "endEvent", "intermediateCatchEvent",
                          "intermediateThrowEvent", "boundaryEvent"):
            return
        if not n.event or n.event == "none":
            return
        tag = EVENT_DEF[n.event]
        ed = _el(el, tag, {"id": f"{n.id}_def"})
        if n.event == "timer":
            if not n.timer:
                raise ValueError(f"timer event {n.id} needs a timer")
            child = {"duration": "timeDuration", "date": "timeDate", "cycle": "timeCycle"}[n.timer.kind]
            _expr(ed, child, n.timer.value)
        elif n.event == "message" and n.ref:
            ed.set("messageRef", self.messages[n.ref])
        elif n.event in REF_ROOT and n.ref:
            kind, attr = REF_ROOT[n.event]
            ed.set(attr, self.refs[(kind, n.ref)])
        elif n.event == "conditional":
            _expr(ed, "condition", n.condition or "true")
        elif n.event == "link":
            ed.set("name", n.ref or n.id)


def to_bpmn_xml(model: LegalProcessModel) -> str:
    return BpmnWriter(model).to_string()
