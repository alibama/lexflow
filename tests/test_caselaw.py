"""CourtListener search: queries, court ids, and searches that must not read as 'no opinions'.

The second half pins the fixes from the re-checks in docs/design/verify-credits.md: a failed search records the state
as failed (with the reason) instead of done with "0 opinions", the 429 back-off stays within ``max_wait``, Redo goes
on through the states not redone yet, and the Setup status and the rerun share one definition of done.  From the
second re-check: a Redo that fails or stops keeps a done state's record, the pacer gets only the wait left after a
back-off, there is no back-off after the last 429, a timeout (or a lost connection, or an answer that is not the
JSON expected) stops the run, and a state with nothing to search is recorded as skipped, not done.
"""
import json
from pathlib import Path

import pytest
import requests

from lexflow import config
from lexflow.municipal import caselaw
from lexflow.pipeline import steps
from lexflow.store import db

TOKEN = "test-token-not-real-0123456789"


def test_queries_follow_how_opinions_cite_the_section():
    assert caselaw.query_for("va", "2.2-3704") == '"2.2-3704"'
    assert caselaw.query_for("ak", "Alaska Stat. § 40.25.110") == '"40.25.110"'          # cited as "AS 40.25.110"
    assert caselaw.query_for("md", "General Provisions § 4-203") == '"4-203" AND "General Provisions"'
    assert caselaw.query_for("ny", "N.Y. PBO Law § 89") == '"89" AND "Public Officers Law"'
    assert caselaw.query_for("il", "5 ILCS 140/3") == '"5 ILCS 140/3"'


def test_every_state_has_court_ids():
    from lexflow.municipal import states as S
    missing = [st for st in S.NAME if st not in ("pr",) and not caselaw.courts_for(st)]
    assert missing == []
    assert caselaw.courts_for("de")[:2] == ["del", "delch"]


def test_a_rate_limit_is_not_recorded_as_no_opinions(con, monkeypatch):
    class Resp:
        status_code, headers = 429, {"Retry-After": "0"}

    monkeypatch.setattr(caselaw.requests, "get", lambda *a, **k: Resp())
    monkeypatch.setattr(caselaw.time, "sleep", lambda s: None)
    monkeypatch.setattr(caselaw, "sections_for", lambda con, st: [("records", "2.2-3704")])
    with pytest.raises(caselaw.RateLimited):
        caselaw.run(con, "va", log=lambda *_: None)
    assert con.execute("SELECT count(*) FROM case_law").fetchone()[0] == 0


# ------------------------------------------------------------------------------------------- helpers
class Clock:
    def __init__(self, t=1_000_000.0):
        self.t, self.slept = t, []

    def __call__(self):
        return self.t

    def sleep(self, s):
        self.slept.append(s)
        self.t += s


@pytest.fixture()
def clock(monkeypatch, tmp_path):
    """A fake clock behind the pacer and every back-off, so nothing really sleeps."""
    c = Clock()
    monkeypatch.setattr(caselaw, "PACER", caselaw.Pacer(path=tmp_path / "pace.json", clock=c, sleep=c.sleep))
    monkeypatch.setattr(caselaw.time, "sleep", c.sleep)
    return c


def _resp(code: int, body=None, headers=None) -> requests.Response:
    r = requests.Response()
    r.status_code = code
    r.reason = {200: "OK", 400: "Bad Request", 401: "Unauthorized", 403: "Forbidden", 429: "Too Many Requests",
                500: "Internal Server Error", 503: "Service Unavailable"}.get(code, "")
    r._content = json.dumps(body).encode() if body is not None else b"<html>not json</html>"
    r.headers.update(headers or {})
    r.url = caselaw.API
    return r


OK = {"results": [{"cluster_id": 7, "caseName": "A v. B", "citation": ["1 Va. 1"], "absolute_url": "/opinion/7/a/"}],
      "next": None}


def _states(con, *states):
    """A seed section for each state, so the cases step searches it."""
    db.upsert(con, "located_law", [{"state": st, "question": "records", "status": "found", "section": f"{st}-1",
                                    "method": "seed", "updated_at": db.now()} for st in states])
    db.upsert(con, "process_models", [{"model_id": f"{st}-records", "state": st, "question": "records",
                                       "tier": "single", "stages": "{}", "updated_at": db.now()} for st in states])
    con.commit()


def _scan(con, st):
    return db.one(con, "SELECT status, rows, matched FROM scans WHERE source='courtlistener' AND state=?", st)


FAILURES = {
    "400": lambda: _resp(400, {"detail": "bad court"}), "401": lambda: _resp(401, {"detail": "Invalid token."}),
    "403": lambda: _resp(403, {"detail": "no"}), "500": lambda: _resp(500), "503": lambda: _resp(503),
    "timeout": requests.ReadTimeout("Read timed out"), "connection": requests.ConnectionError("refused"),
    "not json": lambda: _resp(200),
    "not an object": lambda: _resp(200, ["x"]),
    "results not a list": lambda: _resp(200, {"results": "x", "next": None}),
    "result not an object": lambda: _resp(200, {"results": ["x"], "next": None}),
    "next not a link": lambda: _resp(200, {"results": [], "next": 5}),
}


def _failing(kind, searched=None):
    """A fake requests.get that answers every request with FAILURES[kind], noting each state's court filter."""
    def get(url, params=None, **kw):
        if searched is not None:
            searched.append((params or {}).get("court", url))
        f = FAILURES[kind]
        if isinstance(f, Exception):
            raise f
        return f()
    return get


# ------------------------------------------------------------------- failures are not "0 opinions"
@pytest.mark.parametrize("kind", list(FAILURES))
def test_a_failed_search_records_the_state_as_failed_and_the_next_run_tries_again(con, clock, monkeypatch, kind):
    monkeypatch.setattr(config, "COURTLISTENER_TOKEN", TOKEN)
    _states(con, "va")
    calls = []

    def get(url, **kw):
        calls.append(url)
        f = FAILURES[kind]
        if isinstance(f, Exception):
            raise f
        return f()

    monkeypatch.setattr(caselaw.requests, "get", get)
    logs = []
    out = steps.run_cases(con, {}, logs.append, lambda p: None)
    row = _scan(con, "va")
    assert row["status"].startswith("failed: ") and row["status"] != "done"
    assert "failed" in out["va"] and not any("0 opinions" in m for m in logs)
    if kind.isdigit():
        assert f"HTTP {kind}" in row["status"]
    assert TOKEN not in row["status"] and not any(TOKEN in m for m in logs)       # never the token
    st = steps.st_cases(con)
    assert st["done"] == 0 and "search failed" in st["detail"] and "VA (" in st["detail"]
    # the next run that names no states searches it again; once CourtListener answers, it is done
    calls.clear()
    monkeypatch.setattr(caselaw.requests, "get", lambda url, **kw: calls.append(url) or _resp(200, OK))
    steps.run_cases(con, {}, logs.append, lambda p: None)
    assert calls and _scan(con, "va")["status"] == "done" and steps.st_cases(con)["done"] == 1


@pytest.mark.parametrize("kind", ["500", "timeout"])
def test_a_state_that_keeps_failing_does_not_hold_back_the_others(con, clock, monkeypatch, kind):
    """A state whose search fails the same way every run goes after the never-searched states, and failing again
    does not stop the run: the fault is in that state's searches, not CourtListener as a whole."""
    _states(con, "dc", "va")
    searched = []
    fail = _failing(kind)

    def get(url, params=None, **kw):
        searched.append(params["court"])
        return fail(url, params=params) if params["court"].startswith("dc") else _resp(200, OK)

    monkeypatch.setattr(caselaw.requests, "get", get)
    steps.run_cases(con, {"states": "dc"}, lambda *_: None, lambda p: None)      # DC fails once: it stops that run
    assert _scan(con, "dc")["status"].startswith("failed:")
    searched.clear()
    out = steps.run_cases(con, {}, lambda *_: None, lambda p: None)
    assert searched[0].startswith("va")                                         # the never-searched state goes first
    assert _scan(con, "va")["status"] == "done" and "stopped" not in out
    searched.clear()
    con.execute("DELETE FROM scans WHERE state='va'")
    con.commit()
    steps.run_cases(con, {"states": "dc,va"}, lambda *_: None, lambda p: None)
    assert _scan(con, "va")["status"] == "done"                                 # DC failing again did not stop VA


def test_errors_every_state_would_share_stop_the_run_and_others_go_on(con, clock, monkeypatch):
    _states(con, "dc", "va")
    for code, stops in ((401, True), (403, True), (500, True), (400, False), (404, False)):
        con.execute("DELETE FROM scans")
        con.commit()
        searched = []

        def get(url, params=None, **kw):
            searched.append(params["court"])
            return _resp(code, {"detail": "x"})

        monkeypatch.setattr(caselaw.requests, "get", get)
        out = steps.run_cases(con, {}, lambda *_: None, lambda p: None)
        assert _scan(con, "dc")["status"].startswith(f"failed: § dc-1: HTTP {code}")
        if stops:
            assert len(searched) == 1 and _scan(con, "va") is None and "stopped" in out, code
        else:
            assert len(searched) == 2 and _scan(con, "va")["status"].startswith("failed:"), code


@pytest.mark.parametrize("kind", ["timeout", "connection", "not json", "not an object", "results not a list",
                                  "500"])
def test_a_timeout_or_a_bad_answer_stops_the_run(con, clock, monkeypatch, kind):
    """A timeout, a lost connection or an answer that is not the JSON expected would most likely be the same for
    every other state, so the run stops at the first state instead of spending a request on each of the others."""
    _states(con, "dc", "va")
    searched = []
    monkeypatch.setattr(caselaw.requests, "get", _failing(kind, searched))
    out = steps.run_cases(con, {}, lambda *_: None, lambda p: None)
    assert len(searched) == 1 and searched[0].startswith("dc")
    assert _scan(con, "dc")["status"].startswith("failed: § dc-1: ")
    assert _scan(con, "va") is None and "stopped" in out


def test_ask_still_gets_what_was_found_and_the_step_gets_an_error(con, clock, monkeypatch):
    monkeypatch.setattr(caselaw.requests, "get", lambda *a, **k: _resp(500))
    logs = []
    assert caselaw.search("va", "2.2-3704", pages=1, log=logs.append) == []          # Ask: logged, nothing raised
    assert any("CourtListener search failed: HTTP 500" in m for m in logs)
    with pytest.raises(caselaw.SearchFailed) as e:
        caselaw.search("va", "2.2-3704", log=logs.append, strict=True)
    assert e.value.stops_run and "HTTP 500" in e.value.reason


def test_a_failure_part_way_keeps_the_opinions_already_found(con, clock, monkeypatch):
    monkeypatch.setattr(caselaw, "sections_for", lambda con, st: [("records", "1-1"), ("records", "1-2")])
    answers = iter([_resp(200, OK), _resp(503)])
    monkeypatch.setattr(caselaw.requests, "get", lambda *a, **k: next(answers))
    with pytest.raises(caselaw.SearchFailed) as e:
        caselaw.run(con, "va", log=lambda *_: None)
    assert e.value.sections_done == 1 and e.value.opinions == 1
    assert db.scalar(con, "SELECT count(*) FROM case_law") == 1


# ------------------------------------------------------------------------------- 429 and max_wait
def test_the_429_back_off_stays_within_max_wait(clock, monkeypatch):
    calls = []
    monkeypatch.setattr(caselaw.requests, "get",
                        lambda *a, **k: calls.append(1) or _resp(429, headers={"Retry-After": "300"}))
    start = clock.t
    with pytest.raises(caselaw.RateLimited, match="429"):
        caselaw.search("va", "2.2-3704", pages=1, log=lambda *_: None)                  # Ask's default: a minute
    assert len(calls) == 1 and clock.t - start <= caselaw.SEARCH_MAX_WAIT                # no 300 s sleep
    # the re-check's case: 429 after 429 with Retry-After 300, now with the step's hour
    calls.clear()
    start = clock.t
    with pytest.raises(caselaw.RateLimited):
        caselaw.search("va", "2.2-3704", log=lambda *_: None, max_wait=caselaw.STEP_MAX_WAIT)
    assert clock.t - start <= caselaw.STEP_MAX_WAIT and len(calls) == caselaw.ATTEMPTS


def test_a_429_without_retry_after_backs_off_within_max_wait(clock, monkeypatch):
    answers = iter([_resp(429), _resp(429), _resp(200, OK)])
    monkeypatch.setattr(caselaw.requests, "get", lambda *a, **k: next(answers))
    start = clock.t
    with pytest.raises(caselaw.RateLimited):                       # 30 s, then 60 s: past the minute
        caselaw.search("va", "2.2-3704", pages=1, log=lambda *_: None)
    assert clock.t - start <= caselaw.SEARCH_MAX_WAIT
    answers = iter([_resp(429), _resp(429), _resp(200, OK)])
    found = caselaw.search("va", "2.2-3704", pages=1, log=lambda *_: None, max_wait=caselaw.STEP_MAX_WAIT)
    assert [x["cluster_id"] for x in found] == [7]


def test_after_a_back_off_the_pacer_gets_only_the_wait_left(clock, monkeypatch, tmp_path):
    # one request a minute: after a 40 s back-off the next request would wait 22 s more (60 s + margin - 40 s),
    # which fits a fresh minute but not the 20 s this search has left
    monkeypatch.setattr(caselaw, "PACER", caselaw.Pacer(limits=((60.0, 1, "one request a minute"),),
                                                        path=tmp_path / "one-a-minute.json", clock=clock,
                                                        sleep=clock.sleep))
    answers, calls = iter([_resp(429, headers={"Retry-After": "40"}), _resp(200, OK)]), []
    monkeypatch.setattr(caselaw.requests, "get", lambda *a, **k: calls.append(1) or next(answers))
    start = clock.t
    with pytest.raises(caselaw.RateLimited, match="one request a minute would mean waiting 22 s, longer than 20 s"):
        caselaw.search("va", "2.2-3704", pages=1, log=lambda *_: None)
    assert len(calls) == 1 and clock.t - start == pytest.approx(40.0)          # the back-off, and nothing more


def test_there_is_no_back_off_after_the_last_429(clock, monkeypatch):
    calls, logs = [], []
    monkeypatch.setattr(caselaw.requests, "get",
                        lambda *a, **k: calls.append(1) or _resp(429, headers={"Retry-After": "10"}))
    with pytest.raises(caselaw.RateLimited, match="kept answering 429"):
        caselaw.search("va", "2.2-3704", pages=1, log=logs.append, max_wait=caselaw.STEP_MAX_WAIT)
    assert len(calls) == caselaw.ATTEMPTS
    assert clock.slept == [10.0] * (caselaw.ATTEMPTS - 1)                 # one back-off between tries, none after
    assert sum("waiting 10 s" in m for m in logs) == caselaw.ATTEMPTS - 1


def test_the_docstring_says_what_a_search_waits():
    doc = " ".join(caselaw.__doc__.split())
    assert "a minute at most, besides the time the requests themselves take" in doc
    assert "pacer's and the back-off after a 429 answer together" in doc
    assert "never read as \"no opinions\"" in doc
    # 429s are not only other clients': a run with no token and no other lexflow request got one
    assert "backstop for other clients" not in doc
    assert "can still answer 429 when the pacer's count is within the limits" in doc
    assert "with no wait after the last" in doc
    assert "there is no limit on the whole answer" in doc                # the timeout is not a cap on a request
    assert "is recorded with that reason rather than as done" in doc
    source = " ".join(Path(caselaw.__file__).read_text(encoding="utf-8").split())
    assert "a wrong id is a 400, logged" not in source
    assert "An error answer to a search records the state as failed" in source


# ------------------------------------------------------------------- one definition of done, and Redo
def _fake_run(searched, budget):
    """caselaw.run for a fake day: each state costs one request of ``budget``; then the day's limit stops it."""
    def run(con, st, log=None, progress=None):
        if budget[0] <= 0:
            e = caselaw.RateLimited(f"{st} x: staying within CourtListener's 125 requests a day would mean waiting 20 h")
            e.sections_done = 0
            raise e
        budget[0] -= 1
        searched.append(st)
        return {"sections": 1, "opinions": 0}
    return run


@pytest.fixture()
def ticking(monkeypatch):
    """db.now() a second later each call, so every record has its own time."""
    t = [0]

    def now():
        t[0] += 1
        return f"2026-10-{10 + t[0] // 86400:02d}T{t[0] // 3600 % 24:02d}:{t[0] // 60 % 60:02d}:{t[0] % 60:02d}Z"
    monkeypatch.setattr(db, "now", now)


def test_redo_goes_on_through_the_states_not_redone_yet(con, monkeypatch, ticking):
    states = ["ak", "al", "az", "ca", "co", "ct", "dc", "de", "fl", "ga", "hi", "ia", "id", "il", "in"]
    _states(con, *states)
    searched = []
    for day in range(3):                                         # three days at five states a day cover all 15
        monkeypatch.setattr(caselaw, "run", _fake_run(searched, [5]))
        steps.run_cases(con, {}, lambda *_: None, lambda p: None)
    assert sorted(searched) == states and len(searched) == 15
    assert steps.st_cases(con)["done"] == 15
    redone = []
    for day, args in enumerate([{"force": True}, {"force": True, "states": "all"}, {"force": True}]):
        today = []
        monkeypatch.setattr(caselaw, "run", _fake_run(today, [5]))
        steps.run_cases(con, args, lambda *_: None, lambda p: None)
        assert today == searched[5 * day:5 * day + 5]           # the oldest five, not the first five again
        redone += today
    assert sorted(redone) == states                              # three Redo days refreshed every state
    assert steps.st_cases(con)["done"] == 15                     # a Redo stopped by the limit leaves done as done


def test_a_state_stopped_part_way_is_not_done_and_comes_first(con, monkeypatch, ticking):
    _states(con, "ak", "al")
    searched = []

    def run(con, st, log=None, progress=None):
        searched.append(st)
        if st == "al":                                            # one opinion stored, then the day's limit
            con.execute("INSERT INTO case_law (state, section, cluster_id, source, updated_at) "
                        "VALUES ('al', 'al-1', '1', 'courtlistener', ?)", (db.now(),))
            e = caselaw.RateLimited("al al-2: staying within CourtListener's 125 requests a day would mean waiting 20 h")
            e.sections_done, e.opinions = 1, 1
            raise e
        return {"sections": 1, "opinions": 0}

    monkeypatch.setattr(caselaw, "run", run)
    steps.run_cases(con, {}, lambda *_: None, lambda p: None)
    assert searched == ["ak", "al"]
    assert _scan(con, "al")["status"].startswith("stopped: ") and _scan(con, "al")["rows"] == 1
    st = steps.st_cases(con)
    assert st["done"] == 1 and "stopped by a rate limit, searched first next time: AL" in st["detail"]
    _states(con, "aa")                                            # a new state that sorts before it
    searched.clear()
    monkeypatch.setattr(caselaw, "run", _fake_run(searched, [5]))
    steps.run_cases(con, {}, lambda *_: None, lambda p: None)
    assert searched == ["al", "aa"]                               # the stopped state first
    assert steps.st_cases(con)["done"] == 3


def test_opinions_with_no_search_record_are_not_done_and_wait_for_the_new_states(con, monkeypatch, ticking):
    # the live store had opinions for CA, DC and MD from before searches were recorded, and none for most states
    _states(con, "ak", "ca", "dc", "md", "va", "wy")
    for st, at in (("ca", "2026-10-10T04:33:51Z"), ("dc", "2026-10-10T02:01:55Z"), ("md", "2026-10-10T02:07:06Z")):
        con.execute("INSERT INTO case_law (state, section, cluster_id, source, updated_at) "
                    "VALUES (?, ?, '1', 'courtlistener', ?)", (st, f"{st}-1", at))
    steps._mark_scan(con, "courtlistener", "va", rows=1, matched=0)
    st = steps.st_cases(con)
    assert (st["done"], st["total"]) == (1, 6) and st["status"] == "partial"
    assert "no finished search recorded: CA, DC, MD" in st["detail"]
    searched = []
    monkeypatch.setattr(caselaw, "run", _fake_run(searched, [10]))
    logs = []
    steps.run_cases(con, {}, logs.append, lambda p: None)
    assert searched == ["ak", "wy", "dc", "md", "ca"]             # new states first, then the oldest stored ones
    assert any("skipping 1 state already searched to the end" in m for m in logs)
    assert steps.st_cases(con)["done"] == 6


def test_the_status_and_the_rerun_use_the_same_states(con, monkeypatch):
    # a state with only a seed section (no model in a usable tier) is searched, so it is counted
    _states(con, "va")
    db.upsert(con, "located_law", [{"state": "ar", "question": "records", "status": "found", "section": "ar-1",
                                    "method": "seed", "updated_at": db.now()}])
    con.commit()
    assert steps._cases_targets(con) == {"ar", "va"} and steps.st_cases(con)["total"] == 2


@pytest.mark.parametrize("answer", ["500", "timeout", "429"])
def test_a_redo_that_fails_or_stops_keeps_a_done_state_record(con, clock, monkeypatch, ticking, answer):
    _states(con, "va")
    monkeypatch.setattr(caselaw.requests, "get", lambda url, **kw: _resp(200, OK))
    steps.run_cases(con, {}, lambda *_: None, lambda p: None)
    query = "SELECT status, rows, matched, scanned_at FROM scans WHERE source='courtlistener' AND state='va'"
    before = db.one(con, query)
    assert before["status"] == "done"
    if answer == "429":                                           # a back-off longer than the step's hour: stopped
        monkeypatch.setattr(caselaw.requests, "get",
                            lambda url, **kw: _resp(429, headers={"Retry-After": "99999"}))
    else:
        monkeypatch.setattr(caselaw.requests, "get", _failing(answer))
    logs = []
    out = steps.run_cases(con, {"force": True}, logs.append, lambda p: None)
    assert "stopped" in out
    assert db.one(con, query) == before                           # status, counts and date all unchanged
    assert steps.st_cases(con)["done"] == 1
    if answer != "429":
        assert any("its earlier complete search stays on record" in m for m in logs)


# ------------------------------------------------------------------------ nothing to search: skipped
def test_a_state_with_nothing_to_search_is_skipped_not_done(con, clock, monkeypatch):
    """PR has a seed section but no court ids; CO has a model but no section.  Neither is searched, neither is
    recorded or counted as done, neither stops the run, and each is looked at again on the next run."""
    _states(con, "pr", "va")
    db.upsert(con, "process_models", [{"model_id": "co-records", "state": "co", "question": "records",
                                       "tier": "single", "stages": "{}", "updated_at": db.now()}])
    con.commit()
    searched, logs = [], []
    monkeypatch.setattr(caselaw.requests, "get",
                        lambda url, params=None, **kw: searched.append(params["court"]) or _resp(200, OK))
    out = steps.run_cases(con, {}, logs.append, lambda p: None)
    assert searched == ["va vactapp"] and "stopped" not in out                # no request for CO or PR
    assert _scan(con, "pr")["status"] == "skipped: " + caselaw.NO_COURTS
    assert _scan(con, "co")["status"] == "skipped: " + caselaw.NO_SECTIONS
    assert _scan(con, "va")["status"] == "done"
    assert not any("0 opinions" in m for m in logs)
    st = steps.st_cases(con)
    assert (st["done"], st["total"]) == (1, 3) and st["status"] == "partial"
    assert "1 of 3 states searched to the end" in st["detail"]
    assert f"PR ({caselaw.NO_COURTS})" in st["detail"] and "not searched" in st["detail"]
    assert f"CO ({caselaw.NO_SECTIONS})" in st["detail"]
    # the next run looks at both again; once CO has a section, it is searched and done
    db.upsert(con, "located_law", [{"state": "co", "question": "records", "status": "found", "section": "co-1",
                                    "method": "seed", "updated_at": db.now()}])
    con.commit()
    searched.clear()
    steps.run_cases(con, {}, lambda *_: None, lambda p: None)
    assert searched == ["colo coloctapp"]
    assert _scan(con, "co")["status"] == "done" and _scan(con, "pr")["status"].startswith("skipped: ")
    assert steps.st_cases(con)["done"] == 2


def test_a_state_with_no_court_ids_is_never_searched_across_every_court(con, clock, monkeypatch):
    calls = []
    monkeypatch.setattr(caselaw.requests, "get", lambda *a, **k: calls.append(1) or _resp(200, OK))
    assert caselaw.courts_for("pr") == []
    assert caselaw.search("pr", "3 L.P.R.A. § 1", log=lambda *_: None) == []          # Ask: nothing, no request
    with pytest.raises(caselaw.Skipped) as e:
        caselaw.search("pr", "3 L.P.R.A. § 1", log=lambda *_: None, strict=True)
    assert calls == [] and not e.value.stops_run and e.value.reason.startswith("skipped: ")
    assert isinstance(e.value, caselaw.SearchFailed)                                 # the cases step catches it
    assert len(e.value.reason) <= 80                                                 # the Setup status shows 80


def test_the_token_never_follows_a_next_page_to_another_host(con, clock, monkeypatch):
    monkeypatch.setattr(config, "COURTLISTENER_TOKEN", TOKEN)
    calls = []

    def get(url, params=None, headers=None, **kw):
        calls.append((url, (headers or {}).get("Authorization")))
        return _resp(200, {**OK, "next": "https://elsewhere.example.org/api/rest/v4/search/?cursor=x"})

    monkeypatch.setattr(caselaw.requests, "get", get)
    caselaw.search("va", "2.2-3704", pages=3, log=lambda *_: None)
    assert len(calls) == 1 and calls[0][0] == caselaw.API                      # the other host is never asked
