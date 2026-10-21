"""The scenario space of a family: every combination, or a pairwise (all-pairs) covering set, with constraint pruning.

A family's scenario space is the product of its dimensions' small vocabularies, less the combinations its
constraints rule out (a value out of scope, such as a Charlottesville district in Staunton, or alcohol with neither
events nor food).  ``count`` walks the whole space depth first with pruning; ``all_combinations`` yields it.

Districts are many and the tables never read a district itself, only its derived class (``district_class``), so two
districts of one locality whose class agrees under the baseline and under every variant give the same output for
every table: ``by_class`` keeps one representative of each such equivalence class (equivalence partitioning), and
``tests/test_hypotheticals.py`` checks that swapping a district for another of its class never changes an output.

``pairwise`` is a deterministic greedy all-pairs generator (in the manner of AETG and IPOG): every pair of values of
two dimensions that some valid scenario can hold appears in at least one scenario of the set, and every scenario
satisfies the constraints.
"""
from __future__ import annotations

from itertools import combinations
from typing import Iterator

from .family import Family


def _codes(fam: Family, name: str, by_class: bool, variants: tuple[str, ...] = ()) -> list[str]:
    d = fam.dim[name]
    if not by_class or not any(dv["from"] == name for dv in fam.derived):
        return [o["code"] for o in d.options]
    if any(name in [i["name"] for i in t["inputs"]] for t in fam.tables):
        return [o["code"] for o in d.options]          # a table reads the value itself: no partition
    return [o["code"] for o in representatives(fam, name, variants or tuple(fam.variants))]


def signature(fam: Family, name: str, option: dict, variants: tuple[str, ...]) -> tuple:
    """What the tables can tell apart about a value of a dimension that feeds derived inputs: its scope and its
    derived attributes under the baseline and under each variant (overrides apply whatever their other conditions)."""
    sig = [tuple(sorted((k, tuple(v) if isinstance(v, list) else v) for k, v in (option.get("scope") or {}).items()))]
    for dv in fam.derived:
        if dv["from"] != name:
            continue
        sig.append(option.get(dv["attribute"]))
        for vid in variants:
            got = option.get(dv["attribute"])
            for ov in fam.variants[vid].get("class_overrides") or []:
                if ov["dimension"] != name or ov["attribute"] != dv["name"]:
                    continue
                scope_ok = all(option.get("scope", {}).get(k) is None or
                               set(w if isinstance(w, list) else [w]) & set(option["scope"][k])
                               for k, w in (ov.get("when") or {}).items() if k in (option.get("scope") or {}))
                if scope_ok:
                    got = ov["map"].get(str(option["value"]), ov["map"].get("*", got))
            sig.append(got)
    return tuple(sig)


def representatives(fam: Family, name: str, variants: tuple[str, ...] = ()) -> list[dict]:
    """One value per equivalence class of ``signature`` (the first in file order)."""
    seen, out = set(), []
    for o in fam.dim[name].options:
        s = signature(fam, name, o, variants)
        if s not in seen:
            seen.add(s)
            out.append(o)
    return out


def classes(fam: Family, name: str, variants: tuple[str, ...] = ()) -> dict[str, list[str]]:
    """Representative code -> every code in its class."""
    groups: dict[tuple, list[str]] = {}
    for o in fam.dim[name].options:
        groups.setdefault(signature(fam, name, o, variants), []).append(o["code"])
    return {v[0]: v for v in groups.values()}


def domains(fam: Family, by_class: bool = True, variants: tuple[str, ...] = ()) -> dict[str, list[str]]:
    return {s: _codes(fam, s, by_class, variants) for s in fam.slots}


def _value(fam: Family, name: str, code: str):
    return fam.dim[name].by_code(code)["value"]


def all_combinations(fam: Family, by_class: bool = False, variants: tuple[str, ...] = ()) -> Iterator[dict]:
    """Every valid scenario (inputs as canonical values), depth first with pruning."""
    doms = domains(fam, by_class, variants)
    slots = list(fam.slots)

    def walk(i: int, partial: dict):
        if i == len(slots):
            yield dict(partial)
            return
        name = slots[i]
        for code in doms[name]:
            partial[name] = _value(fam, name, code)
            if not fam.violations(partial):
                yield from walk(i + 1, partial)
            del partial[name]
    yield from walk(0, {})


def count(fam: Family, by_class: bool = False, variants: tuple[str, ...] = ()) -> dict:
    """The size of the space: the raw product of the vocabularies and the number of valid scenarios."""
    doms = domains(fam, by_class, variants)
    raw = 1
    for v in doms.values():
        raw *= len(v)
    n = sum(1 for _ in all_combinations(fam, by_class, variants))
    return {"product": raw, "valid": n, "by_class": by_class, "domains": {k: len(v) for k, v in doms.items()}}


def feasible(fam: Family, assign: dict[str, str], doms: dict[str, list[str]]) -> bool:
    """Whether some valid scenario holds these codes (depth first, pruned by the constraints)."""
    slots = [s for s in fam.slots if s not in assign]
    vals = {k: _value(fam, k, c) for k, c in assign.items()}
    if fam.violations(vals):
        return False

    def walk(i: int) -> bool:
        if i == len(slots):
            return True
        name = slots[i]
        for code in doms[name]:
            vals[name] = _value(fam, name, code)
            if not fam.violations(vals) and walk(i + 1):
                del vals[name]
                return True
            del vals[name]
        return False
    return walk(0)


def valid_pairs(fam: Family, doms: dict[str, list[str]]) -> set:
    slots = list(fam.slots)
    out = set()
    for a, b in combinations(slots, 2):
        for ca in doms[a]:
            for cb in doms[b]:
                if feasible(fam, {a: ca, b: cb}, doms):
                    out.add(((a, ca), (b, cb)))
    return out


def pairwise(fam: Family, by_class: bool = True, variants: tuple[str, ...] = ()) -> list[dict]:
    """A covering set: every pair of values of two dimensions that a valid scenario can hold, in at least one
    scenario of the set."""
    doms = domains(fam, by_class, variants)
    slots = list(fam.slots)
    idx = {s: i for i, s in enumerate(slots)}

    def ok(assign: dict) -> bool:
        return feasible(fam, assign, doms)

    uncovered = valid_pairs(fam, doms)
    order = sorted(slots, key=lambda s: (-len(doms[s]), idx[s]))
    tests: list[dict] = []
    while uncovered:
        (a, ca), (b, cb) = min(uncovered, key=lambda p: (idx[p[0][0]], p[0][1], idx[p[1][0]], p[1][1]))
        test = {a: ca, b: cb}
        complete = True
        for k in order:
            if k in test:
                continue
            best, gain_best = None, -1
            for c in doms[k]:
                cand = {**test, k: c}
                if not ok(cand):
                    continue
                gain = 0
                for m, cm in test.items():
                    p = ((k, c), (m, cm)) if idx[k] < idx[m] else ((m, cm), (k, c))
                    gain += p in uncovered
                if gain > gain_best:
                    best, gain_best = c, gain
            if best is None:
                complete = False
                break
            test[k] = best
        if not complete:
            uncovered.discard(((a, ca), (b, cb)))       # no valid scenario holds this pair
            continue
        covered = {(((x, test[x]), (y, test[y])) if idx[x] < idx[y] else ((y, test[y]), (x, test[x])))
                   for x, y in combinations(test, 2)}
        uncovered -= covered
        tests.append({k: _value(fam, k, test[k]) for k in slots})
    return tests


def pair_coverage(fam: Family, tests: list[dict], by_class: bool = True, variants: tuple[str, ...] = ()) -> dict:
    """How many valid pairs the tests cover (a check of ``pairwise``)."""
    doms = domains(fam, by_class, variants)
    slots = list(fam.slots)
    valid = valid_pairs(fam, doms)
    got = set()
    for t in tests:
        codes = {k: fam.code_of(k, v) for k, v in t.items()}
        for a, b in combinations(slots, 2):
            got.add(((a, codes[a]), (b, codes[b])))
    return {"valid_pairs": len(valid), "covered": len(valid & got), "missing": sorted(valid - got)[:20]}
