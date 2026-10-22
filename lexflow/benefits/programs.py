"""The benefits fixtures, loaded and grounded: statewide systems, state auto-IRA programs, the states' income-tax
treatment of retirement income, and the federal layer.

Files (``fixtures/benefits/``):

* ``systems/<st>.json``: the state's state-administered systems (``curated: true``): each with the Census units it
  groups (``census_units``), the section that creates it (``statute``, ``statute_role`` establishes | defines |
  none), the body that administers it (``body`` with its own ``source``), its official website with a quote from it
  (``website_source``), the person types it covers (``membership``), whether local employers' employees can join
  (``covers_local``), and, where researched, how to ``apply`` and ``appeal`` (each a text with sources) and office
  ``channels``.
* ``auto_ira.json``: ``programs``: one per state program, ``mandate`` true for a state law that requires employers
  without a plan to offer it, with ``facts`` (creates, board, mandate, threshold, deadline, exemption,
  self_employed, penalty, default_contribution, voluntary), each with its sources.
* ``tax/<st>.json``: ``items`` social_security, public_pension, private_pension, military_retirement, each with a
  ``treatment`` (exempt, partly_exempt, taxable, no_income_tax, unknown), lexflow's ``summary``, ``conditions`` and
  sources (the state's tax statute and the tax agency's page).
* ``federal.json``: the federal layer as official pointers (agency, page, law), applying everywhere.

Every source is matched when a file is loaded (``ground.ground_all``); a fact is shown as grounded only when one of
its sources matched, and the loaders keep the grounding report.  Loads are memoised by the file's mtime.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

from .. import config
from . import ground as G

FIX = config.ROOT / "fixtures" / "benefits"
SYSTEMS_DIR = FIX / "systems"
TAX_DIR = FIX / "tax"
AUTO_IRA = FIX / "auto_ira.json"
FEDERAL = FIX / "federal.json"

PERSON_TYPES: dict[str, str] = {
    "state_employee": "Public employee: state government",
    "teacher": "Public employee: teacher (public school)",
    "local_employee": "Public employee: local government (county, city, town)",
    "public_safety": "Public employee: public safety (police, fire, corrections, EMS)",
    "judge": "Public employee: judge",
    "private_with_plan": "Private-sector employee whose employer offers a retirement plan",
    "private_no_plan": "Private-sector employee whose employer offers no retirement plan",
    "self_employed": "Self-employed",
    "veteran": "Veteran",
    "surviving_spouse": "Surviving spouse",
    "retired": "Already retired",
}
PUBLIC = ("state_employee", "teacher", "local_employee", "public_safety", "judge")
INCOME_ITEMS = {"social_security": "Social Security", "public_pension": "Public pensions",
                "private_pension": "Private pensions, 401(k) and IRA distributions",
                "military_retirement": "Military retired pay"}
TREATMENTS = ("exempt", "partly_exempt", "taxable", "no_income_tax", "unknown")
# which income items a person type is asked about first
TAX_ITEMS_FOR = {"state_employee": ["public_pension", "social_security"], "teacher": ["public_pension", "social_security"],
                 "local_employee": ["public_pension", "social_security"], "public_safety": ["public_pension", "social_security"],
                 "judge": ["public_pension", "social_security"], "private_with_plan": ["private_pension", "social_security"],
                 "private_no_plan": ["private_pension", "social_security"], "self_employed": ["private_pension", "social_security"],
                 "veteran": ["military_retirement", "social_security"],
                 "surviving_spouse": ["social_security", "public_pension", "private_pension", "military_retirement"],
                 "retired": ["social_security", "public_pension", "private_pension", "military_retirement"]}

_MEMO: dict[str, tuple[float, object]] = {}


def _mtime(p: Path) -> float:
    try:
        return p.stat().st_mtime
    except OSError:
        return -1.0


def _load(path: Path, state: str | None = None) -> tuple[dict | None, dict | None]:
    """A fixture and its grounding report, memoised by mtime."""
    key = str(path)
    m = _mtime(path)
    hit = _MEMO.get(key)
    if hit and hit[0] == m:
        return hit[1]                                             # type: ignore[return-value]
    if m < 0:
        out = (None, None)
    else:
        doc = json.loads(path.read_text(encoding="utf-8"))
        doc = copy.deepcopy(doc)
        rep = G.ground_all(doc, state or (doc.get("state") if isinstance(doc, dict) else None))
        out = (doc, rep)
    _MEMO[key] = (m, out)
    return out


def clear() -> None:
    _MEMO.clear()


# --------------------------------------------------------------------------------------------- readers
def systems(state: str) -> dict | None:
    doc, rep = _load(SYSTEMS_DIR / f"{state}.json", state)
    if doc is not None:
        doc["grounding_report"] = {k: v for k, v in (rep or {}).items() if k != "unmatched"}
    return doc


def tax(state: str) -> dict | None:
    doc, rep = _load(TAX_DIR / f"{state}.json", state)
    if doc is not None:
        doc["grounding_report"] = {k: v for k, v in (rep or {}).items() if k != "unmatched"}
    return doc


def auto_ira(state: str | None = None) -> list[dict]:
    doc, _ = _load(AUTO_IRA)
    progs = (doc or {}).get("programs") or []
    return [p for p in progs if state is None or p.get("state") == state]


def federal() -> list[dict]:
    doc, _ = _load(FEDERAL)
    return list((doc or {}).get("programs") or [])


def states_with(kind: str) -> list[str]:
    if kind == "systems":
        return sorted(p.stem for p in SYSTEMS_DIR.glob("*.json"))
    if kind == "tax":
        return sorted(p.stem for p in TAX_DIR.glob("*.json"))
    if kind == "auto_ira":
        return sorted({p["state"] for p in auto_ira()})
    raise ValueError(kind)


# --------------------------------------------------------------------------------------------- helpers
def matched_sources(item: dict | None) -> list[dict]:
    """The item's sources that lexflow's software matched (``sources``, or the single ``source``)."""
    if not item:
        return []
    srcs = list(item.get("sources") or [])
    if item.get("source"):
        srcs.append(item["source"])
    return [s for s in srcs if G.matched(s)]


def display(src: dict | None) -> dict | None:
    """A source as a page shows it: the words, the citation or page, and lexflow's match."""
    if not src:
        return None
    g = src.get("grounding") or {}
    return {"kind": src.get("kind"), "quote": src.get("quote"), "citation": src.get("citation") or src.get("ref"),
            "ref": src.get("ref"), "url": src.get("url"), "matched": bool(g.get("matched")),
            "matched_by": g.get("by"), "checked_on": g.get("on"), "why": None if g.get("matched") else g.get("why")}


def fact_grounded(fact: dict) -> bool:
    return bool(matched_sources(fact))


def system_entries(state: str) -> list[dict]:
    doc = systems(state) or {}
    return list(doc.get("systems") or [])


def by_census_unit(state: str) -> dict[str, dict]:
    out = {}
    for s in system_entries(state):
        for u in s.get("census_units") or []:
            out[u] = s
    return out


# --------------------------------------------------------------------------------------------- stats
def stats() -> dict:
    """Coverage by state of each layer (for docs/design/retirement-benefits.md and the report)."""
    from ..municipal import states as S
    out = {"systems": {}, "auto_ira": {}, "tax": {}}
    sys_states, est, defined, sites, total, grounded_sys = 0, 0, 0, 0, 0, 0
    for st in states_with("systems"):
        ents = system_entries(st)
        if not ents:
            continue
        sys_states += 1
        n_est = sum(1 for s in ents if G.matched(s.get("statute")) and s.get("statute_role") == "establishes")
        n_def = sum(1 for s in ents if G.matched(s.get("statute")) and s.get("statute_role") != "establishes")
        n_site = sum(1 for s in ents if G.matched(s.get("website_source")))
        total += len(ents)
        est += n_est
        defined += n_def
        sites += n_site
        grounded_sys += int(n_est + n_def > 0)
        out["systems"][st] = {"systems": len(ents), "establishing_statute": n_est, "defining_statute": n_def,
                              "website": n_site}
    out["systems_summary"] = {"states": sys_states, "systems": total, "with_establishing_statute": est,
                              "with_defining_statute_only": defined, "with_website_quote": sites,
                              "states_with_a_grounded_statute": grounded_sys}
    progs = auto_ira()
    for p in progs:
        facts = p.get("facts") or []
        out["auto_ira"].setdefault(p["state"], []).append(
            {"id": p["id"], "mandate": p.get("mandate"), "status": p.get("status"),
             "facts": len(facts), "grounded_facts": sum(1 for f in facts if fact_grounded(f))})
    mand = sorted({p["state"] for p in progs if p.get("mandate")})
    out["auto_ira_summary"] = {"programs": len(progs), "mandate_states": len(mand), "mandates": mand,
                               "voluntary": sorted({p["state"] for p in progs if not p.get("mandate")})}
    tx_states, full = 0, 0
    by_treat: dict[str, dict[str, int]] = {k: {} for k in INCOME_ITEMS}
    for st in states_with("tax"):
        doc = tax(st) or {}
        items = doc.get("items") or {}
        tx_states += 1
        ok = 0
        row = {}
        for k in INCOME_ITEMS:
            it = items.get(k) or {}
            g = fact_grounded(it)
            kinds = {s.get("kind") for s in matched_sources(it)}
            row[k] = {"treatment": it.get("treatment"), "grounded": g, "statute": "statute" in kinds,
                      "page": "page" in kinds}
            ok += g
            t = it.get("treatment") or "unknown"
            by_treat[k][t] = by_treat[k].get(t, 0) + 1
        full += ok == len(INCOME_ITEMS)
        out["tax"][st] = row
    out["tax_summary"] = {"states": tx_states, "all_four_grounded": full, "by_treatment": by_treat,
                          "with_statute_and_page": sum(1 for st, r in out["tax"].items()
                                                       if all(v["statute"] and v["page"] for v in r.values()))}
    out["jurisdictions"] = len(S.NAME)
    return out
