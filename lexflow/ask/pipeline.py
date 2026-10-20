"""Answer a new question for any number of states and places, and store the answers.

    targets: "va" (a state) · "va:charlottesville" · "md:baltimore county" · a 14-digit Census gov_id · "va:*" (every
    government in a state)

The state answer is worked out once per (question, state) and shared by every place in that state; each place
adds its local layer (LOCUS headings that mention the question, and its contacts).  Rows go to ``asked_answers``
(shared through Turso), keyed by question id and target.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import re
import time

from .. import config
from ..municipal import places as P
from ..municipal import states as S
from ..municipal import statutes
from ..store import db
from . import answer as A
from . import local as L
from .plan import Plan, plan as make_plan, slug
from .retrieve import in_force, retrieve


def asker_for(model: str | None, node: str | None = None):
    """A local model to ask small questions of, or None when Ollama (any node of the pool) does not have it.
    ``node`` pins the calls to one node of the pool (``lexflow run ask ... --node``)."""
    from ..extract.ollama import OllamaClient
    from ..extract.strategies import Asker
    from ..municipal.build import _has, ollama_models
    model = model or config.ASK_MODEL
    url = config.OLLAMA_URL
    if node:
        from ..compute import nodes as CN
        url = CN.url_of(node)
        if not url:
            raise ValueError(f"unknown node {node!r}: the configured nodes are {', '.join(CN.names()) or 'none'}")
    try:
        if not _has(ollama_models(url if node else None), model):
            return None
    except Exception:  # noqa: BLE001 - Ollama not running
        return None
    return Asker(OllamaClient(base_url=url, model=model, num_ctx=4096, timeout=1800, node=node), mode="schema",
                 max_tokens=400)


def embedder():
    from ..extract.selector import Embedder
    return Embedder()


def resolve_targets(con, targets: list[str]) -> dict[str, list[dict]]:
    """state -> governments to answer for (an empty list means the state itself only)."""
    out: dict[str, list[dict]] = {}
    for t in targets:
        t = t.strip()
        if not t:
            continue
        st, _, rest = t.partition(":")
        if len(st) == 2 and not rest:
            out.setdefault(S.normalise(st), [])
            continue
        if len(st) == 2 and rest == "*":
            out.setdefault(S.normalise(st), []).extend(
                db.rows(con, "SELECT * FROM governments WHERE state=? ORDER BY population DESC", S.normalise(st)))
            continue
        hits = P.resolve(con, t)
        if not hits:
            raise ValueError(f"no state or government matches {t!r}")
        for g in hits[:1] if ":" in t else hits:
            out.setdefault(g["state"], []).append(g)
    return out


ROUTES = {"suggestions"}        # /api/ask/<name> paths that a question id must not shadow


def qid_for(con, text: str) -> str:
    """A new question's id: its slug, plus a short hash of the text when the slug already names a different
    question (or an API route).  The same question asked again keeps its id."""
    def norm(t):
        return " ".join(re.findall(r"[\w$%]+", t.lower()))
    base = slug(text)
    used = {norm(r["t"]) for r in db.rows(con, "SELECT text AS t FROM asked_questions WHERE id=? UNION "
                                               "SELECT question_text FROM asked_answers WHERE question_id=?",
                                          base, base) if r["t"]}
    if base not in ROUTES and (not used or norm(text) in used):
        return base
    return f"{base}_{hashlib.sha1(norm(text).encode()).hexdigest()[:6]}"


def save_question(con, text: str, plan: Plan, qid: str | None = None) -> str:
    qid = qid or qid_for(con, text)
    db.upsert(con, "asked_questions", [{"id": qid, "text": text.strip(), "kind": plan.kind,
                                        "terms": db_json(plan.groups), "created_at": db.now()}], keys=("id",))
    con.commit()
    return qid


def answer_state(con, qid: str, plan: Plan, state: str, *, asker=None, emb=None, log=print, store: bool = True,
                 oracle_refs: list[str] | None = None) -> dict:
    """Retrieve, quote, extract and (optionally) summarise one state's answer; store it as target=state.
    ``oracle_refs`` answers from those sections instead of retrieving (the benchmark's oracle-sections arm)."""
    t0 = time.time()
    timings = {}
    # no "published": re-asking keeps an answer's wiki tick; but a new answer is not the one a person reviewed, so
    # the review goes, and the wiki shows it again only once someone signs the new text (lexflow/signoff.py)
    row = {"question_id": qid, "target": state, "state": state, "gov_id": None, "question_text": plan.text,
           "model": None, "reviewed_by": None}
    if not statutes.have(state):
        row.update(status="no-statutes", answer=db_json({"status": "no-statutes", "why":
                   f"{S.NAME[state]} has no statute file in open-us-law"}), seconds=0.0)
        if store:
            db.upsert(con, "asked_answers", [row])
            con.commit()
        return row
    r = oracle(state, oracle_refs) if oracle_refs is not None else retrieve(state, plan, emb)
    timings["retrieve"] = round(time.time() - t0, 1)
    chosen = r["chosen"]
    quotes, steps, facts, bpmn, summary, notes, text = [], [], None, None, None, [], ""
    if chosen:
        texts = texts_of(state, chosen)
        text = statutes.combined_text(texts)
        t1 = time.time()
        quotes = A.evidence(plan.text, plan, text, emb, default_section=texts[0].section)
        timings["evidence"] = round(time.time() - t1, 1)
        if plan.kind in ("process", "either"):
            t1 = time.time()
            facts, steps, bpmn = _process(plan, qid, state, texts, text, notes, emb)
            timings["process"] = round(time.time() - t1, 1)
        if asker is not None and quotes:
            t1 = time.time()
            summary = A.summarise(asker, plan.text, S.NAME[state], quotes, chosen)
            row["model"] = asker.client.model
            timings["summary"] = round(time.time() - t1, 1)
    status = gate(r, summary)
    checked = quote_counts(quotes, steps, text)
    cases = L.court_decisions(state, [c["ref"] for c in chosen], log=log) if chosen and status != "not_found" else []
    md = A.markdown(plan.text, S.NAME[state], chosen, quotes, steps, summary, status)
    row.update(status=status, sections=db_json(r), facts=db_json(facts) if facts else None, bpmn=bpmn,
               answer=db_json({"status": status, "quotes": quotes, "steps": steps, "summary": summary,
                               "markdown": md, "notes": notes, "cases": cases}),
               metrics=db_json({"timings": timings, "concepts": r["concepts"], "plan": plan.groups,
                                "plan_source": plan.source, "kind": plan.kind, **checked,
                                "answered_at": db.now()}),     # when its quotes were taken from the text
               seconds=round(time.time() - t0, 1))
    if store:
        db.upsert(con, "asked_answers", [row])
        con.commit()
    log(f"{qid} · {state}: {status}; {len(chosen)} sections ({', '.join(c['ref'] for c in chosen)}); "
        f"{len(quotes)} quotes, {len(steps)} steps in {row['seconds']}s")
    return row


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", str(s or "").replace("’", "'")).strip()


def quote_counts(quotes: list[dict], steps: list[dict], text: str) -> dict:
    """How many of an answer's quotes (key provisions and steps) appear word for word in the statute text, as the
    wiki label reports them ("21 of 23 quotes matched")."""
    body = _norm(text)
    said = [q.get("text") for q in quotes or []] + [s.get("quote") for s in steps or []]
    said = [_norm(x) for x in said if x]
    return {"quotes_checked": len(said), "quote_misses": sum(1 for x in said if x not in body)} if said else {}


def recount(row: dict) -> dict | None:
    """The quote count of a stored answer made again now, by ``quote_counts`` (the matcher the answer was made
    with) against the text of the sections it chose: the search index's rows by id, else the downloaded statutes by
    section number.  ``{"quotes_checked": n, "quote_misses": m}``; ``{}`` for an answer with no quotes; None when
    the statute text is not at hand here, so a page never states a count it did not make."""
    import sqlite3
    from . import index as I
    loads = lambda v: (db.loads(v, {}) if isinstance(v, str) else v) or {}     # noqa: E731
    a, sec = loads(row.get("answer")), loads(row.get("sections"))
    quotes, steps, chosen = a.get("quotes") or [], a.get("steps") or [], sec.get("chosen") or []
    if not [q for q in quotes if q.get("text")] + [x for x in steps if x.get("quote")]:
        return {}
    state = row.get("state")
    if not chosen or not state:
        return None
    texts = None
    try:
        if I.path(state).exists() and all(c.get("id") is not None for c in chosen):
            texts = texts_of(state, chosen)
    except (KeyError, ValueError, OSError, sqlite3.Error):
        texts = None
    if texts is None:
        try:
            texts = statutes.section_texts(state, [c["ref"] for c in chosen])
        except (KeyError, ValueError, OSError, FileNotFoundError):
            return None
    return quote_counts(quotes, steps, statutes.combined_text(texts))


def texts_of(state: str, chosen: list[dict]) -> list:
    """The chosen sections' texts, as statutes.section_texts() gives them, fetched by index row id: one ref can
    name several rows (an expired and a current version, or two sections that share a citation)."""
    from ..ir import SectionText
    from . import index as I
    con = I.connect(state)
    try:
        rows = [con.execute("SELECT * FROM sec WHERE id=?", (c["id"],)).fetchone() for c in chosen]
    finally:
        con.close()
    out = []
    for c, r in zip(chosen, rows):
        if r is None:
            raise KeyError(f"{state}: section {c['ref']} (row {c['id']}) is not in the index")
        out.append(SectionText(section=r["section_number"], title=r["original_title"] or "",
                               code=statutes.code_of(state, r), jurisdiction=state,
                               text=statutes.strip_history(I.text_of(state, r["id"])), url=r["url"],
                               retrieved_from=f"open-us-law {r['act_id']}",
                               license_note="open-us-law (Vaquill AI), CC BY-NC 4.0; text from the government "
                                            "publisher at the URL shown"))
    return out


def oracle(state: str, refs: list[str]) -> dict:
    """A retrieval result made of the given sections, as if the search had found exactly them (the version in
    force today when a ref has several)."""
    from . import index as I
    today = dt.date.today().isoformat()
    chosen = []
    for ref in refs:
        rows = I.lookup(state, ref)
        if rows:
            row = next((r for r in rows if in_force(r, today) == 1), rows[0])
            c = dict(row, similarity=1.0, rank_score=1.0, passes=["oracle"], rrf=1.0)
            chosen.append({k: c.get(k) for k in ("id", "ref", "citation", "title", "chapter", "url", "words",
                                                 "rrf", "similarity", "rank_score", "passes")})
    return {"status": "found" if chosen else "not-found", "concepts": [], "candidates": chosen, "chosen": chosen}


def gate(r: dict, summary: dict | None) -> str:
    """answered / partial / not_found.  A weak retrieval is not an answer, whatever a model says about it."""
    if not r["chosen"]:
        return "not_found"
    best = r["chosen"][0]
    if best.get("relevance") is not None and "oracle" not in (best.get("passes") or []):
        # the learned relevance model's probability that the best section is one the answer rests on
        if best["relevance"] < config.ASK_MIN_RELEVANCE:
            return "not_found"
        return summary["status"] if summary and summary["status"] != "not_found" else \
            ("partial" if summary else "answered")
    passes = set(best.get("passes") or [])
    sim = best.get("similarity") or 0
    # the best section must hold all the question's core concepts, unless it is clearly about the question
    all_core = bool(passes & {"title_all", "all", "procedure"})
    if sim < config.ASK_MIN_SIMILARITY or (not all_core and sim < config.ASK_MIN_SIMILARITY + 0.12):
        return "not_found"
    if summary and summary["status"] == "not_found":
        return "partial"
    return summary["status"] if summary else "answered"


def _process(plan, qid, state, texts, text, notes, emb=None):
    """Steps from the learned selector, as facts, compiled to BPMN (None when nothing compiles)."""
    from ..extract import strategies as ST
    from ..extract.segment import segment
    from ..ir import Provenance
    from ..municipal import build as B
    from ..municipal.quality import assess
    clauses = segment(text)
    drafts = A.process(clauses, qid, state, notes, question=plan.text, plan=plan, embedder=emb)
    if not drafts:
        return None, [], None
    try:
        facts = ST.assemble(drafts, clauses, texts[0].section, qid, plan.text.rstrip("?"))
        model = B._compile(facts, state, qid, texts, Provenance(method="learned-selector", model="selector:stack"))
        res = assess(model)
        bpmn = res["bpmn"]
    except Exception as e:  # noqa: BLE001 - steps are still shown without a map
        notes.append(f"no process map: {type(e).__name__}: {str(e)[:200]}")
        facts, bpmn = None, None
    steps = [{"actor": d["actor"], "action": d["action"], "section": d["clause"].section or texts[0].section,
              "label": d["clause"].label, "quote": d["clause"].text,
              "deadline": (f"{d['deadline']['amount']} {d['deadline']['unit'].replace('_', ' ')}"
                           if d.get("deadline") else None)} for d in drafts]
    return (facts.model_dump() if facts else None), steps, bpmn


def answer_place(con, qid: str, plan: Plan, g: dict, state_row: dict, rows: list[dict] | None = None,
                 grouped: dict | None = None, keys: dict | None = None) -> dict:
    """A place's answer: its state's answer plus its local layer."""
    hits = L.local_hits(con, g["state"], g["gov_id"], plan, rows=rows, grouped=grouped, keys=keys)
    ctc = L.contacts(con, g["gov_id"])
    row = {k: state_row.get(k) for k in ("question_id", "state", "question_text", "status", "sections", "facts",
                                         "bpmn", "answer", "metrics", "model", "seconds")}
    row.update(target=g["gov_id"], gov_id=g["gov_id"], reviewed_by=None,
               local=db_json({"name": g["name"], "kind": g["kind"], "locus": hits, "contacts": ctc,
                              "web": L.web_pages(g, plan)}))
    db.upsert(con, "asked_answers", [row])
    return row


def run(con, text: str, targets: list[str], *, model: str | None = None, use_llm: bool = True, log=print,
        progress=None, question_id: str | None = None, node: str | None = None) -> dict:
    """Answer one question for every target; returns counts by status.  ``question_id`` is the id the caller
    already gave out (the API does), so the answers land where its link points.  ``node`` pins the model calls
    to one node of the pool."""
    asker = asker_for(model, node) if use_llm else None
    if use_llm and asker is None:
        log(f"no local chat model ({model or config.ASK_MODEL}) in Ollama: answering from quotes only")
    p = make_plan(text, asker)
    qid = save_question(con, text, p, question_id)
    log(f"question {qid} ({p.kind}): concepts {p.groups}")
    try:
        emb = embedder()
    except Exception:  # noqa: BLE001
        emb = None
    by_state = resolve_targets(con, targets)
    total = sum(1 + len(v) for v in by_state.values())
    done, counts = 0, {}
    for st, govs in by_state.items():
        srow = answer_state(con, qid, p, st, asker=asker, emb=emb, log=log)
        counts[srow["status"]] = counts.get(srow["status"], 0) + 1
        done += 1
        if govs:
            rows = None
            try:
                rows = L.locus_rows(st, log)
            except Exception as e:  # noqa: BLE001 - LOCUS unreachable: contacts only
                log(f"{st}: LOCUS not available ({type(e).__name__}); local layer has contacts only")
                rows = []
            from ..municipal import locus_scan
            grouped, keys = L.by_place(rows), locus_scan.gov_keys(con, st)       # once for the whole batch
            for g in govs:
                answer_place(con, qid, p, g, srow, grouped=grouped, keys=keys)
                done += 1
                if progress:
                    progress(done / total)
            con.commit()
        if progress:
            progress(done / total)
    db.bump(con)
    con.commit()
    return {"question": qid, "kind": p.kind, "targets": total, "status": counts}


def db_json(v):
    import json
    return json.dumps(v, default=str)
