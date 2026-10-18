"""Background jobs: each step runs as its own ``python -m lexflow run`` process.

The API enqueues a row in ``jobs``; a runner thread starts queued jobs (up to
``LEXFLOW_MAX_JOBS`` at once, and never two jobs of one of the ``GROUPS`` together, e.g.
one model build at a time because builds share Ollama), streams output to
``data/jobs/<id>.log`` and records the exit status.  A job reports progress by updating
its own row, which the dashboard polls.
"""
from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta, timezone

from .. import config
from ..store import db

EXCLUSIVE = {"build", "quickstart", "models", "ask", "ontology", "coverage"}   # these share Ollama: one at a time
INDEXING = {"index", "ask"}                               # these build the same per-state search index files
GROUPS = (EXCLUSIVE, INDEXING)                            # two jobs in one group never run at once
# which runner started a job: the container's hostname unless set (process ids are only meaningful inside one
# container); LEXFLOW_RUNNER_ID keeps it across a container recreate and must be unique to each instance
RUNNER_ID = os.environ.get("LEXFLOW_RUNNER_ID", "").strip() or socket.gethostname()
BEAT = 30            # seconds between a runner's heartbeats (and its checks for orphaned jobs)
STALE = 300          # seconds without a heartbeat before a runner counts as gone


def enqueue(con, step: str, args: dict | None = None) -> int:
    cur = con.execute("INSERT INTO jobs(step, args, status, created_at, message) VALUES (?,?,?,?,?)",
                      (step, json.dumps(args or {}), "queued", db.now(), "Waiting to start"))
    con.commit()
    return cur.lastrowid


def _clash(a: str, b: str) -> bool:
    return any(a in g and b in g for g in GROUPS)


def claim(con, job_id: int) -> bool:
    """Take a queued job for this runner.  One atomic statement, so two instances on one database never both
    start it, never start it beside a running job of one of its ``GROUPS``, and never run over ``MAX_JOBS``."""
    clash = " OR ".join("(jobs.step IN ({0}) AND r.step IN ({0}))".format(",".join("?" * len(g))) for g in GROUPS)
    n = con.execute("UPDATE jobs SET status='running', runner=?, started_at=?, message='Starting' "
                    "WHERE id=? AND status='queued' AND (SELECT count(*) FROM jobs WHERE status='running') < ? "
                    f"AND NOT EXISTS (SELECT 1 FROM jobs r WHERE r.status='running' AND ({clash}))",
                    (RUNNER_ID, db.now(), job_id, config.MAX_JOBS, *(s for g in GROUPS for s in (*g, *g)))).rowcount
    con.commit()
    return n == 1


def beat(con) -> None:
    """Record that this runner is alive, for ``Runner.recover`` on the other instances."""
    con.execute("INSERT INTO meta(key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (f"runner:{RUNNER_ID}", db.now()))
    con.commit()


def log_path(job_id: int):
    return config.JOBS_DIR / f"{job_id}.log"


def tail(job_id: int, lines: int = 200) -> str:
    p = log_path(job_id)
    if not p.exists():
        return ""
    with open(p, "rb") as f:
        f.seek(0, os.SEEK_END)
        size = f.tell()
        f.seek(max(0, size - 64_000))
        text = f.read().decode("utf-8", errors="replace")
    return "\n".join(text.splitlines()[-lines:])


def _alive(pid: int | None) -> bool:
    if not pid:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def cancel(con, job_id: int) -> bool:
    row = db.one(con, "SELECT status, pid FROM jobs WHERE id=?", job_id)
    if not row or row["status"] not in ("queued", "running"):
        return False
    if row["status"] == "running" and _alive(row["pid"]):
        try:
            os.killpg(row["pid"], signal.SIGTERM) if hasattr(os, "killpg") else os.kill(row["pid"], signal.SIGTERM)
        except OSError:
            pass
    con.execute("UPDATE jobs SET status='cancelled', finished_at=?, message='Cancelled' WHERE id=?", (db.now(), job_id))
    con.commit()
    return True


class Runner(threading.Thread):
    def __init__(self, poll: float = 1.0):
        super().__init__(daemon=True, name="lexflow-jobs")
        self.poll = poll
        self.procs: dict[int, subprocess.Popen] = {}
        self.stop = threading.Event()

    def recover(self, con):
        """Fail running jobs that died with their runner, so they stop holding a slot."""
        # A job of this runner (or with none recorded) is dead when this process did not start it and its pid is
        # not alive here (with no pid yet, when it was claimed over STALE seconds ago).  Another runner's pids mean
        # nothing here, so its jobs are dead only when its heartbeat is missing or over STALE seconds old: a
        # recreated container gets a new hostname and its old one never beats again.
        cutoff = (datetime.now(timezone.utc) - timedelta(seconds=STALE)).strftime("%Y-%m-%dT%H:%M:%SZ")
        seen = {r["key"][7:]: r["value"] for r in db.rows(con, "SELECT key, value FROM meta WHERE key LIKE 'runner:%'")}
        n = 0
        for r in db.rows(con, "SELECT id, pid, runner, started_at FROM jobs WHERE status='running'"):
            if r["runner"] in (None, RUNNER_ID):
                if r["id"] in self.procs or _alive(r["pid"]) or (not r["pid"] and (r["started_at"] or "") > cutoff):
                    continue
            elif seen.get(r["runner"], "") > cutoff:
                continue
            n += con.execute("UPDATE jobs SET status='failed', finished_at=?, message='Interrupted (server restarted)' "
                             "WHERE id=? AND status='running'", (db.now(), r["id"])).rowcount
        con.execute("DELETE FROM meta WHERE key LIKE 'runner:%' AND value < ?", (cutoff,))
        if n:
            db.bump(con)
        con.commit()

    def run(self):
        config.ensure_dirs()
        con = db.connect()
        checked = 0.0
        while not self.stop.is_set():
            try:
                if time.time() - checked >= BEAT:
                    beat(con)
                    self.recover(con)
                    checked = time.time()
                self._reap(con)
                self._start(con)
            except Exception as e:  # noqa: BLE001 - keep the runner alive
                print(f"job runner: {e}", file=sys.stderr)
            time.sleep(self.poll)

    def _reap(self, con):
        for job_id, p in list(self.procs.items()):
            code = p.poll()
            if code is None:
                continue
            del self.procs[job_id]
            row = db.one(con, "SELECT status FROM jobs WHERE id=?", job_id)
            if row and row["status"] == "running":          # the job died before reporting
                if code == 0:
                    con.execute("UPDATE jobs SET status='done', progress=1, finished_at=? WHERE id=?",
                                (db.now(), job_id))
                else:
                    con.execute("UPDATE jobs SET status='failed', finished_at=?, message=? WHERE id=?",
                                (db.now(), f"Failed (exit {code}); see the log", job_id))
                db.bump(con)
                con.commit()

    def _start(self, con):
        running = db.rows(con, "SELECT id, step FROM jobs WHERE status='running'")
        if len(running) >= config.MAX_JOBS:
            return
        for job in db.rows(con, "SELECT id, step, args FROM jobs WHERE status='queued' ORDER BY id"):
            if len(running) >= config.MAX_JOBS:
                break
            # the snapshot saves a write; claim() checks again, as another runner may have started a job since
            if any(_clash(job["step"], r["step"]) for r in running) or not claim(con, job["id"]):
                continue
            cmd = [sys.executable, "-m", "lexflow", "run", job["step"], "--job", str(job["id"]),
                   "--args", job["args"] or "{}"]
            kw = {"start_new_session": True} if os.name == "posix" else {}
            try:
                with open(log_path(job["id"]), "ab") as logf:
                    p = subprocess.Popen(cmd, stdout=logf, stderr=subprocess.STDOUT, cwd=str(config.ROOT),
                                         env={**os.environ, "PYTHONUNBUFFERED": "1"}, **kw)
            except Exception as e:  # noqa: BLE001 - e.g. an argument list too long: fail the job, not the runner
                con.execute("UPDATE jobs SET status='failed', finished_at=?, message=? WHERE id=?",
                            (db.now(), f"Could not start: {e}"[:500], job["id"]))
                db.bump(con)
                con.commit()
                continue
            self.procs[job["id"]] = p
            con.execute("UPDATE jobs SET status='running', pid=?, started_at=?, message='Running' WHERE id=?",
                        (p.pid, db.now(), job["id"]))
            con.commit()
            running.append(job)


class JobContext:
    """Used inside the job process: timestamped log lines and throttled progress updates.

    It writes through the step's own connection: a second connection would wait on the
    write lock the step holds mid-transaction.  Each update commits the step's work so far,
    which is safe because every step writes idempotent upserts.
    """

    def __init__(self, job_id: int | None, con=None):
        self.job_id = job_id
        self.con = con if job_id else None
        self._last = 0.0
        self._last_progress = 0.0

    def log(self, msg: str) -> None:
        stamp = datetime.now(timezone.utc).strftime("%H:%M:%S")
        print(f"{stamp} {msg}", flush=True)
        if self.con and time.time() - self._last > 1.0:
            self.con.execute("UPDATE jobs SET message=? WHERE id=?", (msg[:300], self.job_id))
            self.con.commit()
            self._last = time.time()

    def progress(self, p: float) -> None:
        if self.con and (time.time() - self._last_progress > 0.5 or p >= 1):
            self.con.execute("UPDATE jobs SET progress=? WHERE id=?", (round(min(1.0, max(0.0, p)), 4), self.job_id))
            self.con.commit()
            self._last_progress = time.time()

    def finish(self, result: dict | None, ok: bool, message: str) -> None:
        if self.con:
            self.con.execute("UPDATE jobs SET status=?, finished_at=?, progress=CASE WHEN ? THEN 1 ELSE progress END, "
                             "message=? WHERE id=?", ("done" if ok else "failed", db.now(), ok, message[:500],
                                                      self.job_id))
            db.bump(self.con)
            self.con.commit()
