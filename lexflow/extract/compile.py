"""Deterministic modeling conventions: LegalProcessFacts -> LPIR (BPMN-ready).

Conventions (same for every ordinance, reviewable by lawyers once):
* the public body is one pool; its officials are lanes; private parties and courts are
  black-box pools connected by message flows;
* ``after`` lists are prerequisites: several -> parallel join; several unconditional
  successors -> parallel split; conditional successors -> exclusive split with the
  unconditional successor as default;
* a filing/notice by an outside party becomes a message catch in the agency process; with
  a lapsing deadline it becomes an event-based gateway (message vs timer);
* agency deadlines become timer boundary events: non-interrupting when the text says
  missing them has no effect (directory), interrupting otherwise;
* decision steps with a table become business-rule tasks bound to DMN.
"""
from __future__ import annotations

import re

from ..ir import (Actor, Decision, InputClause, Lane, LegalProcessModel, MessageFlow, Node, OutputClause,
                  Participant, Process, Provenance, Review, Rule, SectionText, SequenceFlow, Source, Timer)
from .schema import LegalProcessFacts, Quote

INTERNAL = {"public-body", "official", "other-government"}
UNIT = {"hours": "H", "days": "D", "business_days": "D", "weeks": "W", "months": "M", "years": "Y"}
TASK_FOR_KIND = {"notice": "sendTask", "decision": "userTask", "hearing": "userTask", "record": "task",
                 "review": "userTask", "inspection": "userTask", "payment": "receiveTask", "act": "task",
                 "filing": "receiveTask"}


def iso_duration(amount: int, unit: str) -> str:
    u = UNIT[unit]
    return f"PT{amount}{u}" if u == "H" else f"P{amount}{u}"


def compile_facts(facts: LegalProcessFacts, *, model_id: str, jurisdiction: str, jurisdiction_name: str,
                  code: str, text: SectionText, jurisdiction_qid: str | None = None,
                  provenance: Provenance | None = None) -> LegalProcessModel:
    def src(q: Quote, grounding: str = "explicit", note: str | None = None) -> Source:
        sub = "".join(f"({p})" for p in q.subsection.split(".")) if q.subsection else ""
        return Source(citation=f"{code} § {q.section}{sub}", section=q.section, subsection=q.subsection,
                      code=code, jurisdiction=jurisdiction, quote=q.quote, url=text.url, grounding=grounding, note=note)

    actors = {a.id: a for a in facts.actors}
    internal = [a for a in facts.actors if a.kind in INTERNAL]
    external = [a for a in facts.actors if a.kind not in INTERNAL]
    lanes = [Lane(id=f"ln_{a.id}", name=a.name, actor=a.id) for a in internal]
    default_lane = lanes[0].id if lanes else None

    nodes: list[Node] = []
    flows: list[SequenceFlow] = []
    mflows: list[MessageFlow] = []
    counter = iter(range(1, 10_000))

    def fid():
        return f"sf{next(counter)}"

    def lane_of(actor_id):
        return f"ln_{actor_id}" if actor_id in {a.id for a in internal} else default_lane

    start = Node(id="start", type="startEvent", name=facts.trigger[:60], lane=default_lane,
                 sources=[src(facts.trigger_source)])
    nodes.append(start)
    entry: dict[str, str] = {}      # step id -> first node id of its block
    exit_: dict[str, str] = {}      # step id -> last node id of its block (where successors attach)
    miss_flows: list[tuple[str, str]] = []   # (timer node id, step/outcome id) for deadlines with on_miss
    pool_of_external = {a.id: f"p_{a.id}" for a in external}

    for s in facts.steps:
        a = actors[s.actor]
        sources = [src(s.source)]
        if a.kind in INTERNAL:
            ntype = "businessRuleTask" if s.decision else TASK_FOR_KIND[s.kind]
            if s.recipient and actors[s.recipient].kind not in INTERNAL and ntype != "businessRuleTask":
                ntype = "sendTask"
            node = Node(id=s.id, type=ntype, name=s.action, lane=lane_of(a.id), sources=sources,
                        deontic=None if s.modality == "none" else ("obligation" if s.kind == "decision" and s.modality == "obligation" else s.modality),
                        bearer=a.id if s.modality != "none" else None, decision_ref=s.decision,
                        ref=s.action if ntype in ("sendTask", "receiveTask") else None)
            nodes.append(node)
            entry[s.id] = exit_[s.id] = s.id
            if ntype == "sendTask" and s.recipient in pool_of_external:
                mflows.append(MessageFlow(id=f"mf_{s.id}", source=s.id, target=pool_of_external[s.recipient], name=s.action))
            if s.deadline:
                d = s.deadline
                soft = d.consequence == "directory-only"
                b = Node(id=f"{s.id}_deadline", type="boundaryEvent", attached_to=s.id, interrupting=not soft,
                         event="timer", name=f"{d.amount} {d.unit.replace('_', ' ')}",
                         timer=Timer(value=iso_duration(d.amount, d.unit), anchor=d.anchor, strict=not soft),
                         sources=[src(d.source)])
                if d.on_miss:
                    nodes.append(b)
                    miss_flows.append((b.id, d.on_miss))
                else:
                    name = ("Deadline passed (no effect)" if soft else "Deemed denied" if d.consequence == "deemed-denial"
                            else f"Deadline missed: {s.action}"[:60])
                    end = Node(id=f"{s.id}_deadline_end", type="endEvent", lane=lane_of(a.id), name=name,
                               sources=[src(d.source, "explicit" if soft or d.consequence == "deemed-denial" else "implied")])
                    nodes += [b, end]
                    flows.append(SequenceFlow(id=fid(), source=b.id, target=end.id))
        else:
            # observed from the agency side: a message arrives (optionally racing a deadline)
            recv_lane = lane_of(s.recipient) if s.recipient else default_lane
            catch = Node(id=s.id, type="intermediateCatchEvent", event="message", ref=s.action,
                         name=f"{s.action}"[:60], lane=recv_lane, sources=sources,
                         deontic=None if s.modality == "none" else s.modality, bearer=a.id if s.modality != "none" else None)
            mflows.append(MessageFlow(id=f"mf_{s.id}", source=pool_of_external[a.id], target=s.id, name=s.action))
            if s.deadline and s.deadline.consequence in ("right-lapses", "action-invalid", "deemed-denial", "unstated"):
                d = s.deadline
                gw = Node(id=f"{s.id}_wait", type="eventBasedGateway", name=f"{s.action} in time?"[:60], lane=recv_lane)
                timer = Node(id=f"{s.id}_timeout", type="intermediateCatchEvent", event="timer", lane=recv_lane,
                             name=f"{d.amount} {d.unit.replace('_', ' ')} pass",
                             timer=Timer(value=iso_duration(d.amount, d.unit), anchor=d.anchor),
                             sources=[src(d.source)])
                nodes += [gw, catch, timer]
                flows += [SequenceFlow(id=fid(), source=gw.id, target=catch.id),
                          SequenceFlow(id=fid(), source=gw.id, target=timer.id)]
                if d.on_miss:
                    miss_flows.append((timer.id, d.on_miss))
                else:
                    lapse = Node(id=f"{s.id}_lapsed", type="endEvent", lane=recv_lane, name="Time to act lapsed",
                                 sources=[src(d.source, "implied", "Consequence of missing the deadline inferred")])
                    nodes.append(lapse)
                    flows.append(SequenceFlow(id=fid(), source=timer.id, target=lapse.id))
                entry[s.id], exit_[s.id] = gw.id, catch.id
            else:
                nodes.append(catch)
                entry[s.id] = exit_[s.id] = s.id

    for o in facts.outcomes:
        nodes.append(Node(id=o.id, type="endEvent", name=o.description[:60], lane=default_lane, sources=[src(o.source)]))
        entry[o.id] = exit_[o.id] = o.id

    # ---------------------------------------------------------------- wiring
    items = [(s.id, s.after, s.condition) for s in facts.steps] + [(o.id, o.after, o.when) for o in facts.outcomes]
    # an item with no 'after' follows the start, unless it is only ever reached by a missed deadline
    miss_only = {s.deadline.on_miss for s in facts.steps if s.deadline and s.deadline.on_miss}
    preds = {i: (after or ([] if i in miss_only else ["__start"])) for i, after, _ in items}
    cond = {i: c for i, _, c in items}
    succs: dict[str, list[str]] = {}
    for i, after in preds.items():
        for p in after:
            succs.setdefault(p, []).append(i)

    def out_of(p):
        return start.id if p == "__start" else exit_[p]

    join_mode = {s.id: s.join for s in facts.steps} | {o.id: o.join for o in facts.outcomes}
    join_for: dict[str, str] = {}
    for i, after in preds.items():
        if len(after) > 1:
            # 'all': wait for every prerequisite (parallel join); 'any': branches that rejoin (exclusive merge)
            jtype = "parallelGateway" if join_mode.get(i, "all") == "all" else "exclusiveGateway"
            j = Node(id=f"{i}_join", type=jtype, name="", lane=nodes[[n.id for n in nodes].index(entry[i])].lane)
            nodes.append(j)
            flows.append(SequenceFlow(id=fid(), source=j.id, target=entry[i]))
            join_for[i] = j.id

    def target_of(i):
        return join_for.get(i, entry[i])

    for p, children in succs.items():
        src_node = out_of(p)
        lane = next((n.lane for n in nodes if n.id == src_node), default_lane)
        if len(children) == 1:
            c = children[0]
            if cond[c]:
                gw = Node(id=f"{src_node}_gw", type="exclusiveGateway", name=f"{cond[c].replace('_', ' ')}?", lane=lane)
                end = Node(id=f"{src_node}_not_{c}", type="endEvent", name=f"Not {cond[c].replace('_', ' ')}"[:60], lane=lane)
                dflt = fid()
                gw.default = dflt
                nodes += [gw, end]
                flows += [SequenceFlow(id=fid(), source=src_node, target=gw.id),
                          SequenceFlow(id=fid(), source=gw.id, target=target_of(c), name="Yes", condition=cond[c]),
                          SequenceFlow(id=dflt, source=gw.id, target=end.id, name="No")]
            else:
                flows.append(SequenceFlow(id=fid(), source=src_node, target=target_of(c)))
            continue
        conditional = [c for c in children if cond[c]]
        plain = [c for c in children if not cond[c]]
        if conditional:
            gw = Node(id=f"{src_node}_gw", type="exclusiveGateway", name="Which path?", lane=lane)
            nodes.append(gw)
            flows.append(SequenceFlow(id=fid(), source=src_node, target=gw.id))
            for c in conditional:
                flows.append(SequenceFlow(id=fid(), source=gw.id, target=target_of(c), name=cond[c].replace("_", " "),
                                          condition=cond[c]))
            if plain:
                dflt = fid()
                gw.default = dflt
                tail = plain[0]
                if len(plain) > 1:      # several unconditional siblings of a conditional one: run them together
                    split = Node(id=f"{src_node}_par", type="parallelGateway", name="", lane=lane)
                    nodes.append(split)
                    flows.append(SequenceFlow(id=dflt, source=gw.id, target=split.id, name="otherwise"))
                    for c in plain:
                        flows.append(SequenceFlow(id=fid(), source=split.id, target=target_of(c)))
                else:
                    flows.append(SequenceFlow(id=dflt, source=gw.id, target=target_of(tail), name="otherwise"))
        else:
            split = Node(id=f"{src_node}_par", type="parallelGateway", name="", lane=lane)
            nodes.append(split)
            flows.append(SequenceFlow(id=fid(), source=src_node, target=split.id))
            for c in children:
                flows.append(SequenceFlow(id=fid(), source=split.id, target=target_of(c)))

    for timer_id, item in miss_flows:
        if item not in entry:
            raise ValueError(f"deadline on_miss {item!r} is not a step or outcome id")
        flows.append(SequenceFlow(id=fid(), source=timer_id, target=target_of(item)))

    # a node reached from several places gets an exclusive merge in front (missed deadlines rejoining a path)
    incoming: dict[str, list[SequenceFlow]] = {}
    for f in flows:
        incoming.setdefault(f.target, []).append(f)
    by_id = {n.id: n for n in nodes}
    for target, fs in list(incoming.items()):
        n = by_id.get(target)
        if n is None or len(fs) < 2 or n.type.endswith("Gateway"):
            continue
        m = Node(id=f"{target}_merge", type="exclusiveGateway", name="", lane=n.lane)
        nodes.append(m)
        for f in fs:
            f.target = m.id
        flows.append(SequenceFlow(id=fid(), source=m.id, target=target))

    # dangling ends
    has_out = {f.source for f in flows}
    for n in list(nodes):
        if n.type in ("endEvent", "boundaryEvent") or n.id in has_out:
            continue
        if n.type == "eventBasedGateway":
            continue
        end = Node(id=f"{n.id}_done", type="endEvent", name="Done", lane=n.lane)
        nodes.append(end)
        flows.append(SequenceFlow(id=fid(), source=n.id, target=end.id))

    decisions = []
    for d in facts.decisions:
        decisions.append(Decision(
            id=d.id, name=d.question[:80], question=d.question, hit_policy=d.hit_policy,
            inputs=[InputClause(id=f"{d.id}_in_{c.name}", label=c.label, expression=c.name, type_ref=c.type) for c in d.inputs],
            outputs=[OutputClause(id=f"{d.id}_out_{c.name}", label=c.label, name=c.name, type_ref=c.type) for c in d.outputs],
            rules=[Rule(id=f"{d.id}_r{i + 1}", inputs=r.when, outputs=r.then, sources=[src(r.source)])
                   for i, r in enumerate(d.rules)]))

    agency_actor = next((a for a in internal if a.kind == "public-body"), internal[0] if internal else None)
    proc = Process(id=f"proc_{re.sub(r'[^a-z0-9_]', '_', model_id.lower())}", name=facts.process_name,
                   lanes=lanes, nodes=nodes, flows=flows)
    participants = [Participant(id="p_agency", name=agency_actor.name if agency_actor else jurisdiction_name,
                                actor=agency_actor.id if agency_actor else None, process=proc)]
    participants += [Participant(id=pool_of_external[a.id], name=a.name, actor=a.id) for a in external]
    return LegalProcessModel(
        id=model_id, title=facts.process_name, jurisdiction=jurisdiction, jurisdiction_name=jurisdiction_name,
        jurisdiction_qid=jurisdiction_qid, summary=facts.trigger,
        actors=[Actor(id=a.id, name=a.name, kind=a.kind) for a in facts.actors],
        participants=participants, message_flows=mflows, decisions=decisions, texts=[text],
        provenance=provenance or Provenance(method="llm-extraction"),
        review=Review(status="draft", gaps=facts.gaps))
