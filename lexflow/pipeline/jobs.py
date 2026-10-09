"""Background jobs: each step runs as its own ``python -m lexflow run`` process.

The API enqueues a row in ``jobs``; a runner thread starts queued jobs (up to
``LEXFLOW_MAX_JOBS`` at once, and only one model build at a time because builds share
Ollama), streams output to ``data/jobs/<id>.log`` and records the exit status.  A job
reports progress by updating its own row, which the dashboard polls.
"""
from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone

from .. import config
from ..store import db

EXCLUSIVE = {"build", "quickstart", "models"}


def enqueue(con, step: str, args: dict | None = None) -> int:
    cur = con.execute("INSERT INTO jobs(step, args, status, created_at, message) VALUES (?,?,?,?,?)",
                      (step, json.dumps(args or {}), "queued", db.now(), "Waiting to start"))
    con.commit()
    return cur.lastrowid


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
        for r in db.rows(con, "SELECT id, pid FROM jobs WHERE status='running'"):
            if not _alive(r["pid"]):
                con.execute("UPDATE jobs SET status='failed', finished_at=?, message='Interrupted (server restarted)' "
                            "WHERE id=?", (db.now(), r["id"]))
        con.commit()

    def run(self):
        config.ensure_dirs()
        con = db.connect()
        self.recover(con)
        while not self.stop.is_set():
            try:
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
        busy_exclusive = any(r["step"] in EXCLUSIVE for r in running)
        for job in db.rows(con, "SELECT id, step, args FROM jobs WHERE status='queued' ORDER BY id"):
            if len(running) >= config.MAX_JOBS:
                break
            if job["step"] in EXCLUSIVE and busy_exclusive:
                continue
            logf = open(log_path(job["id"]), "ab")
            cmd = [sys.executable, "-m", "lexflow", "run", job["step"], "--job", str(job["id"]),
                   "--args", job["args"] or "{}"]
            kw = {"start_new_session": True} if os.name == "posix" else {}
            p = subprocess.Popen(cmd, stdout=logf, stderr=subprocess.STDOUT, cwd=str(config.ROOT),
                                 env={**os.environ, "PYTHONUNBUFFERED": "1"}, **kw)
            logf.close()
            self.procs[job["id"]] = p
            con.execute("UPDATE jobs SET status='running', pid=?, started_at=?, message='Running' WHERE id=?",
                        (p.pid, db.now(), job["id"]))
            con.commit()
            running.append(job)
            busy_exclusive = busy_exclusive or job["step"] in EXCLUSIVE


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
