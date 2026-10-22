"""The Wikibase item shapes proposed for retirement benefits, as a dry run: nothing is sent anywhere.

A statewide system is a ``government agency`` item (``P5 instance of`` the class ``government-agency``; key
``lexflow:agency:<st>:<slug>``, the key ``graph.build`` mints for an agency) with ``authority conferred by`` -> the
section item that creates it (the section's key ``lexflow:statute:<st>:<ref>``; reference: ``quoted text``,
``source section``, ``determination method`` = matched by lexflow's software, ``retrieved``), ``applies to
jurisdiction`` -> the state, ``official website`` (reference: the page and its quote), ``Wikidata item ID`` when an
exact match exists, and ``review status`` = draft.  Which governments' employees a system can cover is not written
as claims (some 140,000 links): it stays the Census table ``pension_coverage``, and a locally administered system
would be ``part of`` its government's item after review.

A state auto-IRA program and a tax treatment are proposed as process-like items: the program with ``authority
conferred by`` -> its creating section and ``played by`` its board; the tax treatment of an income kind as a
``decision`` item of the state's tax process with the statute and the agency's page as references.  ``dry_run``
returns the items with their claims as plain dicts so a reviewer can read them; ``lexflow wikibase`` is not
called and no key is minted in ``wikibase_items``.
"""
from __future__ import annotations

from ..publish import schema as SC
from . import ground as G
from . import programs as PR


def _ref(src: dict | None) -> dict | None:
    if not G.matched(src):
        return None
    g = src["grounding"]
    if src.get("kind") == "statute":
        return {"quoted text": src["quote"][:400], "source section": SC.key_for("statute", src.get("state") or "",
                                                                                 src.get("ref") or ""),
                "determination method": "matched by lexflow's software", "retrieved": g.get("on")}
    return {"quoted text": src["quote"][:400], "source URL": src.get("url"),
            "determination method": "found on official page", "retrieved": g.get("on"),
            **({"archive URL": g.get("capture")} if g.get("capture") else {})}


def system_items(state: str) -> list[dict]:
    from . import systems as SY
    out = []
    for e in PR.system_entries(state):
        key = SC.key_for("agency", state, e["name"])
        claims = [{"property": "instance of", "value": SC.key_for("class", "government-agency")},
                  {"property": "applies to jurisdiction", "value": SC.key_for("jurisdiction", state)},
                  {"property": "review status", "value": SC.key_for("vocab", "review-status", "draft")}]
        st = e.get("statute")
        if G.matched(st):
            claims.append({"property": "authority conferred by",
                           "value": SC.key_for("statute", state, st.get("ref") or ""), "reference": _ref(st),
                           "qualifiers": {"quoted text": st["quote"][:400]}})
        if e.get("website") and G.matched(e.get("website_source")):
            claims.append({"property": "official website", "value": e["website"],
                           "reference": _ref(e["website_source"])})
        hit = SY.wikidata_of(state, e["name"]) or {}
        body_qid = (e.get("body") or {}).get("wikidata") or hit.get("qid")
        if hit.get("qid") and hit.get("searched") == e["name"]:
            claims.append({"property": "Wikidata item ID", "value": hit["qid"]})     # the system's own item
            body_qid = None
        out_body = {"name": (e.get("body") or {}).get("name"), "wikidata": body_qid}
        out.append({"key": key, "label": e["name"], "aliases": [e["short"]] if e.get("short") else [],
                    "description": f"public employee retirement system of {state.upper()}", "claims": claims,
                    "census_units": e.get("census_units") or [], "administered_by": out_body})
    return out


def auto_ira_items() -> list[dict]:
    out = []
    for p in PR.auto_ira():
        creates = next((f for f in p.get("facts") or [] if f.get("kind") == "creates"), None)
        src = next((s for s in (creates or {}).get("sources") or [] if s.get("kind") == "statute" and G.matched(s)), None)
        claims = [{"property": "applies to jurisdiction", "value": SC.key_for("jurisdiction", p["state"])},
                  {"property": "review status", "value": SC.key_for("vocab", "review-status", "draft")}]
        if src:
            claims.append({"property": "authority conferred by", "value": SC.key_for("statute", p["state"], src["ref"]),
                           "reference": _ref(src)})
        if p.get("website"):
            claims.append({"property": "official website", "value": p["website"]})
        out.append({"key": f"lexflow:program:{p['state']}:{p['id']}", "label": p["name"],
                    "description": "state-facilitated payroll IRA program" + (" (employer mandate)" if p.get("mandate")
                                                                              else " (voluntary)"),
                    "claims": claims, "board": p.get("board")})
    return out


def dry_run(states: list[str] | None = None) -> dict:
    """Every proposed item, grouped; counts of what would be written.  Nothing is sent."""
    sts = states or PR.states_with("systems")
    systems = [it for st in sts for it in system_items(st)]
    progs = auto_ira_items()
    return {"dry_run": True, "sent": 0,
            "counts": {"system_items": len(systems),
                       "with_authority_conferred_by": sum(1 for i in systems if any(
                           c["property"] == "authority conferred by" for c in i["claims"])),
                       "with_wikidata": sum(1 for i in systems if any(c["property"] == "Wikidata item ID"
                                                                     for c in i["claims"])),
                       "program_items": len(progs)},
            "systems": systems, "programs": progs}
