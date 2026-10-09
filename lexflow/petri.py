"""LPIR -> workflow net (Petri net) -> soundness check -> POWL 2.0.

Per-participant control-flow projection (message flows and data are dropped).
Mapping follows the usual BPMN->Petri patterns (Dijkman et al. 2008), with
these documented approximations so the result is a single-source /
single-sink workflow net:

* sub-processes are inlined (entry/exit pass-through places);
* event-based gateways become exclusive choices between their catch events;
* an interrupting boundary event becomes an exclusive choice "activity completes
  | boundary fires" in front of the host;
* a non-interrupting boundary event becomes an optional branch that runs
  concurrently with the host and re-joins after it;
* a non-interrupting event sub-process becomes an optional branch concurrent
  with the whole process;
* inclusive gateways are not supported in this projection (reported).
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass, field

from .ir import ACTIVITY_TYPES, Node, Process

GLYPH = {"timer": "⏱ ", "message": "✉ ", "signal": "△ ", "error": "⚡ ",
         "escalation": "↑ ", "conditional": "≡ "}


@dataclass
class Graph:
    nodes: dict[str, dict] = field(default_factory=dict)      # id -> {kind, label}
    edges: set[tuple[str, str]] = field(default_factory=set)
    notes: list[str] = field(default_factory=list)
    _n: itertools.count = field(default_factory=itertools.count)

    def add(self, kind: str, label: str | None = None, ident: str | None = None) -> str:
        ident = ident or f"_{kind}{next(self._n)}"
        self.nodes[ident] = {"kind": kind, "label": label}
        return ident

    def link(self, a: str, b: str):
        self.edges.add((a, b))

    def preds(self, n):
        return [a for a, b in self.edges if b == n]

    def succs(self, n):
        return [b for a, b in self.edges if a == n]

    def redirect_in(self, old: str, new: str):
        for a, b in list(self.edges):
            if b == old:
                self.edges.discard((a, b))
                self.edges.add((a, new))

    def redirect_out(self, old: str, new: str):
        for a, b in list(self.edges):
            if a == old:
                self.edges.discard((a, b))
                self.edges.add((new, b))


def _label(n: Node) -> str:
    return GLYPH.get(n.event or "", "") + (n.name or n.id)


def project(proc: Process) -> Graph:
    g = Graph()
    boundaries: list[Node] = []
    esps: list[Node] = []
    ends: list[str] = []
    end_ids: set[str] = set()
    block: dict[str, tuple[str, str]] = {}   # activity id -> (entry, exit) node ids in g

    def scope(nodes: list[Node], flows, top: bool):
        local_entry: dict[str, str] = {}
        local_exit: dict[str, str] = {}
        starts, scope_ends = [], []
        for n in nodes:
            if n.type == "boundaryEvent":
                boundaries.append(n)
                ident = g.add("task", _label(n), n.id)
                local_entry[n.id] = local_exit[n.id] = ident
            elif n.type in ("subProcess", "transaction") and n.triggered_by_event:
                esps.append(n)
                continue
            elif n.type in ("subProcess", "transaction", "adHocSubProcess"):
                entry = g.add("xor", None, f"{n.id}__in")
                exit_ = g.add("xor", None, f"{n.id}__out")
                inner_starts, inner_ends = scope(n.nodes, n.flows, top=False)
                for s in inner_starts:
                    g.link(entry, s)
                for e in inner_ends:
                    g.link(e, exit_)
                local_entry[n.id], local_exit[n.id] = entry, exit_
                block[n.id] = (entry, exit_)
            elif n.type == "startEvent":
                ident = g.add("xor", None, n.id)
                starts.append(ident)
                local_entry[n.id] = local_exit[n.id] = ident
            elif n.type == "endEvent":
                ident = g.add("xor", None, n.id)
                scope_ends.append(ident)
                end_ids.add(ident)
                local_entry[n.id] = local_exit[n.id] = ident
            elif n.type in ("exclusiveGateway", "eventBasedGateway"):
                ident = g.add("xor", None, n.id)
                local_entry[n.id] = local_exit[n.id] = ident
            elif n.type == "parallelGateway":
                ident = g.add("and", None, n.id)
                local_entry[n.id] = local_exit[n.id] = ident
            elif n.type in ("inclusiveGateway", "complexGateway"):
                g.notes.append(f"{n.id}: {n.type} not supported in WF-net projection")
                ident = g.add("xor", None, n.id)
                local_entry[n.id] = local_exit[n.id] = ident
            else:  # tasks, call activities, intermediate events
                ident = g.add("task", _label(n), n.id)
                local_entry[n.id] = local_exit[n.id] = ident
                if n.type not in ACTIVITY_TYPES and n.type not in ("intermediateCatchEvent", "intermediateThrowEvent"):
                    g.notes.append(f"{n.id}: unexpected type {n.type}")
        for f in flows:
            g.link(local_exit[f.source], local_entry[f.target])
        if top:
            ends.extend(scope_ends)
        return starts, scope_ends

    starts, _ = scope(proc.nodes, proc.flows, top=True)
    if len(starts) != 1:
        g.notes.append(f"{proc.id}: {len(starts)} start events; merged")

    # ---- boundary events -------------------------------------------------
    for b in boundaries:
        host_in, host_out = block.get(b.attached_to, (b.attached_to, b.attached_to))
        handler_ends = _reachable_ends(g, b.id, end_ids)
        if b.interrupting:
            split = g.add("xor")
            g.redirect_in(host_in, split)
            g.link(split, host_in)
            g.link(split, b.id)
            g.notes.append(f"{b.id}: interrupting boundary -> exclusive choice before {b.attached_to}")
        else:
            and_s, and_j = g.add("and"), g.add("and")
            choice, merge = g.add("xor"), g.add("xor")
            g.redirect_in(host_in, and_s)
            g.link(and_s, host_in)
            g.redirect_out(host_out, and_j)
            g.link(host_out, and_j)
            g.link(and_s, choice)
            g.link(choice, merge)            # boundary never fires
            g.link(choice, b.id)
            for e in handler_ends:
                if e in ends:
                    ends.remove(e)
                for a, b2 in list(g.edges):        # an inner end must not also complete its sub-process
                    if a == e:
                        g.edges.discard((a, b2))
                g.link(e, merge)
            g.link(merge, and_j)
            g.notes.append(f"{b.id}: non-interrupting boundary -> optional branch concurrent with {b.attached_to}")

    # ---- single sink: exclusive end events merge (XOR) before the sink ------
    sink = g.add("end", "end", "__end")
    done = g.add("xor", None, "__done")
    for e in ends:
        g.link(e, done)
    g.link(done, sink)

    # ---- event sub-processes: optional branch concurrent with the whole process
    source = g.add("start", "start", "__start")
    if esps:
        and_s, and_j = g.add("and"), g.add("and")
        g.link(source, and_s)
        for s in starts:
            g.link(and_s, s)
        g.redirect_in(sink, and_j)
        g.link(and_j, sink)
        for esp in esps:
            choice, merge = g.add("xor"), g.add("xor")
            g.link(and_s, choice)
            g.link(choice, merge)
            inner_starts, inner_ends = _inline_esp(g, esp)
            for s in inner_starts:
                g.link(choice, s)
            for e in inner_ends:
                g.link(e, merge)
            g.link(merge, and_j)
            g.notes.append(f"{esp.id}: event sub-process -> optional branch concurrent with the process")
    else:
        for s in starts:
            g.link(source, s)
    _normalise(g)
    return g


def _inline_esp(g: Graph, esp: Node):
    starts, ends = [], []
    for n in esp.nodes:
        if n.type == "startEvent":
            ident = g.add("task", _label(n), n.id)
            starts.append(ident)
        elif n.type == "endEvent":
            ends.append(g.add("xor", None, n.id))
        else:
            g.add("task", _label(n), n.id)
    for f in esp.flows:
        g.link(f.source, f.target)
    return starts, ends


def _reachable_ends(g: Graph, start: str, ends) -> list[str]:
    seen, stack, found = set(), [start], []
    while stack:
        n = stack.pop()
        if n in seen:
            continue
        seen.add(n)
        if n in ends:
            found.append(n)
            continue
        stack.extend(g.succs(n))
    return found


def _normalise(g: Graph):
    """Tasks get exactly one input and one output (implicit XOR-join / AND-split made explicit)."""
    for n, meta in list(g.nodes.items()):
        if meta["kind"] != "task":
            continue
        ins, outs = g.preds(n), g.succs(n)
        if len(ins) > 1:
            j = g.add("xor")
            for a in ins:
                g.edges.discard((a, n))
                g.link(a, j)
            g.link(j, n)
        if len(outs) > 1:
            s = g.add("and")
            for b in outs:
                g.edges.discard((n, b))
                g.link(s, b)
            g.link(n, s)


# ------------------------------------------------------------- Petri net build
def to_workflow_net(g: Graph, name: str = "net"):
    from pm4py.objects.petri_net.obj import Marking, PetriNet
    from pm4py.objects.petri_net.utils.petri_utils import add_arc_from_to

    net = PetriNet(name)
    places: dict = {}

    def place(key: str):
        if key not in places:
            p = PetriNet.Place(key)
            net.places.add(p)
            places[key] = p
        return places[key]

    tcount = itertools.count()

    def trans(label: str | None, key: str):
        t = PetriNet.Transition(f"t{next(tcount)}_{key}", label)
        net.transitions.add(t)
        return t

    source, sink = place("source"), place("sink")
    for n, meta in g.nodes.items():
        kind = meta["kind"]
        ins = [place(f"{a}->{n}") for a in g.preds(n)]
        outs = [place(f"{n}->{b}") for b in g.succs(n)]
        if kind == "start":
            t = trans(None, n)
            add_arc_from_to(source, t, net)
            for p in outs:
                add_arc_from_to(t, p, net)
        elif kind == "end":
            for p in ins:
                t = trans(None, f"{n}_{p.name}")
                add_arc_from_to(p, t, net)
                add_arc_from_to(t, sink, net)
        elif kind in ("task", "and"):
            t = trans(meta["label"] if kind == "task" else None, n)
            for p in ins:
                add_arc_from_to(p, t, net)
            for p in outs:
                add_arc_from_to(t, p, net)
        elif kind == "xor":
            hub = place(f"xor:{n}")
            for p in ins:
                t = trans(None, f"{n}_in")
                add_arc_from_to(p, t, net)
                add_arc_from_to(t, hub, net)
            for p in outs:
                t = trans(None, f"{n}_out")
                add_arc_from_to(hub, t, net)
                add_arc_from_to(t, p, net)
    im, fm = Marking({source: 1}), Marking({sink: 1})
    _reduce_silent(net, im, fm)
    return net, im, fm


def _reduce_silent(net, im, fm):
    """Collapse silent 1-in/1-out transitions between private places (keeps behaviour)."""
    from pm4py.objects.petri_net.utils import petri_utils
    changed = True
    while changed:
        changed = False
        for t in list(net.transitions):
            if t.label is not None or len(t.in_arcs) != 1 or len(t.out_arcs) != 1:
                continue
            p_in = next(iter(t.in_arcs)).source
            p_out = next(iter(t.out_arcs)).target
            if p_in is p_out or p_in in im or p_out in fm or p_in in fm or p_out in im:
                continue
            if len(p_in.out_arcs) != 1 or len(p_out.in_arcs) != 1:
                continue
            # merge p_out into p_in
            for arc in list(p_out.out_arcs):
                petri_utils.add_arc_from_to(p_in, arc.target, net)
            petri_utils.remove_transition(net, t)
            petri_utils.remove_place(net, p_out)
            changed = True
            break


# ----------------------------------------------------------------- analysis
@dataclass
class NetReport:
    process: str
    places: int
    transitions: int
    visible: int
    sound: bool | None
    reachable_states: int | None
    powl: str | None
    notes: list[str]
    error: str | None = None


def analyse(proc: Process, out_dir=None) -> tuple[NetReport, object, object, object]:
    import pm4py
    g = project(proc)
    net, im, fm = to_workflow_net(g, proc.id)
    sound = None
    try:
        res = pm4py.check_soundness(net, im, fm)
        sound = bool(res[0] if isinstance(res, tuple) else res)
    except Exception as e:  # pragma: no cover - reported, not fatal
        g.notes.append(f"soundness check failed: {e}")
    states = None
    try:
        from pm4py.objects.petri_net.utils import reachability_graph
        ts = reachability_graph.construct_reachability_graph(net, im)
        states = len(ts.states)
    except Exception as e:  # pragma: no cover
        g.notes.append(f"reachability failed: {e}")
    powl_txt, err = None, None
    powl_model = None
    try:
        import powl
        powl_model = powl.convert_from_workflow_net(net)
        powl_txt = repr(powl_model)
    except Exception as e:
        err = f"POWL conversion: {type(e).__name__}: {e}"
    if out_dir is not None:
        from pathlib import Path
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        pm4py.write_pnml(net, im, fm, str(out / f"{proc.id}.pnml"))
        try:
            pm4py.save_vis_petri_net(net, im, fm, str(out / f"{proc.id}.petri.svg"))
        except Exception as e:  # pragma: no cover
            g.notes.append(f"petri svg: {e}")
        if powl_model is not None:
            try:
                import powl
                powl.save_visualization(powl_model, str(out / f"{proc.id}.powl.svg"))
            except Exception as e:  # pragma: no cover
                g.notes.append(f"powl svg: {e}")
    visible = sum(1 for t in net.transitions if t.label is not None)
    rep = NetReport(proc.id, len(net.places), len(net.transitions), visible, sound, states, powl_txt, g.notes, err)
    return rep, net, im, fm


# ----------------------------------------------------------- POWL rendering
def _freq(m) -> str:
    lo, hi = m.min_freq, m.max_freq
    if lo == 1 and hi == 1:
        return ""
    if lo == 0 and hi == 1:
        return "?"
    if hi is None:
        return "*" if lo == 0 else "+"
    return f"{{{lo},{hi}}}"


def powl_text(m, indent: int = 0) -> str:
    """Readable POWL 2.0: PO = partial order (no edge = concurrent), CHOICE = choice graph."""
    from powl.objects.tagged_powl.activity import Activity
    pad = "  " * indent
    if isinstance(m, Activity):
        return f"{pad}{'τ' if m.label is None else m.label}{_freq(m)}"
    kind = type(m).__name__
    nodes = list(m.get_nodes())
    names = {id(n): f"n{i}" for i, n in enumerate(nodes)}
    head = "PO" if kind == "PartialOrder" else "CHOICE" if kind == "ChoiceGraph" else kind
    lines = [f"{pad}{head}{_freq(m)} ["]
    for n in nodes:
        sub = powl_text(n, indent + 2)
        lines.append(f"{pad}  {names[id(n)]}:")
        lines.append(sub)
    edges = [f"{names[id(a)]}→{names[id(b)]}" for a, b in m.get_edges()]
    if edges:
        lines.append(f"{pad}  order: " + ", ".join(edges))
    if kind == "ChoiceGraph":
        lines.append(f"{pad}  start: " + ", ".join(names[id(n)] for n in m.start_nodes())
                     + "  end: " + ", ".join(names[id(n)] for n in m.end_nodes()))
    lines.append(f"{pad}]")
    return "\n".join(lines)
