"""The dashboard's wikibase step (lexflow/pipeline/steps.py) after the v1 loader's retirement: it runs the v2
pusher (lexflow.publish.push) as a dry run unless the job says ``really``, refuses ``really`` without a lint report
(or, with ``skip_held`` off, with one that holds items) and without a recent dry run of the same graph, passes
``allow_held`` only for the operator's ``skip_held`` choice, and is never part of a run-all chain.  No network:
``push.run`` is recorded, not run, and the graph is a fixed empty one (tests/test_pipeline.py covers the dry-run
records, the chained passes and the refusals in full)."""
import inspect
import json

import pytest

from lexflow.pipeline import steps
from lexflow.publish import graph, push


@pytest.fixture(autouse=True)
def no_graph(monkeypatch):
    """The step builds the graph itself (for its hash); here it is empty.  A bot password is set (never used)."""
    from lexflow import config
    monkeypatch.setattr(graph, "build", lambda con, **kw: [])
    monkeypatch.setattr(config, "WIKIBASE_BOT_USER", "bot")
    monkeypatch.setattr(config, "WIKIBASE_BOT_PASSWORD", "not-a-real-password")
    monkeypatch.delenv("LEXFLOW_WIKIBASE_OUT", raising=False)


@pytest.fixture()
def pushed(monkeypatch):
    """Records every call of push.run instead of planning anything."""
    calls = []

    def fake_run(con, **kw):
        calls.append(kw)
        return {"dry_run": kw["dry_run"], "pass": "all", "items": 3, "plan": str(kw["out_dir"] / push.PLAN_NAME),
                "api_writes": 0 if kw["dry_run"] else 3, "seconds": 0.1,
                "summary": {"creates": 1, "updates": 2, "held_skipped": [], "dropped_snaks": 0, "failures_by_code": {}}}
    monkeypatch.setattr(push, "run", fake_run)
    return calls


def _lint(out, held):
    out.mkdir(parents=True, exist_ok=True)
    (out / push.LINT_NAME).write_text(json.dumps({"held": [{"key": k} for k in held]}), encoding="utf-8")


def _run(con, args, tmp_path):
    logs = []
    out = steps.run_wikibase(con, {"out": str(tmp_path / "wb"), **args}, logs.append, lambda p: None)
    return out, logs


def test_the_step_is_a_dry_run_by_default(con, pushed, tmp_path):
    out, logs = _run(con, {}, tmp_path)
    assert len(pushed) == 1 and pushed[0]["dry_run"] is True and pushed[0]["allow_held"] is False
    assert pushed[0]["drafts"] is False and pushed[0]["resume"] is True
    assert out["dry_run"] is True and out["really"] is False and out["api_writes"] == 0
    assert out["creates"] == 1 and out["updates"] == 2 and out["plan"].endswith(push.PLAN_NAME)
    assert any("dry run" in m and "nothing is written" in m for m in logs)


def test_really_is_refused_without_a_lint_report(con, pushed, tmp_path):
    out, logs = _run(con, {"really": True}, tmp_path)
    assert pushed == []                                           # the pusher is not even reached
    assert out["refused"].endswith("run `lexflow wikibase lint` first") and out["dry_run"] is True
    assert any(m.startswith("push refused: nothing was written") for m in logs)


def test_really_is_refused_while_the_lint_report_holds_items_unless_skip_held(con, pushed, tmp_path):
    _lint(tmp_path / "wb", ["lexflow:step:va.records:respond", "lexflow:role:va:records:custodian"])
    out, _ = _run(con, {"really": True, "skip_held": False}, tmp_path)
    assert pushed == [] and out["refused"].startswith("the lint report holds 2 items: fix them and re-run the lint")
    # skip_held (the default) gets past the lint, and the dry run is asked for next
    out, _ = _run(con, {"really": True}, tmp_path)
    assert pushed == [] and out["refused"].startswith("no dry run of the push has been recorded")


def test_really_with_a_passing_lint_report_pushes_without_allow_held(con, pushed, tmp_path):
    _lint(tmp_path / "wb", [])
    scope = {"drafts": True, "full": True, "states": "va,dc"}
    _run(con, scope, tmp_path)                                     # the dry run a push follows
    out, logs = _run(con, {"really": True, **scope}, tmp_path)
    assert len(pushed) == 2 and pushed[1]["dry_run"] is False and pushed[1]["allow_held"] is False
    pushed.pop(0)
    assert pushed[0]["drafts"] is True and pushed[0]["resume"] is False and sorted(pushed[0]["states"]) == ["dc", "va"]
    assert out["dry_run"] is False and out["really"] is True and out["api_writes"] == 3
    assert any(m.startswith("real push to") for m in logs)


def test_a_dry_run_flag_wins_over_really(con, pushed, tmp_path):
    _lint(tmp_path / "wb", [])
    out, _ = _run(con, {"really": True, "dry_run": True}, tmp_path)
    assert pushed[0]["dry_run"] is True and out["really"] is False


def test_the_step_never_reaches_the_v1_loader():
    src = inspect.getsource(steps.run_wikibase)
    body = src.split('"""', 2)[2]                                 # the code, not the docstring that tells the story
    assert "wikibase_lexipedia" not in body and "retire_drafts" not in body and "allow_held=False" in body
    step = steps.STEPS["wikibase"]
    assert step.run is steps.run_wikibase and "really" in step.params and "dry_run" not in step.params
    assert "dry run" in step.why and "lint" in step.why


def test_run_everything_never_includes_a_step_that_writes_to_an_outside_site(con, monkeypatch):
    """The quickstart composite (the dashboard's run-all button) runs local steps only."""
    ran = []
    for name in ("governments", "statutes", "locate", "contacts", "crawl", "local", "build", "score"):
        monkeypatch.setattr(steps, f"run_{name}", lambda con, args, log, progress, n=name: ran.append(n) or {})
    for ext in steps.EXTERNAL_WRITERS:
        monkeypatch.setattr(steps, f"run_{ext}", lambda *a, **k: (_ for _ in ()).throw(AssertionError(ext)))
    steps.run_quickstart(con, {"states": "va", "places": "va:charlottesville"}, lambda m: None, lambda p: None)
    assert ran and not set(ran) & steps.EXTERNAL_WRITERS
    assert steps.EXTERNAL_WRITERS >= {"wikibase", "publish", "sync"}
    assert not any(ext in inspect.getsource(steps.run_quickstart) for ext in steps.EXTERNAL_WRITERS)
    # and no other composite step calls one either
    for comp in steps.COMPOSITE.values():
        src = inspect.getsource(comp.run)
        assert not any(f"run_{ext}" in src for ext in steps.EXTERNAL_WRITERS), comp.id


def test_single_pass_is_part_of_the_scope_and_bot_and_pause_shape_only_the_push(con, pushed, tmp_path):
    _lint(tmp_path / "wb", [])
    _run(con, {"states": "jpn", "single_pass": True}, tmp_path)   # the dry run plans the single pass
    assert pushed[0]["single_pass"] is True and "bot" not in pushed[0] and "pause" not in pushed[0]
    rec = steps.read_record(tmp_path / "wb" / steps.DRY_RUN_NAME)
    assert rec["scope"] == {"states": ["jpn"], "drafts": False, "full": False, "single_pass": True}
    # a push without the single pass is another scope than the dry run's
    out, _ = _run(con, {"really": True, "states": "jpn"}, tmp_path)
    assert len(pushed) == 1 and "single pass" in out["refused"]
    out, logs = _run(con, {"really": True, "states": "jpn", "single_pass": True, "bot": True, "pause": "0.2"}, tmp_path)
    real = pushed[1]
    assert real["dry_run"] is False and real["single_pass"] is True and real["bot"] is True and real["pause"] == 0.2
    assert any("single pass, with the bot flag, 0.2 s between writes" in m for m in logs)


def test_a_scope_without_single_pass_still_matches_an_older_record():
    assert steps.wikibase_scope({"states": "va"}) == {"states": ["va"], "drafts": False, "full": False}
    assert steps.wikibase_scope({"single_pass": "false"}) == {"states": None, "drafts": False, "full": False}
