"""The dashboard's API, the browser plugin's lookup, and the static dashboard itself.

Read endpoints never block on network: when Turso is configured and ``auto_pull`` is on,
opening a state that has no local data starts a background pull job for it ("pull as needed").
"""
from __future__ import annotations

import json
import re
from contextlib import asynccontextmanager
from typing import Annotated
from urllib.parse import urlparse

from fastapi import Body, FastAPI, Header, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .. import config, reviewers, signoff
from ..ask import prefer
from ..municipal import method as M
from ..municipal import states as S
from ..municipal import stats
from ..municipal.questions import QUESTIONS
from ..pipeline import jobs
from ..pipeline.steps import STEPS, COMPOSITE, checklist, ollama_state
from ..store import db
from ..store import turso as T
from ..compute import api as compute_api
from ..compute import health as compute_health
from ..compute import nodes as compute_nodes

runner = jobs.Runner()
poller = compute_health.Poller()


@asynccontextmanager
async def lifespan(_app):
    config.ensure_dirs()
    with db.session():
        pass
    if config.JOB_RUNNER:          # a second, read-only instance on the same database can run without one
        runner.start()
    if compute_nodes.pool_on():    # health checks of the model servers (lexflow/compute); nothing without a pool
        poller.start()             # idempotent: one thread per process, restarted after a shutdown
    yield
    runner.stop.set()
    poller.shutdown(timeout=2)     # so the next lifespan in this process (a test's TestClient) starts afresh


app = FastAPI(title="lexflow", version="1.0", lifespan=lifespan)
compute_api.register(app)


def con():
    return db.connect()


def _q(question: str) -> str:
    if question not in QUESTIONS:
        raise HTTPException(400, f"question must be one of {sorted(QUESTIONS)}")
    return question


def _settings(c) -> dict:
    stored = db.loads(db.scalar(c, "SELECT value FROM settings WHERE key='app'"), {})
    return {"auto_pull": True, **stored}


# ---------------------------------------------------------------- overview
@app.get("/api/health")
def health():
    c = con()
    try:
        return {"ok": True, "version": db.version(c), "origin": config.ORIGIN,
                "running": db.scalar(c, "SELECT count(*) FROM jobs WHERE status IN ('queued','running')", default=0)}
    finally:
        c.close()


@app.get("/api/meta")
def meta():
    return {"questions": {k: {"title": q.title, "short": q.short} for k, q in QUESTIONS.items()},
            "states": [{"state": s, "fips": f, "name": n} for s, f, n in S.STATES], **M.describe(),
            "models": [config.MODEL_A, config.MODEL_B], "ask_model": config.ASK_MODEL, "origin": config.ORIGIN}


@app.get("/api/overview")
def overview():
    c = con()
    try:
        return stats.overview(c)
    finally:
        c.close()


@app.get("/api/setup")
def setup():
    """The checklist with each step's credits, plus the credits for libraries used across the steps."""
    from ..pipeline.credits import GENERAL
    c = con()
    try:
        steps = checklist(c)
        for s in steps:
            step = STEPS[s["id"]]
            s["credits"], s["credits_note"] = step.credits or [], step.credits_note
        return {"steps": steps, "services": services(c), "credits": GENERAL}
    finally:
        c.close()


def services(c) -> dict:
    o = ollama_state()
    client = T.Turso.from_env()
    turso = {"configured": client is not None, "url": client.base if client else None, "reachable": None}
    if client:
        try:
            turso["reachable"] = client.ping()
        except T.TursoError as e:
            turso["reachable"], turso["error"] = False, str(e)[:200]
    searx = {"configured": bool(config.SEARXNG_URL)}
    return {"ollama": {"url": config.OLLAMA_URL, **o, "want": [config.MODEL_A, config.MODEL_B],
                       "pool": o.get("pool") or compute_api.summary()}, "turso": turso,
            "searxng": searx, "dokuwiki": {"configured": bool(config.DOKUWIKI_URL and config.DOKUWIKI_TOKEN),
                                           "url": config.DOKUWIKI_URL or None},
            "data_dir": str(config.DATA_DIR)}


# -------------------------------------------------------------------- jobs
class JobIn(BaseModel):
    step: str
    args: dict = {}


@app.post("/api/jobs")
def create_job(job: JobIn):
    """Queue a step.  A sync job takes only the shared tables (db.SYNCED): one that names any other table (the
    reviewer list, the review log ...) is a 400 and is not queued."""
    if job.step not in STEPS and job.step not in COMPOSITE:
        raise HTTPException(400, f"unknown step {job.step}")
    if job.step == "sync":
        try:
            T.check_tables(job.args.get("tables"))
        except T.SyncTableError as e:
            raise HTTPException(400, str(e)) from e
        if job.args.get("direction", "push") not in ("push", "pull"):
            raise HTTPException(400, "direction is push or pull")
    if job.args.get("node"):
        known = compute_nodes.names()
        if job.args["node"] not in known:
            raise HTTPException(400, f"unknown node {job.args['node']!r}: the configured nodes are {', '.join(known) or 'none'}")
    c = con()
    try:
        return {"id": jobs.enqueue(c, job.step, job.args)}
    finally:
        c.close()


@app.get("/api/jobs")
def list_jobs(limit: int = 30):
    c = con()
    try:
        rows = db.rows(c, "SELECT * FROM jobs ORDER BY id DESC LIMIT ?", limit)
        for r in rows:
            r["args"] = db.loads(r["args"], {})
            r["title"] = (STEPS.get(r["step"]) or COMPOSITE.get(r["step"])).title if (
                r["step"] in STEPS or r["step"] in COMPOSITE) else r["step"]
        return rows
    finally:
        c.close()


@app.get("/api/jobs/{job_id}")
def get_job(job_id: int, lines: int = 200):
    c = con()
    try:
        r = db.one(c, "SELECT * FROM jobs WHERE id=?", job_id)
        if not r:
            raise HTTPException(404)
        r["args"] = db.loads(r["args"], {})
        r["log"] = jobs.tail(job_id, lines)
        return r
    finally:
        c.close()


@app.post("/api/jobs/{job_id}/cancel")
def cancel_job(job_id: int):
    c = con()
    try:
        return {"cancelled": jobs.cancel(c, job_id)}
    finally:
        c.close()


# --------------------------------------------------------------------- map
@app.get("/api/map")
def map_layer(question: str = "records", layer: str = "confidence"):
    """The county and state values of the scored layers (stats.county_layer) plus what lexflow holds
    (municipal.map_layers.holdings, cached ten minutes): per state ``processes``, ``coverage``, ``wikibase`` and
    ``index`` on each ``states`` entry, the researched localities under ``places`` (by county FIPS), and the
    totals under ``holdings``."""
    from ..municipal import map_layers as ML
    c = con()
    try:
        out = stats.county_layer(c, _q(question), layer)
        held = ML.holdings(c)
        for fips, e in held["states"].items():
            st = out["states"].setdefault(fips, {"state": e["state"], "name": e["name"]})
            for k in ("processes", "coverage", "wikibase", "index"):
                st[k] = e[k]
        out["places"] = held["places"]
        out["holdings"] = held["totals"]
        return out
    finally:
        c.close()


@app.get("/api/states")
def state_table(question: str | None = None):
    c = con()
    try:
        rows = stats.state_table(c)
        return [r for r in rows if not question or r["question"] == question]
    finally:
        c.close()


@app.get("/api/states/{state}")
def state_detail(state: str, question: str = "records"):
    st = S.normalise(state)
    c = con()
    try:
        _maybe_pull(c, st)
        govs = db.rows(c, """SELECT g.gov_id, g.name, g.kind, g.county_fips, g.county_name, g.population, g.website,
                                    a.confidence, a.tier, a.contact_level, a.local_score
                             FROM governments g LEFT JOIN answers a ON a.gov_id=g.gov_id AND a.question=?
                             WHERE g.state=? ORDER BY g.population DESC""", _q(question), st)
        return {"state": st, "name": S.NAME[st], "rows": [r for r in stats.state_table(c) if r["state"] == st],
                "models": stats.models(c, st), "governments": govs,
                "pulling": db.scalar(c, "SELECT id FROM jobs WHERE step='sync' AND status IN ('queued','running') "
                                        "AND args LIKE ?", f'%"{st}"%')}
    finally:
        c.close()


def _maybe_pull(c, st: str):
    """Pull as needed: a state with nothing local is fetched from Turso in the background."""
    if not config.TURSO_URL or not _settings(c).get("auto_pull"):
        return
    if db.scalar(c, "SELECT count(*) FROM answers WHERE state=?", st, default=0):
        return
    if db.scalar(c, "SELECT count(*) FROM jobs WHERE step='sync' AND status IN ('queued','running') AND args LIKE ?",
                 f'%"{st}"%', default=0):
        return
    jobs.enqueue(c, "sync", {"direction": "pull", "states": st})


@app.get("/api/counties/{fips}")
def county(fips: str, question: str = "records"):
    if not re.fullmatch(r"\d{5}", fips):
        raise HTTPException(400, "county FIPS is five digits")
    c = con()
    try:
        if fips[:2] in S.BY_FIPS:
            _maybe_pull(c, S.BY_FIPS[fips[:2]])
        return stats.county_detail(c, fips, _q(question))
    finally:
        c.close()


# ------------------------------------------------------------------ models
@app.get("/api/models")
def models(state: str | None = None):
    c = con()
    try:
        return stats.models(c, S.normalise(state) if state else None)
    finally:
        c.close()


@app.get("/api/models/{mid}")
def model(mid: str):
    c = con()
    try:
        r = stats.model_detail(c, mid)
        if not r:
            raise HTTPException(404)
        r["steps"] = stats.steps_of(r)
        return r
    finally:
        c.close()


@app.get("/api/models/{mid}/{kind}")
def model_file(mid: str, kind: str):
    if kind not in ("bpmn", "dmn", "svg", "facts"):
        raise HTTPException(404)
    c = con()
    try:
        value = db.scalar(c, f"SELECT {kind} FROM process_models WHERE model_id=?", mid)
        if not value:
            raise HTTPException(404)
        media = {"bpmn": "application/xml", "dmn": "application/xml", "svg": "image/svg+xml",
                 "facts": "application/json"}[kind]
        ext = "json" if kind == "facts" else kind
        return Response(value, media_type=media,
                        headers={"Content-Disposition": f'inline; filename="{mid}.{ext}"'})
    finally:
        c.close()


# ----------------------------------------------------------------- answers
@app.get("/api/answers/{gov_id}")
def answers(gov_id: str):
    from ..municipal.answer import answers_for
    c = con()
    try:
        out = answers_for(c, gov_id)
        if out is None:
            raise HTTPException(404)
        return out
    finally:
        c.close()


@app.get("/api/answers/{gov_id}.md", include_in_schema=False)
def answers_markdown(gov_id: str):
    from ..municipal.answer import markdown
    c = con()
    try:
        return PlainTextResponse(markdown(c, gov_id), media_type="text/markdown")
    except KeyError:
        raise HTTPException(404)
    finally:
        c.close()


@app.get("/api/lookup")
def lookup(url: str = Query(..., description="any page on a government's website")):
    """For the browser plugin: which government owns this site, and its answers."""
    host = (urlparse(url if "://" in url else "http://" + url).hostname or "").lower().removeprefix("www.")
    if not host:
        raise HTTPException(400, "no host in url")
    c = con()
    try:
        rows = db.rows(c, "SELECT DISTINCT gov_id FROM contacts WHERE kind='website' AND "
                          "(value LIKE ? OR value LIKE ?) LIMIT 5", f"%://{host}%", f"%://www.{host}%")
        if not rows:
            return JSONResponse({"host": host, "matches": []}, status_code=404)
        return {"host": host, "matches": [answers(r["gov_id"]) for r in rows]}
    finally:
        c.close()


@app.get("/api/benchmark")
def benchmark():
    """Latest score per (case, strategy, model) against the current Claude reference models."""
    from ..extract import benchmark as BM
    c = con()
    try:
        rows = BM.best(c)
        extra = {}
        for name in ("ceiling", "learning_curve", "askbench"):   # lexflow ceiling, learning_curve.py, ask-bench
            p = config.ROOT / "docs" / f"{name}.json"
            if p.exists():
                extra[name] = json.loads(p.read_text(encoding="utf-8"))
        return {"rows": rows, "cases": BM.cases(), "target": 0.75,
                "runs": db.scalar(c, "SELECT count(*) FROM benchmarks", default=0), **extra}
    finally:
        c.close()


@app.get("/api/places")
def places_list(spec: str | None = None):
    """Places with researched local answers, or the governments a spec like 'va:charlottesville' names."""
    from ..municipal import places as P
    c = con()
    try:
        if spec:
            try:
                return P.resolve_all(c, spec)
            except ValueError as e:
                raise HTTPException(404, str(e)) from e
        return db.rows(c, """
            SELECT g.gov_id, g.name, g.kind, g.state, g.population,
                   (SELECT count(*) FROM local_answers l WHERE l.gov_id = g.gov_id) AS researched,
                   (SELECT max(verified) FROM local_answers l WHERE l.gov_id = g.gov_id) AS verified,
                   (SELECT max(researched) FROM local_answers l WHERE l.gov_id = g.gov_id) AS researched_on,
                   (SELECT count(*) FROM place_processes p WHERE p.gov_id = g.gov_id) AS processes,
                   (SELECT coalesce(sum(verified), 0) FROM place_processes p WHERE p.gov_id = g.gov_id) AS processes_verified
            FROM governments g
            WHERE g.gov_id IN (SELECT gov_id FROM local_answers UNION SELECT gov_id FROM place_processes)
            ORDER BY g.population DESC""")
    finally:
        c.close()


@app.get("/api/places/{gov_id}/processes")
def place_processes_list(gov_id: str):
    """A place's researched processes (verified or not), by category and title."""
    c = con()
    try:
        return [{k: r[k] for k in ("process", "title", "question", "category", "kind", "office", "verified", "updated_at")}
                for r in db.rows(c, "SELECT * FROM place_processes WHERE gov_id=? ORDER BY category, title", gov_id)]
    finally:
        c.close()


@app.get("/api/places/{gov_id}/processes/{process}")
def place_process(gov_id: str, process: str):
    c = con()
    try:
        r = db.one(c, "SELECT * FROM place_processes WHERE gov_id=? AND process=?", gov_id, process)
        if not r:
            raise HTTPException(404, "no such process for that place")
        g = db.one(c, "SELECT gov_id, name, kind, state FROM governments WHERE gov_id=?", gov_id)
        return {"government": g, "verified": bool(r["verified"]), "updated_at": r["updated_at"], "spec": db.loads(r["spec"], {})}
    finally:
        c.close()


@app.get("/api/search")
def search(q: str, limit: int = 20):
    c = con()
    try:
        return db.rows(c, "SELECT gov_id, name, kind, state, county_fips, population FROM governments "
                          "WHERE name LIKE ? ORDER BY population DESC LIMIT ?", f"%{q}%", limit)
    finally:
        c.close()


# --------------------------------------------------------------------- ask
class AskIn(BaseModel):
    question: str = Field(min_length=3, max_length=500)
    # a state, "va:*" or a place spec each; the job carries them on its command line, so both are bounded
    targets: list[Annotated[str, Field(max_length=120)]] = Field(min_length=1, max_length=200)
    model: str | None = None
    use_llm: bool = True


@app.get("/api/targets")
def targets(q: str = "", limit: int = 15):
    """Autocomplete for the ask page: states first, then counties, cities and towns (largest first)."""
    q = q.strip()
    out = []
    ql = q.lower()
    for st, _, name in S.STATES:
        if ql and (ql == st or name.lower().startswith(ql) or (len(ql) > 2 and ql in name.lower())):
            out.append({"target": st, "label": f"{name} (state law)", "kind": "state", "state": st})
    if len(q) >= 2:
        c = con()
        try:
            for g in db.rows(c, "SELECT gov_id, name, kind, state, population FROM governments WHERE name LIKE ? "
                                "ORDER BY population DESC LIMIT ?", f"%{q}%", limit):
                out.append({"target": g["gov_id"], "label": f"{g['name']}, {S.NAME.get(g['state'], g['state'])}",
                            "kind": g["kind"], "state": g["state"], "population": g["population"]})
        finally:
            c.close()
    return out[:limit]


@app.get("/api/ask/suggestions")
def ask_suggestions():
    from ..ask.suggestions import SUGGESTIONS
    return SUGGESTIONS


@app.post("/api/ask")
def ask(req: AskIn):
    from ..ask.pipeline import qid_for
    text = req.question.strip()
    if not 8 <= len(text) <= 600:
        raise HTTPException(400, "ask a question of 8 to 600 characters")
    if not req.targets or len(req.targets) > 200:
        raise HTTPException(400, "choose 1 to 200 states or places")
    c = con()
    try:
        qid = qid_for(c, text)
        # hold the id for this text now, so a different question queued before the job runs gets its own
        db.upsert(c, "asked_questions", [{"id": qid, "text": text}], keys=("id",))
        jid = jobs.enqueue(c, "ask", {"question": text, "question_id": qid, "targets": req.targets,
                                      "model": req.model, "no_llm": not req.use_llm})
        return {"job": jid, "question_id": qid}
    finally:
        c.close()


@app.get("/api/ask")
def ask_list():
    """Each question asked, with its answers counted.  ``reviewed`` counts the answers whose review is for the text
    stored now (its text_hash fits, lexflow/signoff.py) and was recorded by this copy's review API (its review_log
    holds it), and ``published`` those of them also marked for the wiki: the answers the next publish writes.  Any
    other review (of another version of an answer, or one this copy did not record) counts in ``review_stale``.
    When several models answered a target, the counts are of the preferred answer per target (lexflow.ask.prefer),
    and ``models`` lists every model that answered the question."""
    c = con()
    try:
        kinds = {r["id"]: r["kind"] for r in db.rows(c, "SELECT id, kind FROM asked_questions")}
        every = db.rows(c, "SELECT * FROM asked_answers ORDER BY question_id, target, model")
        roster = reviewers.roster(c)
        out: dict[str, dict] = {}
        for r in prefer.preferred(every):
            q = out.setdefault(r["question_id"], {"question_id": r["question_id"], "question": r["question_text"],
                                                  "kind": kinds.get(r["question_id"]), "answers": 0, "states": 0,
                                                  "answered": 0, "partial": 0, "not_found": 0, "maps": 0,
                                                  "updated_at": None, "models": [], "reviewed": 0, "published": 0,
                                                  "review_stale": 0})
            q["question"] = q["question"] or r["question_text"]
            q["answers"] += 1
            q["states"] += int(r["gov_id"] is None)
            if r["status"] in ("answered", "partial", "not_found"):
                q[r["status"]] += 1
            q["maps"] += int(bool(r.get("bpmn")))
            q["updated_at"] = max(q["updated_at"] or "", r["updated_at"] or "") or None
            if r.get("reviewed_by"):
                if _reviewer(c, r, roster):
                    q["reviewed"] += 1
                    q["published"] += int(bool(r.get("published")))
                else:
                    q["review_stale"] += 1
        for r in every:
            if r["model"] not in out[r["question_id"]]["models"]:
                out[r["question_id"]]["models"].append(r["model"])
        return sorted(out.values(), key=lambda q: q["updated_at"] or "", reverse=True)
    finally:
        c.close()


def _answer_text(r: dict):
    """The stored text of an asked answer that a review covers (signoff.ASKED_TEXT)."""
    return signoff.row_text(r, signoff.ASKED_TEXT)


def _answered_at(r: dict) -> str | None:
    return (db.loads(r.get("metrics"), {}) if isinstance(r.get("metrics"), str) else r.get("metrics") or {}).get(
        "answered_at")


def _reviewer(c, r: dict, roster: dict) -> dict | None:
    """The person on the reviewer list who reviewed this text of the answer (the hash and date must fit it), with
    the name, role and licence the list gives, and only for a review this copy's API recorded with that reviewer's
    token (its review_log holds it: reviewers.asked_reviewer); or None.  A review pulled from another copy, or
    written into the database by hand, is not a review here, for the page, the dashboard or the wiki tick."""
    return reviewers.asked_reviewer(c, r, roster)


def _ask_row(c, r: dict, roster: dict) -> dict:
    stored = r.get("reviewed_by")
    who = _reviewer(c, r, roster)
    for k in ("sections", "facts", "answer", "local", "metrics"):
        r[k] = db.loads(r.get(k), None)
    # a review of another version of the text (re-asked here, or a newer copy pulled through sync), by someone no
    # longer on the reviewer list, or one this copy did not record (pulled, or written by hand), is not shown
    r["reviewed_by"] = who
    r["review_stale"] = bool(stored) and who is None
    r["review_line"] = signoff.line(who)
    r["text_hash"] = signoff.text_hash(_answer_text(r))
    return r


@app.get("/api/ask/{qid}")
def ask_question(qid: str):
    c = con()
    try:
        roster = reviewers.roster(c)
        every = db.rows(c, "SELECT * FROM asked_answers WHERE question_id=? ORDER BY gov_id IS NOT NULL, state, target, "
                           "model", qid)
        models: dict[str, list[str]] = {}
        for r in every:
            models.setdefault(r["target"], []).append(r["model"])
        rows = [_ask_row(c, r, roster) for r in prefer.preferred(every)]      # one per target: the preferred model's
        if not rows:
            raise HTTPException(404, "no answers for that question yet")
        brief = []
        for r in rows:
            a = r["answer"] or {}
            claims = ((a.get("summary") or {}).get("claims") or [])
            brief.append({"target": r["target"], "state": r["state"], "gov_id": r["gov_id"], "status": r["status"],
                          "name": (r["local"] or {}).get("name") or S.NAME.get(r["state"], r["state"]),
                          "sections": [s["ref"] for s in ((r["sections"] or {}).get("chosen") or [])],
                          "first_claim": claims[0]["text"] if claims else None,
                          "steps": len(a.get("steps") or []), "quotes": len(a.get("quotes") or []),
                          "map": bool(r.get("bpmn")),
                          "local": len(((r["local"] or {}).get("locus")) or []), "model": r["model"],
                          "models": models.get(r["target"], []),
                          "seconds": r["seconds"], "published": r["published"], "updated_at": r["updated_at"],
                          "reviewed_by": r["reviewed_by"], "review_line": signoff.line(r["reviewed_by"]),
                          "review_stale": r["review_stale"]})
        return {"question_id": qid, "question": rows[0]["question_text"], "answers": brief}
    finally:
        c.close()


@app.get("/api/ask/{qid}/{target}")
def ask_answer(qid: str, target: str, model: str | None = None):
    """The answer for the question and target: ``model``'s when ``?model=`` names one, else the preferred one
    (LEXFLOW_ASK_PREFER, else the best-scoring; lexflow.ask.prefer).  ``models`` lists every model that answered."""
    c = con()
    try:
        r = _asked(c, qid, target, model)
        out = _ask_row(c, r, reviewers.roster(c))
        out["models"] = prefer.models_of(c, qid, target)
        return out
    finally:
        c.close()


class PublishIn(BaseModel):
    published: bool


NEEDS_REVIEWER = ("Record a named reviewer first: an answer goes on the wiki only after a person has read it "
                  "against the law.")


def _asked(c, qid: str, target: str, model: str | None = None) -> dict:
    """The stored answer a request is about: ``model``'s, else the preferred one (lexflow.ask.prefer)."""
    r = prefer.answer(c, qid, target, model)
    if not r:
        raise HTTPException(404, "no such answer")
    return r


def _keep_answer_date(r: dict) -> str:
    """The answer's metrics with the date its quotes were taken (answered_at), so ticking or signing it later,
    which moves updated_at, does not move the date the wiki page gives for the quote check."""
    m = db.loads(r.get("metrics"), {}) or {}
    m.setdefault("answered_at", r.get("updated_at"))
    return json.dumps(m, ensure_ascii=False)


@app.post("/api/ask/{qid}/{target}/publish")
def ask_publish(qid: str, target: str, body: PublishIn, model: str | None = None):
    """Mark an answer for (or withdraw it from) the next Lexipedia publish, as its own sub-page.  Marking needs a
    named reviewer whose review this copy recorded (PUT .../review, with their token): a review that arrived through
    sync, or was written into the database by hand, does not count.  Withdrawing never needs one."""
    c = con()
    try:
        r = _asked(c, qid, target, model)
        if body.published and not _reviewer(c, r, reviewers.roster(c)):
            raise HTTPException(409, NEEDS_REVIEWER)
        c.execute("UPDATE asked_answers SET published=?, metrics=?, updated_at=? WHERE question_id=? AND target=? "
                  "AND model=?", (int(body.published), _keep_answer_date(r), db.now(), qid, target, r["model"]))
        db.bump(c)
        c.commit()
        return {"published": body.published}
    finally:
        c.close()


REVIEW_FIELDS = ("reviewer", "attested", "text_hash")
STALE_TEXT = ("The answer has changed since this page was loaded (it was asked again, or a newer copy arrived "
              "through sync). Reload it, read it again, and record the review then.")
NEEDS_HASH = ("send the text_hash of the answer as the reviewer read it (the text_hash that GET "
              "/api/ask/{qid}/{target} gives): a review is for one text")
ONLY_FIELDS = ("a review takes only reviewer (an id from the operator's reviewer list: `lexflow reviewer list`), "
               "attested and text_hash; the name, role and licence come from the list, and the date is today")
NEEDS_TOKEN = (f"send the reviewer's own token in the {reviewers.TOKEN_HEADER} header (`lexflow reviewer add` "
               "printed it; `lexflow reviewer token <id>` makes a new one)")
BAD_TOKEN = "that token is not the token of a reviewer on the operator's list (`lexflow reviewer token <id>`)"
NOT_THEIR_TOKEN = "that token is another reviewer's: a review is recorded only with the named reviewer's own token"


def _token_holder(c, token: str | None) -> dict:
    """The reviewer on the list whose token was sent (401 without one, 403 for one that is no reviewer's)."""
    if not token:
        raise HTTPException(401, NEEDS_TOKEN)
    who = reviewers.holder(c, token)
    if not who:
        raise HTTPException(403, BAD_TOKEN)
    return who


@app.get("/api/reviewers")
def reviewer_list():
    """The reviewer list the operator of this copy keeps (lexflow reviewer add; not synced): what the dashboard
    offers to pick from.  Read only: nothing here adds a reviewer, no token or hash is shown, and lexflow cannot check
    that a reviewer is a person."""
    c = con()
    try:
        return reviewers.shown(c)
    finally:
        c.close()


@app.put("/api/ask/{qid}/{target}/review")
def ask_review(qid: str, target: str, body: Annotated[dict, Body()],
               token: Annotated[str | None, Header(alias=reviewers.TOKEN_HEADER)] = None, model: str | None = None):
    """Record that a person on the operator's reviewer list read this answer against the law (lexflow/signoff.py).
    The body is exactly ``{"reviewer": "<id from the list>", "attested": true, "text_hash": "<the answer's
    text_hash as the reviewer read it>"}``: no name, role, licence or date can be typed in (400), since a page
    prints those from the list, and the review is dated today.  ``attested`` is the reviewer's own statement that
    they, a person, read this exact text.  The ``X-Lexflow-Reviewer-Token`` header carries that reviewer's own token
    (``lexflow reviewer add`` printed it): none is a 401, and a token that is no reviewer's, or another reviewer's,
    a 403; ``review_log`` keeps whose token recorded the review.  A missing or malformed text_hash is a 400; a
    well-formed one that is not the stored answer's is a 409, so a re-asked or newer synced answer is not shown as
    reviewed.  The answer still goes on the wiki only when it is also marked for it."""
    extra = sorted(str(k) for k in body if k not in REVIEW_FIELDS)
    bad = [f"{ONLY_FIELDS} (not {', '.join(extra)})"] if extra else []
    h = body.get("text_hash")
    if not isinstance(h, str) or not h:
        bad.append(NEEDS_HASH)
    elif not signoff.HASH.fullmatch(h):
        bad.append("text_hash is the 64-character SHA-256 (lower-case hex) that GET /api/ask/{qid}/{target} gives")
    c = con()
    try:
        r = _asked(c, qid, target, model)
        roster = reviewers.roster(c)
        ts = db.now()           # the review's date and its review_log entry come from the same moment
        rev = {"reviewer": body.get("reviewer"), "date": ts[:10], "attested": body.get("attested")}
        # not before the answer was made (its answered_at, which _keep_answer_date fixes from updated_at if missing)
        bad += signoff.problems(rev, roster, not_before=_answered_at(r) or r.get("updated_at"))
        if bad:
            raise HTTPException(400, "; ".join(bad))
        holder = _token_holder(c, token)
        if holder["id"] != rev["reviewer"]:
            raise HTTPException(403, NOT_THEIR_TOKEN)
        text = _answer_text(r)
        if h != signoff.text_hash(text):
            raise HTTPException(409, STALE_TEXT)
        rev = signoff.bind(rev, text)
        c.execute("UPDATE asked_answers SET reviewed_by=?, metrics=?, updated_at=? WHERE question_id=? AND target=? "
                  "AND model=?", (json.dumps(rev, ensure_ascii=False), _keep_answer_date(r), db.now(), qid, target,
                                  r["model"]))
        # what makes it a review here: a page names the reviewer only while this is the answer's last entry
        reviewers.log_review(c, "review", qid, target, holder["id"], rev["text_hash"], at=ts)
        db.bump(c)
        c.commit()
        who = signoff.person(rev, roster)
        return {"reviewed_by": who, "review_line": signoff.line(who), "text_hash": rev["text_hash"],
                "recorded_by": holder["id"]}
    finally:
        c.close()


@app.delete("/api/ask/{qid}/{target}/review")
def ask_unreview(qid: str, target: str, token: Annotated[str | None, Header(alias=reviewers.TOKEN_HEADER)] = None,
                 model: str | None = None):
    """Remove the reviewer; the answer leaves the wiki at the next publish, so its tick goes too.  It takes the
    token of a reviewer on the list (401 without one, 403 for one that is no reviewer's), and ``review_log`` keeps
    whose token removed the review."""
    c = con()
    try:
        r = _asked(c, qid, target, model)
        holder = _token_holder(c, token)
        c.execute("UPDATE asked_answers SET reviewed_by=NULL, published=0, metrics=?, updated_at=? "
                  "WHERE question_id=? AND target=? AND model=?", (_keep_answer_date(r), db.now(), qid, target,
                                                                   r["model"]))
        reviewers.log_review(c, "unreview", qid, target, holder["id"], signoff.text_hash(_answer_text(r)))
        db.bump(c)
        c.commit()
        return {"reviewed_by": None, "published": False, "removed_by": holder["id"]}
    finally:
        c.close()


# -------------------------------------------------------------- sync, method
@app.get("/api/sync")
def sync_status():
    c = con()
    try:
        out = T.status(c, T.Turso.from_env())
        out["log"] = db.rows(c, "SELECT * FROM sync_log ORDER BY id DESC LIMIT 20")
        out["settings"] = _settings(c)
        return out
    finally:
        c.close()


class AppSettings(BaseModel):
    auto_pull: bool = True


@app.put("/api/settings")
def put_settings(s: AppSettings):
    c = con()
    try:
        c.execute("INSERT INTO settings(key, value, updated_at) VALUES ('app', ?, ?) ON CONFLICT(key) DO UPDATE SET "
                  "value=excluded.value, updated_at=excluded.updated_at", (json.dumps(s.model_dump()), db.now()))
        c.commit()
        return _settings(c)
    finally:
        c.close()


@app.get("/api/method")
def get_method():
    c = con()
    try:
        return {"method": M.get(c), "defaults": M.DEFAULTS, **M.describe()}
    finally:
        c.close()


@app.put("/api/method")
def put_method(value: dict):
    c = con()
    try:
        for qid, w in value.get("weights", {}).items():
            if abs(sum(float(x) for x in w.values()) - 1.0) > 0.011:
                raise HTTPException(400, f"weights for {qid} must add up to 1")
        return M.save(c, value)
    finally:
        c.close()


# ------------------------------------------------------------------ who do I ask
@app.get("/api/who")
def who(q: str = Query(..., min_length=1, max_length=500, description="a plain question"),
        place: str | None = Query(None, max_length=120, description="a government id, state code or place name"),
        live: int = 0):
    """Who do I ask: the roles of the processes a question names, who plays them, their office channels, links and
    the statute words (``lexflow.ask.who``); from the local SPARQL store, or the live endpoint with live=1."""
    from concurrent.futures import TimeoutError as PoolTimeout
    from ..ask import who as W
    c = con()
    try:
        r = W.route(q, place, c)
        try:
            return _sparql_pool().submit(W.answer, r, c, bool(live)).result(timeout=SPARQL_TIMEOUT * 2)
        except PoolTimeout as e:
            raise HTTPException(504, "the answer took too long") from e
    finally:
        c.close()


# ---------------------------------------------------------------- coverage
@app.get("/api/coverage")
def coverage(run: str | None = Query(None, max_length=60, pattern=r"^[\w\-]+$")):
    """The coverage matrix (lexflow.ask.coverage): the latest run's rows and matrix from coverage_runs, or the run
    named; ``runs`` lists every run.  The same data as docs/coverage-<run>.json."""
    from ..ask import coverage as CV
    c = con()
    try:
        run_id = run or CV.latest_run(c)
        if not run_id:
            return {"run": None, "runs": [], "questions": CV.questions(), "matrix": None, "rows": []}
        rows = CV.rows_of(c, run_id)
        if not rows:
            raise HTTPException(404, f"no coverage run {run_id}")
        return {"run": run_id, "runs": CV.runs(c), "questions": CV.questions(), "matrix": CV.matrix(rows),
                "rows": rows, "kinds": list(CV.KINDS)}
    finally:
        c.close()


# ------------------------------------------------------------------ sparql
# Read-only SPARQL over the local Wikibase copy (data/wikibase/, built by `lexflow sparql --build`) or, with
# live=1, the public endpoint.  GET only, 30 s, at most 2,000 rows; the dashboard's Query page uses it.
SPARQL_TIMEOUT = 30
SPARQL_ROWS = 2000


_SPARQL_POOL = None


def _sparql_pool():
    from concurrent.futures import ThreadPoolExecutor
    global _SPARQL_POOL
    if _SPARQL_POOL is None:
        _SPARQL_POOL = ThreadPoolExecutor(max_workers=2, thread_name_prefix="sparql")
    return _SPARQL_POOL


@app.get("/api/sparql/queries")
def sparql_queries():
    """The canned queries (docs/design/wikibase-schema.md section 6) with their question, parameters and text."""
    from ..publish import ids as I
    from ..publish import rdf
    from ..publish import sparql as SQ
    return {"queries": [q.as_dict() for q in SQ.catalogue()], "prefixes": rdf.QUERY_PREFIXES, "endpoint": rdf.ENDPOINT,
            "local_built": rdf.TTL_PATH.exists(), "ids_resolved": I.IDS_PATH.exists() or bool(I.database_ids()[1]),
            "turtle_stale": I.IdMap.turtle_stale(rdf.TTL_PATH), "max_rows": SPARQL_ROWS, "timeout": SPARQL_TIMEOUT}


@app.get("/api/sparql")
def sparql(q: str = Query(..., min_length=1, max_length=20000, description="a canned query name or SPARQL text"),
           live: int = 0, limit: int = SPARQL_ROWS,
           param: list[str] = Query(default=[], description="name=value for a VALUES parameter (repeatable)")):
    import time as _time
    from concurrent.futures import TimeoutError as PoolTimeout
    from ..publish import ids as I
    from ..publish import rdf
    from ..publish import sparql as SQ
    params = {}
    for p in param:
        if "=" in p:
            k, v = p.split("=", 1)
            params[k.strip()] = v.strip()
    query = SQ.get(q.strip()) if re.fullmatch(r"[a-z0-9\-]+", q.strip()) and SQ.exists(q.strip()) else SQ.parse(q, "")
    if query.live_only and not live:
        raise HTTPException(400, f"{query.name} is a federated query: run it with live=1")
    idmap = I.IdMap() if live else I.IdMap.for_turtle()
    try:
        text = SQ.prepare(query, params, idmap, live=bool(live))
    except KeyError as e:
        raise HTTPException(400, str(e)) from e
    limit = max(1, min(limit, SPARQL_ROWS))
    started = _time.monotonic()

    def run():
        store = None if live else rdf.open_store()
        return rdf.query(store, text, live=bool(live), timeout=SPARQL_TIMEOUT, limit=limit)
    try:
        rows = _sparql_pool().submit(run).result(timeout=SPARQL_TIMEOUT)
    except PoolTimeout as e:
        raise HTTPException(504, f"the query took longer than {SPARQL_TIMEOUT} s") from e
    except FileNotFoundError as e:
        raise HTTPException(409, str(e)) from e
    except Exception as e:
        raise HTTPException(400, f"query failed: {str(e)[:800]}") from e
    return {"vars": rows.vars, "rows": list(rows), "n": len(rows), "truncated": rows.truncated, "live": bool(live),
            "query": text, "name": query.name or None, "unresolved": sorted(set(idmap.unresolved)),
            "ms": int((_time.monotonic() - started) * 1000)}


# ------------------------------------------------------------------ static
if config.WEB_VENDOR_DIR.exists():
    app.mount("/vendor", StaticFiles(directory=str(config.WEB_VENDOR_DIR)), name="vendor")
app.mount("/static", StaticFiles(directory=str(config.DASHBOARD_DIR)), name="static")


@app.get("/", include_in_schema=False)
def index():
    """The dashboard, with a version stamp on its own script and stylesheet so browsers fetch new copies."""
    from fastapi.responses import HTMLResponse
    html = (config.DASHBOARD_DIR / "index.html").read_text(encoding="utf-8")
    for name in ("styles.css", "app.js"):
        stamp = int((config.DASHBOARD_DIR / name).stat().st_mtime)
        html = html.replace(f"/static/{name}\"", f"/static/{name}?v={stamp}\"")
    return HTMLResponse(html, headers={"Cache-Control": "no-cache"})


@app.get("/robots.txt", include_in_schema=False)
def robots():
    return PlainTextResponse("User-agent: *\nDisallow: /\n")
