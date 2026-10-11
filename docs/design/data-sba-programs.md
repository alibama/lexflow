# SBA loans and other business programs: data sources

Status: research and design only, 2026-10-10. Nothing was downloaded, built or changed in the code. This note is the
only file written. **Corrected the same evening** where [verify-data-expansion.md](verify-data-expansion.md) found
errors: the NES path (W1), FOIA access through the DKAN datastore instead of streamed CSVs (W6), the `ProjectCounty`
convention, and third-party lenders who may be people (M2). See [data-expansion.md](data-expansion.md) for the
revision's checks.

The question behind it: what data would let lexflow answer questions about SBA loans and other business-finance
programs, at state and local level, for VA, DC, MD, TX, CA, FL, NY, IL, WA and NC? The three test questions are:

* "What SBA loans can I get to open a restaurant in Charlottesville, and who can help me apply?"
* "Which lenders made SBA loans in my county?"
* "Is my business small under SBA rules?"

How the survey was done:

* Every request was a read-only GET or HEAD; no POST was sent. USAspending's and Grants.gov's search endpoints are
  POST, so only their documentation and GET endpoints were read. The User-Agent was
  `lexflow-research/0.1 (https://github.com/alibama/lexflow)`. Requests to one host were spaced at least 1 s apart.
  No account was created and no API key was requested.
* No data file was downloaded. File sizes come from HEAD requests. Three CSVs were checked by a range read of at
  most 1 KB: for the two SBA loan files only the **header line** was kept and printed (§3.1), so no borrower row
  reached this note; the CDFI Fund awards file shows organisations only (§3.13). Data dictionaries, API
  documentation, one SBA notice PDF and small API samples (one to four rows, or a count) were read, as the brief
  allows.
* Several sites answered this client with a bot check or a 403: America's SBDC, SCORE, the Virginia SBDC network,
  USDA Rural Development (`rd.usda.gov`), EDA (`eda.gov`) and `data.commerce.gov`, and the eCFR's HTML pages (its
  API still answered). They were not retried with another client. What this note says about them is marked
  **unverified**.
* Scope rules followed: organisations and official office channels only. The note names no individual and
  reproduces no email address or phone number, even where a source lists a named staff member. Borrowers in loan
  data appear only as aggregates (§5).
* This is not legal advice. Licensing questions are listed for counsel in §6; none is decided here.

Related plans: entity keys and contacts follow [entities-contacts.md](entities-contacts.md); the aggregation rules
follow [payroll-plan.md](payroll-plan.md) §6.1; the forms registry is `fixtures/forms/forms.json`
([forms-plan.md](forms-plan.md)).

---

## 0. Key decisions proposed

| # | Decision | Why |
|---|---|---|
| B1 | **Rules first, then numbers.** The first build is a searchable *rules corpus* (13 CFR parts 120, 121, 123, 126, 130, 131 from the eCFR API, and SOP 50 10 8.1), then the size-standard DMN, then the loan aggregates. | Two of the three test questions ("which loan", "am I small") are answered by rules, not data. The rules are small (about 1.5 MB of regulation text) and public domain. |
| B2 | **Loan data enters only as aggregates.** lexflow reads an allowlist of FOIA columns. Borrower name, street, city and ZIP are never read into a row (as payroll P2). | The 7(a) and 504 FOIA files name every borrower, and many borrowers are sole proprietors (`BusinessType` = Individual). |
| B3 | **Lenders, CDCs, CDFIs and resource partners are entities**, keyed in the entities plan's spelling (D2), with office channels only. | They are organisations, and the answer to "who can help" is an entity with a contact. |
| B4 | **Places get designations, not scraped lists.** HUBZone and Opportunity Zone status is stored per census tract and county; branch counts per county come from FDIC. | These attach to the 14-digit `gov_id` through `governments.county_fips` and `place_fips`. |
| B5 | **No scraping of partner locators.** SBDC, SCORE and Women's Business Center lists are curated by hand for the 10 states, or obtained from SBA by request. | Their sites block automated clients, and the AWBC terms forbid compiling a directory (§3.7). |
| B6 | **State and local programs are found from three verified anchors**: Treasury's SSBCI program table, the statute indexes lexflow already has, and state open-data portals (§3.19). | All three are machine-readable and official. A web crawl of agency pages is the fallback, not the method. |
| B7 | **One optional Setup step, `business-programs`**, introduces, credits and refreshes these sources. No new page. | The pattern every outside dataset in lexflow follows (payroll P1). |

---

## 1. The short version

| Source | What it answers | Access | Size | Licence | Priority |
|---|---|---|---|---|---|
| eCFR API: 13 CFR 120, 121, 123, 126, 130, 131 | Size standards, loan eligibility, loan limits, HUBZone, SBDC and WBC rules | REST, no key | ~1.5 MB text | US government work | **now** |
| SBA SOP 50 10 8.1 | 7(a) and 504 lending rules in force from 2026-10-01 | one .docx | 1,072 KB | SBA: public domain | **now** |
| SBA 7(a) and 504 FOIA loan data | Loans by county, lender, industry, year | 6 CSVs, quarterly | 1.01 GB in all | US Government Works | **now** (aggregated) |
| SBA district offices page | The SBA office for each place | HTML | 1 page | public domain | **now** |
| Treasury SSBCI program table | Every state's SSBCI loan, guarantee and equity programs | HTML table | 211 rows | US government work | **now** |
| FDIC BankFind API | Banks and branches per county; joins FOIA lenders | REST, no key today | ~30,500 branches in the 10 states | not stated (federal) | **now** |
| HUBZone tracts and counties (SBA GeoServer WFS) | Is this address or tract a HUBZone | WFS, undocumented | 7,047 tracts in the 10 states | not stated (federal) | **next** |
| Opportunity Zone list (CDFI Fund) | Is this tract an Opportunity Zone (current round) | one .xlsx | 277 KB | not stated (federal) | **now** |
| Census CBP 2023, NES 2024 | How many businesses of this kind are here | bulk ZIP (the API now needs a key) | 12 MB + 4.4 MB (county) | Census: public | **now** |
| SBA forms 1919, 413, 1244 | The forms a borrower fills in | PDF | small | public domain | **now** |
| SBA CDC and microlender lists | Who makes 504 loans and microloans in this state | HTML, paginated | ~212 CDCs, ~16 pages of microlenders | public domain | **next** |
| CDFI Fund: certified list, awards CSV | Community lenders here | .xlsx, .csv | 151 KB + small | not stated (federal) | **next** |
| SBIR/STTR award data | Federal R&D awards to firms here | bulk CSV (API down) | 92 MB (no abstracts) | not stated (federal) | **next** |
| USAspending API | Federal loans and grants by county and program | REST POST, no key | query-sized | public | **next** |
| SBA disaster loan data | Disaster loans by ZIP and county | .xlsx per year, FY2000 to FY2022 | 2.2 MB (FY22) | US Government Works | **next** |
| State open-data portals (MD, NY found) | State program awards and local loan funds | Socrata API | dataset-sized | varies | **next** |
| Grants.gov (search2, XML extract) | Open federal grants for small businesses | POST API / daily ZIP | 78 MB ZIP | HHS terms, accepted by use | **next**, after the user accepts the terms |
| USDA RD business programs | Rural guarantees and relending | via USAspending; regs via eCFR | — | federal | **later** (site blocked this client) |
| SAM.gov Assistance Listings | Program descriptions for every federal program | API key required | — | federal | **later** |
| SBA 7(a)/504 monthly activity reports | Current-year approvals by lender | .xlsx monthly | 2.5 MB (7(a) lenders) | US Government Works | **later** |
| EDA revolving loan fund list | Local revolving loan funds | .xlsx (unverified) | unknown | federal | **later** (site blocked this client) |
| PPP, COVID EIDL, RRF, SVOG loan-level files | Pandemic-era history | CSV | large | US Government Works | **avoid** |
| SCORE, SBDC, AWBC locators | Partner offices | JS or bot-protected sites | — | private terms | **avoid** scraping; curate instead |

**Verdict.** lexflow can answer all three test questions with public-domain federal data, and none of it needs an
API key. The rules (13 CFR and the SOP) are the cheapest and most valuable part. The FOIA loan files are the only
way to answer "which lenders lend here", and they need the aggregation rules in §5 because they name sole
proprietors. The weakest link is "who can help me apply": SBA no longer serves a machine-readable resource-partner
list (its old offices JSON endpoint now returns 404), and the partner networks' own sites block automated
clients. That part needs a small curated table per state, or a data request to SBA.

---

## 2. The three test questions, end to end

### 2.1 "What SBA loans can I get to open a restaurant in Charlottesville, and who can help me apply?"

| Part of the answer | Source | Verified fact used |
|---|---|---|
| Am I small? | 13 CFR 121.201 | NAICS 722511, Full-Service Restaurants: **$11.5 million** average annual receipts. |
| Or, for 7(a) and 504 only | 13 CFR 121.301(b)(2) | Tangible net worth not over **$20 million** and average net income after tax over the last two years not over **$6.5 million**, affiliates included. |
| Basic eligibility | 13 CFR 120.100 | Operating business, for profit, in the US, small, able to show a need for the credit. |
| Which products | 13 CFR 120.151, 120.931, 120.707 | 7(a): up to **$5,000,000** per loan. 504: **$5,000,000** per borrower, or $5,500,000 for listed project types. Microloans: working capital, supplies, furniture, fixtures and equipment; SBA's lender page says **$50,000 or less**. |
| How lending works now | SOP 50 10 8.1, effective **2026-10-01** | Sections A (core), B (7(a)), C (504). |
| The forms | SBA Form 1919 (effective 2025-03-19), Form 413 (2025-02-13), Form 1244 for 504 | Pages on legacy.sba.gov. |
| Who lends here | 7(a) FOIA, aggregated to Charlottesville city (county FIPS 51540) and Albemarle County (51003), `NaicsCode` 7225xx | Built in the prototype (§7). |
| Which banks have branches here | FDIC BankFind | 43 offices with city "Charlottesville" in the 2026-10-09 index, some in Albemarle County (`STCNTY` 51003). |
| SBA office | SBA district offices | The Virginia District Office (Richmond) serves Virginia except Arlington, Fairfax and Loudoun counties and the cities of Alexandria, Fairfax and Falls Church. |
| State programs | Treasury SSBCI table | 5 Virginia SSBCI programs, run by the Virginia Small Business Financing Authority (VSBFA), two of them through the Virginia Innovation Partnership Corporation. |
| State law behind them | lexflow's Virginia statute index | Va. Code § 2.2-2280 (VSBFA created), § 2.2-1616 (Small Business Investment Grant Fund), § 2.2-2311.1 (Small, Women-owned, and Minority-owned Business Loan Fund). |
| Local programs | City of Charlottesville | "Cville Match" matches SBIR, STTR, VIPC and Virginia Jobs Investment Program awards, up to $25,000 per company per grant, funded by the Charlottesville Economic Development Authority. It does not fit a restaurant; the answer should say so rather than list it. |
| Place context | HUBZone WFS; CBP; NES | 4 Charlottesville tracts are HUBZone-qualified (51540000201, …202, …501, …600). Restaurant counts come from CBP 2023 and NES 2024 (prototype). |
| Who helps, free | SBA resource partners | The Virginia SBDC network, SCORE, a Women's Business Center and a VBOC: **to be curated, not verified here** (their sites blocked this client). |
| No grants to start a business | sba.gov grants page | "SBA does not provide grants for starting and expanding a business." |

### 2.2 "Which lenders made SBA loans in my county?"

The 7(a) FOIA file carries `BankName`, `BankFDICNumber`, `BankNCUANumber`, `LocationID`, `ProjectCounty`,
`ProjectState`, `ApprovalFY` and `GrossApproval` on every loan; the 504 file carries `CDC_Name` and
`ThirdPartyLender_Name` (which can name a private person, so it is shown only under §5 rule 7). Grouped by county,
year and lender (§5) this answers the question directly: for each
lender with at least 5 loans in the county in the last five fiscal years, the count, and a median loan size where
at least 11 loans share the cell. `BankFDICNumber` is the FDIC certificate number, so each bank links to BankFind and
to its branches in the same county (`STCNTY`).

### 2.3 "Is my business small under SBA rules?"

A DMN table over 13 CFR 121.201 (1,102 table rows in the 2026-10-07 eCFR text, read through the API) plus the
alternative test in 121.301(b) for 7(a) and 504 loans. Inputs and outputs are in §4.3. The answer cites the rule
and the NAICS row, and says that SBA, not lexflow, makes size determinations.

---

## 3. Source by source

Effort scale: **S** = up to a day, **M** = 2 to 5 days, **L** = 1 to 2 weeks.

### 3.1 SBA 7(a) and 504 FOIA loan data

| | |
|---|---|
| Publisher | U.S. Small Business Administration, Office of Capital Access |
| Data | <https://data.sba.gov/dataset/7a-504-foia> |
| Documentation | Data dictionary: <https://data.sba.gov/sites/default/files/uploaded_resources/7a_504_foia_data_dictionary.xlsx> (two sheets, read in full). Portal metadata through the DKAN API: <https://data.sba.gov/api/1/metastore/schemas/dataset/items> |
| Licence and terms | Dataset page: "License U.S. Government Works". The DKAN record's licence is <https://www.usa.gov/publicdomain/label/1.0/>. sba.gov: "Government information on SBA.gov is in the public domain", and SBA asks that its information "be given appropriate acknowledgement" ([about the site](https://www.sba.gov/about-sba/open-government/about-the-sba-gov-website/#disclaimer)). |
| Format and access | Six CSVs, plain HTTPS, no key. data.sba.gov is now DKAN on Drupal 11; the old CKAN API (`/api/3/action/...`) returns 404. **The DKAN datastore also holds the two current files** (checked 2026-10-10, evening). The 7(a) FY2020-to-present distribution `fc21a598-913d-5c29-b7c1-1924ce608538` has 388,338 rows and 43 columns, and the 504 FY2010-to-present distribution `47fa0223-0a71-562f-85f1-b4b732400efc` has 117,983 rows and 40 columns; both counts include `record_number` and `asofdate`. They can be queried through `https://data.sba.gov/api/1/datastore/query/{distributionId}` with column projection (`properties`), `conditions`, `groupings` and the aggregates `sum`, `count`, `avg`, `max` and `min` (API spec at `https://data.sba.gov/api/1`). Under load the API may answer 503 ("Datastore queries are temporarily limited due to high server load") with `Retry-After`. |
| Size (HEAD, 2026-10-10) | 7(a) FY1991–1999 146.4 MB; FY2000–2009 318.4 MB; FY2010–2019 255.1 MB; FY2020–present 181.1 MB. 504 FY1991–2009 53.6 MB; FY2010–present 59.4 MB. **1.01 GB in all.** |
| Cadence, vintage | Quarterly, "typically available one month after the quarter has ended". Current files are "as of June 30, 2026" (Last-Modified 2026-07-21). |
| Granularity, fields | One row per loan approved since FY1991. 7(a): 42 columns; 504: 39 (header lines checked, they match the dictionary). Key fields: `Program`, `LocationID` (SBA lender ID), `BankName`, `BankFDICNumber`, `BankNCUANumber`, `GrossApproval`, `SBAGuaranteedApproval`, `ApprovalDate`, `ApprovalFY`, `ProcessingMethod` (18 7(a) codes such as PLP, SBX, CAI; 8 504 codes), `InitialInterestRate`, `TermInMonths`, `NaicsCode`, `FranchiseCode`/`FranchiseName`, `ProjectCounty`, `ProjectState`, `SBADistrictOffice`, `CongressionalDistrict`, `BusinessType`, `BusinessAge`, `LoanStatus`, `JobsSupported`. 504 adds `CDC_Name`, `ThirdPartyLender_Name`, `ThirdPartyDollars`. |
| Caveats | `LoanStatus` EXEMPT means disbursed and not yet closed, "exempt from disclosure under FOIA Exemption 4". `JobsSupported` is lender-reported; SBA "does not review, audit, or validate these numbers". The dictionary still points to SOP 50 10 5 for processing methods. `ProjectCounty` is an upper-case county name, and Virginia's independent cities end in " CITY". A grouped count on the datastore returned "CHARLOTTESVILLE CITY" with 37 7(a) loans (`asofdate` 2026-06-30), so "FAIRFAX" and "FAIRFAX CITY" are told apart by the suffix. |
| Coverage | Every state, so all 10; county via `ProjectCounty`. No microloans (no FOIA file for them). |
| Personal data | `BorrName`, `BorrStreet`, `BorrCity`, `BorrZip` on every row, and `BusinessType` = Individual marks sole proprietors. Charge-off fields describe a borrower's default. Handling: §5. |
| Plugs into lexflow | Place pages (SBA lending here), entities (lenders, CDCs), the Ask place layer (answer_place in `lexflow/ask/pipeline.py`), and the "who lends here" part of the process model. |
| Example question | "Which lenders made SBA loans in Albemarle County?" |
| Effort | **M**: a DKAN query builder with an allowlist, county crosswalk, cells and disclosure checks, tests. |
| Prototype download | No CSV download. Server-side DKAN queries on the two distributions above, naming only allowlisted columns (§5). Grouped `count(record_number)` gives the count cells, and a column-limited projection gives the amounts for medians. The 10 states hold 175,184 7(a) rows and 55,089 504 rows; the query pages are an estimated 35 to 65 MB in all (not measured). They replace `FOIA_7a_FY2020_Present_asof_260630.csv` (181.1 MB) and `FOIA_504_FY2010_Present_asof_260630.csv` (59.4 MB), which are no longer needed. |

### 3.2 SBA 7(a) and 504 activity reports and dashboards

| | |
|---|---|
| Publisher | SBA, Office of Capital Access |
| Data | <https://data.sba.gov/dataset/7a-504-activity-reports-current-month>; year-end editions FY2022 to FY2025; overview at <https://data.sba.gov/oca-datasets> |
| Licence | "U.S. Government Works" (dataset pages) |
| Format, size | Six .xlsx files on `sba-llms-prd-public.sbalenderportal.com`: 7(a) lender report 2.5 MB (Last-Modified 2026-10-08), 504 CDC report 307 KB, congressional district report 124 KB. Tableau dashboards (state and county, lender, microloan lender, disaster by state) need JavaScript and were not read. |
| Cadence | Monthly ("Frequency Monthly") |
| Fields | Not opened (data files). The descriptions: current fiscal-year approvals by 7(a) lender, by 504 CDC, by third-party lender, by congressional district, and by month since 1991. |
| Coverage | National; by lender and district, not by county. |
| Personal data | None described (lender-level). |
| Plugs into lexflow | A cross-check for the FOIA aggregates (state totals per fiscal year), and the only source for current-year microloan lenders (dashboard only). |
| Effort | **S** |
| Prototype download | Not needed for the prototype. |

### 3.3 SBA disaster loan data (and the pandemic files)

| | |
|---|---|
| Publisher | SBA (portal program "Disaster Assistance", identifier SBA-ODA-2022-09-002) |
| Data | <https://data.sba.gov/dataset/disaster-loan-data> |
| Licence and terms | "U.S. Government Works". The page calls it "non-personally identifiable (non-PII) data", "raw, unedited data from SBA's Disaster Credit Management System", and "not intended to be an official Federal report". |
| Format, size | One spreadsheet per fiscal year, FY2000 to **FY2022** (latest). FY22: 2.19 MB; FY18: 222 KB. |
| Cadence | Irregular; metadata last modified 2024-05-08. The COVID EIDL page says more recent data are on USAspending (ALN 59.008, Disaster Assistance Loans). |
| Granularity | "verified loss and approved loan amount totals for both home and business disaster loans, segmented by city, county, zip code and state". |
| Coverage | All states where SBA declared disasters. |
| Personal data | None at this grain, per SBA. |
| Plugs into lexflow | Place pages ("SBA disaster loans here since 2000"), and the disaster-loan process model (13 CFR 123). |
| Example question | "Did businesses in Duval County get SBA disaster loans after the last hurricane?" |
| Effort | **S** |
| Prototype download | `sba_disaster_loan_data_fy22.xlsx` (2.19 MB) from `https://data.sba.gov/sites/default/files/distribution/SBA-ODA-2022-09-002/`. |

**Pandemic-era files: avoid.** PPP (<https://data.sba.gov/dataset/ppp-foia>, 13 CSVs, final as of 2024-09-30), COVID
EIDL and EIDL Advance (through 2020-12-01), RRF and SVOG are loan-level or grant-level, name borrowers, and describe
closed programs. They do not help anyone choose a loan today. If a history line is ever wanted, take it from
USAspending at county level.

### 3.4 Size standards: 13 CFR 121, the SBA table, and NAICS

| | |
|---|---|
| Publisher | SBA (Office of Size Standards); Office of the Federal Register (eCFR); Census Bureau (NAICS) |
| Data | eCFR API, e.g. `https://www.ecfr.gov/api/versioner/v1/full/2026-10-07/title-13.xml?part=121&section=121.201` (send `Accept-Encoding: gzip`; without it the API answers 406). SBA table: <https://www.sba.gov/document/support-table-size-standards> → .xlsx "effective March 17, 2023" (159 KB). data.sba.gov copies and history: <https://data.sba.gov/dataset/small-business-size-standards>. NAICS 2022: <https://www.census.gov/naics/?48967> → `2022NAICS/2022_NAICS_Structure.xlsx`. |
| Documentation | eCFR versioner endpoints used: `/api/versioner/v1/titles.json`, `/versions/title-13.json?part=121`, `/structure/{date}/title-13.json`. The eCFR's HTML developer pages served a bot check to this client and were not read. |
| Licence | Regulations are US government works. The SBA files: "U.S. Government Works". The eCFR's own statement of its legal status was not read in this pass (its HTML pages served a bot check); read it before an answer cites eCFR text as the law. |
| Size | 13 CFR 121.201: 252,894 characters of XML (27 KB compressed), 1,102 table rows. Part 121 in all: 483,168 (eCFR's size figure). |
| Cadence, vintage | Title 13 up to date as of 2026-10-07. 121.201's last substantive change is dated 2023-03-17; Part 121's latest amendment is 2025-02-18. NAICS 2027 is still a proposal (Federal Register notice of 2026-07-13). |
| Fields | NAICS code, industry title, size standard in $ millions of receipts or in employees, footnotes. |
| Coverage | National; the same rule for every state and place. |
| Personal data | None. |
| Broken link found | data.sba.gov's "Small Business Size Standards - NAICS Data (json)" points to `https://www.sba.gov/sites/default/files/data/naics.json`, which now returns 404 (sba.gov moved to WordPress). Do not build on it; parse 121.201 instead. |
| Plugs into lexflow | DMN `is_small` (§4.3), the rules index, and the Ask answer for "am I small". |
| Example question | "I run a residential remodeling company with $30 million in receipts. Am I small?" (236118 Residential Remodelers: $45.0 million.) |
| Effort | **S** for the table parser; **M** with the DMN and tests. |
| Prototype download | 13 CFR part 121 XML from the eCFR API (~0.5 MB); `2022_NAICS_Structure.xlsx` from census.gov (size not reported by HEAD). |

### 3.5 SBA program rules: 13 CFR, SOP 50 10 8.1, and the forms

| | |
|---|---|
| Publisher | SBA; Office of the Federal Register |
| Data | 13 CFR chapter I through the eCFR API. Parts that matter here, with eCFR's size figure: **120 Business Loans** (553,586), **121 Size** (483,168), **123 Disaster Loans** (117,618), **126 HUBZone** (161,405), **130 SBDCs** (98,122), **131 Women's Business Centers** (69,963), 115 Surety Bonds (90,387). SOP 50 10: <https://legacy.sba.gov/document/sop-50-10-lender-development-company-loan-programs> |
| Licence | Federal regulations and SBA documents: public domain (sba.gov statement quoted in §3.1). |
| SOP vintage | **Version 8.1 with Technical Updates, effective 2026-10-01**, .docx, 1,072 KB. SBA Information Notice 5000-880695 (published 2026-08-14; [notice page](https://legacy.sba.gov/document/information-notice-5000-880695-issuance-sop-50-10-81), PDF read): 8.1 applies "to all applications that are issued an SBA loan number on or after that date", and lenders "must continue to use SOP 50 10 8.0 for 7(a) and 504 applications submitted through September 30, 2026". Version 8 took effect 2025-06-01. Three sections: A core requirements, B 7(a), C 504. Older versions back to 2008 are on the same page. |
| Sections used in this note | 120.100 basic eligibility; 120.101 credit not available elsewhere; 120.110 ineligible businesses; 120.130 use of proceeds; 120.151 loan limits ($3,750,000 guaranty, $5,000,000 per 7(a) loan); 120.707 microloan conditions; 120.882 eligible 504 project costs; 120.931 504 limits. |
| Forms | SBA Form 1919, Borrower Information Form (effective 2025-03-19); SBA Form 413, Personal Financial Statement (2025-02-13); SBA Form 1244, Application for Section 504 Loans (2022-11-29, OMB 3245-0071). sba.gov document URLs redirect to legacy.sba.gov. |
| Coverage | National. |
| Personal data | None in the rules. The forms collect personal financial data, so lexflow links to them and never pre-fills them. |
| Plugs into lexflow | The rules index (§4.2), BPMN "Apply for an SBA-guaranteed loan" and the DMN tables (§4.3), forms registry entries (§4.4). |
| Example question | "Can I use a 504 loan for working capital?" (120.882 lists eligible project costs.) |
| Effort | **M**: eCFR XML to sections is simple; the SOP .docx needs heading-based splitting. |
| Prototype download | 13 CFR parts 120, 121, 123, 126, 130, 131 (about 1.5 MB of XML, eCFR API); `SOP 50 10 8.1 Technical Policy Updates effective  10.1.2026.docx` (1,072 KB) from `https://legacy.sba.gov/sites/default/files/2026-10/`. |

### 3.6 Lender Match and lender lists

| | |
|---|---|
| Lender Match | <https://www.sba.gov/lendermatch> → <https://www.sba.gov/loans/lender-match/>. A referral form: "Answer a few questions", "Get matched in two days". **No data and no API.** lexflow should link to it as a step, never submit it. |
| CDC list | <https://www.sba.gov/loans/504-loans/list-of-certified-development-companies/>: name, states served, address, a contact mailbox and phone. 22 pages of 10 (about 212 CDCs). HTML only; SBA's WordPress REST API returned 403. |
| Microlenders | <https://www.sba.gov/loans/microloans/list-of-microlenders/>: the same layout, 16 pages. |
| Licence | sba.gov public domain statement (§3.1). |
| Personal data | Many contact mailboxes and phones belong to named staff. Keep organisation name, states served, address and website; drop the person-level channels (entities plan §5). |
| Lenders from FOIA | Every 7(a) lender in the FOIA data has `LocationID`, and banks have `BankFDICNumber` (→ FDIC BankFind, §3.17) or `BankNCUANumber` (credit unions; NCUA data not surveyed here). |
| Plugs into lexflow | Entities: `lexflow:lender:fdic:<cert>`, `lexflow:lender:ncua:<charter>`, `lexflow:lender:sba:<LocationID>` for non-bank lenders, `lexflow:cdc:<slug>`, `lexflow:microlender:<slug>`, with `serves` = state list. |
| Example question | "Which CDCs make 504 loans in Virginia?" |
| Effort | **S** for the two lists (about 40 page reads, once, at 1 per second); **M** for lender entities joined to FOIA and FDIC. |
| Prototype download | None; page reads only. |

### 3.7 Resource partners and district offices

| | |
|---|---|
| District offices | <https://www.sba.gov/about-sba/sba-district-offices/>, one HTML table. For the 10 states: VA → Virginia (Richmond) and Washington Metropolitan Area; DC → Washington Metropolitan Area; MD → Baltimore and Washington Metropolitan Area; TX → Dallas/Fort Worth, El Paso, Houston, Lower Rio Grande Valley, San Antonio, West Texas; CA → Fresno, Los Angeles, Orange County/Inland Empire, Sacramento, San Diego, San Francisco; FL → North Florida, South Florida; NY → Buffalo, Metro New York, Syracuse; IL → Illinois; WA ("Washington State") → Seattle, Portland; NC → North Carolina. 24 district offices in all. The Virginia district page states its service area in words, naming the excluded counties and cities; that text maps to `county_fips` by hand once. The other district pages were not opened. |
| Partner lists on sba.gov | The resource-partners page lists the **VBOCs** (31 organisations, with links). It does not list SBDCs, SCORE chapters or WBCs; it sends people to the partners' own sites. |
| SBA locator data | The old JSON endpoint `https://www.sba.gov/api/content/search/offices.json`, which third-party portals copied, **returns 404**. The legacy ZIP search still exists at <https://legacy.sba.gov/local-assistance>, with no published API. |
| Partner sites | America's SBDC (`americassbdc.org/find-your-sbdc/`) answered with a JavaScript redirect; SCORE (`score.org/find-location`) with a bot challenge (403); the Virginia SBDC network with 403. Not scraped, and should not be. |
| AWBC terms | The WBC locator (<https://awbc.org/wbc-locator/>, a WordPress store locator) is governed by the AWBC [terms](https://awbc.org/terms-and-conditions/), updated 2025-04-02, which forbid "Systematically retrieve data or other content from the Services" to build a database, and limit content to "personal, non-commercial use or internal business purpose". |
| Rules | 13 CFR 130 (SBDCs) and 131 (WBCs) say what the centres must provide; useful for "what does an SBDC do for free". |
| Plan | Curate one row per SBDC network lead centre and per WBC and VBOC serving each of the 10 states (about 40 to 60 rows), from each organisation's own public page read in a browser, with a review and a `checked` date; or ask SBA's Office of Entrepreneurial Development for an extract (open question; the user would send any such request). Store as entities with office channels. |
| Plugs into lexflow | Entities and contacts; the "who can help" line in every business answer; place pages. |
| Effort | **M** (curation and review). |
| Prototype download | None. |

### 3.8 SBIR and STTR awards

| | |
|---|---|
| Publisher | SBA, through SBIR.gov |
| Data | Bulk: <https://data.www.sbir.gov/mod_awarddatapublic_no_abstract/award_data_no_abstract.csv> (91.6 MB, Last-Modified 2026-10-07) and <https://data.www.sbir.gov/awarddatapublic/award_data.csv> with abstracts (367.6 MB, Last-Modified 2026-01-01). Listed at <https://www.sbir.gov/data-resources>. |
| API | <https://www.sbir.gov/api> documents `https://api.www.sbir.gov/public/api/awards?...` (agency, firm, year, research institution; 100 rows default; offset paging). The page says the APIs "are currently undergoing maintenance", and a test call returned `{"message":"Forbidden"}` (403). |
| Licence | No licence statement found on the data pages. Federal data; counsel to confirm (§6). |
| Fields | From the API page: firm, award title, agency, branch, phase, program, contract, dates, solicitation, topic, award year and amount, UEI, HUBZone/disadvantaged/women-owned flags, employees, company URL and address, **poc_name, poc_phone, poc_email, pi_name, pi_phone, pi_email**, research institution, keywords, abstract. |
| Coverage | All states, by firm address (city, state, ZIP). |
| Personal data | Points of contact and principal investigators are named people with phones and emails: drop them at read time (allowlist). Firms are organisations. |
| Plugs into lexflow | Place pages (federal R&D awards to firms here), and local programs that match SBIR awards (Cville Match in Charlottesville; N.C. Gen. Stat. § 143B-437.80, the North Carolina SBIR/STTR Incentive Program, found in lexflow's NC statute index). |
| Example question | "Are there local matching funds for an SBIR Phase I award in Charlottesville?" |
| Effort | **S** |
| Prototype download | The no-abstract CSV, 91.6 MB. |

### 3.9 HUBZone

| | |
|---|---|
| Publisher | SBA (HUBZone program) |
| Map | <https://maps.certify.sba.gov/hubzone/map/help>: map "updated effective July 2023"; SBA "will not update Qualified Census Tracts and Qualified Non-Metropolitan Counties on the map again until July 2028". Redesignated areas expired on 2026-07-01 (the `qct_r` layer now has 0 features). |
| Data | The map's GeoServer answers OGC WFS: `https://maps.certify.sba.gov/geoserver/ows?service=WFS&request=GetCapabilities` lists layers including `hubzone:qct_e` (qualified tracts, 15,913 features), `hubzone:qnmc_e` (qualified non-metro counties, 990), `hubzone:indian_lands` (587), `hubzone:qct_qda`/`qnmc_qda` (disaster areas), governor-designated areas, and `hubzone:treasury_opportunity_zones` (8,765). `qct_e` fields: `tract_fips`, `county`, `state`, `omb_delineation`, `prior_status`, `current_status`, `status_change`, `redesignated`. Governor-designated areas also as .xlsx on data.sba.gov (as of 2024-11-05). |
| Licence | Not stated. The WFS is the map's own service, **not a published API**: use it gently and ask SBA before relying on it (§6). |
| Size | Qualified tracts in the 10 states: VA 269, DC 65, MD 274, TX 1,339, CA 1,790, FL 838, NY 1,087, IL 708, WA 213, NC 464 (7,047). Without geometry this is well under 2 MB. |
| Coverage | Tract and county level; every place maps to tracts. |
| Personal data | None. |
| Plugs into lexflow | Place pages (HUBZone tracts here), DMN input `in_hubzone` for contracting questions, rules from 13 CFR 126. |
| Example question | "Is my office in Charlottesville in a HUBZone?" (4 qualified tracts in the city; the exact address needs SBA's map, which lexflow should link to.) |
| Effort | **S** |
| Prototype download | WFS `GetFeature` for `qct_e` and `qnmc_e`, `propertyName=tract_fips,county,state,current_status,redesignated`, filtered per state (10 small requests). |

### 3.10 USAspending.gov

| | |
|---|---|
| Publisher | Department of the Treasury, Bureau of the Fiscal Service |
| API | <https://api.usaspending.gov/docs/endpoints>. Search endpoints are **POST** (e.g. `/api/v2/search/spending_by_geography/`, with `geo_layer` = state, county or district and filters for assistance listings and award types; contract read at the API's [GitHub contract](https://github.com/fedspendingtransparency/usaspending-api/blob/master/usaspending_api/api_contracts/contracts/v2/search/spending_by_geography.md)). GET endpoints include `/api/v2/recipient/state/awards/<FIPS>/` and `/api/v2/references/assistance_listing/<2-digit>/`. No key. |
| Programs | Assistance listings confirmed through the API: SBA 59.012 7(a) Loan Guarantees, 59.041 504 Certified Development Loans, 59.046 Microloan Program, 59.008 Disaster Assistance Loans, 59.016 Surety Bond Guarantees, 59.037 SBDCs, 59.043 Women's Business Ownership Assistance, 59.044 Veterans Outreach; USDA 10.768 Business and Industry Guaranteed Loans, 10.767 Intermediary Relending, 10.870 Rural Microentrepreneur Assistance, 10.868 REAP, 10.854 Rural Economic Development Loans and Grants. |
| Caveat: loan amounts | The glossary: the face value of a loan "is not considered spending and is not included in any obligation or outlay figure". Example: Virginia's FY2025 loan awards total $37.5 million across 14,865 awards in `/recipient/state/awards/51/?year=2025`, far below face value. Use the face-value field, not obligations, for loans. |
| Personal data | OMB M-17-04: "Agencies currently report financial assistance records containing PII in summary groups of similar awards at the county level known as 'aggregate records'" ([memo](https://www.whitehouse.gov/wp-content/uploads/legacy_drupal_files/omb/memoranda/2017/m-17-04.pdf)). Awards to individuals are redacted. Business recipients are named. |
| Licence | Not re-checked in this pass; federal spending data. |
| Plugs into lexflow | Place pages (federal loans and grants by county and program, recent years), cross-check of SBA FOIA, the only easy route to USDA RD business programs. |
| Example question | "How much did USDA guarantee for rural business loans in my county last year?" |
| Effort | **S** to **M** |
| Prototype download | None at first; county totals per assistance listing come from small POST queries, which need the user's approval because the brief allowed only GET in research. |

### 3.11 Grants.gov and Simpler.Grants.gov

| | |
|---|---|
| Publisher | U.S. Department of Health and Human Services, Office of Grants (Grants.gov) |
| Data | search2: `POST https://api.grants.gov/v1/api/search2` (no authentication; <https://www.grants.gov/api/common/search2>). Daily XML extract: <https://www.grants.gov/xml-extract>, e.g. `GrantsDBExtract20261010v2.zip`, 78.3 MB. Simpler.Grants.gov's API needs an API key through Login.gov (<https://simpler.grants.gov/developers>). |
| Terms | <https://www.grants.gov/api/terms-conditions>: "Access to or use of the API or its content constitutes acceptance to this Agreement." Required notice: "This product uses the Grants.gov API but is not endorsed or certified by the U.S. Department of Health and Human Services." Use may be limited or blocked. **Using the API accepts terms, so the user must agree first.** |
| Fields | Opportunity number, title, agency, open and close dates, status, ALN list, eligibility codes, funding category and instrument. Eligibility code **23 = Small businesses** (XML extract guide). |
| Coverage | Federal opportunities, national. Most are for governments and nonprofits; SBA says it "does not provide grants for starting and expanding a business". |
| Personal data | None material (agency contacts are office channels). |
| Plugs into lexflow | Ask answers to "are there grants for…": list open opportunities with eligibility 23, and say plainly how few exist. |
| Effort | **S** |
| Prototype download | One daily extract ZIP (78.3 MB), after the terms are accepted. |

### 3.12 SAM.gov Assistance Listings

The catalogue of every federal assistance program (the former CFDA), with eligibility and contacts.
<https://open.gsa.gov/api/assistance-listings-api/>: `https://api.sam.gov/assistance-listings/v1/search`, an
`api_key` is required, and a non-federal user with no SAM.gov role gets **10 requests a day**. Useful later for
program descriptions; not needed now, because USAspending already gives the listing names. **later**, effort S.

### 3.13 CDFI Fund

| | |
|---|---|
| Publisher | Department of the Treasury, CDFI Fund |
| Certified list | <https://www.cdfifund.gov/programs-training/certification/cdfi> → "List of Currently Certified CDFIs", file `CDFI_Cert_List_Manual_9.17.26.xlsx`, 150,742 bytes, "Certified CDFIs as of September 17, 2026". Columns not opened (data file); expected organisation and location fields are **unverified**. |
| Awards | <https://www.cdfifund.gov/awards/state-awards> → `/system/files/2026-09/2026-09-29_state-awards.csv`, columns `Awardee, City, State, Year, Program, Amount` (header read). NMTC public data release FY2025 (2003–2023, updated 2026-08-07) and CDFI Program awardee data releases at <https://www.cdfifund.gov/documents/data-releases>. |
| Terms | Only a disclaimer of endorsement was found. Federal data; counsel to confirm. |
| Coverage | "Certified CDFIs in all 50 states, the District of Columbia, Guam, and Puerto Rico." |
| Personal data | None: awardees and CDFIs are organisations. |
| Plugs into lexflow | Entities (`lexflow:cdfi:<slug>`), the "who else lends" line, place pages. Virginia's CDFI fund is in statute (Va. Code § 36-140.01, in lexflow's index). |
| Example question | "Are there community lenders in Baltimore that lend to startups?" |
| Effort | **S** |
| Prototype download | The certified-list .xlsx (151 KB) and the state-awards CSV (small; size not reported by HEAD). |

### 3.14 State Small Business Credit Initiative (SSBCI)

| | |
|---|---|
| Publisher | Department of the Treasury |
| Data | <https://home.treasury.gov/policy-issues/small-business-programs/state-small-business-credit-initiative-ssbci/capital-program-list-of-programs-and-contacts>: one HTML table, "DATA CURRENT AS OF 8/25/2026", **211 programs in 56 jurisdictions**. Columns: jurisdiction, implementing entity, approved program, type (capital access, collateral support, loan guarantee, loan participation, debt/equity hybrid, equity/venture), administering entities, contact. Also capital-program and technical-assistance summaries per state, and the 2022–2023 annual report. |
| Licence | US government work. |
| The 10 states | VA 5 (VSBFA; venture programs through VIPC), DC 3 (DISB; venture through DMPED), MD 8 (DHCD; Commerce, Meridian Management Group, TEDCO), TX 3 (Office of the Governor, TSBCI), CA 7 (IBank; some through CPCFA, including CalCAP), FL 5 (FloridaCommerce; Florida First Capital Finance Corporation, Florida Opportunity Fund), NY 10 (Empire State Development, e.g. New York Forward Loan Fund II), IL 4 (DCEO, Advantage Illinois; Climate Bank Finance through IFA), WA 5 (Commerce; Evergreen Business Capital, Calvert Impact Capital, CDP), NC 3 (Commerce; Rural Economic Development Center). **53 programs.** |
| Personal data | The contact column holds mailto links, often to named staff: drop it and link to the program page instead. |
| Plugs into lexflow | The state program registry (§3.19, §4.1), entities for implementing and administering bodies, Ask answers. |
| Example question | "Does Texas have a loan guarantee program for small businesses?" |
| Effort | **S** |
| Prototype download | None (one page read). |

### 3.15 USDA Rural Development business programs

| | |
|---|---|
| Publisher | USDA Rural Business-Cooperative Service |
| Programs and rules | 7 CFR 5001 Guaranteed Loans (subparts A–F), 7 CFR 4280 Loans and Grants (A Rural Economic Development Loan and Grant Programs, B Rural Energy for America Program, D Rural Microentrepreneur Assistance Program, E Rural Business Development Grants), 7 CFR 4274 Direct and Insured Loanmaking, all read through the eCFR structure API. Assistance listings in §3.10. |
| Data | `rd.usda.gov` (the Rural Data Gateway and its data-download page) answered **403** to this client. Search summaries describe state and county investment dashboards from FY2012 and a monthly lender-performance view, **unverified**. |
| Route for lexflow | Rules from the eCFR (public domain); county figures from USAspending by assistance listing. |
| Coverage | Rural areas only; eligibility depends on USDA's rural definitions and map (not surveyed). |
| Personal data | Individual recipients are aggregated by USAspending (M-17-04). |
| Example question | "Can a business in a small North Carolina town get a USDA-guaranteed loan?" |
| Effort | **S** (rules) + **S** (USAspending) |
| Priority | **later**, after the SBA rules. |

### 3.16 Opportunity Zones

| | |
|---|---|
| Publisher | Treasury and IRS; list kept by the CDFI Fund |
| Data | <https://www.cdfifund.gov/opportunity-zones> → `designated-qozs.12.14.18.xlsx` (276,974 bytes). The zip on the same page is named for 8,764 zones; the HUBZone GeoServer layer has 8,765 features. |
| Change coming | Treasury opened a **new designation cycle on 2026-07-01**; the nominations "will determine which census tracts are eligible for new investment beginning January 1, 2027", and zones are redesignated every 10 years ([press release](https://home.treasury.gov/news/press-releases/sb0550)). Treasury and the IRS released a list of **25,332 eligible tracts** for nomination, 8,334 eligible for rural benefits. The current list goes stale on 2027-01-01. |
| Licence | Federal; not stated on the page. |
| Granularity | Census tract, as designated in 2018; the IRS page lists "Qualified Opportunity Zone Boundaries Unaffected by 2020 Decennial Census Changes" (Announcement 2021-10). |
| Personal data | None. |
| Plugs into lexflow | Place designations; Ask answers about investors' tax benefits link to IRS pages (tax questions belong with the tax-code work). |
| Effort | **S** now, **S** again in January 2027. |
| Prototype download | `designated-qozs.12.14.18.xlsx`, 277 KB. |

### 3.17 FDIC BankFind

| | |
|---|---|
| Publisher | Federal Deposit Insurance Corporation |
| API | `https://api.fdic.gov/banks/...` (the old host `banks.data.fdic.gov` now answers 301 to it). Docs: <https://api.fdic.gov/banks/docs/>. "Users are currently not required to register and obtain a unique 'key'." JSON or CSV. Endpoints include institutions, locations (branches), history, summary of deposits. |
| Sample | `locations?filters=STALP:VA AND CITY:Charlottesville` → 43 offices; fields used `NAME`, `CERT`, `UNINUM`, `OFFNAME`, `CITY`, `COUNTY`, `STCNTY` (5-digit county FIPS), `ZIP`, `SERVTYPE`. The response named its index `locations_20261009090008`, built 2026-10-09. |
| Size | Branch locations: VA 1,851, DC 178, MD 1,136, TX 6,402, CA 5,539, FL 4,374, NY 4,007, IL 3,628, WA 1,355, NC 2,057 (**30,527**). |
| Licence | No licence statement found on the docs page; counsel to confirm. |
| Personal data | None (institutions and offices). |
| Plugs into lexflow | Lender entities keyed by `CERT` = FOIA `BankFDICNumber`; place pages (branches here); "which of these lenders has a branch near me". |
| Example question | "Which banks in Montgomery County, MD have made SBA loans and have a branch there?" |
| Effort | **S** |
| Prototype download | `locations` for the 10 states, selected fields, paged (about 30,500 rows, a few MB of JSON). |

### 3.18 Census County Business Patterns and Nonemployer Statistics

| | |
|---|---|
| Publisher | U.S. Census Bureau |
| Data | CBP: <https://www2.census.gov/programs-surveys/cbp/datasets/2023/> (`cbp23co.zip` 12 MB, county; `zbp23detail.zip` 15 MB, ZIP; 2025-06-26). **No 2024 CBP folder yet** on 2026-10-10. NES: the 2024 folder holds only `historical-datasets/`, and the county file is <https://www2.census.gov/programs-surveys/nonemployer-statistics/datasets/2024/historical-datasets/nonemp24co.zip> (4,585,934 B, 2026-09-29). The path without `historical-datasets/` returns 404. |
| API | `api.census.gov` now redirects every data request without a key to `missing_key.html`: "A valid key must be included with each data API request." Metadata (`/data/2023/cbp.json`) still opens. The bulk files need no key. |
| Licence | Census data are federal works; the API has its own terms (not re-read). |
| Granularity | County (and ZIP for CBP) × NAICS: establishments, employment, payroll (CBP); nonemployer firms and receipts (NES). Field names and the NAICS vintage of each file are to be read from the files' own record layouts in the prototype. |
| Personal data | None at this grain. |
| Also | SBA Office of Advocacy state and metro small-business statistics 2025 (.xlsx on data.sba.gov, US Government Works). |
| Plugs into lexflow | Place pages (the number of full-service restaurants here, with and without employees), context in Ask answers, denominators for SBA lending per business. |
| Example question | "How many restaurants are there in Charlottesville?" |
| Effort | **S** |
| Prototype download | `cbp23co.zip` (12 MB) and `historical-datasets/nonemp24co.zip` (4.4 MB). |

### 3.19 State and local programs in the 10 states: finding them systematically

No single list exists. Four verified anchors, in order:

1. **Treasury's SSBCI table** (§3.14): every state's federally funded capital programs and the agency that runs
   them. 53 programs in the 10 states. Start here.
2. **The statutes lexflow already indexes.** Most state finance programs are created by statute. A query of the
   existing indexes for sections matching `"small business" AND (loan OR grant OR guarantee) AND (fund OR authority OR
   program)` returns: VA 47, DC 28, MD 42, TX 30, CA 151, FL 36, NY 97, IL 57, WA 37, NC 17. Top hits include
   Va. Code § 2.2-2288 (VSBFA bonds) and § 2.2-1616, D.C. Code § 2-218.75 (Small Business Capital Access Fund) and
   § 2-1210.81 (SSBCI venture capital), Tex. Gov't Code § 481.602 (Small Business Disaster Recovery Loan Program),
   Cal. Gov. Code § 63089.70 (Small Business Expansion Fund), Fla. Stat. § 288.9935 (Microfinance Guarantee
   Program) and § 288.001 (Florida SBDC Network), N.Y. UDA Law § 16-T (small business revolving loan fund), RCW
   43.163.030, and N.C. Gen. Stat. § 143B-437.80. Each hit names a program and usually its administering body:
   that is a registry row with a citation.
3. **State open-data portals.** One Socrata Discovery API query found program-level award data, for example:
   * Maryland Department of Commerce, "Commerce Consolidated Finance Tracker Data" (`opendata.maryland.gov`,
     `cf3i-xdgb`): fiscal year, recipient, program levels, approved amount, loan guarantee amount, jobs, NAICS,
     county, city, ZIP. No licence set on the dataset.
   * Maryland DBM, "State of Maryland Grant and Loan Data: FY2009 to FY2025" (`absk-avps`), public domain, updated
     2026-10-09; Maryland DHCD "Neighborhood Business Works (NBW) FY 2011-2025" (`xhfz-cz2z`).
   * New York Authorities Budget Office, "Local Development Corporations Loans" (`data.ny.gov`, `vp83-gfyz`) and
     "…Grants" (`j5ab-5nj2`): every local development corporation's loans, with fund source, amount, rate, term and
     purpose. **This is a statewide list of local revolving loan funds.** No licence set.
   * City of Chicago, Small Business Improvement Fund projects (`etqr-sz5x`).
   Recipient columns can name sole proprietors: aggregate them as in §5, or keep program-level facts only.
4. **Local governments.** LOCUS ordinance headings and the place layer already find "economic development
   authority" and "loan fund" mentions. The official program page is then found by reading the government's
   website (the existing crawl step). Charlottesville's Cville Match is an example of what this finds.

Two candidate sources could not be opened: the EDA revolving loan fund recipient list (search results point to
`eda.gov/files/rlf/EDA-RLF-Recipients.xlsx`, last modified 2020-03-31 per a catalogue entry; `eda.gov` and
`data.commerce.gov` answered 403) and USDA's Intermediary Relending Program intermediaries. Both are **later** and
**unverified**.

State agency anchors (implementing entity from the SSBCI table; only Virginia's page was opened):

| State | Agency | Checked |
|---|---|---|
| VA | Virginia Small Business Financing Authority, "the financing arm of the Virginia Department of Small Business and Supplier Diversity": direct loans, credit support, venture capital, bonds, grants (<https://sbsd.virginia.gov/vsbfa/>) | opened |
| DC | Department of Insurance, Securities and Banking; Deputy Mayor for Planning and Economic Development | SSBCI table |
| MD | DHCD; Department of Commerce; TEDCO | SSBCI table, open data |
| TX | Office of the Governor (TSBCI) | SSBCI table |
| CA | California Infrastructure and Economic Development Bank (IBank); CPCFA | SSBCI table |
| FL | Florida Department of Commerce | SSBCI table |
| NY | Empire State Development; local development corporations | SSBCI table, open data |
| IL | Department of Commerce and Economic Opportunity | SSBCI table |
| WA | Department of Commerce | SSBCI table |
| NC | Department of Commerce; Rural Economic Development Center | SSBCI table |

---

## 4. How it plugs into lexflow

### 4.1 Three new stores (next step, not built)

| Table | One row per | Key fields |
|---|---|---|
| `programs` | Program (federal, state, local) | `program_id` (`lexflow:program:<scope>:<slug>`), level, administering entity key, type (loan, guarantee, grant, equity, counselling, certification, designation), citations (CFR, statute, SOP section), `inputs` (the DMN variables it needs), official URL, `checked` |
| `program_cells` | (state, county FIPS, fiscal year, program, NAICS sector) and (state, county FIPS, fiscal-year window, lender key) | count, median and quartiles where allowed (§5), source and vintage |
| `place_designations` | (tract or county, designation) | HUBZone status, OZ, redesignated or expiry date, source vintage |

All three attach to governments through `governments.county_fips` and `place_fips` (`lexflow/store/db.py`, table
`governments`). Lenders, CDCs, CDFIs, district offices and resource partners go into the entities plan's tables as
new kinds, keyed in its spelling (D2): `lexflow:agency:us:sba`, `lexflow:office:sba-district:<slug>`,
`lexflow:lender:fdic:<cert>`, `lexflow:cdc:<slug>`, `lexflow:cdfi:<slug>`, `lexflow:partner:sbdc:<slug>`.

### 4.2 Search index: a rules corpus

`lexflow/ask/index.py` builds one SQLite FTS5 file per state from statute parquet (`sec` + `fts`, BM25 with heading
weight). The same schema can hold regulation and guidance sections:

* `data/index/rules_us.sqlite`: 13 CFR parts 120, 121, 123, 126, 130, 131 (and 7 CFR 4280, 5001 later) from the eCFR
  API, one row per section, `citation` = "13 CFR 120.151"; SOP 50 10 8.1 split at its headings, `citation` =
  "SOP 50 10 8.1, Section B, Chapter …".
* `retrieve.fused()` and `choose()` take a state code; a pseudo-state `us` lets the Ask pipeline search the federal
  corpus beside the state's statutes and fuse the two rankings, labelling each section's source type.
* The planner's thesaurus (`lexflow/ask/plan.py`, `THESAURUS`) needs business-finance concept groups: "SBA",
  "7(a)", "504", "microloan", "loan guarantee", "size standard", "HUBZone", "SBDC".
* open-us-law also ships `us_federal_regulations.parquet` (1.45 GB, CC BY-NC 4.0, listed in the local manifest
  `/data/raw/open-us-law/index.json`, v2026.09.1, not downloaded). The eCFR API gives the needed parts in about
  1.5 MB, public domain. Prefer the eCFR.

The same corpus design serves other regulations; the deck-and-shed permit question that statutes could not answer
is a regulation question too.

### 4.3 Process models and DMN

* **BPMN "Apply for an SBA-guaranteed loan"** (federal, `scope = us`): check eligibility and size → choose a product
  → prepare (business plan, Forms 1919 and 413, 1244 for 504) → find a lender (Lender Match, or the lenders active in
  the county) → lender underwrites and submits → SBA approval or delegated approval (`ProcessingMethod` PLP) →
  closing → disbursement. Each step quotes 13 CFR 120 or the SOP, the way state models quote statutes. This needs a
  curated reference model like `curated/va/business.json`, reviewed by Claude, before publication.
* **DMN `is_small`.** Inputs: primary NAICS code; average annual receipts or average employees (as 121.201 sets for
  that code), affiliates included; program (`loan_7a_504` or other); for 7(a) and 504, tangible net worth and
  average net income after tax. Rules: one row per 121.201 code; then the 121.301(b)(2) alternative. Output: small
  yes/no and the rule applied. Measurement periods follow 13 CFR 121.104 and 121.106 (to be encoded from the text,
  not checked here).
* **DMN `which_sba_product`.** Inputs: amount, use of proceeds (working capital, equipment, real estate, refinance,
  export, line of credit), owner occupancy for real estate, for-profit, in the US, ineligible type (120.110), credit
  elsewhere (120.101). Rules from 120.151 (7(a) limit), 120.882 and 120.931 (504), 120.707 and SBA's $50,000
  microloan figure. Output: candidate products with citations.
* These DMN inputs are also how `programs.inputs` links a state program to the same questions.

### 4.4 Forms

Add SBA Forms 1919, 413 and 1244 to `fixtures/forms/forms.json` under a new process `sba-loan`, each tied to its
BPMN step, with the same `verification` block (HTTP status, robots.txt, content type) the registry uses today.
lexflow links to the forms and never fills them: Form 413 is a personal financial statement.

### 4.5 Entities and contacts

* SBA district offices: 24 serve the 10 states; one row each, office channels only, `serves` = county FIPS list
  from each district page's service-area text.
* Resource partners: the curated table of §3.7.
* Lenders: from FOIA (`LocationID`, name) and FDIC (`CERT`, branches); CDCs and microlenders from SBA's lists;
  CDFIs from the CDFI Fund list. Organisation channels only; named staff contacts are dropped.

### 4.6 Place pages

A "Business finance here" block for each county and independent city, and for cities through their county:
SBA lending in the last five fiscal years (counts by program and sector, lenders with at least 5 loans), HUBZone
and OZ tracts, SBA district office, the SBDC centre and other partners serving the area, CDFIs and CDCs serving the
state, bank branches, CBP and NES counts, and state and local programs from the registry.

### 4.7 Ask answers

* Route questions with business-finance concepts to the rules corpus and the place block.
* Every business-finance answer ends with "who can help" (district office, SBDC, SCORE, WBC, VBOC) from entities.
* The not-found text (`lexflow/ask/answer.py`, around line 247: "…regulations, court rules, agency policy,
  contracts or local ordinances, which lexflow does not search yet") becomes specific once the rules corpus exists:
  it can say which corpus was searched and point to the agency.
* Nothing is fetched when someone asks; answers read stored rows, as in the payroll plan (P6).

### 4.8 Setup step

One optional step, `business-programs`, in `lexflow/pipeline/steps.py`'s `STEPS`: introduces the sources, records
credits (`lexflow/pipeline/credits.py`), and refreshes on each source's cadence: FOIA quarterly (August, November,
February, May), activity reports monthly, eCFR and SOP on change, FDIC monthly, CBP and NES yearly, OZ in January
2027, HUBZone in July 2028.

---

## 5. Privacy and aggregation rules for loan data

The FOIA files publish every borrower's name and address, and sole proprietors are people. SBA publishes them
already, but lexflow should add nothing about any one borrower. The rules mirror payroll §6.1:

1. **Allowlist at read time.** Read only `Program`, `LocationID`, `BankName`, `BankFDICNumber`, `BankNCUANumber`,
   `CDC_Name`, `ThirdPartyLender_Name`, `GrossApproval`, `SBAGuaranteedApproval`, `ApprovalFY`,
   `ProcessingMethod`, `TermInMonths`, `NaicsCode`, `FranchiseCode`, `ProjectCounty`, `ProjectState`,
   `SBADistrictOffice`. Never read `BorrName`, `BorrStreet`, `BorrCity`, `BorrZip`, `BusinessType`,
   `BusinessAge`, `LoanStatus`, dates of payoff or charge-off, `GrossChargeOffAmount`, `JobsSupported`,
   `CollateralInd`. A test feeds a file with borrower columns and asserts none of their values reaches a row.
2. **Project at the server, do not keep.** Query data.sba.gov's DKAN datastore (§3.1) instead of downloading the
   CSVs. Grouped `count(record_number)` queries give the count cells, and a column-limited projection of allowlisted
   columns gives the amounts for medians (there is no median operator). So borrower fields never cross the network.
   The query builder refuses any `properties`, `conditions` or `groupings` entry outside the allowlist, and a test
   checks it. Pages are aggregated as they arrive and then discarded. The vintage is each distribution ID and its
   `asofdate`. On a 503 the job honours `Retry-After` and stops rather than falling back to the full CSVs, which
   would need the user's separate approval. To check columns, read the datastore's schema, which returns column
   names and no rows, rather than a range read of a CSV, which crosses the first borrower rows.
3. **Counts from 5.** A cell with 1 to 4 loans shows "fewer than 5".
4. **Amounts from 11.** Median, quartiles and mean (`avg`) of `GrossApproval` only for 11 or more loans, rounded to
   $10,000, and withheld if a rounded figure equals 1 to 10 loans' exact amounts. `min` and `max` are never published,
   because each is one loan's exact amount.
5. **No sums at small grain, no differencing.** Cells nest (county → state; lender-in-county → county). Every
   published cell holds 0 or at least 11 loans outside its published sub-cells, or the smallest sub-cell is
   withheld.
6. **No quasi-identifiers.** No franchise name, no six-digit NAICS and no single fiscal year in the same cell for a
   county with few loans: the default cell is (county, five-year window, program, NAICS sector).
7. **Organisations are named; people are not.** Lenders and CDCs are institutions and appear by name. 504
   third-party lenders can be people: 13 CFR 120.802 defines a Third Party Loan as "a loan from a commercial or
   private lender, investor, or Federal (non-SBA), State or local government source". A `ThirdPartyLender_Name` is
   kept only if it matches an FDIC or NCUA institution or carries an organisation form, and has at least 5 loans in
   the cell window. Any other name is dropped at read time and never stored.

SBIR points of contact and investigators, CDC and SSBCI staff contacts, and recipient names in state datasets are
handled the same way: dropped at read time, or aggregated.

---

## 6. Licensing questions for counsel

Not decided here. Each needs counsel before derived data goes anywhere public, including Lexipedia.

1. Federal works (SBA, Treasury, CDFI Fund, FDIC, Census, eCFR): are the derived cells free to publish with
   attribution, and does SBA's request for "appropriate acknowledgement" need a credit line on each page?
2. Grants.gov: use of the API "constitutes acceptance" of HHS's terms. The user has to accept them before any call,
   and lexflow must show the required non-endorsement notice.
3. The HUBZone GeoServer is the map's own service, not a published API: may lexflow read it in bulk, or should it
   ask SBA?
4. SBIR.gov, CDFI Fund and FDIC data carry no licence statement on the pages read: confirm they are public domain.
5. State portals: Maryland Commerce's and New York ABO's datasets have no licence set; Maryland DBM's is marked
   public domain. Confirm each before use.
6. AWBC's terms limit use to personal, non-commercial or internal business purposes and forbid compiling a
   directory: confirm that linking to the locator is the only use.
7. Mixing: the statute text lexflow cites comes from open-us-law (CC BY-NC 4.0). Do program pages that combine it
   with public-domain data inherit the non-commercial limit?

---

## 7. The prototype: exact downloads

Nothing below has been downloaded. Each needs the user's approval first.

| # | What | Source | Size | Use |
|---|---|---|---|---|
| 1 | 13 CFR parts 120, 121, 123, 126, 130, 131 (XML) | `https://www.ecfr.gov/api/versioner/v1/full/2026-10-07/title-13.xml?part=<n>` (with gzip) | ~1.5 MB | rules corpus, `is_small`, `which_sba_product` |
| 2 | SOP 50 10 8.1 (.docx) | `https://legacy.sba.gov/sites/default/files/2026-10/SOP%2050%2010%208.1%20Technical%20Policy%20Updates%20effective%20%2010.1.2026.docx` | 1,072 KB | rules corpus, BPMN |
| 3 | 2022 NAICS structure (.xlsx) | `https://www.census.gov/naics/2022NAICS/2022_NAICS_Structure.xlsx` | small (not reported) | NAICS titles for the size DMN |
| 4 | 7(a) FOIA FY2020 to present, as DKAN queries (grouped counts and an allowlisted projection; no CSV) | `https://data.sba.gov/api/1/datastore/query/fc21a598-913d-5c29-b7c1-1924ce608538` | 175,184 rows in the 10 states; an estimated 25 to 50 MB of JSON pages (not measured), against 181.1 MB for the CSV | lender and county cells |
| 5 | 504 FOIA FY2010 to present, as DKAN queries | `https://data.sba.gov/api/1/datastore/query/47fa0223-0a71-562f-85f1-b4b732400efc` | 55,089 rows in the 10 states; an estimated 7 to 15 MB (not measured), against 59.4 MB for the CSV | CDC and county cells |
| 6 | FDIC branch locations, 10 states (JSON, paged) | `https://api.fdic.gov/banks/locations?filters=STALP:<st>&fields=NAME,CERT,UNINUM,OFFNAME,CITY,COUNTY,STCNTY,STALP,ZIP,SERVTYPE` | ~30,500 rows, a few MB | lender entities, branches per county |
| 7 | HUBZone qualified tracts and counties (WFS, no geometry) | `https://maps.certify.sba.gov/geoserver/ows?service=WFS&version=2.0.0&request=GetFeature&typeNames=hubzone:qct_e&propertyName=tract_fips,county,state,current_status,redesignated&outputFormat=application/json&CQL_FILTER=...` and `hubzone:qnmc_e` | 7,047 tracts + counties, under 2 MB | place designations (after counsel question 3) |
| 8 | Opportunity Zones list (.xlsx) | `https://www.cdfifund.gov/system/files/documents/designated-qozs.12.14.18.xlsx` | 277 KB | place designations, until 2027-01-01 |
| 9 | CBP 2023 county (ZIP) | `https://www2.census.gov/programs-surveys/cbp/datasets/2023/cbp23co.zip` | 12 MB | place context |
| 10 | NES 2024 county (ZIP) | `https://www2.census.gov/programs-surveys/nonemployer-statistics/datasets/2024/historical-datasets/nonemp24co.zip` | 4,585,934 B | place context |

Page reads, not downloads: the SSBCI table, the district offices page, the CDC and microlender lists (about 40 pages
at 1 per second), and the SBA form pages.

For the second round: the CDFI certified list (151 KB) and state-awards CSV, SBIR awards without abstracts (91.6 MB),
SBA disaster loan data FY22 (2.19 MB), one Grants.gov extract (78.3 MB, after the terms), the Maryland and New York
Socrata datasets (grouped queries).

---

## 8. Phases and effort

| Phase | Work | Effort |
|---|---|---|
| 1 | Rules corpus (eCFR 13 CFR, SOP 8.1) in `rules_us.sqlite`; thesaurus groups; Ask fuses it with state statutes | M |
| 2 | `is_small` DMN from 121.201 and 121.301(b), with tests on known rows (722511 at $11.5 million, 236118 at $45.0 million) | M |
| 3 | FOIA aggregation with the §5 rules and attacker tests; county crosswalk; lender entities joined to FDIC | M |
| 4 | Place designations (HUBZone, OZ), CBP and NES, place-page block | S |
| 5 | Program registry: SSBCI table, statute hits, SBA district offices, curated resource partners, CDC and microlender lists | M |
| 6 | BPMN "Apply for an SBA-guaranteed loan" and `which_sba_product`, Claude-reviewed; forms registry entries | M |
| 7 | Second round: CDFI, SBIR, USAspending, Grants.gov, state portals, disaster data | M |

---

## 9. Open questions

1. May the prototype run the DKAN queries for items 4 and 5? They are grouped counts plus an allowlisted
   projection, and the pages are discarded after aggregation. The 240.5 MB CSVs are no longer needed.
2. Should lexflow ask SBA (the Chief Data Officer's address on data.sba.gov, or the Office of Entrepreneurial
   Development) for a resource-partner extract and about the HUBZone service? Any such message is the user's to
   send.
3. Is a federal (`us`) process model in scope for Lexipedia, beside the state models?
4. Five-year cells or single fiscal years for lenders in small counties?
5. **Answered 2026-10-10.** `ProjectCounty` is an upper-case county name, and Virginia's independent cities appear
   as "… CITY" (for example "CHARLOTTESVILLE CITY"), from a server-side grouped count (§3.1).
6. When the new Opportunity Zones are designated for 2027-01-01, where will Treasury publish the list?
7. Credit unions: should NCUA data be surveyed to complete the lender entities (`BankNCUANumber`)?

---

## 10. Sources consulted (all opened on 2026-10-10 unless marked)

SBA open data and files
* <https://data.sba.gov/dataset/7a-504-foia>, its data dictionary, and HEAD on the six CSVs
* <https://data.sba.gov/api/1/metastore/schemas/dataset/items> (25 datasets)
* <https://data.sba.gov/oca-datasets>, <https://data.sba.gov/dataset/7a-504-activity-reports-current-month>
* <https://data.sba.gov/dataset/disaster-loan-data>, <https://data.sba.gov/dataset/covid-19-eidl>, <https://data.sba.gov/dataset/ppp-foia>, <https://data.sba.gov/dataset/sbg-foia>
* <https://data.sba.gov/dataset/small-business-size-standards>; broken: <https://www.sba.gov/sites/default/files/data/naics.json>
* <https://data.sba.gov/about> (DKAN)

SBA pages
* <https://www.sba.gov/federal-contracting/contracting-guide/size-standards>, <https://www.sba.gov/document/support-table-size-standards>
* <https://legacy.sba.gov/document/sop-50-10-lender-development-company-loan-programs>, <https://legacy.sba.gov/document/information-notice-5000-880695-issuance-sop-50-10-81> and its PDF (<https://legacy.sba.gov/sites/default/files/2026-08/SBA%20Information%20Notice%205000-880695%20-%20Issuance%20of%20SOP%2050%2010%208.1.pdf>, 193 KB, text extracted locally)
* <https://www.sba.gov/loans/lender-match/>, <https://www.sba.gov/loans/504-loans/list-of-certified-development-companies/>, <https://www.sba.gov/loans/microloans/list-of-microlenders/>, <https://www.sba.gov/sba-lenders/>
* <https://www.sba.gov/counseling/local-assistance/>, <https://www.sba.gov/counseling/local-assistance/resource-partners/>, <https://www.sba.gov/about-sba/sba-district-offices/>, <https://legacy.sba.gov/district/virginia>, <https://legacy.sba.gov/local-assistance>
* <https://www.sba.gov/loans/additional-funding-opportunities/grants/>, <https://www.sba.gov/about-sba/open-government/about-the-sba-gov-website/#disclaimer>
* Forms: <https://legacy.sba.gov/document/sba-form-1919-borrower-information-form>, <https://legacy.sba.gov/document/sba-form-413-personal-financial-statement>, <https://legacy.sba.gov/document/sba-form-1244-application-section-504-loans>
* 404: `https://www.sba.gov/api/content/search/offices.json`; 403: `https://www.sba.gov/wp-json/wp/v2/types`

Regulations
* eCFR API: `/api/versioner/v1/titles.json`, `/versions/title-13.json?part=121`, `/structure/2026-10-07/title-13.json`, `/structure/2026-10-07/title-7.json`, and full text of 13 CFR 120.100, 120.151, 120.707, 120.931, 121.201, 121.301

Other federal
* SBIR: <https://www.sbir.gov/api>, <https://www.sbir.gov/data-resources>, HEAD on both bulk CSVs
* HUBZone: <https://maps.certify.sba.gov/hubzone/map/help>, GeoServer WFS GetCapabilities, DescribeFeatureType, hit counts, one Charlottesville query
* USAspending: <https://api.usaspending.gov/docs/endpoints>, the spending_by_geography contract, GET samples, the glossary API
* OMB M-17-04 (PDF, text extracted locally)
* Grants.gov: <https://www.grants.gov/api>, <https://www.grants.gov/api/common/search2>, <https://www.grants.gov/api/terms-conditions>, <https://www.grants.gov/xml-extract>, <https://www.grants.gov/help/xml-extract/>; <https://simpler.grants.gov/developers>
* SAM.gov: <https://open.gsa.gov/api/assistance-listings-api/>
* CDFI Fund: <https://www.cdfifund.gov/programs-training/certification/cdfi>, <https://www.cdfifund.gov/awards>, <https://www.cdfifund.gov/awards/state-awards>, <https://www.cdfifund.gov/documents/data-releases>, <https://www.cdfifund.gov/opportunity-zones>, <https://www.cdfifund.gov/disclaimer>
* Treasury: SSBCI page and program table (URLs in §3.14), <https://home.treasury.gov/news/press-releases/sb0550>
* IRS: <https://www.irs.gov/credits-deductions/businesses/opportunity-zones>
* FDIC: <https://api.fdic.gov/banks/docs/>, location samples and counts
* Census: CBP and NES directories on www2.census.gov, API metadata, `missing_key.html`, <https://www.census.gov/naics/?48967>

State and local
* <https://home.treasury.gov/policy-issues/small-business-programs/state-small-business-credit-initiative-ssbci/capital-program-list-of-programs-and-contacts>
* <https://sbsd.virginia.gov/vsbfa/>, <https://charlottesville.gov/215/Charlottesville-Match>
* Socrata Discovery API (`api.us.socrata.com/api/catalog/v1`) and view metadata for `cf3i-xdgb`, `absk-avps` (opendata.maryland.gov) and `vp83-gfyz` (data.ny.gov)
* lexflow's own statute indexes (`/data/index/statutes_<st>.sqlite` in `lexflow-app-1`, read-only queries) and the open-us-law manifest

Blocked or refused this client (not retried): americassbdc.org, score.org, virginiasbdc.org, rd.usda.gov, eda.gov,
data.commerce.gov, ecfr.gov HTML pages. AWBC's locator and terms were read; its terms are summarised in §3.7.
