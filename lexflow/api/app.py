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

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .. import config
from ..municipal import method as M
from ..municipal import states as S
from ..municipal import stats
from ..municipal.questions import QUESTIONS
from ..pipeline import jobs
from ..pipeline.steps import STEPS, COMPOSITE, checklist, ollama_state
from ..store import db
from ..store import turso as T

runner = jobs.Runner()


@asynccontextmanager
async def lifespan(_app):
    config.ensure_dirs()
    with db.session():
        pass
    if config.JOB_RUNNER:          # a second, read-only instance on the same database can run without one
        runner.start()
    yield
    runner.stop.set()


app = FastAPI(title="lexflow", version="1.0", lifespan=lifespan)


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
    c = con()
    try:
        return {"steps": checklist(c), "services": services(c)}
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
    return {"ollama": {"url": config.OLLAMA_URL, **o, "want": [config.MODEL_A, config.MODEL_B]}, "turso": turso,
            "searxng": searx, "dokuwiki": {"configured": bool(config.DOKUWIKI_URL and config.DOKUWIKI_TOKEN),
                                           "url": config.DOKUWIKI_URL or None},
            "data_dir": str(config.DATA_DIR)}


# -------------------------------------------------------------------- jobs
class JobIn(BaseModel):
    step: str
    args: dict = {}


@app.post("/api/jobs")
def create_job(job: JobIn):
    if job.step not in STEPS and job.step not in COMPOSITE:
        raise HTTPException(400, f"unknown step {job.step}")
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
    c = con()
    try:
        return stats.county_layer(c, _q(question), layer)
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
            SELECT g.gov_id, g.name, g.kind, g.state, g.population, count(l.question) AS researched,
                   max(l.verified) AS verified, max(l.researched) AS researched_on
            FROM local_answers l JOIN governments g ON g.gov_id = l.gov_id
            GROUP BY g.gov_id ORDER BY g.population DESC""")
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
    c = con()
    try:
        return db.rows(c, """SELECT question_id, max(question_text) AS question, count(*) AS answers,
                                    sum(status='answered') AS answered, sum(status='partial') AS partial,
                                    sum(status='not_found') AS not_found, sum(published) AS published,
                                    max(updated_at) AS updated_at
                             FROM asked_answers GROUP BY question_id ORDER BY max(updated_at) DESC""")
    finally:
        c.close()


def _ask_row(r: dict) -> dict:
    for k in ("sections", "facts", "answer", "local", "metrics"):
        r[k] = db.loads(r.get(k), None)
    return r


@app.get("/api/ask/{qid}")
def ask_question(qid: str):
    c = con()
    try:
        rows = [_ask_row(r) for r in db.rows(c, "SELECT * FROM asked_answers WHERE question_id=? "
                                                "ORDER BY gov_id IS NOT NULL, state, target", qid)]
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
                          "local": len(((r["local"] or {}).get("locus")) or []), "model": r["model"],
                          "seconds": r["seconds"], "published": r["published"], "updated_at": r["updated_at"]})
        return {"question_id": qid, "question": rows[0]["question_text"], "answers": brief}
    finally:
        c.close()


@app.get("/api/ask/{qid}/{target}")
def ask_answer(qid: str, target: str):
    c = con()
    try:
        r = db.one(c, "SELECT * FROM asked_answers WHERE question_id=? AND target=?", qid, target)
        if not r:
            raise HTTPException(404, "no such answer")
        return _ask_row(r)
    finally:
        c.close()


class PublishIn(BaseModel):
    published: bool


@app.post("/api/ask/{qid}/{target}/publish")
def ask_publish(qid: str, target: str, body: PublishIn):
    """Mark an answer for (or withdraw it from) the next Lexipedia publish, as its own sub-page."""
    c = con()
    try:
        n = c.execute("UPDATE asked_answers SET published=?, updated_at=? WHERE question_id=? AND target=?",
                      (int(body.published), db.now(), qid, target)).rowcount
        db.bump(c)
        c.commit()
        if not n:
            raise HTTPException(404, "no such answer")
        return {"published": body.published}
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
