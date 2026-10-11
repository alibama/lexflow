"""Links between process models: one model *provides* a typed status that another model's decision *requires*.

Worked example: Cal. Bus. & Prof. Code § 480(c) bars denying a license for a conviction "that has been dismissed
pursuant to Section 1203.4, 1203.4a, 1203.41, 1203.42, or 1203.425 of the Penal Code".  The licensing model
(``ca.license_conviction``) needs the input ``conviction_dismissed``; the dismissal model (``ca.record_sealing``)
ends in the outcome ``dismissed``.  The cross-references say which: their targets are the dismissal model's gold
sections.  See ``docs/design/bpc-480-decision.md``.

The pieces:

* :class:`ProvidedStatus` - a status a model produces: one of its outcomes, or a boolean decision output, keyed
  ``lexflow:status:{model_id}:{element}``.
* :class:`RequiredInput` - an input a consumer's decision reads (a DMN input data / BPMN condition variable),
  keyed ``lexflow:input:{model_id}:{variable}``, with the citations that justify it, how its value arrives
  (``evidence``: register, document, finding or call) and the jurisdiction-level status type it needs
  (``lexflow:status:ca:conviction-dismissed``), which several providers can produce (a petition under
  § 1203.4, automatic relief under § 1203.425, a comparable dismissal elsewhere).
* :class:`ProcessLink` - a proposed edge provider -> consumer, with the references that justify it, the provider's
  gold sections they matched, a score, and (when known) the status and input it joins.

:func:`propose_links` takes cross-references of role ``prerequisite_process`` or ``definition`` - in the shape
``lexflow.law.xref.Reference`` produces, or the gold fixtures' shape (``fixtures/xref/gold_*.json``) - and
matches their targets against the gold sections of the other models in :func:`load_catalog`
(``curated/*/*.json``, ``curated_ask/*/*.json``).  Matching is by ``act_id`` when a resolver backed by the
statute index is given (:func:`index_resolver`), else by normalised citation (code + number; a bare number on
either side matches any code).  A container reference ("Chapter 3.5 (commencing with Section 4852.01)") also
matches any gold section inside the unit.  :func:`shared_sections` finds models of one state that share a gold
section or a chapter, a weaker signal with no direction.

Proposals only: nothing here writes to the database, the wiki or Wikibase.  Run ``python -m lexflow.law.links``
for the California and Virginia proposals.
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Mapping, Optional

ROOT = Path(__file__).resolve().parents[2]
ROLES = ("prerequisite_process", "definition")
# how strongly a matched gold section ties the cited procedure to the provider model, by its gold role
GOLD_WEIGHT = {"primary": 1.0, "supporting": 0.7, "definition": 0.5}
UNIT_FACTOR = 0.8                       # a match inside a cited unit, not the cited section itself
BACKGROUND = 0.35                       # the provider lists the section, but as background its steps never quote
# BPMN rendering of a required status by how its value reaches the consumer (see the design note, part 2)
RENDERING = {"register": "dataStoreReference", "document": "messageFlow", "call": "callActivity",
             "finding": None}
RELATIVE = re.compile(r"(?i)\s*(this|that|such|the same)\b")     # "this subtitle": the citing section's own unit
CALL_CUES = re.compile(r"\b(in the manner provided|in accordance with the procedures?|as provided in|"
                       r"shall be conducted|pursuant to the procedures?)\b", re.I)


# ------------------------------------------------------------------ records
@dataclass(frozen=True)
class SectionRef:
    """A section, by citation and (when an index resolved it) its stable open-us-law ``act_id``."""
    state: str
    citation: str
    act_id: Optional[str] = None
    unit: Optional[str] = None          # index path of the unit that holds it ("California Code / Code pen / ...")
    title: Optional[str] = None

    @property
    def key(self) -> str:
        return f"lexflow:statute:{self.state}:{self.citation}"


@dataclass(frozen=True)
class ProvidedStatus:
    key: str                            # lexflow:status:ca.record_sealing:dismissed
    model: str                          # lexflow:process:ca.record_sealing
    element: str                        # outcome id, or "decision_id.output"
    label: str
    type_ref: str = "boolean"
    sections: tuple[str, ...] = ()      # the sections its source quotes come from (as the model writes them)


@dataclass(frozen=True)
class RequiredInput:
    key: str                            # lexflow:input:ca.license_conviction:conviction_dismissed
    model: str                          # lexflow:process:ca.license_conviction
    variable: str                       # DMN inputData name / BPMN condition variable
    decision: Optional[str] = None      # the decision that reads it
    type_ref: str = "boolean"
    cites: tuple[str, ...] = ()         # citations whose references justify it
    evidence: str = "register"          # register | document | finding | call  (-> BPMN rendering)
    status: Optional[str] = None        # the status type it needs: lexflow:status:ca:conviction-dismissed


@dataclass(frozen=True)
class ProcessLink:
    id: str
    kind: str                           # provides-input | definition-from | internal | related
    provider: str                       # model key
    consumer: Optional[str]             # model key (None: the citing section belongs to no model)
    role: str                           # the references' role (prerequisite_process | definition | shared-*)
    via: tuple[str, ...]                # cited sections (citations) that matched
    matched: tuple[tuple[str, str], ...]  # (provider gold section as written, its gold role)
    match: str                          # section | unit
    score: float
    coverage: float = 1.0               # share of the cited sections (of this role) the provider covers
    spans: tuple[str, ...] = ()         # the citing words
    status: Optional[str] = None        # ProvidedStatus.key (the provider's element)
    required: Optional[str] = None      # RequiredInput.key
    status_type: Optional[str] = None   # RequiredInput.status (the jurisdiction-level type both sides share)
    rendering: Optional[str] = None     # dataStoreReference | messageFlow | callActivity | None
    note: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class MissingModel:
    """A cited procedure that no model covers: a candidate for a model of its own."""
    consumer: Optional[str]
    role: str
    via: tuple[str, ...]
    spans: tuple[str, ...]
    suggested_key: str
    note: str = ""


@dataclass(frozen=True)
class DefinitionRef:
    """A borrowed definition with no model behind it: becomes a DMN knowledge source and, when the gold terms name
    what it defines, a term item (``key``).  An unnamed one keeps ``term`` and ``key`` None."""
    consumer: Optional[str]
    defined_in: str
    span: str
    term: Optional[str] = None
    key: Optional[str] = None           # lexflow:term:{state}:{ref}:{slug}


@dataclass
class LinkReport:
    consumer: Optional[str]
    source: str
    links: list[ProcessLink] = field(default_factory=list)
    internal: list[ProcessLink] = field(default_factory=list)
    missing: list[MissingModel] = field(default_factory=list)
    definitions: list[DefinitionRef] = field(default_factory=list)
    skipped: int = 0                    # references of other roles, or pointing at the citing section itself

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class XRef:
    """The fields of a cross-reference this module reads (what ``lexflow.law.xref.Reference`` carries)."""
    state: str
    source: str                         # citing section's citation
    span: str
    role: str
    targets: tuple[str, ...]            # target section citations
    unit: Optional[str] = None          # target unit path, for containers
    start: Optional[int] = None
    list_group: Optional[str] = None


@dataclass(frozen=True)
class ModelEntry:
    key: str                            # lexflow:process:ca.record_sealing
    model_id: str                       # ca.record_sealing (the DB id form: state.question)
    state: str
    question: str
    origin: str                         # curated | curated_ask
    title: str
    sections: tuple[tuple[str, str], ...]          # (gold section as written, role)
    quoted: tuple[str, ...] = ()                   # sections the model's own steps/decisions/outcomes quote
    statuses: tuple[ProvidedStatus, ...] = ()


# ------------------------------------------------------------------ citations
_CODE_ALIASES = {
    "penal code": "pen", "cal pen": "pen", "cal penal code": "pen",
    "business and professions code": "bpc", "cal bpc": "bpc", "bus prof code": "bpc", "cal bus prof code": "bpc",
    "government code": "gov", "cal gov": "gov", "cal gov code": "gov", "vehicle code": "veh", "cal veh": "veh",
    "va code ann": "va", "va code": "va", "code of virginia": "va",
}


def _code(code: str | None) -> str | None:
    if not code:
        return None
    c = re.sub(r"[^a-z0-9 ]+", " ", code.lower().replace("&", " and "))
    c = " ".join(c.split())
    return _CODE_ALIASES.get(c, c) or None


def parse_cite(ref: str) -> tuple[Optional[str], str]:
    """'Cal. PEN § 1203.4' -> ('pen', '1203.4'); '1203.4' -> (None, '1203.4'); 'Penal Code § 4852.01 et seq.'
    -> ('pen', '4852.01'); 'Va. Code Ann. § 54.1-204' -> ('va', '54.1-204')."""
    ref = re.sub(r"\s+et\s+seq\.?$", "", (ref or "").strip())
    if "§" in ref:
        code, num = ref.rsplit("§", 1)
        num = num.strip(" §")
    else:
        code, num = "", ref
    num = re.sub(r"\(.*$", "", num).strip().rstrip(".").lower()      # drop pinpoints "(a)(1)"
    return _code(code), num


def same_section(a: SectionRef, b: SectionRef) -> bool:
    if a.state != b.state:
        return False
    if a.act_id and b.act_id:
        return a.act_id == b.act_id
    ca, na = parse_cite(a.citation)
    cb, nb = parse_cite(b.citation)
    return bool(na) and na == nb and (ca is None or cb is None or ca == cb)


def in_unit(unit: str | None, s: SectionRef) -> bool:
    return bool(unit and s.unit and (s.unit == unit or s.unit.startswith(unit + " / ")))


Resolver = Callable[[str, str], list[SectionRef]]


def offline_resolver(state: str, ref: str) -> list[SectionRef]:
    return [SectionRef(state, ref)]


def index_resolver() -> Resolver:
    """Resolve through the statute index (read-only): citations to act_ids and unit paths, cached."""
    from ..ask import index as I
    cache: dict[tuple[str, str], list[SectionRef]] = {}

    def resolve(state: str, ref: str) -> list[SectionRef]:
        k = (state, ref)
        if k not in cache:
            clean = re.sub(r"\s+et\s+seq\.?$", "", ref.strip())
            try:
                rows = I.lookup(state, clean)
            except Exception:  # noqa: BLE001 - no index for the state: fall back to the citation
                rows = []
            cache[k] = [SectionRef(state, r["citation"], r.get("act_id"), I.parent(r) or None, r.get("title"))
                        for r in rows] or [SectionRef(state, ref)]
        return cache[k]
    return resolve


# ------------------------------------------------------------------ the catalog of models
def _statuses(model_key: str, model_id: str, facts: Mapping) -> tuple[ProvidedStatus, ...]:
    out = []
    for o in facts.get("outcomes") or []:
        out.append(ProvidedStatus(f"lexflow:status:{model_id}:{o['id']}", model_key, o["id"], o.get("description", ""),
                                  "boolean", tuple(x for x in [(o.get("source") or {}).get("section")] if x)))
    for d in facts.get("decisions") or []:
        secs = tuple(dict.fromkeys((r.get("source") or {}).get("section") for r in d.get("rules") or []
                                   if (r.get("source") or {}).get("section")))
        for c in d.get("outputs") or []:
            if c.get("type") == "boolean":
                out.append(ProvidedStatus(f"lexflow:status:{model_id}:{d['id']}.{c['name']}", model_key,
                                          f"{d['id']}.{c['name']}", c.get("label", ""), "boolean", secs))
    return tuple(out)


def _quoted(facts: Mapping) -> tuple[str, ...]:
    secs = []
    for group in ("steps", "outcomes", "actors"):
        for x in facts.get(group) or []:
            secs.append((x.get("source") or {}).get("section"))
            if (x.get("deadline") or {}).get("source"):
                secs.append(x["deadline"]["source"].get("section"))
    for d in facts.get("decisions") or []:
        secs += [(r.get("source") or {}).get("section") for r in d.get("rules") or []]
    if facts.get("trigger_source"):
        secs.append(facts["trigger_source"].get("section"))
    return tuple(dict.fromkeys(s for s in secs if s))


def load_catalog(root: Path | str = ROOT) -> list[ModelEntry]:
    """Every curated model with its gold sections: ``curated/<state>/<question>.json`` (``sections``, all primary)
    and ``curated_ask/<question>/<state>.json`` (``gold_sections`` with roles)."""
    root = Path(root)
    out = []
    for p in sorted(root.glob("curated/*/*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(d, dict) or "sections" not in d or "state" not in d:
            continue
        mid = f"{d['state']}.{d['question']}"
        facts = d.get("facts") or {}
        key = f"lexflow:process:{mid}"
        out.append(ModelEntry(key, mid, d["state"], d["question"], "curated", facts.get("process_name", mid),
                              tuple((s, "primary") for s in d["sections"]), _quoted(facts),
                              _statuses(key, mid, facts)))
    for p in sorted(root.glob("curated_ask/*/*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(d, dict) or "gold_sections" not in d:
            continue
        mid = f"{d['state']}.{d['qid']}"
        facts = d.get("steps") or {}
        key = f"lexflow:process:{mid}"
        out.append(ModelEntry(key, mid, d["state"], d["qid"], "curated_ask", facts.get("process_name") or d["question"],
                              tuple((g["ref"], g.get("role", "supporting")) for g in d["gold_sections"]),
                              _quoted(facts), _statuses(key, mid, facts)))
    return out


# ------------------------------------------------------------------ cross-references in
def _get(obj, *names, default=None):
    for n in names:
        v = obj.get(n) if isinstance(obj, Mapping) else getattr(obj, n, None)
        if v is not None:
            return v
    return default


def as_xref(obj, state: str | None = None, source: str | None = None) -> XRef:
    """Accept an :class:`XRef`, a ``lexflow.law.xref.Reference`` (``sections`` = [{"id", "citation"}], ``unit`` =
    {"path", ...}), or a gold-fixture reference (``target_sections`` = [citation], ``target_unit`` = path or
    {"index_path", ...})."""
    if isinstance(obj, XRef):
        return obj
    targets = _get(obj, "targets", "target_sections") or []
    if not targets and _get(obj, "sections"):
        targets = [s["citation"] if isinstance(s, Mapping) else str(s) for s in _get(obj, "sections")]
    unit = _get(obj, "unit", "target_unit")
    if isinstance(unit, Mapping):
        unit = unit.get("path") or unit.get("index_path")
    group = _get(obj, "list_group", "list_span")
    return XRef(state=_get(obj, "state", default=state) or "", source=_get(obj, "source", "citation", default=source) or "",
                span=_get(obj, "span", default="") or "", role=_get(obj, "role", default="other") or "other",
                targets=tuple(str(t) for t in targets), unit=unit, start=_get(obj, "start"),
                list_group=None if group is None else str(group))


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


# ------------------------------------------------------------------ proposing links
def propose_links(consumer: str | ModelEntry | None, xrefs: Iterable, catalog: list[ModelEntry], *,
                  resolver: Resolver | None = None, requires: Iterable[RequiredInput] = (),
                  terms: Iterable[Mapping] = (), state: str | None = None, source: str | None = None) -> LinkReport:
    """Links into ``consumer`` (a model key, id or entry; None when the citing section belongs to no model) from
    the cross-references of one citing section (or several).

    * A reference of role ``prerequisite_process`` whose target is a gold section of another model of the same
      state proposes a ``provides-input`` link from that model; ``definition`` proposes ``definition-from``.
    * A match only in the consumer's own model is ``internal`` when the consumer models it (its gold role is
      primary or definition, or its steps quote it); a cited procedure that only appears as the consumer's
      supporting background, or nowhere, is reported ``missing`` (a model to build).  A definition with no model
      becomes a :class:`DefinitionRef` (a term to make addressable).
    * References to the citing section itself are skipped.

    Links are grouped per (provider, role): § 480 cites the dismissal sections three times - all five in (a)(2) and
    in the first sentence of (c), four in the second sentence of (c), which omits § 1203.425 - and those 14
    references propose one link.  ``requires`` binds a link to the consumer input whose ``cites`` it matched, and so
    picks its BPMN rendering; ``terms`` (gold-fixture term entries: ``term``, ``defined_in``) names borrowed
    definitions.  Only a definition the terms name gets a term key: of § 480's three borrowed definitions, PEN
    § 1192.7 and BPC § 729 do, and BPC § 726, which the gold terms do not name, has ``term`` and ``key`` None.
    """
    resolve = resolver or offline_resolver
    terms = list(terms)
    cons = _entry(consumer, catalog)
    cons_key = cons.key if cons else (consumer if isinstance(consumer, str) and consumer.startswith("lexflow:") else None)
    xs = [as_xref(x, state, source) for x in xrefs]
    report = LinkReport(consumer=cons_key, source=", ".join(dict.fromkeys(x.source for x in xs if x.source)))
    resolved: dict[tuple[str, str], list[SectionRef]] = {}

    def res(st, ref):
        if (st, ref) not in resolved:
            resolved[(st, ref)] = resolve(st, ref)
        return resolved[(st, ref)]

    groups: dict[tuple[str, str], dict] = {}       # (provider key, role) -> evidence
    hit_targets: dict[str, set[str]] = {r: set() for r in ROLES}   # targets some other model covers
    unmatched: dict[tuple[str, tuple[str, ...]], list[XRef]] = {}
    live: list[tuple[XRef, list[str]]] = []
    for x in xs:
        if x.role not in ROLES:
            report.skipped += 1
            continue
        src = res(x.state, x.source) if x.source else []
        targets = [t for t in x.targets if not any(same_section(s, r) for s in src for r in res(x.state, t))]
        relative_unit = not x.targets and x.unit and (any(in_unit(x.unit, s) for s in src)
                                                      or RELATIVE.match(x.span or ""))
        if not targets and (not x.unit or x.targets or relative_unit):
            report.skipped += 1                    # the citing section or its own unit ("this section", "this subtitle")
            continue
        live.append((x, targets))
        trefs = [(t, r) for t in targets for r in res(x.state, t)]
        hit_any = False
        for m in catalog:
            if m.state != x.state:
                continue
            for gref, grole in m.sections:
                g = res(m.state, gref)
                cov = [t for t, r in trefs if any(same_section(r, gs) for gs in g)]
                how = "section" if cov else ("unit" if x.unit and any(in_unit(x.unit, gs) for gs in g) else None)
                if not how:
                    continue
                hit_any = True
                acc = groups.setdefault((m.key, x.role), {"entry": m, "per": {}, "spans": {}, "how": set(),
                                                          "groups": set()})
                acc["how"].add(how)
                acc["spans"][x.span] = None
                acc["groups"].add(x.list_group or f"#{id(x)}")
                for t in (cov or targets or [x.unit]):
                    acc["per"].setdefault(t, {})[gref] = grole
                if not cons or m.key != cons.key:
                    hit_targets[x.role].update(cov or targets or [x.unit])
        if not hit_any:
            unmatched.setdefault((x.role, tuple(targets) or (x.unit or "",)), []).append(x)

    reqs = [r for r in requires if cons_key is None or r.model == cons_key]

    def models_it(m: ModelEntry, gref: str, grole: str) -> bool:
        return grole in ("primary", "definition") or _norm_num(gref) in {_norm_num(q) for q in m.quoted}
    internal_targets = {role: {t for t, gs in acc["per"].items() if any(models_it(acc["entry"], g, gr) for g, gr in gs.items())}
                        for (pkey, role), acc in groups.items() if cons is not None and pkey == cons.key}
    for (pkey, role), acc in sorted(groups.items(), key=lambda kv: kv[0][0] != (cons.key if cons else None)):
        m: ModelEntry = acc["entry"]
        own = cons is not None and pkey == cons.key
        if not own:      # what the consumer models itself is not another model's to provide
            acc["per"] = {t: gs for t, gs in acc["per"].items() if t not in internal_targets.get(role, set())}
            if not acc["per"]:
                continue
        weight = {}
        for t, gs in acc["per"].items():
            w = [(GOLD_WEIGHT.get(gr, 0.5) if role == "prerequisite_process" else (1.0 if gr == "definition" else 0.6))
                 if models_it(m, g, gr) else BACKGROUND for g, gr in gs.items()]
            weight[t] = max(w)
        factor = 1.0 if "section" in acc["how"] else UNIT_FACTOR
        in_groups = {t for x, ts in live if x.role == role and (x.list_group or f"#{id(x)}") in acc["groups"]
                     for t in (ts or [x.unit])}
        if own:
            modelled = sorted(internal_targets.get(role, set()), key=list(acc["per"]).index)
            background = [t for t in acc["per"] if t not in modelled and t not in hit_targets[role]]
            if modelled:
                report.internal.append(ProcessLink(
                    id=f"{pkey}:internal:{role}", kind="internal", provider=pkey, consumer=cons_key, role=role,
                    via=tuple(modelled), matched=tuple((g, gr) for t in modelled for g, gr in acc["per"][t].items()),
                    match="section" if "section" in acc["how"] else "unit", score=round(max(weight[t] for t in modelled) * factor, 3),
                    spans=tuple(acc["spans"])))
            if background and role == "definition":
                report.definitions += [_defref(cons_key, m.state, t, next(iter(acc["spans"])), terms)
                                       for t in background]
            elif background:
                report.missing.append(_missing(cons_key, role, tuple(background), tuple(acc["spans"]), m.state, res,
                                               "cited as a procedure, but the consumer lists it only as background "
                                               "(no step quotes it) and no other model covers it"))
            continue
        via = tuple(acc["per"])
        status = (_pick_status(m, {g: gr for gs in acc["per"].values() for g, gr in gs.items()}, res)
                  if role == "prerequisite_process" else None)
        req = _bind(reqs, via, res)
        rendering = None
        if role == "prerequisite_process":
            rendering = (RENDERING.get(req.evidence) if req else
                         "callActivity" if any(CALL_CUES.search(s) for s in acc["spans"]) else "dataStoreReference")
        weak = [t for t in via if weight[t] == BACKGROUND]
        report.links.append(ProcessLink(
            id=f"{pkey}->{cons_key or report.source}:{role}",
            kind="provides-input" if role == "prerequisite_process" else "definition-from", provider=pkey,
            consumer=cons_key, role=role, via=via,
            matched=tuple(dict.fromkeys((g, gr) for gs in acc["per"].values() for g, gr in gs.items())),
            match="section" if "section" in acc["how"] else "unit", score=round(max(weight.values()) * factor, 3),
            coverage=round(len([t for t in via if t in in_groups]) / max(1, len(in_groups)), 3),
            spans=tuple(acc["spans"]), status=status.key if status else None, required=req.key if req else None,
            status_type=req.status if req else None, rendering=rendering,
            note=(f"the provider lists {', '.join(weak)} only as background (no step quotes it)" if weak else None)))
    for (role, targets), group in unmatched.items():
        spans = tuple(dict.fromkeys(x.span for x in group))
        if role == "definition":
            report.definitions += [_defref(cons_key, group[0].state, t, spans[0], terms) for t in targets]
        else:
            report.missing.append(_missing(cons_key, role, targets, spans, group[0].state, res,
                                           "no model covers the cited section"))
    report.links.sort(key=lambda ln: -ln.score)
    return report


def _defref(consumer, state: str, target: str, span: str, terms: list[Mapping]) -> DefinitionRef:
    """A borrowed definition, named from the gold terms when they say what it defines; keyed like
    ``lexflow.law.terms.term_key`` (``lexflow:term:{state}:{ref}:{slug}``).  With no term to name it there is no
    slug, so the key is None (BPC § 726 in § 480)."""
    term = next((tm.get("term") for tm in terms if tm.get("defined_in")
                 and same_section(SectionRef(state, tm["defined_in"]), SectionRef(state, target))), None)
    key = f"lexflow:term:{state}:{target}:{re.sub(r'[^a-z0-9]+', '-', term.lower()).strip('-')}" if term else None
    return DefinitionRef(consumer, target, span, term, key)


def _norm_num(ref: str) -> str:
    return parse_cite(ref)[1]


def _entry(consumer, catalog) -> ModelEntry | None:
    if isinstance(consumer, ModelEntry):
        return consumer
    if not consumer:
        return None
    return next((m for m in catalog if consumer in (m.key, m.model_id)), None)


def _pick_status(m: ModelEntry, matched: Mapping[str, str], res) -> ProvidedStatus | None:
    """The provider's status whose source quotes one of the matched sections: an outcome first (the state the
    process ends in), else a boolean decision output."""
    secs = [SectionRef(m.state, s) for s in matched]

    def hits(st: ProvidedStatus) -> bool:
        return any(same_section(a, b) for q in st.sections for a in res(m.state, q) for s in secs
                   for b in res(m.state, s.citation))
    outcomes = [s for s in m.statuses if "." not in s.element and hits(s)]
    decisions = [s for s in m.statuses if "." in s.element and hits(s)]
    return (outcomes or decisions or [None])[0]


def _bind(reqs: list[RequiredInput], via: tuple[str, ...], res) -> RequiredInput | None:
    best, n = None, 0
    for r in reqs:
        k = sum(1 for c in r.cites for v in via
                if any(same_section(a, b) for a in res(_state_of(r), c) for b in res(_state_of(r), v)))
        if k > n:
            best, n = r, k
    return best


def _state_of(r: RequiredInput) -> str:
    m = re.match(r"lexflow:process:([a-z]{2})\.", r.model)
    return m.group(1) if m else ""


def _missing(consumer, role, via, spans, state, res, note) -> MissingModel:
    first = via[0] if via else "unit"
    rows = res(state, first) if via else []
    title = next((r.title for r in rows if r.title), None)
    code, num = parse_cite(first) if via else (None, first)
    return MissingModel(consumer, role, tuple(via), tuple(spans),
                        "lexflow:process:" + state + "." + _slug((code or "") + " " + num),
                        note + (f"; first cited section: {first}" + (f" ({title})" if title else "")))


def shared_sections(catalog: list[ModelEntry], *, resolver: Resolver | None = None,
                    states: Iterable[str] | None = None) -> list[ProcessLink]:
    """Pairs of models in one state whose gold sections coincide (score 0.6) or sit in one chapter (0.3).  No
    direction: a lead for review, e.g. the Virginia licensing and sealing models, which share Title 19.2
    Chapters 23.1 and 23.2."""
    resolve = resolver or offline_resolver
    want = set(states) if states else None
    by_state: dict[str, list[ModelEntry]] = {}
    for m in catalog:
        if want is None or m.state in want:
            by_state.setdefault(m.state, []).append(m)
    out = []
    for st, models in by_state.items():
        refs = {m.key: [(g, r) for g, _ in m.sections for r in resolve(st, g)] for m in models}
        for i, a in enumerate(models):
            for b in models[i + 1:]:
                same = sorted({(ga, gb) for ga, ra in refs[a.key] for gb, rb in refs[b.key] if same_section(ra, rb)})
                units = sorted({ra.unit for _, ra in refs[a.key] for _, rb in refs[b.key]
                                if ra.unit and ra.unit == rb.unit} - {None})
                if not same and not units:
                    continue
                out.append(ProcessLink(
                    id=f"{a.key}<->{b.key}", kind="related", provider=a.key, consumer=b.key,
                    role="shared-section" if same else "shared-unit", via=tuple(f"{x} = {y}" for x, y in same) or tuple(units),
                    matched=(), match="section" if same else "unit", score=0.6 if same else 0.3,
                    note=f"shared units: {'; '.join(units)}" if units else None))
    return sorted(out, key=lambda ln: (-ln.score, ln.id))


# ------------------------------------------------------------------ the worked examples
BPC_480_INPUTS = (
    RequiredInput("lexflow:input:ca.license_conviction:conviction_dismissed", "lexflow:process:ca.license_conviction",
                  "conviction_dismissed", "dismissal_bar",
                  cites=("Cal. PEN § 1203.4", "Cal. PEN § 1203.4a", "Cal. PEN § 1203.41", "Cal. PEN § 1203.42",
                         "Cal. PEN § 1203.425"), evidence="register", status="lexflow:status:ca:conviction-dismissed"),
    RequiredInput("lexflow:input:ca.license_conviction:certificate_of_rehabilitation",
                  "lexflow:process:ca.license_conviction", "certificate_of_rehabilitation", "rehabilitation_bar",
                  cites=("Cal. PEN § 4852.01",), evidence="document",
                  status="lexflow:status:ca:certificate-of-rehabilitation"),
    RequiredInput("lexflow:input:ca.license_conviction:showing_of_rehabilitation",
                  "lexflow:process:ca.license_conviction", "showing_of_rehabilitation", "rehabilitation_bar",
                  cites=("Cal. BPC § 482",), evidence="finding",
                  status="lexflow:status:ca:showing-of-rehabilitation-482"),
)


def _gold_sections(states: Iterable[str]) -> list[dict]:
    out = []
    for p in sorted((ROOT / "fixtures" / "xref").glob("gold_*.json")):
        for s in json.loads(p.read_text(encoding="utf-8"))["sections"]:
            if s["state"] in states:
                out.append({**s, "_file": p.name})
    return out


def demo(states=("ca", "va"), use_index: bool = True, xref_module: bool = False) -> dict:
    """Proposals for every gold-fixture section of ``states``: the section's references (from the gold fixtures,
    or from ``lexflow.law.xref`` when ``xref_module``) into each model that lists the section."""
    catalog = load_catalog()
    resolver = index_resolver() if use_index else offline_resolver
    out = {"sections": [], "shared": []}
    for s in _gold_sections(states):
        refs = s["references"]
        origin = s["_file"]
        if xref_module:
            try:
                from . import xref as X
                from ..ask import index as I
                row = I.lookup(s["state"], s["citation"])[0]
                refs, origin = X.references(s["state"], row), "lexflow.law.xref"
            except Exception as e:  # noqa: BLE001 - the module is optional here
                origin = f"{s['_file']} (lexflow.law.xref failed: {type(e).__name__})"
        here = resolver(s["state"], s["citation"])
        listing = [(m, g, r) for m in catalog if m.state == s["state"] for g, r in m.sections
                   if any(same_section(a, b) for a in resolver(m.state, g) for b in here)]
        # the consumer is a model that models the citing section (primary or quoted); a model that lists it only
        # as background is used when no model does
        modelling = [m for m, g, r in listing if r in ("primary", "definition")
                     or _norm_num(g) in {_norm_num(q) for q in m.quoted}]
        consumers = list(dict.fromkeys(modelling or [m for m, _, _ in listing])) or [None]
        for c in consumers:
            rep = propose_links(c, refs, catalog, resolver=resolver, state=s["state"], source=s["citation"],
                                requires=BPC_480_INPUTS if s["citation"] == "Cal. BPC § 480" else (),
                                terms=s.get("terms") or ())
            out["sections"].append({"section": s["citation"], "xrefs_from": origin, **rep.to_dict()})
    out["shared"] = [ln.to_dict() for ln in shared_sections(catalog, resolver=resolver, states=states)]
    return out


def _print(result: dict) -> None:
    for r in result["sections"]:
        if not (r["links"] or r["internal"] or r["missing"] or r["definitions"]):
            print(f"{r['section']} -> {r['consumer'] or '(no model)'}: no prerequisite or definition references "
                  f"to other sections ({r['skipped']} others)")
            continue
        print(f"{r['section']} -> {r['consumer'] or '(no model)'}  [{r['xrefs_from']}]")
        for ln in r["links"]:
            print(f"   LINK {ln['kind']}: {ln['provider']} (score {ln['score']}, coverage {ln['coverage']}, "
                  f"{ln['match']}) via {', '.join(ln['via'])}; status {ln['status']}; input {ln['required']}; "
                  f"BPMN {ln['rendering']}")
        for ln in r["internal"]:
            print(f"   internal: {', '.join(ln['via'])} ({ln['role']})" + (f" - {ln['note']}" if ln["note"] else ""))
        for mm in r["missing"]:
            print(f"   MISSING model {mm['suggested_key']} for {', '.join(mm['via'])} ({mm['role']}): {mm['note']}")
        for d in r["definitions"]:
            print(f"   definition from {d['defined_in']} ({d['term'] or 'term unnamed'}) {d['key'] or ''}")
    print("shared sections / units:")
    for ln in result["shared"]:
        print(f"   {ln['provider']} <-> {ln['consumer']} ({ln['role']}, {ln['score']}): {'; '.join(ln['via'])[:160]}")


if __name__ == "__main__":
    args = sys.argv[1:]
    res = demo(states=[a for a in args if len(a) == 2] or ("ca", "va"), use_index="--offline" not in args,
               xref_module="--xref" in args)
    if "--json" in args:
        print(json.dumps(res, indent=1, default=str))
    else:
        _print(res)
