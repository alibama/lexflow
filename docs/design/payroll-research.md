# Public-employee records: payroll, pay scales, headcount and records-office contacts

Status: research, 2026-10-10. It led to the prototype in `lexflow/payroll/`, which follows [payroll-plan.md](payroll-plan.md). **Where the two differ, the plan supersedes this note**, above all on what may be published about pay: §7.3's first rule (cell size 5, with a mean or median, minimum and maximum) failed verification and is replaced by the plan's §6.1. The hosts and terms that changed since the survey are corrected below (from [verify-payroll.md](verify-payroll.md)).

This note surveys the public-employee records that could make lexflow's answers easier to act on. It covers open payroll data in VA, DC, MD, TX, CA, FL, NY, IL, WA and NC and in some large cities and counties among lexflow's governments, plus aggregator sites, pay scales, headcount and records-office contacts. It ends with what lexflow should ingest, what it should only link to, and where this fits in the product: one optional step on the **Setup** page, not a new page.

How it was checked. Every linked source was requested on 10 October 2026; the exceptions are listed in §9. Socrata datasets were read through their metadata API (`/api/views/<id>.json`; that endpoint also carries cached column statistics, which can include a column's most common values, so the plan's refreshes use the dataset-level `/api/views/metadata/v1/<id>` instead, payroll-plan.md §5). ArcGIS layers were read through their REST schema (`?f=json`), and CKAN datasets through `package_show`. Statute text comes from the Open US Law files already downloaded in `data/raw/open-us-law/`, and each citation links to the state publisher's URL kept with that section. All requests were read-only, at most one a second per host, with the User-Agent `lexflow-research/0.1 (https://github.com/alibama/lexflow)` and 15-second timeouts. Sites whose robots.txt or blocking rules shut out automated clients were not crawled; they are marked below. No person-level row was downloaded or kept. The only rows read were aggregate counts and averages, computed on the publisher's server to test the method in §7.2.

Scope rules followed throughout:

* Organisations and official office channels only. This note names no employee and copies no personal email address or phone number.
* For public employees, lexflow works with aggregates (by government, agency and job title) and with official role contacts. Anything person-level is linked to its official source.
* lexflow's users are private people. Nothing here adds collection about them (§7.5).

---

## 0. The short version

| # | Finding | What it means for lexflow |
|---|---|---|
| F1 | **Pay data is public by statute in every jurisdiction surveyed.** Most statutes name the employee's name, title and salary (§2). | The question is not whether lexflow may use the data. It is how little of it lexflow needs. |
| F2 | **Official state-level open data is uneven.** DC, NY (public authorities only), WA, NC, IL and VA publish searchable state payrolls. Only DC's is an open, licensed, machine-readable dataset. TX, MD and the NY state agencies have no official open state payroll that we could find. CA publishes positions, not names. Florida's portal forbids crawlers. | State-level aggregates should come from the Census Bureau's survey, which covers every government lexflow has, and from published pay scales. Do not build per-state payroll scrapers. |
| F3 | **City and county portals are better.** NYC, Chicago, LA City, LA County, San Francisco, Seattle, Baltimore, Montgomery County, Houston, Miami, Miami-Dade, Charlotte, Norfolk and Virginia Beach publish payroll through Socrata, ArcGIS or CKAN. | These APIs can **aggregate on the publisher's server** (SoQL `$group`, ArcGIS `outStatistics`). lexflow can store counts and pay statistics without a single name reaching its disk. Both methods were tested (§7.2). |
| F4 | **The Census Annual Survey of Public Employment & Payroll (ASPEP) publishes an individual-unit file.** It is keyed on a 14-digit Census government ID with the same structure as lexflow's `gov_id`. | This is the one source that gives employees and payroll by function for all of lexflow's governments. It is public domain and needs no API key. It should be the first thing ingested. |
| F5 | **Several aggregators forbid what lexflow would do with them.** Transparent California's data agreement bans republishing datasets. SeeThroughNY reserves all rights. The Texas Tribune's terms ban automated use and unauthorised linking. Open Payrolls blocks automated clients. | Use none of them as a data source. Link at most to official sources. |
| F6 | **Records officers must be designated, and their contacts published, in most of these jurisdictions** (VA, MD, WA, IL, NY, TX by office). Three central lists exist: the Virginia FOIA Council's search, the Maryland PIA Manual's Appendix J and DC's FOIA officer list. Washington's state agency officers are published in the State Register. | Ingest the **office channel**: the role, the office mailbox, the portal URL and the office line. Link the official list for names. New values go through the review queue planned in [entities-contacts.md](entities-contacts.md) (D7). |
| F7 | **Staff pay sets records fees.** Several statutes tie fees to salaries: Maryland prorates each person's salary and makes the first 2 hours free. New York charges the hourly salary of the lowest-paid employee with the needed skill. North Carolina and DC charge the actual labour cost. | Pay scales for clerk and records titles let lexflow show a person a **fee range before they ask**. This is the most direct way this data helps someone act (§1). |
| F8 | **Several "anonymised" payrolls can still identify people.** Houston publishes hashed IDs with birth year, gender and race. LA City adds gender and ethnicity to names. Virginia Beach publishes position IDs with hire dates. | Never ingest demographic, birth-year, hire-date or ID columns. Publish no pay figure that could single out a person: the plan's rules (§7.3, superseded by payroll-plan.md §6.1) show pay only for groups of 11 or more, and never a minimum, maximum or mean. |

---

## 1. Why this helps a person act

lexflow answers "how do I request public records" and "how do I start a business" for each government. Employee records add four practical things to those answers:

1. **Who to write to.** Most state laws require a named records or FOIA officer for each public body (§6.4). The officer's office mailbox or portal is a better contact than a general city inbox. It moves a government up lexflow's contact ladder (`page` level in `lexflow/municipal/contacts.py`).
2. **What it may cost.** Fees often depend on staff pay:
   * Maryland: staff and attorney review costs "shall be prorated for each individual's salary", and the first 2 hours are free ([GP § 4-206](https://mgaleg.maryland.gov/mgawebsite/Laws/StatuteText?article=ggp&section=4-206&enactments=false)). The Attorney General's manual adds that benefits are left out, and that the Compliance Board has objected when a higher-paid person did work a lower-paid employee could do.
   * New York: an agency may charge "the hourly salary attributed to the lowest paid agency employee who has the necessary skill" ([POL § 87(1)(c)](https://www.nysenate.gov/legislation/laws/PBO/87)).
   * Virginia: actual cost of "accessing, duplicating, supplying, or searching" ([§ 2.2-3704](https://law.lis.virginia.gov/vacode/2.2-3704/)).
   * DC: actual cost of "searching for, reviewing, redacting, and making copies" ([§ 2-532(b)](https://code.dccouncil.gov/us/dc/council/code/sections/2-532)).
   * North Carolina: a special service charge based on "labor costs of the personnel" ([G.S. 132-6.2](https://www.ncleg.gov/EnactedLegislation/Statutes/HTML/BySection/Chapter_132/GS_132-6.2.html)).
   * Texas: labour may be charged only above 50 pages, or when the records are in separate buildings or remote storage ([§ 552.261](https://tcss.legis.texas.gov/resources/GV/htm/GV.552.htm#552.261)).
   * Illinois: no search or personnel costs for non-commercial, non-voluminous requests ([5 ILCS 140/6](https://www.ilga.gov/ftp/ILCS/Ch%200005/Act%200140/000501400K6.html)).

   With the pay band for a records clerk title, lexflow can say: "after the first 2 free hours, staff time costs about $X to $Y an hour here".
3. **How big the office is.** Headcount by function (Census) or by agency (city budgets) tells a person whether a town has one clerk or a records unit. That sets expectations about response times and about narrowing a request.
4. **Where the person-level record lives.** When someone needs one employee's pay (for example, to check an official's salary), lexflow links to the official payroll search or tells them which statute makes it public. It does not show the record itself.

---

## 2. Legal basis: what each jurisdiction makes public

| Jurisdiction | What the statute makes public | What stays private (relevant parts) | Records-officer rule |
|---|---|---|---|
| VA | FOIA does not deny access to "the name, position, job classification, official salary, or rate of pay" of any employee. Access is not required to the pay of employees earning $10,000 a year or less ([§ 2.2-3705.1(1)](https://law.lis.virginia.gov/vacode/2.2-3705.1/)) | Other personnel information | Every public body designates and publicly identifies a FOIA officer. State bodies post the officer on their website ([§ 2.2-3704.2](https://law.lis.virginia.gov/vacode/2.2-3704.2/)). Records officers for records management are a separate role ([§ 42.1-85](https://law.lis.virginia.gov/vacode/42.1-85/)) |
| DC | "The names, salaries, title, and dates of employment of all employees and officers of a public body". Participants in the Address Confidentiality Program can ask DCHR to keep theirs out ([§ 2-536(a)(1)](https://code.dccouncil.gov/us/dc/council/code/sections/2-536)) | Exempt categories in § 2-534 | Agency FOIA officers (list in §6.4) |
| MD | "Public record" includes a document that lists an employee's salary ([GP § 4-101(k)(2)](https://mgaleg.maryland.gov/mgawebsite/Laws/StatuteText?article=ggp&section=4-101&enactments=false)). The finance exemption "does not apply to the salary of a public employee" ([GP § 4-336(a)](https://mgaleg.maryland.gov/mgawebsite/Laws/StatuteText?article=ggp&section=4-336&enactments=false)). The AG's manual says salaries, bonuses and performance awards may not be withheld as personnel records | Personnel records ([GP § 4-311](https://mgaleg.maryland.gov/mgawebsite/Laws/StatuteText?article=ggp&section=4-311&enactments=false)). Home address, personal phone and personal email ([GP § 4-331](https://mgaleg.maryland.gov/mgawebsite/Laws/StatuteText?article=ggp&section=4-331&enactments=false)). The manual says employees' individual benefit choices must be withheld | Each unit identifies a PIA representative with a name, business address, phone, email and website, and the AG keeps the list ([GP § 4-503](https://mgaleg.maryland.gov/mgawebsite/Laws/StatuteText?article=ggp&section=4-503&enactments=false)) |
| TX | "The name, sex, ethnicity, salary, title, and dates of employment of each employee and officer" ([Gov't Code § 552.022(a)(2)](https://tcss.legis.texas.gov/resources/GV/htm/GV.552.htm#552.022)) | Home address, home phone, emergency contact, SSN and family information of employees who elect to keep them private ([§ 552.117](https://tcss.legis.texas.gov/resources/GV/htm/GV.552.htm#552.117), [§ 552.024](https://tcss.legis.texas.gov/resources/GV/htm/GV.552.htm#552.024)) | The chief administrative officer is the officer for public information. Each elected county officer is the officer for that office ([§ 552.201](https://tcss.legis.texas.gov/resources/GV/htm/GV.552.htm#552.201)) |
| CA | The Controller must publish each city's, county's and special district's annual compensation in a printable, downloadable format ([Gov. Code § 12463(a)](https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=GOV&sectionNum=12463.)). Local agencies report it by April 30 ([§ 53891(a)](https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=GOV&sectionNum=53891.), [§ 53892(l)](https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=GOV&sectionNum=53892.)). The state Supreme Court held that names and salaries of employees earning $100,000 or more, peace officers included, are not exempt under the CPRA ([IFPTE Local 21 v. Superior Court, 2007, S134253](https://scocal.stanford.edu/opinion/internat-prof-tech-engineers-v-super-ct-33771)) | Personnel files whose disclosure is an unwarranted invasion of privacy ([§ 7927.700](https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=GOV&sectionNum=7927.700.)) | No statewide designation rule found |
| FL | "All state, county, and municipal records are open" ([§ 119.01](http://www.leg.state.fl.us/statutes/index.cfm?App_mode=Display_Statute&URL=0100-0199/0119/Sections/0119.01.html)). The state transparency website must include "position and rate information" for positions in the General Appropriations Act ([§ 215.985](http://www.leg.state.fl.us/statutes/index.cfm?App_mode=Display_Statute&URL=0200-0299/0215/Sections/0215.985.html)) | Home addresses and related details of many listed employee classes ([§ 119.071(4)(d)](http://www.leg.state.fl.us/statutes/index.cfm?App_mode=Display_Statute&URL=0100-0199/0119/Sections/0119.071.html)) | No statewide designation rule found |
| NY | Each agency keeps "a record setting forth the name, public office address, title and salary of every officer or employee" ([POL § 87(3)(b)](https://www.nysenate.gov/legislation/laws/PBO/87)). Public authorities report salaries to the Authorities Budget Office under Public Authorities Law § 2800 (stated in the ABO datasets) | FOIL exemptions in § 87(2) | Agencies name records access officers by name or by title and business address, with an email address if they take requests by email ([21 NYCRR 1401.2](https://regulations.justia.com/states/new-york/title-21/chapter-xxv/part-1401/section-1401-2), Justia reprint current to September 2024) |
| IL | All records of "the obligation, receipt, and use of public funds" are public ([5 ILCS 140/2.5](https://www.ilga.gov/ftp/ILCS/Ch%200005/Act%200140/000501400K2.5.html)). Information bearing on public employees' public duties "shall not be considered an invasion of personal privacy" ([140/7(1)(c)](https://www.ilga.gov/ftp/ILCS/Ch%200005/Act%200140/000501400K7.html)) | Highly personal information (§ 7(1)(c)) | Each body designates FOIA officers ([140/3.5](https://www.ilga.gov/ftp/ILCS/Ch%200005/Act%200140/000501400K3.5.html)). Each body must display "a block diagram giving its functional subdivisions", its operating budget, its approximate number of employees and "a directory designating the Freedom of Information officer" ([140/4](https://www.ilga.gov/ftp/ILCS/Ch%200005/Act%200140/000501400K4.html)) |
| WA | Salaries of state employees are public under RCW 42.56.210 (OFM's salary FAQ, §3). Personal information in employee files is exempt only "to the extent that disclosure would violate their right to privacy" ([RCW 42.56.230(3)](https://apps.leg.wa.gov/rcw/default.aspx?cite=42.56.230)) | Job applications and related material ([RCW 42.56.250](https://apps.leg.wa.gov/rcw/default.aspx?cite=42.56.250)) | Each agency appoints and publicly identifies a public records officer. State agency officers are published in the State Register and kept on the code reviser's website ([RCW 42.56.580](https://apps.leg.wa.gov/rcw/default.aspx?cite=42.56.580)) |
| NC | For state employees: name, age, original hire date, contract terms, position, title, current salary, each change in pay and classification, disciplinary dismissals, and office or station ([G.S. 126-23](https://www.ncleg.gov/EnactedLegislation/Statutes/HTML/BySection/Chapter_126/GS_126-23.html)). The same for city ([160A-168](https://www.ncleg.gov/EnactedLegislation/Statutes/HTML/BySection/Chapter_160A/GS_160A-168.html)) and county employees ([153A-98](https://www.ncleg.gov/EnactedLegislation/Statutes/HTML/BySection/Chapter_153A/GS_153A-98.html)) | The rest of the personnel file | No statewide designation rule found |

Note for lexflow: "public by statute" is not a reason to ingest. North Carolina makes employees' **age** public, and Texas makes **sex and ethnicity** public. lexflow still keeps none of these (§7.3).

---

## 3. Official payroll sources by state

"Names" says whether the official source shows employee names. "API" says how a machine reads it. Licence "not stated" means the dataset page gives none; the portal's general terms then apply.

| State | Official source (publisher) | Fields | Names | Granularity and coverage | Cadence | API and format | Licence or terms |
|---|---|---|---|---|---|---|---|
| VA | [Commonwealth Data Point: Salaries](https://datapoint.apa.virginia.gov/salaries.php) (Auditor of Public Accounts) | Agency, position title, state salary and bonuses (from 2020). Before 2020 also non-state salary, special rate and begin date | No (a record ID) | Per employee and fiscal year, filterable by agency | By fiscal year (not stated) | Web app. No bulk download seen | The [About page](https://datapoint.apa.virginia.gov/about.php) says the data come from the state's financial systems, that the APA "does not own the data", and that some fields are redacted under FOIA, FERPA and HIPAA. No licence |
| DC | [DC Public Employee Salary](https://opendata.dc.gov/datasets/DCGIS::dc-public-employee-salary) (OCTO, from DCHR) | `FIRST_NAME`, `LAST_NAME`, `JOBTITLE`, `DESCRSHORT` (agency), `GRADE`, `COMPRATE`, `HIREDATE_STRING`, `GVT_TYPE_OF_APPT` | Yes | 62,201 rows, one per employee. Last modified 26 Sep 2024 | Snapshot. DCHR describes its own release as quarterly | ArcGIS REST ([MapServer/35](https://maps2.dcgis.dc.gov/dcgis/rest/services/DCGIS_DATA/Government_Operations/MapServer/35)), CSV and GeoJSON downloads | CC BY 4.0. DCHR also posts quarterly [Public Body Employee Information](https://dchr.dc.gov/public-employee-salary-information) PDFs (the newest listed is as of 31 Dec 2021) |
| MD | No official open dataset of named state payroll found. Salaries are public (§2) | – | – | – | – | – | Baltimore City and Montgomery County publish their own (§4) |
| TX | No official open state payroll found. The Comptroller runs state payroll, and the Texas Tribune gets its copy from the Comptroller under the PIA (§5). So the official route is a PIA request to the Comptroller (§ 552.022(a)(2)) | – | – | – | – | – | data.texas.gov has agency aggregates, for example [DFPS average monthly salaries by program and staff type](https://data.texas.gov/d/pedx-fc9i) |
| CA | [Government Compensation in California](https://gcc.sco.ca.gov/) (State Controller; formerly `publicpay.ca.gov`, which now redirects there) | Employer, position, pay and benefits | **No.** The Controller's FAQ says it "does not receive employee names for most positions" | Per position, by employer type: cities, counties, special districts, state and CSU (required). UC, community colleges, courts, K–12, First 5 and fairs report voluntarily | Yearly reports. Search coverage says the raw files are refreshed each weekday | Raw export: yearly CSVs in ZIPs, from the site's reports pages | During this survey the old host returned **HTTP 403** to both automated clients used here. At verification (10 October 2026) `gcc.sco.ca.gov` answered HTTP 200 and its robots.txt allowed the research client. Terms not read: link only, and treat any download as a manual step |
| FL | [Florida Has a Right to Know: state payroll search](https://floridahasarighttoknow.myflorida.com/search_state_payroll) | Per launch coverage: name, agency, position and salary for executive branch agencies, the Lottery, the courts, universities, colleges and others | Yes | Per employee | Not verified | Web app | **robots.txt disallows all agents except named search engines.** lexflow must not crawl it. Link only |
| NY | No open dataset of named state-agency payroll found on data.ny.gov. The Authorities Budget Office publishes [Salary Information for State Authorities](https://data.ny.gov/d/unag-2p27), plus [local authorities](https://data.ny.gov/d/fx93-cifz), [local development corporations](https://data.ny.gov/d/wryv-rizw) and [IDAs](https://data.ny.gov/d/9yx9-29p4) | Authority, fiscal year, name, title, group, department, pay type, base, actual paid, overtime, bonus, other and total compensation | Yes | Per employee, eight fiscal years | Annual | Socrata (SODA) | Licence not stated (data.ny.gov terms apply). The [MTA payroll](https://data.ny.gov/d/kcjb-nf3e) is similar (names, start and separation dates, pay) |
| IL | [Comptroller salary database](https://illinoiscomptroller.gov/financial-reports-data/data-sets-portals/salary-database) | Search by name, agency, position title, salary and year. An agency summary shows employee counts and year-to-date gross pay | Yes | Per employee. Executive agencies, boards, courts, the General Assembly and statewide officers. Years 2024–2026 | Current (agency summary updated within the week) | Web app. No download seen | Not stated |
| WA | [State employee salaries](https://fiscal.wa.gov/Staffing/Salaries) (LEAP and OFM) | Name, job title and total annual earnings, including overtime and premiums, rounded to $100 ([FAQ](https://fiscal.wa.gov/staffing/SalaryDataFAQ.pdf)) | Yes. Names are withheld for domestic-violence victims and for jobs that require confidentiality | Per employee per calendar year, five years, earnings over $300. No students | Annual, early summer | Search, plus a full download link **sent by email to `leap@leg.wa.gov` on request** (name and email asked) | The FAQ says publication "is not required by law". data.wa.gov holds only an old [2010–2013 file](https://data.wa.gov/d/y3ds-rkew) |
| NC | [State Employee Salary Database](https://ncosc.gov/salary_database) (Office of the State Controller) | Names, job and position titles, salaries | Yes | Active permanent and temporary employees paid through the Integrated HR-Payroll System. Excludes county, teacher, community college, university and General Assembly employees | Monthly, on the first business day | Web search. No download mentioned | Links to a disclaimer and terms. Not read during this survey; read at verification (10 October 2026): non-commercial copying is allowed, unaltered and with a citation, so a link fits (§9, item 4) |

---

## 4. Large cities and counties

All of these are lexflow governments (Census GUS 2022). The `gov_id` column is lexflow's key.

| Government (`gov_id`) | Dataset (publisher) | Fields | Names | Cadence | API | Licence or terms |
|---|---|---|---|---|---|---|
| City of New York (`33203100100000`) | [Citywide Payroll Data (Fiscal Year)](https://data.cityofnewyork.us/d/k397-673e) (Office of Payroll Administration) | Fiscal year, agency, last name, first name, start date, borough, title, leave status, base salary, pay basis, regular hours and pay, OT hours and pay, other pay | Yes | Annual | SODA | No licence field. NYC Open Data terms apply (not re-read here) |
| City of New York | [Position Schedule](https://data.cityofnewyork.us/d/f4wx-5ve6) (OMB) | Agency, unit of appropriation, title code and name, number of full-time positions, minimum, maximum and mean salary | No (aggregate) | Twice a year | SODA | as above |
| City of New York | [Full-Time and FTE Headcount](https://data.cityofnewyork.us/d/84ax-hg3y) (OMB) | Agency, fiscal year, personnel type, funding, total | No (aggregate) | Twice a year | SODA | as above |
| City of New York | [Local Law 18 Pay and Demographics, agency table](https://data.cityofnewyork.us/d/423i-ukqr) | Agency, EEO-4 category, pay band, status, race, ethnicity, gender, number of employees | No (aggregate, but small cells) | Annual | SODA | as above |
| City of Chicago (`14201601600000`) | [Current Employee Names, Salaries, and Position Titles](https://data.cityofchicago.org/d/xzkq-xp2w) | Name, job title, department, full or part time, salary or hourly, typical hours, annual salary, hourly rate | Yes | Daily | SODA | "See Terms of Use" (Chicago data portal) |
| City of Chicago | [2026 Budget Ordinance: Positions and Salaries](https://data.cityofchicago.org/d/v2t2-vajc) | Department, fund, organisation, division, section, schedule grade, bargaining unit, title code and description, budgeted units, budgeted pay rate, total | No (positions) | Annual (one dataset a year since 2011) | SODA | as above |
| Cook County (`14101601600000`) | [Employee Payroll](https://datacatalog.cookcountyil.gov/d/xu6t-uvny) (Comptroller) | Fiscal year and quarter, name, bureau, office, job code and title, base pay, position ID, employee ID, hire date | Yes | Labelled quarterly, but last updated June 2018 | SODA | Public domain. Also [FY2017 budgeted positions by business unit](https://datacatalog.cookcountyil.gov/d/ngjf-wnd5) (public domain) |
| City of Los Angeles (`05201902700000`) | [City Employee Payroll (Current)](https://controllerdata.lacity.org/d/g9h8-fvhu) (Controller) | Year, last and first name, department, job class and title, employment type, MOU, regular, overtime, other, total and benefit pay, **gender, ethnicity** | Yes | Bi-weekly (DWP quarterly) | SODA | CC BY 4.0 |
| Los Angeles County | [LA County Employee Salaries](https://hub.arcgis.com/datasets/1fefbd3af4cf41fda827f2c23a1fe09b_0) (Auditor-Controller) | Year, name, position title, department, base, overtime, other earnings, leave payouts, total earnings, benefits by type, total compensation | Yes | 1.41 million rows. Modified 31 Aug 2026 | ArcGIS FeatureServer | None stated. An older copy of the layer carries an "informational purposes" disclaimer |
| San Francisco | [Employee Compensation](https://data.sf.gov/d/88g8-5mnd) (Controller; the portal moved from `data.sfgov.org`, which answers HTTP 301) | Organisation group, department, union, job family, job, a per-employee identifier, salaries, overtime, other pay, retirement, health and dental, other benefits, totals, hours, employment type | **No** | Weekly (since FY2013) | SODA | ODC Public Domain Dedication and Licence |
| City of Seattle (`48201702100000`) | [City of Seattle Wage Data](https://data.seattle.gov/d/2khk-5ukd) (Department of Human Resources) | Department, last name, first name, job title, hourly rate. "Exclusions may apply for vulnerable populations" | Yes | Monthly | SODA | Public domain |
| City of Baltimore (`21200400100000`) | [Baltimore City Employee Salaries](https://hub.arcgis.com/datasets/0bceed42ed994e65bec410bdf9c383c8_0) (Open Baltimore) | Name, job title, agency ID and name, hire date, annual salary, gross pay, fiscal year | Yes | FY2011 to FY2025, employees on payroll on June 30. 231,945 rows | ArcGIS FeatureServer | None stated |
| Montgomery County, MD (`21101601500000`) | [Employee Salaries 2025](https://data.montgomerycountymd.gov/d/4rpu-n3ya) (one dataset a year) | Department, division, **gender**, base salary, overtime, longevity pay, grade | No | Annual | SODA | Not stated. Also [Average Salary by Job Classification](https://data.montgomerycountymd.gov/d/48wg-fkab) (2020) and [Salary Schedule](https://data.montgomerycountymd.gov/d/6xch-b4j2) (2020, public domain) |
| City of Houston (`44210100800000`) | [Payroll](https://data.houstontx.gov/dataset/payroll) (Administration and Regulatory Affairs) | Two hashed IDs, **birth year, gender, race**, pay grade, FLSA status, EEO code, employment type, department, status, year, position start and end dates, annual base salary, gross, base, overtime and other pay | No ("anonymized", but see §7.3) | 2018 onward. The 2026 file has 26,008 rows. Updated 6 Oct 2026 | CKAN (`datastore_search`) and yearly CSVs | Open Data Commons Attribution |
| City of Dallas (`44205700700000`) | [Payroll Registry](https://www.dallasopendata.com/d/qrgv-mijx) | Pay period, payroll type, employee count, gross payroll, taxes, insurance, health, retirement, total | No (one row per pay period) | Last updated Oct 2019 | SODA | Not stated |
| City of Austin (`44222700100000`) | No payroll dataset found on data.austintexas.gov. It has aggregates only, such as employees by gender, attrition rate and number of jobs | – | – | – | SODA | – |
| City of Miami (`10201301300000`) | [City Employee Roster](https://hub.arcgis.com/datasets/421065367dc342888cddabc106e09722_0) | Name, title, department, annual salary, gross of last paycheck, YTD gross, years | Yes | Bi-weekly. 5,225 rows | ArcGIS FeatureServer | CC BY 4.0 |
| Miami-Dade County (`10101301300000`) | [Miami Dade County Employee Pay Information](https://hub.arcgis.com/datasets/3d3cafbe1aed46e9b1e0f2ec6f429756_0) | Name, title, department, annual salary, last paycheck, YTD | Yes | Modified Sep 2026. The description notes that five departments became independent constitutional offices on 7 Jan 2025 and left this payroll | ArcGIS FeatureServer | "As is" disclaimer |
| City of Charlotte (`34206000100000`) | [City of Charlotte Employee Salaries](https://hub.arcgis.com/datasets/2eaeb9bbc40c4bc6816170ba08e71021_1) | Name, unit, department, job title, annual rate, full or part time, year, quarter, regular or temporary | Yes | Quarterly, appended | ArcGIS MapServer ([layer 1](https://gis.charlottenc.gov/arcgis/rest/services/ODP/CityofCharlotteEmployeeSalaries/MapServer/1)) | CC BY 4.0 |
| City of Norfolk, VA | [Employee Salaries](https://data.norfolk.gov/d/4fsk-z8s8) (Human Resources) | Department, division, job title, classification, start date, title date, FLSA status, annual base rate | No | Daily | SODA | Public domain |
| City of Virginia Beach (`47213200100000`) | [Employee Salaries](https://hub.arcgis.com/datasets/33c808ff26ed445c88de2b3f1fc4929e_0) (Human Resources) | Department, supervisory organisation, **position ID**, position title, FLSA, initial hire date, date in title, base pay | No | Modified 5 Oct 2026. 7,754 rows | ArcGIS FeatureServer | Custom terms on data.virginiabeach.gov |
| City of Charlottesville (`47210400100000`), Fairfax County (`47103003000000`), King County (`48101701700000`), City of Raleigh (`34209200800000`) | No employee pay dataset found. King County publishes [pay rates and salary tables](https://cd.kingcounty.gov/en/dept/dhr/about-king-county/hr-resources-employees-partners/compensation-classification/pay-rates) | – | – | – | – | Use pay scales and the Census unit file. Send a FOIA or records request for anything else |

---

## 5. Aggregators and news databases

| Site (operator) | What it holds | Terms that matter | Verdict for lexflow |
|---|---|---|---|
| [Transparent California](https://transparentcalifornia.com/) (a project of the Nevada Policy Research Institute) | Names, titles, pay and pensions, mostly from records requests | Bulk data comes only under a [data use agreement](https://transparentcalifornia.com/records-request): "exclusively for non-commercial purposes". Recipients may not "post, host, or make the full datasets publicly available in raw or derivative form", and may not "replicate or reverse engineer" the database. The site calls the compilation proprietary. Its [disclaimer](https://transparentcalifornia.com/disclaimer) says errors come from agencies' reporting | **Do not use. Do not scrape.** lexflow's sync and wiki would republish derived data |
| [SeeThroughNY](https://seethroughny.net/) (Empire Center for Public Policy) | Names, titles and pay for NY state and local governments, authorities and schools | [Terms](https://seethroughny.net/terms-use): all contents copyrighted, "Any rights not expressly granted herein are reserved". No obtaining material by "any means not intentionally made available" | **Do not use. Do not scrape.** Link at most |
| [Open Payrolls](https://openpayrolls.com/) | Per-person payroll pages for many states | Returned HTTP 403 to automated requests, including `robots.txt`, so its terms could not be read | **Do not use.** Not an official source |
| [Texas Tribune Government Salaries Explorer](https://salaries.texastribune.org/about/) | Texas state payroll obtained from the Comptroller under the PIA, refreshed about monthly, with a CSV download. It includes race and gender | [Terms of service](https://www.texastribune.org/about/terms-of-service/): no "automated use of the system", no use "in connection with any commercial endeavors" without approval, and "unauthorized framing of or linking to the Service is prohibited" | **Do not use or link.** For Texas, point to the PIA route (§ 552.022(a)(2)) and the Comptroller |
| [OpenTheBooks](https://www.openthebooks.com/) (American Transparency) | Spending and payroll across many governments | [Terms](https://www.openthebooks.com/terms-and-conditions) allow copying and redistributing search results, with attribution given "in a neutral manner". Scraping and commercial use are not addressed | Person-level, so link only. Not needed: the official sources cover what lexflow wants |
| News databases: the Virginia Center for Investigative Journalism's Virginia salary database at WHRO (July 2026, 2025 pay, from the Department of Accounts and universities; its page returned 404 to automated clients, so it is not linked here), the [Baltimore Sun salary archive](https://salaries-archive.news.baltimoresun.com/city/fy2015/), the News & Observer | Names and pay, compiled by newsrooms | Newsroom terms. Journalism, not an official source | **Link only**, and only where no official source exists |

---

## 6. Other employee-related records that help a person act

### 6.1 Headcount and payroll by function, for every government (ingest)

* **Census ASPEP.** The [Annual Survey of Public Employment & Payroll](https://www.census.gov/programs-surveys/apes.html) counts state and local civilian employees and gross payroll for the March pay period. Preliminary 2025 data were released in April 2026. The [2025 tables page](https://www.census.gov/data/tables/2025/econ/apes/annual-apes.html) links an [individual unit file](https://www2.census.gov/programs-surveys/apes/tables/2025/2025_individual_unit_files.zip) (ZIP, 10.9 MB) with "all data items by item code (functional category) for individual governments".
* **It joins to lexflow directly.** The documented [ID layout](https://www2.census.gov/programs-surveys/apes/technical-documentation/file-layouts/2011/gov-id-layout-11.csv) is a 14-character Census ID: state code, type, county, unit, supplement and sub-code. lexflow's `gov_id` is the GUS `CENSUS_ID_GIDID`, a 14-digit ID of the same shape (Charlottesville is `47210400100000`). The 2025 file's ID column must still be checked on first load. The ID record also has a "year of data" flag that marks imputed (`II`) and missing (`NN`) responses. lexflow should keep it and show imputed figures as estimates.
* **API.** The [`timeseries/govsemp` API](https://www.census.gov/data/developers/data-sets/govsemp.html) now requires a key for all queries. The ZIP does not, so lexflow should use the ZIP.
* **Licence.** A US federal work, with the Census citation policy (see [credits-research.md](credits-research.md)).
* **For counties and states, BLS QCEW** gives government employment and wages by ownership (federal, state, local) through [CSV data slices](https://www.bls.gov/cew/additional-resources/open-data/). Useful as a cross-check, not needed first.

### 6.2 Pay scales and job classifications (ingest)

These are tables of grades and ranges, not records about people. They are what the fee estimate in §1 needs.

| Jurisdiction | Source |
|---|---|
| VA | DHRM [jobs and salary structure](https://www.dhrm.virginia.gov/jobs-and-careers/jobs-and-salary-structure): pay bands 1–9, occupational families and [career groups](https://www.dhrm.virginia.gov/jobs-and-careers/jobs-and-salary-structure/career-groups) |
| DC | DCHR [classification and compensation](https://dchr.dc.gov/node/1630296): [FY2026 non-union](https://dchr.dc.gov/page/fiscal-year-2026-non-union-salary-schedules) and [union](https://dchr.dc.gov/page/fiscal-year-2026-union-salary-schedules) schedules (PDF) |
| MD | DBM [Standard Salary Schedule effective 1 July 2026](https://dbm.maryland.gov/employees/Documents/SalaryInfo/STANDARD_SALARY_SCHEDULE_Effective_7-1-26.pdf) and [Executive Pay Plan](https://dbm.maryland.gov/employees/Documents/SalaryInfo/EXECUTIVE_PAY_PLAN_SALARY_SCHEDULE_Effective_7-1-26.pdf). Montgomery County's [salary schedule](https://data.montgomerycountymd.gov/d/6xch-b4j2) is on Socrata |
| TX | State Auditor's [salary schedules A, B and C](https://hr.sao.texas.gov/CompensationSystem/SalarySchedules) and [job descriptions](https://sao.texas.gov/CompensationSystem/JobDescriptions) (the State Classification Plan) |
| CA | CalHR [pay scales manual](https://www.calhr.ca.gov/state-hr-professionals/Pages/pay-scales.aspx) (section 15 lists classes alphabetically) |
| FL | DMS broadband classification and compensation program ([program manual](https://www.dms.myflorida.com/content/download/115449/637238/Classification_and_Compensation_Program_Manual_[R_05-13-19].pdf), 2019). Statutory frame: [§ 110.2035](https://www.flsenate.gov/laws/statutes/2024/110.2035) |
| NY | Department of Civil Service [Title and Salary Listing](https://data.ny.gov/d/t3vp-5tka): title code, grade, negotiating unit, agency and **filled positions** per title. Semi-annual, on Socrata. It is both a pay scale and a headcount by title and agency |
| NYC | OMB [Position Schedule](https://data.cityofnewyork.us/d/f4wx-5ve6) (§4): use its position counts. Its minimum and maximum salary per title are each one position's pay, so they are not republished (§7.3) |
| IL | CMS [Pay Plan](https://cms.illinois.gov/personnel/employeeresources/personnelpayplan1.html) (80 Ill. Adm. Code 310) |
| WA | OFM [salary schedules](https://ofm.wa.gov/state-human-resources/compensation-job-classes/compensation-administration/salary-schedules) (PDF and XLSX, effective 1 July 2026) and the [classified job listing](https://ofm.wa.gov/hr-policies/compensation-job-classes/job-classes-salaries/listing/). King County [pay rates](https://cd.kingcounty.gov/en/dept/dhr/about-king-county/hr-resources-employees-partners/compensation-classification/pay-rates) |
| NC | OSHR [classification and compensation](https://oshr.nc.gov/state-employee-resources/classification-compensation) |

### 6.3 Budgets, headcount by department and organisation charts (ingest the numbers, link the charts)

* **Texas** agencies report FTEs to the State Auditor every quarter ([Gov't Code § 2052.103](https://tcss.legis.texas.gov/resources/GV/htm/GV.2052.htm#2052.103)). The SAO publishes them under [FTE reports](https://sao.texas.gov/Reports/Category/FTE/).
* **Illinois** bodies must display a block diagram of their functional subdivisions, their operating budget and their approximate employee count ([5 ILCS 140/4(a)](https://www.ilga.gov/ftp/ILCS/Ch%200005/Act%200140/000501400K4.html)). This is the only statutory organisation chart found. lexflow should link it from each body's records page, not copy it.
* **City budgets as data:** NYC [headcount](https://data.cityofnewyork.us/d/84ax-hg3y) and [position schedule](https://data.cityofnewyork.us/d/f4wx-5ve6), Chicago [budgeted positions](https://data.cityofchicago.org/d/v2t2-vajc), Cook County [budgeted positions](https://datacatalog.cookcountyil.gov/d/ngjf-wnd5).
* **Illinois Comptroller:** the agency summary in the [salary database](https://illinoiscomptroller.gov/financial-reports-data/data-sets-portals/salary-database) gives employee counts and YTD gross by agency. Only that summary should be used.

### 6.4 Records officers, clerks and licensing staff (ingest the office channel, link the list)

| Jurisdiction | Official list | What lexflow should store |
|---|---|---|
| VA | FOIA Council, [FOIA officers by agency or organisation](https://foiaform.dls.virginia.gov/Home/Searchforms/0) (a search form). Agencies update it with a contact form | Role ("FOIA officer"), the body's FOIA page or shared FOIA mailbox, the source list's URL |
| MD | Attorney General, [PIA Manual](https://oag.maryland.gov/resources-info/Pages/pia-manual.aspx) (20th ed., October 2026), Appendix J: State, county and municipal PIA representatives (updated 1 Oct 2026) | Role ("PIA representative"), a shared PIA mailbox where one is listed (otherwise the unit's PIA web page), office line, website |
| DC | [DC FOIA officer contact information](https://www.open-dc.gov/node/4861) (about 88 bodies, marked "under review, current as of Jan 2022"). Many entries are shared mailboxes | Shared FOIA mailboxes as-is. For personal addresses, the agency's FOIA page instead |
| WA | State agency public records officers, published in the [Washington State Register](https://lawfilesext.leg.wa.gov/law/wsr/) under RCW 42.56.580. Local agencies post their own | Role and agency, with the WSR notice as the source |
| IL | Each body's own directory of FOIA officers (140/4(b)) | Role and the body's FOIA page |
| NY | Each agency's records access officer, by name or by title (21 NYCRR 1401.2) | Role and title, never the name |
| TX | The chief administrative officer, or each elected county officer, is the officer for public information (§ 552.201) | The office ("County Clerk", "City Secretary") as the role |

Clerks and licensing staff: the Census GUS file already gives each government an official's **title** (`TITLE`), which lexflow loads. The [entities-contacts plan](entities-contacts.md) adds office types (for example `lexflow:office-type:fl:clerk_of_circuit_court`) and agencies such as licensing boards, with provenance on each contact. Records-officer channels fit there as contacts of an agency or office type. They are not a separate table.

Staff directories as open data exist too, for example Seattle's [SDCI employee contact list](https://data.seattle.gov/d/yb5c-ur9z) (names, titles, phone, email, supervisor). These are person-level. lexflow should take only the department's office channel and link the directory.

---

## 7. Recommendation

### 7.1 Ingest, link, or leave alone

| Class of record | Decision | Why |
|---|---|---|
| Census ASPEP individual-unit data (employees, payroll, FTE by function) | **Ingest**, keyed on `gov_id` | Covers every government. Public domain. Already aggregate. Needs no key |
| Pay scales and classifications (§6.2) | **Ingest** | Not about people. Powers fee estimates and "what does a records clerk earn here" |
| Headcount and budgeted positions by agency and title (§6.3) | **Ingest** | Aggregate by construction |
| City and county payrolls (§4) | **Ingest only aggregates computed on the publisher's server**, by government × agency × title × year, with suppression (§7.3). Never the rows | Names, IDs and demographics never reach lexflow, Turso or the wiki |
| State payroll search tools (VA, IL, WA, NC, FL) | **Link only** | Person-level, mostly without a bulk API. Florida forbids crawlers. Washington's bulk file needs an emailed request by a person |
| Records-officer lists (§6.4) | **Ingest the office channel** (role, office mailbox, portal, office line) through the review queue. **Link** the list for names | Official role contacts are in scope. Names of individual officers are person-level |
| Staff directories with names | **Link only** | Person-level |
| Aggregators (§5) | **Do not use** | Their terms forbid lexflow's use, or they block clients. They are not official sources either |
| Demographics, age, birth year, hire dates, IDs, benefit choices, home addresses | **Never ingest**, even where public by statute | Re-identification risk, and nothing in an answer needs them |

### 7.2 Aggregate on the publisher's server

Both main APIs can return grouped statistics, so lexflow never downloads a row about a person. Both were tested read-only on 10 October 2026:

```text
# Socrata (SoQL): Chicago, count, mean and median by department or title
GET https://data.cityofchicago.org/resource/xzkq-xp2w.json
    ?$select=department, count(*) AS n, avg(annual_salary) AS mean_salary
    &$group=department&$order=n DESC
# -> [{"department":"CHICAGO POLICE DEPARTMENT","n":"12235","mean_salary":"118224.7..."}, ...]
# median(annual_salary) also works (tested for Chicago Public Library titles)

# ArcGIS REST: DC, count and mean by agency
GET https://maps2.dcgis.dc.gov/dcgis/rest/services/DCGIS_DATA/Government_Operations/MapServer/35/query
    ?where=1=1&groupByFieldsForStatistics=DESCRSHORT&f=json
    &outStatistics=[{"statisticType":"count","onStatisticField":"OBJECTID","outStatisticFieldName":"n"},
                    {"statisticType":"avg","onStatisticField":"COMPRATE","outStatisticFieldName":"mean_rate"}]
# -> [{"DESCRSHORT":"DCPS","N":19820,"MEAN_RATE":82280.4}, ...]
```

These queries used means only to check that grouping works on the publisher's server. lexflow publishes no mean (a mean times its headcount is a sum, and two nested sums that differ by one person subtract to that person's exact pay), and no minimum or maximum (each is always one person's pay). What it does publish is in payroll-plan.md §6.1.

Caveats found while testing:

* **Pay basis is mixed.** DC's `COMPRATE` mixes hourly and annual rates, so the DPW mean came out implausibly low (under $30,000). Chicago fills `annual_salary` only for salaried staff. Seattle publishes hourly rates only. Each source needs a pay-basis filter, for example `$where=salary_or_hourly='SALARY'`. The pay basis is stored with every statistic.
* **Medians are not everywhere.** SoQL `median()` worked. ArcGIS `percentile_cont` was refused by DC's MapServer layer, although the layer advertises percentile support. Where percentiles are refused, publish headcounts only. Do not fall back to a mean, minimum or maximum (see above). Counts by pay band would need the same checks as quartiles, because for a small group they say what its members earn.
* **CKAN (Houston)** exposes `datastore_search`. Its grouping SQL endpoint may be disabled, and was not tested. Houston's yearly CSV would have to be aggregated in memory and discarded. Because of §7.3, it is better skipped until a grouped query is confirmed.
* **Socrata throttles anonymous clients** by IP ([app tokens](https://dev.socrata.com/docs/app-tokens.html)). A handful of grouped queries per dataset per year stays far below any limit. An app token could be added as an optional `.env` key.
* **No calls at answer time.** The aggregates are fetched once, by the operator, in the Setup step. A user's question never triggers a request to a payroll portal, so no third party learns what a user asked about.

### 7.3 Suppression and re-identification

* **Superseded: a minimum cell size of 5 is not enough.** This note first proposed storing a mean, median, minimum and maximum for any group of 5 or more. Verification showed why that fails, and the plan replaced it ([payroll-plan.md](payroll-plan.md) §6.1):
  * a group's minimum and maximum are always one person's pay, however large the group;
  * with linear-interpolated quartiles, a group of 5 has the 2nd, 3rd and 4th person's pay as its quartiles;
  * a mean times its headcount is a sum, so the means of a group and of the same group less one person give that person's exact pay;
  * a similar subtraction of medians can recover one person's pay, between a title and its agency or between two years of one group.

  The plan publishes a headcount from 5 and rounded quartiles only for 11 or more people on one pay basis. It never publishes a figure that equals the exact pay of 1 to 10 people, or one that 1 to 4 people's pay lies within half a rounding step of (so no figure pins down fewer than 5 people's pay). Nor does it publish two groups that differ by 1 to 10 people, pay for more than one period per fetch, or a pay group whose headcount is within 10 of one published from an earlier release. It publishes no pay at all from a source that may list one person more than once, since its counts are then counts of rows. It never publishes a mean, minimum, maximum or sum. Below that, the answer shows the headcount and the pay-scale range for the title, with a link to the official payroll. One "Records Manager" in a small town is one person, and any statistic of their pay is their pay.
* **No quasi-identifiers.** Houston's "anonymized" file pairs a hashed ID with birth year, gender, race, department and exact position dates. That combination identifies most people in a small department. LA City adds gender and ethnicity to names. Virginia Beach pairs position IDs with hire dates. Montgomery County adds gender. lexflow drops all of these columns, and it never groups by them. That includes NYC's Local Law 18 table, where race × gender × pay band cells within one agency are often tiny.
* **Coarse titles.** Group by the publisher's title or job class. Small titles still count toward their agency's and government's roll-ups, and the plan's differencing rule keeps a roll-up from being subtracted back down to them.
* **Separated employees and protected people.** Washington withholds names of domestic-violence victims, DC lets Address Confidentiality Program participants keep their information out, and Seattle notes exclusions "for vulnerable populations". Grouped statistics never reveal which rows were withheld. That is one more reason not to copy rows.

### 7.4 Link only, and say why

For person-level questions, an answer shows the official search and the statute, for example:

> Salaries of DC government employees are public (D.C. Code § 2-536(a)(1)). Search them in DC's [public employee salary data](https://opendata.dc.gov/datasets/DCGIS::dc-public-employee-salary).

Link targets come only from the official sources in §3 and §4.

### 7.5 Users of the lab

* **Nothing is collected by default.** The Setup step reads public aggregates. It sends no information about the operator or any user.
* **A user's process data stays on their machine.** Fee estimates are computed locally from the stored pay scales. The questions people ask, and the records they plan to request, are not sent anywhere.
* **Sharing is opt-in and anonymised.** The aggregates can be pushed to Turso like any other table, because they are public data about governments. The `sync` step needs no new rule for them. Anything a user adds stays local unless they push it explicitly: a corrected records mailbox, or a note that an office answered in 3 days. Before sharing, it is reduced to the government, the office and the fact, with no user identifier.

### 7.6 Shape of the data (a sketch, superseded by payroll-plan.md §2)

The prototype went in `lexflow/payroll/`, and its table is sketched in payroll-plan.md §2. The pay columns below follow the plan's rules, not this note's first draft, which had a mean, median, minimum and maximum. Nothing in `lexflow/ask/` or `lexflow/extract/` changes:

```sql
CREATE TABLE IF NOT EXISTS workforce_stats (
  gov_id TEXT NOT NULL,            -- lexflow / Census 14-digit ID
  agency TEXT NOT NULL,            -- publisher's department name, or '*' for the whole government
  agency_key TEXT,                 -- lexflow:agency:... once the entities plan exists
  title TEXT NOT NULL,             -- publisher's title or class, '*' for all, or an ASPEP function code
  year INTEGER NOT NULL,
  measure TEXT NOT NULL,           -- headcount | fte | budgeted_positions | base_pay | gross_pay | payroll_march
  pay_basis TEXT,                  -- annual | hourly | monthly | none
  n INTEGER,                       -- people or positions in the cell; NULL under 5
  p25 REAL, median REAL, p75 REAL, -- rounded; NULL unless payroll-plan.md §6.1 allows them
                                   -- (never a mean, minimum or maximum: see §7.3)
  source TEXT NOT NULL,            -- census-aspep-2025 | socrata:data.cityofchicago.org/xzkq-xp2w | ...
  source_url TEXT NOT NULL,
  licence TEXT,
  retrieved_at TEXT NOT NULL,
  PRIMARY KEY (gov_id, agency, title, year, measure, source)
);
CREATE TABLE IF NOT EXISTS pay_scales (
  jurisdiction TEXT NOT NULL,      -- va | dc | ... or a gov_id for a city or county schedule
  schedule TEXT NOT NULL,          -- e.g. DBM standard, DCHR non-union DS, SAO schedule B
  grade TEXT NOT NULL, step TEXT NOT NULL DEFAULT '',
  min REAL, max REAL, pay_basis TEXT NOT NULL,
  effective TEXT, source_url TEXT NOT NULL, retrieved_at TEXT NOT NULL,
  PRIMARY KEY (jurisdiction, schedule, grade, step, effective)
);
```

Records-office channels go into the existing `contacts` table with `question='records'` and `kind` set to `email`, `page`, `phone` or `office`. The label names the role ("FOIA officer, Department of X"), never a person. The source is the official list. The `person` kind that `contacts.import_csv` accepts today should not be used for this.

---

## 8. Where this ties in: the Setup page

This belongs on the Setup checklist as **one optional step**, with its sources credited on its card, like the other steps in [credits-research.md](credits-research.md). It does not need its own page. Answers and place pages then show the derived facts (fee range, office size, records-office channel) with links to the official sources.

A possible card (not implemented; `lexflow/pipeline/steps.py` is not edited by this note):

| Field | Value |
|---|---|
| `id` | `workforce` |
| `title` | Load public-employee numbers and records offices |
| `why` | Headcount and payroll for every government (Census ASPEP), pay scales for each state, and aggregate pay by agency and title from city and county open data, computed on the publisher's server. No names are downloaded. Used for records-fee estimates and office sizes. Records-office mailboxes from official FOIA and PIA lists go to review before they are shown. |
| `level` | `optional` |
| `needs` | `["governments"]` |
| `params` | `["states"]` |
| `cost` | One 10.9 MB Census download. A few grouped queries per city dataset. Seconds per state |
| status | `done` when a `scans` row with `source='workforce'` exists for each loaded state (as `st_crawl` does), with detail "N governments with headcount; M with pay by title; K records offices" |

Suggested "Sources" line for the card:

> Sources: U.S. Census Bureau, Annual Survey of Public Employment & Payroll 2025 (public domain). State pay scales from each state's personnel office. City and county pay aggregates from their open-data portals (NYC, Chicago, Cook County, Los Angeles, Los Angeles County, San Francisco, Seattle, Baltimore, Montgomery County, Miami, Miami-Dade, Charlotte, Norfolk, Virginia Beach; licences as each portal states). Records-officer lists from the Virginia FOIA Council, the Maryland Attorney General and the DC government. Person-level records are linked, never copied.

Order with the other steps: after `contacts` and before `score`. A records-office mailbox from a state list can then raise a government's contact level once it has been reviewed.

---

## 9. Open questions and things not verified

1. **The ASPEP 2025 ID column.** Only the 2011 layout was read. The 2025 ZIP was not downloaded. Check that its IDs match `gov_id` before relying on the join.
2. **California GCC** returned 403 to automated clients during this survey, so the raw-export column list and its current terms were not read. The no-names statement comes from the Controller's FAQ, quoted in search results. At verification the site had moved to `gcc.sco.ca.gov`, which answered HTTP 200 with a robots.txt that allows the research client. Its terms are still unread: download by hand, or ask the Controller's office whether automated access is allowed.
3. **Florida Has a Right to Know.** Its robots.txt was read on 10 October 2026. One page request went out in the same batch, and nothing from it was parsed or kept. The fields listed come from launch coverage, not from the page.
4. **Terms not re-read during this survey:** NYC Open Data (the old terms URL returns 404), the Chicago data portal (403 to the fetcher), data.ny.gov, the NC State Controller's disclaimer, and Virginia Beach's "Terms of Use". Since then two were read (payroll-plan.md §6.2). Chicago's require a set disclaimer, let the City demand that a use stop, and contain an indemnity, so Chicago is not fetched. The NC State Controller allows non-commercial copying, unaltered and with a citation, so a link fits. The others are still unread and must be read before the first load.
5. **Washington's bulk file** needs an emailed request that gives a name and an email address. That is a decision for the operator, not something to automate. lexflow does not need it if it uses OFM's salary schedules and the Census data.
6. **The Texas Tribune's "no linking" clause** is unusual. If linking matters, ask the Tribune. The official route (a PIA request to the Comptroller) is enough for lexflow's answers.
7. **Fee estimates are estimates.** Each body sets its own fee schedule (Washington requires a published one, RCW 42.56.120). Where a published schedule exists, it wins over a pay-scale estimate, and lexflow should say so in the answer.
8. **Freshness.** The DC open-data snapshot is from September 2024, Cook County's payroll stops in 2018, and Dallas's registry in 2019. The `retrieved_at` and source year must show in the answer. Stale sources should drop to "link only".
9. **Link check.** Every link in this note was requested once on 10 October 2026 (HEAD, or a 1 KB ranged GET). Some hosts refuse automated clients even though the pages exist and were read another way. These are `leginfo.legislature.ca.gov` (403), `nysenate.gov` (403 to HEAD; the page was read), `regulations.justia.com` (403; the text came from search results), `texastribune.org` and `bls.gov` (403 to HEAD; both pages were read), `illinoiscomptroller.gov` (500 to HEAD; the page was read), and `ilga.gov`, whose certificate chain fails without the Windows certificate store. The California and Illinois statute links are the publisher URLs that Open US Law keeps with each section. Florida's payroll search, Open Payrolls and the California Controller's site were not re-requested, for the reasons above.

## 10. Sources (all opened on 2026-10-10)

Statutes, in the publishers' own text: Virginia Code §§ [2.2-3704](https://law.lis.virginia.gov/vacode/2.2-3704/), [2.2-3704.2](https://law.lis.virginia.gov/vacode/2.2-3704.2/), [2.2-3705.1](https://law.lis.virginia.gov/vacode/2.2-3705.1/), [42.1-85](https://law.lis.virginia.gov/vacode/42.1-85/). D.C. Code §§ [2-532](https://code.dccouncil.gov/us/dc/council/code/sections/2-532), [2-536](https://code.dccouncil.gov/us/dc/council/code/sections/2-536). Md. General Provisions §§ [4-101](https://mgaleg.maryland.gov/mgawebsite/Laws/StatuteText?article=ggp&section=4-101&enactments=false), [4-206](https://mgaleg.maryland.gov/mgawebsite/Laws/StatuteText?article=ggp&section=4-206&enactments=false), [4-311](https://mgaleg.maryland.gov/mgawebsite/Laws/StatuteText?article=ggp&section=4-311&enactments=false), [4-331](https://mgaleg.maryland.gov/mgawebsite/Laws/StatuteText?article=ggp&section=4-331&enactments=false), [4-336](https://mgaleg.maryland.gov/mgawebsite/Laws/StatuteText?article=ggp&section=4-336&enactments=false), [4-503](https://mgaleg.maryland.gov/mgawebsite/Laws/StatuteText?article=ggp&section=4-503&enactments=false). Tex. Gov't Code [ch. 552](https://tcss.legis.texas.gov/resources/GV/htm/GV.552.htm) and [§ 2052.103](https://tcss.legis.texas.gov/resources/GV/htm/GV.2052.htm#2052.103). Cal. Gov. Code §§ [12463](https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=GOV&sectionNum=12463.), [53891](https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=GOV&sectionNum=53891.), [53892](https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=GOV&sectionNum=53892.), [7927.700](https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=GOV&sectionNum=7927.700.). Fla. Stat. §§ [119.01](http://www.leg.state.fl.us/statutes/index.cfm?App_mode=Display_Statute&URL=0100-0199/0119/Sections/0119.01.html), [119.071](http://www.leg.state.fl.us/statutes/index.cfm?App_mode=Display_Statute&URL=0100-0199/0119/Sections/0119.071.html), [215.985](http://www.leg.state.fl.us/statutes/index.cfm?App_mode=Display_Statute&URL=0200-0299/0215/Sections/0215.985.html), [110.2035](https://www.flsenate.gov/laws/statutes/2024/110.2035). N.Y. Public Officers Law [§ 87](https://www.nysenate.gov/legislation/laws/PBO/87). 5 ILCS 140/[2.5](https://www.ilga.gov/ftp/ILCS/Ch%200005/Act%200140/000501400K2.5.html), [3.5](https://www.ilga.gov/ftp/ILCS/Ch%200005/Act%200140/000501400K3.5.html), [4](https://www.ilga.gov/ftp/ILCS/Ch%200005/Act%200140/000501400K4.html), [6](https://www.ilga.gov/ftp/ILCS/Ch%200005/Act%200140/000501400K6.html), [7](https://www.ilga.gov/ftp/ILCS/Ch%200005/Act%200140/000501400K7.html). RCW [42.56.120](https://apps.leg.wa.gov/rcw/default.aspx?cite=42.56.120), [42.56.230](https://apps.leg.wa.gov/rcw/default.aspx?cite=42.56.230), [42.56.250](https://apps.leg.wa.gov/rcw/default.aspx?cite=42.56.250), [42.56.580](https://apps.leg.wa.gov/rcw/default.aspx?cite=42.56.580). N.C. Gen. Stat. [126-23](https://www.ncleg.gov/EnactedLegislation/Statutes/HTML/BySection/Chapter_126/GS_126-23.html), [132-6.2](https://www.ncleg.gov/EnactedLegislation/Statutes/HTML/BySection/Chapter_132/GS_132-6.2.html), [153A-98](https://www.ncleg.gov/EnactedLegislation/Statutes/HTML/BySection/Chapter_153A/GS_153A-98.html), [160A-168](https://www.ncleg.gov/EnactedLegislation/Statutes/HTML/BySection/Chapter_160A/GS_160A-168.html). 21 NYCRR [1401.2](https://regulations.justia.com/states/new-york/title-21/chapter-xxv/part-1401/section-1401-2) (Justia reprint). Case: [IFPTE Local 21 v. Superior Court (Cal. 2007)](https://scocal.stanford.edu/opinion/internat-prof-tech-engineers-v-super-ct-33771). Guidance: Maryland Attorney General, [PIA Manual](https://oag.maryland.gov/resources-info/Pages/pia-manual.aspx), 20th ed. (October 2026): p. 1-9 (salaries are public records), p. 3-16 (salaries, bonuses and awards may not be withheld as personnel records; benefit choices must be), p. 7-2 (fees: prorated salary, no benefits, lowest-paid capable employee).

Data, tools and lists: the dataset links in §§3–6 above. Census: [ASPEP](https://www.census.gov/programs-surveys/apes.html), [2025 tables](https://www.census.gov/data/tables/2025/econ/apes/annual-apes.html), [ID layout](https://www2.census.gov/programs-surveys/apes/technical-documentation/file-layouts/2011/gov-id-layout-11.csv), [govsemp API](https://www.census.gov/data/developers/data-sets/govsemp.html). Socrata: [app tokens](https://dev.socrata.com/docs/app-tokens.html).
