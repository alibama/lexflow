"""The dispatcher: each model call goes to a node that has the model and a free slot; when a node fails, the
call moves to another.

Works across processes (each job is its own process; they share ``compute.db``): a slot is a row in ``leases``,
claimed with one atomic INSERT ... SELECT that checks the node's ``max_concurrency``.  Order of preference: the
least busy node, then one that already has the model loaded with this context length (another ``num_ctx`` makes
Ollama reload it), then the generation speed measured there, then priority.

``LEXFLOW_LLM_ONLY=<node>`` (set for a job with ``args.node``) pins every call of the process to one node, for
strict comparisons; a client can also pin itself (``OllamaClient.node``).  Embeddings always go to the one embed
node (``nodes.embed_node``).  Retrying a call on another node is safe: lexflow's calls hold no state and run at
temperature 0.
"""
from __future__ import annotations

import json
import os
import random
import sys
import threading
import time
from datetime import datetime, timedelta, timezone

import requests

from .. import config
from . import health as H
from . import nodes as N

MAX_ATTEMPTS = 3
LEASE_MAX_AGE = 1900          # seconds: a lease older than the longest call timeout (1800 s) is stale
_synced: set[str] = set()
_sync_lock = threading.Lock()


class PoolError(RuntimeError):
    """Base class: no node can take the call."""


class NoNode(PoolError):
    """No configured node has the model."""


class NoFreeSlot(PoolError):
    """The nodes that have the model took no new work within LEXFLOW_LLM_WAIT seconds."""


class NoNodeLeft(PoolError):
    """Every node that has the model failed during this call."""


def job_context() -> tuple[int | None, str | None]:
    """The job this process runs (``LEXFLOW_JOB_ID`` / ``LEXFLOW_JOB_STEP``, set by the runner and ``lexflow run``)."""
    jid = os.environ.get("LEXFLOW_JOB_ID", "").strip()
    return (int(jid) if jid.isdigit() else None), (os.environ.get("LEXFLOW_JOB_STEP", "").strip() or None)


def ensure_synced(con) -> None:
    """Once per process: the table's env rows match LEXFLOW_LLM_NODES."""
    key = str(N.db_path())
    if key in _synced:
        return
    with _sync_lock:
        if key not in _synced:
            N.sync_env(con)
            _synced.add(key)


def routes(url: str | None) -> bool:
    """Does the pool route calls to this base URL: the pool is on and the URL is OLLAMA_URL or a node's."""
    if not N.pool_on():
        return False
    u = (url or "").rstrip("/")
    if u == config.OLLAMA_URL.rstrip("/") or u in N.env_urls().values():
        return True
    con = N.connect()
    try:
        ensure_synced(con)
        return con.execute("SELECT 1 FROM nodes WHERE url=? AND gone=0", (u,)).fetchone() is not None
    finally:
        con.close()


def has_model(node: dict, model: str) -> bool:
    names = {m.get("name") for m in (node.get("models") or [])}
    return model in names or f"{model}:latest" in names


def loaded_with(node: dict, model: str, num_ctx: int | None) -> bool:
    for m in node.get("loaded") or []:
        if m.get("name") in (model, f"{model}:latest"):
            return num_ctx is None or not m.get("context_length") or int(m["context_length"]) >= int(num_ctx)
    return False


def busy_counts(con) -> dict[str, int]:
    return {r["node"]: r["n"] for r in con.execute("SELECT node, count(*) AS n FROM leases GROUP BY node")}


def speed(con, node: str, model: str, limit: int = 20) -> dict:
    """Tokens per second on this node for this model from its last ``limit`` good calls."""
    rows = con.execute("SELECT prompt_tokens, prompt_s, out_tokens, out_s FROM calls WHERE node=? AND model=? AND ok=1 "
                       "AND kind='chat' ORDER BY id DESC LIMIT ?", (node, model, limit)).fetchall()
    pt = sum(r["prompt_tokens"] or 0 for r in rows)
    ps = sum(r["prompt_s"] or 0 for r in rows)
    ot = sum(r["out_tokens"] or 0 for r in rows)
    os_ = sum(r["out_s"] or 0 for r in rows)
    return {"prefill_tps": round(pt / ps, 1) if ps else None, "gen_tps": round(ot / os_, 1) if os_ else None,
            "calls": len(rows)}


def ready(node: dict) -> bool:
    return bool(node.get("enabled")) and not node.get("draining") and not node.get("gone") \
        and node.get("status") == "online"


def why_not(node: dict, model: str, kind: str) -> str:
    if node.get("gone"):
        return f"{node['name']}: left the overlay group"
    if not node.get("enabled"):
        return f"{node['name']}: disabled"
    if node.get("draining"):
        return f"{node['name']}: draining"
    if node.get("status") != "online":
        return f"{node['name']}: {node.get('status')}" + (f" ({node['last_error']})" if node.get("last_error") else "")
    if kind == "chat" and not has_model(node, model):
        return f"{node['name']}: no {model}"
    return f"{node['name']}: busy"


def candidates(con, model: str, kind: str, pin: str | None = None, exclude=()) -> list[dict]:
    """The nodes that could serve this call (before slots): for ``embed`` the embed node alone; for ``chat`` the
    nodes that have the model (an unchecked or stale node is checked inline first).  ``pin`` narrows to one."""
    ensure_synced(con)
    pin = pin or config.LLM_ONLY or None
    nodes = [n for n in N.load_nodes(con) if not n.get("gone") and n["name"] not in exclude]
    if kind == "embed":
        name, url = N.embed_node(con)
        nodes = [n for n in nodes if n["name"] == name]
        if not nodes:                                   # the embed URL is not a pool node: a synthetic row
            nodes = [{"name": name, "url": url, "enabled": 1, "draining": 0, "gone": 0, "status": "online",
                      "max_concurrency": 1, "threads": None, "priority": 50, "models": [], "loaded": [],
                      "synthetic": True}]
    if pin:
        nodes = [n for n in nodes if n["name"] == pin]
    out = []
    for n in nodes:
        if not n.get("synthetic"):
            n = H.refresh_if_stale(con, n)
        if kind == "embed" or has_model(n, model):
            out.append(n)
    return out


def claim_slot(con, node: dict, model: str, kind: str, job_id=None, step=None) -> int | None:
    """One atomic statement: a lease when the node is enabled, not draining and under its max_concurrency."""
    if node.get("synthetic"):
        return -1
    ts = N.now()
    cur = con.execute(
        "INSERT INTO leases(node, model, kind, job_id, step, runner, pid, started_at, beat_at) "
        "SELECT ?, ?, ?, ?, ?, ?, ?, ?, ? "
        "WHERE (SELECT enabled FROM nodes WHERE name=?) = 1 AND (SELECT draining FROM nodes WHERE name=?) = 0 "
        "AND (SELECT count(*) FROM leases WHERE node=?) < (SELECT max_concurrency FROM nodes WHERE name=?)",
        (node["name"], model, kind, job_id, step, _runner(), os.getpid(), ts, ts,
         node["name"], node["name"], node["name"], node["name"]))
    con.commit()
    return cur.lastrowid if cur.rowcount == 1 else None


def release(con, lease_id: int | None) -> None:
    if lease_id and lease_id > 0:
        con.execute("DELETE FROM leases WHERE id=?", (lease_id,))
        con.commit()


def _runner() -> str:
    return os.environ.get("LEXFLOW_RUNNER_ID", "").strip() or __import__("socket").gethostname()


def _alive(pid: int | None) -> bool:
    if not pid:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def reap_leases(con) -> int:
    """Drop leases whose process is dead on this runner, or that are older than any call can run."""
    cutoff = (datetime.now(timezone.utc) - timedelta(seconds=LEASE_MAX_AGE)).strftime("%Y-%m-%dT%H:%M:%SZ")
    n = 0
    for r in con.execute("SELECT id, runner, pid, started_at FROM leases").fetchall():
        dead = (r["runner"] == _runner() and not _alive(r["pid"])) or (r["started_at"] or "") < cutoff
        if dead:
            n += con.execute("DELETE FROM leases WHERE id=?", (r["id"],)).rowcount
    if n:
        con.commit()
    return n


def acquire(con, model: str, kind: str, num_ctx: int | None = None, *, pin: str | None = None, exclude=(),
            wait: float | None = None, job_id=None, step=None) -> tuple[dict, int, float]:
    """A node with the model and a free slot, claimed for this call: ``(node, lease id, seconds waited)``."""
    wait = config.LLM_WAIT if wait is None else wait
    t0 = time.time()
    deadline = t0 + wait
    reaped = False
    while True:
        nodes = candidates(con, model, kind, pin=pin, exclude=exclude)
        if not nodes and exclude:
            raise NoNodeLeft(f"{model}: tried {', '.join(exclude)}; no other node has it")
        if not nodes:
            raise NoNode(f"no node has {model}" + (f" (pinned to {pin or config.LLM_ONLY})" if (pin or config.LLM_ONLY) else "")
                         + ": pull it on the Compute page")
        busy = busy_counts(con)
        ok = [n for n in nodes if ready(n) or n.get("synthetic")]
        ok.sort(key=lambda n: (busy.get(n["name"], 0) / max(1, int(n.get("max_concurrency") or 1)),
                               not loaded_with(n, model, num_ctx),
                               -(speed(con, n["name"], model).get("gen_tps") or 0.0),
                               -int(n.get("priority") or 50)))
        for n in ok:
            lease = claim_slot(con, n, model, kind, job_id, step)
            if lease is not None:
                return n, lease, round(time.time() - t0, 2)
        if not reaped:
            reap_leases(con)
            reaped = True
        if time.time() > deadline:
            raise NoFreeSlot(f"{model}: " + "; ".join(why_not(n, model, kind) for n in nodes))
        time.sleep(random.uniform(0.5, 1.5))


def record_call(con, node: str, model: str, kind: str, *, data: dict | None, ok: bool, error: str | None = None,
                attempt: int = 1, num_ctx: int | None = None, wait_s: float | None = None, total_s: float | None = None,
                job_id=None, step=None) -> None:
    d = data or {}

    def secs(k):
        v = d.get(k)
        return round(v / 1e9, 3) if isinstance(v, (int, float)) else None
    con.execute(
        "INSERT INTO calls(at, node, model, digest, kind, job_id, step, num_ctx, attempt, prompt_tokens, prompt_s, "
        "out_tokens, out_s, load_s, total_s, wait_s, ok, error) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (N.now(), node, model, None, kind, job_id, step, num_ctx, attempt, d.get("prompt_eval_count"),
         secs("prompt_eval_duration"), d.get("eval_count"), secs("eval_duration"), secs("load_duration"),
         secs("total_duration") if d.get("total_duration") else total_s, wait_s, int(ok), (error or None)))
    con.commit()
    if random.random() < 0.02:
        prune_calls(con)


def prune_calls(con) -> None:
    """Rolling and capped: rows older than 30 days go, and at most LEXFLOW_LLM_CALLS_MAX stay."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
    con.execute("DELETE FROM calls WHERE at < ?", (cutoff,))
    con.execute("DELETE FROM calls WHERE id <= (SELECT id FROM calls ORDER BY id DESC LIMIT 1 OFFSET ?)",
                (config.LLM_CALLS_MAX,))
    con.commit()


def _note_missing(con, node: dict, model: str) -> None:
    """A node's /api/tags said it had the model but the call got 404: drop it from the row until the next check."""
    models = [m for m in (node.get("models") or []) if m.get("name") not in (model, f"{model}:latest")]
    con.execute("UPDATE nodes SET models=? WHERE name=?", (json.dumps(models), node["name"]))
    con.commit()


def call(path: str, body: dict, *, model: str, kind: str = "chat", timeout: float = 900, pin: str | None = None,
         wait: float | None = None) -> tuple[requests.Response, str]:
    """POST ``body`` to ``path`` on the best node; on a connection error, a timeout or a 5xx, try another (at most
    MAX_ATTEMPTS nodes).  Returns the response and the node's name.  Other 4xx go back to the caller."""
    job_id, step = job_context()
    num_ctx = (body.get("options") or {}).get("num_ctx")
    tried: list[str] = []
    con = N.connect()
    try:
        for attempt in range(1, MAX_ATTEMPTS + 1):
            node, lease, waited = acquire(con, model, kind, num_ctx, pin=pin, exclude=tried, wait=wait,
                                          job_id=job_id, step=step)
            sent = dict(body)
            if node.get("threads") and kind == "chat":
                sent["options"] = {**(body.get("options") or {})}
                sent["options"].setdefault("num_thread", int(node["threads"]))
            t0 = time.time()
            try:
                r = requests.post(f"{node['url'].rstrip('/')}{path}", json=sent, timeout=timeout)
            except (requests.ConnectionError, requests.Timeout) as e:
                release(con, lease)
                err = f"{type(e).__name__}: {str(e)[:160]}"
                if not node.get("synthetic"):
                    H.record(con, node["name"], {"ok": False, "error": err})
                record_call(con, node["name"], model, kind, data=None, ok=False, error=err, attempt=attempt,
                            num_ctx=num_ctx, wait_s=waited, total_s=round(time.time() - t0, 3), job_id=job_id, step=step)
                print(f"compute: {node['name']} failed ({err}); trying another node", file=sys.stderr)
                tried.append(node["name"])
                continue
            release(con, lease)
            if r.status_code == 404 and "not found" in r.text.lower() and not node.get("synthetic"):
                _note_missing(con, node, model)
                record_call(con, node["name"], model, kind, data=None, ok=False, error=f"HTTP 404: {r.text[:120]}",
                            attempt=attempt, num_ctx=num_ctx, wait_s=waited, job_id=job_id, step=step)
                tried.append(node["name"])
                continue
            if r.status_code >= 500:
                err = f"HTTP {r.status_code}: {r.text[:120]}"
                if not node.get("synthetic"):
                    H.record(con, node["name"], {"ok": False, "error": err})
                record_call(con, node["name"], model, kind, data=None, ok=False, error=err, attempt=attempt,
                            num_ctx=num_ctx, wait_s=waited, total_s=round(time.time() - t0, 3), job_id=job_id, step=step)
                tried.append(node["name"])
                continue
            data = None
            if r.ok:
                try:
                    data = r.json()
                except ValueError:
                    data = None
                if not node.get("synthetic") and node.get("fails"):
                    con.execute("UPDATE nodes SET fails=0, status='online', backoff_until=NULL, last_ok=? WHERE name=?",
                                (N.now(), node["name"]))
                    con.commit()
            record_call(con, node["name"], model, kind, data=data if isinstance(data, dict) else None, ok=r.ok,
                        error=None if r.ok else f"HTTP {r.status_code}", attempt=attempt, num_ctx=num_ctx,
                        wait_s=waited, total_s=round(time.time() - t0, 3), job_id=job_id, step=step)
            return r, node["name"]
        raise NoNodeLeft(f"{model}: tried {', '.join(tried)}")
    finally:
        con.close()


def free_slots(con=None, model: str | None = None) -> int:
    """Open slots on online, enabled, non-draining nodes (that have ``model``): what a batch may fan out over."""
    c = con or N.connect()
    try:
        ensure_synced(c)
        busy = busy_counts(c)
        total = 0
        for n in N.load_nodes(c):
            if not ready(n) or (model and not has_model(n, model)):
                continue
            total += max(0, int(n.get("max_concurrency") or 1) - busy.get(n["name"], 0))
        return total
    finally:
        if con is None:
            c.close()


def node_count(con=None) -> int:
    """How many usable nodes the pool has (0 when the pool is off): the one-heavy-job rule relaxes above one."""
    if not N.pool_on():
        return 0
    c = con or N.connect()
    try:
        ensure_synced(c)
        return c.execute("SELECT count(*) FROM nodes WHERE gone=0 AND enabled=1").fetchone()[0]
    finally:
        if con is None:
            c.close()


def union_models(con=None) -> list[str]:
    """The model names on enabled, online nodes: what ``asker_for`` and the Setup card may count on."""
    c = con or N.connect()
    try:
        ensure_synced(c)
        out: list[str] = []
        for n in N.load_nodes(c):
            if n.get("gone") or not n.get("enabled"):
                continue
            n = H.refresh_if_stale(c, n)
            if n.get("status") == "online":
                out += [m["name"] for m in (n.get("models") or []) if m.get("name")]
        return sorted(dict.fromkeys(out))
    finally:
        if con is None:
            c.close()
