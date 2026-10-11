"""Business-day and calendar-day arithmetic for statutory deadlines: per-state holiday tables, the counting rules,
and a parser for the deadline rules that the curated models state ("5 working days", "within 10 business days of
receipt", "not later than the 15th business day after ...").

Sources.  Each calendar is the holiday list in one jurisdiction's own statute, with that statute's rule for a
holiday that falls on a weekend and the jurisdiction's rule for a period whose last day is not a business day.
Statute text was read on 10 October 2026 from lexflow's local open-us-law copy (v2026.09.1) through
``lexflow.municipal.statutes.section_texts``; the URL next to each citation is the official publisher's page.  A
comment says so where a section could not be read.  Federal holidays (5 U.S.C. § 6103) form the ``us`` calendar,
and each state table repeats a federal holiday only where the state's statute lists it, because the lists differ:
Texas, for example, counts Columbus Day as a business day (Gov't Code §§ 552.0031, 662.003).

Counting, as the time-computation statutes cited below state it:

* the day of the triggering event is not counted;
* "N business days" ends on the Nth business day after that day (a business day is a weekday that is not a
  holiday in the table and not a day the office was closed);
* "N days" ends on the Nth calendar day after it; when that day is a weekend or holiday, the jurisdiction's
  roll-forward rule (if any) moves it.

The tables apply each statute's current text to every year.  Earlier versions (Virginia's Lee-Jackson Day, repealed
in 2020, for example) are not modelled, so dates before 2021 are approximate.  Two tables also carry a published
schedule for named years, read on 10 October 2026 from the official pages: California's court holidays (Cal. Rules
of Court, rule 1.11, and the Judicial Council's 2026 and 2027 schedules) and Virginia's executive time off (the
Department of Human Resource Management's 2026 and 2027 Pay and Holiday Calendars).  Virginia's part days off are
not counted as business days by default, the conservative choice for a body's deadline; another reading counts
them (see the Virginia table).  Days a Governor closes offices in a later year are not known in advance and must be
recorded as closures.  Nothing here is legal advice: a body's own closures, a court order or an agreement can
change a date.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from functools import lru_cache
from typing import Callable, Iterable

MON, TUE, WED, THU, FRI, SAT, SUN = range(7)
_WD = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
_MONTH = ("", "January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December")
_NTH = {1: "first", 2: "second", 3: "third", 4: "fourth", 5: "fifth", -1: "last"}

UNITS = ("hours", "days", "business_days", "weeks", "months", "years")      # lexflow/extract/schema.py FDeadline


# ============================================================================ date rules
@dataclass(frozen=True)
class When:
    """How a statute fixes a holiday's date: ``on(year)`` gives that year's date, or None when it does not fall."""
    text: str
    fn: Callable[[int], "date | None"] = field(compare=False, repr=False)

    def on(self, year: int) -> date | None:
        return self.fn(year)


def nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    """The nth (1-5) or last (-1) given weekday of a month."""
    if n == -1:
        d = date(year + (month == 12), month % 12 + 1, 1) - timedelta(days=1)
        return d - timedelta(days=(d.weekday() - weekday) % 7)
    d = date(year, month, 1)
    return d + timedelta(days=(weekday - d.weekday()) % 7 + 7 * (n - 1))


def easter(year: int) -> date:
    """Western Easter Sunday (the anonymous Gregorian algorithm, as given by Meeus)."""
    a, b, c = year % 19, year // 100, year % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l_ = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l_) // 451
    return date(year, (h + l_ - 7 * m + 114) // 31, (h + l_ - 7 * m + 114) % 31 + 1)


def election_day(year: int) -> date:
    """The Tuesday after the first Monday in November."""
    return nth_weekday(year, 11, MON, 1) + timedelta(days=1)


def thanksgiving(year: int) -> date:
    return nth_weekday(year, 11, THU, 4)


# The Hebrew calendar, for the days Texas (optional holidays) and North Carolina name: arithmetic from Reingold and
# Dershowitz, Calendrical Calculations; checked against the published dates of Rosh Hashanah for 2020-2030.
_HEBREW_EPOCH = -1373427            # fixed (proleptic Gregorian ordinal) date of 1 Tishri, year 1


def _hebrew_elapsed(y: int) -> int:
    months = (235 * y - 234) // 19
    days = 29 * months + (12084 + 13753 * months) // 25920
    return days + 1 if (3 * (days + 1)) % 7 < 3 else days


def _hebrew_new_year(y: int) -> int:
    ny0, ny1, ny2 = _hebrew_elapsed(y - 1), _hebrew_elapsed(y), _hebrew_elapsed(y + 1)
    correction = 2 if ny2 - ny1 == 356 else 1 if ny1 - ny0 == 382 else 0
    return _HEBREW_EPOCH + ny1 + correction


def rosh_hashanah(year: int) -> date:
    """1 Tishri falling in the given Gregorian year (the daytime day; the observance begins the evening before)."""
    return date.fromordinal(_hebrew_new_year(year + 3761))


def fixed(month: int, day: int) -> When:
    return When(f"{_MONTH[month]} {day}", lambda y: date(y, month, day))


def on_date(d: date) -> When:
    """One day of one year (an executive closure from a published calendar)."""
    return When(f"{d.day} {_MONTH[d.month]} {d.year} only", lambda y: d if y == d.year else None)


def nth(n: int, weekday: int, month: int) -> When:
    return When(f"the {_NTH[n]} {_WD[weekday]} in {_MONTH[month]}", lambda y: nth_weekday(y, month, weekday, n))


def from_easter(days: int, text: str) -> When:
    return When(text, lambda y: easter(y) + timedelta(days=days))


DAY_AFTER_THANKSGIVING = When("the Friday after the fourth Thursday in November",
                              lambda y: thanksgiving(y) + timedelta(days=1))


def election(every: str = "year") -> When:
    """Election Day every year, or only in even-numbered years (statewide general elections)."""
    if every == "even":
        return When("the Tuesday after the first Monday in November, in even-numbered years",
                    lambda y: election_day(y) if y % 2 == 0 else None)
    return When("the Tuesday after the first Monday in November", election_day)


def from_rosh_hashanah(days: int, text: str) -> When:
    return When(text, lambda y: rosh_hashanah(y) + timedelta(days=days))


def _inauguration(y: int) -> date | None:
    if y < 1981 or (y - 1981) % 4:
        return None
    d = date(y, 1, 20)
    return d + timedelta(days=1) if d.weekday() == SUN else d


INAUGURATION = When("January 20 of every fourth year from 1981 (the next day when it is a Sunday)", _inauguration)


# ============================================================================ holidays and calendars
SHIFT_BOTH = "sat-fri sun-mon"      # Saturday holiday observed the Friday before, Sunday holiday the Monday after
SHIFT_SUN = "sun-mon"
SHIFT_SAT = "sat-fri"
SHIFT_NONE = "none"

ROLL_NEXT_BUSINESS = "next business day"
ROLL_NOT_SUNDAY_HOLIDAY = "next day that is not a Sunday or legal holiday"
ROLL_NONE = "none stated"
ROLL_UNKNOWN = "not checked"


@dataclass(frozen=True)
class Holiday:
    key: str
    name: str
    when: When
    cite: str
    shift: str = SHIFT_NONE
    optional: bool = False      # counted only when the body observes it (Tex. Gov't Code § 552.0031(c))
    legal: bool = True          # False: closes the office but is not a "legal holiday" for rolling a period forward
    since: int | None = None    # first year the statute applies it
    # part of a day off (Virginia's "4 hours additional holiday time"): whether it counts as a business day depends
    # on the reading (Calendar.part_day_closed, Variant.part_day_open, Variant.part_day_extends)
    part_day: bool = False
    # (year, observed date, source): a published schedule that moves the day in one year (California's 2027 court
    # calendar observes Farmworkers Day, Wednesday 31 March, on Friday 9 April)
    moved: tuple[tuple[int, date, str], ...] = ()

    def dates(self, year: int, shift: str | None = None) -> tuple[date | None, date | None]:
        """(statutory date, observed date) in a year."""
        if self.since and year < self.since:
            return None, None
        d = self.when.on(year)
        if d is None:
            return None, None
        for y, observed, _ in self.moved:
            if y == year:
                return d, observed
        s = self.shift if shift is None else shift
        if d.weekday() == SAT and "sat-fri" in s:
            return d, d - timedelta(days=1)
        if d.weekday() == SUN and "sun-mon" in s:
            return d, d + timedelta(days=1)
        return d, d


@dataclass(frozen=True)
class Variant:
    """Another reading of the same calendar, shown next to the default when it gives a different date."""
    key: str
    text: str
    cite: str
    add: tuple[Holiday, ...] = ()
    remove: tuple[str, ...] = ()
    observe_optional: bool = False
    shift: str | None = None
    part_day_open: bool = False         # a part day off is a business day in this reading
    part_day_extends: bool = False      # ... but a period whose last day is one runs to the next business day


@dataclass(frozen=True)
class Calendar:
    key: str
    name: str
    holidays: tuple[Holiday, ...]
    business_day: str           # what a business or working day is, and where that comes from
    first_day: str              # the source for not counting the day of the event
    roll: str
    roll_source: str
    # (at most n days, Saturdays excluded too): in periods that short, intermediate non-business days are skipped
    short_period: tuple[int, bool] | None = None
    variants: tuple[Variant, ...] = ()
    closures: str = ""          # where days the office is closed come from
    notes: tuple[str, ...] = ()
    sources: tuple[tuple[str, str], ...] = ()
    shift_source: str = ""      # added to the citation of a day observed away from its date (CA: rule 1.11)
    # by default a part day off is not a business day (the office may have closed for part of it), so a body's
    # deadline is never counted short; a variant with part_day_open counts it
    part_day_closed: bool = False
    part_day_rule: str = ""     # how the table treats a part day off, in words (shown next to each one)
    # the reading used by default for a deadline of the requester's own: the earlier date (the default reading is
    # then shown beside it), as the B.4 rule in instances.py does for an unsettled anchor
    you_variant: str | None = None
    default_reading: str = ""   # the default reading in words, when it is shown as another reading

    def variant(self, key: str | None) -> Variant | None:
        return next((v for v in self.variants if v.key == key), None)


# --------------------------------------------------------------------------- federal: 5 U.S.C. § 6103
# 5 U.S.C. § 6103(a) lists the eleven legal public holidays (Juneteenth added by Pub. L. 117-17, 2021); Executive
# Order 11582 and § 6103(b) move a Saturday holiday to Friday and a Sunday holiday to Monday for federal offices.
# https://www.law.cornell.edu/uscode/text/5/6103
# observed dates: https://www.opm.gov/policy-data-oversight/pay-leave/federal-holidays/
_US = "5 U.S.C. § 6103(a)"
FEDERAL = {
    "new_year": Holiday("new_year", "New Year's Day", fixed(1, 1), _US, SHIFT_BOTH),
    "mlk": Holiday("mlk", "Birthday of Martin Luther King, Jr.", nth(3, MON, 1), _US, SHIFT_BOTH),
    "washington": Holiday("washington", "Washington's Birthday", nth(3, MON, 2), _US, SHIFT_BOTH),
    "memorial": Holiday("memorial", "Memorial Day", nth(-1, MON, 5), _US, SHIFT_BOTH),
    "juneteenth": Holiday("juneteenth", "Juneteenth National Independence Day", fixed(6, 19), _US, SHIFT_BOTH,
                          since=2021),
    "independence": Holiday("independence", "Independence Day", fixed(7, 4), _US, SHIFT_BOTH),
    "labor": Holiday("labor", "Labor Day", nth(1, MON, 9), _US, SHIFT_BOTH),
    "columbus": Holiday("columbus", "Columbus Day", nth(2, MON, 10), _US, SHIFT_BOTH),
    "veterans": Holiday("veterans", "Veterans Day", fixed(11, 11), _US, SHIFT_BOTH),
    "thanksgiving": Holiday("thanksgiving", "Thanksgiving Day", nth(4, THU, 11), _US, SHIFT_BOTH),
    "christmas": Holiday("christmas", "Christmas Day", fixed(12, 25), _US, SHIFT_BOTH),
}


def _fed(key: str, cite: str, shift: str, name: str | None = None, **kw) -> Holiday:
    """A federal holiday as a state statute lists it: the same rule, the state's own name, citation and shift."""
    f = FEDERAL[key]
    return Holiday(key, name or f.name, kw.pop("when", f.when), cite, shift, **kw)


def _all_fed(cite: str, shift: str, names: dict[str, str] | None = None, skip: Iterable[str] = ()) -> list[Holiday]:
    names = names or {}
    return [_fed(k, cite, shift, names.get(k)) for k in FEDERAL if k not in set(skip)]


US = Calendar(
    "us", "Federal", tuple(FEDERAL.values()),
    business_day="A weekday that is not a legal public holiday (5 U.S.C. § 552(a)(6)(A) counts 20 days "
                 "'excepting Saturdays, Sundays, and legal public holidays').",
    first_day="FRCP 6(a)(1)(A) excludes the day of the event (court deadlines)",
    roll=ROLL_NEXT_BUSINESS, roll_source="FRCP 6(a)(1)(C) (court deadlines; agency deadlines are counted in days "
                                         "that exclude weekends and holidays)",
    closures="Days the office is closed by executive order are added by the user",
    sources=(("5 U.S.C. § 6103", "https://www.law.cornell.edu/uscode/text/5/6103"),
             ("OPM federal holidays", "https://www.opm.gov/policy-data-oversight/pay-leave/federal-holidays/"),
             ("FRCP 6", "https://www.law.cornell.edu/rules/frcp/rule_6")))

# --------------------------------------------------------------------------- Virginia
# Va. Code § 2.2-3300, https://law.lis.virginia.gov/vacode/2.2-3300/ : the eleven federal days (Washington's Birthday
# as "George Washington Day", the second Monday in October as "Columbus Day and Yorktown Victory Day"), plus "The
# Tuesday following the first Monday in November — Election Day" and Thanksgiving "and the Friday next following".
# "Whenever any of such days falls on Saturday, the Friday next preceding such day, or whenever any of such days falls
# on Sunday, the Monday next following such day ... shall be a legal holiday".
_VA = "Va. Code § 2.2-3300"
# Executive time off, from the Department of Human Resource Management's Pay and Holiday Calendars
# (https://www.dhrm.virginia.gov/payandholidaycalendar, read 10 October 2026).  2026: "8 hours additional holiday
# time" on Thursday 24 December and "4 hours" on Wednesday 25 November.  2027: "4 hours" on Wednesday 24 November and
# Thursday 23 December (Christmas, a Saturday, is observed on Friday 24 December and New Year's Day 2028 on Friday 31
# December, both already in the table).  A full day off is read as the Governor closing state government, which
# § 1-210(F) makes a legal holiday and § 2.2-3300's last paragraph ("any day so appointed by the Governor") makes a
# legal holiday for all business.  A part day is the unsettled case.  The DHRM calendar grants time off without
# saying that offices close, but § 1-210(E) covers "any day or part of a day on which the state or local government
# office ... is closed".  The conservative choice for a body's deadline is the later date, so by default a part day
# is not counted as a working day (and a period that ends on it runs on).  The § 1-210(E) reading, shown beside it
# when it gives a different date, counts the part day and moves only a period that ends on it.  A body that was open
# all day is marked open for the case; for a deadline of the requester's own the lab takes the earlier date, from
# the reading without the executive days (``you_variant``), and shows the default beside it.
_VA_CLOSING = "Va. Code §§ 2.2-3300, 1-210(F); DHRM {year} Pay and Holiday Calendar"
_VA_PART = "DHRM {year} Pay and Holiday Calendar; Va. Code § 1-210(E)"
VA_EXECUTIVE = (
    Holiday("va_closing_2026_12_24", "Christmas Eve: 8 hours additional holiday time (a full-day closing of state "
            "offices)", on_date(date(2026, 12, 24)), _VA_CLOSING.format(year=2026)),
    Holiday("va_part_2026_11_25", "4 hours additional holiday time for state employees", on_date(date(2026, 11, 25)),
            _VA_PART.format(year=2026), part_day=True),
    Holiday("va_part_2027_11_24", "4 hours additional holiday time for state employees", on_date(date(2027, 11, 24)),
            _VA_PART.format(year=2027), part_day=True),
    Holiday("va_part_2027_12_23", "4 hours additional holiday time for state employees", on_date(date(2027, 12, 23)),
            _VA_PART.format(year=2027), part_day=True),
)
VA = Calendar(
    "va", "Virginia",
    tuple(_all_fed(_VA, SHIFT_BOTH, {"washington": "George Washington Day",
                                     "columbus": "Columbus Day and Yorktown Victory Day", "juneteenth": "Juneteenth"})
          + [Holiday("election", "Election Day", election(), _VA, SHIFT_BOTH),
             Holiday("thanksgiving_friday", "Thanksgiving (the Friday next following)", DAY_AFTER_THANKSGIVING, _VA,
                     SHIFT_BOTH)]
          + list(VA_EXECUTIVE)),
    business_day="'Working days' is not defined in Va. Code § 2.2-3704. The Virginia FOIA Council counts by "
                 "leaving out Saturdays, Sundays and legal holidays, with day 1 the first working day after the day "
                 "the request was received (advisory opinion AO-02-08, 2008). The Governor's full-day closings in "
                 "DHRM's 2026 and 2027 calendars are left out too, and so, by default, are its part days off (4 "
                 "hours): the office may have closed for part of the day (§ 1-210(E)), and the lab does not call a "
                 "body overdue while it may still be in time. The § 1-210(E) reading, which counts a part day and "
                 "moves only a period that ends on one, is shown beside the date when it differs.",
    first_day="Va. Code § 1-210(A): the day of the event is not counted",
    roll=ROLL_NEXT_BUSINESS,
    roll_source="Va. Code § 1-210(E): an act due on a Saturday, Sunday, legal holiday or a day or part of a day the "
                "office is closed may be done on the next business day",
    variants=(Variant("part_days_1210e", "A part day off counts as a working day, and a period that ends on one runs "
                                         "to the next business day (§ 1-210(E))", "Va. Code § 1-210(E)",
                      part_day_open=True, part_day_extends=True),
              Variant("executive_open", "The office was open on the executive days off in DHRM's calendar (the "
                                        "Governor's closing and the part days)", "Va. Code §§ 2.2-3300, 1-210",
                      remove=tuple(h.key for h in VA_EXECUTIVE))),
    closures="Va. Code § 1-210(F): a day the Governor closes state government is a legal holiday; § 1-210(E) also "
             "covers days the local office is closed",
    notes=("Days appointed by the Governor or the President are legal holidays (§ 2.2-3300). The table has the "
           "full-day closing of 24 December 2026 and the part days off in DHRM's 2026 and 2027 calendars; record any "
           "other as an office closure.",
           "The executive days off are set for state employees. A local body that stayed open on one can mark it "
           "open for the case, and the date it would give is shown as another reading.",
           "A deadline of the requester's own is counted without the executive days off (the earlier date), with "
           "the default reading beside it."),
    part_day_closed=True,
    part_day_rule="part day off: not counted as a working day by default; the § 1-210(E) reading counts it and "
                  "moves only a period that ends on it; marked open, it is an ordinary working day",
    you_variant="executive_open",
    default_reading="The executive days off in DHRM's calendar, part days included, are days the office was closed "
                    "(the default for a body's deadline)",
    sources=(("Va. Code § 2.2-3300", "https://law.lis.virginia.gov/vacode/2.2-3300/"),
             ("Va. Code § 1-210", "https://law.lis.virginia.gov/vacode/1-210/"),
             ("Virginia FOIA Council AO-02-08", "https://foiacouncil.dls.virginia.gov/ops/08/AO_02_08.htm"),
             ("DHRM Pay and Holiday Calendar (2026, 2027)", "https://www.dhrm.virginia.gov/payandholidaycalendar")))

# --------------------------------------------------------------------------- District of Columbia
# D.C. Code § 1-612.02(a), https://code.dccouncil.gov/us/dc/council/code/sections/1-612.02 : the federal days (the
# second Monday in October as "Indigenous Peoples' Day") and "(11) Beginning in the year 2007, District of Columbia
# Emancipation Day, April 16th".  § 28-2701, https://code.dccouncil.gov/us/dc/council/code/sections/28-2701 , lists
# the same days plus "the day of the inauguration of the President, in every fourth year" as "holidays in the
# District for all purposes"; "When a day set apart as a legal holiday, other than the day of the inauguration of the
# President, falls on a Saturday, the next preceding day is a holiday. When ... on a Sunday, the next succeeding day".
_DC = "D.C. Code §§ 1-612.02(a), 28-2701"
DC = Calendar(
    "dc", "District of Columbia",
    tuple(_all_fed(_DC, SHIFT_BOTH, {"mlk": "Dr. Martin Luther King, Jr.'s Birthday",
                                     "columbus": "Indigenous Peoples' Day"})
          + [Holiday("emancipation", "District of Columbia Emancipation Day", fixed(4, 16), _DC, SHIFT_BOTH,
                     since=2007),
             Holiday("inauguration", "Inauguration Day", INAUGURATION, "D.C. Code §§ 1-612.02(c), 28-2701")]),
    business_day="D.C. Code § 2-532(c) counts the response time in days 'except Saturdays, Sundays, and legal "
                 "public holidays'.",
    first_day="(not checked for D.C.; the day of receipt is not counted, as in the other tables)",
    roll=ROLL_UNKNOWN, roll_source="No D.C. time-computation statute was read",
    closures="D.C. Code § 1-612.02(b), (d): other days the Mayor designates or closes agencies",
    sources=(("D.C. Code § 1-612.02", "https://code.dccouncil.gov/us/dc/council/code/sections/1-612.02"),
             ("D.C. Code § 28-2701", "https://code.dccouncil.gov/us/dc/council/code/sections/28-2701"),
             ("D.C. Code § 2-532", "https://code.dccouncil.gov/us/dc/council/code/sections/2-532")))

# --------------------------------------------------------------------------- Maryland
# Md. Code, General Provisions § 1-111(a),
# https://mgaleg.maryland.gov/mgawebsite/Laws/StatuteText?article=ggp&section=1-111&enactments=false : "legal holiday"
# in the Code.  Martin Luther King Jr.'s birthday, Memorial Day and Columbus Day fall on "the day designated by the
# United States Congress", that is the federal Monday.  "(b) ... a legal holiday shall be observed on: (1) the date
# specified ...; or (2) if that date falls on a Sunday, on the next Monday".  State Personnel and Pensions § 9-201,
# https://mgaleg.maryland.gov/mgawebsite/Laws/StatuteText?article=gsp&section=9-201&enactments=false , is a shorter
# "employee holiday" list (no Lincoln's birthday, Maryland Day, Good Friday or Defenders' Day): the variant below.
_MD = "Md. Code, Gen. Prov. § 1-111(a)"
_MD_ONLY = ("lincoln", "maryland_day", "good_friday", "defenders")
MD = Calendar(
    "md", "Maryland",
    (_fed("new_year", _MD, SHIFT_SUN),
     _fed("mlk", _MD, SHIFT_SUN, "Dr. Martin Luther King, Jr.'s birthday (day designated by Congress)"),
     Holiday("lincoln", "Lincoln's birthday", fixed(2, 12), _MD, SHIFT_SUN),
     _fed("washington", _MD, SHIFT_SUN),
     Holiday("maryland_day", "Maryland Day", fixed(3, 25), _MD, SHIFT_SUN),
     Holiday("good_friday", "Good Friday", from_easter(-2, "Good Friday"), _MD, SHIFT_SUN),
     _fed("memorial", _MD, SHIFT_SUN, "Memorial Day (day designated by Congress)"),
     _fed("juneteenth", _MD, SHIFT_SUN),
     _fed("independence", _MD, SHIFT_SUN),
     _fed("labor", _MD, SHIFT_SUN),
     Holiday("defenders", "Defenders' Day", fixed(9, 12), _MD, SHIFT_SUN),
     _fed("columbus", _MD, SHIFT_SUN, "Columbus Day (day designated by Congress)"),
     _fed("veterans", _MD, SHIFT_SUN, "Veterans' Day"),
     _fed("thanksgiving", _MD, SHIFT_SUN),
     Holiday("thanksgiving_friday", "American Indian Heritage Day", DAY_AFTER_THANKSGIVING, _MD, SHIFT_SUN),
     _fed("christmas", _MD, SHIFT_SUN),
     Holiday("election", "Statewide general election day", election("even"), _MD, SHIFT_SUN)),
    business_day="'Working days' is not defined in the Public Information Act (Gen. Prov. § 4-101). This table uses "
                 "the Code's 'legal holiday' (§ 1-111); the employee-holiday list (SPP § 9-201) is shown as a "
                 "variant when it gives a different date. Which one applies is an open question.",
    first_day="Md. Code, Gen. Prov. § 1-302(a): the day of the event is not included",
    roll=ROLL_NOT_SUNDAY_HOLIDAY,
    roll_source="Md. Code, Gen. Prov. § 1-302(b)(1): a last day on a Sunday or legal holiday runs to the next day "
                "that is not a Sunday or legal holiday",
    short_period=(7, False),
    variants=(Variant("employee", "Maryland employee holidays (SPP § 9-201) instead of legal holidays (§ 1-111)",
                      "Md. Code, State Pers. & Pens. § 9-201", remove=_MD_ONLY),),
    closures="Days the President or the Governor designates for general cessation of business (§ 1-111(a)(18))",
    notes=("Gen. Prov. § 1-302(c): in periods of 7 days or less, intermediate Sundays and legal holidays are not "
           "counted.",),
    sources=(("Md. Code, Gen. Prov. § 1-111",
              "https://mgaleg.maryland.gov/mgawebsite/Laws/StatuteText?article=ggp&section=1-111&enactments=false"),
             ("Md. Code, Gen. Prov. § 1-302",
              "https://mgaleg.maryland.gov/mgawebsite/Laws/StatuteText?article=ggp&section=1-302&enactments=false"),
             ("Md. Code, State Pers. & Pens. § 9-201",
              "https://mgaleg.maryland.gov/mgawebsite/Laws/StatuteText?article=gsp&section=9-201&enactments=false")))

# --------------------------------------------------------------------------- Texas
# Tex. Gov't Code § 552.0031, https://tcss.legis.texas.gov/resources/GV/htm/GV.552.htm#552.0031 : "business day"
# means a day other than "(1) a Saturday or Sunday; (2) a national holiday under Section 662.003(a); or (3) a state
# holiday under Section 662.003(b)".  § 662.003, https://tcss.legis.texas.gov/resources/GV/htm/GV.662.htm#662.003 :
# (a) nine national holidays (no Columbus Day; June 19 is the state's "Emancipation Day in Texas"), (b) eight state
# holidays, (c) optional holidays: "Rosh Hashanah, Yom Kippur, or Good Friday", not business days only "if the officer
# for public information ... observes the optional holiday" (§ 552.0031(c)).  § 552.0031(e): the Friday before or
# Monday after a weekend holiday is not a business day only if the body observes it then (the variant below).
# § 552.0031(f): a body may designate up to 10 nonbusiness days a year (record them as closures).
_TXA, _TXB, _TXC = "Tex. Gov't Code § 662.003(a)", "Tex. Gov't Code § 662.003(b)", "Tex. Gov't Code § 662.003(c)"
TX = Calendar(
    "tx", "Texas",
    (_fed("new_year", _TXA, SHIFT_NONE), _fed("mlk", _TXA, SHIFT_NONE, "Martin Luther King, Jr., Day"),
     _fed("washington", _TXA, SHIFT_NONE, "Presidents' Day"), _fed("memorial", _TXA, SHIFT_NONE),
     _fed("independence", _TXA, SHIFT_NONE), _fed("labor", _TXA, SHIFT_NONE), _fed("veterans", _TXA, SHIFT_NONE),
     _fed("thanksgiving", _TXA, SHIFT_NONE), _fed("christmas", _TXA, SHIFT_NONE),
     Holiday("confederate_heroes", "Confederate Heroes Day", fixed(1, 19), _TXB),
     Holiday("texas_independence", "Texas Independence Day", fixed(3, 2), _TXB),
     Holiday("san_jacinto", "San Jacinto Day", fixed(4, 21), _TXB),
     Holiday("juneteenth", "Emancipation Day in Texas", fixed(6, 19), _TXB),
     Holiday("lbj", "Lyndon Baines Johnson Day", fixed(8, 27), _TXB),
     Holiday("thanksgiving_friday", "The Friday after Thanksgiving Day", DAY_AFTER_THANKSGIVING, _TXB),
     # § 662.021 makes only (b)(1)-(6) "legal holidays", so December 24 and 26 close offices but do not extend a period
     Holiday("christmas_eve", "December 24", fixed(12, 24), _TXB, legal=False),
     Holiday("boxing_day", "December 26", fixed(12, 26), _TXB, legal=False),
     Holiday("rosh_hashanah", "Rosh Hashanah (optional holiday)", from_rosh_hashanah(0, "Rosh Hashanah (1 Tishri)"),
             _TXC, optional=True, legal=False),
     Holiday("yom_kippur", "Yom Kippur (optional holiday)", from_rosh_hashanah(9, "Yom Kippur (10 Tishri)"), _TXC,
             optional=True, legal=False),
     Holiday("good_friday", "Good Friday (optional holiday)", from_easter(-2, "Good Friday"), _TXC, optional=True,
             legal=False)),
    business_day="Defined by Tex. Gov't Code § 552.0031 for the Public Information Act: not a Saturday, Sunday, or "
                 "national or state holiday under § 662.003(a)-(b). Optional holidays count only if the body's "
                 "officer for public information observes them.",
    first_day="Tex. Gov't Code § 311.014(a): the first day is excluded and the last day is included",
    roll=ROLL_NEXT_BUSINESS,
    roll_source="Tex. Gov't Code § 311.014(b): a last day on a Saturday, Sunday or legal holiday extends to the next "
                "day that is not one",
    variants=(Variant("observes_optional", "The body observes the optional holidays (§ 552.0031(c))",
                      "Tex. Gov't Code § 552.0031(c)", observe_optional=True),
              Variant("observes_shift", "The body observes weekend holidays on the Friday before or Monday after "
                                        "(§ 552.0031(e))", "Tex. Gov't Code § 552.0031(e)", shift=SHIFT_BOTH)),
    closures="Tex. Gov't Code § 552.0031(f): up to 10 nonbusiness days a year designated by the body; "
             "§ 552.2325: catastrophe suspensions",
    notes=("César Chávez Day (March 31) is not a § 662.003 holiday; § 662.013(c) says state agencies 'shall remain "
           "open', so it is a business day unless the body designates it under § 552.0031(f).",),
    sources=(("Tex. Gov't Code § 552.0031", "https://tcss.legis.texas.gov/resources/GV/htm/GV.552.htm#552.0031"),
             ("Tex. Gov't Code § 662.003", "https://tcss.legis.texas.gov/resources/GV/htm/GV.662.htm#662.003"),
             ("Tex. Gov't Code § 311.014", "https://tcss.legis.texas.gov/resources/GV/htm/GV.311.htm#311.014")))

# --------------------------------------------------------------------------- Illinois
# 205 ILCS 630/17(a), https://www.ilga.gov/ftp/ILCS/Ch%200205/Act%200630/020506300K17.html : "The following days shall
# be legal holidays in the State of Illinois": the federal days plus Lincoln's birthday (February 12), Casimir
# Pulaski's birthday (first Monday in March), Good Friday and "the days upon which the general elections for members
# of the House of Representatives are held" (even-numbered years).  (d): "When any such holidays, except Juneteenth
# National Freedom Day, fall on Sunday, the Monday next following shall be held and considered such holiday."
# 5 ILCS 70/1.11, https://www.ilga.gov/ftp/ILCS/Ch%200005/Act%200070/000500700K1.11.html : exclude the first day,
# include the last "unless the last day is Saturday or Sunday or is a holiday ... and then it shall also be excluded".
_IL = "205 ILCS 630/17(a)"
IL = Calendar(
    "il", "Illinois",
    (_fed("new_year", _IL, SHIFT_SUN), _fed("mlk", _IL, SHIFT_SUN, "Martin Luther King, Jr.'s birthday"),
     Holiday("lincoln", "Abraham Lincoln's birthday", fixed(2, 12), _IL, SHIFT_SUN),
     _fed("washington", _IL, SHIFT_SUN, "Presidents Day"),
     Holiday("pulaski", "Casimir Pulaski's birthday", nth(1, MON, 3), _IL, SHIFT_SUN),
     Holiday("good_friday", "Good Friday", from_easter(-2, "the Friday preceding Easter Sunday"), _IL, SHIFT_SUN),
     _fed("memorial", _IL, SHIFT_SUN),
     _fed("juneteenth", _IL, SHIFT_NONE, "Juneteenth National Freedom Day"),
     _fed("independence", _IL, SHIFT_SUN), _fed("labor", _IL, SHIFT_SUN), _fed("columbus", _IL, SHIFT_SUN),
     _fed("veterans", _IL, SHIFT_SUN, "Veterans' Day"), _fed("thanksgiving", _IL, SHIFT_SUN),
     _fed("christmas", _IL, SHIFT_SUN),
     Holiday("election", "General election for the House of Representatives", election("even"), _IL, SHIFT_SUN)),
    business_day="'Business days' is not defined in the Freedom of Information Act's definitions (5 ILCS 140/2). "
                 "This table uses the legal holidays of 205 ILCS 630/17.",
    first_day="5 ILCS 70/1.11: the first day is excluded",
    roll=ROLL_NEXT_BUSINESS,
    roll_source="5 ILCS 70/1.11: a last day on a Saturday, Sunday or holiday is excluded, and so is the next day if "
                "it is one too",
    closures="Any day the Governor proclaims a legal holiday (205 ILCS 630/17(a))",
    notes=("The list is in the Promissory Note and Bank Holiday Act. Days state offices close by administrative "
           "schedule (for example the day after Thanksgiving) are not in a statute that was read.",),
    sources=(("205 ILCS 630/17", "https://www.ilga.gov/ftp/ILCS/Ch%200205/Act%200630/020506300K17.html"),
             ("5 ILCS 70/1.11", "https://www.ilga.gov/ftp/ILCS/Ch%200005/Act%200070/000500700K1.11.html"),
             ("5 ILCS 140/2", "https://www.ilga.gov/ftp/ILCS/Ch%200005/Act%200140/000501400K2.html")))

# --------------------------------------------------------------------------- New York
# N.Y. General Construction Law § 24, https://www.nysenate.gov/legislation/laws/GCN/24 (text read locally; the
# publisher page answered 403 to scripts): the federal days plus Lincoln's birthday (February 12), Flag day (the
# second Sunday in June, always a Sunday, so it never changes a count) and "each general election day"; "if any of
# such days except Flag day is Sunday, the next day thereafter".  GCL § 25-a: a period ending on a Saturday, Sunday or
# public holiday runs to "the next succeeding business day".  GCL § 20: the day of the event is excluded, and in a
# two-day period an intervening Saturday, Sunday or public holiday is excluded.
_NY = "N.Y. Gen. Constr. Law § 24"
NY = Calendar(
    "ny", "New York",
    (_fed("new_year", _NY, SHIFT_SUN), _fed("mlk", _NY, SHIFT_SUN, "Dr. Martin Luther King, Jr. day"),
     Holiday("lincoln", "Lincoln's birthday", fixed(2, 12), _NY, SHIFT_SUN),
     _fed("washington", _NY, SHIFT_SUN), _fed("memorial", _NY, SHIFT_SUN),
     _fed("juneteenth", _NY, SHIFT_SUN, "Juneteenth"), _fed("independence", _NY, SHIFT_SUN),
     _fed("labor", _NY, SHIFT_SUN), _fed("columbus", _NY, SHIFT_SUN), _fed("veterans", _NY, SHIFT_SUN),
     _fed("thanksgiving", _NY, SHIFT_SUN), _fed("christmas", _NY, SHIFT_SUN),
     # New York holds a general election every November (Election Law § 8-100, not read here)
     Holiday("election", "General election day", election(), _NY, SHIFT_SUN)),
    business_day="'Business days' in Public Officers Law § 89(3)(a) is not defined there; this table leaves out "
                 "Saturdays, Sundays and the public holidays of GCL § 24.",
    first_day="N.Y. Gen. Constr. Law § 20: the day of the event is excluded",
    roll=ROLL_NEXT_BUSINESS,
    roll_source="N.Y. Gen. Constr. Law § 25-a(1): a period ending on a Saturday, Sunday or public holiday runs to "
                "the next succeeding business day",
    short_period=(2, True),
    closures="Days the President or the Governor appoints (GCL § 24)",
    sources=(("N.Y. Gen. Constr. Law § 24", "https://www.nysenate.gov/legislation/laws/GCN/24"),
             ("N.Y. Gen. Constr. Law § 25-a", "https://www.nysenate.gov/legislation/laws/GCN/25-A"),
             ("N.Y. Gen. Constr. Law § 20", "https://www.nysenate.gov/legislation/laws/GCN/20")))

# --------------------------------------------------------------------------- Washington
# RCW 1.16.050(1), https://apps.leg.wa.gov/rcw/default.aspx?cite=1.16.050 : Sunday and the federal days except
# Columbus Day (listed in (7)(r) among days that "may not be considered legal holidays for any purpose"), plus "(k)
# The Friday immediately following the fourth Thursday in November, to be known as Native American Heritage Day".
# "(5) Whenever any state legal holiday: (a) Other than Sunday, falls upon a Sunday, the following Monday is the legal
# holiday; or (b) Falls upon a Saturday, the preceding Friday is the legal holiday."  RCW 1.12.040,
# https://apps.leg.wa.gov/rcw/default.aspx?cite=1.12.040 : "excluding the first day, and including the last, unless
# the last day is a holiday, Saturday, or Sunday, and then it is also excluded".
_WA = "RCW 1.16.050(1)"
WA = Calendar(
    "wa", "Washington",
    tuple(_all_fed(_WA, SHIFT_BOTH, {"washington": "Presidents' Day", "juneteenth": "Juneteenth"}, skip=("columbus",))
          + [Holiday("thanksgiving_friday", "Native American Heritage Day", DAY_AFTER_THANKSGIVING, _WA, SHIFT_BOTH)]),
    business_day="'Business days' in RCW 42.56.520 is not defined in RCW 42.56.010; this table leaves out Saturdays, "
                 "Sundays and the legal holidays of RCW 1.16.050.",
    first_day="RCW 1.12.040: the first day is excluded",
    roll=ROLL_NEXT_BUSINESS,
    roll_source="RCW 1.12.040: a last day on a holiday, Saturday or Sunday is also excluded",
    closures="Each employee's floating holiday (RCW 1.16.050(2)) does not close the office; record real closures",
    sources=(("RCW 1.16.050", "https://apps.leg.wa.gov/rcw/default.aspx?cite=1.16.050"),
             ("RCW 1.12.040", "https://apps.leg.wa.gov/rcw/default.aspx?cite=1.12.040"),
             ("RCW 1.16.060", "https://apps.leg.wa.gov/rcw/default.aspx?cite=1.16.060")))

# --------------------------------------------------------------------------- Ohio
# Ohio Rev. Code § 124.19(A), https://codes.ohio.gov/ohio-revised-code/section-124.19 (text read locally): "State
# holidays shall be the first day of January, the third Monday in January, the third Monday in February, the day
# designated in ... 5 U.S.C. 6103 ... for the commemoration of Memorial day, the nineteenth day of June, the fourth day
# of July, the first Monday in September, the second Monday in October, the eleventh day of November, the fourth
# Thursday in November, the twenty-fifth day of December".  No weekend shift is stated in the text read.  R.C. 1.14
# (legal holidays and computation of time) is not in the local copy, and codes.ohio.gov's robots.txt disallows
# scripted access, so it was not read: the roll-forward rule below is unchecked.
_OH = "Ohio Rev. Code § 124.19(A)"
OH = Calendar(
    "oh", "Ohio",
    tuple(_all_fed(_OH, SHIFT_NONE, {"juneteenth": "June 19"})),
    business_day="'Business days' in R.C. 149.43 is not defined in R.C. 149.011; this table uses the state holidays "
                 "of R.C. 124.19.",
    first_day="(R.C. 1.14 not read)",
    roll=ROLL_UNKNOWN, roll_source="R.C. 1.14 was not read (not in the local copy; codes.ohio.gov disallows scripts)",
    closures="Any day appointed by the Governor or the President (R.C. 124.19(A))",
    notes=("A person should read R.C. 1.14 before a calendar-day date is relied on in Ohio.",),
    sources=(("Ohio Rev. Code § 124.19", "https://codes.ohio.gov/ohio-revised-code/section-124.19"),
             ("Ohio Rev. Code § 1.14 (not read)", "https://codes.ohio.gov/ohio-revised-code/section-1.14")))

# --------------------------------------------------------------------------- California
# The CPRA counts calendar days, so the table is the "holiday" of Code Civ. Proc. § 12a (texts read locally; the
# leginfo pages answered 403 to scripts): "all day on Saturdays, all holidays specified in Section 135 and ... all
# days that by terms of Section 12b are required to be considered as holidays".  CCP § 135: every full day that
# Gov. Code § 6700 makes a holiday is a judicial holiday, "except" Lunar New Year, Diwali, Genocide Remembrance Day
# (April 24), Admission Day (September 9), Columbus Day and days appointed by the Governor alone; "Every Saturday and
# the day after Thanksgiving Day are judicial holidays".  Good Friday (Gov. § 6700(a)(19)) is a holiday from noon to
# 3 p.m. only, not a full day.  CCP § 135 goes on: "If a judicial holiday falls on a Saturday or a Sunday, the
# Judicial Council may designate an alternative day for observance of the holiday", and Cal. Rules of Court, rule
# 1.11 (https://courts.ca.gov/cms/rules/index.cfm?title=one&linkid=rule1_11, read 10 October 2026) does: "When a
# judicial holiday specified by Code of Civil Procedure section 135 falls on a Saturday, the courts must observe the
# holiday on the preceding Friday. ... on a Sunday, ... on the following Monday."  So every holiday here shifts both
# ways: Gov. § 6701's narrower shifts fix the state holiday, but CCP § 12a counts the judicial holidays of § 135.
# The Judicial Council's published court holidays (https://courts.ca.gov/about/court-holidays, read 10 October 2026)
# match the table for 2026 (Independence Day observed on Friday 3 July) and 2027 (Juneteenth on Friday 18 June,
# Independence Day on Monday 5 July, Christmas on Friday 24 December), except that the 2027 schedule observes
# Farmworkers Day (Wednesday 31 March) on Friday 9 April: the ``moved`` entry below.  Gov. § 6701(c) lets the
# Legislature move a Tuesday-to-Thursday 31 March; for a year whose court schedule is not published yet, the table
# keeps 31 March.  Gov. § 6800 / CCP § 12: exclude the first day, include the last unless a holiday.
_CA = "Cal. Code Civ. Proc. § 135; Gov. Code § 6700"
_CA_2027 = "Judicial Council of California, 2027 court holidays"
CA = Calendar(
    "ca", "California",
    (_fed("new_year", _CA, SHIFT_BOTH, "January 1"),
     _fed("mlk", _CA, SHIFT_BOTH, "Dr. Martin Luther King, Jr. Day"),
     Holiday("lincoln", "Lincoln Day", fixed(2, 12), _CA, SHIFT_BOTH),
     _fed("washington", _CA, SHIFT_BOTH, "The third Monday in February"),
     Holiday("farmworkers", "Farmworkers Day", fixed(3, 31), _CA, SHIFT_BOTH,
             moved=((2027, date(2027, 4, 9), _CA_2027),)),
     _fed("memorial", _CA, SHIFT_BOTH, "The last Monday in May"),
     _fed("juneteenth", _CA, SHIFT_BOTH, "Juneteenth"),
     _fed("independence", _CA, SHIFT_BOTH, "July 4"),
     _fed("labor", _CA, SHIFT_BOTH, "The first Monday in September"),
     Holiday("native_american", "Native American Day", nth(4, FRI, 9), _CA, SHIFT_BOTH),
     _fed("veterans", _CA, SHIFT_BOTH, "Veterans Day"),
     _fed("thanksgiving", _CA, SHIFT_BOTH),
     Holiday("thanksgiving_friday", "The day after Thanksgiving Day", DAY_AFTER_THANKSGIVING,
             "Cal. Code Civ. Proc. § 135"),
     _fed("christmas", _CA, SHIFT_BOTH, "December 25")),
    business_day="The CPRA (Gov. Code § 7922.535) counts calendar days. For other counts this table is the judicial "
                 "holidays of CCP § 135 that CCP § 12a uses, on the days the courts observe them (Cal. Rules of "
                 "Court, rule 1.11, and the Judicial Council's schedule), plus Saturdays and Sundays.",
    first_day="Cal. Gov. Code § 6800 and Code Civ. Proc. § 12: the first day is excluded",
    roll=ROLL_NEXT_BUSINESS,
    roll_source="Cal. Code Civ. Proc. § 12a(a): a last day that is a holiday (including every Saturday) extends to "
                "the next day that is not a holiday",
    closures="Cal. Code Civ. Proc. § 12b: a day the city, county, state or public office is closed counts as a "
             "holiday",
    shift_source="observed under Cal. Rules of Court, rule 1.11",
    notes=("Gov. Code § 6700 also names Lunar New Year, Diwali, Genocide Remembrance Day, Admission Day and Columbus "
           "Day, which CCP § 135 leaves out; and § 6700(a)(20)(B) says some days bind a city, county or district "
           "only if it adopts them.",
           "Rule 1.11 observes a judicial holiday that falls on a Saturday on the Friday before, and one on a Sunday "
           "on the Monday after. The Judicial Council's 2027 schedule also observes Farmworkers Day on Friday 9 "
           "April instead of Wednesday 31 March. For later years the table keeps 31 March until the court schedule "
           "is published.",
           "Gov. Code § 6803: a year is 365 days, with a leap day and the day before it counted as one day."),
    sources=(("Cal. Code Civ. Proc. § 12a",
              "https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=CCP&sectionNum=12a."),
             ("Cal. Code Civ. Proc. § 135",
              "https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=CCP&sectionNum=135."),
             ("Cal. Rules of Court, rule 1.11", "https://courts.ca.gov/cms/rules/index.cfm?title=one&linkid=rule1_11"),
             ("California court holidays (Judicial Council)", "https://courts.ca.gov/about/court-holidays"),
             ("Cal. Gov. Code § 6700",
              "https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=GOV&sectionNum=6700."),
             ("Cal. Gov. Code § 6701",
              "https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=GOV&sectionNum=6701.")))

# --------------------------------------------------------------------------- North Carolina
# N.C. Gen. Stat. § 103-4(a),
# https://www.ncleg.gov/EnactedLegislation/Statutes/HTML/BySection/Chapter_103/GS_103-4.html : "legal public holidays",
# including Robert E. Lee's Birthday (January 19), Greek Independence Day (March 25), the Halifax Resolves (April 12),
# Confederate Memorial Day (May 10), the Mecklenburg Declaration (May 20), Good Friday, First Responders Day
# (September 11), Yom Kippur and "Tuesday after the first Monday in November in years in which a general election is to
# be held".  "(b) Whenever any public holiday shall fall upon Sunday, the Monday following shall be a public holiday."
# § 103-5(a), same site: an act due on "a Saturday, Sunday, or legal holiday when the public office ... is closed" may
# be done "on the next day that the public office or courthouse is open".
_NC = "N.C. Gen. Stat. § 103-4(a)"
NC = Calendar(
    "nc", "North Carolina",
    (_fed("new_year", _NC, SHIFT_SUN), _fed("mlk", _NC, SHIFT_SUN, "Martin Luther King, Jr.'s, Birthday"),
     Holiday("lee", "Robert E. Lee's Birthday", fixed(1, 19), _NC, SHIFT_SUN),
     _fed("washington", _NC, SHIFT_SUN),
     Holiday("greek_independence", "Greek Independence Day", fixed(3, 25), _NC, SHIFT_SUN),
     Holiday("halifax", "Anniversary of signing of Halifax Resolves", fixed(4, 12), _NC, SHIFT_SUN),
     Holiday("confederate_memorial", "Confederate Memorial Day", fixed(5, 10), _NC, SHIFT_SUN),
     Holiday("mecklenburg", "Anniversary of Mecklenburg Declaration of Independence", fixed(5, 20), _NC, SHIFT_SUN),
     _fed("memorial", _NC, SHIFT_SUN),
     Holiday("good_friday", "Good Friday", from_easter(-2, "Good Friday"), _NC, SHIFT_SUN),
     _fed("independence", _NC, SHIFT_SUN), _fed("labor", _NC, SHIFT_SUN),
     Holiday("first_responders", "First Responders Day", fixed(9, 11), _NC, SHIFT_SUN),
     _fed("columbus", _NC, SHIFT_SUN),
     Holiday("yom_kippur", "Yom Kippur", from_rosh_hashanah(9, "Yom Kippur (10 Tishri)"), _NC, SHIFT_SUN),
     _fed("veterans", _NC, SHIFT_SUN),
     Holiday("election", "General election day", election("even"), _NC, SHIFT_SUN),
     _fed("thanksgiving", _NC, SHIFT_SUN), _fed("christmas", _NC, SHIFT_SUN)),
    business_day="'Business days' in N.C. Gen. Stat. § 132-6(d) is not defined there; this table leaves out the "
                 "legal public holidays of § 103-4, which include days many offices are open (mark them 'open').",
    first_day="(not checked for North Carolina; the day of the event is not counted, as in the other tables)",
    roll=ROLL_NEXT_BUSINESS,
    roll_source="N.C. Gen. Stat. § 103-5(a): to the next day the public office is open",
    closures="The days state offices actually close are set outside § 103-4 (not read); record closures",
    sources=(("N.C. Gen. Stat. § 103-4",
              "https://www.ncleg.gov/EnactedLegislation/Statutes/HTML/BySection/Chapter_103/GS_103-4.html"),
             ("N.C. Gen. Stat. § 103-5",
              "https://www.ncleg.gov/EnactedLegislation/Statutes/HTML/BySection/Chapter_103/GS_103-5.html")))

# --------------------------------------------------------------------------- Florida
# Fla. Stat. § 110.117(1),
# http://www.leg.state.fl.us/statutes/index.cfm?App_mode=Display_Statute&URL=0100-0199/0110/Sections/0110.117.html :
# the "paid holidays observed by all state branches and agencies" (the days offices close): New Year's Day, Martin
# Luther King Jr.'s birthday (third Monday in January), Memorial Day, Independence Day, Labor Day, Veterans' Day,
# Thanksgiving Day, the Friday after Thanksgiving and Christmas Day; "If any of these holidays falls on Saturday, the
# preceding Friday shall be observed ... on Sunday, the following Monday".  § 683.01 (same site) lists a much longer
# set of "legal holidays", including every Sunday and many commemorative days: the variant below.
_FL = "Fla. Stat. § 110.117(1)"
_FL_LEGAL = "Fla. Stat. § 683.01(1)"
FL = Calendar(
    "fl", "Florida",
    (_fed("new_year", _FL, SHIFT_BOTH), _fed("mlk", _FL, SHIFT_BOTH, "Birthday of Martin Luther King, Jr."),
     _fed("memorial", _FL, SHIFT_BOTH), _fed("independence", _FL, SHIFT_BOTH), _fed("labor", _FL, SHIFT_BOTH),
     _fed("veterans", _FL, SHIFT_BOTH, "Veterans' Day"), _fed("thanksgiving", _FL, SHIFT_BOTH),
     Holiday("thanksgiving_friday", "Friday after Thanksgiving", DAY_AFTER_THANKSGIVING, _FL, SHIFT_BOTH),
     _fed("christmas", _FL, SHIFT_BOTH)),
    business_day="Florida's records model has no fixed deadline. For other counts this table uses the days state "
                 "agencies close (§ 110.117); the legal holidays of § 683.01 are a variant.",
    first_day="(not checked for Florida)",
    roll=ROLL_UNKNOWN, roll_source="No Florida time-computation statute was read",
    variants=(Variant("legal", "Florida legal holidays (§ 683.01) instead of state paid holidays (§ 110.117)",
                      _FL_LEGAL, remove=("mlk", "thanksgiving_friday"), shift=SHIFT_SUN, add=(
                          Holiday("mlk_fixed", "Birthday of Martin Luther King, Jr.", fixed(1, 15), _FL_LEGAL),
                          Holiday("lee", "Birthday of Robert E. Lee", fixed(1, 19), _FL_LEGAL),
                          Holiday("lincoln", "Lincoln's Birthday", fixed(2, 12), _FL_LEGAL),
                          Holiday("anthony", "Susan B. Anthony's Birthday", fixed(2, 15), _FL_LEGAL),
                          _fed("washington", _FL_LEGAL, SHIFT_SUN),
                          Holiday("tuskegee", "Tuskegee Airmen Commemoration Day", nth(4, THU, 3), _FL_LEGAL),
                          Holiday("good_friday", "Good Friday", from_easter(-2, "Good Friday"), _FL_LEGAL),
                          Holiday("pascua", "Pascua Florida Day", fixed(4, 2), _FL_LEGAL),
                          Holiday("confederate_memorial", "Confederate Memorial Day", fixed(4, 26), _FL_LEGAL),
                          Holiday("davis", "Birthday of Jefferson Davis", fixed(6, 3), _FL_LEGAL),
                          Holiday("flag", "Flag Day", fixed(6, 14), _FL_LEGAL),
                          _fed("columbus", _FL_LEGAL, SHIFT_SUN, "Columbus Day and Farmers' Day"),
                          Holiday("election", "General Election Day", election("even"), _FL_LEGAL))),),
    closures="A state day of mourning the Governor declares (§ 110.117(2))",
    notes=("§ 683.01 does not list Juneteenth; § 683.01(1)(v) adds Shrove Tuesday in counties with carnival "
           "associations (not in the table).",),
    sources=(("Fla. Stat. § 110.117", "http://www.leg.state.fl.us/statutes/index.cfm?App_mode=Display_Statute&URL="
                                      "0100-0199/0110/Sections/0110.117.html"),
             ("Fla. Stat. § 683.01", "http://www.leg.state.fl.us/statutes/index.cfm?App_mode=Display_Statute&URL="
                                     "0600-0699/0683/Sections/0683.01.html")))

CALENDARS: dict[str, Calendar] = {c.key: c for c in (US, VA, DC, MD, TX, IL, NY, WA, OH, CA, NC, FL)}


def calendar_for(state: str | None) -> Calendar:
    """The state's table, or the federal one (with a note in its result) for a state without one."""
    return CALENDARS.get((state or "").lower(), US)


# ============================================================================ per-case options
@dataclass(frozen=True)
class Options:
    """What one case adds to a calendar: days the office was closed, optional holidays the body observes, holidays
    on which the body is open, and the name of a variant reading."""
    closures: frozenset = frozenset()
    observes: frozenset = frozenset()
    opens: frozenset = frozenset()
    variant: str | None = None

    @classmethod
    def from_dict(cls, d: dict | None) -> "Options":
        d = d or {}

        def dates(xs):
            out = set()
            for x in xs or []:
                try:
                    out.add(x if isinstance(x, date) else date.fromisoformat(str(x)[:10]))
                except ValueError:
                    continue
            return frozenset(out)
        return cls(closures=dates(d.get("closures")), observes=frozenset(map(str, d.get("observes") or [])),
                   opens=frozenset(map(str, d.get("opens") or [])), variant=d.get("variant") or None)

    def with_variant(self, key: str | None) -> "Options":
        return Options(self.closures, self.observes, self.opens, key)


NO_OPTIONS = Options()


def _holidays_of(cal: Calendar, opts: Options) -> tuple[list[Holiday], str | None, bool]:
    v = cal.variant(opts.variant)
    hs = [h for h in cal.holidays if not (v and h.key in v.remove)] + list(v.add if v else ())
    return hs, (v.shift if v else None), bool(v and v.observe_optional)


@dataclass(frozen=True)
class _Hit:
    key: str
    name: str
    cite: str
    legal: bool
    statutory: date
    part_day: bool


@lru_cache(maxsize=1024)
def _table(cal_key: str, year: int, variant: str | None, observes: frozenset, opens: frozenset) -> dict:
    """Observed date -> _Hit for one calendar year.  A full day wins over a part day, and a legal holiday over one
    that only closes the office."""
    cal = CALENDARS[cal_key]
    hs, shift, all_optional = _holidays_of(cal, Options(variant=variant))
    out: dict[date, _Hit] = {}
    for y in (year - 1, year, year + 1):            # a January 1 on a Saturday is observed on December 31
        for h in hs:
            if h.key in opens or (h.optional and not all_optional and h.key not in observes):
                continue
            statutory, observed = h.dates(y, shift)
            if observed is None or observed.year != year:
                continue
            cite = h.cite
            published = next((src for yy, _, src in h.moved if yy == y), None)
            if published:
                cite = f"{h.cite}; {published}"
            elif statutory != observed and cal.shift_source:
                cite = f"{h.cite}; {cal.shift_source}"
            hit = _Hit(h.key, h.name, cite, h.legal, statutory, h.part_day)
            old = out.get(observed)
            if old is None or (not old.part_day, old.legal) < (not h.part_day, h.legal):
                out[observed] = hit
    return out


def holidays(cal: Calendar | str, year: int, opts: Options = NO_OPTIONS) -> list[dict]:
    """The year's non-business days other than weekends, each with its reason and source.  Part days off are listed
    with ``part_day`` true, and ``counted`` says whether the reading counts them as business days."""
    cal = CALENDARS[cal] if isinstance(cal, str) else cal
    t = _table(cal.key, year, opts.variant, opts.observes, opts.opens)
    counted = not _part_day_closed(cal, opts)
    out = [{"date": d.isoformat(), "key": h.key, "name": h.name, "cite": h.cite, "legal": h.legal,
            "part_day": h.part_day, "counted": h.part_day and counted,
            "observed_for": h.statutory.isoformat() if h.statutory != d else None}
           for d, h in sorted(t.items())]
    out += [{"date": d.isoformat(), "key": None, "name": "Office closed (recorded in this case)", "cite": cal.closures,
             "legal": True, "part_day": False, "counted": False, "observed_for": None}
            for d in sorted(opts.closures) if d.year == year]
    return sorted(out, key=lambda r: r["date"])


def _hit(cal: Calendar, d: date, opts: Options) -> _Hit | None:
    return _table(cal.key, d.year, opts.variant, opts.observes, opts.opens).get(d)


def _describe(h: _Hit, d: date) -> str:
    moved = f", observed for {h.statutory:%a %d %b}" if h.statutory != d else ""
    return f"{h.name}{moved} ({h.cite})"


def _part_day_closed(cal: Calendar, opts: Options) -> bool:
    """Whether a part day off is a non-business day in this reading (the calendar's default unless a variant
    counts it)."""
    v = cal.variant(opts.variant)
    if v and v.part_day_open:
        return False
    return cal.part_day_closed


def closed_reason(cal: Calendar, d: date, opts: Options = NO_OPTIONS) -> str | None:
    """Why a day is not a business day under the calendar, or None when it is one.  A part day off is not one in a
    reading where part days are closed (Virginia's default), and is one otherwise."""
    if d in opts.closures:
        return "office closed (recorded in this case)"
    if d.weekday() == SAT:
        return "Saturday"
    if d.weekday() == SUN:
        return "Sunday"
    hit = _hit(cal, d, opts)
    if hit and not hit.part_day:
        return _describe(hit, d)
    if hit and _part_day_closed(cal, opts):
        return f"{_describe(hit, d)}: a part day off, not counted as a business day in this reading"
    return None


def part_day(cal: Calendar | str, d: date, opts: Options = NO_OPTIONS) -> str | None:
    """Why a weekday is a part day off (the office open for only part of it, or not at all), or None.  Whether it
    counts as a business day depends on the reading (``closed_reason``)."""
    cal = CALENDARS[cal] if isinstance(cal, str) else cal
    if d in opts.closures or d.weekday() >= SAT:
        return None
    hit = _hit(cal, d, opts)
    return _describe(hit, d) if hit and hit.part_day else None


def _legal_holiday(cal: Calendar, d: date, opts: Options) -> bool:
    hit = _hit(cal, d, opts)
    return bool(hit and hit.legal and not hit.part_day)


def _part_day_extends(cal: Calendar, opts: Options) -> bool:
    v = cal.variant(opts.variant)
    return bool(v and v.part_day_extends)


def is_business_day(cal: Calendar | str, d: date, opts: Options = NO_OPTIONS) -> bool:
    cal = CALENDARS[cal] if isinstance(cal, str) else cal
    return closed_reason(cal, d, opts) is None


# ============================================================================ counting
@dataclass
class Count:
    due: date
    how: str
    skipped: list[dict] = field(default_factory=list)       # holidays and closures passed over (weekends left out)
    rolled_from: date | None = None
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {"due": self.due.isoformat(), "how": self.how, "skipped": self.skipped,
                "rolled_from": self.rolled_from.isoformat() if self.rolled_from else None, "notes": self.notes}


def _skip(cal, d, opts, skipped):
    why = closed_reason(cal, d, opts)
    if why and why not in ("Saturday", "Sunday"):
        skipped.append({"date": d.isoformat(), "why": why})
    return why


def _part_day_notes(cal: Calendar, days: Iterable[date], opts: Options) -> list[str]:
    """Notes for part days off that this reading counts as business days."""
    notes = []
    for d in days:
        why = part_day(cal, d, opts)
        if why:
            notes.append(f"{d:%a %d %b %Y} is counted as a business day in this reading although it is a part day "
                         f"off: {why}. Record an office closure if the office was closed all day.")
    return notes


def _skipped_part_day_notes(cal: Calendar, skipped: list[dict], opts: Options) -> list[str]:
    """Notes for part days off that this reading leaves out of the count."""
    notes = []
    for s in skipped:
        d = date.fromisoformat(s["date"])
        why = part_day(cal, d, opts)
        if why:
            other = any(v.part_day_open for v in cal.variants)
            notes.append(f"{d:%a %d %b %Y} is a part day off: {why}. It is not counted as a business day, since "
                         f"the office may have closed for part of it, so the body is not called overdue while it "
                         f"may still be in time." + (" Another reading counts it; its date is shown beside this one "
                                                     "when it differs." if other else "")
                         + " Mark the day open if the office was open all day.")
    return notes


def add_business_days(cal: Calendar | str, start: date, n: int, opts: Options = NO_OPTIONS) -> Count:
    """The Nth business day after ``start`` (day 1 is the first business day after it).  A part day off is left
    out where the reading closes part days (``Calendar.part_day_closed``, Virginia's default); a reading that counts
    it (``part_day_open``) may still move a period that ends on one to the next business day (``part_day_extends``,
    Va. Code § 1-210(E))."""
    cal = CALENDARS[cal] if isinstance(cal, str) else cal
    d, counted, skipped, days = start, 0, [], []
    while counted < n:
        d += timedelta(days=1)
        if not _skip(cal, d, opts, skipped):
            counted += 1
            days.append(d)
    count = Count(d, f"{n} business day{'s' * (n != 1)} by the {cal.name} calendar; day 1 is the first business "
                     f"day after {start:%a %d %b %Y}", skipped)
    count.notes += _skipped_part_day_notes(cal, skipped, opts)
    if _part_day_extends(cal, opts) and part_day(cal, d, opts):
        moved = d + timedelta(days=1)
        while closed_reason(cal, moved, opts) or part_day(cal, moved, opts):
            moved += timedelta(days=1)
        count.notes += _part_day_notes(cal, days[:-1], opts)
        count.notes.append(f"{d:%a %d %b %Y} is a part day off: {part_day(cal, d, opts)}. In this reading a period "
                           f"that ends on it runs to the next business day, {moved:%a %d %b %Y}.")
        count.rolled_from, count.due = d, moved
    else:
        count.notes += _part_day_notes(cal, days, opts)
    return count


def _extends(cal: Calendar, d: date, opts: Options) -> bool:
    """Whether a period whose last day is ``d`` runs on to the next day under the calendar's roll-forward rule.
    A holiday marked ``legal=False`` (Texas's December 24 and 26, § 662.021) closes offices but does not extend.
    A part day off extends where the reading closes part days, or moves a period ending on one (Va. Code
    § 1-210(E) covers "part of a day" an office is closed)."""
    if cal.roll == ROLL_NOT_SUNDAY_HOLIDAY:         # Md. Gen. Prov. § 1-302(b)(1): Saturdays do not extend
        return d.weekday() == SUN or _legal_holiday(cal, d, opts)
    if part_day(cal, d, opts) and (_part_day_closed(cal, opts) or _part_day_extends(cal, opts)):
        return True
    return d in opts.closures or d.weekday() >= SAT or _legal_holiday(cal, d, opts)


def _roll(cal: Calendar, d: date, opts: Options, count: Count) -> Count:
    if cal.roll in (ROLL_NOT_SUNDAY_HOLIDAY, ROLL_NEXT_BUSINESS):
        moved = d
        while _extends(cal, moved, opts):
            moved += timedelta(days=1)
    else:
        why = closed_reason(cal, d, opts)
        if why:
            nxt = d
            while closed_reason(cal, nxt, opts):
                nxt += timedelta(days=1)
            count.notes.append(f"The last day, {d:%a %d %b %Y}, is not a business day ({why}); no rule moving "
                               f"it was found for {cal.name} ({cal.roll_source}). If it moves, it is "
                               f"{nxt:%a %d %b %Y}.")
        return count
    if moved != d:
        why = closed_reason(cal, d, opts) or f"a part day off, on which in this reading a period that ends then " \
                                             f"runs on: {part_day(cal, d, opts)}"
        count.notes.append(f"{d:%a %d %b %Y} is not a business day ({why}), so the period runs to "
                           f"{moved:%a %d %b %Y} ({cal.roll_source}).")
        count.rolled_from, count.due = d, moved
    elif part_day(cal, d, opts):
        count.notes += _part_day_notes(cal, [d], opts)
    return count


def add_calendar_days(cal: Calendar | str, start: date, n: int, opts: Options = NO_OPTIONS,
                      roll: bool = True) -> Count:
    """The Nth calendar day after ``start``, moved by the calendar's roll-forward rule when it is not a business day.
    Short periods follow Md. Gen. Prov. § 1-302(c)(2) and N.Y. Gen. Constr. Law § 20 where those apply."""
    cal = CALENDARS[cal] if isinstance(cal, str) else cal
    skipped: list[dict] = []
    if cal.short_period and 0 < n <= cal.short_period[0]:
        d, counted = start, 0
        while counted < n:
            d += timedelta(days=1)
            off = d.weekday() == SUN or _legal_holiday(cal, d, opts) or (cal.short_period[1] and d.weekday() == SAT)
            if off:
                _skip(cal, d, opts, skipped)
            else:
                counted += 1
        count = Count(d, f"{n} day{'s' * (n != 1)}, leaving out intermediate "
                         f"{'Saturdays, ' if cal.short_period[1] else ''}Sundays and holidays ({cal.name} rule for "
                         f"periods of {cal.short_period[0]} days or less)", skipped)
    else:
        count = Count(start + timedelta(days=n), f"{n} calendar day{'s' * (n != 1)} after {start:%a %d %b %Y}")
    return _roll(cal, count.due, opts, count) if roll else count


def add_months(start: date, n: int) -> date:
    """Same day number n months later, or the month's last day (Tex. Gov't Code § 311.014(c); RCW 1.16.060)."""
    m = start.month - 1 + n
    y, m = start.year + m // 12, m % 12 + 1
    last = (date(y + (m == 12), m % 12 + 1, 1) - timedelta(days=1)).day
    return date(y, m, min(start.day, last))


def count_deadline(cal: Calendar | str, start: date, amount: int, unit: str, opts: Options = NO_OPTIONS) -> Count:
    """The last day of a period of ``amount`` ``unit`` that starts on the day of ``start`` (not counted)."""
    cal = CALENDARS[cal] if isinstance(cal, str) else cal
    if unit == "business_days":
        return add_business_days(cal, start, amount, opts)
    if unit == "days":
        return add_calendar_days(cal, start, amount, opts)
    if unit == "weeks":
        c = add_calendar_days(cal, start, 7 * amount, opts)
        c.how = f"{amount} week{'s' * (amount != 1)} ({7 * amount} calendar days) after {start:%a %d %b %Y}"
        return c
    if unit == "hours":
        days = math.ceil(amount / 24)
        c = add_calendar_days(cal, start, days, opts)
        c.how = f"{amount} hours, counted as {days} whole day{'s' * (days != 1)}"
        c.notes.append("Hours are counted in whole days; the exact time of the event matters.")
        return c
    if unit in ("months", "years"):
        months = amount * (12 if unit == "years" else 1)
        count = Count(add_months(start, months), f"{amount} {unit[:-1] if amount == 1 else unit} after "
                                                 f"{start:%a %d %b %Y} (calendar {unit})")
        return _roll(cal, count.due, opts, count)
    raise ValueError(f"unknown unit {unit!r}; expected one of {UNITS}")


def elapsed(cal: Calendar | str, start: date, end: date, unit: str, opts: Options = NO_OPTIONS) -> int:
    """How long from ``start`` (not counted) to ``end``: business days for a business-day rule, else calendar days."""
    cal = CALENDARS[cal] if isinstance(cal, str) else cal
    if end <= start:
        return 0
    if unit == "business_days":
        n, d = 0, start
        while d < end:
            d += timedelta(days=1)
            n += closed_reason(cal, d, opts) is None
        return n
    return (end - start).days


# ============================================================================ deadline rules
_CARD = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
         "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
         "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40,
         "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90}
_ORD = {"first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5, "sixth": 6, "seventh": 7, "eighth": 8,
        "ninth": 9, "tenth": 10, "eleventh": 11, "twelfth": 12, "thirteenth": 13, "fourteenth": 14,
        "fifteenth": 15, "sixteenth": 16, "seventeenth": 17, "eighteenth": 18, "nineteenth": 19, "twentieth": 20,
        "thirtieth": 30, "fortieth": 40, "fiftieth": 50, "sixtieth": 60, "ninetieth": 90}
_WORDS = sorted(list(_CARD) + list(_ORD) + ["hundred"], key=len, reverse=True)
_W = "|".join(_WORDS)
_NUMBER = rf"(?:\d{{1,4}}(?:st|nd|rd|th)?|(?:{_W})(?:[\s-]+(?:{_W}))*)"
_UNIT = (r"(?P<unit>(?:business|working|work)[\s-]*days?|workdays?|calendar\s+days?|days?|weeks?|months?|years?"
         r"|hours?)\b(?P<except>\s*\((?:except|excepting|excluding)[^)]*\))?")
_LEAD = (r"(?P<lead>within|not\s+later\s+than|no\s+later\s+than|on\s+or\s+before|not\s+more\s+than|"
         r"no\s+more\s+than|at\s+the\s+end\s+of|up\s+to|at\s+most|an?\s+additional|additional|"
         r"for\s+more\s+than|more\s+than|has|have|by)")
_RULE = re.compile(rf"(?:\b{_LEAD}\s+)?(?:the\s+)?\b(?P<n>{_NUMBER})\s+{_UNIT}"
                   rf"(?:\s+(?P<prep>of|after|from|following|before)\s+(?P<anchor>[^.;:,(]+))?", re.I)


@dataclass(frozen=True)
class DeadlineRule:
    amount: int
    unit: str                   # one of UNITS
    kind: str = "within"        # within | nth | extension | limit | set_by_body
    anchor: str | None = None
    text: str = ""

    def describe(self) -> str:
        if self.kind == "set_by_body":
            return "a date the body states"
        u = self.unit.replace("_", " ")
        u = u[:-1] if self.amount == 1 else u
        lead = {"extension": "an additional ", "limit": "at most "}.get(self.kind, "")
        return f"{lead}{self.amount} {u}"

    def as_dict(self) -> dict:
        return {"amount": self.amount, "unit": self.unit, "kind": self.kind, "anchor": self.anchor,
                "text": self.describe()}


def _to_int(phrase: str) -> int:
    phrase = phrase.lower().strip()
    m = re.fullmatch(r"(\d+)(?:st|nd|rd|th)?", phrase)
    if m:
        return int(m.group(1))
    total = 0
    for tok in re.split(r"[\s-]+", phrase):
        if tok == "hundred":
            total = max(total, 1) * 100
        else:
            total += _CARD.get(tok, _ORD.get(tok, 0))
    return total


def _norm_unit(unit: str, exception: str | None) -> str:
    u = unit.lower()
    if re.match(r"(business|working|work)|workday", u):
        return "business_days"
    if u.startswith(("day", "calendar")):
        return "business_days" if exception and "saturday" in exception.lower() else "days"
    for name in ("week", "month", "year", "hour"):
        if u.startswith(name):
            return name + "s"
    raise ValueError(unit)


def _is_ordinal(phrase: str) -> bool:
    p = phrase.lower().strip()
    return bool(re.fullmatch(r"\d+(st|nd|rd|th)", p)) or p.split("-")[-1].split()[-1] in _ORD


def parse_deadline(text: str | None) -> DeadlineRule | None:
    """The time rule in a deadline phrase, or None when it states no number of units.

    >>> parse_deadline("promptly, but in all cases within five working days of receiving a request").describe()
    '5 business days'
    """
    if not text:
        return None
    t = re.sub(r"\s+", " ", str(text))
    matches = list(_RULE.finditer(t))
    if not matches:
        return None
    # an extension clause wins over the condition that precedes it ("If ... within five working days, the body shall
    # have an additional seven work days"); otherwise the first stated period wins
    pick = next((m for m in matches if m.group("lead") and "additional" in m.group("lead").lower()), matches[0])
    lead = (pick.group("lead") or "").lower()
    amount = _to_int(pick.group("n"))
    kind = ("extension" if "additional" in lead else "limit" if lead.endswith("more than") and
            not lead.startswith(("not", "no ")) else "nth" if _is_ordinal(pick.group("n")) else "within")
    anchor = re.split(r"\s+(?:shall|must|may|will|is|are|has|have)\b", pick.group("anchor") or "")[0].strip() or None
    return DeadlineRule(amount, _norm_unit(pick.group("unit"), pick.group("except")), kind, anchor, pick.group(0))


@dataclass(frozen=True)
class RuleCheck:
    """A model deadline's rule (from its amount and unit), with what its quote says."""
    rule: DeadlineRule
    quote_rule: DeadlineRule | None
    status: str                 # agrees | unparsed | differs
    note: str = ""

    def as_dict(self) -> dict:
        return {"rule": self.rule.as_dict(), "quote_rule": self.quote_rule.as_dict() if self.quote_rule else None,
                "status": self.status, "note": self.note}


def rule_from_fields(deadline: dict) -> DeadlineRule:
    """The rule a model deadline's fields express: ``{"amount": 5, "unit": "business_days", "anchor": ...}``."""
    unit = deadline.get("unit") or "days"
    if unit not in UNITS:
        raise ValueError(f"unknown unit {unit!r}")
    amount = int(deadline.get("amount") or 0)
    parsed = parse_deadline(f"{amount} {unit.replace('_', ' ')}")
    if parsed is None or (parsed.amount, parsed.unit) != (amount, unit):
        raise ValueError(f"cannot read the deadline fields {amount!r} {unit!r}")
    return DeadlineRule(amount, unit, "set_by_body" if amount == 0 else "within", deadline.get("anchor"),
                        f"{amount} {unit.replace('_', ' ')}")


def check_deadline(deadline: dict) -> RuleCheck:
    """Parse a model deadline's fields and its quoted words, and say whether they agree."""
    rule = rule_from_fields(deadline)
    quote = (deadline.get("source") or {}).get("quote")
    q = parse_deadline(quote)
    if rule.kind == "set_by_body":
        return RuleCheck(rule, q, "unparsed" if q is None else "differs",
                         "The body states the date itself (amount 0); record it from the acknowledgement.")
    if q is None:
        return RuleCheck(rule, None, "unparsed", "The quote states no number of days; the lab counts the model's "
                                                 f"fields ({rule.describe()}).")
    if (q.amount, q.unit) == (rule.amount, rule.unit):
        kind = rule.kind if q.kind == "limit" else q.kind
        return RuleCheck(DeadlineRule(rule.amount, rule.unit, kind, rule.anchor, rule.text), q, "agrees")
    return RuleCheck(rule, q, "differs", f"The quote says {q.describe()}; the model's fields say {rule.describe()} "
                                         f"from '{rule.anchor}'. The lab counts the fields.")


# ============================================================================ serialising a calendar
def describe_calendar(cal: Calendar | str, year: int | None = None, opts: Options = NO_OPTIONS) -> dict:
    """A calendar's rules, sources and (for one year) its dates, for the API and for publishing inline."""
    cal = CALENDARS[cal] if isinstance(cal, str) else cal
    out = {"key": cal.key, "name": cal.name, "business_day": cal.business_day, "first_day": cal.first_day,
           "roll": cal.roll, "roll_source": cal.roll_source, "closures": cal.closures, "notes": list(cal.notes),
           "sources": [{"cite": c, "url": u} for c, u in cal.sources],
           "variants": [{"key": v.key, "text": v.text, "cite": v.cite} for v in cal.variants],
           "part_day_rule": cal.part_day_rule, "you_variant": cal.you_variant,
           "default_reading": cal.default_reading,
           "holidays": [{"key": h.key, "name": h.name, "rule": h.when.text, "cite": h.cite, "shift": h.shift,
                         "optional": h.optional, "legal": h.legal, "part_day": h.part_day,
                         "moved": [{"year": y, "date": d.isoformat(), "source": s} for y, d, s in h.moved]}
                        for h in cal.holidays]}
    if year:
        out["year"], out["dates"] = year, holidays(cal, year, opts)
    return out
