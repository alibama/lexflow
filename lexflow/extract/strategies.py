"""Ways to turn statute text into LegalProcessFacts with a small local model, from least to most decomposed.

* ``oneshot``  - the original: the whole facts JSON in one call, with repair rounds (extract()).
* ``snap``     - oneshot, then every quote that is not an exact span is snapped to the closest clause.
* ``rules``    - no model: duty clauses (shall/may/...) become steps; actor = grammatical subject.
* ``hybrid``   - rules propose candidate clauses; the model labels each one in a tiny JSON call
                 (is it a step? the action in <= 8 words, kind, condition).
* ``outline``  - recursion over a compressed view: the model summarises each subsection in one line,
                 then plans the steps from those summaries only; code grounds every planned step in the
                 best-matching clause of its subsection (exact quote, deadline, modality from the text).
* ``*_review`` - a final pass: the model sees the step list and drops duplicates and minor steps.

In every decomposed strategy the model never copies text: quotes are clause texts, so they are exact
by construction, and the model's job shrinks to judgements a 1-2 B model can make on short inputs.
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from difflib import SequenceMatcher

import requests
from pydantic import ValidationError

from .ollama import OllamaClient, check_facts, extract
from .schema import (FActor, FCrossRef, FDeadline, FOutcome, FStep, LegalProcessFacts, Quote)
from .segment import Clause, outline as clause_outline, segment

AGENT_WORDS = re.compile(
    r"\b(body|bodies|custodian|requester|person|persons|applicant|officer|official|clerk|commission|department|"
    r"mayor|council|court|agency|board|organizer|organizers|incorporator|incorporators|member|partner|partners|"
    r"registrant|director|secretary|attorney|administrator|employee|owner|citizen|unit|corporation|company|"
    r"partnership|treasurer|commissioner|division|office|governing|locality|county|city|town|state)\b", re.I)
FILER_WORDS = re.compile(r"\b(request|application|petition|articles|certificate|statement|notice of)\b", re.I)
KIND_VERBS = [
    ("notice", r"notif|inform|send|mail|give notice|advise|post"),
    ("filing", r"file|submit|deliver|apply|request|petition|sign"),
    ("decision", r"decide|determin|grant|deny|approve|find|reject|accept"),
    ("hearing", r"hear|hearing"),
    ("payment", r"pay|charge|collect|fee|deposit"),
    ("record", r"record|maintain|keep|admit"),
    ("review", r"review|inspect|examin"),
]
COURT = re.compile(r"\bcourt\b", re.I)
PRIVATE = re.compile(r"\b(requester|person|applicant|organizer|incorporator|member|partner|owner|citizen|registrant|"
                     r"individual|corporation|company|partnership|founder)\b", re.I)


@dataclass
class Run:
    strategy: str
    model: str | None
    facts: LegalProcessFacts | None
    problems: list[str]
    calls: int = 0
    seconds: float = 0.0
    notes: list[str] = field(default_factory=list)


# ------------------------------------------------------------------ helpers
def slug(s: str, n: int = 30) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", (s or "").lower()).strip("_")
    s = re.sub(r"^(?=\d)", "x_", s) or "x"
    return s[:n].strip("_") or "x"


def modality_of(modal: str | None) -> str:
    if not modal:
        return "none"
    if " not" in modal:
        return "prohibition"
    if modal.startswith(("shall", "must", "is required", "are required")):
        return "obligation"
    if "entitled" in modal or "right" in modal:
        return "right"
    return "permission"


def kind_of(action: str) -> str:
    a = action.lower()
    for kind, pat in KIND_VERBS:
        if re.search(rf"\b(?:{pat})", a):
            return kind
    return "act"


def actor_kind(name: str) -> str:
    if COURT.search(name):
        return "court"
    if PRIVATE.search(name) and not re.search(r"\b(public|state|county|city|governmental)\b", name, re.I):
        return "private-party"
    return "public-body"


def verb_phrase(after_modal: str, words: int = 8) -> str:
    """'promptly, but in all cases within five working days of receiving a request, provide the requested records'
    -> 'Provide the requested records'."""
    s = re.sub(r"^\s*(?:\w+ly,?\s+)+", "", after_modal)                     # adverbs
    s = re.sub(r"^,?\s*but\b[^,]*,\s*", "", s)                              # ", but in all cases within ..., "
    s = re.sub(r"\b(?:within|not more than|not later than|no later than)\s+[^,;.]*?(?:days?|weeks?|months?)\b[^,;.]*", "", s)
    s = re.sub(r"\s+", " ", s).strip(" ,;:.")
    toks = s.split()
    phrase = " ".join(toks[:words]) or "Act"
    return phrase[:1].upper() + phrase[1:]


class Actors:
    """Collects actors by normalised name; each gets an exact quote (a clause that names it)."""

    def __init__(self, section: str):
        self.section = section
        self.by_key: dict[str, FActor] = {}

    def get(self, name: str, clause: Clause, kind: str | None = None) -> str:
        key = re.sub(r"\b(of such records|of the requested records)\b", "", name.lower()).strip()
        key = re.sub(r"\s+", " ", key)
        aid = slug(key, 24)
        if aid not in self.by_key:
            self.by_key[aid] = FActor(id=aid, name=key[:1].upper() + key[1:], kind=kind or actor_kind(key),
                                      source=Quote(section=clause.section or self.section, subsection=clause.label or None,
                                                   quote=clause.text))
        return aid


def quote(section: str, c: Clause) -> Quote:
    """An exact quote of one clause, cited to its own section when the text joins several."""
    return Quote(section=c.section or section, subsection=c.label or None, quote=c.text)


def filer_for(question: str) -> str:
    return {"records": "requester", "business": "organizer"}.get(question, "applicant")


def assemble(drafts: list[dict], clauses: list[Clause], section: str, question: str, process_name: str) -> LegalProcessFacts:
    """drafts: [{clause, actor, kind?, action, kind, modality, condition, deadline}] in process order."""
    actors = Actors(section)
    steps: list[FStep] = []
    used_ids: set[str] = set()
    last_plain: str | None = None
    for d in drafts:
        c: Clause = d["clause"]
        aid = actors.get(d["actor"], c, d.get("actor_kind"))
        sid = slug(d["action"], 28)
        while sid in used_ids:
            sid = f"{sid[:25]}_{len(used_ids)}"
        used_ids.add(sid)
        dl = d.get("deadline")
        deadline = FDeadline(amount=dl["amount"], unit=dl["unit"], anchor=dl.get("anchor") or "the triggering event",
                             consequence="unstated", source=quote(section, c)) if dl else None
        cond = slug(d["condition"], 32) if d.get("condition") else None
        steps.append(FStep(id=sid, actor=aid, action=d["action"][:80], kind=d["kind"], modality=d["modality"],
                           after=[last_plain] if last_plain else [], condition=cond, deadline=deadline,
                           source=quote(section, c)))
        if not cond:
            last_plain = sid
    if not steps:
        raise ValueError("no steps")
    first = drafts[0]["clause"]
    outcome = FOutcome(id="process_complete", description="Process complete", after=[last_plain or steps[-1].id],
                       source=quote(section, drafts[-1]["clause"]))
    return LegalProcessFacts(process_name=process_name, trigger=f"A {question} process begins",
                             trigger_source=quote(section, first), actors=list(actors.by_key.values()), steps=steps,
                             outcomes=[outcome], gaps=[])


def rule_drafts(clauses: list[Clause], question: str) -> list[dict]:
    out = []
    for c in clauses:
        if not c.modal:
            continue
        # "No public body shall ..." is stored as "shall not" but the text says "shall"
        m = re.search(re.escape(c.modal), c.text, re.I) or re.search(r"\b(shall|may|must)\b", c.text, re.I)
        after = c.text[m.end():] if m else ""
        subj = c.subject or ""
        if re.match(r"\s*(?:\w+ly\s+)?be\b", after) and not re.search(r"\bby\s+(?:the|a|an|any)\b", after[:120]):
            continue                                           # "shall be deemed", "shall be open": a state, not an act
        if not AGENT_WORDS.search(subj):
            if FILER_WORDS.search(subj):
                subj = filer_for(question)
            else:
                continue
        action = verb_phrase(re.sub(r"^\s*(?:\w+ly\s+)?be\s+\w+\s+by\s+[^,;]+", "", after) if "by " in after[:80] else after)
        out.append({"clause": c, "actor": subj, "action": action, "kind": kind_of(action),
                    "modality": modality_of(c.modal), "condition": None, "deadline": c.deadline})
    return out


def _top(c: Clause) -> str:
    return f"{c.section or ''}:{(c.label or '-').split('.')[0]}"


def subsection_rule_drafts(clauses: list[Clause], question: str) -> list[dict]:
    """At most one step per top-level subsection: its first duty clause led by an actor (statutes put
    roughly one procedural act in each lettered subsection)."""
    seen, out = set(), []
    for d in rule_drafts(clauses, question):
        k = _top(d["clause"])
        if k in seen:
            continue
        seen.add(k)
        out.append(d)
    return out


# ------------------------------------------------------------------ model calls
class Asker:
    """One small question to the model.

    ``mode="schema"`` constrains the reply with the JSON schema (Ollama ``format``): reliable, but grammar-guided
    sampling is slow on a CPU.  ``mode="lines"`` asks for pipe-separated lines derived from the same schema and parses
    them, which lets the model sample freely and stops after a few tokens; a reply that does not parse is a miss.
    """

    def __init__(self, client: OllamaClient, mode: str = "schema", max_tokens: int = 160):
        self.client = client
        self.mode = mode
        self.max_tokens = max_tokens
        self.calls = 0

    def ask(self, system: str, user: str, schema: dict, retries: int = 1) -> dict | None:
        if self.mode == "lines":
            return self._ask_lines(system, user, schema)
        msgs = [{"role": "system", "content": system}, {"role": "user", "content": user}]
        for _ in range(retries + 1):
            self.calls += 1
            try:
                raw = self.client.chat(msgs, schema=schema)
                return json.loads(raw)
            except (json.JSONDecodeError, requests.RequestException, KeyError):
                msgs.append({"role": "user", "content": "Return only valid JSON matching the schema."})
        return None

    # ---- line protocol
    @staticmethod
    def _fields(obj_schema: dict) -> list[tuple[str, dict]]:
        return [(k, v) for k, v in obj_schema["properties"].items()]

    @staticmethod
    def _describe(fields) -> str:
        parts = []
        for k, v in fields:
            if v.get("type") == "boolean":
                parts.append(f"{k} (yes or no)")
            elif v.get("enum"):
                parts.append(f"{k} (one of: {', '.join(v['enum'])})")
            else:
                parts.append(k)
        return " | ".join(parts)

    @staticmethod
    def _coerce(fields, cells: list[str]) -> dict | None:
        if len(cells) < len(fields):
            cells = cells + [""] * (len(fields) - len(cells))
        out = {}
        for (k, v), cell in zip(fields, cells):
            cell = cell.strip().strip('"').strip()
            if v.get("type") == "boolean":
                out[k] = cell.lower().startswith(("y", "true"))
            elif v.get("enum"):
                low = cell.lower()
                out[k] = next((e for e in v["enum"] if e == low), next((e for e in v["enum"] if e in low), v["enum"][0]))
            else:
                out[k] = "" if cell in ("-", "none", "None", "n/a") else cell
        return out

    def _ask_lines(self, system: str, user: str, schema: dict) -> dict | None:
        props = schema["properties"]
        array_obj = next(((k, v) for k, v in props.items() if v.get("type") == "array"
                          and v.get("items", {}).get("type") == "object"), None)
        array_str = next(((k, v) for k, v in props.items() if v.get("type") == "array"
                          and v.get("items", {}).get("type") == "string"), None)
        if array_obj:
            key, spec = array_obj
            fields = self._fields(spec["items"])
            fmt = f"Reply with one line per item, fields separated by |: {self._describe(fields)}. No other text."
        elif array_str:
            key, fields = array_str[0], None
            fmt = "Reply with the ids separated by commas, or none. No other text."
        else:
            key, fields = None, self._fields(schema)
            fmt = f"Reply with ONE line, fields separated by |: {self._describe(fields)}. No other text."
        msgs = [{"role": "system", "content": system.replace("Return JSON only.", "").strip() + "\n" + fmt},
                {"role": "user", "content": user}]
        self.calls += 1
        try:
            raw = self.client.chat(msgs, schema=None, max_tokens=self.max_tokens * (6 if array_obj else 1))
        except requests.RequestException:
            return None
        raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.S).replace("```", "")
        lines = [ln.strip(" -*\t") for ln in raw.splitlines() if ln.strip()]
        if array_str:
            text = " ".join(lines)
            ids = [] if re.fullmatch(r"\s*none\.?\s*", text, re.I) else re.findall(r"\b[sc]\d+\b", text)
            return {key: ids}
        rows = [self._coerce(fields, ln.split("|")) for ln in lines if "|" in ln]
        rows = [r for r in rows if r]
        if array_obj:
            return {key: rows}
        return rows[0] if rows else None


LABEL_SCHEMA = {"type": "object", "properties": {
    "is_step": {"type": "boolean"},
    "action": {"type": "string"},
    "kind": {"type": "string", "enum": ["act", "notice", "filing", "hearing", "decision", "payment", "inspection",
                                        "record", "review"]},
    "condition": {"type": "string"}},
    "required": ["is_step", "action", "kind", "condition"]}

LABEL_SYSTEM = """You label one sentence of a statute for a process map of "{goal}".
is_step = true only if the sentence makes someone DO something as part of handling one case from start to finish
(submit, respond, decide, notify, extend time, petition, pay, issue, record). false for definitions, policy statements,
limits on fees, exceptions, record-keeping in general, and anything that is merely "deemed" or "is open".
action = the act as an imperative of at most 8 words, e.g. "Respond in writing within five work days".
condition = a short phrase if the act happens only in some cases (e.g. "records cannot be found"), else "".
Return JSON only."""


def hybrid_drafts(asker: Asker, clauses: list[Clause], question: str, goal: str) -> list[dict]:
    out = []
    for d in rule_drafts(clauses, question):
        c = d["clause"]
        ctx = next((x.text for x in clauses if x.label and c.label and x.label == c.label.split(".")[0]
                    and x.id != c.id), "")
        user = f"Sentence ({c.label or '-'}): {c.text[:700]}\n" + (f"Subsection starts: {ctx[:200]}\n" if ctx else "") + \
            f"Who acts: {d['actor']}"
        r = asker.ask(LABEL_SYSTEM.format(goal=goal), user, LABEL_SCHEMA)
        if not r or not r.get("is_step"):
            continue
        action = (r.get("action") or d["action"]).strip()
        action = " ".join(action.split()[:8])
        out.append({**d, "action": action[:1].upper() + action[1:], "kind": r.get("kind") or d["kind"],
                    "condition": (r.get("condition") or "").strip() or None})
    return out


PICK_SCHEMA = {"type": "object", "properties": {
    "clause": {"type": "string"},
    "action": {"type": "string"},
    "kind": {"type": "string", "enum": ["act", "notice", "filing", "hearing", "decision", "payment", "inspection",
                                        "record", "review"]},
    "condition": {"type": "string"}},
    "required": ["clause", "action", "kind", "condition"]}
PICK_SYSTEM = """You read one subsection of a statute about "{goal}". Its sentences are numbered like [c12].
Pick the ONE sentence that makes someone do the main act of the process in this subsection, or "none" if the
subsection only defines, limits, excepts or explains. action = that act as an imperative of at most 8 words.
condition = a short phrase if it happens only in some cases, else "". Return JSON only."""


def pick_drafts(asker: Asker, clauses: list[Clause], question: str, goal: str) -> list[dict]:
    """One call per top-level subsection that has duty clauses: the model picks the clause and phrases the act."""
    candidates = {d["clause"].id: d for d in rule_drafts(clauses, question)}
    groups: dict[str, list[Clause]] = {}
    for c in clauses:
        groups.setdefault(_top(c), []).append(c)
    out = []
    for key, cs in groups.items():
        duty = [c for c in cs if c.id in candidates]
        if not duty:
            continue
        listing = "\n".join(f"[{c.id}] {c.text[:400]}" for c in cs[:14])
        r = asker.ask(PICK_SYSTEM.format(goal=goal), f"Subsection {key.split(':')[1]}:\n{listing}", PICK_SCHEMA)
        if not r:
            continue
        cid = re.search(r"c\d+", r.get("clause") or "")
        if not cid or cid.group(0) not in candidates:
            if (r.get("clause") or "").strip().lower().startswith("none"):
                continue
            cid = None
        d = candidates[cid.group(0)] if cid else candidates[duty[0].id]
        action = " ".join((r.get("action") or d["action"]).split()[:8]) or d["action"]
        out.append({**d, "action": action[:1].upper() + action[1:], "kind": r.get("kind") or d["kind"],
                    "condition": (r.get("condition") or "").strip() or None})
    return out


SELECT_SCHEMA = {"type": "object", "properties": {"steps": {"type": "array", "items": {"type": "string"}}},
                 "required": ["steps"]}
SELECT_SYSTEM = """You choose which sentences of a statute are the STEPS of the process "{goal}".
A step is something a person or office must or may DO while handling one case from start to finish: submit,
respond, decide, notify, extend the time, petition, pay or collect a fee, issue, record. NOT steps: definitions,
limits or caps, exceptions, statements that something is deemed or open, general duties unrelated to one case.
{examples}Reply with the ids of the step sentences in the order the steps happen. Return JSON only."""


def few_shot(question: str, exclude_state: str | None, n: int = 4) -> str:
    """Worked examples from Claude's reference model for another state: sentences it made steps, and
    duty sentences it left out.  This is how the reference reasoning reaches the small model."""
    import json as _json
    from .. import config as _config
    from ..municipal import statutes as _statutes
    for path in sorted(_config.CURATED_DIR.glob(f"*/{question}.json")):
        st = path.parent.name
        if st in (exclude_state, "places"):
            continue
        try:
            spec = _json.loads(path.read_text(encoding="utf-8"))
            texts = _statutes.reference_texts(st, spec["sections"][:6])
        except Exception:  # noqa: BLE001 - statutes not downloaded for that state
            continue
        text = _statutes.combined_text(texts)
        quotes = [re.sub(r"\s+", " ", s["source"]["quote"]).lower() for s in spec["facts"]["steps"]]
        pos, neg = [], []
        for c in segment(text):
            if not c.modal:
                continue
            norm = re.sub(r"\s+", " ", c.text).lower()
            (pos if any(q in norm or norm in q for q in quotes) else neg).append(c.text)
        if len(pos) >= 2 and len(neg) >= 2:
            ex = [f'STEP: "{t[:200]}"' for t in pos[:n]] + [f'NOT A STEP: "{t[:200]}"' for t in neg[:n]]
            return "Examples, decided by a careful lawyer for another state's law:\n" + "\n".join(ex) + "\n"
    return ""


def _features(d: dict) -> list[str]:
    """What the learned selector looks at for one candidate clause."""
    c: Clause = d["clause"]
    m = re.search(r"\b(?:shall|may|must)\b(.*)", c.text, re.I | re.S)
    words = [w.lower() for w in re.findall(r"[A-Za-z]+", verb_phrase(m.group(1)) if m else "")]
    words = [w for w in words if w not in ("either", "also", "then", "only", "not", "be", "immediately", "promptly")]
    verb = (words[0] if words else "?")[:6]                 # "shall within 15 days ... either make" -> "make"
    who = actor_kind(d["actor"])
    depth = len((c.label or "").split("."))
    return [f"modal={modality_of(c.modal)}", f"who={who}", f"verb={verb}", f"kind={d['kind']}",
            f"deadline={bool(c.deadline)}", f"depth={min(depth, 3)}", f"who_modal={who}:{modality_of(c.modal)}",
            f"passive={bool(re.search(r'be [a-z]+ed by', c.text))}"]


def _training(question: str, exclude: tuple[str, str]) -> list[tuple[list[str], bool]]:
    """Labelled candidates from Claude's reference models of other cases: a candidate is a positive when its
    clause contains (or is contained in) the quote of one of Claude's steps."""
    import json as _json
    from .. import config as _config
    from ..municipal import statutes as _statutes
    data = []
    for path in sorted(_config.CURATED_DIR.glob("*/*.json")):
        st, q = path.parent.name, path.stem
        if st == "places" or st == exclude[0]:      # hold out the whole state, as a new state would be
            continue
        try:
            spec = _json.loads(path.read_text(encoding="utf-8"))
            text = _statutes.combined_text(_statutes.reference_texts(st, spec["sections"]))
        except Exception:  # noqa: BLE001 - that state's statutes are not downloaded
            continue
        quotes = [(s["source"]["section"], re.sub(r"\s+", " ", s["source"]["quote"]).lower())
                  for s in spec["facts"]["steps"]]
        for d in rule_drafts(segment(text), q):
            c = d["clause"]
            norm = re.sub(r"\s+", " ", c.text).lower()
            pos = any(sec == (c.section or sec) and (qt in norm or norm in qt) for sec, qt in quotes)
            weight = 1.0 if q == question else 0.5          # other questions teach a little, same question more
            data.append((_features(d), pos, weight))
    return data


def learned_scores(clauses: list[Clause], question: str, state: str | None) -> list[tuple[float, dict]]:
    """(log-odds, draft) for every candidate clause, from a Naive Bayes selector trained on Claude's choices
    in the other cases (never this one)."""
    import math
    data = _training(question, (state or "", question))
    cands = rule_drafts(clauses, question)
    if not data or not cands:
        return [(0.0, d) for d in cands]
    pos_w = sum(w for _, y, w in data if y) or 1e-9
    neg_w = sum(w for _, y, w in data if not y) or 1e-9
    counts: dict[tuple[str, bool], float] = {}
    for feats, y, w in data:
        for f in feats:
            counts[(f, y)] = counts.get((f, y), 0.0) + w
    vocab = {f for feats, _, _ in data for f in feats}

    def log_odds(feats):
        lo = math.log(pos_w / neg_w)
        for f in feats:
            p = (counts.get((f, True), 0.0) + 1) / (pos_w + len(vocab))
            n = (counts.get((f, False), 0.0) + 1) / (neg_w + len(vocab))
            lo += math.log(p / n)
        return lo
    return [(log_odds(_features(d)), d) for d in cands]


def learned_llm_drafts(asker: Asker, clauses: list[Clause], question: str, goal: str, state: str | None) -> list[dict]:
    """The learned selector keeps its top third and drops its bottom third; the local model judges each
    clause in the middle third on its own."""
    ranked = [d for _, d in sorted(learned_scores(clauses, question, state), key=lambda x: -x[0])]
    n = len(ranked)
    top, middle = ranked[:max(2, n // 3)], ranked[max(2, n // 3):max(2, 2 * n // 3)]
    out = list(top)
    for d in middle:
        c = d["clause"]
        r = asker.ask(LABEL_SYSTEM.format(goal=goal), f"Sentence ({c.label or '-'}): {c.text[:600]}\n"
                      f"Who acts: {d['actor']}", LABEL_SCHEMA)
        if r and r.get("is_step"):
            out.append(d)
    return sorted(out, key=lambda d: d["clause"].start)


def learned_drafts(clauses: list[Clause], question: str, state: str | None, share: float | None = None) -> list[dict]:
    """Keep the best-ranked candidates.  Naive Bayes ranks well but its probabilities are not calibrated, so the
    number kept is the share of candidates Claude made steps in the training cases, plus a little for recall."""
    scored = learned_scores(clauses, question, state)
    if not scored:
        return []
    if share is None:
        data = _training(question, (state or "", question))
        pos = sum(w for _, y, w in data if y)
        share = min(0.8, 1.25 * pos / max(1e-9, sum(w for _, _, w in data))) if data else 0.5
    k = max(3, round(share * len(scored)))
    keep = [d for _, d in sorted(scored, key=lambda x: -x[0])[:k]]
    return sorted(keep, key=lambda d: d["clause"].start)


def select_drafts(asker: Asker, clauses: list[Clause], question: str, goal: str, examples: str = "") -> list[dict]:
    """One call: the model sees every candidate duty sentence and returns the ids that are process steps."""
    cands = rule_drafts(clauses, question)
    if not cands:
        return []
    listing = "\n".join(f"[{d['clause'].id}] ({d['clause'].label or '-'}) {' '.join(d['clause'].text.split()[:40])}"
                        for d in cands)
    r = asker.ask(SELECT_SYSTEM.format(goal=goal, examples=examples), listing, SELECT_SCHEMA)
    by_id = {d["clause"].id: d for d in cands}
    chosen = []
    for x in (r or {}).get("steps", []):
        m = re.search(r"c\d+", str(x))
        if m and m.group(0) in by_id and by_id[m.group(0)] not in chosen:
            chosen.append(by_id[m.group(0)])
    return chosen


SUMMARY_SCHEMA = {"type": "object", "properties": {
    "acts": {"type": "boolean"}, "who": {"type": "string"}, "summary": {"type": "string"}},
    "required": ["acts", "who", "summary"]}
SUMMARY_SYSTEM = """You summarise one subsection of a statute about "{goal}".
acts = true if it makes someone do something in the process; who = that actor (short); summary = one line, at most
20 words, saying who does what, and any time limit. Return JSON only."""
PLAN_SCHEMA = {"type": "object", "properties": {"steps": {"type": "array", "items": {"type": "object", "properties": {
    "sub": {"type": "string"}, "who": {"type": "string"}, "action": {"type": "string"},
    "kind": {"type": "string", "enum": ["act", "notice", "filing", "hearing", "decision", "payment", "inspection",
                                        "record", "review"]},
    "condition": {"type": "string"}}, "required": ["sub", "who", "action", "kind", "condition"]}}},
    "required": ["steps"]}
PLAN_SYSTEM = """You turn a summary of a statute into the steps of the process "{goal}", in the order they happen.
One step per legally meaningful act (usually 4 to 9 steps). sub = the subsection label the step comes from (exactly as
given). who = the actor. action = imperative, at most 8 words. condition = "" unless the step happens only in some
cases. Leave out definitions, fee limits and exceptions. Return JSON only."""


def _overlap(a: str, b: str) -> float:
    ta = set(re.findall(r"[a-z]{3,}", a.lower()))
    tb = set(re.findall(r"[a-z]{3,}", b.lower()))
    return len(ta & tb) / (len(ta) or 1)


def outline_drafts(asker: Asker, clauses: list[Clause], question: str, goal: str) -> list[dict]:
    groups: dict[str, list[Clause]] = {}
    for c in clauses:
        groups.setdefault((c.label or "-").split(".")[0], []).append(c)
    lines = []
    for sub, cs in groups.items():
        body = " ".join(c.text for c in cs)[:1600]
        r = asker.ask(SUMMARY_SYSTEM.format(goal=goal), f"Subsection {sub}:\n{body}", SUMMARY_SCHEMA)
        if r and r.get("acts"):
            lines.append(f"{sub}: {r.get('who', '')} - {r.get('summary', '')}")
    if not lines:
        return []
    plan = asker.ask(PLAN_SYSTEM.format(goal=goal), "Summary by subsection:\n" + "\n".join(lines), PLAN_SCHEMA)
    out = []
    for s in (plan or {}).get("steps", [])[:14]:
        sub = (s.get("sub") or "").strip().strip("()").split(".")[0]
        pool = groups.get(sub) or groups.get(sub.upper()) or groups.get(sub.lower()) or clauses
        best = max(pool, key=lambda c: (_overlap(s.get("action", "") + " " + s.get("who", ""), c.text)
                                        + (0.3 if c.modal else 0)))
        dl = best.deadline or next((c.deadline for c in pool if c.deadline), None)
        action = " ".join((s.get("action") or "Act").split()[:8])
        out.append({"clause": best, "actor": (s.get("who") or best.subject or filer_for(question)).strip()[:60],
                    "action": action[:1].upper() + action[1:], "kind": s.get("kind") or kind_of(action),
                    "modality": modality_of(best.modal), "condition": (s.get("condition") or "").strip() or None,
                    "deadline": dl})
    return out


REVIEW_SCHEMA = {"type": "object", "properties": {"drop": {"type": "array", "items": {"type": "string"}}},
                 "required": ["drop"]}
REVIEW_SYSTEM = """You check a draft list of steps for the process "{goal}". Return the ids of steps to drop:
duplicates of another step, steps that are not acts in handling one case, and minor details. Keep the 4 to 9 steps
that matter most. Return JSON only."""


def review(asker: Asker, drafts: list[dict], goal: str) -> list[dict]:
    if len(drafts) <= 4:
        return drafts
    listing = "\n".join(f"s{i}: {d['actor']} - {d['action']}" for i, d in enumerate(drafts))
    r = asker.ask(REVIEW_SYSTEM.format(goal=goal), listing, REVIEW_SCHEMA)
    drop = {x.strip() for x in (r or {}).get("drop", [])}
    kept = [d for i, d in enumerate(drafts) if f"s{i}" not in drop]
    return kept if len(kept) >= 3 else drafts


JUDGE_SCHEMA = {"type": "object", "properties": {"is_step": {"type": "boolean"}}, "required": ["is_step"]}
JUDGE_SYSTEM = """You decide whether one sentence of a statute is a STEP of the process "{goal}": something a person or
office does while handling one case (submit, respond, decide, notify, extend the time, appeal, pay, issue, record).
Definitions, caps, exceptions and general policy are not steps.
Here is how a careful lawyer decided the most similar sentences in other states' laws:
{examples}
Return JSON only."""


def config_vectors() -> str:
    from .. import config
    return config.VECTORS


def stacked_drafts(clauses: list[Clause], question: str, state: str | None, *, vectors: str | None = None,
                   asker: Asker | None = None, goal: str = "", band: float = 0.12, notes: list | None = None,
                   only_states: set[str] | None = None) -> list[dict]:
    """Wide candidates scored by the selector trained on Claude's references in other states; with an asker,
    the local model re-judges the borderline ones, shown the nearest labelled sentences as examples."""
    from . import selector as SEL
    cands = SEL.wide_drafts(clauses, question)
    if not cands:
        return []
    vectors = vectors or config_vectors()
    emb = (SEL.tfidf() if vectors == "tfidf" else SEL.Embedder() if vectors == "embed"
           else SEL.Combo(SEL.tfidf(), SEL.Embedder()) if vectors == "combo" else None)
    sel = SEL.Selector(question, state, emb, use_embeddings=emb is not None, only_states=only_states)
    if sel.emb is None and vectors in ("embed", "combo"):
        sel = SEL.Selector(question, state, SEL.tfidf(), only_states=only_states)   # no embedding server: words only
    if not sel.refs:
        if notes is not None:
            notes.append("no reference models to learn from")
        return []                                   # nothing learned: better no model than every clause
    sel = sel.fit()
    probs = sel.predict(cands)
    t = sel.threshold
    keep = []
    judged = 0
    judge = Asker(asker.client, mode=asker.mode, max_tokens=12) if asker else None   # a yes or no: no rambling
    for d, p in zip(cands, probs):
        if judge is not None and abs(p - t) < band:
            ex = "\n".join(f'{"STEP" if y else "NOT A STEP"}: "{" ".join(txt.split()[:45])}"'
                           for txt, y in sel.neighbours(d))
            r = judge.ask(JUDGE_SYSTEM.format(goal=goal, examples=ex),
                          f'Sentence: "{" ".join(d["clause"].text.split()[:90])}"\nWho acts: {d["actor"]}', JUDGE_SCHEMA)
            judged += 1
            if r is not None:
                if r.get("is_step"):
                    keep.append(d)
                continue
        if p >= t:
            keep.append(d)
    # who acts: the rules, except where they fall back to "public body" - there the actor kind Claude gave the
    # most similar step clauses in other states wins (a passive "may be inspected" is usually the requester's act)
    kinds = dict(zip((id(d) for d in cands), sel.neighbour_kinds(cands)))
    rename = {"private-party": filer_for(question), "court": "court", "official": "responsible official",
              "other-government": "local government"}
    for d in keep:
        rule, near = actor_kind(d["actor"]), kinds.get(id(d))
        if near and rule == "public-body" and near != rule:
            d["actor"], d["actor_kind"] = rename[near], near
        else:
            d["actor_kind"] = rule
    if notes is not None:
        notes.append(f"{len(keep)} of {len(cands)} candidates kept (threshold {t:.2f}, train F1 "
                     f"{getattr(sel, 'train_f1', 0):.2f}, {len(sel.refs)} references, vectors "
                     f"{sel.emb.name if sel.emb is not None else 'none'}"
                     + (f", {judged} judged by the model)" if asker else ")"))
    if judge is not None:
        asker.calls += judge.calls
    return sorted(keep, key=lambda d: d["clause"].start)


# ------------------------------------------------------------------ snapping
def snap_quotes(facts: LegalProcessFacts, text: str, threshold: float = 0.72) -> tuple[LegalProcessFacts, int]:
    """Replace each quote that is not an exact span with the most similar clause (if similar enough)."""
    clauses = segment(text)
    norm = lambda s: re.sub(r"\s+", " ", s.replace("’", "'").replace("“", '"').replace("”", '"')).strip()  # noqa: E731
    ntext = norm(text)
    data = facts.model_dump()
    fixed = 0

    def walk(node):
        nonlocal fixed
        if isinstance(node, dict):
            if "quote" in node and isinstance(node["quote"], str) and norm(node["quote"]) not in ntext:
                best = max(clauses, key=lambda c: SequenceMatcher(None, norm(node["quote"]).lower(),
                                                                  norm(c.text).lower()).ratio())
                if SequenceMatcher(None, norm(node["quote"]).lower(), norm(best.text).lower()).ratio() >= threshold \
                        or norm(node["quote"]).lower() in norm(best.text).lower():
                    node["quote"] = best.text
                    fixed += 1
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)
    walk(data)
    return LegalProcessFacts.model_validate(data), fixed


# ------------------------------------------------------------------ entry point
STRATEGIES = ["stack", "stack_combo", "stack_tfidf", "stack_embed", "stack_nb", "stack_llm", "stack_llm_lines", "wide", "rules", "rules_sub", "learned", "learned_wide", "learned_llm", "learned_llm_review", "select", "select_fewshot", "select_fewshot_dl", "select_fewshot_review", "pick",
              "pick_review",
              "pick_lines", "hybrid", "hybrid_review", "outline",
              "outline_review", "hybrid_lines", "hybrid_review_lines",
              "outline_lines", "outline_review_lines", "snap", "oneshot"]
GOALS = {"records": "requesting public records from a public body", "business": "forming a business entity"}


def run(strategy: str, text: str, *, section: str, title: str, code: str, jurisdiction: str, question: str,
        client: OllamaClient | None = None, prior: LegalProcessFacts | None = None, state: str | None = None) -> Run:
    t0 = time.time()
    goal = GOALS.get(question, question)
    name = {"records": "Request public records", "business": "Form a business entity"}.get(question, title)
    clauses = segment(text)
    mode = "lines" if strategy.endswith("_lines") else "schema"
    strategy_name, strategy = strategy, strategy.removesuffix("_lines")
    asker = Asker(client, mode=mode) if client else None
    notes: list[str] = []
    try:
        if strategy == "oneshot":
            res = extract(client, text=text, section=section, title=title, code=code, jurisdiction=jurisdiction)
            return Run(strategy_name, client.model, res.facts, res.problems, res.rounds, time.time() - t0)
        if strategy == "snap":
            facts = prior
            if facts is None:
                res = extract(client, text=text, section=section, title=title, code=code, jurisdiction=jurisdiction)
                facts = res.facts
            if facts is None:
                return Run(strategy_name, client.model if client else None, None, ["no facts to snap"], 0, time.time() - t0)
            facts, n = snap_quotes(facts, text)
            notes.append(f"{n} quotes snapped")
            return Run(strategy_name, client.model if client else None, facts, check_facts(facts, text), 0,
                       time.time() - t0, notes)
        if strategy == "wide":
            from .selector import wide_drafts
            drafts = wide_drafts(clauses, question)
        elif strategy in ("stack", "stack_nb", "stack_tfidf", "stack_embed", "stack_combo"):
            vectors = {"stack_nb": "none", "stack_tfidf": "tfidf", "stack_embed": "embed", "stack_combo": "combo"}.get(strategy)
            drafts = stacked_drafts(clauses, question, state, vectors=vectors, notes=notes)
        elif strategy.startswith("stack_llm"):
            drafts = stacked_drafts(clauses, question, state, asker=asker, goal=goal, notes=notes)
        elif strategy == "rules_sub":
            drafts = subsection_rule_drafts(clauses, question)
        elif strategy == "rules":
            drafts = rule_drafts(clauses, question)
        elif strategy.startswith("learned_llm"):
            drafts = learned_llm_drafts(asker, clauses, question, goal, state)
        elif strategy.startswith("learned_wide"):
            drafts = learned_drafts(clauses, question, state, share=0.6)
        elif strategy.startswith("learned"):
            drafts = learned_drafts(clauses, question, state)
            notes.append("selector trained on Claude's other reference models")
        elif strategy.startswith("select"):
            examples = few_shot(question, state) if "fewshot" in strategy else ""
            if examples:
                notes.append("few-shot examples from another state's reference model")
            drafts = select_drafts(asker, clauses, question, goal, examples)
            if strategy.endswith("_dl") or "_dl_" in strategy:
                # domain prior: a clause that sets a time limit is almost always a step
                chosen = {d["clause"].id for d in drafts}
                extra = [d for d in rule_drafts(clauses, question) if d["deadline"] and d["clause"].id not in chosen]
                drafts = sorted(drafts + extra, key=lambda d: d["clause"].start)
                notes.append(f"{len(extra)} deadline clauses added")
        elif strategy.startswith("pick"):
            drafts = pick_drafts(asker, clauses, question, goal)
        elif strategy.startswith("hybrid"):
            drafts = hybrid_drafts(asker, clauses, question, goal)
        elif strategy.startswith("outline"):
            drafts = outline_drafts(asker, clauses, question, goal)
        else:
            raise ValueError(f"unknown strategy {strategy}")
        if strategy.endswith("_review") and asker:
            before = len(drafts)
            drafts = review(asker, drafts, goal)
            notes.append(f"review kept {len(drafts)} of {before}")
        facts = assemble(drafts, clauses, section, question, name)
        problems = check_facts(facts, text)
        return Run(strategy_name, client.model if client else None, facts, problems, asker.calls if asker else 0,
                   time.time() - t0, notes)
    except (ValueError, ValidationError) as e:
        return Run(strategy_name, client.model if client else None, None, [f"{type(e).__name__}: {e}"[:300]],
                   asker.calls if asker else 0, time.time() - t0, notes)
