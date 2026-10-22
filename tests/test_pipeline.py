"""The Pipeline page (lexflow/pipeline/flow.py, GET /api/pipeline) and the dry run a real write follows
(lexflow/pipeline/steps.py): the payload's places and transitions on a seeded store, the wikibase step's dry-run
record, its refusals, ``skip_held``, the chained lint -> pass 1 -> pass 2, and the same pattern for the publish
step.  No network: the graph, the lint and the pusher are fakes (and one test runs the real pusher against a fake
API), and the live Wikibase count is a fake."""
import json
import os
import time
from datetime import datetime, timedelta, timezone

import pytest

from lexflow import config
from lexflow.pipeline import flow, steps
from lexflow.publish import graph, lint, push
from lexflow.store import db

HELD = "lexflow:step:va.records:held"


def _item(key, label):
    return graph.Item(key=key, label=label, description="a step of the records process", aliases=[], cls=None,
                      claims=[], exists=False)


def _items():
    return [_item("lexflow:process:va.records", "Requesting public records in Virginia"),
            _item("lexflow:step:va.records:ask", "Ask the custodian"),
            _item(HELD, "Held step")]


@pytest.fixture(autouse=True)
def fresh(monkeypatch):
    monkeypatch.delenv("LEXFLOW_WIKIBASE_OUT", raising=False)
    monkeypatch.delenv("LEXFLOW_JOB_ID", raising=False)
    flow.clear()
    yield
    flow.clear()


@pytest.fixture()
def wb(con, monkeypatch):
    """A fake graph (``box['items']``) and a fake lint that holds ``box['held']``; a bot password is set (the fake
    API never sends it)."""
    box = {"items": _items(), "held": [], "lints": 0}
    monkeypatch.setattr(graph, "build", lambda con, **kw: list(box["items"]))
    monkeypatch.setattr(config, "WIKIBASE_BOT_USER", "bot")
    monkeypatch.setattr(config, "WIKIBASE_BOT_PASSWORD", "not-a-real-password")

    def fake_lint(con, *, out_dir, items, **kw):
        box["lints"] += 1
        report = {"generated": db.now(), "items": len(items), "held_count": len(box["held"]),
                  "held": [{"key": k} for k in box["held"]]}
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / push.LINT_NAME).write_text(json.dumps(report), encoding="utf-8")
        return report
    monkeypatch.setattr(lint, "run", fake_lint)
    return box


@pytest.fixture()
def pushed(monkeypatch):
    """push.run recorded: each call writes one edit per item it may write through the api it is given."""
    calls = []

    def fake_run(con, **kw):
        held = push.held_keys(push.read_lint(kw["out_dir"] / push.LINT_NAME))
        n = len([it for it in kw["items"] if it.key not in held])
        calls.append(dict(kw, held=held))
        if not kw["dry_run"]:
            for _ in range(n):
                kw["api"].edit({}, new="item")
        return {"dry_run": kw["dry_run"], "pass": kw.get("pass_no", "all"), "items": len(kw["items"]),
                "plan": str(kw["out_dir"] / push.PLAN_NAME), "api_writes": 0 if kw["dry_run"] else n, "seconds": 0.1,
                "summary": {"creates": n, "updates": n, "held_skipped": sorted(held), "dropped_snaks": 1,
                            "failures_by_code": {}, "properties_to_create": [],
                            "counts": {"1": {"step": {"create": n}}, "2": {"step": {"clear": n}}}}}
    monkeypatch.setattr(push, "run", fake_run)
    return calls


class FakeApi:
    """What the step hands the pusher for a real pass: records each write."""

    def __init__(self, on_write=None):
        self.on_write, self.edits, self.writes = on_write, [], 0
        self.user, self.password = "bot", "pw"
        self.session = FakeSession()

    def login(self):
        return "bot"

    def edit(self, body, **kw):
        self.edits.append({"body": body, **kw})
        self.writes += 1
        if self.on_write:
            self.on_write()
        return {"entity": {"id": f"Q{900 + len(self.edits)}"}}


class FakeSession:
    headers: dict = {}

    def get(self, url, params=None, **kw):
        class R:
            def raise_for_status(self):
                return None

            def json(self):
                return {"entities": {}}
        return R()


@pytest.fixture()
def apis(monkeypatch):
    made = []

    def factory(on_write=None):
        made.append(FakeApi(on_write))
        return made[-1]
    monkeypatch.setattr(steps, "wikibase_api", factory)
    return made


def _step(con, args):
    logs, prog = [], []
    out = steps.run_wikibase(con, args, logs.append, prog.append)
    return out, logs, prog


def _out():
    return config.DATA_DIR / "wikibase-push"


def _record():
    return steps.read_record(_out() / steps.DRY_RUN_NAME)


def _age(rec, hours):
    rec = dict(rec, generated=(datetime.now(timezone.utc) - timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ"))
    steps.write_record(_out() / steps.DRY_RUN_NAME, rec)


def _reals(calls):
    return [c for c in calls if not c["dry_run"]]


# ------------------------------------------------------------------------------------------- the wikibase step
def test_a_dry_run_lints_plans_and_records_its_numbers(con, wb, pushed, apis):
    out, logs, _ = _step(con, {"passes": "1,2"})
    assert wb["lints"] == 1 and len(pushed) == 1 and pushed[0]["dry_run"] is True and apis == []
    assert pushed[0]["items"] == wb["items"] and pushed[0]["out_dir"] == _out()        # data/wikibase-push by default
    rec = _record()
    assert rec["id"] == out["dry_run_id"] and rec["graph_hash"] == steps.graph_hash(wb["items"])
    assert rec["scope"] == {"states": None, "drafts": False, "full": False} and rec["ids_mark"] == steps.ids_mark(con)
    assert (rec["creates"], rec["updates"], rec["pass1_writes"], rec["pass2_writes"]) == (3, 3, 3, 3)
    assert rec["held_count"] == 0 and rec["linted"] is True and "used" not in rec
    assert any(m.startswith("== lint") for m in logs) and any(m.startswith(f"dry run {rec['id']}") for m in logs)


def test_a_real_push_is_refused_without_a_recent_dry_run_of_the_same_graph(con, wb, pushed, apis):
    really = {"really": True, "passes": "1,2"}
    out, logs, _ = _step(con, really)
    assert out["refused"].startswith("no dry run of the push has been recorded") and out["api_writes"] == 0
    assert logs[0].startswith("push refused: nothing was written to") and pushed == [] and apis == []
    _step(con, {"passes": "1,2"})
    rec = _record()
    _age(rec, 25)
    why = _step(con, really)[0]["refused"]
    assert why.startswith("the last dry run") and "older than 24 hours" in why
    _age(rec, 1)
    # another scope than the dry run's
    assert "the dry run planned every state, not states va" in _step(con, dict(really, states="va"))[0]["refused"]
    assert "not every state, with drafts" in _step(con, dict(really, drafts=True))[0]["refused"]
    # the dry run the operator confirmed is not the latest one
    assert "is not the latest one" in _step(con, dict(really, dry_run_id="2026-01-01T00:00:00Z-abc"))[0]["refused"]
    # the graph changed since
    wb["items"] = _items()[:2]
    assert _step(con, really)[0]["refused"] == "the graph changed since the dry run: run a dry run again"
    wb["items"] = _items()
    # a push ran since (the Wikibase record changed)
    con.execute("INSERT INTO wikibase_items(key, qid, label, updated_at) VALUES ('lexflow:x', 'Q1', 'x', ?)",
                (db.now(),))
    con.commit()
    assert "the Wikibase record changed since the dry run" in _step(con, really)[0]["refused"]
    assert _reals(pushed) == [] and apis == []


def test_skip_held_lets_the_push_go_on_and_held_items_are_never_written(con, wb, pushed, apis):
    wb["held"] = [HELD]
    _step(con, {"passes": "1,2"})
    out, logs, _ = _step(con, {"really": True, "passes": "1,2", "skip_held": False})
    assert out["refused"].startswith("the lint report holds 1 items") and _reals(pushed) == []
    out, logs, _ = _step(con, {"really": True, "passes": "1,2"})                    # skip_held is on by default
    real = _reals(pushed)
    assert [c["pass_no"] for c in real] == ["1", "2"] and all(c["allow_held"] is True for c in real)
    assert all(c["held"] == {HELD} for c in real) and out["really"] is True and out["dry_run"] is False
    assert [len(a.edits) for a in apis] == [2, 2]                                  # 3 items, 1 held: 2 writes a pass
    assert any("1 held items are skipped and never written" in m for m in logs)
    # the lint now holds something else than the dry run planned with: refused
    _step(con, {"passes": "1,2"})
    wb["held"] = [HELD, "lexflow:step:va.records:ask"]
    assert "the lint report now holds 2 items and the dry run planned with 1" in _step(
        con, {"really": True, "passes": "1,2"})[0]["refused"]


def test_the_chained_push_lints_then_runs_pass_1_then_pass_2_with_progress(con, wb, pushed, apis):
    _step(con, {"passes": "1,2"})
    rid = _record()["id"]
    lints = wb["lints"]
    out, logs, prog = _step(con, {"really": True, "passes": "1,2", "dry_run_id": rid})
    assert wb["lints"] == lints + 1
    heads = [m for m in logs if m.startswith("== ")]
    assert heads[0].startswith("== lint") and heads[1].startswith("== pass 1") and heads[2].startswith("== pass 2")
    assert [c["pass_no"] for c in _reals(pushed)] == ["1", "2"] and len(apis) == 2
    assert prog == sorted(prog) and prog[-1] == 1.0
    # after the lint (0.15), pass 1's writes move the bar to 0.575 (3 of the 6 planned writes), pass 2's to the end
    assert 0.575 in [round(x, 3) for x in prog]
    assert any(0.15 < x < 0.575 for x in prog) and any(0.575 < x < 1.0 for x in prog)
    assert set(out["passes"]) == {"1", "2"} and out["api_writes"] == 6 and out["dry_run_id"] == rid
    assert _record()["used"]["at"]
    # one dry run, one push
    again = _step(con, {"really": True, "passes": "1,2"})[0]
    assert "was used by the real job" in again["refused"] and len(_reals(pushed)) == 2


def test_a_push_without_the_bot_password_is_refused_before_the_dry_run_is_used(con, wb, pushed, apis, monkeypatch):
    _step(con, {"passes": "1,2"})
    monkeypatch.setattr(config, "WIKIBASE_BOT_PASSWORD", "")
    out = _step(con, {"really": True, "passes": "1,2"})[0]
    assert out["refused"].startswith("WIKIBASE_BOT_USER and WIKIBASE_BOT_PASSWORD") and "used" not in _record()
    assert _reals(pushed) == [] and apis == []


def test_passes_are_checked(con, wb, pushed):
    for bad in ("3", "2,1", "1,1", "x"):
        with pytest.raises(ValueError):
            steps.parse_passes(bad)
    assert steps.parse_passes("all") == ["1", "2"] and steps.parse_passes([1, 2]) == ["1", "2"]
    assert steps.parse_passes(None) is None and steps.parse_passes("2") == ["2"]


def test_the_real_pusher_never_writes_a_held_item(con, wb, apis, monkeypatch):
    """The step with the real push.run against a fake API: pass 1 creates the items the lint does not hold, pass 2
    writes their statements, and the held item is never sent."""
    monkeypatch.setattr(push.I, "throttle", lambda: None)
    monkeypatch.setattr(push.Resolver, "load_live", lambda self, session, log=print: None)
    monkeypatch.setattr(push.Pusher, "fetch_live", lambda self, qids: None)          # no reads of the live wiki
    wb["held"] = [HELD]
    _step(con, {"passes": "1,2"})
    out, logs, _ = _step(con, {"really": True, "passes": "1,2"})
    assert out.get("refused") is None, out
    sent = [e.get("summary", "") for a in apis for e in a.edits]
    assert any("lexflow:process:va.records" in s for s in sent) and not any(HELD in s for s in sent)
    assert db.scalar(con, "SELECT count(*) FROM wikibase_items WHERE key=?", HELD) == 0
    assert db.scalar(con, "SELECT count(*) FROM wikibase_items WHERE key='lexflow:step:va.records:ask'") == 1
    assert not any(e.get("action") == "delete" or "wbdelete" in json.dumps(e) for a in apis for e in a.edits)


# ---------------------------------------------------------------------------------------- the publish step
@pytest.fixture()
def wiki(con, monkeypatch):
    from lexflow.publish import dokuwiki as D
    from lexflow.publish import lexipedia as LX
    box = {"pages": {"lexflow:start": "start page", "lexflow:va:records": "records page"}, "saved": [],
           "current": {"lexflow:start": "start page"}}
    monkeypatch.setattr(LX, "all_pages", lambda con: dict(box["pages"]))
    monkeypatch.setattr(config, "CORRECTIONS", "fixes@lexipedia.xyz")
    monkeypatch.setattr(config, "DOKUWIKI_URL", "http://example.invalid")
    monkeypatch.setattr(config, "DOKUWIKI_TOKEN", "x")

    class Wiki(D.DokuWiki):
        def whoami(self):
            return {"login": "bot"}

        def get_page(self, page):
            return box["current"].get(page, "")

        def call(self, method, **params):
            if not self.dry_run:
                box["saved"].append(params.get("page"))
            return True
    monkeypatch.setattr(D, "DokuWiki", Wiki)
    return box


def _publish(con, args):
    logs = []
    return steps.run_publish(con, args, logs.append, lambda p: None), logs


def test_a_real_publish_follows_a_recent_dry_run_of_the_same_pages(con, wiki):
    out, logs = _publish(con, {})
    assert out["refused"] and out["reason"].startswith("no dry run of the publish") and wiki["saved"] == []
    out, logs = _publish(con, {"dry_run": True})
    rec = steps.read_record(steps.publish_dir() / steps.DRY_RUN_NAME)
    assert out["dry_run_id"] == rec["id"] and (rec["pages"], rec["would_write"], rec["unchanged"]) == (2, 1, 1)
    assert rec["compared"] is True and wiki["saved"] == [] and rec["corrections"] == "fixes@lexipedia.xyz"
    # the pages changed since the dry run
    wiki["pages"]["lexflow:va:records"] = "records page, rebuilt"
    out, _ = _publish(con, {})
    assert out["reason"] == "the pages changed since the dry run: run a dry run again" and wiki["saved"] == []
    _publish(con, {"dry_run": True})
    rid = steps.read_record(steps.publish_dir() / steps.DRY_RUN_NAME)["id"]
    out, logs = _publish(con, {"dry_run_id": rid})
    assert out["refused"] == [] and wiki["saved"] == ["lexflow:va:records"] and out["unchanged"] == ["lexflow:start"]
    again, _ = _publish(con, {})
    assert "was used by the real job" in again["reason"] and wiki["saved"] == ["lexflow:va:records"]


def test_the_corrections_guard_still_comes_first(con, wiki, monkeypatch):
    _publish(con, {"dry_run": True})
    monkeypatch.setattr(config, "CORRECTIONS", "")
    out, logs = _publish(con, {})
    assert out["reason"].startswith("LEXFLOW_CORRECTIONS is") and len(logs) == 1 and wiki["saved"] == []


# ----------------------------------------------------------------------------------------------- the API
@pytest.fixture()
def client(con):
    from fastapi.testclient import TestClient
    from lexflow.api.app import app
    return TestClient(app)


def test_the_api_queues_a_real_job_only_with_the_confirmed_dry_run(con, client, wb, pushed):
    r = client.post("/api/jobs", json={"step": "wikibase", "args": {"really": True, "passes": "1,2"}})
    assert r.status_code == 409 and "Pipeline page" in r.json()["detail"]
    assert client.post("/api/jobs", json={"step": "wikibase", "args": {"passes": "3"}}).status_code == 400
    assert client.post("/api/jobs", json={"step": "wikibase", "args": {"passes": "1,2"}}).status_code == 200
    _step(con, {"passes": "1,2"})
    rid = _record()["id"]
    args = {"really": True, "passes": "1,2", "skip_held": True, "dry_run_id": rid}
    r = client.post("/api/jobs", json={"step": "wikibase", "args": dict(args, dry_run_id="old")})
    assert r.status_code == 409 and "not the latest one" in r.json()["detail"]
    r = client.post("/api/jobs", json={"step": "wikibase", "args": dict(args, states="va")})
    assert r.status_code == 409 and "the dry run planned every state" in r.json()["detail"]
    # the dry run queued above is still waiting: no real push beside another job of the step
    r = client.post("/api/jobs", json={"step": "wikibase", "args": args})
    assert r.status_code == 409 and "already queued or running" in r.json()["detail"]
    con.execute("UPDATE jobs SET status='done' WHERE step='wikibase'")
    con.commit()
    assert client.post("/api/jobs", json={"step": "wikibase", "args": args}).status_code == 200
    _age(_record(), 30)
    r = client.post("/api/jobs", json={"step": "wikibase", "args": args})
    assert r.status_code == 409 and "older than 24 hours" in r.json()["detail"]


def test_the_api_publish_gate(con, client, wiki):
    assert client.post("/api/jobs", json={"step": "publish", "args": {}}).status_code == 409
    assert client.post("/api/jobs", json={"step": "publish", "args": {"dry_run": True}}).status_code == 200
    con.execute("UPDATE jobs SET status='done'")
    con.commit()
    _publish(con, {"dry_run": True})
    rid = steps.read_record(steps.publish_dir() / steps.DRY_RUN_NAME)["id"]
    assert client.post("/api/jobs", json={"step": "publish", "args": {"dry_run_id": rid}}).status_code == 200


# ------------------------------------------------------------------------------------------- the payload
def _seed(con):
    up = db.upsert
    up(con, "asked_questions", [{"id": "how_glass_shop", "text": "how do i start a glass shop", "kind": "process"},
                                {"id": "no_answer_yet", "text": "how do i get a dog licence", "kind": "process"}],
       keys=("id",))
    up(con, "asked_answers", [{"question_id": "how_glass_shop", "target": "va", "state": "va", "status": "answered",
                               "bpmn": "<definitions/>", "model": "m"},
                              {"question_id": "how_glass_shop", "target": "dc", "state": "dc", "status": "partial",
                               "model": "m"}])
    up(con, "process_models", [{"model_id": f"{st}.records", "state": st, "question": "records", "tier": tier,
                                "stages": "{}"} for st, tier in (("va", "reviewed"), ("dc", "agreed"),
                                                                 ("md", "single"), ("de", "single"))])
    up(con, "place_processes", [{"gov_id": "51540", "state": "va", "process": p, "verified": v}
                                for p, v in (("dog_license", 1), ("building_permit", 1), ("yard_sale", 0))])
    con.executemany("INSERT INTO statute_files(state, status) VALUES (?, ?)",
                    [("va", "downloaded"), ("dc", "downloaded"), ("ar", "not-in-release")])
    up(con, "located_law", [{"state": "va", "question": "records", "status": "found"},
                            {"state": "dc", "question": "records", "status": "not-found"}])
    con.executemany("INSERT INTO wikibase_items(key, qid, label, updated_at) VALUES (?, ?, ?, ?)",
                    [(f"lexflow:step:va.records:s{i}", f"Q{100 + i}", "s", "2026-10-01T00:00:00Z") for i in range(3)])
    t0, t1 = "2026-10-01T10:00:00Z", "2026-10-01T10:02:05Z"
    con.executemany("INSERT INTO jobs(step, args, status, progress, message, created_at, started_at, finished_at) "
                    "VALUES (?,?,?,?,?,?,?,?)", [
                        ("index", "{}", "done", 1, "Finished", t0, t0, t1),
                        ("publish", '{"dry_run": false}', "failed", 0.2, "DokuWikiError: 401", t0, t0, t1),
                        ("wikibase", '{"passes": "1,2"}', "running", 0.4, "== pass 2", t0, t0, None),
                        ("wikibase", '{"states": "", "dry_run": false}', "failed", 0, "WikibaseError", t0, t0, t1)])
    con.commit()
    out = config.DATA_DIR / "wikibase-push"
    out.mkdir(parents=True, exist_ok=True)
    (out / push.PLAN_NAME).write_text(json.dumps({
        "dry_run": True, "pass": "all", "items": 4, "generated": "2026-10-22T09:00:00Z", "creates": 2, "updates": 3,
        "held_skipped": [HELD], "dropped_snaks": 4, "failures_by_code": {},
        "writes": [{"pass": 1, "kind": "property", "key": "a prop", "action": "create"},
                   {"pass": 1, "kind": "step", "key": "lexflow:step:va.records:new", "action": "create"},
                   {"pass": 2, "kind": "step", "key": "lexflow:step:va.records:new", "action": "clear"},
                   {"pass": 2, "kind": "step", "key": "lexflow:step:va.records:s1", "action": "clear"},
                   {"pass": 2, "kind": "step", "key": "lexflow:step:va.records:s2", "action": "skip-resume"},
                   {"pass": 2, "kind": "step", "key": "lexflow:step:va.records:lint", "action": "clear"}]}),
        encoding="utf-8")
    (out / push.LINT_NAME).write_text(json.dumps({"generated": "2026-10-22T08:59:00Z", "held_count": 1,
                                                  "held": [{"key": "lexflow:step:va.records:lint"}]}),
                                      encoding="utf-8")
    jobs_dir = config.JOBS_DIR
    jobs_dir.mkdir(parents=True, exist_ok=True)
    for name in ("1.log", "aus-pull.log", "old-run.log"):
        (jobs_dir / name).write_text("x", encoding="utf-8")
    old = time.time() - 3600
    os.utime(jobs_dir / "old-run.log", (old, old))


@pytest.fixture()
def quiet(monkeypatch):
    """No network: a fixed live count and compute pool; and none of the checkout's research files."""
    from lexflow.municipal import places
    monkeypatch.setattr(places, "process_files", lambda: [])
    monkeypatch.setattr(flow, "_fetch_live_count", lambda: (4321, "query service"))
    monkeypatch.setattr(flow, "_compute", lambda con: {"count": 1, "parts": {"nodes": 2, "online": 1, "slots": 3},
                                                       "detail": "1 of 2 nodes online"})
    flow.live_items(wait=True)


def test_the_payload_on_a_seeded_store(con, quiet, client):
    from lexflow.ask import coverage as CV
    _seed(con)
    p = flow.payload(con)
    places = {x["id"]: x for x in p["places"]}
    assert set(places) >= {"questions", "sources", "index", "located", "local", "drafts", "coverage", "verified",
                           "ready", "wikibase", "wiki", "turso", "compute", "benefits"}
    for x in places.values():
        assert x["label"] and x["meaning"] and x["href"].startswith("#/") and "detail" in x
    cov = {q["id"] for q in CV.questions()}
    assert places["questions"]["count"] == len(cov | {"how_glass_shop", "no_answer_yet"})
    assert places["sources"]["count"] == 2 and places["located"]["count"] == 1
    assert places["drafts"]["count"] == 1 + 2 and places["drafts"]["parts"] == {"asked_maps": 1, "single_models": 2}
    assert places["verified"]["count"] == 1 + 1 + 2
    assert places["local"]["parts"]["verified"] == 2 and places["local"]["parts"]["processes"] == 3
    # what the dry run would write (not properties, not skips), less what the lint report holds now
    assert places["ready"]["count"] == 2 and places["ready"]["parts"]["lint_held"] == 1
    assert places["wikibase"]["count"] == 3 and "4,321 items" in places["wikibase"]["detail"]
    assert places["coverage"]["count"] is None and places["benefits"]["count"] == 0
    assert places["compute"]["band"] is True
    t = {x["id"]: x for x in p["transitions"]}
    assert set(t) >= {"statutes", "index", "regulations", "locate", "local", "ask", "build", "coverage", "plan",
                      "wikibase", "publish", "sync"}
    for x in t.values():
        assert set(x["reads"]) | set(x["writes"]) <= set(places) and x["writes"]
        assert x["status"]["state"] in ("never", "running", "queued", "done", "failed", "cancelled")
    assert t["index"]["status"]["state"] == "done" and t["index"]["status"]["last"]["seconds"] == 125
    assert t["publish"]["status"]["state"] == "failed" and "401" in t["publish"]["status"]["last"]["message"]
    # the running dry run is the plan's; the v1-era job with dry_run false was a real write, the push's
    assert t["plan"]["status"]["state"] == "running" and t["plan"]["status"]["active"]["progress"] == 0.4
    assert t["wikibase"]["status"]["state"] == "failed"
    assert {x["id"] for x in t.values() if x["external"]} == {"wikibase", "publish", "sync"}
    assert {x["id"] for x in t.values() if x["model"] is True} == {"ask", "build", "coverage"}
    kinds = {k: [a["kind"] for a in x["actions"]] for k, x in t.items()}
    assert kinds["wikibase"] == ["dry_run", "push"] and kinds["publish"] == ["dry_run", "publish"]
    assert kinds["index"] == ["run"] and kinds["ask"] == ["link"] and kinds["plan"] == ["dry_run"]
    push_action = t["wikibase"]["actions"][1]
    assert push_action["args"] == {"really": True, "passes": "1,2", "skip_held": True} and push_action["confirm"]
    assert t["ask"]["waiting"]["count"] == 1 and t["local"]["waiting"]["count"] == 1
    assert [w["name"] for w in p["other_work"]] == ["aus-pull.log"]           # 1.log is job 1's; old-run.log is old
    assert p["wikibase"]["plan"]["would_write"] == 3 and p["wikibase"]["lint"]["held_count"] == 1
    assert p["wikibase"]["dry_run"] is None and "_plan" not in p["wikibase"]
    assert {"places", "transitions", "running", "other_steps", "publish", "dry_run_ttl"} <= set(p)
    flow.clear()
    flow.live_items(wait=True)
    r = client.get("/api/pipeline")
    assert r.status_code == 200 and {x["id"] for x in r.json()["places"]} == set(places)


def test_the_counts_are_cached_until_a_job_finishes(con, quiet):
    _seed(con)
    before = {x["id"]: x["count"] for x in flow.payload(con)["places"]}
    db.upsert(con, "process_models", [{"model_id": "ny.records", "state": "ny", "question": "records",
                                       "tier": "agreed", "stages": "{}"}])
    con.commit()
    assert {x["id"]: x["count"] for x in flow.payload(con)["places"]}["verified"] == before["verified"]
    con.execute("UPDATE jobs SET status='done', finished_at=? WHERE status='running'", (db.now(),))
    con.commit()
    p = flow.payload(con)
    assert {x["id"]: x["count"] for x in p["places"]}["verified"] == before["verified"] + 1
    assert {x["id"]: x for x in p["transitions"]}["plan"]["status"]["state"] == "done"   # statuses are always fresh


def test_the_live_count_is_cached_and_fails_soft(monkeypatch):
    calls = []

    def boom():
        calls.append(1)
        raise RuntimeError("the endpoint answered 404")
    v = flow.live_items(fetch=boom, wait=True)
    assert v["count"] is None and "404" in v["error"] and calls == [1]
    assert flow.live_items(fetch=boom, wait=True) == v and calls == [1]            # ten minutes before the next read
    monkeypatch.setattr(flow, "_now", lambda: time.time() + flow.LIVE_TTL + 1)
    assert flow.live_items(fetch=lambda: (12, "query service"), wait=True)["count"] == 12


def test_the_dry_run_records_show_on_the_payload(con, quiet, wb, pushed, wiki):
    _step(con, {"passes": "1,2"})
    _publish(con, {"dry_run": True})
    flow.clear()
    flow.live_items(wait=True)
    p = flow.payload(con)
    d = p["wikibase"]["dry_run"]
    assert d["id"] == _record()["id"] and d["refusal"] is None and 0 <= d["age_s"] < 60
    assert d["expires_in_s"] > 23 * 3600 and (d["creates"], d["updates"]) == (3, 3)
    pd = p["publish"]["dry_run"]
    assert pd["would_write"] == 1 and pd["refusal"] is None and p["publish"]["corrections_set"] is True
    _age(_record(), 30)
    flow.clear()
    flow.live_items(wait=True)
    assert "older than 24 hours" in flow.payload(con)["wikibase"]["dry_run"]["refusal"]
