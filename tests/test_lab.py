"""Process lab: business-day arithmetic over holidays and weekends (VA, CA, with the published 2026-2027 court and
executive schedules), deadline parsing for every curated deadline, the timeline of a Virginia records request, the
per-case calendar options, the state places bundle (the place never leaves the browser), the office-channel rules of
``lexflow.privacy``, and the opt-in outcome endpoint (field whitelist, random keys, no rowid, aggregates only)."""
import json
import re
import sqlite3
import warnings
from datetime import date
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from lexflow import config, privacy
from lexflow.lab import api as A
from lexflow.lab import deadlines as D
from lexflow.lab import instances as I
from lexflow.lab.api import router
from lexflow.store import db

ROOT = Path(__file__).resolve().parents[1]


# ------------------------------------------------------------------ business days: Virginia
@pytest.mark.parametrize("start, n, due, skipped", [
    (date(2008, 1, 18), 5, date(2008, 1, 28), ["2008-01-21"]),          # FOIA Council AO-02-08; MLK Day skipped
    (date(2026, 10, 30), 5, date(2026, 11, 9), ["2026-11-03"]),          # Election Day (§ 2.2-3300)
    (date(2026, 11, 25), 5, date(2026, 12, 4), ["2026-11-26", "2026-11-27"]),   # Thanksgiving and the Friday after
    (date(2026, 11, 4), 7, date(2026, 11, 16), ["2026-11-11"]),          # B.4 from the extension notice; Veterans Day
    (date(2026, 11, 9), 7, date(2026, 11, 19), ["2026-11-11"]),          # B.4 from the end of the five days
    (date(2026, 10, 9), 5, date(2026, 10, 19), ["2026-10-12"]),          # Columbus Day and Yorktown Victory Day
    (date(2026, 7, 2), 1, date(2026, 7, 6), ["2026-07-03"]),             # July 4 on a Saturday: observed Friday
    (date(2027, 12, 29), 2, date(2028, 1, 3), ["2027-12-31"]),           # 1 Jan 2028 (Saturday) observed 31 Dec 2027
    # the Governor's full-day closing on Thu 24 Dec 2026 (DHRM 2026 calendar, 8 hours; § 1-210(F)), then Christmas:
    # the verifier's case, due Wed 30 Dec rather than Tue 29 Dec
    (date(2026, 12, 21), 5, date(2026, 12, 30), ["2026-12-24", "2026-12-25"]),
    # (the part day of 25 Nov 2026 is tested on its own below: by default it is not counted)
])
def test_virginia_business_days(start, n, due, skipped):
    c = D.add_business_days("va", start, n)
    assert c.due == due
    assert [s["date"] for s in c.skipped] == skipped
    assert all("2.2-3300" in s["why"] for s in c.skipped)


def test_virginia_weekend_is_never_a_due_date_and_counts_start_after_the_event():
    for day in range(1, 32):
        start = date(2026, 12, day)
        due = D.add_business_days("va", start, 5).due
        assert due.weekday() < 5 and due > start
    assert not D.is_business_day("va", date(2026, 11, 3))       # Election Day
    assert D.is_business_day("va", date(2026, 3, 31))           # not a Virginia holiday


# DHRM's 2026 and 2027 Pay and Holiday Calendars (read 10 Oct 2026): every day off, with the part days (4 hours) apart
VA_2026 = ["2026-01-01", "2026-01-19", "2026-02-16", "2026-05-25", "2026-06-19", "2026-07-03", "2026-09-07",
           "2026-10-12", "2026-11-03", "2026-11-11", "2026-11-26", "2026-11-27", "2026-12-24", "2026-12-25"]
VA_2027 = ["2027-01-01", "2027-01-18", "2027-02-15", "2027-05-31", "2027-06-18", "2027-07-05", "2027-09-06",
           "2027-10-11", "2027-11-02", "2027-11-11", "2027-11-25", "2027-11-26", "2027-12-24", "2027-12-31"]


@pytest.mark.parametrize("year, full, part", [(2026, VA_2026, ["2026-11-25"]),
                                              (2027, VA_2027, ["2027-11-24", "2027-12-23"])])
def test_virginia_table_matches_the_dhrm_calendar(year, full, part):
    days = D.holidays("va", year)
    assert [h["date"] for h in days if not h["part_day"]] == full
    assert [h["date"] for h in days if h["part_day"]] == part


PART_1210E = D.Options(variant="part_days_1210e")


def test_virginia_part_day_is_not_counted_by_default_and_the_1210e_reading_counts_it():
    """Decision (the conservative one): the 4 hours the DHRM calendar grants on Wed 25 Nov 2026 may close the
    office for part of the day (§ 1-210(E) covers 'part of a day' an office is closed), so by default the day is not
    counted and a body is never called overdue while it may still be in time.  The § 1-210(E) reading counts it
    and moves only a period that ends on it."""
    wed = date(2026, 11, 25)
    assert not D.is_business_day("va", wed) and D.part_day("va", wed)
    assert "part day off" in D.closed_reason(D.VA, wed) and "1-210(E)" in D.closed_reason(D.VA, wed)
    c = D.add_business_days("va", date(2026, 11, 20), 7)                 # skipped, not counted: Fri 4 Dec
    assert c.due == date(2026, 12, 4)
    assert [s["date"] for s in c.skipped] == ["2026-11-25", "2026-11-26", "2026-11-27"]
    assert any("part day off" in n and "not counted" in n for n in c.notes)
    # the § 1-210(E) reading: counted in mid-period (the verifier's hand-worked Thu 3 Dec) ...
    assert D.add_business_days("va", date(2026, 11, 20), 7, PART_1210E).due == date(2026, 12, 3)
    # ... and a period that ends on it runs on, to the same date as the default
    v = D.add_business_days("va", date(2026, 11, 20), 3, PART_1210E)
    assert (v.due, v.rolled_from) == (date(2026, 11, 30), wed)
    assert D.add_business_days("va", date(2026, 11, 20), 3).due == date(2026, 11, 30)
    assert D.elapsed("va", date(2026, 11, 24), wed, "business_days") == 0
    assert D.elapsed("va", date(2026, 11, 24), wed, "business_days", PART_1210E) == 1
    assert D.add_calendar_days("va", date(2026, 11, 18), 7).due == date(2026, 11, 30)     # rolls past it
    opened = D.Options(opens=frozenset({"va_part_2026_11_25"}))          # an office open all day: a working day
    assert D.is_business_day("va", wed, opened)
    assert D.add_business_days("va", date(2026, 11, 20), 7, opened).due == date(2026, 12, 3)
    open_ = D.Options(opens=frozenset({"va_closing_2026_12_24"}))           # a local office that stayed open
    assert D.add_business_days("va", date(2026, 12, 21), 5, open_).due == date(2026, 12, 29)
    assert D.add_business_days("va", date(2026, 12, 21), 5, D.Options(variant="executive_open")).due == \
        date(2026, 12, 29)
    assert [h["counted"] for h in D.holidays("va", 2026) if h["part_day"]] == [False]
    assert [h["counted"] for h in D.holidays("va", 2026, PART_1210E) if h["part_day"]] == [True]
    rule = D.describe_calendar("va")["part_day_rule"]
    assert "not counted as a working day by default" in rule and "1-210(E)" in rule


# ------------------------------------------------------------------ business and calendar days: California
@pytest.mark.parametrize("start, n, due", [
    (date(2026, 11, 25), 3, date(2026, 12, 2)),     # Thanksgiving and the day after (CCP § 135)
    (date(2027, 3, 30), 1, date(2027, 3, 31)),      # the 2027 court schedule moves Farmworkers Day off 31 March ...
    (date(2027, 4, 8), 1, date(2027, 4, 12)),       # ... to Friday 9 April
    (date(2026, 3, 30), 1, date(2026, 4, 1)),       # in 2026 it is on 31 March (Gov. § 6700(a)(7))
    (date(2027, 2, 11), 1, date(2027, 2, 16)),      # Lincoln Day (Fri) and the third Monday in February
    (date(2026, 10, 9), 1, date(2026, 10, 12)),     # Columbus Day is not a judicial holiday (CCP § 135)
    (date(2028, 11, 9), 1, date(2028, 11, 13)),     # 11 Nov 2028 is a Saturday: the Friday before
    (date(2026, 7, 2), 1, date(2026, 7, 6)),        # 4 Jul 2026 is a Saturday: courts close Fri 3 Jul (rule 1.11)
    (date(2027, 6, 17), 1, date(2027, 6, 21)),      # Juneteenth 2027 (Sat) observed Fri 18 Jun
    (date(2027, 12, 23), 1, date(2027, 12, 27)),    # Christmas 2027 (Sat) observed Fri 24 Dec
])
def test_california_business_days(start, n, due):
    assert D.add_business_days("ca", start, n).due == due


# the Judicial Council's published court holidays (courts.ca.gov/about/court-holidays, read 10 Oct 2026)
CA_2026 = ["2026-01-01", "2026-01-19", "2026-02-12", "2026-02-16", "2026-03-31", "2026-05-25", "2026-06-19",
           "2026-07-03", "2026-09-07", "2026-09-25", "2026-11-11", "2026-11-26", "2026-11-27", "2026-12-25"]
CA_2027 = ["2027-01-01", "2027-01-18", "2027-02-12", "2027-02-15", "2027-04-09", "2027-05-31", "2027-06-18",
           "2027-07-05", "2027-09-06", "2027-09-24", "2027-11-11", "2027-11-25", "2027-11-26", "2027-12-24"]


def test_california_table_matches_the_court_schedule():
    assert [h["date"] for h in D.holidays("ca", 2026)] == CA_2026
    days_2027 = [h["date"] for h in D.holidays("ca", 2027)]
    # rule 1.11 also observes New Year's Day 2028 (a Saturday) on Fri 31 Dec 2027, which belongs to the 2028 list
    assert days_2027 == CA_2027 + ["2027-12-31"]
    assert "2027-03-31" not in days_2027
    assert "rule 1.11" in D.closed_reason(D.CA, date(2026, 7, 3))
    assert "2027 court holidays" in D.closed_reason(D.CA, date(2027, 4, 9))


def test_california_calendar_days_roll_forward_over_holidays_and_saturdays():
    c = D.add_calendar_days("ca", date(2026, 11, 16), 10)       # CPRA: "within 10 days from receipt"
    assert (c.rolled_from, c.due) == (date(2026, 11, 26), date(2026, 11, 30))
    assert "12a" in c.notes[0]
    assert D.add_calendar_days("ca", date(2026, 10, 7), 10).due == date(2026, 10, 19)    # Saturday rolls (CCP § 12a)
    assert D.add_calendar_days("ca", date(2026, 10, 1), 10).due == date(2026, 10, 12)    # Columbus Day does not
    c = D.add_calendar_days("ca", date(2026, 6, 23), 10)        # the verifier's case: 3 Jul is a court holiday
    assert (c.rolled_from, c.due) == (date(2026, 7, 3), date(2026, 7, 6))


def test_state_tables_follow_their_own_statutes():
    assert D.add_business_days("va", date(2026, 10, 9), 1).due == date(2026, 10, 13)     # VA counts Columbus Day
    assert D.is_business_day("tx", date(2026, 10, 12))          # not in Tex. Gov't Code § 662.003
    assert not D.is_business_day("tx", date(2026, 3, 2))        # Texas Independence Day
    assert D.is_business_day("tx", date(2026, 4, 3))            # Good Friday: optional holiday ...
    observes = D.Options(observes=frozenset({"good_friday"}))
    assert not D.is_business_day("tx", date(2026, 4, 3), observes)    # ... unless the body observes it
    assert D.is_business_day("md", date(2026, 7, 3))            # Md. § 1-111(b) moves Sunday holidays only
    assert not D.is_business_day("md", date(2026, 3, 25))       # Maryland Day ...
    assert D.is_business_day("md", date(2026, 3, 25), D.Options(variant="employee"))     # ... not an employee holiday
    assert D.rosh_hashanah(2026) == date(2026, 9, 12) and D.easter(2026) == date(2026, 4, 5)
    assert not D.is_business_day("nc", date(2026, 9, 21))       # Yom Kippur 2026 (N.C. § 103-4(a)(11a))
    assert D.is_business_day("nc", date(2026, 3, 25), D.Options(opens=frozenset({"greek_independence"})))
    assert D.add_calendar_days("md", date(2026, 12, 23), 3).due == date(2026, 12, 28)    # § 1-302(c): Sunday, Christmas
    closed = D.Options(closures=frozenset({date(2026, 11, 5)}))
    assert D.add_business_days("va", date(2026, 10, 30), 5, closed).due == date(2026, 11, 10)


# ------------------------------------------------------------------ deadline rules
@pytest.mark.parametrize("text, amount, unit, kind", [
    ("5 working days", 5, "business_days", "within"),
    ("within 10 business days of receipt", 10, "business_days", "within"),
    ("promptly, but in all cases within five working days of receiving a request", 5, "business_days", "within"),
    ("not later than the 15th business day after the date of receiving the written request", 15, "business_days",
     "nth"),
    ("an additional seven work days", 7, "business_days", "extension"),
    ("within 15 days (except Saturdays, Sundays, and legal public holidays)", 15, "business_days", "within"),
    ("Within one hundred twenty days after the effectiveness", 120, "days", "within"),
    ("at the end of the second business day following the denial of inspection", 2, "business_days", "nth"),
    ("within one year of the agency's claim of exemption", 1, "years", "within"),
])
def test_parse_deadline(text, amount, unit, kind):
    r = D.parse_deadline(text)
    assert (r.amount, r.unit, r.kind) == (amount, unit, kind)


def test_parse_deadline_anchor_and_no_number():
    assert D.parse_deadline("within 10 business days of receipt").anchor == "receipt"
    assert D.parse_deadline("Failure to respond within the time permitted for extension") is None
    assert D.rule_from_fields({"amount": 0, "unit": "days"}).kind == "set_by_body"

# deadlines whose quote states no number of days (the lab counts the model's fields for these), and the one whose
# quote states a different figure from the fields (the 14-day cap on an extension vs the 24-day outer limit)
KNOWN_UNPARSED = {("dc", "records", "respond"), ("dc", "records", "respond_extended"),
                  ("dc", "records", "mayor_review"), ("il", "records", "respond_extended"),
                  ("ny", "records", "decide_later")}
KNOWN_DIFFERS = {("ca", "records", "determine_extended")}


def test_every_curated_deadline_parses_and_the_rest_are_reported():
    seen, unparsed, differs = 0, [], []
    for path in sorted(config.CURATED_DIR.glob("*/*.json")):
        spec = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(spec, dict) or "facts" not in spec:
            continue
        for step in spec["facts"].get("steps", []):
            d = step.get("deadline")
            if not d:
                continue
            seen += 1
            key = (path.parent.name, path.stem, step["id"])
            rule = D.rule_from_fields(d)                 # the fields always give a countable rule
            assert rule.unit in D.UNITS and rule.amount >= 0
            check = D.check_deadline(d)
            if check.status == "unparsed":
                unparsed.append((key, (d.get("source") or {}).get("quote")))
            elif check.status == "differs":
                differs.append((key, check.note))
            if rule.amount:                              # and every one of them can be counted
                assert D.count_deadline(D.calendar_for(key[0]), date(2026, 10, 30), rule.amount, rule.unit).due
    assert seen > 0
    report = "\n".join([f"cannot parse {'/'.join(k)}: {q!r}" for k, q in unparsed] +
                       [f"differs {'/'.join(k)}: {n}" for k, n in differs])
    print(f"\n{seen} curated deadlines; {len(unparsed)} quotes state no number, {len(differs)} differ:\n{report}")
    if report:
        warnings.warn(f"lab deadline parsing report:\n{report}", stacklevel=1)
    assert {k for k, _ in unparsed} <= KNOWN_UNPARSED, report
    assert {k for k, _ in differs} <= KNOWN_DIFFERS, report


# ------------------------------------------------------------------ the Virginia records timeline
def _va(*events, **kw):
    return {"lab": I.SCHEMA, "state": "va", "question": "records", "model_id": "va.records", "started": "2026-10-30",
            "events": [{"type": t, "date": d, "note": "kept by the user"} for t, d in events], **kw}


def _dl(tl, step):
    return next(d for d in tl["deadlines"] if d["step"] == step)


def test_virginia_steps_come_from_the_bpmn_with_their_deadlines(con):
    m = I.load_model("va.records", con)
    assert m and m.bpmn
    ids = [s["id"] for s in m.steps]
    assert ids[0] == "submit_request" and ids.index("respond") < ids.index("respond_extended")
    respond = m.step("respond")["deadline"]
    assert (respond["amount"], respond["unit"], respond["anchor_event"]) == (5, "business_days", "request_received")
    assert respond["on_miss"] == ["deemed_denied"] and respond["bpmn_timer"] == "P5D" and "P5D" in respond["unit_note"]
    assert m.step("respond_extended")["deadline"]["extension"]


def test_virginia_records_timeline(con):
    sent = ("request_sent", "2026-10-30")
    tl = I.timeline(_va(sent), today=date(2026, 11, 5), con=con)
    r = _dl(tl, "respond")
    assert (tl["status"], tl["current"]["id"], r["status"], r["due"]) == ("on time", "respond", "on time", "2026-11-09")
    assert [s["date"] for s in r["skipped"]] == ["2026-11-03"]
    assert (r["section"], r["subsection"]) == ("2.2-3704", "B") and "within five working days" in r["quote"]
    assert "2.2-3704(B)" in r["citation"] and r["days_left"] == 4
    assert _dl(tl, "respond_extended")["status"] == "waiting"        # only if the body claims more time

    tl = I.timeline(_va(sent), today=date(2026, 11, 12), con=con)    # no answer by day 5: deemed denial
    assert (tl["status"], tl["current"]["id"], _dl(tl, "respond")["status"]) == ("overdue", "deemed_denied", "overdue")
    assert any("2.2-3713" in g for g in tl["current"]["gaps"])          # the remedy the model does not cover
    assert any(x["kind"] == "implied" and x["date"] == "2026-11-09" for x in tl["timeline"])

    # B.4: the text does not say whether the seven work days run from the notice (Mon 16 Nov) or from the end of
    # the five days (Thu 19 Nov).  The lab counts the body's deadline to the later date, so it never shows the body
    # overdue while it may still be in time, and shows the model's reading beside it.
    ext = ("extension_claimed", "2026-11-04")
    tl = I.timeline(_va(sent, ext), today=date(2026, 11, 12), con=con)
    e = _dl(tl, "respond_extended")
    assert _dl(tl, "respond")["status"] == "met"
    assert (e["status"], e["due"], tl["current"]["id"]) == ("on time", "2026-11-19", "respond_extended")
    assert [a["due"] for a in e["alternatives"]] == ["2026-11-16"]      # counted from the extension notice
    assert any("later date" in n for n in e["notes"])
    tl = I.timeline(_va(sent, ext), today=date(2026, 11, 17), con=con)
    assert _dl(tl, "respond_extended")["status"] == "on time"           # not overdue on the 17th

    tl = I.timeline(_va(sent, ext, ("records_received", "2026-11-13")), today=date(2026, 11, 20), con=con)
    assert (tl["status"], _dl(tl, "respond_extended")["status"], tl["current"]["id"]) == ("on time", "met", "supply")
    assert I.outcome_for(tl, "respond_extended") == {"state": "va", "question": "records", "step": "respond_extended",
                                                     "days_taken": 6, "outcome": "answered_in_time"}
    late = I.timeline(_va(sent, ("records_received", "2026-11-12")), today=date(2026, 11, 20), con=con)
    assert _dl(late, "respond")["status"] == "late"

    ao = I.timeline(_va(("request_sent", "2008-01-17"), ("request_received", "2008-01-18")), today=date(2008, 1, 22),
                    con=con)
    assert _dl(ao, "respond")["due"] == "2008-01-28"                    # counted from receipt, not sending


def test_timeline_never_calls_a_body_overdue_over_a_part_day(con):
    """The re-check's case: received Wed 18 Nov 2026.  The body is not overdue on Fri 27 Nov; it is due Mon 30 Nov
    (the § 1-210(E) reading agrees), and the date for an office that was open all day is shown beside it."""
    tl = I.timeline(_va(("request_sent", "2026-11-18"), started="2026-11-18"), today=date(2026, 11, 27), con=con)
    r = _dl(tl, "respond")
    assert (r["due"], r["status"]) == ("2026-11-30", "on time")
    assert [(a["due"], a["cite"]) for a in r["alternatives"]] == [("2026-11-25", "Va. Code §§ 2.2-3300, 1-210")]
    assert any("part day off" in n for n in r["notes"])
    # in mid-period the § 1-210(E) reading is earlier, and is shown as another reading
    tl = I.timeline(_va(("request_sent", "2026-11-23"), started="2026-11-23"), today=date(2026, 11, 24), con=con)
    r = _dl(tl, "respond")
    assert r["due"] == "2026-12-03"
    assert [(a["due"], "1-210(E)" in a["cite"]) for a in r["alternatives"]] == [("2026-12-02", True)]


def test_a_deadline_of_your_own_takes_the_earlier_virginia_reading():
    """For the requester's own deadline the lab takes the earlier date (as the B.4 rule does): the executive days
    off are not counted as closed, and the default reading is shown beside it."""
    facts = {"actors": [{"id": "you", "kind": "private-party", "name": "Requester"}],
             "steps": [{"id": "file_it", "actor": "you", "action": "File it",
                        "deadline": {"amount": 5, "unit": "business_days", "anchor": "receipt of the request"}}]}
    m = I.Model("va.test", "va", "test", "Test", facts)
    I._attach_steps(m)
    inst = {"state": "va", "question": "test", "events": [{"type": "request_sent", "date": "2026-12-21"}]}
    d = _dl(I.timeline(inst, today=date(2026, 12, 22), model=m), "file_it")
    assert (d["due"], d["status"]) == ("2026-12-29", "open")             # 24 Dec counted for your own deadline
    assert [a["due"] for a in d["alternatives"]] == ["2026-12-30"]      # the default reading
    assert any("Your own deadline" in n for n in d["notes"])
    m.steps[0]["you"] = False                                          # the same step as the body's: the later date
    assert _dl(I.timeline(inst, today=date(2026, 12, 22), model=m), "file_it")["due"] == "2026-12-30"


def test_deemed_denial_starts_the_appeal_clock_in_new_york(con):
    tl = I.timeline({"state": "ny", "question": "records", "events": [{"type": "request_sent", "date": "2026-10-01"}]},
                    today=date(2026, 10, 20), con=con)
    appeal = _dl(tl, "appeal")
    assert _dl(tl, "respond")["due"] == "2026-10-08"
    assert (appeal["anchor_date"], appeal["due"], appeal["status"]) == ("2026-10-08", "2026-11-09", "open")
    assert tl["current"]["id"] == "appeal"              # 30 days end Saturday 7 Nov; GCL § 25-a moves it to Monday


# ------------------------------------------------------------------ the API, on a throwaway app
@pytest.fixture()
def client(con):
    A._recent.clear()                                   # the global rate window, per test
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


GOOD = {"state": "va", "place": None, "question": "records", "step": "respond", "days_taken": 4,
        "outcome": "answered_in_time"}


def test_timeline_endpoint_uses_the_case_options(client):
    """Open days, closures and the reading reach the count (the page sends them; an import keeps them)."""
    def due(options):
        r = client.post("/api/lab/timeline?today=2026-11-05", json=_va(("request_sent", "2026-10-30"), options=options))
        assert r.status_code == 200, r.text
        return _dl(r.json(), "respond")["due"]
    assert due({}) == "2026-11-09"                                      # Election Day skipped
    assert due({"opens": ["election"]}) == "2026-11-06"                 # the office was open on Election Day
    assert due({"closures": ["2026-11-05"]}) == "2026-11-10"
    assert client.post("/api/lab/timeline", json=_va(options={"opens": ["Not A Key!"]})).status_code == 422


def test_outcome_endpoint_stores_six_fields_under_a_random_key_without_rowid(client, con):
    for days in (4, 5, 6):
        assert client.post("/api/lab/outcomes", json={**GOOD, "days_taken": days}).status_code == 201
    assert db.columns(con, "lab_outcomes") == ["k", "state", "place", "question", "step", "days_taken", "outcome"]
    sql = db.scalar(con, "SELECT sql FROM sqlite_master WHERE name='lab_outcomes'")
    assert "WITHOUT ROWID" in sql.upper()
    with pytest.raises(sqlite3.OperationalError):                      # no implicit, sequential row number
        con.execute("SELECT rowid FROM lab_outcomes").fetchall()
    keys = [r["k"] for r in db.rows(con, "SELECT k FROM lab_outcomes")]
    assert len(set(keys)) == 3 and all(re.fullmatch(r"[0-9a-f]{32}", k) for k in keys)
    assert sorted(db.rows(con, "SELECT state, place, question, step, days_taken, outcome FROM lab_outcomes"),
                  key=lambda r: r["days_taken"]) == [{**GOOD, "days_taken": d} for d in (4, 5, 6)]
    r = client.post("/api/lab/outcomes", json=GOOD).json()
    assert r["stored"] == GOOD and "k" not in r["stored"]               # the key is never returned


def test_outcome_table_from_the_first_prototype_is_rebuilt_without_rowid(client, con):
    con.execute("CREATE TABLE lab_outcomes (state TEXT NOT NULL, place TEXT, question TEXT NOT NULL, "
                "step TEXT NOT NULL, days_taken INTEGER NOT NULL, outcome TEXT NOT NULL)")
    con.executemany("INSERT INTO lab_outcomes VALUES (?,?,?,?,?,?)", [("va", None, "records", "respond", d,
                                                                      "answered_in_time") for d in (1, 2)])
    con.commit()
    assert client.post("/api/lab/outcomes", json=GOOD).status_code == 201
    assert "WITHOUT ROWID" in db.scalar(con, "SELECT sql FROM sqlite_master WHERE name='lab_outcomes'").upper()
    assert db.scalar(con, "SELECT count(*) FROM lab_outcomes WHERE length(k) = 32") == 3
    assert not db.scalar(con, "SELECT count(*) FROM sqlite_master WHERE name='lab_outcomes_rowid'")


OLD_TABLE = ("(state TEXT NOT NULL, place TEXT, question TEXT NOT NULL, step TEXT NOT NULL, days_taken INTEGER NOT "
             "NULL, outcome TEXT NOT NULL)")
OLD_ROWS = [("va", None, "records", "respond", d, "answered_in_time") for d in (1, 2)]


def test_outcome_table_migration_is_all_or_nothing(client, con, monkeypatch):
    """An interruption after the old table is dropped (here: the random key fails while the rows are copied)
    rolls the whole migration back: the old table and its rows are intact and nothing is left behind."""
    con.execute(f"CREATE TABLE lab_outcomes {OLD_TABLE}")
    con.executemany("INSERT INTO lab_outcomes VALUES (?,?,?,?,?,?)", OLD_ROWS)
    con.commit()
    real = A.secrets.token_hex

    def boom(n=None):
        raise RuntimeError("interrupted")
    monkeypatch.setattr(A.secrets, "token_hex", boom)
    with pytest.raises(RuntimeError):
        client.post("/api/lab/outcomes", json=GOOD)
    assert "WITHOUT ROWID" not in db.scalar(con, "SELECT sql FROM sqlite_master WHERE name='lab_outcomes'").upper()
    assert db.scalar(con, "SELECT count(*) FROM lab_outcomes") == 2
    assert db.scalar(con, "SELECT count(*) FROM sqlite_master WHERE name LIKE 'lab_outcomes%'") == 1
    monkeypatch.setattr(A.secrets, "token_hex", real)
    assert client.post("/api/lab/outcomes", json=GOOD).status_code == 201
    assert db.scalar(con, "SELECT count(*) FROM lab_outcomes WHERE length(k) = 32") == 3


def test_two_first_reports_cannot_both_rebuild_the_table(con):
    """The migration holds SQLite's write lock from BEGIN IMMEDIATE: a second report waits, then finds the table
    rebuilt and copies nothing twice."""
    con.execute(f"CREATE TABLE lab_outcomes {OLD_TABLE}")
    con.executemany("INSERT INTO lab_outcomes VALUES (?,?,?,?,?,?)", OLD_ROWS)
    con.commit()
    a, b = A._con(), sqlite3.connect(str(config.DB_PATH), timeout=0.1)
    try:
        a.execute("BEGIN IMMEDIATE")
        A._ensure(a)
        with pytest.raises(sqlite3.OperationalError, match="locked"):
            b.execute("BEGIN IMMEDIATE")
        a.commit()
        b.execute("BEGIN IMMEDIATE")
        A._ensure(b)
        b.commit()
    finally:
        a.close()
        b.close()
    assert db.scalar(con, "SELECT count(*) FROM lab_outcomes WHERE length(k) = 32") == 2
    assert "WITHOUT ROWID" in db.scalar(con, "SELECT sql FROM sqlite_master WHERE name='lab_outcomes'").upper()


@pytest.mark.parametrize("with_new_table", [False, True])
def test_outcome_rows_left_by_the_old_non_atomic_migration_are_moved_in(client, con, with_new_table):
    """The first migration renamed the table before copying it; a run interrupted there left lab_outcomes_rowid
    (with its sequential rowids), and sometimes an empty new table.  The next report moves those rows in."""
    con.execute(f"CREATE TABLE lab_outcomes_rowid {OLD_TABLE}")
    con.executemany("INSERT INTO lab_outcomes_rowid VALUES (?,?,?,?,?,?)", OLD_ROWS)
    if with_new_table:
        con.execute(A.OUTCOME_TABLE)
    con.commit()
    assert client.post("/api/lab/outcomes", json=GOOD).status_code == 201
    assert db.scalar(con, "SELECT count(*) FROM lab_outcomes WHERE length(k) = 32") == 3
    assert not db.scalar(con, "SELECT count(*) FROM sqlite_master WHERE name='lab_outcomes_rowid'")


@pytest.mark.parametrize("extra", [{"email": "x@example.org"}, {"date": "2026-11-09"}, {"note": "my request"},
                                   {"name": "A requester"}, {"received": "2026-10-30"}, {"model_id": "va.records"}])
def test_outcome_endpoint_rejects_any_extra_field(client, con, extra):
    r = client.post("/api/lab/outcomes", json={**GOOD, **extra})
    assert r.status_code == 422
    assert list(extra) == [e["loc"][-1] for e in r.json()["detail"]]       # refused for that field, by name
    assert not db.scalar(con, "SELECT count(*) FROM sqlite_master WHERE name='lab_outcomes'")   # nothing written


@pytest.mark.parametrize("query", ["?ref=newsletter", "?email=x%40example.org", "?today=2026-11-09"])
def test_outcome_endpoint_rejects_query_parameters(client, con, query):
    assert client.post(f"/api/lab/outcomes{query}", json=GOOD).status_code == 422
    assert not db.scalar(con, "SELECT count(*) FROM sqlite_master WHERE name='lab_outcomes'")


@pytest.mark.parametrize("headers, code", [({"Origin": "https://elsewhere.example"}, 403),
                                           ({"Sec-Fetch-Site": "cross-site"}, 403), ({"Origin": "null"}, 403),
                                           ({"Origin": "http://testserver", "Sec-Fetch-Site": "same-origin"}, 201)])
def test_outcome_endpoint_takes_reports_only_from_its_own_page(client, headers, code):
    assert client.post("/api/lab/outcomes", json=GOOD, headers=headers).status_code == code


def test_outcome_endpoint_has_a_global_rate_limit(client, monkeypatch):
    monkeypatch.setattr(A, "RATE", (2, 60.0))
    assert [client.post("/api/lab/outcomes", json=GOOD).status_code for _ in range(3)] == [201, 201, 429]


@pytest.mark.parametrize("bad", [{"outcome": "great"}, {"step": "not_a_step"}, {"days_taken": -1},
                                 {"state": "VA"}, {"place": "99999999999999"}])
def test_outcome_endpoint_rejects_bad_values(client, bad):
    assert client.post("/api/lab/outcomes", json={**GOOD, **bad}).status_code == 422


def test_outcome_place_must_be_a_government_in_the_state(client, con):
    db.upsert(con, "governments", [{"gov_id": "47210400100000", "state": "va", "name": "City of Charlottesville",
                                    "kind": "municipality"}])
    con.commit()
    assert client.post("/api/lab/outcomes", json={**GOOD, "place": "47210400100000"}).status_code == 201
    assert client.post("/api/lab/outcomes", json={**GOOD, "state": "md", "place": "47210400100000",
                                                  "step": "decide_application"}).status_code == 422


def test_summary_hides_small_cells_and_small_outcome_counts_and_writes_nothing(client, con):
    assert client.get("/api/lab/outcomes/summary").json()["cells"] == []
    assert not db.scalar(con, "SELECT count(*) FROM sqlite_master WHERE name='lab_outcomes'")   # a GET creates nothing
    for _ in range(3):
        client.post("/api/lab/outcomes", json=GOOD)
    assert client.get("/api/lab/outcomes/summary").json()["cells"] == []          # 3 < k
    for _ in range(7):
        client.post("/api/lab/outcomes", json=GOOD)
    for _ in range(2):
        client.post("/api/lab/outcomes", json={**GOOD, "outcome": "denied"})
    cell, = client.get("/api/lab/outcomes/summary").json()["cells"]
    # ten in time and two denied: a pool of 2 would show that two reports differ, so the ten join it
    assert (cell["n"], cell["outcomes"], cell["other"]) == (12, {}, 12)
    assert "denied" not in json.dumps(cell) and "answered_in_time" not in json.dumps(cell)


def _put(con, counts):
    con.execute("BEGIN IMMEDIATE")
    A._ensure(con)
    con.executemany(A.INSERT, [(f"{i:032x}", "va", None, "records", "respond", 3, outcome)
                               for i, outcome in enumerate(o for o, n in counts.items() for _ in range(n))])
    con.commit()


@pytest.mark.parametrize("counts, outcomes, other", [
    ({"answered_in_time": 10, "denied": 1}, {}, 11),                     # the re-check's case: no "other": 1
    ({"answered_in_time": 10, "denied": 10, "no_answer": 1}, {"denied": 10}, 11),
    ({"answered_in_time": 12, "denied": 10, "no_answer": 6, "withdrawn": 4}, {"answered_in_time": 12,
                                                                          "denied": 10}, 10),
    ({"answered_in_time": 10, "denied": 10}, {"answered_in_time": 10, "denied": 10}, None),
    ({"no_answer": 4, "denied": 3, "withdrawn": 3}, {}, 10),
])
def test_summary_shows_no_group_smaller_than_k(client, con, counts, outcomes, other):
    _put(con, counts)
    cell, = client.get("/api/lab/outcomes/summary").json()["cells"]
    assert (cell["n"], cell["outcomes"], cell.get("other")) == (sum(counts.values()), outcomes, other)
    groups = list(cell["outcomes"].values()) + [cell.get("other", 0), cell["n"] - sum(cell["outcomes"].values())]
    assert all(g == 0 or g >= A.K_MIN for g in groups)


def _snapshot(con):
    tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    return {t: db.scalar(con, f'SELECT count(*) FROM "{t}"') for t in tables}


def test_read_endpoints_store_nothing(client, con):
    db.upsert(con, "governments", [{"gov_id": "47210400100000", "state": "va", "name": "City of Charlottesville",
                                    "kind": "municipality"}])
    con.commit()
    before, version = _snapshot(con), con.execute("PRAGMA data_version").fetchone()[0]
    steps = client.get("/api/lab/models/va.records/steps").json()
    assert [s["id"] for s in steps["steps"]][0] == "submit_request"
    assert client.get("/api/lab/models/xx.nothing/steps").status_code == 404
    r = client.post("/api/lab/timeline?today=2026-11-05", json=_va(("request_sent", "2026-10-30"),
                                                                  place={"gov_id": "1", "name": "kept locally"}))
    assert r.status_code == 200 and _dl(r.json(), "respond")["due"] == "2026-11-09"
    assert "kept locally" not in r.text
    assert client.get("/api/lab/calendars/va?year=2026").json()["dates"][0]["date"] == "2026-01-01"
    assert client.get("/api/lab/states/va/places").status_code == 200
    assert client.get("/api/lab/outcomes/summary").status_code == 200
    assert _snapshot(con) == before                                    # every table, row for row
    assert con.execute("PRAGMA data_version").fetchone()[0] == version  # and no other connection committed


# ------------------------------------------------------------------ one state's places: the place stays in the browser
def test_no_endpoint_takes_a_place_or_a_search(client):
    paths = {r.path for r in router.routes}
    assert "/api/lab/places" not in paths and not any("gov_id" in p or "channels" in p for p in paths)
    assert client.get("/api/lab/places?q=Charlo").status_code == 404
    assert client.get("/api/lab/places/47210400100000/channels").status_code == 404


def test_state_places_bundle_lists_governments_and_office_channels_only(client, con):
    db.upsert(con, "governments", [
        {"gov_id": "47210400100000", "state": "va", "name": "City of Charlottesville", "kind": "municipality",
         "population": 46000, "website": "https://www.charlottesville.example.org"},
        {"gov_id": "47200300000000", "state": "va", "name": "Albemarle County", "kind": "county", "population": 112000},
        {"gov_id": "21200400100000", "state": "md", "name": "City of Baltimore", "kind": "municipality"}])
    cv = {"gov_id": "47210400100000", "state": "va"}
    db.upsert(con, "contacts", [
        {**cv, "question": "records", "kind": "email", "value": "foia@example.org", "label": "FOIA requests",
         "source": "https://example.org/foia"},
        {**cv, "question": "records", "kind": "email", "value": "courtney.smith@example.org", "label": "FOIA"},
        {**cv, "question": "records", "kind": "phone", "value": "434-555-0100", "label": "Clerk's Office main line"},
        {**cv, "question": "records", "kind": "phone", "value": "434-555-0101", "label": "Direct line"},
        {**cv, "question": "records", "kind": "phone", "value": "434-555-0102", "label": "FOIA Officer"},
        {**cv, "question": "records", "kind": "phone", "value": "434-555-0103", "label": None},
        {**cv, "question": "records", "kind": "page", "value": "https://example.org/foia", "label": "FOIA"},
        {**cv, "question": "records", "kind": "office", "value": "Clerk's Office\nAttn: Courtney Smith\nP.O. Box 1",
         "label": "Office"},
        {**cv, "question": "general", "kind": "website", "value": "https://www.charlottesville.example.org"},
        {**cv, "question": "records", "kind": "person", "value": "A person"}])
    con.commit()
    b = client.get("/api/lab/states/VA/places").json()
    assert b["state"] == "va" and b["columns"][:3] == ["gov_id", "name", "kind"]
    assert [g[1] for g in b["governments"]] == ["Albemarle County", "City of Charlottesville"]     # largest first
    got = {(c["kind"], c["value"]) for c in b["channels"]["47210400100000"]}
    # §5.2 rule 5: no check has found the role-shaped mailbox on the office's own page, so it is not shown
    assert got == {("phone", "434-555-0100"), ("page", "https://example.org/foia"),
                   ("office", "Clerk's Office\nP.O. Box 1")}
    assert "courtney" not in json.dumps(b).lower() and "@" not in json.dumps(b)


def _status(con, rows):
    con.execute("CREATE TABLE IF NOT EXISTS contact_status (owner TEXT NOT NULL, question TEXT NOT NULL, kind TEXT "
                "NOT NULL, norm_value TEXT NOT NULL, state TEXT NOT NULL, status TEXT NOT NULL, method TEXT, "
                "verified_at TEXT, checked_at TEXT NOT NULL, updated_at TEXT NOT NULL, "
                "PRIMARY KEY (owner, question, kind, norm_value))")
    con.executemany("INSERT INTO contact_status VALUES (?,?,?,?,?,?,?,?,?,?)", rows)
    con.commit()


def test_state_places_shows_a_mailbox_only_once_found_on_the_office_page(client, con):
    """entities-contacts.md §5.2 rule 5 and §2.2: a role-shaped address is shown only when a check found it on the
    office's own page (status ok, method page-contains) within 90 days.  Labels and sources are checked too."""
    gid = "47210400100000"
    db.upsert(con, "governments", [{"gov_id": gid, "state": "va", "name": "City of Charlottesville",
                                    "kind": "municipality"}])
    mail = {"gov_id": gid, "state": "va", "question": "records", "kind": "email"}
    db.upsert(con, "contacts", [
        {**mail, "value": "foia@example.org", "label": "Jane Doe, FOIA Officer", "source": "site-scan"},
        {**mail, "value": "records@example.org", "label": "Records", "source": "jane-doe"},
        {**mail, "value": "clerk@example.org", "label": "Clerk"},
        {**mail, "value": "info@example.org", "label": "Info"},
        {**mail, "value": "courtney.smith@example.org", "label": "FOIA"}])
    con.commit()
    today = date.today().isoformat()
    old = date.fromordinal(date.today().toordinal() - 200).isoformat()
    _status(con, [(gid, "records", "email", "foia@example.org", "va", "ok", "page-contains", today, today, today),
                  (gid, "records", "email", "records@example.org", "va", "ok", "page-contains", today, today, today),
                  (gid, "records", "email", "clerk@example.org", "va", "ok", "curated", today, today, today),
                  (gid, "records", "email", "info@example.org", "va", "ok", "page-contains", old, today, today),
                  (gid, "records", "email", "courtney.smith@example.org", "va", "ok", "page-contains", today, today,
                   today)])
    shown = client.get("/api/lab/states/va/places").json()["channels"][gid]
    assert [(c["value"], c["label"], c["source"]) for c in sorted(shown, key=lambda c: c["value"])] == [
        ("foia@example.org", None, "site-scan"),             # the label names a person: dropped, the mailbox kept
        ("records@example.org", "Records", None)]            # a source tag that is not a writer's tag: dropped
    assert "jane" not in json.dumps(shown).lower() and "courtney" not in json.dumps(shown).lower()


def test_state_places_drops_person_level_links_labels_and_office_lines(client, con):
    gid = "47210400100000"
    db.upsert(con, "governments", [{"gov_id": gid, "state": "va", "name": "City of Charlottesville",
                                    "kind": "municipality", "website": "https://www.charlottesville.example.org"}])
    cv = {"gov_id": gid, "state": "va", "question": "records"}
    db.upsert(con, "contacts", [
        {**cv, "kind": "page", "value": "https://example.org/staff/jane-doe", "label": "FOIA"},
        {**cv, "kind": "page", "value": "https://example.org/Directory.aspx?EID=12", "label": "Records"},
        {**cv, "kind": "page", "value": "mailto:records@example.org", "label": "Records"},
        {**cv, "kind": "page", "value": "https://example.org/records", "label": "MARY SMITH"},
        {**cv, "kind": "website", "value": "https://example.org/foia-portal", "label": "Official website (Wikidata Q1)"},
        {**cv, "kind": "office", "value": "Jane Doe, Records Custodian\nP.O. Box 2", "label": "Records Office"},
        {**cv, "kind": "office", "value": "FOIA Officer: Jane Doe; 123 Main St", "label": "Jane Doe"},
        {**cv, "kind": "phone", "value": "434-555-0104", "label": "Clerk's Office - MARY SMITH"},
        {**cv, "kind": "phone", "value": "434-555-0105", "label": "Records: JANE DOE"}])
    con.commit()
    shown = client.get("/api/lab/states/va/places").json()["channels"][gid]
    assert sorted((c["kind"], c["value"], c["label"]) for c in shown) == [
        ("office", "FOIA Officer; 123 Main St", None),
        ("office", "Records Custodian\nP.O. Box 2", "Records Office"),
        ("page", "https://example.org/records", None),
        ("website", "https://example.org/foia-portal", "Official website (Wikidata Q1)")]
    text = json.dumps(shown).lower()
    assert "jane" not in text and "mary" not in text and "smith" not in text


def test_lab_page_sends_no_place_or_keystroke_and_keeps_the_case_options():
    js = (ROOT / "dashboard" / "lab.js").read_text(encoding="utf-8")
    calls = re.findall(r"api\(\s*`([^`]*)`", js) + re.findall(r'api\(\s*"([^"]*)"', js)
    assert sorted(set(calls)) == sorted({"/models", "/models/${encodeURIComponent(modelId)}/steps",
                                         "/states/${encodeURIComponent(st)}/places", "/timeline?today=${today()}",
                                         "/outcomes"})
    assert "place" not in re.search(r"function forServer\(c\) \{(.*?)\n\}", js, re.S).group(1).replace(
        "no place", "")
    assert "options: cleanOptions(c.options)" in js                    # sent with the timeline, kept on import
    assert re.search(r"options: cleanOptions\(c\.options\),\s*\n\s*events:", js)


def test_lab_page_text_says_what_happens():
    js = (ROOT / "dashboard" / "lab.js").read_text(encoding="utf-8")
    show = re.search(r"async function showCase\(id\) \{(.*?)\n\}", js, re.S).group(1)
    # the state's list is loaded for every opened case, before and apart from any test of the case's place
    load = next(line for line in show.splitlines() if "placesFor(c.state)" in line)
    assert "place" not in load.replace("placesFor", "") and show.index("placesFor(c.state)") < show.index("c.place")
    assert "counted unless marked open" not in js and "cal.part_day_rule" in js
    assert "client IP" in js                                            # the share card names what the log keeps
    assert "notes that a report arrived, and when." not in js
    # Setup does not link to the lab yet (lab-plan.md §1), so the page must not say it is reached from there
    page = (ROOT / "dashboard" / "lab.html").read_text(encoding="utf-8")
    assert "Reached from" not in page and "does not yet" in page


def test_the_plan_states_how_many_tests_this_file_has():
    """lab-plan.md §0 gives this file's test count; a fresh collection (in a subprocess, so a -k or a node id given
    to this run does not change it) must match."""
    import subprocess
    import sys
    out = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider",
                          str(Path(__file__).resolve())], capture_output=True, text=True, cwd=ROOT, timeout=300)
    n = int(re.search(r"(\d+) tests? collected", out.stdout).group(1))
    plan = (ROOT / "docs" / "design" / "lab-plan.md").read_text(encoding="utf-8")
    assert f"| `tests/test_lab.py` | {n} tests." in plan


# ------------------------------------------------------------------ lexflow.privacy: entities-contacts.md section 5.2
PERSONAL = ["courtney.smith", "jtownsend", "kwaters", "aborowski", "firestone.j", "apressley", "boardman.t",
            "publicover.d", "jmailer", "pia.jones", "cor.devries", "mayor.brown",
            "jtownsend2", "townsendj", "courtney.smith1", "kwaters77",
            # the verifier's: passed the old lab filter on a substring
            "prakash.n", "spratt", "kopenhaver", "j.clerkin"]
OFFICES = [("mpd", "Metropolitan Police Department"), ("CorpHelp", "Florida Division of Corporations"),
           ("corporations", "New York Division of Corporations"),
           ("corps", "Washington Corporations and Charities Division")]
ROLES = ["foia", "records", "mpia", "oig", "publicrecords", "foia.appeals", "cityclerk"]


@pytest.mark.parametrize("local", PERSONAL)
def test_personal_looking_mailboxes_are_refused(local):
    for owner in (None, "City of Baltimore", "Metropolitan Police Department"):
        assert privacy.mailbox_shape(f"{local}@example.org", owner) == "personal"
        assert not privacy.is_office_channel("email", f"{local}@example.org", "FOIA requests", owner)


@pytest.mark.parametrize("local, owner", OFFICES + [(r, None) for r in ROLES])
def test_office_mailboxes_are_role_shaped(local, owner):
    assert privacy.is_office_mailbox(f"{local}@example.org", owner)


def test_mailbox_tokens_initials_and_owner_words():
    assert privacy.local_tokens("CorpHelp") == ["corp", "help"]
    assert privacy.local_tokens("FOIARequests") == ["foia", "requests"]
    assert privacy.local_tokens("records2026") == ["records"]
    assert not privacy.is_office_mailbox("mpd@example.org")                     # initials need the owner's name
    assert privacy.is_office_mailbox("bmza@example.org", "City of Baltimore",
                                     label="Board of Municipal and Zoning Appeals MPIA requests")
    assert privacy.is_office_mailbox("baltimorecity.license@example.org", "Baltimore City")
    assert not privacy.is_office_mailbox("baltimore@example.org", "Baltimore City")   # an owner word alone
    assert not privacy.is_office_mailbox("@example.org") and not privacy.is_office_mailbox("2026@example.org")


def test_initials_never_come_from_a_label_that_is_a_persons_name():
    """§5.2 rule 3 means the office name that starts the label; a label that is a person's name gives no
    initials, whatever its case or what follows it."""
    for label in ("Jane Doe", "Jane Doe, FOIA Officer", "JANE DOE", "Jane Doe Records Division",
                  "FOIA Officer Jane Doe"):
        assert privacy.mailbox_shape("jd@example.org", "City of Baltimore", label) == "personal", label
    assert privacy.mailbox_shape("jdrd@example.org", "City of Baltimore", "Jane Doe Records Division") == "personal"
    assert privacy.mailbox_shape("ms@example.org", "City of Baltimore", "MARY SMITH Records Division") == "personal"
    assert privacy.is_office_mailbox("oig@example.org", "City of Baltimore",
                                     label="Office of the Inspector General PIA requests")
    assert privacy.is_office_mailbox("dhcd@example.org", "City of Baltimore",
                                     label="Department of Housing & Community Development MPIA requests")
    assert privacy.is_office_name("Records Management Division") and not privacy.is_office_name("Jane Doe")


@pytest.mark.parametrize("label, ok", [
    ("Business Licensing Division", True), ("Clerk's Office main line", True), ("Mayor's Office", True),
    ("Zoning: home occupation and mobile food unit permits", True), ("Main line", True),
    ("Department of Licensing and Consumer Protection (DLCP)", True),       # the acronym of the office named
    ("DLCP business licensing", False),                 # an upper-case word is not an acronym on its shape alone
    ("Clerk's Office - MARY SMITH", False), ("Records: JANE DOE", False), ("Records - JD", False),
    ("Phone", False), ("Fax", False), ("Toll free", False),                 # a line, but no office named
    ("Director", False), ("FOIA Officer", False), ("Direct line", False), ("Mobile", False), ("home phone", False),
    ("Records cell", False), ("Courtney Smith", False), ("Courtney Smith, Clerk", False), ("", False), (None, False)])
def test_phone_needs_an_office_label(label, ok):
    assert privacy.is_office_phone(label, "City of Charlottesville") is ok
    assert privacy.is_office_channel("phone", "434-555-0100", label, "City of Charlottesville") is ok


def test_phone_acronym_of_the_owner_is_allowed():
    assert privacy.is_office_phone("DLCP business licensing", "Department of Licensing and Consumer Protection")


@pytest.mark.parametrize("label, kept", [
    ("Public Records Request", True), ("Right to Know", True), ("Transparency Portal", True), ("FOIA", True),
    ("Email on the official website", True), ("Official website (Wikidata Q12345)", True), ("Office", True),
    ("Mail, fax, or in-person FOIA requests", True), ("Mayor's Office", True),
    ("Jane Doe, FOIA Officer", False), ("MARY SMITH", False), ("Smith", False), ("Records: Jane Doe", False),
    ("FOIA appeals to the Mayor", False), ("Direct line", False), ("", False), (None, False)])
def test_labels_of_every_kind_are_checked(label, kept):
    assert privacy.office_label(label, "City of Charlottesville") == (label if kept else None)


@pytest.mark.parametrize("value, kept", [
    ("Records Office\nAttn: Records Custodian\nP.O. Box 1", "Records Office\nAttn: Records Custodian\nP.O. Box 1"),
    ("Records Office\nAttn: Courtney Smith\nP.O. Box 1", "Records Office\nP.O. Box 1"),
    ("c/o Courtney Smith", None),
    # the re-check's cases: a staff name anywhere in the value, not only after Attn or c/o
    ("Jane Doe, Records Custodian\nP.O. Box 2", "Records Custodian\nP.O. Box 2"),
    ("FOIA Officer: Jane Doe; 123 Main St", "FOIA Officer; 123 Main St"),
    ("Jane Doe\nClerk's Office\n123 Main St\nCharlottesville, VA 22902",
     "Clerk's Office\n123 Main St\nCharlottesville, VA 22902"),
    ("Records Office - MARY SMITH, P.O. Box 5", "Records Office, P.O. Box 5"),
    ("123 Main St, Attn: Jane Doe", "123 Main St"),
    ("City Hall (Jane Doe)", "City Hall"),
    ("Records, 434-555-0100 (Jane Doe)", "Records, 434-555-0100"),
    ("Jane Doe 434-555-0100", None),
    ("Jane Doe", None),
    # an office address comes back unchanged
    ("Clerk's Office, 605 E Main St, Room 200, Charlottesville, VA 22902",
     "Clerk's Office, 605 E Main St, Room 200, Charlottesville, VA 22902"),
    ("City Attorney's Office, P.O. Box 911, Charlottesville, VA 22902; fax 434-555-0100",
     "City Attorney's Office, P.O. Box 911, Charlottesville, VA 22902; fax 434-555-0100"),
    ("Charlottesville City Hall, Suite B100, Charlottesville VA 22902",
     "Charlottesville City Hall, Suite B100, Charlottesville VA 22902"),
    # re-check 2: nothing after a number is kept unchecked (a room, box or phone number, or a street address)
    ("City Hall Room 101 Jane Doe, Clerk", "Clerk"),
    ("P.O. Box 911 Attn Jane Doe", "P.O. Box 911"),
    ("P.O. Box 911 Attn: Jane Doe", "P.O. Box 911"),
    ("Room 200 Jane Doe", None),
    ("Phone 434-555-0100 Jane Doe", None),
    ("123 Main St Jane Doe", None),
    ("434-555-0100 Jane Doe", None),
    ("Room 200 Jane Doe St", None),                     # a room number is never a house number with a street
    ("123 Main St Suite 4 Jane", None),
    ("Box911 Doe123", None),                            # letters run into a number are checked as words
    ("Clerk's Office, 123 Main St Jane Doe, Charlottesville, VA 22902", "Clerk's Office, Charlottesville, VA 22902"),
    ("Clerk's Office c/o Jane Doe", "Clerk's Office"),
    ("123 Jane Doe", None),                             # no street type: the words are not a street's name
    ("Clerk's Office - Wayne", "Clerk's Office"),       # not cut into "way" + "ne"
    # ... while an office's own address, lines and hours stay whole
    ("605 E. Main St., Room 200", "605 E. Main St., Room 200"),
    ("Main line 434-555-0100 ext. 12", "Main line 434-555-0100 ext. 12"),
    ("120 7th Street NE, 2nd Floor", "120 7th Street NE, 2nd Floor"),
    ("Suite 200, 123 Main St", "Suite 200, 123 Main St"),
    ("100 Court Square", "100 Court Square"),
    ("Charlottesville City Hall 605 E Main St", "Charlottesville City Hall 605 E Main St"),
    ("401 McIntire Rd, Charlottesville, VA 22902-5481", "401 McIntire Rd, Charlottesville, VA 22902-5481"),
    ("City Hall, in person 8:30 a.m. to 4:30 p.m., Monday through Friday",
     "City Hall, in person 8:30 a.m. to 4:30 p.m., Monday through Friday"),
    ("TTY 711", "TTY 711"),
])
def test_office_values_lose_every_staff_name(value, kept):
    assert privacy.office_value(value, "City of Charlottesville") == kept
    assert privacy.is_office_channel("office", value, None, "City of Charlottesville") is (kept is not None)


@pytest.mark.parametrize("value, shown", [
    ("434-555-0100", True), ("(434) 970-3000 ext. 12", True), ("Main line 434-555-0100", True),
    ("1-800-555-0100", True), ("434.555.0100 x 12", True), ("434-970-3000 option 2", True),
    # the re-check's case: the value is checked, not only the label; a name beside the number refuses all of it
    ("434-555-0100 Jane Doe", False), ("Jane Doe: 434-555-0100", False), ("434-555-0100, Jane Doe", False),
    ("434-555-0100 (Jane Doe)", False), ("Jane Doe", False), ("", False), (None, False)])
def test_phone_values_are_checked_not_only_labels(value, shown):
    owner, label = "City of Charlottesville", "Clerk's Office main line"
    assert privacy.office_phone_value(value, owner) == (value if shown else None)
    assert privacy.is_office_channel("phone", value, label, owner) is shown


def test_two_letter_initials_never_count():
    """The re-check's judgement call, taken the conservative way: two letters are also a person's initials, so no
    initialism of fewer than three letters makes a mailbox role-shaped or a phone label an office's."""
    assert privacy.MIN_INITIALS == 3
    assert privacy.mailbox_shape("cc@example.org", "City of Charlottesville") == "personal"
    assert privacy.mailbox_shape("va@example.org", "Village of Arcanum") == "personal"
    assert privacy.mailbox_shape("lg@example.org", "City of Linn Grove") == "personal"
    assert not privacy.is_office_phone("Clerk's Office - CC", "City of Charlottesville")
    assert not privacy.is_office_phone("DC Department of Buildings", "City of Washington DC")
    assert privacy.is_office_mailbox("coc.clerk@example.org", "City of Charlottesville")      # three letters count
    assert privacy.is_office_mailbox("mpd@example.org", "Metropolitan Police Department")
    assert privacy.is_office_mailbox("hr@example.org")                                       # a role word, not initials


@pytest.mark.parametrize("url", [
    "https://example.org/contact?to=jane.doe%40example.org", "https://example.org/%7Ejdoe/",
    "https://example.org/%2540jdoe", "https://example.org/a&#64;b", "https://example.org/%73taff/jd",
    "https://example.org/our%20staff/x", "vbscript:msgbox(1)", "file:///etc/passwd", "FILE:///C:/x",
    "data:text/html,hi", "ftp://example.org/records", "java\tscript:alert(1)", " JavaScript:alert(1)",
    "tel:4345550100"])
def test_office_url_refuses_encoded_addresses_and_other_schemes(url):
    assert not privacy.is_office_url(url)
    assert not privacy.is_office_channel("page", url)
    assert privacy.office_source(url) is None


def test_office_url_keeps_plain_office_links():
    for url in ("https://example.org/foia", "http://example.org/foia%20requests", "www.example.org/foia",
                "https://example.org/government/public-records?lang=en"):
        assert privacy.is_office_url(url), url


def test_state_places_checks_phone_values_and_encoded_links(client, con):
    gid = "47210400100000"
    db.upsert(con, "governments", [{"gov_id": gid, "state": "va", "name": "City of Charlottesville",
                                    "kind": "municipality"}])
    cv = {"gov_id": gid, "state": "va", "question": "records"}
    db.upsert(con, "contacts", [
        {**cv, "kind": "phone", "value": "434-555-0100", "label": "Clerk's Office main line"},
        {**cv, "kind": "phone", "value": "434-555-0106 Jane Doe", "label": "Clerk's Office main line"},
        {**cv, "kind": "phone", "value": "434-555-0107", "label": "Clerk's Office - CC"},
        {**cv, "kind": "page", "value": "https://example.org/contact?to=jane.doe%40example.org", "label": "FOIA"},
        {**cv, "kind": "page", "value": "https://example.org/%7Ejdoe/", "label": "FOIA"},
        {**cv, "kind": "page", "value": "vbscript:msgbox(1)", "label": "FOIA"},
        {**cv, "kind": "office", "value": "City Hall Room 101 Jane Doe, Clerk", "label": "Office"},
        {**cv, "kind": "office", "value": "P.O. Box 911 Attn Jane Doe", "label": "Office"}])
    con.commit()
    shown = client.get("/api/lab/states/va/places").json()["channels"][gid]
    assert sorted((c["kind"], c["value"]) for c in shown) == [
        ("office", "Clerk"), ("office", "P.O. Box 911"), ("phone", "434-555-0100")]
    text = json.dumps(shown).lower()
    assert "jane" not in text and "jdoe" not in text and "0106" not in text and "0107" not in text


def test_links_and_sources_and_other_kinds():
    assert privacy.is_office_channel("website", "https://example.org")
    assert privacy.is_office_url("https://example.org/government/foia-requests")
    for url in ("https://example.org/staff/jane-doe", "https://example.org/Directory.aspx?EID=12",
                "mailto:records@example.org", "https://example.org/~jdoe/", "https://example.org/people/jd",
                "javascript:alert(1)", ""):
        assert not privacy.is_office_url(url), url
        assert not privacy.is_office_channel("page", url)
    assert [privacy.office_source(s) for s in ("census-gus-2022", "site-scan", "wikidata", "jane-doe",
                                               "https://example.org/foia", "https://example.org/staff/jd", None)] == \
        ["census-gus-2022", "site-scan", "wikidata", None, "https://example.org/foia", None, None]
    assert not privacy.is_office_channel("person", "A person")
