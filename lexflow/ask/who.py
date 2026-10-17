"""Who do I ask: a plain question becomes a jurisdiction, a topic and the processes it names, and the answer lists
every role in those processes, who plays it, how to reach them, and the statute words that make it responsible.

``route(question, place=None)`` finds the place (the ``governments`` table and the 52 states, the same data as the
dashboard's place autocomplete), the topic (``RULES`` first, in order; then the decision model of
``lexflow.extract.decide`` when ``LEXFLOW_DECIDE=1`` or a decider is passed, as a choice over
``schema.VOCAB["topic"]`` accepted at confidence ``TOPIC_CONFIDENCE`` or more) and the process keys: the state's
process models whose question maps to the topic, and the place's researched processes (``place_processes``) whose
category maps to the topic or whose name shares a word with the question.

``answer(route)`` reads the local SPARQL store (``lexflow.publish.rdf``; the canned ``who-does-what.rq`` for the
state and for the government, ``body-contacts.rq`` per body, and three small inline queries for a body's details,
its parent chain and a role's grounding quote), or the live endpoint with ``live=True``.  Roles are grouped: role,
played by (a body, a post, an office type, or "you / a private party"), the body's parent chain, its office
channels with source and date (the store's, plus the ``contacts`` rows keyed by the body's key), its Wikidata and
Govdirectory links, the quote, and the steps the role bears with their deadlines.  Local processes of the place
come under ``local`` ("ask the locality").  When the store is absent the same shape is built from the models'
facts and the researched files (``source = "facts"``).

Privacy (``lexflow.privacy``): organisations and office channels only.  Every channel shown passes
``is_office_channel`` (or, for a store row that has no label, the value checks alone), labels pass
``office_label``, and general mailboxes are withheld until a contact check found them on the office's own page.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable

from .. import config, privacy
from ..municipal import states as S
from ..publish import schema as SC
from ..store import db

TOPIC_CONFIDENCE = 0.8
CHANNELS_MAX = 10
WIKIDATA_WIKI = "https://www.wikidata.org/wiki/"
LEXIPEDIA_ITEM = "https://lexipedia.wikibase.cloud/wiki/Item:"
AGENCIES = config.ROOT / "fixtures" / "entities" / "agencies.json"

# ----------------------------------------------------------------------------------------------------- topics
# (topic slug, pattern): the first rule that matches wins, so the specific ones come first ("dog licence" is
# animals, "business licence" is business, "building permit" is building and zoning, before the generic licensing)
RULES: list[tuple[str, re.Pattern]] = [(t, re.compile(p, re.I)) for t, p in [
    ("animals", r"\b(dogs?|pets?|cats?|animals?|kennels?|rabies)\b"),
    ("public-records", r"\bfoia\b|\bfoil\b|public[- ]records?|records? request|freedom of information|open records|"
                       r"right[- ]to[- ]know|public information act|\bopra\b|\bcpra\b"),
    ("criminal-records", r"expung|\bseal(ing|ed)?\b.{0,30}\brecords?\b|criminal (history|records?)|background check"),
    ("business", r"\bllcs?\b|limited liability|corporations?\b|incorporat|start(ing|ed)? (a |my |an? new )?business|"
                 r"business licen[cs]e|\bbpol\b|register(ing)? (a |my )?business|meals tax|assumed name|"
                 r"fictitious name|trade name|\bdba\b|short[- ]term rental|homestay|open(ing)? (a |my )?(shop|store|business)"),
    ("building-and-zoning", r"building permit|\bzoning\b|\bvariance\b|construction permit|renovat|\bdemoli|"
                            r"\bpermit\b.{0,40}\b(build|deck|fence|addition|garage|shed)|\b(build|deck|fence|addition|garage|shed)\b.{0,40}\bpermit\b"),
    ("voting", r"\bvot(e|er|ers|ing)\b|absentee|\bballot\b|\belections?\b|register to vote|registrar"),
    ("benefits", r"\bsnap\b|medicaid|\btanf\b|food stamps|public benefits|energy assistance|\bwelfare\b|"
                 r"social services"),
    ("taxes", r"\btax(es)?\b|assessment appeal|personal property|real estate assess|land use (tax|valuation)|"
              r"board of equalization"),
    ("courts", r"\btickets?\b|small claims|\bprobate\b|\bexecutor\b|marriage licen[cs]e|\bcourts?\b|lawsuit|"
               r"\bsue\b|\btraffic\b|\bjudge\b|\bclerk of (the )?court\b"),
    ("property", r"\bdeeds?\b|land records|property records|vital records|birth certificate|death certificate|"
                 r"\brecord(ing)? a deed\b"),
    ("licensing", r"licen[cs]e|licens|\bpermits?\b|certif"),
]]
TOPICS: dict[str, SC.Voc] = {v.slug: v for v in SC.VOCAB["topic"]}

# place process categories the schema's map does not cover (curated/places/*/*.json: category)
CATEGORY_TOPIC: dict[str, str] = {
    **SC.CATEGORY_TOPIC,
    "permits_construction": "building-and-zoning", "zoning_land_use": "building-and-zoning",
    "courts_legal": "courts", "health_social_services": "benefits", "elections": "voting",
    "transportation_parking": "courts", "tax_relief": "taxes", "taxes_assessments": "taxes",
    "animals": "animals", "records": "public-records",
}
# the state questions (process_models.question) by topic
QUESTION_OF_TOPIC: dict[str, list[str]] = {}
for _q, _t in SC.QUESTION_TOPIC.items():
    QUESTION_OF_TOPIC.setdefault(_t, []).append(_q)

# words shared by many processes: alone they do not make a process a match ("dog license" is not "marriage license")
GENERIC = frozenset("license permit request application registration register tax record file filing appeal get pay "
                    "apply form city county town local state".split())
STOP = frozenset("""
a an the and or of for to in on at by with from how do i can who what where which is are my me our we you your
handles handle ask asking need get getting apply applying start starting file filing request requesting
about into up out does should would could want wants there here it its this that these those one someone
""".split())
_PLURAL = re.compile(r"(?<=[a-z])(?:es|s)$")


def words(text: str) -> set[str]:
    """Content words of a question or a title, lower-cased, singular-ish, with ``licence`` spelt ``license``."""
    out = set()
    for w in re.findall(r"[a-z0-9]+", (text or "").lower().replace("licence", "license")):
        if w in STOP or len(w) < 3:
            continue
        out.add(_PLURAL.sub("", w) if len(w) > 4 else w)
    return out


def topic_by_rule(question: str) -> str | None:
    for slug, pat in RULES:
        if pat.search(question or ""):
            return slug
    return None


TOPIC_QUESTIONS = {"topic": {"type": "choice", "instructions": "Which topic is this question about? Judge by what the "
                                                                "person wants to do.",
                             "criteria": {v.slug: v.description for v in SC.VOCAB["topic"]}}}


def topic_by_model(question: str, decider=None) -> tuple[str | None, float | None]:
    """The decision model's topic (``lexflow.extract.decide``) when it is confident enough, else None.  With no
    ``decider`` the process-wide one is used, which exists only when ``LEXFLOW_DECIDE=1``."""
    from ..extract import decide as D
    d = decider or D.shared()
    if d is None:
        return None, None
    try:
        out = d.decide({"Question": " ".join((question or "").split())[:1000]}, TOPIC_QUESTIONS)
    except Exception:
        return None, None
    a = (out.get("answers") or {}).get("topic") or {}
    choice, conf = a.get("choice"), a.get("confidence")
    try:
        conf = float(conf) if conf is not None else None
    except (TypeError, ValueError):
        conf = None
    if choice in TOPICS and conf is not None and conf >= TOPIC_CONFIDENCE:
        return choice, conf
    return None, conf


# ----------------------------------------------------------------------------------------------------- places
_STATE_NAME = re.compile(r"\b(" + "|".join(sorted((re.escape(n) for n in S.NAME.values()), key=len, reverse=True))
                         + r")\b", re.I)
_STATE_CODE = re.compile(r"(?<![A-Za-z])(" + "|".join(c.upper() for c in S.CODES) + r")(?![A-Za-z])")
_NAME_BY_LOWER = {n.lower(): c for c, n in S.NAME.items()}
# "in Charlottesville", "for the City of Staunton", "in Albemarle County, Virginia", "in charlottesville va"
_PLACE = re.compile(r"\b(?=(?:in|for|at|of|from|to)\s+(?:the\s+)?((?:city|county|town|village|borough|township)\s+of\s+)?"
                    r"([A-Za-z][\w.'\-]*(?:\s+[A-Za-z][\w.'\-]*){0,3}))", re.I)      # a lookahead: matches may overlap
# a place named without a preposition: "Albemarle County", "City of Staunton", "Charlottesville, Virginia"
_PLACE_BARE = re.compile(r"\b((?:City|County|Town|Village|Borough|Township)\s+of\s+[A-Z][\w.'\-]*(?:\s+[A-Z][\w.'\-]*){0,2}"
                         r"|[A-Z][\w.'\-]*(?:\s+[A-Z][\w.'\-]*){0,2}\s+(?:County|City|Town|Parish|Borough|Township))\b")
_FURNITURE = re.compile(r"\b(city|county|town|village|borough|township|of|the|government|municipality|charter)\b", re.I)
_KIND_WORD = re.compile(r"\b(county|city|town|village|borough|township)\b", re.I)


def _core(name: str) -> str:
    return re.sub(r"\s+", " ", _FURNITURE.sub(" ", name or "")).strip().lower()


def state_in(text: str) -> str | None:
    """The state a question names: a name ("Virginia", "District of Columbia") or an upper-case code ("VA")."""
    m = _STATE_NAME.search(text or "")
    if m:
        return _NAME_BY_LOWER[m.group(1).lower()]
    m = _STATE_CODE.search(text or "")
    return m.group(1).lower() if m else None


def find_place(con, text: str, state: str | None = None) -> dict | None:
    """The government whose name best matches ``text`` ("Charlottesville", "Albemarle County", "City of
    Staunton"): a name whose core equals the text wins, then a county when the text says county, then the most
    populous match.  ``state`` narrows the search when known."""
    t = re.sub(r"\s+", " ", (text or "").strip(" ,.;:?!")).strip()
    if len(t) < 3 or not con:
        return None
    core = _core(t)
    if not core or core in _NAME_BY_LOWER:
        return None
    sql = "SELECT gov_id, name, kind, state, population, wikidata, website FROM governments WHERE name LIKE ?"
    args: list = [f"%{core}%"]
    if state:
        sql += " AND state = ?"
        args.append(state)
    rows = db.rows(con, sql + " ORDER BY population DESC LIMIT 25", *args)
    if not rows:
        return None
    wants = (_KIND_WORD.search(t) or [None, ""])[1].lower() if _KIND_WORD.search(t) else ""

    def score(g):
        exact = _core(g["name"]) == core
        kind_ok = (wants == "county") == (g["kind"] == "county") if wants else g["kind"] != "county"
        return (exact, kind_ok, g["population"] or 0)
    return max(rows, key=score)


def place_in(con, question: str, state: str | None = None) -> dict | None:
    """The government a question names after "in", "for", "at" ("who handles a FOIA request in Charlottesville");
    a state name after the preposition is not a place."""
    for m in _PLACE.finditer(question or ""):
        cand = (m.group(1) or "") + m.group(2)
        # cut a trailing state name or code ("Charlottesville, Virginia", "Staunton VA") and trailing question words
        cand = _STATE_NAME.sub("", cand)
        cand = re.sub(r"\s+(?:" + "|".join(c.upper() for c in S.CODES) + r")\b", "", cand)
        cand = re.split(r"\s+(?:and|or|when|if|where|how|what|who|that|which|with|about)\b", cand, maxsplit=1)[0]
        g = find_place(con, cand, state)
        if g:
            return g
        # try the shorter heads of the phrase ("Charlottesville city hall" -> "Charlottesville")
        parts = cand.split()
        for n in range(len(parts) - 1, 0, -1):
            g = find_place(con, " ".join(parts[:n]), state) or find_place(con, " ".join(parts[-n:]), state)
            if g:
                return g
    for m in _PLACE_BARE.finditer(question or ""):
        g = find_place(con, m.group(1), state)
        if g:
            return g
    # "public records request, Charlottesville, Virginia": a comma-separated piece that is a place
    for piece in re.split(r"\s*[,;]\s*", question or "")[1:]:
        piece = _STATE_NAME.sub("", piece).strip(" ?.!")
        if 2 < len(piece) <= 40 and not re.search(r"\b(and|or|how|what|who|the)\b", piece, re.I):
            g = find_place(con, piece, state)
            if g:
                return g
    return None


def resolve_place(con, place: str | None, state: str | None = None) -> dict | None:
    """The ``place`` parameter of the API: a government id, a state code, or a name."""
    p = (place or "").strip()
    if not p:
        return None
    if re.fullmatch(r"\d{8,14}", p) and con:
        return db.one(con, "SELECT gov_id, name, kind, state, population, wikidata, website FROM governments "
                           "WHERE gov_id=?", p)
    if p.lower() in S.NAME:
        return {"state": p.lower()}
    if p.lower() in _NAME_BY_LOWER:
        return {"state": _NAME_BY_LOWER[p.lower()]}
    st = state_in(p) or state
    name = _STATE_NAME.sub("", re.sub(r"\(.*?\)", "", p)).strip(" ,")
    return find_place(con, name, st) if name else ({"state": st} if st else None)


# ---------------------------------------------------------------------------------------------------- routing
def _local_candidates(con, gov_id: str, topic: str | None, qwords: set[str]) -> list[dict]:
    """The place's researched processes that fit: category -> topic, or a shared content word (``dog`` ->
    ``dog_license``); best fit first."""
    out = []
    for p in db.rows(con, "SELECT gov_id, state, process, title, question, category, office, verified "
                          "FROM place_processes WHERE gov_id=? ORDER BY process", gov_id):
        ptopic = CATEGORY_TOPIC.get(p.get("category") or "")
        pw = words(p["process"].replace("_", " ")) | words(p.get("title") or "")
        shared = (qwords & pw) - GENERIC
        if (topic and ptopic == topic) or shared:
            out.append({**p, "topic": ptopic, "key": SC.key_for("process", gov_id, p["process"]),
                        "score": (2 if topic and ptopic == topic else 0) + len(shared), "scope": "local"})
    out.sort(key=lambda p: (-p["score"], p["process"]))
    return out


def route(question: str, place: str | None = None, con=None, decider=None) -> dict:
    """``{question, jurisdiction, gov_id, place, topic, topic_by, confidence, process_keys, processes, words}``.

    ``con`` is the database (opened when None); ``decider`` a ``lexflow.extract.decide.Decider`` for tests (else
    the shared one, when ``LEXFLOW_DECIDE=1``)."""
    own = con is None
    con = con or db.connect()
    try:
        q = " ".join((question or "").split())
        st = state_in(q)
        g = resolve_place(con, place, st) or place_in(con, q, st)
        if g and g.get("gov_id"):
            st = st or g["state"]
        elif g and g.get("state"):
            st, g = g["state"], None
        topic, by, conf = topic_by_rule(q), "rule", None
        if not topic:
            topic, conf = topic_by_model(q, decider)
            by = "decision" if topic else None
        qwords = words(q)
        processes: list[dict] = []
        if st:
            qs = QUESTION_OF_TOPIC.get(topic or "", [])
            for m in db.rows(con, "SELECT model_id, state, question, tier, title FROM process_models WHERE state=? "
                                  "ORDER BY model_id", st):
                if m["question"] in qs:
                    processes.append({**m, "key": SC.key_for("process", m["model_id"]), "scope": "state",
                                      "topic": SC.QUESTION_TOPIC.get(m["question"])})
        if g and g.get("gov_id"):
            processes += _local_candidates(con, g["gov_id"], topic, qwords)
        return {"question": q, "jurisdiction": st, "gov_id": g["gov_id"] if g else None,
                "place": {k: g.get(k) for k in ("gov_id", "name", "kind", "state", "population", "wikidata",
                                                "website")} if g else None,
                "topic": topic, "topic_label": TOPICS[topic].label if topic else None, "topic_by": by,
                "confidence": conf, "process_keys": [p["key"] for p in processes], "processes": processes,
                "words": sorted(qwords)}
    finally:
        if own:
            con.close()


# ---------------------------------------------------------------------------------------------------- answers
_BODY_DETAILS = """SELECT ?body ?key ?wd ?gd ?site ?cls ?clsLabel ?head ?headLabel ?headKey WHERE {
  VALUES ?body { %s }
  OPTIONAL { ?body lxt:{P:legal identifier} ?key }
  OPTIONAL { ?body lxt:{P:Wikidata item ID} ?wd }
  OPTIONAL { ?body lxt:{P:described at URL} ?gd }
  OPTIONAL { ?body lxt:{P:official website} ?site }
  OPTIONAL { ?body lxt:{P:instance of} ?cls . ?cls rdfs:label ?clsLabel . FILTER(lang(?clsLabel) = "en") }
  OPTIONAL { ?body lxt:{P:head position} ?head . ?head rdfs:label ?headLabel . FILTER(lang(?headLabel) = "en")
             OPTIONAL { ?head lxt:{P:legal identifier} ?headKey } }
}"""
_PARENT = """SELECT ?p ?pLabel ?key ?wd WHERE {
  VALUES ?body { %s }
  ?body lxt:{P:part of} ?p . ?p rdfs:label ?pLabel . FILTER(lang(?pLabel) = "en")
  OPTIONAL { ?p lxt:{P:legal identifier} ?key }
  OPTIONAL { ?p lxt:{P:Wikidata item ID} ?wd }
} LIMIT 1"""
_ROLE_QUOTE = """SELECT ?sec ?secLabel ?url ?quote ?pin WHERE {
  VALUES ?role { %s }
  ?role lxp:{P:authority conferred by} ?st . ?st lxps:{P:authority conferred by} ?sec .
  ?sec rdfs:label ?secLabel . FILTER(lang(?secLabel) = "en")
  OPTIONAL { ?sec lxt:{P:official text} ?url }
  OPTIONAL { ?st prov:wasDerivedFrom ?ref .
             OPTIONAL { ?ref lxpr:{P:quoted text} ?quote } OPTIONAL { ?ref lxpr:{P:pinpoint} ?pin } }
} LIMIT 3"""
_PROCESS_QUOTES = """SELECT ?sec ?secLabel ?url ?quote ?pin WHERE {
  VALUES ?process { %s }
  ?process lxp:{P:references} ?st . ?st lxps:{P:references} ?sec .
  ?sec rdfs:label ?secLabel . FILTER(lang(?secLabel) = "en")
  OPTIONAL { ?sec lxt:{P:official text} ?url }
  ?st prov:wasDerivedFrom ?ref . ?ref lxpr:{P:quoted text} ?quote .
  OPTIONAL { ?ref lxpr:{P:pinpoint} ?pin }
} LIMIT 4"""
_KEYS = """SELECT ?item ?key WHERE { VALUES ?item { %s } ?item lxt:{P:legal identifier} ?key }"""
# per step: the cited sections (P13 on the step, with the reference's quote and pinpoint) and, failing that, the
# source section of the step's time limit; the forms used; the fees
_STEP_SECTIONS = """SELECT ?step ?sec ?secLabel ?url ?quote ?pin ?how WHERE {
  VALUES ?step { %s }
  { ?step lxp:{P:references} ?st . ?st lxps:{P:references} ?sec . BIND("cites" AS ?how)
    OPTIONAL { ?st prov:wasDerivedFrom ?ref . OPTIONAL { ?ref lxpr:{P:quoted text} ?quote } OPTIONAL { ?ref lxpr:{P:pinpoint} ?pin } } }
  UNION
  { ?step lxp:{P:time limit} ?st . ?st prov:wasDerivedFrom ?ref . ?ref lxpr:{P:source section} ?sec . BIND("deadline" AS ?how)
    OPTIONAL { ?ref lxpr:{P:quoted text} ?quote } OPTIONAL { ?ref lxpr:{P:pinpoint} ?pin } }
  ?sec rdfs:label ?secLabel . FILTER(lang(?secLabel) = "en")
  OPTIONAL { ?sec lxt:{P:official text} ?url }
}"""
_STEP_FORMS = """SELECT ?step ?form ?formLabel ?url ?number WHERE {
  VALUES ?step { %s }
  ?step lxt:{P:form used} ?form . ?form rdfs:label ?formLabel . FILTER(lang(?formLabel) = "en")
  OPTIONAL { ?form lxt:{P:official text} ?url } OPTIONAL { ?form lxt:{P:form number} ?number }
}"""
_STEP_FEES = """SELECT ?step ?amount ?basis ?quote WHERE {
  VALUES ?step { %s }
  ?step lxp:{P:fee} ?st . ?st lxps:{P:fee} ?amount .
  OPTIONAL { ?st lxpq:{P:fee basis} ?basis }
  OPTIONAL { ?st prov:wasDerivedFrom ?ref . ?ref lxpr:{P:quoted text} ?quote }
}"""
# the offices of one government (its agency items), and the ones that are instances of an office type
_GOV_OFFICES = """SELECT ?office ?label ?type WHERE {
  VALUES ?gov { %s }
  ?office lxt:{P:part of} ?gov ; rdfs:label ?label . FILTER(lang(?label) = "en")
  OPTIONAL { ?office lxt:{P:instance of} ?type . ?type lxt:{P:instance of} lx:{Q:lexflow:class:office-type} }
}"""


def _step_details(store: _Store, steps: dict[str, dict]) -> None:
    """Fill each step's ``sections``, ``forms`` and ``fees`` (steps: iri -> step dict)."""
    if not steps:
        return
    terms = " ".join(store.term(i) for i in steps)
    for s in steps.values():
        s.setdefault("sections", []), s.setdefault("forms", []), s.setdefault("fees", [])
    cites = {}
    for r in store.run(_STEP_SECTIONS % terms):
        st = steps.get(_v(r, "step"))
        if st is None:
            continue
        entry = {"section": _v(r, "secLabel"), "pinpoint": _v(r, "pin"), "text": _v(r, "quote"),
                 "url": _v(r, "url") if privacy.is_office_url(_v(r, "url")) else None, "how": _v(r, "how")}
        cites.setdefault(st["iri"], []).append(entry)
    for iri, entries in cites.items():
        cited = [e for e in entries if e["how"] == "cites"]
        keep = cited or entries                      # the deadline's source section only when nothing is cited
        seen = set()
        for e in keep:
            k = (e["section"], e["pinpoint"], e["text"])
            if k not in seen:
                seen.add(k)
                steps[iri]["sections"].append({k2: e[k2] for k2 in ("section", "pinpoint", "text", "url")})
    for r in store.run(_STEP_FORMS % terms):
        st = steps.get(_v(r, "step"))
        if st is not None:
            st["forms"].append({"label": _v(r, "formLabel"), "number": _v(r, "number"),
                                "url": _v(r, "url") if privacy.is_office_url(_v(r, "url")) else None,
                                "lexipedia": _lexipedia(_v(r, "form"))})
    for r in store.run(_STEP_FEES % terms):
        st = steps.get(_v(r, "step"))
        if st is not None:
            st["fees"].append({"amount": _v(r, "amount"), "basis": _v(r, "basis"), "quote": _v(r, "quote")})


def _gov_offices(store: _Store, gov_key: str) -> list[dict]:
    try:
        rows = store.run(_GOV_OFFICES % store.term(store.iri(gov_key)))
    except Exception:
        return []
    out: dict[str, dict] = {}
    for r in rows:
        o = out.setdefault(_v(r, "office"), {"iri": _v(r, "office"), "label": _v(r, "label"), "types": set()})
        if _v(r, "type"):
            o["types"].add(_v(r, "type"))
    return list(out.values())


def _office_for(offices: list[dict], type_iri: str | None, role_label: str) -> dict | None:
    """The place's office that plays an office type: an instance of the type (P5) when the graph records one,
    else the office whose label has every content word of the role's name ("Commissioner of the revenue" ->
    "Commissioner of the Revenue (assessment); City Treasurer (billing and collection)"); the shortest wins."""
    if type_iri:
        inst = [o for o in offices if type_iri in o["types"]]
        if inst:
            return min(inst, key=lambda o: len(o["label"] or ""))
    rw = words(re.sub(r"\([^)]*\)", " ", role_label)) - GENERIC
    if not rw:
        return None
    hits = [o for o in offices if rw <= words(o["label"] or "")]
    return min(hits, key=lambda o: len(o["label"] or "")) if hits else None


class _Store:
    """One answer's view of the store: prepared, token-expanded queries run locally or live."""

    def __init__(self, live: bool = False):
        from ..publish import ids as I
        from ..publish import rdf
        from ..publish import sparql as SQ
        self.live = live
        self.rdf, self.SQ = rdf, SQ
        self.idmap = I.IdMap() if live else I.IdMap.for_turtle()
        self.store = None if live else rdf.open_store()        # FileNotFoundError when nothing is built

    def iri(self, key: str) -> str:
        return self.rdf.PREFIXES["lx"] + self.idmap.qid(key, live=self.live)

    def term(self, iri: str) -> str:
        return "<" + iri + ">"

    def run(self, text: str, params: dict | None = None, limit: int = 2000) -> list[dict]:
        q = self.SQ.prepare(text, params or {}, self.idmap, live=self.live)
        return list(self.rdf.query(self.store, q, live=self.live, limit=limit))

    def canned(self, name: str, params: dict) -> list[dict]:
        return self.run(self.SQ.get(name).text, params)


def _v(row: dict, var: str) -> str | None:
    b = row.get(var)
    return b.get("value") if b else None


def _lexipedia(iri: str | None) -> str | None:
    m = re.search(r"/entity/(Q\d+)$", iri or "")
    return LEXIPEDIA_ITEM + m.group(1) if m and int(m.group(1)[1:]) < 900_000 else None


def _links(wd: str | None, gd: str | None) -> dict:
    qid = (re.search(r"Q\d+", wd or "") or [None])[0] if wd else None
    return {"wikidata_qid": qid, "wikidata": WIKIDATA_WIKI + qid if qid else None,
            "govdirectory": gd if gd and privacy.is_office_url(gd) else None}


def channel_ok(kind: str, value: str | None, label: str | None = None, owner=None) -> bool:
    """The privacy gate every channel shown passes: the shape checks of ``privacy.is_office_channel`` with the
    row's label, or (a store row carries no label) the value checks alone for phones; ``govdirectory`` is a link."""
    if kind == "govdirectory":
        return privacy.is_office_url(value)
    if kind == "phone" and not label:
        return privacy.office_phone_value(value, owner) is not None
    v = value or ""
    if kind == "email":
        v = v.removeprefix("mailto:")
    return privacy.is_office_channel(kind, v, label, owner)


def _channel(kind: str, value: str, label: str | None, source: str | None, retrieved: str | None, owner) -> dict | None:
    if not value or not channel_ok(kind, value, label, owner):
        return None
    v = value.removeprefix("mailto:") if kind == "email" else value
    if kind in ("office", "postal"):
        v = privacy.office_value(v, owner) or ""
    if kind == "phone":
        v = privacy.office_phone_value(v, owner) or ""
    if not v:
        return None
    return {"kind": "postal" if kind == "office" else kind, "value": v, "label": privacy.office_label(label, owner),
            "source": privacy.office_source(source), "retrieved": (retrieved or "")[:10] or None}


def table_channels(con, owner_key: str, owner_name, question: str = "general") -> list[dict]:
    """The ``contacts`` rows of one owner (a government id or a body key, after ``lexflow.municipal.agencies
    --load``) that pass the privacy checks.  General mailboxes are shown only when a check found them on the
    office's own page (the row's source is that page)."""
    out = []
    for r in db.rows(con, "SELECT kind, value, label, source, updated_at FROM contacts WHERE gov_id=? AND question=? "
                          "ORDER BY kind, value", owner_key, question):
        if r["kind"] == "email" and question == "general" and not (r["source"] or "").startswith("http"):
            continue
        c = _channel(r["kind"], r["value"], r["label"], r["source"], r["updated_at"], owner_name)
        if c:
            out.append(c)
    return out


def _merge(*lists: list[dict]) -> list[dict]:
    seen, out = set(), []
    for lst in lists:
        for c in lst:
            k = (c["kind"], c["value"].strip().lower().rstrip("/"))
            if k not in seen:
                seen.add(k)
                out.append(c)
    order = {"website": 0, "page": 1, "email": 2, "phone": 3, "postal": 4, "govdirectory": 5}
    return sorted(out, key=lambda c: order.get(c["kind"], 9))


def _body_card(store: _Store, con, iri: str, label: str) -> dict:
    """A body's details, parent chain, channels and links from the store (and the contacts table)."""
    d = (store.run(_BODY_DETAILS % store.term(iri)) or [{}])[0]
    key = _v(d, "key")
    chain, cur, seen = [], iri, set()
    while cur and cur not in seen and len(chain) < 8:
        seen.add(cur)
        p = store.run(_PARENT % store.term(cur))
        if not p:
            break
        cur = _v(p[0], "p")
        chain.append({"iri": cur, "label": _v(p[0], "pLabel"), "key": _v(p[0], "key"),
                      "lexipedia": _lexipedia(cur), **_links(_v(p[0], "wd"), None)})
    owner = [label] + [c["label"] for c in chain[:1] if c.get("label")]
    chans: list[dict] = []
    for r in store.canned("body-contacts", {"body": iri.rsplit("/", 1)[-1]}):
        kind = _v(r, "kind")
        if kind in ("website", "page", "email", "phone", "postal"):
            c = _channel(kind, _v(r, "value") or "", None, _v(r, "source"), _v(r, "retrieved"), owner)
            if c:
                chans.append(c)
    if con and key:
        chans = _merge(chans, table_channels(con, key, owner))
    gd = _v(d, "gd") or next((c["value"] for c in chans if c["kind"] == "govdirectory"), None)
    chans = [c for c in chans if c["kind"] != "govdirectory"]
    if not gd and _v(d, "wd"):                               # the read-only cache of lexflow.publish.govdirectory
        from ..publish import govdirectory as GD
        gd = GD.page_url(_v(d, "wd"), (key or "").split(":")[2] if key else None, check=False)
    head = {"iri": _v(d, "head"), "label": _v(d, "headLabel"), "key": _v(d, "headKey"),
            "lexipedia": _lexipedia(_v(d, "head"))} if _v(d, "head") else None
    return {"iri": iri, "key": key, "label": label, "class": _v(d, "clsLabel"), "lexipedia": _lexipedia(iri),
            "chain": chain, "head": head, "channels": chans, "links": _links(_v(d, "wd"), gd)}


def _quotes(rows: list[dict]) -> list[dict]:
    out = []
    for r in rows:
        if _v(r, "quote") or _v(r, "secLabel"):
            out.append({"section": _v(r, "secLabel"), "pinpoint": _v(r, "pin"), "text": _v(r, "quote"),
                        "url": _v(r, "url") if privacy.is_office_url(_v(r, "url")) else None})
    return out


def _roles_from_store(store: _Store, con, jurisdiction_key: str, wanted: dict[str, dict],
                      place: dict | None = None) -> list[dict]:
    """``who-does-what`` for one jurisdiction item, kept to the wanted process keys (iri -> process), grouped by
    role.  With ``place`` (the government the question names), a state role played by an office *type* (the
    commissioner of the revenue) resolves to that place's own office and shows its channels."""
    rows = store.canned("who-does-what", {"jurisdiction": jurisdiction_key})
    by_role: dict[str, dict] = {}
    bodies: dict[str, dict] = {}
    step_iris: list[str] = []
    all_steps: dict[str, dict] = {}
    for r in rows:
        p = _v(r, "process")
        if p not in wanted:
            continue
        role = _v(r, "role") or f"{_v(r, 'step')}#norole"
        card = by_role.get(role)
        if card is None:
            card = by_role[role] = {"iri": _v(r, "role"), "key": None,
                                    "label": _v(r, "roleLabel") or "(no bearer named)",
                                    "lexipedia": _lexipedia(_v(r, "role")),
                                    "process": {"key": wanted[p]["key"], "label": _v(r, "processLabel"),
                                                "iri": p, "scope": wanted[p]["scope"], "lexipedia": _lexipedia(p)},
                                    "played_by": None, "steps": [], "quotes": [], "missing": []}
            b = _v(r, "body")
            if b:
                if b not in bodies:
                    bodies[b] = _body_card(store, con, b, _v(r, "bodyLabel") or "")
                card["played_by"] = bodies[b]
        step = {"iri": _v(r, "step"), "label": _v(r, "stepLabel"), "limit": _v(r, "limit"), "unit": _v(r, "unit"),
                "quote": _v(r, "quote"), "lexipedia": _lexipedia(_v(r, "step"))}
        if step["iri"] and all(s["iri"] != step["iri"] for s in card["steps"]):
            card["steps"].append(step)
            step_iris.append(step["iri"])
            all_steps[step["iri"]] = step
    _step_details(store, all_steps)
    offices = _gov_offices(store, SC.key_for("gov", place["gov_id"])) if place and place.get("gov_id") else []
    for card in by_role.values():
        pb = card["played_by"]
        is_type = bool(pb) and (pb.get("class") or "") in ("office type", "position type")
        if offices and card["process"]["scope"] == "state" and (is_type or pb is None):
            office = _office_for(offices, pb["iri"] if is_type else None, card["label"])
            if office:
                inst = bodies.get(office["iri"]) or _body_card(store, con, office["iri"], office["label"] or "")
                bodies[office["iri"]] = inst
                card["played_by"] = {**inst, "office_type": {"iri": pb["iri"], "label": pb["label"]} if is_type else None,
                                     "resolved_for": place.get("name")}
            elif is_type:
                card["missing"].append(f"no {pb['label']} office recorded for {place.get('name')}")
    role_iris = [c["iri"] for c in by_role.values() if c["iri"]]
    if role_iris:
        keys = {_v(r, "item"): _v(r, "key") for r in store.run(_KEYS % " ".join(store.term(i) for i in role_iris))}
        for c in by_role.values():
            c["key"] = keys.get(c["iri"])
    for role, card in by_role.items():
        pb = card["played_by"]
        if pb and pb.get("channels") and card["process"]["scope"] == "local" and con:
            # a body shared by several local processes (the Treasurer): the channels this process's own pages gave
            # come first, the rest after, and the list stays short
            gid, pid = card["process"]["key"].split(":")[2:4]
            own = table_channels(con, gid, pb["label"], question=pid)
            own_src = {c["source"] for c in own if c.get("source")} | {(c["kind"], c["value"]) for c in own}
            first = [c for c in pb["channels"] if c.get("source") in own_src or (c["kind"], c["value"]) in own_src]
            rest = [c for c in pb["channels"] if c not in first]
            card["played_by"] = pb = {**pb, "channels": (first + rest)[:CHANNELS_MAX],
                                      "channels_more": max(0, len(first) + len(rest) - CHANNELS_MAX)}
        if card["iri"]:
            card["quotes"] = _quotes(store.run(_ROLE_QUOTE % store.term(card["iri"])))
        if not card["quotes"] and card["process"]["iri"]:
            card["quotes"] = _quotes(store.run(_PROCESS_QUOTES % store.term(card["process"]["iri"])))[:2]
        pb = card["played_by"]
        if pb is None:
            card["played_by"] = {"kind": "unknown", "label": "no body recorded yet"}
            card["missing"].append("no body plays this role yet (played by is not recorded)")
        elif pb["key"] == SC.PRIVATE_PARTY or (pb["label"] or "").lower() == "private party":
            card["played_by"] = {"kind": "private-party", "label": "you, or a private party", "key": SC.PRIVATE_PARTY}
        else:
            pb["kind"] = {"government agency": "body", "organizational unit": "unit", "court": "court",
                          "office type": "office type", "position": "post", "position type": "post type",
                          "government": "government"}.get(pb.get("class") or "", "body")
            if not pb["channels"]:
                card["missing"].append(f"no office channel recorded for {pb['label']}")
            if not pb["links"]["wikidata"]:
                card["missing"].append(f"no Wikidata item recorded for {pb['label']}")
        if not card["quotes"]:
            card["missing"].append("no statute quote recorded for this role")
    return list(by_role.values())


def _process_entries(processes: list[dict]) -> dict[str, dict]:
    return {p["key"]: p for p in processes}


def answer(route_: dict, con=None, live: bool = False) -> dict:
    """The answer for a ``route`` (see the module docstring); ``source`` says where it came from."""
    own = con is None
    con = con or db.connect()
    try:
        st, gid = route_.get("jurisdiction"), route_.get("gov_id")
        procs = route_.get("processes") or []
        out: dict[str, Any] = {"route": route_, "source": None, "roles": [], "local": [], "place": None,
                               "missing": [], "sparql": None}
        if not st:
            out["missing"].append("name a state or a place (\"in Virginia\", \"in Charlottesville\")")
        if not route_.get("topic"):
            out["missing"].append("no topic recognised: say what you want to do (records, a business, a permit, "
                                  "a licence, voting, taxes, a court matter)")
        if st:
            out["sparql"] = {"query": "who-does-what", "params": {"jurisdiction": SC.key_for("jurisdiction", st)}}
        try:
            store = _Store(live=live) if st else None
        except (FileNotFoundError, ImportError) as e:     # no store built, or pyoxigraph not installed
            store = None
            if isinstance(e, ImportError):
                out["missing"].append("pyoxigraph is not installed, so the local store cannot be read")
        if store is not None:
            out["source"] = "live" if live else "store"
            by_key = _process_entries(procs)
            wanted = {store.iri(k): p for k, p in by_key.items()}
            state_keys = {k: p for k, p in by_key.items() if p["scope"] == "state"}
            if state_keys:
                out["roles"] = _roles_from_store(store, con, SC.key_for("jurisdiction", st), wanted, route_.get("place"))
            if gid and any(p["scope"] == "local" for p in procs):
                out["local"] = _roles_from_store(store, con, SC.key_for("gov", gid), wanted)
            if gid:
                out["place"] = _place_card(store, con, route_["place"])
        else:
            out["source"] = "facts"
            out["roles"] = _roles_from_facts(con, [p for p in procs if p["scope"] == "state"])
            out["local"] = _local_from_facts(con, [p for p in procs if p["scope"] == "local"])
            if gid:
                out["place"] = _place_card(None, con, route_["place"])
            if st:
                out["missing"].append("the local SPARQL store is not built (lexflow sparql --build); answered from "
                                      "the models' facts")
        if st and route_.get("topic") and not procs:
            out["missing"].append(f"no process on {TOPICS[route_['topic']].label} is modelled for "
                                  f"{S.NAME.get(st, st)}" + (f" or {route_['place']['name']}" if route_.get("place") else ""))
        if not gid and st:
            out["missing"].append("no place named: local processes (\"ask the locality\") need a city, county or town")
        return out
    finally:
        if own:
            con.close()


def _place_card(store: _Store | None, con, g: dict | None) -> dict | None:
    if not g:
        return None
    owner = g.get("name") or ""
    chans = table_channels(con, g["gov_id"], owner) if con else []
    if g.get("website") and privacy.is_office_url(g["website"]):
        chans = _merge([{"kind": "website", "value": g["website"], "label": "Official website", "source": "census-gus-2022",
                         "retrieved": None}], chans)
    card = {"gov_id": g["gov_id"], "label": f"{g.get('name')}, {S.NAME.get(g.get('state'), g.get('state'))}",
            "kind": g.get("kind"), "channels": chans, "links": _links(g.get("wikidata"), None), "lexipedia": None}
    if store is not None:
        try:
            iri = store.iri(SC.key_for("gov", g["gov_id"]))
            card["lexipedia"] = _lexipedia(iri)
            d = (store.run(_BODY_DETAILS % store.term(iri)) or [{}])[0]
            if _v(d, "wd"):
                card["links"] = _links(_v(d, "wd"), _v(d, "gd"))
        except Exception:
            pass
    return card


# ------------------------------------------------------------------------------------- without a store: facts
_ACTORS = re.compile(r"model (\w\w)/(\w+): actors?\s+([a-z_]+)(?:\s*\([^)]*\))?(?:,?\s+(?:and\s+)?([a-z_]+))?")
_agencies_cache: dict = {}


def _agency_bodies() -> dict[tuple[str, str, str], dict]:
    """(state, question, actor id) -> the agencies fixture's body, for the exact matches."""
    if "map" not in _agencies_cache:
        m: dict[tuple[str, str, str], dict] = {}
        try:
            data = json.loads(Path(AGENCIES).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = {}
        for b in data.get("bodies", []):
            if b.get("match") != "exact" or not b.get("qid"):
                continue
            for mm in _ACTORS.finditer(b.get("source") or ""):
                st, q = mm.group(1), mm.group(2)
                for a in (mm.group(3), mm.group(4)):
                    if a and a != "and":
                        m[(st, q, a)] = b
        _agencies_cache["map"] = m
    return _agencies_cache["map"]


def _roles_from_facts(con, procs: list[dict]) -> list[dict]:
    out = []
    bodies = _agency_bodies()
    for p in procs:
        m = db.one(con, "SELECT model_id, state, question, title, facts FROM process_models WHERE model_id=?", p["model_id"])
        if not m:
            continue
        facts = db.loads(m["facts"], {}) or {}
        st, q = m["state"], m["question"]
        steps_of: dict[str, list] = {}
        for s in facts.get("steps", []):
            src = s.get("source") or {}
            steps_of.setdefault(s.get("actor") or "", []).append(
                {"iri": None, "label": s.get("action"), "limit": None, "unit": None, "quote": src.get("quote"),
                 "lexipedia": None, "forms": [], "fees": [],
                 "sections": [{"section": src.get("section"), "pinpoint": src.get("subsection"),
                               "text": src.get("quote"), "url": None}] if src.get("section") else []})
        for a in facts.get("actors", []):
            src = a.get("source") or {}
            key = SC.key_for("role", st, q, a.get("id") or "")
            card = {"iri": None, "key": key, "label": f"{a.get('name') or a.get('id')} ({S.NAME.get(st, st)})",
                    "lexipedia": None, "process": {"key": p["key"], "label": m["title"] or p["model_id"], "iri": None,
                                                   "scope": "state", "lexipedia": None},
                    "played_by": None, "steps": steps_of.get(a.get("id"), []),
                    "quotes": [{"section": src.get("section"), "pinpoint": src.get("subsection"),
                                "text": src.get("quote"), "url": None}] if src.get("quote") else [], "missing": []}
            if a.get("kind") == "private-party":
                card["played_by"] = {"kind": "private-party", "label": "you, or a private party", "key": SC.PRIVATE_PARTY}
            else:
                b = bodies.get((st, q, a.get("id")))
                if b:
                    name = b.get("resolved_name") or ""
                    bkey = SC.key_for("position" if b.get("item_kind") == "position" else "agency", st, name)
                    chans = [c for c in [_channel("website", b.get("website") or "", "Official website", "wikidata", None, name)]
                             if c]
                    chans = _merge(chans, table_channels(con, bkey, name))
                    card["played_by"] = {"iri": None, "key": bkey, "label": name, "kind": "post" if b.get("item_kind") == "position" else "body",
                                         "class": b.get("item_kind"), "lexipedia": None, "chain": [], "head": None,
                                         "channels": chans, "links": _links(b.get("qid"), b.get("govdirectory_url"))}
                    if not chans:
                        card["missing"].append(f"no office channel recorded for {name}")
                else:
                    card["played_by"] = {"kind": "unknown", "label": "no body recorded yet"}
                    card["missing"].append("no body plays this role yet")
            if not card["quotes"]:
                card["missing"].append("no statute quote recorded for this role")
            out.append(card)
    return out


def _local_from_facts(con, procs: list[dict]) -> list[dict]:
    out = []
    for p in procs:
        row = db.one(con, "SELECT p.*, g.name AS gov_name FROM place_processes p JOIN governments g USING (gov_id) "
                          "WHERE p.gov_id=? AND p.process=?", p["gov_id"], p["process"])
        if not row:
            continue
        spec = db.loads(row["spec"], {}) or {}
        office = spec.get("office") or row.get("office") or "The office"
        owner = (row["gov_name"], office)
        chans = table_channels(con, row["gov_id"], owner, question=row["process"])
        quotes = [{"section": lb.get("citation"), "pinpoint": None, "text": lb.get("quote"),
                   "url": lb.get("url") if privacy.is_office_url(lb.get("url")) else None}
                  for lb in (spec.get("legal_basis") or []) if lb.get("quote")][:3]
        steps = [{"iri": None, "label": s.get("title") or s.get("action") or s.get("id"), "limit": None, "unit": None,
                  "quote": None, "lexipedia": None} for s in spec.get("steps") or []]
        proc = {"key": p["key"], "label": row.get("title") or row["process"], "iri": None, "scope": "local",
                "lexipedia": None}
        out.append({"iri": None, "key": SC.key_for("role", row["gov_id"], row["process"], "office"),
                    "label": f"{office} ({row['gov_name']})", "lexipedia": None, "process": proc, "steps": steps,
                    "played_by": {"iri": None, "key": SC.key_for("agency", row["gov_id"], office), "label": office,
                                  "kind": "body", "class": "government agency", "lexipedia": None, "head": None,
                                  "chain": [{"label": f"{row['gov_name']}, {S.NAME.get(row['state'], row['state'])}",
                                             "key": SC.key_for("gov", row["gov_id"]), "iri": None, "lexipedia": None,
                                             **_links(None, None)}],
                                  "channels": chans, "links": _links(None, None)},
                    "quotes": quotes, "missing": ([] if chans else [f"no office channel recorded for {office}"])
                    + ([] if quotes else ["no statute quote recorded for this process"])})
        out.append({"iri": None, "key": SC.key_for("role", row["gov_id"], row["process"], "applicant"),
                    "label": f"Person using the process ({row['gov_name']})", "lexipedia": None, "process": proc,
                    "steps": [], "played_by": {"kind": "private-party", "label": "you, or a private party",
                                               "key": SC.PRIVATE_PARTY}, "quotes": [], "missing": []})
    return out


def ask(question: str, place: str | None = None, con=None, live: bool = False, decider=None) -> dict:
    """``answer(route(question, place))`` on one connection."""
    own = con is None
    con = con or db.connect()
    try:
        return answer(route(question, place, con, decider), con, live=live)
    finally:
        if own:
            con.close()


# --------------------------------------------------------------------------------------------------------- text
def render(a: dict) -> str:
    """The answer as plain text (the CLI and the report)."""
    r = a["route"]
    L = [f"Q: {r['question']}", f"jurisdiction: {r.get('jurisdiction')}  place: {(r.get('place') or {}).get('name')}  "
                                f"topic: {r.get('topic')} ({r.get('topic_by')})  source: {a['source']}"]

    def card(c):
        pb = c["played_by"] or {}
        L.append(f"- ROLE {c['label']}  [{c['process']['label']}]")
        L.append(f"    played by: {pb.get('label')} ({pb.get('kind')})"
                 + (f"  [the {pb['office_type']['label']} of {pb.get('resolved_for')}]" if pb.get("office_type")
                    else f"  [resolved for {pb['resolved_for']}]" if pb.get("resolved_for") else ""))
        if pb.get("chain"):
            L.append("    parent chain: " + " > ".join(x["label"] or "?" for x in pb["chain"]))
        if pb.get("head"):
            L.append(f"    head: {pb['head']['label']}")
        for ch in pb.get("channels") or []:
            L.append(f"    {ch['kind']}: {ch['value']}" + (f"  ({ch['label']})" if ch.get("label") else "")
                     + (f"  source {ch['source']}" if ch.get("source") else "") + (f" {ch['retrieved']}" if ch.get("retrieved") else ""))
        links = pb.get("links") or {}
        if links.get("wikidata") or links.get("govdirectory"):
            L.append(f"    links: {links.get('wikidata') or ''} {links.get('govdirectory') or ''}".rstrip())
        for q in c.get("quotes") or []:
            L.append(f"    quote ({q.get('section')}{' ' + q['pinpoint'] if q.get('pinpoint') else ''}): \"{(q.get('text') or '')[:160]}\"")
        for s in c.get("steps") or []:
            lim = f" [{s['limit']} {s['unit'] or ''}]" if s.get("limit") else ""
            L.append(f"    step: {s['label']}{lim}")
            for sec in s.get("sections") or []:
                L.append(f"      cites {sec['section']}{' ' + sec['pinpoint'] if sec.get('pinpoint') else ''}"
                         + (f": \"{sec['text'][:120]}\"" if sec.get("text") else ""))
            for f in s.get("forms") or []:
                L.append(f"      form: {f['label']}" + (f" ({f['number']})" if f.get("number") else "") + (f" {f['url']}" if f.get("url") else ""))
            for fee in s.get("fees") or []:
                L.append(f"      fee: ${fee['amount']}" + (f" {fee['basis']}" if fee.get("basis") else ""))
        for m in c.get("missing") or []:
            L.append(f"    missing: {m}")
    for c in a["roles"]:
        card(c)
    if a["local"]:
        L.append("ask the locality:")
        for c in a["local"]:
            card(c)
    if a.get("place"):
        p = a["place"]
        L.append(f"place: {p['label']}  " + "; ".join(f"{c['kind']} {c['value']}" for c in p["channels"]))
    for m in a.get("missing") or []:
        L.append(f"missing: {m}")
    return "\n".join(L)


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="python -m lexflow.ask.who", description="Who do I ask?")
    ap.add_argument("question")
    ap.add_argument("--place")
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    out = ask(a.question, a.place, live=a.live)
    print(json.dumps(out, indent=1, ensure_ascii=False) if a.json else render(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
