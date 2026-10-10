"""AskBench honesty: whole-number slots, same-code citations, most-of-the-nugget coverage, claims when every one was
dropped, versioned rows, an unmatched --cases filter, the held-out reranker, and the Claude-vs-Claude ceiling."""
import argparse
import json
import re

import pytest

from lexflow.ask import bench as AB
from lexflow.ask import index as I
from lexflow.ask import reference as R
from lexflow.store import db


def _spec(**kw):
    spec = {"qid": "records_q", "question": "How do I request records?", "state": "va", "question_type": "facts",
            "coverage": "in_code", "profile": {"groups": [["public records"], ["request"]]},
            "gold_sections": [{"ref": "2.2-3704", "role": "primary", "why": "the procedure"}],
            "nuggets": [{"id": "N1", "text": "Five working days to respond.", "importance": "vital",
                         "section": "2.2-3704", "quote": "within five working days of receiving a request",
                         "slot": "deadline"}],
            "slots": {"deadline": [{"amount": 5, "unit": "working days", "anchor": "receipt", "nuggets": ["N1"]}]},
            "answer": "A public body must respond to a records request within five working days of receiving it "
                      "[N1]. It can be said in more words here so the answer is long enough to pass the length "
                      "check for a reference answer in the benchmark.",
            "out_of_corpus": [], "steps": None}
    spec.update(kw)
    return spec


def _row(quotes, chosen=(), summary=None, status="answered"):
    return {"status": status, "sections": {"candidates": [], "chosen": [{"id": i} for i in chosen]},
            "answer": {"quotes": [dict(id=f"Q{i}", **q) for i, q in enumerate(quotes, 1)], "steps": [],
                       "summary": summary}}


# ---------------------------------------------------------------- numbers
def test_has_num_matches_whole_numbers_and_whole_words():
    assert R.has_num("5", "within 5 days") and R.has_num("5", "within five days") and R.has_num("5", "a five-year term")
    assert not R.has_num("5", "1995 acts") and not R.has_num("5", "within 45 days") and not R.has_num("5", "§ 1.5")
    assert not R.has_num("5", "within forty-five days") and R.has_num("45", "within forty-five days")
    assert not R.has_num("10", "section 1050") and not R.has_num("10", "a sentence, extended, written, tenth")
    assert R.has_num("10", "the 10th day") and R.has_num("10", "on the tenth day after")
    assert not R.has_num("2", "§ 19.2-243") and not R.has_num("500", "a fee of $1,500")
    assert R.has_num("1,500", "a fee of $1,500.") and R.has_num("243", "§ 19.2-243")
    assert R.has_num("5", "on or after the fifth anniversary") and not R.has_num("2", "a second or subsequent offense")
    assert not R.has_num("1", "§ 1205") and not R.has_num("", "1")


def test_slot_match_counts_whole_numbers_only(con, va_statutes):
    assert I.ensure("va")
    spec = _spec()
    noise = AB.score(spec, _row([{"section": "2.2-3704", "text": "Upon conviction the court shall impose a sentence as "
                                                                "provided in § 19.2-243 and 1995 Acts."}]))
    assert noise["slot_match"] == 0.0                       # no 5, five or 10 here, only digits of other numbers
    hit = AB.score(spec, _row([{"section": "2.2-3704", "text": "the public body shall respond within 5 working days"}]))
    assert hit["slot_match"] == 1.0


def test_reference_check_rejects_slot_numbers_inside_other_numbers(con, va_statutes):
    text = va_statutes[va_statutes["section_number"] == "2.2-3704"].iloc[0]["text"]
    i = text.index("60 work days")
    quote = " ".join(text[text.rindex("pursuant to", 0, i):i + len("60 work days in which")].split())
    assert "3706.1" in quote
    spec = _spec(nuggets=[{"id": "N1", "text": "Sixty work days.", "importance": "vital", "section": "2.2-3704",
                           "quote": quote, "slot": "deadline"}],
                 slots={"deadline": [{"amount": 60, "unit": "work days", "anchor": "request", "nuggets": ["N1"]}]})
    assert R.check(spec, "records_q", "va")["ok"], R.check(spec, "records_q", "va")["problems"]
    for wrong in (6, 706, 3):                               # each is inside 60 or 3706.1, none is a number there
        bad = json.loads(json.dumps(spec))
        bad["slots"]["deadline"][0]["amount"] = wrong
        assert any(f"{wrong} does not appear" in p for p in R.check(bad, "records_q", "va")["problems"]), wrong


def test_every_curated_reference_passes_the_stricter_slot_check():
    """The slot part of R.check (no statutes needed): every number of every slot is whole in its nuggets' quotes."""
    for alt in (False, True):
        for qid, state in R.cases(alt=alt):
            spec = R.load(qid, state, alt)
            quotes = {n.get("id"): R.norm(n.get("quote")) for n in spec.get("nuggets") or []}
            for kind, vals in (spec.get("slots") or {}).items():
                for v in [x for x in (vals if isinstance(vals, list) else [vals]) if isinstance(x, dict)]:
                    for num in re.findall(r"\d[\d,.]*", f"{v.get('value', '')} {v.get('amount', '')}"):
                        num = num.strip(".,")
                        assert not num or any(R.has_num(num, quotes.get(r, "")) for r in v["nuggets"]), \
                            (qid, state, alt, kind, num)


# ---------------------------------------------------------------- citations
def _two_codes(monkeypatch):
    """California with § 200 in two codes: the fixture's Corporations Code and a made-up Penal Code section."""
    import pandas as pd
    from conftest import fixture_frame
    from lexflow.municipal import statutes
    df = fixture_frame("ca")
    corp = df[df["citation"] == "Cal. CORP § 200"].iloc[0]
    pen = dict(corp, act_id="pen200", citation="Cal. PEN § 200", section_title="Penalty for nonpayment",
               text="Every person who willfully fails to pay a fine ordered by the court is guilty of a misdemeanor.")
    frame = pd.concat([df, pd.DataFrame([pen])], ignore_index=True)
    monkeypatch.setattr(statutes, "load", lambda st: frame)
    monkeypatch.setattr(statutes, "have", lambda st: st == "ca")
    assert I.ensure("ca", log=lambda *_: None)
    return corp["text"], pen["text"]


def test_citation_precision_needs_the_same_section_of_the_same_code(con, monkeypatch):
    corp_text, pen_text = _two_codes(monkeypatch)
    ids = {r["citation"]: r["id"] for r in I.lookup("ca", "200")}
    assert set(ids) == {"Cal. CORP § 200", "Cal. PEN § 200"}
    spec = _spec(state="ca", gold_sections=[{"ref": "Cal. CORP § 200", "role": "primary", "why": "x"}], nuggets=[],
                 slots={})
    corp_q = {"section": "200", "text": " ".join(corp_text.split()[:12])}
    pen_q = {"section": "200", "text": "Every person who willfully fails to pay a fine ordered by the court"}
    for chosen in (ids.values(), ()):                       # with both sections chosen, and with none
        assert AB.score(spec, _row([corp_q], chosen))["citation_precision"] == 1.0
        assert AB.score(spec, _row([pen_q], chosen))["citation_precision"] == 0.0
        assert AB.score(spec, _row([corp_q, pen_q], chosen))["citation_precision"] == 0.5
    # a number that is only a suffix of the gold one is another section
    assert AB.score(spec, _row([{"section": "00", "text": corp_q["text"]}]))["citation_precision"] == 0.0


def test_citation_precision_no_suffix_match(con, va_statutes):
    assert I.ensure("va")
    spec = _spec()
    text = "the public body shall respond within five working days of receiving a request"
    assert AB.score(spec, _row([{"section": "2.2-3704", "text": text}]))["citation_precision"] == 1.0
    for other in ("3704", "04", "", None):
        assert AB.score(spec, _row([{"section": other, "text": text}]))["citation_precision"] == 0.0, other


# ---------------------------------------------------------------- nuggets
NUGGET = ("the person has been released; (2) the charge, if any, has not resulted in a final conviction and is no "
          "longer pending; and (3) there was no court-ordered community supervision under chapter 42a for the offense")
CLAUSES = ["the person has been released;",
           "the charge, if any, has not resulted in a final conviction and is no longer pending; and",
           "there was no court-ordered community supervision under Chapter 42A for the offense, other than for a "
           "Class C misdemeanor."]


def test_a_short_clause_of_a_long_nugget_does_not_cover_it():
    assert not AB.overlaps(NUGGET, CLAUSES[0]) and not AB.covered(NUGGET, CLAUSES[:1])
    assert not AB.covered(NUGGET, CLAUSES[:2])              # 2 of 3 clauses: under COVER of its words
    assert AB.covered(NUGGET, CLAUSES)                     # all of it shown, the last clause running on past its end
    assert AB.overlaps(NUGGET, "Thus " + NUGGET + " more")  # the whole nugget inside one quote
    # a quote that starts before the nugget and ends inside it shows that part
    assert AB._shared(NUGGET, "Each condition applies: the person has been released;") == CLAUSES[0]
    assert AB._shared(NUGGET, "a person who has been released by the court") == ""


def test_vital_recall_and_the_ceiling_ignore_fragments(con, va_statutes):
    assert I.ensure("va")
    spec = _spec(nuggets=[{"id": "N1", "text": "Three conditions.", "importance": "vital", "section": "2.2-3704",
                           "quote": NUGGET, "slot": None}], slots={})
    assert AB.score(spec, _row([{"section": "2.2-3704", "text": CLAUSES[0]}]))["vital_recall"] == 0.0
    assert AB.score(spec, _row([{"section": "2.2-3704", "text": t} for t in CLAUSES]))["vital_recall"] == 1.0
    other = json.loads(json.dumps(spec))
    other["nuggets"][0]["quote"] = CLAUSES[0]
    assert AB.agreement(spec, other)["vital_nuggets"] == 0.5     # it covers the other's fragment, not the reverse


# ---------------------------------------------------------------- claims
def test_claim_metrics_count_summaries_whose_claims_were_all_dropped(con, va_statutes):
    assert I.ensure("va")
    spec = _spec()
    quote = {"section": "2.2-3704", "text": "shall respond within five working days of receiving a request by"}
    kept = AB.score(spec, _row([quote], summary={"status": "answered", "dropped": [],
                                                 "claims": [{"text": "Five working days.", "quotes": ["Q1"]}]}))
    dropped = AB.score(spec, _row([quote], summary={"status": "not_found", "claims": [],
                                                    "dropped": [{"text": "x", "why": "cites no quote"}] * 4}))
    assert (kept["claims"], kept["claim_vital_recall"]) == (1, 1.0)
    assert (dropped["claims"], dropped["claims_dropped"], dropped["claim_vital_recall"]) == (0, 4, 0.0)
    s = AB.summary([dict(kept, arm="local+llm"), dict(dropped, arm="local+llm")])["local+llm"]
    assert (s["claims"], s["claims_dropped"], s["claim_vital_recall"]) == (0.5, 2.0, 0.5)
    assert "claims" not in AB.score(spec, _row([quote]))          # no summary written: no claim metrics


# ---------------------------------------------------------------- docs/askbench.json
def test_stored_rows_are_the_current_reference_and_code_only(con):
    (q1, s1), (q2, s2) = R.cases()[:2]
    h1, h2, ver = R.hash_of(R.load(q1, s1)), R.hash_of(R.load(q2, s2)), AB.version()
    assert ver.startswith(f"{AB.METRIC_VERSION}-") and ver == AB.version()
    rows = [(f"{q1}.{s1}", "local", h1, ver), (f"{q1}.{s1}", "oracle", h1, "1-old"),
            (f"{q2}.{s2}", "local", "stale", ver), (f"{q2}.{s2}", "profile", h2, None)]
    db.upsert(con, "ask_bench", [{"case_id": c, "arm": a, "ref_hash": h, "created_at": db.now(),
                                  "metrics": json.dumps({"case": c, "arm": a, "composite": 0.5, "version": v})}
                                 for c, a, h, v in rows], keys=("case_id", "arm"), stamp=False)
    con.commit()
    kept, excluded = AB.stored(con)
    assert [(r["case"], r["arm"]) for r in kept] == [(f"{q1}.{s1}", "local")]
    assert excluded == {"stale_reference": 1, "stale_code": 2}
    summ = AB.summary(kept + [{"case": f"{q2}.{s2}", "arm": "oracle", "composite": 1.0}])
    assert summ["local"]["cases"] == 1 and summ["local"]["case_ids"] == [f"{q1}.{s1}"]
    assert summ["oracle"]["case_ids"] == [f"{q2}.{s2}"]


def test_an_unmatched_cases_filter_errors_instead_of_running_everything(monkeypatch, capsys):
    from lexflow import cli
    monkeypatch.setattr(AB, "run", lambda *a, **k: pytest.fail("the benchmark must not run"))
    q, s = R.cases()[0]
    for cases in ("no_such_question.zz", f"{q}.{s},{q}.zz", " , "):
        args = argparse.Namespace(cases=cases, arms="local", llm=False, llm_plan=False)
        assert cli.cmd_ask_bench(args) == 1, cases
    assert "no reference matches" in capsys.readouterr().out


def _fake_pipeline(monkeypatch, seen):
    from lexflow.ask import pipeline as AP
    from lexflow.ask import relevance as RV
    from lexflow.ask import retrieve as RT

    def answer_state(*a, **k):
        seen.append((RT.USE_LEARNED, RV.OVERRIDE))
        return {"status": "not_found", "sections": {"candidates": [], "chosen": []},
                "answer": {"quotes": [], "steps": []}}
    monkeypatch.setattr(AP, "embedder", lambda: None)
    monkeypatch.setattr(AP, "answer_state", answer_state)


def test_run_with_no_cases_runs_nothing(con, monkeypatch):
    seen = []
    _fake_pipeline(monkeypatch, seen)
    assert AB.run(con, ("local",), [], log=lambda *_: None) == [] and not seen


def test_a_missing_or_stale_held_out_model_marks_the_arm(con, va_statutes, monkeypatch, tmp_path):
    from lexflow.ask import relevance as RV
    from lexflow.ask import retrieve as RT
    assert I.ensure("va")
    monkeypatch.setattr(RV, "loqo_path", lambda qid: tmp_path / "loqo" / f"{qid}.json")
    case = ("court_debt", "va")
    seen, logs = [], []
    _fake_pipeline(monkeypatch, seen)
    (tmp_path / "loqo").mkdir()
    for model, arm, reranker, learned in ((None, "local-unlearned", "missing", False),
                                          ({"features": ["old"]}, "local-unlearned", "stale", False),
                                          ({"features": RV.FEATURES, "beta": [0]}, "local", "loqo", True)):
        path = tmp_path / "loqo" / "court_debt.json"
        if model is not None:
            path.write_text(json.dumps(model), encoding="utf-8")
        seen.clear()
        rows = AB.run(con, ("local", "heuristic"), [case], log=logs.append)
        assert [(r["arm"], r["reranker"]) for r in rows] == [(arm, reranker), ("heuristic", "none")]
        assert seen == [(learned, model if learned else None), (False, None)]
        assert all(r["version"] == AB.version() for r in rows)
    assert RT.USE_LEARNED is True and RV.OVERRIDE is None
    assert sum("held-out reranker missing" in line for line in logs) == 1
    assert sum("held-out reranker stale" in line for line in logs) == 1
    arms = {r["arm"] for r in db.rows(con, "SELECT arm FROM ask_bench")}
    assert arms == {"local-unlearned", "local", "heuristic"}


# ---------------------------------------------------------------- the Claude-vs-Claude ceiling
def test_ceiling_skips_a_malformed_alt_draft(con, va_statutes, monkeypatch):
    assert I.ensure("va")
    good = _spec()
    no_importance = _spec(nuggets=[{k: v for k, v in good["nuggets"][0].items() if k != "importance"}])
    no_coverage = {k: v for k, v in good.items() if k != "coverage"}
    drafts = {("a", "va"): no_importance, ("b", "va"): no_coverage, ("c", "va"): good}
    monkeypatch.setattr(R, "cases", lambda alt=False: sorted(drafts))
    monkeypatch.setattr(R, "load", lambda q, s, alt=False: dict(drafts[(q, s)], qid=q) if alt else dict(good, qid=q))
    out = AB.ceiling()
    assert [c["case"] for c in out] == ["a.va", "b.va", "c.va"]
    assert "importance" in out[0]["error"] and "coverage" in out[1]["error"] and out[2]["mean"] == 1.0
    # a draft that passes the checks but still cannot be compared is skipped too, not raised
    monkeypatch.setattr(AB, "agreement", lambda a, b: {}["x"])
    assert all("KeyError" in c["error"] for c in AB.ceiling() if c["case"] == "c.va")


def test_agreement_counts_steps_when_only_one_draft_has_them(con, va_statutes):
    assert I.ensure("va")
    a, b = _spec(), _spec(steps={"actors": [], "steps": []})
    assert AB.agreement(a, b)["steps"] == 0.0 and AB.agreement(b, a)["steps"] == 0.0
    assert AB.agreement(a, json.loads(json.dumps(a)))["steps"] is None
