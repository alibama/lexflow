"""Coverage: do we have adequate data to answer the questions people actually ask?

``fixtures/coverage/questions.json`` holds the questions (a topic slug of ``schema.VOCAB["topic"]``, an audience,
a level and the kinds of facts an adequate answer needs: who, steps, deadline, fee, form, where, appeal).
``curated_ask/coverage/<state>/<qid>.json`` holds the gold: the nuggets a correct answer must contain, each with
its citation and a verbatim quote from Open US Law's index text (``source: index``) or from a researched local
process file (``source: local``); ``gold: none`` says no grounding was found rather than inventing one.

For every question x jurisdiction (and x place when the question's level allows and a place is given):

1. route it (``lexflow.ask.who.route``) and read the who-answer from the local store;
2. probe the Wikibase by SPARQL (live, falling back to the local store): the process items for the topic and
   jurisdiction, their review status, steps with bearers, bearers resolved to bodies, bodies with channels,
   deadlines with quotes, forms, fees, escalation, cited sections, and a local process for the place;
3. with the ``ollama`` arm, answer with the ask pipeline (retrieval over the statute index) plus the Wikibase
   facts of the who-answer as extra quotes, the local chat model writing the summary, and score it against the
   gold with the AskBench scorer (nugget recall, citation precision, quote verification); without gold only the
   coverage is reported;
4. a verdict per cell, adequate / partial / none, with the kinds of facts still missing.

Rows go to this copy's own ``coverage_runs`` table (never synced); a run writes ``docs/coverage-<run>.json`` and the
Markdown matrix ``docs/coverage.md``.  A run is resumable (cells already stored under the run id are skipped) and
shardable by state; ``--node`` pins the model calls to one node of ``LEXFLOW_LLM_NODES`` (or the pool of
``lexflow.compute`` when that exists), else the node recorded is ``OLLAMA_URL``.

The gap-filling loop (``fill``, ``lexflow run coverage --fill``): every state-level cell of the latest run whose
verdict is none, or partial with steps or who still missing, is answered with the ask pipeline (the question
registered in asked_questions under the coverage qid, the answer stored in asked_answers with the node and model in
its metrics).  ``lexflow sparql --build`` then puts those answers in the local store as draft process items
(``lexflow.publish.graph.Build.asked``), the probe counts them apart (``counts.drafts``), and a cell that rests on
drafts alone is at most partial (``D`` in the matrix).
"""
from __future__ import annotations

import json
import os
import re
import statistics as st
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .. import config, validate
from ..municipal import states as S
from ..publish import schema as SC
from ..store import db

QUESTIONS_PATH = config.ROOT / "fixtures" / "coverage" / "questions.json"
GOLD_DIR = config.ROOT / "curated_ask" / "coverage"
DOCS_DIR = config.ROOT / "docs"
KINDS = ("who", "steps", "deadline", "fee", "form", "where", "appeal")
LEVELS = ("state", "local", "either")
GOLD_KINDS = ("index", "local", "mixed", "none")
SOURCES = ("index", "local", "unknown")
VERDICTS = ("adequate", "partial", "none")
ARMS = ("coverage", "ollama")
TOPICS = {v.slug for v in SC.VOCAB["topic"]}
AUDIENCES = {v.slug for v in SC.VOCAB["audience"]}
PLACES_BY_GOV = {"47210400100000": ("va", "charlottesville"), "47100200200000": ("va", "albemarle"),
                 "47213000100000": ("va", "staunton")}
ADEQUATE_VITAL = 0.5          # the vital-nugget recall an Ollama answer needs for its cell to count as adequate

TABLE = """
CREATE TABLE IF NOT EXISTS coverage_runs (
  run_id TEXT NOT NULL,
  qid TEXT NOT NULL,
  state TEXT NOT NULL,
  gov_id TEXT NOT NULL DEFAULT '',
  arm TEXT NOT NULL,
  model TEXT,
  node TEXT,
  probe TEXT,
  score TEXT,
  verdict TEXT,
  missing TEXT,
  seconds REAL,
  updated_at TEXT,
  PRIMARY KEY (run_id, qid, state, gov_id, arm)
);
CREATE INDEX IF NOT EXISTS coverage_runs_run ON coverage_runs(run_id);
"""


# ------------------------------------------------------------------------------------------------- questions
def questions(path: Path | str | None = None) -> list[dict]:
    p = Path(path) if path else QUESTIONS_PATH
    return json.loads(p.read_text(encoding="utf-8"))["questions"]


def question(qid: str) -> dict:
    for q in questions():
        if q["id"] == qid:
            return q
    raise KeyError(qid)


def check_questions(qs: list[dict]) -> list[str]:
    """Every problem with the question file (an empty list means it is usable)."""
    problems, ids = [], set()
    for q in qs:
        qid = q.get("id")
        if not qid or not re.fullmatch(r"[a-z][a-z0-9_]*", qid):
            problems.append(f"bad id {qid!r}")
        if qid in ids:
            problems.append(f"repeated id {qid}")
        ids.add(qid)
        if not (q.get("text") or "").strip():
            problems.append(f"{qid}: no text")
        if q.get("topic") not in TOPICS:
            problems.append(f"{qid}: topic {q.get('topic')!r} is not a schema topic slug")
        if q.get("audience") not in AUDIENCES:
            problems.append(f"{qid}: audience {q.get('audience')!r} is not a schema audience slug")
        if q.get("level") not in LEVELS:
            problems.append(f"{qid}: level must be one of {LEVELS}")
        needs = q.get("needs") or []
        if not needs or any(k not in KINDS for k in needs):
            problems.append(f"{qid}: needs must name kinds from {KINDS}")
        ph = q.get("phrasings") or []
        if not 2 <= len(ph) <= 3 or not all(isinstance(p, str) and p.strip() for p in ph):
            problems.append(f"{qid}: 2-3 phrasings expected")
    return problems


# ------------------------------------------------------------------------------------------------------ gold
def gold_path(state: str, qid: str) -> Path:
    return GOLD_DIR / state / f"{qid}.json"


def load_gold(state: str, qid: str) -> dict | None:
    p = gold_path(state, qid)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def gold_cases(states: list[str] | None = None) -> list[tuple[str, str]]:
    out = []
    for p in sorted(GOLD_DIR.glob("*/*.json")):
        if states is None or p.parent.name in states:
            out.append((p.stem, p.parent.name))
    return out


def local_file(gov_id: str, process: str) -> Path | None:
    place = PLACES_BY_GOV.get(gov_id)
    if not place:
        return None
    return config.ROOT / "curated" / "places" / place[0] / place[1] / f"{process}.json"


def _flatten(v) -> str:
    if isinstance(v, dict):
        return " ".join(_flatten(x) for x in v.values())
    if isinstance(v, list):
        return " ".join(_flatten(x) for x in v)
    return str(v) if v is not None else ""


def local_text(gov_id: str, process: str) -> str:
    """Every string of a researched local process file, for quote checks."""
    p = local_file(gov_id, process)
    if not p or not p.exists():
        return ""
    return _flatten(json.loads(p.read_text(encoding="utf-8")))


def check_gold(spec: dict, state: str | None = None, qid: str | None = None, skip_missing: bool = False) -> dict:
    """Every problem with a gold entry: shape, kinds, and each quote verified word for word against the statute
    index (``lexflow.ask.index``) or the local process file with lexflow's matcher (``validate.quote_in``).
    ``skip_missing`` ignores nuggets whose section is not in the index here (the tests' fixtures)."""
    from . import index as I
    problems: list[str] = []
    st_ = state or spec.get("state")
    if qid and spec.get("qid") != qid:
        problems.append(f"qid {spec.get('qid')!r} does not match the file {qid!r}")
    if state and spec.get("state") != state:
        problems.append(f"state {spec.get('state')!r} does not match the folder {state!r}")
    if spec.get("gold") not in GOLD_KINDS:
        problems.append(f"gold must be one of {GOLD_KINDS}")
    if spec.get("coverage") not in ("in_code", "partial", "not_in_code"):
        problems.append("coverage must be in_code, partial or not_in_code")
    nuggets = spec.get("nuggets") or []
    if spec.get("gold") == "none":
        if nuggets:
            problems.append("gold: none must carry no nuggets")
        return {"problems": problems, "nuggets": 0, "checked": 0, "ok": not problems}
    least = 1 if spec.get("coverage") == "partial" else 3        # a partial grounding may be a single enabling act
    if not least <= len(nuggets) <= 8:
        problems.append(f"{least}-8 nuggets expected (has {len(nuggets)})")
    if not any(n.get("importance") == "vital" for n in nuggets):
        problems.append("at least one vital nugget is needed")
    refs = {g.get("ref") for g in spec.get("gold_sections") or []}
    ids, checked = set(), 0
    for n in nuggets:
        nid = n.get("id")
        if not nid or nid in ids:
            problems.append(f"nugget id {nid!r} missing or repeated")
        ids.add(nid)
        if n.get("kind") not in KINDS:
            problems.append(f"{nid}: kind must be one of {KINDS}")
        if n.get("importance") not in ("vital", "okay"):
            problems.append(f"{nid}: importance must be vital or okay")
        if n.get("source") not in SOURCES:
            problems.append(f"{nid}: source must be one of {SOURCES}")
        q = (n.get("quote") or "").strip()
        sec = n.get("section") or ""
        # an office's name from a local file ("City Treasurer") may be two words; statute quotes need three
        least = 2 if (n.get("source") == "local" and n.get("kind") == "who") else 3
        if len(q.split()) < least:
            problems.append(f"{nid}: the quote is too short to check")
            continue
        if n.get("source") == "local" or sec.startswith("local:"):
            parts = sec.split(":")
            if len(parts) != 3:
                problems.append(f"{nid}: a local section is local:<gov_id>:<process>")
                continue
            text = local_text(parts[1], parts[2])
            if not text:
                problems.append(f"{nid}: no local process file for {sec}")
            elif not validate.quote_in(q, text):
                problems.append(f"{nid}: the quote is not word for word in {sec}: {q[:80]!r}")
            else:
                checked += 1
        elif n.get("source") == "index":
            if sec not in refs:
                problems.append(f"{nid}: section {sec!r} is not one of the gold sections")
            try:
                rows = I.lookup(st_, sec, with_text=True)
            except Exception as e:  # noqa: BLE001 - no index here
                rows = []
                if not skip_missing:
                    problems.append(f"{nid}: cannot read the {st_} index: {e}")
                    continue
            if not rows:
                if not skip_missing:
                    problems.append(f"{nid}: section {sec} is not in the {st_} index")
                continue
            if not any(validate.quote_in(q, r["text"]) for r in rows):
                problems.append(f"{nid}: the quote is not word for word in {sec}: {q[:80]!r}")
            else:
                checked += 1
    return {"problems": problems, "nuggets": len(nuggets), "checked": checked, "ok": not problems}


def as_reference(gold: dict) -> dict:
    """The gold as an AskBench reference (``lexflow.ask.bench.score`` reads coverage, gold_sections, nuggets,
    slots).  Local nuggets keep their quotes (the who-answer may show them); their sections are not statute refs."""
    return {"qid": gold["qid"], "state": gold["state"], "coverage": gold.get("coverage", "in_code"),
            "question_type": "facts", "gold_sections": gold.get("gold_sections") or [],
            "nuggets": [{"id": n["id"], "quote": n["quote"], "importance": n["importance"], "section": n["section"]}
                        for n in gold.get("nuggets") or []],
            "slots": gold.get("slots") or {}}


# ------------------------------------------------------------------------------------------------------ probe
_PROCESSES = """SELECT ?process ?label ?key ?topic ?status WHERE {
  VALUES ?j { %s }
  ?process lxt:{P:applies to jurisdiction} ?j ; lxt:{P:instance of} lx:{Q:legal process} ; rdfs:label ?label .
  FILTER(lang(?label) = "en")
  OPTIONAL { ?process lxt:{P:legal identifier} ?key }
  OPTIONAL { ?process lxt:{P:topic} ?topic }
  OPTIONAL { ?process lxt:{P:review status} ?s . ?s rdfs:label ?status . FILTER(lang(?status) = "en") }
}"""
_STEPS = """SELECT ?process ?step ?role ?body WHERE {
  VALUES ?process { %s }
  ?step lxt:{P:part of} ?process ; lxt:{P:instance of} lx:{Q:legal process step} .
  OPTIONAL { ?step lxt:{P:bearer} ?role . OPTIONAL { ?role lxt:{P:played by} ?body } }
}"""
_FACTS = """SELECT ?process ?kind ?x ?v ?quote WHERE {
  VALUES ?process { %s }
  ?x (lxt:{P:part of})? ?process .
  {
    ?x lxp:{P:time limit} ?st . ?st lxps:{P:time limit} ?v . BIND("deadline" AS ?kind)
    OPTIONAL { ?st prov:wasDerivedFrom ?ref . ?ref lxpr:{P:quoted text} ?quote }
  } UNION { ?x lxt:{P:form used} ?v . BIND("form" AS ?kind)
  } UNION { ?x lxt:{P:fee} ?v . BIND("fee" AS ?kind)
  } UNION { ?x (lxt:{P:escalates to}|lxt:{P:defers to}) ?v . BIND("escalation" AS ?kind)
  } UNION { ?x lxt:{P:references} ?v . BIND("section" AS ?kind) }
}"""
_CHANNELS = """SELECT ?body (COUNT(?v) AS ?n) WHERE {
  VALUES ?body { %s }
  ?body (lxt:{P:contact page URL}|lxt:{P:email address}|lxt:{P:phone number}|lxt:{P:official website}) ?v
} GROUP BY ?body"""
EMPTY_COUNTS = {"processes": 0, "reviewed": 0, "drafts": 0, "steps": 0, "steps_with_bearer": 0,
                "bearers_resolved": 0, "bodies": 0, "bodies_with_channels": 0, "deadlines": 0, "deadlines_quoted": 0,
                "forms": 0, "fees": 0, "escalation": 0, "sections": 0}


class Store:
    """One probe's view of a store: the live endpoint, or a local pyoxigraph store (``store`` given, or opened)."""

    def __init__(self, live: bool = True, store=None, idmap=None):
        from ..publish import ids as I
        from ..publish import rdf
        from ..publish import sparql as SQ
        self.live, self.rdf, self.SQ = live, rdf, SQ
        if store is not None:
            self.store, self.idmap = store, idmap or I.default()
        elif live:
            self.store, self.idmap = None, idmap or I.IdMap()
        else:
            self.store, self.idmap = rdf.open_store(), idmap or I.IdMap.for_turtle()
        self.calls = 0

    def iri(self, key: str) -> str:
        return self.rdf.PREFIXES["lx"] + self.idmap.qid(key, live=self.live)

    def term(self, key_or_iri: str) -> str:
        return "<" + (key_or_iri if key_or_iri.startswith("http") else self.iri(key_or_iri)) + ">"

    def run(self, text: str, limit: int = 2000) -> list[dict]:
        self.calls += 1
        q = self.SQ.prepare(text, {}, self.idmap, live=self.live)
        return list(self.rdf.query(self.store, q, live=self.live, limit=limit))


def _v(row: dict, var: str):
    b = row.get(var)
    return b.get("value") if b else None


def _counts(store: Store, procs: dict[str, dict]) -> dict:
    """The counts of EMPTY_COUNTS over the given process items (iri -> {key, label, status, scope})."""
    out = dict(EMPTY_COUNTS)
    out["processes"] = len(procs)
    out["reviewed"] = sum(1 for p in procs.values() if (p.get("status") or "") in ("reviewed", "agreed"))
    # draft process items: a state model of the single tier, or an asked answer published as a draft (graph.asked)
    out["drafts"] = sum(1 for p in procs.values() if (p.get("status") or "") == "draft")
    if not procs:
        return out
    terms = " ".join(store.term(i) for i in procs)
    private = store.iri(SC.PRIVATE_PARTY)
    steps, with_bearer, bodies = set(), set(), set()
    for r in store.run(_STEPS % terms):
        s = _v(r, "step")
        steps.add(s)
        if _v(r, "role"):
            with_bearer.add(s)
        b = _v(r, "body")
        if b and b != private:
            bodies.add(b)
    out.update(steps=len(steps), steps_with_bearer=len(with_bearer), bearers_resolved=len(bodies), bodies=len(bodies))
    if bodies:
        rows = store.run(_CHANNELS % " ".join(store.term(b) for b in bodies))
        out["bodies_with_channels"] = sum(1 for r in rows if int(float(_v(r, "n") or 0)) > 0)
    seen: dict[str, set] = {k: set() for k in ("deadline", "form", "fee", "escalation", "section")}
    quoted = set()
    for r in store.run(_FACTS % terms):
        kind, x, v = _v(r, "kind"), _v(r, "x"), _v(r, "v")
        seen[kind].add((x, v))
        if kind == "deadline" and _v(r, "quote"):
            quoted.add((x, v))
    out.update(deadlines=len(seen["deadline"]), deadlines_quoted=len(quoted), forms=len(seen["form"]),
               fees=len(seen["fee"]), escalation=len(seen["escalation"]), sections=len(seen["section"]))
    return out


def kinds_of(counts: dict) -> dict[str, bool]:
    """Which kinds of facts the probed items carry."""
    return {"who": counts["bearers_resolved"] > 0, "steps": counts["steps"] > 0,
            "deadline": counts["deadlines_quoted"] > 0, "fee": counts["fees"] > 0, "form": counts["forms"] > 0,
            "where": counts["bodies_with_channels"] > 0, "appeal": counts["escalation"] > 0}


def probe_with(store: Store, route: dict) -> dict:
    """The coverage probe on one store: the process items of the route's topic in the state (and in the place),
    plus the ones the route named, with the counts of what they carry."""
    topic = route.get("topic")
    topic_iri = store.iri(SC.key_for("vocab", "topic", topic)) if topic else None
    # the route's state models, and its local processes on the same topic (a local process the route matched on a
    # shared word alone, "public" in "public benefits", is not coverage of the question)
    wanted = {p["key"] for p in route.get("processes") or []
              if p.get("scope") == "state" or not topic or p.get("topic") == topic}
    found: dict[str, dict] = {}
    juris = [("state", SC.key_for("jurisdiction", route["jurisdiction"]))]
    if route.get("gov_id"):
        juris.append(("local", SC.key_for("gov", route["gov_id"])))
    for scope, jkey in juris:
        for r in store.run(_PROCESSES % store.term(jkey)):
            key = _v(r, "key") or ""
            if (topic_iri and _v(r, "topic") == topic_iri) or key in wanted:
                found[_v(r, "process")] = {"key": key, "label": _v(r, "label"), "status": _v(r, "status"),
                                           "scope": scope, "by_topic": _v(r, "topic") == topic_iri}
    counts = _counts(store, found)
    return {"processes": sorted(found.values(), key=lambda p: (p["scope"], p["key"])), "counts": counts,
            "state_process": any(p["scope"] == "state" for p in found.values()),
            "local_process": any(p["scope"] == "local" for p in found.values()), "kinds": kinds_of(counts),
            "sparql_calls": store.calls}


def route_for(con, q: dict, state: str, gov_id: str = "") -> dict:
    """``who.route`` for a question in a state or place; when the router recognises no topic the question file's
    topic stands in (``topic_by = "fixture"``, so the router's gap stays visible) and the processes are found
    the way the router finds them."""
    from . import who as W
    route = W.route(q["text"], place=gov_id or state, con=con)
    route["jurisdiction"] = route.get("jurisdiction") or state
    if gov_id and route.get("gov_id") != gov_id:
        route["gov_id"] = gov_id
    if not route.get("topic") and q.get("topic") in TOPICS:
        topic = q["topic"]
        route.update(topic=topic, topic_label=W.TOPICS[topic].label, topic_by="fixture")
        procs = []
        qs = W.QUESTION_OF_TOPIC.get(topic, [])
        for m in db.rows(con, "SELECT model_id, state, question, tier, title FROM process_models WHERE state=? "
                              "ORDER BY model_id", route["jurisdiction"]):
            if m["question"] in qs:
                procs.append({**m, "key": SC.key_for("process", m["model_id"]), "scope": "state",
                              "topic": SC.QUESTION_TOPIC.get(m["question"])})
        if route.get("gov_id"):
            procs += W._local_candidates(con, route["gov_id"], topic, set(route.get("words") or []))
        route["processes"] = procs
        route["process_keys"] = [p["key"] for p in procs]
    return route


def who_counts(who: dict) -> dict:
    """What the who-answer (``lexflow.ask.who.answer``) resolved: bodies, bodies with channels, deadlines."""
    cards = list(who.get("roles") or []) + list(who.get("local") or [])
    bodies = {(c.get("played_by") or {}).get("key") or (c.get("played_by") or {}).get("label")
              for c in cards if (c.get("played_by") or {}).get("kind") not in (None, "private-party", "unknown")}
    with_ch = {(c.get("played_by") or {}).get("key") or (c.get("played_by") or {}).get("label")
               for c in cards if (c.get("played_by") or {}).get("channels")}
    dl = [s for c in cards for s in c.get("steps") or [] if s.get("limit")]
    return {"source": who.get("source"), "roles": len(who.get("roles") or []), "local": len(who.get("local") or []),
            "bodies": len(bodies), "bodies_with_channels": len(with_ch), "deadlines": len(dl),
            "deadlines_quoted": sum(1 for s in dl if s.get("quote")), "missing": (who.get("missing") or [])[:6]}


def probe(route: dict, live: bool = True, store: Store | None = None) -> dict:
    """``probe_with`` on the live endpoint, falling back to the local store; with neither, empty counts."""
    errors = []
    tries = [store] if store is not None else ([Store(live=True)] if live else [])
    if store is None:
        tries.append("local")
    for s in tries:
        try:
            if s == "local":
                s = Store(live=False)
            out = probe_with(s, route)
            out["source"] = "live" if s.live else "store"
            out["errors"] = errors
            return out
        except Exception as e:  # noqa: BLE001 - the endpoint is down, or the store is not built
            errors.append(f"{'live' if getattr(s, 'live', s == 'live') else 'store'}: {type(e).__name__}: {str(e)[:200]}")
    return {"processes": [], "counts": dict(EMPTY_COUNTS), "state_process": False, "local_process": False,
            "kinds": kinds_of(EMPTY_COUNTS), "sparql_calls": 0, "source": "none", "errors": errors}


# ----------------------------------------------------------------------------------------------------- answer
_SEC = re.compile(r"§+\s*([0-9][\w.\-:]*)")


def _ref_of(label: str | None) -> str | None:
    """'Va. Code Ann. § 2.2-3704' -> '2.2-3704'; a bare number stays."""
    if not label:
        return None
    m = _SEC.search(label)
    return m.group(1) if m else (label.strip() if re.match(r"^[0-9][\w.\-:]*$", label.strip()) else None)


def wiki_quotes(who: dict) -> list[dict]:
    """The statute quotes the who-answer shows (roles' grounding quotes and the steps' cited sections), as extra
    quotes for the answer: ``{id: W1, section, text, label}``."""
    out, seen = [], set()
    for card in list(who.get("roles") or []) + list(who.get("local") or []):
        items = list(card.get("quotes") or [])
        for s in card.get("steps") or []:
            items += [{"section": c.get("section"), "text": c.get("text")} for c in s.get("sections") or []]
            if s.get("quote"):
                items.append({"section": None, "text": s["quote"]})
        for q in items:
            text = " ".join((q.get("text") or "").split())
            if len(text.split()) < 3 or text in seen:
                continue
            seen.add(text)
            out.append({"id": f"W{len(out) + 1}", "section": _ref_of(q.get("section")), "text": text,
                        "label": q.get("section") or "", "from": card.get("label")})
    return out


def answer_cell(con, q: dict, state: str, who: dict, asker=None, emb=None, log=print) -> dict:
    """The ask pipeline's answer for one question and state (retrieval over the statute index, no store), with
    the who-answer's quotes added, and the local model's summary over both when ``asker`` is given."""
    from ..municipal import statutes
    from . import answer as A
    from . import pipeline as AP
    from .plan import plan as make_plan
    t0 = time.time()
    plan = make_plan(q["text"], None)
    row = AP.answer_state(con, f"coverage_{q['id']}", plan, state, asker=None, emb=emb, store=False,
                          log=lambda *_: None)
    timings = {"retrieve_and_quote": round(time.time() - t0, 1)}
    if row.get("status") == "no-statutes":
        row["timings"] = timings
        return row
    ans = json.loads(row["answer"])
    extra = wiki_quotes(who)
    ans["quotes"] = list(ans.get("quotes") or []) + extra
    ans["wiki_quotes"] = len(extra)
    sections = json.loads(row["sections"]) if isinstance(row.get("sections"), str) else row.get("sections") or {}
    chosen = list(sections.get("chosen") or [])
    for w in extra:
        if w["section"] and w["section"] not in {c["ref"] for c in chosen}:
            chosen.append({"ref": w["section"], "title": w["label"]})
    if asker is not None and ans["quotes"]:
        t1 = time.time()
        try:
            ans["summary"] = A.summarise(asker, q["text"], S.NAME.get(state, state), ans["quotes"], chosen)
            row["model"] = asker.client.model
        except Exception as e:  # noqa: BLE001 - the model is down: the quotes still count
            ans["summary"] = None
            ans["summary_error"] = f"{type(e).__name__}: {str(e)[:200]}"
            log(f"  summary failed: {ans['summary_error']}")
        timings["summary"] = round(time.time() - t1, 1)
        row["status"] = AP.gate(sections, ans.get("summary")) if sections else row["status"]
    row["answer"] = json.dumps(ans, default=str)
    row["timings"] = timings
    row["seconds"] = round(time.time() - t0, 1)
    return row


def score_cell(gold: dict, row: dict) -> dict:
    """The AskBench score of an answer against the gold, plus which kinds of facts its quotes cover."""
    from . import bench as B
    ref = as_reference(gold)
    s = B.score(ref, row)
    ans = json.loads(row["answer"]) if isinstance(row.get("answer"), str) else row.get("answer") or {}
    shown = [q["text"] for q in ans.get("quotes") or []] + [x["quote"] for x in ans.get("steps") or []]
    kinds: dict[str, bool] = {}
    hit = []
    for n in gold.get("nuggets") or []:
        ok = B.covered(n["quote"], shown)
        if ok:
            hit.append(n["id"])
        kinds[n["kind"]] = kinds.get(n["kind"], False) or ok
    s["kinds"] = kinds
    s["nuggets_hit"] = hit
    s["wiki_quotes"] = ans.get("wiki_quotes", 0)
    s["claims"] = len((ans.get("summary") or {}).get("claims") or []) if isinstance(ans.get("summary"), dict) else None
    s["quotes_shown"] = len(shown)
    return s


# ---------------------------------------------------------------------------------------------------- verdict
def drafts_only(probe_: dict) -> bool:
    """Every process item the probe found is a draft (a ``single`` state model or an asked answer's draft): the
    cell rests on unreviewed items alone."""
    c = probe_.get("counts") or {}
    return bool(c.get("processes")) and c.get("drafts", 0) == c.get("processes", 0)


def verdict(q: dict, probe_: dict, score: dict | None, gold: dict | None) -> tuple[str, list[str]]:
    """adequate / partial / none, and the kinds the question needs that neither the Wikibase items nor the scored
    answer carry.  With no gold (or ``gold: none``) only the probe counts; with gold, an adequate cell also needs
    the answer's vital-nugget recall at ADEQUATE_VITAL or more.  A cell whose process items are all drafts is at
    most partial (``drafts_only``): a draft fills the gap but nobody has checked it."""
    needs = list(q.get("needs") or [])
    have = {k for k in needs if (probe_.get("kinds") or {}).get(k)}
    if score:
        have |= {k for k in needs if (score.get("kinds") or {}).get(k)}
    missing = [k for k in needs if k not in have]
    any_process = bool(probe_.get("processes"))
    cap = "partial" if drafts_only(probe_) else "adequate"
    recall = (score or {}).get("vital_recall")
    if gold is None or gold.get("gold") == "none" or score is None:
        if not any_process and not have:
            return "none", missing
        return (cap if not missing else "partial"), missing
    if not any_process and not (recall or 0) and not have:
        return "none", missing
    if not missing and (recall or 0) >= ADEQUATE_VITAL:
        return cap, missing
    return "partial", missing


# ------------------------------------------------------------------------------------------------------- runs
def ensure_table(con) -> None:
    con.executescript(TABLE)


def node_of(name: str | None) -> tuple[str, str]:
    """``(node name, Ollama URL)``: a node of ``LEXFLOW_LLM_NODES`` (``name=url|opts, ...``), the pool of
    ``lexflow.compute`` when that package exists, else ``OLLAMA_URL`` under the name of its host."""
    nodes: dict[str, str] = {}
    for part in (os.environ.get("LEXFLOW_LLM_NODES") or "").split(","):
        part = part.strip()
        if "=" in part:
            n, rest = part.split("=", 1)
            nodes[n.strip()] = rest.split("|", 1)[0].strip()
    from ..compute import nodes as CN
    if name:
        if name in nodes:
            return name, nodes[name]
        url = CN.url_of(name)                  # an overlay node the pool knows
        if url:
            return name, url
        raise ValueError(f"unknown node {name!r}: LEXFLOW_LLM_NODES names {sorted(nodes) or 'nothing'}"
                         + (f"; the pool has {', '.join(CN.names())}" if CN.pool_on() and CN.names() else ""))
    host = urlsplit(config.OLLAMA_URL).hostname or config.OLLAMA_URL
    for n, u in nodes.items():
        if u.rstrip("/") == config.OLLAMA_URL.rstrip("/"):
            return n, u
    return host, config.OLLAMA_URL


def asker_at(url: str, model: str | None = None):
    """The ask pipeline's asker on one Ollama URL, or None when the model is not there."""
    from ..extract.ollama import OllamaClient
    from ..extract.strategies import Asker
    import requests
    model = model or config.ASK_MODEL
    try:
        names = [m["name"] for m in requests.get(url.rstrip("/") + "/api/tags", timeout=10).json().get("models", [])]
    except Exception:  # noqa: BLE001
        return None
    if model not in names and f"{model}:latest" not in names:
        return None
    from ..compute import nodes as CN
    pin = CN.name_for_url(url) if CN.pool_on() else None          # with the pool on, the calls stay on this node
    return Asker(OllamaClient(base_url=url, model=model, num_ctx=4096, timeout=1800, node=pin), mode="schema",
                 max_tokens=400)


def cells_for(con, states: list[str], places: list[dict] | None, qs: list[dict]) -> list[tuple[dict, str, str]]:
    """(question, state, gov_id or '') for every question x state, and x place when the level allows."""
    out = []
    for st_ in states:
        for q in qs:
            out.append((q, st_, ""))
        for g in places or []:
            if g.get("state") != st_:
                continue
            for q in qs:
                if q["level"] in ("local", "either"):
                    out.append((q, st_, g["gov_id"]))
    return out


def _pick_llm(cells: list[tuple[dict, str, str]], per_state: int | None) -> set[tuple[str, str, str]]:
    """The cells that get the Ollama answer: all, or the first ``per_state`` state-level cells with gold."""
    if per_state is None:
        return {(q["id"], s, g) for q, s, g in cells}
    out, n = set(), {}
    for q, s, g in cells:
        if g:
            continue
        gold = load_gold(s, q["id"])
        if gold and gold.get("gold") != "none" and n.get(s, 0) < per_state:
            out.add((q["id"], s, g))
            n[s] = n.get(s, 0) + 1
    return out


def run(con, states: list[str], places: list[dict] | None = None, qids: list[str] | None = None,
        arm: str = "ollama", llm_cells: int | None = None, run_id: str | None = None, node: str | None = None,
        live: bool = True, force: bool = False, model: str | None = None, log=print, progress=None) -> dict:
    """The coverage test for the states (and places).  ``arm``: ``coverage`` probes only; ``ollama`` also answers
    and scores, for every cell or for ``llm_cells`` per state (the rest are stored under ``coverage``)."""
    from . import who as W
    ensure_table(con)
    run_id = run_id or time.strftime("%Y%m%d-%H%M")
    qs = [q for q in questions() if not qids or q["id"] in qids]
    cells = cells_for(con, states, places, qs)
    node_name, node_url = node_of(node)
    asker, emb = None, None
    if arm == "ollama":
        asker = asker_at(node_url, model)
        if asker is None:
            log(f"no chat model ({model or config.ASK_MODEL}) at {node_name} ({node_url}): answers are quotes only")
        try:
            from .pipeline import embedder
            emb = embedder()
        except Exception:  # noqa: BLE001
            emb = None
    llm = _pick_llm(cells, llm_cells) if arm == "ollama" else set()
    done = {(r["qid"], r["state"], r["gov_id"], r["arm"]) for r in
            db.rows(con, "SELECT qid, state, gov_id, arm FROM coverage_runs WHERE run_id=?", run_id)} if not force else set()
    log(f"coverage run {run_id}: {len(cells)} cells over {', '.join(states)} ({len(llm)} with the Ollama answer), "
        f"node {node_name}, {'live' if live else 'local'} probe; {len(done)} already stored")
    counts: dict[str, int] = {}
    store_cache: dict[str, Store | None] = {}
    for i, (q, st_, gid) in enumerate(cells):
        cell_arm = "ollama" if (q["id"], st_, gid) in llm else "coverage"
        if (q["id"], st_, gid, cell_arm) in done:
            if progress:
                progress((i + 1) / len(cells))
            continue
        t0 = time.time()
        timings: dict[str, float] = {}
        route = route_for(con, q, st_, gid)
        timings["route"] = round(time.time() - t0, 1)
        t1 = time.time()
        try:
            who = W.answer(route, con, live=False)
        except Exception as e:  # noqa: BLE001
            who = {"roles": [], "local": [], "missing": [f"who failed: {e}"], "source": None}
        timings["who"] = round(time.time() - t1, 1)
        t1 = time.time()
        if "probe" not in store_cache:
            try:
                store_cache["probe"] = Store(live=True) if live else Store(live=False)
            except Exception:  # noqa: BLE001
                store_cache["probe"] = None
        pr = probe(route, live=live, store=store_cache["probe"]) if store_cache["probe"] is not None \
            else probe(route, live=live)
        if pr["source"] == "none" and store_cache.get("probe") is not None and store_cache["probe"].live:
            pr = probe(route, live=False)        # the endpoint failed: the local store, once per cell
        timings["probe"] = round(time.time() - t1, 1)
        pr["route"] = {k: route.get(k) for k in ("jurisdiction", "gov_id", "topic", "topic_by", "process_keys")}
        pr["who"] = who_counts(who)
        # the who-answer reads the local store and the contacts table: a body it resolves, or a channel it shows,
        # counts even when the endpoint probed has not got the claim yet
        pr["counts_probe"] = dict(pr["counts"])
        pr["counts"]["bearers_resolved"] = max(pr["counts"]["bearers_resolved"], pr["who"]["bodies"])
        pr["counts"]["bodies"] = max(pr["counts"]["bodies"], pr["who"]["bodies"])
        pr["counts"]["bodies_with_channels"] = max(pr["counts"]["bodies_with_channels"], pr["who"]["bodies_with_channels"])
        pr["counts"]["deadlines_quoted"] = max(pr["counts"]["deadlines_quoted"], pr["who"]["deadlines_quoted"])
        pr["counts"]["deadlines"] = max(pr["counts"]["deadlines"], pr["who"]["deadlines"])
        pr["kinds"] = kinds_of(pr["counts"])
        pr["drafts_only"] = drafts_only(pr)
        gold = load_gold(st_, q["id"])
        score, model_used, answer_doc = None, None, None
        if cell_arm == "ollama":
            t1 = time.time()
            row = answer_cell(con, q, st_, who, asker=asker, emb=emb, log=log)
            timings["answer"] = round(time.time() - t1, 1)
            timings.update({f"answer.{k}": v for k, v in (row.get("timings") or {}).items()})
            model_used = row.get("model") or (asker.client.model if asker else None)
            ans = json.loads(row["answer"]) if isinstance(row.get("answer"), str) else row.get("answer") or {}
            sections = json.loads(row["sections"]) if isinstance(row.get("sections"), str) else row.get("sections") or {}
            answer_doc = {"status": row.get("status"), "chosen": [c.get("ref") for c in sections.get("chosen") or []],
                          "quotes": ans.get("quotes"), "steps": [{"step": s.get("step"), "section": s.get("section"),
                                                                    "quote": s.get("quote")} for s in ans.get("steps") or []],
                          "summary": ans.get("summary"), "summary_error": ans.get("summary_error"),
                          "markdown": ans.get("markdown")}
            if gold and gold.get("gold") != "none" and row.get("status") != "no-statutes":
                t1 = time.time()
                score = score_cell(gold, row)
                timings["score"] = round(time.time() - t1, 1)
        v, missing = verdict(q, pr, score, gold)
        seconds = round(time.time() - t0, 1)
        pr["timings"] = timings
        pr["gold"] = (gold or {}).get("gold") or "missing"
        pr["answer"] = answer_doc
        db.upsert(con, "coverage_runs", [{"run_id": run_id, "qid": q["id"], "state": st_, "gov_id": gid, "arm": cell_arm,
                                          "model": model_used, "node": node_name, "probe": json.dumps(pr, default=str),
                                          "score": json.dumps(score) if score else None, "verdict": v,
                                          "missing": json.dumps(missing), "seconds": seconds, "updated_at": db.now()}],
                  keys=("run_id", "qid", "state", "gov_id", "arm"), stamp=False)
        con.commit()
        counts[v] = counts.get(v, 0) + 1
        c = pr["counts"]
        log(f"{q['id']:<24} {st_}{('/' + gid) if gid else '':<16} {cell_arm:<8} {v:<8} missing {','.join(missing) or '-':<24} "
            f"wiki {pr['source']}: proc {c['processes']}{' (drafts)' if pr['drafts_only'] else ''} steps "
            f"{c['steps']}/{c['steps_with_bearer']} bodies {c['bearers_resolved']}"
            f"/{c['bodies_with_channels']} dl {c['deadlines_quoted']}/{c['deadlines']} forms {c['forms']} fees {c['fees']} "
            f"esc {c['escalation']}"
            + (f" · vital {score.get('vital_recall')} cite {score.get('citation_precision')} comp {score.get('composite')}"
               if score else "") + f" · {seconds}s")
        if progress:
            progress((i + 1) / len(cells))
    paths = write_reports(con, run_id, log=log)
    return {"run": run_id, "cells": len(cells), "verdicts": counts, "node": node_name, **paths}


# ------------------------------------------------------------------------------------------------------- fill
FILL_KINDS = ("steps", "who")      # a partial cell is a gap when one of these is still missing


def gap_cells(con, run_id: str, states: list[str], qids: list[str] | None = None) -> list[dict]:
    """The state-level cells of a run that the fill answers: verdict ``none``, or ``partial`` with steps or who
    still missing.  ``{qid, state, verdict, missing, gold}``, the cells with gold first (they can be scored), then
    in question order."""
    order = {q["id"]: i for i, q in enumerate(questions())}
    seen: dict[tuple[str, str], dict] = {}
    for r in db.rows(con, "SELECT qid, state, verdict, missing FROM coverage_runs WHERE run_id=? AND gov_id='' "
                          "ORDER BY state, qid", run_id):
        if r["state"] not in states or (qids and r["qid"] not in qids) or r["qid"] not in order:
            continue
        missing = db.loads(r["missing"], []) or []
        if r["verdict"] == "none" or (r["verdict"] == "partial" and set(missing) & set(FILL_KINDS)):
            g = load_gold(r["state"], r["qid"])
            seen[(r["qid"], r["state"])] = {"qid": r["qid"], "state": r["state"], "verdict": r["verdict"],
                                            "missing": missing, "gold": bool(g and g.get("gold") != "none")}
    return sorted(seen.values(), key=lambda c: (states.index(c["state"]), not c["gold"], order[c["qid"]]))


def fill_terms(q: dict) -> list[list[str]]:
    """The concept groups of the question's text, plus each phrasing's concepts the text does not already name
    (what ``asked_questions.terms`` records for the question)."""
    from .plan import STOP, plan as make_plan
    groups = [list(g) for g in make_plan(q["text"], None).groups]
    seen = {t for g in groups for t in g}
    for ph in q.get("phrasings") or []:
        for g in make_plan(ph, None).groups:
            g = [t for t in g if t.lower() not in STOP and len(t) > 2]     # "soon", "after": no concept of their own
            if g and not any(t in seen for t in g):
                groups.append(g)
                seen.update(g)
    return groups


def register_question(con, q: dict) -> str:
    """The coverage question as an asked question (id = the coverage qid, kind process, the phrasings' terms),
    unless one with that id is there already."""
    from .pipeline import db_json
    if db.one(con, "SELECT id FROM asked_questions WHERE id=?", q["id"]):
        return q["id"]
    db.upsert(con, "asked_questions", [{"id": q["id"], "text": q["text"].strip(), "kind": "process",
                                        "terms": db_json(fill_terms(q)), "created_at": db.now()}], keys=("id",))
    con.commit()
    return q["id"]


def filled(con, qid: str, state: str) -> dict | None:
    """The stored fill of a cell (an asked answer whose metrics carry ``coverage_fill``), or None."""
    r = db.one(con, "SELECT status, metrics FROM asked_answers WHERE question_id=? AND target=?", qid, state)
    if not r:
        return None
    m = db.loads(r["metrics"], {}) or {}
    return {"status": r["status"], **m["coverage_fill"]} if m.get("coverage_fill") else None


def fill(con, states: list[str], run_id: str | None = None, qids: list[str] | None = None,
         llm_cells: int | None = None, node: str | None = None, model: str | None = None, force: bool = False,
         log=print, progress=None, pipeline=None) -> dict:
    """Answer the gap cells of a coverage run (``gap_cells``: the latest run unless ``run_id`` names one) with the
    ask pipeline: the question is registered in asked_questions, then for each cell ``pipeline.answer_state``
    (retrieval over the statute index, quotes, the facts and the map, quote verification, the local model's
    summary when the node has it) stores the answer in asked_answers under target = state, with the node and model
    in its metrics (``coverage_fill``).  Resumable (a cell with a stored fill is skipped unless ``force``),
    shardable by state, at most ``llm_cells`` cells per state (the cells with gold come first).  ``pipeline``
    stands in for ``lexflow.ask.pipeline.answer_state`` (the tests' stub)."""
    from . import pipeline as AP
    from .plan import Plan, plan as make_plan
    ensure_table(con)
    run_id = run_id or latest_run(con)
    if not run_id:
        raise ValueError("no coverage run to fill: run `lexflow run coverage` first")
    answer_state = pipeline or AP.answer_state
    node_name, node_url = node_of(node)
    asker = asker_at(node_url, model) if pipeline is None else None
    if pipeline is None and asker is None:
        log(f"no chat model ({model or config.ASK_MODEL}) at {node_name} ({node_url}): drafts carry no summary")
    emb = None
    if pipeline is None:
        try:
            emb = AP.embedder()
        except Exception:  # noqa: BLE001
            emb = None
    cells = gap_cells(con, run_id, states, qids)
    todo: list[dict] = []
    per_state: dict[str, int] = {}
    for c in cells:
        if llm_cells is not None and per_state.get(c["state"], 0) >= llm_cells:
            continue
        per_state[c["state"]] = per_state.get(c["state"], 0) + 1
        todo.append(c)
    log(f"coverage fill of run {run_id}: {len(cells)} gap cells over {', '.join(states)}, {len(todo)} to answer"
        f"{f' (at most {llm_cells} per state)' if llm_cells is not None else ''}, node {node_name}"
        f"{f', model {asker.client.model}' if asker else ''}")
    qs = {q["id"]: q for q in questions()}
    counts: dict[str, int] = {"answered": 0, "partial": 0, "not_found": 0, "skipped": 0, "failed": 0}
    seconds: list[float] = []
    for i, c in enumerate(todo):
        q = qs[c["qid"]]
        prior = filled(con, q["id"], c["state"])
        if prior and not force:
            counts["skipped"] += 1
            log(f"{q['id']:<24} {c['state']:<4} skipped: filled {prior.get('at', '')} on {prior.get('node', '?')} ({prior['status']})")
            if progress:
                progress((i + 1) / len(todo))
            continue
        register_question(con, q)
        base = make_plan(q["text"], None)
        plan = Plan(text=q["text"].strip(), groups=base.groups, kind="process", goal=q["text"].strip().rstrip("?"),
                    source="coverage-fill", notes=list(base.notes))
        t0 = time.time()
        try:
            row = answer_state(con, q["id"], plan, c["state"], asker=asker, emb=emb, log=lambda *_: None, store=True)
        except Exception as e:  # noqa: BLE001 - one cell must not stop the fill
            counts["failed"] += 1
            log(f"{q['id']:<24} {c['state']:<4} failed: {type(e).__name__}: {str(e)[:200]}")
            continue
        took = round(time.time() - t0, 1)
        seconds.append(took)
        metrics = db.loads(row.get("metrics"), {}) if isinstance(row.get("metrics"), str) else dict(row.get("metrics") or {})
        metrics["coverage_fill"] = {"run": run_id, "node": node_name, "model": row.get("model") or (asker.client.model if asker else None),
                                    "at": db.now(), "verdict": c["verdict"], "missing": c["missing"], "seconds": took}
        con.execute("UPDATE asked_answers SET metrics=?, updated_at=? WHERE question_id=? AND target=?",
                    (json.dumps(metrics, default=str), db.now(), q["id"], c["state"]))
        con.commit()
        status = row.get("status") or "failed"
        counts[status] = counts.get(status, 0) + 1
        facts = db.loads(row.get("facts"), None) if isinstance(row.get("facts"), str) else row.get("facts")
        sections = db.loads(row.get("sections"), {}) if isinstance(row.get("sections"), str) else row.get("sections") or {}
        log(f"{q['id']:<24} {c['state']:<4} {status:<9} was {c['verdict']} missing {','.join(c['missing']) or '-':<22} "
            f"sections {len(sections.get('chosen') or [])} steps {len((facts or {}).get('steps') or [])} "
            f"quotes {metrics.get('quotes_checked', 0)}/{metrics.get('quote_misses', 0)} misses · {took}s")
        if progress:
            progress((i + 1) / len(todo))
    return {"run": run_id, "gap_cells": len(cells), "answered": len(seconds), "status": counts, "node": node_name,
            "seconds_mean": _mean(seconds), "seconds_total": round(sum(seconds), 1)}


# ---------------------------------------------------------------------------------------------------- reports
def rows_of(con, run_id: str) -> list[dict]:
    out = []
    for r in db.rows(con, "SELECT * FROM coverage_runs WHERE run_id=? ORDER BY state, gov_id, qid", run_id):
        r = dict(r)
        r["probe"] = db.loads(r["probe"], {}) or {}
        r["score"] = db.loads(r["score"], None)
        r["missing"] = db.loads(r["missing"], []) or []
        out.append(r)
    return out


def latest_run(con) -> str | None:
    ensure_table(con)
    return db.scalar(con, "SELECT run_id FROM coverage_runs ORDER BY updated_at DESC LIMIT 1")


def runs(con) -> list[dict]:
    ensure_table(con)
    return db.rows(con, "SELECT run_id, count(*) AS cells, min(updated_at) AS started, max(updated_at) AS finished, "
                        "group_concat(DISTINCT state) AS states FROM coverage_runs GROUP BY run_id ORDER BY finished DESC")


def _mean(vals):
    vals = [v for v in vals if v is not None]
    return round(st.mean(vals), 3) if vals else None


def matrix(rows: list[dict], qs: list[dict] | None = None) -> dict:
    """The matrix of a run: questions x columns (a state, or a state/place), each cell's verdict and missing
    kinds, and per column the verdict counts, the top missing kinds, the Ollama score means and the timing."""
    qs = qs or questions()
    cols: dict[str, dict] = {}
    cells: dict[str, dict] = {}
    for r in rows:
        col = r["state"] + (f"/{r['gov_id']}" if r["gov_id"] else "")
        c = cols.setdefault(col, {"state": r["state"], "gov_id": r["gov_id"] or None, "adequate": 0, "partial": 0,
                                  "none": 0, "draft": 0, "cells": 0, "missing": {}, "seconds": [], "ollama": [],
                                  "ollama_seconds": [], "sources": {}, "node": r.get("node"), "model": None})
        c[r["verdict"]] = c.get(r["verdict"], 0) + 1
        c["cells"] += 1
        # the fourth shade: a cell whose process items are all drafts (its verdict is partial at most)
        draft = bool((r["probe"] or {}).get("drafts_only"))
        if draft:
            c["draft"] += 1
        for k in r["missing"]:
            c["missing"][k] = c["missing"].get(k, 0) + 1
        c["seconds"].append(r["seconds"] or 0)
        src = (r["probe"] or {}).get("source") or "none"
        c["sources"][src] = c["sources"].get(src, 0) + 1
        if r["arm"] == "ollama":
            c["ollama_seconds"].append(r["seconds"] or 0)
            c["model"] = c["model"] or r.get("model")
            if r["score"]:
                c["ollama"].append(r["score"])
        pr = r["probe"] or {}
        cells[f"{r['qid']}|{col}"] = {"qid": r["qid"], "col": col, "verdict": r["verdict"], "missing": r["missing"],
                                       "draft": draft, "arm": r["arm"], "seconds": r["seconds"], "gold": pr.get("gold"),
                                       "counts": pr.get("counts"), "source": pr.get("source"),
                                       "composite": (r["score"] or {}).get("composite"),
                                       "vital_recall": (r["score"] or {}).get("vital_recall")}
    by_col = {}
    for col, c in cols.items():
        scores = c.pop("ollama")
        keys = ("composite", "vital_recall", "nugget_recall", "citation_precision", "citation_support", "slot_match",
                "recall@10", "gate_correct")
        by_col[col] = {**{k: v for k, v in c.items() if k not in ("seconds", "ollama_seconds", "missing")},
                       "top_missing": sorted(c["missing"].items(), key=lambda kv: (-kv[1], kv[0]))[:4],
                       "missing": c["missing"], "seconds_mean": _mean(c["seconds"]), "seconds_total": round(sum(c["seconds"]), 1),
                       "ollama_cells": len(scores), "ollama_seconds_mean": _mean(c["ollama_seconds"]),
                       "ollama": {k: _mean([s.get(k) for s in scores]) for k in keys} if scores else None}
    return {"questions": [{"id": q["id"], "text": q["text"], "topic": q["topic"], "level": q["level"], "needs": q["needs"]}
                          for q in qs], "columns": by_col, "cells": cells,
            "totals": {**{v: sum(c.get(v, 0) for c in by_col.values()) for v in VERDICTS},
                       "draft": sum(c.get("draft", 0) for c in by_col.values())}}


GLYPH = {"adequate": "A", "partial": "P", "none": "-"}
DRAFT_GLYPH = "D"            # a partial cell resting on draft process items alone (the fourth shade)


def markdown(m: dict, run_id: str) -> str:
    cols = list(m["columns"])
    L = [f"# Coverage: can we answer what people ask? (run {run_id})", "",
         "Do the Wikibase items and the statute index hold the facts each question needs (who, steps, deadline, fee, "
         "form, where, appeal)?  `A` adequate, `P` partial, `D` partial on draft process items alone (a `single` "
         "state model or an asked answer's draft; never more than partial), `-` none; the kinds still missing follow "
         "the verdict.  `lexflow run coverage --states va,dc` regenerates this file (lexflow/ask/coverage.py); "
         "`lexflow run coverage --fill` answers the gap cells with the ask pipeline and stores the drafts.", "",
         "| Column | Cells | Adequate | Partial | Draft | None | Top missing kinds | Ollama cells | Composite | "
         "Vital recall | Citation precision | s/cell | s/Ollama cell |", "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for col in cols:
        c = m["columns"][col]
        o = c.get("ollama") or {}
        L.append(f"| {col} | {c['cells']} | {c.get('adequate', 0)} | {c.get('partial', 0)} | {c.get('draft', 0)} | "
                 f"{c.get('none', 0)} | "
                 f"{', '.join(f'{k} ({n})' for k, n in c['top_missing']) or '-'} | {c['ollama_cells']} | "
                 f"{o.get('composite') if o else '-'} | {o.get('vital_recall') if o else '-'} | "
                 f"{o.get('citation_precision') if o else '-'} | {c['seconds_mean']} | {c['ollama_seconds_mean'] or '-'} |")
    L += ["", "| Question | " + " | ".join(cols) + " |", "|---|" + "---|" * len(cols)]
    for q in m["questions"]:
        row = []
        for col in cols:
            cell = m["cells"].get(f"{q['id']}|{col}")
            if not cell:
                row.append("")
                continue
            s = DRAFT_GLYPH if cell.get("draft") and cell["verdict"] == "partial" else GLYPH.get(cell["verdict"], "?")
            if cell["missing"]:
                s += " " + ",".join(cell["missing"])
            if cell.get("composite") is not None:
                s += f" ({cell['composite']})"
            row.append(s)
        L.append(f"| {q['id']} | " + " | ".join(row) + " |")
    t = m["totals"]
    n = sum(t.get(v, 0) for v in VERDICTS)
    L += ["", f"Totals: {t.get('adequate', 0)} adequate, {t.get('partial', 0)} partial (of them {t.get('draft', 0)} on "
              f"drafts alone), {t.get('none', 0)} none over {n} cells."]
    return "\n".join(L) + "\n"


def write_reports(con, run_id: str, docs_dir: Path | str | None = None, log=print) -> dict:
    """docs/coverage-<run>.json (the rows and the matrix) and docs/coverage.md (the matrix)."""
    from . import bench as B
    docs = Path(docs_dir) if docs_dir else DOCS_DIR
    docs.mkdir(parents=True, exist_ok=True)
    rows = rows_of(con, run_id)
    m = matrix(rows)
    try:
        ver = B.version()
    except Exception:  # noqa: BLE001
        ver = None
    doc = {"run": run_id, "generated": db.now(), "scorer_version": ver, "states": sorted({r["state"] for r in rows}),
           "matrix": m, "rows": rows}
    jp = docs / f"coverage-{run_id}.json"
    jp.write_text(json.dumps(doc, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    mp = docs / "coverage.md"
    mp.write_text(markdown(m, run_id), encoding="utf-8")
    log(f"wrote {jp} and {mp}")
    return {"json": str(jp), "markdown": str(mp)}


def latest_report(docs_dir: Path | str | None = None) -> dict | None:
    docs = Path(docs_dir) if docs_dir else DOCS_DIR
    files = sorted(docs.glob("coverage-*.json"), key=lambda p: p.stat().st_mtime)
    return json.loads(files[-1].read_text(encoding="utf-8")) if files else None


# -------------------------------------------------------------------------------------------------------- CLI
def main(argv=None) -> int:
    import argparse
    from ..municipal import places as P
    ap = argparse.ArgumentParser(prog="python -m lexflow.ask.coverage", description=__doc__.split("\n\n")[0])
    ap.add_argument("--states", default="va,dc")
    ap.add_argument("--places", help="va:charlottesville,va:albemarle ...")
    ap.add_argument("--questions", help="question ids, comma-separated")
    ap.add_argument("--arm", choices=ARMS, default="ollama")
    ap.add_argument("--llm-cells", type=int, help="Ollama answers for this many state-level cells per state")
    ap.add_argument("--run", help="run id (default: the date and time); an existing id resumes")
    ap.add_argument("--node")
    ap.add_argument("--model")
    ap.add_argument("--local", action="store_true", help="probe the local store, not the live endpoint")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--check", action="store_true", help="check the question file and every gold entry, then stop")
    ap.add_argument("--fill", action="store_true", help="answer the gap cells of the run (--run, else the latest) with "
                                                        "the ask pipeline and store the drafts in asked_answers")
    a = ap.parse_args(argv)
    states = S.parse_states(a.states)
    if a.fill:
        con = db.connect()
        try:
            out = fill(con, states, run_id=a.run, qids=[q for q in (a.questions or "").split(",") if q] or None,
                       llm_cells=a.llm_cells, node=a.node, model=a.model, force=a.force)
            print(json.dumps(out, indent=1))
        finally:
            con.close()
        return 0
    if a.check:
        bad = check_questions(questions())
        for p in bad:
            print("questions:", p)
        n = 0
        for qid, st_ in gold_cases(states):
            r = check_gold(load_gold(st_, qid), st_, qid)
            n += 1
            for p in r["problems"]:
                print(f"{st_}/{qid}: {p}")
            bad += r["problems"]
        print(f"{n} gold entries checked; {len(bad)} problems")
        return 1 if bad else 0
    con = db.connect()
    try:
        places = P.resolve_all(con, a.places) if a.places else None
        out = run(con, states, places, [q for q in (a.questions or "").split(",") if q] or None, arm=a.arm,
                  llm_cells=a.llm_cells, run_id=a.run, node=a.node, live=not a.local, force=a.force, model=a.model)
        print(json.dumps(out, indent=1))
    finally:
        con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
