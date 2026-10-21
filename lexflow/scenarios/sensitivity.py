"""One-at-a-time sensitivity: which inputs change the requirement set, the fees or the timeline the most.

From a base scenario (a persona in a locality), each dimension is moved to every other value it can take while the
others stay put (a value the constraints rule out is skipped and said so); each move is evaluated and compared with
the base on three measures:

* **requirements**: how many requirements to do appear or disappear (by requirement id), and whether the move blocks
  the studio (a use not allowed);
* **fees**: the change in the known cost floor (known fees, those that may be required, and the known minimums);
* **timeline**: the change in the estimated days of the longest path through the order.

A dimension's swing is its largest change on each measure; the ranking orders dimensions by a combined score (each
swing divided by the largest swing of that measure across dimensions, summed; a move that blocks counts as the
largest requirement swing), like a tornado chart's bars.  The locality is held by default (drivers are ranked
within a place); when it is moved, the new locality takes the persona's district there.
"""
from __future__ import annotations

from .family import COUNTED, Family, FamilyError
from .run import evaluate


def _floor(out: dict) -> float:
    f = out["fees"]
    return round(f["known_required_usd"] + f["known_possible_usd"] + f["minimum_usd"], 2)


def _todo(out: dict) -> set[str]:
    return {r["id"] for r in out["requirements"] if r["status"] in COUNTED}


def swings(fam: Family, base: dict, variant: str | None = None, persona: str | None = None,
           hold: tuple[str, ...] = ("locality",)) -> dict:
    """The one-at-a-time swings around ``base`` (normalised inputs).  The dimensions in ``hold`` (by default the
    locality: the drivers are ranked within a place, since each place has its own offices and requirement ids) are
    not moved; pass ``hold=()`` to compare places too."""
    base = fam.normalise(base)
    b = evaluate(fam, base, variant)
    loc_dim = (fam.spec.get("grammar") or {}).get("locality", "locality")
    rows = []
    for d in fam.dims:
        if d.name in hold:
            continue
        alts = []
        for opt in d.options:
            if opt["code"] == fam.code_of(d.name, base[d.name]):
                continue
            if d.name != loc_dim and not d.in_scope(opt, base):
                continue                               # another place's district is no alternative here
            moved = dict(base)
            moved[d.name] = opt["value"]
            if d.name == loc_dim:                      # a new locality brings its own district (the persona's)
                theirs = {}
                if persona:
                    try:
                        theirs = fam.persona_inputs(persona, opt["value"])
                    except FamilyError:
                        theirs = {}
                for other in fam.dims:
                    if other.name == loc_dim or other.in_scope(other.option_of(moved[other.name]), moved):
                        continue
                    moved[other.name] = theirs.get(other.name) if other.name in theirs else (
                        (other.spec.get("default_by") or {}).get(opt["value"], other.spec.get("default")))
            bad = fam.violations(moved)
            if bad:
                alts.append({"code": opt["code"], "label": opt.get("label"), "possible": False, "why": bad})
                continue
            o = evaluate(fam, moved, variant)
            added, removed = sorted(_todo(o) - _todo(b)), sorted(_todo(b) - _todo(o))
            alts.append({"code": opt["code"], "label": opt.get("label"), "possible": True,
                         "requirements_delta": len(added) + len(removed), "added": added, "removed": removed,
                         "fee_delta": round(_floor(o) - _floor(b), 2),
                         "days_delta": o["order"]["timeline_days"] - b["order"]["timeline_days"],
                         "blocks": o["blocked"] and not b["blocked"], "scenario": o["scenario"]})
        ok = [a for a in alts if a["possible"]]
        rows.append({"dimension": d.name, "label": d.label, "base": fam.code_of(d.name, base[d.name]), "alternatives": alts,
                     "swing_requirements": max((a["requirements_delta"] for a in ok), default=0),
                     "swing_fees": max((abs(a["fee_delta"]) for a in ok), default=0.0),
                     "swing_days": max((abs(a["days_delta"]) for a in ok), default=0),
                     "can_block": any(a["blocks"] for a in ok)})
    top_r = max((r["swing_requirements"] for r in rows), default=0) or 1
    top_f = max((r["swing_fees"] for r in rows), default=0) or 1
    top_d = max((r["swing_days"] for r in rows), default=0) or 1
    for r in rows:
        r["score"] = round((1.0 if r["can_block"] else r["swing_requirements"] / top_r) + r["swing_fees"] / top_f
                           + r["swing_days"] / top_d, 3)
    ranked = sorted(rows, key=lambda r: (-r["score"], r["dimension"]))
    return {"family": fam.id, "base": b["scenario"], "variant": variant, "persona": persona,
            "base_counts": b["counts"], "base_fee_floor": _floor(b), "base_days": b["order"]["timeline_days"],
            "ranking": [{"dimension": r["dimension"], "label": r["label"], "score": r["score"],
                         "swing_requirements": r["swing_requirements"], "swing_fees": r["swing_fees"],
                         "swing_days": r["swing_days"], "can_block": r["can_block"]} for r in ranked],
            "dimensions": rows}


def for_persona(fam: Family, persona: str, locality: str, variant: str | None = None,
                hold: tuple[str, ...] = ("locality",)) -> dict:
    return swings(fam, fam.persona_inputs(persona, locality), variant, persona, hold)


def top(sens: dict, n: int = 3) -> list[str]:
    return [r["dimension"] for r in sens["ranking"][:n]]
