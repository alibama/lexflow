"""Score an extraction against the answer key (gold facts) - for choosing local models."""
from __future__ import annotations

import re
from dataclasses import dataclass, asdict

from .ollama import check_facts
from .schema import LegalProcessFacts

STOP = {"the", "a", "an", "of", "to", "for", "and", "or", "with", "in", "on", "by", "at", "be", "is", "are"}


def _tokens(s: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", s.lower()) if t not in STOP}


def _sim(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    return len(ta & tb) / len(ta | tb) if ta | tb else 0.0


def _sub(q) -> str:
    return (q.subsection or "").split(".")[0].upper()


@dataclass
class Score:
    quote_validity: float
    actor_recall: float
    step_recall: float
    step_precision: float
    modality_accuracy: float
    deadline_recall: float
    decision_rules: int
    gold_decision_rules: int
    problems: int

    def as_dict(self):
        return asdict(self)


def score(candidate: LegalProcessFacts, gold: LegalProcessFacts, text: str, threshold: float = 0.34) -> Score:
    problems = check_facts(candidate, text)
    quotes_total = 1 + len(candidate.actors) + len(candidate.steps) + sum(1 for s in candidate.steps if s.deadline) \
        + sum(len(d.rules) for d in candidate.decisions) + len(candidate.outcomes) + len(candidate.cross_references)
    bad_quotes = sum(1 for p in problems if "not an exact span" in p)
    actor_hits = sum(1 for g in gold.actors if any(_sim(g.name, c.name) >= threshold or g.id == c.id for c in candidate.actors))
    matched: list[tuple] = []
    used = set()
    for g in gold.steps:
        best, best_s = None, 0.0
        for c in candidate.steps:
            if c.id in used:
                continue
            s = _sim(g.action, c.action) + (0.15 if _sub(g.source) == _sub(c.source) else 0)
            if s > best_s:
                best, best_s = c, s
        if best is not None and best_s >= threshold:
            used.add(best.id)
            matched.append((g, best))
    modality_ok = sum(1 for g, c in matched if g.modality == c.modality)
    gold_deadlines = [s.deadline for s in gold.steps if s.deadline]
    cand_deadlines = [s.deadline for s in candidate.steps if s.deadline]
    deadline_hits = sum(1 for g in gold_deadlines if any(
        c.amount == g.amount and c.unit == g.unit and _sim(c.anchor, g.anchor) >= threshold for c in cand_deadlines))
    return Score(
        quote_validity=round(1 - bad_quotes / max(quotes_total, 1), 3),
        actor_recall=round(actor_hits / max(len(gold.actors), 1), 3),
        step_recall=round(len(matched) / max(len(gold.steps), 1), 3),
        step_precision=round(len(matched) / max(len(candidate.steps), 1), 3),
        modality_accuracy=round(modality_ok / max(len(matched), 1), 3),
        deadline_recall=round(deadline_hits / max(len(gold_deadlines), 1), 3),
        decision_rules=sum(len(d.rules) for d in candidate.decisions),
        gold_decision_rules=sum(len(d.rules) for d in gold.decisions),
        problems=len(problems),
    )
