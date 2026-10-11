# Verification: data expansion (SBA programs, tax, building codes)

Checked 2026-10-10, evening (US Eastern), against [data-expansion.md](data-expansion.md) and the three research notes
it builds on: [data-sba-programs.md](data-sba-programs.md) (SBA), [data-tax.md](data-tax.md) (TAX) and
[data-building-codes.md](data-building-codes.md) (BC). Nothing was edited except this note. **This is not legal
advice.** Where a point is a licensing judgment, it is passed to counsel, not decided.

**How it was checked.**

* About 90 read-only GET and HEAD requests across about 35 hosts. Each carried the User-Agent
  `lexflow-research/0.1 (https://github.com/alibama/lexflow)` and a 25 to 60 s timeout, and requests were spaced at
  least 1.5 s apart. Nothing was written remotely, no account or key was used, and no `.env` value was read.
* **No data file was downloaded.** Data files got HEAD requests only. API reads were counts or metadata:
  * ArcGIS `returnCountOnly` and the layer and item JSON;
  * FDIC `limit=1` totals;
  * Socrata view metadata and one grouped `count(*)`;
  * the eCFR titles list and five short sections of 13 CFR;
  * data.sba.gov's DKAN schema and grouped `count` queries. These named only `projectcounty` and a count, so no
    borrower field could be returned (§W6).
* Two court documents were saved as PDFs in this session's scratchpad (`docs/`) so their text could be extracted:
  the ICC v. UpCodes opinion (1.5 MB) and the Copyright Office's summary of ASTM v. UpCodes (136 KB). HTML pages
  are in the scratchpad's `pages/` folder. Neither folder is in the repository.
* **Gap:** robots.txt was not read for each host. Requests were read-only and spaced, but before any approved job
  runs, robots.txt should be checked on each data host (M6).
* State text was read in place from the open-us-law parquet in `lexflow-app-1`, and `governments` was read from
  `/data/lexflow.db` with a read-only connection.
* CourtListener answered 429 after one search, so it was not queried again.

## Verdict

The plan is careful and mostly right: the licence quotes, case holdings, sizes and state text below check out. Fix
these before acting on it:

1. **The FOIA privacy design can be stronger than written** (W6). data.sba.gov's DKAN datastore holds both FOIA
   files and answers grouped, column-limited queries. Borrower names never need to cross the network, so the
   240.5 MB "stream everything" downloads (D15, D16) are not needed.
2. **The deck/shed answer cites the wrong section for zoning** (W2), and attributes the 18 January 2024 date to the
   regulation (W9).
3. **Georgia v. Public.Resource.Org is stated more broadly than its holding** (W3), and one line in BC says
   lexflow's outputs "are already CC BY-NC" (W12).
4. **One prototype URL returns 404** (W1). Also fix the "public domain" label on the "Now" table (W4), the
   "quoted word for word today" claim for NY and NC (W5), and the Baltimore shed cell (W8).

---

## Confirmed

### Licence and terms quotes (all verbatim unless noted)

| Source | What was checked | Result |
|---|---|---|
| [data.sba.gov 7(a)/504 FOIA](https://data.sba.gov/dataset/7a-504-foia) | Licence; cadence | "License U.S. Government Works". The DKAN record's licence is `https://www.usa.gov/publicdomain/label/1.0/` and `accrualPeriodicity` is `R/P3M`. "The data is typically available one month after the quarter has ended." |
| [sba.gov site notice](https://www.sba.gov/about-sba/open-government/about-the-sba-gov-website/) | Public domain; acknowledgement | "Government information on SBA.gov is in the public domain." It asks that "SBA's information be given appropriate acknowledgement". The page also warns that material from private parties on the site may be protected, so the statement does not cover third-party content. |
| [IRS use of content](https://www.irs.gov/about-irs/use-of-content-from-irsgov) | Copyright line | Content by federal employees "is not subject to copyright and may be freely copied. Credit is requested." A section on the official seal, names and symbols follows. |
| [CDTFA Conditions of Use](https://www.cdtfa.ca.gov/use.htm) | Public domain; seals | Site information "unless otherwise indicated, is considered in the public domain"; seals and marks "may not be used without permission of the State". |
| [AWBC terms](https://awbc.org/terms-and-conditions/) | Date; two quotes | "Last updated April 02, 2025". "Systematically retrieve data or other content from the Services to create or compile … a collection, compilation, database, or directory". Use is for "personal, non-commercial use or internal business purpose". |
| [Grants.gov API terms](https://www.grants.gov/api/terms-conditions) | Acceptance; notice | "Access to or use of the API or its content constitutes acceptance to this Agreement." The notice reads "This product uses the Grants.gov API but is not endorsed or certified by the U.S. Department of Health and Human Services." |
| [ICC Terms of Use](https://www.iccsafe.org/about/terms-of-use/) | Date; restrictions | "Last revised: May 4, 2023". The licence covers "personal, internal business, and non-commercial use". It bars "data mining, robots, or similar data gathering and extraction tools" and display "on a third-party or government website". Subscribers may copy up to 10% of a title. No AI or machine-learning wording. (The page answered this client; BC's §-numbers 4, 5 and 9 were not checked.) |
| [FDIC BankFind docs](https://api.fdic.gov/banks/docs/) | Keys; licence | "Users are currently not required to register and obtain a unique 'key'". No licence, terms or rate-limit statement on the page. |
| FEMA BCAT ([layer](https://services.arcgis.com/DN2fPfpggEPlLhP6/arcgis/rest/services/FEMA_BCAT_Government_Jurisdictions/FeatureServer/0)) | Licence fields | Item `licenseInfo` and `accessInformation` are empty, and the layer's `copyrightText` is empty: no licence stated, as BC says. |
| [Wikibase Cloud hosting policy](https://www.mediawiki.org/w/index.php?title=Wikibase/Wikibase.cloud/Hosting_policy&action=raw) (staging copy) | Required conditions | "The structured data is in the public domain or released under CC0." The licence for text "allows commercial and non-commercial use and derivatives". A `Project:Copyrights` statement is also required. The page warns that the binding copy is at wikibase.cloud/hosting-policy, as data-expansion says. |
| [Baltimore codes site](https://codes.baltimorecity.gov/us/md/cities/baltimore) | Public domain; bulk | "The codes and laws on this website are in the public domain. Please do not scrape. Instead, bulk download the HTML or XML." GitHub API: `law-xml` 14,637 KB, pushed 2026-09-28; `law-html` 138,416 KB; both `license: null`. |
| Florida 61G20-1.001 (on disk, `in_force`, 2026) | Copyright line | (2) The incorporated FBC "is copyrighted material that is available for public inspection". (1) names the 8th Edition (2023), as updated through December 9, 2025. |
| [SST rate and boundary files](https://www.streamlinedsalestax.org/Shared-Pages/rate-and-boundary-files) | Notice; use | "© Copyright 2018 Streamlined Sales Tax Governing Board, Inc."; the files are "created for use in your tax calculation applications". |
| [SAM.gov Assistance Listings API](https://open.gsa.gov/api/assistance-listings-api/) | Rate limit | A non-federal user with no SAM.gov role gets "10 requests/day". |
| Texas `jrea-zgmq`, NY `iq85-sdzs` (Socrata metadata) | Licence; rows | TX: licence "Public Domain". NY: no licence field, rows updated 2025-10-23. Roll-year counts: 2024 = 2,832, 2023 = 2,911. |
| open-us-law manifest (container) | Licence; vintage | `license_data: CC-BY-NC-4.0`, `license_scripts: Apache-2.0`, `v2026.09.1`, snapshot `2026-09-30`. `credits.py` says "Commercial use needs a licence from Vaquill AI." |
| [Treasury SSBCI table](https://home.treasury.gov/policy-issues/small-business-programs/state-small-business-credit-initiative-ssbci/capital-program-list-of-programs-and-contacts) | Vintage | "DATA CURRENT AS OF 8/25/2026". Its contact column holds named staff mailboxes, so dropping it (P1) is right. |
| [DC OTR](https://otr.cfo.dc.gov/) and D.C. Code § 47-2002 (on disk) | Version flag | OTR: "The increase in the general sales tax rate to 7% has been postponed. The general sales tax rate remains 6% through September 30, 2027." The snapshot reads "6.0% before October 1, 2026, and 7.0% beginning on October 1, 2026". The E3 and N5 reasoning holds. |

### Case law (BC §2.2, data-expansion E5 and §4.1)

* **Georgia v. Public.Resource.Org, Inc.**, 590 U.S. 255 (27 April 2020), 5–4, Roberts, C.J.
  ([LII](https://www.law.cornell.edu/supremecourt/text/18-1150);
  [citation](https://en.wikipedia.org/wiki/Georgia_v._Public.Resource.Org,_Inc.)).
  * The holding is quoted correctly: "We hold that the annotations in Georgia's Official Code are ineligible for
    copyright protection".
  * The doctrine as stated: "judges—and, we now confirm, legislators—may not be considered the 'authors' of the
    works they produce in the course of their official duties". It applies "regardless of whether a given material
    carries the force of law".
  * BC is right that it did not decide privately written model codes incorporated into law. See W3 for what it
    did not settle.
* **Veeck v. SBCCI**, 293 F.3d 791 (5th Cir. 2002) (en banc)
  ([opinion](https://law.resource.org/pub/us/case/reporter/F3/293/293.F3d.791.99-40632.html)).
  * The vote was **9–6**: 15 judges sat, and Judge Wiener's dissent was joined by five.
  * Both quotes are verbatim: "as law, the model codes enter the public domain and are not subject to the copyright
    holder's exclusive prerogatives", and "The copyrighted works do not 'become law' merely because a statute
    refers to them."
* **ASTM v. Public.Resource.Org (ASTM II)**, 896 F.3d 437 (D.C. Cir., 17 July 2018). Tatel wrote for the court, and
  Katsas concurred.
  * A CourtListener phrase search for "far thornier question" with "incorporated by reference" returned exactly
    this opinion. That settles BC §8 item 8: the phrase is in the opinion, not only in the blog excerpt.
* **ASTM v. Public.Resource.Org** (D.C. Cir., No. 22-7063, 12 September 2023, Katsas, J.)
  ([Stanford summary](https://fairuse.stanford.edu/case/american-society-for-testing-and-materials-v-public-resource-org-inc)).
  * The court concluded that "Public Resource's non-commercial posting of incorporated standards is fair use", and
    that the district court "reasonably declined to enter an injunction".
  * PRO had already removed the 32 standards found not to be incorporated.
  * The 82 F.4th 1262 reporter cite was not re-checked (CourtListener 429).
* **Int'l Code Council v. UpCodes**, 17 Civ. 6261 (VM), 2020 WL 2750636 (S.D.N.Y.), decided 26 May 2020 and filed
  27 May ([opinion](https://sites.uci.edu/ipat/files/2021/04/Int_l-Code-Council_-Inc.-v.-UpCodes_-Inc._-2020-U.S.-Dist.-LEXIS-92324.pdf)).
  * Both cross-motions for summary judgment were "DENIED", and the parties were ordered to submit "a timeline for
    trial".
  * The court said "the law of the public domain will not protect the posting of the I-Codes as I-Codes or the
    I-Code Redlines". So BC's line ("accurate text as adopted … never unadopted model text or redlines") states
    the decision correctly.
  * BC's quote starts mid-sentence. The original begins "Though the Court holds that Defendants' accurate posting
    of the I-Codes as Adopted is protected as a matter of public domain law, the Court would also reach the same
    result under the rubric of fair use." Restoring "Though" is optional.
* **ASTM v. UpCodes, Inc.**, 172 F.4th 253 (3d Cir. 2026)
  ([Copyright Office summary](https://www.copyright.gov/fair-use/summaries/ASTM-v-UpCodes-Inc-172-F-4th-253-3d-Cir-2026.pdf)).
  * It affirmed the denial of a preliminary injunction. The first three factors favour fair use and the fourth is
    "equivocal". The outcome is recorded as "Preliminary finding; Fair use found".
  * UpCodes is for-profit, but account holders "can view currently incorporated standards for free". BC's summary
    is accurate. (See M10 for a detail worth adding.)
* **Pro Codes Act of 2026**, S. 4145 ([govinfo](https://www.govinfo.gov/content/pkg/BILLS-119s4145is/html/BILLS-119s4145is.htm)).
  * Introduced 19 March 2026 by Mr. Coons, with Mr. Cornyn, Ms. Hirono and Mr. Tillis; referred to the Committee
    on the Judiciary.
  * It would add "Sec. 123. Works incorporated by reference into law". A standard "shall retain such protection" if
    it is made "publicly accessible online at no monetary cost", in a format with a searchable table of contents
    and index.
  * The House companion number (H.R. 4009) was not checked.

### Personal-data handling for loan data (data-expansion §4.4; SBA §5)

* The publisher's own column lists (DKAN `schema`, read with `results=false`, so no row was returned) confirm the
  personal fields. 7(a) has 42 columns, and 504 has 39. Both include `borrname`, `borrstreet`, `borrcity`,
  `borrstate` and `borrzip`, plus `businesstype`, `businessage`, `loanstatus`, `paidinfulldate`, `chargeoffdate`,
  `grosschargeoffamount` and `jobssupported`.
* **Every name on the P1 allowlist is a real column, and none of them is a borrower field.** The "never read" list
  omits `BorrState`, `FirstDisbursementDate`, `RevolverStatus` and `FranchiseName`. That is harmless, because P1
  is an allowlist.
* P4 to P8 (counts from 5, amounts from 11, no differencing, no quasi-identifiers, attacker tests) mirror the payroll
  rules and are adequate for a file whose names are already public. P9 to P11 keep users' figures and addresses
  local. Two additions are in M1 and M2.

### API limits, sizes and vintages for a sample

| Item | Plan says | Checked (HEAD or count, 2026-10-10) |
|---|---|---|
| D15 7(a) FOIA FY2020–present | 181.1 MB | 181,130,871 B, Last-Modified 2026-07-21 |
| D16 504 FOIA FY2010–present | 59.4 MB | 59,412,738 B, 2026-07-21 |
| D2 SOP 50 10 8.1 | 1,072 KB | 1,071,898 B, 2026-10-07. The [SOP page](https://legacy.sba.gov/document/sop-50-10-lender-development-company-loan-programs) says "Version 8.1 with Technical Updates, Effective: October 1, 2026" |
| eCFR titles | T13 and T26 up to date as of 2026-10-07 | Same. T13 last amended 2026-09-29, T26 2026-10-06 |
| 13 CFR 121.201 | 1,102 rows; 722511 $11.5 M; 236118 $45.0 M | 1,102 `<TR>` rows; "Full-Service Restaurants $11.5"; "Residential Remodelers $45.0" |
| 13 CFR 121.301(b)(2) | TNW $20 M, net income $6.5 M | Same |
| 13 CFR 120.151, 120.931, 120.707 | $5 M 7(a); $5 M / $5.5 M 504; microloan uses | Same. $5.5 M applies "for each Project" of the listed kinds. The $50,000 microloan limit is not in 120.707, which is correctly attributed to SBA's lender page |
| FDIC VA locations | 1,851, index `locations_20261009090008` | Same. Charlottesville: 43 |
| BCAT | 6,722 rows (10 states), 33,041 national, `maxRecordCount` 2000 | Same. `Contact_Email` is a field, as noted |
| D14 BPS 2025 | ≈ 2.9 MB | 692,949 + 1,198,782 + 847,668 + 322,164 = 3,061,563 B (2.92 MiB), all 2026-05-14. The folders are `South Region/`, `Midwest Region/`, `Northeast Region/` and `West Region/` |
| D28 Census finance 2022 | 9,719,280 B | Same, Last-Modified 2026-08-04 |
| D20 CBP 2023 county | 12 MB | 12,919,520 B, 2025-06-26 |
| D18 OZ list | 276,974 B | Same |
| D34 SBIR, no abstracts | 91.6 MB | 91,580,645 B, 2026-10-07 |
| D4 IRS Pubs 334 and 583 | 115,396 + 65,029 B | Same |
| D5 VA rates | 83,424 B, 2026-08-28 | Same |
| D8 WA Rates_26Q4.zip | 4,420 B | Same |
| D12 NY Pub 718 | 215,766 B | Same, 2025-01-27 |
| D11 FL DR-15DSS | ≈ 204 KB | 208,772 B (204 KiB), 2025-12-09 |
| D13 SST NC and WA | 15,870 + 58,577 B | Same (via a 302 to `www.`) |
| D10 IL ordmache | 31,004 B | 200, 2026-06-30 (no length on HEAD) |
| D27 OLRC Title 26 | site under maintenance | Still "Site is currently under maintenance" |
| GUS workbook (on disk) | 11,459,763 B | Same |
| Regulation parquet (on disk) | 145.7 MB for 7 states; none for CA, TX, NY | 145,702,717 B; no CA, TX or NY file |

### The deck/shed walk-through (data-expansion §3.1; BC §1)

Read from `us_va_regulations.parquet` (`in_force`, last amended 2024) and the statute parquet, with each row's
`source_url`:

* **13VAC5-63-80** ([LIS](https://law.lis.virginia.gov/admincode/title13/agency5/chapter63/section80/)). A is 108.1;
  item 1 is "Construction or demolition of a building or structure".
  * B is 108.2. Its preamble includes "when an owner or an owner's agent requests that a permit be issued … a permit
    shall be issued".
  * Item 2 (the shed text) is quoted correctly, including "not classified as a Group F-1 or H occupancy".
  * Item 13 is "minor and ordinary". Exception 1 (historic districts: siding, roofing and windows) and Exception 2
    (special flood hazard area) are quoted correctly.
  * **None of the 16 items exempts decks.** 14.6 is about roof decking.
  * C (108.3) contains "In no case shall an applicant be required to appear in person". D (108.4) covers the
    contractor licence or written statement, plus local taxes. F (108.6) says "a form supplied by the local
    building department".
* **13VAC5-63-70** ([LIS](https://law.lis.virginia.gov/admincode/title13/agency5/chapter63/section70/)). 107.1.1 is
  the fee schedule. 107.2 says the local building department "shall collect a 2.0% levy of fees charged for permits"
  for the Code Academy, and localities with their own accredited academy keep it.
* **13VAC5-63-10.** Says "also known as the 2021 edition of the USBC". 101.2 incorporates IBC chapters 2 to 35 and
  the codes and standards they reference.
* **The other states:**
  * Va. Code § 36-98 (supersession) and § 36-105 are verbatim. § 36-105 A covers towns under 3,500 that "may elect"
    to enforce, with the county enforcing otherwise; § 36-105 B is the $2,500 inspection waiver.
  * DC 12-A DCMR 105 (`in_force`, 2020): item 8 (the shed: 50 sq ft, under ten feet, one per lot) and item 13 (the
    playhouse, 36 sq ft) are verbatim, and "subject to historic and Flood Hazard Area restrictions" is present. No
    deck item.
  * NY 19 NYCRR 1203.3(a)(1) ([LII](https://www.law.cornell.edu/regulations/new-york/19-NYCRR-1203.3)): the opt-in
    and the 144 sq ft item (i) are verbatim.
  * N.C.G.S. 160D-1110(c)(1) ([ncleg](https://www.ncleg.gov/EnactedLegislation/Statutes/HTML/BySection/Chapter_160D/GS_160D-1110.html)):
    $40,000 and the decking, pickets, railings and stair treads text are verbatim.
  * WAC 51-51-003 adopts the 2021 IRC except "chapters 11 and 25 through 43", so Chapter 1, including R105.2,
    applies. The 71 chapter 51-51 sections on disk have no R105 amendment. WAC 51-51-008 gives March 15, 2024.
  * The [DHCD codes page](https://www.dhcd.virginia.gov/codes) says the 2021 USBC took effect Jan. 18, 2024.
* **Charlottesville.** In the `governments` table it is `gov_id` 47210400100000 (`municipality`, county FIPS 51540,
  place FIPS 14968, population 45,672). Albemarle County is 47100200200000 (51003).
* The [SBA Virginia district page](https://legacy.sba.gov/district/virginia) gives the service area as stated.
  [SBA's grants page](https://www.sba.gov/loans/additional-funding-opportunities/grants/) says "SBA does not provide
  grants for starting and expanding a business."

### Nothing downloads without approval

* Every row D1 to D41 in data-expansion §5 is marked **needed**. The page reads in R1 and the Fairfax and
  Charlottesville reads in Phase 0 are marked "approval to run". Phase 0 uses only files already on disk.
* The research incidents are disclosed and no data from them is used:
  * TAX §12.3: EO BMF state CSVs were sent in full to `/dev/null` when range requests were ignored, and some PDFs
    were cached by the fetch tool;
  * BC's header: cached opinion and rule PDFs;
  * SBA's header: ≤ 1 KB range reads of the FOIA CSVs. A 1 KB read crosses the header line and the first borrower
    row or two, even though only the header was kept. The DKAN `schema` read used here gives the column names with
    no rows; prefer it next time.

### Repository facts

* `credit(name, by, licence, url, use, cite="", note="", cite_by="lexflow", licence_url="")` and `used_for(c, use)`
  are as stated (`lexflow/pipeline/credits.py`).
* `Step` is a dataclass, and `STEPS` is defined (`lexflow/pipeline/steps.py`).
* `QUESTIONS` has `records` and `business` (`lexflow/municipal/questions.py`).
* `is_office_mailbox` and `is_office_phone` exist (`lexflow/privacy.py`).
* The not-found text is at `lexflow/ask/answer.py:248`.
* `index.py` `effective()` reads only the heading parenthetical.
* `forms.json` uses `record_sealing`, and `curated/va/business.json` and `curated/places/va/charlottesville.json`
  exist.
* `st_score` counts `governments`, which supports keeping districts in their own table. `st_governments` also
  hard-codes `total: 38_736` and a 30,000 "done" threshold, a second reason to keep districts out.

---

## Wrong (with evidence)

**W1. The NES URL returns 404** (data-expansion D21; SBA §3.18 and §7 item 10).
* `…/nonemployer-statistics/datasets/2024/nonemp24co.zip` → **404**.
* The 2024 folder holds only `historical-datasets/`, and the file is
  `https://www2.census.gov/programs-surveys/nonemployer-statistics/datasets/2024/historical-datasets/nonemp24co.zip`
  (4.4M, 2026-09-29).

**W2. The zoning cite in the rendered answer is wrong** (data-expansion §3.1: "Zoning setbacks still apply
([13VAC5-63-20])"; BC §1.3).
* 13VAC5-63-20 (102.2) says the USBC "shall supersede the building codes and regulations of the counties,
  municipalities…". It then preserves only listed land-use conditions: proffers, special exceptions and use permits,
  cluster conditions, airport or highway overlays, historic districts and NFIP floodplain rules. It never mentions
  setbacks.
* The right authority is **Va. Code § 36-97**: "'Building regulations' does not include zoning ordinances or other
  land use controls that do not affect the manner of construction or materials" (on disk, amended 2023,
  <https://law.lis.virginia.gov/vacode/36-97/>). The setback itself comes from the locality's zoning ordinance
  (via LOCUS and a link).
* The 108.2 preamble ("other applicable requirements of this code") means the USBC, not zoning.

**W3. Georgia v. PRO is stated more broadly than it held** (BC §2.2 row: "It settles that state-authored law text
(statutes, regulations, and plausibly state amendments written by legislators) carries no copyright";
data-expansion §4.1: state building regulations are "government edicts (Georgia v. PRO)").
* The majority confirms the doctrine for **judges and legislators**.
* The sentence "it must follow from our precedents that statutes and regulations cannot be copyrighted" comes from
  **Justice Thomas's dissent**. The majority notes in a footnote that "Justice Thomas concedes that such assertions
  are plainly foreclosed by our government edicts precedents". That is a strong signal, not the holding.
* The building texts lexflow would quote are written by executive bodies, not legislators: the USBC by Virginia's
  Board of Housing and Community Development, and the DC supplements by DC agencies.
* Parts of that text follow ICC model language. For example, 12-A DCMR 105.2's preamble mirrors the IBC's. Georgia
  says nothing about state text that reproduces private model wording.
* Policy item 1 (quote state- and local-adopted text) may still be right, but it rests on the wider
  government-edicts doctrine, Veeck in the 5th Circuit, ICC v. UpCodes (persuasive only) and the ASTM fair-use line,
  not on Georgia alone. Say "supported by" rather than "settled by", and add C21 (M8).

**W4. "Public-domain files" mislabels the Now table** (data-expansion §0 header: "Now: no download, or under about
7 MB of public-domain files").
* N5's rate files are mostly "no licence stated" (C9). SST carries a © notice, and only CDTFA states public domain.
* N6's local schedules are C9 too, and N1 is built from the CC BY-NC compilation (C1).
* Say "small official files; licence status per §4.1".

**W5. N2 overstates the "quoted word for word today" claim for NY and NC** (data-expansion §0 N2: "In these four
states the exemption list is state text that can be quoted word for word today").
* NY Part 1203 is not on disk. There is no NY regulations file, and D25 needs approval.
* NC's statute settles the deck question but not the shed (BC §8 item 4).
* Today the claim holds for VA and DC; NC holds for decks only, and NY after D25.

**W6. "The FOIA CSVs have no grouped query" is wrong, and the privacy design can be stronger** (data-expansion P3
and O7; SBA §5 rule 2).
* The data.sba.gov DKAN datastore holds both files: 7(a) FY2020–present (`fc21a598-…`, **388,338 rows**, 43 columns
  with `record_number`) and 504 FY2010–present (`47fa0223-…`, **117,983 rows**).
* Its published API spec documents `properties` (column projection), `conditions`, `groupings`, and aggregate
  expressions `sum`, `count`, `avg`, `max` and `min`. A GET with only `count(record_number)` and `projectcounty`,
  grouped by `projectcounty` with `projectstate = VA`, returned **130 county rows of name and count only**.
* What follows:
  * Borrower fields never need to cross the network. Use grouped counts for the count cells, and a column-limited
    projection for medians (there is no median operator). The spec also lists a
    `GET /api/1/datastore/query/{distributionId}/download` endpoint, which was not called. Projections are far
    smaller than 240.5 MB.
  * `max`, `min` and small-cell `avg` are single loans' exact amounts, so P4 must forbid publishing them, as it
    already does for medians.
  * The spec has a 503 response ("Datastore queries are temporarily limited due to high server load"), so the job
    needs back-off.
  * This answers SBA open question 5: `ProjectCounty` is an upper-case name, with independent cities as "… CITY".
    Charlottesville appears as **"CHARLOTTESVILLE CITY": 37 7(a) approvals, FY2020 to the 30 June 2026 file**, a
    server-side count. So `FAIRFAX` and `FAIRFAX CITY` are told apart by the suffix.
  * It is still a data pull, so it still needs the user's approval. It replaces D15 and D16, and P3 becomes
    "project at the server".

**W7. The Census finance licence quote is credited to the wrong page** (data-expansion `CENSUS_FINANCE`; TAX §2.7).
* The quoted words are not on the 2022 public-use page used as the credit URL.
* They are on the finance datasets index page, <https://www.census.gov/programs-surveys/gov-finances/data/datasets.html>,
  and read "Datasets are **usually** for public use, and users may analyze, extract, customize and publish
  statistics."
* Fix the `licence_url` and keep "usually".

**W8. The Baltimore shed cell is wrong** (data-expansion §3.1 table: Baltimore shed = "IRC item 1 not adopted";
BC §1.7).
* [Part X § 105](https://codes.baltimorecity.gov/us/md/cities/baltimore/code/building-codes/X/105) marks Building
  items "1. to 3. {Not Adopted} 4. {As in IRC} 5. {Not Adopted} 6. to 8. {As in IRC} 9. to 10. {Not Adopted}". BC
  omits item 5 (sidewalks and driveways in the model IRC).
* § 105.1.1 adds the permit requirements of the city Building Code § 105.1, and BC notes that Part II keeps IBC
  item 1 "As in IBC".
* Whether a house shed in Baltimore is exempt is therefore **unresolved**. The cell should say "open: check Part II
  item 1 against Part X", not imply that a permit is required. The deck cell (item 10 not adopted) stands.

**W9. The effective date is attributed to the regulation** (data-expansion §3.1 step 5 and the rendered answer:
"13VAC5-63-10 … in effect since 18 January 2024").
* 13VAC5-63-10 gives the edition, but the date is not in the regulation text: a search of all 81 sections found no
  "2024".
* Cite DHCD ("2021 Virginia Codes effective Jan. 18, 2024") for the date.

**W10. BC §6 P3 says no approval is needed for NY Part 1203.**
* It says "none (the PDF is already read …)", approval "no". A PDF cached by a research tool is not an approved
  input.
* data-expansion D25 ("needed") is right, so mark BC's row superseded.

**W11. Minor figures and line references to update.**
* D6 TX `city-rates.xlsx` is **340,481 B** (2026-10-06), and D9 NC CSV is **1,370 B** (2026-07-01). Both were "not
  reported".
* D14's region folders carry " Region".
* The regulations switch is at `steps.py:298`, not line 281 (TAX §1.2).
* `reference.py` `SLOTS` already has `amount` and `order`, as well as `fee`, `deadline`, `office` and `yes_no`
  (TAX §8.5).

**W12. A legal conclusion is stated as fact** (BC §2.4 item 6: "lexflow's own outputs are already CC BY-NC").
* CC BY-NC sets conditions on sharing the licensed material and adaptations of it. Whether a given lexflow output is
  an adaptation is exactly counsel question C1.
* Reword it as a question, and do not label outputs.

**W13. The `regulations` card's "No download" holds only where the add-on is present** (data-expansion §2.1).
* "No download" is true only where the add-on is already on disk, as in this container.
* On a fresh install, the card depends on the statutes step's regulations option, which `steps.py` describes as
  "regulations add 2.1 GB". The card should show that cost and need the same approval.

---

## Missing

* **M1. Make DKAN projection the default for FOIA, with its own tests** (from W6).
  * Add an attacker test to P8: the query builder must refuse any `properties` entry outside the allowlist.
  * Never publish `min`, `max` or `avg` for cells under 11.
  * Record the distribution IDs and `asofdate` as the vintage.
* **M2. `ThirdPartyLender_Name` (504) can be a person.** Private or seller financing appears in that column. P7
  ("organisations are named") needs an organisation check, or the ≥ 5-loan threshold per name, before a third-party
  lender is shown. The threshold is in §3.2 step 5 but not stated as a privacy rule.
* **M3. DC historic districts.**
  * 12-A 105.2 exemptions are "subject to historic … restrictions" (105.2.5).
  * 10-C DCMR 304 (on disk) lists "Construction or replacement of a … deck, patio, garden storage shed" among work
    needing historic-preservation review.
  * `permit_required` rule 5 has `historic_district = false` but no row for true, and the DC answer should say so.
* **M4. Wikibase disqualifiers.** The same policy disqualifies instances holding "data about living people …
  without appropriate local rules", and instances whose size or load is excessive. That bears on publishing contact
  and lender entities, and on loading 38,640 governments plus lenders. Add it to §4.2 and O6.
* **M5. FDIC keys.** The docs say keys are "currently not required", then speak of "the safekeeping of your key".
  Plan for a key becoming required. The user would request it; lexflow must not.
* **M6. robots.txt before any approved job.** Check it on data.sba.gov, api.fdic.gov, services.arcgis.com,
  www2.census.gov, www.ecfr.gov, data.ny.gov, the revenue sites and codes.baltimorecity.gov. (Baltimore's page says
  "Please do not scrape", and its bulk files are the route.)
* **M7. BCAT details.**
  * The layer has a `Local_Code_Weakening_Note` field that the D22 `outFields` list leaves out. It may matter for
    "code in force".
  * The ArcGIS item's `owner` is a named contractor employee's account. Credit FEMA, and never copy `owner`, just as
    `Contact_Email` is never copied.
* **M8. Add counsel question C21** (from W3). Is state or District regulation text that reproduces ICC model
  language (USBC Chapter 1, the DC supplements) government-edict text that may be quoted in full, or does part of it
  remain ICC's?
* **M9. Pro Codes Act condition.** Besides free online access, the bill requires "a searchable table of contents and
  index, or equivalent aids". Note this in BC §2.2 and C19.
* **M10. ASTM v. UpCodes went one level deeper.**
  * The standards there were incorporated **through the 2018 IBC**, as adopted by Philadelphia, and UpCodes copied
    their non-mandatory parts too.
  * Virginia's 101.2 likewise incorporates "any codes and standards referenced in the IBC".
  * Worth a line in BC §2.2: lexflow stores none of these referenced standards, and links only.

---

## Not re-checked

* The 82 F.4th 1262 reporter cite, ICC v. UpCodes' later history, and the H.R. 4009 companion number (CourtListener
  429; congress.gov not tried).
* The Virginia Tax "All Rights Reserved" PDF and the Weldon Cooper terms. The VA PDF is a data table and was not
  opened.
* The HUBZone tract count for Charlottesville. The GeoServer was not queried, since bulk use is C6.
* IRC R105.2 from ICC itself (BC §8 item 1), the CRC 120 sq ft figure, FBC § 105.2, and the OPEN-NY terms PDF.
* Not tested: the eCFR's 406 without gzip, the Census API key redirect, the SBIR API 403, and SSBCI's 53-program
  count for the 10 states (the page was read, but its rows were not counted).
