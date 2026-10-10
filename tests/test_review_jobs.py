"""Regression tests for the job runner: orphan recovery, Popen failures, and exclusive claims."""
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone

import pytest

from lexflow import config
from lexflow.pipeline import jobs
from lexflow.store import db


class FakeProc:
    def __init__(self, *_a, **_k):
        self.pid = 999_999_999

    def poll(self):
        return None


@pytest.fixture(autouse=True)
def two_slots(monkeypatch):
    monkeypatch.setattr(config, "MAX_JOBS", 2)


@pytest.fixture()
def jobs_dir(con):
    config.JOBS_DIR.mkdir(parents=True, exist_ok=True)
    return config.JOBS_DIR


def _ago(seconds):
    return (datetime.now(timezone.utc) - timedelta(seconds=seconds)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _running(con, step, runner, pid=None, started_at=None):
    jid = jobs.enqueue(con, step)
    con.execute("UPDATE jobs SET status='running', runner=?, pid=?, started_at=? WHERE id=?",
                (runner, pid, started_at or db.now(), jid))
    con.commit()
    return jid


def _status(con, jid):
    return db.scalar(con, "SELECT status FROM jobs WHERE id=?", jid)


def _heartbeat(con, runner, when):
    con.execute("INSERT INTO meta(key, value) VALUES (?, ?)", (f"runner:{runner}", when))
    con.commit()


# ---------------------------------------------------------------- orphaned jobs
def test_recover_fails_jobs_of_a_runner_that_never_beat(con):
    """The old container's hostname wrote no heartbeat: its running jobs are failed, not left blocking."""
    jid = _running(con, "ask", "old-hostname", pid=os.getpid())
    jobs.Runner().recover(con)
    row = db.one(con, "SELECT status, message, finished_at FROM jobs WHERE id=?", jid)
    assert row["status"] == "failed" and row["finished_at"] and "Interrupted" in row["message"]


def test_recover_fails_jobs_of_a_runner_with_a_stale_heartbeat(con):
    jid = _running(con, "build", "gone")
    _heartbeat(con, "gone", _ago(jobs.STALE + 60))
    jobs.Runner().recover(con)
    assert _status(con, jid) == "failed"
    assert db.scalar(con, "SELECT count(*) FROM meta WHERE key='runner:gone'") == 0


def test_recover_leaves_jobs_of_a_live_runner_alone(con):
    """Another instance that beat recently owns its jobs, even though its pids mean nothing here."""
    jid = _running(con, "ask", "other", pid=999_999_999)
    _heartbeat(con, "other", db.now())
    jobs.Runner().recover(con)
    assert _status(con, jid) == "running"


def test_recover_checks_this_runners_pids(con):
    dead = _running(con, "score", jobs.RUNNER_ID, pid=999_999_999)
    alive = _running(con, "score", jobs.RUNNER_ID, pid=os.getpid())
    legacy = _running(con, "score", None, pid=999_999_999)
    jobs.Runner().recover(con)
    assert (_status(con, dead), _status(con, alive), _status(con, legacy)) == ("failed", "running", "failed")


def test_recover_gives_a_just_claimed_job_time_to_get_its_pid(con):
    fresh = _running(con, "score", jobs.RUNNER_ID)
    old = _running(con, "score", jobs.RUNNER_ID, started_at=_ago(jobs.STALE + 60))
    jobs.Runner().recover(con)
    assert (_status(con, fresh), _status(con, old)) == ("running", "failed")


def test_recover_skips_processes_this_runner_started(con):
    jid = _running(con, "score", jobs.RUNNER_ID, pid=999_999_999)
    r = jobs.Runner()
    r.procs[jid] = FakeProc()
    r.recover(con)
    assert _status(con, jid) == "running"


def test_beat_records_this_runner(con):
    jobs.beat(con)
    jobs.beat(con)
    assert db.scalar(con, "SELECT value FROM meta WHERE key=?", f"runner:{jobs.RUNNER_ID}") >= _ago(5)


def test_the_runner_keeps_recovering_while_it_runs(con, monkeypatch):
    """An orphan that appears after startup (its old runner's heartbeat goes stale later) is still failed."""
    monkeypatch.setattr(config, "ensure_dirs", lambda: config.JOBS_DIR.mkdir(parents=True, exist_ok=True))
    monkeypatch.setattr(jobs, "BEAT", 0)
    r = jobs.Runner(poll=0.02)
    r.start()
    try:
        time.sleep(0.1)
        jid = _running(con, "ask", "old-container")
        deadline = time.time() + 10
        while _status(con, jid) == "running" and time.time() < deadline:
            time.sleep(0.05)
        assert _status(con, jid) == "failed"
        assert db.scalar(con, "SELECT count(*) FROM meta WHERE key=?", f"runner:{jobs.RUNNER_ID}") == 1
    finally:
        r.stop.set()
        r.join(5)


def test_runner_id_can_be_set_so_it_survives_a_recreate():
    env = {**os.environ, "LEXFLOW_RUNNER_ID": "lexflow-app"}
    out = subprocess.run([sys.executable, "-c", "from lexflow.pipeline import jobs; print(jobs.RUNNER_ID)"],
                         env=env, cwd=str(config.ROOT), capture_output=True, text=True, check=True).stdout
    assert out.strip() == "lexflow-app"


# ---------------------------------------------------------------- a job whose process cannot start
def test_a_job_that_cannot_start_is_failed(con, jobs_dir, monkeypatch):
    def too_long(*_a, **_k):
        raise OSError(7, "Argument list too long")
    monkeypatch.setattr(jobs.subprocess, "Popen", too_long)
    jid = jobs.enqueue(con, "ask", {"targets": ["x" * 1000] * 199})
    r = jobs.Runner()
    r._start(con)
    row = db.one(con, "SELECT status, message, finished_at FROM jobs WHERE id=?", jid)
    assert row["status"] == "failed" and "Argument list too long" in row["message"] and row["finished_at"]
    assert r.procs == {}
    monkeypatch.setattr(jobs.subprocess, "Popen", FakeProc)       # the failed job no longer blocks the queue
    nxt = jobs.enqueue(con, "build")
    r._start(con)
    assert _status(con, nxt) == "running" and nxt in r.procs


# ---------------------------------------------------------------- exclusive claims
def test_index_and_ask_never_run_together(con):
    index, ask = jobs.enqueue(con, "index"), jobs.enqueue(con, "ask")
    assert jobs.claim(con, index) is True
    assert jobs.claim(con, ask) is False
    assert jobs.claim(con, jobs.enqueue(con, "index")) is False
    assert _status(con, ask) == "queued"


def test_index_does_not_wait_for_a_model_build(con):
    assert jobs.claim(con, jobs.enqueue(con, "build")) is True
    assert jobs.claim(con, jobs.enqueue(con, "index")) is True


def test_claim_checks_exclusivity_atomically_across_connections(con):
    """Two runners on one database: the second cannot start an exclusive job beside the first's."""
    other = db.connect(config.DB_PATH)
    try:
        ask, build, score = jobs.enqueue(con, "ask"), jobs.enqueue(con, "build"), jobs.enqueue(con, "score")
        assert jobs.claim(con, ask) is True
        assert jobs.claim(other, build) is False
        assert jobs.claim(other, score) is True                   # not exclusive: still allowed
        con.execute("UPDATE jobs SET status='done' WHERE id=?", (ask,))
        con.commit()
        assert jobs.claim(other, build) is True
    finally:
        other.close()


def test_claim_respects_max_jobs(con, monkeypatch):
    monkeypatch.setattr(config, "MAX_JOBS", 1)
    first, second = jobs.enqueue(con, "score"), jobs.enqueue(con, "sync")
    assert jobs.claim(con, first) is True
    assert jobs.claim(con, second) is False


def test_start_does_not_trust_a_stale_snapshot(con, jobs_dir, monkeypatch):
    """Runner B reads no running jobs, runner A then claims an ask, and B reads the queue: B must not start
    the build beside it."""
    monkeypatch.setattr(jobs.subprocess, "Popen", FakeProc)
    ask, build = jobs.enqueue(con, "ask"), jobs.enqueue(con, "build")
    rows = db.rows

    def racing(c, sql, *args):
        if "status='queued'" in sql:                              # runner A claims the ask in between
            other = db.connect(config.DB_PATH)
            assert jobs.claim(other, ask) is True
            other.close()
        return rows(c, sql, *args)
    monkeypatch.setattr(jobs.db, "rows", racing)
    r = jobs.Runner()
    r._start(con)
    assert _status(con, build) == "queued" and r.procs == {}
