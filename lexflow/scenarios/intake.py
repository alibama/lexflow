"""From a free-text fact pattern to a family's enumerated inputs, or to the questions still to ask.

"I want to open a glass studio with a gas furnace in district X, classes of 60 people and wine at events" becomes
one ``choice`` question per dimension for lexflow's decision model (``lexflow.extract.decide``: the options are the
dimension's values or bins, each with its label, plus ``not_said``).  An answer is accepted when the model's
confidence is at least ``threshold`` (0.8, the bar ``decide.step_kind`` uses) and it does not pick ``not_said``;
its probabilities are kept.  The chat fallback gives no confidence, so its answers are never accepted on their
own.  A short deterministic pass (``patterns``) reads what needs no model: a locality's name, a district code of
that locality, a number of people, employees or dollars, and plain words for fuel, food, alcohol and the building.
Every accepted value is tagged ``SCN`` (the asker's hypothetical) with its ``method`` (``decision-model`` or
``pattern``); whatever is left becomes a question for the asker, with the model's best guess when it had one.

Privacy: the text is used here and returned to the caller, and nothing else keeps it.  The decision cache stores a
hash of it, never the words; a scenario recorded from it holds only the enumerated values and is marked
``local_only`` (never synced, never published).
"""
from __future__ import annotations

import re
from typing import Any

from .family import Family

THRESHOLD = 0.8
NOT_SAID = "not_said"
NUM = r"(\d[\d,]*(?:\.\d+)?)\s*(k|thousand)?"


def questions(fam: Family) -> dict:
    """One choice question per dimension, its options the value codes with their labels plus ``not_said``."""
    out = {}
    for d in fam.dims:
        crit = {o["code"]: (o.get("label") or o["code"]) for o in d.options}
        crit[NOT_SAID] = "The text does not say"
        out[d.name] = {"type": "choice", "instructions": f"{d.label}: which option does the text describe?",
                       "criteria": crit}
    return out


def _num(m) -> float | int:
    v = float(m.group(1).replace(",", ""))
    v = v * 1000 if m.group(2) else v
    return int(v) if v == int(v) else v


def patterns(fam: Family, text: str) -> dict[str, dict]:
    """What a plain reading of the text settles: dimension -> {code, evidence}."""
    t = " " + re.sub(r"\s+", " ", text) + " "
    low = t.lower()
    out: dict[str, dict] = {}
    loc_dim = (fam.spec.get("grammar") or {}).get("locality", "locality")
    hits = [o for o in fam.dim[loc_dim].options
            if re.search(r"\b" + re.escape(o["value"]) + r"\b", low) or re.search(r"\b" + re.escape(o["label"].lower()) + r"\b", low)]
    if len(hits) == 1:
        out[loc_dim] = {"code": hits[0]["code"], "evidence": hits[0]["value"]}
    if "district" in fam.dim:
        loc = fam.dim[loc_dim].by_code(out[loc_dim]["code"])["value"] if loc_dim in out else None
        found = []
        for o in fam.dim["district"].options:
            if loc and loc not in ((o.get("scope") or {}).get(loc_dim) or [loc]):
                continue
            code = str(o["value"])
            if "-review" in code:
                continue
            if re.search(r"(?<![A-Za-z0-9-])" + re.escape(code) + r"(?![A-Za-z0-9-])", t):
                found.append(o)
        if len({f["code"] for f in found}) == 1:
            out["district"] = {"code": found[0]["code"], "evidence": found[0]["value"]}
    m = re.search(NUM + r"\s*(?:people|students|participants|guests|attendees|visitors|seats)", low)
    if m and "occupants" in fam.dim:
        out["occupants"] = {"code": fam.code_of("occupants", _num(m)), "value": _num(m), "evidence": m.group(0).strip()}
    elif re.search(r"\bno (?:classes|public|events)\b", low) and "occupants" in fam.dim:
        out["occupants"] = {"code": fam.code_of("occupants", 0), "value": 0, "evidence": "no classes or public"}
    m = re.search(NUM + r"\s*(?:employees|staff|workers|assistants)", low)
    if m and "employees" in fam.dim:
        out["employees"] = {"code": fam.code_of("employees", _num(m)), "value": _num(m), "evidence": m.group(0).strip()}
    elif re.search(r"\b(?:no employees|just me|by myself|on my own)\b", low) and "employees" in fam.dim:
        out["employees"] = {"code": fam.code_of("employees", 0), "value": 0, "evidence": "no employees"}
    m = re.search(r"\$\s?" + NUM + r"[^.]{0,40}?(?:receipts|revenue|sales|turnover|gross)", low) or \
        re.search(r"(?:receipts|revenue|sales|turnover|gross)[^.$]{0,40}?\$\s?" + NUM, low)
    if m and "receipts" in fam.dim:
        out["receipts"] = {"code": fam.code_of("receipts", _num(m)), "value": _num(m), "evidence": m.group(0).strip()}
    words = {
        "fuel": [(r"\bpropane\b|\blp[- ]?gas\b", "LP"), (r"\bnatural gas\b|\bgas[- ](?:fired )?furnace\b|\bgas glory", "NG"),
                 (r"\belectric (?:kilns? |furnace )?only\b|\bno gas\b", "EL")],
        "food": [(r"\bcaf[eé]\b|\bkitchen\b|\bsandwich|\bprepared food\b|\bcooking\b", "FK"),
                 (r"\bpackaged\b|\bsnacks?\b|\bbottled\b|\bsealed\b", "FP"), (r"\bno food\b", "F0")],
        "alcohol": [(r"\b(?:every|each|weekly|monthly|regular(?:ly)?)\b[^.]{0,30}\b(?:wine|beer|alcohol|drinks)\b|"
                     r"\b(?:wine|beer|alcohol)\b[^.]{0,30}\b(?:nights|events|evenings|every|weekly|monthly|regular(?:ly)?)\b", "WR"),
                    (r"\b(?:one[- ]off|one night|single event|opening (?:party|night))\b", "W1"), (r"\bno (?:alcohol|wine|beer)\b", "W0")],
        "building": [(r"\bnew (?:building|build)\b|\bbuild (?:a|my) (?:own )?(?:new )?(?:studio|building|shop)\b|\bconstruct", "NB"),
                     (r"\bexisting (?:building|space|shop|warehouse)\b|\blease\b|\brent(?:ing)?\b|\bwarehouse\b|\bstorefront\b", "EX")],
        "historic": [(r"\bhistoric district\b", "H1")],
        "sign": [(r"\bno sign\b", "S0"), (r"\bsign\b", "S1")],
        "oxygen": [(r"\bno oxygen\b", "O2N")],
    }
    for dim, rules in words.items():
        if dim not in fam.dim or dim in out:
            continue
        got = [(code, re.search(rx, low).group(0)) for rx, code in rules if re.search(rx, low)]
        codes = {c for c, _ in got}
        if dim == "fuel" and codes == {"LP", "NG"}:
            continue                                     # both named: ask
        if dim == "alcohol" and "WR" in codes:
            codes = {"WR"}
        if len(codes) == 1:
            code = codes.pop()
            out[dim] = {"code": code, "evidence": next(e for c, e in got if c == code)}
    return out


def intake(fam: Family, text: str, decider: Any = None, threshold: float = THRESHOLD, use_model: bool = True,
           use_patterns: bool = True) -> dict:
    """Map ``text`` to inputs.  Returns ``{"inputs": {dim: code}, "methods": {dim: {tag, method, p,
    probabilities, evidence}}, "ask": [{dimension, label, options, best_guess, p}], "complete", "local_only": True,
    "model"}``.  ``decider`` is a ``lexflow.extract.decide.Decider`` (made here when ``use_model`` and none is
    given); a model or server that fails leaves every dimension to the patterns and the questions."""
    from ..extract import decide as D
    answers, model, error = {}, None, None
    if use_model:
        try:
            dec = decider or D.Decider()
            # only a decision model: the chat fallback gives no confidence, so none of its answers could be accepted,
            # and asking it would load a chat model for nothing
            if getattr(dec, "_answer", None) is not None or dec.backend["kind"] == "decision":
                res = dec.decide({"Fact pattern": text}, questions(fam))
                answers, model = res.get("answers") or {}, res.get("model")
            else:
                error = "no decision model is pulled here; the text was read by the patterns alone"
        except Exception as e:                          # noqa: BLE001 - no model: patterns and questions only
            error = f"{type(e).__name__}: {str(e)[:200]}"
    pat = patterns(fam, text) if use_patterns else {}
    inputs, methods, ask = {}, {}, []
    for d in fam.dims:
        a = answers.get(d.name) or {}
        choice, conf = a.get("choice"), a.get("confidence")
        valid = {o["code"] for o in d.options}
        if choice in valid and conf is not None and conf >= threshold:
            inputs[d.name] = choice
            methods[d.name] = {"tag": "SCN", "method": "decision-model", "p": round(float(conf), 3),
                               "probabilities": a.get("probabilities") or {}}
            continue
        if d.name in pat:
            inputs[d.name] = pat[d.name].get("value", pat[d.name]["code"])
            methods[d.name] = {"tag": "SCN", "method": "pattern", "p": None, "evidence": pat[d.name]["evidence"]}
            continue
        ask.append({"dimension": d.name, "label": d.label,
                    "options": [{"code": o["code"], "label": o.get("label")} for o in d.options],
                    "best_guess": choice if choice in valid else None, "p": conf,
                    "default": d.spec.get("default"),
                    "why": "the decision model was not sure" if choice in valid else "the text does not say"})
    # a value the constraints rule out (a district of another locality) is a question too
    if inputs:
        partial = {}
        for k, v in inputs.items():
            try:
                partial[k] = fam.dim[k].canonical(v)
            except Exception:                           # noqa: BLE001
                continue
        for bad in fam.violations(partial):
            dim = bad.split("=", 1)[0].split(":", 1)[0]
            if dim in inputs and dim in fam.dim:
                inputs.pop(dim)
                methods.pop(dim, None)
                ask.append({"dimension": dim, "label": fam.dim[dim].label, "options": [
                    {"code": o["code"], "label": o.get("label")} for o in fam.dim[dim].options
                    if fam.dim[dim].in_scope(o, partial)], "why": f"out of scope: {bad}"})
    return {"inputs": inputs, "methods": methods, "ask": ask, "complete": not ask, "local_only": True,
            "model": model, "model_error": error, "threshold": threshold}


def with_defaults(fam: Family, result: dict) -> tuple[dict, dict]:
    """Fill the questions left with the family's defaults (tagged ASM: lexflow's assumption, not the asker's)."""
    inputs, methods = dict(result["inputs"]), dict(result["methods"])
    loc_dim = (fam.spec.get("grammar") or {}).get("locality", "locality")
    for q in result["ask"]:
        d = fam.dim[q["dimension"]]
        v = d.spec.get("default")
        if v is None and d.spec.get("default_by"):
            loc = inputs.get(loc_dim) or fam.dim[loc_dim].spec.get("default")
            loc = fam.dim[loc_dim].by_code(loc)["value"] if isinstance(loc, str) and loc.isupper() else loc
            v = d.spec["default_by"].get(loc)
        if v is not None:
            inputs[d.name] = v
            methods[d.name] = {"tag": "ASM", "method": "family default", "p": None}
    return inputs, methods
