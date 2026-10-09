"""Map Lexipedia models onto the lexipedia.wikibase.cloud ontology.

Existing ontology (verified via the instance's SPARQL endpoint, 2026-10-06):
  P5 instance of, P8 exact match (URL), P9 part of, P10 has part, P11 follows,
  P12 followed by, P13 references, P15 applies to jurisdiction, P16 deontic modality,
  P17 bearer, P18 condition, P19 governed by norm, P20 sanction, P21 defeated by,
  P22 citation (string), P23 official text (URL), P24 effective date, P25 legal identifier
  Q7 legal process, Q8 legal process step, Q9 decision point, Q10 statute or legal
  provision, Q11 norm, Q13 Obligation, Q14 Permission, Q15 Prohibition, Q16 Right

Properties this pipeline needs that do not exist yet are emitted as proposals and
referenced through placeholders ({P:bpmn_model} ...).  Two outputs:
  * QuickStatements v1 in two phases (create items, then link them), placeholders
    {Q:<key>} resolved after phase 1 with :func:`resolve`;
  * wbeditentity JSON payloads for a bot (bot password / OAuth), see :class:`WikibaseBot`.
wikibase.cloud caps string values at 400 characters and has file uploads off, so
diagrams stay on DokuWiki and Wikibase stores their URLs.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from ..ir import LegalProcessModel, Node
from ..text.history import parse_history
from .dokuwiki import law_page_id, process_page_id

P = dict(instance_of="P5", exact_match="P8", part_of="P9", has_part="P10", follows="P11", followed_by="P12",
         references="P13", jurisdiction="P15", deontic="P16", bearer="P17", condition="P18", norm="P19",
         sanction="P20", citation="P22", official_text="P23", effective="P24", legal_id="P25")
Q = dict(legal_process="Q7", step="Q8", decision_point="Q9", provision="Q10", norm="Q11",
         obligation="Q13", permission="Q14", prohibition="Q15", right="Q16")
MODALITY = {"obligation": Q["obligation"], "duty-to-decide": Q["obligation"], "permission": Q["permission"],
            "prohibition": Q["prohibition"], "right": Q["right"]}
PROPOSED = {
    "bpmn_model": ("BPMN model URL", "url", "Canonical BPMN 2.0 file (with DI) for this legal process"),
    "dmn_model": ("DMN model URL", "url", "Canonical DMN 1.3 decision tables used by this process"),
    "wiki_page": ("Lexipedia wiki page", "url", "DokuWiki page that renders the process and cross-references"),
    "time_limit": ("time limit", "string", "ISO 8601 duration of a legal deadline, e.g. P30D"),
    "deadline_anchor": ("deadline runs from", "string", "Event that starts a legal deadline (qualifier of time limit)"),
    "grounding": ("grounding status", "string", "explicit | implied | assumed - why this step exists"),
    "bpmn_element": ("BPMN element id", "external-id", "Id of the element inside the process model"),
    "performed_by": ("performed by", "wikibase-item", "Actor that carries out the step"),
}
STEP_TYPES = {"task", "userTask", "serviceTask", "sendTask", "receiveTask", "businessRuleTask", "manualTask",
              "scriptTask", "callActivity", "subProcess", "intermediateCatchEvent", "boundaryEvent", "startEvent",
              "endEvent", "eventBasedGateway", "exclusiveGateway"}
MAX_STRING = 400


def _s(text: str, limit: int = MAX_STRING) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _qs_str(text: str, limit: int = MAX_STRING) -> str:
    return '"' + _s(text, limit).replace('"', "'") + '"'


@dataclass
class Bundle:
    """Items keyed by a local key; statements reference other items by key."""
    items: dict[str, dict] = field(default_factory=dict)
    statements: list[tuple[str, str, str, list[tuple[str, str]]]] = field(default_factory=list)

    def item(self, key: str, label: str, description: str, existing: str | None = None):
        if key not in self.items:
            self.items[key] = {"label": _s(label, 250), "description": _s(description, 250), "qid": existing}
        return key

    def add(self, key: str, prop: str, value: str, qualifiers: list[tuple[str, str]] | None = None):
        self.statements.append((key, prop, value, qualifiers or []))


def _step_key(model: LegalProcessModel, n: Node) -> str:
    return f"step:{model.id}:{n.id}"


def build_bundle(model: LegalProcessModel, wiki_base: str = "https://lexipedia.xyz/doku.php?id=",
                 existing: dict[str, str] | None = None) -> Bundle:
    existing = existing or {}
    b = Bundle()
    juris = b.item(f"jurisdiction:{model.jurisdiction}", model.jurisdiction_name, "jurisdiction",
                   existing.get(f"jurisdiction:{model.jurisdiction}"))
    if model.jurisdiction_qid:
        b.add(juris, P["exact_match"], f"url:https://www.wikidata.org/wiki/{model.jurisdiction_qid}")
    proc = b.item(f"process:{model.id}", model.title, f"legal process ({model.jurisdiction_name})")
    b.add(proc, P["instance_of"], f"item:{Q['legal_process']}")
    b.add(proc, P["jurisdiction"], f"key:{juris}")
    page = process_page_id(model)
    b.add(proc, "{P:wiki_page}", f"url:{wiki_base}{page}")
    b.add(proc, "{P:bpmn_model}", f"url:{wiki_base.replace('doku.php?id=', 'lib/exe/fetch.php?media=')}{page}.bpmn")
    if model.decisions:
        b.add(proc, "{P:dmn_model}", f"url:{wiki_base.replace('doku.php?id=', 'lib/exe/fetch.php?media=')}{page}.dmn")
    # provisions
    for t in model.texts:
        key = f"provision:{t.jurisdiction}:{t.section}"
        b.item(key, f"{t.code} § {t.section}", _s(t.title, 250))
        b.add(key, P["instance_of"], f"item:{Q['provision']}")
        b.add(key, P["citation"], f"string:{t.code} § {t.section}")
        b.add(key, P["legal_id"], f"string:{t.section}")
        if t.url:
            b.add(key, P["official_text"], f"url:{t.url}")
        b.add(key, "{P:wiki_page}", f"url:{wiki_base}{law_page_id(t.jurisdiction, t.section)}")
        if t.jurisdiction == model.jurisdiction:
            b.add(key, P["jurisdiction"], f"key:{juris}")
        hist = parse_history(t.history)
        eff = [a.effective for a in hist.amendments if a.effective]
        if eff:
            b.add(key, P["effective"], f"time:{max(eff)}", [(P["legal_id"], f"string:{next(a.ordinance for a in hist.amendments if a.effective == max(eff))}")])
        b.add(proc, P["references"], f"key:{key}")
    # actors
    for a in model.actors:
        key = f"actor:{model.id}:{a.id}"
        b.item(key, a.name, f"{a.kind} in {model.jurisdiction_name}")
        if a.wikidata:
            b.add(key, P["exact_match"], f"url:https://www.wikidata.org/wiki/{a.wikidata}")
    # steps
    lane_actor = {}
    for proc_ir in model.processes():
        for lane in proc_ir.lanes:
            lane_actor[lane.id] = lane.actor
    part_actor = {p.process.id: p.actor for p in model.participants if p.process}
    nodes = {n.id: (pr, n) for pr, _, n in model.iter_nodes()}
    for pr, scope, n in model.iter_nodes():
        if n.type not in STEP_TYPES or not (n.name or "").strip():
            continue
        key = _step_key(model, n)
        kind = Q["decision_point"] if n.type in ("businessRuleTask", "exclusiveGateway", "eventBasedGateway") else Q["step"]
        b.item(key, n.name, f"step of: {model.title}")
        b.add(key, P["instance_of"], f"item:{kind}")
        b.add(key, P["part_of"], f"key:{proc}")
        b.add(proc, P["has_part"], f"key:{key}")
        b.add(key, "{P:bpmn_element}", f"string:{n.id}")
        actor = n.bearer or lane_actor.get(n.lane or "") or part_actor.get(pr.id)
        if actor:
            b.add(key, "{P:performed_by}", f"key:actor:{model.id}:{actor}")
        if n.deontic in MODALITY:
            b.add(key, P["deontic"], f"item:{MODALITY[n.deontic]}",
                  [(P["bearer"], f"key:actor:{model.id}:{n.bearer}")] if n.bearer else [])
        if n.timer:
            quals = [("{P:deadline_anchor}", f"string:{n.timer.anchor}")] if n.timer.anchor else []
            b.add(key, "{P:time_limit}", f"string:{n.timer.value}", quals)
        for s in n.sources:
            target = f"provision:{s.jurisdiction or model.jurisdiction}:{s.section}"
            if target in b.items:
                b.add(key, P["references"], f"key:{target}",
                      [(P["citation"], f"string:{s.citation}"), ("{P:grounding}", f"string:{s.grounding}")])
    # precedence between named steps (collapse gateways / unnamed nodes)
    for pr_ir in model.processes():
        _precedence(model, pr_ir.nodes, pr_ir.flows, b)
    return b


def _precedence(model, nodes, flows, b: Bundle):
    succ: dict[str, list[str]] = {}
    for f in flows:
        succ.setdefault(f.source, []).append(f.target)
    named = {n.id for n in nodes if n.type in STEP_TYPES and (n.name or "").strip()}
    for n in nodes:
        if n.nodes:
            _precedence(model, n.nodes, n.flows, b)
        if n.id not in named:
            continue
        seen, stack, nxt = set(), list(succ.get(n.id, [])), set()
        while stack:
            x = stack.pop()
            if x in seen:
                continue
            seen.add(x)
            if x in named:
                nxt.add(x)
            else:
                stack.extend(succ.get(x, []))
        for x in sorted(nxt):
            b.add(f"step:{model.id}:{n.id}", P["followed_by"], f"key:step:{model.id}:{x}")
            b.add(f"step:{model.id}:{x}", P["follows"], f"key:step:{model.id}:{n.id}")


# -------------------------------------------------------------- QuickStatements
def _qs_value(value: str, phase_keys: dict[str, str]) -> str:
    kind, _, v = value.partition(":")
    if kind == "item":
        return v
    if kind == "key":
        return phase_keys.get(v, "{Q:%s}" % v)
    if kind == "string":
        return _qs_str(v)
    if kind == "url":
        return _qs_str(v)
    if kind == "time":
        return f"+{v}T00:00:00Z/11"
    raise ValueError(value)


def quickstatements(b: Bundle, lang: str = "en") -> tuple[str, str]:
    """Return (phase1 create commands, phase2 statement commands with {Q:key} placeholders)."""
    p1 = []
    for key, it in b.items.items():
        if it.get("qid"):
            continue
        p1.append("CREATE")
        p1.append(f"LAST\tL{lang}\t{_qs_str(it['label'], 250)}")
        p1.append(f"LAST\tD{lang}\t{_qs_str(it['description'], 250)}")
        p1.append(f"LAST\tA{lang}\t{_qs_str('lexflow:' + key, 250)}")    # alias = stable key for resolution
    known = {k: it["qid"] for k, it in b.items.items() if it.get("qid")}
    p2 = []
    for key, prop, value, quals in b.statements:
        subject = known.get(key, "{Q:%s}" % key)
        line = [subject, prop, _qs_value(value, known)]
        for qp, qv in quals:
            line += [qp, _qs_value(qv, known)]
        p2.append("\t".join(line))
    return "\n".join(p1) + "\n", "\n".join(p2) + "\n"


def resolve(phase2: str, key_to_qid: dict[str, str], prop_ids: dict[str, str]) -> str:
    def q(m):
        return key_to_qid[m.group(1)]

    def p(m):
        return prop_ids[m.group(1)]
    out = re.sub(r"\{Q:([^}]+)\}", q, phase2)
    return re.sub(r"\{P:([^}]+)\}", p, out)


def property_proposals_qs(lang: str = "en") -> str:
    """QuickStatements cannot create properties; this is the checklist for an admin (or the bot API)."""
    lines = ["# Create these properties (Special:NewProperty or wbeditentity new=property):"]
    for key, (label, dtype, desc) in PROPOSED.items():
        lines.append(f"# {{P:{key}}}\t{label}\t{dtype}\t{desc}")
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------- bot payloads
def wbeditentity_payloads(b: Bundle, lang: str = "en") -> list[dict]:
    """JSON for action=wbeditentity&new=item (phase 1); claims are added in phase 2 once ids exist."""
    out = []
    for key, it in b.items.items():
        if it.get("qid"):
            continue
        out.append({"key": key, "data": {
            "labels": {lang: {"language": lang, "value": it["label"]}},
            "descriptions": {lang: {"language": lang, "value": it["description"]}},
            "aliases": {lang: [{"language": lang, "value": f"lexflow:{key}"}]},
        }})
    return out


@dataclass
class WikibaseBot:
    """Minimal MediaWiki action-API client (bot password login, csrf token, wbeditentity)."""
    api: str                        # e.g. https://lexipedia.wikibase.cloud/w/api.php
    user: str
    password: str
    session: object = None
    maxlag: int = 5

    def _s(self):
        import requests
        if self.session is None:
            self.session = requests.Session()
            self.session.headers["User-Agent"] = "lexflow/0.3 (Lexipedia pipeline; contact via lexipedia.xyz)"
        return self.session

    def login(self):
        s = self._s()
        tok = s.get(self.api, params={"action": "query", "meta": "tokens", "type": "login", "format": "json"}).json()
        lt = tok["query"]["tokens"]["logintoken"]
        r = s.post(self.api, data={"action": "login", "lgname": self.user, "lgpassword": self.password,
                                   "lgtoken": lt, "format": "json"}).json()
        if r.get("login", {}).get("result") != "Success":
            raise RuntimeError(f"login failed: {r}")
        self.csrf = s.get(self.api, params={"action": "query", "meta": "tokens", "format": "json"}).json()[
            "query"]["tokens"]["csrftoken"]

    def create_item(self, data: dict, summary: str = "lexflow") -> str:
        r = self._s().post(self.api, data={"action": "wbeditentity", "new": "item", "data": json.dumps(data),
                                           "token": self.csrf, "bot": 1, "summary": summary,
                                           "maxlag": self.maxlag, "format": "json"}).json()
        if "error" in r:
            raise RuntimeError(r["error"])
        return r["entity"]["id"]
