"""The judge: one prompt per case, one JSON answer, and the checks no model is trusted on.

The prompt shows the record (label, kind, description, aliases, its statements), each candidate (Wikidata label,
description, the facts that tell namesakes apart, the English Wikipedia lead) and the search snippets, then asks
for ``{"verdict": "<Q id | none | unsure>", "confidence": 0..1, "because": "..."}``.  ``json`` mode (Ollama's plain
JSON format with the shape described in words) is the default: under a grammar a thinking model with its
reasoning off tends to the shortest legal reply, and here that would be ``unsure`` (docs/design/askbench-json-mode.md).
``schema`` mode is kept for comparison.

``sanity`` then applies what the evidence settles without a model: a verdict that is not one of the candidates is
no verdict; a person's record cannot be a non-human item; a candidate who died decades ago is not the maker with
an Instagram account.  Those lower the confidence or turn the verdict to ``unsure`` and say why in ``flags``.
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone

from .source import Case

SYSTEM = (
    "You check whether a record in the Glass Database (a community register of glass artists, studios, schools, "
    "museums, shows, places and the vocabulary of glass) is the same real-world thing as one of the candidate items "
    "found on Wikidata. Decide from the evidence shown and nothing else. The record and a candidate are the same "
    "thing when the name fits and the facts agree: the same place or region, the same kind of work, no contradiction "
    "in dates, occupation or what kind of thing it is. A namesake in another field, another country or another "
    "century is not the same. If the candidates are clearly different things, the verdict is none. If one could be "
    "the same but nothing in the evidence confirms it, the verdict is unsure. When the record is a vocabulary term "
    "(a colour, an occupation, a technique, a vessel form, a trait of glass), the answer is the general concept of "
    "that name in the sense the record's description gives, not a narrower kind of it or a namesake in another "
    "language: a record 'student' is the plain item for a student, not a doctoral student; 'curator' in the glass "
    "field is the museum curator; a term described as a kind of glass is the glass item. Confidence is how sure the "
    "evidence makes you, from 0 to 1; say what decided it in one or two sentences that name the facts."
)
SHAPE = ('Answer with one JSON object and nothing else, shaped like this: {"verdict": "<the Q id of the one '
         'candidate that is the same thing, or none, or unsure>", "confidence": <a number from 0 to 1>, '
         '"because": "<one or two sentences naming the facts that decided it>"}')
SCHEMA = {"type": "object", "properties": {"verdict": {"type": "string"}, "confidence": {"type": "number"},
                                           "because": {"type": "string"}}, "required": ["verdict", "confidence", "because"]}
MAX_CHARS = 9000            # of evidence in one prompt: candidates first, then search, each cut to fit
MAX_TOKENS = 400
NONE_WORDS = {"none", "no", "neither", "nobody", "nothing", "no match", "none of these", "none of them", "null", ""}
UNSURE_WORDS = {"unsure", "unknown", "uncertain", "unclear", "maybe", "possibly", "cannot tell", "not sure"}
_Q = re.compile(r"\bQ\d+\b")


@dataclass
class Verdict:
    verdict: str = "unsure"              # a Q id, "none" or "unsure"
    confidence: float = 0.0
    because: str = ""
    ok: bool = True                      # the answer parsed into a verdict (a Q id among the candidates, none or unsure)
    flags: list[str] = field(default_factory=list)
    model: str = ""
    node: str = ""
    seconds: float = 0.0
    prompt_tokens: int | None = None
    tokens: int | None = None
    raw: str = ""

    def as_dict(self) -> dict:
        d = asdict(self)
        d.pop("raw", None)
        d["confidence"] = round(float(d["confidence"]), 3)
        return d


# ------------------------------------------------------------------------------------------------ the prompt
def _facts(facts: dict, limit: int = 6) -> list[str]:
    return [f"  {k}: {', '.join(str(x) for x in v[:limit])}" for k, v in (facts or {}).items() if v]


def record_text(case: Case) -> str:
    lines = [f"RECORD (Glass Database, kind: {case.kind})", f"  name: {case.label}"]
    if case.description:
        lines.append(f"  description: {case.description}")
    if case.aliases:
        lines.append(f"  also known as: {', '.join(case.aliases[:6])}")
    lines += _facts(case.facts)
    return "\n".join(lines)


def candidate_text(qid: str, c: dict, wiki: bool = True) -> str:
    lines = [f"CANDIDATE {qid}: {c.get('label') or qid}"]
    if c.get("description"):
        lines.append(f"  description: {c['description']}")
    if c.get("aliases"):
        lines.append(f"  also known as: {', '.join(c['aliases'][:6])}")
    lines += _facts(c.get("facts") or {})
    if wiki and c.get("wikipedia"):
        lines.append(f"  Wikipedia: {c['wikipedia']}")
    return "\n".join(lines)


def search_text(searched: dict) -> str:
    if not searched:
        return ""
    lines = ["WEB SEARCH"]
    for q, hits in searched.items():
        lines.append(f"  query: {q}")
        if not hits:
            lines.append("    (no results)")
        for hit in hits:
            lines.append(f"    - {hit.get('title') or ''} <{hit.get('url') or ''}>: {hit.get('snippet') or ''}")
    return "\n".join(lines)


def prompt(case: Case, evidence: dict) -> list[dict]:
    """The two messages.  Candidates come first and are never cut away; search text takes what room is left."""
    cands = evidence.get("candidates") or {}
    seen = {c.get("qid"): c for c in case.candidates}           # what the lookup saw, when no facts were read
    parts = [record_text(case), ""]
    budget = MAX_CHARS - len(parts[0])
    for qid in case.candidate_ids():
        c = cands.get(qid) or {"label": seen.get(qid, {}).get("label") or qid, "description": seen.get(qid, {}).get("description") or "",
                               "facts": {"instance of": list(seen.get(qid, {}).get("types") or [])}}
        text = candidate_text(qid, c)
        if len(text) > budget and budget > 400:
            text = text[:budget - 1] + "…"
        parts.append(text)
        parts.append("")
        budget -= len(text) + 1
    st = search_text(evidence.get("search") or {})
    if st and budget > 300:
        parts.append(st[:budget])
        parts.append("")
    elif evidence.get("searched") is False:
        parts.append("WEB SEARCH: not available for this run")
        parts.append("")
    parts.append("QUESTION: Which candidate, if any, is the same thing as the record? " + SHAPE)
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": "\n".join(parts)}]


# ------------------------------------------------------------------------------------------------ the answer
def _first_object(text: str) -> dict | None:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()
    try:
        v = json.loads(text)
        return v if isinstance(v, dict) else None
    except ValueError:
        pass
    m = re.search(r"\{.*\}", text, flags=re.S)
    if m:
        try:
            v = json.loads(m.group(0))
            return v if isinstance(v, dict) else None
        except ValueError:
            pass
    out: dict = {}
    mv = re.search(r'"?verdict"?\s*[:=]\s*"?([^",}\n]+)', text, flags=re.I)
    mc = re.search(r'"?confidence"?\s*[:=]\s*([0-9.]+)', text, flags=re.I)
    mb = re.search(r'"?because"?\s*[:=]\s*"([^"]+)', text, flags=re.I)
    if mv:
        out["verdict"] = mv.group(1).strip()
    if mc:
        out["confidence"] = mc.group(1)
    if mb:
        out["because"] = mb.group(1)
    return out or None


def parse(text: str, case: Case, labels: dict[str, str] | None = None) -> Verdict:
    """The model's text → a Verdict whose verdict is a candidate's Q id, ``none`` or ``unsure``.  A label instead
    of an id is mapped back to the candidate; anything else is ``unsure`` and ``ok=False``."""
    ids = case.candidate_ids()
    labels = {k.strip().lower(): q for q, k in (labels or {}).items()}
    for c in case.candidates:
        if c.get("label"):
            labels.setdefault(str(c["label"]).strip().lower(), c["qid"])
    obj = _first_object(text or "")
    v = Verdict(raw=text or "")
    if not obj:
        v.ok, v.because, v.confidence = False, "the model gave no readable answer", 0.0
        return v
    raw_verdict = str(obj.get("verdict") if obj.get("verdict") is not None else "").strip()
    low = raw_verdict.lower().strip(" .\"'")
    verdict = None
    if low in NONE_WORDS:
        verdict = "none"
    elif low in UNSURE_WORDS:
        verdict = "unsure"
    else:
        qs = [q for q in _Q.findall(raw_verdict.upper()) if q in ids]
        if qs:
            verdict = qs[0]
        elif low in labels and labels[low] in ids:
            verdict = labels[low]
        elif _Q.search(raw_verdict.upper()):
            v.flags.append(f"named {raw_verdict}, which is not one of the candidates")
            verdict, v.ok = "unsure", False
        elif any(w in low for w in ("none", "neither", "no match")):
            verdict = "none"
        elif any(w in low for w in ("unsure", "uncertain", "unknown", "not sure")):
            verdict = "unsure"
        else:
            v.flags.append(f"the verdict {raw_verdict!r} names no candidate")
            verdict, v.ok = "unsure", False
    try:
        conf = float(obj.get("confidence"))
    except (TypeError, ValueError):
        conf = 0.5 if v.ok else 0.0
        v.flags.append("no confidence given")
    if conf > 1 and conf <= 100:
        conf = conf / 100
    v.verdict, v.confidence = verdict, max(0.0, min(1.0, conf))
    v.because = str(obj.get("because") or "").strip()[:600]
    if verdict == "unsure" and v.ok:
        v.confidence = min(v.confidence, 0.5)
    return v


def sanity(case: Case, v: Verdict, evidence: dict) -> Verdict:
    """What the evidence settles on its own.  Lowers confidence or turns the verdict to unsure; never raises it."""
    if not _Q.fullmatch(v.verdict or ""):
        return v
    c = (evidence.get("candidates") or {}).get(v.verdict) or {}
    facts = c.get("facts") or {}
    kinds = " ".join(x.lower() for x in facts.get("instance of") or [])
    is_human = "human" in kinds.split() or kinds.startswith("human")
    if case.kind == "person" and kinds and not is_human:
        v.flags.append(f"the record is a person and {v.verdict} is {', '.join(facts.get('instance of') or [])[:60]}")
        v.verdict, v.confidence = "unsure", min(v.confidence, 0.2)
        return v
    if case.kind != "person" and is_human:
        v.flags.append(f"the record is a {case.kind} and {v.verdict} is a person")
        v.verdict, v.confidence = "unsure", min(v.confidence, 0.2)
        return v
    died = facts.get("died") or []
    alive_signs = case.facts.get("Instagram username") or case.facts.get("official website")
    if died and alive_signs:
        try:
            year = int(re.sub(r"\D", "", died[0])[:4])
        except ValueError:
            year = 0
        if year and year < datetime.now(timezone.utc).year - 20:
            v.flags.append(f"{v.verdict} died in {died[0]}; the record has a website or Instagram account")
            v.confidence = min(v.confidence, 0.2)
    return v


# ------------------------------------------------------------------------------------------------ the call
def judge(client, case: Case, evidence: dict, mode: str = "json") -> Verdict:
    """Ask ``client`` (an OllamaClient with its model set) about one case."""
    t0 = time.time()
    since = len(client.log)
    fmt = SCHEMA if mode == "schema" else "json"
    text = client.chat(prompt(case, evidence), schema=fmt, temperature=0.0, max_tokens=MAX_TOKENS)
    v = sanity(case, parse(text, case), evidence)
    v.model, v.seconds = client.model, round(time.time() - t0, 1)
    used = client.nodes_used(since)
    v.node = ",".join(sorted(used)) if used else ""
    last = client.log[-1] if len(client.log) > since else {}
    v.prompt_tokens, v.tokens = last.get("prompt_eval_count"), last.get("eval_count")
    return v
