"""lexflow.payroll: the field map, person-level columns dropped at read time, the disclosure rules, and polite fetching.

No test touches the network: the fetcher runs against a fake session and a fake clock. The disclosure tests play
the attacker: each tries to recover one person's pay from the published cells, and must fail.
"""
import io
import json
import random
import re
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest
import requests

from lexflow.payroll import aggregate as A
from lexflow.payroll import sources as S

ROOT = Path(__file__).resolve().parents[1]
WHEN = "2026-10-10T12:00:00Z"


def make(**kw) -> S.Dataset:
    base = dict(id="t-city", state="va", government="City of Testville", gov_id="47299900100000",
                publisher="Testville HR", title="Employee Salaries", url="https://data.example.gov/d/abcd-1234",
                api="soda", endpoint="https://data.example.gov/resource/abcd-1234.json", licence="Public Domain",
                cadence="daily", person_level=True, fetch=True,
                fields={"agency": "department", "title": "job_title", "pay": "annual_base_rate"},
                drop=("first_name", "last_name", "gender", "start_date"), pay_basis="annual", rows="person")
    base.update(kw)
    return S.check_fields(S.Dataset(**base))


# A tiny literal payroll, person-level as published: names, gender and hire dates included.
HEADER = ["first_name", "last_name", "gender", "start_date", "department", "job_title", "annual_base_rate"]
TABLE = [
    ["Alice", "Smith", "F", "2001-02-03", "Clerk's Office", "Deputy Clerk", "40000"],
    ["Avery", "Okafor", "M", "2010-04-05", "Clerk's Office", "Deputy Clerk", "42,000.00"],
    ["Sam", "Brown", "F", "2012-06-07", "Clerk's Office", "Deputy Clerk", "$44000"],
    ["Lee", "Nguyen", "M", "2015-08-09", "Clerk's Office", "Deputy Clerk", "46000"],
    ["Kim", "Garcia", "X", "2018-10-11", "Clerk's  Office ", "Deputy Clerk", "48000"],
    ["Jo", "Kowalski", "F", "1999-12-13", "Clerk's Office", "City Clerk", "90000"],
    ["Ana", "Rivera", "F", "2020-01-14", "Police", "Officer", "50000"],
    ["Raj", "Patel", "M", "2021-03-15", "Police", "Officer", "52000"],
]
PERSON_VALUES = [v for row in TABLE for v in row[:4]]      # names, gender and hire dates


def assert_no_person_values(blob: str):
    for value in PERSON_VALUES:
        assert json.dumps(value) not in blob, value             # never as a value
        if len(value) > 2:
            assert value not in blob, value                     # nor inside one


def table_rows() -> list[dict]:
    return [dict(zip(HEADER, r)) for r in TABLE]


def csv_text() -> str:
    buf = io.StringIO()
    buf.write(",".join(HEADER) + "\n")
    for r in TABLE:
        buf.write(",".join(f'"{v}"' for v in r) + "\n")
    return buf.getvalue()


def cell(cells, agency, title):
    (c,) = [c for c in cells if c["agency"] == agency and c["title"] == title]
    return c


def people(agency, title, pays, basis="annual"):
    """Projected rows, one per person."""
    return [{"agency": agency, "title": title, "pay": p, "pay_basis": basis, "n": 1} for p in pays]


def figures(c) -> list[float]:
    """Every pay figure a cell publishes, on every basis."""
    return [p[k] for p in [c] + c["other_pay"] for k in ("p25", "median", "p75") if p[k] is not None]


# ---- the field map ------------------------------------------------------------------------------------------

def test_project_maps_canonical_fields_only():
    ds = make()
    out = S.project(table_rows()[0], ds)
    assert out == {"agency": "Clerk's Office", "title": "Deputy Clerk", "pay": "40000", "pay_basis": "annual", "n": 1}


def test_project_maps_pay_basis_and_period_columns():
    ds = make(fields={"agency": "agency_name", "title": "title_description", "pay": "base_salary",
                      "pay_basis": "pay_basis", "period": "fiscal_year"},
              basis_map={"per Annum": "annual", "per Hour": "hourly"}, pay_basis=None, period_format="FY{}")
    row = {"agency_name": "DEPT OF RECORDS", "title_description": "CLERICAL ASSOCIATE", "base_salary": "41000",
           "pay_basis": "per Annum", "fiscal_year": "2026", "last_name": "Smith"}
    assert S.project(row, ds) == {"agency": "DEPT OF RECORDS", "title": "CLERICAL ASSOCIATE", "pay": "41000",
                                  "pay_basis": "annual", "period": "2026", "n": 1}
    assert S.project({**row, "pay_basis": "per Day"}, ds)["pay_basis"] == "per day"   # unknown values pass lowered


def test_grouped_rows_carry_their_count():
    ds = make()
    row = {"department": "Police", "job_title": "Officer", "annual_base_rate": "50000", S.COUNT: "7"}
    assert S.project(row, ds, counted=True)["n"] == 7
    assert S.project(row, ds)["n"] == 1


def test_soda_query_selects_mapped_columns_only():
    ds = make(where="flsa_status='Exempt'")
    p = S.soda_params(ds, limit=100, offset=200)
    assert p["$select"] == f"`department`, `job_title`, `annual_base_rate`, count(*) AS {S.COUNT}"
    assert p["$group"] == p["$order"] == "`department`, `job_title`, `annual_base_rate`"
    assert (p["$where"], p["$limit"], p["$offset"]) == ("flsa_status='Exempt'", 100, 200)
    for col in ds.drop:
        assert col not in json.dumps(p)


def test_registry_entries_are_complete():
    assert len(S.fetchable()) >= 2
    for d in S.REGISTRY:
        assert d.id == S.get(d.id).id
        assert d.api in ("soda", "csv", "arcgis", "ckan", "web")
        assert d.ingest in ("aggregate", "as-is", "link", "none")
        assert isinstance(d.person_level, bool) and d.licence and d.cadence and d.publisher
        assert d.url.startswith("https://")
        assert len(d.state) == 2 and (d.gov_id is None or (len(d.gov_id) == 14 and d.gov_id.isdigit()))
        assert not set(d.fields.values()) & set(d.drop)
    for d in S.fetchable():
        assert set(S.REQUIRED) <= set(d.fields) and d.person_level and d.fields_checked
        assert d.api in ("soda", "csv") and d.endpoint
        assert len(S.listed_hosts(d)) == 1                      # landing page and endpoint on one host
    with pytest.raises(ValueError, match="rows must be one of"):
        make(rows="people")


def test_rows_are_people_only_where_the_publisher_says_so():
    """Re-check N11: the thresholds count rows. Neither fetched source's publisher says one row per person per
    period, so neither is marked rows='person', and the old unverified "one row per employee" note is gone."""
    for i in ("va-norfolk-salaries", "wa-seattle-wages", "ca-sf-compensation"):
        d = S.get(i)
        assert d.rows == "unknown" and "rows='unknown'" in d.notes, i
        assert not d.notes.startswith("One row per employee"), i
    for d in S.REGISTRY:
        assert d.rows in S.ROWS
        if d.rows == "person":                                  # a claim needs its source in the notes
            assert "one row per" in d.notes.lower(), d.id


def test_a_source_whose_rows_may_repeat_a_person_publishes_no_pay():
    """Re-check N11: one person with two jobs is two rows, so 11 rows can be 10 people, and one person's repeated
    rows could meet rule 4's within-half-a-step count. Without rows='person' no pay is published at all."""
    pays = [50120 + 70 * i for i in range(30)]
    rows = people("Works", "Crew", pays)
    assert any(figures(c) for c in A.aggregate(rows, make(), retrieved_at=WHEN))      # rows are people: shown
    why = Counter()
    cells = A.aggregate(rows, make(rows="unknown"), retrieved_at=WHEN, withheld=why)
    assert all(not figures(c) and c["suppressed"] for c in cells) and why == Counter(rows=3)
    assert [c["n"] for c in cells] == [30, 30, 30]                                     # headcounts of rows stay
    line = A.describe(cell(cells, "Works", A.ALL), ds=make(rows="unknown"))
    assert "30 payroll entries" in line and "staff" not in line and "more than once" in line
    assert "30 staff" in A.describe(cell(cells, "Works", A.ALL), ds=make())
    shown = [c for c in FIXTURE["aggregates"] if figures(c)]          # cells stored before this rule
    assert shown and all("$" not in A.describe(c) and "payroll entries" in A.describe(c) for c in shown)


def test_link_targets_are_official_entries():
    va = S.links("va", "47212200100000")
    assert va[0].id == "va-norfolk-salaries" and "va-datapoint-salaries" in [d.id for d in va]
    assert "fl-right-to-know-payroll" in [d.id for d in S.links("fl")]


def test_registry_records_the_verified_hosts_and_terms():
    assert S.listed_hosts(S.get("ca-sf-compensation")) == {"data.sf.gov"}      # data.sfgov.org answers 301
    assert S.get("ca-publicpay").url == "https://gcc.sco.ca.gov/"              # publicpay.ca.gov redirects
    chicago = S.get("il-chicago-employees")
    assert "indemnity" in chicago.notes and "not read" not in chicago.notes and not chicago.fetch
    montgomery = S.get("md-montgomery-salaries-2025")
    assert "not found" in montgomery.licence and "indemnity of the County" not in montgomery.notes
    assert not montgomery.fetch
    assert S.get("nc-osc-salaries").licence.startswith("terms read")
    for d in S.fetchable():                                      # no portal terms page: metadata only
        assert "licence rests on the dataset's own metadata" in d.notes
    for i in ("ny-nyc-payroll", "ny-state-authorities-salaries", "va-virginia-beach-salaries"):
        assert "not read" in S.get(i).notes or "not downloaded" in S.get(i).notes


def test_registered_sources_with_a_period_column_say_to_filter_one_period():
    """Re-check N1: a fetch publishes pay for one period, so a multi-year source is filtered to one year first."""
    multi = [d for d in S.REGISTRY if "period" in d.fields and d.ingest == "aggregate" and d.person_level]
    assert {"ny-nyc-payroll", "ca-la-city-payroll", "il-cook-county-payroll",
            "ny-state-authorities-salaries"} <= {d.id for d in multi}
    for d in multi:
        assert d.where or "filter one" in d.notes.lower(), d.id


def test_as_is_minimum_and_maximum_salaries_are_not_republished():
    """A group's minimum and maximum are each one person's pay (re-check N3), even in a publisher's own table."""
    assert "not republished" in S.get("ny-nyc-position-schedule").notes


DOCS = {name: (ROOT / "docs" / "design" / name).read_text(encoding="utf-8")
        for name in ("payroll-plan.md", "payroll-research.md", "verify-payroll.md")}
FIXTURE = json.loads((ROOT / "fixtures" / "payroll" / "sample_aggregates.json").read_text(encoding="utf-8"))
_N = r"(\d{1,3}(?:,\d{3})+|\d+)(\.\d+)?"
MONEY = re.compile(rf"\$\s?{_N}|(?<![\w.,]){_N}\s*(?:dollars|USD)\b|\bUSD\s?{_N}")    # $52,000, 52 dollars, USD 52
SHORTHAND = re.compile(r"(?<![\w.,])\$?\d+(?:\.\d+)?\s?[kK](?![\w+])")                 # 52k, $52.3K; not "4k+1"
STEPS = {0.25, 1.0, 10.0, 100.0}                                                        # rounding steps, old and new


def _bands() -> dict[str, set]:
    """Published figures of the fixture's cells, by the agency or title that names them."""
    out: dict[str, set] = defaultdict(set)
    for c in FIXTURE["aggregates"]:
        for name in (c["agency"], c["title"]):
            if name != A.ALL and len(name) >= 4:
                out[name] |= set(figures(c))
    return out


BANDS = _bands()


def figure_problems(text: str) -> list[str]:
    """The money figures in ``text`` that the doc-figure rules refuse.

    A figure is allowed when it is a rounding step ($0.25, $1, $10, $100), a $1,000 band or round bound from $1,000
    up, a round bound in hundreds under $1,000 ("under $200 an hour"), or, for any other figure under $1,000 (the
    form an hourly, daily or monthly rate takes), a published band figure of the group that its paragraph last
    names. Refused: cents, a non-round figure from $1,000 up, any other figure under $1,000, shorthand in
    thousands ("52k"), and a list of salaries. Beyond these rules: a bare number with no currency mark, and a
    figure written in words."""
    problems = []
    for m in MONEY.finditer(text):
        whole = next(g for g in m.groups()[0::2] if g)
        cents = next((g for g in m.groups()[1::2] if g), "")
        amount = float(whole.replace(",", "") + cents)
        if amount in STEPS:
            continue
        if cents or (amount >= 1000 and amount % 1000):
            problems.append(m.group())                   # cents, or not a $1,000 band
            continue
        if amount % 100 == 0:
            continue                                     # a $1,000 band, or a round bound such as $200 or $5,000
        start = text.rfind("\n\n", 0, m.start()) + 1
        before = text[start:m.start()]
        named = max(((before.rfind(n) + len(n), len(n), n) for n in BANDS if n in before), default=None)
        if named is None or amount not in BANDS[named[2]]:
            problems.append(m.group())                   # an hourly, daily or monthly figure of nobody's group
    problems += [m.group() for m in SHORTHAND.finditer(text)]
    problems += re.findall(r"\d{1,3},\d{3}\s*/\s*\d{1,3},\d{3}", text)                  # a list of salaries
    return problems


def test_docs_and_notes_quote_no_ones_pay():
    """Pay figures in the plan, the research note, the verification note and the registry notes are band figures
    of published groups or round range bounds. The figures once quoted are not kept here, not even as strings to
    look for (that would store them); the rules of :func:`figure_problems` catch their forms."""
    texts = {**DOCS, "registry notes": " ".join(d.notes for d in S.REGISTRY)}
    for name, text in texts.items():
        assert figure_problems(text) == [], name
    for name in ("payroll-plan.md", "verify-payroll.md", "registry notes"):     # (research cites RCW 42.56.120)
        for m in re.finditer(r"(?<![\w.§-])(\d[\d,]*)\.\d{2}(?![\d.])(?!\s*(?:million|billion|MB|%))", texts[name]):
            assert float(m.group(1).replace(",", "")) < 1, (name, m.group())   # no bare figure with cents


@pytest.mark.parametrize("text, refused", [
    # re-check 2 (N9): the two forms the rules used to let through
    ("The records clerk earns $47 an hour.", True),
    ("City of Seattle, Seattle Public Utilities: median about $47 an hour.", True),    # not that group's figure
    ("Her salary is about 61k a year.", True), ("about $61.4K", True), ("about 61 k", True),
    # and the forms they already caught
    ("$52,340 a year", True), ("$52,000.50", True), ("52,340 dollars", True), ("USD 52,340", True),
    ("51,200 / 52,300", True), ("$20 an hour", True),
    # allowed
    ("City of Seattle, Seattle Public Utilities: median about $55 an hour, middle half about $45 to $71.", False),
    ("all under $200 an hour, none between $200 and $5,000", False), ("rounded to $1,000 a year or $1 an hour",
                                                                       False),
    ("the old step of $0.25 an hour", False), ("$100 a month and $10 a day", False), ("a group of 4k+1 people", False),
    ("a 1 KB ranged GET", False)])
def test_doc_figure_rules(text, refused):
    assert bool(figure_problems(text)) is refused, figure_problems(text)


def test_notes_say_what_the_code_does():
    """Re-check 2 (N10, N12): claims that were not true."""
    plan, research = (" ".join(DOCS[n].split()) for n in ("payroll-plan.md", "payroll-research.md"))
    assert "No existing file was edited" not in plan
    assert "equals or pins down 1 to 10 people's pay" not in research and "pins down fewer than 5" in research
    (nc,) = [line for line in DOCS["payroll-research.md"].splitlines() if line.startswith("| NC | [State Employee")]
    assert "not read here" not in nc and "non-commercial copying" in nc
    for stale in ("A year's turnover is larger", "only the latest release's pay is kept",
                  "Keep pay from the latest release of each source only"):          # N10: not a protection
        assert stale not in plan, stale
    assert "Two fetches (releases) of one source are not compared" not in A.__doc__
    assert "No differencing across releases" in plan and "No differencing across releases" in A.__doc__
    assert "/api/views/<id>.json`, one request" not in plan              # a refresh reads no column statistics


def test_verification_note_is_redacted():
    """Re-check N4: the City Clerk quartiles (three people's pay to the nearest $100) and Norfolk's top hourly
    figure are gone from the verification note, replaced by what was checked."""
    note = DOCS["verify-payroll.md"]
    (clerk,) = [line for line in note.splitlines() if "City Clerk example" in line]
    assert not re.search(r"\d{2,3},\d{3}", clerk) and "was recomputed" in clerk
    assert not re.search(r"between about \d", note)
    assert "Redacted" in note


# ---- person-level columns never reach the output ------------------------------------------------------------

@pytest.mark.parametrize("col", [
    "name", "Name", "last_name", "FIRST_NAME", "employee_name", "employee_identifier", "record_nbr", "mid_init",
    "middle_initial", "HIREDATE_STRING", "original_hire_date", "agency_start_date", "title_date", "birth_year",
    "gender", "ethnicity", "race", "position_id", "home_address", "work_phone", "email", "OBJECTID", "row_id",
    # found by the verifier (W5)
    "EMPLID", "empl_id", "ee_id", "badge_number", "position_number", "name_last", "lname", "fname", "emp_nm",
    "incumbent", "employee", "zip_code", "phone_number", "address_line_1", "gender_code", "race_desc", "age_group",
    "veteran_status", "GlobalID", "unique_id", "ssn_last4",
    # more spellings of the same things
    "EmployeeID", "firstName", "e_mail", "dob", "date_of_birth", "rehire_date", "separation_date",
    "termination_dt", "years_of_service_date", "seniority", "disability_status", "marital_status", "id", "uuid",
    "hashed_id", "employee_full_name", "staff_number", "person_key", "position_end_date", "effective_date", "",
    # found by the re-check (N2)
    "l_name", "f_name", "m_name", "lst_nm", "frst_nm", "payee_name", "supervisor_name", "manager_name",
    "contact_name", "name_of_employee", "nickname", "payee_id", "empno", "employeenumber", "empnum", "pernr",
    "years_of_service", "length_of_service", "service_years", "longevity", "sexual_orientation", "photo_url",
    "home_city",
    # more of the same: glued, camelCase and capitalised forms, and owners that are people
    "EMPNO", "PERNR", "EmployeeNumber", "Nickname", "surname", "username", "full_name", "legal_name",
    "preferred_name", "given_name", "family_name", "display_name", "spouse_name", "department_head_name",
    "employee_dept_id", "check_number", "job_id", "years", "home_phone", "residence_state",
    # found by re-check 2 (N7): an ID word followed by "of" is not a count
    "id_of_employee", "identifier_of_employee", "key_of_person", "id_of_payee", "number_of_employee",
    # found by re-check 2 (N8): glued all-caps, as in ArcGIS schemas
    "POSITIONNUMBER", "POSITIONID", "PAYROLLID", "CHECKNUMBER", "EMAILADDRESS", "PHONENUMBER", "HOMEADDRESS",
    "AGEGROUP", "STARTDT",
    # (N8) bare nouns whose values are names
    "supervisor", "manager", "department_head", "officer", "elected_official", "approver", "last", "first",
    "middle",
    # (N8) abbreviations
    "gndr", "vet_status", "yob", "doh", "begin_date", "employment_start", "yrs_svc", "time_in_grade", "hispanic",
    "resident_state",
    # more of the same
    "EMPLOYEEID", "BADGENUMBER", "WORKPHONE", "CELLPHONE", "GNDRCD", "VETSTATUS", "YRSSVC", "TIMEINGRADE",
    "ELECTEDOFFICIAL", "DEPARTMENTHEAD", "SUPERVISORNAME", "OFFICERNAME", "ORIGHIREDATE", "ADDRLINE1",
    "EMPLOYMENTEND", "last_first", "officers", "emergency_contact", "position_holder", "staff", "telno",
    "years_in_title", "num_of_staff"])
def test_person_columns_cannot_be_mapped(col):
    with pytest.raises(ValueError, match="person-level"):
        make(fields={"agency": "department", "title": col, "pay": "annual_base_rate"}, drop=())


@pytest.mark.parametrize("col", [
    "department", "department_name", "agency_name", "job_title", "title_code_name", "grade", "annual_base_rate",
    "hourly_rate", "fiscal_year", "fiscal_year_end_date", "average_wage", "Annual_Rt", "Dept", "DESCRSHORT",
    "JOBTITLE", "COMPRATE", "office_name", "authority_name", "fms_department_title", "employee_status",
    "employment_type", "position_title", "job_code", "dept_nm", "dept_id", "pay_period_end_date", "as_of_date",
    "number_of_employees", "home_department", "bargaining_unit", "flsa_status",
    # organisational names and IDs, and pay columns the general rules must let through
    "agency_description", "title_description", "title_name", "division_name", "position_name", "employer_name",
    "union_name", "cost_center_name", "work_location_name", "agency_short_name", "deptname", "unit_no",
    "fund_number", "pay_period_number", "org_id", "class_code", "job_family", "pay_grade", "amount_paid",
    "total_paid", "gross_paid", "base_salary", "regular_pay", "overtime_pay", "total_compensation", "salaries",
    "pay_type", "pay_year", "Year", "employment_category", "full_or_part_time",
    # glued all-caps forms of ordinary columns, and counts (re-check 2, N7 and N8)
    "DEPTNAME", "DEPTID", "AGENCYNAME", "AGENCYCODE", "ORGID", "FUNDNO", "UNITNO", "JOBCODE", "PAYGRADE", "PAYTYPE",
    "FISCALYEAR", "POSITIONTITLE", "EMPLOYEESTATUS", "EMPLOYMENTTYPE", "HOMEDEPARTMENT", "WORKLOCATION",
    "CHECKDATE", "PAYPERIODENDDATE", "AMOUNTPAID", "GROSSPAY", "BASESALARY", "OVERTIME", "NUMBEROFEMPLOYEES",
    "POSITIONCOUNT", "DIVISIONNAME", "LOCATIONNAME", "headcount", "HEADCOUNT", "officer_count",
    "number_of_officers", "id_of_department", "supervisory_organization", "GVT_TYPE_OF_APPT", "midyear_adjustment",
    "paid", "unpaid", "hybrid"])
def test_ordinary_columns_can_be_mapped(col):
    make(fields={"agency": "department", "title": col, "pay": "annual_base_rate"}, drop=())


@pytest.mark.parametrize("col, person", [
    ("approver_name", True), ("xyz_name", True), ("name_xyz", True), ("approver_id", True), ("xyz_number", True),
    ("xyz_no", True), ("bureau_name", False), ("program_id", False), ("cost_center_number", False),
    ("agency_official_name", False), ("no_of_positions", False),
    # re-check 2 (N7): the owner of an ID before "of" is the word after it, and only a count word makes a count
    ("id_of_xyz", True), ("id_of_department", False), ("number_of_xyzs", False), ("number_of_staff", True),
    ("XYZNUMBER", True), ("XYZ_NBR", True)])
def test_name_and_id_columns_need_an_organisational_owner(col, person):
    """Re-check N2: the general rule. A name or ID column is person-level unless an organisation owns it."""
    assert S.looks_person_level(col) is person


def test_glued_names_are_split_into_known_words():
    """Re-check 2 (N8): an all-caps glued name is judged by the words in it, and ordinary words stay whole."""
    def split(col):
        return [p for t in S._words(col) for p in S._unglue(t)]
    assert split("POSITIONNUMBER") == ["position", "number"] and split("STARTDT") == ["start", "dt"]
    assert split("EMAILADDRESS") == ["email", "address"] and split("TIMEINGRADE") == ["time", "in", "grade"]
    assert split("DEPTID") == ["dept", "id"] and split("JOBTITLE") == ["job", "title"]
    for word in ("paid", "overtime", "usage", "average", "comprate", "descrshort"):
        assert split(word) == [word], word


def test_every_registered_person_column_is_recognised():
    for d in S.REGISTRY:
        for col in d.drop:
            assert S.looks_person_level(col), (d.id, col)


def test_names_never_reach_the_aggregates_csv_path():
    ds = make(api="csv", endpoint="https://data.example.gov/salaries.csv")
    rows, truncated = S.read_csv_rows(io.StringIO(csv_text()), ds)
    assert not truncated and len(rows) == len(TABLE)
    assert all(set(r) <= {"agency", "title", "pay", "pay_basis", "n"} for r in rows)
    cells = A.aggregate(rows, ds, retrieved_at="2026-10-10T00:00:00Z")
    blob = json.dumps({"rows": rows, "cells": cells})
    assert_no_person_values(blob)
    for col in HEADER[:4]:
        assert f'"{col}"' not in blob, col


def test_names_never_reach_the_aggregates_when_a_server_ignores_select():
    ds = make()
    clock = Clock()
    full_rows = [{**r, S.COUNT: "1"} for r in table_rows()]       # a server that sends every column anyway
    http = S.Http(FakeSession(clock, full_rows), sleep=clock.sleep, clock=clock.now, log=lambda m: None)
    got = S.fetch(ds, http, log=lambda m: None)
    blob = json.dumps({"rows": got.rows, "cells": A.aggregate(got.rows, ds, retrieved_at=got.retrieved_at)})
    assert_no_person_values(blob)


def test_sample_fixture_holds_aggregates_only():
    fx = json.loads((ROOT / "fixtures" / "payroll" / "sample_aggregates.json").read_text(encoding="utf-8"))
    cell_keys = {"state", "gov_id", "government", "agency", "title", "period", "n", "pay_basis", "n_pay", "p25",
                 "median", "p75", "suppressed", "other_pay", "source"}
    pay_keys = {"pay_basis", "n_pay", "p25", "median", "p75", "suppressed"}
    sources = {s["id"]: s for s in fx["sources"]}
    assert (fx["min_count"], fx["min_pay"], fx["min_shared"]) == (A.MIN_COUNT, A.MIN_PAY, A.MIN_SHARED)
    assert fx["rounding"] == A.ROUND_TO and len(sources) >= 2 and fx["aggregates"]
    for s in sources.values():
        ds = S.get(s["id"])
        assert s["fields"] == ds.fields and not s["truncated"] and s["people"] > 0
        # The committed fixture predates the rows rule and rule 7 (re-check N10, N11), so it has no count for
        # them; a rebuild writes every key of WHY (test_rebuilding_a_fixture_carries_its_record_forward).
        assert set(s["pay_groups_withheld"]) | {"rows", "release"} == set(A.WHY)
        assert "period" not in ds.fields and s["pay_groups_withheld"]["period"] == 0     # one-period snapshots
        assert len({c["period"] for c in fx["aggregates"] if c["source"] == s["id"]}) == 1
        assert S.listed_hosts(ds) == {urlsplit(s["endpoint"]).netloc}
        for col in s["never_read"]:                       # named as never read, and absent from the query sent
            assert col not in json.dumps(s["query"])
    for c in fx["aggregates"]:
        assert set(c) == cell_keys and c["source"] in sources
        assert c["n"] is None or c["n"] >= A.MIN_COUNT
        for p in [c] + c["other_pay"]:
            assert set(p) >= pay_keys
            assert p["n_pay"] is None or p["n_pay"] == 0 or p["n_pay"] >= A.MIN_COUNT
            if p["suppressed"]:
                assert p["p25"] is p["median"] is p["p75"] is None
            else:
                assert p["n_pay"] >= A.MIN_PAY and p["p25"] <= p["median"] <= p["p75"]
                step = A.ROUND_TO[p["pay_basis"]]
                assert all(abs(p[k] / step - round(p[k] / step)) < 1e-6 for k in ("p25", "median", "p75"))


# ---- aggregation and the disclosure rules -------------------------------------------------------------------

D_PAYS = [50120, 50180, 50260, 50340, 50410, 50480, 50530, 50610, 50690, 50770, 50860]   # 11, spread, not round


def threshold_rows():
    return (people("Archive", "Archivist", [41000 + 300 * i for i in range(4)])
            + people("Budget", "Analyst", [60000 + 700 * i for i in range(5)])
            + people("Courts", "Bailiff", [45000 + 100 * i for i in range(10)])
            + people("Records", "Records Clerk", D_PAYS))


def test_headcount_from_five_and_pay_from_eleven():
    why = Counter()
    cells = A.aggregate(threshold_rows(), make(), retrieved_at=WHEN, withheld=why)
    four, five, ten = (cell(cells, a, t) for a, t in (("Archive", "Archivist"), ("Budget", "Analyst"),
                                                      ("Courts", "Bailiff")))
    assert (four["n"], four["n_pay"], four["suppressed"]) == (None, None, True)      # "fewer than 5"
    assert (five["n"], five["n_pay"], five["suppressed"]) == (5, 5, True)
    assert (ten["n"], ten["n_pay"], ten["suppressed"]) == (10, 10, True)
    eleven = cell(cells, "Records", "Records Clerk")
    assert (eleven["n"], eleven["n_pay"], eleven["suppressed"]) == (11, 11, False)
    assert (eleven["p25"], eleven["median"], eleven["p75"]) == (50000, 50000, 51000)  # $1,000 bands
    assert cell(cells, "Records", A.ALL)["median"] == 50000                            # the same 11 people
    everyone = cell(cells, A.ALL, A.ALL)          # its p25 would round to $45,000: one bailiff's exact pay
    assert (everyone["n"], everyone["n_pay"], everyone["suppressed"]) == (30, 30, True) and why["match"] == 1
    assert all(45000 not in figures(c) for c in cells)
    assert (why["small"], why["overlap"]) == (6, 0)          # 3 small titles, each with its agency
    assert all(c["n"] is None or c["n"] >= A.MIN_COUNT for c in cells)
    assert (eleven["state"], eleven["gov_id"], eleven["period"]) == ("va", "47299900100000", "as of 2026-10-10")


def test_five_people_never_publish_their_order_statistics():
    """The verifier's case: with type-7 quartiles a group of 4k+1 people has exact order statistics as quartiles."""
    pays = [48211, 51377, 53902, 56140, 59865]
    pairs = [(float(p), 1) for p in pays]
    assert [A.quantile(pairs, q) for _, q in A.QUARTILES] == [51377, 53902, 56140]   # the 2nd, 3rd and 4th person
    cells = A.aggregate(people("Treasurer", "Deputy Treasurer", pays), make(), retrieved_at=WHEN)
    assert all(not figures(c) for c in cells)                                        # nothing to recover
    assert all(c["n"] == 5 for c in cells)


def test_a_single_title_holder_cannot_be_recovered_by_differencing():
    """Agency = 11 clerks + 1 records manager. Publishing both groups' medians gives x = 2 * agency - clerks."""
    clerks = [60100, 60200, 60300, 60400, 60500, 60700, 61300, 61400, 61450, 61600, 61900]
    x = 61100                                                                         # the records manager
    rows = people("Records", "Clerk", clerks) + people("Records", "Records Manager", [x])
    exact = {name: A.quantile(sorted(Counter(map(float, p)).items()), 0.5)
             for name, p in (("agency", clerks + [x]), ("clerks", clerks))}
    assert 2 * exact["agency"] - exact["clerks"] == x                                 # exact quartiles leak x
    rounded = {name: A._figures(Counter(map(float, p)), "annual")[0]["median"]
               for name, p in (("agency", clerks + [x]), ("clerks", clerks))}
    assert abs(2 * rounded["agency"] - rounded["clerks"] - x) <= 500                  # so does rounding alone

    why = Counter()
    cells = A.aggregate(rows, make(), retrieved_at=WHEN, withheld=why)
    agency, clerk, manager = (cell(cells, "Records", t) for t in (A.ALL, "Clerk", "Records Manager"))
    assert not agency["suppressed"] and (agency["p25"], agency["median"], agency["p75"]) == (60000, 61000, 61000)
    assert clerk["suppressed"] and why["overlap"] == 1                               # rule 5 withholds the clerks
    assert manager["n"] is None and manager["suppressed"]
    published = [c for c in cells if not c["suppressed"]]
    for p in published:                                                               # no pair differs by 1 to 10
        for q in published:
            assert p["n_pay"] == q["n_pay"] or abs(p["n_pay"] - q["n_pay"]) >= A.MIN_PAY
    attempts = [2 * p["median"] - q["median"] for p in published for q in published if p["n_pay"] - q["n_pay"] == 1]
    assert attempts == []


def test_a_government_total_cannot_be_differenced_against_an_agency():
    crew = [38100 + 70 * i for i in range(12)]
    rows = people("Works", "Crew", crew) + people("Mayor's Office", "Mayor", [97250])
    why = Counter()
    cells = A.aggregate(rows, make(), retrieved_at=WHEN, withheld=why)
    total = cell(cells, A.ALL, A.ALL)
    assert not total["suppressed"] and total["n"] == 13
    assert cell(cells, "Works", A.ALL)["suppressed"] and cell(cells, "Works", "Crew")["suppressed"]
    assert why["overlap"] == 2                                     # the agency, then the title that stood in for it
    assert 97250 not in figures(total) and all(abs(v - 97250) > 500 for v in figures(total))


def test_a_round_salary_held_by_one_person_is_never_a_published_figure():
    pays = [51600, 51650, 51700, 51750, 51800, 52000, 52100, 52150, 52200, 52250, 52300]  # one at exactly 52,000
    assert A.quantile([(float(p), 1) for p in pays], 0.5) == 52000                     # her exact pay
    why = Counter()
    cells = A.aggregate(people("Library", "Librarian", pays), make(), retrieved_at=WHEN, withheld=why)
    assert all(c["suppressed"] for c in cells) and why["match"] == 3                   # title, agency, government
    assert all(52000 not in figures(c) for c in cells)
    step = A.aggregate(people("Library", "Librarian", [52000] * 11), make(), retrieved_at=WHEN)
    assert cell(step, "Library", "Librarian")["median"] == 52000    # a rate 11 people share is a pay-scale step


def test_a_figure_that_would_pin_down_one_persons_pay_is_withheld():
    pays = [45100, 45200, 45300, 45400, 45500, 52340, 58100, 58200, 58300, 58400, 58500]
    why = Counter()
    cells = A.aggregate(people("Parks", "Planner", pays), make(), retrieved_at=WHEN, withheld=why)
    assert all(c["suppressed"] for c in cells) and why["match"] == 3                   # alone within $500 of 52,000
    assert all(not figures(c) for c in cells)


def test_unknown_pay_basis_is_never_published():
    ds = make(fields={"agency": "dept", "title": "job", "pay": "rate", "pay_basis": "basis"}, pay_basis=None)
    rows = [S.project({"dept": "Pool", "job": "Lifeguard", "rate": str(700 + i), "basis": "per week"}, ds)
            for i in range(12)]
    why = Counter()
    c = cell(A.aggregate(rows, ds, retrieved_at=WHEN, withheld=why), "Pool", "Lifeguard")
    assert (c["pay_basis"], c["n_pay"], c["suppressed"]) == ("per week", 12, True) and why["basis"] == 3


def random_payroll(seed: int) -> list[dict]:
    """Agencies of titles of 1 to 45 people, paid on scale steps (shared, sometimes round) or anywhere near them."""
    rng = random.Random(seed)
    rows = []
    for a in range(rng.randint(3, 7)):
        for t in range(rng.randint(1, 6)):
            hourly = rng.random() < 0.3
            size = rng.choice([1, 1, 2, 3, 4, 5, 6, 9, 10, 11, 12, 13, 15, 20, 30, 45])
            if hourly:
                steps = [rng.randint(15, 80) + rng.choice([0, 0, 0.25, 0.5, 0.73]) for _ in range(rng.randint(1, 4))]
                spread = 3
            else:
                steps = [rng.randint(30, 90) * 1000 + rng.choice([0, 0, 250, 500, 731]) for _ in
                         range(rng.randint(1, 4))]
                spread = 3000
            for _ in range(size):
                pay = rng.choice(steps) if rng.random() < 0.6 else round(
                    rng.uniform(min(steps) - spread, max(steps) + spread), 2)
                rows.append({"agency": f"Agency {a}", "title": f"Title {a}.{t}", "pay": max(pay, 1.0),
                             "pay_basis": "hourly" if hourly else "annual", "n": 1})
    if seed % 2:                                        # a lone office holder in an agency of its own
        rows.append({"agency": "Mayor", "title": "Mayor", "pay": 98000.0, "pay_basis": "annual", "n": 1})
    return rows


def truth(rows):
    """Every group's pay list per basis, as the attacker would like to know it."""
    groups: dict[tuple, list[float]] = defaultdict(list)
    heads: Counter = Counter()
    for r in rows:
        for key in ((r["agency"], r["title"]), (r["agency"], A.ALL), (A.ALL, A.ALL)):
            groups[(key, r["pay_basis"])].append(r["pay"])
            heads[key] += 1
    return groups, heads


def inside(small, big):
    (sa, st), (ba, bt) = small, big
    return small != big and (ba == A.ALL or (ba == sa and (bt == A.ALL or bt == st)))


SEEDS = range(12)


@pytest.mark.parametrize("seed", SEEDS)
def test_random_payrolls_never_let_an_attacker_isolate_a_person(seed):
    rows = random_payroll(seed)
    groups, heads = truth(rows)
    cells = A.aggregate(rows, make(), retrieved_at=WHEN)
    shown: dict[str, dict[tuple, dict]] = defaultdict(dict)     # basis -> group -> published pay part
    for c in cells:
        key = (c["agency"], c["title"])
        assert c["n"] == (heads[key] if heads[key] >= A.MIN_COUNT else None)
        for p in [c] + c["other_pay"]:
            pays = groups[(key, p["pay_basis"])]
            assert p["n_pay"] == (len(pays) if len(pays) >= A.MIN_COUNT else None)
            if not p["suppressed"]:
                shown[p["pay_basis"]][key] = p
    for basis, published in shown.items():
        step = A.ROUND_TO[basis]
        for key, p in published.items():
            pays = groups[(key, basis)]
            assert len(pays) >= A.MIN_PAY
            for v in (p["p25"], p["median"], p["p75"]):
                assert abs(v / step - round(v / step)) < 1e-9
                exact = sum(1 for x in pays if abs(x - v) < 0.005)
                near = sum(1 for x in pays if abs(x - v) <= step / 2 + 0.005)
                assert exact == 0 or exact >= A.MIN_PAY, (key, v, exact)     # never one person's exact pay
                assert near == 0 or near >= A.MIN_SHARED, (key, v, near)     # never pins down fewer than 5
        for big in published:                                                # differencing two groups
            for small in published:
                if inside(small, big):
                    d = len(groups[(big, basis)]) - len(groups[(small, basis)])
                    assert d == 0 or d >= A.MIN_PAY, (big, small, d)
            below = [k for k in published if inside(k, big)]
            top = [k for k in below if not any(inside(k, o) for o in below)]
            rest = len(groups[(big, basis)]) - sum(len(groups[(k, basis)]) for k in top)
            assert rest == 0 or rest >= A.MIN_PAY, (big, rest)              # nor several groups at once


def test_random_payrolls_exercise_every_rule():
    why = Counter()
    published = 0
    for seed in SEEDS:
        cells = A.aggregate(random_payroll(seed), make(), retrieved_at=WHEN, withheld=why)
        published += sum(1 for c in cells for p in [c] + c["other_pay"] if not p["suppressed"])
    assert published > 20 and all(why[k] > 0 for k in ("small", "match", "overlap")), (published, why)


def by_year(**kw):
    return make(fields={"agency": "department", "title": "job_title", "pay": "annual_base_rate",
                        "period": "fiscal_year"}, period_format="FY{}", **kw)


def test_a_newcomer_cannot_be_recovered_by_differencing_two_periods():
    """Re-check N1: FY2025 has 11 clerks, FY2026 the same 11 and a newcomer. Rule 5 cannot see across periods
    (no IDs are read, so nobody can be matched), so a fetch publishes pay for one period only."""
    clerks = [60100, 60200, 60300, 60400, 60500, 60700, 61300, 61400, 61450, 61600, 61900]
    x = 61100                                                                         # the newcomer
    rows = ([dict(r, period="2025") for r in people("Records", "Clerk", clerks)]
            + [dict(r, period="2026") for r in people("Records", "Clerk", clerks + [x])])
    ds = by_year()
    alone = {p: cell(A.aggregate([r for r in rows if r["period"] == p], ds, retrieved_at=WHEN), "Records", "Clerk")
             for p in ("2025", "2026")}
    assert abs(2 * alone["2026"]["median"] - alone["2025"]["median"] - x) <= 100      # both years together leak x

    why = Counter()
    cells = A.aggregate(rows, ds, retrieved_at=WHEN, withheld=why)
    assert {c["period"] for c in cells if figures(c)} == {"FY2026"}                   # the latest period only
    old = [c for c in cells if c["period"] == "FY2025"]
    assert len(old) == 3 and all(c["n"] == c["n_pay"] == 11 and c["suppressed"] for c in old)   # counts kept
    assert why["period"] == 3                                                         # title, agency, government
    assert [c for c in cells if c["period"] == "FY2026"] == [
        c for c in A.aggregate([r for r in rows if r["period"] == "2026"], ds, retrieved_at=WHEN)]


def test_the_published_period_is_the_latest_by_number_and_from_the_column():
    assert A.pay_period(["FY9", "FY10"]) == "FY10"                                    # not "FY9" > "FY10"
    assert A.pay_period(["2025-03-31T00:00:00.000", "2026-03-31T00:00:00.000"]) == "2026-03-31T00:00:00.000"
    assert A.pay_period(["FY2026", "as of 2026-10-10"], dated=["FY2026"]) == "FY2026"
    assert A.pay_period([]) is None
    pays = [50120 + 70 * i for i in range(11)]
    rows = ([dict(r, period="2026") for r in people("Works", "Crew", pays)]
            + [dict(r, period="") for r in people("Works", "Crew", pays)])            # rows with no year
    cells = A.aggregate(rows, by_year(), retrieved_at=WHEN)
    assert {c["period"] for c in cells} == {"FY2026", "as of 2026-10-10"}
    assert {c["period"] for c in cells if figures(c)} == {"FY2026"}


@pytest.mark.parametrize("seed", range(6))
def test_random_two_period_payrolls_publish_one_period(seed):
    """Two years of a random payroll, the second with a newcomer: the later year's cells are exactly what a fetch
    of that year alone would give (so every single-period attack above applies), the earlier year's carry counts."""
    old = random_payroll(seed)
    new = old + [{"agency": "Agency 0", "title": "Title 0.0", "pay": 61234.0, "pay_basis": "annual", "n": 1}]
    rows = [dict(r, period="2025") for r in old] + [dict(r, period="2026") for r in new]
    ds = by_year()
    why = Counter()
    cells = A.aggregate(rows, ds, retrieved_at=WHEN, withheld=why)
    alone = {p: A.aggregate([r for r in rows if r["period"] == p], ds, retrieved_at=WHEN) for p in ("2025", "2026")}
    assert [c for c in cells if c["period"] == "FY2026"] == alone["2026"]
    earlier = [c for c in cells if c["period"] == "FY2025"]
    assert all(not figures(c) and c["suppressed"] for c in earlier)
    assert [(c["agency"], c["title"], c["n"], c["n_pay"]) for c in earlier] == [
        (c["agency"], c["title"], c["n"], c["n_pay"]) for c in alone["2025"]]
    assert why["period"] == sum(1 + len(c["other_pay"]) for c in earlier)


CLERKS = [60100, 60200, 60300, 60400, 60500, 60700, 61300, 61400, 61450, 61600, 61900]


def test_a_newcomer_cannot_be_recovered_by_differencing_two_releases():
    """Re-check 2 (N10): the N1 attack across two fetches. Last year's release published the 11 clerks' figures
    (they survive in wiki history, a synced copy or a committed fixture); this year's has the same 11 and a
    newcomer. Rule 7 reads the record of what was published and withholds this year's pay."""
    x = 61100                                                                         # the newcomer
    ds = make()
    last = A.aggregate(people("Records", "Clerk", CLERKS), ds, retrieved_at="2025-10-10T12:00:00Z")
    record = A.pay_groups(last)
    assert [(g["period"], g["pay_basis"], g["n_pay"]) for g in record] == [("as of 2025-10-10", "annual", 11)] * 3
    rows = people("Records", "Clerk", CLERKS + [x])
    unguarded = A.aggregate(rows, ds, retrieved_at=WHEN)                             # no record: rule 7 is blind
    assert abs(2 * cell(unguarded, "Records", "Clerk")["median"] - cell(last, "Records", "Clerk")["median"]
               - x) <= 100                                                            # so the two releases leak x
    why = Counter()
    cells = A.aggregate(rows, ds, retrieved_at=WHEN, withheld=why, earlier=record)
    assert all(not figures(c) and c["suppressed"] for c in cells) and why["release"] == 3
    assert [c["n"] for c in cells] == [12, 12, 12]                                    # headcounts stay


def test_rule_7_sees_a_swap_and_a_renamed_office_and_lets_a_real_change_through():
    record = A.pay_groups(A.aggregate(people("Records", "Clerk", CLERKS), make(), retrieved_at="2025-10-10"))
    swap = people("Records", "Clerk", CLERKS[:-1] + [61100])          # one leaver, one joiner: still 11
    renamed = people("Records Department", "Records Clerk", CLERKS + [61100])     # same people, new names
    for rows in (swap, renamed):
        assert all(figures(c) for c in A.aggregate(rows, make(), retrieved_at=WHEN))   # shown without the record
        why = Counter()
        assert not any(figures(c) for c in A.aggregate(rows, make(), retrieved_at=WHEN, withheld=why,
                                                        earlier=record))
        assert why["release"] == 3
    grown = people("Records", "Clerk", CLERKS + [62010 + 37 * i for i in range(11)])   # 11 more people: 22
    assert all(figures(c) for c in A.aggregate(grown, make(), retrieved_at=WHEN, earlier=record))
    hourly = [dict(g, pay_basis="hourly") for g in record]           # another basis is other people
    assert all(figures(c) for c in A.aggregate(people("Records", "Clerk", CLERKS + [61100]), make(),
                                               retrieved_at=WHEN, earlier=hourly))


@pytest.mark.parametrize("seed", range(6))
def test_random_releases_never_pair_two_groups_that_differ_by_1_to_10(seed):
    """Rule 7 on random payrolls: every pay group published from the second release differs in size from every
    one published from the first, on its basis, by at least 11 (so by at least 11 people)."""
    rng = random.Random(seed)
    first_rows = random_payroll(seed)
    second_rows = [r for r in first_rows if rng.random() > 0.05] + [
        {"agency": f"Agency {rng.randint(0, 2)}", "title": "Title 0.0", "pay": 50000.0 + 113 * i,
         "pay_basis": "annual", "n": 1} for i in range(rng.randint(0, 15))]
    first = A.aggregate(first_rows, make(), retrieved_at="2025-10-10")
    second = A.aggregate(second_rows, make(), retrieved_at=WHEN, earlier=A.pay_groups(first))
    for g in A.pay_groups(second):
        for h in A.pay_groups(first):
            if g["pay_basis"] == h["pay_basis"]:
                assert abs(g["n_pay"] - h["n_pay"]) >= A.MIN_PAY, (g, h)


def test_headcount_minus_pay_count_shows_a_few_on_another_basis_never_their_pay():
    """Re-check N6, a documented gap: n - n_pay says that 1 to 4 people in a cell are on another pay basis (at
    Norfolk, a temporary, part-time, retiree, sheriff or state-compensated class) or have no pay figure (re-check 2,
    N12). It never says what they earn."""
    ds = make(hourly_below=1000.0)
    annual = [52100 + 80 * i for i in range(11)]
    rows = [S.project({"department": "Clerk", "job_title": "Deputy Clerk", "annual_base_rate": str(v)}, ds)
            for v in annual + [18.5, 23.75]]
    cells = A.aggregate(rows, ds, retrieved_at=WHEN)
    assert len(cells) == 3                                         # title, agency and government: the same 13
    for c in cells:
        assert (c["n"], c["pay_basis"], c["n_pay"], c["suppressed"]) == (13, "annual", 11, False)
        assert c["n"] - c["n_pay"] == 2                            # what subtraction shows
        (hourly,) = c["other_pay"]
        assert (hourly["pay_basis"], hourly["n_pay"], hourly["suppressed"]) == ("hourly", None, True)
        assert all(v >= 1000 for v in figures(c))                  # no hourly figure anywhere
    empty = [S.project({"department": "Clerk", "job_title": "Deputy Clerk", "annual_base_rate": v}, ds)
             for v in [str(p) for p in annual] + [""]]             # one row with no pay figure, no other basis
    for c in A.aggregate(empty, ds, retrieved_at=WHEN):
        assert c["n"] - c["n_pay"] == 1 and c["other_pay"] == []
    for text in (A.__doc__, DOCS["payroll-plan.md"]):              # and the docs say so
        assert "on another pay basis or have no pay figure" in " ".join(text.split())


def test_grouped_counts_give_the_same_cells_as_rows():
    ds = make()
    rows = [S.project(r, ds) for r in table_rows()]
    grouped = [{"agency": "Clerk's Office", "title": "Deputy Clerk", "pay": "44000", "pay_basis": "annual", "n": 12}]
    expanded = [{"agency": "Clerk's Office", "title": "Deputy Clerk", "pay": "44000", "pay_basis": "annual", "n": 1}] * 12
    assert A.aggregate(grouped + rows, ds, retrieved_at="2026-10-10") == A.aggregate(expanded + rows, ds,
                                                                                     retrieved_at="2026-10-10")


def test_whitespace_is_normalised_and_a_literal_star_is_not_a_roll_up():
    cells = A.aggregate([S.project(r, make()) for r in table_rows()], make(), retrieved_at=WHEN)
    assert cell(cells, "Clerk's Office", "Deputy Clerk")["n"] == 5            # "Clerk's  Office " joined in
    assert A.clean("*") != A.ALL and A.clean("  ") == A.NOT_GIVEN


def test_pay_bases_are_never_pooled_and_periods_are_separate_cells():
    ds = make(fields={"agency": "dept", "title": "job", "pay": "rate", "pay_basis": "basis", "period": "year"},
              pay_basis=None, basis_map={"H": "hourly", "A": "annual"}, period_format="FY{}")
    rates = (20.10, 20.20, 20.30, 20.40, 20.45, 20.55, 20.60, 20.70, 20.80, 20.90, 20.95)
    rows = [{"dept": "Library", "job": "Library Assistant", "rate": str(r), "basis": "H", "year": "2026"}
            for r in rates]
    rows.append({"dept": "Library", "job": "Library Assistant", "rate": "61234", "basis": "A", "year": "2026"})
    rows.append({"dept": "Library", "job": "Library Assistant", "rate": "", "basis": "H", "year": "2025"})
    cells = A.aggregate([S.project(r, ds) for r in rows], ds, retrieved_at="2026-10-10")
    (c26,) = [c for c in cells if c["period"] == "FY2026" and c["title"] == "Library Assistant"]
    assert (c26["n"], c26["pay_basis"], c26["n_pay"]) == (12, "hourly", 11)         # headcount spans both bases
    assert (c26["p25"], c26["median"], c26["p75"]) == (20, 21, 21)                   # $1 bands, hourly only
    assert c26["other_pay"] == [{"pay_basis": "annual", "n_pay": None, "p25": None, "median": None, "p75": None,
                                 "suppressed": True}]
    (c25,) = [c for c in cells if c["period"] == "FY2025" and c["title"] == "Library Assistant"]
    assert (c25["n"], c25["n_pay"], c25["suppressed"], c25["other_pay"]) == (None, 0, True, [])
    line = A.describe(c26, ds=ds)
    assert "Hourly rate (11 people): median about $21 an hour" in line and "other groups is not shown" in line
    assert "61,234" not in line and "61,000" not in line
    assert A.describe(c25, ds=ds) == ("City of Testville, Library (Library Assistant): fewer than 5 staff in "
                                      "FY2025. The source gives no pay figure for them.")


def test_a_mixed_annual_column_splits_hourly_rates():
    ds = make(hourly_below=1000.0)
    annual = (52100, 52200, 52300, 52400, 52450, 52550, 52600, 52700, 52800, 52900, 52950)
    rows = [{"department": "Sheriff", "job_title": "Deputy", "annual_base_rate": str(v)}
            for v in annual + (21.5, 34.17)]
    projected = [S.project(r, ds) for r in rows]
    assert [p["pay_basis"] for p in projected] == ["annual"] * 11 + ["hourly"] * 2
    c = cell(A.aggregate(projected, ds, retrieved_at="2026-10-10"), "Sheriff", "Deputy")
    assert (c["n"], c["pay_basis"], c["n_pay"], c["median"]) == (13, "annual", 11, 53000)
    assert c["other_pay"][0]["pay_basis"] == "hourly" and c["other_pay"][0]["suppressed"]
    assert c["other_pay"][0]["n_pay"] is None
    with pytest.raises(ValueError, match="hourly_below"):
        make(hourly_below=1000.0, pay_basis="hourly")


def test_quantile_matches_linear_interpolation():
    pairs = [(10.0, 1), (20.0, 2), (40.0, 1)]                 # 10, 20, 20, 40
    assert [A.quantile(pairs, q) for q in (0, 0.25, 0.5, 0.75, 1)] == [10.0, 17.5, 20.0, 25.0, 40.0]
    assert A.parse_pay("$1,234.50") == 1234.5 and A.parse_pay("0") is None and A.parse_pay("n/a") is None
    assert A.band(52499, "annual") == 52000 and A.band(20.6, "hourly") == 21
    with pytest.raises(KeyError):
        A.band(700, "per week")


def test_describe_shows_pay_only_for_published_groups():
    ds = make()
    cells = A.aggregate(threshold_rows(), ds, retrieved_at=WHEN)
    line = A.describe(cell(cells, "Records", A.ALL), ds=ds)
    assert line == ("City of Testville, Records: 11 staff as of 2026-10-10. Annual base pay: median about $50,000, "
                    "middle half about $50,000 to $51,000.")
    five = A.describe(cell(cells, "Budget", "Analyst"), ds=ds)
    assert "5 staff" in five and "$" not in five and f"groups of {A.MIN_PAY} or more" in five
    four = A.describe(cell(cells, "Archive", "Archivist"), ds=ds)
    assert "fewer than 5 staff" in four and "$" not in four
    real = dict(cell(cells, "Records", A.ALL), source="va-norfolk-salaries")
    assert A.describe(real, source=True).endswith(
        "Source: City of Norfolk, Department of Human Resources, Employee Salaries (https://data.norfolk.gov/d/4fsk-z8s8).")
    assert "11 payroll entries" in A.describe(real)                 # Norfolk's rows are not known to be people


def test_describe_gives_a_large_group_no_small_group_reason():
    """Re-check 2 (N12): an earlier period of a two-period fetch (11 clerks, pay withheld by rule 6) was explained
    as if the group were under 11. The line now says only what the cell shows."""
    rows = ([dict(r, period="2025") for r in people("Records", "Clerk", CLERKS)]
            + [dict(r, period="2026") for r in people("Records", "Clerk", CLERKS + [61100])])
    ds = by_year()
    old = [c for c in A.aggregate(rows, ds, retrieved_at=WHEN) if c["period"] == "FY2025" and c["title"] == "Clerk"]
    line = A.describe(old[0], ds=ds)
    assert old[0]["n_pay"] == 11 and f"groups of {A.MIN_PAY} or more" not in line
    assert A.HIDDEN["other"] in line and "period" in line
    week = make(fields={"agency": "dept", "title": "job", "pay": "rate", "pay_basis": "basis"}, pay_basis=None)
    pool = [S.project({"dept": "Pool", "job": "Lifeguard", "rate": str(700 + i), "basis": "per week"}, week)
            for i in range(12)]
    assert A.HIDDEN["basis"] in A.describe(A.aggregate(pool, week, retrieved_at=WHEN)[0], ds=week)
    assert "staff" in line and "payroll entries" in A.describe(old[0], ds=by_year(rows="unknown"))


def test_sample_keeps_totals_and_records_offices():
    ds = make()
    cells = A.aggregate([S.project(r, ds) for r in table_rows()], ds, retrieved_at="2026-10-10")
    picked = A.sample(cells, top_agencies=1, titles=2)
    keys = [(c["agency"], c["title"]) for c in picked]
    assert (A.ALL, A.ALL) in keys and ("Clerk's Office", A.ALL) in keys
    assert ("Clerk's Office", "Deputy Clerk") in keys and ("Clerk's Office", "City Clerk") in keys
    assert ("Police", A.ALL) not in keys


# ---- polite fetching (fake session, fake clock) -------------------------------------------------------------

class Clock:
    def __init__(self):
        self.t = 0.0
        self.slept = []

    def now(self):
        return self.t

    def sleep(self, dt):
        self.slept.append(dt)
        self.t += dt


class FakeResponse:
    def __init__(self, status=200, payload=None, text="", headers=None):
        self.status_code, self._payload, self.text, self.headers = status, payload, text, headers or {}

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def close(self):
        pass


class FakeSession:
    """Serves robots.txt and Socrata pages. ``routes`` maps a URL (without query) to a response, an exception to
    raise, or a function of (url, params)."""

    def __init__(self, clock, rows, robots="User-agent: *\nCrawl-delay: 1\nDisallow: /api/odata/\n", fail_first=0,
                 routes=None):
        self.clock, self.rows, self.robots, self.fail_first = clock, rows, robots, fail_first
        self.routes = routes or {}
        self.calls = []

    def get(self, url, params=None, timeout=None, stream=False, headers=None, allow_redirects=True):
        self.calls.append({"url": url, "params": params, "timeout": timeout, "headers": headers, "at": self.clock.t,
                           "allow_redirects": allow_redirects})
        route = self.routes.get(url.split("?")[0])
        if isinstance(route, Exception):
            raise route
        if callable(route):
            return route(url, params)
        if route is not None:
            return route
        if url.endswith("/robots.txt"):
            return FakeResponse(200, text=self.robots)
        if self.fail_first:
            self.fail_first -= 1
            return FakeResponse(429, headers={"Retry-After": "3"})
        if params is None:                               # a redirect hop: the query is in the URL
            params = {k: v[0] for k, v in parse_qs(urlsplit(url).query).items()}
        off, lim = int(params["$offset"]), int(params["$limit"])
        return FakeResponse(200, payload=self.rows[off:off + lim])


def grouped_rows(n):
    return [{"department": f"D{i % 3}", "job_title": f"T{i}", "annual_base_rate": str(40000 + i), S.COUNT: "2"}
            for i in range(n)]


def client(session, clock):
    return S.Http(session, sleep=clock.sleep, clock=clock.now, log=lambda m: None)


ROBOTS = "https://data.example.gov/robots.txt"
ENDPOINT = "https://data.example.gov/resource/abcd-1234.json"


def test_fetch_pages_politely_and_stops_on_a_short_page():
    clock = Clock()
    session = FakeSession(clock, grouped_rows(25), robots="User-agent: *\nCrawl-delay: 2\n")
    got = S.fetch_soda(make(), client(session, clock), page_size=10, log=lambda m: None)
    assert [c["url"].rsplit("/", 1)[-1] for c in session.calls] == ["robots.txt"] + ["abcd-1234.json"] * 3
    assert all(c["headers"]["User-Agent"] == S.USER_AGENT and c["timeout"] == S.TIMEOUT for c in session.calls)
    assert all(c["allow_redirects"] is False for c in session.calls)       # redirects are checked by hand
    times = [c["at"] for c in session.calls]
    assert all(b - a >= 2.0 for a, b in zip(times, times[1:]))         # the site's Crawl-delay, at least 1 s
    assert (got.read, got.truncated, got.requests, len(got.rows)) == (25, False, 4, 25)
    assert sum(r["n"] for r in got.rows) == 50
    assert "$limit" not in got.query and got.query["$select"].endswith(f"AS {S.COUNT}")


def test_row_cap_marks_the_result_truncated():
    clock = Clock()
    got = S.fetch_soda(make(), client(FakeSession(clock, grouped_rows(40)), clock), page_size=10, row_cap=15,
                       log=lambda m: None)
    assert (got.read, got.truncated) == (15, True)


def test_a_truncated_fetch_keeps_no_cells():
    clock = Clock()
    fx = A.build_fixture(datasets=[make()], http=client(FakeSession(clock, grouped_rows(40)), clock), row_cap=15,
                         log=lambda m: None)
    (src,) = fx["sources"]
    assert src["truncated"] and "no cell" in src["withheld"] and fx["aggregates"] == []
    assert "cells" not in src and "people" not in src
    clock = Clock()
    whole = A.build_fixture(datasets=[make()], http=client(FakeSession(clock, grouped_rows(40)), clock),
                            log=lambda m: None)
    assert not whole["sources"][0]["truncated"] and whole["aggregates"] and whole["sources"][0]["people"] == 80


def test_rebuilding_a_fixture_carries_its_record_forward():
    """Re-check 2 (N10): a committed fixture is a release with history. Rebuilding it compares the new release with
    the record of the old one (rule 7), and keeps that record, for every source, in the new fixture."""
    def build(**kw):
        clock = Clock()
        return A.build_fixture(datasets=[make()], http=client(FakeSession(clock, grouped_rows(40)), clock),
                               log=lambda m: None, **kw)
    first = build()
    record = first["pay_published"]["t-city"]
    assert record and record == A.ledger(first)["t-city"] and set(first["sources"][0]["pay_groups_withheld"]) == set(A.WHY)
    assert {g["n_pay"] for g in record} == {26}                      # two agencies of 26 rows each
    again = build(earlier=[first])                                   # the same data a second time
    assert not any(figures(c) for c in again["aggregates"])
    assert again["sources"][0]["pay_groups_withheld"]["release"] == 2
    assert again["pay_published"] == first["pay_published"]
    later = A.build_fixture(datasets=[], log=lambda m: None, earlier=[again])    # a build that fetches nothing
    assert later["pay_published"] == first["pay_published"]                     # still remembers t-city


def test_the_command_line_compares_with_the_fixture_it_replaces(tmp_path, monkeypatch):
    seen = {}

    def fake_build(ids, *, row_cap, log, earlier):
        seen["earlier"] = earlier
        return {"aggregates": []}
    monkeypatch.setattr(A, "build_fixture", fake_build)
    out = tmp_path / "fx.json"
    out.write_text(json.dumps({"pay_published": {"x": [{"period": "p", "pay_basis": "annual", "n_pay": 30}]},
                               "aggregates": []}), encoding="utf-8")
    A.main(["--out", str(out)])
    assert {"x": [{"period": "p", "pay_basis": "annual", "n_pay": 30}]} in [e.get("pay_published") for e in
                                                                          seen["earlier"]]
    assert len(seen["earlier"]) == 2                                 # and the committed fixture


def test_research_note_no_longer_recommends_pay_statistics_of_small_groups():
    """Re-check N3: the research note's cell-size-5 rule with mean, median, min and max is marked superseded, and
    it links the hosts the sources moved to."""
    text = DOCS["payroll-research.md"]
    for stale in ("mean REAL", "median REAL, min REAL", "mean plus min and max", "Store a mean or median only when",
                  "](https://data.sfgov.org", "](https://publicpay.ca.gov"):        # (pay_scales keeps grade min, max)
        assert stale not in text, stale
    assert "superseded" in text.lower() and "payroll-plan.md" in text
    assert "one person's pay" in text                              # why a minimum or maximum is never stored


def test_a_refused_source_is_recorded_without_cells():
    clock = Clock()
    session = FakeSession(clock, grouped_rows(3), routes={ROBOTS: FakeResponse(503)})
    fx = A.build_fixture(datasets=[make()], http=client(session, clock), log=lambda m: None)
    (src,) = fx["sources"]
    assert "HTTP 503" in src["error"] and src["fields"] == make().fields and fx["aggregates"] == []


def test_robots_disallow_is_respected():
    clock = Clock()
    session = FakeSession(clock, grouped_rows(3), robots="User-agent: *\nDisallow: /resource/\n")
    with pytest.raises(PermissionError):
        S.fetch_soda(make(), client(session, clock), log=lambda m: None)
    assert len(session.calls) == 1                                       # robots.txt only


@pytest.mark.parametrize("status", [500, 502, 503, 504])
def test_robots_txt_server_error_means_complete_disallow(status):
    clock = Clock()
    session = FakeSession(clock, grouped_rows(3), routes={ROBOTS: FakeResponse(status)})
    with pytest.raises(PermissionError, match=f"HTTP {status}"):
        S.fetch_soda(make(), client(session, clock), log=lambda m: None)
    assert session.calls and all(c["url"] == ROBOTS for c in session.calls)   # the data was never requested


@pytest.mark.parametrize("status", [401, 403, 429])
def test_robots_txt_refusal_means_complete_disallow(status):
    clock = Clock()
    session = FakeSession(clock, grouped_rows(3), routes={ROBOTS: FakeResponse(status)})
    with pytest.raises(PermissionError):
        S.fetch_soda(make(), client(session, clock), log=lambda m: None)
    assert all(c["url"] == ROBOTS for c in session.calls)


@pytest.mark.parametrize("status", [404, 410])
def test_missing_robots_txt_means_no_rules(status):
    clock = Clock()
    session = FakeSession(clock, grouped_rows(3), routes={ROBOTS: FakeResponse(status)})
    got = S.fetch_soda(make(), client(session, clock), log=lambda m: None)
    assert len(got.rows) == 3


def test_unreachable_robots_txt_means_complete_disallow():
    clock = Clock()
    session = FakeSession(clock, grouped_rows(3), routes={ROBOTS: requests.ConnectionError("no route")})
    with pytest.raises(PermissionError, match="unreachable"):
        S.fetch_soda(make(), client(session, clock), log=lambda m: None)
    assert all(c["url"] == ROBOTS for c in session.calls)


def moved(to_host: str, status: int = 301):
    """A route that redirects a request, query and all, to the same path on another host."""
    def route(url, params):
        full = requests.Request("GET", url, params=params).prepare().url
        return FakeResponse(status, headers={"Location": full.replace("data.example.gov", to_host)})
    return route


def test_redirect_to_an_unlisted_host_is_refused():
    clock = Clock()
    session = FakeSession(clock, grouped_rows(3), routes={ENDPOINT: moved("elsewhere.example.com")})
    with pytest.raises(PermissionError, match="does not list elsewhere.example.com"):
        S.fetch_soda(make(), client(session, clock), log=lambda m: None)
    assert not any("elsewhere" in c["url"] for c in session.calls)


def test_redirect_to_the_listed_host_rechecks_robots_and_spacing():
    clock = Clock()
    new_robots = "https://new.example.gov/robots.txt"
    session = FakeSession(clock, grouped_rows(3), routes={
        ENDPOINT: moved("new.example.gov"), new_robots: FakeResponse(200, text="User-agent: *\nCrawl-delay: 3\n")})
    ds = make(url="https://new.example.gov/d/abcd-1234")             # the registry lists the new host
    got = S.fetch_soda(ds, client(session, clock), log=lambda m: None)
    urls = [c["url"].split("?")[0] for c in session.calls]
    assert urls == [ROBOTS, ENDPOINT, new_robots, "https://new.example.gov/resource/abcd-1234.json"]
    assert session.calls[3]["at"] - session.calls[2]["at"] >= 3.0     # the new host's own Crawl-delay
    assert len(got.rows) == 3 and got.requests == 4


def test_redirect_target_disallowed_by_its_robots_txt_is_not_requested():
    clock = Clock()
    new_robots = "https://new.example.gov/robots.txt"
    session = FakeSession(clock, grouped_rows(3), routes={
        ENDPOINT: moved("new.example.gov"), new_robots: FakeResponse(200, text="User-agent: *\nDisallow: /resource/\n")})
    with pytest.raises(PermissionError, match="robots.txt disallows https://new.example.gov"):
        S.fetch_soda(make(url="https://new.example.gov/d/abcd-1234"), client(session, clock), log=lambda m: None)
    assert [c["url"] for c in session.calls][-1] == new_robots


def test_same_host_redirect_is_checked_against_robots():
    clock = Clock()
    session = FakeSession(clock, grouped_rows(3), robots="User-agent: *\nDisallow: /private/\n",
                          routes={ENDPOINT: FakeResponse(302, headers={"Location": "/private/abcd-1234.json"})})
    with pytest.raises(PermissionError, match="/private/"):
        S.fetch_soda(make(), client(session, clock), log=lambda m: None)
    assert not any("/private/" in c["url"] for c in session.calls)


def test_redirect_from_https_to_http_is_refused():
    clock = Clock()
    session = FakeSession(clock, grouped_rows(3), routes={
        ENDPOINT: FakeResponse(301, headers={"Location": "http://data.example.gov/resource/abcd-1234.json"})})
    with pytest.raises(PermissionError, match="leaves https"):
        S.fetch_soda(make(), client(session, clock), log=lambda m: None)


def test_redirect_loops_stop_and_every_hop_is_spaced():
    clock = Clock()
    session = FakeSession(clock, grouped_rows(3), routes={ENDPOINT: FakeResponse(302, headers={"Location": ENDPOINT})})
    with pytest.raises(RuntimeError, match="redirects"):
        S.fetch_soda(make(), client(session, clock), log=lambda m: None)
    hops = [c["at"] for c in session.calls if c["url"].startswith(ENDPOINT)]
    assert len(hops) == S.MAX_REDIRECTS + 1 and all(b - a >= 1.0 for a, b in zip(hops, hops[1:]))


def test_robots_txt_redirect_is_followed_only_to_a_listed_host():
    clock = Clock()
    new_robots = "https://new.example.gov/robots.txt"
    routes = {ROBOTS: FakeResponse(301, headers={"Location": new_robots}),
              new_robots: FakeResponse(200, text="User-agent: *\nDisallow: /resource/\n")}
    session = FakeSession(clock, grouped_rows(3), routes=routes)
    with pytest.raises(PermissionError, match="robots.txt disallows"):    # the redirected file's rules apply
        S.fetch_soda(make(url="https://new.example.gov/d/abcd-1234"), client(session, clock), log=lambda m: None)
    assert [c["url"] for c in session.calls] == [ROBOTS, new_robots]
    clock = Clock()
    session = FakeSession(clock, grouped_rows(3), routes=routes)
    with pytest.raises(PermissionError, match="does not list new.example.gov"):
        S.fetch_soda(make(), client(session, clock), log=lambda m: None)
    assert [c["url"] for c in session.calls] == [ROBOTS]


def test_429_waits_for_retry_after_then_retries():
    clock = Clock()
    session = FakeSession(clock, grouped_rows(3), fail_first=1)
    got = S.fetch_soda(make(), client(session, clock), log=lambda m: None)
    assert len(got.rows) == 3 and 3 in clock.slept and len(session.calls) == 3


def test_fetch_refuses_datasets_the_prototype_does_not_read():
    with pytest.raises(ValueError, match="not read by this prototype"):
        S.fetch(S.get("md-montgomery-salaries-2025"))
    with pytest.raises(ValueError):
        make(api="arcgis")                                               # only soda and csv can be fetched
