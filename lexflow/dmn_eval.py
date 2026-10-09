"""Reference decision-table evaluator on canonical FEEL cells (independent of SpiffWorkflow)."""
from __future__ import annotations

from .feel import evaluate_literal, evaluate_unary
from .ir import Decision


def matching_rules(decision: Decision, data: dict) -> list:
    hits = []
    for rule in decision.rules:
        if all(evaluate_unary(cell, data.get(inp.expression))
               for cell, inp in zip(rule.inputs, decision.inputs)):
            hits.append(rule)
    return hits


def decide(decision: Decision, data: dict) -> dict:
    hits = matching_rules(decision, data)
    if decision.hit_policy == "UNIQUE" and len(hits) > 1:
        raise ValueError(f"{decision.id}: UNIQUE violated by {[r.id for r in hits]} for {data}")
    if decision.hit_policy == "COLLECT":
        out: dict = {o.name: [] for o in decision.outputs}
        for r in hits:
            for o, cell in zip(decision.outputs, r.outputs):
                out[o.name].append(evaluate_literal(cell))
        return out
    if not hits:
        return {}
    rule = hits[0]
    return {o.name: evaluate_literal(cell) for o, cell in zip(decision.outputs, rule.outputs)} | {"_rule": rule.id}


def completeness_gaps(decision: Decision, grid: list[dict]) -> list[dict]:
    """Input combinations from ``grid`` that match no rule (table not complete)."""
    return [g for g in grid if not matching_rules(decision, g)]


def overlaps(decision: Decision, grid: list[dict]) -> list[tuple[dict, list[str]]]:
    """Grid points hit by more than one rule (fine for FIRST, a defect for UNIQUE)."""
    out = []
    for g in grid:
        hits = matching_rules(decision, g)
        if len(hits) > 1:
            out.append((g, [r.id for r in hits]))
    return out
