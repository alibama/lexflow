"""Per-feature round-trip probe: lexflow BPMN -> bpmn-assistant JSON -> bpmn-assistant XML.

For each BPMN feature a legal process needs, build a minimal one-process model, import
it with bpmn-assistant's BpmnJsonGenerator and regenerate XML with its BpmnXmlGenerator.
Reports: imported?  feature survives the round trip?  output XSD-valid?  has DI?
Run with PYTHONPATH pointing at bpmn-assistant/src.
"""
import json
import sys
from pathlib import Path

from lxml import etree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lexflow.bpmn_xml import to_bpmn_xml  # noqa: E402
from lexflow.ir import (Actor, DataRef, LegalProcessModel, Lane, MessageFlow, Node, Participant,  # noqa: E402
                        Process, SequenceFlow, Source, Timer)
from lexflow.validate import xsd_errors  # noqa: E402

from bpmn_assistant.services.bpmn_json_generator import BpmnJsonGenerator  # noqa: E402
from bpmn_assistant.services.bpmn_xml_generator import BpmnXmlGenerator  # noqa: E402

SRC = [Source(citation="Test Code § 1-1", section="1-1", quote="x")]
B = "{http://www.omg.org/spec/BPMN/20100524/MODEL}"


def model(nodes, flows, data=(), lanes=(), extra_participants=(), mflows=()):
    proc = Process(id="proc", name="Probe", nodes=nodes, flows=flows, data=list(data), lanes=list(lanes))
    parts = [Participant(id="p_main", name="Main", process=proc)] + list(extra_participants)
    return LegalProcessModel(id="probe", title="Probe", jurisdiction="x/y", jurisdiction_name="Probe",
                             actors=[Actor(id="a", name="A")], participants=parts, message_flows=list(mflows))


def seq(*ids):
    return [SequenceFlow(id=f"f_{a}_{b}", source=a, target=b) for a, b in zip(ids, ids[1:])]


S = Node(id="s", type="startEvent", name="Start")
E = Node(id="e", type="endEvent", name="End")


def t(i, typ="userTask", **kw):
    return Node(id=i, type=typ, name=i.upper(), **kw)


PROBES = {
    "plain sequence": (model([S, t("t1"), E], seq("s", "t1", "e")), lambda r: r.find(f".//{B}userTask") is not None),
    "documentation (legal citation text)": (model([S, t("t1", sources=SRC), E], seq("s", "t1", "e")),
                                            lambda r: r.find(f".//{B}documentation") is not None),
    "extensionElements (lex:source)": (model([S, t("t1", sources=SRC), E], seq("s", "t1", "e")),
                                       lambda r: r.find(f".//{B}extensionElements") is not None),
    "conditionExpression on flow": (model(
        [S, Node(id="g", type="exclusiveGateway", name="OK?", default="f3"), t("t1"), t("t2"),
         Node(id="j", type="exclusiveGateway"), E],
        [SequenceFlow(id="f0", source="s", target="g"),
         SequenceFlow(id="f2", source="g", target="t1", name="yes", condition="ok"),
         SequenceFlow(id="f3", source="g", target="t2", name="no"),
         SequenceFlow(id="f4", source="t1", target="j"), SequenceFlow(id="f5", source="t2", target="j"),
         SequenceFlow(id="f6", source="j", target="e")]),
        lambda r: r.find(f".//{B}conditionExpression") is not None),
    "timer boundary, non-interrupting": (model(
        [S, t("t1"), Node(id="b", type="boundaryEvent", name="30 days", attached_to="t1", interrupting=False,
                          event="timer", timer=Timer(value="P30D")), Node(id="e2", type="endEvent", name="Late"), E],
        seq("s", "t1", "e") + [SequenceFlow(id="f_b", source="b", target="e2")]),
        lambda r: r.find(f".//{B}boundaryEvent[@cancelActivity='false']") is not None),
    "message boundary event": (model(
        [S, t("t1"), Node(id="b", type="boundaryEvent", name="Msg", attached_to="t1", interrupting=False,
                          event="message", ref="Ping"), Node(id="e2", type="endEvent", name="X"), E],
        seq("s", "t1", "e") + [SequenceFlow(id="f_b", source="b", target="e2")]),
        lambda r: r.find(f".//{B}boundaryEvent/{B}messageEventDefinition") is not None),
    "event-based gateway (deadline race)": (model(
        [S, Node(id="g", type="eventBasedGateway", name="Which first?"),
         Node(id="m", type="intermediateCatchEvent", name="Filed", event="message", ref="Filing"),
         Node(id="tm", type="intermediateCatchEvent", name="30 days", event="timer", timer=Timer(value="P30D")),
         E, Node(id="e2", type="endEvent", name="Lapsed")],
        [SequenceFlow(id="f0", source="s", target="g"), SequenceFlow(id="f1", source="g", target="m"),
         SequenceFlow(id="f2", source="g", target="tm"), SequenceFlow(id="f3", source="m", target="e"),
         SequenceFlow(id="f4", source="tm", target="e2")]),
        lambda r: r.find(f".//{B}eventBasedGateway") is not None),
    "call activity (state-law process)": (model([S, Node(id="c", type="callActivity", name="Judicial review",
                                                         called_element="other_proc"), E], seq("s", "c", "e")),
                                          lambda r: r.find(f".//{B}callActivity") is not None),
    "event sub-process": (model(
        [S, t("t1"), E, Node(id="esp", type="subProcess", name="On request", triggered_by_event=True,
                             nodes=[Node(id="es", type="startEvent", name="Req", event="message", ref="Req",
                                         interrupting=False), t("et"), Node(id="ee", type="endEvent", name="Done")],
                             flows=seq("es", "et", "ee"))], seq("s", "t1", "e")),
        lambda r: r.find(f".//{B}subProcess[@triggeredByEvent='true']") is not None),
    "nested embedded sub-process": (model(
        [S, Node(id="sp", type="subProcess", name="Hearing", nodes=[
            Node(id="is", type="startEvent", name="in"), t("it"), Node(id="ie", type="endEvent", name="out")],
            flows=seq("is", "it", "ie")), E], seq("s", "sp", "e")),
        lambda r: r.find(f".//{B}subProcess/{B}userTask") is not None),
    "data object + association": (model([S, t("t1", data_outputs=["rec"]), E], seq("s", "t1", "e"),
                                        data=[DataRef(id="rec", name="Record")]),
                                  lambda r: r.find(f".//{B}dataObjectReference") is not None),
    "data store": (model([S, t("t1", data_inputs=["db"]), E], seq("s", "t1", "e"),
                         data=[DataRef(id="db", name="Reports", kind="store")]),
                   lambda r: r.find(f".//{B}dataStoreReference") is not None),
    "business rule task (DMN link)": (model([S, Node(id="br", type="businessRuleTask", name="Decide"), E],
                                            seq("s", "br", "e")),
                                      lambda r: r.find(f".//{B}businessRuleTask") is not None),
    "pools + lanes + message flow": (model(
        [Node(id="s", type="startEvent", name="Start", lane="l1"), Node(id="snd", type="sendTask", name="Notify",
                                                                         lane="l2", ref="Note"),
         Node(id="e", type="endEvent", name="End", lane="l2")], seq("s", "snd", "e"),
        lanes=[Lane(id="l1", name="Clerk"), Lane(id="l2", name="Officer")],
        extra_participants=[Participant(id="p_out", name="Outsider")],
        mflows=[MessageFlow(id="mf", source="snd", target="p_out", name="Notice")]),
        lambda r: r.find(f".//{B}messageFlow") is not None and r.find(f".//{B}lane") is not None),
}


def run():
    rows = []
    for name, (m, survives) in PROBES.items():
        xml = to_bpmn_xml(m)
        row = {"feature": name, "imported": False, "survives_round_trip": False, "output_xsd_valid": None,
               "output_has_di": None, "error": None}
        try:
            js = BpmnJsonGenerator().create_bpmn_json(xml)
            row["imported"] = True
            out = BpmnXmlGenerator().create_bpmn_xml(js)
            root = etree.fromstring(out.encode())
            row["survives_round_trip"] = bool(survives(root))
            row["output_xsd_valid"] = not xsd_errors(out)
            row["output_has_di"] = root.find(".//{http://www.omg.org/spec/BPMN/20100524/DI}BPMNShape") is not None
            if not row["output_xsd_valid"]:
                row["error"] = xsd_errors(out)[0][:160]
        except Exception as e:  # noqa: BLE001
            row["error"] = f"{type(e).__name__}: {str(e)[:160]}"
        rows.append(row)
    return rows


if __name__ == "__main__":
    rows = run()
    out = ROOT / "out" / "bpmn_assistant_roundtrip.json"
    out.write_text(json.dumps(rows, indent=2))
    for r in rows:
        print(f"{r['feature']:<40} imported={str(r['imported']):<5} survives={str(r['survives_round_trip']):<5} "
              f"xsd={str(r['output_xsd_valid']):<5} di={str(r['output_has_di']):<5} {r['error'] or ''}")
