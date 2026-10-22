# Retirement benefits: who runs them, the law behind them, and how they are taxed

_22 October 2026. The design behind `lexflow/benefits/` (`python -m lexflow.benefits`), the fixtures under
`fixtures/benefits/`, the question family `fixtures/families/retirement_va.json`, the tables `pension_systems` and
`pension_coverage` in `lexflow/store/db.py`, the route `GET /api/benefits`, the dashboard page `#/benefits`, the
eight `retirement_*` coverage questions and their gold in `curated_ask/coverage/{va,md,dc}/`, and
`tests/test_benefits.py`. The idea of tagging inputs as published facts, assumptions or scenario values, personas and
one-at-a-time sensitivity comes from [github.com/dam8u/VRSLite](https://github.com/dam8u/VRSLite), a model of one
proposed Virginia Retirement System bill. That repository carries no licence, so nothing was copied from it: no
code, text or data._

## 1. The question

A person gives where they work or live (a state, county, city or town: the `governments` table) and who they are:

| Person type | Label |
|---|---|
| `state_employee` | Public employee: state government |
| `teacher` | Public employee: teacher (public school) |
| `local_employee` | Public employee: local government (county, city, town) |
| `public_safety` | Public employee: public safety (police, fire, corrections, EMS) |
| `judge` | Public employee: judge |
| `private_with_plan` | Private-sector employee whose employer offers a retirement plan |
| `private_no_plan` | Private-sector employee whose employer offers no retirement plan |
| `self_employed` | Self-employed |
| `veteran` | Veteran |
| `surviving_spouse` | Surviving spouse |
| `retired` | Already retired |

lexflow answers with the retirement programs that apply, who administers each, the law that creates it, its
eligibility rules (computed, for Virginia), how to apply, how to appeal, and how the state taxes the income. The
person type is a category. Nothing about the asker is taken or stored. Age and service go only into the Virginia
family's computation, as a GET request that stores nothing.

## 2. Sources and licences

| Source | What | Licence or terms | How it was read |
|---|---|---|---|
| U.S. Census Bureau, Annual Survey of Public Pensions, Individual Unit Files 2025 and 2022, and the 2022–2025 file layout | 4,454 state- and locally-administered defined-benefit systems, with membership and beneficiary counts | Public domain (a U.S. government work) | Three files from `www2.census.gov` (robots allows it), the lexflow-research User-Agent, at least 1.2 s apart; kept in `data/raw/census-aspp/` |
| Census Government Units List 2022 | The `governments` table (already loaded) | Public domain | Already on this copy |
| Open US Law's state codes (the statute index, `lexflow.ask.index`) | Every statute quote | As for the rest of lexflow | Read locally; no fetch |
| Official pages: retirement systems, state tax agencies, auto-IRA programs, SSA, VA, OPM, DOL, DFAS | Page quotes for websites, apply steps, tax guidance, thresholds | Public government pages | lexflow's quote fetch (`municipal.quotes.fetch`): GET only, lexflow-research User-Agent, robots.txt obeyed, at least 1.5 s per host, nothing behind a login. An Internet Archive capture is read when the live site refuses automated readers |
| Wikidata | Exact matches for the systems' bodies, with official website (P856) | CC0 | `wbsearchentities` and `wbgetentities`, read-only, one request every 2 s (`publish.vocab_links._get`) |

**Not pulled**, and listed instead:

- **Behind an account.** The member portals myVRS (`myvrs.varetire.org`) and mySRPS. Employer portals.
- **No usable text.** `services.marylandcomptroller.gov`, the Comptroller's script-rendered knowledge base, which holds the 2025 pension exclusion figure ($41,200). RetirePath Virginia's site, which renders by script so only its description is readable. The South Dakota and Utah systems' script-rendered pages.
- **Robots or connection refused, no capture to fall back on.** `retirepath.virginia.gov` and `incometax.utah.gov`.
- **Read through Internet Archive captures** because robots.txt answered 403: `ssa.gov` and `dfas.mil`. Some state program sites (CT, CO, DE, ME, MN, NV, NY, OR, RI, VT, IL) were read the same way.
- **PDFs.** This container has no PDF text extractor, so no PDF (form instruction booklets, handbooks) is quoted anywhere.

## 3. The Census join (`lexflow/benefits/census.py`)

The unit files are long: one row per item (`RJ01` total members, `RJ10` active, `RJ11`/`RJ12` state and local
active members, `RJ20` beneficiaries, `RJ30` inactive, `RX40` benefits paid). A system's row is its latest year
(2025 if it is in the 2025 sample, otherwise the 2022 census), with older counts filling items the latest year lacks.

**No government id.** `PID6` is the pension unit's own id. None of the 4,454 matches a government's
`CENSUS_ID_PID6` in the Government Units List, so the join is by state and name:

- **Local systems** (Census government type 1 county, 2 municipal, 3 township) are joined to the government of
  that type whose core name appears as whole words in the system's name. `CHARLOTTESVILLE RETIREMENT FUND` gives
  City of Charlottesville, and `FAIRFAX COUNTY UNIFORMED…` gives Fairfax County, not the City of Fairfax.
  - The longest core wins.
  - A tie between two governments with the same core (Pennsylvania's thirteen Penn Townships) is left unjoined
    as `ambiguous`, unless the Census writes the county in brackets (`[ST LOUIS]`).
  - A core followed by a word that names another body (`WASHINGTON SUBURBAN SANITARY COMMISSION`) is not a match.
- **State systems** (type 0) are open to a local government's employees when either of these holds:
  - the Census counts local active members in any year;
  - the name is for municipal, county, local, school or political-subdivision employees. A police word alone does
    not count: a state police system is for state employees.

  A curated reading in `fixtures/benefits/systems/<st>.json` overrides this, in two cases: the statute opens the
  system to local employers (its quote matched), or a curated reading says the system is not open to them (37
  overrides). New Hampshire's NHRS is one, opened by RSA 100-A:20.

| Count | Value |
|---|---|
| Systems | 4,454: 318 state-administered, 4,136 local |
| Local systems joined to their government by name | 3,443 |
| … ambiguous (two governments share the name) | 237 (mostly Pennsylvania townships) |
| … no government of that type carries a name the system's name holds | 141 |
| Special-district and school-district systems (not in the `governments` table) | 315 |
| **Local governments with their own system** | **2,429**: 262 counties, 1,737 municipalities, 430 townships (1,552 of the local systems are Pennsylvania's) |
| Governments covered by at least one system (their own, or a statewide system open to local employers) | 38,640 of 38,640 |
| Jurisdictions with a state system open to local employers | 50 (all but DC) |
| `pension_coverage` rows | 141,461 (`administers` and `statewide`, each with the person types it can cover and how the link was made) |

The two tables are this copy's own (`LOCAL_KEYS`), rebuilt from the unit files with `python -m lexflow.benefits
census`. Whether a particular employer participates in a statewide system is not in the Census file. The coverage
rows say so.

## 4. The four layers (`fixtures/benefits/`)

Every quote in every fixture is matched when it is loaded (`lexflow/benefits/ground.py`):

- a statute quote word for word against the index text (`validate.quote_in`);
- a page quote against the page as lexflow's quote fetch read it.

`python -m lexflow.benefits check` reports **1,461 of 1,461 sources matched in 104 files**. A fact whose sources do
not match is not shown as grounded anywhere. The fixtures were researched with Claude, one state at a time, using
`python -m lexflow.benefits.research` (search, section, page, check, checkfile). The match is lexflow's software's.

### 4.1 Statewide systems (`systems/<st>.json`, 51 files)

Each Census state unit is grouped into a system. VRS's three Census units are one system with three plans. Each
system records:

- the section that creates it, with `statute_role` set to `establishes` or `defines`;
- the body that administers it, with a statute quote naming that body;
- its website, with a quote from the site;
- its membership and `covers_local`;
- for Virginia and Maryland, how to apply, how to appeal, and office channels.

| | |
|---|---|
| Jurisdictions | 51 (50 states and DC) |
| Systems | 260 |
| Sections that establish, create or continue the system, matched | 188 |
| Only a defining section matched | 28 |
| Systems with a matched website quote | 222 |
| States with at least one grounded statute | 46. The other five are AR, CO, GA, MS and TN, which have no statute index on this copy. |
| Exact Wikidata matches | 10 among the first 74 systems checked (16 states): Virginia Retirement System Q115813717, CalPERS Q2933412, CalSTRS Q14681677, and the bodies that run some smaller plans. The run is read-only and slow (one request every 2 s), and was stopped there. `python -m lexflow.benefits wikidata --write` resumes it and keeps what `wikidata_bodies.json` already holds. |

Most bodies have no Wikidata item with the system's exact name. A system's name and its board's name are the two
names tried, then the name with "of <State>" added.

### 4.2 State auto-IRA programs (`auto_ira.json`)

There are 22 programs: 17 states with an employer mandate and 5 voluntary programs or marketplaces.

**Mandates:** CA, CO, CT, DE, HI, IL, MD, ME, MN, NJ, NV, NY, OR, RI, VA, VT and WA. Hawaii and Washington are
`enacted`, not yet open.

**Voluntary:** MA, MO, NM, the New Jersey marketplace and the Washington marketplace.

Each fact (creates, board, mandate, threshold with `employees_min`, deadline, exemption, self-employed, penalty,
default contribution) carries its sources. 223 sources are matched: 122 statute, 38 live page and 63 Internet
Archive.

Rollout dates by employer size are often in board rules or on pages lexflow could not read. Facts without a source
were dropped and are named in each program's `notes`.

### 4.3 State income-tax treatment (`tax/<st>.json`, 51 files)

Each file covers Social Security, public pensions, private pensions (with 401(k) and IRA distributions) and
military retired pay. Each item has a `treatment` (`exempt`, `partly_exempt`, `taxable` or `no_income_tax`), a
summary and its conditions.

**What is grounded:**

- All four items are grounded in all 51 jurisdictions.
- All four rest on statute quotes in 31 states, and on agency-page quotes in 46.
- Both kinds back all four in 26.

**Treatments, counted across the 51 jurisdictions:**

| Income | Exempt | Partly exempt | Taxed | No income tax |
|---|---|---|---|---|
| Social Security | 33 | 8 | 1 | 9 |
| Public pensions | 9 | 26 | 7 | 9 |
| Private pensions | 3 | 24 | 15 | 9 |
| Military retired pay | 29 | 12 | 1 | 9 |

**Gaps:**

- **Sections missing or truncated in the index.**
  - Missing: Maryland Tax-General § 10-207, Rhode Island chapter 44-30, Nebraska 77-27xx, and Pennsylvania's Tax
    Reform Code.
  - Truncated: Wisconsin 71.05(6)(b), North Dakota 57-38-30.3, and the CT 12-701 table.

  Those items rest on agency pages.
- **Older figures.** Some agency pages lag the Code. Each case is in the file's `notes`.

### 4.4 The federal layer (`federal.json`)

These are pointers, not models:

- Social Security retirement and survivors benefits;
- SSI;
- VA Pension and Survivors Pension;
- military retired pay (DFAS);
- FERS and CSRS (OPM);
- ERISA plans (DOL EBSA).

Each pointer has its agency, its official page with a matched quote, and the law as a citation only, because there
is no U.S. Code index on this copy. Each lists the person types it applies to, and the appeal route where the
agency's page gives one. All are federal and apply everywhere.

## 5. Lookup and "Who do I ask" (`lexflow/benefits/lookup.py`)

`lookup(place, person)` assembles the answer from these parts:

- **Statewide systems** whose membership includes that kind of employee. For `local_employee`, these are only the
  systems open to local employers.
- **The place's own systems**, from `pension_coverage` `administers`, filtered by the person types each covers.
  The police fund is not shown to a general employee.
- **Census counts** for each system.
- **The state auto-IRA program**, for a private employee without a plan or a self-employed person when the law
  admits them. A private employee with a plan is told that employers with a qualified plan are exempt.
- **Tax treatment**, with the items that matter for that person first.
- **Federal pointers.**
- **For Virginia public employees**, the link to the `retirement_va` family.

`ask(place, person)` returns the same as "Who do I ask" cards: the role ("Runs your pension", "Runs the state's
auto-IRA program", "Taxes your retirement income"), who plays it, its channels, the law's words, and the steps
(apply, appeal) with their grounding. Every channel passes `lexflow.privacy` through `who._channel`.

The fixtures were cleaned against that check:

- Phone labels must be office labels. "Member Services" was refused and replaced by "Retirement Agency main line".
- A page whose path has `/members/` is a person-level path by the privacy rule's shape. Those page channels were
  dropped; the pages stay cited as quote sources.

## 6. The Virginia pilot (`fixtures/families/retirement_va.json`)

**How it is built.** `lexflow/benefits/family_va.py` writes the family from
`fixtures/benefits/va_retirement_backbone.json`. That file holds 34 provisions, each a verbatim quote:

- Va. Code Title 51.1;
- the Administrative Process Act, §§ 2.2-4001, -4019 and -4026;
- VRS's own Plan 1, Plan 2 and Applying for Retirement pages.

`python -m lexflow.scenarios.family --fill retirement_va` grounds it: **201 of 201 sources matched (199 statute
index, 2 live page), 124 rules, none dropped**.

**Dimensions.** The scenario-ID grammar is `{LOC}-{EMP}-{MEM}-{AGE}-{SVC}`.

- **Employer:** state, teacher, political subdivision, or hazardous duty. Hazardous duty means a state police
  officer, a VaLORS member, or a subdivision's law-enforcement officer, firefighter or EMT whose employer elected
  enhanced benefits under § 51.1-138.
- **Membership date:**
  - before 1 July 2010 and vested by 1 January 2013;
  - before 1 July 2010 and not vested;
  - 1 July 2010 to 31 December 2013;
  - on or after 1 January 2014;
  - on or after 1 January 2014, hazardous duty.
- **Age**, in bins under 50, 50, 55, 60, 65 and 67 or older.
- **Years of creditable service**, in bins under 5, then 5 to 30 or more in steps of 5.

The **plan** (Plan 1, Plan 2 or Hybrid) is a derived input, set by the membership date as the Code defines it:

- § 51.1-124.3 sets the normal retirement date: the 65th birthday, or the Social Security retirement age for a
  person who becomes a member on or after 1 July 2010 or has fewer than 60 months of service on 1 January 2013.
- § 51.1-169 puts members hired from 1 January 2014 in the hybrid program. Hazardous-duty members are kept out of it.

**Tables.**

- **`plan`:** which plan, and "ask your employer" when a subdivision's hazardous-duty election decides it.
- **`retirement`:** unreduced, reduced or not yet. This covers § 51.1-153(A) normal retirement, (B)(1) 55/5 or
  60/5 early retirement, (B)(2) Plan 1 50/30, (B)(3) the Rule of 90, (D) 50/10, and for hazardous duty §§ 51.1-201,
  -205 and -206 (60/5, 50/25, 50/5). Each rule's deadline cites § 51.1-153(E): the effective date may be no more than
  90 days before the notice.
- **`steps`:** buying service credit (§ 51.1-142.2, with the 24-month price rule), keeping contributions for a
  deferred retirement (§ 51.1-153(C)), the hybrid plan's contributions, and designating a beneficiary (§ 51.1-162(A)).
- **`protection`:** pointers to disability retirement (§ 51.1-156) and to the allowance for survivors of a member
  who dies in service (§ 51.1-162(B)).

**Appeals.** Informal fact-finding under § 2.2-4019, then a court action under § 2.2-4026. VRS is not exempt from
the Administrative Process Act.

**The Rule of 90 is exact for whole years.** FEEL unary tests cannot add two inputs. `family_va.runs` therefore
computes eligibility for every whole age 0 to 100 and every year of service 0 to 60. It writes one rule per run of
ages and years that share an outcome and the provision that gives it. The test re-evaluates the table on the whole
grid: exactly one rule fires for each plan class, age and service, with the outcome `eligibility` computes.

**Statuses.** Here a row's status reads:

- `required`: applies to you now;
- `recommended`: an option worth checking;
- `ask first`: depends on your employer's election;
- `not required`: not (yet) eligible.

**Assumptions:**

- **ASM-01:** the Social Security retirement age is taken as 67.
- **ASM-02:** age and service are whole years.
- **ASM-03:** hybrid members follow the Plan 2 eligibility rules.
- **ASM-04:** what hazardous duty covers.
- **ASM-05:** not modelled: the 2014 hybrid opt-in, and § 51.1-153(B)(4) resolutions.

**Personas**, in Virginia; each persona's output also lists the rows that apply to every member:

| Persona | Plan | Result |
|---|---|---|
| Teacher, 55, 25 years | Plan 1 | Reduced early retirement available now (55 with 5 years; the reduction runs to the earlier of 65 or 30 years). Designate a beneficiary; check buying service credit, deferred retirement, disability and survivor protection. |
| State employee, 60, 10 years | Plan 2 | Reduced early retirement available now (60 with 5 years); unreduced at 67, or when age plus service reaches 90. |
| Firefighter, 50, 25 years | Hazardous duty | **Unreduced retirement now** (50 with 25 years, § 51.1-206(A)(2)). "Ask your employer" whether it provides the § 51.1-138 benefits. |
| Political subdivision employee, 45, 8 years | Hybrid | **Not yet eligible.** Plan the hybrid plan's contributions (the employer puts in 1% and matches); keep contributions for a deferred retirement. |

**Sensitivity.** `lexflow hypo sens retirement_va --persona … --locality virginia` gives one-at-a-time swings:

| Persona | Ranking (most influence first) |
|---|---|
| Teacher | employer, membership, age, service |
| State employee | employer, membership, age, service |
| Firefighter | employer, service, age; membership does not move the outcome |
| Hybrid member | membership, then age and service tied; employer does not move the outcome |

**Scenario space.**

- 564 valid scenarios of 840.
- 400 by plan class, because membership values with the same plan and scope are interchangeable.
- A pairwise set of 42 covers the 171 feasible pairs.
- Over all 564: 237 not yet eligible, 183 unreduced, 144 reduced.
- `lexflow hypo expand` itself assumes a `district` dimension and fails on this family (see §10).

## 7. Coverage before and after

Eight questions were added: `retirement_which_system`, `_unreduced`, `_buy_service`, `_tax`, `_employer_plan`,
`_apply`, `_appeal` and `_survivor`, all with the topic `benefits`. `_tax` uses `taxes` and `_employer_plan` uses
`business`; the schema has no retirement topic.

Their gold is in `curated_ask/coverage/{va,md,dc}/`:

- Virginia: 35 nuggets, all checked.
- Maryland: 24 nuggets, and `gold: none` for the appeal, whose route was not in the Maryland index.
- DC: 9 nuggets across five questions, which the existing test requires for every question.

The probe was run locally with no Ollama arm:

```
python -m lexflow.ask.coverage --states va,md --questions retirement_... --arm coverage --local \
    --run retire-before --docs-dir /data/benefits
```

That is the "before" run. The "after" run adds `--computed`, so the `retirement_va` family counts. Both reports are
in `/data/benefits/`.

| Cell | Before | After |
|---|---|---|
| va which_system | partial (who, where missing) | **adequate** |
| va unreduced | partial (who) | **adequate** |
| va buy_service | partial (who, fee) | partial (fee) |
| va tax | partial (who, where) | partial (who, where) |
| va employer_plan | adequate | adequate |
| va apply | partial (who, where, form) | partial (form) |
| va appeal | partial (who, appeal) | partial (appeal) |
| va survivor | partial (who) | **adequate** |
| md, all eight | none ×7, partial ×1 (employer_plan) | unchanged |

**Totals:** Virginia went from 1 adequate of 8 to 4 of 8. Maryland went from 0 adequate to 0.

**Why some cells stay partial:**

- The computed signal never claims `appeal` for a state cell (by design in `coverage.computed_signal`).
- The service-credit cost is a `charge`, not a fee.
- The tax and Maryland answers come from `lookup`, which the probe does not read yet (§10).

## 8. Surface

- **CLI:** `python -m lexflow.benefits census | check | stats | lookup <place> <person> | ask <place> <person> |
  family-va | wikidata | wikibase`. `python -m lexflow.benefits.research …` is the research helper.
- **API:** `GET /api/benefits?gov_id=&person=[&who=1]`. With no `gov_id` it returns the person types. It is
  read-only and stores nothing. The running server picks the route up at its next restart; it does not reload.
- **Dashboard:** `#/benefits` has the place picker (the same `/api/targets` autocomplete as Ask and Who do I ask)
  and the person type. The answer shows:
  - pension system cards: run by, channels, the law that creates it, plans, Census members, how to apply, how to
    appeal, and for Virginia a link to `#/hypo/retirement_va`;
  - state program cards;
  - the tax table;
  - the federal list.

  The page was checked at 375 px with no horizontal scroll. "Who do I ask" links to it. `node --check
  dashboard/app.js` passes. There is no tab in the top navigation, because `dashboard/index.html` was not touched;
  adding one is a single line there.

## 9. Wikibase item shapes (proposed; dry run only)

`python -m lexflow.benefits wikibase` prints the items. Nothing is sent, and no key is minted.

- **A statewide system** is a `government agency` item (key `lexflow:agency:<st>:<slug>`) with these claims:
  - `instance of` → `government-agency`;
  - `applies to jurisdiction` → the state;
  - `authority conferred by` → the section item that creates it (`lexflow:statute:<st>:<ref>`). Its reference is
    `quoted text`, `source section` and `determination method` = matched by lexflow's software, with `retrieved`.
  - `official website`, with the page and its quote as reference;
  - `Wikidata item ID`, when the system's own name matched exactly. A match found through the body's name (CalPERS
    for California's Judges' Retirement System) is the administering body's item, not the system's;
  - `review status` = draft.

  That makes 260 items, 216 of them with `authority conferred by`.
- **A state auto-IRA program** is a program item with these claims: `authority conferred by` → its creating
  section, `applies to jurisdiction`, `official website`, and `review status` = draft. That makes 22 items. Its
  board would be `played by` on the program's administering role.
- **Coverage of governments is not written as claims.** That would be some 140,000 links. It stays the Census table.
  After review, a locally administered system would be `part of` its government's item.
- **The tax treatment of an income kind** would be a decision of the state's tax process, with the statute and the
  agency page as references. It is not drafted yet.

## 10. What needs a person's review, and open problems

**Review:**

1. **Choices of section.** The statutory sections chosen for the 260 systems. 28 rest on a definition only, and the
   Census-to-statute grouping is a reading.
2. **Tax readings.** Each state's tax treatment, especially:
   - `partly_exempt` versus `taxable` where a general age deduction applies (Virginia's age deduction is read as
     `taxable` with a condition);
   - the figures that agency pages and the Code disagree on (listed in `notes`).
3. **The Virginia family's assumptions.** ASM-01 to ASM-05, and its plain-language row titles.
4. **Census overrides.** The 37 curated `covers_local` overrides, and the 237 ambiguous local systems (a person
   with the county could settle them).

**Open problems:**

1. **No government id in the unit file.** The join is by name: 237 local systems are ambiguous and 141 are
   unjoined. Special-district and school-district systems (315) are not linked to any government.
2. **The coverage probe does not read `lookup`.** Cells that `lookup` answers (tax, Maryland) count only through
   the Wikibase store or a family. A `benefits` signal beside `computed` in `coverage.run` would let them count. It
   would be a few lines in `lexflow/ask/coverage.py`, which this work did not edit.
3. **No `retirement` topic.** `schema.VOCAB["topic"]` has none, and `who.RULES` has no pattern for pension words,
   so the router falls back to the question file's topic. Proposal, for the schema's owner: a `retirement` topic
   slug, and a pattern of `\bpension|retire(ment|e)?\b|\b401\(k\)|\bIRA\b|annuit`.
4. **`lexflow hypo expand` assumes a `district` dimension.** It fails on this family; `expand.classes(f, "district")`
   in `scenarios/cli.py` should skip a family without one.
5. **Eligibility is modelled for Virginia only.** Elsewhere the answer names the system, its law and its body, not
   the age and service tests. Maryland's § 23-401 (Rule of 90, or 65 with 10 years, for members since July 2011)
   is the next family.
6. **PDFs cannot be quoted.** Handbooks and tax booklets are the clearest statements of many rules. A PDF extractor
   in the image would open them to lexflow's quote fetch.
7. **Wikidata matches are sparse.** Exact-name matching finds few system items. Some systems have items under
   another name, which a person would accept as `close`.
8. **Federal law is cited, not quoted.** There is no U.S. Code index on this copy.
9. **Not modelled:** Social Security coverage of state and local jobs (Section 218 agreements), the Windfall
   Elimination Provision's repeal, and benefit amounts.
