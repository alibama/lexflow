"""Official public payroll datasets, and a polite reader that keeps only aggregate-safe fields.

The registry follows ``docs/design/payroll-research.md`` (sections 3, 4 and 7). Each entry says who publishes the
data, how a machine reads it, its licence and cadence, and whether its rows describe individual people
(``person_level``). From a person-level source lexflow keeps aggregates only; see ``aggregate.py``.

Privacy is enforced by an allowlist, not a blocklist:

* A dataset's ``fields`` map names the only source columns lexflow ever reads: the agency, the title or class, the
  pay figure, and optionally the pay basis and the period.
* A Socrata query asks for those columns only (``$select``), grouped on the publisher's server, so names, IDs,
  dates and demographics never leave the publisher. The CSV path cannot do that: it downloads the whole file,
  names included, and drops every unmapped column as each row is parsed. No enabled source uses it.
* Every row, whatever the transport, goes through :func:`project` before anything else sees it. It returns the
  mapped fields and nothing else, so a column that is not mapped (a name, say) is dropped at read time.
* :func:`check_fields` refuses a map that points at a column that looks person-level (see
  :func:`looks_person_level`): by a general rule any name or ID column whose owner is not an organisation, a
  column that is only a person word or a role, plus named categories such as demographics, career dates, tenure
  and contact details; glued names ("POSITIONNUMBER") are split into known words first. It runs on the whole
  registry at import. It is a second line of defence: it knows common spellings, not every one, and errs towards
  refusing; the allowlist above is the real protection.

Each entry also says what one of its rows is (``rows``). The disclosure thresholds count rows, so they count people
only for a source with at most one row per person per period (``rows='person'``, from the publisher's own
documentation). From any other source lexflow publishes headcounts of rows and no pay.

Politeness: one session with the research User-Agent, 15-second timeouts, at least one second between two requests
to a host, a bounded retry on 429 and 503 that honours ``Retry-After``, and a row cap per dataset. robots.txt is
read once per host, its ``Crawl-delay`` honoured, and read as RFC 9309 says: a 5xx answer or an unreachable host
means complete disallow; so (more cautiously than the RFC) do 401, 403 and 429; other 4xx answers mean no rules.
Redirects are never followed blindly. Each hop is checked against robots.txt and spaced like any request, a hop to
another host is refused unless the registry lists that host for the dataset, and a hop from https to http is
refused. That includes robots.txt itself: RFC 9309 would follow its redirects to any host, but one to an unlisted
host is refused here, which leaves that host completely disallowed. Nothing here writes to any remote service.
"""
from __future__ import annotations

import csv
import io
import math
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Callable, Iterable
from urllib import robotparser
from urllib.parse import urljoin, urlsplit

import requests

Log = Callable[[str], None]

USER_AGENT = "lexflow-research/0.1 (https://github.com/alibama/lexflow)"
TIMEOUT = 15            # seconds per request
MIN_INTERVAL = 1.0      # seconds between two requests to one host
PAGE_SIZE = 5000        # rows per Socrata page
ROW_CAP = 50_000        # rows read per dataset in this prototype; reaching it marks the result truncated
MAX_RETRIES = 2         # extra tries after a 429 or 503
MAX_WAIT = 60.0         # never wait longer than this for a Retry-After
MAX_REDIRECTS = 5       # hops followed for one request (RFC 9309 asks crawlers to follow at least five)
REDIRECTS = (301, 302, 303, 307, 308)

CANONICAL = ("agency", "title", "pay", "pay_basis", "period")
REQUIRED = ("agency", "title", "pay")
PAY_BASES = ("annual", "hourly", "daily", "monthly", "paid_year")
COUNT = "row_count"     # alias of count(*) in a grouped Socrata query

# ---- the guard: column names that are, or can stand in for, a person ----------------------------------------
# A column name is split into lower-case words (snake_case, camelCase and digits). A glued word ("EMPLID",
# "POSITIONNUMBER", "EMAILADDRESS", "nickname") is split again into the words the guard knows; failing that, a
# trailing "name" or "nm", a trailing "number", "nbr" or "nr", and an ID suffix after a person-like prefix
# ("empno", "pernr") are split off. Then the words are judged.
#
# Two general rules do most of the work. A *name* column and an *ID or number* column are person-level unless the
# word that says whose name or ID it is (its owner: the word before it, or the word after "of") is organisational,
# and no word in the column names a person. So "department_name", "dept_nm", "agency_short_name", "dept_id" and
# "fund_number" pass, while "payee_name", "supervisor_name", "l_name", "name_of_employee", "id_of_employee",
# "payee_id", "position_number", "POSITIONID", "EMPLID" and "GlobalID" do not. A count is not an ID: a count word
# (number, no, num, nbr, nr) followed by "of", in a column with no person word, as in "number_of_employees".
#
# A column that is only a person word or a role ("last", "first", "staff", "supervisor", "manager",
# "department_head", "elected_official") holds names, and is refused too.
#
# On top of that, some categories are refused wherever they appear: demographics, dates of a person's career,
# tenure, home and contact details, and photos. "average_wage", "employee_status" and "home_department" pass;
# "age_group", "ssn_last4", "years_of_service", "time_in_grade" and "home_city" do not.
_NAME_WORDS = {"name", "names", "nm", "nme"}
_ID_WORDS = {"id", "ids", "identifier", "number", "nbr", "no", "num", "nr", "key", "hash", "hashed", "uid", "guid",
             "uuid"}
_COUNT_WORDS = {"number", "no", "num", "nbr", "nr"}     # "number_of_employees": a count, when no person word is in it
_PERSON_WORDS = {"first", "last", "middle", "mid", "given", "family", "sur", "maiden", "preferred", "nick",
                 "employee", "emp", "empl", "ee", "person", "personal", "worker", "staff", "member", "incumbent",
                 "individual", "user", "payee"}
# a column that ends in one of these holds a person's name ("supervisor", "department_head", "elected_official")
_ROLE_WORDS = {"supervisor", "supv", "supvr", "manager", "mgr", "officer", "official", "approver", "reviewer",
               "director", "head", "chief", "boss", "foreman", "holder", "occupant", "appointee", "contact"}
# whose name or ID it is, when that is an organisation, a place of work or a classification, not a person
_ORG_OWNERS = {"department", "dept", "dpt", "agency", "agcy", "office", "division", "div", "unit", "bureau", "org",
               "organization", "organisation", "organizational", "fund", "program", "programme", "project", "union",
               "bargaining", "location", "loc", "site", "facility", "building", "cost", "center", "centre", "budget",
               "account", "acct", "authority", "employer", "entity", "government", "gov", "govt", "district", "board",
               "commission", "branch", "section", "group", "area", "region", "city", "county", "state", "title",
               "class", "classification", "grade", "occupation", "series", "schedule", "plan", "category", "type",
               "status", "code", "period", "year", "fiscal", "quarter", "month", "week"}
_ID_OWNERS = _ORG_OWNERS                            # a job or position number can stand for one person: not here
_NAME_OWNERS = _ORG_OWNERS | {"job", "position", "pos", "description", "desc"}
_MODIFIERS = {"short", "long", "abbreviated", "abbr", "abbrev", "official", "display", "legal", "full", "common",
              "alt", "alternate", "primary", "secondary", "current", "previous", "prior", "old", "new"}
_GLUE_PREFIXES = _PERSON_WORDS | {"per", "pers", "personnel", "badge", "record", "rec", "row", "object", "obj",
                                  "global", "unique", "file", "employ", "emply"}
_GLUE_ID = ("number", "num", "nbr", "nr", "no", "id", "key")
_GLUE_NAME = ("name", "nm")
_GLUE_NUMBER = ("number", "nbr", "nr")    # split off after any prefix: "...number" is always a number of something
_INITIALS = {"init", "initial", "initials", "mi"}
_SOLO = {   # a column that is just one of these words
    "fname", "lname", "mname", "firstname", "lastname", "middlename", "fullname", "surname", "givenname", "familyname",
    "nickname", "empname", "employeename", "empnm", "midinit", "middleinitial", "employee", "emp", "empl", "person",
    "worker", "payee", "emplid", "empid", "employeeid", "eeid", "staffid", "personid", "empno", "empnum",
    "employeenumber", "pernr", "persno", "badge", "badgeno", "objectid", "globalid", "rowid", "uniqueid", "fid", "oid",
    "hiredate", "startdate", "titledate", "termdate", "servicedate", "years", "yrs", "start", "begin"}
_ANYWHERE = {"sex", "sexual", "orientation", "race", "racial", "age", "dob", "yob", "doh", "ssn", "address",
             "addresses", "addr", "street", "zip", "zipcode", "postal", "postcode", "phone", "telephone", "tel",
             "mobile", "fax", "email", "emails", "mail", "mailing", "residence", "residential", "passport", "pronoun",
             "pronouns", "seniority", "tenure", "longevity", "yos", "incumbent", "spouse", "beneficiary", "photo",
             "photos", "photograph", "picture", "pic", "headshot", "avatar", "image", "signature", "biometric",
             "fingerprint", "vet", "vets", "hispanic", "latino", "latina", "latinx"}
_INSIDE = ("hire", "birth", "gender", "gndr", "ethnic", "separat", "terminat", "hash", "ssn", "veteran", "disab",
           "marital", "religio", "nationalit", "citizen", "phone", "email")   # inside a word: "rehire", "gender_cd"
_TENURE = {"service", "svc", "serv", "srv", "employment", "experience", "tenure", "seniority"}
_SPANS = {"years", "yrs", "year", "length", "len", "months", "mos", "time", "duration", "anniversary"}
_HOME = {"home", "residence", "residential", "resident", "residency"}
_PLACES = {"city", "town", "state", "county", "country", "zip", "postal", "address", "street", "phone", "email",
           "location", "loc", "region", "area", "district", "parish", "borough"}
_DATE_WORDS = {"date", "dt", "dte", "datetime", "timestamp"}
_PERSON_DATES = {"start", "begin", "title", "service", "seniority", "anniversary", "appointment", "appointed",
                 "promotion", "step", "retirement", "retire", "entry", "assignment", "effective", "original", "orig",
                 "hire"}
_ENDS_OF = {"position", "job", "employment", "service", "contract", "assignment"}
_EDGES = {"start", "begin", "end", "entry", "exit"}     # with _ENDS_OF, a person's career edge: "employment_start"
# The words a glued column name is split into. Short words that occur inside ordinary words (such as "pa", "us",
# "over") are left out on purpose, so "paid", "usage" and "overtime" stay whole.
_VOCAB = frozenset(
    t for group in (_NAME_WORDS, _ID_WORDS, _PERSON_WORDS, _ROLE_WORDS, _ORG_OWNERS, _NAME_OWNERS, _MODIFIERS,
                    _GLUE_PREFIXES, _INITIALS, _ANYWHERE, _TENURE, _SPANS, _HOME, _PLACES, _DATE_WORDS,
                    _PERSON_DATES, _ENDS_OF, _EDGES,
                    {"of", "in", "pay", "payroll", "check", "cheque", "rate", "salary", "base", "count", "total",
                     "amount", "line", "work", "cell", "card", "clock", "roster", "group", "status", "badge", "elected",
                     "grade", "rank", "step", "role"})
    for t in group if t.isalpha() and len(t) >= 2)


def _words(col: str) -> list[str]:
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", col)
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", s)
    return re.findall(r"[a-z]+|\d+", s.lower())


def _segment(t: str) -> list[str] | None:
    """Split a glued word into words of ``_VOCAB``, fewest pieces first ("positionnumber" -> position, number;
    "emailaddress" -> email, address); None when it cannot be covered completely."""
    best: list[list[str] | None] = [[]] + [None] * len(t)
    for i in range(len(t)):
        if best[i] is None:
            continue
        for j in range(i + 2, len(t) + 1):
            piece = t[i:j]
            if piece in _VOCAB and (best[j] is None or len(best[i]) + 1 < len(best[j])):
                best[j] = best[i] + [piece]
    return best[-1]


def _unglue(t: str) -> list[str]:
    """Split a glued word. First into known words ("POSITIONID", "PAYROLLID", "STARTDT", "AGEGROUP"); failing that,
    a trailing "...name" or "...nm" ("nickname"), a trailing "...number", "...nbr" or "...nr" whatever comes before
    it, and an ID suffix after a person-like prefix ("emplid", "empno", "pernr"). "paid" and "deptid" stay whole,
    or split into organisational words."""
    if t in _VOCAB:
        return [t]
    seg = _segment(t)
    if seg:
        return seg
    for s in _GLUE_NAME:
        if t.endswith(s) and len(t) > len(s):
            return [t[:-len(s)], s]
    for s in _GLUE_NUMBER:
        if t.endswith(s) and len(t) > len(s):
            return [t[:-len(s)], s]
    for s in _GLUE_ID:
        if t.endswith(s) and t[:-len(s)] in _GLUE_PREFIXES:
            return [t[:-len(s)], s]
    return [t]


def _is_count(w: list[str]) -> bool:
    """A count of people, not an ID: a count word followed by "of", and no person word ("number_of_employees",
    "no_of_positions"; not "number_of_employee" or "id_of_employee")."""
    return (not set(w) & _PERSON_WORDS
            and any(t in _COUNT_WORDS and i + 1 < len(w) and w[i + 1] == "of" for i, t in enumerate(w)))


def _owner(w: list[str], i: int) -> str | None:
    """Whose name or ID ``w[i]`` is: the nearest word before it that is not a modifier ("agency_short_name"), or,
    when it comes first, the word after "of" ("name_of_employee") or else the next word ("name_last")."""
    j = i - 1
    while j >= 0 and w[j] in _MODIFIERS:
        j -= 1
    if j >= 0:
        return w[j]
    if i + 2 < len(w) and w[i + 1] == "of":
        return w[i + 2]
    return w[i + 1] if i + 1 < len(w) else None


def looks_person_level(col: str) -> bool:
    """True for a column name that is, or can stand in for, a person.

    General rules: a name column, or an ID or number column, is person-level unless its owner word (see
    :func:`_owner`) is organisational and no word in it names a person; only a count ("number_of_employees", see
    :func:`_is_count`) is exempt from the ID rule. A column made only of person words ("last", "last_first",
    "staff") or ending in a role ("supervisor", "department_head", "elected_official") holds names. Also refused
    wherever they appear: initials; birth, age, sex, sexual orientation, gender, race and ethnicity; veteran,
    disability and marital status; hire, start, title, service and separation dates, and the start or end of a
    job or of employment; tenure (seniority, longevity, years or length of service, time in grade); home and
    contact details; photos and signatures. Glued words are split first (:func:`_unglue`).

    It knows common spellings, not every one, and it errs towards refusing: a column it passes is not proven
    safe. The ``fields`` allowlist is the protection; this is a second check.
    """
    raw = [t for t in _words(col) if not t.isdigit()] or _words(col)
    w = [p for t in raw for p in _unglue(t)]
    if not w:
        return True                                     # an empty or symbol-only name is not a column we can judge
    ws = set(w)
    if len(w) == 1 and (w[0] in _SOLO or w[0] in _NAME_WORDS or w[0] in _ID_WORDS or w[0] in _INITIALS):
        return True
    if all(t in _PERSON_WORDS or t in _MODIFIERS for t in w) and ws & _PERSON_WORDS:
        return True                                     # "last", "first", "middle", "last_first", "staff"
    if w[-1] in _ROLE_WORDS or (len(w) == 1 and w[0].endswith("s") and w[0][:-1] in _ROLE_WORDS):
        return True                                     # "supervisor", "department_head", "officers"; not "officer_count"
    if any(t in _ANYWHERE or any(p in t for p in _INSIDE) for t in w):
        return True
    counted = _is_count(w)
    for i, t in enumerate(w):
        if t in _NAME_WORDS and (ws & _PERSON_WORDS or _owner(w, i) not in _NAME_OWNERS):
            return True                                 # "first_name", "payee_name", "l_name", "name_of_employee"
        if t in _ID_WORDS and not counted and (ws & _PERSON_WORDS or _owner(w, i) not in _ID_OWNERS):
            return True                                 # "emp_id", "id_of_employee", "position_number", "GlobalID"
        near = set(w[max(i - 1, 0):i]) | set(w[i + 1:i + 2])
        if t in _INITIALS and near & {"mid", "middle", "first", "last", "name"}:
            return True
        if t in _SPANS and i + 1 < len(w) and w[i + 1] == "in":
            return True                                 # "time_in_grade", "years_in_title"
    if ws & _TENURE and ws & _SPANS:
        return True                                     # "years_of_service", "length_of_service", "yrs_svc"
    if ws & _HOME and ws & _PLACES:
        return True                                     # "home_city", "home_phone", "resident_state"; not "home_department"
    if ws & _EDGES and ws & _ENDS_OF:
        return True                                     # "employment_start", "position_end_date"
    if ws & _DATE_WORDS and ws & _PERSON_DATES:
        return True                                     # "agency_start_date", "title_date", "begin_date", "STARTDT"
    return False


@dataclass
class Dataset:
    id: str
    state: str
    government: str                  # the publishing government, as lexflow's governments table names it
    gov_id: str | None               # lexflow / Census 14-digit ID; None for a state-wide source
    publisher: str
    title: str
    url: str                         # the dataset's landing page: what answers link to
    api: str                         # soda | csv | arcgis | ckan | web
    endpoint: str | None             # the machine endpoint, when there is one
    licence: str
    cadence: str
    person_level: bool               # rows describe individual employees, named or not: keep aggregates only
    ingest: str = "aggregate"        # aggregate (rows -> lexflow aggregates) | as-is (already aggregate) | link | none
    fetch: bool = False              # read by this prototype
    fields: dict = field(default_factory=dict)       # canonical name -> source column
    drop: tuple[str, ...] = ()       # person-level or quasi-identifying columns the source has: never read
    pay_basis: str | None = None     # fixed pay basis, when no column gives it
    basis_map: dict = field(default_factory=dict)    # source pay-basis value -> one of PAY_BASES
    where: str | None = None         # a SoQL filter (a pay basis, a year, an employment type)
    period: str | None = None        # a fixed period label; otherwise the period column, or "as of <date>"
    period_format: str = "{}"        # how a period column's value is labelled, e.g. "FY{}"
    hourly_below: float | None = None   # the pay column mixes bases: an "annual" figure below this is an hourly rate
    fields_checked: str | None = None   # the date the field names were read from the publisher's schema
    # What one row is, for the counts. "person": at most one row per person per period, as the publisher's own
    # documentation says (the notes say where). "unknown": a person may appear more than once (two jobs, appended
    # quarters), so a count of rows is not a count of people, and lexflow publishes no pay from it (aggregate.py).
    rows: str = "unknown"
    notes: str = ""


ROWS = ("person", "unknown")


def check_fields(ds: Dataset) -> Dataset:
    """Refuse a fields map that names an unknown canonical field or points at a person-level column."""
    for canon, col in ds.fields.items():
        if canon not in CANONICAL:
            raise ValueError(f"{ds.id}: unknown canonical field {canon!r}")
        if looks_person_level(col) or col in ds.drop:
            raise ValueError(f"{ds.id}: {canon!r} maps to {col!r}, which looks person-level; lexflow never reads it")
    if ds.rows not in ROWS:
        raise ValueError(f"{ds.id}: rows must be one of {ROWS}, not {ds.rows!r}")
    if ds.fetch:
        missing = [c for c in REQUIRED if c not in ds.fields]
        if missing:
            raise ValueError(f"{ds.id}: a fetched dataset needs {missing}")
        if not ds.pay_basis and "pay_basis" not in ds.fields:
            raise ValueError(f"{ds.id}: say the pay basis ({', '.join(PAY_BASES)}) or map a column to it")
        if ds.pay_basis and ds.pay_basis not in PAY_BASES:
            raise ValueError(f"{ds.id}: unknown pay basis {ds.pay_basis!r}")
        if ds.hourly_below and ds.pay_basis != "annual":
            raise ValueError(f"{ds.id}: hourly_below splits an annual column; set pay_basis='annual'")
        if ds.ingest != "aggregate" or not ds.endpoint or ds.api not in ("soda", "csv"):
            raise ValueError(f"{ds.id}: only soda or csv aggregate sources with an endpoint can be fetched")
    return ds


# Checked 2026-10-10 unless noted. Field names marked with ``fields_checked`` were read from the publisher's own
# schema (Socrata /api/views/<id>.json, ArcGIS ?f=json). Entries with ``fetch=False`` say why in ``notes``.
REGISTRY: list[Dataset] = [
    # ---- read by this prototype -----------------------------------------------------------------------------
    Dataset("va-norfolk-salaries", "va", "City of Norfolk", "47212200100000",
            "City of Norfolk, Department of Human Resources", "Employee Salaries",
            "https://data.norfolk.gov/d/4fsk-z8s8", "soda", "https://data.norfolk.gov/resource/4fsk-z8s8.json",
            "Public Domain", "daily", person_level=True, fetch=True,
            fields={"agency": "department", "title": "job_title", "pay": "annual_base_rate"},
            drop=("start_date", "title_date"), pay_basis="annual", hourly_below=1000.0, fields_checked="2026-10-10",
            notes="No names or IDs. Hire and title dates are never read. Whether anyone has two rows (two jobs) "
                  "is not stated: the publisher's description (read 2026-10-10) says only that the dataset "
                  "'provides base salary information about City of Norfolk employees', so rows='unknown' and no "
                  "pay is published from a fetch until a person confirms one row per employee with the "
                  "publisher. 'Base Salary' holds hourly "
                  "rates for temporary, part-time, retiree, sheriff and state-compensated staff (all under $200 "
                  "an hour on 2026-10-10) and annual salaries for everyone else (none between $200 and $5,000), "
                  "so a figure under 1,000 is read as hourly. The annual basis pools full-time and part-time "
                  "salaried staff, elected officials and council appointees; the Employee Status column could "
                  "separate them but is not read. A daily snapshot, so the period is the retrieval date. The "
                  "portal links no terms page (its footer 'Terms' link answered 404 on 2026-10-10), so the "
                  "licence rests on the dataset's own metadata: Public Domain."),
    Dataset("wa-seattle-wages", "wa", "City of Seattle", "48201702100000",
            "City of Seattle, Seattle Department of Human Resources", "City of Seattle Wage Data",
            "https://data.seattle.gov/d/2khk-5ukd", "soda", "https://data.seattle.gov/resource/2khk-5ukd.json",
            "Public Domain", "monthly", person_level=True, fetch=True,
            fields={"agency": "department", "title": "job_title", "pay": "hourly_rate"},
            drop=("first_name", "last_name"), pay_basis="hourly", fields_checked="2026-10-10",
            notes="Names at source; the query never selects them. Hourly rates only. The publisher notes that "
                  "exclusions may apply for vulnerable populations. Whether anyone has two rows (two jobs) is not "
                  "stated: the description (read 2026-10-10) says only 'Wage and classification information of "
                  "City of Seattle Employees', and checking would mean querying the name columns, so "
                  "rows='unknown' and no "
                  "pay is published from a fetch until a person confirms one row per employee with the "
                  "publisher. The portal links no terms page (its footer "
                  "'Terms' link answered 404 on 2026-10-10), so the licence rests on the dataset's own metadata: "
                  "Public Domain."),
    Dataset("ca-sf-compensation", "ca", "City and County of San Francisco", "05203800100000",
            "City and County of San Francisco, Controller's Office", "Employee Compensation",
            "https://data.sf.gov/d/88g8-5mnd", "soda", "https://data.sf.gov/resource/88g8-5mnd.json",
            "Open Data Commons Public Domain Dedication and Licence (PDDL)", "twice a year",
            person_level=True,
            fields={"agency": "department", "title": "job", "pay": "salaries", "period": "year"},
            drop=("employee_identifier",), pay_basis="paid_year", period_format="FY{}",
            where="year_type='Fiscal' AND `year`='2026' AND starts_with(employment_type, 'Permanent')",
            fields_checked="2026-10-10",
            notes="Each row carries a per-employee identifier, but one row per employee per year is not "
                  "confirmed from the publisher's own documentation, so rows='unknown'. That column is labelled "
                  "'Employee Name' in the "
                  "schema and is never selected. Pay is regular salary actually paid in the fiscal year, so it "
                  "barely repeats and a grouped query still returns about one row per person (35,600 for FY2026 "
                  "permanent staff). On 2026-10-10 the anonymous query was refused with HTTP 428 at offset "
                  "25,000, so the prototype does not read it. It needs an app token, or headcount by "
                  "department and job with the median computed on the server. The portal moved from "
                  "data.sfgov.org, which now answers HTTP 301 to data.sf.gov (checked 2026-10-10); data.sf.gov's "
                  "robots.txt sets Crawl-delay: 1."),

    # ---- registered, not read by the prototype --------------------------------------------------------------
    Dataset("dc-public-employee-salary", "dc", "City of Washington DC", "09200100100000",
            "District of Columbia, OCTO (from DCHR)", "DC Public Employee Salary",
            "https://opendata.dc.gov/datasets/DCGIS::dc-public-employee-salary", "arcgis",
            "https://maps2.dcgis.dc.gov/dcgis/rest/services/DCGIS_DATA/Government_Operations/MapServer/35",
            "CC BY 4.0", "snapshot (last modified 26 Sep 2024)", person_level=True,
            fields={"agency": "DESCRSHORT", "title": "JOBTITLE", "pay": "COMPRATE"},
            drop=("FIRST_NAME", "LAST_NAME", "HIREDATE_STRING", "OBJECTID"), pay_basis="annual", hourly_below=1000.0,
            fields_checked="2026-10-10",
            notes="COMPRATE mixes hourly and annual rates and has no basis column (hence hourly_below); ArcGIS "
                  "refused percentile statistics. Use outStatistics counts by agency and title before enabling. "
                  "Stale: link only until DC republishes."),
    Dataset("il-chicago-employees", "il", "City of Chicago", "14201601600000", "City of Chicago",
            "Current Employee Names, Salaries, and Position Titles", "https://data.cityofchicago.org/d/xzkq-xp2w",
            "soda", "https://data.cityofchicago.org/resource/xzkq-xp2w.json",
            "City of Chicago data portal terms (a required disclaimer, stop-use and indemnity clauses)",
            "daily", person_level=True,
            fields={"agency": "department", "title": "job_titles", "pay": "annual_salary"},
            drop=("name",), pay_basis="annual", where="salary_or_hourly='Salary'", fields_checked="2026-10-10",
            notes="The terms (readable through chicago.gov on 2026-10-10) require a set disclaimer on any "
                  "application built on the data, let the City demand that the use stop, and contain an "
                  "indemnity: an operator decision, so not fetched. Hourly staff need a second query on "
                  "hourly_rate. Check the case of 'Salary'."),
    Dataset("ny-nyc-payroll", "ny", "City of New York", "33203100100000", "City of New York, Office of Payroll "
            "Administration", "Citywide Payroll Data (Fiscal Year)", "https://data.cityofnewyork.us/d/k397-673e",
            "soda", "https://data.cityofnewyork.us/resource/k397-673e.json", "not stated (NYC Open Data terms)",
            "annual", person_level=True,
            fields={"agency": "agency_name", "title": "title_description", "pay": "base_salary",
                    "pay_basis": "pay_basis", "period": "fiscal_year"},
            basis_map={"per Annum": "annual", "per Hour": "hourly", "per Day": "daily", "Prorated Annual": "annual"},
            drop=("last_name", "first_name", "mid_init", "agency_start_date"), period_format="FY{}",
            fields_checked="2026-10-10",
            notes="Millions of rows: filter one fiscal year and leave status 'ACTIVE'. NYC Open Data terms not "
                  "read (they sit on www.nyc.gov, whose robots.txt answered 403, so they were not requested): a "
                  "person reads them before enabling. The pay-basis values in basis_map are to be confirmed."),
    Dataset("ny-nyc-position-schedule", "ny", "City of New York", "33203100100000", "City of New York, Office of "
            "Management and Budget", "Position Schedule", "https://data.cityofnewyork.us/d/f4wx-5ve6", "soda",
            "https://data.cityofnewyork.us/resource/f4wx-5ve6.json", "not stated (NYC Open Data terms)",
            "twice a year", person_level=False, ingest="as-is",
            fields={"agency": "agency_name", "title": "title_code_name"}, fields_checked="2026-10-10",
            notes="Already aggregate: positions, minimum, maximum and mean salary per title and unit of "
                  "appropriation. Load the position counts only. The minimum and maximum are each one "
                  "position's pay, and a mean can be differenced, so they are not republished unless a person "
                  "decides otherwise. NYC Open Data terms not read (see ny-nyc-payroll)."),
    Dataset("ny-nyc-headcount", "ny", "City of New York", "33203100100000", "City of New York, Office of Management "
            "and Budget", "Full-Time and FTE Headcount including Covered Organizations",
            "https://data.cityofnewyork.us/d/84ax-hg3y", "soda", "https://data.cityofnewyork.us/resource/84ax-hg3y.json",
            "not stated (NYC Open Data terms)", "twice a year", person_level=False, ingest="as-is",
            fields={"agency": "agency_name", "period": "fyear"}, fields_checked="2026-10-10",
            notes="Already aggregate: headcount by agency, fiscal year and personnel type. NYC Open Data terms "
                  "not read (see ny-nyc-payroll)."),
    Dataset("ca-la-city-payroll", "ca", "City of Los Angeles", "05201902700000", "City of Los Angeles, Controller",
            "City Employee Payroll (Current)", "https://controllerdata.lacity.org/d/g9h8-fvhu", "soda",
            "https://controllerdata.lacity.org/resource/g9h8-fvhu.json", "CC BY 4.0", "bi-weekly",
            person_level=True,
            fields={"agency": "fms_department_title", "title": "job_title", "pay": "regular_pay", "period": "pay_year"},
            drop=("record_nbr", "last_name", "first_name", "gender", "ethnicity", "row_id"), pay_basis="paid_year",
            fields_checked="2026-10-10",
            notes="Names, gender and ethnicity at source: never selected, never grouped by. Large; filter one "
                  "pay_year first."),
    Dataset("md-montgomery-salaries-2025", "md", "Montgomery County", "21101601500000", "Montgomery County, MD",
            "Employee Salaries - 2025", "https://data.montgomerycountymd.gov/d/4rpu-n3ya", "soda",
            "https://data.montgomerycountymd.gov/resource/4rpu-n3ya.json", "not stated (portal terms not found)",
            "annual (one dataset a year)", person_level=True,
            fields={"agency": "department_name", "title": "grade", "pay": "base_salary"},
            drop=("gender",), pay_basis="annual", period="2025", fields_checked="2026-10-10",
            notes="No names, but a gender column (never read). The grade is the class. Terms not found or "
                  "unclear: the portal's Terms of Use link (/page/terms-of-use) and the county's /disclaimer "
                  "answered 404 on 2026-10-10, and the county's site-wide User Rights terms (warranty "
                  "disclaimers, no indemnity, sites described as maintained for personal use) may not cover the "
                  "data portal. Not fetched until a person reads the portal's terms."),
    Dataset("il-cook-county-payroll", "il", "Cook County", "14101601600000", "Cook County, Comptroller",
            "Employee Payroll", "https://datacatalog.cookcountyil.gov/d/xu6t-uvny", "soda",
            "https://datacatalog.cookcountyil.gov/resource/xu6t-uvny.json", "Public Domain",
            "labelled quarterly; last updated June 2018", person_level=True,
            fields={"agency": "office_name", "title": "job_title", "pay": "base_pay", "period": "fiscal_year"},
            drop=("first_name", "last_name", "middle_init", "position_id", "employee_identifier",
                  "original_hire_date"), fields_checked="2026-10-10",
            notes="Stale since 2018: link only. The pay basis of base_pay (quarterly or annual) is not "
                  "documented. If it is ever enabled, filter one fiscal year: pay is published for one period "
                  "per fetch, so other years would get headcounts only."),
    Dataset("ny-state-authorities-salaries", "ny", "New York State public authorities", None,
            "New York State Authorities Budget Office", "Salary Information for State Authorities",
            "https://data.ny.gov/d/unag-2p27", "soda", "https://data.ny.gov/resource/unag-2p27.json",
            "not stated (data.ny.gov terms)", "annual", person_level=True,
            fields={"agency": "authority_name", "title": "title", "pay": "base_annualized_salary",
                    "period": "fiscal_year_end_date"},
            drop=("last_name", "middle_initial", "first_name"), pay_basis="annual", fields_checked="2026-10-10",
            notes="Each authority is an agency, not a government. It covers eight fiscal years: filter one "
                  "fiscal year, since pay is published for one period per fetch and other years would get "
                  "headcounts only. data.ny.gov's terms are a PDF that was not downloaded: a person reads them "
                  "before enabling."),
    Dataset("ny-civil-service-titles", "ny", "State of New York", None, "New York State Department of Civil Service",
            "Title and Salary Listing", "https://data.ny.gov/d/t3vp-5tka", "soda",
            "https://data.ny.gov/resource/t3vp-5tka.json", "not stated (data.ny.gov terms)", "twice a year",
            person_level=False, ingest="as-is", fields={"agency": "agency_description", "title": "title_name"},
            fields_checked="2026-10-10",
            notes="Already aggregate: filled positions per title and agency, with the grade (a pay scale). "
                  "data.ny.gov's terms (a PDF) not read (see ny-state-authorities-salaries)."),
    Dataset("nc-charlotte-salaries", "nc", "City of Charlotte", "34206000100000", "City of Charlotte",
            "City of Charlotte Employee Salaries",
            "https://hub.arcgis.com/datasets/2eaeb9bbc40c4bc6816170ba08e71021_1", "arcgis",
            "https://gis.charlottenc.gov/arcgis/rest/services/ODP/CityofCharlotteEmployeeSalaries/MapServer/1",
            "CC BY 4.0", "quarterly, appended", person_level=True,
            fields={"agency": "Dept", "title": "Job_Title", "pay": "Annual_Rt", "period": "Year"},
            drop=("OBJECTID", "Name"), pay_basis="annual", fields_checked="2026-10-10",
            notes="ArcGIS: aggregate with outStatistics on the server (counts; percentiles may be refused). "
                  "Filter one Year and Quarter."),
    Dataset("md-baltimore-salaries", "md", "City of Baltimore", "21200400100000", "City of Baltimore (Open Baltimore)",
            "Baltimore City Employee Salaries", "https://hub.arcgis.com/datasets/0bceed42ed994e65bec410bdf9c383c8_0",
            "arcgis", None, "not stated", "annual (employees on payroll on 30 June)", person_level=True,
            notes="Names and hire dates at source. Read the layer schema before writing a fields map."),
    Dataset("tx-houston-payroll", "tx", "City of Houston", "44210100800000",
            "City of Houston, Administration and Regulatory Affairs", "Payroll",
            "https://data.houstontx.gov/dataset/payroll", "ckan", None, "Open Data Commons Attribution", "yearly files",
            person_level=True, ingest="none",
            notes="'Anonymized' rows carry hashed IDs with birth year, gender, race and exact position dates: "
                  "re-identifiable. Skip until a grouped server-side query is confirmed."),
    Dataset("tx-dallas-payroll-registry", "tx", "City of Dallas", "44205700700000", "City of Dallas",
            "Payroll Registry", "https://www.dallasopendata.com/d/qrgv-mijx", "soda",
            "https://www.dallasopendata.com/resource/qrgv-mijx.json", "not stated", "last updated Oct 2019",
            person_level=False, ingest="as-is",
            notes="Already aggregate (employee count and gross payroll per pay period), but stale since 2019: "
                  "link only. Field names not read."),
    Dataset("va-virginia-beach-salaries", "va", "City of Virginia Beach", "47213200100000",
            "City of Virginia Beach, Human Resources", "Employee Salaries",
            "https://hub.arcgis.com/datasets/33c808ff26ed445c88de2b3f1fc4929e_0", "arcgis", None,
            "custom terms (data.virginiabeach.gov)", "frequent (modified 5 Oct 2026)", person_level=True,
            notes="Position IDs with hire dates at source. Its 'About this Site' terms were not read: a person "
                  "reads them before enabling."),
    Dataset("fl-miami-roster", "fl", "City of Miami", "10201301300000", "City of Miami", "City Employee Roster",
            "https://hub.arcgis.com/datasets/421065367dc342888cddabc106e09722_0", "arcgis", None, "CC BY 4.0",
            "bi-weekly", person_level=True, notes="Names at source. Read the layer schema first."),
    Dataset("fl-miami-dade-pay", "fl", "Miami-Dade County", "10101301300000", "Miami-Dade County",
            "Miami Dade County Employee Pay Information",
            "https://hub.arcgis.com/datasets/3d3cafbe1aed46e9b1e0f2ec6f429756_0", "arcgis", None,
            "'as is' disclaimer", "modified Sep 2026", person_level=True,
            notes="Names at source. Five constitutional offices left this payroll on 7 Jan 2025."),
    Dataset("ca-la-county-salaries", "ca", "Los Angeles County", "05101901900000", "Los Angeles County, "
            "Auditor-Controller", "LA County Employee Salaries",
            "https://hub.arcgis.com/datasets/1fefbd3af4cf41fda827f2c23a1fe09b_0", "arcgis", None, "not stated",
            "yearly (modified 31 Aug 2026)", person_level=True, notes="Names at source; 1.41 million rows."),

    # ---- state search tools: person-level, linked from answers, never read -----------------------------------
    Dataset("va-datapoint-salaries", "va", "Commonwealth of Virginia", None, "Auditor of Public Accounts",
            "Commonwealth Data Point: Salaries", "https://datapoint.apa.virginia.gov/salaries.php", "web", None,
            "not stated", "by fiscal year", person_level=True, ingest="link",
            notes="Per employee (a record ID, no names). Va. Code § 2.2-3705.1(1)."),
    Dataset("il-comptroller-salaries", "il", "State of Illinois", None, "Illinois Comptroller", "Salary database",
            "https://illinoiscomptroller.gov/financial-reports-data/data-sets-portals/salary-database", "web", None,
            "not stated", "current", person_level=True, ingest="link",
            notes="Search by name; the agency summary gives counts and YTD gross by agency."),
    Dataset("wa-fiscal-salaries", "wa", "State of Washington", None, "LEAP Committee and OFM",
            "State employee salaries", "https://fiscal.wa.gov/Staffing/Salaries", "web", None, "not stated",
            "annual", person_level=True, ingest="link",
            notes="The bulk file is sent on an emailed request that asks for a name: an operator decision."),
    Dataset("nc-osc-salaries", "nc", "State of North Carolina", None, "NC Office of the State Controller",
            "State Employee Salary Database", "https://ncosc.gov/salary_database", "web", None,
            "terms read: non-commercial copying allowed, unaltered and with a citation", "monthly",
            person_level=True, ingest="link", notes="G.S. 126-23. Link only, which its terms allow."),
    Dataset("fl-right-to-know-payroll", "fl", "State of Florida", None, "State of Florida",
            "Florida Has a Right to Know: state payroll search",
            "https://floridahasarighttoknow.myflorida.com/search_state_payroll", "web", None, "not stated",
            "not verified", person_level=True, ingest="link",
            notes="robots.txt disallows all but named search engines: link only, never request it."),
    Dataset("ca-publicpay", "ca", "State of California", None, "California State Controller",
            "Government Compensation in California", "https://gcc.sco.ca.gov/", "web", None, "not stated",
            "yearly reports", person_level=True, ingest="link",
            notes="Positions without names. publicpay.ca.gov now redirects here; on 2026-10-10 this host answered "
                  "HTTP 200 and its robots.txt allowed the research client. Link only: read its terms before any "
                  "bulk download."),
]

BY_ID: dict[str, Dataset] = {d.id: check_fields(d) for d in REGISTRY}


def get(dataset_id: str) -> Dataset:
    return BY_ID[dataset_id]


def fetchable() -> list[Dataset]:
    return [d for d in REGISTRY if d.fetch]


def links(state: str, gov_id: str | None = None) -> list[Dataset]:
    """Official sources an answer may link to for a person-level question: the government's own, then the state's."""
    own = [d for d in REGISTRY if gov_id and d.gov_id == gov_id and d.ingest != "none"]
    return own + [d for d in REGISTRY if d.state == state and d.gov_id is None and d.ingest == "link"]


# ---- reading rows -------------------------------------------------------------------------------------------

def parse_pay(value) -> float | None:
    """A positive pay figure, or None. Accepts numbers and strings such as '$52,000.00'."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        x = float(value)
    else:
        try:
            x = float(re.sub(r"[,$\s]", "", str(value)))
        except ValueError:
            return None
    return x if math.isfinite(x) and x > 0 else None


def project(row: dict, ds: Dataset, *, counted: bool = False) -> dict:
    """The mapped fields of one source row, and nothing else. Every other column is dropped here, at read time."""
    out = {canon: row.get(col) for canon, col in ds.fields.items()}
    if "pay_basis" in out:
        raw = str(out["pay_basis"] or "").strip()
        out["pay_basis"] = ds.basis_map.get(raw, raw.lower() or None)
    elif ds.pay_basis:
        out["pay_basis"] = ds.pay_basis
    if ds.hourly_below and out.get("pay_basis") == "annual":
        x = parse_pay(out.get("pay"))
        if x is not None and x < ds.hourly_below:
            out["pay_basis"] = "hourly"
    n = row.get(COUNT) if counted else None
    out["n"] = int(float(n)) if n not in (None, "") else 1
    return out


def _q(col: str) -> str:
    return f"`{col}`"


def soda_params(ds: Dataset, *, grouped: bool = True, limit: int = PAGE_SIZE, offset: int = 0) -> dict:
    """A SoQL query for the mapped columns only. Grouped, the publisher counts identical rows and sends each once."""
    cols = [_q(c) for c in dict.fromkeys(ds.fields.values())]
    p: dict = {}
    if grouped:
        p["$select"] = ", ".join(cols + [f"count(*) AS {COUNT}"])
        p["$group"] = ", ".join(cols)
        p["$order"] = ", ".join(cols)
    else:
        p["$select"] = ", ".join(cols)
        p["$order"] = ":id"
    if ds.where:
        p["$where"] = ds.where
    p["$limit"] = limit
    p["$offset"] = offset
    return p


def read_csv_rows(lines: Iterable[str], ds: Dataset, *, row_cap: int = ROW_CAP) -> tuple[list[dict], bool]:
    """Project each CSV row as it is parsed. Returns (rows, truncated)."""
    reader = csv.DictReader(lines)
    missing = [c for c in ds.fields.values() if c not in (reader.fieldnames or [])]
    if missing:
        raise ValueError(f"{ds.id}: the CSV has no column {missing}")
    rows: list[dict] = []
    for i, row in enumerate(reader):
        if i >= row_cap:
            return rows, True
        rows.append(project(row, ds))
    return rows, False


# ---- polite HTTP --------------------------------------------------------------------------------------------

def _retry_after(value: str | None, default: float) -> float:
    if not value:
        return default
    try:
        return max(0.0, float(value))
    except ValueError:
        pass
    try:
        return max(0.0, (parsedate_to_datetime(value) - datetime.now(timezone.utc)).total_seconds())
    except (TypeError, ValueError):
        return default


def _host(url: str) -> str:
    return urlsplit(url).netloc.lower()


def listed_hosts(ds: Dataset) -> set[str]:
    """The hosts the registry lists for a dataset (its landing page and endpoint): the only redirect targets."""
    return {_host(u) for u in (ds.url, ds.endpoint) if u}


class Http:
    """GET only. One request at a time per host, at least ``min_interval`` (or the site's Crawl-delay) apart.

    Redirects are followed by hand (``allow_redirects=False``), so every hop is checked: against robots.txt for its
    host, against the per-host spacing, against the hosts the caller allows, and against a downgrade to http.
    """

    def __init__(self, session: requests.Session | None = None, *, min_interval: float = MIN_INTERVAL,
                 timeout: float = TIMEOUT, sleep: Callable[[float], None] = time.sleep,
                 clock: Callable[[], float] = time.monotonic, log: Log = print):
        self.session = session or requests.Session()
        self.min_interval, self.timeout = min_interval, timeout
        self.sleep, self.clock, self.log = sleep, clock, log
        self._last: dict[str, float] = {}
        self._gap: dict[str, float] = {}
        self._robots: dict[str, robotparser.RobotFileParser] = {}
        self._why: dict[str, str] = {}                  # host -> why its robots.txt means complete disallow
        self.requests = 0

    def _wait(self, host: str) -> None:
        last = self._last.get(host)
        if last is not None:
            left = last + self._gap.get(host, self.min_interval) - self.clock()
            if left > 0:
                self.sleep(left)
        self._last[host] = self.clock()

    def _send(self, url: str, params: dict | None = None, stream: bool = False) -> requests.Response:
        host = _host(url)
        for attempt in range(MAX_RETRIES + 1):
            self._wait(host)
            r = self.session.get(url, params=params, timeout=self.timeout, stream=stream,
                                 headers={"User-Agent": USER_AGENT}, allow_redirects=False)
            self.requests += 1
            if r.status_code not in (429, 503) or attempt == MAX_RETRIES:
                return r
            wait = _retry_after(r.headers.get("Retry-After"), default=5.0 * (attempt + 1))
            if wait > MAX_WAIT:
                return r
            self.log(f"{host}: HTTP {r.status_code}, waiting {wait:.0f} s")
            r.close()
            self.sleep(wait)
        return r

    @staticmethod
    def _next_hop(url: str, r: requests.Response, hosts: set[str]) -> tuple[str | None, str | None]:
        """(next url, None) for a redirect that may be followed, or (None, why) for one that may not."""
        loc = r.headers.get("Location")
        r.close()
        if not loc:
            return None, f"{url} redirected without a Location"
        nxt = urljoin(url, loc)
        if urlsplit(url).scheme == "https" and urlsplit(nxt).scheme != "https":
            return None, f"redirect from {url} to {nxt} refused: it leaves https"
        if _host(nxt) != _host(url) and _host(nxt) not in hosts:
            return None, (f"redirect from {_host(url)} to {_host(nxt)} refused: the registry does not list "
                          f"{_host(nxt)} for this source")
        return nxt, None

    def _load_robots(self, scheme: str, host: str, hosts: set[str]) -> None:
        """Read one host's robots.txt (RFC 9309 §2.3.1): 2xx rules apply; 5xx or unreachable is complete disallow."""
        rp = robotparser.RobotFileParser()
        url, why, r = f"{scheme}://{host}/robots.txt", None, None
        try:
            for hop in range(MAX_REDIRECTS + 1):
                r = self._send(url)
                if r.status_code not in REDIRECTS:
                    break
                if hop == MAX_REDIRECTS:
                    why = f"robots.txt for {host} redirected more than {MAX_REDIRECTS} times"
                    break
                url, why = self._next_hop(url, r, hosts | {host})
                if why:
                    break
        except requests.RequestException as e:
            why = f"robots.txt for {host} unreachable ({type(e).__name__})"
        if not why and r is not None:
            code = r.status_code
            if 200 <= code < 300:
                rp.parse(r.text.splitlines())
                delay = rp.crawl_delay(USER_AGENT)
                if delay:
                    self._gap[host] = max(self.min_interval, float(delay))
            elif 400 <= code < 500 and code not in (401, 403, 429):
                rp.allow_all = True                     # "unavailable": no rules (RFC 9309 §2.3.1.3)
            else:                                       # 5xx "unreachable" (§2.3.1.4); 401, 403, 429 and odd codes
                why = f"robots.txt for {host} answered HTTP {code}"
        if why:
            rp.disallow_all = True
            self._why[host] = why
            self.log(f"{why}: treated as complete disallow")
        self._robots[host] = rp

    def allowed(self, url: str, hosts: Iterable[str] = ()) -> bool:
        parts = urlsplit(url)
        host = parts.netloc.lower()
        if host not in self._robots:
            self._load_robots(parts.scheme, host, {h.lower() for h in hosts})
        return self._robots[host].can_fetch(USER_AGENT, url)

    def get(self, url: str, params: dict | None = None, *, stream: bool = False,
            hosts: Iterable[str] = ()) -> requests.Response:
        """GET ``url``. A redirect may stay on its host or go to one of ``hosts``; each hop is checked first."""
        allowed_hosts = {_host(url)} | {h.lower() for h in hosts}
        current = requests.Request("GET", url, params=params).prepare().url
        for hop in range(MAX_REDIRECTS + 1):
            if not self.allowed(current, allowed_hosts):
                why = self._why.get(_host(current))
                raise PermissionError((f"{why}, so " if why else "") + f"robots.txt disallows {current}")
            r = self._send(current if hop else url, params=None if hop else params, stream=stream)
            if r.status_code not in REDIRECTS:
                r.raise_for_status()
                return r
            if hop == MAX_REDIRECTS:
                r.close()
                break
            nxt, why = self._next_hop(current, r, allowed_hosts)
            if why:
                raise PermissionError(why)
            self.log(f"{_host(current)}: HTTP {r.status_code} to {nxt}")
            current = nxt
        raise RuntimeError(f"{url}: more than {MAX_REDIRECTS} redirects")


# ---- fetching -----------------------------------------------------------------------------------------------

def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class Fetched:
    dataset: str
    rows: list[dict]                 # projected rows only: canonical fields plus a count ``n``
    retrieved_at: str
    requests: int = 0
    read: int = 0                    # rows received (one per group for a grouped query)
    truncated: bool = False          # the row cap was reached, so the aggregates may be incomplete
    query: dict | None = None        # the query sent, without paging, for provenance


def fetch_soda(ds: Dataset, http: Http, *, row_cap: int = ROW_CAP, page_size: int = PAGE_SIZE,
               grouped: bool = True, log: Log = print) -> Fetched:
    check_fields(ds)
    out = Fetched(ds.id, [], now())
    out.query = {k: v for k, v in soda_params(ds, grouped=grouped).items() if k not in ("$limit", "$offset")}
    before = http.requests
    offset = 0
    while True:
        if offset >= row_cap:
            out.truncated = True
            break
        limit = min(page_size, row_cap - offset)
        page = http.get(ds.endpoint, params=soda_params(ds, grouped=grouped, limit=limit, offset=offset),
                        hosts=listed_hosts(ds)).json()
        if not isinstance(page, list):
            raise RuntimeError(f"{ds.id}: unexpected Socrata reply {str(page)[:200]}")
        out.rows.extend(project(row, ds, counted=grouped) for row in page)
        offset += len(page)
        log(f"{ds.id}: {offset:,} rows read")
        if len(page) < limit:
            break
    out.read, out.requests = offset, http.requests - before
    return out


def fetch_csv(ds: Dataset, http: Http, *, row_cap: int = ROW_CAP, log: Log = print) -> Fetched:
    """Stream a whole CSV file and keep only the projected rows.

    Unlike the grouped Socrata query, the file crosses the network whole, names and every other column included;
    they exist only in the parser's buffer until :func:`project` drops them. Prefer a grouped query wherever the
    publisher offers one.
    """
    check_fields(ds)
    out = Fetched(ds.id, [], now())
    before = http.requests
    with http.get(ds.endpoint, stream=True, hosts=listed_hosts(ds)) as r:
        r.raw.decode_content = True
        text = io.TextIOWrapper(r.raw, encoding="utf-8-sig", newline="")
        out.rows, out.truncated = read_csv_rows(text, ds, row_cap=row_cap)
    out.read, out.requests = len(out.rows), http.requests - before
    log(f"{ds.id}: {out.read:,} rows read" + (" (row cap reached)" if out.truncated else ""))
    return out


def fetch(ds: Dataset, http: Http | None = None, *, row_cap: int = ROW_CAP, log: Log = print) -> Fetched:
    """Read one enabled dataset. Raises for a dataset the prototype does not read, with the reason."""
    if not ds.fetch:
        raise ValueError(f"{ds.id} is not read by this prototype: {ds.notes or ds.ingest}")
    http = http or Http(log=log)
    if ds.api == "soda":
        return fetch_soda(ds, http, row_cap=row_cap, log=log)
    return fetch_csv(ds, http, row_cap=row_cap, log=log)
