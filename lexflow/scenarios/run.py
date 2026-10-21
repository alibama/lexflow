"""Evaluate a scenario across a family's decision tables, and record the run.

``evaluate(family, inputs, variant)`` is deterministic: the same inputs, tables and engine give the same output,
with no model call anywhere.  It returns the requirements that apply (each with its office, status, fee, deadline,
the citing quote and lexflow's match of it), the order to do them in (a topological sort of the family's ordering
rules over the requirements present and the milestones, each edge with the quote that makes it), a timeline
estimate (the longest path of lead days through that order), the fees (known fees, fees with only a minimum
known, fees not known, taxes and other charges, apart), where a refusal can be appealed, and the trace of which
rules fired in which table.

``record`` stores the scenario (only its enumerated values) and the run, keyed by the scenario id and the tables'
content hash, so a stored run always says which tables made it and a changed table gives a new run.
"""
from __future__ import annotations

import hashlib
import json
import time
from typing import Any

from ..store import db
from . import dmn
from .family import COUNTED, MILESTONES, Family, FamilyError

ENGINE = f"lexflow.scenarios.run/1 ({dmn.ENGINE})"
MILESTONE_STAGE = {"m:lease": 1.5, "m:construction": 2.5, "m:occupancy": 4.5, "m:opening": 6.5}
POSSIBLE = ("may be required", "ask first")
IMPERATIVE = {"Keep", "Follow", "Hire", "Pay", "Tell", "Register", "Check", "Ask", "Design", "Plan"}


# --------------------------------------------------------------------------------------------- display
def _display(src: dict | None) -> dict | None:
    """A source as a page may show it: the quote, or for a site whose terms forbid reposting (or a withheld quote)
    lexflow's paraphrase and the reason, never the words."""
    if not src:
        return None
    from ..municipal import quotes as Q
    g = src.get("grounding") or {}
    out = {"citation": src.get("citation"), "url": src.get("url"), "from": src.get("from"),
           "matched": bool(g.get("matched")), "matched_by": g.get("by"), "checked_on": g.get("on")}
    pol = Q.policy(src.get("url"))
    if src.get("quote") and (not pol or src.get("free")):
        out["quote"] = src["quote"]
        if pol:
            out["free_words"] = src["free"]
    else:
        out["paraphrase"] = src.get("paraphrase")
        out["withheld"] = True
        out["why_withheld"] = Q.reprint_note(pol) if pol else None
    return out


def office_of(fam: Family, office_id: str, locality: str | None) -> dict:
    o = fam.offices.get(office_id) or {}
    if o.get("by_locality"):
        target = o["by_locality"].get(locality)
        if target:
            inner = fam.offices.get(target) or {}
            return {"id": target, "label": inner.get("label") or o.get("label"), "url": inner.get("url")}
    return {"id": office_id, "label": o.get("label") or office_id, "url": o.get("url")}


def _fee(rule: dict) -> dict:
    f = dict(rule.get("fee") or {})
    kind = f.get("kind", "fee")
    grounded = f.get("grounded", True)
    if f.get("none"):
        return {"kind": "none", "text": "no fee", "known": True, "usd": 0.0}
    out = {"kind": kind, "rule": f.get("rule"), "known": False, "usd": None, "min_usd": None, "grounded": grounded}
    if f.get("usd") is not None and grounded:
        out.update(usd=float(f["usd"]), known=True)
    elif f.get("min_usd") is not None and grounded:
        out.update(min_usd=float(f["min_usd"]))
    out["text"] = (f"${out['usd']:,.2f}" if out["known"] else
                   f"at least ${out['min_usd']:,.2f}" if out["min_usd"] is not None else "not known") + (
        f" ({f['rule']})" if f.get("rule") else "")
    return out


def _level(table: dict, rule: dict) -> str:
    """``local`` when the rule names a locality, else ``state`` (the rule holds wherever the family applies)."""
    if rule.get("level"):
        return rule["level"]
    names = [i["name"] for i in table.get("inputs") or []]
    if "locality" in names and (rule.get("when") or ["-"] * len(names))[names.index("locality")].strip() not in ("", "-"):
        return "local"
    return "state"


def requirement(fam: Family, table: dict, rule: dict, out: dict, locality: str) -> dict:
    assumptions = list(rule.get("assumptions") or [])
    return {"id": out.get("requirement"), "rule": rule.get("id"), "table": table["id"], "status": out.get("status"),
            "title": rule.get("title"), "office": office_of(fam, rule.get("office"), locality), "fee": _fee(rule),
            "deadline": rule.get("deadline"), "deadline_source": _display(rule.get("deadline_source")),
            "lead_days": rule.get("lead_days"), "tags": list(rule.get("tags") or []), "stage": rule.get("stage", 3),
            "tag": rule.get("tag"), "assumptions": assumptions, "level": _level(table, rule),
            "source": _display(rule.get("source")), "fee_source": _display(rule.get("fee_source")),
            "note": rule.get("note")}


# ------------------------------------------------------------------------------------------------ order
def _applies(cond: dict | None, inputs: dict) -> bool:
    for k, allowed in (cond or {}).items():
        allowed = allowed if isinstance(allowed, list) else [allowed]
        if inputs.get(k) not in allowed:
            return False
    return True


def order_of(fam: Family, reqs: list[dict], inputs: dict) -> dict:
    """The order: requirements (to do, or blocked) and milestones, sorted so that every ordering rule whose ends
    are both present holds; ties by stage, then table and rule order.  Returns ``{"steps", "edges",
    "timeline_days", "critical_path", "cycle"}``."""
    todo = [r for r in reqs if r["status"] in COUNTED or r["status"] == "blocked"]
    nodes: dict[str, dict] = {}
    for i, r in enumerate(todo):
        nodes[r["id"]] = {"id": r["id"], "kind": "requirement", "title": r["title"], "office": r["office"]["label"],
                          "stage": r["stage"], "rank": i, "lead": r.get("lead_days") or 0, "tags": set(r["tags"])}
    labels = {m["id"]: m["label"] for m in fam.spec.get("milestones") or []}

    def members(tag: str) -> list[str]:
        if tag in MILESTONES:
            if tag not in nodes:
                nodes[tag] = {"id": tag, "kind": "milestone", "title": labels.get(tag, tag), "office": None,
                              "stage": MILESTONE_STAGE.get(tag, 9), "rank": 10_000 + MILESTONES.index(tag), "lead": 0,
                              "tags": {tag}}
            return [tag]
        return [n for n, v in nodes.items() if v["kind"] == "requirement" and tag in v["tags"]]

    edges = []
    for o in fam.order:
        if not _applies(o.get("when"), inputs):
            continue
        firsts = [n for n in nodes if nodes[n]["kind"] == "requirement" and o["first"] in nodes[n]["tags"]] \
            if o["first"] not in MILESTONES else None
        thens = [n for n in nodes if nodes[n]["kind"] == "requirement" and o["then"] in nodes[n]["tags"]] \
            if o["then"] not in MILESTONES else None
        # a milestone joins the order only when a requirement on the other end is present (or both are milestones)
        if firsts == [] or thens == []:
            continue
        a = members(o["first"]) if firsts is None else firsts
        b = members(o["then"]) if thens is None else thens
        src = _display(o.get("source"))
        why = o.get("why") or (fam.assumptions.get(o.get("assumption")) or {}).get("text")
        for x in a:
            for y in b:
                if x != y:
                    edges.append({"before": x, "after": y, "rule": o["id"], "tag": o.get("tag"),
                                  "assumption": o.get("assumption"), "why": why, "source": src})
    # milestones in their natural order when more than one is present
    ms = [m for m in MILESTONES if m in nodes]
    for x, y in zip(ms, ms[1:]):
        if not any(e["before"] == x and e["after"] == y for e in edges):
            edges.append({"before": x, "after": y, "rule": "milestones", "tag": "ASM", "assumption": None,
                          "why": "milestones in their natural order", "source": None})
    preds: dict[str, list[dict]] = {n: [] for n in nodes}
    succ: dict[str, set] = {n: set() for n in nodes}
    for e in edges:
        preds[e["after"]].append(e)
        succ[e["before"]].add(e["after"])
    indeg = {n: len({e["before"] for e in preds[n]}) for n in nodes}
    ready = sorted([n for n in nodes if indeg[n] == 0], key=lambda n: (nodes[n]["stage"], nodes[n]["rank"]))
    seq, cycle = [], False
    while ready:
        n = ready.pop(0)
        seq.append(n)
        for m in sorted(succ[n]):
            indeg[m] -= 1
            if indeg[m] == 0:
                ready.append(m)
        ready.sort(key=lambda k: (nodes[k]["stage"], nodes[k]["rank"]))
    if len(seq) < len(nodes):                    # a cycle: put the rest in stage order and say so
        cycle = True
        seq += sorted([n for n in nodes if n not in seq], key=lambda k: (nodes[k]["stage"], nodes[k]["rank"]))
    finish, best = {}, {}
    for n in seq:
        start = max((finish.get(e["before"], 0) for e in preds[n]), default=0)
        finish[n] = start + nodes[n]["lead"]
        best[n] = max(preds[n], key=lambda e: finish.get(e["before"], 0))["before"] if preds[n] else None
    end = max(finish, key=finish.get) if finish else None
    path = []
    while end:
        path.append(end)
        end = best.get(end)
    steps = []
    for i, n in enumerate(seq, 1):
        v = nodes[n]
        after = []
        for e in preds[n]:
            s = e.get("source") or {}
            after.append({"node": e["before"], "rule": e["rule"], "tag": e.get("tag"),
                          "because": s.get("quote") or s.get("paraphrase") or e.get("why"),
                          "citation": s.get("citation"), "url": s.get("url"), "assumption": e.get("assumption")})
        steps.append({"n": i, "id": n, "kind": v["kind"], "title": v["title"], "office": v["office"],
                      "lead_days": v["lead"] or None, "starts_after_days": finish[n] - v["lead"], "after": after})
    return {"steps": steps, "edges": len(edges), "timeline_days": max(finish.values(), default=0),
            "critical_path": list(reversed(path)), "cycle": cycle}


# ------------------------------------------------------------------------------------------------- fees
def fees_of(reqs: list[dict]) -> dict:
    """Known fees (exact amounts) for what is to be done, those that depend on an official's decision apart, fees
    with only a minimum known, fees not known (listed), and taxes and other charges (not fees)."""
    out = {"label": "known fees", "known_required_usd": 0.0, "known_possible_usd": 0.0, "minimum_usd": 0.0,
           "known": [], "minimums": [], "unknown": [], "taxes": [], "charges": []}
    for r in reqs:
        if r["status"] not in COUNTED:
            continue
        f = r["fee"]
        item = {"requirement": r["id"], "title": r["title"], "office": r["office"]["label"], "status": r["status"],
                "text": f.get("text")}
        if f["kind"] == "none":
            continue
        if f["kind"] == "tax":
            out["taxes"].append(item)
            continue
        if f["kind"] == "charge":
            out["charges"].append(item)
            continue
        if f["known"]:
            out["known"].append({**item, "usd": f["usd"]})
            if r["status"] in POSSIBLE:
                out["known_possible_usd"] += f["usd"]
            else:
                out["known_required_usd"] += f["usd"]
        elif f.get("min_usd") is not None:
            out["minimums"].append({**item, "min_usd": f["min_usd"]})
            out["minimum_usd"] += f["min_usd"]
        else:
            out["unknown"].append(item)
    for k in ("known_required_usd", "known_possible_usd", "minimum_usd"):
        out[k] = round(out[k], 2)
    out["summary"] = (f"Known fees: ${out['known_required_usd']:,.2f}"
                      + (f", plus ${out['known_possible_usd']:,.2f} if the officials require the items that may be "
                         f"required" if out["known_possible_usd"] else "")
                      + (f"; at least ${out['minimum_usd']:,.2f} more in {len(out['minimums'])} fees with only a "
                         f"minimum known" if out["minimums"] else "")
                      + (f"; {len(out['unknown'])} fees not known: " + "; ".join(u["title"] for u in out["unknown"])
                         if out["unknown"] else "; no fee left unknown")
                      + (f". Taxes and other charges are listed apart ({len(out['taxes']) + len(out['charges'])})."
                         if out["taxes"] or out["charges"] else "."))
    return out


# ---------------------------------------------------------------------------------------------- evaluate
def evaluate(fam: Family, inputs: dict, variant: str | None = None, tables: list[str] | None = None) -> dict:
    """One scenario through the family's tables (or the ``tables`` named).  Raises FamilyError for an input the
    family does not know or a combination its constraints rule out."""
    t0 = time.perf_counter()
    inputs = fam.normalise(inputs)
    bad = fam.violations(inputs)
    if bad:
        raise FamilyError(f"the scenario breaks the family's constraints: {', '.join(bad)}")
    data = fam.data(inputs, variant)
    loc_dim = (fam.spec.get("grammar") or {}).get("locality", "locality")
    loc = inputs.get(loc_dim)
    reqs, trace, seen = [], [], set()
    for t in fam.tables:
        if tables and t["id"] not in tables:
            continue
        res = dmn.evaluate(t, data)
        trace.append({"table": t["id"], "hit_policy": res["hit_policy"],
                      "fired": [t["rules"][h]["id"] for h in res["hits"]]})
        for h, out in zip(res["hits"], res["outputs"]):
            rule = t["rules"][h]
            if out.get("requirement") in seen:
                continue
            seen.add(out.get("requirement"))
            reqs.append(requirement(fam, t, rule, out, loc))
    order = order_of(fam, reqs, inputs)
    pos = {s["id"]: s["n"] for s in order["steps"]}
    for r in reqs:
        r["order"] = pos.get(r["id"])
    reqs.sort(key=lambda r: (r["order"] is None, r["order"] or 0))
    used_tables = {r["table"] for r in reqs if r["status"] in COUNTED or r["status"] == "blocked"}
    appeals = [{"table": a["table"], "to": a["to"], "deadline": a.get("deadline"), "source": _display(a.get("source"))}
               for a in fam.appeals if a["table"] in used_tables and _applies(a.get("when"), inputs)]
    asm = set()
    for r in reqs:
        asm.update(r["assumptions"])
    in_tags = {}
    for name in fam.slots:
        opt = fam.dim[name].option_of(inputs[name])
        in_tags[name] = {"value": inputs[name], "code": opt["code"], "label": opt.get("label"),
                         "tag": opt.get("tag") or "SRC", "assumptions": opt.get("assumptions") or [],
                         **({"class": opt["class"]} if "class" in opt else {})}
        asm.update(opt.get("assumptions") or [])
    if variant:
        asm.add(fam.variants[variant].get("assumption"))
    sid = fam.scenario_id(inputs, variant)
    counted = [r for r in reqs if r["status"] in COUNTED]
    return {"family": fam.id, "version": fam.version, "tables_hash": fam.content_hash(), "engine": ENGINE,
            "scenario": sid, "variant": variant, "kind": "policy" if variant else "fact", "inputs": in_tags,
            "derived": {k: v for k, v in data.items() if k not in inputs},
            "blocked": any(r["status"] == "blocked" for r in reqs),
            "requirements": reqs, "counts": {"to_do": len(counted),
                                             "required": sum(1 for r in reqs if r["status"] == "required"),
                                             "possible": sum(1 for r in reqs if r["status"] in POSSIBLE),
                                             "not_required": sum(1 for r in reqs if r["status"] == "not required")},
            "order": order, "fees": fees_of(reqs), "appeals": appeals,
            "assumptions": sorted(a for a in asm if a), "trace": trace,
            "ms": round((time.perf_counter() - t0) * 1000, 2)}


def text(out: dict) -> str:
    """The output as plain text: every requirement names the office it comes from."""
    lines = [f"Scenario {out['scenario']} ({out['family']} {out['version']}): computed from grounded decision "
             f"tables, not reviewed by a person, not legal advice"]
    if out["blocked"]:
        lines.append("BLOCKED: " + "; ".join(r["title"] for r in out["requirements"] if r["status"] == "blocked"))
    verbs = {"required": "You need", "recommended": "Recommended: you need", "may be required": "You may need",
             "blocked": "Blocked: you need"}
    k = 0
    for s in out["order"]["steps"]:
        if s["kind"] == "milestone":
            lines.append(f"     -- {s['title']}")
            continue
        k += 1
        r = next(x for x in out["requirements"] if x["id"] == s["id"])
        if r["status"] == "ask first":
            lines.append(f"{k:>3}. Ask first ({r['office']['label']}): {r['title']} [{r['fee']['text']}]")
        elif (r["title"] or "").split(" ", 1)[0] in IMPERATIVE:     # "Keep slurry out of the drains": a duty
            lines.append(f"{k:>3}. {r['title']} (office: {r['office']['label']}) [{r['status']}; {r['fee']['text']}]")
        else:
            lines.append(f"{k:>3}. {verbs.get(r['status'], 'You need')} {r['title']} from {r['office']['label']} "
                         f"[{r['status']}; {r['fee']['text']}]")
    nr = [r for r in out["requirements"] if r["status"] == "not required"]
    if nr:
        lines.append("Not required: " + "; ".join(f"{r['title']} ({r['office']['label']})" for r in nr))
    lines.append(out["fees"]["summary"])
    return "\n".join(lines)


# ------------------------------------------------------------------------------------------------ storage
def run_id(out: dict) -> str:
    h = hashlib.sha256(f"{out['scenario']}|{out['tables_hash']}|{out['engine']}".encode()).hexdigest()[:16]
    return f"{out['family']}:{h}"


def save_family(con, fam: Family) -> None:
    """The family, its personas and assumptions in the shared tables (the committed form of the tables only)."""
    st = fam.spec.get("state") or "va"
    db.upsert(con, "families", [{"id": fam.id, "state": st, "title": fam.spec.get("title"),
                                 "questions": json.dumps(fam.spec.get("serves") or {}), "version": fam.version,
                                 "dimensions": json.dumps(fam.spec["dimensions"], ensure_ascii=False),
                                 "tables": json.dumps(fam.tables, ensure_ascii=False),
                                 "content_hash": fam.content_hash(),
                                 "grounding": json.dumps({**(fam.spec.get("grounding") or {}),
                                                          "dropped": fam.dropped}, ensure_ascii=False)}])
    db.upsert(con, "personas", [{"family": fam.id, "id": p["id"], "state": st, "label": p.get("label"),
                                 "inputs": json.dumps(p["inputs"], ensure_ascii=False), "note": p.get("note")}
                                for p in fam.personas.values()])
    db.upsert(con, "assumptions", [{"family": fam.id, "id": a["id"], "state": st, "text": a.get("text"),
                                    "direction": a.get("direction"), "range": a.get("range")}
                                   for a in fam.assumptions.values()])
    con.commit()


def scenario_row(fam: Family, out: dict, persona: str | None = None, created_by: str = "cli",
                 local_only: bool = False, method: dict | None = None) -> dict:
    """The scenario as stored: only its enumerated values, each with its tag (SCN for an asker's own value)."""
    ins = {}
    for k, v in out["inputs"].items():
        ins[k] = {"code": v["code"], "value": v["value"],
                  "tag": (method or {}).get(k, {}).get("tag") or ("SCN" if created_by in ("intake", "api") else v["tag"]),
                  **({"method": (method or {})[k].get("method"), "p": (method or {})[k].get("p")}
                     if (method or {}).get(k) else {})}
    return {"family": fam.id, "id": out["scenario"], "state": fam.spec.get("state"),
            "inputs": json.dumps(ins, ensure_ascii=False), "persona": persona, "kind": out["kind"],
            "variant": out["variant"], "created_by": created_by, "local_only": int(bool(local_only)),
            "created_at": db.now(), "updated_at": db.now()}


def record(con, fam: Family, out: dict, persona: str | None = None, created_by: str = "cli", local_only: bool = False,
           method: dict | None = None, commit: bool = True) -> str:
    """Store the scenario and its run (one short write); returns the run id."""
    row = scenario_row(fam, out, persona, created_by, local_only, method)
    have = db.one(con, "SELECT created_at, local_only, persona FROM scenarios WHERE family=? AND id=?", fam.id, out["scenario"])
    if have:
        row["created_at"] = have["created_at"] or row["created_at"]
        row["local_only"] = max(int(have["local_only"] or 0), row["local_only"])     # once local, always local
        row["persona"] = row["persona"] or have["persona"]
    db.upsert(con, "scenarios", [row], keys=("family", "id"), stamp=False)
    rid = run_id(out)
    keep = {k: v for k, v in out.items() if k != "trace"}
    db.upsert(con, "scenario_runs", [{"run_id": rid, "family": fam.id, "scenario": out["scenario"],
                                      "family_version": out["version"], "tables_hash": out["tables_hash"],
                                      "engine": out["engine"], "outputs": json.dumps(keep, ensure_ascii=False, default=str),
                                      "trace": json.dumps(out["trace"]), "seconds": round(out["ms"] / 1000, 4),
                                      "created_at": db.now()}], keys=("run_id",), stamp=False)
    if commit:
        con.commit()
    return rid


def run_scenario(fam: Family, sid_or_inputs: Any, variant: str | None = None) -> dict:
    """Evaluate a scenario given as its id string or as inputs."""
    if isinstance(sid_or_inputs, str):
        inputs, v = fam.parse_id(sid_or_inputs)
        return evaluate(fam, inputs, variant or v)
    return evaluate(fam, sid_or_inputs, variant)
