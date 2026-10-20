"""The ``/api/compute/*`` endpoints and the shape the Compute page reads.

Lexflow's server asks the nodes; the browser never calls a node or the overlay.  No endpoint sets a URL: node
URLs come from the environment or the overlay alone.  A pull is never automatic: the operator picks a model on
the page, the endpoint says how many GB it downloads, and it runs as a ``models`` job whose log shows progress.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from pydantic import BaseModel

from .. import config
from ..pipeline import jobs
from ..store import db
from . import health as H
from . import nodes as N
from . import overlay as O
from . import pool as P

# download sizes (GB) of the models the page offers; "other" takes a typed name with no size known
SIZES_GB = {"qwen3:1.7b": 1.4, "qwen3:4b": 2.5, "qwen3:8b": 5.2, "qwen3:14b": 9.3, "qwen3:30b": 18.6,
            "gemma3:1b": 0.8, "gemma3:4b": 3.3, "gemma3:12b": 8.1, "nomic-embed-text": 0.27, "tev1:0.8b": 0.83}
HEADROOM_GB = 3.0


def _gb(size) -> float | None:
    return round(size / 1e9, 2) if isinstance(size, (int, float)) and size else None


def node_view(c, n: dict, busy: dict[str, int], leases: list[dict]) -> dict:
    loaded = {m.get("name"): m for m in (n.get("loaded") or [])}
    models = []
    for m in n.get("models") or []:
        name = m.get("name")
        ld = loaded.get(name)
        models.append({"name": name, "size_gb": _gb(m.get("size")), "quant": m.get("quant"), "params": m.get("params"),
                       "digest": m.get("digest"), "loaded": ld is not None,
                       "context_length": ld.get("context_length") if ld else None,
                       "expires_at": ld.get("expires_at") if ld else None,
                       "speed": P.speed(c, n["name"], name) if name else None})
    have = {m["name"] for m in models} | {f"{m['name']}".split(":")[0] for m in models}
    return {"name": n["name"], "url": n["url"], "source": n.get("source"), "status": n.get("status"),
            "enabled": bool(n.get("enabled")), "draining": bool(n.get("draining")), "gone": bool(n.get("gone")),
            "max_concurrency": n.get("max_concurrency"), "busy": busy.get(n["name"], 0), "priority": n.get("priority"),
            "threads": n.get("threads"), "part_time": bool(n.get("part_time")), "tags": n.get("tags") or [],
            "models_wanted": n.get("models_wanted") or [], "missing": [m for m in (n.get("models_wanted") or []) if m not in have],
            "version": n.get("version"), "last_ok": n.get("last_ok"), "last_error": n.get("last_error"),
            "checked_at": n.get("checked_at"), "backoff_until": n.get("backoff_until"), "fails": n.get("fails"),
            "host": n.get("host") or None, "status_url": n.get("status_url"), "overlay": n.get("overlay"), "embed": bool(n.get("embed")),
            "models": models, "in_flight": [l for l in leases if l["node"] == n["name"]],
            "pullable": pullable(n)}


def pullable(n: dict) -> list[dict]:
    """The models the page offers to pull on this node, with sizes and whether they fit the host's RAM."""
    ram = (n.get("host") or {}).get("ram_total_gb")
    have = {m.get("name") for m in (n.get("models") or [])}
    out = []
    for model, gb in SIZES_GB.items():
        if model in have or f"{model}:latest" in have:
            continue
        fits = None if not isinstance(ram, (int, float)) else gb + HEADROOM_GB <= ram
        out.append({"model": model, "gb": gb, "fits": fits})
    return out


def _lease_rows(c) -> list[dict]:
    now = datetime.now(timezone.utc)
    out = []
    for r in c.execute("SELECT * FROM leases ORDER BY id"):
        d = dict(r)
        try:
            started = datetime.strptime(d["started_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            d["elapsed_s"] = int((now - started).total_seconds())
        except (TypeError, ValueError):
            d["elapsed_s"] = None
        out.append(d)
    return out


def call_rows(c, node: str | None = None, model: str | None = None, job: int | None = None, limit: int = 100) -> list[dict]:
    where, args = [], []
    if node:
        where.append("node=?")
        args.append(node)
    if model:
        where.append("model=?")
        args.append(model)
    if job is not None:
        where.append("job_id=?")
        args.append(job)
    sql = "SELECT * FROM calls" + (" WHERE " + " AND ".join(where) if where else "") + " ORDER BY id DESC LIMIT ?"
    rows = []
    for r in c.execute(sql, args + [max(1, min(500, limit))]):
        d = dict(r)
        d["prefill_tps"] = round(d["prompt_tokens"] / d["prompt_s"], 1) if d.get("prompt_s") and d.get("prompt_tokens") else None
        d["gen_tps"] = round(d["out_tokens"] / d["out_s"], 1) if d.get("out_s") and d.get("out_tokens") else None
        d["ok"] = bool(d["ok"])
        rows.append(d)
    return rows


def single_node_view() -> dict:
    """With the pool off: the one Ollama at OLLAMA_URL, probed now, as a read-only card."""
    name, url = N.name_for_url(config.OLLAMA_URL), config.OLLAMA_URL.rstrip("/")
    res = H.probe(url, timeout=3)
    n = {"name": name, "url": url, "source": "env", "status": "online" if res["ok"] else "offline", "enabled": 1,
         "draining": 0, "gone": 0, "max_concurrency": 1, "priority": 50, "threads": None, "part_time": 0, "tags": [],
         "models_wanted": list(dict.fromkeys((config.EMBED_MODEL, config.MODEL_A, config.MODEL_B))), "version": res["version"],
         "last_ok": N.now() if res["ok"] else None, "last_error": res["error"], "checked_at": N.now(), "backoff_until": None,
         "fails": 0 if res["ok"] else 1, "host": None, "status_url": None, "overlay": None, "embed": 1,
         "models": res["models"] or [], "loaded": res["loaded"] or []}
    v = node_view(_NoCalls(), n, {}, [])
    return v


class _NoCalls:
    """A stand-in connection for the pool-off view: no calls table to read speeds from."""

    def execute(self, *a, **k):
        return self

    def fetchall(self):
        return []

    def fetchone(self):
        return None


def snapshot(limit: int = 20) -> dict:
    if not N.pool_on():
        n = single_node_view()
        return {"pool": False, "embed_node": n["name"], "embed_model": config.EMBED_MODEL, "overlay": None, "refused": [],
                "totals": {"nodes": 1, "online": int(n["status"] == "online"), "slots": 1, "busy": 0, "calls_1h": 0},
                "nodes": [n], "in_flight": [], "recent": [],
                "note": "No pool: LEXFLOW_LLM_NODES is not set, so every call goes to OLLAMA_URL. See docs/compute.md."}
    c = N.connect()
    try:
        P.ensure_synced(c)
        nodes = N.load_nodes(c)
        busy = P.busy_counts(c)
        leases = _lease_rows(c)
        views = [node_view(c, n, busy, leases) for n in nodes]
        hour = (datetime.now(timezone.utc) - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        embed_name, _ = N.embed_node(c)
        return {"pool": True, "embed_node": embed_name, "embed_model": config.EMBED_MODEL,
                "overlay": {"kind": config.OVERLAY, "url": config.OVERLAY_URL or None, "group": config.OVERLAY_COMPUTE_GROUP}
                if config.OVERLAY in ("netbird", "headscale") else None,
                "refused": list(N.REFUSED),
                "totals": {"nodes": len([v for v in views if not v["gone"]]),
                           "online": len([v for v in views if v["status"] == "online" and not v["gone"]]),
                           "slots": sum(v["max_concurrency"] or 0 for v in views if v["enabled"] and not v["gone"]),
                           "busy": sum(busy.values()),
                           "calls_1h": c.execute("SELECT count(*) FROM calls WHERE at >= ?", (hour,)).fetchone()[0]},
                "nodes": views, "in_flight": leases, "recent": call_rows(c, limit=limit)}
    finally:
        c.close()


def summary() -> dict | None:
    """One line for the Setup card: ``{"nodes": 3, "online": 2}`` when the pool is on, else None."""
    if not N.pool_on():
        return None
    c = N.connect()
    try:
        P.ensure_synced(c)
        nodes = [n for n in N.load_nodes(c) if not n.get("gone")]
        return {"nodes": len(nodes), "online": len([n for n in nodes if n.get("status") == "online"]),
                "names": [n["name"] for n in nodes]}
    finally:
        c.close()


class PullIn(BaseModel):
    model: str
    confirm: bool = False


class NodeEdit(BaseModel):
    max_concurrency: int | None = None
    threads: int | None = None


def _need_pool():
    if not N.pool_on():
        raise HTTPException(409, "the pool is off: set LEXFLOW_LLM_NODES (docs/compute.md)")


def _node(c, name: str) -> dict:
    n = N.get_node(c, name)
    if n is None or n.get("gone"):
        raise HTTPException(404, f"no node {name!r}: the configured nodes are {', '.join(N.names(c)) or 'none'}")
    return n


def register(app) -> None:
    @app.get("/api/compute")
    def compute_overview():
        return snapshot()

    @app.get("/api/compute/calls")
    def compute_calls(node: str | None = None, model: str | None = None, job: int | None = None, limit: int = 100):
        if not N.pool_on():
            return []
        c = N.connect()
        try:
            return call_rows(c, node, model, job, limit)
        finally:
            c.close()

    @app.post("/api/compute/check")
    def compute_check_all():
        _need_pool()
        c = N.connect()
        try:
            P.ensure_synced(c)
            if config.OVERLAY in ("netbird", "headscale"):
                O.sync(c)
            for n in N.load_nodes(c):
                H.check(c, n["name"])
            return {"checked": [n["name"] for n in N.load_nodes(c)]}
        finally:
            c.close()

    @app.get("/api/compute/nodes/{name}")
    def compute_node(name: str):
        if not N.pool_on():
            v = single_node_view()
            if v["name"] != name:
                raise HTTPException(404, f"no node {name!r}")
            return {**v, "recent": []}
        c = N.connect()
        try:
            P.ensure_synced(c)
            n = _node(c, name)
            return {**node_view(c, n, P.busy_counts(c), _lease_rows(c)), "recent": call_rows(c, node=name, limit=200)}
        finally:
            c.close()

    @app.post("/api/compute/nodes/{name}/check")
    def compute_node_check(name: str):
        _need_pool()
        c = N.connect()
        try:
            P.ensure_synced(c)
            _node(c, name)
            n = H.check(c, name)
            return node_view(c, n, P.busy_counts(c), _lease_rows(c))
        finally:
            c.close()

    @app.post("/api/compute/nodes/{name}/drain")
    def compute_node_drain(name: str):
        _need_pool()
        c = N.connect()
        try:
            P.ensure_synced(c)
            _node(c, name)
            n = N.set_edited(c, name, draining=1)
            return node_view(c, n, P.busy_counts(c), _lease_rows(c))
        finally:
            c.close()

    @app.post("/api/compute/nodes/{name}/resume")
    def compute_node_resume(name: str):
        _need_pool()
        c = N.connect()
        try:
            P.ensure_synced(c)
            _node(c, name)
            n = N.set_edited(c, name, draining=0, enabled=1)
            return node_view(c, n, P.busy_counts(c), _lease_rows(c))
        finally:
            c.close()

    @app.post("/api/compute/nodes/{name}/disable")
    def compute_node_disable(name: str):
        _need_pool()
        c = N.connect()
        try:
            P.ensure_synced(c)
            _node(c, name)
            n = N.set_edited(c, name, enabled=0)
            return node_view(c, n, P.busy_counts(c), _lease_rows(c))
        finally:
            c.close()

    @app.put("/api/compute/nodes/{name}")
    def compute_node_edit(name: str, body: NodeEdit):
        _need_pool()
        changes = {}
        if body.max_concurrency is not None:
            if not 1 <= body.max_concurrency <= 8:
                raise HTTPException(400, "max_concurrency is 1 to 8")
            changes["max_concurrency"] = body.max_concurrency
        if body.threads is not None:
            if not 1 <= body.threads <= 64:
                raise HTTPException(400, "threads is 1 to 64")
            changes["threads"] = body.threads
        c = N.connect()
        try:
            P.ensure_synced(c)
            _node(c, name)
            n = N.set_edited(c, name, **changes) if changes else N.get_node(c, name)
            return node_view(c, n, P.busy_counts(c), _lease_rows(c))
        finally:
            c.close()

    @app.post("/api/compute/nodes/{name}/pull")
    def compute_node_pull(name: str, body: PullIn):
        """Queue a ``models`` job that pulls ``model`` onto this node.  Says how many GB it downloads; refused for
        a node that is not online (409); needs ``confirm`` when the model plus 3 GB is more than the host's RAM."""
        model = body.model.strip()
        if not N.MODEL_RE.match(model):
            raise HTTPException(400, "model names are like qwen3:8b")
        if N.pool_on():
            c = N.connect()
            try:
                P.ensure_synced(c)
                n = _node(c, name)
            finally:
                c.close()
        else:
            n = single_node_view()
            if n["name"] != name:
                raise HTTPException(404, f"no node {name!r}")
        if n.get("status") != "online":
            raise HTTPException(409, f"{name} is {n.get('status')}: a pull needs an online node")
        gb = SIZES_GB.get(model)
        ram = (n.get("host") or {}).get("ram_total_gb")
        if gb and isinstance(ram, (int, float)) and gb + HEADROOM_GB > ram and not body.confirm:
            raise HTTPException(409, f"{model} is {gb} GB and {name} has {ram} GB of RAM: it may not run there. "
                                     "Send confirm: true to pull it anyway.")
        s = db.connect()
        try:
            job_id = jobs.enqueue(s, "models", {"node": name, "models": model})
        finally:
            s.close()
        return {"job_id": job_id, "model": model, "node": name, "gb": gb,
                "message": f"This downloads {f'{gb} GB' if gb else 'an unknown size'} from the Ollama registry onto {name}."}
