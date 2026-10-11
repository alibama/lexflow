# Tax data for lexflow: codes, regulations, rates, forms and local business taxes

Status: research and design, 2026-10-10. Nothing described here is built, and no data file was downloaded on purpose
(see §12.3 for two things that came close). No file other than this note was written. **Corrected the same evening**
where [verify-data-expansion.md](verify-data-expansion.md) found errors: the page that carries the Census finance
licence words (W7), the `steps.py` line of the regulations switch, and the `SLOTS` list in `reference.py` (W11).

This note covers the tax data lexflow could gather so that it can answer questions such as:

* "What business taxes do I owe to open a shop in Baltimore?"
* "What is the sales tax rate in Austin, and how do I register to collect it?"
* "Do I need a BPOL licence in Fairfax County?"

It covers federal tax law (the Internal Revenue Code and Treasury regulations), IRS guidance, forms and exempt-organisation
data, the state tax titles and regulations lexflow already holds, sales and use tax rates and boundaries, property tax
rates, local business taxes and licences, state registration and forms, and Census finance data. It ends with how each
source plugs into lexflow, the exact downloads a prototype would need, and the licensing questions to put to counsel.

**How it was checked.** Every source was opened on 10 October 2026, except where §12.2 says otherwise.
* Web requests were read-only GETs or HEADs, made one at a time, at least 1.2 s apart per host. Each carried the
  User-Agent `lexflow-research/0.1 (https://github.com/alibama/lexflow)` and a 15 s timeout.
* API calls fetched only metadata or a few rows: Socrata `api/views/<id>.json`, server-side `count(*)` and `$group`, one
  eCFR section, one rate lookup for a state office's own address, and an OData `$top=3`.
* Corpus figures come from the open-us-law files already in container `lexflow-app-1` under `/data/raw/open-us-law/`.
  They were read in place with pyarrow.
* No account was created and no API key was requested or used.

**Scope rules.**
* Only organisations and official channels are named. No person-level row was kept. Where a source holds personal data,
  for example sole-proprietor permit holders, property owners or nonprofit contacts, this note says so and gives an
  aggregate-only method (§7).
* This is not legal advice. Licensing questions are listed for counsel in §11 and are not decided here.

---

## 0. The short version

| # | Finding | What it means for lexflow |
|---|---|---|
| T1 | **Every state tax title is already on disk.** The open-us-law statute files hold 24,020 tax sections across the ten states. Examples: VA Title 58.1 (1,774 sections), DC Title 47 (1,940), MD Tax-General and Tax-Property (1,354), TX Tax Code (2,119), CA Revenue and Taxation Code (7,327), FL Title XIV (1,176), NY Tax Law and Real Property Tax Law (2,240), IL 35 ILCS (2,595), WA Titles 82, 82A and 84 (2,093) and NC Chapters 105, 105A and 105B (1,402). The key sections are present: BPOL (§ 58.1-3700 et seq.), the sales tax impositions, the permit and licence sections and the property tax rate list (Tex. Tax Code § 5.091) (§1.1). | Tax *law* questions already work through the existing index. Tax *rate* questions do not, because statutes give caps and authorisations, not the local rates in force. |
| T2 | **The regulations add-on is already downloaded but not indexed.** It covers 7 of the 10 states: VA, DC, MD, FL, IL, WA and NC. Their tax titles are 23 VAC (423 sections), 9 DCMR (535), COMAR 03 (89), FAC 12 to 12D (786), 86 Ill. Adm. Code (1,723), WAC 458 (520) and 17 NCAC (2,189, of which 1,684 are repealed). There are no regulations for TX, CA or NY. MD's file holds only COMAR 03.04 (income tax): no sales tax rules and no SDAT title (§1.2). | Indexing these files (no download needed) makes VA's BPOL regulation (23VAC10-500) searchable. The same files hold the building codes behind the deck-and-shed question (§1.3). |
| T3 | **Rates must come from revenue departments, and they move.** DC Code § 47-2002 in the 2026-09-30 snapshot schedules 7% from 1 October 2026. The DC Office of Tax and Revenue says the rise was postponed and the rate stays 6% through 30 September 2027. Mecklenburg County, NC, added 1% on 1 July 2026 (§3). | Rates need their own table with effective dates and the agency notice as source. They should never be read from statute text alone. This is a version flag the Ask answer must carry. |
| T4 | **Sales tax rate files are free and small for all ten states.** Seven states publish machine-readable tables: VA XLSX (83 KB), TX XLSX, CA XLSX (71 KB) plus an OData API, WA CSV zip (4.4 KB), NC CSV, IL fixed-width (31 KB) and SST files for WA and NC. FL and NY publish PDFs: DR-15DSS (204 KB) and Pub 718 (216 KB). MD (6%) and DC (6%) have one statewide rate. | A prototype needs about 1 MB of downloads (two small files not measured) to cover state and local general sales tax rates for all ten states. |
| T5 | **Only WA and NC are Streamlined Sales Tax members.** The SST rate and boundary files cover those two states only. The other eight publish in their own formats. Address-level lookups are free and need no key in WA (URL interface) and CA (CDTFA Tax Rate API), but each lookup would send a user's address to a state server (§7.4). | Use jurisdiction-level tables for answers. Make address lookup an explicit, opt-in user action, never a background call. |
| T6 | **Local business taxes are the hard part and have no statewide table.** VA's BPOL caps are in statute (§§ 58.1-3703, 58.1-3706) and the regulation (23VAC10-500) is on disk, but each locality's rates and fee tiers are on its own website. Fairfax County's are on its Department of Tax Administration page. WA is the exception: its Business Licensing Service publishes a fee page for every partner city (§5). | Model BPOL as a two-layer DMN: statutory caps from the corpus, plus a curated local schedule for each place lexflow covers in depth. Use WA's per-city pages for WA. |
| T7 | **Federal tax law is public domain and easy to get.** The US Code is a US government work (17 U.S.C. § 105). The eCFR API served 26 CFR without a key (Title 26 is 87.8 MB of XML, Part 1 alone 69.7 MB). The OLRC download site was under maintenance on 10 October, and its last good capture (30 August) shows release point PL 119-102 (07/12/2026). open-us-law also carries the US Code (80.8 MB), the CFR (1.45 GB) and IRS rulings, notices and procedures under CC BY-NC 4.0 (§2). | Build the federal layer from the public-domain primary sources (OLRC, eCFR). Use open-us-law only for IRS guidance, and only if counsel clears the NC terms for lexflow's use. |
| T8 | **IRS forms and publications are listable and partly machine-readable.** The current-products list holds 3,141 items, with revision and posted dates. 595 instructions and publications have XML sources, for example Pub 334 at 115 KB. The IRS says its own content "may be freely copied", but forbids implying endorsement through its seal (§2.4). | Add federal entries to `fixtures/forms/forms.json` (SS-4 for the EIN step). Index a handful of small-business publications. |
| T9 | **Census finance data gives every government's tax mix.** The 2022 Census of Governments Finance individual unit file (9.7 MB) uses item codes T01 (property), T09 (general sales), T28 (occupation and business licences, not elsewhere classified) and T40 (individual income). The GUS workbook already downloaded also lists 39,555 special districts and 12,546 school districts, the taxing units behind property tax bills (§2.7). | Place pages can show "how this government raises money" without any scraping. Property tax answers can name the school district and special district levying the tax. |
| T10 | **Some tax datasets are mostly personal data.** Texas's Active Sales Tax Permit Holders lists 890,307 permits with names and addresses, 232,801 of them with organisation type `IS`. NY's assessment-roll dataset carries owner names and mailing addresses. The EO BMF's `ICO` field is "the person (officer, director, etc.)" for correspondence (§7). | Use these only as server-side aggregates (counts by place and type), or not at all. |

**Recommended order:**
1. Index the regulation files already on disk.
2. Load the ten states' sales tax rate tables with effective dates.
3. Build the VA BPOL DMN and the "register to collect sales tax" BPMN for each state.
4. Add the IRC and 26 CFR (EIN, employment tax and procedure parts first).
5. Add the Census finance file and property tax rate tables.
6. Leave address-level boundary files and personal-data sets for later or never.

---

## 1. What lexflow already has

### 1.1 State tax statutes (open-us-law v2026.09.1, snapshot 2026-09-30)

The manifest is at `/data/raw/open-us-law/index.json`: dataset `open-us-law`, version `v2026.09.1`, snapshot date
`2026-09-30`, `license_data: CC-BY-NC-4.0`. Counts come from the local statute parquet files, grouped by the top level
of `display_path`.

| State | Tax division in the file | Sections | Words | Key sections checked (present, with `source_url`) |
|---|---|---:|---:|---|
| VA | Title 58.1 (Taxation) | 1,774 | 524,403 | § 58.1-603 (sales tax imposed), § 58.1-605 (local sales tax), § 58.1-3700 (licence requirement), § 58.1-3703 (local licence taxes and fees), § 58.1-3706 (rate limits), § 58.1-3201 (real estate) |
| DC | Title 47 (Taxation, Licensing, Permits, Assessments, and Fees) | 1,940 | 462,213 | § 47-2002 (sales tax imposed), § 47-1806.03 (income tax rates), § 47-2853.01 |
| MD | Tax-General (`gtg`) and Tax-Property (`gtp`) | 1,354 | 395,652 | TG § 11-102 (imposed), § 11-104 (rate: "6 cents for each exact dollar"), § 11-702 (licence required), § 10-106 (county income tax 2.25% to 3.30%), TP § 11-101 (annual report to SDAT by 15 April), TP § 6-302 |
| TX | Tax Code (`tx`) | 2,119 | 566,935 | § 151.051 (6.25%), § 151.201 and § 151.202 (permits), § 151.251 (security), § 151.0595 (remote sellers), § 321.103 (city sales tax), § 171.001 (franchise tax), § 5.091 (statewide list of tax rates), § 11.13 (homestead), § 26.04 (no-new-revenue rate) |
| CA | Revenue and Taxation Code (`rtc`) | 7,327 | 1,486,322 | § 6051 (sales tax), § 6066 (seller's permit), § 7202, § 7251 (Transactions and Use Tax Law), § 17041 (personal income tax) |
| FL | Title XIV (Taxation and Finance) | 1,176 | 648,085 | § 212.05 ("6 percent"), § 212.055 (discretionary surtaxes), § 212.18 (dealer registration), § 196.031 (homestead), §§ 205.032, 205.042 and 205.053 (local business tax) |
| NY | Tax Law (`TAX`) and Real Property Tax Law (`RPT`) | 2,240 | 1,902,447 | Tax Law § 1105 (sales tax), § 1101 (definitions), § 1134 (registration), § 1253; RPTL § 300, § 1210 |
| IL | Chapter 35 (Revenue), about 70 Acts | 2,595 | 1,009,272 | 35 ILCS 120/2 (Retailers' Occupation Tax), 105/3 (Use Tax), 5/201 (income tax), 200/9-195 (Property Tax Code); the largest Act is 35 ILCS 200 with 840 sections |
| WA | Titles 82, 82A and 84 | 2,093 | 561,409 | RCW 82.08.020 (retail sales tax), 82.14.030 (local sales taxes), 82.32.030 (registration), 84.52.043 (levy limits) |
| NC | Chapters 105, 105A and 105B | 1,402 | 348,629 | § 105-164.4 (tax imposed), § 105-164.29 (registration), § 105-467 (local sales tax); § 160A-211 (city privilege licence tax) is present as "Repealed by Session Laws 2014-3, s. 12.3(a), effective July 1, 2015" |

Notes:
* **Local taxing authority often sits outside the tax title.** Examples are municipal codes such as IL 65 ILCS and city
  charters. MD's trader's licence, Bus. Reg. § 17-1803, is in the Business Regulation article; 19 Business Regulation
  sections mention a trader's licence. The existing index covers these too, because it indexes whole states.
* **Links to the IRC.** 1,411 sections across the ten tax titles name the Internal Revenue Code (case-insensitive text
  match). Only 84 carry a parsed 26 U.S.C. entry in the `cross_references_usc` column, so a federal layer (§2.1) needs
  its own citation linker. `lexflow/law/xref.py` already classifies these citations as `federal` with no target.
* **No amendment year for NY.** NY rows have no `last_amended_year`, so the Ask answer cannot show when a NY tax section
  last changed.

### 1.2 The regulations add-on (already downloaded, not indexed)

The pipeline fetches `us_<state>_regulations.parquet` when `--regulations` is set (`lexflow/pipeline/steps.py`, line
298). The 39 state and territory files are on disk; the federal file (`us_federal_regulations.parquet`, 1.45 GB) is
not. `lexflow/ask/index.py`, however, builds
`statutes_<state>.sqlite` only. The manifest lists 40 regulation files, one of them federal. The add-on's README says that
California, New York and Texas regulations, among others, are "not in this release" and are available through Vaquill's
hosted API. lexflow does not use that API.

| State | Tax regulations in the file | Rows | Status | Notes |
|---|---|---:|---|---|
| VA | 23 VAC (Taxation), 18 chapters | 423 | all in force; latest amendment 2024 | 23VAC10-210 (retail sales and use) 118 sections; 23VAC10-500 (**BPOL**) 91; 23VAC10-120 (corporate income) 56; 23VAC10-110 (individual income) 35. **Completeness check:** the LIS chapter page for 23VAC10-210 lists 181 sections, 62 of them repealed and 119 live. The file has 118. |
| DC | 9 DCMR (Taxation and Assessments) | 535 | 423 in force, 112 reserved | ch. 4 Sales and Use (90), ch. 1 Income and Franchise (85), ch. 3 Real Property (70), ch. 20 Real Property Tax Appeals Commission (25) |
| MD | COMAR Title 03 (Comptroller) | 89 | in force; latest 2022 | **only Subtitle 04 (Income Tax).** No sales and use tax rules (03.06) and no SDAT title (18) |
| FL | FAC 12, 12A, 12B, 12C, 12D | 786 (748 without 12E) | 612 in force, 164 repealed, 10 transferred | 12A (155 rows; its Sales and Use Tax chapter alone has 101), 12D property tax (tax collectors, value adjustment boards, exemptions), 12C corporate income. 12E is the Child Support Program, not tax. |
| IL | 86 Ill. Adm. Code (Revenue) | 1,723 | in force | Part 130 Retailers' Occupation Tax (167), Part 100 Income Tax (118), Part 150 Use Tax (79), Part 140 Service Occupation Tax (53). Part 3000 is riverboat gambling, not tax. |
| WA | WAC 458 (Revenue) | 520 | in force | 458-20 Excise Tax Rules (199), 458-61A Real Estate Excise (42), 458-19 Levies, Rates and Limits (19), 458-14 County Boards of Equalization (21) |
| NC | 17 NCAC (Revenue) | 2,189 | 496 in force, 1,684 repealed, 9 reserved | median 8 words per row: most rows are repeal stubs |

The schema is the same as the statutes, so the same `index.py` builder can take a `kind` argument (`statutes` or
`regulations`) and produce `regulations_<state>.sqlite`. This needs no new download.

### 1.3 Adjacent finding: the building codes behind the deck-and-shed question are on disk too

The question that prompted this survey was "Do I need a building permit for a deck or a shed?". The regulation files
already on disk hold:
* **VA 13VAC5-63, the Uniform Statewide Building Code (81 sections).** 13VAC5-63-80 (Section 108, Application for
  permit) lists exemptions from the permit requirement. Item 2 exempts one-story detached tool and storage sheds,
  playhouses and similar structures up to 256 square feet. The section's exemption list has no deck exemption.
* **DC Title 12-A to 12-M, Construction Codes Supplements (833 rows).**
* **WA WAC 51-xx, State Building Code adoption and amendment (706 rows).**

MD's Building Performance Standards are not in the MD file. Indexing the regulation files (§1.2) would let lexflow
quote the shed exemption today. Building codes are outside this note's domain, so this is noted for the building-code
survey.

---

## 2. Federal sources

### 2.1 Internal Revenue Code (26 U.S.C.), USLM XML, Office of the Law Revision Counsel

| Field | Detail |
|---|---|
| Publisher | Office of the Law Revision Counsel (OLRC), U.S. House of Representatives |
| Data | Download page: <https://uscode.house.gov/download/download.shtml>. Title 26 XML at the last captured release point: `https://uscode.house.gov/download/releasepoints/us/pl/119/102/xml_usc26@119-102.zip` |
| Documentation | USLM User Guide `https://uscode.house.gov/download/resources/USLM-User-Guide.pdf`; schema and CSS `resources/schemaandcss.zip` (both linked from the download page) |
| Licence / terms | A US government work: "Copyright protection under this title is not available for any work of the United States Government" ([17 U.S.C. § 105](https://www.law.cornell.edu/uscode/text/17/105)). No OLRC terms page could be read on 10 October (see below). |
| Format and access | One zip of USLM XML per title (also XHTML, PCC and PDF), or one zip for all titles. Bulk files only, with no query API. No key needed. |
| Size | **Not measured.** On 10 October 2026 every uscode.house.gov page returned "Site is currently under maintenance". The Internet Archive's 9 October capture shows the same notice. For scale, open-us-law's whole US Code file is 80,786,461 bytes (60,667 sections). |
| Cadence and vintage | One "release point" per batch of classified laws. The [30 August 2026 capture](https://web.archive.org/web/20260830085506/https://uscode.house.gov/download/download.shtml) shows "Public Law 119-102 (07/12/2026)", and Title 26 is listed as current through 119-102. |
| Granularity and fields | Title, subtitle, chapter, subchapter, part and section, with notes, source credits and amendment history. USLM identifiers such as `/us/usc/t26/s162`. |
| Coverage | Federal: applies in all ten states. Not specific to any local government. |
| Personal data | None |
| Fits lexflow | (a) A new federal index (`usc26.sqlite`) with the same contentless FTS5 layout as the state indexes. (b) A citation linker for the 1,411 state tax sections that name the IRC (§1.1), so a state conformity section can show the federal section it adopts. (c) Process steps that cite federal law, such as getting an EIN before state registration. |
| Example question | "Do I need an EIN to open a shop?" (the IRC section the regulation implements, with 26 CFR 301.6109-1 from §2.2) |
| Effort | M: a USLM-to-sections parser (about 2 days) plus reuse of `index.py` |
| Prototype download | `xml_usc26@<current release point>.zip` from uscode.house.gov (size to be read off the page when it is back). Alternative: `us_federal_statutes.parquet` from open-us-law, 80,786,461 bytes, CC BY-NC compilation (§11 Q1). |
| Priority | **next** |

### 2.2 Treasury regulations (26 CFR), eCFR API and GovInfo bulk XML

| Field | Detail |
|---|---|
| Publisher | Office of the Federal Register (eCFR) and the Government Publishing Office (GovInfo bulk data) |
| Data | eCFR API, e.g. `https://www.ecfr.gov/api/versioner/v1/full/{date}/title-26.xml?part=301&section=301.6109-1`; titles list `https://www.ecfr.gov/api/versioner/v1/titles.json`; ancestry `.../ancestry/{date}/title-26.json?part=301`. Bulk: `https://www.govinfo.gov/bulkdata/ECFR/title-26/ECFR-title26.xml` |
| Documentation | eCFR developer resources page, <https://www.ecfr.gov/reader-aids/ecfr-developer-resources/rest-api-interactive-documentation>. **The eCFR and Federal Register HTML pages redirected this client to a CAPTCHA "Request Access" page**, which says programmatic access is limited to the developer APIs. The page was not read directly; the API itself answered every call. |
| Licence / terms | US government work (17 U.S.C. § 105). No API key: every call here worked without one. The eCFR's standing relative to the official annual CFR edition could not be read from its own pages today, so check it before citing eCFR text as the official edition. |
| Format and access | REST. XML for full text, JSON for structure and ancestry. **The `full` endpoint returns HTTP 406 unless the request sends `Accept-Encoding: gzip`.** No published rate limit was read; use one request per second. GovInfo bulk: one XML file per title. |
| Size | Title 26 is 87,821,969 bytes per the eCFR `size` metadata. Part 1 (Income Taxes) is 69,677,493, Part 301 (Procedure and Administration) 4,699,706, and Part 31 (Employment Taxes) 2,015,776. The GovInfo file `ECFR-title26.xml` is 88,093,603 bytes, plus a 3,981,823-byte graphics zip. |
| Cadence and vintage | Daily. On 2026-10-08 `titles.json` showed Title 26 latest amended 2026-10-06 and up to date as of 2026-10-07. The GovInfo file was last modified 07-Oct-2026. |
| Granularity and fields | Title, chapter, subchapter, part, subpart and section (`DIV8 TYPE="SECTION"`), with `hierarchy_metadata` giving the citation, e.g. "26 CFR 1.162-1" and "§ 1.162-1 Business expenses". |
| Coverage | Federal |
| Personal data | None |
| Fits lexflow | A federal regulation index next to `usc26`. Start with Parts 301 (EIN: § 301.6109-1 "Identifying numbers"), 31 and 601, then add the Part 1 subparts that small-business questions reach (e.g. § 1.162-1). **The same pipeline also gives 13 CFR Part 120 (SBA Business Loans, 553,586 bytes).** That is useful for the SBA work the user asked about. |
| Example question | "Do I have to withhold tax from my first employee's pay?" (26 CFR Part 31) |
| Effort | S–M: XML to sections is simple, and the hierarchy metadata is clean |
| Prototype download | eCFR API, Parts 301 and 31 of Title 26 (about 6.7 MB of XML in total, fetched part by part), plus selected Part 1 sections. Avoid the 1.45 GB `us_federal_regulations.parquet`, which holds the whole CFR. |
| Priority | **next** |

### 2.3 IRS guidance (revenue rulings, procedures, notices, announcements, written determinations), open-us-law files

| Field | Detail |
|---|---|
| Publisher | Compiled by Vaquill AI from IRS releases; the underlying text is IRS (public domain) |
| Data | From the local manifest: `us_federal_irs_rev_rul.parquet` (339,821 bytes, 248 documents), `us_federal_irs_rev_proc.parquet` (4,539,026 bytes, 378), `us_federal_irs_notice.parquet` (3,973,199 bytes, 769), `us_federal_irs_announcement.parquet` (234,111 bytes, 83), `us_federal_irs_written_determination.parquet` (132,414,071 bytes, 45,368). Base URL `https://oss-data-us.vaquill.ai/v2026.09.1/`. |
| Documentation | `https://oss-data-us.vaquill.ai/v2026.09.1/README.md` (read). The Hugging Face card is gated and returned 401. |
| Licence / terms | The README says the legal text is public domain and the compilation is CC BY-NC 4.0, "free for non-commercial use". Commercial use needs a licence from Vaquill (§11 Q1). |
| Format and access | Parquet, the same 27-column schema as the statutes. Static files with SHA-256 sums. No key. |
| Size | 9.1 MB for the four small sets; 132 MB for written determinations |
| Cadence and vintage | Quarterly snapshots; this one is v2026.09.1 (2026-09-30) |
| Granularity and fields | One row per document, with citation, text, year and source URL |
| Coverage | Federal |
| Personal data | Written determinations (private letter rulings) are issued redacted. The file was not opened here, so check for residual identifiers before indexing it. |
| Fits lexflow | Index the four small sets as "federal guidance" so Ask can cite a revenue procedure. Skip written determinations, which cannot be relied on as precedent and are large. |
| Example question | "What are the safe-harbor rules for a home office deduction?" |
| Effort | S |
| Prototype download | The four small files, 9,086,157 bytes in total, after the §11 Q1 answer |
| Priority | **later** (the IRC and regulations come first). The IRS's own bulletin pages are a fallback, but `robots.txt` disallows `/*/internal-revenue-bulletins` for language-prefixed paths. |

### 2.4 IRS forms, instructions and publications listing

| Field | Detail |
|---|---|
| Publisher | Internal Revenue Service |
| Data | <https://www.irs.gov/forms-instructions-and-publications> (`?items_per_page=200&find=<number>`). PDFs at `https://www.irs.gov/pub/irs-pdf/<file>.pdf`, e.g. `fss4.pdf` and `iss4.pdf`. |
| Documentation | <https://www.irs.gov/forms-pubs/using-irs-forms-instructions-publications-and-other-item-files> |
| Licence / terms | [Use of content from IRS.gov](https://www.irs.gov/about-irs/use-of-content-from-irsgov): content by federal employees "is not subject to copyright and may be freely copied. Credit is requested." The same page forbids using Treasury or IRS seals and names to imply endorsement (18 U.S.C. § 701, 31 U.S.C. § 333, 31 C.F.R. Part 37). On forms, the IRS says it accepts "forms that are consistent with the official printed versions". |
| Format and access | An HTML table with Product Number, Title, Revision Date and Posted Date; 200 rows per page fits the 3,141 products in 16 requests. `robots.txt` disallows `/*/forms-instructions-and-publications`, which covers the language-prefixed copies (`/es/...`). The English path is not listed, unlike `/charities-non-profits/tax-exempt-organization-search`, which is disallowed both with and without the prefix. |
| Size | 3,141 current products (10 October 2026) |
| Cadence and vintage | Continuous. Form SS-4 is revision Dec 2025, posted 12/22/2025; its instructions were posted 12/23/2025. |
| Granularity and fields | Product number, title, revision date, posted date and PDF link |
| Coverage | Federal |
| Personal data | None |
| Fits lexflow | New `forms.json` entries with `publisher: "Internal Revenue Service"`, matched to a `get_ein` step in the business process (SS-4, plus the online EIN application as the portal). Revision dates feed the forms checker's freshness test. |
| Example question | "What form do I file to get an EIN?" |
| Effort | S |
| Prototype download | 16 HTML listing pages (no data file) |
| Priority | **now** (small, and it fills a gap in the business process) |

### 2.5 IRS instructions and publications XML source files

| Field | Detail |
|---|---|
| Publisher | IRS |
| Data | <https://www.irs.gov/instructions-and-publications-xml-source-files>; files at `https://www.irs.gov/pub/irs-sgml/<p###>.zip` |
| Documentation | The same page, and the "Using IRS forms ... item files" page. The IRS describes its XML as "primarily used by republishers of tax information". |
| Licence / terms | As §2.4 |
| Format and access | One zip per product (XML or SGML). `robots.txt` disallows only the language-prefixed listing (`/*/instructions-and-publications-xml-source-files`). |
| Size | 595 products. Pub 334 (Tax Guide for Small Business) is 115,396 bytes, modified 2026-02-12; Pub 583 is 65,029 bytes, modified 2025-01-30. |
| Cadence and vintage | Per product, when it is revised |
| Granularity and fields | Structured chapters and sections of each publication |
| Coverage | Federal |
| Personal data | None |
| Fits lexflow | A small "federal guidance" index for plain-language answers, cited as guidance rather than law. |
| Example question | "What records should a new small business keep?" (Pub 583) |
| Effort | S (format parser) |
| Prototype download | `p334.zip` (115,396 bytes) and `p583.zip` (65,029 bytes); add `p15.zip` (Employer's Tax Guide) when employment questions are added (size not checked) |
| Priority | **next** |

### 2.6 IRS Exempt Organizations Business Master File Extract (EO BMF) and TEOS bulk data

| Field | Detail |
|---|---|
| Publisher | IRS, Tax Exempt and Government Entities |
| Data | <https://www.irs.gov/charities-non-profits/exempt-organizations-business-master-file-extract-eo-bmf>: one CSV per state, e.g. `https://www.irs.gov/pub/irs-soi/eo_va.csv`. TEOS bulk: <https://www.irs.gov/charities-non-profits/tax-exempt-organization-search-bulk-data-downloads> (Pub 78, auto-revocation list, Form 990-N) |
| Documentation | Info sheet `https://www.irs.gov/pub/foia/ig/tege/eo-info.pdf` (field definitions) |
| Licence / terms | As §2.4 |
| Format and access | CSV, sorted by EIN. The VA header is `EIN,NAME,ICO,STREET,CITY,STATE,ZIP,GROUP,SUBSECTION,AFFILIATION,CLASSIFICATION,RULING,DEDUCTIBILITY,FOUNDATION,ACTIVITY,ORGANIZATION,STATUS,TAX_PERIOD,ASSET_CD,INCOME_CD,FILING_REQ_CD,PF_FILING_REQ_CD,ACCT_PD,ASSET_AMT,INCOME_AMT,REVENUE_AMT,NTEE_CD,SORT_NAME`. TEOS files are zipped delimited text. |
| Size | `eo_va.csv` is 9,508,327 bytes (from one `Content-Range` header). The other states were not measured (§12.3). |
| Cadence and vintage | EO BMF posting date 9/8/2026. TEOS files are "updated monthly" (Pub 78 last updated September 10, 2026). |
| Granularity and fields | One row per exempt organisation: EIN, name, address, subsection (e.g. 501(c)(3)), deductibility, NTEE code, asset and revenue amounts |
| Coverage | All ten states, by headquarters filing address, which "may or may not represent the state(s) in which an organization has operations" |
| Personal data | **`ICO`, "In Care Of Name", is "the person (officer, director, etc.) to whose attention any correspondence should be directed"** (info sheet). Drop `ICO` on load. Organisation names and addresses are fine. |
| Fits lexflow | Entities: nonprofits as organisations with EIN and NTEE. Ask: "can donations be deducted" through Pub 78 or `DEDUCTIBILITY`. Place pages: counts of exempt organisations by type in each government's ZIP codes (aggregate). |
| Example question | "Is this food bank a 501(c)(3), so my donation is deductible?" |
| Effort | S |
| Prototype download | `eo_va.csv`, `eo_dc.csv` and `eo_md.csv` (VA 9.5 MB; others not measured) |
| Priority | **later** (marginal for the business-tax questions) |

### 2.7 Census of Governments: Finance (individual unit files) and the GUS lists already on disk

| Field | Detail |
|---|---|
| Publisher | U.S. Census Bureau |
| Data | 2022 Census of Governments, finance: <https://www.census.gov/data/datasets/2022/econ/local/public-use-datasets.html>, file `https://www2.census.gov/programs-surveys/gov-finances/tables/2022/2022_Individual_Unit_File.zip`. 2024 Annual Survey: <https://www.census.gov/data/datasets/2024/econ/local/public-use-datasets.html>, file `.../tables/2024/2024_Individual_Unit_Files.zip` |
| Documentation | Inside the zip, and the methodology PDFs on the same pages. Item codes: [Government Finance and Employment Classification Manual (2006)](https://www2.census.gov/govs/pubs/classification/2006_classification_manual.pdf) |
| Licence / terms | The finance datasets index page (<https://www.census.gov/programs-surveys/gov-finances/data/datasets.html>) says "Datasets are usually for public use, and users may analyze, extract, customize and publish statistics." The 2022 public-use page linked above does not carry that line, so a credit should link the index page. A US government work. |
| Format and access | Zip of fixed-width or text records (government ID, item code, amount). No key. |
| Size | 2022: 9,719,280 bytes (HEAD; the page label says "<3.8 MB"). 2024: 4,267,040 bytes (HEAD, last modified 2026-08-04). |
| Cadence and vintage | Annual survey; a full census every five years (2022). The 2024 data were released July 2026. |
| Granularity and fields | One record per government and item code. Tax codes from the manual: **T01** Property Taxes; **T09** General Sales and Gross Receipts Taxes (which covers "all gross receipts, whether at a single rate or at classified rates"); **T20–T29** licence taxes, including **T28** "Occupation and Businesses License, NEC" (licences "required of persons engaged in particular professions, trades, or occupations"); **T40** Individual Income; **T41** Corporation Net Income. |
| Coverage | 2022 covers every government (the census year). Other years are a sample: the 2024 page says "all governments in the annual survey sample". |
| Personal data | None (government-level) |
| Fits lexflow | Place pages: a "tax mix" panel by `gov_id` (property, sales, licence, income), giving a sense of scale before the rate details. It is also a check: a locality with T28 revenue has a business licence tax worth modelling. Joining needs the 14-character government ID. `payroll-research.md` §6.1 found ASPEP uses the same layout as lexflow's `gov_id`; confirm the finance file's IDs on first load. |
| Example question | "How much of Fairfax County's revenue comes from business licence taxes?" Whether VA BPOL is reported under T28 or T09 must be checked in the Fairfax rows (§12.1). |
| Effort | S |
| Prototype download | `2022_Individual_Unit_File.zip`, 9,719,280 bytes |
| Priority | **next** |

**Already on disk, no download:** `/data/raw/census/govt_units_2022.ZIP` (11,459,763 bytes, loaded by
`lexflow/municipal/governments.py`) holds sheets `General Purpose` (38,736 data rows), `Special District` (39,555),
`School District` (12,546) and `DEP School Dist` (1,313). lexflow loads only the first. School districts and special
districts are the taxing units in TX, NY and IL property tax tables (§4). Loading those two sheets as governments of kind
`school_district` and `special_district` would let property tax answers name the unit that levies each part of a bill.

---

## 3. Sales and use tax rates and boundaries

General rule for all states. A rate row needs: the state, a jurisdiction code in the state's own scheme, the `gov_id`
it maps to, the tax component (state, county, city, transit, district), the rate, `effective_from`, `effective_to`, the
source URL and the retrieval date. Statute text gives the state rate and the local authorisation, and that text should
be linked from the row.

### 3.1 Streamlined Sales Tax rate and boundary files (WA and NC)

| Field | Detail |
|---|---|
| Publisher | Streamlined Sales Tax Governing Board, Inc. (files supplied by each member state) |
| Data | Rates: <https://streamlinedsalestax.org/ratesandboundry/Rates/>. Boundaries: <https://streamlinedsalestax.org/ratesandboundry/Boundary/> |
| Documentation | <https://www.streamlinedsalestax.org/Shared-Pages/rate-and-boundary-files>; Technology Guide ch. 5, linked from that page |
| Licence / terms | No licence was found. The site footer reads "© Copyright 2018 Streamlined Sales Tax Governing Board, Inc." The files page says they are "created for use in your tax calculation applications". The WA state page adds that its information "is not legal advice" (§11 Q4). |
| Format and access | CSV, or a zip of CSV, from a plain directory listing. No key. |
| Size | NC rate `NCR2026Q3APR23.csv` 15,870 bytes; WA rate `WAR2026Q4AUG27.zip` 58,577; NC boundary `NCB2026Q4AUG19.zip` 15,770,839; WA boundary `WAB2026Q4AUG27.zip` 19,643,331 |
| Cadence and vintage | Quarterly. Files are posted "by the first day of the month prior to the beginning of each calendar quarter", and states post only when something changed. The latest are WA Q4 2026 (rate and boundary), NC Q4 2026 (boundary) and NC Q3 2026 (rate). |
| Granularity and fields | The boundary file maps 5- or 9-digit ZIPs, or addresses, to jurisdiction codes; the rate file gives the rate for each code |
| Coverage | **Of the ten states, only NC and WA are Full Members.** The member list shows 23 full members, with Tennessee as an associate. CA, DC, FL, IL, MD, NY, TX and VA are listed as non-members. |
| Personal data | None |
| Fits lexflow | The rate files give jurisdiction rates. The boundary files are only needed for address-level answers (§7.4). The SST "Taxability Matrix" for each state, linked from each state page, could feed a DMN of what is taxable. |
| Example question | "What is the combined sales tax rate in Charlotte?" |
| Effort | S (rates); M (boundaries) |
| Prototype download | The two rate files (74,447 bytes). Not the boundary files. |
| Priority | **now** (rates), **later** (boundaries) |

### 3.2 Washington: DOR downloadable database and rate lookup URL interface

| Field | Detail |
|---|---|
| Publisher | Washington State Department of Revenue |
| Data | <https://dor.wa.gov/taxes-rates/sales-use-tax-rates/downloadable-database>: `Rates_26Q4.zip` (location codes and rates) and `State_26Q4.zip` (address ranges). URL interface: `https://webgis.dor.wa.gov/webapi/AddressRates.aspx?output=xml&addr=...&city=...&zip=...` |
| Documentation | Field descriptions linked from the download page; the URL interface page <https://dor.wa.gov/wa-sales-tax-rate-lookup-url-interface> |
| Licence / terms | No licence was found (the footer links only privacy and accessibility). The download page says the data "is a resource for you to integrate into your own customized applications" (§11 Q4). |
| Format and access | CSV in zips. The URL interface returns XML or text with result codes 0–9 and needs no key. |
| Size | `Rates_26Q4.zip` 4,420 bytes (HEAD); `State_26Q4.zip` 8.39 MB (page label) |
| Cadence and vintage | Quarterly, posted 30 days before each quarter. Q4 2026 (Oct 1 to Dec 31) is current. |
| Granularity and fields | 4-digit DOR location code, state rate, local rate, total rate (field descriptions page). The lookup also returns the street range, ZIP+4, period (`Q42026`) and the PTBA and RTA. |
| Coverage | Statewide, by DOR location code |
| Personal data | None in the files. The lookup takes an address (§7.4). |
| Fits lexflow | The rate table, crosswalked to `gov_id` by location-code name and county. One test lookup of DOR's own office address (6500 Linderson Way, ZIP 98501) returned location code 3406 in **Tumwater**, rate 0.098, result code 2 ("address was updated and found"). The office has an Olympia ZIP but sits in Tumwater's taxing jurisdiction, which is why answers should not infer jurisdiction from a ZIP code. |
| Example question | "What sales tax do I charge in Tumwater?" |
| Effort | S |
| Prototype download | `Rates_26Q4.zip` (4,420 bytes) |
| Priority | **now** |

### 3.3 North Carolina: DOR current rates (CSV export)

| Field | Detail |
|---|---|
| Publisher | North Carolina Department of Revenue |
| Data | <https://www.ncdor.gov/taxes-forms/sales-and-use-tax/sales-and-use-tax-rates/current-sales-and-use-tax-rates>, "Export Table Data" CSV (`files.nc.gov/dor/2026-07/Total Current S&U Tax Rates Effective 7-1-2026.csv`) |
| Documentation | The same page and its "Effective Dates of Local and Transit Tax Rates" page |
| Licence / terms | None found (§11 Q4) |
| Format and access | CSV; an HTML table. No key. |
| Size | Not reported by the server (HEAD gave no length); one row per county |
| Cadence and vintage | Effective July 1, 2026. The CSV was last modified 2026-07-01. |
| Granularity and fields | County, total rate (state 4.75% general, plus local and transit) |
| Coverage | Every county (NC local sales tax is county-level). Examples: Mecklenburg 8.25%, after the additional 1% from July 1, 2026; Wake 7.25%. |
| Personal data | None |
| Fits lexflow | County rows map to county `gov_id`s directly; cities inherit their county's rate. |
| Example question | "Did the sales tax go up in Charlotte this year?" (Mecklenburg, July 1, 2026) |
| Effort | S |
| Prototype download | The CSV above |
| Priority | **now** |

### 3.4 Texas: Comptroller local rate tables (city, county, transit, special purpose districts)

| Field | Detail |
|---|---|
| Publisher | Texas Comptroller of Public Accounts |
| Data | City <https://comptroller.texas.gov/taxes/sales/city.php> with `docs/city-rates.xlsx`; county `county.php`; transit `mta.php`; SPD `spd.php`; combined areas `combined-area.php`; quarterly updates `quarterly-updates/`. Address lookup: the [Sales Tax Rate Locator](https://gis.cpa.texas.gov/search/), an ArcGIS JavaScript app; no documented API was found. |
| Documentation | <https://comptroller.texas.gov/taxes/sales/> |
| Licence / terms | No licence statement was found on the policies page, which links Link, Privacy and Public Information Act policies (§11 Q4). `robots.txt` allows `/taxes/`. |
| Format and access | XLSX, PDF and HTML. No key. |
| Size | `city-rates.xlsx`: size not reported (HEAD), last modified 2026-10-06 |
| Cadence and vintage | Quarterly |
| Granularity and fields | Jurisdiction name, 7-digit local code, local rate, total rate |
| Coverage | Statewide, in separate city, county, transit and SPD tables. The state rate is 6.25%, and "local taxing jurisdictions ... can also impose up to 2 percent ... for a maximum combined rate of 8.25 percent". |
| Personal data | None. (See §7.1 for the separate permit-holder dataset.) |
| Fits lexflow | The rate table. Austin's rows show the overlap problem well: `Austin (Travis Co)` code 2227016, city 1%, total 8.25%, with `Austin MTA` 3227999 at 1%. There are separate rows for the Hays County and Williamson County parts of Austin and for library districts. One city can have several combined rates. |
| Example question | "What is the sales tax rate in Austin, and how do I register to collect it?" (§8.6) |
| Effort | S–M (multi-part jurisdictions) |
| Prototype download | `city-rates.xlsx` and the county, MTA and SPD equivalents (sizes not reported) |
| Priority | **now** |

### 3.5 California: CDTFA rate tables, OData API and Tax Rate API

| Field | Detail |
|---|---|
| Publisher | California Department of Tax and Fee Administration |
| Data | <https://www.cdtfa.ca.gov/taxes-and-fees/sales-use-tax-rates.htm>: `SalesTaxRates10-1-26.xlsx`. OData: `https://www.cdtfa.ca.gov/dataportal/api/odata/Effective_Sales_Tax_Rates`. Address API: `https://services.maps.cdtfa.ca.gov/api/taxrate/GetRateByAddress?address=...&city=...&zip=...` and `GetRateByLngLat` |
| Documentation | Data portal catalog entry (`api/odata/Catalog?$filter=DatasetURL eq 'SalesTaxRates'`); the API page <https://services.maps.cdtfa.ca.gov/>; CDTFA publications 44 and 105 on district taxes |
| Licence / terms | [Conditions of Use](https://www.cdtfa.ca.gov/use.htm): information on the site "unless otherwise indicated, is considered in the public domain". State seals and branding may not be used without permission, and the content carries a full warranty disclaimer. |
| Format and access | XLSX; OData v4 JSON; REST JSON for address and coordinate lookups. No key seen. |
| Size | XLSX 71,474 bytes (last modified 2026-08-31). OData `@odata.count` = 546 rows. |
| Cadence and vintage | Quarterly; "Tax Rates Effective October 1, 2026". Catalog `LastUpdated` 2026-10-01. |
| Granularity and fields | OData fields `Location`, `Rate`, `County`, `Type` (e.g. `City`), `Notes`. The address API returns `rate`, `jurisdiction`, `city`, `county` and `tac` (tax area code). |
| Coverage | Statewide: 546 rows of cities and other areas. Statewide rate 7.25%; district taxes 0.10% to 2.00%. |
| Personal data | None in the table; the address API takes an address (§7.4) |
| Fits lexflow | The rate table from OData, which needs no file at all: 546 rows in one call. |
| Example question | "What is the sales tax in Alameda?" (0.10750 in the sample row) |
| Effort | S |
| Prototype download | One OData call (`$top=1000`), or the 71 KB XLSX |
| Priority | **now** |

### 3.6 New York: Pub 718 and the Jurisdiction/Rate Lookup

| Field | Detail |
|---|---|
| Publisher | New York State Department of Taxation and Finance |
| Data | <https://www.tax.ny.gov/pubs_and_bulls/publications/sales/local_rates_current.htm>: `pdf/publications/sales/pub718.pdf`. Address tool: <https://www8.tax.ny.gov/JRLA/jrlaStart> (interactive) |
| Documentation | <https://www.tax.ny.gov/bus/st/rates.htm>; Tax Bulletin TB-ST-820 (rate publications) |
| Licence / terms | The [website disclaimer](https://www.tax.ny.gov/help/tech/disclaimer.htm) disclaims accuracy and liability. No licence or copyright statement was found (§11 Q4). |
| Format and access | **PDF only** for the rate table. No machine-readable rate file was found, either on DTF's site or by searching data.ny.gov. |
| Size | `pub718.pdf` 215,766 bytes, last modified 2025-01-27 |
| Cadence and vintage | Pub 718 "Effective March 1, 2025". It changes when a locality changes its rate; see "Sales tax locality rate change notices". |
| Granularity and fields | Jurisdiction rates (the PDF itself was not opened). The rates page gives the structure: the state rate is 4%, plus local rates, plus 0.375% in the Metropolitan Commuter Transportation District, and each jurisdiction has a jurisdiction code. |
| Coverage | Statewide. Combined rates "vary in each county and in cities that impose sales tax" (rates page). |
| Personal data | None |
| Fits lexflow | Parse the PDF table once, check every row by hand, and re-check whenever DTF posts a rate change notice. |
| Example question | "What is the sales tax rate in Albany?" |
| Effort | M (PDF table extraction and checking) |
| Prototype download | `pub718.pdf` (215,766 bytes) |
| Priority | **now** |

### 3.7 Illinois: IDOR machine-readable rate files

| Field | Detail |
|---|---|
| Publisher | Illinois Department of Revenue |
| Data | <https://tax.illinois.gov/research/taxrates/sales-tax-rate-machine-readable-files.html>: `ordmache-current.txt` (jurisdiction-wide), `ordmacha-current.txt` (addendum addresses), `grocerymache-current.txt`. Address-specific files: <https://tax.illinois.gov/research/taxrates/machine-readable-file-address-specific.html> |
| Documentation | Layout pages, e.g. "sales tax machine readable file guide county municipality 01-01-2026" |
| Licence / terms | [Legal notices](https://tax.illinois.gov/aboutidor/legalnotices.html): information is provided "as is", with warranties disclaimed. No licence was found (§11 Q4). |
| Format and access | Fixed-width text. No key. |
| Size | `ordmache-current.txt` 31,004 bytes (last modified 2026-06-30). The address-specific file is "approximately 2 GB compressed and 9 GB uncompressed": **avoid it**. |
| Cadence and vintage | Changes "generally" take effect on January 1 or July 1. The current file is "Effective - 08/01/2026". |
| Granularity and fields | Location ID (`xxx-xxxx-x`), location name, county, effective date, general merchandise and drug/medical rates (high and low), receipts and purchases rates |
| Coverage | Statewide, one record per IDOR location ID (jurisdiction-wide rates) |
| Personal data | None |
| Fits lexflow | The rate table. The location name maps to a municipality `gov_id`. |
| Example question | "What sales tax does a shop in Springfield charge?" |
| Effort | S |
| Prototype download | `ordmache-current.txt` (31,004 bytes) |
| Priority | **now** |

### 3.8 Florida: DR-15DSS and the Address/Jurisdiction Database

| Field | Detail |
|---|---|
| Publisher | Florida Department of Revenue |
| Data | `https://floridarevenue.com/Forms_library/current/dr15dss_26.pdf` (Discretionary Sales Surtax Information, from the [forms index](https://floridarevenue.com/Pages/forms_index.aspx)). Addresses: <https://pointmatch.floridarevenue.com/Default.aspx>, with master address list downloads by county or jurisdiction and change logs |
| Documentation | <https://floridarevenue.com/taxes/taxesfees/Pages/discretionary.aspx> |
| Licence / terms | None found (§11 Q4) |
| Format and access | PDF (rates); the address database through web forms and downloads |
| Size | `dr15dss_26.pdf` 204 KB (forms index label). The address files were not measured. |
| Cadence and vintage | DR-15DSS is "updated yearly in November"; the current file is `dr15dss_26.pdf` (2026) |
| Granularity and fields | County surtax rates. The state rate is 6% (§ 212.05 "At the rate of 6 percent"). The surtax applies to "the first $5,000 of the sales amount" on tangible personal property. |
| Coverage | Every county. Rates "currently range from .5% to 2%"; some counties levy none. |
| Personal data | None |
| Fits lexflow | County rows mapped to county `gov_id`s. The $5,000 cap becomes a DMN rule. |
| Example question | "What sales tax do I charge in Miami-Dade?" |
| Effort | S (one small PDF table) |
| Prototype download | `dr15dss_26.pdf` |
| Priority | **now** |

### 3.9 Virginia: rates by locality (XLSX) and the locality code lookup

| Field | Detail |
|---|---|
| Publisher | Virginia Department of Taxation |
| Data | <https://www.tax.virginia.gov/retail-sales-and-use-tax>: `sites/default/files/inline-files/sales-and-use-tax-rates-by-locality-by-date.xlsx`. Locality Code Lookup (FIPS) through Online Services. |
| Documentation | The same page |
| Licence / terms | None found on the page. Another Virginia Tax PDF carries "All Rights Reserved" (§4.4, §11 Q2). |
| Format and access | XLSX. No key. |
| Size | 83,424 bytes, last modified 2026-08-28 |
| Cadence and vintage | Updated when rates change; the workbook is "by date" |
| Granularity and fields | Locality, locality code (FIPS), rate, effective date |
| Coverage | Every county and independent city (one row each in the workbook). General rates: **5.3%** "everywhere else"; **6%** in Central Virginia, Hampton Roads and Northern Virginia (Fairfax County among them); **6.3%** in Charlotte, Danville, Gloucester, Halifax, Henry, Northampton, Patrick and Pittsylvania; **7%** in James City County, Williamsburg and York County |
| Personal data | None |
| Fits lexflow | FIPS codes join to `governments.county_fips` directly; VA independent cities are county equivalents. |
| Example question | "What sales tax do I collect in Fairfax County?" (6%) |
| Effort | S |
| Prototype download | The XLSX (83,424 bytes) |
| Priority | **now** |

### 3.10 Maryland and DC: a single rate (no file needed), plus the version flag

* **MD.** TG § 11-104 sets 6 cents per dollar statewide. There is no local sales tax in MD. The rate needs no table, only
  the statute citation.
* **DC.** The [DC Office of Tax and Revenue](https://otr.cfo.dc.gov/) home page says the increase to 7% "has been
  postponed" and that the general rate "remains 6% through September 30, 2027". But D.C. Code § 47-2002(a) in the
  2026-09-30 snapshot still reads 6.0% before October 1, 2026, and 7.0% from October 1, 2026. `index.py`'s
  `effective()` parses only the leading parenthetical of a heading, so it would not catch this. **The rate table must
  hold DC at 6% with the OTR notice as its source.** The Ask answer must carry a version flag saying the statute text in
  lexflow's snapshot is out of date on this point. The enacting measure was not identified here (§12.1).

---

## 4. Property tax rates

These rates feed questions like docs/questions.md A2 (assessment appeals) and "what will my tax bill be". The
appeal process is already in the statutes and regulations (e.g. 9 DCMR ch. 20; WAC 458-14).

### 4.1 Texas: Comptroller PTAD tax rates and levies

| Field | Detail |
|---|---|
| Publisher | Texas Comptroller, Property Tax Assistance Division |
| Data | <https://comptroller.texas.gov/taxes/property-tax/rates/>: per year (2021–2025), `docs/2025-school-district-rates-levies.xlsx`, `2025-city-rates-levies.xlsx`, `2025-county-rates-levies.xlsx`, `2025-special-district-rates-levies.xlsx` and `2025-total-rates-levies.xlsx` |
| Documentation | The same page. Its legal basis is Tex. Tax Code § 5.091 ("Statewide list of tax rates", present in the corpus). |
| Licence / terms | As §3.4 |
| Format and access | XLSX. No key. |
| Size | Not reported by HEAD. The 2025 city file was last modified 2026-01-30. |
| Cadence and vintage | Annual, published "not later than Jan. 1 of the following year". 2025 is the latest. |
| Granularity and fields | Each taxing unit by county: total tax rate and levy. `*` marks a unit whose appraisal district did not report. |
| Coverage | Every TX taxing unit: counties, cities, school districts and special districts |
| Personal data | None |
| Fits lexflow | Needs the school district and special district sheets from GUS (§2.7) to join to `gov_id`. |
| Example question | "What is the property tax rate in Austin ISD?" |
| Effort | M (name matching to GUS) |
| Prototype download | The five 2025 XLSX files listed above |
| Priority | **next** |

### 4.2 New York: Real Property Tax Rates Levy Data by Municipality (data.ny.gov `iq85-sdzs`)

| Field | Detail |
|---|---|
| Publisher | NYS Department of Taxation and Finance, Office of Tax Policy Analysis |
| Data | <https://data.ny.gov/d/iq85-sdzs> (SODA API `https://data.ny.gov/resource/iq85-sdzs.json`) |
| Documentation | `api/views/iq85-sdzs.json`: column descriptions, plus a "Limitations" note on multi-class taxing in Nassau County and NYC |
| Licence / terms | [OPEN-NY Terms of Use](https://data.ny.gov/dataset/OPEN-NY-Terms-Of-Use/77gx-ii52) (PDF, read): it says the terms impose no attribution, licence re-posting or share-alike requirements, and do not require pre-approval for re-use. The main condition is lawful use. The dataset has no separate licence field. |
| Format and access | Socrata API (JSON or CSV); `$select`, `$where` and `$group` on the server. No key needed at low volume. |
| Size | 64,330 rows (server `count(*)`) |
| Cadence and vintage | Annual. The latest roll year is 2024; the dataset was updated 2025-10-23. |
| Granularity and fields | Roll year, SWIS code, municipality, county, school district code and name, county, municipal and school levies and rates per $1,000 of assessed (or full) value |
| Coverage | Statewide, by municipality and school district segment |
| Personal data | None |
| Fits lexflow | SWIS code to `gov_id` crosswalk. Place pages show county, town and school rates. |
| Example question | "What is the school tax rate in my town?" |
| Effort | S |
| Prototype download | One API query for `roll_year=2024` (2,832 rows; 2023 has 2,911) |
| Priority | **next** |

### 4.3 Maryland: SDAT county and municipal tax rate tables

| Field | Detail |
|---|---|
| Publisher | Maryland State Department of Assessments and Taxation |
| Data | <https://dat.maryland.gov/Pages/Tax-Rates.aspx>: "Tax Rates 2026-2027 - Tax Table & Homestead Credit Caps - July 2026" (PDF) and earlier years back to 2011 |
| Documentation | The same page: "Every August, new tax rates are posted". Rates are reported by local governments. |
| Licence / terms | None found (§11 Q4) |
| Format and access | PDF (6 pages; text extraction failed here, so treat it as a table to transcribe or to parse with a proper PDF tool) |
| Size | 883,275 bytes, last modified 2026-09-18 |
| Cadence and vintage | Annual (July 1 tax bills); 2026–2027 is current |
| Granularity and fields | County and municipal real property and business personal property rates, and homestead credit caps |
| Coverage | Every county, Baltimore City and the municipalities |
| Personal data | None |
| Fits lexflow | Cross-check against city sources. For Baltimore City, the [Bureau of the Budget and Management Research](https://bbmr.baltimorecity.gov/city-tax-rates) lists Fiscal 2027 real property at $2.248 and personal property at $5.62 per $100 of assessed value, among other local taxes (§5.4). |
| Example question | "What is the personal property tax rate on my shop's equipment in Baltimore?" |
| Effort | M (PDF) |
| Prototype download | The 2026–2027 PDF (883,275 bytes) |
| Priority | **next** |

### 4.4 Virginia: Virginia Tax "Local Tax Rates" survey, and Weldon Cooper Center tables

| Field | Detail |
|---|---|
| Publisher | Virginia Department of Taxation (survey PDFs, TY 1999–2025); Weldon Cooper Center for Public Service, University of Virginia (Local Tax Rates book and tables, 2024–2025) |
| Data | <https://www.tax.virginia.gov/local-tax-rates>: `2025-local-tax-rates.pdf`. <https://www.coopercenter.org/virginia-local-tax-rates>: filterable web tables with CSV export (real property nominal rates; tax relief for the elderly and disabled; tangible personal property; meals, transient occupancy, cigarette and admissions taxes). The 2025 book, Data File and Data Dictionary are on `virginia.box.com`. |
| Documentation | The PDF's table of contents (Tables 1–5: county, city, town, county district and city district levies); the Cooper Center Data Dictionary (not opened) |
| Licence / terms | **The Virginia Tax PDF carries "© 2025 Virginia Department of Taxation All Rights Reserved" on every page.** The Cooper Center page footer reads "© 2026 by the rector and visitors of the University of Virginia". No reuse terms were found for the Data File (§11 Q2, Q3). |
| Format and access | PDF; web tables with CSV export; Box-hosted files |
| Size | VA Tax 2025 PDF 474,686 bytes (last modified 2026-03-31). Cooper Center files not measured. |
| Cadence and vintage | Annual: TY 2025 (VA Tax), 2025 (Cooper Center) |
| Granularity and fields | VA Tax: rates per $100 of assessed value on real estate, tangible personal property, machinery and tools, and merchants' capital, for each county, city, town and district. Example: Fairfax County TY 2025 real estate 1.123, TPP 4.570, M&T 2.000, merchants' capital 0.000. Cooper Center: more categories (meals, lodging, tobacco and others). **BPOL coverage in the 2025 Cooper Center book was not confirmed.** |
| Coverage | Every county, city and town (VA Tax Tables 1–5). The Cooper Center book covers "28 Virginia cities, 79 counties, and ... one of the state's incorporated towns". |
| Personal data | None |
| Fits lexflow | Place pages and Ask answers for local property-type taxes. § 58.1-3703 A also names Weldon Cooper population estimates as the basis for BPOL fee caps, which ties these sources to the BPOL DMN (§8.3). |
| Example question | "What is the business personal property tax rate in Fairfax County?" (4.57 per $100 for TPP; check whether a separate business rate applies) |
| Effort | M |
| Prototype download | `2025-local-tax-rates.pdf` (474,686 bytes), after §11 Q2 |
| Priority | **next** |

### 4.5 North Carolina, Washington, Florida, Illinois, California, DC (pointers)

* **NC.** [Property Tax Rates](https://www.ncdor.gov/taxes-forms/property-tax/property-tax-rates) links "County and
  Municipal Property Tax Rates and Year of Most Recent Reappraisal", "County and Municipal Effective Tax Rates" and
  county rates for the last five years. Formats were not checked. Priority: next.
* **WA.** WAC 458-19 (levies, rates and limits) is on disk. DOR property tax statistics were not surveyed.
* **IL.** The IDOR tax rates page says property tax rate tables "are available in the Property Tax Statistics area by
  tax year in tables 27 and 28". That page loads its table by script, and the tables were not retrieved.
* **FL.** 12D FAC is on disk. The DOR Property Tax Oversight millage data were not surveyed.
* **CA.** Rates are county-administered (Proposition 13 base plus voter-approved debt). No statewide table was
  surveyed.
* **DC.** OTR has a [Real Property Tax Rates](https://otr.cfo.dc.gov/page/real-property-tax-rates) page, linked from
  the home page but not opened.

---

## 5. Local business taxes and licences

### 5.1 Virginia BPOL (Va. Code § 58.1-3700 et seq.; 23VAC10-500)

| Field | Detail |
|---|---|
| Publisher | General Assembly (statute, in corpus); Department of Taxation (regulation 23VAC10-500 in the add-on; advisory rulings); each county, city and town (ordinance, rates, forms) |
| Data | Statute: `law.lis.virginia.gov/vacode/58.1-3700/` and following (in `us_va_statutes.parquet`). Regulation: 23VAC10-500, 91 sections (in `us_va_regulations.parquet`). Rulings: the [Laws, Rules & Decisions](https://www.tax.virginia.gov/laws-rules-decisions) library (keyword and document-number search; e.g. ruling 03-11, tax type "BPOL Tax"). Local example: [Fairfax County DTA, Understanding BPOL](https://www.fairfaxcounty.gov/taxes/business/understanding-bpol-tax) and the [rate schedule](https://www.fairfaxcounty.gov/taxes/business/bpol-license-rates). The ordinance is Fairfax County Code ch. 4, art. 7.2, hosted on library.municode.com. |
| Documentation | § 58.1-3701 (guidelines); 23VAC10-500 |
| Licence / terms | Statute and regulation: public law (corpus licence, §11 Q1). Rulings: redacted, with names shown as `*****`. County pages: no licence found. Municode-hosted ordinances: the terms were not read here, and the existing `lexflow/sources/locus.py` note says "where terms allow" (§11 Q5). |
| Format and access | Corpus parquet; HTML pages. No key. |
| Size | Small: 91 regulation sections; one HTML page per locality |
| Cadence and vintage | Statute: annual sessions (§ 58.1-3700 last amended 2026, § 58.1-3703 2022, § 58.1-3706 2021). Local rates are set by ordinance, and Fairfax renews licences each year by **March 1**. |
| Granularity and fields | **State layer (from statute).** § 58.1-3703 A caps the licence fee at $100, $50 or $30 by population band (greater than 50,000; 25,000 to 50,000; under 25,000). A locality over 50,000 had to reduce its fee to no more than $50 by January 1, 2000. Population "may be based on" Weldon Cooper estimates. § 58.1-3706 A allows no tax below $100,000 of gross receipts (over 50,000 population) or $50,000 (25,000–50,000). Above that, rates may not exceed 16¢ per $100 (contracting), 20¢ (retail), 58¢ (financial, real estate and professional) or 36¢ (repair, personal, business and other). **Local layer (Fairfax County DTA).** No fee at $10,000 or less of gross receipts; $30 for $10,001–$50,000; $50 for $50,001–$100,000. Above $100,000 the rate per $100 is 4¢ wholesale (on purchases), 5¢ builders and developers, 11¢ contractors, 17¢ retail, 19¢ business, personal and repair services and money lenders, 24¢ telephone, 26¢ amusement, hotels and renting by owner, and 31¢ professional, consultants and real estate brokers (the DTA rate page; some federally funded R&D prime contracts can get 3¢ with DTA approval). Registration is due "within 75 days of beginning business operations", with a 10% late-filing penalty. Businesses in the cities of Fairfax, Falls Church and Alexandria and the towns of Clifton, Herndon and Vienna are not subject to the county tax. |
| Coverage | VA only. Under § 58.1-3703 A the governing body of any county, city or town may levy it. |
| Personal data | None in statute or regulation. Rulings are redacted. |
| Fits lexflow | A two-layer DMN (§8.3), the "local licence" step already in `curated/va/business.json` (`local_license`, issued by the commissioner of the revenue), and a place-page panel. Charlottesville's hand-researched answer in `curated/places/va/charlottesville.json` already gives its fee tiers. The DMN makes that kind of answer systematic. |
| Example question | "Do I need a BPOL licence in Fairfax County?" (§8.6) |
| Effort | M: the state layer is S; each locality is about half a day of curation and checking |
| Prototype download | None (corpus plus HTML pages) |
| Priority | **now** |

### 5.2 Florida local business tax (Fla. Stat. ch. 205)

The counties' and municipalities' powers to levy are in §§ 205.032 and 205.042, and due dates and penalties in
§ 205.053. All three are in the corpus. Rates and receipts are issued by county tax collectors and city offices; no
statewide table was found or surveyed. Model it like BPOL: state rules from the statute, and a curated local schedule for
each place covered in depth. Priority: next.

### 5.3 Washington city business licences (Business Licensing Service endorsements)

| Field | Detail |
|---|---|
| Publisher | Washington DOR, Business Licensing Service, for partner cities |
| Data | <https://dor.wa.gov/manage-business/city-endorsements>, one page per city, e.g. [Olympia](https://dor.wa.gov/manage-business/city-endorsements/Olympia) |
| Documentation | The same pages |
| Licence / terms | None found (§11 Q4) |
| Format and access | HTML, one page per city. No key. |
| Size | The index page links 223 city URLs (with duplicates); one page per partner city |
| Cadence and vintage | Pages are updated as cities change fees. Olympia's was last modified 2026-10-09. |
| Granularity and fields | Requirement, fee table by gross income and thresholds. Olympia: no fee at $0–$4,000 of gross income and $30 above; nonprofits $0. |
| Coverage | Partner cities only. The index says to contact any other city directly. |
| Personal data | None |
| Fits lexflow | A local licence schedule for each WA city, filled from a uniform page layout (a parser, not hand curation), plus the BLS application as the portal in the process model |
| Example question | "Do I need a city business licence in Olympia, and what does it cost?" |
| Effort | M (one parser for all pages) |
| Prototype download | HTML pages, about 150 requests at 1 per second |
| Priority | **next** |

### 5.4 Maryland: trader's licence, state registration, and Baltimore City's local taxes

* **Trader's licence.** Bus. Reg. § 17-1803 (in corpus, amended 2026) requires one whenever a person "does business as a
  trader in the State". The clerk of the circuit court issues it (§§ 17-1804, 17-1805). lexflow's Baltimore place file already says it costs
  "$20 up to $2,125 depending on the value of your stock-in-trade".
* **State.** A sales and use tax licence is required by TG § 11-702, and the Combined Registration Application opens it
  (§6). The SDAT annual report is due by April 15 for entities and for anyone owning property subject to property tax
  (TP § 11-101). The county or city income tax is set between 2.25% and 3.30% (TG § 10-106).
* **Baltimore City.** The [City Tax Rates](https://bbmr.baltimorecity.gov/city-tax-rates) page, from the Bureau of the
  Budget and Management Research, lists Fiscal 2027 rates:
  * property: real $2.248 and personal $5.62 per $100 of assessed value;
  * income: 3.2% of a city resident's taxable income;
  * transfer 1.5% and recordation $5.00 per $500;
  * hotel 9.5%, admissions 10% and parking 20% of gross receipts;
  * billboard $5.00, or $15.00 if electronic, per square foot;
  * beverage container $0.05;
  * taxi and passenger-for-hire $0.38 per ride, and telephone $4.00 per line;
  * energy tax by user group and unit, plus special benefits district surcharges.

  It is one HTML page, with no licence found (§11 Q4). Priority: **now**, for the Baltimore place page.

### 5.5 Other states (pointers, not surveyed in depth)

* **NC.** City privilege licence taxes were repealed effective July 1, 2015 (§ 160A-211 in corpus).
* **DC.** OTR's [New Business Registration](https://otr.cfo.dc.gov/page/new-business-registration) sets the order:
  register with DLCP if required, complete the FR-500 on MyTax.DC.gov, then return to DLCP for the business licence.
* **CA, IL, NY, TX.** Local business taxes and licences were not surveyed. Where they exist, cities and counties set
  them. LOCUS ordinances (`lexflow/sources/locus.py`) are the first place to look for each city lexflow covers
  in depth.

---

## 6. State registration and forms

These pages list each state's revenue forms and its registration route, for the "register to collect sales tax" step.
Each was opened on 10 October 2026 (HTTP 200, unless noted).

| State | Forms index | Registration route (sales tax) | Statute |
|---|---|---|---|
| VA | <https://www.tax.virginia.gov/forms> (search by category: Sales & Use = `category=5`, Business Registration = `category=8`) | Online registration (`/register-business-virginia`). The certificate "must be displayed prominently" at the registered location. Account numbers begin with 10 for in-state dealers and 12 for remote sellers. | § 58.1-612 (dealer) |
| DC | <https://otr.cfo.dc.gov/page/tax-forms-instructions> | FR-500 New Business Registration on MyTax.DC.gov. Officers must give an SSN or ITIN. | Title 47 |
| MD | <https://www.marylandcomptroller.gov/businesses/tax-services.html>, which links a "Business tax forms and instructions" knowledge-base article on `services.marylandcomptroller.gov`, rendered by script. Filing is through `mdtaxconnect.gov`. The old `marylandtaxes.gov/forms/` returned 404. | Combined Registration Application (online at `interactive.marylandtaxes.gov/webapps/comptrollercra`, found by search, not opened) | TG § 11-702 |
| TX | <https://comptroller.texas.gov/taxes/forms/> | [Texas Online Tax Registration Application](https://comptroller.texas.gov/taxes/permit/) via eSystems ("Allow 2-3 weeks"). § 151.251 requires adequate security unless § 151.254 exempts the applicant. | §§ 151.201, 151.202, 151.251 |
| CA | <https://www.cdtfa.ca.gov/formspubs/> (sales) and <https://www.ftb.ca.gov/forms/> (income) | CDTFA "Register for a Permit, License, or Account" (`/services/registration.htm`) | RTC § 6066 |
| FL | <https://floridarevenue.com/Pages/forms_index.aspx> (one page listing DOR forms with PDF links and sizes) | Not surveyed | § 212.18 |
| NY | <https://www.tax.ny.gov/forms/> | Not surveyed | Tax Law § 1134 |
| IL | <https://tax.illinois.gov/forms.html> | MyTax Illinois (not surveyed) | 35 ILCS 120 |
| WA | <https://dor.wa.gov/forms-publications> | Business Licensing Service (§5.3) | RCW 82.32.030 |
| NC | <https://www.ncdor.gov/taxes-forms> | Not surveyed | § 105-164.29 |

Fit with `fixtures/forms/forms.json`: add a `sales_tax_registration` process and a `federal_ein` step. The existing
`business` process already has the `local_license` step. Each entry needs the usual `verification` block. FL's single
forms index page is the easiest to check automatically. MD's script-rendered pages may need a human check.

---

## 7. Personal data: what to avoid and how to aggregate

### 7.1 Texas Active Sales Tax Permit Holders (data.texas.gov `jrea-zgmq`)

* **What is in it.** The dataset metadata says "Public Domain" and lists 890,307 rows (server `count(*)`, last updated
  2026-10-10). Fields include `taxpayer_name`, `taxpayer_address`, `outlet_name`, `outlet_address`, `outlet_naics_code`,
  `outlet_permit_issue_date` and `taxpayer_organization_type`.
* **Organisation types.** A server-side `$group` returned `CL` 371,284, `IS` 232,801, `CT` 127,564, `CI` 51,504, `CF`
  47,131 and others. `IS` appears to be individual sole owners; confirm against the Comptroller's code list. Those rows
  are people's names and often home addresses.
* **Use.** Only server-side aggregates should ever reach lexflow: `$select=outlet_city, outlet_naics_code, count(*)`
  with `$group`, and no names. Example: "about how many permitted retailers are in Austin", as context on a place page.
  Priority: later or never.

### 7.2 Property assessment rolls (e.g. data.ny.gov `7vem-aaz7`)

The schema includes `primary_owner_first_name`, `primary_owner_last_name`, three more owner name sets and the full
mailing address. **Do not ingest.** If needed, aggregate on the server (exemption counts by municipality). The same
caution applies to county parcel portals in every state.

### 7.3 EO BMF `ICO` field

Drop it on load (§2.6).

### 7.4 Address lookups send the user's address to a state server

The WA URL interface, the CDTFA Tax Rate API, NY's JRLA and FL's Address/Jurisdiction Database all take a street
address. lexflow's users are private people, so an address lookup is collection about them, even if transient.

* **Default:** answer at jurisdiction level ("in the City of Austin, Travis County part: 8.25%"). Ask the user to pick
  their jurisdiction when a ZIP spans several.
* **Opt-in address lookup:** only on an explicit user action, with a notice naming the state service. The request goes
  from the user's browser, not lexflow's server, and lexflow never logs the address.
* The `asked_questions` table must not store the address.

---

## 8. How it plugs into lexflow

### 8.1 Search index (`lexflow/ask/index.py`)

1. **`regulations_<state>.sqlite`**, with the same contentless FTS5 schema, built from the files already on disk (§1.2).
   `retrieve.fused()` searches statutes and regulations, and each hit carries `kind` so the answer can say "regulation".
   The cost is one parameter in `path()`, `_stamp()` and `build()`, plus a `kind` column. No download is needed.
2. **`federal_usc26.sqlite`, `federal_cfr26.sqlite` and `federal_guidance.sqlite`** (§2.1, §2.2, §2.3, §2.5). The plan
   chooses a federal pass when the question names a federal concept (EIN, IRS, deduction, withholding) or when a chosen
   state section names the IRC.
3. **Effective dates.** `effective()` reads only the heading parenthetical. Rate facts come from the rate table (§8.2)
   instead, with `effective_from` and `effective_to`. A statute row whose text schedules a future rate gets a version
   flag when the rate table disagrees (the DC case, §3.10).

### 8.2 New tables (sketch)

```sql
CREATE TABLE IF NOT EXISTS tax_rates (
  state TEXT NOT NULL,
  scheme TEXT NOT NULL,          -- 'va-fips' | 'tx-local-code' | 'wa-loccode' | 'ca-odata' | 'il-locid' | 'nc-county' | 'fl-county' | 'ny-pub718' | 'md' | 'dc'
  code TEXT NOT NULL,            -- the jurisdiction code in that scheme
  gov_id TEXT,                   -- lexflow / Census 14-digit ID, when mapped
  tax TEXT NOT NULL,             -- 'sales_general' | 'sales_local' | 'sales_transit' | 'sales_district' | 'property_real' | 'property_personal' | 'local_income' | 'hotel' | ...
  component TEXT,                -- 'state' | 'county' | 'city' | 'transit' | 'district' | 'total'
  rate REAL NOT NULL,            -- as a fraction (0.0825) or per $100 for property (see unit)
  unit TEXT NOT NULL,            -- 'fraction' | 'per_100' | 'per_1000' | 'per_unit'
  base_note TEXT,                -- e.g. 'first $5,000 of a sale of tangible personal property' (FL surtax)
  effective_from TEXT, effective_to TEXT,
  statute TEXT,                  -- the authorising section, e.g. 'Tex. Tax Code § 321.103'
  source_url TEXT NOT NULL, source_file TEXT, retrieved TEXT NOT NULL,
  PRIMARY KEY (state, scheme, code, tax, component, effective_from)
);
CREATE TABLE IF NOT EXISTS local_license_schedules (
  gov_id TEXT NOT NULL, state TEXT NOT NULL,
  kind TEXT NOT NULL,            -- 'bpol' | 'fl_business_tax' | 'wa_city_endorsement' | 'md_traders'
  class TEXT,                    -- 'retail' | 'professional' | ... (NULL for flat fees)
  min_receipts REAL, max_receipts REAL,
  fee REAL, rate_per_100 REAL,
  due TEXT,                      -- e.g. 'March 1'; 'within 75 days of starting'
  ordinance TEXT, source_url TEXT NOT NULL, checked TEXT NOT NULL, checked_by TEXT,
  PRIMARY KEY (gov_id, kind, class, min_receipts)
);
CREATE TABLE IF NOT EXISTS gov_finance (
  gov_id TEXT NOT NULL, year INTEGER NOT NULL, item TEXT NOT NULL,   -- Census item code, e.g. 'T01'
  amount INTEGER, imputed INTEGER, source TEXT NOT NULL,
  PRIMARY KEY (gov_id, year, item)
);
```

Rows are written by loaders and checked the same way `fixtures/forms/forms.json` entries are: every row has a source
URL and a check date.

### 8.3 Process models and DMN inputs

* **`va_bpol_liability` (DMN, two layers).**
  * Inputs: `gov_id`; `population` (from `governments`, with § 58.1-3703 A's Weldon Cooper basis noted); `in_town_exempt`
    (e.g. inside Herndon, which is not subject to Fairfax County's tax); `gross_receipts`; `business_class`.
  * Layer 1 holds the statutory caps from §§ 58.1-3703 A and 58.1-3706 A, each rule carrying a `source.quote`, as
    `curated/va/business.json` already does.
  * Layer 2 holds the locality's `local_license_schedules` rows.
  * Outputs: `license_required`, `fee`, `rate_per_100`, `tax_due`, `cap_ok`. A local rate above the cap is flagged for
    review, not silently used. Fairfax's 17¢ retail rate is under the 20¢ cap; its 31¢ professional rate is under 58¢.
* **`must_register_sales_tax` (DMN, one per state).**
  * Inputs: sells tangible personal property or taxable services; place of business in the state; remote-seller and
    marketplace status.
  * Outputs: register (yes or no), agency, portal or form, and security or fee.
  * Sources: VA § 58.1-612; TX §§ 151.202 and 151.251; MD TG § 11-702; CA RTC § 6066; FL § 212.18; NY Tax Law § 1134;
    NC § 105-164.29; WA RCW 82.32.030.
* **`combined_sales_tax_rate`** is a lookup in `tax_rates`, not a DMN. The DMN only decides which jurisdictions apply
  (city, county, transit, district) when the user's place is known.
* **"Open a shop" BPMN (composite).** The existing entity formation process (`curated/<state>/business.json`), then
  get an EIN (IRS; SS-4 or the online application; 26 CFR 301.6109-1), then the state tax registration (above), then the
  local licence (BPOL, trader's licence, WA city endorsement or FL business tax receipt), then recurring timer events:
  * sales tax returns;
  * BPOL renewal by March 1 (Fairfax);
  * MD annual report by April 15 (TP § 11-101).
* **Property tax appeal (docs/questions.md A2).** The DMN `appeal_route` gets its regulation sources from the add-on:
  9 DCMR ch. 20 (DC Real Property Tax Appeals Commission) and WAC 458-14 (WA county boards of equalization).

### 8.4 Forms, entities and contacts

* **Forms.** Federal SS-4 and its instructions (§2.4). State registration forms and portals (§6). Local BPOL
  applications (e.g. Fairfax's BPOL Exclusion Worksheet 8TA-EX, linked as a DocuSign PowerForm from the DTA page).
* **Entities and contacts.** These follow `docs/design/entities-contacts.md`:
  * revenue departments (one per state);
  * VA commissioners of the revenue (one per county and city);
  * Fairfax County DTA;
  * MD SDAT and the clerks of the circuit court (trader's licences);
  * TX appraisal districts;
  * FL county tax collectors;
  * WA DOR BLS.

  Official office channels only. The GUS special district and school district sheets (§2.7) supply the property taxing
  units.

### 8.5 Place pages and the Ask answers

* **Place pages: a "Taxes here" panel.**
  * Combined sales tax rate with its parts and effective date.
  * Property rates (real and personal, per $100).
  * The local business licence summary, with fee tiers and due date.
  * The Census tax mix (T01, T09, T28, T40) as context.
  * Each figure links to its source and shows its check date.
* **Ask.** A new `rate` slot in the reference format (`lexflow/ask/reference.py` `SLOTS` already has `fee`,
  `deadline`, `office`, `order`, `yes_no` and `amount`).
  * The answer quotes the statute for the rule, the rate table for the number, and a `version_flags` entry when they
    disagree.
  * `out_of_corpus` entries of kind `agency policy` or `local` name the revenue department or locality page.
  * Federal hits are labelled federal.

### 8.6 The three example questions, worked through

**"What business taxes do I owe to open a shop in Baltimore?"** All of these sources were verified for this note:
* Maryland sales and use tax licence (TG § 11-702) at 6% (TG § 11-104), through the Combined Registration Application.
* Trader's licence from the clerk of the circuit court (Bus. Reg. § 17-1803).
* SDAT annual report by April 15 (TP § 11-101). Business personal property is taxed by the City at $5.62 per $100, and
  real property at $2.248 (BBMR, Fiscal 2027).
* City income tax of 3.2% for city residents (BBMR), within TG § 10-106's 2.25–3.30% range.
* Activity-specific city taxes where they apply: admissions 10%, parking 20%, hotel 9.5%.
* An EIN from the IRS.

lexflow has the statutes today. It would need the BBMR table (one page), the CRA link (forms) and the composite BPMN.

**"What is the sales tax rate in Austin, and how do I register to collect it?"**
* The state rate is 6.25% (Tax Code § 151.051), plus City of Austin 1% and Austin MTA (Capital Metro) 1%, for **8.25%**
  in the Travis County part, per the Comptroller's city table. The table has separate rows for the Hays and Williamson
  County parts and the library districts, so the answer should name the part it assumes.
* Registration: one permit application for each place of business (§ 151.202), filed through the Texas Online Tax
  Registration Application ("Allow 2-3 weeks"). § 151.251 requires adequate security unless an exemption in
  § 151.254 applies.

lexflow has the statutes. It needs `city-rates.xlsx` and the TX `must_register_sales_tax` rules.

**"Do I need a BPOL licence in Fairfax County?"**
* Yes, for a business operating in the county, unless it is inside the cities of Fairfax, Falls Church or Alexandria or
  the towns of Clifton, Herndon or Vienna.
* Register with the DTA within 75 days of starting. There is no fee up to $10,000 of gross receipts, $30 up to $50,000
  and $50 up to $100,000.
* Above $100,000, the class rate applies (e.g. 17¢ per $100 for retail). Renewal is due by March 1.
* The state caps (§§ 58.1-3703 A and 58.1-3706 A) bound the county's choices.

lexflow has the statute and, once indexed, 23VAC10-500. It needs the Fairfax schedule (two DTA pages).

---

## 9. Prototype downloads (each needs the user's approval first)

| # | What | Source | Size | Why |
|---:|---|---|---:|---|
| 1 | VA sales tax rates by locality | `https://www.tax.virginia.gov/sites/default/files/inline-files/sales-and-use-tax-rates-by-locality-by-date.xlsx` | 83,424 B | §3.9 |
| 2 | TX city rates (and county, MTA and SPD equivalents) | `https://comptroller.texas.gov/taxes/sales/docs/city-rates.xlsx` | not reported | §3.4 |
| 3 | CA effective rates | `https://www.cdtfa.ca.gov/dataportal/api/odata/Effective_Sales_Tax_Rates` (one call, 546 rows), or `.../taxes-and-fees/SalesTaxRates10-1-26.xlsx` | 71,474 B (XLSX) | §3.5 |
| 4 | WA location codes and rates | `https://dor.wa.gov/sites/default/files/2026-08/Rates_26Q4.zip` | 4,420 B | §3.2 |
| 5 | NC current rates | NCDOR "Export Table Data" CSV (§3.3) | not reported | §3.3 |
| 6 | IL jurisdiction rates | `https://tax.illinois.gov/content/dam/soi/en/web/tax/research/taxrates/documents/salestaxrates/ordmache-current.txt` | 31,004 B | §3.7 |
| 7 | FL surtax rates | `https://floridarevenue.com/Forms_library/current/dr15dss_26.pdf` | ~204 KB | §3.8 |
| 8 | NY rates | `https://www.tax.ny.gov/pdf/publications/sales/pub718.pdf` | 215,766 B | §3.6 |
| 9 | SST rate files (NC, WA) | `https://streamlinedsalestax.org/ratesandboundry/Rates/NCR2026Q3APR23.csv`, `.../WAR2026Q4AUG27.zip` | 15,870 B + 58,577 B | §3.1 cross-check |
| 10 | Baltimore City tax table | `https://bbmr.baltimorecity.gov/city-tax-rates` (HTML) | one page | §5.4 |
| 11 | Fairfax BPOL pages | `https://www.fairfaxcounty.gov/taxes/business/understanding-bpol-tax` and `/bpol-license-rates` (HTML) | two pages | §5.1 |
| 12 | IRS forms listing | `https://www.irs.gov/forms-instructions-and-publications?items_per_page=200` and its next-page links (16 pages, HTML) | 3,141 rows | §2.4 |
| 13 | IRS Pubs 334 and 583 (XML) | `https://www.irs.gov/pub/irs-sgml/p334.zip`, `p583.zip` | 115,396 B + 65,029 B | §2.5 |
| 14 | 26 CFR Parts 301 and 31 | eCFR API `full/<date>/title-26.xml?part=301` and `?part=31` (gzip) | ≈ 4.7 MB + 2.0 MB XML | §2.2 |
| 15 | IRC Title 26 | `https://uscode.house.gov/download/releasepoints/us/pl/<congress>/<law>/xml_usc26@<rp>.zip` (current release point when the site returns) | not measured | §2.1 |
| 16 | Census finance 2022 | `https://www2.census.gov/programs-surveys/gov-finances/tables/2022/2022_Individual_Unit_File.zip` | 9,719,280 B | §2.7 |
| 17 | NY property tax rates | `https://data.ny.gov/resource/iq85-sdzs.json?roll_year=2024` (API) | 2,832 rows (server count) | §4.2 |
| 18 | TX property tax rates 2025 | five XLSX files on `comptroller.texas.gov/taxes/property-tax/docs/` | not reported | §4.1 |
| 19 | MD SDAT rate table 2026–27 | the `dat.maryland.gov` PDF (§4.3) | 883,275 B | §4.3 |

Rows 1–11 and 13 are under 1 MB of measured files (rows 2 and 5 were not measured, but are small tables). Row 12 is 16
HTML listing pages. Together they cover sales tax rates for all ten states, the three worked examples and the federal
EIN step. Rows 14, 16 and 19 add about 17 MB; rows 15 and 18 were not measured, and row 17 is one API call.

No download is needed to index the regulation files already on disk (§1.2), or to load the GUS special district and
school district sheets (§2.7).

**Not recommended:**
* the IL address-specific file (≈ 2 GB compressed);
* the SST boundary files (15.8 MB for NC and 19.6 MB for WA), unless address-level answers are wanted;
* `us_federal_regulations.parquet` (1.45 GB);
* IRS written determinations (132 MB);
* TX permit holders and assessment rolls (§7).

---

## 10. Effort and order

| Priority | Item | Effort | Depends on |
|---|---|---|---|
| now | Index the regulation files on disk (§1.2, §8.1) | S (1–2 days) | nothing |
| now | `tax_rates` with sales rates for all ten states (§3, rows 1–9) | M (3–5 days, mostly crosswalks to `gov_id`) | user approval for downloads |
| now | VA BPOL two-layer DMN; Fairfax and Charlottesville schedules (§5.1, §8.3) | M | regulation index |
| now | `must_register_sales_tax` DMN and "open a shop" BPMN with IRS EIN step; forms entries (§2.4, §6, §8.3) | M | forms registry |
| now | Baltimore City tax table on the Baltimore place page (§5.4) | S | — |
| next | IRC Title 26 and 26 CFR Parts 301 and 31 indexes (§2.1, §2.2) | M | OLRC site back; approval |
| next | IRS XML publications 334 and 583 (§2.5) | S | — |
| next | Census finance 2022 and the GUS special and school district sheets (§2.7) | S | ID check |
| next | Property tax rates: NY API, TX XLSX, MD PDF, VA PDF, NC (§4) | M | §11 Q2 for VA |
| next | WA city endorsement parser (§5.3); FL local business tax for covered places (§5.2) | M | — |
| later | IRS guidance files from open-us-law (§2.3), after §11 Q1 | S | counsel |
| later | EO BMF (§2.6) | S | — |
| later | Opt-in address-level lookup (WA, CA) with a client-side call (§7.4) | M | privacy design |
| avoid | IL 2 GB address file; SST boundary files without a use; TX permit holders and assessment rolls as rows (§7) | — | — |

---

## 11. Questions for counsel (not decided here)

1. **open-us-law's CC BY-NC 4.0 compilation licence.** lexflow already relies on it for state statutes. Does lexflow's
   use (an open repository, and publishing to the lexipedia sandbox sites) count as non-commercial? The question
   matters more if federal text or IRS guidance is taken from the same compilation, when public-domain primary sources
   (OLRC, eCFR, IRS) exist. The README says earlier snapshots were CC BY 4.0, and that licence "continues to apply to
   copies of those snapshots".
2. **The Virginia Department of Taxation "© 2025 ... All Rights Reserved" notice** on the Local Tax Rates survey PDF.
   May lexflow extract rate figures (facts) from it, store them and republish them with attribution?
3. **Weldon Cooper Center tables and data files.** The page footer reads "© 2026 by the rector and visitors of the
   University of Virginia". No reuse terms were found for the 2025 Data File on Box.
4. **State revenue sites with no stated licence:** WA DOR, TX Comptroller, NC DOR, FL DOR, IL IDOR, VA Tax, the MD
   Comptroller and SDAT, DC OTR, Baltimore City BBMR, Fairfax County DTA, and the SST site. The SST site carries its own
   copyright notice. May lexflow store and republish compiled rate tables? Do disclaimers such as IL's "as is" or NY's
   change anything? (CA's Conditions of Use and Open NY's terms state reuse terms; the IRS's and Census's do too.)
5. **Municode-hosted ordinances**, such as the Fairfax County Code. Can lexflow quote and link them? (Not read here.)
6. **IRS forms.** If lexflow ever pre-fills or reproduces an IRS form, what limits apply? The IRS accepts forms
   "consistent with the official printed versions", and Pub 1167 covers substitute forms but was not read here. Seals
   and names must not imply endorsement (18 U.S.C. § 701).

---

## 12. Open questions, things not verified, and incidents

### 12.1 To check on first load

* The OLRC Title 26 zip size and the current release point. The site was under maintenance on 10 October 2026.
* Whether VA BPOL appears in the Census finance file as T28 or T09 (Fairfax's rows).
* The Census finance file's government ID format against `gov_id`.
* The enacting measure behind DC's postponement of the 7% sales tax. Until it is found, the rate table relies on OTR's
  notice.
* TX organisation type codes (`IS` and the others) from the Comptroller's documentation.
* Whether IL Part 130 (167 sections) and the other regulation counts are complete. Only VA 23VAC10-210 was checked
  against its publisher.
* The NC CSV and TX XLSX sizes (their servers did not report them).

### 12.2 Pages that could not be read

* uscode.house.gov (maintenance); the Archive's 30 August capture was used instead.
* ecfr.gov and federalregister.gov HTML (CAPTCHA redirect for automated clients; the API was used).
* huggingface.co/datasets/vaquill/open-us-law (gated, 401; the publisher's own README was used).
* MD Comptroller pages (script-rendered knowledge base).
* IL property tax statistics (script-loaded table).
* The text of the MD SDAT rate PDF and the Open NY terms PDF could not be extracted by WebFetch. The Open NY terms
  were read with a local text extractor.

### 12.3 Incidents (disclosed)

* **EO BMF size checks.** To measure the EO BMF state CSVs, one-byte `Range` requests were sent to
  `irs.gov/pub/irs-soi/eo_<state>.csv`. For `eo_va.csv` the server answered `206 Partial Content` (total 9,508,327
  bytes). For the nine other states (DC, MD, TX, CA, FL, NY, IL, WA, NC) it ignored the range and sent the whole file
  with `200 OK`. That happened in two passes, and once more for DC while debugging. curl wrote every body to
  `/dev/null`, so nothing was stored, but the files were transferred; the total volume was not measured. Later size
  checks used HEAD only.
* **PDFs saved by WebFetch.** WebFetch saves PDF responses to the session's `tool-results` folder. These copies are
  there: the OPEN-NY Terms of Use (125.8 KB); Virginia Tax's TY 2025 Local Tax Rates (463.6 KB); MD SDAT's 2026–27 rate
  table (862.6 KB); the Census 2006 Classification Manual (2.8 MB); and the IRS EO BMF info sheet (415.5 KB). They are
  documents read for this note, not loaded into lexflow, and can be deleted. The session scratchpad also holds working
  copies of a few HTML pages (e.g. the LIS 23VAC10-210 chapter listing) and text extracted from those PDFs.

---

## Sources (opened 10 October 2026 unless noted)

Federal: [OLRC download page, Aug 30 2026 capture](https://web.archive.org/web/20260830085506/https://uscode.house.gov/download/download.shtml) ·
[17 U.S.C. § 105](https://www.law.cornell.edu/uscode/text/17/105) · [eCFR titles API](https://www.ecfr.gov/api/versioner/v1/titles.json) ·
[eCFR developer resources](https://www.ecfr.gov/reader-aids/ecfr-developer-resources/rest-api-interactive-documentation) (via search; page bot-blocked) ·
[GovInfo bulk ECFR Title 26](https://www.govinfo.gov/bulkdata/ECFR/title-26/ECFR-title26.xml) ·
[IRS use of content](https://www.irs.gov/about-irs/use-of-content-from-irsgov) · [IRS forms list](https://www.irs.gov/forms-instructions-and-publications) ·
[IRS XML source files](https://www.irs.gov/instructions-and-publications-xml-source-files) ·
[IRS file formats](https://www.irs.gov/forms-pubs/using-irs-forms-instructions-publications-and-other-item-files) ·
[EO BMF](https://www.irs.gov/charities-non-profits/exempt-organizations-business-master-file-extract-eo-bmf) ·
[TEOS bulk](https://www.irs.gov/charities-non-profits/tax-exempt-organization-search-bulk-data-downloads) ·
[EO BMF info sheet](https://www.irs.gov/pub/foia/ig/tege/eo-info.pdf) · [IRS robots.txt](https://www.irs.gov/robots.txt) ·
[Census 2022 finance datasets](https://www.census.gov/data/datasets/2022/econ/local/public-use-datasets.html) ·
[Census 2024 finance datasets](https://www.census.gov/data/datasets/2024/econ/local/public-use-datasets.html) ·
[Census finance datasets index](https://www.census.gov/programs-surveys/gov-finances/data/datasets.html) ·
[Classification Manual](https://www2.census.gov/govs/pubs/classification/2006_classification_manual.pdf) ·
[open-us-law README v2026.09.1](https://oss-data-us.vaquill.ai/v2026.09.1/README.md).

Sales tax: [SST rate and boundary files](https://www.streamlinedsalestax.org/Shared-Pages/rate-and-boundary-files) ·
[SST state information](https://www.streamlinedsalestax.org/about-us/state-information) ·
[WA downloadable database](https://dor.wa.gov/taxes-rates/sales-use-tax-rates/downloadable-database) ·
[WA URL interface](https://dor.wa.gov/wa-sales-tax-rate-lookup-url-interface) ·
[NC current rates](https://www.ncdor.gov/taxes-forms/sales-and-use-tax/sales-and-use-tax-rates/current-sales-and-use-tax-rates) ·
[TX sales tax](https://comptroller.texas.gov/taxes/sales/) · [TX city rates](https://comptroller.texas.gov/taxes/sales/city.php) ·
[TX permit](https://comptroller.texas.gov/taxes/permit/) · [CDTFA rates](https://www.cdtfa.ca.gov/taxes-and-fees/sales-use-tax-rates.htm) ·
[CDTFA Tax Rate API](https://services.maps.cdtfa.ca.gov/) · [CDTFA conditions of use](https://www.cdtfa.ca.gov/use.htm) ·
[NY rates](https://www.tax.ny.gov/bus/st/rates.htm) · [NY current local rates](https://www.tax.ny.gov/pubs_and_bulls/publications/sales/local_rates_current.htm) ·
[NY disclaimer](https://www.tax.ny.gov/help/tech/disclaimer.htm) · [IL tax rates](https://tax.illinois.gov/research/taxrates.html) ·
[IL machine-readable files](https://tax.illinois.gov/research/taxrates/sales-tax-rate-machine-readable-files.html) ·
[IL address-specific files](https://tax.illinois.gov/research/taxrates/machine-readable-file-address-specific.html) ·
[IL legal notices](https://tax.illinois.gov/aboutidor/legalnotices.html) · [FL discretionary surtax](https://floridarevenue.com/taxes/taxesfees/Pages/discretionary.aspx) ·
[FL forms index](https://floridarevenue.com/Pages/forms_index.aspx) · [FL address database](https://pointmatch.floridarevenue.com/Default.aspx) ·
[VA retail sales and use tax](https://www.tax.virginia.gov/retail-sales-and-use-tax) · [DC OTR](https://otr.cfo.dc.gov/) ·
[DC new business registration](https://otr.cfo.dc.gov/page/new-business-registration).

Property and local: [TX property tax rates](https://comptroller.texas.gov/taxes/property-tax/rates/) ·
[NY property tax rates dataset](https://data.ny.gov/d/iq85-sdzs) · [OPEN-NY terms](https://data.ny.gov/dataset/OPEN-NY-Terms-Of-Use/77gx-ii52) ·
[MD SDAT tax rates](https://dat.maryland.gov/Pages/Tax-Rates.aspx) · [Baltimore City tax rates](https://bbmr.baltimorecity.gov/city-tax-rates) ·
[VA local tax rates](https://www.tax.virginia.gov/local-tax-rates) · [Cooper Center local tax rates](https://www.coopercenter.org/virginia-local-tax-rates) ·
[NC property tax rates](https://www.ncdor.gov/taxes-forms/property-tax/property-tax-rates) ·
[Fairfax BPOL](https://www.fairfaxcounty.gov/taxes/business/understanding-bpol-tax) · [Fairfax BPOL rates](https://www.fairfaxcounty.gov/taxes/business/bpol-license-rates) ·
[VA Laws, Rules & Decisions](https://www.tax.virginia.gov/laws-rules-decisions) ·
[VA ruling 03-11](https://www.tax.virginia.gov/laws-rules-decisions/rulings-tax-commissioner/03-11) ·
[LIS 23VAC10-210](https://law.lis.virginia.gov/admincode/title23/agency10/chapter210/) ·
[WA city endorsements](https://dor.wa.gov/manage-business/city-endorsements) · [WA Olympia endorsement](https://dor.wa.gov/manage-business/city-endorsements/Olympia) ·
[MD Comptroller business tax services](https://www.marylandcomptroller.gov/businesses/tax-services.html) ·
[TX active permit holders](https://data.texas.gov/Government-and-Taxes/Active-Sales-Tax-Permit-Holders/jrea-zgmq) ·
[NY assessment rolls](https://data.ny.gov/d/7vem-aaz7).
