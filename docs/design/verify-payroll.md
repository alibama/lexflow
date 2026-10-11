# Verification: payroll prototype

Checked 2026-10-10, 15:40 to 16:30 UTC, against `lexflow/payroll/`, `tests/test_payroll.py`,
`fixtures/payroll/sample_aggregates.json` and [payroll-plan.md](payroll-plan.md). Nothing was edited except this
note. (Two figures in "Confirmed" were redacted after the re-check, at its request (N4); the redactions are marked.)

Network use: about 160 GET requests across about 30 hosts. Each used the research User-Agent and a 15 s timeout.
robots.txt was read first on every host; Crawl-delay was honoured (60 s on two ArcGIS hubs) and requests to one
host were at least 1.1 s apart. Data queries selected only department, title and pay, or server-side counts.
Nothing was written remotely and no `.env` value was read. Three landing pages redirected to another host, and that
host's robots.txt was not re-checked (the same gap as finding W3).

## Confirmed

* **Tests.** `pytest tests/test_payroll.py`: 58 passed. Fixture: 44 cells, 18,437 bytes.
* **No person-level field reaches disk.**
  * `project()` returns only the mapped fields plus `n`.
  * `soda_params()` selects and groups only the mapped columns. The fixture's recorded queries match.
  * `build_fixture()` writes cells and source metadata only, and clears the projected rows.
  * Fixture cell keys are exactly the 15 aggregate keys. The only name-like strings in the fixture are the column
    names in `never_read` (`first_name`, `last_name`, `start_date`, `title_date`), never values.
  * No raw payroll file exists in the repo or in the container's `/tmp` or `/root`. Only the six payroll files
    mention the dataset IDs.
* **The fixture is correct.** A fresh read-only fetch recomputed, independently with `numpy.quantile` (linear),
  **all 44 cells: 0 mismatches.** That covers headcount, `n_pay`, the three quartiles and suppression, on both
  bases.
  * Norfolk: 4,927 people. 917 have pay under 1,000. No pay values are null.
  * Seattle: 14,820 people.
  * The builder's `aggregate()` on fresh data gives 1,082 cells (853 suppressed) and 2,215 cells (1,535
    suppressed), as recorded.
  * The City Clerk example (14 staff, 13 of them salaried) was recomputed from the rows: its headcounts and its
    three quartiles matched. [Redacted after the re-check (N4): the quartiles were order statistics of 13 people,
    so each was one person's pay to the nearest $100, and they are no longer quoted.]
* **Norfolk's mixed column.** Grouping by Employee Status (counts, minimum and maximum only) confirms the < 1,000
  rule for today's data:
  * Every value under 1,000 is in a temporary, part-time, retiree, state-compensated or sheriff class.
  * A wide gap separates the highest hourly rate from the lowest annual salary, and the registry note's ranges
    (hourly rates all under $200, no figure between $200 and $5,000) hold. [Redacted after the re-check (N4): the
    top hourly figure was quoted to within about a dollar, and is no longer quoted.]
  * Two classes hold both bases. The rule splits them correctly.
* **Registry.** All 27 URLs were checked.
  * 26 landing pages return HTTP 200. Florida's was not requested, because its robots.txt disallows this
    User-Agent (link-only, as registered).
  * All Socrata entries have `provenance: official`. The ArcGIS items are owned by the governments' own accounts.
  * Licences match the publishers' metadata:
    * Public Domain: Norfolk, Seattle, Cook.
    * PDDL: SF.
    * CC BY 4.0: LA City, DC, Charlotte, Miami.
    * ODC-BY: Houston.
    * "As is" disclaimer: Miami-Dade.
    * Use constraints and site terms: Virginia Beach.
    * None stated: NYC (all three), Montgomery, NY (both), Dallas, Baltimore, LA County.
  * All 14 `fields` maps and `drop` lists match the publishers' column schemas.
  * All 19 `gov_id`s match the `governments` table (read-only query).
  * Staleness is confirmed: DC was last modified 26 Sep 2024, Cook's rows were last updated 25 Jun 2018, Dallas's
    on 25 Oct 2019.
* **Only clearly licensed sources are fetched.** The only fetched sources are Norfolk and Seattle: Public Domain,
  official, with robots.txt `Crawl-delay: 1` and `/resource/` allowed.
  * Both portals' footer "Terms" links return 404, and the Socrata catalog lists no terms page for either.
  * Nothing found forbids reuse.
  * No source whose terms are restrictive or unread is fetched.
* **San Francisco.** 35,607 FY2026 permanent staff, and `employee_identifier` is labelled "Employee Name": both
  confirmed. The HTTP 428 was not re-triggered on purpose.
* **Setup tie-in, as the user asked.** It is referenced as one optional Setup step (`workforce`, plan P1 and §5.1),
  with no new page. `steps.py`, `db.py` and `municipal/answer.py` are unchanged: their modification times predate
  the build, and they have no payroll or workforce references.
* No person is named as a partner, advisor or endorser.

## Wrong

**W1. The small-cell protection is weaker than the plan claims** (P4, §6.1 items 4 and 5, and the `aggregate.py`
docstring). The plan claims that "rounding means a published figure is never one person's exact pay" and that no
one's pay can be worked out from a roll-up. Neither holds.

* With type-7 quantiles, a group of 4k+1 people publishes its exact order statistics, rounded only to $100 or
  $0.25. A 5-person cell publishes the 2nd, 3rd and 4th person's pay.
* 34 Norfolk and 126 Seattle published groups have exactly 5 people.
* 16 Norfolk and 46 Seattle published quartiles equal one person's exact, unrounded pay, in 10 and 29 groups. 5 and
  18 of those groups have fewer than 10 people.
* 13 Norfolk and 8 Seattle holders of single-person titles have their own pay suppressed. Yet their (unique) pay
  appears as an exact order statistic of their agency roll-up.
* The source already publishes these values person by person, so the harm is small. But the stated rule is not
  what the code does.
* Fix: either publish quartiles only for 10 or more people (the median alone from 5 to 9) and use coarser bands
  ($1,000 a year, $1 an hour), or reword the claims.
* The plan and the Norfolk registry note also quote single people's exact extreme pay. Give ranges instead.

**W2. A robots.txt that fails with a 5xx is treated as allow-all** (`sources.py` `Http.allowed`, the
`status_code >= 400` branch). Tested offline: 500, 502 and 503 all give `allowed=True`. RFC 9309 says to assume
complete disallow on 5xx. Treat only 4xx other than 401 and 403 as allow, and add a test.

**W3. Redirects bypass the robots and spacing checks.** `requests` follows redirects to other hosts by default.
SF's endpoint now returns 301 to `data.sf.gov`, and its landing page moved there too. Update the SF entry. Either
refuse cross-host redirects or re-check robots.txt for the final host.

**W4. Registry notes are wrong or stale.**

* **Chicago.** Its terms are readable now (via chicago.gov, HTTP 200). They require a set disclaimer on any
  derived application, let the City demand that use stop, and contain an indemnity. That is the operator-decision
  case the builder described for Montgomery County. Chicago is not fetched, so nothing was violated, but the note
  ("terms not read") needs the real reason.
* **Montgomery County.** The "disclaimer plus indemnity" claim could not be reproduced, and no source for it is
  recorded.
  * The portal's Terms of Use link (`/page/terms-of-use`) and the county's `/disclaimer` both return 404.
  * The county's site-wide User Rights terms have warranty disclaimers but no indemnity. They also describe the
    sites as maintained for personal use; it is unclear whether that covers the data portal.
  * Keep the dataset unfetched, but record "terms not found or unclear". Drop plan §5.1's credit-note idea until a
    person reads the terms.
* **California GCC.** `publicpay.ca.gov` now redirects to `gcc.sco.ca.gov`, which answered 200 (not 403).
  robots.txt allows it. Update the URL and the note.
* **NC State Controller.** Its terms are now read: non-commercial copying is allowed, unaltered and with a
  citation. Link-only fits; update "not read".

**W5. The column guard misses common person-level names.** `PERSON_FIELD` accepts, among others: `EMPLID` (the
PeopleSoft employee ID), `empl_id`, `ee_id`, `badge_number`, `position_number`, `name_last`, `lname`, `fname`,
`emp_nm`, `incumbent`, `employee`, `zip_code`, `phone_number`, `address_line_1`, `gender_code`, `race_desc`,
`age_group`, `veteran_status`, `GlobalID`, `unique_id` and `ssn_last4`. The allowlist is still the real
protection. But the summary's claim that the guard "refuses any map pointing at a name, ID, date, demographic or
contact column" is overstated. Extend the pattern and the parametrized test.

**W6. Smaller inaccuracies in the plan.**

* §6.1 item 3 ("names never cross the network") is true only for the Socrata grouped path. `fetch_csv` downloads
  the whole file, names included, into memory.
* §5 says a capped run's cells are not shown, but `build_fixture()` still aggregates and samples a truncated
  fetch.
* "Annual base pay" pools part-time salaried staff, elected officials and council appointees with full-time staff.
  Small offices' medians mix the two. Norfolk's Employee Status column is aggregate-safe and could qualify the
  basis (the builder's open question 4).

## Missing

* Tests for: robots.txt 5xx, cross-host redirects, the guard names in W5, and withholding a truncated fetch.
* Terms still unread, all for unfetched sources. A person should read each before enabling it:
  * NYC (www.nyc.gov's robots.txt returns 403, so it was not requested);
  * data.ny.gov (its terms are a PDF and were not downloaded);
  * Virginia Beach's "About this Site" terms;
  * Montgomery County's portal terms (404).
* Seattle's and Norfolk's portal terms: none exist at the linked URLs. Their licence rests on the dataset metadata
  alone, which is adequate (Public Domain), but should be recorded as such.

## Re-check, 2026-10-10 (17:10 to 17:30 UTC)

Checked the fix against the current `lexflow/payroll/`, `tests/test_payroll.py`, the fixture and the plan.
Nothing was edited except this section.

Network use: 7 GET requests, all through the project's own `Http` client (research User-Agent, robots.txt first,
Crawl-delay honoured, at least 1 s between requests to one host). data.sf.gov got 3: robots.txt, the landing page and
its same-host 302. data.norfolk.gov and data.seattle.gov got 2 each, a grouped query of department, title and pay
only. The rows were held in memory and only counts were printed.

### Fixed

* **Tests.** 159 passed in `lexflow-app-1`, and the `python -W error` import passes. I made 14 mutations, each
  undoing one fix, on a copy in the container's `/tmp`. Every one makes a test fail, and the unmutated copy passes.
  The mutations: the near check, the exact check, rule 5, `MIN_PAY` back to 5, an unknown basis published, a
  robots.txt answering 5xx, 429 or unreachable read as allow, an https-to-http hop, a hop to an unlisted host, a
  hop not checked against robots.txt, a truncated fetch kept, the guard without word splitting, and a literal `*`
  read as a roll-up.
* **W1: fixed, apart from N1 below.** A fresh fetch gives the same source data as the fixture:
  * Each source's people, cells, headcounts withheld, suppressed cells and pay groups withheld per rule are equal.
    All 44 sample cells equal a recomputation.
  * 66 and 213 pay groups are shown. Agencies with pay: 11/42 and 9/41. Cells under 11 people on their main basis:
    89 % and 86 %.
  * Checked independently against the rows: no published figure covers fewer than 11 people, none equals the exact
    pay of 1 to 10 people, none has 1 to 4 people within half a step, and no nested pair or remainder of published
    groups holds 1 to 10 people.
  * The original case: of 555 Norfolk and 911 Seattle one-person titles, no holder's exact pay is a published
    roll-up figure (before the fix, 13 and 8 were).
  * The groups the plan says rule 4 withholds (Norfolk's city-wide and Police annual groups, Seattle's city-wide and
    Public Library groups) are withheld for that reason. Three published figures per source equal a rate that 11 or
    more people share, which rule 4 allows.
  * A randomised search found no violation in 2,100 payrolls (one basis, mixed bases, two periods) or in 1,488 more
    seeds of the test's own generator.
  * The plan and the Norfolk note now give ranges, and the ranges hold on today's data.
* **W2: fixed.** A robots.txt answering 5xx, 401, 403 or 429, or not reachable at all, means complete disallow. 404
  and 410 mean no rules.
* **W3: fixed.** Every hop is checked against robots.txt and spaced like any request. Hops to unlisted hosts and
  from https to http are refused, robots.txt redirects included. SF: data.sf.gov's robots.txt allows `/resource/`
  with a 1 s crawl delay. `/d/88g8-5mnd` answers 302 on the same host, then 200.
* **W4, W6 and Missing: fixed** as described in the fix report.
* **W5: fixed** for every listed spelling. All 38 ordinary column names I tried still pass.

### Not fixed, or new

* **N1 (new, privacy weakness, not reachable today).** Rule 5 runs per period, but `aggregate()` publishes pay for
  every period in one fetch.
  * A synthetic test case: FY2025 has 11 clerks, and FY2026 has the same 11 plus one newcomer. Both years' agency
    figures are published (11 and 12 people).
  * Then 2 × the FY2026 median − the FY2025 median gives the newcomer's pay to within $100. This is the attack
    that `test_a_single_title_holder_cannot_be_recovered_by_differencing` defends against within one period.
  * The docstring's headline ("no union or difference of published groups isolates fewer than 11 people") is
    therefore overstated. The plan's "Rule 5 works within one release" is too: rule 5 works within one *period*.
  * Affected if enabled: the entries with a period column and no single-period `where`, which are
    `ny-nyc-payroll`, `ca-la-city-payroll`, `il-cook-county-payroll` and `ny-state-authorities-salaries`. The NYC
    and LA City notes say to filter one year; the other two do not.
  * Suggested fix: keep pay for the latest period only, or make `check_fields` require a single-period `where`
    for a fetched source with a period column. Document whichever is chosen.
* **N2 (W5 residual, overstated docstring).** The guard still accepts the following spellings:
  * names: `l_name`, `f_name`, `m_name`, `lst_nm`, `frst_nm`, `payee_name`, `supervisor_name`, `manager_name`,
    `contact_name`, `name_of_employee` and `nickname`;
  * IDs: `payee_id`, `empno`, `employeenumber`, `empnum` and `pernr`;
  * tenure: `years_of_service`, `length_of_service`, `service_years` and `longevity`;
  * others: `sexual_orientation`, `photo_url` and `home_city`.

  The module docstring and the plan say that the guard knows common spellings, not every one, which is accurate.
  But the `looks_person_level` docstring claims "tenure" and ends "whatever the source calls it", which overstates
  it. No registry field maps to any of these names, so nothing leaks.
* **N3 (outside the fixer's files).** `payroll-research.md` still recommends storing mean, median, min and max from
  5 people (§7.3, line 233; the §7.6 sketch, line 266), with "mean plus min and max" as a fallback (line 226). A
  group's min and max are always one person's exact pay. The plan supersedes this, but the research doc does not
  say so. Lines 81 and 105 still link the old hosts.
* **N4 (this note).** "Confirmed" above still quotes the City Clerk group's three quartiles. Those are exact order
  statistics of 13 people, that is, three people's pay to the nearest $100. It also gives Norfolk's top hourly
  figure to within about a dollar. A person should redact both; this re-check may only append.
  *Redacted after the re-check:* both now state what was checked instead, each marked "[Redacted ...]", and
  `test_verification_note_is_redacted` pins it.
* **N5 (minor, overstated).** The `aggregate.py` docstring and the plan (header, P4) say the old rule published
  "exact pay". It published order statistics rounded to $100 or $0.25, which equal exact pay only for round salaries.
* **N6 (nit).** Subtracting headcounts can also show that 1 to 4 people in a title are on the other basis. For
  Norfolk that means a temporary, part-time, retiree, sheriff or state-compensated class. It never shows pay, and it
  falls under the plan's gap (c) in spirit.
* **Judgement calls accepted:** the strict rule 4 (open question 7) and not reading Norfolk's Employee Status column
  (open question 2).

## Re-check 2, 2026-10-11 (00:00 to 00:45 UTC)

Checked the round-2 fix against the current `lexflow/payroll/`, `tests/test_payroll.py`, the fixture, the plan, the
research note and this note. Nothing was edited except this section. No network request was made.

### Fixed

* **Tests.** 257 passed in `lexflow-app-1`, and the `python -W error` import passes. I made 10 mutations on a copy
  in the container's `/tmp`: rule 6 off, the earliest period published instead of the latest, period labels
  compared as plain strings, the period-column preference off, rule 5 off, glued-word splitting off, the tenure rule
  off, the home rule off, the count exemption off, and person words ignored for IDs. Every one makes a test fail.
* **N1: fixed.** Rule 6 publishes pay for one period per fetch.
  * The verifier's case (11 clerks, then the same 11 and a newcomer) now publishes pay for FY2026 only. FY2025
    keeps its headcounts.
  * I ran 400 random fetches of 2 to 4 periods, with labels such as FY9 and FY10 and some rows with no period.
    Pay appeared for at most one period, always the latest one read from the period column. That period's cells
    equal a fetch of it alone. The other periods' cells carry the same headcounts as a fetch of them alone, and no
    pay.
  * The Cook County and NY authorities notes now say to filter one year.
* **N2: fixed for every listed spelling**, and the `looks_person_level` docstring no longer claims "whatever the
  source calls it". See N7 and N8 below.
* **N3: fixed.**
  * The research note marks its cell-size-5 rule and its table sketch as superseded.
  * It drops the mean, minimum and maximum fallback.
  * It no longer quotes the DPW mean exactly, and it links the hosts the sources moved to.
  * The NYC Position Schedule note no longer republishes the minimum and maximum.
* **N4: fixed.** Both redactions are in place.
  * I scanned the plan, the research note, this note, the registry notes, the fixture and the tests for `$`
    figures, bare figures of four or more digits, email addresses and phone numbers. No individual's pay or
    contact detail was found.
  * What remains is band figures of published groups, round range bounds, and two server-side means of groups of
    thousands (the research note's query examples). The rest is synthetic test values and one official office
    mailbox.
  * The test file no longer stores the redacted figures.
* **N5 and N6: fixed** as reported.
* **Judgement calls accepted:**
  * rule 6 rather than rule 5 across periods, since no IDs are read and nobody can be matched;
  * removing the guarded figures from the test rather than hashing them;
  * a guard that errs towards refusing.

### Not fixed, or new

* **N7 (new, a defect in the N2 fix, not reachable).** The count exemption treats any ID word followed by "of" as
  a count, whatever follows.
  * So `id_of_employee`, `identifier_of_employee`, `key_of_person` and `id_of_payee` pass, while
    `name_of_employee` is refused.
  * This contradicts the stated rule (the module comment, the `looks_person_level` docstring and plan §6.1 item 2):
    the owner is "the word after of", and "no word in it names a person". For ID words, that owner check never
    runs.
  * Fix: exempt only count words (number, no, num, nbr, nr), and never a column that contains a person word.
* **N8 (residual of N2, not reachable).** The guard still accepts:
  * glued all-caps forms, common in ArcGIS schemas: `POSITIONNUMBER`, `POSITIONID`, `PAYROLLID`, `CHECKNUMBER`,
    `EMAILADDRESS`, `PHONENUMBER`, `HOMEADDRESS`, `AGEGROUP`, `STARTDT`;
  * bare nouns whose values are names: `supervisor`, `manager`, `department_head`, `officer`, `elected_official`,
    `approver`, and a bare `last`, `first` or `middle`;
  * abbreviations: `gndr`, `vet_status`, `yob`, `doh`, `begin_date`, `employment_start`, `yrs_svc`,
    `time_in_grade`, `hispanic`, `resident_state`.

  The docs say the guard knows common spellings, not every one, and that stays accurate. No registry field maps to
  any of these. The ArcGIS entries (DC, Charlotte, Virginia Beach, Miami, LA County) are the likely next sources,
  so glued all-caps names deserve one more pass before any of them is enabled.
* **N9 (new, understated limit).** The plan says only a bare whole number is beyond the doc-figure rules. Two other
  forms also pass, which I checked by appending made-up figures to a copy of this note:
  * a whole-dollar `$` figure under $1,000, which is the form an hourly, daily or monthly rate takes (and the form
    of the hourly figure redacted under N4);
  * a shorthand figure in thousands (digits followed by "k").

  The plan's N4 bullet and the fix report should name all three.
* **N10 (new, overstated mitigation, privacy weakness, not built).** The plan's answer to the two-releases gap does
  not stop the N1 attack across releases. That answer is pay from the latest release only, refreshed yearly
  (§2, §5: "a year's turnover is larger").
  * An 11-person group that gains one newcomer in a year is exactly the N1 case.
  * Earlier releases' figures survive wherever they were shown or published, such as wiki page history, a synced
    copy or a committed fixture. "Latest release only" limits what lexflow stores, not what someone else kept.
  * Before the §2 storage or any wiki publishing is built, one of two things is needed. Either add a cross-release
    rule (for example, withhold a group's pay when its `n_pay` changed by 1 to 10 since the last published release,
    while noting that equal counts can hide a swap), or keep pay out of anything with history.
  * §5 and the "Two releases" gap in §6.1 should say this.
* **N11 (new, minor, plausible).** The thresholds count rows, but the docs say people.
  * Take a source with more than one row per person per period, such as Charlotte's appended quarters or a person
    with two jobs in one agency. There, 11 rows can be fewer than 11 people, and one person's repeated rows can
    meet rule 4's within-half-a-step count.
  * Norfolk's note says one row per employee. Seattle's does not say, and I did not check it, since no fetch was
    made. Charlotte's note already says to filter one Year and Quarter.
  * Suggested fix: record one row per person per period as a registry fact for each fetched source, or say "rows"
    in the rules.
* **N12 (minor wording).**
  * Plan, line 5: "No existing file was edited." The research note and this note were edited in round 2 (N3, N4).
  * Research note §7.3: "never publishes a figure that equals or pins down 1 to 10 people's pay". Rule 4 withholds
    a figure only when 1 to 4 people are within half a step of it. The plan's wording ("never pins fewer than 5")
    is right.
  * Research note §3, the NC row, still says its terms were "not read here". Its §9 item 4 has the update, but the
    header says changed terms are corrected below.
  * The `aggregate.py` docstring and plan §6.1 say that `n` minus `n_pay` shows people on another pay basis. It
    also counts people with no pay figure: one row with an empty pay gives a difference of 1 and no other basis.
    Norfolk has no empty pay values, and it is still a count, never pay.
  * `describe()` explains an earlier period of a multi-period fetch with the small-group reason ("only for groups
    of 11 or more"). That can mislead for a large group, though it is harmless for privacy.

## Re-check 3, 2026-10-11 (04:20 to 05:00 UTC)

Checked the round-3 fix against the current `lexflow/payroll/`, `tests/test_payroll.py`, the fixture, the plan, the
research note and this note. Nothing was edited except this section.

Network use: 4 GET requests, all through the project's own `Http` client (research User-Agent, robots.txt first,
Crawl-delay honoured, at least 1 s between requests to one host): robots.txt and the dataset-level metadata
(`/api/views/metadata/v1/<id>`) on data.norfolk.gov and data.seattle.gov. Only the description, the key names and
`dataUpdatedAt` were printed. No data query was made.

### Fixed

* **Tests.** 389 passed in `lexflow-app-1`, 411 with `tests/test_design_privacy.py`, and the `python -W error`
  import passes. I made 28 mutations on a copy in the container's `/tmp`; the unmutated copy passes, and 27 of the
  mutations make a test fail:
  * N7 and N8: the count rule ignoring person words, any ID word before "of" read as a count, and each of the role
    rule, the person-words-only rule, word splitting, the trailing-number split, the time-in rule and the
    career-edge rule turned off;
  * N10: rule 7 off, equal counts allowed, a window of 6 instead of 11, the record not carried forward, `ledger()`
    ignoring a fixture's `pay_published` or its cells, `source_entry()` dropping `earlier`, and the command line
    ignoring `--out` or the committed fixture;
  * N11: the rows gate off, `describe()` showing stored pay, `rows` defaulting to `person`, and `rows` unchecked;
  * N12: every hidden group given the small-group reason, or no basis or rows reason;
  * N9: the rule for figures under $1,000, the shorthand rule and the "dollars" and "USD" forms, each off.

  The one that survives is N14 below.
* **N7: fixed** for every listed name. `id_of_employee`, `identifier_of_employee`, `key_of_person`, `id_of_payee`
  and `number_of_employee` are refused; `number_of_employees`, `no_of_positions` and `id_of_department` pass. See
  N13 for a residual.
* **N8: fixed** for every listed name (9 glued, 9 bare nouns, 10 abbreviations). Of 67 ordinary column names I
  tried, glued all-caps forms included, all pass except `step_number`, `STEPNUMBER`, `CONTRACTNUMBER` and
  `longevity_pay`. Those are refused, which errs towards refusing, as accepted in re-check 2. See N13.
* **N9: fixed.** A whole-dollar figure under $1,000 that is no named group's published figure, shorthand in
  thousands (with or without `$` or a space) and figures written with "dollars" or "USD" are now refused. See N16.
* **N10: fixed for the reported attack.**
  * The verifier's case across two fetches (11 clerks, then the same 11 and a newcomer) is withheld when the
    record is passed. Without the record it leaks the newcomer's pay to within $100.
  * A swap that keeps the count at 11, a renamed office, a group 11 larger and a record on another basis behave
    as the tests say.
  * `build_fixture()` keeps the record for every source, fetched that time or not, and the command line reads
    `--out` and the committed fixture.
  * Plan §2, §5 and §6.1 no longer rest on turnover or on keeping only the latest release.
  * New gaps: N15, N17 and N18.
* **N11: fixed.**
  * All 27 entries are `rows='unknown'`, and `check_fields()` refuses any value other than `person` or `unknown`.
  * `aggregate()` publishes no pay from a `rows='unknown'` source, and `describe()` shows no pay for any of the
    44 fixture cells.
  * Both quoted descriptions match the publishers' metadata word for word, and neither says how many rows one
    person has.
  * The metadata endpoint has no `columns` key and no cached column statistics, as the plan says.
* **N12: fixed**, all five items. The lines in plan §1.3 match what `describe()` prints for those fixture cells,
  in both forms. The City Clerk line in §4.2 has the same reasons, with the date written out in words.
* **Judgement calls accepted:**
  * no pay from a `rows='unknown'` source until a publisher documents one row per person;
  * rule 7 as a suppression rule against a permanent record, ignoring agency and title and withholding equal
    counts;
  * "begin" read as a person date beside period words;
  * one general reason for rules 4 to 7 in `describe()`.

### Not fixed, or new

* **N13 (residual of N7 and N8, not reachable).**
  * The count exemption covers the whole column. Once a column has a count word followed by "of" and no person
    word, every ID word in it is exempt, so `id_number_of_record`, `uid_num_of_entries` and
    `position_number_of_record` pass. Exempt only the count word itself.
  * The guard still accepts ArcGIS editor-tracking and workflow columns, which hold staff account names:
    `created_user`, `last_edited_user`, `Creator`, `Editor`, `approved_by` and `modified_by`. Editor tracking is
    common on ArcGIS layers, and the ArcGIS entries are the likely next sources.
  * It also accepts a person noun after a qualifier (`check_payee`, `assigned_employee`, `board_member`,
    `council_member`), roles it does not list (`clerk`, `assignee`, `owner`, `record_owner`), and `svc_date`,
    `EFFDT`, `military_status` and `mar_status`.
  * The docs' "common spellings, not every one" stays accurate, and no registry field maps to any of these.
  * Wording: the `sources.py` module docstring says the guard refuses "a column that is only a person word or a
    role". The code refuses any column that ends in a role (`department_head`, `account_holder`), which is wider.
* **N14 (test gap).** With `pay_groups()` changed to ignore `other_pay`, all 389 tests still pass. Rule 7's record
  would then miss every pay group published on a cell's second basis. In the committed fixture that is 3 of
  Norfolk's 7 recorded groups (annual 12, hourly 29 and hourly 917); the 12 are the Clerk of the Circuit Court's
  annual staff. Pin it with a test.
* **N15 (new, privacy weakness, not reachable).** Rule 7 compares pairs, but three groups across two releases can
  still isolate one person. A synthetic case, with pay on scale steps so that rule 4 allows the figures:
  * The earlier release publishes the government (105 people) and Agency A (70). Agency B (30) is withheld by
    rule 5, because Agency C has 5. So the government minus Agency A is B's 30 and C's 5.
  * In this release B gains a newcomer (31). Its gaps to the recorded groups are 74 and 39, so rule 7 allows it,
    and it is published. The government and A are withheld, as near or equal to their earlier counts.
  * This release's B minus (the earlier government minus the earlier A) is the newcomer alone; the reverse is C's
    5. Rule 5 forbids such a set within one release.
  * Whether the quartiles give the newcomer's pay depends on the figures. But within a release the plan treats any
    such set as unsafe. The docstring and plan claim only the pairwise property, which holds, and their lists of
    what is not covered name only an incomplete record.
  * Conservative fix: also record, for each earlier release, the size of every published group's remainder
    outside its published sub-groups, and withhold a group within 10 of one of those (here B, at 31 against 35).
    Otherwise state the gap.
* **N16 (residual of N9, understated limit).** A whole-thousand figure, or a whole-hundred figure under $1,000,
  passes the doc-figure rules whatever it describes. I checked a made-up sentence giving one office's only analyst
  a whole-thousand salary, and no problem was reported. W1 noted that round salaries are common. The plan's N9
  bullet names only bare numbers and figures in words as beyond the rules; add round figures.
* **N17 (new, privacy weakness, not reachable).** Rule 7's record is keyed by registry id, and a publisher that
  issues each year as a new dataset gets a new entry with an empty record.
  * Montgomery County is registered that way (`md-montgomery-salaries-2025`, "one dataset a year").
  * A synthetic case: a 2025 entry publishes 11 clerks, and a 2026 entry with its own id publishes the same 11 and
    a newcomer. Twice the 2026 median minus the 2025 median is within $100 of the newcomer's pay.
  * Fix: key the record by government and pay basis (rule 7 already ignores agency and title), or give yearly
    entries a shared series key. Say which in plan §2 and §6.1.
* **N18 (new, understated cost).** Rule 7 compares a group with every recorded group on its basis, whatever the
  agency or title, and the record is never trimmed, so the set of sizes it blocks only grows.
  * Plan §5 ("pay once a year", "for coverage") and §8 question 7 ("a rebuild soon after it would show little
    pay") suggest that waiting restores coverage. It does not.
  * On 60 of the tests' random payrolls, over three yearly releases with 8 % leaving and 10 % joining, the pay
    groups shown fell from 133 to 41 to 29.
  * This is safe, but the plan should state the cost, and §8 should ask whether a narrower comparison is
    acceptable.
* **N19 (minor wording, privacy).** The research note and plan §5 say that `/api/views/<id>.json` carries cached
  column statistics that "can include a column's most common values". Socrata's cached statistics also hold each
  column's largest and smallest values, and for a pay column those are one person's exact pay. (Not re-requested
  here, so as not to download those values.) The research note's "No person-level row was downloaded or kept"
  holds for rows, but the survey's metadata reads may have carried such values, and it should say so.
* **N20 (nits).**
  * Plan, lines 5 to 6: the research note was also edited in round 3, for N10, N11 and that caveat, not only "for
    the re-checks' N3 and N12".
  * The round-3 reads are dated 2026-10-10 (plan §1.2 and §5, and the Norfolk and Seattle notes). Round 3 came
    after re-check 2 (00:00 to 00:45 UTC on 2026-10-11), so in UTC, which this note uses, they were made on
    2026-10-11; 2026-10-10 is the local (UTC-4) date. The facts hold (see N11 above).
* **Not fixed, outside the fixer's files: the committed fixture.**
  * Its cells still carry pay figures computed as if rows were people, and its `about` text describes pay as shown
    with no rows rule.
  * `describe()` hides those figures, and `ledger()` counts them as published. That is right, since they are in
    the repository's history.
  * A conservative fix needs no fetch: write `pay_published` from `aggregate.ledger()` of the fixture first, then
    blank its figures (`suppressed: true`) and correct `about`.
