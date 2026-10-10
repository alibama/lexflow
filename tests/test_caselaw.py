"""CourtListener search: queries, court ids, and rate limits that must not read as 'no opinions'."""
import pytest

from lexflow.municipal import caselaw


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
