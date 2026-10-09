"""Score every government's answer to each question (see :mod:`lexflow.municipal.method`)."""
from __future__ import annotations

from collections import defaultdict

from ..store import db
from . import contacts as C
from . import method as M
from .fetch import Log
from .questions import QUESTIONS

CONTACT_ORDER = {"page": 0, "email": 1, "person": 1, "office": 1, "phone": 2, "website": 3, "postal": 4}


def state_part(con, state: str, question: str, meth: dict) -> dict:
    pm = db.one(con, "SELECT model_id, tier, built_by FROM process_models WHERE model_id=?", f"{state}.{question}")
    loc = db.one(con, "SELECT status, score, citation FROM located_law WHERE state=? AND question=?", state, question)
    if pm:
        tier = pm["tier"]
    else:
        tier = "found" if loc and loc["status"] == "found" else "none"
    s = meth["tier_score"][tier]
    if tier == "found":
        s *= (loc or {}).get("score") or 0.5
    return {"tier": tier, "score": round(s, 4), "built_by": (pm or {}).get("built_by"),
            "model_id": pm["model_id"] if pm and tier not in ("none",) else None}


def run(con, state: str, log: Log = print) -> dict:
    meth = M.get(con)
    govs = db.rows(con, "SELECT gov_id, county_fips FROM governments WHERE state=?", state)
    if not govs:
        log(f"{state}: no governments loaded")
        return {"answers": 0}
    by_gov = defaultdict(list)
    for c in db.rows(con, "SELECT gov_id, question, kind, value, label FROM contacts WHERE state=?", state):
        by_gov[c["gov_id"]].append(c)
    local = defaultdict(list)
    for r in db.rows(con, "SELECT gov_id, question, header, score FROM local_law WHERE state=? AND score > 0 ORDER BY score DESC",
                     state):
        local[(r["gov_id"], r["question"])].append(r)
    rows, ts = [], db.now()
    totals = {}
    for qid in QUESTIONS:
        sp = state_part(con, state, qid, meth)
        w = meth["weights"][qid]
        conf_sum = 0.0
        for g in govs:
            cs = by_gov.get(g["gov_id"], [])
            level = C.level(cs, qid)
            contact_score = meth["contact_score"][level]
            loc_rows = local.get((g["gov_id"], qid), [])
            local_score = meth["local_found_score"] * max((r["score"] for r in loc_rows), default=0.0)
            confidence = w["state"] * sp["score"] + w["local"] * local_score + w["contact"] * contact_score
            offices = sorted((c for c in cs if c["question"] in (qid, "general")),
                             key=lambda c: (c["question"] != qid, CONTACT_ORDER.get(c["kind"], 9)))[:4]
            rows.append({
                "gov_id": g["gov_id"], "state": state, "question": qid, "county_fips": g["county_fips"],
                "confidence": round(confidence, 4), "state_score": sp["score"], "local_score": round(local_score, 4),
                "contact_score": contact_score, "tier": sp["tier"], "built_by": sp["built_by"],
                "contact_level": level, "model_id": sp["model_id"], "updated_at": ts,
                "summary": {"offices": [{k: c[k] for k in ("kind", "value", "label")} for c in offices],
                            "local": [r["header"] for r in loc_rows[:3]]},
            })
            conf_sum += confidence
        totals[qid] = round(conf_sum / len(govs), 3)
    for i in range(0, len(rows), 5000):
        db.upsert(con, "answers", rows[i:i + 5000])
    db.bump(con)
    con.commit()
    log(f"{state}: scored {len(govs):,} governments - mean confidence "
        + ", ".join(f"{k} {v:.2f}" for k, v in totals.items()))
    return {"answers": len(rows), "mean": totals}
