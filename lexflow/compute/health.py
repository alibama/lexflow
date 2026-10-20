"""Read-only health checks of each node, with back-off, and the poller thread.

A check is ``GET /api/version`` (proves the node answers, even while it generates), ``GET /api/tags`` (the models
on disk), ``GET /api/ps`` (the models loaded, with their context length) and, when the node has one, its status
URL (CPU, RAM, load, temperature: the host lines on the Compute page).  Nothing is written to a node.

Each failure sets ``backoff_until = now + min(900, 30 x 2^(fails-1)) x random(0.8-1.2)`` seconds; after five
failures in a row the node is ``offline`` and checked every two minutes.  One good check restores it.
"""
from __future__ import annotations

import json
import random
import sys
import threading
import time
from datetime import datetime, timedelta, timezone

import requests

from .. import config
from . import nodes as N

OFFLINE_AFTER = 5            # consecutive failures before a node is offline
OFFLINE_POLL = 120           # seconds between checks of an offline node
STALE = 60                   # a CLI-only process re-checks a node whose last check is older than this
TAGS_EVERY = 60              # seconds between /api/tags reads of an online node (version changes force one)


def _ts(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def probe(url: str, status_url: str | None = None, timeout: float = 3.0, tags: bool = True) -> dict:
    """One read-only look at an Ollama: ``{"ok", "version", "models", "loaded", "host", "error"}``."""
    base = url.rstrip("/")
    out: dict = {"ok": False, "version": None, "models": None, "loaded": None, "host": None, "error": None}
    try:
        r = requests.get(f"{base}/api/version", timeout=timeout)
        r.raise_for_status()
        out["version"] = (r.json() or {}).get("version")
        out["ok"] = True
    except (requests.RequestException, ValueError) as e:
        out["error"] = f"{type(e).__name__}: {str(e)[:160]}"
        return out
    if tags:
        try:
            r = requests.get(f"{base}/api/tags", timeout=max(timeout, 5))
            r.raise_for_status()
            out["models"] = [{"name": m.get("name") or m.get("model"), "size": m.get("size"),
                              "digest": (m.get("digest") or "")[:12],
                              "params": (m.get("details") or {}).get("parameter_size"),
                              "quant": (m.get("details") or {}).get("quantization_level"),
                              "family": (m.get("details") or {}).get("family")}
                             for m in (r.json() or {}).get("models", [])]
        except (requests.RequestException, ValueError) as e:
            out["error"] = f"tags: {type(e).__name__}"
    try:
        r = requests.get(f"{base}/api/ps", timeout=max(timeout, 5))
        r.raise_for_status()
        out["loaded"] = [{"name": m.get("name") or m.get("model"), "size": m.get("size"),
                          "size_vram": m.get("size_vram"), "context_length": m.get("context_length"),
                          "expires_at": m.get("expires_at"), "digest": (m.get("digest") or "")[:12]}
                         for m in (r.json() or {}).get("models", [])]
    except (requests.RequestException, ValueError):
        out["loaded"] = []
    if status_url:
        try:
            r = requests.get(status_url, timeout=max(timeout, 5))
            r.raise_for_status()
            host = r.json()
            out["host"] = host if isinstance(host, dict) else None
        except (requests.RequestException, ValueError):
            out["host"] = None
    return out


def backoff_seconds(fails: int) -> float:
    return min(900, 30 * 2 ** max(0, fails - 1)) * random.uniform(0.8, 1.2)


def record(con, name: str, result: dict) -> dict | None:
    """Write a probe's result on the node's row: online and ``fails=0`` on success, else the next back-off."""
    cur = N.get_node(con, name)
    if cur is None:
        return None
    ts = N.now()
    if result["ok"]:
        sets = {"status": "online", "fails": 0, "backoff_until": None, "version": result.get("version"),
                "last_ok": ts, "last_error": None, "checked_at": ts, "loaded": json.dumps(result.get("loaded") or [])}
        if result.get("models") is not None:
            sets["models"] = json.dumps(result["models"])
        if result.get("host") is not None or cur.get("status_url"):
            sets["host"] = json.dumps(result.get("host")) if result.get("host") is not None else None
    else:
        fails = int(cur.get("fails") or 0) + 1
        wait = OFFLINE_POLL if fails >= OFFLINE_AFTER else backoff_seconds(fails)
        sets = {"status": "offline" if fails >= OFFLINE_AFTER else "backoff", "fails": fails,
                "backoff_until": _ts(datetime.now(timezone.utc) + timedelta(seconds=wait)),
                "last_error": result.get("error"), "checked_at": ts, "loaded": json.dumps([])}
    con.execute(f"UPDATE nodes SET {', '.join(f'{k}=?' for k in sets)} WHERE name=?", list(sets.values()) + [name])
    con.commit()
    return N.get_node(con, name)


def check(con, name: str, timeout: float = 3.0) -> dict | None:
    """Probe one node now and record the result.  An overlay peer the overlay says is disconnected is set
    ``offline`` without a request."""
    node = N.get_node(con, name)
    if node is None:
        return None
    ov = node.get("overlay") or {}
    if node["source"] == "overlay" and ov and ov.get("connected") is False:
        con.execute("UPDATE nodes SET status='offline', checked_at=?, last_error='overlay: disconnected', loaded='[]' "
                    "WHERE name=?", (N.now(), name))
        con.commit()
        return N.get_node(con, name)
    return record(con, name, probe(node["url"], node.get("status_url"), timeout=timeout))


def due(node: dict, now: datetime | None = None, poll: int | None = None) -> bool:
    """Is this node due a check: an online node every ``poll`` seconds, a backing-off or offline one at its
    ``backoff_until``, an unchecked one now."""
    now = now or datetime.now(timezone.utc)
    poll = poll or config.LLM_POLL
    if node.get("gone"):
        return False
    if not node.get("checked_at"):
        return True
    if node["status"] in ("backoff", "offline"):
        bu = node.get("backoff_until")
        return not bu or bu <= _ts(now)
    last = datetime.strptime(node["checked_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    return (now - last).total_seconds() >= poll


def check_due(con, poll: int | None = None, timeout: float = 3.0) -> list[str]:
    """Check every node that is due, each in its own thread so one dead node never delays the others."""
    todo = [n["name"] for n in N.load_nodes(con) if due(n, poll=poll)]
    if not todo:
        return []
    results: dict[str, dict] = {}

    def one(n: dict):
        ov = n.get("overlay") or {}
        if n["source"] == "overlay" and ov and ov.get("connected") is False:
            results[n["name"]] = {"ok": False, "error": "overlay: disconnected", "skip": True}
        else:
            results[n["name"]] = probe(n["url"], n.get("status_url"), timeout=timeout)
    threads = [threading.Thread(target=one, args=(n,), daemon=True) for n in N.load_nodes(con) if n["name"] in todo]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout + 12)
    for name, res in results.items():
        if res.get("skip"):
            con.execute("UPDATE nodes SET status='offline', checked_at=?, last_error=?, loaded='[]' WHERE name=?",
                        (N.now(), res["error"], name))
            con.commit()
        else:
            record(con, name, res)
    return list(results)


def refresh_if_stale(con, node: dict, max_age: int = STALE) -> dict:
    """For a CLI-only run with no poller: re-check a node whose last check is older than ``max_age`` seconds."""
    ca = node.get("checked_at")
    if ca:
        last = datetime.strptime(ca, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        if (datetime.now(timezone.utc) - last).total_seconds() < max_age:
            return node
    elif node["status"] in ("backoff", "offline") and not due(node):
        return node
    return check(con, node["name"]) or node


class Poller:
    """Checks the nodes every LEXFLOW_LLM_POLL seconds and re-reads the overlay every LEXFLOW_OVERLAY_POLL
    seconds; started by the API's lifespan when the pool is on.

    One Poller is a module-level singleton (``lexflow.api.app.poller``) and a lifespan runs once per app start,
    but a process may start the app many times (every ``TestClient`` in a test run does).  So ``start`` is
    idempotent: it starts a fresh daemon thread when none is running, and does nothing while one is; ``shutdown``
    stops it and waits for it, after which ``start`` may run it again.  ``stop`` is the event the thread watches
    (``poller.stop.set()`` alone also ends it, the thread then being replaced on the next ``start``)."""

    def __init__(self, poll: float | None = None, overlay_poll: float | None = None):
        self.poll = poll or config.LLM_POLL
        self.overlay_poll = overlay_poll or config.OVERLAY_POLL
        self.stop = threading.Event()
        self.ticks = 0
        self.starts = 0
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()

    @property
    def name(self) -> str:
        return "lexflow-compute"

    def is_alive(self) -> bool:
        t = self._thread
        return bool(t and t.is_alive())

    def start(self) -> bool:
        """Start the poller thread unless one is already running; True when this call started it."""
        with self._lock:
            if self._thread is not None and self._thread.is_alive() and not self.stop.is_set():
                return False
            if self._thread is not None and self._thread.is_alive():   # told to stop, not yet gone: a moment to go
                self._thread.join(timeout=2)                           # (it ends on its own event in any case)
            self.stop = threading.Event()
            self._thread = threading.Thread(target=self.run, daemon=True, name=self.name)
            self.starts += 1
            self._thread.start()
            return True

    def shutdown(self, timeout: float | None = None) -> None:
        """Stop the poller thread and wait for it (``timeout`` seconds at most; the thread is a daemon)."""
        self.stop.set()
        t = self._thread
        if t is not None and t.is_alive() and t is not threading.current_thread():
            t.join(timeout if timeout is not None else max(self.poll, 5) + 1)

    def join(self, timeout: float | None = None) -> None:
        t = self._thread
        if t is not None:
            t.join(timeout)

    def run(self):
        from . import overlay as O
        from . import pool as P
        stop = self.stop                                           # this thread's event, not a later one's
        con = N.connect()
        last_overlay = 0.0
        try:
            N.sync_env(con)
            while not stop.is_set():
                try:
                    if config.OVERLAY in ("netbird", "headscale") and time.time() - last_overlay >= self.overlay_poll:
                        O.sync(con)
                        last_overlay = time.time()
                    check_due(con, poll=int(self.poll))
                    P.reap_leases(con)
                    self.ticks += 1
                except Exception as e:  # noqa: BLE001 - keep polling
                    print(f"compute poller: {type(e).__name__}: {e}", file=sys.stderr)
                stop.wait(min(self.poll, 5))
        finally:
            con.close()
