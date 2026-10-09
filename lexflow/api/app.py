"""The dashboard's API, the browser plugin's lookup, and the static dashboard itself.

Read endpoints never block on network: when Turso is configured and ``auto_pull`` is on,
opening a state that has no local data starts a background pull job for it ("pull as needed").
"""
from __future__ import annotations

import json
import re
from contextlib import asynccontextmanager
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

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
            "models": [config.MODEL_A, config.MODEL_B], "origin": config.ORIGIN}


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
    c = con()
    try:
        g = db.one(c, "SELECT * FROM governments WHERE gov_id=?", gov_id)
        if not g:
            raise HTTPException(404)
        out = {"government": g, "answers": {}}
        for a in db.rows(c, "SELECT * FROM answers WHERE gov_id=?", gov_id):
            a["summary"] = db.loads(a["summary"], {})
            m = stats.model_detail(c, a["model_id"]) if a["model_id"] else None
            a["steps"] = stats.steps_of(m)
            a["law"] = db.one(c, "SELECT citation, heading, url, method, score FROM located_law "
                                 "WHERE state=? AND question=?", a["state"], a["question"])
            a["model"] = {k: m[k] for k in ("model_id", "title", "tier", "built_by", "quality", "completion")} if m \
                else None
            out["answers"][a["question"]] = a
        out["contacts"] = db.rows(c, "SELECT question, kind, value, label, source FROM contacts WHERE gov_id=?", gov_id)
        return out
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


@app.get("/api/search")
def search(q: str, limit: int = 20):
    c = con()
    try:
        return db.rows(c, "SELECT gov_id, name, kind, state, county_fips, population FROM governments "
                          "WHERE name LIKE ? ORDER BY population DESC LIMIT ?", f"%{q}%", limit)
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
    return FileResponse(config.DASHBOARD_DIR / "index.html")


@app.get("/robots.txt", include_in_schema=False)
def robots():
    return PlainTextResponse("User-agent: *\nDisallow: /\n")
