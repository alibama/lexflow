"""A process instance: one person's case under a lexflow model, with the step it is on, each deadline (with its
section and quote) and whether it is on time or overdue.

An instance is plain JSON that the user keeps: in the browser's storage, or in a file they export.  Nothing in this
module stores it, and nothing here needs an account.  The shape (``SCHEMA``)::

    {"lab": "lexflow-lab/1", "state": "va", "question": "records", "model_id": "va.records",
     "place": {"gov_id": "47210400100000", "name": "City of Charlottesville"},      # optional
     "started": "2026-10-30",
     "events": [{"type": "request_sent", "date": "2026-10-30"},
                {"type": "extension_claimed", "date": "2026-11-04", "step": "respond"}],
     "options": {"closures": ["2026-11-20"], "observes": [], "opens": [], "variant": null}}

Free-text notes may sit on events in the user's copy; they are ignored here and never needed.  The place and the
label stay in the user's copy too: the lab page never sends them to count a timeline.  ``options`` holds the
per-case calendar choices the page lets the user set: days the office was closed, optional holidays the body
observes, holidays on which it was open (by holiday key) and a variant reading.

The steps come from the model's BPMN (the order of the flow, the lanes, the timers and where a missed timer leads),
joined by id to the model's facts, which keep each deadline's unit.  The unit matters: the compiler writes five
*business* days as ``P5D`` (lexflow/extract/compile.py, ``UNIT``), so the lab counts from the facts' ``unit`` and
says so when the BPMN timer reads differently (docs/design/lab-research.md §3.4).
"""
from __future__ import annotations

import json
import re
import sqlite3
import xml.etree.ElementTree as ET
from collections import deque
from dataclasses import dataclass, field
from datetime import date

from .. import config
from . import deadlines as D

SCHEMA = "lexflow-lab/1"
MODEL_ID = re.compile(r"^[a-z]{2}\.[a-z_]{1,40}$")
DISCLAIMER = ("Information, not legal advice. Dates are counted from the model's quoted law and the calendar shown; "
              "a body's closures, an agreement or a court order can change them. Check with the body's records "
              "officer or the oversight office named in the law.")

# --------------------------------------------------------------------------- events the user can record
# key: (label, who records it happening: "you" or "body")
EVENTS: dict[str, tuple[str, str]] = {
    "request_sent": ("Request sent", "you"),
    "request_received": ("Body received the request", "body"),
    "acknowledged": ("Acknowledgement received (states a date)", "body"),
    "fee_charged": ("Fee or cost estimate received", "body"),
    "fee_paid": ("Fee paid or estimate answered", "you"),
    "extension_claimed": ("Body claimed more time", "body"),
    "response_received": ("Response received", "body"),
    "records_received": ("Records received or made available", "body"),
    "denied": ("Denied in whole or part", "body"),
    "appeal_sent": ("Appeal, review request or petition sent", "you"),
    "appeal_decided": ("Appeal or review decided", "body"),
    "complaint_sent": ("Complaint sent", "you"),
    "suit_filed": ("Suit or motion filed", "you"),
    "clock_started": ("Clock started for a step (the law's own starting event)", "you"),
    "step_done": ("Step done", "you"),
    "office_closed": ("Office closed all day", "body"),
    "closed": ("Case closed", "you"),
}
ANSWERS = ("response_received", "records_received", "denied")
ANCHOR_WORDS = {
    "request_received": "the body receives the request",
    "started": "the process starts",
    "extension_claimed": "the body claims more time",
    "prev_due": "the end of the earlier period",
    "denied": "a denial (written, or deemed when a deadline passes)",
    "appeal_sent": "the appeal, review request or petition is received",
    "complaint_sent": "the complaint is received",
    "fee_charged": "you are told the charges",
    "records_received": "the records are made available",
    "acknowledged": "the date the body states in its acknowledgement",
    None: "the event the law names (record it with 'Clock started')",
}
GATEWAYS = {"exclusiveGateway", "parallelGateway", "inclusiveGateway", "eventBasedGateway", "complexGateway"}
FLOW_NODES = GATEWAYS | {"startEvent", "endEvent", "intermediateCatchEvent", "intermediateThrowEvent",
                         "boundaryEvent", "task", "userTask", "sendTask", "receiveTask", "businessRuleTask",
                         "serviceTask", "manualTask", "scriptTask", "callActivity", "subProcess"}
_B = "{http://www.omg.org/spec/BPMN/20100524/MODEL}"
_L = "{https://lexipedia.xyz/ns/lex/1.0}"


# =========================================================================== models
@dataclass
class Model:
    model_id: str
    state: str
    question: str
    title: str
    facts: dict
    bpmn: str | None = None
    citation: str | None = None
    source_url: str | None = None
    tier: str | None = None
    origin: str = "store"                       # store | curated
    steps: list[dict] = field(default_factory=list)
    outcomes: list[dict] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def step(self, sid: str | None) -> dict | None:
        return next((s for s in self.steps if s["id"] == sid), None)


def _compile_bpmn(spec: dict, state: str, question: str) -> str | None:
    """BPMN for a curated facts file that the store has not built yet (in memory only; nothing is written)."""
    try:
        from ..bpmn_xml import to_bpmn_xml
        from ..extract.compile import compile_facts
        from ..extract.schema import LegalProcessFacts
        from ..ir import SectionText
        from ..municipal import states as S
        from ..municipal.statutes import code_name
        code = code_name(state)
        section = (spec.get("sections") or [""])[0]
        model = compile_facts(LegalProcessFacts(**spec["facts"]), model_id=f"{state}-{question}", jurisdiction=state,
                              jurisdiction_name=S.NAME.get(state, state.upper()), code=code,
                              text=SectionText(section=section, title="", code=code, jurisdiction=state, text=""))
        return to_bpmn_xml(model)
    except Exception:                       # a model the compiler cannot take still shows its steps from the facts
        return None


def load_model(model_id: str, con: sqlite3.Connection | None = None) -> Model | None:
    """A model from the local store, or from ``curated/<state>/<question>.json`` when the store has none."""
    if not MODEL_ID.match(model_id or ""):
        return None
    state, question = model_id.split(".")
    row = None
    if con is not None:
        try:
            r = con.execute("SELECT title, tier, facts, bpmn, citation, source_url FROM process_models "
                            "WHERE model_id=?", (model_id,)).fetchone()
            row = dict(r) if r else None
        except sqlite3.Error:
            row = None
    facts = None
    if row and row.get("facts"):
        try:
            facts = json.loads(row["facts"])
        except ValueError:
            facts = None
    if facts:
        m = Model(model_id, state, question, row.get("title") or facts.get("process_name") or model_id, facts,
                  row.get("bpmn"), row.get("citation"), row.get("source_url"), row.get("tier"), "store")
    else:
        path = config.CURATED_DIR / state / f"{question}.json"
        if not path.exists():
            return None
        spec = json.loads(path.read_text(encoding="utf-8"))
        facts = spec.get("facts") or {}
        m = Model(model_id, state, question, facts.get("process_name") or model_id, facts,
                  _compile_bpmn(spec, state, question), tier="curated", origin="curated")
        m.notes.append("Loaded from the curated file; this lexflow has not built the model yet.")
    _attach_steps(m)
    return m


def list_models(con: sqlite3.Connection | None = None, state: str | None = None) -> list[dict]:
    """Models a case can start from: built ones in the store, then curated ones the store lacks."""
    out, seen = [], set()
    if con is not None:
        try:
            q = ("SELECT model_id, state, question, title, tier, citation FROM process_models "
                 "WHERE facts IS NOT NULL AND facts != ''" + (" AND state=?" if state else "") +
                 " ORDER BY state, question")
            for r in con.execute(q, (state,) if state else ()):
                out.append({**dict(r), "origin": "store"})
                seen.add(r["model_id"])
        except sqlite3.Error:
            pass
    for path in sorted(config.CURATED_DIR.glob("*/*.json")):
        st, qu = path.parent.name, path.stem
        mid = f"{st}.{qu}"
        if not MODEL_ID.match(mid) or mid in seen or (state and st != state):
            continue
        try:
            facts = json.loads(path.read_text(encoding="utf-8")).get("facts") or {}
        except ValueError:
            continue
        if facts.get("steps"):
            out.append({"model_id": mid, "state": st, "question": qu, "title": facts.get("process_name") or mid,
                        "tier": "curated", "citation": None, "origin": "curated"})
    for r in out:
        r["calendar"] = D.calendar_for(r["state"]).key
    return out


# =========================================================================== BPMN
def parse_bpmn(xml: str) -> dict:
    """Flow nodes, sequence flows and lane actors of a lexflow BPMN file (all processes, sub-processes included)."""
    root = ET.fromstring(xml.encode("utf-8") if isinstance(xml, str) else xml)
    nodes: dict[str, dict] = {}
    out: dict[str, list[str]] = {}
    inc: dict[str, list[str]] = {}
    lane_actor: dict[str, str] = {}
    review = None
    for lm in root.iter(_L + "model"):
        review = lm.get("reviewStatus")
    for proc in root.iter(_B + "process"):
        for lane in proc.iter(_B + "lane"):
            a = lane.find(f"{_B}extensionElements/{_L}actor")
            for ref in lane.findall(_B + "flowNodeRef"):
                if a is not None and ref.text:
                    lane_actor[ref.text.strip()] = a.get("ref")
        for el in proc.iter():
            tag = el.tag.rsplit("}", 1)[-1]
            if tag == "sequenceFlow":
                s, t = el.get("sourceRef"), el.get("targetRef")
                out.setdefault(s, []).append(t)
                inc.setdefault(t, []).append(s)
            elif tag in FLOW_NODES and el.get("id"):
                ext = el.find(_B + "extensionElements")
                dl = ext.find(_L + "deadline") if ext is not None else None
                src = ext.find(f"{_L}grounding/{_L}source") if ext is not None else None
                timer = el.find(f".//{_B}timeDuration")
                nodes[el.get("id")] = {
                    "id": el.get("id"), "type": tag, "name": el.get("name") or "", "attached": el.get("attachedToRef"),
                    "deadline": dict(dl.attrib) if dl is not None else None,
                    "timer": (timer.text or "").strip() if timer is not None else None,
                    "source": ({**{k: src.get(k) for k in ("citation", "section", "subsection", "url")},
                                "quote": (src.findtext(_L + "quote") or "").strip()} if src is not None else None)}
    return {"nodes": nodes, "out": out, "inc": inc, "lanes": lane_actor, "review": review}


def _order(g: dict) -> list[str]:
    """Breadth-first from the start events; a boundary event follows the activity it is attached to."""
    nodes, out = g["nodes"], g["out"]
    attached: dict[str, list[str]] = {}
    for n in nodes.values():
        if n["type"] == "boundaryEvent" and n["attached"]:
            attached.setdefault(n["attached"], []).append(n["id"])
    starts = [n for n in nodes if nodes[n]["type"] == "startEvent" and not g["inc"].get(n)] or \
             [n for n in nodes if nodes[n]["type"] == "startEvent"]
    seen, order, q = set(), [], deque(starts)
    while q:
        n = q.popleft()
        if n in seen or n not in nodes:
            continue
        seen.add(n)
        order.append(n)
        q.extend(out.get(n, []))
        q.extend(attached.get(n, []))
    return order + [n for n in nodes if n not in seen]


def _through_gateways(g: dict, start: str) -> list[str]:
    """The first non-gateway nodes reached from ``start``'s outgoing flows."""
    found, seen, q = [], set(), deque(g["out"].get(start, []))
    while q:
        n = q.popleft()
        if n in seen:
            continue
        seen.add(n)
        if g["nodes"].get(n, {}).get("type") in GATEWAYS:
            q.extend(g["out"].get(n, []))
        elif n in g["nodes"]:
            found.append(n)
    return found


def _sub(subsection: str | None) -> str:
    return "".join(f"({p})" for p in (subsection or "").split(".") if p)


def _attach_steps(m: Model) -> None:
    """Join the facts' steps to the BPMN: order, element type, lane, grounding URL, timer and missed-timer target."""
    f = m.facts
    actors = {a["id"]: a for a in f.get("actors", [])}
    fsteps = {s["id"]: s for s in f.get("steps", [])}
    outcomes = {o["id"]: o for o in f.get("outcomes", [])}
    g = None
    if m.bpmn:
        try:
            g = parse_bpmn(m.bpmn)
        except ET.ParseError:
            m.notes.append("The stored BPMN could not be read; steps come from the facts only.")
    order = [n for n in _order(g) if n in fsteps] if g else []
    order += [s for s in fsteps if s not in order]
    timers: dict[str, str] = {}
    if g:
        for nid, n in g["nodes"].items():
            if not n["deadline"]:
                continue
            if n["type"] == "boundaryEvent":
                timers[n["attached"]] = nid
            else:                           # a timer racing the requester's message after an event-based gateway
                for gw in g["inc"].get(nid, []):
                    if g["nodes"].get(gw, {}).get("type") == "eventBasedGateway":
                        for t in g["out"].get(gw, []):
                            if t != nid and t in fsteps:
                                timers[t] = nid
    gaps = f.get("gaps") or []

    def name_of(nid):
        if nid in fsteps:
            return fsteps[nid]["action"]
        if nid in outcomes:
            return outcomes[nid]["description"]
        return (g["nodes"].get(nid, {}).get("name") if g else None) or nid

    steps = []
    for i, sid in enumerate(order):
        s = fsteps[sid]
        a = actors.get(s.get("actor"), {})
        node = g["nodes"].get(sid) if g else None
        src = s.get("source") or {}
        nsrc = (node or {}).get("source") or {}
        nxt = [n for n in _through_gateways(g, sid) if not g["nodes"][n]["type"] == "boundaryEvent"] if node else \
              [o for o, st in fsteps.items() if sid in (st.get("after") or [])]
        step = {"id": sid, "n": i + 1, "name": s.get("action") or sid, "bpmn_type": (node or {}).get("type"),
                "actor": s.get("actor"), "actor_name": a.get("name") or s.get("actor"), "actor_kind": a.get("kind"),
                "you": a.get("kind") == "private-party", "kind": s.get("kind"), "modality": s.get("modality"),
                "condition": s.get("condition"), "after": s.get("after") or [], "next": nxt,
                "next_names": [name_of(n) for n in nxt],
                "section": src.get("section"), "subsection": src.get("subsection"),
                "citation": nsrc.get("citation") or (f"§ {src.get('section')}{_sub(src.get('subsection'))}"
                                                     if src.get("section") else None),
                "url": nsrc.get("url") or m.source_url, "quote": src.get("quote"), "deadline": None,
                "gaps": [x for x in gaps if re.search(rf"\b{re.escape(sid)}\b", x)]}
        d = s.get("deadline")
        if d:
            check = D.check_deadline(d)
            dsrc = d.get("source") or {}
            tnode = g["nodes"].get(timers.get(sid)) if g and timers.get(sid) else None
            on_miss = d.get("on_miss")
            missed = ([on_miss] if on_miss else []) or (_through_gateways(g, tnode["id"]) if tnode else [])
            anchor = classify_anchor(d.get("anchor"), check.rule)
            unit_note = None
            if tnode and tnode.get("timer") and d.get("unit") == "business_days":
                unit_note = (f"The BPMN timer is written {tnode['timer']} (calendar days); the lab counts "
                             f"{check.rule.describe()} from the model's facts.")
            step["deadline"] = {
                **check.rule.as_dict(), "rule": check.rule.describe(), "parse": check.as_dict(),
                "anchor_text": d.get("anchor"), "anchor_event": anchor, "starts_when": ANCHOR_WORDS.get(anchor),
                "consequence": d.get("consequence") or "unstated", "on_miss": missed,
                "on_miss_names": [name_of(n) for n in missed],
                "section": dsrc.get("section"), "subsection": dsrc.get("subsection"),
                "citation": ((tnode or {}).get("source") or {}).get("citation") or
                            (f"§ {dsrc.get('section')}{_sub(dsrc.get('subsection'))}" if dsrc.get("section") else None),
                "url": ((tnode or {}).get("source") or {}).get("url") or step["url"], "quote": dsrc.get("quote"),
                "bpmn_timer": (tnode or {}).get("timer"), "unit_note": unit_note,
                "extension": _is_extension(sid, d, check.rule),
                "gaps": [x for x in gaps if re.search(rf"\b{re.escape(sid)}\b", x) or
                         any(re.search(rf"\b{re.escape(o)}\b", x) for o in missed)]}
        steps.append(step)
    m.steps = steps
    m.outcomes = [{"id": o["id"], "name": o.get("description") or o["id"], "after": o.get("after") or [],
                   "quote": (o.get("source") or {}).get("quote"),
                   "citation": f"§ {(o.get('source') or {}).get('section', '')}"
                               f"{_sub((o.get('source') or {}).get('subsection'))}".strip()} for o in outcomes.values()]
    if g and g.get("review"):
        m.notes.append(f"BPMN review status: {g['review']}.")


def _is_extension(sid: str, d: dict, rule: D.DeadlineRule) -> bool:
    return "extend" in sid or rule.kind == "extension" or "original due date" in (d.get("anchor") or "").lower()


def classify_anchor(text: str | None, rule: D.DeadlineRule | None = None) -> str | None:
    """Which recorded event starts a deadline's clock, read from the model's anchor words."""
    if rule is not None and rule.kind == "set_by_body":
        return "acknowledged"
    t = (text or "").lower()
    if not t or "not stated" in t:
        return None
    if "original due date" in t:
        return "prev_due"
    if "b.4 response" in t:
        return "extension_claimed"
    if re.search(r"request for review|petition|appeal", t):
        return "appeal_sent"
    if "complaint" in t:
        return "complaint_sent"
    if "informed of the charges" in t:
        return "fee_charged"
    if "made available" in t:
        return "records_received"
    if re.search(r"denial|claim of exemption|rejected|refusal|mailed to the applicant", t):
        return "denied"
    if re.search(r"first use|commences|formation|effectiveness|original articles", t):
        return "started"
    if re.search(r"receiv|receipt|delivered|submission", t):
        return "request_received"
    return None


def model_steps(m: Model) -> dict:
    """What the lab shows before a case starts: the steps in BPMN order with their deadlines, and the vocabulary."""
    cal = D.calendar_for(m.state)
    return {"model": _model_head(m), "steps": m.steps, "outcomes": m.outcomes,
            "actors": [{"id": a["id"], "name": a["name"], "kind": a["kind"]} for a in m.facts.get("actors", [])],
            "gaps": m.facts.get("gaps") or [], "calendar": D.describe_calendar(cal),
            "events": [{"type": k, "label": v[0], "by": v[1]} for k, v in EVENTS.items()], "notes": m.notes,
            "disclaimer": DISCLAIMER}


def _model_head(m: Model) -> dict:
    return {"model_id": m.model_id, "state": m.state, "question": m.question, "title": m.title,
            "citation": m.citation, "url": m.source_url, "tier": m.tier, "origin": m.origin}


# =========================================================================== instances
@dataclass
class Event:
    type: str
    date: date
    step: str | None = None
    until: date | None = None
    implied: bool = False
    why: str = ""

    def as_dict(self) -> dict:
        d = {"type": self.type, "date": self.date.isoformat(), "label": EVENTS.get(self.type, (self.type,))[0]}
        if self.step:
            d["step"] = self.step
        if self.until:
            d["until"] = self.until.isoformat()
        if self.implied:
            d["implied"], d["why"] = True, self.why
        return d


def _day(x) -> date | None:
    if x is None or x == "":
        return None
    if isinstance(x, date):
        return x
    return date.fromisoformat(str(x)[:10])


def normalise(inst: dict) -> tuple[dict, list[Event], list[str]]:
    """Validate an instance; return its header, its events (sorted, unknown types dropped) and warnings."""
    if not isinstance(inst, dict):
        raise ValueError("an instance is a JSON object")
    state = str(inst.get("state") or "").lower()
    question = str(inst.get("question") or "")
    mid = str(inst.get("model_id") or f"{state}.{question}")
    if not MODEL_ID.match(mid):
        raise ValueError("model_id must look like 'va.records'")
    warnings, events = [], []
    for i, e in enumerate(inst.get("events") or []):
        if not isinstance(e, dict):
            continue
        t = str(e.get("type") or "")
        if t not in EVENTS:
            warnings.append(f"Event {i + 1}: unknown type {t!r} ignored.")
            continue
        try:
            d = _day(e.get("date"))
            until = _day(e.get("until"))
        except ValueError:
            warnings.append(f"Event {i + 1}: date not in YYYY-MM-DD form; ignored.")
            continue
        if d is None:
            warnings.append(f"Event {i + 1}: no date; ignored.")
            continue
        step = e.get("step") or None
        events.append(Event(t, d, str(step)[:80] if step else None, until))
    events.sort(key=lambda e: e.date)
    try:
        started = _day(inst.get("started"))
    except ValueError:
        started = None
    head = {"state": mid.split(".")[0], "question": mid.split(".")[1], "model_id": mid, "started": started,
            "place": inst.get("place") if isinstance(inst.get("place"), (dict, str)) else None,
            "options": inst.get("options") if isinstance(inst.get("options"), dict) else {}}
    return head, events, warnings


def _first(events: list[Event], types, after: date | None = None, step: str | None = None) -> Event | None:
    """The first event of the given types on or after ``after``; with ``step``, events tagged with another step are
    passed over (an untagged event can close any step)."""
    types = (types,) if isinstance(types, str) else tuple(types)
    for e in events:
        if e.type not in types or (after and e.date < after):
            continue
        if step and e.step and e.step != step:
            continue
        return e
    return None


def _done_types(step: dict, anchor: str | None, extension: bool, model: Model) -> tuple[str, ...]:
    if not step["you"]:
        if extension or anchor in ("complaint_sent",):
            return ANSWERS
        if anchor in ("appeal_sent", "denied"):
            return ("appeal_decided", "response_received", "records_received")
        if anchor in ("request_received", "started", "prev_due", None):
            extra = ()
            if any(s["deadline"] and s["deadline"]["extension"] for s in model.steps):
                extra += ("extension_claimed",)
            if any(s["deadline"] and s["deadline"]["kind"] == "set_by_body" for s in model.steps):
                extra += ("acknowledged",)
            return ANSWERS + extra
        return ANSWERS
    kind = step.get("kind")
    if kind == "payment":
        return ("fee_paid",)
    if kind == "filing":
        return ("appeal_sent", "suit_filed", "complaint_sent")
    return ()


def _status_word(applies: str, due: date | None, done: Event | None, you: bool, today: date) -> str:
    if due is None:
        return "waiting"
    if applies == "if":
        return "may apply"
    if done is not None:
        return "met" if done.date <= due else "late"
    if you:
        return "open" if today <= due else "lapsed"
    return "on time" if today <= due else "overdue"


def timeline(inst: dict, *, today: date | None = None, con: sqlite3.Connection | None = None,
             model: Model | None = None) -> dict:
    """The case's current step, every deadline (with how it was counted, its section and quote) and its status."""
    head, events, warnings = normalise(inst)
    model = model or load_model(head["model_id"], con)
    if model is None:
        raise LookupError(f"no model {head['model_id']}")
    today = today or date.today()
    cal = D.calendar_for(model.state)
    if cal.key == "us" and model.state != "us":
        warnings.append(f"No holiday table for {model.state.upper()}; federal holidays (5 U.S.C. § 6103) are used.")
    opts = D.Options.from_dict(head["options"])
    closures = {e.date for e in events if e.type == "office_closed"}
    opts = D.Options(opts.closures | closures, opts.observes, opts.opens, opts.variant)
    if opts.variant and not cal.variant(opts.variant):
        warnings.append(f"Unknown calendar variant {opts.variant!r} ignored.")
        opts = opts.with_variant(None)

    sent = _first(events, "request_sent")
    received = _first(events, "request_received")
    if received is None and sent is not None:
        received = Event("request_received", sent.date, implied=True,
                         why="assumed received the day it was sent; record the day it was received if different")
    started = head["started"] or (sent.date if sent else None)
    closed = _first(events, "closed")

    implied: list[Event] = []
    results: dict[str, dict] = {}
    for _ in range(4):                          # a deemed denial can start later clocks; repeat until stable
        all_events = sorted(events + implied + ([received] if received and received.implied else []),
                            key=lambda e: e.date)
        results = {}
        new_implied = []
        for s in model.steps:
            if not s["deadline"]:
                continue
            r = _deadline(s, model, cal, opts, all_events, results, received, started, today)
            results[s["id"]] = r
            if (r["status"] == "overdue" and r["consequence"] == "deemed-denial" and not closed
                    and not any(e.implied and e.step == s["id"] for e in implied)):
                new_implied.append(Event("denied", date.fromisoformat(r["due"]), s["id"], implied=True,
                                         why=f"{s['name']}: the deadline passed without an answer, which the law "
                                             f"treats as a denial"))
        if not new_implied:
            break
        implied += new_implied

    dls = list(results.values())
    current, why = _current(model, dls, events, closed)
    status = "closed" if closed else ("overdue" if any(d["status"] in ("overdue", "lapsed") for d in dls)
                                      else "on time")
    attention = []
    for d in dls:
        if d["status"] == "overdue":
            nxt = ", ".join(d["on_miss_names"]) or "not stated in the model"
            attention.append(f"{d['name']}: due {d['due']}, no answer recorded. If it stays unanswered: {nxt} "
                             f"({d['consequence'].replace('-', ' ')}).")
        elif d["status"] == "lapsed":
            attention.append(f"{d['name']}: your time ended on {d['due']} ({d['consequence'].replace('-', ' ')}).")
        elif d["status"] in ("on time", "open") and d.get("days_left") is not None and d["days_left"] <= 2:
            attention.append(f"{d['name']}: due {d['due']} ({d['days_left']} day{'s' * (d['days_left'] != 1)} "
                             f"left).")
    entries = [{"date": e.date.isoformat(), "kind": "implied" if e.implied else "event", **e.as_dict()}
               for e in sorted(events + implied, key=lambda e: e.date)]
    entries += [{"date": d["due"], "kind": "due", "label": f"Due: {d['name']}", "step": d["step"],
                 "status": d["status"], "citation": d["citation"]} for d in dls if d["due"]]
    entries.sort(key=lambda x: (x["date"], {"event": 0, "implied": 1, "due": 2}[x["kind"]]))
    if received is not None and received.implied:
        warnings.append("The body is assumed to have received the request the day it was sent "
                        f"({received.date.isoformat()}); add 'Body received the request' if it was later.")
    return {"lab": SCHEMA, "model": _model_head(model), "calendar": {
                "key": cal.key, "name": cal.name, "business_day": cal.business_day, "roll": cal.roll,
                "roll_source": cal.roll_source, "variant": opts.variant, "sources": [
                    {"cite": c, "url": u} for c, u in cal.sources]},
            "today": today.isoformat(), "started": started.isoformat() if started else None, "status": status,
            "current": current, "current_why": why, "deadlines": dls, "timeline": entries, "attention": attention,
            "outcomes": model.outcomes, "gaps": model.facts.get("gaps") or [], "warnings": warnings + model.notes,
            "disclaimer": DISCLAIMER}


def _deadline(s: dict, model: Model, cal: D.Calendar, opts: D.Options, events: list[Event], earlier: dict,
              received: Event | None, started: date | None, today: date) -> dict:
    d = s["deadline"]
    rule = D.DeadlineRule(d["amount"], d["unit"], d["kind"], d["anchor_text"])
    anchor = d["anchor_event"]
    own = [e for e in events if e.step == s["id"] and not e.implied]
    clock = _first(own, "clock_started")
    notes: list[str] = []
    a_date, due, count, alternatives = None, None, None, []
    ext = d["extension"]
    ext_event = _first(events, "extension_claimed")
    # the calendar reading this deadline is counted with: the case's own choice, else the default, except that a
    # deadline of the requester's own takes the calendar's earlier reading (``you_variant``) when it has one
    copts = opts
    if s["you"] and not opts.variant and cal.you_variant and cal.variant(cal.you_variant):
        copts = opts.with_variant(cal.you_variant)

    if clock:
        a_date = clock.date
        notes.append("Counted from the date you recorded for the start of this clock.")
    elif rule.kind == "set_by_body":
        ack = _first(events, "acknowledged", step=s["id"])
        if ack:
            a_date = ack.date
            if ack.until:
                due = ack.until
                notes.append("The body set this date in its acknowledgement; the law asks only that it be "
                             "reasonable.")
            else:
                notes.append("Add the date the acknowledgement states ('until') to track it.")
    elif anchor == "prev_due":
        prev = _previous_due(s, model, earlier)
        if prev:
            a_date = prev
            notes.append(f"Counted from the end of the earlier period ({prev.isoformat()}).")
    elif anchor == "request_received":
        a_date = received.date if received else None
    elif anchor == "started":
        a_date = started
    elif anchor:
        e = _first(events, anchor)          # any recorded event of that type starts the clock, whichever step it closed
        if e:
            a_date = e.date
            if e.implied:
                notes.append(f"Counted from the deemed denial on {e.date.isoformat()} ({e.why}).")
            if anchor in ("appeal_sent", "complaint_sent"):
                notes.append("Counted from the day you sent it; the law counts from the day it was received.")
    else:
        notes.append(f"The model's starting event is '{d['anchor_text']}'; record it with 'Clock started' and this "
                     f"step.")

    if a_date and due is None and rule.amount:
        base = a_date
        if ext and anchor == "extension_claimed":
            # Does the added time run from the extension notice (the model's timer) or from the end of the first
            # period?  The model's gap note says the text does not settle it.  The lab counts the body's deadline
            # to the later of the two dates, so it never calls a body overdue while it may still be in time, and a
            # deadline of yours to the earlier one; the other date is shown as another reading.
            prev = _previous_due(s, model, earlier)
            if prev:
                from_notice = D.count_deadline(cal, a_date, rule.amount, rule.unit, copts).due
                from_prev = D.count_deadline(cal, prev, rule.amount, rule.unit, copts).due
                if from_prev != from_notice:
                    use_prev = (from_prev > from_notice) != bool(s["you"])
                    if use_prev:
                        base = prev
                        alternatives.append({"due": from_notice.isoformat(), "reading": "counted from the extension "
                                             "notice (the model's timer); the model's gap note says the text does "
                                             "not settle which", "cite": d.get("citation")})
                    else:
                        alternatives.append({"due": from_prev.isoformat(), "reading": "counted from the end of the "
                                             "first period instead of from the extension notice; the model's gap "
                                             "note says the text does not settle which", "cite": d.get("citation")})
                    notes.append(f"Counted from {'the end of the first period' if use_prev else 'the extension notice'}"
                                 f" ({base.isoformat()}): the law does not say which, and the lab uses the "
                                 f"{'earlier' if s['you'] else 'later'} date for "
                                 f"{'your own deadline' if s['you'] else 'the body'}.")
        count = D.count_deadline(cal, base, rule.amount, rule.unit, copts)
        due = count.due
        if copts is not opts:
            v = cal.variant(copts.variant)
            notes.append(f"Your own deadline is counted with the reading that gives the earlier date ({v.text}); "
                         f"the default reading is shown beside it when it differs.")
        # every other reading of the calendar (the default one included) that gives a different date; a date that
        # an earlier reading already gave is not repeated
        readings = [(None, cal.default_reading or f"The {cal.name} calendar's default table",
                     cal.sources[0][0] if cal.sources else "")] + [(v.key, v.text, v.cite) for v in cal.variants]
        seen = {due}
        for key, text, cite in readings:
            if key == copts.variant:
                continue
            vc = D.count_deadline(cal, base, rule.amount, rule.unit, opts.with_variant(key))
            if vc.due not in seen:
                seen.add(vc.due)
                alternatives.append({"due": vc.due.isoformat(), "reading": text, "cite": cite})

    # does this deadline apply to the case?
    if own:
        applies = "yes"
    elif ext:
        applies = "yes" if ext_event else "if"
    elif s.get("condition") and not (anchor == "denied" and "deni" in s["condition"]):
        applies = "if"
    else:
        applies = "yes"

    after = ext_event.date if (ext and ext_event) else a_date
    done = _first(own, "step_done")
    if done is None and a_date is not None and applies == "yes":
        types = _done_types(s, anchor, ext, model)
        done = _first([e for e in events if not e.implied], types, after=after, step=s["id"]) if types else None
    status = _status_word(applies, due, done, s["you"], today)
    out = {"step": s["id"], "name": s["name"], "who": s["actor_name"], "you": s["you"], "rule": rule.describe(),
           "amount": rule.amount, "unit": rule.unit, "anchor": d["anchor_text"], "anchor_event": anchor,
           "starts_when": d["starts_when"], "anchor_date": a_date.isoformat() if a_date else None,
           "due": due.isoformat() if due else None, "status": status, "applies": applies,
           "condition": s.get("condition"), "done": done.as_dict() if done else None,
           "how": count.how if count else None, "skipped": count.skipped if count else [],
           "rolled_from": count.rolled_from.isoformat() if count and count.rolled_from else None,
           "notes": notes + (count.notes if count else []), "alternatives": alternatives,
           "consequence": d["consequence"], "on_miss": d["on_miss"], "on_miss_names": d["on_miss_names"],
           "section": d["section"], "subsection": d["subsection"], "citation": d["citation"], "url": d["url"],
           "quote": d["quote"], "unit_note": d["unit_note"], "parse": d["parse"]["status"], "gaps": d["gaps"]}
    if status in ("on time", "open") and due:
        out["days_left"] = (due - today).days
    if a_date:
        end = done.date if done else today
        out["elapsed"] = D.elapsed(cal, a_date, end, rule.unit, copts)
        out["elapsed_unit"] = "business days" if rule.unit == "business_days" else "days"
    return out


def _previous_due(s: dict, model: Model, earlier: dict) -> date | None:
    """The due date of the nearest earlier deadline on this step's path (``after`` links, breadth-first)."""
    q, seen = deque(s["after"]), set()
    while q:
        sid = q.popleft()
        if sid in seen:
            continue
        seen.add(sid)
        r = earlier.get(sid)
        if r and r.get("due"):
            return date.fromisoformat(r["due"])
        st = model.step(sid)
        if st:
            q.extend(st["after"])
    return None


def _current(model: Model, dls: list[dict], events: list[Event], closed: Event | None) -> tuple[dict | None, str]:
    def view(sid, kind="step"):
        st = model.step(sid)
        if st:
            return {"id": sid, "kind": "step", "name": st["name"], "who": st["actor_name"], "you": st["you"],
                    "citation": st["citation"], "quote": st["quote"], "next": st["next_names"], "gaps": st["gaps"]}
        o = next((o for o in model.outcomes if o["id"] == sid), None)
        if o:
            gaps = [g for g in model.facts.get("gaps") or [] if re.search(rf"\b{re.escape(sid)}\b", g)]
            return {"id": sid, "kind": "outcome", "name": o["name"], "who": None, "you": False,
                    "citation": o["citation"], "quote": o["quote"], "next": [], "gaps": gaps}
        return {"id": sid, "kind": kind, "name": sid, "who": None, "you": False, "citation": None, "quote": None,
                "next": [], "gaps": []}

    if closed:
        return None, "The case is closed."
    overdue = sorted((d for d in dls if d["status"] in ("overdue", "lapsed")), key=lambda d: d["due"])
    running = sorted((d for d in dls if d["status"] in ("on time", "open")), key=lambda d: d["due"])
    if overdue:
        d = overdue[0]
        follow = [x for x in d["on_miss"] if x]
        # the missed deadline's own next step may already be running (an appeal clock, for example)
        for r in running:
            if r["step"] in follow:
                return view(r["step"]), f"{d['name']} was due {d['due']}; {r['name']} is now open until {r['due']}."
        if follow:
            return view(follow[0]), f"{d['name']} was due {d['due']} and no answer is recorded."
        return view(d["step"]), f"{d['name']} was due {d['due']} and no answer is recorded."
    if running:
        d = running[0]
        return view(d["step"]), (f"Waiting for {d['who']}: due {d['due']}." if not d["you"] else
                                 f"Your step: open until {d['due']}.")
    if not events:
        first = model.steps[0]["id"] if model.steps else None
        return (view(first), "Start here.") if first else (None, "The model has no steps.")
    done_steps = {d["step"] for d in dls if d["status"] in ("met", "late")} | {e.step for e in events if e.step}
    last = max((model.step(sid)["n"] for sid in done_steps if model.step(sid)), default=1)
    last_step = next(s for s in model.steps if s["n"] == last)
    for nid in last_step["next"]:
        if model.step(nid) or any(o["id"] == nid for o in model.outcomes):
            return view(nid), f"After {last_step['name']}."
    return view(last_step["id"]), "No open deadline."


def outcome_for(tl: dict, step: str) -> dict | None:
    """A suggested anonymised outcome for one deadline of a computed timeline (the user can change it)."""
    d = next((x for x in tl.get("deadlines", []) if x["step"] == step), None)
    if d is None or d.get("elapsed") is None:
        return None
    done = (d.get("done") or {}).get("type")
    category = {"met": "answered_in_time", "late": "answered_late", "overdue": "no_answer", "lapsed": "still_open",
                "on time": "still_open", "open": "still_open"}.get(d["status"], "still_open")
    if d["status"] == "met" and done == "extension_claimed":
        category = "extension_notice"
    if d["status"] == "met" and done == "denied":
        category = "denied"
    return {"state": tl["model"]["state"], "question": tl["model"]["question"], "step": step,
            "days_taken": d["elapsed"], "outcome": category}
