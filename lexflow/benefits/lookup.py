"""Which retirement benefits apply to a person in a place, who runs each, the law that creates it, how to apply and
appeal, and how the state taxes it.

``lookup(place, person)``: ``place`` is a Census government id (the ``governments`` table), a state code, or a
place's name ("Charlottesville, VA"); ``person`` one of ``programs.PERSON_TYPES``.  The answer lists:

* **pension systems**: for a public employee, the statewide systems whose membership includes that kind of
  employee (``fixtures/benefits/systems/<st>.json``, each with the section that creates it, the body that runs it,
  its website and office channels), and for a county, city or township employee the systems that government itself
  administers (the Census join in ``pension_coverage``); with the Census's member counts;
* **the state auto-IRA program** for a private-sector employee whose employer offers no plan (and, where the law
  lets them join, the self-employed), with its thresholds and deadlines;
* **tax treatment**: how the state taxes Social Security, public and private pensions and military retired pay;
* **federal pointers**: Social Security, SSI, VA pension, military retired pay, ERISA plans, as applicable;
* for Virginia public employees, a link to the computed ``retirement_va`` family (plan, eligibility, service credit).

Only facts whose quote lexflow's software matched are shown as grounded; anything else is listed under ``missing``.
``ask`` gives the same as "Who do I ask" cards (``lexflow.ask.who``'s shape: role, played by, channels, the law's
words, steps).  Privacy: organisations and office channels only; every channel passes ``lexflow.privacy`` through
``who._channel``.  A person's own facts are never taken here: the person type is a category, not data about them.
"""
from __future__ import annotations

import json
import re

from ..store import db
from . import ground as G
from . import programs as PR

FAMILY_EMPLOYER = {"state_employee": "state", "teacher": "teacher", "local_employee": "political_subdivision",
                   "public_safety": "hazardous"}
LOCAL_PERSON = ("local_employee", "public_safety", "teacher")
MEMBERS_WORDS = {"state_employee": "state employees", "teacher": "public school teachers",
                 "public_safety": "police, fire, corrections or EMS employees", "judge": "judges"}
CENSUS_CITATION = None


class LookupError_(ValueError):
    pass


# ------------------------------------------------------------------------------------------------ place
def resolve(con, place: str | None) -> dict:
    """``{state, gov}`` for a government id, a state code or name, or a place's name."""
    from ..ask import who as W
    from ..municipal import states as S
    p = (place or "").strip()
    if not p:
        raise LookupError_("give a place: a state, county, city or town (or a Census government id)")
    g = W.resolve_place(con, p)
    m = re.match(r"^(.*?)[,\s]+([A-Za-z]{2}|[A-Za-z][A-Za-z ]+)$", p)
    if (not g or not g.get("gov_id")) and m and (m.group(2).lower() in S.NAME or W.state_in(m.group(2))):
        st = m.group(2).lower() if m.group(2).lower() in S.NAME else W.state_in(m.group(2))
        g = W.find_place(con, m.group(1).strip(" ,"), st) or g      # "Charlottesville, VA", "Staunton, Virginia"
    if not g:
        raise LookupError_(f"no state or government matches {p!r}")
    if g.get("gov_id"):
        return {"state": g["state"], "gov": g}
    st = g.get("state")
    if st not in S.NAME:
        raise LookupError_(f"no state or government matches {p!r}")
    return {"state": st, "gov": None}


# --------------------------------------------------------------------------------------------- pieces
def _channels(entry: dict, owner: str) -> list[dict]:
    from ..ask.who import _channel
    out = []
    for c in entry.get("channels") or []:
        src = c.get("source")
        if src and not G.matched(src):
            continue                                       # a channel the site's own page no longer shows
        ch = _channel(c.get("kind"), c.get("value"), c.get("label"), (src or {}).get("url") or "fixture",
                      (src or {}).get("grounding", {}).get("on"), owner)
        if ch:
            out.append(ch)
    site = entry.get("website")
    if site and not any(c["kind"] == "website" for c in out) and G.matched(entry.get("website_source")):
        ch = _channel("website", site, "Official website", (entry.get("website_source") or {}).get("url"),
                      (entry.get("website_source") or {}).get("grounding", {}).get("on"), owner)
        if ch:
            out.append(ch)
    return out


def _shown(src: dict | None) -> dict | None:
    """A source for display only when lexflow's software matched it."""
    return PR.display(src) if G.matched(src) else None


def _census(con, ids: list[str]) -> list[dict]:
    if not ids:
        return []
    rows = db.rows(con, f"SELECT id, name, census_name, members_active, members_active_local, beneficiaries, "
                        f"members_total, year, years FROM pension_systems WHERE id IN ({','.join('?' * len(ids))})", *ids)
    return [{**r, "years": json.loads(r["years"] or "[]")} for r in rows]


def _census_source(years: list[int] | None = None) -> str:
    from . import census as C
    return C.citation(years)


def _person_matches(entry: dict, person: str) -> bool:
    m = set(entry.get("membership") or [])
    if person == "local_employee":
        return "local_employee" in m and bool(entry.get("covers_local"))
    if person == "public_safety":
        return "public_safety" in m
    return person in m


def _system_card(con, st: str, entry: dict, person: str, doc: dict) -> dict:
    from . import systems as SY
    body = dict(entry.get("body") or {})
    body_src = body.pop("source", None)
    if not body.get("wikidata"):
        body["wikidata"] = (SY.wikidata_of(st, entry.get("name") or "") or {}).get("qid")
    owner = [body.get("name") or entry.get("name"), entry.get("name")]
    statute = _shown(entry.get("statute"))
    out = {"kind": "state_system", "level": "state", "name": entry.get("name"), "short": entry.get("short"),
           "plans": entry.get("plans") or [], "membership": entry.get("membership") or [],
           "covers_local": bool(entry.get("covers_local")),
           "body": {"name": body.get("name") or entry.get("name"), "wikidata": body.get("wikidata"),
                    "wikidata_url": f"https://www.wikidata.org/wiki/{body['wikidata']}" if body.get("wikidata") else None,
                    "source": _shown(body_src)},
           "website": entry.get("website") if G.matched(entry.get("website_source")) else None,
           "website_source": _shown(entry.get("website_source")),
           "channels": _channels(entry, owner),
           "statute": statute, "statute_role": entry.get("statute_role") if statute else None,
           "also": [x for x in (_shown(s) for s in entry.get("also") or []) if x],
           "covers_local_source": _shown(entry.get("covers_local_source")),
           "census": _census(con, entry.get("census_units") or []),
           "why": _why(entry, person), "notes": entry.get("notes") or None}
    for k in ("apply", "appeal"):
        item = entry.get(k) or doc.get(k)
        if item:
            srcs = [x for x in (_shown(s) for s in item.get("sources") or []) if x]
            out[k] = {"text": item.get("text"), "sources": srcs, "grounded": bool(srcs)}
        else:
            out[k] = None
    if entry.get("family"):
        emp = FAMILY_EMPLOYER.get(person)
        out["family"] = {"id": entry["family"], "href": f"#/hypo/{entry['family']}",
                         "api": f"/api/hypo/{entry['family']}/run" + (f"?employer={emp}" if emp else ""),
                         "employer": emp}
    if not statute:
        out["missing"] = [f"the section that creates {entry.get('name')} was not found (or not matched) in this "
                          f"copy's {st.upper()} statute index" + (f": {entry.get('why')}" if entry.get("why") else "")]
    return out


def _why(entry: dict, person: str) -> str:
    if person == "local_employee":
        return "open to local governments' employees; whether your employer takes part is its choice"
    return "its members include " + MEMBERS_WORDS.get(person, person)


def _local_cards(con, gov: dict, person: str) -> list[dict]:
    from ..ask.who import table_channels
    rows = db.rows(con, "SELECT c.system_id, c.how, c.person_types, c.note, s.* FROM pension_coverage c JOIN "
                        "pension_systems s ON s.id = c.system_id WHERE c.gov_id=? AND c.how='administers' "
                        "ORDER BY s.members_active DESC", gov["gov_id"])
    out = []
    chans = table_channels(con, gov["gov_id"], gov["name"])
    for r in rows:
        types = json.loads(r["person_types"] or "[]")
        if person not in types and not (person == "local_employee" and not types):
            continue
        years = json.loads(r["years"] or "[]")
        out.append({"kind": "local_system", "level": "local", "name": r["name"], "census_name": r["census_name"],
                    "membership": types, "body": {"name": gov["name"], "gov_id": gov["gov_id"],
                                                  "wikidata": gov.get("wikidata")},
                    "channels": chans, "website": gov.get("website"),
                    "how": r["note"], "statute": None,
                    "census": [{"id": r["id"], "name": r["name"], "census_name": r["census_name"],
                                "members_active": r["members_active"], "beneficiaries": r["beneficiaries"],
                                "members_total": r["members_total"], "year": r["year"], "years": years}],
                    "source": _census_source(years),
                    "why": f"administered by {gov['name']} (the Census join by name)",
                    "missing": ["a locally administered system rests on the local government's own ordinance or "
                                "charter, which is not in the statute index; the Census Bureau's survey is the source"],
                    "apply": None, "appeal": None})
    return out


def _auto_ira(st: str, person: str) -> list[dict]:
    out = []
    for p in PR.auto_ira(st):
        kinds = {f.get("kind") for f in p.get("facts") or [] if PR.fact_grounded(f)}
        if person == "private_with_plan" and p.get("mandate"):
            note = "an employer that already offers a qualified plan is exempt from the mandate"
        elif person == "self_employed" and "self_employed" not in kinds and p.get("mandate"):
            continue
        elif person not in ("private_no_plan", "self_employed", "private_with_plan"):
            continue
        else:
            note = None
        facts = []
        for f in p.get("facts") or []:
            srcs = [x for x in (_shown(s) for s in f.get("sources") or []) if x]
            if not srcs:
                continue
            facts.append({"kind": f.get("kind"), "text": f.get("text"), "employees_min": f.get("employees_min"),
                          "deadline": f.get("deadline"), "sources": srcs})
        thresholds = [f for f in facts if f["kind"] == "threshold"]
        out.append({"kind": "auto_ira", "level": "state", "id": p["id"], "name": p["name"],
                    "mandate": bool(p.get("mandate")), "status": p.get("status"),
                    "body": {"name": p.get("board")}, "website": p.get("website"), "facts": facts,
                    "smallest_employer": min((t["employees_min"] for t in thresholds if t.get("employees_min")),
                                             default=None),
                    "note": note, "notes": p.get("notes") or None})
    return out


def _tax(st: str, person: str) -> dict | None:
    doc = PR.tax(st)
    if not doc:
        return None
    items = {}
    for k, label in PR.INCOME_ITEMS.items():
        it = (doc.get("items") or {}).get(k) or {}
        srcs = [x for x in (_shown(s) for s in it.get("sources") or []) if x]
        grounded = bool(srcs) and it.get("treatment") not in (None, "unknown")
        items[k] = {"label": label, "treatment": it.get("treatment") if grounded else "unknown",
                    "summary": it.get("summary") if grounded else None, "conditions": it.get("conditions") or [],
                    "amount_usd": it.get("amount_usd"), "age_min": it.get("age_min"), "sources": srcs,
                    "grounded": grounded, "why": None if grounded else (it.get("why") or "no matched source")}
    first = PR.TAX_ITEMS_FOR.get(person) or list(PR.INCOME_ITEMS)
    return {"state": st, "income_tax": doc.get("income_tax"), "tax_year": doc.get("tax_year"),
            "agency": doc.get("agency"), "first": first, "items": items, "notes": doc.get("notes") or None}


def _federal(person: str) -> list[dict]:
    out = []
    for p in PR.federal():
        if person not in (p.get("applies_to") or []):
            continue
        out.append({"kind": "federal", "level": "federal", "id": p["id"], "name": p["name"],
                    "body": {"name": p.get("agency")}, "website": p.get("url"), "law": p.get("law"),
                    "source": _shown(p.get("source")), "note": p.get("note"),
                    "appeal": {"text": p["appeal"]["text"], "url": p["appeal"].get("url"),
                               "sources": [x for x in [_shown(p["appeal"].get("source"))] if x]}
                    if p.get("appeal") else None})
    return out


# --------------------------------------------------------------------------------------------- lookup
def lookup(place: str, person: str, con=None) -> dict:
    """The programs that apply (see the module docstring)."""
    if person not in PR.PERSON_TYPES:
        raise LookupError_(f"person must be one of {', '.join(PR.PERSON_TYPES)}")
    own = con is None
    con = con or db.connect()
    try:
        where = resolve(con, place)
        st, gov = where["state"], where["gov"]
        from ..municipal import states as S
        doc = PR.systems(st) or {}
        systems, missing, notes = [], [], []
        if person in PR.PUBLIC:
            for e in doc.get("systems") or []:
                if _person_matches(e, person):
                    systems.append(_system_card(con, st, e, person, doc))
            if gov and person in LOCAL_PERSON:
                systems += _local_cards(con, gov, person)
            elif person in LOCAL_PERSON and not gov:
                notes.append("Give your county, city or town: some local governments run their own systems "
                             "(the Census Bureau's survey lists them).")
            if not doc:
                missing.append(f"no statewide systems fixture for {S.NAME.get(st, st)} (fixtures/benefits/systems/)")
            elif not systems:
                missing.append(f"no statewide system in {S.NAME.get(st, st)} lists this kind of employee as a member")
        progs = _auto_ira(st, person)
        if person == "private_no_plan" and not any(p["mandate"] for p in progs):
            notes.append(f"{S.NAME.get(st, st)} has no state law (in lexflow's fixtures) requiring employers without "
                         f"a plan to offer a state-run IRA.")
        tax = _tax(st, person)
        if tax is None:
            missing.append(f"no tax-treatment fixture for {S.NAME.get(st, st)}")
        fam = next((s["family"] for s in systems if s.get("family")), None)
        return {"place": {"state": st, "state_name": S.NAME.get(st),
                          **({k: gov.get(k) for k in ("gov_id", "name", "kind", "population")} if gov else {})},
                "person": person, "person_label": PR.PERSON_TYPES[person],
                "systems": systems, "auto_ira": progs, "tax": tax, "federal": _federal(person),
                "family": fam, "missing": missing + [m for s in systems for m in s.get("missing") or []],
                "notes": notes,
                "about": "Programs, bodies and office channels only; every quote is matched by lexflow's software "
                         "against the statute index or the cited page. Computed, not reviewed by a person; not legal "
                         "or financial advice."}
    finally:
        if own:
            con.close()


# --------------------------------------------------------------------------------------------- who do I ask
def ask(place: str, person: str, con=None) -> dict:
    """The lookup as "Who do I ask" cards: one per program, with the body that plays the role, its channels and the
    law's words, and the steps (apply, appeal) each with its grounding."""
    out = lookup(place, person, con)
    cards = []
    for s in out["systems"]:
        steps = []
        for k, label in (("apply", "Apply for your retirement benefit"), ("appeal", "Appeal a benefit decision")):
            item = s.get(k)
            if item and item.get("grounded"):
                steps.append({"label": label, "text": item["text"], "sources": item["sources"]})
        cards.append({"label": "Runs your pension" if s["level"] == "state" else "Runs a local pension system",
                      "program": s["name"], "level": s["level"],
                      "played_by": {"label": s["body"]["name"], "kind": "body", "channels": s.get("channels") or [],
                                    "links": {"wikidata": s["body"].get("wikidata_url")}},
                      "quotes": [q for q in [s.get("statute")] + (s.get("also") or []) if q],
                      "steps": steps, "missing": s.get("missing") or []})
    for p in out["auto_ira"]:
        cards.append({"label": "Runs the state's auto-IRA program" if p["mandate"] else "Runs a voluntary state program",
                      "program": p["name"], "level": "state",
                      "played_by": {"label": p["body"]["name"], "kind": "body",
                                    "channels": [{"kind": "website", "value": p["website"], "label": "Official website"}]
                                    if p.get("website") else [], "links": {}},
                      "quotes": [s for f in p["facts"] if f["kind"] in ("creates", "mandate") for s in f["sources"]][:3],
                      "steps": [{"label": f["kind"], "text": f["text"], "sources": f["sources"]}
                                for f in p["facts"] if f["kind"] in ("threshold", "deadline", "exemption", "penalty")],
                      "missing": []})
    if out["tax"] and out["tax"].get("agency"):
        t = out["tax"]
        cards.append({"label": "Taxes your retirement income", "program": f"{out['place']['state_name']} income tax",
                      "level": "state",
                      "played_by": {"label": t["agency"].get("name"), "kind": "body",
                                    "channels": [{"kind": "website", "value": t["agency"].get("url"),
                                                  "label": "Official website"}] if t["agency"].get("url") else [],
                                    "links": {}},
                      "quotes": [s for k in t["first"] for s in t["items"][k]["sources"]][:4],
                      "steps": [{"label": t["items"][k]["label"], "text": f"{t['items'][k]['treatment']}: "
                                 f"{t['items'][k]['summary'] or ''}", "sources": t["items"][k]["sources"]}
                                for k in t["first"]], "missing": []})
    for f in out["federal"]:
        cards.append({"label": "Federal program", "program": f["name"], "level": "federal",
                      "played_by": {"label": f["body"]["name"], "kind": "body",
                                    "channels": [{"kind": "website", "value": f["website"], "label": "Official page"}],
                                    "links": {}},
                      "quotes": [q for q in [f.get("source")] if q],
                      "steps": [{"label": "Appeal", "text": f["appeal"]["text"], "sources": f["appeal"]["sources"]}]
                      if f.get("appeal") else [], "missing": []})
    return {"route": {"place": out["place"], "person": person, "person_label": out["person_label"]},
            "roles": cards, "family": out["family"], "missing": out["missing"], "notes": out["notes"]}


# --------------------------------------------------------------------------------------------- text
def render_lookup(out: dict) -> str:
    pl = out["place"]
    L = [f"{out['person_label']} in {pl.get('name') + ', ' if pl.get('name') else ''}{pl['state_name']}"]
    for s in out["systems"]:
        L.append(f"- {s['name']} ({s['level']}) run by {s['body']['name']}"
                 + (f" [Wikidata {s['body']['wikidata']}]" if s['body'].get('wikidata') else ""))
        if s.get("statute"):
            L.append(f"    law: {s['statute']['citation']}: \"{s['statute']['quote'][:150]}\"")
        for c in s.get("channels") or []:
            L.append(f"    {c['kind']}: {c['value']}")
        for k in ("apply", "appeal"):
            if s.get(k) and s[k].get("grounded"):
                L.append(f"    {k}: {s[k]['text']}")
        for cu in s.get("census") or []:
            L.append(f"    Census {cu['year']}: {cu['census_name']}: {cu['members_active'] or '?'} active, "
                     f"{cu['beneficiaries'] or '?'} beneficiaries")
        if s.get("family"):
            L.append(f"    computed eligibility: {s['family']['href']}")
    for p in out["auto_ira"]:
        L.append(f"- {p['name']} ({'mandate' if p['mandate'] else 'voluntary'}, {p['status']}), run by "
                 f"{p['body']['name']}" + (f"; smallest employer covered: {p['smallest_employer']}"
                                           if p.get("smallest_employer") else ""))
    t = out.get("tax")
    if t:
        for k in t["first"]:
            it = t["items"][k]
            L.append(f"- tax: {it['label']}: {it['treatment']}" + (f" ({it['summary']})" if it.get("summary") else ""))
    for f in out["federal"]:
        L.append(f"- federal: {f['name']} ({f['body']['name']}) {f['website']}")
    for m in out["missing"]:
        L.append(f"missing: {m}")
    for n in out["notes"]:
        L.append(f"note: {n}")
    return "\n".join(L)


def render(a: dict) -> str:
    r = a["route"]
    L = [f"Who do I ask: {r['person_label']} in {r['place'].get('name') or r['place']['state_name']}"]
    for c in a["roles"]:
        pb = c["played_by"]
        L.append(f"- {c['label']}: {c['program']} -> {pb['label']}")
        for ch in pb.get("channels") or []:
            L.append(f"    {ch['kind']}: {ch['value']}")
        for q in c.get("quotes") or []:
            L.append(f"    the law says ({q.get('citation') or q.get('url')}): \"{(q.get('quote') or '')[:140]}\"")
        for s in c.get("steps") or []:
            L.append(f"    {s['label']}: {s['text'][:160]}")
    for m in a.get("missing") or []:
        L.append(f"missing: {m}")
    return "\n".join(L)
