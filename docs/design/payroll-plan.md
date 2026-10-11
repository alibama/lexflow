# Public-employee aggregates: the plan

Status: plan and prototype, 2026-10-10. The prototype is `lexflow/payroll/` (a registry, a fetcher and the
aggregation), `tests/test_payroll.py` and `fixtures/payroll/sample_aggregates.json`. Nothing else is built.
Outside those files and this plan, only [payroll-research.md](payroll-research.md) (for the re-checks' N3 and
N12) and [verify-payroll.md](verify-payroll.md) (its redactions, N4) were edited. There is no new table, no Setup
step and no change to answers yet.

**Revised 2026-10-10, after [verify-payroll.md](verify-payroll.md).** The verification found that the first
small-cell rule did not do what this plan claimed: with type-7 quartiles a 5-person cell published three people's
pay, rounded only to $100 a year or $0.25 an hour (exactly, for a round salary), and roll-ups exposed, to within
that rounding, the pay of people whose own one-person cells were suppressed (its W1). The rules are now those in
§6.1: headcount from 5 people, pay from 11, coarser rounding, a check that no figure singles out a person, and a
check that no two published groups can be subtracted to isolate one. The fixture was rebuilt under them from one
more polite read of the same two sources (4 requests). The fetcher now treats a robots.txt that fails with a 5xx as
complete disallow and checks every redirect hop (W2, W3). The registry notes, the column guard and the claims below
were corrected (W4 to W6).

**Revised again the same day, after the verification's re-check** (its N1 to N6). No new fetch was made.

* *N1.* Rule 5 works within one period, but a fetch could publish pay for several. A new rule 6 publishes pay for
  one period per fetch, the latest, and keeps the other periods' headcounts. The other choice, applying rule 5
  across periods, cannot work: lexflow reads no IDs, so nobody can be matched from one period to the next. The
  registry notes of the multi-year sources now say to filter one year.
* *N2.* The column guard has general rules for name and ID columns (§6.1 item 2) and catches every spelling the
  re-check listed.
* *N3.* [payroll-research.md](payroll-research.md) now marks its cell-size-5 rule and its mean, median, minimum
  and maximum sketch as superseded, and links the hosts the sources moved to. The NYC Position Schedule note no
  longer says to republish the publisher's minimum and maximum salaries.
* *N4.* The verification note's figures that were, or approximated, one person's pay (the City Clerk group's three
  quartiles and Norfolk's top hourly rate) are redacted. The test that kept such figures out of this plan used to
  list them, which stored them too. It now applies general rules instead (as revised for N9 below).
* *N5.* The "exact pay" wording above and in P4 is corrected.
* *N6.* The headcount gap is documented (§6.1, "What the rules do not cover").

The fixture's cells are unchanged. Its `about` text and a zero count for rule 6 were added by hand, since both
sources are one-period snapshots.

**Revised a third time, after the verification's second re-check** (its N7 to N12). No data was fetched. Five
read-only requests went out through the project's own client (N11): robots.txt and the dataset description
(`/api/views/metadata/v1/<id>`, no columns and no values) on each of the two portals, and robots.txt on the Socrata
catalog host, which redirected to an unlisted host and was refused, so the catalog was not read.

* *N7.* The column guard's count exemption now covers only a count word (number, no, num, nbr, nr) followed by
  "of", in a column with no person word. `id_of_employee`, `key_of_person` and `number_of_employee` are refused;
  `number_of_employees` still passes.
* *N8.* Glued names are split into the words the guard knows (`POSITIONNUMBER`, `STARTDT`, `EMAILADDRESS`), and a
  trailing "number", "nbr" or "nr" is split off whatever precedes it. A column that is only a person word or
  ends in a role (`last`, `staff`, `supervisor`, `department_head`, `elected_official`) is refused, and so is
  every abbreviation the re-check listed (§6.1 item 2).
* *N9.* The test that keeps pay figures out of these notes now also refuses a dollar figure under $1,000 unless it
  is a rounding step, a round bound in hundreds, or a published band figure of the group its paragraph names. It
  also refuses shorthand in thousands (digits followed by "k") and figures written as dollars or USD. As before
  it refuses cents, a non-round figure from $1,000 up, and a list of salaries. Beyond it: a bare number with no
  currency mark, and a figure written in words. These notes must still be written with care.
* *N10.* Rule 7 (§6.1) withholds a pay group whose headcount is within 10 of one published from an earlier
  release, against a record that is kept for good (§2). The fixture builder already keeps that record.
* *N11.* The thresholds count rows. Pay is now published only from a source whose rows are one per person per
  period, as its publisher documents. Neither Norfolk's nor Seattle's description says so, so a fetch of either
  now gives headcounts of payroll entries and no pay, until a person confirms it with the publisher (§1.2, §8).
* *N12.* The wording the re-check listed is corrected here, in `aggregate.py` and in the research note, and
  `describe()` no longer gives a large group the small-group reason (§4.3).

The committed fixture predates the rows rule and rule 7: it was built treating rows as people, and it has no count
for either rule. It is not rebuilt here (that would be a new fetch). `describe()` shows no pay from it today (§1.3),
and rebuilding it must keep its record (§2).

This plan follows the survey in [payroll-research.md](payroll-research.md). It also uses the entity model in
[entities-contacts.md](entities-contacts.md), which exists as a plan and is not built.

Scope rules followed throughout:

* Organisations and official office channels only. The prototype keeps no row about a person. Its output and
  fixture name no employee.
* For public employees lexflow works with aggregates (by government, agency and job title or class) and with
  official role contacts. Anything person-level is linked to its official source.
* lexflow's users are private people. Nothing here collects anything about them (§6.3).

---

## 0. Key decisions

| # | Decision | Why |
|---|---|---|
| P1 | **It ties in on the Setup page, as one optional step** (`workforce`, research §8). The step is where the data is introduced, credited, opted into and refreshed. There is no new page. | Every outside dataset in lexflow is introduced and credited on its Setup card. The derived facts then show in answers and on place pages that already exist. |
| P2 | **The field map is an allowlist.** lexflow reads only the columns a dataset's `fields` map names: agency, title or class, pay, and optionally the pay basis and period. Everything else is dropped as each row is read, before anything is written. | A name column that is never named is never read. A blocklist would miss the next spelling of "name". |
| P3 | **The publisher groups the rows.** A Socrata query selects only the mapped columns, grouped with `count(*)`. Names, IDs, dates and demographics never leave the publisher's server. | Research §7.2. It also cuts the transfer: 2,011 grouped rows for Norfolk's 4,927 source rows, 4,446 for Seattle's 14,820. |
| P4 | **One cell per (state, government, agency, title, period).** It holds the headcount (shown from 5), plus quartiles for each pay basis. Quartiles appear only where at least 11 people share a basis, rounded to $1,000 a year or $1 an hour, and only when no figure singles out a person and no two published groups differ by 1 to 10 people. Pay is published for one period per fetch, never for a group within 10 people of one published from an earlier release, and only from a source whose rows are one per person per period (§6.1). | Research §7.3 asked for a minimum cell size of 5. That was not enough: with type-7 quartiles a 5-person cell published the 2nd, 3rd and 4th person's pay, rounded only to $100 a year or $0.25 an hour, so exactly for a round salary (verification W1). |
| P5 | **Aggregates attach to the government key now and to agency keys later.** Every cell carries the 14-digit `gov_id`. The publisher's department name is linked to a `lexflow:agency:<gid>:<slug>` key through the entities plan's review queue. | The entities plan mints keys once, and adding a link needs a person (its D2, D7). |
| P6 | **Nothing is fetched when someone asks a question.** Answers read stored cells. | No payroll portal learns what a user asked about (research §7.2). |
| P7 | **Only sources with a clear licence are read.** The prototype reads two public-domain Socrata datasets (headcounts only, until each publisher confirms one row per person, §1.2). Sources whose terms need an operator's decision, or have not been read, stay registered but are not read. | The workflow's terms-of-use rule. For example, Chicago's portal terms require a set disclaimer, let the City demand that a use stop, and contain an indemnity. |

---

## 1. What the prototype does

### 1.1 Files

| File | What it holds |
|---|---|
| `lexflow/payroll/sources.py` | `REGISTRY`: 27 official datasets and search tools from research §3–4. Each has its state, government and `gov_id`, publisher, landing URL, API kind, endpoint, licence, cadence, `person_level`, `ingest` (`aggregate`, `as-is`, `link` or `none`), `fields` map, `drop` list (the person-level columns at the source), pay basis, `rows` (`person` or `unknown`: whether a row is one person per period) and notes. It also has `looks_person_level` and `check_fields` (the guard), `project` (the allowlist), `soda_params`, `read_csv_rows`, `Http` (the polite client) and `fetch`. |
| `lexflow/payroll/aggregate.py` | `aggregate` (cells, roll-ups and the disclosure rules of §6.1), `pay_groups` and `ledger` (rule 7's record of what was published), `describe` (one answer line per cell), `sample` and `build_fixture`. Run it with `python -m lexflow.payroll.aggregate --out <path>`. |
| `tests/test_payroll.py` | 389 offline tests: the field map, the guard and its general rules, name-dropping on the CSV and Socrata paths, the disclosure rules (including tests that play the attacker and must fail to recover one person's pay, on literal cases, on random payrolls, on fetches that span two periods and on two releases), sources whose rows may repeat a person, mixed pay bases, the fixture's invariants and its carried-forward record, a truncated fetch, rules that keep pay figures out of these notes, and politeness (robots.txt status codes, redirects, `Crawl-delay`, 1 s spacing, `Retry-After`, the row cap) on a fake clock. |
| `fixtures/payroll/sample_aggregates.json` | 44 cells from one real fetch on 2026-10-10, with a provenance block for each source: the query sent, the request count, rows received, rows counted (`people`), cells, and how many headcounts and pay groups each rule withheld. It predates the rows rule and rule 7 (§6.1). |

### 1.2 The sources read on 2026-10-10

| Dataset | Licence | Requests (robots.txt included) | Rows received (grouped) | Rows counted | Cells | Headcounts withheld (under 5) | Pay groups shown | Pay groups withheld: under 11 / could single out a person / overlap |
|---|---|---|---|---|---|---|---|---|
| City of Norfolk, VA: [Employee Salaries](https://data.norfolk.gov/d/4fsk-z8s8) (`va-norfolk-salaries`) | Public Domain | 2 | 2,011 | 4,927 | 1,082 | 850 | 66 | 1,015 / 70 / 1 |
| City of Seattle, WA: [City of Seattle Wage Data](https://data.seattle.gov/d/2khk-5ukd) (`wa-seattle-wages`) | Public Domain | 2 | 4,446 | 14,820 | 2,215 | 1,535 | 213 | 1,901 / 101 / 0 |

A *pay group* is one pay basis within one cell. Both counts above come from the rebuild under the §6.1 rules as
they then stood. A check run during the same fetch, against the projected rows held in memory, found no published
figure that breaks rules 2 to 4, and no two nested published groups that differ by 1 to 10 rows. Only counts left
that check. Rule 6 (one period per fetch) came later and withholds nothing here: neither source has a period column,
so each fetch is one period, and the fixture records 0 for it.

**Rows are not known to be people.** Every count above is a count of rows, and the "pay groups shown" were
computed as if each row were one person. Neither publisher says so. Norfolk's description says only that the
dataset "provides base salary information about City of Norfolk employees", and Seattle's only "Wage and
classification information of City of Seattle Employees" (both read 2026-10-10). A person with two jobs would be
two rows, so 11 rows could be 10 people. lexflow reads no names or IDs, so it cannot check, and checking Seattle's
names on the server would mean querying them. Both entries are therefore `rows='unknown'`: a fetch of either today
gives headcounts of payroll entries and no pay (§6.1), until a person confirms one row per employee with each
publisher and records where it is documented (§8, question 8). Rule 7 came later too, and withholds nothing in the
fixture, which is each source's first release.

Norfolk publishes no names; its hire and title dates were never requested. Seattle publishes first and last
names, and the query never selected them. Both portals' robots.txt allow `/resource/` and set `Crawl-delay: 1`.
The client honoured that delay. Neither portal links a terms page (both footer "Terms" links answer 404), so their
licence rests on each dataset's own metadata: Public Domain.

Four findings shaped the prototype:

* **Norfolk's "Base Salary" mixes pay bases.** Temporary, part-time, retiree, sheriff and "State Comp Board" staff
  show hourly rates, all under $200 an hour. Everyone else shows an annual salary, and no figure lies between $200
  and $5,000. One grouped query by employee status (counts, minimum and maximum only) showed this. The registry
  marks the column with `hourly_below=1000`, and each cell keeps its hourly and annual figures apart. DC's `COMPRATE`
  has the same problem (research §7.2) and carries the same marker. The annual basis still pools full-time and
  part-time salaried staff, elected officials and council appointees, so a small office's annual figures mix them.
  Norfolk's Employee Status column could separate them (§8, question 2).
* **San Francisco is registered but not read.** Its Employee Compensation dataset (PDDL) holds pay actually
  received in the year. That figure barely repeats, so a grouped query returned more than 25,000 rows for 35,607
  FY2026 permanent staff. The anonymous query was then refused with HTTP 428 at offset 25,000. The client stopped
  there, did not retry, and nothing from it was kept. This source needs a Socrata app token (an optional `.env`
  key, never printed), or headcount and median computed on the server. The portal has since moved from
  `data.sfgov.org` to `data.sf.gov` (HTTP 301), and the registry lists the new host.
* **Small cells are the norm.** 89 % of Norfolk's cells and 86 % of Seattle's have fewer than 11 rows on their
  main pay basis. Their counts are kept (from 5) and their pay is not.
* **The rules cost coverage, and that is the intended trade.** In the fixture, pay shows for 11 of Norfolk's 42
  agencies and 9 of Seattle's 41, on at least one basis. Rule 4 (§6.1) withholds some large groups whenever a
  rounded quartile equals the exact pay of 1 to 10 people in the group. That happens with whole-dollar hourly rates
  and round salaries, even in groups of hundreds. Seattle's city-wide figure, Norfolk's city-wide and Police annual
  figures, and Seattle Public Library's figure are withheld for this reason. §8 question 7 asks whether to relax it.

### 1.3 What a cell looks like

Today `describe()` shows no pay from either source, because neither is known to have one row per person. It
prints these rows of the fixture like this (the other four read the same way):

```text
City of Norfolk, Fire-Rescue: 581 payroll entries as of 2026-10-10. Pay is not shown: the source may list one
  person more than once, so lexflow cannot count the people in a group. The official source has it.
City of Seattle, Seattle Public Utilities: 1,607 payroll entries as of 2026-10-10. Pay is not shown: [as above].
  The official source has it.
```

Once a publisher confirms one row per person (`rows='person'`), the same rows print like this:

```text
City of Norfolk, Fire-Rescue: 581 staff as of 2026-10-10. Annual base pay (579 people): median about $72,000,
  middle half about $62,000 to $92,000. Pay for the other groups is not shown: lexflow shows pay only for groups
  of 11 or more people.
City of Norfolk, Clerk of the Circuit Court: 31 staff as of 2026-10-10. Annual base pay (12 people): median about
  $102,000, middle half about $79,000 to $116,000. Pay for the other groups is not shown: lexflow never shows a
  figure that could single out one person, alone or set against another it publishes for another group, period
  or release.
City of Norfolk, City Clerk: 14 staff as of 2026-10-10. Pay is not shown: lexflow never shows a figure that could
  single out one person, [as above]; lexflow shows pay only for groups of 11 or more people. The official source
  has it.
City of Norfolk, City Clerk (Records & Information Clerk): fewer than 5 staff as of 2026-10-10. Pay is not
  shown: lexflow shows pay only for groups of 11 or more people. The official source has it.
City of Seattle, Seattle Public Utilities: 1,607 staff as of 2026-10-10. Hourly rate: median about $55 an hour,
  middle half about $45 to $71 an hour.
City of Seattle, Seattle Municipal Courts (Court Clerk): 31 staff as of 2026-10-10. Pay is not shown: lexflow
  never shows a figure that could single out one person, [as above]. The official source has it.
```

A hidden group's reason is chosen from what the cell itself shows: fewer than 11 on the basis, a basis with no
rounding step, a source whose rows may repeat a person, or else the general reason, which covers rules 4 to 7
without saying which applied.

The JSON form:

```json
{"state": "va", "gov_id": "47212200100000", "government": "City of Norfolk", "agency": "Clerk of the Circuit Court",
 "title": "*", "period": "as of 2026-10-10", "n": 31, "pay_basis": "hourly", "n_pay": 19, "p25": null,
 "median": null, "p75": null, "suppressed": true,
 "other_pay": [{"pay_basis": "annual", "n_pay": 12, "p25": 79000.0, "median": 102000.0, "p75": 116000.0,
                "suppressed": false}],
 "source": "va-norfolk-salaries"}
```

* `n` counts the cell's rows, or is `null` for fewer than 5. `n_pay` follows the same rule. For a source with
  `rows='person'` these are counts of people; for any other source they are counts of payroll entries.
* The top-level pay fields describe the basis most of them are paid on. `other_pay` holds the other bases.
* Quartiles use linear interpolation between order statistics (numpy's default). They are rounded to $1,000 a
  year, $100 a month, $10 a day or $1 an hour, and answers say "about".
* `suppressed: true` means no figure for that basis. The cell does not say which rule withheld it; the source's
  provenance block only counts them.
* `agency='*'` is the whole government, and `title='*'` is the whole agency.
* A snapshot source has a period of `as of <retrieval date>`. A source with a year column gets `FY2026` and the
  like.

---

## 2. Storing the cells (next step, not built)

One new table. The research sketch's `workforce_stats` is adapted to the cell shape, so the Census ASPEP counts
(research §6.1) can share it later through `measure`:

```sql
CREATE TABLE IF NOT EXISTS workforce_stats (
  gov_id TEXT NOT NULL,            -- the 14-digit Census/lexflow ID; a state-wide source uses 'lexflow:jurisdiction:<st>'
  state TEXT NOT NULL,
  agency TEXT NOT NULL,            -- the publisher's department name, '*' for the whole government
  agency_key TEXT,                 -- lexflow:agency:<gid>:<slug>, once the link is accepted (§3.2)
  title TEXT NOT NULL,             -- the publisher's title or class, '*' for the whole agency
  period TEXT NOT NULL,            -- 'as of 2026-10-10', 'FY2026', '2025'
  measure TEXT NOT NULL DEFAULT 'staff',   -- staff | fte | budgeted_positions | payroll_march (ASPEP)
  source TEXT NOT NULL,            -- registry id, e.g. va-norfolk-salaries
  n INTEGER,                       -- rows (people where the source's rows='person'); NULL for fewer than 5
  pay TEXT,                        -- JSON list, main basis first: [{pay_basis, n_pay, p25, median, p75, suppressed}]
  source_url TEXT NOT NULL, licence TEXT, retrieved_at TEXT NOT NULL,
  updated_at TEXT NOT NULL, origin TEXT,
  PRIMARY KEY (gov_id, agency, title, period, measure, source)
);

-- rule 7's record: one row per pay group ever published, from any release. Counts only; never deleted.
CREATE TABLE IF NOT EXISTS workforce_pay_published (
  source TEXT NOT NULL, period TEXT NOT NULL, retrieved_at TEXT NOT NULL,
  pay_basis TEXT NOT NULL, n_pay INTEGER NOT NULL,
  PRIMARY KEY (source, retrieved_at, period, pay_basis, n_pay)
);
```

* The table holds the cells as published, after the §6.1 rules. No unrounded figure and no withheld figure is
  stored, so nothing downstream (sync, the wiki) can leak one.
* The table holds public data about governments, so it can join `SYNCED` in `db.py` like `governments` (research
  §7.5).
* A refresh recomputes every rule over the whole release and replaces all cells of one (source, period) in one
  transaction. A title that disappears does not linger, and a group that falls under 11 people, or starts to
  single someone out, loses its pay.
* **Releases and the record (rule 7).** Two releases of one group differ by whoever joined or left, and an earlier
  release's figures survive wherever they were shown or published: wiki page history, a synced copy, a committed
  fixture. Keeping only the latest release in this table does not change that, so the protection is a record and
  a rule, not a retention limit:
  * every refresh passes `aggregate(..., earlier=...)` the source's rows of `workforce_pay_published`, and rule 7
    withholds any pay group whose `n_pay` is within 10 of one of them on the same basis (equal counts included);
  * the same transaction adds the pay groups it publishes to `workforce_pay_published`;
  * that table is never trimmed, rewritten or dropped, and it syncs with `workforce_stats`. Its rows are counts
    that were published already. If it is ever lost, pay for the affected sources stays off until a person
    rebuilds it from what was published (wiki history, fixtures), since lexflow cannot tell a lost record from a
    first release;
  * the committed fixture is a release too. `build_fixture` reads the record from the fixture it replaces (and
    from the committed one) and writes it forward in `pay_published`, for every source, fetched that time or not.
    When the table is created, it is seeded with the committed fixture's record (`aggregate.ledger()` of it), so
    the figures already in the repository count as published.
* Earlier periods keep their headcounts, so a page can say "up from N last year". Within one release
  `aggregate()` publishes pay for one period per fetch (rule 6).

---

## 3. How aggregates attach to governments and agencies

### 3.1 Governments: today

Every registry entry that belongs to one government carries its `gov_id`, checked against the `governments`
table on 2026-10-10. Norfolk is `47212200100000`, Seattle `48201702100000`, San Francisco `05203800100000` and DC
`09200100100000`. A cell therefore joins `governments` directly, and `answers_for(con, gov_id)` can read it with
one query.

State-wide sources (the New York authorities, the state search tools) have no `gov_id`. Their cells attach to
`lexflow:jurisdiction:<st>`, and each authority becomes an agency.

### 3.2 Agencies: with the entities plan

The entities plan defines the keys: `lexflow:agency:<scope>:<slug>`, with `scope` a GID for a government's own
office, and office types such as `lexflow:office-type:va:clerk_of_circuit_court`. It mints office instances
lazily, the first time something needs them (its open question 3). Payroll departments are a natural first need.

1. **Propose.** For each distinct `(gov_id, agency)` in `workforce_stats`, propose an agency.
   * The key is `lexflow:agency:<gid>:<slug of the publisher's name>`, with `scope=<gid>`.
   * It is `part-of` `lexflow:gov:<gid>`.
   * Where the name matches an office type's alias, it is `instance-of` that office type. For example, Norfolk's
     "Clerk of the Circuit Court" matches `office-type:va:clerk_of_circuit_court`.
   * Every link is an `entity_links` row with `status='proposed'`, `method='alias'` and `source` set to the
     registry id.
2. **Review.** A person accepts or rejects each proposal in the entities plan's review queue (its D7).
   * Only an accepted link fills `workforce_stats.agency_key`.
   * The numbers never change on review. Only the link does.
3. **Rename.** A department rename in the source is a new agency name and the same key. The entities plan's
   alias rule covers it: the old name goes to `aliases`.
4. **Which office handles records.** This is never guessed from a department name when an answer is made. It
   comes from the entities links:
   * a `played-by` link from the records model's custodian role, which resolves to "the public body" and then to
     the chosen government (entities plan §1.5);
   * a `serves(records)` link;
   * a records contact whose label names the office.

   The `RECORDS_OFFICE` pattern in `aggregate.py` only picks rows for the sample fixture.

### 3.3 Places with no open payroll

Charlottesville, Fairfax County, King County and Raleigh publish no employee pay data (research §4). Most of
lexflow's 38,640 governments are in the same position. For them:

* the Census ASPEP unit file gives employees and payroll by function for every government (research §6.1, to be
  ingested by the same Setup step);
* state pay scales give the band for a clerk or records title (research §6.2).

The answer then says what is known and where the person-level record lives. It does not invent an office
headcount.

---

## 4. How they show in answers

### 4.1 Where

* **Place page and `lexflow answer`.** `municipal/answer.py` builds these (`answers_for`, `markdown`). A
  `workforce` block would go next to each question's contacts. It is a small edit to that file once this plan is
  accepted. Nothing in `lexflow/ask/` changes while AskBench runs.
* **The records question first.** Here the numbers help most: the size of the office, and the pay band behind
  labour fees (research §1, F7).
* **The wiki and Wikibase.** Only through the existing user-triggered publish, dry run first (entities plan D12).
  Pages get published cells only, and no statement about a person.

### 4.2 What a line says

The pattern is: the office and its size, the pay band if the §6.1 rules allow it, the period, and the source.

> **City of Norfolk's records office** (if the review links the records role to the Clerk of the Circuit Court, and
> once Norfolk confirms one row per employee, §1.2): 31 staff in the Clerk of the Circuit Court's office as of 10
> October 2026. Annual base pay (12 people): median about $102,000, middle half about $79,000 to $116,000; the
> hourly pay of the other staff is not shown. Source: City of Norfolk, Department of Human Resources,
> [Employee Salaries](https://data.norfolk.gov/d/4fsk-z8s8) (public domain).

Where the rules withhold pay, the line keeps the size and says so. For example, Norfolk's City Clerk (on the same
condition): "14 staff as of 10 October 2026. Pay is not shown: lexflow never shows a figure that could single out
one person, alone or set against another it publishes for another group, period or release; lexflow shows pay only
for groups of 11 or more people. The official source has it." Until then the line says "14 payroll entries" and
gives the rows reason (§1.3).

For a place with no open payroll:

> **City of Charlottesville's records office:** the city publishes no payroll by office. Send requests to its FOIA
> officer (the city's FOIA page and records portal are listed above). Virginia allows only the actual cost of
> "accessing, duplicating, supplying, or searching" for records ([Va. Code § 2.2-3704](https://law.lis.virginia.gov/vacode/2.2-3704/)).

The office-size half of that line ("N staff in the Clerk's office") appears only where a source gives it. For
Charlottesville it would come from the city's budget or from ASPEP function counts once those are ingested. It is
never estimated.

**Fee ranges** use title cells. For example, in Maryland, where staff time is prorated by salary after 2 free hours
(GP § 4-206):

> After the first 2 free hours, staff time costs about $X to $Y an hour here (the middle half of hourly pay for
> records clerks, from the county's own pay data).

Three rules apply to fee ranges:

* A body's published fee schedule always wins over this estimate, and the answer says so (research §9.7).
* The range is the middle half (p25 to p75) of the most specific cell that shows pay. The fallback order is title,
  then agency, then the state pay scale.
* Benefits are never added. The Maryland Attorney General's manual leaves them out.

### 4.3 Display rules

| Case | Shown |
|---|---|
| A source whose rows may repeat a person (`rows='unknown'`, §6.1) | the count as "N payroll entries"; pay "not shown" because the source may list one person more than once, even for a cell stored with pay |
| Fewer than 5 in a cell | "fewer than 5 staff"; no pay; a link to the official source |
| 5 to 10 people on a pay basis | the count; pay "not shown": "lexflow shows pay only for groups of 11 or more people", with a link to the official source |
| A pay basis with no rounding step | the count; pay "not shown": "lexflow has no rounding step for that pay basis" |
| 11 or more on a basis, but a figure would single out a person (rule 4), two groups would differ by 1 to 10 people (rule 5), it is an earlier period of a fetch that spans several (rule 6), or its count is within 10 of a pay group from an earlier release (rule 7) | the count; pay "not shown": "lexflow never shows a figure that could single out one person, alone or set against another it publishes for another group, period or release". The line does not say which rule applied, and never gives the small-group reason |
| Some bases shown, others not | the shown bases; "pay for the other groups is not shown", with the reasons above |
| A person-level question ("what does X earn?") | no figure. The statute that makes pay public, and the official search from `sources.links(state, gov_id)`. For example: Norfolk's dataset and Virginia's Data Point for Virginia; Florida's state search, which may be linked but never crawled. |
| A stale source (§5) | "link only": the dataset link and its last update date, no figures |
| A source with no licence stated, or terms not yet read | not shown until the operator records a decision on its Setup card |

Each line carries its `period` and source link. `describe(cell, source=True)` already produces the source
sentence.

---

## 5. Refresh cadence

| Source | Publisher's cadence | lexflow refresh | Cost per refresh |
|---|---|---|---|
| Norfolk | daily | headcount monthly; pay once a year (§2) | 2 requests |
| Seattle | monthly | headcount monthly; pay once a year (§2) | 2 requests |
| San Francisco (when enabled with a token) | twice a year | after each release (January and July) | about 8 requests |
| NYC, NY authorities (when enabled) | annual or twice a year | after each release | a few grouped queries |
| Census ASPEP | yearly (preliminary data in April) | yearly, in May | one 10.9 MB ZIP |
| State pay scales | yearly, effective 1 July in most states | yearly, in July | one file per state |

* **The operator triggers each refresh from the Setup page.** Nothing runs on a timer by default. The card marks
  a source *due* when its `retrieved_at` is older than its refresh interval.
* **Pay is refreshed less often than headcount** for snapshot sources. That is for coverage, not for safety:
  rule 7 (§6.1) withholds every pay group whose count is within 10 of one published from an earlier release, and
  a month's hires and leavers rarely move a group by 11, so a monthly pay refresh would mostly withhold. Safety
  across releases comes from rule 7 and the record it reads (§2), which is kept for good. It does not come from the
  size of a year's turnover, nor from keeping only the latest release, since earlier figures survive elsewhere.
* **Conditional refresh.** A refresh first reads the dataset-level metadata (`/api/views/metadata/v1/<id>`, one
  request) and skips the data query when `dataUpdatedAt` has not moved since the last retrieval. That endpoint
  carries no columns (checked on both portals, 2026-10-10). The full `/api/views/<id>.json` also carries cached
  column statistics, which can include a column's most common values (names, for a named payroll), so a refresh
  does not use it.
* **Freshness decides display.** A source not updated by its publisher for 18 months drops to "link only".
  Today that is DC (September 2024), Cook County (2018) and Dallas (2019). Every displayed line shows its
  `as of` date or period.
* **Politeness on every refresh.** It uses the research User-Agent, 15 s timeouts, at least 1 s between requests
  to a host, and at most two retries on 429 or 503 within `Retry-After`. robots.txt is read as RFC 9309 says:
  rules from a 2xx answer, `Crawl-delay` honoured; no rules after a 404 or 410; complete disallow after a 5xx or
  when the host is unreachable, and (more cautiously than the RFC) after 401, 403 or 429. Redirects are followed by
  hand: each hop is checked against its host's robots.txt and spaced like any request, a hop to a host the
  registry does not list for that dataset is refused, and so is a hop from https to http. Any other refusal (HTTP
  428, 403) stops that source for the run and is reported on the card. The row cap stays (50,000 grouped rows per
  dataset). A capped run is marked `truncated`, and no cell from it is kept (the fixture builder already does
  this, and a test pins it).

### 5.1 The Setup step (where this ties in)

The Setup checklist (`lexflow/pipeline/steps.py`) gets one optional card. Its fields match research §8, and
`steps.py` is not edited by this plan:

| Field | Value |
|---|---|
| `id` | `workforce` |
| `title` | Load public-employee numbers and records offices |
| `why` | Headcount and pay bands by agency and title from city and county open data, grouped on the publisher's server, with no names downloaded. Census headcount for every government, and state pay scales. Used for office sizes and records-fee estimates. Records-office mailboxes go to review before they are shown. |
| `level` | `optional` |
| `needs` | `["governments"]` |
| `params` | `["states", "force"]` |
| `cost` | 2 requests per city dataset (robots.txt included); one 10.9 MB Census download |
| `status` | `done` when every enabled source in the loaded states has a `scans` row (`source='workforce:<registry id>'`) newer than its refresh interval; `partial` otherwise. Detail: "N governments with headcount; M with pay by title; K sources due". |
| `run` | `run_workforce(con, args, log, progress)`: for each enabled registry entry in the chosen states, `sources.fetch`, then `aggregate.aggregate` with the source's rows of `workforce_pay_published` as `earlier` (rule 7, §2). In one transaction it replaces the cells and adds the pay groups it published to that record; then it marks the scan. The projected rows are discarded in memory. |
| `credits` | One `credit()` per dataset read, from the registry: publisher, licence, landing URL and use ("headcount and pay bands by agency and title"). |

Order: after `contacts` and before `score`, as research §8 proposes.

The card also lists the registered sources that are not read, with the reason from `notes`. For example:
"Chicago: terms require a set disclaimer, let the City stop the use, and contain an indemnity", "Montgomery County:
terms not found or unclear". The operator can then decide on each one there.

---

## 6. Privacy rules

### 6.1 About public employees

1. **The allowlist** (P2). `project()` returns the mapped fields and a count, nothing else. A test feeds a table
   with first names, last names, gender and hire dates through both the CSV path and a Socrata server that
   ignores `$select`. It asserts that none of those values reaches a row, a cell or the JSON.
2. **The guard.** `check_fields()` runs on the whole registry at import. It refuses a map that points at a column
   that `looks_person_level()` flags. It splits a column name into words (snake_case, camelCase, digits). A glued
   word is split again: into words the guard knows where it can be covered by them (`POSITIONNUMBER`,
   `PAYROLLID`, `EMAILADDRESS`, `STARTDT`, `TIMEINGRADE`, `EMPLID`), or else by splitting off a trailing "name" or
   "nm", a trailing "number", "nbr" or "nr", or an ID suffix after a person-like prefix (`empno`, `pernr`). Short
   words that occur inside ordinary words are left out of that vocabulary, so `paid`, `overtime` and `usage` stay
   whole. Then:
   * *A general rule for names and IDs.* A name column, or an ID or number column, is person-level unless the word
     that says whose name or ID it is (the word before it, or the word after "of") is organisational, and no word
     in it names a person. So `department_name`, `dept_nm`, `dept_id`, `DEPTID`, `id_of_department` and
     `fund_number` pass, while `payee_name`, `supervisor_name`, `l_name`, `name_of_employee`, `id_of_employee`,
     `payee_id`, `position_number`, `POSITIONID` and `GlobalID` do not. Only a count is exempt from the ID rule: a
     count word (number, no, num, nbr, nr) followed by "of", in a column with no person word, such as
     `number_of_employees` or `no_of_positions` (not `number_of_employee` or `number_of_staff`).
   * *People and roles.* A column made only of person words (`last`, `first`, `middle`, `last_first`, `staff`) or
     ending in a role (`supervisor`, `manager`, `officer`, `approver`, `department_head`, `elected_official`,
     `emergency_contact`) holds names. `officer_count` and `number_of_officers` pass.
   * *Named categories, wherever they appear:* initials; birth and age (`dob`, `yob`, `AGEGROUP`); sex, sexual
     orientation and gender (`gndr`); race and ethnicity (`hispanic`); veteran (`vet_status`), disability and
     marital status; hire, start, begin, title, service and separation dates (`doh`, `begin_date`, `STARTDT`), and
     the start or end of a job or of employment (`employment_start`); tenure (`seniority`, `longevity`,
     `years_of_service`, `yrs_svc`, `time_in_grade`); home and contact details (`home_city`, `resident_state`,
     `phone_number`, `EMAILADDRESS`); photos and signatures.

   It knows common spellings, not every one, and errs towards refusing: the allowlist is the protection, the guard
   a second check. Tests check every column in a registry entry's `drop` list, every spelling the verification and
   its two re-checks found, the general rule on invented names, and a list of ordinary columns (glued all-caps
   forms included) that must still pass.
3. **Server-side grouping** (P3). On the Socrata path, names are never requested, so they never cross the
   network. The CSV path cannot do this: it downloads the whole file, names included, and drops the other columns
   as each row is parsed. No enabled source uses it; prefer a grouped query wherever one exists.
4. **Disclosure rules for what lexflow publishes.** The sources publish every person's pay already. These rules
   limit what lexflow's cells say about any one person (`aggregate.py`, rules 1 to 7); the gaps they leave are
   listed below.

   *What the counts count.* Every count and threshold counts rows. A row is one person only where the registry
   entry says `rows='person'`: at most one row per person per period, as the publisher's own documentation says.
   Elsewhere a person with two jobs, or a source that appends quarters, gives one person several rows, so 11 rows
   can be fewer than 11 people and one person's repeated rows could meet rule 4's count of 5. So pay is published
   only from a `rows='person'` source. Any other source gets headcounts of rows, which answers call "payroll
   entries", and no pay. No source is `rows='person'` yet (§1.2). Below, "people" means rows of such a source.
   1. *Headcount from 5.* A count of fewer than 5 is not published ("fewer than 5"); 0 is.
   2. *Pay from 11.* Quartiles for a pay basis are published only for 11 or more people on it, only for a basis
      with a rounding step, and only from a source whose rows are people.
   3. *Coarse bands.* Quartiles are rounded to $1,000 a year, $100 a month, $10 a day or $1 an hour.
   4. *No figure singles out a person.* A group's quartiles are all withheld if a rounded figure equals the exact
      pay of 1 to 10 people in the group, or if 1 to 4 people's pay lies within half a step of it. So a published
      figure is never one person's pay (a rate shared by 11 or more is a pay-scale step), and never pins fewer
      than 5 people's pay to within half a step.
   5. *No differencing.* Within one period and pay basis the published groups nest: title, agency, government.
      Every published group must hold nobody or at least 11 people outside its published sub-groups; while one
      does not, the smallest of those sub-groups is withheld. Then any union, intersection or difference of
      published groups holds 0 or at least 11 people, so subtracting an agency from its government, or a title
      from its agency, never isolates a person.
   6. *One period per fetch.* Rule 5 works within one period only. lexflow reads no IDs, so nobody can be matched
      from one period to the next, and the same group in two periods differs by whoever joined or left: with 11
      clerks one year and the same 11 plus a newcomer the next, twice the second median minus the first can give
      the newcomer's pay (to within $100 in the test's case). So when a fetch spans several periods (a source
      with a year column and no one-year filter), pay is published for the latest only, by the numbers in its
      label (FY10 after FY9), and the other periods keep their headcounts. A period read from the source's
      period column wins over rows that have none. The multi-year sources' registry notes say to filter one
      year, so that nothing is fetched only to be withheld.
   7. *No differencing across releases.* The rule 6 attack also works across two fetches (releases), wherever the
      earlier figures survive: wiki page history, a synced copy, a committed fixture. Keeping only the latest
      release does not remove those copies. So `aggregate()` takes the record of every pay group published from
      earlier releases of the source (`earlier`: period, basis and `n_pay`, counts only) and withholds a pay group
      whose `n_pay` is within 10 of any of them on the same basis. It compares every pair, whatever the agency or
      title, because a renamed office holds the same people. Equal counts are withheld too, because one leaver and
      one joiner leave the count unchanged. Two groups whose sizes differ by 11 or more differ by at least 11
      people, so no published pair of releases isolates 1 to 10 people. The record is kept for good (§2). A lost
      record cannot be told from a first release, so it must not be lost. The fixture builder already carries the
      record from the fixture it replaces.

   No means, minimums, maximums or sums are published: a group's minimum and maximum are each one person's pay,
   and two nested sums that differ by one person subtract to that person's pay. Tests play the attacker: they try
   exact order statistics in a 5-person group, subtracting a title from its agency to recover a single
   title-holder, subtracting an agency from the government, a round salary held by one person, a figure close to
   one isolated person, and subtracting two periods or two releases to recover a newcomer (also after a swap, and
   under a new office name). They also check every rule on random payrolls with pay-scale steps, over one period,
   over two, and over two releases. Each attempt fails. The same checks found no violation in the real fetch,
   which counted rows as people (§1.2).

   What the rules do not cover:
   * *An incomplete record.* Rule 7 is only as good as `earlier`. A release published without the record of the
     earlier ones (a fixture written somewhere else, a record lost or trimmed) is not protected against them.
   * *Insiders.* A figure between two people's pay (nobody within half a step of it) is a weighted mix of
     their two pays. Someone who knows their colleagues' ranks and one of those two pays could estimate the
     other to within about a step. The source publishes both pays anyway.
   * *Small headcounts by subtraction.* Published headcounts can be subtracted to give counts under 5:
     * an agency's count minus its published title counts says how many people hold the remaining titles;
     * a cell's `n` minus its `n_pay` says that 1 to 4 people in it are on another pay basis or have no pay
       figure. At Norfolk, which has no empty pay values, that means they are in a temporary, part-time,
       retiree, sheriff or state-compensated class;
     * one period's or release's count minus another's says how many joined or left.

     Each says how many people, never what they are paid; a test pins the second case.
5. **No quasi-identifiers.** Nothing is grouped by or stores gender, race, ethnicity, age, birth year, dates or
   IDs, even where a statute makes them public. That rules out Houston's hashed file, LA City's demographic
   columns, Montgomery County's gender column, NYC's Local Law 18 table and Virginia Beach's position IDs.
6. **Person-level questions get links.** Answers link to the official search and cite the statute
   (`sources.links()`), and never show a record about a person. Plans and notes describe sources by ranges
   ("all under $200 an hour"), never by one person's exact pay.
7. **Office channels, not people.** Records-office contacts follow the entities plan (§5 there): role and office
   mailbox, never a named officer.

### 6.2 About sources

* Only official publishers. No aggregator is in the registry (research §5).
* A source is read only when its licence is clear (Public Domain, PDDL, CC BY) and its robots.txt allows the
  endpoint. Norfolk's and Seattle's portals link no terms page, so their licence rests on each dataset's metadata
  (Public Domain). That is adequate, and the registry records it.
* Terms that need a decision stay with the operator: Chicago's (a set disclaimer, a stop-use clause and an
  indemnity) and Washington's emailed bulk-file request. lexflow never accepts terms, sends a request or creates
  an account on anyone's behalf.
* Terms not yet read, all for sources that are not fetched. A person reads each before it is enabled:
  * NYC Open Data (its terms are on www.nyc.gov, whose robots.txt answered 403, so they were not requested);
  * data.ny.gov (its terms are a PDF, not downloaded);
  * Virginia Beach's "About this Site" terms;
  * Montgomery County's portal terms (not found: the portal's Terms of Use link and the county's `/disclaimer`
    answered 404, and the county's site-wide terms may not cover the portal).
* Terms read for linked tools: the NC State Controller allows non-commercial copying, unaltered and with a
  citation, so a link fits. California's search moved from publicpay.ca.gov to gcc.sco.ca.gov (HTTP 200,
  robots.txt allows it); it stays link-only.
* Florida's state payroll search may be linked and is never requested.

### 6.3 About the users of the lab

* **Nothing is collected by default.** The Setup step reads public aggregates and sends nothing about the operator
  or any user.
* **Answers make no outside calls** (P6). Fee ranges are computed on the user's machine from stored cells.
* **A user's process data stays on their machine.** That covers the questions they ask, the records they plan to
  request, and their notes on how an office answered. It is not part of `workforce_stats` and does not sync.
* **Sharing is explicit and anonymised.** If a user chooses to share a note (for example, "this office answered
  in 3 days"), it is first reduced to the government, the office and the fact, with no user identifier. Then it
  goes through the same review queue as any other contact change.

### 6.4 Credits

Datasets are credited on the Setup card by publisher and licence. No person is named as a source, partner,
reviewer or endorser.

---

## 7. Phases

| Phase | Scope | Tests | Exit check |
|---|---|---|---|
| 0 (done) | Registry, polite fetcher, aggregation with the §6.1 rules, fixture | `tests/test_payroll.py` (389) | The fixture comes from a real fetch; no person-level value in any output; the attacker tests fail to recover anyone's pay |
| 1 | `workforce_stats` and `workforce_pay_published` in `db.py` and in `SYNCED`; `run_workforce` and the Setup card; `scans` marks; conditional refresh | Schema idempotent; a refresh replaces a period atomically, recomputes the rules with the record as `earlier`, and adds to the record in the same transaction; nothing ever deletes from the record; a stale or truncated source shows nothing; a `rows='unknown'` source shows headcounts only; the card lists sources that are not read and why | A run for VA and WA from the Setup page (headcounts only until §8 question 8 is settled), then `sync push` |
| 2 | Census ASPEP unit file (`measure='staff'`, `'fte'`, `'payroll_march'` by function), after checking its ID column against `gov_id` (research §9.1) | The ID join on a fixture of 20 governments; imputed (`II`) rows marked as estimates | Headcount by function for every loaded government |
| 3 | Agency proposals and links through the entities queue (§3.2); the `workforce` block in `answers_for` and `markdown` | Proposals are idempotent; only accepted links fill `agency_key`; suppressed cells render without pay | Norfolk's and Seattle's records answers show office size with a source link |
| 4 | Pay scales and fee ranges (research §6.2) for the corpus states | Fee range fallback order; a published fee schedule overrides | A Maryland records answer shows a fee range with its basis |

---

## 8. Open questions

1. **San Francisco and other large sources.** Add an optional Socrata app token to `.env`, or use server-side
   `median()` with counts by department and job, and give up the quartiles for those sources? A server-side median
   cannot be checked against rule 4 without the rows, so it would need its own rule.
2. **Norfolk's mixed column.** The 1,000 threshold separates the hourly rates (all under $200) from the annual
   salaries (none under $5,000) in today's data. Reading the Employee Status column (an aggregate-safe class)
   would make the split exact, and would also let the annual basis separate full-time staff from part-time staff,
   elected officials and appointees. It reads one more column. Is that worth it?
3. **Seattle's figures are hourly for everyone,** salaried staff included. Should answers convert them to annual
   figures at 2,080 hours, or keep them hourly, as published?
4. **Agency matching.** How much alias matching should run before a person reviews it? Publisher names such as
   "Clerk of the Circuit Court" vs "Clerk of Circuit Court" are easy. Seattle's "Legislative Department", which
   holds the City Clerk's office, needs the publisher's division column, and the prototype does not read it.
5. **Wiki publishing.** Should suppressed cells appear on public wiki pages at all, or only cells with pay?
6. **Montgomery County.** Its portal terms were not found (§6.2). Who reads the county's terms, and do they cover
   the portal? Its 2025 file has grades but no titles.
7. **Rule 4's exact-match test.** It withholds a group of any size when a rounded quartile equals the exact pay of
   1 to 10 of its people: Seattle's city-wide figure is lost because a few people earn a whole-dollar rate that
   equals a rounded quartile. A narrower test would tolerate the coincidence when at least 11 people's pay lies
   within half a step of the figure, since the figure then says nothing about any one of them. That would restore
   most large groups, but a published figure could then equal someone's exact pay. The stricter rule was kept as
   the conservative choice. Relaxing it needs a person's decision and one more fetch to rebuild the fixture, and
   that fetch is a second release: rule 7 would withhold every group whose count moved by less than 11 since the
   committed fixture, so a rebuild soon after it would show little pay.
8. **One row per person.** Neither Norfolk nor Seattle says whether a person can appear twice, so both are
   `rows='unknown'` and give headcounts only (§1.2). Who asks each publisher (through its open-data contact), and
   where is the answer recorded? Only a documented answer sets `rows='person'`; the registry note must then say
   where it is documented. Reading Seattle's names on the server to check was ruled out.
