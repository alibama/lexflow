"""Lexipedia Process IR (LPIR).

A graph-shaped, legally-grounded intermediate representation that covers the
parts of the BPMN 2.0 DOM a legal process needs, plus DMN decision tables.

Design rules
------------
* Every flow node, flow and decision rule can carry ``sources`` - citations
  into the law text with an optional verbatim ``quote`` used for
  cross-reference highlighting and hallucination checks.
* ``grounding`` records *why* an element exists: ``explicit`` (the text says
  it), ``implied`` (another provision presupposes it), ``assumed`` (modeller's
  operational assumption).  Reviewers can filter on this.
* Conditions are written in the boolean subset that is valid in both FEEL and
  Python (variables, not(), and, or, numeric comparisons), so the same model
  renders in bpmn-js and executes in SpiffWorkflow.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

Grounding = Literal["explicit", "implied", "assumed"]

TASK_TYPES = {
    "task", "userTask", "serviceTask", "sendTask", "receiveTask",
    "businessRuleTask", "manualTask", "scriptTask",
}
ACTIVITY_TYPES = TASK_TYPES | {"callActivity", "subProcess", "transaction", "adHocSubProcess"}
GATEWAY_TYPES = {"exclusiveGateway", "inclusiveGateway", "parallelGateway",
                 "eventBasedGateway", "complexGateway"}
EVENT_TYPES = {"startEvent", "endEvent", "intermediateCatchEvent",
               "intermediateThrowEvent", "boundaryEvent"}
NodeType = Literal[
    "startEvent", "endEvent", "intermediateCatchEvent", "intermediateThrowEvent", "boundaryEvent",
    "task", "userTask", "serviceTask", "sendTask", "receiveTask", "businessRuleTask",
    "manualTask", "scriptTask", "callActivity", "subProcess", "transaction", "adHocSubProcess",
    "exclusiveGateway", "inclusiveGateway", "parallelGateway", "eventBasedGateway", "complexGateway",
]
EventKind = Literal["none", "message", "timer", "signal", "error", "escalation",
                    "conditional", "link", "terminate", "compensate", "cancel"]
Deontic = Literal["obligation", "permission", "prohibition", "right", "power", "duty-to-decide"]


class Source(BaseModel):
    """A pointer into the law text."""
    citation: str                      # human form: "Albemarle County Code § 17-211(D)(2)"
    section: str                       # canonical section number: "17-211"
    subsection: Optional[str] = None   # "D.2"
    code: str = ""                     # "Albemarle County Code"
    jurisdiction: str = ""             # "va/albemarle_county"
    quote: Optional[str] = None        # exact span of the source text (used for highlighting)
    url: Optional[str] = None
    grounding: Grounding = "explicit"
    note: Optional[str] = None         # e.g. why an element is implied/assumed, or a gap


class Timer(BaseModel):
    kind: Literal["duration", "date", "cycle"] = "duration"
    value: str                         # ISO 8601: P30D, R/P1Y, 2026-07-01T00:00:00Z
    anchor: Optional[str] = None       # legal anchor: "date of notice of the action"
    strict: bool = True                # False = directory/soft deadline (missing it does not end the matter)


class SequenceFlow(BaseModel):
    id: str
    source: str
    target: str
    name: str = ""
    condition: Optional[str] = None
    sources: list[Source] = Field(default_factory=list)


class DataRef(BaseModel):
    id: str
    name: str
    kind: Literal["object", "store"] = "object"
    collection: bool = False
    state: Optional[str] = None
    sources: list[Source] = Field(default_factory=list)


class Annotation(BaseModel):
    id: str
    text: str
    attached_to: list[str] = Field(default_factory=list)


class Node(BaseModel):
    id: str
    type: NodeType
    name: str = ""
    lane: Optional[str] = None
    documentation: Optional[str] = None
    sources: list[Source] = Field(default_factory=list)
    # events
    event: Optional[EventKind] = None
    timer: Optional[Timer] = None
    ref: Optional[str] = None            # message / signal / error / escalation name
    condition: Optional[str] = None      # conditional event condition
    attached_to: Optional[str] = None    # boundary events
    interrupting: bool = True            # boundary cancelActivity / event-subprocess start
    # activities
    decision_ref: Optional[str] = None   # businessRuleTask -> Decision.id
    called_element: Optional[str] = None # callActivity -> process id (may live in another model)
    loop: Optional[Literal["standard", "parallel", "sequential"]] = None
    triggered_by_event: bool = False     # event sub-process
    expanded: bool = True
    nodes: list["Node"] = Field(default_factory=list)          # sub-process content
    flows: list[SequenceFlow] = Field(default_factory=list)
    data: list[DataRef] = Field(default_factory=list)
    data_inputs: list[str] = Field(default_factory=list)      # DataRef ids read by this activity
    data_outputs: list[str] = Field(default_factory=list)     # DataRef ids written by this activity
    # gateways
    default: Optional[str] = None        # default sequence flow id
    instantiate: bool = False
    # legal semantics
    deontic: Optional[Deontic] = None
    bearer: Optional[str] = None         # Actor.id that carries the obligation / permission
    wikibase: Optional[str] = None       # Lexipedia Wikibase item once published


class Lane(BaseModel):
    id: str
    name: str
    actor: Optional[str] = None


class Process(BaseModel):
    id: str
    name: str
    executable: bool = True
    lanes: list[Lane] = Field(default_factory=list)
    nodes: list[Node] = Field(default_factory=list)
    flows: list[SequenceFlow] = Field(default_factory=list)
    data: list[DataRef] = Field(default_factory=list)
    annotations: list[Annotation] = Field(default_factory=list)
    documentation: Optional[str] = None


class Actor(BaseModel):
    id: str
    name: str
    kind: Literal["public-body", "official", "private-party", "court", "other-government", "role"] = "role"
    wikidata: Optional[str] = None       # QID, links Lexipedia to Wikidata / govdirectory
    govdirectory: Optional[str] = None   # URL when the agency is listed on govdirectory.org
    description: Optional[str] = None


class Participant(BaseModel):
    id: str
    name: str
    actor: Optional[str] = None
    process: Optional[Process] = None    # None = black-box pool


class MessageFlow(BaseModel):
    id: str
    source: str
    target: str
    name: str = ""
    message: Optional[str] = None
    sources: list[Source] = Field(default_factory=list)


class InputClause(BaseModel):
    id: str
    label: str
    expression: str                      # variable name
    type_ref: Literal["string", "number", "boolean", "date", "time"] = "string"
    values: Optional[list[str]] = None   # allowed values (FEEL literals)


class OutputClause(BaseModel):
    id: str
    label: str
    name: str
    type_ref: Literal["string", "number", "boolean", "date", "time"] = "string"
    values: Optional[list[str]] = None


class Rule(BaseModel):
    id: str
    inputs: list[str]                    # FEEL unary tests ("-" = any)
    outputs: list[str]                   # FEEL literal expressions
    annotation: Optional[str] = None
    sources: list[Source] = Field(default_factory=list)


class Decision(BaseModel):
    id: str
    name: str
    question: Optional[str] = None
    hit_policy: Literal["UNIQUE", "FIRST", "PRIORITY", "ANY", "COLLECT", "RULE ORDER", "OUTPUT ORDER"] = "UNIQUE"
    inputs: list[InputClause]
    outputs: list[OutputClause]
    rules: list[Rule]
    sources: list[Source] = Field(default_factory=list)

    @model_validator(mode="after")
    def _shape(self) -> "Decision":
        for rule in self.rules:
            if len(rule.inputs) != len(self.inputs) or len(rule.outputs) != len(self.outputs):
                raise ValueError(f"rule {rule.id} does not match the table's column count")
        return self


class SectionText(BaseModel):
    """Law text kept with the model so viewers can highlight quotes."""
    section: str
    title: str
    code: str
    jurisdiction: str
    text: str
    url: Optional[str] = None
    history: Optional[str] = None
    retrieved_from: str = ""             # dataset / API the text came from
    license_note: Optional[str] = None


class Provenance(BaseModel):
    generator: str = "lexflow"
    method: Literal["gold-manual", "llm-extraction", "assistant-edited"] = "gold-manual"
    model: Optional[str] = None
    prompt_hash: Optional[str] = None
    dataset_rows: list[str] = Field(default_factory=list)
    created: Optional[str] = None
    notes: list[str] = Field(default_factory=list)


class Review(BaseModel):
    status: Literal["draft", "machine-checked", "legal-reviewed"] = "draft"
    gaps: list[str] = Field(default_factory=list)
    reviewers: list[str] = Field(default_factory=list)


class LegalProcessModel(BaseModel):
    id: str
    title: str
    jurisdiction: str                    # "va/albemarle_county"
    jurisdiction_name: str
    jurisdiction_qid: Optional[str] = None
    summary: str = ""
    actors: list[Actor] = Field(default_factory=list)
    participants: list[Participant] = Field(default_factory=list)
    message_flows: list[MessageFlow] = Field(default_factory=list)
    decisions: list[Decision] = Field(default_factory=list)
    texts: list[SectionText] = Field(default_factory=list)
    provenance: Provenance = Field(default_factory=Provenance)
    review: Review = Field(default_factory=Review)

    # ------------------------------------------------------------------ helpers
    def processes(self) -> list[Process]:
        return [p.process for p in self.participants if p.process is not None]

    def iter_nodes(self):
        """Yield (process, scope_node_or_None, node) for every node, recursively."""
        def walk(proc, scope, nodes):
            for node in nodes:
                yield proc, scope, node
                if node.nodes:
                    yield from walk(proc, node, node.nodes)
        for proc in self.processes():
            yield from walk(proc, None, proc.nodes)

    def node_index(self) -> dict[str, Node]:
        return {n.id: n for _, _, n in self.iter_nodes()}

    # --------------------------------------------------------------- validation
    @model_validator(mode="after")
    def _integrity(self) -> "LegalProcessModel":
        ids: set[str] = set()

        def claim(identifier: str) -> None:
            if identifier in ids:
                raise ValueError(f"duplicate id: {identifier}")
            ids.add(identifier)

        actor_ids = {a.id for a in self.actors}
        decision_ids = {d.id for d in self.decisions}
        node_owner: dict[str, str] = {}
        for part in self.participants:
            claim(part.id)
            if part.actor and part.actor not in actor_ids:
                raise ValueError(f"participant {part.id} references unknown actor {part.actor}")
            if part.process is None:
                continue
            proc = part.process
            claim(proc.id)
            lane_ids = {lane.id for lane in proc.lanes}
            for lane in proc.lanes:
                claim(lane.id)
                if lane.actor and lane.actor not in actor_ids:
                    raise ValueError(f"lane {lane.id} references unknown actor {lane.actor}")
            for d in proc.data:
                claim(d.id)
            for a in proc.annotations:
                claim(a.id)

            def check_scope(nodes, flows, data, in_lanes):
                local = {n.id for n in nodes}
                data_ids = {d.id for d in data} | {d.id for d in proc.data}
                for d in data:
                    claim(d.id)
                for n in nodes:
                    claim(n.id)
                    node_owner[n.id] = part.id
                    if in_lanes and lane_ids and n.type != "boundaryEvent" and n.lane not in lane_ids:
                        raise ValueError(f"node {n.id} must sit in a lane of {proc.id}")
                    if n.type == "boundaryEvent":
                        if n.attached_to not in local:
                            raise ValueError(f"boundary {n.id} must attach to an activity in its scope")
                    if n.decision_ref and n.decision_ref not in decision_ids:
                        raise ValueError(f"{n.id} references unknown decision {n.decision_ref}")
                    if n.bearer and n.bearer not in actor_ids:
                        raise ValueError(f"{n.id} has unknown bearer {n.bearer}")
                    for ref in n.data_inputs + n.data_outputs:
                        if ref not in data_ids:
                            raise ValueError(f"{n.id} references unknown data {ref}")
                    if n.nodes:
                        check_scope(n.nodes, n.flows, n.data, False)
                for f in flows:
                    claim(f.id)
                    if f.source not in local or f.target not in local:
                        raise ValueError(f"flow {f.id} must connect nodes in the same scope")
                for n in nodes:
                    if n.default and n.default not in {f.id for f in flows}:
                        raise ValueError(f"default flow {n.default} of {n.id} not found")

            check_scope(proc.nodes, proc.flows, [], True)
            all_ids = ids.copy()
            for a in proc.annotations:
                for target in a.attached_to:
                    if target not in all_ids:
                        raise ValueError(f"annotation {a.id} attaches to unknown {target}")
        participant_ids = {p.id for p in self.participants}
        for mf in self.message_flows:
            claim(mf.id)
            src = node_owner.get(mf.source, mf.source if mf.source in participant_ids else None)
            tgt = node_owner.get(mf.target, mf.target if mf.target in participant_ids else None)
            if src is None or tgt is None:
                raise ValueError(f"message flow {mf.id} has an unknown endpoint")
            if src == tgt:
                raise ValueError(f"message flow {mf.id} must connect different pools")
        for d in self.decisions:
            claim(d.id)
        return self


Node.model_rebuild()
