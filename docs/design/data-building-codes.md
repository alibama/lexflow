# Building codes and permit rules: sources, copyright and a plan

Status: research and design, 2026-10-10. Nothing described here is built. No file other than this note was changed. **Corrected the same evening** where [verify-data-expansion.md](verify-data-expansion.md) found errors: the zoning authority (W2), the reach of Georgia v. PRO (W3), what can be quoted today (W5), Baltimore's shed rule (W8), the effective-date source (W9), the NY approval (W10), the CC BY-NC line (W12), and the missing DC historic rule, BCAT field, Pro Codes condition and ASTM v. UpCodes detail (M3, M7, M9, M10). See [data-expansion.md](data-expansion.md) for the revision's checks.

This note asks which data would let lexflow answer building-code and permit questions for its 10 states and their local governments, and how to use it without breaking anyone's copyright. The test question is the one lexflow could not answer: **"Do I need a building permit for a deck or a shed, and how do I get one?"** Virginia's statutes do not say. The Uniform Statewide Building Code regulation and the local building department do. Two more questions are used as checks: "Which building code edition applies in my county?" and "What setback applies to a shed in my city?"

**This is not legal advice.** Section 2 summarises court decisions and terms of use so that counsel can decide the licensing questions. It does not decide them.

How it was checked:

* Every claim was checked against a page, file or API response opened on 10 October 2026. Links are given inline. Claims that could not be checked are marked **unverified** and listed in §8.
* All web requests were read-only GETs with the User-Agent `lexflow-research/0.1 (https://github.com/alibama/lexflow)`. They had 15–30 s timeouts and were spaced at least 1 s apart per host. No accounts were created, no keys were requested and nothing was written to any remote site.
* No dataset, archive or package was downloaded. The API reads were small:
  * ArcGIS item metadata and layer schemas, server-side counts (`outStatistics`, `returnCountOnly`), and 3 sample rows for Charlottesville and Albemarle County;
  * one 700-byte ranged read of a Census file header;
  * Internet Archive search counts and metadata for 5 items;
  * one CourtListener search API call, for reporter citations;
  * GitHub repository metadata for 2 repositories.

  The fetch tool cached some of the PDF *documents* it opened (court opinions, a Copyright Office summary, a New York rule, a California guide and some local checklists) in this session's `tool-results` folder. They are documents, not data. None was added to the repository.
* State law was read from the open-us-law files already in the container (`/data/raw/open-us-law/`, manifest version `v2026.09.1`, snapshot 2026-09-30). Each quote links to the official URL stored with that section.
* **Copyright rule for this note.** Statutes, regulations, court opinions and federal documents are quoted, since the law itself is not copyrighted (§2.2). Text written by private bodies is paraphrased, not quoted. That covers ICC and NFPA codes and terms, UpCodes, publishers' terms and law-firm or press summaries. This is why the IRC exemption list in §1.2 is described in words and numbers, not quoted.
* **Privacy rule for this note.** It names organisations and official channels only. FEMA's adoption layer has a `Contact_Email` column, and its values were never requested. Building-permit records name owners, but no permit record was read.
* **robots.txt and blocking.** `codes.iccsafe.org` refuses automated clients: CloudFront returns 403 even for `robots.txt`. `up.codes/robots.txt` disallows every user agent except named search engines. Neither site was crawled. On UpCodes, one fetch of `up.codes/terms` (an empty JavaScript shell) came before `robots.txt` was read. The command that read `robots.txt` then made four path probes: `/terms` returned 200, and the other three returned 404. Nothing more was requested from that host.

---

## 0. The short version

| # | Finding | What it means for lexflow |
|---|---|---|
| F1 | **The key text for Virginia is already on disk.** The open-us-law regulations file for VA holds all 81 sections of the USBC (13VAC5-63, 130,567 words), and the permit exemption list (13VAC5-63-80 B, "Section 108.2") is among them. The same add-on also holds DC's Construction Codes supplements (12 DCMR, 452 in-force sections), Maryland's COMAR 09.12.50–.58, Washington's WAC 51 chapters (706 sections), Florida's 61G20 and Illinois's 71 Ill. Adm. Code 400/600. | A building-code search index can be built **with no download** for 7 of the 10 states. Today `lexflow/ask/index.py` indexes statutes only, which is why the deck question came back "not found". |
| F2 | **Permit exemptions are state text in VA, DC, NY and NC, and local text elsewhere.** VA, DC and NY wrote their own lists into regulations. North Carolina's rule is in a statute (G.S. 160D-1110(c)). In MD, CA, TX, IL and FL the list comes from Chapter 1 of the model code as adopted, or amended, by each local government. Washington adopts the IRC's Chapter 1 unamended. | The deck and shed answer can be quoted word for word today in VA and DC, from text on disk. NC's statute (on disk) settles decks but not sheds (§8 item 4). NY's Part 1203 is not on disk and needs an approved download first. Elsewhere it needs the local adopting ordinance and the model-code facts. |
| F3 | **The answers differ a lot.** VA: a detached one-story shed up to **256 sq ft** needs no permit, and decks are not exempt. DC: one garden shed up to **50 sq ft** per lot, and decks are not exempt. NY: a locality *may* exempt sheds up to **144 sq ft** if its programme says so, and decks are not on the list. Model IRC: accessory structures up to **200 sq ft**, and decks only if all four conditions hold (≤200 sq ft, ≤30 in above grade, not attached, not serving the required exit door). Baltimore City did not adopt the IRC deck and accessory-structure exemptions. Its Building Code (Part II) keeps the IBC's item 1, so whether a house shed is exempt there is still open (§1.7). | A national "no permit under 200 sq ft" answer would be wrong in most of lexflow's states. The rule must be looked up per state and per locality, with its source. |
| F4 | **Model codes are copyrighted, but the law as adopted is in contested public-domain or fair-use territory.** Veeck (5th Cir. en banc 2002): adopted model codes "enter the public domain" as law. Georgia v. Public.Resource.Org (2020): works by legislators in their official duties cannot be copyrighted. ASTM v. Public.Resource.Org (D.C. Cir. 2023): non-commercial posting of incorporated standards is fair use. ASTM v. UpCodes (3d Cir. 2026): even a for-profit site is *likely* making fair use, at the preliminary-injunction stage. ICC v. UpCodes (S.D.N.Y. 2020): accurate posting of the codes *as adopted* is protected, but copying unadopted model text and "redlines" was left for trial. The Pro Codes Act (S. 4145, 2026) would preserve copyright in standards that are offered free online, and it is still in committee. | Proposed policy, for counsel to approve: quote state- and local-authored text. For incorporated model-code text, store only facts (numbers, conditions) with a citation and a link to the free official view. Never store or show unadopted model text. Never crawl ICC or UpCodes. |
| F5 | **Free official read-only access exists for every state's current code.** ICC's free Basic view hosts VA, MD, NY, WA, NC, FL and CA, according to each state's own pages. NFPA offers free read-only access to NFPA 70 after login. IAPMO hosts California's plumbing and mechanical codes. ICC's terms forbid data mining, robots, commercial use and display on third-party or government websites. | Link to these views and never copy them. They are the "read the full text here" target for every answer. |
| F6 | **"Which edition applies in my county?" has a public, government-wide answer.** FEMA's Building Code Adoption Tracking (BCAT) layer is a public ArcGIS feature service with 33,041 jurisdictions, all with data currency 2026-06-30. It gives the IBC, IRC and IEBC edition per place and county, with adoption-history notes. The 10 states have 6,722 rows, close to the Census of Governments counts (IL 1,396 = 102 counties + 1,294 municipalities). | This is the best single source for place pages. It needs a name crosswalk (it has no FIPS or GID), one approved download of about 7k rows of attributes, and a licence check (no licence is stated). |
| F7 | **The Census Building Permits Survey names about 19,900 permit-issuing places**, with FIPS place, MCD and county codes. Its 2025 annual place files are 2.9 MB in total and in the public domain. | This tells lexflow which government actually issues permits for a place, for example a county for a small Virginia town (Va. Code § 36-105 A). It is a crosswalk, not an answer. |
| F8 | **Three states publish who adopted what.** Illinois law requires the Capital Development Board to publish each municipality's and county's code by title and edition (20 ILCS 3105/10.18(c)). California's BSC lists local amendment ordinances by cycle. Florida keeps local amendments in its Florida Building Code Online search. Maryland's Department of Labor links each county's amendments. | These are the "local amendments" layer, read jurisdiction by jurisdiction. None offers a documented bulk export, and the Illinois portal loads its data in the browser. |
| F9 | **Baltimore City publishes its building code as public domain**, with bulk HTML and XML on GitHub (`baltimore-legref/law-xml`, 14.6 MB). The site asks people not to scrape. | It is the cleanest local building-code source found, and the model for "fetch local text from the publisher's bulk files". |
| F10 | **Commercial and aggregator sites are link-only or off-limits.** UpCodes disallows all generic crawlers. Municode is already link-only in `credits-research.md`. ICC's Code Connect API is an enterprise licence. Public.Resource.Org's mirrors (archive.org `publicsafetycode`, 30,863 items, including NY's and CA's 2025 codes) rest on PRO's own legal position. | Do not ingest these. Whether lexflow may link to or rely on PRO's copies is a question for counsel. |

**Recommended order.**

1. **Now, no download.** Index the building-code regulations already on disk (§4.1). Hand-curate a `permit_required` decision table for VA and DC from state text (§4.2), then for NY and NC.
2. **Next, small downloads that need approval.** The BCAT attributes for the 10 states (§3.19), the 2025 BPS place files (§3.20), Baltimore's `law-xml` (§3.17), and the BSC and Maryland local-amendment index pages.
3. **Later.** The Illinois CDB directory (ask CDB for an export), Florida local amendments, NYC's codes, energy-code status, and local fee schedules through LOCUS.
4. **Avoid.** Crawling or storing ICC, NFPA, IAPMO, UpCodes, Municode, eCode360 or American Legal text, and bulk ingestion of Public.Resource.Org copies until counsel decides.

---

## 1. The deck and shed question, state by state

This is the content an answer needs. Wherever the rule is state law, the official text is quoted. Model-code rules are paraphrased.

### 1.1 Summary table

| State | Where the exemption list lives | Shed | Deck | Who issues the permit | Text status |
|---|---|---|---|---|---|
| **VA** | 13VAC5-63-80 B (USBC § 108.2), state regulation | Exempt if detached, one story, ≤ 256 sq ft and not Group F-1 or H | **Not on the list.** It needs a permit, unless the building official deems it "minor and ordinary" (item 13) | The local building department. Towns under 3,500 people may leave this to the county (§ 36-105 A) | State text, quoted below |
| **DC** | 12-A DCMR § 105.2 (2017 Building Code Supplement). The Residential Code points to it (12-B DCMR R101.2) | One garden storage shed ≤ 50 sq ft and < 10 ft high, one per lot. A tree house or playhouse ≤ 36 sq ft | **Not on the list.** It needs a permit | DC Department of Buildings | District text, quoted below |
| **MD** | Local. The state adds a note that Chapter 1 is local (COMAR 09.12.51.04 B(1)) | Depends on the county or city. Baltimore City did not adopt IRC R105.2 Building items 1–3, 5 and 9–10. Part II keeps IBC item 1 "As in IBC", so a Baltimore house shed is **open** until a reviewer checks Part II item 1 against Part X (§1.7) | Baltimore City: not exempt (IRC item 10 not adopted) | County or municipal building office | State note quoted. Baltimore text is public domain |
| **TX** | Local ordinance adopting the IRC "as it existed on May 1, 2012" or later (LGC § 214.212) | Depends on the city's IRC edition and amendments | Same | The city. A county under LGC ch. 233 subch. F may not require prior approval | Statute quoted. The list is local plus model text |
| **CA** | Chapter 1, Division II of the CBC and CRC as adopted locally. CRC R105.2 has California amendments | Local. A 120 sq ft limit is reported for the CRC (**unverified**) | Local | City or county building department | Model plus state text, free on ICC |
| **FL** | Florida Building Code, Building and Residential § 105.2 (a state code published by ICC), plus local administrative amendments | Statewide text, not read here (**unverified**). Prefabricated sheds with a state insignia skip local plan review but still need local permits and inspections (Fla. Stat. § 553.80(1)(d)) | Statewide text, not read here | Local enforcement agency | State statute quoted. The FBC is "copyrighted material" according to the adopting rule |
| **NY** | 19 NYCRR 1203.3(a)(1), state regulation. A locality *may* exempt listed categories | Exempt only if the local programme says so: ≤ 144 sq ft, one story, detached, tool shed, playhouse or similar | **Not on the list.** It needs a permit | The city, town or village code enforcement officer. NYC has its own codes (Exec. Law § 383(1)(c)) | State text, quoted below |
| **IL** | Local codes. CDB publishes which code each municipality and county adopted | Local | Local | Municipality or county. "Non-building code jurisdictions" have no permit system | Statute quoted |
| **WA** | IRC R105.2, adopted statewide by WAC 51-51-003 with no state amendment to R105 | Model IRC: ≤ 200 sq ft | Model IRC: four conditions (§1.2) | City or county. Local residential amendments need State Building Code Council approval | Model text. WAC adoption quoted |
| **NC** | G.S. 160D-1110(c), the $40,000 rule, plus the NC State Building Code's administrative chapter | The statute alone does not settle it (**open question**, §8) | New deck framing is "load-bearing structures", so it needs a permit. Replacing the decking, pickets, railings and stair treads does not | City or county inspections department | State statute, quoted below |

### 1.2 The model rule: IRC R105.2 (paraphrased; ICC copyright)

The 2021 International Residential Code, § R105.2 "Work exempt from permit", Building items, includes:

* **item 1:** one-story detached accessory structures with a floor area of no more than **200 sq ft** (storm shelters are excluded);
* **item 10:** decks that meet **all four** conditions:
  * no more than **200 sq ft** in area;
  * no more than **30 inches** above grade at any point;
  * **not attached** to a dwelling;
  * **not serving** the exit door required by § R311.4.

The list's preamble says that an exemption does not authorise work that breaks the code or other local laws, so zoning still applies.

Verified from local-government reproductions, not from ICC, because `codes.iccsafe.org` refuses automated requests:

* the City of Lynnwood, WA checklist "Work exempted from building permit" (June 2024, [PDF](https://lynnwoodwa.gov/files/sharedassets/public/v/1/dbs/checklists/building/work-exempted-from-building-permit-2024.06.pdf)). It reproduces items 1 and 10 with these numbers.
* Grant County, WA's sheet headed "2021 International Residential Code (IRC) Section R105 Permits" ([PDF](https://www.grantcountywa.gov/DocumentCenter/View/5840/Exempt-R1052)). Its building items could not be extracted, so it confirms only the edition and section.

Local governments change these numbers often. Boise, for example, cuts the deck height to 12 inches, according to a search summary only (**unverified**).

### 1.3 Virginia: the state text (13VAC5-63-80, "Section 108")

Source: [13VAC5-63-80](https://law.lis.virginia.gov/admincode/title13/agency5/chapter63/section80/), last amended 2024. The VAC calls this the 2021 edition of the USBC.

* The **permit duty** (108.1): "Application for a permit shall be made to the building official and a permit shall be obtained prior to the commencement of any of the following activities … 1. Construction or demolition of a building or structure."
* The **exemption preamble** (108.2): "application for a permit and any related inspections shall not be required for the following; however, this section shall not be construed to exempt such activities from other applicable requirements of this code. In addition, when an owner or an owner's agent requests that a permit be issued for any of the following, then a permit shall be issued and any related inspections shall be required."
* **Sheds** (item 2): "One story detached structures used as tool and storage sheds, playhouses, or similar uses, provided the building area does not exceed 256 square feet (23.78 m 2 ) and the structures are not classified as a Group F-1 or H occupancy."
* **The discretionary catch-all** (item 13): "Construction work deemed by the building official to be minor and ordinary and that does not adversely affect public health or general safety."
* **Exceptions:** "1. Application for a permit may be required by the building official for the installation of replacement siding, roofing, and windows in buildings within a historic district designated by a locality pursuant to § 15.2-2306 of the Code of Virginia. 2. Application for a permit may be required by the building official for any items exempted in this section that are located in a special flood hazard area."
* **Decks:** none of the 16 items covers new decks. Other sections mention decks for structural rules (for example 13VAC5-63-410 on reconstructed decks 30 inches or more above grade), not for exemption. This reading is offered for the curated model to confirm with DHCD.
* **How to apply** (108.3): "A permit application may be submitted by mail and such permit applications shall be processed by mail, unless the jurisdiction offers an online permit option … In no case shall an applicant be required to appear in person." 108.4 requires proof of a contractor licence, or a written statement that the applicant is not subject to licensing (§ 54.1-1111). 108.6 says the application is "on a form supplied by the local building department."
* **Fees** ([13VAC5-63-70](https://law.lis.virginia.gov/admincode/title13/agency5/chapter63/section70/), 107.1.1): "The local governing body shall establish a fee schedule incorporating unit rates, which may be based on square footage, cubic footage, estimated cost of construction, or other appropriate criteria." 107.2 adds "a 2.0% levy of fees charged for permits", which goes to DHCD's Building Code Academy.
* **Statute:** the Code "shall supersede the building codes and regulations of the counties, municipalities and other political subdivisions" ([Va. Code § 36-98](https://law.lis.virginia.gov/vacode/36-98/)). On inspections, "Where the construction cost is less than $2,500, however, the inspection may, in the discretion of the inspecting authority, be waived" ([§ 36-105 B](https://law.lis.virginia.gov/vacode/36-105/)).
* **Zoning is not superseded.** The authority is the statute. "'Building regulations' does not include zoning ordinances or other land use controls that do not affect the manner of construction or materials to be used in the erection, alteration, or repair of a building or structure" ([Va. Code § 36-97](https://law.lis.virginia.gov/vacode/36-97/)). The USBC supersedes only "building regulations" (§ 36-98).
  * 13VAC5-63-20 (102.2) is narrower than first written here. It says the USBC "shall supersede the building codes and regulations of the counties, municipalities, and other political subdivisions". It then preserves only listed land-use conditions: proffers, special exceptions and use permits, cluster conditions, airport or highway overlays, historic districts and NFIP floodplain rules. It never mentions setbacks.
  * The 108.2 preamble ("other applicable requirements of this code") means the USBC itself, not zoning.
  * Setbacks are local zoning, found through LOCUS and linked. A shed with no permit still has to meet them.

### 1.4 District of Columbia (12-A DCMR § 105.2)

Source: 12-A DCMR § 105 "Permits", 2017 Building Code Supplement, final rulemaking at 67 DCR 5690 (29 May 2020). [dcregs file](https://dcregs.dc.gov/Common/DCMR/RuleList.aspx?DownloadFile={64284980-8CFE-4134-BB96-94FBB25965E0}).

* **Shed** (item 8): "A single garden storage shed that does not exceed 50 square feet (4.65 m2) in area, is less than ten feet (3048 mm) in overall height, is an accessory structure to a building of Use Group R-3 or to a building under the jurisdiction of the Residential Code, and is erected on a lot with no other exempted storage shed."
* **Playhouse** (item 13): "A tree house or playhouse, no more than 36 square feet, (3.35 m2) in area and accessory to detached one- and two-family dwellings and townhouses."
* **Limits:** the exemptions are "subject to historic and Flood Hazard Area restrictions set forth in Sections 105.2.5 and 105.2.6". There is no deck item.
  * 105.2.5 is headed "Permit Exemptions Not Applicable in Historic Districts or to Historically Designated Structures". In those places, "an application for a building permit subject only to historic preservation review pursuant to Section 105.1 shall be required" for listed items, including "8. Garden storage shed". No such permit issues "without the prior review and approval of the Historic Preservation Office".
  * 10-C DCMR 304.1(h), also on disk (in force), counts "Construction or replacement of a retaining wall, fence, deck, patio, garden storage shed, swimming pool, or other site feature" as an alteration under the historic preservation Act.
  * So the DC answer must ask whether the property is in a historic district or designated (§4.2, rules 5a and 5b).
* **Residential Code:** "Administration and enforcement of the Residential Code shall be governed by Chapter 1 of the Building Code, Title 12-A DCMR" (12-B DCMR R101.2, 67 DCR 6033).
* **Edition:** "The District of Columbia Building Code (2017) … consists of the 2015 edition of the International Building Code … as amended by the Building Code Supplement of 2017 (12-A DCMR). The International Building Code is copyrighted by the ICC and therefore is not republished here." On 11 February 2026 the Department of Buildings became the lead for code development and set a goal of adopting the 2024 codes by the end of 2027 ([DOB release](https://dob.dc.gov/release/dc-department-buildings-quicken-pace-dc-construction-code-development-under-organizational)).
* The local file also holds the superseded 2013 supplements: 376 sections, marked `superseded`. The index must keep only rows marked `in_force`.

### 1.5 New York (19 NYCRR 1203.3)

Source: DOS full text of Part 1203, effective 30 December 2022 ([PDF](https://dos.ny.gov/2021-12-10-full-text-rule-part-1203); [Part 1203 page](https://dos.ny.gov/19-nycrr-part-1203-uniform-code-and-energy-code-minimum-standards-administration-and-enforcement)).

* **The opt-in:** "Where expressly set forth in their code enforcement program, an authority having jurisdiction may exempt from the requirement for a building permit any one or more of the categories of work listed in section 1203.3(a)(1)(i) through (viii)."
* **Sheds** (item (i)): "construction or installation of one-story detached structures associated with one- or two-family dwellings or multiple single-family dwellings (townhouses), which are used for tool and storage sheds, playhouses, or similar uses, provided the gross floor area does not exceed 144 square feet".
* The other seven categories are sets and scenery, window awnings, partitions or movable cases under 5′-9″, finish work, listed portable equipment, like-for-like equipment replacement, and repairs that do not affect fire and life safety. **None covers decks.**
* **New York City:** in cities of over one million, "the existing building and fire prevention codes shall continue in full force and effect" unless the Code Council finds them less stringent ([Exec. Law § 383(1)(c)](https://www.nysenate.gov/legislation/laws/EXC/383)). NYC publishes its own 2022 Construction Codes as PDF chapters ([NYC DOB](https://www.nyc.gov/site/buildings/codes/2022-construction-codes.page)).

### 1.6 North Carolina (G.S. 160D-1110(c))

Source: [G.S. 160D-1110](https://www.ncleg.gov/EnactedLegislation/Statutes/HTML/BySection/Chapter_160D/GS_160D-1110.html).

* "No permit issued under Article 9 of Chapter 143 of the General Statutes is required for any construction, installation, repair, replacement, or alteration costing forty thousand dollars ($40,000) or less and performed in accordance with the current edition of the North Carolina State Building Code in any single-family residence, farm building, or commercial building unless the work involves any of the following: (1) The addition, repair, or replacement of load-bearing structures. However, no permit is required for replacement of windows, doors, exterior siding, or the pickets, railings, stair treads, and decking of porches and exterior decks that otherwise meet the requirements of this subsection."
* So a new deck needs a permit (it adds load-bearing structure), but re-decking does not. Whether a small detached shed is "in" a residence, and what the NC Residential Code's own scope says about small accessory buildings, are open questions (§8).

### 1.7 The other five states (what governs, in brief)

* **Maryland.** COMAR 09.12.51.04 B(1) adds a note to IBC Chapter 1: "Local jurisdictions are responsible for the implementation and enforcement of the Maryland Building Performance Standards. Refer to each local jurisdiction for local amendments to Chapter 1 of the IBC." Each jurisdiction "May by local amendment modify the provisions of the Standards to address conditions peculiar to the local jurisdiction's community" (.05 B(1)(a)) ([COMAR 09.12.51.04](https://regs.maryland.gov/us/md/exec/comar/09.12.51.04), [.05](https://regs.maryland.gov/us/md/exec/comar/09.12.51.05)).
  * In Baltimore City's Part X (IRC 2021), § 105.2 marks the Building items "1. to 3. {Not Adopted} 4. {As in IRC} 5. {Not Adopted} 6. to 8. {As in IRC} 9. to 10. {Not Adopted}" ([Part X § 105](https://codes.baltimorecity.gov/us/md/cities/baltimore/code/building-codes/X/105)). In the model IRC, items 1 and 10 are the accessory-structure and deck exemptions. The first version of this note left out item 5, which is also "{Not Adopted}".
  * Part X § 105.1.1 adds: "a permit is required before any person may do any of the work described in § 105.1 of the Baltimore City Building Code".
  * The city's own Building Code, Part II § 105.2, keeps IBC item 1 "As in IBC and subject to all local, state, and federal laws" ([Part II § 105](https://codes.baltimorecity.gov/us/md/cities/baltimore/code/building-codes/II/105)). That is the IBC's tool-shed item; its size limit was not checked.
  * So **whether a house shed in Baltimore is exempt is unresolved**. Part X drops the IRC item, but Part II's permit rule, which Part X brings in, keeps the IBC item. A reviewer must read Part II item 1 against Part X before an answer says either way. The deck answer stands, as the review found: IRC item 10 is not adopted. None of Part II's written-out items is a deck exemption. The IBC items it keeps by reference (1, 5, 9, 11 and 13) were not re-read from ICC.
* **Texas.** "the International Residential Code, as it existed on May 1, 2012, is adopted as a municipal residential building code in this state" ([LGC § 214.212(a)](https://tcss.legis.texas.gov/resources/LG/htm/LG.214.htm#214.212)). A municipality may adopt local amendments that "add, modify, or remove requirements set by the code", after a public hearing and by ordinance (§ 214.212(c), (e)). The IBC follows the same pattern (§ 214.216).
  * Counties: Subchapter F "may not be construed to: (1) require prior approval by the county before the beginning of new residential construction" ([LGC § 233.153(d)](https://tcss.legis.texas.gov/resources/LG/htm/LG.233.htm#233.153)).
  * Process: a city must grant or deny a building permit, or explain the delay in writing, within 45 days, or lose its fees ([§ 214.904](https://tcss.legis.texas.gov/resources/LG/htm/LG.214.htm#214.904)).
* **California.** Local changes to the building standards need "an express finding that such modifications or changes are reasonably necessary because of local climatic, geological, or topographical conditions", filed with the BSC ([HSC § 17958.7(a)](https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=HSC&sectionNum=17958.7.)).
  * "Commencing October 1, 2025, to June 1, 2031, inclusive", a city or county may not change residential building standards except in listed cases ([HSC § 17958.5(c)](https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=HSC&sectionNum=17958.5.)). This freezes most local residential amendments for the 2025 and 2028 cycles.
  * Local R105.2 lists exist, for example Santa Clarita's amendments to Chapter 1 Division II ([Santa Clarita ch. 18.11](https://codepublishing.com/CA/SantaClarita/html/SantaClarita18/SantaClarita1811.html), found by search and not opened).
* **Florida.** Local governments "may adopt amendments to the administrative provisions of the Florida Building Code", which "must be more stringent than the minimum standards" and must be sent to the Commission within 30 days ([Fla. Stat. § 553.73](http://www.leg.state.fl.us/statutes/index.cfm?App_mode=Display_Statute&URL=0500-0599/0553/Sections/0553.73.html)).
  * State-approved prefabricated "lawn storage buildings and storage sheds" are exempt from local plan review, but "Erection, assembly, and construction at the site are subject to local permitting and inspections" ([§ 553.80(1)(d)](http://www.leg.state.fl.us/statutes/index.cfm?App_mode=Display_Statute&URL=0500-0599/0553/Sections/0553.80.html)).
  * Each local agency "shall post each type of building permit application … on its website" and "must post its procedures for processing, reviewing, and approving submitted building permit applications on its website" ([§ 553.79(1)(b), (e)](http://www.leg.state.fl.us/statutes/index.cfm?App_mode=Display_Statute&URL=0500-0599/0553/Sections/0553.79.html)).
* **Illinois.** Municipalities and counties adopting a code must "identify the model code being adopted, by title and edition, and any local amendments to the Board" at least 30 days before it takes effect. The Board must publish the list on its website ([20 ILCS 3105/10.18(a), (c)](https://www.ilga.gov/ftp/ILCS/Ch%200020/Act%203105/002031050K10.18.html)).
  * In places with no code, a new-home contract adopts a residential code by agreement, or by default "the current edition of the International Residential Code" ([815 ILCS 670/15](https://www.ilga.gov/ftp/ILCS/Ch%200815/Act%200670/081506700K15.html)).
* **Washington.** "The 2021 edition of the International Residential Code … is hereby adopted by reference with the following additions, deletions, and exceptions" ([WAC 51-51-003](https://app.leg.wa.gov/WAC/default.aspx?cite=51-51-003)). It took effect "in all counties and cities of this state on March 15, 2024" (WAC 51-51-008).
  * The 71 sections of chapter 51-51 on disk include R101 and R102 amendments but none for R105, so the model R105.2 applies unless a city or county amends it.
  * Local residential amendments are not effective "unless the amendment is approved by the building code council" ([RCW 19.27.060(1)(a)](https://apps.leg.wa.gov/rcw/default.aspx?cite=19.27.060); [WAC 51-04-030](https://app.leg.wa.gov/WAC/default.aspx?cite=51-04-030)).

---

## 2. Copyright and licensing (summaries for counsel, not decisions)

### 2.1 What the code publishers allow

* **ICC Terms of Use** (last revised 4 May 2023, [iccsafe.org/about/terms-of-use](https://www.iccsafe.org/about/terms-of-use/)), paraphrased:
  * § 4 grants a limited, revocable licence for personal, internal business and non-commercial use only.
  * § 4 also excludes resale, commercial use, derivative use, sharing with third parties, display on a third-party or government website, and the use of data mining, robots or similar extraction tools.
  * § 5 bars reproduction, modification, derivative works and republishing without written permission. § 9 bars circumventing technical protections.
  * Subscribers may copy or print a section up to 10 % of a title.
  * The terms do not mention AI or machine-learning training.
* **ICC free view.** ICC's own 2024 I-Code page says users who are not logged in Premium subscribers see the "Digital Codes Basic" free view ([2024 I-Code updates](https://www.iccsafe.org/about/2024-i-code-updates/)). The states point to it:
  * DHCD ([codes.iccsafe.org/codes/virginia](https://codes.iccsafe.org/codes/virginia));
  * WA SBCC ([sbcc.wa.gov](https://sbcc.wa.gov/));
  * NY DOS (the 2025 code books "are free on the International Code Council website", [notice](https://dos.ny.gov/notice-adoption));
  * NC OSFM (free viewing of the 2018 NC codes, [press release](https://ncosfm.gov/news/press-releases/2025/04/07/north-carolina-delays-implementation-2024-state-building-code));
  * CA BSC (part-by-part links, [Codes page](https://www.dgs.ca.gov/BSC/Codes)).

  The view could not be opened here, because CloudFront returns 403 to automated clients, so its exact limits were not checked.
* **ICC Code Connect API.** An enterprise and reseller API to code content, launched in 2022 ([product page](https://solutions.iccsafe.org/codeconnect), [announcement](https://www.iccsafe.org/about/periodicals-and-newsroom/the-international-code-council-introduces-icc-code-connect-api/)). This is the licensed route if lexflow ever needs model text. Pricing and terms were not published.
* **NFPA** (NFPA 70, the NEC). NFPA's archived free-access page (2020, [UNT web archive](https://webarchive.library.unt.edu/web/20201218004222mp_/http://www.nfpa.org/codes-and-standards/resources/free-access)) says documents are free to read after sign-in, are read-only and cannot be downloaded or printed. NFPA says sales fund its standards process and that it must keep its copyright.
  * The live page ([nfpa.org/freeaccess](https://www.nfpa.org/freeaccess)) renders in JavaScript and could not be read.
  * California's BSC links the California Electrical Code to NFPA's free access, "login required" ([BSC Codes](https://www.dgs.ca.gov/BSC/Codes)).
* **IAPMO** hosts California's 2025 Mechanical and Plumbing Codes at `epubs.iapmo.org` (linked by the BSC). Its terms were not read.
* **Florida** says so itself: the adopting rule calls the Florida Building Code "copyrighted material that is available for public inspection and examination at the Department of State … and at the Department of Business and Professional Regulation" ([61G20-1.001(2)](https://flrules.org/gateway/ruleno.asp?id=61G20-1.001)). The statute describes the I-Codes as "copyrighted and published by the International Code Council" and the NEC as "copyrighted and published by the National Fire Protection Association" (§ 553.73).

### 2.2 The cases (summaries; persuasive weight differs by circuit)

| Case | Court and date | What it held (quoted from the opinion where possible) | Relevance |
|---|---|---|---|
| **Veeck v. Southern Building Code Congress Int'l**, 293 F.3d 791 | 5th Cir. (en banc), 2002, 9–6; Jones, J. Cert. denied, 539 U.S. 969 (2003) ([opinion](https://law.resource.org/pub/us/case/reporter/F3/293/293.F3d.791.99-40632.html); [cert. note](https://en.wikipedia.org/wiki/Veeck_v._Southern_Building_Code_Congress_Int%27l)) | "As _law,_ the model codes enter the public domain and are not subject to the copyright holder's exclusive prerogatives." "As model codes, however, the organization's works retain their protected status." It distinguished extrinsic standards: "The copyrighted works do not 'become law' merely because a statute refers to them." | Binding in Texas, which is in the 5th Circuit. A Texas city's adopted code text is "the law" there. The model IRC itself is not. |
| **Georgia v. Public.Resource.Org, Inc.**, 590 U.S. 255 | U.S. Supreme Court, 27 Apr 2020, 5–4; Roberts, C.J. ([LII](https://www.law.cornell.edu/supremecourt/text/18-1150)) | "We hold that the annotations in Georgia's Official Code are ineligible for copyright protection." The majority confirms the doctrine for **judges and legislators**: "judges—and, we now confirm, legislators—may not be considered the 'authors' of the works they produce in the course of their official duties". It applies "regardless of whether a given material carries the force of law". | It is narrower than "state law text carries no copyright". The sentence "it must follow from our precedents that statutes and regulations cannot be copyrighted" comes from **Justice Thomas's dissent**. The majority's footnote notes that "Justice Thomas concedes that such assertions are plainly foreclosed by our government edicts precedents": a strong signal, not the holding. The building texts lexflow would quote are written by executive bodies (the USBC by Virginia's Board of Housing and Community Development; DC's supplements by DC agencies), and parts follow ICC model wording. Georgia says nothing about state text that reproduces private model language (counsel question C21 in [data-expansion.md](data-expansion.md)). It did **not** decide privately written model codes incorporated into law. |
| **ASTM v. Public.Resource.Org** (ASTM II), 896 F.3d 437 | D.C. Cir., 17 Jul 2018 | It remanded for a fair-use analysis, "leaving for another day the far thornier question" of whether incorporation strips copyright. This phrase is quoted from the opinion as excerpted at [schwimmerlegal.com](https://www.schwimmerlegal.com/2018/07/text-of-astm-v-public-resource-dc-circ-decision-re-fair-use-of-standards-incorporated-into-laws.html); the opinion itself was not opened | It frames the question as fair use, not loss of copyright. |
| **ASTM v. Public.Resource.Org**, 82 F.4th 1262 | D.C. Cir., 12 Sep 2023; Katsas, J. (citation from CourtListener's API; summary at [Stanford Fair Use](https://fairuse.stanford.edu/case/american-society-for-testing-and-materials-v-public-resource-org-inc)) | It affirmed that **non-commercial** posting of standards incorporated by reference into law is fair use, and that an injunction was properly declined. PRO had removed 32 standards found not to be incorporated. | It protects PRO's non-commercial posting. It does not license lexflow, and it does not cover unincorporated text. |
| **Int'l Code Council v. UpCodes**, No. 17 Civ. 6261 (VM), 2020 WL 2750636 | S.D.N.Y., 26 May 2020; Marrero, J. ([opinion PDF, UCI copy](https://sites.uci.edu/ipat/files/2021/04/Int_l-Code-Council_-Inc.-v.-UpCodes_-Inc._-2020-U.S.-Dist.-LEXIS-92324.pdf)) | "Though the Court holds that Defendants' accurate posting of the I-Codes as Adopted is protected as a matter of public domain law, the Court would also reach the same result under the rubric of fair use." The court could not say the same for the "I-Code Redlines", which included unadopted sections. Both motions for summary judgment were denied and the case was sent toward trial. Later status was not verified. | It draws the line lexflow should keep: **accurate text as adopted for a named jurisdiction**, never unadopted model text or redlines. It is a district court opinion and binds no one else. |
| **ASTM v. UpCodes, Inc.**, 172 F.4th 253 | 3d Cir., Apr 2026 (Copyright Office [fair use summary](https://www.copyright.gov/fair-use/summaries/ASTM-v-UpCodes-Inc-172-F-4th-253-3d-Cir-2026.pdf); [EFF note](https://www.eff.org/deeplinks/2026/04/another-court-rules-copyright-cant-stop-people-reading-and-speaking-law)) | It affirmed the denial of a preliminary injunction. UpCodes is likely to succeed on fair use: the first three factors favour it and the fourth is "equivocal". It is a for-profit company with a subscription service, but users "can view currently incorporated standards for free." The Copyright Office records the outcome as "Preliminary finding; Fair use found." The case went one level deeper than a code. The ten ASTM standards at issue include both "mandatory" and "non-mandatory" text, and they were incorporated by reference into the 2018 IBC, which several jurisdictions, including Philadelphia, adopted as law. | This is the most recent appellate view, and it covers a commercial site. It is preliminary, not a final merits ruling. Virginia's 101.2 likewise brings in "Any codes and standards referenced in the IBC" (13VAC5-63-10). lexflow stores none of these referenced standards and links only. |
| **Pro Codes Act of 2026**, S. 4145 (119th Cong.) | Introduced 19 Mar 2026 and referred to Judiciary ([govinfo text](https://www.govinfo.gov/content/pkg/BILLS-119s4145is/html/BILLS-119s4145is.htm)). House companion H.R. 4009 | It would add 17 U.S.C. § 123: an incorporated standard "shall retain such protection, notwithstanding that the standard is incorporated by reference", if the developer "makes all portions of the standard so incorporated publicly accessible online at no monetary cost and in a format that includes a searchable table of contents and index, or equivalent aids to facilitate the location of specific content". | If enacted, free ICC and NFPA views that meet both conditions (free access, and a searchable table of contents and index or equivalent aids) would likely keep copyright in model text, and fair use would remain the only route for copying. Whether the current free views meet the second condition was not checked (counsel question C19). It is pending, not law. |

### 2.3 Public.Resource.Org's postings

* **law.resource.org.** `/pub/us/code/ibr/` holds ICC model codes from 2000 to 2012 (IBC, IRC, IECC, IFC, IMC, IPC and others), IAPMO codes, NYC's 2008 codes and ANSI A117.1, posted 2012–2014. It has no NFPA 70 ([listing](https://law.resource.org/pub/us/code/ibr/)).
* **Internet Archive.** The `publicsafetycode` collection has 30,863 items ([search API](https://archive.org/advancedsearch.php?q=collection%3Apublicsafetycode&rows=0&output=json)). In the 10 states, title searches found:
  * 2008 uploads of Virginia, Maryland, North Carolina, Florida and Texas "building codes", marked with a Creative Commons public-domain licence URL (e.g. [gov.va.building](https://archive.org/details/gov.va.building));
  * 2009 Washington codes;
  * **2025 California Title 24 parts** (for example [gov.ca.bsc.residential.2025](https://archive.org/details/gov.ca.bsc.residential.2025), "Includes January 2026 errata");
  * **the 2025 New York State codes** ([gov.ny.building.2025](https://archive.org/details/gov.ny.building.2025)), uploaded 2 Feb 2026 with no licence field.

  Nothing turned up for Illinois or DC.
* **California.** PRO's docket on law.resource.org records a settlement signed 13 Aug 2024. The BSC then released 2019 and 2022 Title 24 files after public-records requests ([docket listing](https://law.resource.org/pub/us/code/ca/)).
* **What this means for lexflow.** PRO's legal position is PRO's own. ASTM 2023 protects PRO's non-commercial posting. It does not make PRO's copies licensed for others to republish. Archive.org copies may also differ from the official text: the collection pages warn that OCR and re-keying can introduce errors.

### 2.4 Proposed lexflow policy (for counsel to approve or change)

1. **State- and local-authored text may be stored, indexed and quoted.** This covers VAC, DCMR, COMAR, WAC, NYCRR, statutes, local ordinances and public-domain local codes such as Baltimore's. The support is the wider government-edicts doctrine, which Georgia v. PRO confirmed for judges and legislators, together with Veeck in the 5th Circuit, ICC v. UpCodes (persuasive only) and the ASTM fair-use line. Georgia alone does not settle it. Whether agency-written text that reproduces ICC model language (USBC Chapter 1, the DC supplements) may be quoted in full is counsel question C21 in [data-expansion.md](data-expansion.md).
2. **Incorporated model-code text** (IRC, IBC, IFC, IECC, NEC, UPC; also the ICC-published FBC and NC code books) is *not* stored as text. lexflow stores facts: section number, thresholds, conditions, jurisdiction, edition and adopting ordinance. It links to the free official view. It shows no more than a short phrase where a quote is unavoidable.
3. **Never store or show unadopted model text, redlines or commentary.** This is the line ICC v. UpCodes drew.
4. **Do not crawl** ICC, NFPA, IAPMO, UpCodes, Municode, eCode360 or American Legal. ICC's terms forbid robots, and the publishers' robots.txt and blocking rules shut out automated clients.
5. **Bulk use of Public.Resource.Org copies waits for counsel.**
6. **A question for counsel, not a label.** open-us-law is CC BY-NC 4.0, and commercial use needs a Vaquill licence (README). CC BY-NC sets conditions on sharing the licensed material and adaptations of it. Whether a given lexflow output (a decision table, a quoted answer, a place page) is such an adaptation is exactly counsel question C1 in [data-expansion.md](data-expansion.md), so outputs are not labelled CC BY-NC here. Counsel should also say whether model-code facts in a decision table raise any other issue.

Questions for counsel:

* Q1. May lexflow quote a short span of adopted model-code text (for example the IRC deck item as adopted by a Washington city) in an answer? Does Veeck in Texas, or fair use elsewhere, cover that?
* Q2. Are numeric thresholds and conditions taken from a model code uncopyrightable facts in every one of the 10 states?
* Q3. Does the Florida Building Code count as a government edict? It is a state code adopted by rule, but published by ICC and called "copyrighted material" by the state.
* Q4. May lexflow link to, or rely on, Public.Resource.Org's archive.org copies for states without a free official view of an older edition?
* Q5. If the Pro Codes Act passes, what changes for facts and links? Do ICC's free views meet the bill's condition of "a searchable table of contents and index, or equivalent aids"?

---

## 3. The sources

Each card gives:

* **What:** name and publisher;
* **Data / Docs:** the data and documentation URLs;
* **Terms:** licence or terms of use;
* **Access:** format and access;
* **Size;**
* **Cadence:** update cadence and latest vintage;
* **Grain:** granularity and fields;
* **Coverage:** coverage of the 10 states and of local governments;
* **Personal data;**
* **Plugs in:** where it plugs into lexflow, with an example question;
* **Effort;**
* **Prototype download:** the exact download a prototype would need.

Effort: **S** is up to 2 days, **M** is 3–10 days and **L** is more.

### 3.1 open-us-law regulations add-on (already on disk)

* **What:** state administrative codes, from Vaquill AI's open-us-law.
* **Data / Docs:** `/data/raw/open-us-law/us_<st>_regulations.parquet` in `lexflow-app-1`. Manifest at `/data/raw/open-us-law/index.json`, with `canonical` [huggingface.co/datasets/vaquill/open-us-law](https://huggingface.co/datasets/vaquill/open-us-law) and scrapers at [github.com/Vaquill-AI/open-us-law](https://github.com/Vaquill-AI/open-us-law).
* **Terms:** the manifest's `license_data` is `CC-BY-NC-4.0` and `license_scripts` is `Apache-2.0`. The README already notes that commercial use needs a Vaquill licence.
* **Access:** Parquet with the same columns as the statute files, plus `adopting_citations`, `act_status`, `currency_note` and `official_status`.
* **Size:** VA 14.8 MB, DC 17.3 MB, MD 9.4 MB, FL 19.2 MB, IL 40.5 MB, NC 12.3 MB and WA 32.2 MB, all already downloaded. **CA, TX and NY have no regulations file in the manifest.**
* **Cadence:** snapshot 2026-09-30 (`v2026.09.1`).
* **Grain:** one row per section, with `citation_short`, `section_title`, `text`, `source_url`, `last_amended_year` and `act_status`.
* **Coverage:** the building-code chapters found in the files are listed below. NC's State Building Code is not in the NCAC; it is published by OSFM and ICC.

  | State | Chapters | Sections | Words |
  |---|---|---|---|
  | VA | 13VAC5-63 | 81 | 130,567 |
  | DC | 12 DCMR, 2017 edition, `in_force` | 452 | 350,484 |
  | MD | COMAR 09.12.50–.58 | 70 | 21,103 |
  | WA | WAC 51-04 … 51-56 | 706 | 342,378 |
  | FL | 61G20 (adoption and procedure only; the FBC itself is not there) | 31 | 15,726 |
  | IL | 71 Ill. Adm. Code 400 (Accessibility) and 600 (Energy) | 3 (Part 400) + 17 (Part 600) | 67,848 (Part 400) + 3,797 (Part 600) |

* **Personal data:** none.
* **Plugs in:** the search index (§4.1) and the DMN sources (§4.2). Example question: "Do I need a permit for a shed in Virginia?", answered from 13VAC5-63-80 B.2.
* **Effort:** S.
* **Prototype download:** none.

### 3.2 Virginia Uniform Statewide Building Code (DHCD, Board of Housing and Community Development)

* **Data:** the official text is the VAC on [law.lis.virginia.gov](https://law.lis.virginia.gov/admincode/title13/agency5/chapter63/), which is the same text as §3.1. DHCD publishes amendment-only PDFs. DHCD says the linked USBC documents "contain only the specific Virginia amendments to the International Codes" ([archives page](https://www.dhcd.virginia.gov/building-and-fire-regulations-archives)), with the integrated text on ICC.
* **Docs:** [dhcd.virginia.gov/codes](https://www.dhcd.virginia.gov/codes).
* **Terms:** state law. The ICC integrated view is under ICC's terms (§2.1).
* **Current edition:** "This code is also known as the 2021 edition of the USBC due to the use of the 2021 editions of the model codes" (13VAC5-63-10). It took effect on 18 January 2024 (DHCD). Applicants could choose the 2018 or 2021 edition for one year (103.2). DHCD's page names no newer edition.
* **Structure:** Chapter 1 (administration, permits, fees, inspections, appeals: 13VAC5-63-10 to -190) is state text. "Chapters 2 - 35 of the 2021 International Building Code … are adopted and incorporated by reference" (101.2). State amendments follow, by IBC section number. The IRC applies as the "Virginia Residential Code" through VCC 310.6.1 and is amended in 310.8.
* **Coverage:** statewide. All 322 VA governments are bound. Enforcement is local (§ 36-105).
* **Personal data:** none.
* **Plugs in:** the search index, the `permit_required` DMN, and a permit BPMN from §§ 108–119.
  * Example: "My shed is 240 sq ft and my deck is 12 × 16 ft. Which needs a permit in Albemarle County?" The shed is exempt (item 2). The deck needs one. Fees come from the county's schedule.
* **Effort:** S.
* **Prototype download:** none.

### 3.3 DC Construction Codes (12 DCMR; DC Department of Buildings)

* **Data:** §3.1, and [dcregs.dc.gov](https://dcregs.dc.gov/) for the official text.
* **Terms:** District law. The DCMR text itself says the I-Codes are "copyrighted by the ICC and therefore is not republished here."
* **Edition:** the 2017 DC Construction Codes are based on the 2015 I-Codes (67 DCR 5690, 29 May 2020). The DOB targets the 2024 codes by the end of 2027.
* **Grain:** subtitles 12-A (Building) to 12-M. Chapter 1 of 12-A holds permits, fees, inspections and appeals.
* **Coverage:** the District, 1 government.
* **Personal data:** none.
* **Plugs in:** the index and the DMN. Example: "Can I build a 64 sq ft shed in my DC backyard without a permit?" No; the exemption stops at 50 sq ft.
* **Effort:** S.
* **Prototype download:** none.

### 3.4 Maryland Building Performance Standards (Maryland Department of Labor, Building Codes Administration)

* **Data:** COMAR 09.12.51 (§3.1); local code pages for the [counties](https://labor.maryland.gov/labor/build/buildcounties.shtml) and [municipalities](https://labor.maryland.gov/labor/build/buildmuni.shtml).
* **Docs:** [Building Codes Administration](https://labor.maryland.gov/labor/build/buildadmin.shtml).
* **Terms:** state law, and state web pages.
* **Edition:** 2021 IBC, IRC and IECC, effective 29 May 2023. Local enforcement was due by 29 May 2024. Public Safety § 12-503(a)(2) requires each new version to be adopted "within 18 months after it is issued". No 2024 adoption was found.
* **Grain:** the county page lists 24 jurisdictions (23 counties and Baltimore City). Each row gives the responsible office's title, its address, phone and fax, and links to the local codes, an amendments PDF and the local IRC Table R301.2. It shows no edition or date.
* **Coverage:** state rules statewide. Local amendments are linked per county.
* **Personal data:** office titles and office lines only. These would go through the contacts review queue (D7 in [entities-contacts.md](entities-contacts.md)).
* **Plugs in:** entities (office type `building-official` per county) and place pages (links to local amendments). Example: "Who issues building permits in Calvert County?"
* **Effort:** M.
* **Prototype download:** the two HTML index pages (about 100 KB, estimated). The per-county amendment PDFs come later.

### 3.5 California Building Standards Code, Title 24 (California Building Standards Commission)

* **Data:** free views per part from the [BSC Codes page](https://www.dgs.ca.gov/BSC/Codes): ICC for Parts 1, 2, 2.5, 6–12; IAPMO for Parts 4 and 5; NFPA for Part 3, with login. Local amendments: [Local Amendments to Building Standards](https://www.dgs.ca.gov/BSC/Codes/Local-Amendments-to-Building-Standards---Ordinances), with yearly lists such as [2025 Ordinances](https://www.dgs.ca.gov/BSC/Codes/2025-Ordinances), which are "still incomplete" according to the page.
* **Terms:** model text is under the publishers' terms. The ordinance lists are state web pages.
* **Edition:** 2025 Title 24, published 1 July 2025 and effective 1 January 2026 (BSC).
* **Grain:** the ordinance lists give the jurisdiction and ordinance number. A copy of an ordinance is requested by email.
* **Coverage:** all 539 CA governments for state text. Local amendments for those that filed. HSC § 17958.5(c) now freezes most residential amendments.
* **Personal data:** none.
* **Plugs in:** place pages ("filed local amendments for the 2025 code: ordinance no. X") and the DMN (CA R105.2 facts, once read from the free view). Example: "Which building code edition applies in Fresno County?"
* **Effort:** M.
* **Prototype download:** the BSC 2025 and 2022 ordinance list pages, which are HTML (size not measured).

### 3.6 Florida Building Code (Florida Building Commission, DBPR)

* **Data:** the adoption rule is in §3.1. The code is viewable free through the Commission's site ([floridabuilding.org](https://floridabuilding.org/bc/bc_lst.aspx), "Florida Building Code Online", which has an amendment and interpretation search by jurisdiction).
* **Terms:** "copyrighted material" (61G20-1.001(2)). The search pages' terms were not read.
* **Edition:** "The Florida Building Code, 8th Edition (2023), as updated by the Florida Building Commission on … December 9, 2025" (61G20-1.001(1)). The 9th Edition (2026) is scheduled to take effect 31 December 2026. That date appears in search results for the Commission's [August 2026 workplan](https://www.floridabuilding.org/fbc/commission/FBC_0726/Commission/2026_FBC_Workplan_August_2026.pdf) and for a Miami-Dade notice. Neither PDF was opened, so the date is **unverified** first-hand.
* **Grain:** local administrative and technical amendments per jurisdiction, with TAC actions.
* **Coverage:** all 478 FL governments, under one statewide code.
* **Personal data:** none.
* **Plugs in:** the DMN (FBC § 105.2 facts once read), forms (§ 553.79 requires the posted permit application types), and place pages (the permit-utilisation report each local government must post, § 553.80(7)(b)). Example: "Does a prefab shed with a state sticker need a permit in Orange County?" Yes, for erection on site.
* **Effort:** M.
* **Prototype download:** none yet. Local amendment lists come later.

### 3.7 Texas: statutes plus city ordinances

* **Data:** LGC ch. 214 and ch. 233 and HSC ch. 388 are on disk (statutes file). Local text is in city codes, on Municode or American Legal, which are link-only.
* **Regional amendments:** NCTCOG's recommended amendments to the 2021 IRC, approved July 2021 ([PDF](https://nctcog.org/getmedia/feafbc55-3c35-4022-bcab-6b07c95c7f9e/2021-IRC-Amendments-Final.pdf), found by search and not opened). No list of adopting cities was found.
* **Terms:** state law. Publishers' terms apply to the city codes.
* **Edition:** per city. FEMA BCAT counts these residential codes across 1,482 TX jurisdictions:

  | Residential code | Jurisdictions |
  |---|---|
  | No Residential Code | 872 |
  | 2021 IRC | 182 |
  | 2018 IRC | 159 |
  | 2015 IRC | 94 |
  | 2012 IRC | 55 |
  | 2024 IRC | 52 |

* **Coverage:** all 1,477 TX governments; the code edition comes from BCAT.
* **Personal data:** none.
* **Plugs in:** the Ask answer explains that Texas has no state code, the city's adopted edition (BCAT), and the 45-day decision rule (§ 214.904). Example: "My county says it doesn't issue building permits. Is that right?"
* **Effort:** M.
* **Prototype download:** none beyond BCAT (§3.19).

### 3.8 New York State Uniform Code (Department of State, Division of Building Standards and Codes)

* **Data:** the 2025 code books are free on ICC. Part 1203 is on DOS's site ([full text PDF](https://dos.ny.gov/2021-12-10-full-text-rule-part-1203), 260 KB). NYCRR text is otherwise published through the official NYCRR site, which was not checked.
* **Docs:** the [notice of adoption](https://dos.ny.gov/notice-adoption).
* **Terms:** state law. The code books are under ICC's terms.
* **Edition:** the 2025 Uniform Code is effective 31 December 2025, with a transition period. The fossil-fuel provisions (19 NYCRR § 1240.6 and Subpart 1229-2) are "neither effective nor enforceable" under a court order, according to DOS. Part 1203 has been effective since 30 December 2022.
* **Grain:** a statewide minimum. Each local programme chooses its exemptions.
* **Coverage:** 1,581 NY governments, NYC excepted. Local programmes are per town, village or city.
* **Personal data:** none.
* **Plugs in:** the DMN (the opt-in output "only if your town's local law exempts it"), the index (Part 1203 is not in open-us-law; NY has no regulations file), and LOCUS for each local programme. Example: "Do I need a permit for a 120 sq ft shed in the Town of X?" Only if X's local law adopts exemption (i).
* **Effort:** M.
* **Prototype download:** the Part 1203 PDF (260 KB). It needs the user's approval ([data-expansion.md](data-expansion.md) D25). The copy the fetch tool cached during this survey is not an approved input and is not used.

### 3.9 Illinois Municipal Code Directory (Capital Development Board)

* **Data:** [illinois-code-directory.powerappsportals.us](https://illinois-code-directory.powerappsportals.us/), a Power Apps portal with a jurisdiction filter. Records load in the browser, and the captured page showed "no records to display".
* **Docs:** [CDB building codes page](https://cdb.illinois.gov/business/codes/buildingcodesregulations.html).
* **Terms:** a disclaimer says CDB is not responsible for the content and users should confirm with the jurisdiction. No licence is stated.
* **Grain:** by statute, the model code by title and edition, whether local amendments exist, and the date reported (10.18(c)).
* **Coverage:** municipalities and counties that report. Townships are not covered.
* **Personal data:** none expected.
* **Plugs in:** place pages (code edition), as a cross-check on BCAT. BCAT shows 2021 IRC for 1,369 of 1,396 IL rows and 2024 for 27, which looks like the statewide baseline, not local reports. Example: "Which code does Naperville enforce?"
* **Effort:** M. It needs an export from CDB.
* **Prototype download:** ask CDB (CDB.BuildingCodes@illinois.gov, the office mailbox listed on the CDB page) for a CSV export. Do not script the portal.

### 3.10 Washington State Building Code (State Building Code Council)

* **Data:** WAC 51 is in §3.1. The model codes with WA amendments are on ICC.
* **Docs:** [sbcc.wa.gov](https://sbcc.wa.gov/) and the [2024 adoption schedule](https://www.sbcc.wa.gov/sites/default/files/2026-08/2024CodeAdoptionSchedule_Revised_08142026_dc.pdf).
* **Terms:** state law.
* **Edition:** the 2021 codes have been in force since 15 March 2024. The 2024 codes take effect 3 May 2027; final adoption is targeted for 16 Oct 2026 (building, residential, mechanical, fire, plumbing) and 20 Nov 2026 (energy).
* **Grain:** state amendments by section.
* **Coverage:** all 320 WA governments.
* **Personal data:** none.
* **Plugs in:** the index and the DMN (the model R105.2 facts apply statewide by default). Example: "Do I need a permit for a 180 sq ft freestanding deck 2 ft off the ground in Spokane?" Under the model IRC, no, unless Spokane amended it.
* **Effort:** S.
* **Prototype download:** none.

### 3.11 North Carolina State Building Code (Building Code Council; Office of State Fire Marshal)

* **Data:** the statutes (G.S. 143-138, 160D-1110) are on disk. The code is viewable free on ICC.
* **Docs:** the [OSFM release of 7 Apr 2025](https://ncosfm.gov/news/press-releases/2025/04/07/north-carolina-delays-implementation-2024-state-building-code).
* **Terms:** the code books are published through ICC. Their copyright status raises the same question as Florida's (Q3 in §2.4).
* **Edition:** the 2018 NCSBC remains in force. The 2024 code takes effect 12 months after the State Fire Marshal certifies publication and a fully constituted Residential Code Council (S.L. 2025-2). No certification was found as of this survey (**unverified**).
* **Coverage:** all 652 NC governments, under one statewide code.
* **Personal data:** none.
* **Plugs in:** the DMN, with the $40,000 rule quoted. Example: "I'm replacing the boards on my deck. Do I need a permit?" No, under § 160D-1110(c)(1).
* **Effort:** S.
* **Prototype download:** none.

### 3.12 ICC model codes (International Code Council)

* **Data:** [codes.iccsafe.org](https://codes.iccsafe.org/) free Basic view; Premium is paid.
* **Docs:** [Terms of Use](https://www.iccsafe.org/about/terms-of-use/).
* **Terms:** §2.1. No robots, no commercial use and no display on other sites.
* **Access:** a web reader only. Automated requests are refused (403).
* **Coverage:** every I-Code and state edition that the states link to.
* **Personal data:** none.
* **Plugs in:** the **link target only**. Every answer that relies on a model-code fact links to the section here.
* **Effort:** S for links.
* **Prototype download:** none, and none is allowed.

### 3.13 NFPA 70 (National Electrical Code) and other NFPA codes

* **Data:** [nfpa.org/freeaccess](https://www.nfpa.org/freeaccess).
* **Terms:** read-only after sign-in, with no download or printing (archived page, §2.1).
* **Coverage:** the NEC is adopted in VA (2020 NEC per DHCD), TX (Occupations Code § 1305.101: the revised NEC is adopted every three years), CA (Part 3) and others.
* **Plugs in:** link-only, for electrical permit questions.
* **Effort:** S.
* **Prototype download:** none.

### 3.14 Public.Resource.Org (law.resource.org; Internet Archive `publicsafetycode`)

* **Data:** see §2.3.
* **Terms:** older items carry a CC public-domain mark. The 2025 items have no licence field. PRO's legal basis is its own.
* **Size:** large. The CA and NY 2025 sets are multi-volume PDFs (not measured).
* **Coverage:** CA 2025, NY 2025, and older VA, MD, FL, TX, NC and WA editions. Nothing for IL or DC.
* **Personal data:** none.
* **Plugs in:** nothing until counsel answers Q4.
* **Effort:** —.
* **Prototype download:** none.

### 3.15 UpCodes

* **Data:** [up.codes](https://up.codes/).
* **Terms:** the terms page renders in JavaScript and was not read. `robots.txt` disallows every user agent except named search engines.
* **Plugs in:** none. UpCodes' own court wins (§2.2) do not license others to copy its database.
* **Prototype download:** none.

### 3.16 Municipal code publishers (Municode/CivicPlus, American Legal, eCode360/General Code)

* **Terms:** Municode is link-only per [credits-research.md](credits-research.md); `docs/core.md` notes that its terms forbid republishing. American Legal's `robots.txt` blocks named crawlers and sets a crawl delay. eCode360's blocks Bing and others. Neither site's terms were read here.
* **Plugs in:** link targets for local zoning (setbacks) and building-code adoption ordinances found through LOCUS.
* **Prototype download:** none.

### 3.17 Baltimore City Building, Fire, and Related Codes (Department of Legislative Reference; Open Law Library)

* **Data:** [codes.baltimorecity.gov](https://codes.baltimorecity.gov/us/md/cities/baltimore/code/building-codes), in the 2024 edition. Bulk copies are on GitHub: [baltimore-legref/law-xml](https://github.com/baltimore-legref/law-xml), 14,637 KB, last pushed 2026-09-28, and [law-html](https://github.com/baltimore-legref/law-html), 138,416 KB.
* **Terms:** the site says its codes and laws are in the public domain and asks people to bulk-download from GitHub instead of scraping. The GitHub repositories carry no licence file (`license: null`), so counsel should be told.
* **Grain:** section-level XML (format not inspected).
* **Coverage:** Baltimore City, 1 of MD's 180 governments.
* **Personal data:** none expected.
* **Plugs in:** the index (local layer), the DMN (Baltimore rows) and place pages. Example: "Do I need a permit for a deck in Baltimore?" Yes; IRC item 10 is "{Not Adopted}".
* **Effort:** S–M.
* **Prototype download:** `git clone --depth 1 https://github.com/baltimore-legref/law-xml` (about 15 MB). Keep only the building-codes subtree.

### 3.18 LOCUS-v1 (already on disk for VA and CA)

* **Data:** `/data/raw/locus/va.parquet` (106,155 rows, 110 places) and `ca.parquet` (130,966 rows, 55 places). These hold small columns only: header, function and topic.
* **Docs:** [huggingface.co/datasets/LocalLaws/LOCUS-v1](https://huggingface.co/datasets/LocalLaws/LOCUS-v1).
* **Terms:** CC BY-NC 4.0, with no source URLs. It is used to find law, never to cite it (README, `lexflow/sources/locus.py`).
* **Grain:** ordinance headings per place. Counts of matching headings:

  | Topic | VA rows | VA places | CA rows | CA places |
  |---|---|---|---|---|
  | Building code adoption | 118 | 70 | 145 | 41 |
  | Building permits | 213 | 85 | — | — |
  | Accessory structures or sheds | 92 | 45 | 83 | 34 |
  | Setbacks | 477 | 77 | 360 | 45 |
  | Fee schedules | 84 | 52 | 94 | 33 |

  Charlottesville's include "Sec. 5-26. Building Code adopted." and "Sec. 5-56. Building permits."
* **Personal data:** none.
* **Plugs in:** the local layer of an answer, pointing to the official ordinance link. Example: "What setback applies to a shed in Charlottesville?" LOCUS finds the zoning section, and the answer links the city's official code.
* **Effort:** S. The scanner exists (`municipal/locus_scan.py`); add a `building` question pattern.
* **Prototype download:** none for VA and CA. Other states would need the same small-column read of the LOCUS shards (a download, so it needs approval).

### 3.19 FEMA Building Code Adoption Tracking (BCAT)

* **What:** published by FEMA, maintained by a contractor on ArcGIS Online.
* **Data:** feature layer `FEMA_BCAT_Government_Jurisdictions/FeatureServer/0` at `services.arcgis.com/DN2fPfpggEPlLhP6`. Query capability is on, statistics are supported, and `maxRecordCount` is 2000.
* **Docs:** [FEMA BCAT page](https://www.fema.gov/emergency-managers/risk-management/building-science/bcat), [glossary](https://www.fema.gov/emergency-managers/risk-management/building-science/bcat/glossary) and the [portal](https://stantec.maps.arcgis.com/apps/MapSeries/index.html?appid=a053ac48343c4217ab4184bc8759c350).
* **Terms:** **no licence is stated** on the layer or the item. The web map carries a disclaimer (paraphrased): the data are for general information only, may not reflect local updates, must be verified with state and local authorities, are not legal advice, and come with no warranty. This is FEMA-funded work, but its copyright status was not established, so it goes to counsel.
* **Size:** 33,041 rows nationally and 6,722 for the 10 states. Attributes only, with no geometry. Estimated 5–15 MB of JSON for the 10 states.
* **Cadence:** quarterly (FEMA page). Every row has `Data_Currency` = 2026-06-30.
* **Grain:** one row per jurisdiction. The fields include:
  * `Place`, `County`, `State_abbr`;
  * `Building_Code`, `Res_Code`, `Existing_Building_Code`, `WUI_Building_Code`;
  * hazard risk and code status for flood, hurricane, seismic, tornado and wind;
  * NFIP and CRS status;
  * `Adoption_Notes`, with the edition history (for Charlottesville, back to the 1970 NBC);
  * `Local_Code_Weakening_Note`;
  * `State_Building_Code_Link_1..3`;
  * `Pop_2020`, `FEMA_Region`;
  * **`Contact_Email`**, populated in 29,114 rows.

  There is no FIPS or GID column.
* **Coverage:**

  | State | BCAT rows | lexflow governments |
  |---|---|---|
  | VA | 328 | 322 |
  | DC | 1 | 1 |
  | MD | 181 | 180 |
  | TX | 1,482 | 1,477 |
  | CA | 540 | 539 |
  | FL | 477 | 478 |
  | NY | 1,346 | 1,581, with 929 townships |
  | IL | 1,396 | 1,396 counties and municipalities (lexflow also has 1,425 townships) |
  | WA | 320 | 320 |
  | NC | 651 | 652 |

* **Personal data:** `Contact_Email` may hold named officials' addresses. **Never request it.** Use `outFields` without it. The ArcGIS item's `owner` field is a named contractor employee's account. Never copy it; the credit names FEMA.
* **Plugs in:** place pages ("Building code in force: 2021 IBC / 2021 IRC; history …"), the Ask answer to "which edition applies", and a cross-check against state adoption rules.
  * Example: "Which building code edition applies in Charlottesville?" 2021 IRC and 2021 IBC since 18 Jan 2024, under the statewide USBC.
* **Effort:** M (the name crosswalk to `gov_id`, like `locus_scan.gov_keys`).
* **Prototype download:** 4 paged queries:
  * `where=State_abbr IN (...)`;
  * `outFields=Place,County,State_abbr,Building_Code,Res_Code,Existing_Building_Code,Adoption_Notes,Local_Code_Weakening_Note,Data_Currency,State_Building_Code_Link_1,Pop_2020`. `Local_Code_Weakening_Note` (a 1,000-character text field on the layer) may matter for "code in force";
  * `returnGeometry=false`;
  * 2,000 rows each, about 5–15 MB in all. **This needs approval.**

### 3.20 Census Building Permits Survey (BPS), place files

* **What:** U.S. Census Bureau.
* **Data:** [www2.census.gov/econ/bps/Place/](https://www2.census.gov/econ/bps/Place/), with four region folders. The 2025 annual files are `so2025a.txt` (677 KB), `mw2025a.txt` (1.1 MB), `ne2025a.txt` (828 KB) and `we2025a.txt` (315 KB), all published 2026-05-14.
* **Docs:** [BPS](https://www.census.gov/construction/bps/), [methodology](https://www.census.gov/construction/bps/methodology.html) and layout notes under `Documentation/placeasc.pdf`.
* **Terms:** a federal government work (17 U.S.C. § 105).
* **Grain:** one row per permit-issuing place. The columns are:
  * survey date, state code, 6-digit ID, county code, Census place code, FIPS place code, FIPS MCD code, population, CSA, CBSA, footnote, central city, ZIP, region, division, months reported, place name;
  * buildings, units and value for 1, 2, 3–4 and 5+ units, each reported and imputed.
* **Coverage:** about 19,900 places as of January 2023. These cover over 99 % of new private housing. When a city and its county both issue permits, only the county office is counted (methodology).
* **Personal data:** aggregates only. A place with one or two new buildings can reveal one household's build value, so lexflow uses only the permit-issuing flag and counts, and suppresses values for cells under 5.
* **Plugs in:** entities and place pages, for which government issues permits for a place, keyed by FIPS to `governments.place_fips` and `county_fips`. Example: "I live in a small Virginia town. Do I go to the town or the county for a permit?"
* **Effort:** S.
* **Prototype download:** the 4 files listed above, about 2.9 MB.

### 3.21 DOE Building Energy Codes Program, state status

* **Data:** [state portal](https://www.energycodes.gov/state-portal), with the [residential](https://www.energycodes.gov/sites/default/files/2026-09/StateLevelResidentialCodesEnergyUseIndex.xlsx) and [commercial](https://www.energycodes.gov/sites/default/files/2026-09/StateLevelCommercialCodesEnergyUseIndex.xlsx) spreadsheets (September 2026 paths).
* **Terms:** no terms stated on the page; it is a federal site.
* **Grain:** state-level energy-code equivalency.
* **Plugs in:** later, for "which energy code applies".
* **Effort:** S.
* **Prototype download:** none now.

---

## 4. How it plugs into lexflow

### 4.1 Search index: regulations beside statutes

* **Why.** The deck question failed because `lexflow/ask/index.py` indexes `us_<st>_statutes.parquet` only. The answer sits in `us_va_regulations.parquet`, which is already downloaded.
* **What.** A second, contentless FTS5 index per state, `data/index/regs_<state>.sqlite`, with the same tables as the statute index (`sec`, `fts`). It is filled first from the building-code chapters in §3.1 (with `act_status == 'in_force'`) and later from whole regulation files.
* **Where in the code.** This belongs in a new module (for example `lexflow/codes/index.py`), not in `lexflow/ask/*`. Changes to `ask/*` wait for the AskBench freeze to end (D13 in [entities-contacts.md](entities-contacts.md)).
* **The Ask answer.** It searches regulations when the statute search returns "not found", or when the question's concepts include `permit`, `building code`, `shed`, `deck` or `setback`. Quotes keep the regulation's citation and `source_url`. The existing "not found" pointer then becomes a found answer.
* **Model code.** None is indexed (§2.4). Where a regulation incorporates a model code by reference, the answer names the code, its section and edition, and links to the free ICC view.

### 4.2 Process models and DMN: `permit_required`

[docs/questions.md](../questions.md) (A1) already sets the inputs: jurisdiction, project type, size, attached or not, structural or not, historic district, floodplain, and owner-occupied. One decision per state, with every rule quoting state text:

| Rule | jurisdiction | project | detached | stories | area_sqft | occupancy | historic_district | flood_hazard | → permit | → also | Source |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | VA | shed/playhouse | true | 1 | ≤ 256 | not F-1, H | – | false | not required | zoning check | 13VAC5-63-80 B.2 |
| 2 | VA | shed/playhouse | true | 1 | ≤ 256 | not F-1, H | – | true | **may be required** (ask the building official) | zoning, floodplain | 13VAC5-63-80 B, Exception 2 |
| 3 | VA | shed/playhouse | – | – | > 256 | – | – | – | required | zoning check | 13VAC5-63-80 A.1 |
| 4 | VA | deck | – | – | – | – | – | – | required, unless the official deems it minor and ordinary | zoning check | 13VAC5-63-80 A.1, B.13 |
| 5 | DC | shed | true | – | ≤ 50, < 10 ft high, one per lot | accessory to R-3/IRC | false | false | not required | zoning check | 12-A DCMR 105.2 item 8 |
| 5a | DC | shed (garden storage) | – | – | – | – | true (historic district, or a historically designated building or structure) | – | **a building permit application "subject only to historic preservation review" is required**; no permit issues without the Historic Preservation Office's approval | zoning check | 12-A DCMR 105.2.5, item 8; 10-C DCMR 304.1(h) |
| 5b | DC | deck | – | – | – | – | – | – | required | if historic: historic preservation review, since deck construction is an alteration (10-C DCMR 304.1(h)) | 12-A DCMR 105.2 (no deck item); 10-C DCMR 304.1(h) |
| 6 | NY | shed/playhouse | true | 1 | ≤ 144 | 1–2-family/townhouse | – | – | not required **only if the local programme adopts (i)** | – | 19 NYCRR 1203.3(a)(1)(i) |
| 7 | NC | deck: new framing | – | – | – | – | – | – | required | – | G.S. 160D-1110(c)(1) |
| 8 | NC | deck: decking, railings, treads only, cost ≤ $40,000 | – | – | – | – | – | – | not required | – | G.S. 160D-1110(c)(1) |
| 9 | WA, or a local IRC adopter with no amendment | deck | true | – | ≤ 200, ≤ 30 in above grade, not serving the exit door | – | – | – | not required | zoning check | IRC R105.2 item 10 (fact only, link to ICC) |

Notes on the table:

* "zoning check" is a pointer to local zoning (setbacks), which comes from LOCUS headings and the official local code link.
* In VA the owner may always ask for a permit (108.2 preamble). That is a note, not a rule.
* In DC, `historic_district` must be asked whenever the question does not give it. 12-A DCMR 105.2.5 removes the shed exemption for "the land of or the exterior of buildings or other structures located in historic districts, or of historically designated buildings or other structures" (rule 5a), so the DC answer has to say so.
* Rows from model codes (rule 9) carry the IRC section and edition as a citation and no quote. The curated-model checks (`lexflow check-curated`) need a source type `model-code-fact` that has `citation`, `edition` and `url` but no `quote`. This is a schema change to make after the freeze.

**BPMN, Virginia.** VCC Chapter 1 is state-adopted text from start to finish, so it is a complete source for a process model. Whether the parts that follow ICC model wording may be quoted in full is counsel question C21 in [data-expansion.md](data-expansion.md):

1. Decide whether a permit is needed (the DMN above).
2. Apply on the local form, by mail or online (108.3, 108.6), with contractor-licence proof or a statement, and local taxes paid (108.4).
3. Submit construction documents (109).
4. Pay the local fee and the 2 % levy (107).
5. The permit is issued (110).
6. Inspections (113).
7. A certificate of occupancy where required (116).
8. Appeal to the local board of building code appeals (119; Va. Code § 36-105 A).

The same pattern applies to DC's 12-A Chapter 1.

### 4.3 Forms

* Permit application forms are local. Virginia requires "a form supplied by the local building department" (108.6). Florida requires each local agency to post every permit application type online (§ 553.79(1)(b)), so a Florida forms crawl has a legal anchor.
* The registry (`fixtures/forms/forms.json`) would gain local entries, starting with DC DOB's permit application and Charlottesville's. They would be checked the same way as the existing state forms ([forms-plan.md](forms-plan.md) §5). Not done here.

### 4.4 Entities and contacts

* **Agencies:**
  * `lexflow:agency:va:dhcd` (State Building Codes Office);
  * `lexflow:agency:dc:dob`;
  * `lexflow:agency:md:labor-bca`;
  * `lexflow:agency:ca:bsc`;
  * `lexflow:agency:fl:building-commission`;
  * `lexflow:agency:ny:dos-bsc`;
  * `lexflow:agency:il:cdb`;
  * `lexflow:agency:wa:sbcc`;
  * `lexflow:agency:nc:osfm`.
* **Office type:** `lexflow:office-type:<st>:building-official` (the local building department). It resolves to an instance per government, the way D4 resolves generic mentions.
* **Which government enforces:**
  * VA: a town under 3,500 people that has not elected to enforce defaults to its county (§ 36-105 A). BPS's permit-issuing list is the evidence.
  * TX: counties may not require prior approval (§ 233.153(d)).
  * IL: non-building-code jurisdictions have no permit office.
* **Contacts:** office phone, mailbox and portal URLs come from official pages (the Maryland county list, building department pages). They enter through the review queue (D7) and are shown only once checked (D8). BCAT's `Contact_Email` is never used.

### 4.5 Place pages

A "Building permits" block per government:

* the code in force, with its edition and date (BCAT, cross-checked against the state rule);
* who issues permits (BPS and the state rule);
* local amendments (the BSC, Maryland Labor, Florida or Illinois CDB lists, or Baltimore's code);
* LOCUS headings for the adoption ordinance, the permit fee schedule and accessory-structure setbacks, each linked to the official code;
* a link to the free official view of the model code.

### 4.6 Worked answer: "Do I need a building permit for a deck or a shed in Charlottesville, and how do I get one?"

1. **Shed:** no permit if it is a detached, one-story tool or storage shed or playhouse of 256 sq ft or less (13VAC5-63-80 B.2, quoted). The city may still require one in a special flood hazard area (Exception 2). The owner can ask for a permit anyway.
2. **Deck:** a permit is required. The USBC's exemption list has no deck item (13VAC5-63-80 A.1, quoted). The city's deck guidance applies, for example "Typical Deck Details" ([PDF](https://charlottesville.gov/DocumentCenter/View/9152/Typical-Deck-Details-PDF), found by search and not opened).
3. **Zoning still applies** even without a permit: zoning ordinances are not "building regulations" ([Va. Code § 36-97](https://law.lis.virginia.gov/vacode/36-97/)), so the USBC does not supersede them (§ 36-98). LOCUS points to the city's zoning sections, with a link to the official code (link-only).
4. **How:**
   * apply to the city's building official (Neighborhood Development Services), by mail or online (108.3);
   * give a contractor licence or a written statement (108.4);
   * pay the city's fee schedule (107.1.1) plus the 2 % state levy (107.2);
   * book the inspections.
5. **Code in force:** the 2021 Virginia Residential Code (2021 IRC with state amendments), since 18 January 2024. Sources: 13VAC5-63-10 for the edition; DHCD's [codes page](https://www.dhcd.virginia.gov/codes) for the date ("2021 Virginia Codes effective Jan. 18, 2024"), which the regulation text does not state; BCAT, data as of 2026-06-30.
6. **Read the full code:** a link to the free ICC view of the Virginia codes. No IRC text is reproduced.

---

## 5. Answering the three test questions

| Question | Sources that answer it | Ready? |
|---|---|---|
| Do I need a building permit for a deck or a shed? | VA, DC, NY and NC state text (on disk, or after D25 for NY); model IRC facts for WA; local codes for MD, CA, TX, IL and FL | VA and DC now (no download; DC with its historic-district rule, 105.2.5). NY needs Part 1203 downloaded with approval (D25) and added to the index. NC from the statute file, decks only. Others need the local layer |
| What setback applies to a shed in my city? | Local zoning ordinances, found by LOCUS (VA: 477 setback headings in 77 places; CA: 360 in 45) and linked to the official code. DC's Zoning Regulations (11 DCMR: subtitles 11-A to 11-K, 11-U and 11-W to 11-Z) are in the DC regulations file. Baltimore's code is public domain | DC and Baltimore can be quoted. Everywhere else is a link, since publisher terms block storing the text |
| Which building code edition applies in my county? | FEMA BCAT (every jurisdiction), the state adoption rules (VA 13VAC5-63-10, MD COMAR 09.12.51.04, WA WAC 51-51-003, FL 61G20-1.001), Illinois CDB, and the CA BSC lists | Yes, once BCAT is approved and crosswalked |

---

## 6. Prototype: what to build first, and the exact downloads

| Step | What | Download needed | Size | Approval |
|---|---|---|---|---|
| P1 | `regs_<st>.sqlite` FTS index over the building-code chapters for VA, DC, MD, WA, FL and IL (§4.1) | none (on disk) | – | no |
| P2 | Curated `permit_required` for VA and DC from state text, plus the VA permit BPMN (§4.2) | none | – | no |
| P3 | NY Part 1203 and NC § 160D-1110 rows | **Superseded** by [data-expansion.md](data-expansion.md) D25. NY needs the Part 1203 PDF; a copy cached by a research tool is not an approved input. The NC statute is on disk | 260 KB (NY) | **yes** for NY (D25); none for NC |
| P4 | BCAT attributes for the 10 states, without `Contact_Email`, crosswalked to `gov_id` | ArcGIS query (§3.19) | ~5–15 MB, estimated | **yes** |
| P5 | BPS 2025 place files, for the permit-issuing flag and counts | `www2.census.gov/econ/bps/Place/{South,Midwest,Northeast,West} Region/??2025a.txt` | ~2.9 MB | **yes** |
| P6 | Baltimore building codes, the local layer | `git clone --depth 1` of `baltimore-legref/law-xml` | ~15 MB | **yes** |
| P7 | Local amendment index pages for CA (BSC 2022 and 2025 lists) and MD (Labor county and municipality pages) | HTML pages | < 1 MB, estimated | **yes** (small) |
| P8 | Illinois CDB directory | ask CDB for an export | unknown | **yes**, by email from the user |

---

## 7. Privacy

* Building-code sources are almost free of personal data, with three exceptions:
  1. BCAT's `Contact_Email`, which is never requested;
  2. county office pages, which carry office titles and lines and go through the review queue;
  3. permit records on city open-data portals, which name owners, contractors and addresses.
* Permit records are not part of this plan. If they are used later for processing times or permit volumes, they follow the payroll rule ([payroll-plan.md](payroll-plan.md) §6): aggregate on the publisher's server, keep counts and medians by permit type and month, suppress cells under 5, and never store a name or address.
* BPS place values for very small places are suppressed the same way (§3.20).

---

## 8. Open questions and what was not verified

1. **IRC R105.2 from ICC itself.** The thresholds in §1.2 come from Washington local-government reproductions, because ICC refuses automated requests. A person should read R105.2 in the free view once and confirm items 1 and 10 for the 2021 and 2024 IRC.
2. **California R105.2.** A 120 sq ft accessory-structure limit in the CRC was seen only in a search summary of Alpine County's 2022 CRC sheet. The PDF is a scan and could not be read. Confirm it in the free CARC2025 view.
3. **Florida § 105.2.** The FBC's own exemption list was not read. Florida's 9th Edition effective date (31 Dec 2026) was seen in search results for Commission workplans, not opened first-hand.
4. **North Carolina.** Whether the 2024 code's effective date has been certified. Whether the 2018 NC Residential Code exempts small accessory buildings. How § 160D-1110(c) applies to a new detached shed.
5. **IBC § 105.2 item 1.** The shed size limit that Baltimore keeps "As in IBC" was not checked.
6. **New York.** Part 1203 has a 2021 DOS notice only. Confirm that no later amendment changed § 1203.3. NYCRR hosting terms were not checked.
7. **ICC v. UpCodes** after 2020 (trial, settlement, or the related Lanham Act case) was not verified.
8. **The ASTM II quote** ("leaving for another day the far thornier question") was read from a blog excerpt, not from the opinion.
9. **BCAT licence and maintenance.** Ask FEMA whether the layer is public domain, and whether it may be stored and republished with attribution.
10. **Illinois CDB directory.** Ask whether an export exists and on what terms.
11. **Terms not read:** UpCodes, IAPMO epubs, Municode's current terms, eCode360, American Legal, and Florida Building Code Online.
12. **National Zoning Atlas** ([zoningatlas.org](https://www.zoningatlas.org/)) might help with setbacks. Its coverage and terms were not read; only the landing page was opened.
13. **Counsel questions Q1–Q5** (§2.4).
