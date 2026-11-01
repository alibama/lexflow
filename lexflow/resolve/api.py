"""The Resolve page's API (``lexflow.resolve``): what the panel concluded, the bench, and one button a person
presses to apply an answer.  Reads never touch the network; the apply route calls the Glass Database with the
admin key from ``.env`` and refuses without one."""
from __future__ import annotations

import json
import re

from fastapi import HTTPException
from pydantic import BaseModel

from .. import config
from ..store import db
from . import bench as RB


class Decision(BaseModel):
    qid: str = ""                                  # a Q id, or "" to rule Wikidata out


def overview(c) -> dict:
    counts = {k: db.scalar(c, f"SELECT count(*) FROM resolve_queue WHERE {w}", default=0)
              for k, w in (("settled", "settled=1"), ("open", "settled=0"), ("applied", "applied_at IS NOT NULL"),
                           ("suggested", "suggested_at IS NOT NULL"))}
    counts["cases"] = db.scalar(c, "SELECT count(*) FROM resolve_queue", default=0)
    jobs = db.rows(c, "SELECT id, step, status, progress, message, created_at, finished_at FROM jobs "
                      "WHERE step IN ('resolve', 'resolve-bench') ORDER BY id DESC LIMIT 6")
    bench = None
    if RB.DOCS.exists():
        try:
            d = json.loads(RB.DOCS.read_text(encoding="utf-8"))
            bench = {k: d.get(k) for k in ("version", "threshold", "cases", "summary", "written_at")}
            bench["current"] = d.get("version") == RB.version()
        except (OSError, ValueError):
            bench = None
    return {"configured": {"glassdb": config.GLASSDB_URL, "token": bool(config.GLASSDB_ADMIN_TOKEN),
                           "search": bool(config.SEARXNG_URL), "models": config.RESOLVE_MODELS,
                           "threshold": config.RESOLVE_THRESHOLD, "pool": bool(config.LLM_NODES or config.OVERLAY != "none")},
            "queue": counts, "jobs": jobs, "bench": bench, "version": RB.version()}


def register(app) -> None:
    @app.get("/api/resolve")
    def resolve_overview():
        c = db.connect()
        try:
            return overview(c)
        finally:
            c.close()

    @app.get("/api/resolve/cases")
    def resolve_cases(state: str = "all", limit: int = 300):
        if state not in ("all", "open", "settled", "applied"):
            raise HTTPException(400, "state must be all, open, settled or applied")
        c = db.connect()
        try:
            rows = RB.queue_rows(c, state, min(max(int(limit), 1), 1000))
            # the candidates' Wikidata facts, from the evidence cache, so the page can show what the judge saw
            for r in rows:
                facts = {}
                for cand in r.get("candidates") or []:
                    e = db.one(c, "SELECT json FROM resolve_evidence WHERE kind='wd' AND ident=?", cand.get("qid") or "")
                    if e:
                        d = db.loads(e["json"], {})
                        facts[cand["qid"]] = {"description": d.get("description"), "facts": d.get("facts") or {},
                                              "wikipedia": (d.get("wikipedia") or "")[:300]}
                r["evidence"] = facts
            return {"rows": rows, "state": state}
        finally:
            c.close()

    @app.get("/api/resolve/bench")
    def resolve_bench():
        c = db.connect()
        try:
            rows = RB.stored(c)
            return {"version": RB.version(), "threshold": config.RESOLVE_THRESHOLD, "rows": rows,
                    "summary": RB.summarize(rows)}
        finally:
            c.close()

    @app.get("/api/resolve/enrich")
    def resolve_enrich(limit: int = 300):
        """What the enrich step proposed per record (website, Instagram, town) and, for check runs, how right it was."""
        from . import enrich as EN
        c = db.connect()
        try:
            rs = EN.rows(c, min(max(int(limit), 1), 1000))
            return {"rows": rs, "check": EN.check_summary(rs), "version": EN.version(), "search": bool(config.SEARXNG_URL)}
        finally:
            c.close()

    @app.post("/api/resolve/cases/{key:path}")
    def resolve_apply(key: str, body: Decision):
        """A person applies an answer: the Glass Database is told, and the local row records it."""
        if not config.GLASSDB_ADMIN_TOKEN:
            raise HTTPException(409, "GLASSDB_ADMIN_TOKEN is not set in .env: this copy can suggest but not decide")
        qid = (body.qid or "").strip().upper()
        if qid and not re.fullmatch(r"Q\d+", qid):
            raise HTTPException(400, "a Wikidata id looks like Q123, or '' to rule Wikidata out")
        from .source import GlassDatabase
        c = db.connect()
        try:
            if not db.one(c, "SELECT key FROM resolve_queue WHERE key=?", key):
                raise HTTPException(404, "that case is not in the local queue; run resolve first")
            try:
                out = GlassDatabase().decide(key, qid)
            except PermissionError as e:
                raise HTTPException(409, str(e))
            except Exception as e:  # noqa: BLE001
                raise HTTPException(502, f"the Glass Database did not take the decision: {e}")
            c.execute("UPDATE resolve_queue SET applied_at=?, applied_qid=? WHERE key=?", (db.now(), qid, key))
            c.commit()
            return {"ok": True, "key": key, "qid": qid, "remote": out}
        finally:
            c.close()
