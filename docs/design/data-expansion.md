# Data expansion: SBA programs, tax and building codes (the roadmap)

Status: design only, 2026-10-10. Nothing was built or changed in the code, and no dataset was downloaded. Revised the
same evening to fix every finding marked wrong or missing in [verify-data-expansion.md](verify-data-expansion.md)
(W1 to W13, M1 to M10). The three research notes were corrected only where that review found errors in them. The
revision's own checks are listed under **Revision checks** below.

It turns three research notes into one ordered plan:

* [data-building-codes.md](data-building-codes.md), cited below as **BC §n**;
* [data-tax.md](data-tax.md), cited as **TAX §n**;
* [data-sba-programs.md](data-sba-programs.md), cited as **SBA §n**.

The user asked what data would let lexflow handle SBA loans and other business programs, and said that tax codes
and building codes "should be included soon to help answer technical questions". The question that started the
work was one lexflow could not answer: "Do I need a building permit for a deck or a shed, and how do I get one?"

**Facts re-checked for this note** (all read-only, on 2026-10-10; one request per host; User-Agent
`lexflow-research/0.1 (https://github.com/alibama/lexflow)`):

* In container `lexflow-app-1`, the regulation files are on disk for VA, DC, MD, FL, IL, NC and WA (14.8, 17.3, 9.4,
  19.2, 40.5, 12.3 and 32.2 MB). There is no file for CA, TX or NY. The search indexes in `/data/index/` are
  `statutes_<st>.sqlite` only.
* `us_va_regulations.parquet` holds 81 rows of 13VAC5-63. Row 13VAC5-63-80 is `in_force`, last amended 2024, and has
  `source_url` <https://law.lis.virginia.gov/admincode/title13/agency5/chapter63/section80/>. Its item 2 reads "One
  story detached structures used as tool and storage sheds, playhouses, or similar uses, provided the building area
  does not exceed 256 square feet …".
* In lexflow's database, the City of Charlottesville is `gov_id` 47210400100000 (county FIPS 51540, population 45,672),
  and Albemarle County is 47100200200000 (51003).
* On the web:
  * [data.sba.gov 7(a)/504 FOIA](https://data.sba.gov/dataset/7a-504-foia) lists its licence as "U.S. Government Works".
  * The FEMA BCAT layer counts 6,722 rows for the 10 states (`returnCountOnly`).
  * FDIC BankFind lists 1,851 Virginia locations, in index `locations_20261009090008`.
  * The Census BPS file `so2025a.txt` is 692,949 bytes, last modified 2026-05-14.
  * The eCFR [titles API](https://www.ecfr.gov/api/versioner/v1/titles.json) shows Titles 13 and 26 up to date as of
    2026-10-07.
  * Treasury's SSBCI table says "DATA CURRENT AS OF 8/25/2026".
  * Virginia's rate workbook is 83,424 bytes, last modified 2026-08-28.
  * The Census 2022 finance file is 9,719,280 bytes.
  * The [DC OTR](https://otr.cfo.dc.gov/) home page says the general sales tax rate "remains 6% through September 30, 2027".
  * Wikibase Cloud's [hosting policy](https://www.mediawiki.org/wiki/Wikibase/Wikibase.cloud/Hosting_policy) (staged
    text, read raw) requires: "The structured data is in the public domain or released under CC0". The licence for
    text in other namespaces must allow "commercial and non-commercial use and derivatives".

**Revision checks** (2026-10-10, evening; read-only GET or HEAD, the same User-Agent, at least 1.2 s between
requests; nothing written remotely; no account or key):

* **data.sba.gov's DKAN datastore** (W6). The import metadata for both FOIA distributions: 7(a) FY2020 to present
  (`fc21a598-913d-5c29-b7c1-1924ce608538`) has 388,338 rows and 43 columns, and 504 FY2010 to present
  (`47fa0223-0a71-562f-85f1-b4b732400efc`) has 117,983 rows and 40 columns. Both counts include `record_number`
  and `asofdate`. The API spec is at `https://data.sba.gov/api/1`. Three grouped counts named only `projectstate`
  or `projectcounty` and a count, so no borrower field was requested. Charlottesville appears as
  "CHARLOTTESVILLE CITY", with 37 7(a) loans and `asofdate` 2026-06-30. The 10 states hold 175,184 7(a) rows and
  55,089 504 rows.
* **HEAD requests.** NES 2024: the old path returns 404, and the `historical-datasets/` path is 4,585,934 B
  (2026-09-29). Also the four BPS 2025 files, Texas `city-rates.xlsx`, the North Carolina CSV, and GovInfo's bulk
  eCFR files for Titles 13 and 26 (no size reported).
* **Pages read:**
  * the Census finance pages;
  * Baltimore Part X and Part II § 105;
  * DHCD's codes page;
  * Georgia v. PRO on LII;
  * S. 4145 on govinfo;
  * the Wikibase Cloud hosting policy (raw);
  * the FDIC API docs;
  * the BCAT layer and item JSON. The item's `owner` was checked to be a person's account and is not reproduced
    here;
  * 13 CFR 120.10, 120.802 and 120.920 (eCFR API);
  * RFC 9309;
  * robots.txt on 35 hosts (§5.2).
* **Documentation saved** to the session scratchpad, not the repository: the FOIA data dictionary (24,529 B .xlsx)
  and the Copyright Office's ASTM v. UpCodes summary (135,772 B PDF).
* **In the container:** 13VAC5-63-10 and -20 and Va. Code § 36-97 were read from the Virginia parquet files, and
  12-A DCMR § 105 and 10-C DCMR § 304 from the DC regulations file. In the repository: `lexflow/pipeline/steps.py`
  lines 298 and 595, and `SLOTS` in `lexflow/ask/reference.py`.
* **Disclosure.** robots.txt was read after these requests, not before them:
  * three eCFR section reads through `/api/versioner/v1/full/`;
  * seven requests to www2.census.gov.

  On at least one reading, both hosts' robots.txt files cover those paths (§5.2). The research notes and the review
  made similar requests. No data from any of them is stored.

Every other fact comes from the three notes. They give the link for each, and this note cites the section. **This
is not legal advice.** Licensing points are collected for counsel in §4.3 and are not decided here.

---

## 0. The short answer

### Now: no download, or about 7 MB of small official files (licence status per §4.1)

| # | Add | Reason |
|---|---|---|
| N1 | **A regulations search index** for VA, DC, MD, FL, IL, NC and WA, built from the files already on disk (BC §3.1, TAX §1.2) | No download is needed. It turns the deck and shed "not found" into a quoted answer, and also makes Virginia's BPOL regulation and the tax rules searchable. |
| N2 | **A curated `permit_required` decision table and a Virginia permit process model**, from state text for VA, DC and NC, with NY as a local opt-in (BC §1, §4.2) | Today the exemption list can be quoted word for word, from text on disk, for VA and DC. In DC the exemptions do not reach historic districts (12-A DCMR 105.2.5). NC's statute settles decks but not sheds (BC §8 item 4). NY's Part 1203 is not on disk, so NY waits for D25. |
| N3 | **A federal rules index**: 13 CFR parts 120, 121, 123, 126, 130 and 131 (about 1.5 MB), SBA SOP 50 10 8.1 (1,072 KB) and IRS Publications 334 and 583 (180 KB) (SBA §3.5, TAX §2.5) | Two of the three SBA questions are answered by rules, and the rules are small and public domain. The eCFR and SOP routes first need the robots.txt decision in §5.2 (O10). |
| N4 | **The `is_small` and `which_sba_product` decision tables** (SBA §4.3) | "Am I small?" and "which loan?" are rule questions. 13 CFR 121.201 has 1,102 table rows. |
| N5 | **A sales tax rate table for all 10 states**, with effective dates (TAX §3; about 1 MB) | Rates must come from revenue departments. DC's statute text in the snapshot says 7%, but the rate is 6%. |
| N6 | **A two-layer BPOL decision table for Virginia**, with Fairfax, Charlottesville and Baltimore City schedules (TAX §5.1, §5.4) | The state caps are already on disk, and these local schedules answer the most common local business-tax question. |
| N7 | **Census Building Permits Survey place files** (3.06 MB, public domain; BC §3.20; the www2.census.gov robots.txt reading is open, §5.2) | They tell which government issues the permit, for example a county for a small Virginia town. |
| N8 | **A program registry seed**: Treasury's SSBCI table (53 programs in the 10 states), the SBA district offices page, and the statute indexes lexflow already has (SBA §3.14, §3.7, §3.19) | These answer "which state programs" and "which SBA office" from official pages, with page reads only. |
| N9 | **Forms registry entries**: SBA Forms 1919, 413 and 1244, IRS SS-4, state sales tax registration, and local permit applications, all as links (SBA §4.4, TAX §6, BC §4.3) | They fill the process steps. lexflow links to these forms and never pre-fills them. |
| N10 | **School and special districts** from the Census workbook already on disk (39,555 special and 12,546 school districts; TAX §2.7) | They name the units that levy each part of a property tax bill, with no download. |

### Next: needs approval, and is larger or depends on a licence answer

| # | Add | Reason |
|---|---|---|
| X1 | **SBA 7(a) and 504 FOIA loan aggregates**, read as grouped, column-limited queries on data.sba.gov's DKAN datastore (D15, D16; SBA §3.1, §5) | This is the only source for "which lenders lend here". It names every borrower, so it enters as aggregates only. Borrower fields are never requested, so no borrower name crosses the network (P3). The 240.5 MB CSVs are not needed. |
| X2 | **FDIC BankFind branches** (about 30,500 rows; SBA §3.17) | They join FOIA lenders by certificate number and give branches per county. |
| X3 | **Resource partners** (SBDC, SCORE, WBC, VBOC), curated by hand, about 40 to 60 rows (SBA §3.7) | No machine-readable source exists, and the partners' sites block automated clients. |
| X4 | **Building departments, revenue offices and SBA offices as agencies with verified contacts**, through phases 1 to 3 of the entities plan ([entities-contacts.md](entities-contacts.md)) | "Who issues the permit" and "who can help" need a checked office channel, and none of that plan's tables exist yet. |
| X5 | **FEMA BCAT code editions** (6,722 rows for the 10 states; BC §3.19) | It is the best answer to "which edition applies here", but no licence is stated, so the operator or counsel decides first. |
| X6 | **Place designations and counts**: Opportunity Zones (277 KB), HUBZone tracts (under 2 MB, after SBA answers), CBP and NES (17.5 MB) (SBA §3.9, §3.16, §3.18) | They give place-page context for business answers. |
| X7 | **Baltimore's public-domain building codes** (`law-xml`, about 15 MB), plus the Maryland and California local-amendment index pages (BC §3.17, §3.4, §3.5) | This is the local building-code layer where it is published openly. |
| X8 | **Federal tax and property data**: 26 CFR parts 301 and 31 (6.7 MB), IRC Title 26 once OLRC is back, the Census finance file (9.7 MB), and property tax rates for NY, TX and MD (VA after counsel) (TAX §2, §4) | These cover the EIN and employer steps, each government's tax mix, and the property tax units. |

### Later

| # | Add | Reason |
|---|---|---|
| L1 | CDFI lists and awards, SBIR awards (91.6 MB), USAspending, SBA disaster loans FY22, and Maryland and New York program datasets (SBA §3.8, §3.10, §3.3, §3.13, §3.19) | Second-round finance context, after the core answers work. |
| L2 | Grants.gov (SBA §3.11) | Its API terms are accepted by use, so only the user can accept them. SBA says it "does not provide grants for starting and expanding a business". |
| L3 | Washington city licence pages, Florida local business tax, an Illinois CDB export, Florida local amendments, NYC's codes, DOE energy codes (TAX §5.2–5.3, BC §3.6, §3.9, §3.21) | Locality-by-locality depth. |
| L4 | IRS guidance from open-us-law, the EO BMF without `ICO`, SAM.gov Assistance Listings (needs a key), and opt-in address lookups (TAX §2.3, §2.6, §7.4; SBA §3.12) | Each waits on counsel, a key or a privacy design. |

### Avoid

| Avoid | Reason |
|---|---|
| PPP, COVID EIDL, RRF and SVOG loan-level files (SBA §3.3) | They name borrowers and describe closed programs. |
| Scraping the SBDC, SCORE or AWBC locators (SBA §3.7) | The sites block automated clients, and AWBC's terms forbid systematic retrieval. |
| Crawling or storing text from ICC, NFPA, IAPMO, UpCodes, Municode, eCode360 or American Legal (BC §2.1, §3.12–3.16) | The publishers' terms and robots rules forbid it. lexflow links to these sites only. |
| Bulk use of Public.Resource.Org copies (BC §2.3) | PRO's legal position is its own. Wait for counsel (BC Q4). |
| `us_federal_regulations.parquet` (1.45 GB, CC BY-NC) (SBA §4.2, TAX §2.2) | The eCFR gives the needed parts in megabytes, in the public domain. |
| Illinois's 2 GB address file and the SST boundary files (35 MB) (TAX §3.1, §3.7) | Answers are made at jurisdiction level, and address-level lookups raise privacy issues (§4.4). |
| Texas permit holders and NY assessment rolls as rows; BCAT `Contact_Email`; IRS written determinations (132 MB) (TAX §7, BC §3.19, TAX §2.3) | Personal data, or bulk with little use. |
| Address lookups from lexflow's server (TAX §7.4) | They would send users' addresses to state servers. |

---

## 1. Decisions that tie the three notes together

| # | Decision | Why |
|---|---|---|
| E1 | **One index schema with two new corpus kinds.** State regulations go in `data/index/regulations_<st>.sqlite`. Federal text uses the pseudo-state `us`: `regulations_us.sqlite` (CFR), `statutes_us.sqlite` (USC Title 26) and `guidance_us.sqlite` (the SBA SOP and IRS publications). All use the same `sec` and `fts` tables as `statutes_<st>.sqlite`, plus a `kind` column. | The notes proposed `regs_<st>` (BC §4.1), `regulations_<st>` (TAX §8.1), `rules_us` (SBA §4.2) and `federal_*` (TAX §8.1). One rule matches the parquet names (`us_<st>_regulations.parquet`) and the entities plan's `state='us'` for federal rows. |
| E2 | **Rules first, numbers second.** | All three notes agree (SBA B1, TAX order, BC order). The rules are small, public domain and quotable. |
| E3 | **Rates, code editions and designations are dated facts in tables**, with `effective_from`, `effective_to`, the source URL and a check date. They are never read from statute text. | DC's § 47-2002 in the 2026-09-30 snapshot schedules 7%, but OTR says 6% through 30 September 2027 (TAX §3.10). Code editions and HUBZone status also change on dates. |
| E4 | **Personal data enters only as aggregates, under one rulebook** (§4.4). | The SBA FOIA, BPS, SBIR, EO BMF and state award files all carry people. The rules mirror payroll §6.1. |
| E5 | **Model codes enter as facts and links only.** Thresholds and conditions are stored with a citation and edition, and the answer links the free official view. No model-code text, unadopted text or redlines are stored (BC §2.4). | ICC's terms, and the line drawn in ICC v. UpCodes. This is pending counsel. |
| E6 | **One optional Setup card per domain**, each with credits. A card lists the sources it reads and those it does not, with the reason (payroll P1, P7). | Every outside dataset in lexflow is introduced, credited, opted into and refreshed on its Setup card. |
| E7 | **Offices and organisations are entities**, keyed in the entities plan's spelling (its D2). Their contacts enter through its review queue and are shown only once checked (its D7, D8). | "Who issues the permit" and "who can help" are answered by an entity with a checked office channel. |
| E8 | **Nothing is fetched when someone asks** (payroll P6). No address and no business financials leave the user's machine through lexflow (TAX §7.4). | Privacy of the people using lexflow. |
| E9 | **New code goes in new modules**: `lexflow/corpus/`, `lexflow/business/`, `lexflow/tax/` and `lexflow/codes/`, beside the planned `lexflow/entities/`. The Ask wiring in `lexflow/ask/*` waits for the AskBench freeze to end (entities plan D13). | The benchmark freeze. Until then, the new indexes serve place pages, the CLI and curated models. |
| E10 | **Publishing stays user-triggered, with a dry run first.** The Wikibase receives only public-domain or CC0-compatible facts (§4.2). | Wikibase Cloud's hosting policy (quoted above), and the publishing rules in memory. |

### 1.1 Key spellings (reconciled)

The notes used a few spellings that differ from the entities plan's rule (lower-case slugs joined by `_`). This plan
uses:

| Thing | Key | Note |
|---|---|---|
| State building-code agency | `lexflow:agency:va:dhcd`, `lexflow:agency:dc:dob`, `lexflow:agency:wa:sbcc`, … | BC §4.4 as written |
| Local building department | `lexflow:office-type:<st>:building_official` → instance `lexflow:agency:<gid>:building_official` | BC §4.4 wrote `building-official`; slugs use `_` |
| Revenue offices | `lexflow:agency:<st>:department_of_taxation` (by name), `lexflow:office-type:va:commissioner_of_the_revenue` | TAX §8.4 |
| SBA and its offices | `lexflow:agency:us:sba`; `lexflow:agency:us:sba_<district>_district_office`, part-of SBA | SBA §4.1 proposed `lexflow:office:sba-district:<slug>`; an agency key avoids a new kind |
| Lenders, CDCs, CDFIs, resource partners | `lexflow:lender:fdic:<cert>`, `lexflow:lender:ncua:<charter>`, `lexflow:lender:sba:<LocationID>`, `lexflow:cdc:<slug>`, `lexflow:cdfi:<slug>`, `lexflow:partner:<sbdc\|score\|wbc\|vboc>:<slug>` | New entity kinds, not government bodies. They need a row in the entities plan's §1.2 table and a P25 key on the Wikibase (open question O6) |
| Programs | `lexflow:program:<us\|st\|gid>:<slug>`, e.g. `lexflow:program:us:sba_7a` | SBA §4.1 |
| Forms processes | `sba_loan`, `sales_tax_registration`, `building_permit` | `forms.json` uses `_` (for example `record_sealing`); SBA §4.4 wrote `sba-loan` |

---

## 2. Ingest, store, refresh and use

### 2.1 Six new Setup cards

All six are `optional`, follow the `Step` dataclass in `lexflow/pipeline/steps.py`, and are run by the operator from
the Setup page. Nothing runs on a timer by default. A card shows a source as *due* when its `retrieved_at` is older
than its refresh interval (payroll §5). Proposed order in `STEPS`: `regulations` and `federal-rules` after `index`;
then `districts`, `tax-rates`, `building-codes` and `business-programs` after `contacts`, before `score`.

| `id` | Title | `needs` | `params` | Cost (shown on the card) | Status rule | Credits |
|---|---|---|---|---|---|---|
| `regulations` | Make the state regulations searchable | `statutes` (run with `regulations`) | `states`, `force` | No new download where the regulations add-on is already on disk, as in this container; seconds per state. On a fresh install the card first needs the `statutes` step run with `regulations`, which `steps.py` costs as "regulations add 2.1 GB". The card shows that cost and needs the same approval | `done` when every `us_<st>_regulations.parquet` on disk has a ready `regulations_<st>.sqlite` | `used_for(OPEN_US_LAW, …)`, `used_for(SQLITE_FTS5, …)` |
| `federal-rules` | Make federal rules searchable | — | `force`, `parts` | About 2.8 MB at first (13 CFR, the SOP, two IRS publications); 26 CFR parts later add 6.7 MB | `done` when each configured part's stored `latest_amended_on` equals the eCFR's, and the SOP version matches SBA's page | `ECFR`, `SBA_SOP`, `IRS`, later `OLRC` |
| `districts` | Load school and special districts | `governments` | `states` | No download: the same Census workbook | `done` when both sheets are loaded for the loaded states | `used_for(CENSUS_GUS, …)` |
| `tax-rates` | Load tax rates and local business-tax schedules | `governments` | `states`, `force` | About 1 MB of rate files for 10 states; 9.7 MB Census finance (next) | `done` when every loaded state has rate rows whose source is not due, and every curated schedule is newer than 18 months | `REVENUE[st]` per state, `DC_OTR`, `IRS`, `CENSUS_FINANCE`; curated schedules use `credits_note` |
| `building-codes` | Load building-code editions and permit offices | `governments` | `states`, `force` | 3.06 MB BPS; BCAT 5–15 MB after a decision; Baltimore 15 MB | `done` when each loaded state has `permit_issuers` rows and, once enabled, `code_adoptions` rows | `CENSUS_BPS`, `FEMA_BCAT` (when enabled), `BALTIMORE_CODES`, `MD_LABOR`, `CA_BSC`, `ICC_FREE_VIEW` (link only) |
| `business-programs` | Load SBA and state business-finance programs | `governments` | `states`, `force`, `sources` | Page reads first. Once approved (next): grouped FOIA counts and a column-limited projection from the DKAN datastore, covering about 230,000 loan rows for the 10 states, an estimated 35 to 65 MB of JSON pages (not measured) | `done` when every enabled source in the loaded states has a `scans` row (`source='business:<id>'`) newer than its refresh interval | `SBA_FOIA`, `SBA_PAGES`, `TREASURY_SSBCI`, `FDIC_BANKFIND`, `SBA_HUBZONE`, `CDFI_OZ`, `CENSUS_CBP_NES`, `CENSUS_NAICS` |

The curated decision tables (`permit_required`, `va_bpol_liability`, `is_small`, `which_sba_product`,
`must_register_sales_tax`) are not Setup sources. They are reference models in `curated/`, written and reviewed by
Claude and checked by `lexflow check-curated`, like `curated/va/business.json`. The existing `build` and `publish`
rules apply to them: only Claude-reviewed or two-extraction-agreed models go to Lexipedia.

The existing `index` card and the `ask` composite need one more credit each once the Ask pipeline searches the new
indexes: `used_for(ECFR, …)` and the regulations use of `OPEN_US_LAW`.

### 2.2 Credit lines (proposed constants for `lexflow/pipeline/credits.py`)

These follow `credit(name, by, licence, url, use, cite="", note="", cite_by="lexflow", licence_url="")`. The licence
text is what the maker's own page says, as the notes report it. Where a page states no licence, the credit says so.
`credits.py` is not edited by this note.

```python
OPEN_US_LAW_REGS = used_for(
    OPEN_US_LAW, "State regulations (the add-on): building codes, tax and licensing rules, each section with the URL "
                 "of its official publisher. CA, NY and TX have no regulations file in this release")
ECFR = credit(
    "eCFR, the Electronic Code of Federal Regulations (versioner API)",
    "Office of the Federal Register and the Government Publishing Office",
    "US government work (17 U.S.C. § 105); the eCFR's own terms page was not readable to automated clients",
    "https://www.ecfr.gov/", "13 CFR parts 120, 121, 123, 126, 130 and 131 (SBA) and, later, 26 CFR parts 31 and 301 "
    "(IRS): the federal rules index and the size-standard table",
    licence_url="https://www.law.cornell.edu/uscode/text/17/105",
    note="An editorial compilation, not the official annual CFR edition. Each quote cites the section and links it.")
OLRC = credit(
    "United States Code, Title 26 (USLM XML)", "Office of the Law Revision Counsel, U.S. House of Representatives",
    "US government work (17 U.S.C. § 105)", "https://uscode.house.gov/download/download.shtml",
    "The Internal Revenue Code in the federal statutes index", licence_url="https://www.law.cornell.edu/uscode/text/17/105")
SBA_SOP = credit(
    "SOP 50 10 8.1, Lender and Development Company Loan Programs", "U.S. Small Business Administration",
    "Public domain (\"Government information on SBA.gov is in the public domain\")",
    "https://legacy.sba.gov/document/sop-50-10-lender-development-company-loan-programs",
    "7(a) and 504 lending rules in force from 1 October 2026, split at its headings for the federal guidance index",
    licence_url="https://www.sba.gov/about-sba/open-government/about-the-sba-gov-website/#disclaimer",
    note="SBA asks that its information be given appropriate acknowledgement.")
SBA_FOIA = credit(
    "SBA 7(a) and 504 FOIA loan data", "U.S. Small Business Administration, Office of Capital Access",
    "U.S. Government Works", "https://data.sba.gov/dataset/7a-504-foia",
    "Loan counts and median loan sizes by county, lender, program and industry sector",
    note="Read as grouped, column-limited queries on data.sba.gov's DKAN datastore, through an allowlist: borrower "
         "names and addresses are never requested. A count is shown from 5 loans, an amount from 11; minimum and "
         "maximum amounts are never shown (docs/design/data-expansion.md §4.4). Vintage: the distribution IDs and "
         "asofdate of each run.")
SBA_PAGES = credit(
    "SBA district offices, CDC and microlender lists, Lender Match, Forms 1919, 413 and 1244",
    "U.S. Small Business Administration", "Public domain (sba.gov statement)",
    "https://www.sba.gov/about-sba/sba-district-offices/",
    "SBA offices, CDCs and microlenders as organisations; links to Lender Match and the forms",
    licence_url="https://www.sba.gov/about-sba/open-government/about-the-sba-gov-website/#disclaimer",
    note="Organisation channels only: staff names, mailboxes and phones on the lists are dropped. lexflow links to "
         "Lender Match and never submits it.")
TREASURY_SSBCI = credit(
    "SSBCI capital program list of programs and contacts", "U.S. Department of the Treasury", "US government work",
    "https://home.treasury.gov/policy-issues/small-business-programs/state-small-business-credit-initiative-ssbci/"
    "capital-program-list-of-programs-and-contacts",
    "State loan, guarantee and equity programs and the bodies that run them",
    note="The contact column is not read; answers link each program's own page.")
FDIC_BANKFIND = credit(
    "FDIC BankFind Suite API (institutions and locations)", "Federal Deposit Insurance Corporation",
    "No licence stated on the API documentation (federal data)", "https://api.fdic.gov/banks/docs/",
    "Bank branches per county, joined to SBA lenders by FDIC certificate number",
    note="Keys are \"currently not required\". If FDIC starts requiring one, the user requests it and keeps it in "
         ".env; lexflow never registers for one.")
SBA_HUBZONE = credit(
    "HUBZone qualified census tracts and non-metropolitan counties (map service)",
    "U.S. Small Business Administration", "Not stated; the map's own service, not a published API",
    "https://maps.certify.sba.gov/hubzone/map/help", "HUBZone status per tract and county on place pages",
    note="The map is not updated again until July 2028. Whether an exact address qualifies is checked on SBA's map.")
CDFI_OZ = credit(
    "Designated Qualified Opportunity Zones", "U.S. Department of the Treasury, CDFI Fund", "Not stated (federal)",
    "https://www.cdfifund.gov/opportunity-zones", "Opportunity Zone tracts on place pages",
    note="The 2018 designations; tracts for new investment from 1 January 2027 are being nominated now.")
CENSUS_CBP_NES = credit(
    "County Business Patterns 2023 and Nonemployer Statistics 2024", "U.S. Census Bureau",
    "Public domain (US government work)", "https://www2.census.gov/programs-surveys/cbp/datasets/2023/",
    "Business counts by county and industry, as context")
CENSUS_NAICS = credit(
    "North American Industry Classification System 2022", "U.S. Census Bureau", "Public domain (US government work)",
    "https://www.census.gov/naics/?48967", "Industry titles for the size-standard decision table")
CENSUS_FINANCE = credit(
    "2022 Census of Governments: Finance, individual unit file", "U.S. Census Bureau",
    "\"Datasets are usually for public use, and users may analyze, extract, customize and publish statistics\"",
    "https://www.census.gov/data/datasets/2022/econ/local/public-use-datasets.html",
    "Each government's tax mix (property, sales, licence and income taxes) on place pages",
    licence_url="https://www.census.gov/programs-surveys/gov-finances/data/datasets.html",
    note="The licence words are on the finance datasets index page, not on the 2022 public-use page.")
IRS = credit(
    "IRS forms, instructions and publications (product list and XML source files)", "Internal Revenue Service",
    "Not subject to copyright and may be freely copied; credit is requested",
    "https://www.irs.gov/forms-instructions-and-publications",
    "The EIN step (Form SS-4) in the business process; Publications 334 and 583 in the federal guidance index",
    licence_url="https://www.irs.gov/about-irs/use-of-content-from-irsgov",
    note="IRS and Treasury seals and names are never used to imply endorsement. lexflow links to forms and never "
         "fills them.")
REVENUE = {   # one credit per state rate source (TAX §3); MD needs none (one statutory rate, TG § 11-104)
    "va": credit("Sales and use tax rates by locality", "Virginia Department of Taxation", "No licence stated",
                 "https://www.tax.virginia.gov/retail-sales-and-use-tax", "Sales tax rates by county and city"),
    "tx": credit("Local sales and use tax rates", "Texas Comptroller of Public Accounts", "No licence stated",
                 "https://comptroller.texas.gov/taxes/sales/city.php", "City, county, transit and district rates"),
    "ca": credit("Sales and use tax rates", "California Department of Tax and Fee Administration",
                 "Public domain unless otherwise indicated (Conditions of Use); state seals excluded",
                 "https://www.cdtfa.ca.gov/taxes-and-fees/sales-use-tax-rates.htm", "City and district rates",
                 licence_url="https://www.cdtfa.ca.gov/use.htm"),
    "wa": credit("Sales and use tax rates, downloadable database", "Washington State Department of Revenue",
                 "No licence stated", "https://dor.wa.gov/taxes-rates/sales-use-tax-rates/downloadable-database",
                 "Rates by location code"),
    "nc": credit("Current sales and use tax rates", "North Carolina Department of Revenue", "No licence stated",
                 "https://www.ncdor.gov/taxes-forms/sales-and-use-tax/sales-and-use-tax-rates/current-sales-and-use-tax-rates",
                 "County rates"),
    "il": credit("Sales tax rate machine-readable files", "Illinois Department of Revenue",
                 "Provided \"as is\"; no licence stated",
                 "https://tax.illinois.gov/research/taxrates/sales-tax-rate-machine-readable-files.html",
                 "Rates by IDOR location", licence_url="https://tax.illinois.gov/aboutidor/legalnotices.html"),
    "fl": credit("Discretionary Sales Surtax Information (DR-15DSS)", "Florida Department of Revenue",
                 "No licence stated", "https://floridarevenue.com/taxes/taxesfees/Pages/discretionary.aspx",
                 "County surtax rates"),
    "ny": credit("Publication 718, local sales and use tax rates", "New York State Department of Taxation and Finance",
                 "No licence stated; website disclaimer",
                 "https://www.tax.ny.gov/pubs_and_bulls/publications/sales/local_rates_current.htm",
                 "Jurisdiction rates, checked by hand", licence_url="https://www.tax.ny.gov/help/tech/disclaimer.htm"),
    "dc": credit("Office of Tax and Revenue", "Office of the Chief Financial Officer, District of Columbia",
                 "No licence stated", "https://otr.cfo.dc.gov/",
                 "The 6% rate in force, which the statute snapshot misstates"),
}
FEMA_BCAT = credit(
    "Building Code Adoption Tracking (BCAT)", "Federal Emergency Management Agency",
    "No licence stated; the map's disclaimer applies",
    "https://www.fema.gov/emergency-managers/risk-management/building-science/bcat",
    "Building, residential and existing-building code editions for each jurisdiction",
    note="General information only and may lag local updates, so answers say to confirm with the building "
         "department. The Contact_Email column is never requested, and the ArcGIS item's owner field (a "
         "contractor employee's account) is never copied: the credit names FEMA.")
CENSUS_BPS = credit(
    "Building Permits Survey, annual place files", "U.S. Census Bureau", "Public domain (US government work)",
    "https://www.census.gov/construction/bps/", "Which governments issue building permits",
    note="Counts under 5 buildings are not shown; construction values are not stored.")
BALTIMORE_CODES = credit(
    "Baltimore City Building, Fire, and Related Codes (law-xml)", "Baltimore City Department of Legislative Reference",
    "Public domain (the code site's statement); the repository has no licence file",
    "https://github.com/baltimore-legref/law-xml",
    "Baltimore's local building-code layer, quoted with links to codes.baltimorecity.gov")
ICC_FREE_VIEW = credit(
    "ICC Digital Codes, free view", "International Code Council",
    "ICC Terms of Use: no robots, copying, or display on other websites", "https://codes.iccsafe.org/",
    "Not called by lexflow: answers link the model-code section here; no model-code text is stored",
    licence_url="https://www.iccsafe.org/about/terms-of-use/")
```

The Maryland Labor county and municipal pages and the California BSC ordinance lists get credits of the same shape
(state web pages, no licence stated). The curated local schedules (BPOL tiers, Baltimore's tax table, building
departments) follow the `local` step's precedent: `credits=[]` with `credits_note="No outside dataset: each schedule
was researched from the locality's own official pages and carries its URL and check date."`

### 2.3 Stores

**Index files**, all contentless FTS5 with the `statutes_<st>.sqlite` layout plus `kind`:

| File | Built from | First contents |
|---|---|---|
| `regulations_<st>.sqlite` (VA, DC, MD, FL, IL, NC, WA) | `us_<st>_regulations.parquet` on disk, `act_status='in_force'` only | Everything in force. Rows marked `superseded` (DC's 2013 supplements, 376 sections) and repealed stubs (1,684 of NC's 2,189 tax rows) are left out (BC §1.4, TAX §1.2) |
| `regulations_ny.sqlite` | 19 NYCRR Part 1203 (DOS PDF, 260 KB) | Next phase, once the PDF download is approved |
| `regulations_us.sqlite` | eCFR XML | 13 CFR 120, 121, 123, 126, 130, 131; then 26 CFR 301, 31; later 7 CFR 4280 and 5001 |
| `statutes_us.sqlite` | OLRC USLM XML | 26 U.S.C. |
| `guidance_us.sqlite` | SOP .docx, IRS XML | SOP 50 10 8.1 (cited by section and chapter), Pubs 334 and 583 |

**Tables** (new). The sketches are in the notes and are not repeated in full. This plan consolidates them as
follows:

| Table | One row per | Defined in | Synced through Turso? |
|---|---|---|---|
| `programs` | federal, state or local program | SBA §4.1 | yes (public facts) |
| `program_cells` | (county FIPS, five-year window, program, NAICS sector) and (county, window, lender key) | SBA §4.1, rules §4.4 | yes, published cells only |
| `place_designations` | (tract or county, designation) | SBA §4.1 | yes |
| `place_stats` | (county FIPS, source, year, NAICS, measure) for CBP, NES and BPS counts | this note | yes |
| `tax_rates` | (state, scheme, code, tax, component, effective_from) | TAX §8.2 | yes |
| `local_license_schedules` | (gov_id, kind, class, min_receipts) | TAX §8.2 | yes |
| `gov_finance` | (gov_id, year, Census item code) | TAX §8.2 | yes |
| `districts` | school or special district (14-digit Census ID) | this note | yes |
| `code_adoptions` | (gov_id, code, source) | this note, below | yes, after the BCAT decision (§4.2) |
| `permit_issuers` | gov_id | this note, below | yes |
| `agencies`, `office_types`, `entity_links`, `contact_status` | entity, link, check | [entities-contacts.md](entities-contacts.md) §1.3, §2.1 | yes (federal rows use `state='us'`) |

Two design changes from the notes:

* **Districts get their own table** instead of rows in `governments` (which TAX §2.7 suggested). `st_score` sets its
  total as `count(*) FROM governments` × the number of questions. Adding 52,101 districts would score and map
  bodies that no question covers.
* **Code editions and permit offices** need tables that no note defined:

```sql
CREATE TABLE IF NOT EXISTS code_adoptions (
  gov_id TEXT NOT NULL, state TEXT NOT NULL,
  code TEXT NOT NULL,             -- building | residential | existing | energy | wui
  model TEXT, edition TEXT,       -- e.g. 'IRC', '2021'; or 'USBC', '2021'
  effective_from TEXT,
  basis TEXT NOT NULL,            -- state (statewide rule) | local (ordinance) | none ("No Residential Code")
  authority TEXT,                 -- '13VAC5-63-10', 'WAC 51-51-003', or the local ordinance
  source TEXT NOT NULL,           -- fema-bcat | state-rule | il-cdb | ca-bsc | md-labor
  source_url TEXT NOT NULL, data_currency TEXT, retrieved_at TEXT NOT NULL,
  match TEXT,                     -- how the row was tied to gov_id: name+county | reviewer
  updated_at TEXT NOT NULL, origin TEXT,
  PRIMARY KEY (gov_id, code, source)
);
CREATE TABLE IF NOT EXISTS permit_issuers (
  gov_id TEXT PRIMARY KEY, state TEXT NOT NULL,
  issues_permits INTEGER,         -- 1 when BPS lists the place; NULL when unknown (absence is not proof, see below)
  issuer_gov_id TEXT,             -- who issues for it, e.g. the county for a Virginia town under § 36-105 A
  bps_id TEXT, survey_year INTEGER, months_reported INTEGER,
  buildings INTEGER, units INTEGER,   -- NULL when under 5; construction values are never stored
  basis TEXT NOT NULL,            -- bps | statute | reviewer
  source_url TEXT NOT NULL, retrieved_at TEXT NOT NULL, updated_at TEXT NOT NULL, origin TEXT
);
```

BPS counts only the county office when a city and its county both issue permits (BC §3.20). A place missing from
BPS therefore gets `issues_permits = NULL`, not 0, until the state rule or a reviewer settles it.

### 2.4 Refresh

| Source | Publisher's cadence | lexflow refresh (operator-triggered; card marks it due) | Cheap check first |
|---|---|---|---|
| open-us-law regulations | quarterly snapshot (v2026.09.1, 2026-09-30) | with each new release, through the `statutes` step | the existing index stamp (`_stamp`) |
| eCFR parts | daily | monthly | `titles.json` `latest_amended_on` for Titles 13 and 26 (one request) |
| SOP 50 10 | on an SBA information notice (8.1 effective 2026-10-01) | monthly check | the SOP page lists the current version |
| IRS publications and forms list | per revision | yearly in January; forms monthly through the forms checker | HEAD `Last-Modified` |
| OLRC Title 26 | per release point | quarterly | the download page's release point |
| SBA FOIA | quarterly, about a month after quarter end | August, November, February, May | the DKAN import's `numOfRows` and one grouped `asofdate` count (the distribution IDs change when SBA replaces a file, so they are re-read from the dataset record) |
| FDIC locations | index rebuilt often (2026-10-09) | monthly | `meta.index.createTimestamp` |
| SSBCI table, district offices, CDC and microlender lists | when changed (SSBCI 8/25/2026) | quarterly | the page's "current as of" line |
| Resource partners (curated) | — | through the entities `recheck` step's tiers | `checked_at` |
| HUBZone | frozen until July 2028 | July 2028 | — |
| Opportunity Zones | new tracts from 2027-01-01 | January 2027 | Treasury notice |
| CBP, NES | yearly (CBP 2023 and NES 2024 latest) | yearly | directory listing |
| Sales tax rates | quarterly (TX, CA, WA, SST), January and July (IL), yearly in November (FL), on change (VA, NY, NC) | quarterly, before each quarter starts; NY on DTF's rate-change notices | HEAD `Last-Modified`; CA OData `LastUpdated` |
| Local licence schedules | yearly by ordinance (Fairfax renews by 1 March) | yearly in January; older than 18 months becomes link only | `checked` |
| Census finance | yearly survey; full census every 5 years | yearly (2024 file released July 2026) | HEAD |
| Property tax rates | yearly | TX January, MD August, NY October | HEAD or Socrata `rowsUpdatedAt` |
| BCAT | quarterly (`Data_Currency` 2026-06-30) | quarterly | one `outStatistics` call on `Data_Currency` |
| BPS | yearly (2025 files on 2026-05-14) | yearly in June | HEAD |
| Baltimore `law-xml` | pushed often (2026-09-28) | quarterly | GitHub `pushed_at` |

Display follows freshness: a rate row past its `effective_to` is never shown as current, and a source its publisher
has not updated for 18 months drops to "link only" (payroll §5).

### 2.5 Where each source is used

| Source | Ask search index | Decision tables (DMN inputs) | Forms | Entities and contacts | Place pages |
|---|---|---|---|---|---|
| State regulations (on disk) | `regulations_<st>` beside statutes, labelled "regulation" | `permit_required` (VA, DC rules quote 13VAC5-63-80 and 12-A DCMR 105.2); BPOL layer 1 (23VAC10-500); `appeal_route` sources (9 DCMR ch. 20, WAC 458-14) | — | state code agencies (DHCD, DOB, SBCC) | "Building permits", "Taxes here" |
| 13 CFR, SOP | `regulations_us`, `guidance_us` | `is_small` (NAICS code, receipts or employees, affiliates, program, tangible net worth, net income); `which_sba_product` (amount, use of proceeds, owner occupancy, ineligible type, credit elsewhere) | SBA 1919, 413, 1244 (`sba_loan`) | `lexflow:agency:us:sba` | — |
| NAICS 2022 | — | `is_small` industry titles | — | — | — |
| SBA FOIA | — | — | — | lenders and CDCs, keyed by FDIC CERT or SBA LocationID; 504 third-party lenders only when they pass P7 | "Business finance here": counts by program and sector, lenders with ≥ 5 loans |
| FDIC | — | — | — | lender entities and branches | bank branches here |
| SSBCI, statute hits | statutes already indexed | `programs.inputs` reuse the DMN variables | — | implementing bodies (VSBFA, IBank, …) | state programs |
| District offices, CDC and microlender lists, partners | — | — | Lender Match as a linked step | SBA offices (`serves` = county FIPS), CDCs, microlenders, SBDC, SCORE, WBC, VBOC | "who can help" |
| HUBZone, OZ | — | `in_hubzone` (contracting questions) | — | — | designations per tract |
| CBP, NES | — | — | — | — | business counts by sector |
| Sales tax rates | — | `combined_sales_tax_rate` is a lookup; `must_register_sales_tax` per state | state registration (`sales_tax_registration`) | revenue departments | combined rate with parts and date |
| Local schedules (BPOL, Baltimore, WA) | — | `va_bpol_liability` layer 2 | local BPOL forms | commissioners of the revenue, Fairfax DTA | licence tiers and due date |
| IRS forms and pubs | `guidance_us` | — | SS-4 (`business` → `federal_ein`) | `lexflow:agency:us:irs` | — |
| Census finance, districts | — | — | — | districts as taxing units | tax mix (T01, T09, T28, T40); who levies |
| BCAT, state adoption rules | — | `permit_required` chooses the state or local rule set by edition | — | — | code in force, with edition and history |
| BPS | — | resolves who issues | — | building department instance per issuing government | who issues permits |
| Baltimore codes, local-amendment lists | `regulations_md` local rows (Baltimore) | Baltimore rows in `permit_required` | DC DOB and Charlottesville permit forms (`building_permit`) | MD county building offices | local amendments |
| LOCUS (already loaded) | finding only, never cited | "zoning check" pointer | — | — | links to adoption, fee and setback ordinances |

`QUESTIONS` in `lexflow/municipal/questions.py` holds two questions today (`records`, `business`). The permit work
can enter as a third, `building_permit`, so that the maps score it. That raises the score total for every
government, and it is the user's decision (open question O4).

---

## 3. Two questions, end to end

### 3.1 "Do I need a building permit for a deck or a shed, and how do I get one?" (City of Charlottesville)

Once N1, N2, N7 and X4 are in place, the answer is assembled from stored rows only:

| Step | What happens | Reads | Today |
|---|---|---|---|
| 1. Plan | The planner's concept groups add `permit`, `building code`, `shed`, `deck`, `setback` (a thesaurus entry in `lexflow/ask/plan.py`, after the freeze) | — | the planner sees only statute concepts |
| 2. Place | The target resolves to `gov_id` 47210400100000, county FIPS 51540, state `va` | `governments` | works |
| 3. Search | Statutes and regulations are fused, each hit labelled by kind: 13VAC5-63-80 (Section 108, Application for permit), -70 (fees), -10 (edition), -20 (what the USBC supersedes; it preserves only listed land-use conditions and never mentions setbacks); Va. Code § 36-97 (zoning is not a "building regulation"), § 36-98 (supersession) and § 36-105 | `statutes_va`, `regulations_va` | "not found": only statutes are indexed |
| 4. Decide | `permit_required` (VA) runs once per project. A shed is detached, one story and ≤ 256 sq ft, so no permit is needed (rule 1). A deck needs a permit, unless the building official deems it minor and ordinary (rule 4). Inputs the question does not give, such as size, flood zone or historic district, are asked or carried as conditions | `process_models` (curated VA model) | no model |
| 5. Edition | The state rule (13VAC5-63-10 names the 2021 edition of the USBC) is compared with BCAT's Charlottesville row (2021 IRC and IBC, data as of 2026-06-30). The effective date, 18 January 2024, is not in the regulation text (none of the 81 sections contains "2024"). It comes from DHCD's [codes page](https://www.dhcd.virginia.gov/codes) ("2021 Virginia Codes effective Jan. 18, 2024") and is stored as a `code_adoptions` row with that URL. A disagreement becomes a version flag | `code_adoptions` | — |
| 6. Who | BPS should list the city as permit-issuing (checked on first load). It resolves to `lexflow:agency:47210400100000:building_official`, an instance of `lexflow:office-type:va:building_official`. The name (Neighborhood Development Services per BC §4.6) and the office page, mailbox and main line are shown only once the review queue and `recheck` mark them `ok` | `permit_issuers`, `agencies`, `contacts`, `contact_status` | the city's contact rows exist, but no building office entity |
| 7. How | The VA permit process model: apply by mail or online (108.3), contractor licence or a statement (108.4), documents (109), local fee plus the 2% levy (107), issue (110), inspections (113), certificate where required (116), appeal (119) | `process_models` | — |
| 8. Forms | The city's permit application, with its `verification` block | `fixtures/forms/forms.json` (`building_permit`) | — |
| 9. Local layer | LOCUS headings ("Sec. 5-26. Building Code adopted.", "Sec. 5-56. Building permits.") and the zoning setback sections, each a link to the official code, never quoted | `local_law` | LOCUS is loaded for VA |
| 10. Full code | A link to the free ICC view of the Virginia codes. No IRC text | constant link | — |

The rendered answer would read (abridged; the quotes are state law):

> **Shed: no permit, within limits.** Virginia's building code exempts "One story detached structures used as tool
> and storage sheds, playhouses, or similar uses, provided the building area does not exceed 256 square feet …"
> ([13VAC5-63-80](https://law.lis.virginia.gov/admincode/title13/agency5/chapter63/section80/), item 2). The building
> official may still require a permit in a special flood hazard area (Exception 2). You may ask for a permit anyway.
> The building code does not replace the city's zoning rules, so setbacks still apply: "'Building regulations' does
> not include zoning ordinances or other land use controls that do not affect the manner of construction or
> materials" ([Va. Code § 36-97](https://law.lis.virginia.gov/vacode/36-97/)). The setback itself is in the city's
> zoning ordinance [link to the official code, found through LOCUS].
>
> **Deck: permit required.** No exemption covers new decks. A permit is needed unless the building official deems
> the work "minor and ordinary" (item 13).
>
> **How:** apply to the City of Charlottesville's building official, by mail or online; "In no case shall an
> applicant be required to appear in person" (108.3). Bring proof of a contractor licence or a written statement
> (108.4), and pay the city's fee plus the 2% state levy
> ([13VAC5-63-70](https://law.lis.virginia.gov/admincode/title13/agency5/chapter63/section70/)). Then book the
> inspections. [Office name, page and contact, shown once checked.]
>
> **Code in force:** the 2021 edition of the USBC (13VAC5-63-10), in effect since 18 January 2024
> ([DHCD](https://www.dhcd.virginia.gov/codes)). Read the full code on
> [ICC's free view](https://codes.iccsafe.org/codes/virginia). Regulation text as of the 2026-09-30 snapshot; code
> editions as of BCAT's 2026-06-30 data. Not legal advice.

The same pipeline in other places (BC §1.1):

| Place | Shed | Deck | What it rests on |
|---|---|---|---|
| DC | exempt only for one garden shed ≤ 50 sq ft and < 10 ft high per lot, and not in a historic district or on a historically designated property. There, a permit application "subject only to historic preservation review" is required for a garden storage shed (105.2.5 item 8) | permit required; in a historic district the deck is also an alteration needing historic preservation review (10-C DCMR 304.1(h)) | 12-A DCMR § 105.2 and § 105.2.5, quoted; 10-C DCMR § 304 |
| A NY town | exempt (≤ 144 sq ft) only if the town's programme adopts 1203.3(a)(1)(i) | permit required | 19 NYCRR 1203.3, quoted; the town's local law via LOCUS |
| NC | open question (BC §8 item 4) | new framing needs a permit; re-decking does not | G.S. 160D-1110(c)(1), quoted |
| WA (no local amendment) | ≤ 200 sq ft exempt | exempt only if ≤ 200 sq ft, ≤ 30 in above grade, detached and not serving the required exit | IRC R105.2 facts, edition from WAC 51-51-003; link to ICC |
| Baltimore City | **open**. Part X does not adopt IRC Building items 1 to 3, 5, 9 or 10. But Part X § 105.1.1 adds the permit requirements of the city Building Code's § 105.1, and Part II keeps IBC item 1 "As in IBC". A reviewer must check Part II item 1 against Part X before the answer says either way | IRC item 10 not adopted: permit required | Baltimore's public-domain code ([Part X § 105](https://codes.baltimorecity.gov/us/md/cities/baltimore/code/building-codes/X/105), [Part II § 105](https://codes.baltimorecity.gov/us/md/cities/baltimore/code/building-codes/II/105)) |
| MD, TX, CA, IL, FL elsewhere | "depends on the local adoption" | same | edition from BCAT, the building department from BPS and entities, local text by link |

### 3.2 "What SBA loans can I get in Charlottesville, and who can help?"

Once N3, N4, N8, X1 to X4 and X6 are in:

| Step | What happens | Reads |
|---|---|---|
| 1. Plan | The concepts `SBA`, `7(a)`, `504`, `microloan` and `loan guarantee` route to the federal corpus, the Virginia statutes and the place block | — |
| 2. Search | 13 CFR 120.100, 120.110, 120.151, 120.707, 120.882, 120.931 and 121.201; SOP 8.1 sections A to C; Va. Code § 2.2-2280, § 2.2-1616, § 2.2-2311.1 | `regulations_us`, `guidance_us`, `statutes_va` |
| 3. Am I small? | `is_small`, if the user gives an industry. Restaurants (NAICS 722511) are small up to $11.5 million in average annual receipts (121.201). For 7(a) and 504 there is an alternative test: tangible net worth up to $20 million and average net income after tax up to $6.5 million (121.301(b)(2)). The answer says SBA, not lexflow, makes size determinations | curated DMN |
| 4. Which product | `which_sba_product`: 7(a) up to $5,000,000 per loan (120.151); 504 for eligible fixed-asset project costs (120.882), $5,000,000 per borrower or $5,500,000 for listed project types (120.931); microloans for working capital, supplies, furniture, fixtures and equipment (120.707), $50,000 or less per SBA's lender page. And: "SBA does not provide grants for starting and expanding a business" | curated DMN |
| 5. Who lends here | 7(a) and 504 cells for Charlottesville (51540) and Albemarle (51003), over five fiscal years, by sector: lenders with at least 5 loans, and median size where 11 or more loans share the cell. A 504 third-party lender is shown only if it also passes the organisation check in P7. Each bank links to its FDIC branches here (43 offices with city "Charlottesville" in the 2026-10-09 index) | `program_cells`, lender entities |
| 6. State programs | Five Virginia SSBCI programs run by VSBFA, two through VIPC, with the statutes that create them | `programs` |
| 7. Local programs | Charlottesville's "Cville Match" matches SBIR, STTR, VIPC and VJIP awards up to $25,000. It does not fit a restaurant, and the answer says so | `programs` (local) |
| 8. Who helps | The SBA Virginia District Office (Richmond) serves all of Virginia except Arlington, Fairfax and Loudoun counties and the cities of Alexandria, Fairfax and Falls Church, so it covers Charlottesville. Also the SBDC centre serving the city, SCORE, a Women's Business Center and a VBOC (curated, X3), VSBFA, and Lender Match as a linked step that lexflow never submits | `agencies`, partner entities, checked contacts |
| 9. Forms | SBA Forms 1919, 413 and 1244, as links only (Form 413 is a personal financial statement) | `forms.json` (`sba_loan`) |
| 10. Place context | Four HUBZone-qualified tracts in the city (51540000201, …202, …501, …600), and restaurant counts from CBP and NES | `place_designations`, `place_stats` |
| 11. Related steps | The VA BPOL licence (the curated tiers for the place), registering to collect sales tax (§ 58.1-612, with the rate from `tax_rates` for FIPS 51540), an EIN (SS-4), and a building permit if the space is built out (§3.1) | the tax and building tables |

The user's own figures (receipts, net worth, loan amount) are DMN inputs on their machine only. They are never
stored in a synced table and never logged (§4.4, rule P9).

---

## 4. Licensing and privacy

### 4.1 Source terms and what lexflow may do

Key: **yes** means it may be stored, shown or republished with the credit line. **facts** means only numbers,
conditions, citations and links, with no text from the source. **agg** means published aggregates only (§4.4).
**link** means link only. **counsel** means wait for the answer in §4.3. The DokuWiki column covers lexipedia.xyz
(`lexflow:` namespace). The Wikibase column covers lexipedia.wikibase.cloud, whose structured data must be public
domain or CC0. The Turso column covers sharing rows with other lexflow users.

| Source | Terms (key words, as reported) | Store | Show | Wiki | Wikibase | Turso | Counsel |
|---|---|---|---|---|---|---|---|
| open-us-law regulations | CC BY-NC 4.0; "Commercial use needs a licence from Vaquill AI" (credits.py) | yes (on disk) | quotes with the official URL | as statutes today, with attribution | **facts**: citation, URL, thresholds; no text | as today | C1, C2 |
| eCFR, OLRC | US government works (17 U.S.C. § 105) | yes | yes | yes | yes | yes | C3 (official edition) |
| SBA SOP, sba.gov pages, forms | "Government information on SBA.gov is in the public domain"; acknowledgement asked | yes | yes | yes | yes | yes | C4 |
| SBA FOIA | "U.S. Government Works" | **agg** only; borrower fields are never requested, and query pages are discarded after aggregation (P3, O1) | agg | agg | agg (organisation facts) | agg | C4 |
| Treasury SSBCI | US government work | program rows, no contact column | yes | yes | yes | yes | — |
| FDIC BankFind | no licence statement found; keys "currently not required" | yes | yes | after C5 | after C5 | yes | C5 |
| HUBZone service | not stated; "not a published API" | after SBA's answer (O2) | yes | after C6 | after C6 | yes | C6 |
| CDFI Fund OZ list, CDFI lists, SBIR | not stated (federal) | yes | yes | after C5 | after C5 | yes | C5 |
| Census CBP, NES, NAICS, BPS, finance, GUS | federal works; the finance datasets index page: "Datasets are usually for public use, and users may analyze, extract, customize and publish statistics" | yes | yes (BPS: counts under 5 hidden) | yes | yes | yes | — |
| Grants.gov | "Access to or use of the API or its content constitutes acceptance"; required non-endorsement notice | not until the user accepts | — | — | — | — | C7 |
| AWBC, SCORE, SBDC locators | AWBC forbids systematic retrieval; for "personal, non-commercial use or internal business purpose" | **no** (hand-curated from each organisation's own pages) | link | link | link | — | C8 |
| CDTFA rates | "considered in the public domain" unless otherwise indicated; no seals | yes | yes | yes | facts | yes | — |
| Other revenue departments (VA, TX, WA, NC, IL "as is", FL, NY, DC OTR), SST (© notice) | no licence stated | facts (rates and dates) | yes | after C9 | facts after C9 | yes | C9 |
| VA Tax "Local Tax Rates" PDF | "© 2025 Virginia Department of Taxation All Rights Reserved" | **not until C10** | link | link | — | — | C10 |
| Weldon Cooper Center tables | © UVA; no reuse terms found | not until C11 | link | link | — | — | C11 |
| IRS forms and publications | "not subject to copyright and may be freely copied. Credit is requested"; no seals implying endorsement | yes; forms as links | yes | yes | yes | yes | C12 (forms) |
| IRS guidance via open-us-law | CC BY-NC compilation | later, after C1 | — | — | — | — | C1 |
| Local schedules (Fairfax DTA, Baltimore BBMR, WA BLS city pages) | no licence stated | curated facts with URL and date | yes | after C9 | facts after C9 | yes | C9 |
| Municode-hosted ordinances, eCode360, American Legal | link-only per credits-research; not read | **no** | link | link | link | — | C13 |
| Texas permit holders, NY assessment rolls | public data but person-level | **no** (at most server-side counts, later) | — | — | — | — | — |
| FEMA BCAT | no licence stated; disclaimer: general information, verify locally | after an operator decision (O3), without `Contact_Email` and without the item's `owner` | yes, with "confirm locally" | after C14 | after C14 | after O3 | C14 |
| State building regulations (VAC, DCMR, COMAR, WAC, NYCRR) | Supported by the government-edicts doctrine, not settled by it. Georgia v. PRO confirms the doctrine for judges and legislators; these rules are written by executive bodies. Veeck binds in the 5th Circuit only, ICC v. UpCodes is persuasive only, and the ASTM cases rest on fair use. Parts of the text reproduce ICC model language (C21). The lexflow copy comes from the CC BY-NC compilation | yes | quotes | yes | facts | yes | C1, C21 |
| Baltimore `law-xml` | site: public domain, and asks for GitHub bulk use instead of scraping; repository `license: null`; the code site's robots.txt adds `Content-signal: search=yes,ai-train=no` | yes | quotes | yes | facts | yes | C15 |
| ICC, NFPA, IAPMO model codes; the FBC and NC code books | ICC: no robots, commercial use, derivatives or display on third-party sites; the FBC is "copyrighted material" | **facts only** (BC §2.4) | facts and a link | facts and a link | after C16 | facts | C16–C19 |
| UpCodes, Public.Resource.Org copies | robots disallow; PRO's own position | **no** | — | — | — | — | C18 |
| MD Labor, CA BSC, IL CDB, FL Building Code Online | state pages; FBC Online terms not read | index facts (jurisdiction, ordinance number, link) | yes | yes | facts | yes | C20 (FL) |
| LOCUS-v1 (already used) | CC BY-NC 4.0; find, never cite | as today | links only | links | — | as today | C1 |

### 4.2 Rules by surface

* **Wikibase.** Only facts from public-domain sources (federal works, and state or local law as citations,
  thresholds and links) go there, under the hosting policy's CC0 rule. Facts derived from a CC BY-NC compilation
  or from a source with no stated licence wait for counsel (C2, C5, C9). Text never goes there: the policy requires
  text that allows commercial use, which CC BY-NC does not. The Wikibase still needs a `Project:Copyrights` page
  ([authority-wikibase.md](authority-wikibase.md) §2.7). The same point affects what the Wikibase loader writes today,
  as [credits-research.md](credits-research.md) finding 2 already notes. This plan adds no CC BY-NC text there.
  * The same policy lists **disqualifying conditions**. Two bear on this plan. First, an instance that contains, or
    is intended to contain, "data about living people and other sensitive topics without appropriate local rules
    and processes to handle the content responsibly". Second, a dataset whose "intended or observed dataset size or
    load exceeds the technical capacity that Wikibase Cloud can realistically support", or whose load is "abusive
    and unjustified".
  * So contact and lender entities go to the Wikibase as organisations and office channels only. 504 third-party
    lenders go only once they pass P7. No contact goes there until the Wikibase has published local rules on people
    data.
  * Loading 38,640 governments, plus lenders, districts and programs, is planned in stages with a dry run. The user
    decides whether to ask WMDE first (O6). The binding copy of the policy is at wikibase.cloud/hosting-policy; the
    text above is the staged copy, read raw.
* **DokuWiki.** The owner sets the licence, and the `lexflow:` pages already carry CC BY-NC-derived content. New
  pages follow the same attribution and add the credit lines of §2.2. Pages carry no "All rights reserved" source
  text and no model-code text.
* **Turso.** Syncing shares rows with other people, so it counts as republishing. Only published aggregates, public
  facts and checked office channels go in `SYNCED` tables. `asked_questions`, users' inputs and any raw file stay
  local.
* **Everywhere.** Each figure carries its source link and as-of date. Publishing stays user-triggered, after a dry
  run, and only Claude-reviewed or two-extraction-agreed models are published.

### 4.3 Questions for counsel (consolidated; none decided here)

| # | Question | From |
|---|---|---|
| C1 | Is lexflow's use (an open repository, and the sandbox Lexipedia sites) non-commercial under open-us-law's CC BY-NC 4.0? Do pages mixing that text with public-domain data inherit the limit? | TAX Q1, SBA Q7, BC §2.4(6) |
| C2 | May citations, thresholds and links taken from the CC BY-NC compilation go to the Wikibase as CC0 facts, or must they be re-derived from the official publisher first? | this note, credits-research finding 2 |
| C3 | Before citing eCFR text as the law, what is the eCFR's standing against the official annual edition? | SBA §3.4, TAX §2.2 |
| C4 | Are cells derived from SBA data free to publish with attribution, and does SBA's request for "appropriate acknowledgement" need a credit on each page? | SBA Q1 |
| C5 | Confirm that FDIC, CDFI Fund and SBIR data with no licence statement are public domain. | SBA Q4 |
| C6 | May lexflow read the HUBZone GeoServer in bulk, or should it ask SBA? | SBA Q3 |
| C7 | Grants.gov terms: the user must accept them before any call, and show the required notice. | SBA Q2 |
| C8 | Confirm that linking to the AWBC locator is the only permitted use. | SBA Q6 |
| C9 | May compiled rate tables and local schedules from sites with no stated licence be stored and republished? Do "as is" disclaimers change anything? | TAX Q4 |
| C10 | May rate figures (facts) be taken from the "All Rights Reserved" Virginia Tax PDF and republished with attribution? | TAX Q2 |
| C11 | What reuse terms apply to the Weldon Cooper Center tables and data file? | TAX Q3 |
| C12 | If lexflow ever reproduces an IRS form, what limits apply? | TAX Q6 |
| C13 | May lexflow quote Municode-hosted ordinances such as the Fairfax County Code? | TAX Q5 |
| C14 | Is FEMA's BCAT layer public domain, and may it be stored and republished? (The user may also ask FEMA, O3.) | BC §8 item 9 |
| C15 | Baltimore's repositories have no licence file. Is the site's public-domain statement enough? The code site's robots.txt also carries `Content-signal: search=yes,ai-train=no` and blocks named AI crawlers. Does that signal bear on indexing and quoting the code in answers (no model training), whether the text comes from GitHub or the site? | BC §3.17; robots.txt read 2026-10-10 |
| C16 | Are numeric thresholds and conditions from model codes uncopyrightable facts in all 10 states? May an answer quote a short span of adopted model text? | BC Q1, Q2 |
| C17 | Does the Florida Building Code count as a government edict? | BC Q3 |
| C18 | May lexflow link to or rely on Public.Resource.Org's archive.org copies? | BC Q4 |
| C19 | What changes if the Pro Codes Act passes? S. 4145 keeps protection only where the developer makes the incorporated standard "publicly accessible online at no monetary cost and in a format that includes a searchable table of contents and index, or equivalent aids to facilitate the location of specific content". Do ICC's free views meet that condition? | BC Q5; [S. 4145](https://www.govinfo.gov/content/pkg/BILLS-119s4145is/html/BILLS-119s4145is.htm) |
| C20 | The Florida Building Code Online terms (not read). | BC §8 item 11 |
| C21 | Is state or District regulation text that reproduces ICC model language government-edict text that may be quoted in full? Examples are USBC Chapter 1 and the DC supplements (12-A DCMR 105.2's preamble mirrors the IBC's). Or does part of it remain ICC's? Georgia v. PRO confirmed the doctrine for judges and legislators. These rules are written by executive bodies (Virginia's Board of Housing and Community Development, DC agencies). | verify-data-expansion W3, M8 |

### 4.4 Privacy: one rulebook for every source

**About people in the data** (payroll §6.1, applied to loans, permits and awards):

| # | Rule | Applies to |
|---|---|---|
| P1 | **Allowlist at read time.** Only named columns are read. FOIA reads `Program`, `LocationID`, `BankName`, `BankFDICNumber`, `BankNCUANumber`, `CDC_Name`, `ThirdPartyLender_Name`, `GrossApproval`, `SBAGuaranteedApproval`, `ApprovalFY`, `ProcessingMethod`, `TermInMonths`, `NaicsCode`, `FranchiseCode`, `ProjectCounty`, `ProjectState`, `SBADistrictOffice` and `AsOfDate`, and nothing else. The list is an allowlist: every other column is refused, including `BorrName`, `BorrStreet`, `BorrCity`, `BorrState`, `BorrZip`, `BusinessType`, `BusinessAge`, `LoanStatus`, `FirstDisbursementDate`, `RevolverStatus`, `FranchiseName`, the charge-off fields and `JobsSupported` (SBA §5). On the DKAN datastore the allowlist applies to every `properties`, `conditions` and `groupings` entry the query builder sends (P3). BCAT `outFields` omit `Contact_Email`, and the ArcGIS item's `owner` is never copied. The EO BMF drops `ICO`. SBIR drops `poc_*` and `pi_*`. The SSBCI, CDC and microlender lists drop staff contacts | SBA FOIA, BCAT, EO BMF, SBIR, SBA lists |
| P2 | **Group on the publisher's server where possible.** Socrata sources are read with `$select` and `$group`, so names never cross the network. | MD and NY program data, TX permit counts (later) |
| P3 | **Project at the server.** data.sba.gov's DKAN datastore holds both FOIA files (7(a) FY2020 to present `fc21a598-913d-5c29-b7c1-1924ce608538`; 504 FY2010 to present `47fa0223-0a71-562f-85f1-b4b732400efc`). Its published API spec (`https://data.sba.gov/api/1`) offers column projection (`properties`), `conditions`, `groupings`, and the aggregates `sum`, `count`, `avg`, `max` and `min`. Count cells come from grouped `count(record_number)` queries. Medians need a column-limited projection of allowlisted columns, since there is no median operator. Either way, borrower fields never cross the network. Pages are aggregated as they arrive and then discarded. The vintage is each distribution ID and its `asofdate`. The spec documents a 503 ("Datastore queries are temporarily limited due to high server load") with a `Retry-After` header. The job honours it, backs off, and stops rather than falling back to the full CSVs: a fallback would need its own approval (O1). | SBA FOIA |
| P4 | **Counts from 5; amounts from 11.** A cell of 1 to 4 shows "fewer than 5". A median, quartiles or mean (`avg`) need at least 11 loans, are rounded to $10,000, and are withheld if a rounded figure equals 1 to 10 loans' exact amounts. `min` and `max` are never published at any cell size, because each is one loan's exact amount. | `program_cells`, `permit_issuers`, `place_stats` |
| P5 | **No sums at small grain and no differencing.** Cells nest (lender in county, county, state). Every published cell holds 0 or at least 11 loans outside its published sub-cells; otherwise the smallest sub-cell is withheld. | `program_cells` |
| P6 | **No quasi-identifiers.** A small county's cell never combines a franchise name, a six-digit NAICS code and a single fiscal year. The default cell is (county, five-year window, program, NAICS sector). BPS construction values are never stored. | FOIA, BPS |
| P7 | **Organisations are named; people are not.** Lenders, CDCs, CDFIs, SBIR firms and agencies appear by name. Offices appear by role and office channel only, through `lexflow/privacy.py` (`is_office_mailbox`, `is_office_phone`) and the entities plan's §5. **504 third-party lenders can be people.** 13 CFR 120.802 defines a Third Party Loan as "a loan from a commercial or private lender, investor, or Federal (non-SBA), State or local government source", and the dictionary describes `ThirdPartyLender_Name` only as "Name of third party lender". So a third-party lender name is kept only if it passes both tests below. Any name that fails is dropped at read time and never stored: (a) it matches an FDIC or NCUA institution, or carries an organisation form (bank, credit union, association, Inc., LLC, a government body); (b) it has at least 5 loans in the cell window. | all entities; FOIA 504 |
| P8 | **Attacker tests.** Each aggregator gets the payroll tests: a file with borrower columns, where no value may reach a row; exact order statistics; subtracting a lender from its county. The FOIA query builder also gets three tests: it must refuse any `properties`, `conditions` or `groupings` entry outside the P1 allowlist; it must never emit `min` or `max` for a published cell, or `avg` for a cell under 11; and it must drop a person-like third-party lender name (P7). | FOIA, BPS |

**About the people using lexflow:**

| # | Rule |
|---|---|
| P9 | A user's business figures (receipts, employees, net worth, loan amount), project details and questions stay on their machine. They are never stored in a `SYNCED` table and never logged. |
| P10 | No address lookup from lexflow's server. An address-level rate or HUBZone check is a link to the state's or SBA's own tool, or an explicit opt-in call from the user's browser with a notice naming the service (TAX §7.4). `asked_questions` never stores an address. |
| P11 | Nothing is fetched at question time (payroll P6). No publisher learns what a user asked. |

---

## 5. Effort and order, with the exact downloads

Effort is in developer days. The notes' scales differ (SBA's M is 2 to 5 days, BC's M is 3 to 10), so each item is
given in days. Every download below needs the user's approval before it is made, and so does every page-reading
job run. Each approved job also reads its host's robots.txt on the day it runs and stops if the planned path is
disallowed. The 2026-10-10 reading is in §5.2: three hosts already need a decision first (O10). **Nothing listed
here has been downloaded.**

### Phase 0: no download (about 9 to 15 days)

| Work | Effort | Depends on |
|---|---|---|
| `regulations_<st>.sqlite` for 7 states in a new `lexflow/corpus/` module, with the `regulations` card | 1–2 | nothing |
| `districts` table and card from the GUS workbook on disk | 1 | nothing |
| Curated `permit_required` (VA, DC, NC; NY as opt-in rows), including DC's historic-district rows (12-A DCMR 105.2.5, 10-C DCMR 304.1(h)), and the VA permit process model, Claude-reviewed | 3–5 | the index, for quotes |
| `va_bpol_liability` layer 1 from §§ 58.1-3703 and 58.1-3706 and 23VAC10-500; layer 2 rows for Fairfax and Charlottesville from their pages | 3–5 | page reads of 2 Fairfax pages (approval to run) |
| Ask wiring: `retrieve.fused()` across kinds, thesaurus groups, the specific not-found text | 1–2 | the AskBench freeze ending (O5) |

Downloads: none in this container. The inputs are already on disk: 145.7 MB of regulation parquet for the 7 states,
and the 11,459,763-byte GUS workbook. On a fresh install, the regulation files come only through the `statutes` step
run with `regulations`, which adds 2.1 GB and needs the user's approval (§2.1).

### Phase 1: small official files, about 6.8 MB measured (about 18 to 32 days)

| Work | Effort |
|---|---|
| `federal-rules` card: the eCFR loader, the SOP split at its headings, the IRS XML parser | 3–5 |
| `is_small` (with tests on 722511 at $11.5 million and 236118 at $45.0 million) and `which_sba_product` | 3–5 |
| BPMN "Apply for an SBA-guaranteed loan" (federal scope), Claude-reviewed | 2–3 |
| `tax_rates` for 10 states with crosswalks to `gov_id`, and the DC version flag | 3–5 |
| `must_register_sales_tax` per state and the composite "open a shop" process model with the EIN step | 3–5 |
| `permit_issuers` from BPS | 1–2 |
| Program registry: SSBCI, district offices, statute hits, the CDC and microlender lists | 3–5 |
| Forms entries (`sba_loan`, `federal_ein`, `sales_tax_registration`, `building_permit`) | 1–2 |

| # | What | Source | Size | Approval |
|---|---|---|---|---|
| D1 | 13 CFR parts 120, 121, 123, 126, 130 and 131 (XML, sent with `Accept-Encoding: gzip`) | `https://www.ecfr.gov/api/versioner/v1/full/<date>/title-13.xml?part=<n>` | about 1.48 MB (eCFR size figures) | **needed**, after O10: eCFR's robots.txt disallows `/api/versioner/v1/full/`. Alternative: GovInfo's bulk file `https://www.govinfo.gov/bulkdata/ECFR/title-13/ECFR-title13.xml` (allowed; the whole title; Last-Modified 2026-09-30; size not reported by HEAD) |
| D2 | SOP 50 10 8.1 (.docx) | `https://legacy.sba.gov/sites/default/files/2026-10/SOP%2050%2010%208.1%20Technical%20Policy%20Updates%20effective%20%2010.1.2026.docx` | 1,072 KB | **needed**, after O10: legacy.sba.gov's robots.txt disallows `/sites/default/files/*`, and www.sba.gov's page redirects there. Alternative: the user saves the file from SBA's SOP page in a browser |
| D3 | 2022 NAICS structure (.xlsx) | `https://www.census.gov/naics/2022NAICS/2022_NAICS_Structure.xlsx` | not reported by HEAD | **needed** |
| D4 | IRS Publications 334 and 583 (XML zips) | `https://www.irs.gov/pub/irs-sgml/p334.zip`, `p583.zip` | 115,396 B + 65,029 B | **needed** |
| D5 | VA rates by locality | `https://www.tax.virginia.gov/sites/default/files/inline-files/sales-and-use-tax-rates-by-locality-by-date.xlsx` | 83,424 B | **needed** |
| D6 | TX city, county, MTA and SPD rates | `https://comptroller.texas.gov/taxes/sales/docs/city-rates.xlsx` and the three equivalents | `city-rates.xlsx` 340,481 B (2026-10-06); the other three not measured | **needed** |
| D7 | CA effective rates | one OData call `https://www.cdtfa.ca.gov/dataportal/api/odata/Effective_Sales_Tax_Rates` (546 rows), or the 71,474 B XLSX | small | **needed** |
| D8 | WA location codes and rates | `https://dor.wa.gov/sites/default/files/2026-08/Rates_26Q4.zip` | 4,420 B | **needed** |
| D9 | NC current rates (CSV export) | `https://files.nc.gov/dor/2026-07/Total%20Current%20S%26U%20Tax%20Rates%20Effective%207-1-2026.csv` | 1,370 B (2026-07-01) | **needed** |
| D10 | IL jurisdiction rates | `https://tax.illinois.gov/content/dam/soi/en/web/tax/research/taxrates/documents/salestaxrates/ordmache-current.txt` | 31,004 B | **needed** |
| D11 | FL surtax rates | `https://floridarevenue.com/Forms_library/current/dr15dss_26.pdf` | about 204 KB | **needed** |
| D12 | NY Publication 718 | `https://www.tax.ny.gov/pdf/publications/sales/pub718.pdf` | 215,766 B | **needed** |
| D13 | SST rate files, as a cross-check (NC, WA) | `https://streamlinedsalestax.org/ratesandboundry/Rates/NCR2026Q3APR23.csv`, `.../WAR2026Q4AUG27.zip` | 15,870 B + 58,577 B | **needed** |
| D14 | BPS 2025 place files (4 regions) | `https://www2.census.gov/econ/bps/Place/South%20Region/so2025a.txt`, `Midwest%20Region/mw2025a.txt`, `Northeast%20Region/ne2025a.txt`, `West%20Region/we2025a.txt` (the folder names end in " Region") | 692,949 + 1,198,782 + 847,668 + 322,164 = 3,061,563 B (2026-05-14) | **needed**, after O10 (www2.census.gov robots.txt reading) |
| R1 | Page reads (no data file): the SSBCI table (1), SBA district offices (1 plus district pages), the CDC list (22 pages) and microlender list (16), SBA form pages (3), the IRS forms list (16 pages of 200), Baltimore BBMR (1), Fairfax BPOL (2), Charlottesville's permit and fee pages | each publisher, at 1 request per second | — | **approval to run** |

### Phase 2: the larger and licence-dependent sources, about 100 to 140 MB (about 51 MB measured, the rest estimated) (about 35 to 60 days, including the entities plan)

| Work | Effort |
|---|---|
| Entities plan phases 1 to 3 (contacts with provenance, the `recheck` step, agencies and links): the prerequisite for any shown building-department, revenue-office or SBA contact | 11–14 (from that plan) |
| FOIA aggregation through a DKAN query builder with the §4.4 rules and attacker tests (P1, P3, P4, P7, P8). The county crosswalk: `ProjectCounty` is an upper-case county name, and Virginia's independent cities end in " CITY", so "FAIRFAX" and "FAIRFAX CITY" are told apart by the suffix. Lender entities joined to FDIC | 5–8 |
| Resource partners curated for 10 states (40 to 60 rows) and the 24 SBA district offices' service areas | 3–5 |
| Place designations (HUBZone, OZ), CBP and NES, and the "Business finance here" block | 2–3 |
| BCAT crosswalk to `gov_id` (name plus county, as `locus_scan.gov_keys` does) and `code_adoptions` | 3–10 |
| Baltimore's local layer; the MD and CA local-amendment indexes; NY Part 1203 in `regulations_ny` | 4–7 |
| 26 CFR parts 301 and 31, IRC Title 26, Census finance, property tax rates for NY, TX and MD | 6–10 |

| # | What | Source | Size | Approval |
|---|---|---|---|---|
| D15 | 7(a) FOIA FY2020 to present, as DKAN queries. These are grouped `count(record_number)` cells, plus a column-limited projection of allowlisted columns only (`projectstate`, `projectcounty`, `approvalfy`, `program`, `naicscode`, `locationid`, `bankname`, `bankfdicnumber`, `bankncuanumber`, `processingmethod`, `terminmonths`, `grossapproval`, `asofdate`) for medians. Paged; the server applied a default limit of 500 rows | `https://data.sba.gov/api/1/datastore/query/fc21a598-913d-5c29-b7c1-1924ce608538` (GET, deepObject parameters), or its `/download` CSV form (documented, not tried) | 175,184 rows in the 10 states (of 388,338); an estimated 25 to 50 MB of JSON pages (not measured; the lower end with `keys=false`), against 181.1 MB for the CSV | **needed** (O1) |
| D16 | 504 FOIA FY2010 to present, as DKAN queries: the same pattern, with `cdc_name` and `thirdpartylender_name` (P7) in place of the bank columns | `https://data.sba.gov/api/1/datastore/query/47fa0223-0a71-562f-85f1-b4b732400efc` | 55,089 rows in the 10 states (of 117,983); an estimated 7 to 15 MB (not measured), against 59.4 MB for the CSV | **needed** (O1) |
| D17 | FDIC branch locations for the 10 states, selected fields, paged | `https://api.fdic.gov/banks/locations?filters=STALP:<st>&fields=NAME,CERT,UNINUM,OFFNAME,CITY,COUNTY,STCNTY,STALP,ZIP,SERVTYPE` | about 30,527 rows, a few MB | **needed**. No key today ("currently not required"). If one becomes required, the user requests it and stores it in `.env`; lexflow never registers |
| D18 | Opportunity Zones list | `https://www.cdfifund.gov/system/files/documents/designated-qozs.12.14.18.xlsx` | 276,974 B | **needed** |
| D19 | HUBZone tracts and counties, without geometry (10 per-state queries) | `https://maps.certify.sba.gov/geoserver/ows?service=WFS&version=2.0.0&request=GetFeature&typeNames=hubzone:qct_e` (and `qnmc_e`), `propertyName=tract_fips,county,state,current_status,redesignated` | under 2 MB | **needed**, after C6 or SBA's answer (O2) |
| D20 | CBP 2023, county | `https://www2.census.gov/programs-surveys/cbp/datasets/2023/cbp23co.zip` | 12,919,520 B | **needed**, after O10 (www2.census.gov) |
| D21 | NES 2024, county | `https://www2.census.gov/programs-surveys/nonemployer-statistics/datasets/2024/historical-datasets/nonemp24co.zip` (the path without `historical-datasets/` returns 404) | 4,585,934 B (2026-09-29) | **needed**, after O10 (www2.census.gov) |
| D22 | BCAT attributes for the 10 states (4 pages of 2,000, `returnGeometry=false`). `outFields=Place,County,State_abbr,Building_Code,Res_Code,Existing_Building_Code,Adoption_Notes,Local_Code_Weakening_Note,Data_Currency,State_Building_Code_Link_1,Pop_2020`: no `Contact_Email`, and the item's `owner` is never copied | `services.arcgis.com/DN2fPfpggEPlLhP6/arcgis/rest/services/FEMA_BCAT_Government_Jurisdictions/FeatureServer/0/query` | 6,722 rows, about 5–15 MB (estimated) | **needed**, after O3 |
| D23 | Baltimore building codes | `git clone --depth 1 https://github.com/baltimore-legref/law-xml` (keep the building-codes subtree) | 14,637 KB | **needed** |
| D24 | CA BSC 2022 and 2025 ordinance lists; MD Labor county and municipal pages | `https://www.dgs.ca.gov/BSC/Codes/2025-Ordinances` and the 2022 list; `https://labor.maryland.gov/labor/build/buildcounties.shtml`, `buildmuni.shtml` | under 1 MB (estimated) | **needed** |
| D25 | 19 NYCRR Part 1203 full text | `https://dos.ny.gov/2021-12-10-full-text-rule-part-1203` | about 260 KB | **needed** |
| D26 | 26 CFR parts 301 and 31 | eCFR API, `title-26.xml?part=301` and `?part=31`; or GovInfo's whole-title bulk file `ECFR-title26.xml` (Last-Modified 2026-10-07; size not reported, likely far larger) | 4,699,706 + 2,015,776 B through the API | **needed**, after O10 (eCFR robots.txt) |
| D27 | IRC Title 26 (USLM) | `https://uscode.house.gov/download/releasepoints/us/pl/<congress>/<law>/xml_usc26@<rp>.zip` (the current release point, when the site is back) | not measured (the site was under maintenance) | **needed** |
| D28 | Census finance 2022 | `https://www2.census.gov/programs-surveys/gov-finances/tables/2022/2022_Individual_Unit_File.zip` | 9,719,280 B | **needed**, after O10 (www2.census.gov) |
| D29 | NY property tax rates, roll year 2024 | `https://data.ny.gov/resource/iq85-sdzs.json?roll_year=2024` | 2,832 rows | **needed** |
| D30 | TX property tax rates and levies 2025 (5 XLSX files) | `comptroller.texas.gov/taxes/property-tax/docs/2025-*-rates-levies.xlsx` | not reported | **needed** |
| D31 | MD SDAT rate table 2026–27 | the PDF on `https://dat.maryland.gov/Pages/Tax-Rates.aspx` | 883,275 B | **needed** |
| D32 | VA local tax rates TY 2025 | `https://www.tax.virginia.gov/local-tax-rates` → `2025-local-tax-rates.pdf` | 474,686 B | **needed**, after C10 |

### Phase 3: later (about 15 to 25 days)

| # | What | Source | Size | Approval |
|---|---|---|---|---|
| D33 | CDFI certified list and state awards | `CDFI_Cert_List_Manual_9.17.26.xlsx`; `/system/files/2026-09/2026-09-29_state-awards.csv` on cdfifund.gov | 150,742 B + small | **needed** |
| D34 | SBIR and STTR awards without abstracts | `https://data.www.sbir.gov/mod_awarddatapublic_no_abstract/award_data_no_abstract.csv` | 91.6 MB | **needed** |
| D35 | SBA disaster loans FY22 | `https://data.sba.gov/sites/default/files/distribution/SBA-ODA-2022-09-002/sba_disaster_loan_data_fy22.xlsx` | 2.19 MB | **needed** |
| D36 | Grants.gov daily extract | `https://www.grants.gov/xml-extract` (e.g. `GrantsDBExtract20261010v2.zip`) | 78.3 MB | **needed**, after the user accepts the terms |
| D37 | USAspending county totals by assistance listing | POST `https://api.usaspending.gov/api/v2/search/spending_by_geography/` | query-sized | **needed** (POST) |
| D38 | MD and NY program data, as grouped queries | `opendata.maryland.gov` (`cf3i-xdgb`, `absk-avps`), `data.ny.gov` (`vp83-gfyz`) | grouped rows | **needed** |
| D39 | WA city endorsement pages | `https://dor.wa.gov/manage-business/city-endorsements/<City>` | about 150 page reads | **needed** |
| D40 | IRS guidance (4 small sets) | `https://oss-data-us.vaquill.ai/v2026.09.1/` | 9,086,157 B | **needed**, after C1 |
| D41 | EO BMF state files | `https://www.irs.gov/pub/irs-soi/eo_<st>.csv` | VA 9,508,327 B; others not measured | **needed** |
| — | Illinois CDB directory export | a request the user sends to CDB's office mailbox | unknown | the user's message |

### 5.1 Summary of approvals

* **Phase 0:** no download in this container. Approve only the page reads for the Fairfax and Charlottesville
  schedules. A fresh install also needs the 2.1 GB regulations add-on through the `statutes` step.
* **Phase 1:** D1 to D14 and the page reads R1. That is about 6.8 MB measured, plus small tables whose servers did
  not report a size: D3, three of D6's four files, and D7's OData call. D1, D2 and D14 also wait on O10.
* **Phase 2:** D15 to D32, about 100 to 140 MB (about 51 MB measured). D15 and D16 are now server-side DKAN queries,
  not the 240.5 MB CSVs. D19, D22 and D32 also wait on counsel or the publisher, and D20, D21, D26 and D28 on O10.
* **Phase 3:** D33 to D41, and the CDB request.

Not recommended at any phase: the 1.45 GB federal regulations parquet, IRS written determinations (132 MB), the SST
boundary files, the Illinois address file, the pandemic-era loan files, and the full FOIA CSVs (replaced by D15 and
D16).

### 5.2 robots.txt on the data hosts (read 2026-10-10)

Each file was read once with lexflow's User-Agent. Planned paths were tested under RFC 9309. Its grammar lets empty
lines sit inside a group, so a `User-agent: *` line followed by an empty line still joins the rules below it. robots.txt
rules "are not a form of access authorization" (RFC 9309), and they address crawlers. Whether a one-off, approved,
rate-limited download counts as crawling is the operator's decision (O10), not something decided here. Re-read each
file on the day a job runs.

| Host | Result for the planned paths | Downloads affected |
|---|---|---|
| www.ecfr.gov | `User-agent: *`, then (after an empty line) `Disallow: /api/versioner/v1/full/`. The planned path is disallowed; `titles.json` is allowed | D1, D26 (and the eCFR section reads made in research, review and this revision) |
| legacy.sba.gov | `Disallow: /sites/default/files/*`, so the SOP .docx path is disallowed. `/document/` and `/district/` pages are allowed | D2 |
| www2.census.gov | `User-agent: *` stands alone, then an empty line, then `User-agent: RavenCrawler` and `Disallow: /`. Under RFC 9309 the two lines form one group, so everything is disallowed for unnamed agents. Under the older convention, where an empty line ends a record, nothing is disallowed. The file names other crawlers one by one, which suggests the narrower intent, but the operator decides | D14, D20, D21, D28 |
| codes.baltimorecity.gov | `User-Agent: *` allowed except `/_*`; `Content-signal: search=yes,ai-train=no`; named AI crawlers (including ClaudeBot and GPTBot) disallowed. The bulk route is GitHub, whose robots.txt allows the repository paths | D23 (C15) |
| data.ny.gov, opendata.maryland.gov | allowed, `Crawl-delay: 1` | D29, D38 |
| data.sba.gov | allowed, including `/api/1/datastore/` and `/sites/default/files/` | D15, D16, D35 |
| www.tax.virginia.gov, comptroller.texas.gov, cdtfa.ca.gov (via a 301 from www.), dor.wa.gov, tax.illinois.gov, floridarevenue.com, www.tax.ny.gov, www.streamlinedsalestax.org, www.irs.gov, www.cdfifund.gov, maps.certify.sba.gov (all lines commented out), www.census.gov, dos.ny.gov, dat.maryland.gov, www.dgs.ca.gov, labor.maryland.gov, uscode.house.gov, www.grants.gov, home.treasury.gov, www.sba.gov, www.govinfo.gov (`/bulkdata/`), github.com | allowed | D3 to D8, D10 to D13, D18, D19, D24, D25, D27, D30 to D33, D36, D39, D41, R1 |
| api.fdic.gov, api.usaspending.gov, oss-data-us.vaquill.ai (404); services.arcgis.com, files.nc.gov, data.www.sbir.gov (403) | no robots.txt served. Under RFC 9309 a 4xx status means the crawler "MAY access any resources on the server" | D9, D17, D22, D34, D37, D40 |

---

## 6. Open questions for the user

| # | Question |
|---|---|
| O1 | May the FOIA aggregates be built from DKAN queries (D15, D16)? These are grouped counts plus a column-limited projection of allowlisted columns, an estimated 35 to 65 MB of query pages, with no borrower field requested. The pages would be discarded after aggregation. The full CSVs (240.5 MB) are no longer needed; any fallback to them would need a separate approval. |
| O2 | Should the user ask SBA (the Office of Entrepreneurial Development, or data.sba.gov's contact) for a resource-partner extract and about bulk use of the HUBZone service? Any such message is the user's to send. |
| O3 | Should the user ask FEMA whether BCAT may be stored and republished? Until then, should lexflow read BCAT for local display only, or not at all? (The payroll rule P7 says a source whose terms need a decision is not read until the operator records it.) |
| O4 | Should `building_permit` become a third scored question in `QUESTIONS`? It changes every government's score total and the maps. |
| O5 | Is the AskBench freeze over? Until it is, the new indexes reach place pages and curated models, but not the Ask answers. |
| O6 | Are federal (`us`) process models, and the new entity kinds (lenders, CDCs, CDFIs, partners, programs), in scope for Lexipedia? Each needs P25 keys and a `Project:Copyrights` statement first. The hosting policy also disqualifies instances holding "data about living people" without "appropriate local rules and processes", and datasets whose size or load exceeds what Wikibase Cloud "can realistically support" (§4.2). Should the user publish local rules on people data first, and ask WMDE before loading 38,640 governments plus lenders? |
| O7 | **Answered 2026-10-10.** Yes. data.sba.gov's DKAN datastore holds both FOIA files and documents grouped, column-limited queries with `count`, `sum`, `avg`, `max` and `min` (P3). A grouped count for Virginia returned county names and counts only. |
| O8 | Who reviews the curated rows: resource partners, building departments and local schedules? The entities plan's open question 5 applies here as well. |
| O9 | Should NCUA credit-union data be surveyed to complete the lender entities (`BankNCUANumber`)? (SBA Q7) |
| O10 | Three hosts' robots.txt files cover planned paths (§5.2): eCFR `/api/versioner/v1/full/` (D1, D26), legacy.sba.gov `/sites/default/files/*` (D2) and www2.census.gov, ambiguously (D14, D20, D21, D28). For each, should lexflow (a) treat an approved, one-off, rate-limited download as outside robots.txt's scope, (b) use an allowed route (GovInfo's bulk eCFR for D1; for D2, the user saves the .docx in a browser), (c) ask the publisher, or (d) drop the item? |

---

## 7. Sources

The three research notes hold every source card, with its links:
[data-sba-programs.md](data-sba-programs.md), [data-tax.md](data-tax.md) and
[data-building-codes.md](data-building-codes.md). The tax note also discloses two research incidents (its §12.3):
nothing from them is used here, and the cached PDFs it lists can be deleted.

Opened or queried for the revision on 2026-10-10 (evening), as listed under **Revision checks** at the top:

* [verify-data-expansion.md](verify-data-expansion.md), the review this revision answers;
* [data.sba.gov DKAN API spec](https://data.sba.gov/api/1), the [7(a)](https://data.sba.gov/api/1/datastore/imports/fc21a598-913d-5c29-b7c1-1924ce608538) and [504](https://data.sba.gov/api/1/datastore/imports/47fa0223-0a71-562f-85f1-b4b732400efc) import records, three grouped counts, and the [FOIA data dictionary](https://data.sba.gov/sites/default/files/uploaded_resources/7a_504_foia_data_dictionary.xlsx);
* [13 CFR 120.802](https://www.ecfr.gov/current/title-13/section-120.802) (Third Party Loan), 120.920 and 120.10. These were read through the eCFR API; the HTML link redirects automated clients to an unblock page;
* [NES 2024 folder](https://www2.census.gov/programs-surveys/nonemployer-statistics/datasets/2024/) and the BPS, Texas, North Carolina and GovInfo HEAD requests;
* [Census finance datasets index](https://www.census.gov/programs-surveys/gov-finances/data/datasets.html) and the [2022 public-use page](https://www.census.gov/data/datasets/2022/econ/local/public-use-datasets.html);
* Baltimore [Part X § 105](https://codes.baltimorecity.gov/us/md/cities/baltimore/code/building-codes/X/105) and [Part II § 105](https://codes.baltimorecity.gov/us/md/cities/baltimore/code/building-codes/II/105);
* [DHCD codes page](https://www.dhcd.virginia.gov/codes);
* [Va. Code § 36-97](https://law.lis.virginia.gov/vacode/36-97/), [13VAC5-63-10](https://law.lis.virginia.gov/admincode/title13/agency5/chapter63/section10/) and [13VAC5-63-20](https://law.lis.virginia.gov/admincode/title13/agency5/chapter63/section20/) (container copies);
* 12-A DCMR § 105 and 10-C DCMR § 304 (container copies, with their dcregs URLs);
* [Georgia v. Public.Resource.Org (LII)](https://www.law.cornell.edu/supremecourt/text/18-1150): the majority's holding, its footnote on Justice Thomas, and the Thomas dissent;
* [S. 4145](https://www.govinfo.gov/content/pkg/BILLS-119s4145is/html/BILLS-119s4145is.htm);
* [Copyright Office summary of ASTM v. UpCodes](https://www.copyright.gov/fair-use/summaries/ASTM-v-UpCodes-Inc-172-F-4th-253-3d-Cir-2026.pdf);
* [Wikibase Cloud hosting policy, raw](https://www.mediawiki.org/w/index.php?title=Wikibase/Wikibase.cloud/Hosting_policy&action=raw);
* [FDIC BankFind API docs](https://api.fdic.gov/banks/docs/) (keys);
* the [BCAT layer JSON](https://services.arcgis.com/DN2fPfpggEPlLhP6/arcgis/rest/services/FEMA_BCAT_Government_Jurisdictions/FeatureServer/0?f=json) and its ArcGIS item record;
* [RFC 9309](https://www.rfc-editor.org/rfc/rfc9309.txt) and robots.txt on the 35 hosts in §5.2;
* lexflow: `lexflow/pipeline/steps.py` (lines 298, 595), `lexflow/ask/reference.py` (`SLOTS`).

Opened or queried again for this note on 2026-10-10 (first version):

* lexflow: `lexflow/pipeline/credits.py`, `lexflow/pipeline/steps.py`, `lexflow/store/db.py`, `lexflow/ask/index.py`,
  `lexflow/ask/answer.py` (not-found text), `lexflow/municipal/questions.py`, `lexflow/privacy.py`,
  `fixtures/forms/forms.json`, `curated/places/va/charlottesville.json`, [entities-contacts.md](entities-contacts.md),
  [payroll-plan.md](payroll-plan.md), [credits-research.md](credits-research.md),
  [authority-wikibase.md](authority-wikibase.md);
* the container: `/data/raw/open-us-law/` (regulation files), `us_va_regulations.parquet` (13VAC5-63-80),
  `/data/index/`, and the `governments` table (Charlottesville, Albemarle);
* [data.sba.gov 7(a)/504 FOIA](https://data.sba.gov/dataset/7a-504-foia) (licence);
* [FEMA BCAT layer](https://services.arcgis.com/DN2fPfpggEPlLhP6/arcgis/rest/services/FEMA_BCAT_Government_Jurisdictions/FeatureServer/0) (count);
* [FDIC BankFind API](https://api.fdic.gov/banks/docs/) (Virginia location count);
* [Census BPS place files](https://www2.census.gov/econ/bps/Place/) (HEAD);
* [eCFR titles API](https://www.ecfr.gov/api/versioner/v1/titles.json);
* [Treasury SSBCI program list](https://home.treasury.gov/policy-issues/small-business-programs/state-small-business-credit-initiative-ssbci/capital-program-list-of-programs-and-contacts);
* [Virginia rates by locality](https://www.tax.virginia.gov/sites/default/files/inline-files/sales-and-use-tax-rates-by-locality-by-date.xlsx) (HEAD);
* [Census 2022 finance file](https://www2.census.gov/programs-surveys/gov-finances/tables/2022/2022_Individual_Unit_File.zip) (HEAD);
* [DC Office of Tax and Revenue](https://otr.cfo.dc.gov/);
* [Wikibase.cloud hosting policy](https://www.mediawiki.org/wiki/Wikibase/Wikibase.cloud/Hosting_policy) (staged text,
  read raw; the binding copy at wikibase.cloud/hosting-policy renders by script).
