"""Aggregates for the dashboard, the maps and the README charts."""
from __future__ import annotations

from ..law import wording as W
from ..store import db
from . import method as M
from . import states as S
from .questions import QUESTIONS

LIGHT_MODEL_COLS = ("model_id, state, question, scope, title, tier, built_by, stages, completion, quality, metrics, "
                    "citation, source_url, updated_at, origin")


def overview(con) -> dict:
    out = {"governments": db.scalar(con, "SELECT count(*) FROM governments", default=0),
           "states_loaded": db.scalar(con, "SELECT count(DISTINCT state) FROM governments", default=0),
           "version": db.version(con), "questions": {}}
    kinds = db.rows(con, "SELECT kind, count(*) AS n FROM governments GROUP BY kind")
    out["kinds"] = {k["kind"]: k["n"] for k in kinds}
    out["statutes"] = {r["status"]: r["n"] for r in db.rows(con, "SELECT status, count(*) AS n FROM statute_files "
                                                               "GROUP BY status")}
    for qid, q in QUESTIONS.items():
        a = db.one(con, "SELECT count(*) AS n, avg(confidence) AS mean FROM answers WHERE question=?", qid) or {}
        tiers = {r["tier"]: r["n"] for r in db.rows(con, "SELECT tier, count(*) AS n FROM answers WHERE question=? "
                                                          "GROUP BY tier", qid)}
        contacts = {r["contact_level"]: r["n"] for r in db.rows(
            con, "SELECT contact_level, count(*) AS n FROM answers WHERE question=? GROUP BY contact_level", qid)}
        models = {r["tier"]: r["n"] for r in db.rows(con, "SELECT tier, count(*) AS n FROM process_models "
                                                           "WHERE question=? GROUP BY tier", qid)}
        located = db.scalar(con, "SELECT count(*) FROM located_law WHERE question=? AND status='found'", qid, default=0)
        local = db.scalar(con, "SELECT count(DISTINCT gov_id) FROM local_law WHERE question=? AND score > 0", qid, default=0)
        out["questions"][qid] = {"title": q.title, "short": q.short, "answers": a.get("n") or 0,
                                 "mean_confidence": round(a["mean"], 3) if a.get("mean") is not None else None,
                                 "governments_by_tier": tiers, "governments_by_contact": contacts,
                                 "models_by_tier": models, "states_located": located,
                                 "governments_with_local_law": local}
    out["stages"] = stage_counts(con)
    out["last_update"] = db.scalar(con, "SELECT max(updated_at) FROM answers")
    return out


def stage_counts(con) -> dict:
    """How many state models (per question) have reached each stage."""
    out = {qid: {s: 0 for s in M.STAGES} for qid in QUESTIONS}
    for r in db.rows(con, "SELECT question, stages FROM process_models"):
        st = db.loads(r["stages"], {})
        for s in M.STAGES:
            if st.get(s) and r["question"] in out:
                out[r["question"]][s] += 1
    for qid in QUESTIONS:      # located is known even before a model row exists
        out[qid]["located"] = max(out[qid]["located"], db.scalar(
            con, "SELECT count(*) FROM located_law WHERE question=? AND status='found'", qid, default=0))
    out["possible"] = len(S.CODES)
    return out


def state_table(con) -> list[dict]:
    govs = {r["state"]: r for r in db.rows(con, "SELECT state, count(*) AS governments, "
                                                 "sum(population) AS population FROM governments GROUP BY state")}
    ans = {(r["state"], r["question"]): r for r in db.rows(con, """
        SELECT state, question, avg(confidence) AS confidence, avg(contact_score) AS contact,
               avg(local_score) AS local, sum(contact_level='page') AS page, sum(contact_level='direct') AS direct,
               sum(contact_level='website') AS website, sum(contact_level IN ('postal','none')) AS weak,
               count(*) AS n
        FROM answers GROUP BY state, question""")}
    loc = {(r["state"], r["question"]): r for r in db.rows(con, "SELECT state, question, status, citation, heading, "
                                                                 "url, method, score FROM located_law")}
    pms = {(r["state"], r["question"]): r for r in db.rows(con, "SELECT state, question, tier, built_by, completion, "
                                                                "quality, title FROM process_models")}
    files = {r["state"]: r["status"] for r in db.rows(con, "SELECT state, status FROM statute_files")}
    local = {(r["state"], r["question"]): r["n"] for r in db.rows(
        con, "SELECT state, question, count(DISTINCT gov_id) AS n FROM local_law WHERE score > 0 GROUP BY state, question")}
    out = []
    for st, fips, name in S.STATES:
        for qid in QUESTIONS:
            a, l, p = ans.get((st, qid), {}), loc.get((st, qid), {}), pms.get((st, qid), {})
            n = a.get("n") or 0
            tier = p.get("tier") or ("found" if l.get("status") == "found" else "none")
            out.append({
                "state": st, "fips": fips, "name": name, "question": qid,
                "governments": (govs.get(st) or {}).get("governments", 0),
                "confidence": round(a["confidence"], 3) if a.get("confidence") is not None else None,
                "contact": round(a["contact"], 3) if a.get("contact") is not None else None,
                "page_share": round(a["page"] / n, 3) if n else None,
                "direct_share": round(a["direct"] / n, 3) if n else None,
                "website_share": round(a["website"] / n, 3) if n else None,
                "local_governments": local.get((st, qid), 0),
                "statutes": files.get(st, "not-downloaded"),
                "law_status": l.get("status") or "not-located", "citation": l.get("citation"),
                "heading": l.get("heading"), "law_url": l.get("url"), "method": l.get("method"),
                "locator_score": l.get("score"),
                "tier": tier, "built_by": p.get("built_by"), "completion": p.get("completion") or (
                    round(2 / len(M.STAGES), 3) if l.get("status") == "found" and not p else p.get("completion")),
                "quality": p.get("quality"), "model_title": p.get("title"),
            })
    return out


# The map (us-atlas, 2017 boundaries) predates two changes the Census 2022 list uses:
# Connecticut's planning regions replaced its counties, and Valdez-Cordova split in two.
CT_OLD = ["09001", "09003", "09005", "09007", "09009", "09011", "09013", "09015"]
SPLIT = {"02261": ["02063", "02066"]}


def _legacy(counties: dict) -> None:
    def merge(codes):
        parts = [counties[k] for k in codes if k in counties and counties[k]["value"] is not None]
        n = sum(p["n"] for p in parts)
        if not n:
            return None
        return {"value": round(sum(p["value"] * p["n"] for p in parts) / n, 4), "n": n}
    ct = merge([k for k in counties if k.startswith("091")])
    if ct:
        for k in CT_OLD:
            counties[k] = {**ct, "note": "Connecticut has planning regions, not counties: statewide figure"}
    for old, new in SPLIT.items():
        m = merge(new)
        if m:
            counties[old] = {**m, "note": "Chugach and Copper River census areas"}


def county_codes(fips: str) -> list[str]:
    """The Census county codes behind a map county code."""
    if fips in CT_OLD:
        return ["09110", "09120", "09130", "09140", "09150", "09160", "09170", "09180", "09190"]
    return SPLIT.get(fips, [fips])


def county_layer(con, question: str, layer: str) -> dict:
    """Per-county values for the map (layers: confidence, contact, local) plus per-state values."""
    if layer == "contact":
        expr = "avg(contact_score)"
    elif layer == "local":
        expr = "avg(local_score > 0)"
    else:
        expr = "avg(confidence)"
    counties = {r["county_fips"]: {"value": round(r["v"], 4) if r["v"] is not None else None, "n": r["n"]}
                for r in db.rows(con, f"SELECT county_fips, {expr} AS v, count(*) AS n FROM answers "
                                      f"WHERE question=? AND county_fips IS NOT NULL GROUP BY county_fips", question)}
    _legacy(counties)
    table = [r for r in state_table(con) if r["question"] == question]
    states = {r["fips"]: {k: r[k] for k in ("state", "name", "tier", "completion", "quality", "confidence",
                                           "governments", "citation", "built_by", "law_status")} for r in table}
    return {"question": question, "layer": layer, "counties": counties, "states": states,
            "version": db.version(con)}


def county_detail(con, fips: str, question: str) -> dict:
    codes = county_codes(fips)
    govs = db.rows(con, f"""
        SELECT g.gov_id, g.name, g.kind, g.population, g.website, a.confidence, a.tier, a.contact_level,
               a.state_score, a.local_score, a.contact_score, a.summary, a.model_id
        FROM governments g LEFT JOIN answers a ON a.gov_id = g.gov_id AND a.question = ?
        WHERE g.county_fips IN ({','.join('?' for _ in codes)})
        ORDER BY g.kind != 'county', g.population DESC""", question, *codes)
    for g in govs:
        g["summary"] = db.loads(g["summary"], {})
    name = govs[0]["name"] if govs and govs[0]["kind"] == "county" else None
    return {"fips": fips, "question": question, "county": name, "governments": govs}


def models(con, state: str | None = None) -> list[dict]:
    where, args = ("WHERE state=?", (state,)) if state else ("", ())
    out = db.rows(con, f"SELECT {LIGHT_MODEL_COLS} FROM process_models {where} ORDER BY state, question", *args)
    for r in out:
        r["stages"] = db.loads(r["stages"], {})
        r["metrics"] = db.loads(r["metrics"], {})
        r["state_name"] = S.NAME.get(r["state"], r["state"])
    return out


def model_detail(con, mid: str) -> dict | None:
    r = db.one(con, "SELECT * FROM process_models WHERE model_id=?", mid)
    if not r:
        return None
    for k in ("stages", "metrics", "facts"):
        r[k] = db.loads(r[k], {})
    r["state_name"] = S.NAME.get(r["state"], r["state"])
    r["law"] = db.one(con, "SELECT * FROM located_law WHERE state=? AND question=?", r["state"], r["question"])
    if r["law"]:
        r["law"]["related"] = db.loads(r["law"]["related"], [])
        r["law"]["candidates"] = db.loads(r["law"]["candidates"], [])
    r["extractions"] = db.rows(con, "SELECT llm, ok, rounds, problems, seconds, updated_at FROM extractions "
                                    "WHERE model_id=?", mid)
    for e in r["extractions"]:
        e["problems"] = db.loads(e["problems"], [])
    r["governments"] = db.scalar(con, "SELECT count(*) FROM answers WHERE model_id=?", mid, default=0)
    from .caselaw import for_model
    r["cases"] = for_model(con, r["state"], (r["metrics"] or {}).get("sections") or
                           ([r["law"]["section"]] if r.get("law") and r["law"].get("section") else []))
    return r


def steps_of(model: dict | None) -> list[dict]:
    """Plain-language steps from a model's facts, for answers and the browser plugin."""
    if not model or not model.get("facts"):
        return []
    f = model["facts"]
    actors = {a["id"]: a["name"] for a in f.get("actors", [])}
    code = "§"
    out = []
    for s in f.get("steps", []):
        q = s.get("source") or {}
        sub = "".join(f"({p})" for p in (q.get("subsection") or "").split(".") if p)
        d = s.get("deadline")
        # "deadline" is lexflow's unit, for the arithmetic; "law_deadline" is the statute's own words (or a figure
        # marked as lexflow's count), which is what public pages print (lexflow/law/wording.py)
        out.append({"step": s["action"], "who": actors.get(s["actor"], s["actor"]),
                    "cite": f"{code} {q.get('section', '')}{sub}".strip(), "quote": q.get("quote"),
                    "deadline": f"{d['amount']} {d['unit'].replace('_', ' ')}" if d else None,
                    "law_deadline": W.describe(s, f) if d else None,
                    "modality": s.get("modality")})
    return out
