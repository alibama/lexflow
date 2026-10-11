# Entity sources: Govdirectory and Wikidata

This note asks whether Govdirectory and Wikidata can supply government agencies and their official contact
channels for the jurisdictions in the lexflow corpus. It also asks how far their provenance and freshness can
be trusted.

* Surveyed 2026-10-10. All numbers come from pages opened and SPARQL queries run on that date.
* Every request was a read-only GET. The User-Agent was `lexflow-research/0.1 (https://github.com/alibama/lexflow)`,
  each request had a 15 s timeout, and requests were spaced at least 1 s apart per host. Queries went to
  `query.wikidata.org` one at a time. Nothing was edited on Wikidata, Govdirectory or GitHub.
* The note records organisations and official office channels only. It reproduces no email address or phone
  number. Wherever this note says an item "has an email" or "has a phone", the value was seen but not copied.
* For how lexflow stores governments, contacts and QIDs today, see [entities-codebase.md](entities-codebase.md).

## 1. The short version

| Question | Answer |
|---|---|
| What Govdirectory is | A static website. It is rebuilt from Wikidata with SPARQL and publishes official websites, contact pages, referenced phone numbers and social-media accounts of public bodies. It holds no data of its own: everything is a Wikidata statement, licensed CC0. |
| Who runs it | A volunteer open-source project with two maintainers, who are listed in the repository README. Its GitHub organisation is `govdirectory`, and its `publiccode.yml` names "Govdirectory" as owner. It started in Wikimedia Deutschland's Unlock accelerator in 2021. Wikimedia Sverige hosts its analytics, and NLnet funds its Fediverse work. |
| Scale | 46 countries, 21,105 organisations and 46,431 contact points (statistics page, built 2026-09-25). |
| US coverage | Three pages. **United States**: 374 federal entries, mostly embassies and consulates. **New York**: 97 state agencies and 62 counties. **North Carolina**: 400 state agencies (39 of them licensing boards), 100 counties, 100 county election boards, the legislature, the cabinet, the Council of State and 2 courts. There is nothing for VA, DC, MD, TX, CA, FL, IL or WA. |
| API or export | There is no API. Each listing has a "Download (as TSV)" button that builds the file in the browser. Each organisation page carries schema.org `GovernmentOrganization` JSON-LD, and there is a sitemap. The real source is the SPARQL queries in the repository, which anyone can run against the Wikidata Query Service (WDQS). |
| Corrections | You cannot edit on Govdirectory. Each page links to the Wikidata item and to a pre-filled error report on `Wikidata:WikiProject Govdirectory/Error_reports`. A fix made on Wikidata appears after the next build. Builds are deployed by hand, about monthly. |
| Wikidata coverage, our 10 jurisdictions | 978 state-level government bodies were found. **91 % have an official website, 6 % an email, 5 % a phone, 9 % a contact-page URL and 38 % a social account.** North Carolina alone has 410 of them, thanks to the Govdirectory curation (398 carry its focus-list marker). Without NC there are 568 bodies: 88 % have a website, 10 % an email and 6 % a phone. |
| Licensing boards | 58 in total, 41 of them in North Carolina. Virginia has only the Board of Medicine, and Washington has none. **The Virginia Department of Professional and Occupational Regulation has no Wikidata item.** |
| Courts and clerks | 55 state courts. Every state's supreme and appellate courts are there, but trial courts are mostly missing. 39 of the 55 courts have a website, none has an email, and 1 has a phone. Clerks are almost absent: 3 county clerk offices (San Diego, Santa Clara, Duval), none in VA, DC, MD, TX, NY, WA or NC, and in Illinois only an untyped Cook County clerk item. |
| Provenance | Email and phone statements are well sourced: 98 % and 97 % have references, and 82 % and 53 % have a retrieved date. Official-website statements are not: 59 % have any reference, 18 % carry an "imported from Wikimedia project" reference, and 4 % have a retrieved date. Start and end qualifiers are rare on websites (17 start, 9 end out of 1,076 statements). |
| Freshness | In a random sample of 48 official websites, 42 answered 2xx, 5 had moved to another host, and 6 failed or were refused. 32 % of website values are still `http://`. One Florida Department of State URL returns 404. The `schema:dateModified` of an item is recent (median 2025-11), but it records any edit, not a check of the contact details. |

**Verdict.** Wikidata works as an **identifier and crosswalk** for state agencies, and as a website seed: QID,
English label, parent body, official website. It is not a usable source of emails or phones outside a few
curated pockets: NY, NC, Maryland and some DC agencies. It does not supply licensing
boards outside NC, county courts or clerks. Govdirectory adds no data beyond Wikidata. Its value to lexflow
is the curated class lists, the query patterns and the rule that a phone is shown only when it has a
reference, and it covers only NY and NC among the corpus states.

## 2. Govdirectory

### 2.1 What it is and who runs it

* [govdirectory.org](https://www.govdirectory.org/) describes itself as a crowdsourced, fact-checked directory of
  official government online accounts and services. Its [About page](https://www.govdirectory.org/about/) sets
  out the mission: the online presence of every public organisation should be findable, queryable and
  trustworthy. Data quality comes from the Wikidata community's curation.
* The [README](https://github.com/govdirectory/website) lists two maintainers. They have the final say "for now",
  and a shared governance model is planned once the community grows. There is a weekly open "Collab Hour" on
  Jitsi. [`publiccode.yml`](https://github.com/govdirectory/website/blob/main/publiccode.yml) gives
  `mainCopyrightOwner: Govdirectory` and `developmentStatus: stable`. No incorporated body is named.
* Support, as listed on the About page: Wikimedia Deutschland's Unlock accelerator (2021); Matomo analytics
  hosted by Wikimedia Sverige, whose dashboard is public; and an NLnet grant for Fediverse display.
* Recognition, as listed on the About page: Digital Public Good (2022); finalist for the SDG Game Changers Award
  (2023); WSIS Prizes champion (2024); FSF Award for Projects of Social Benefit (announced 2025, for 2024).
* Licence: the site says all data is CC0 1.0. The repository is CC0 too.
* The repository's contribution guide says that contributions which can be recognised as AI-generated get the
  contributor blocked. This matters if anyone ever proposes lexflow-generated changes upstream.

### 2.2 How a listing is built

From [DEPLOY.md](https://github.com/govdirectory/website/blob/main/DEPLOY.md),
[`snowman.yaml`](https://github.com/govdirectory/website/blob/main/snowman.yaml) and the `queries/` folder:

1. **One "generator" SPARQL query per country, or per sub-national part.** It returns `?qid ?orgLabel
   ?orgDescription ?type ?typeLabel ?country`. Its first line is an `# expected_result_count`, which CI checks.
   See [ADD_A_COUNTRY.md](https://github.com/govdirectory/website/blob/main/ADD_A_COUNTRY.md).
2. Members are selected by **`wdt:P31` (instance of) against an explicit `VALUES` list of classes**. There is
   no `P279*` subclass walk. Most generators also apply `MINUS { ?org wdt:P576 [] }` (dissolved) and
   `MINUS { ?org wdt:P1366 [] }` (replaced by). The US generator adds `P3999` (date of official closure) and
   drops positions (`Q4164871`).
3. **Static build.** [Snowman](https://github.com/glaciers-in-archives/snowman) runs the queries against
   `https://query.wikidata.org/sparql`, caches the results and renders HTML. The `gh-pages` branch is pushed by
   hand. The recent deploy commits are 2026-04-06, 07-29, 08-28, 08-29 and 09-25, and pages carry
   "Data last updated 2026-09-25". The cache can be cleared for a single country.
4. **Per-organisation queries.**
   * [`organization-optional.rq`](https://github.com/govdirectory/website/blob/main/queries/organization-optional.rq)
     reads P856 official website, P968 email, P11266 contact page URL, P10214 FOI request URL, P9732 citizens'
     initiative URL and P92 main regulatory text (shown only if the text item has P953 and P1476). It also
     reads P749 parent organisation, the "led by" person (P2388 or P1313 office holder, or
     P488/P169/P1037/P3975), the English Wikipedia sitelink, and **P1329 phone, which is kept only if the
     statement has a reference** (`prov:wasDerivedFrom`).
   * The query uses truthy `wdt:` values and `SAMPLE`. It drops deprecated values, but **it does not drop
     values that have an end-time qualifier**.
   * [`account-data.rq`](https://github.com/govdirectory/website/blob/main/queries/account-data.rq) builds the
     social-media list. It does not hard-code the platforms. It takes every property that is an instance of
     `Q105388954` ("Wikidata property to identify online accounts") and has a formatter URL (P1630) and a
     platform (P9073, applicable "stated in" value). It skips discontinued-website properties (`Q60457486`)
     and works around P11245 (YouTube handle). In this survey's query, 104 properties qualified. **It drops
     statements with an end time (`pq:P582`) and statements with deprecated rank.** P4033 (Mastodon), P12622
     (PeerTube) and P11892 (Threads) are flagged as Fediverse.
   * The account properties that the contributing guide names as the common ones are P2002 X, P2013 Facebook,
     P2003 Instagram, P2397 YouTube channel ID and P4264 LinkedIn.
5. **Country configuration.** [`countries.rq`](https://github.com/govdirectory/website/blob/main/queries/countries.rq)
   holds the slug, the coverage description and the sub-parts. For the US the parts are `New York|new-york` and
   `North Carolina|north-carolina`.

The US generators, quoted by class, with the counts their comments give:

| Page | Classes (`wdt:P31`) | Count |
|---|---|---|
| [united-states.rq](https://github.com/govdirectory/website/blob/main/queries/generators/united-states.rq) | Q910252 federal executive department (15); Q115456878 legislative branch agency (24); Q96397182 OSDBU (36); parts of the Executive Office of the President (6, through current P749 to Q1355327); embassies, consulates, consulates general, missions and de facto embassy operated by the US (P137 = Q30, 264); Q106583901 interstate commissions with P101 in low-level radioactive waste, energy, oil or **occupational licensing** (29) | 374 |
| [new-york.rq](https://github.com/govdirectory/website/blob/main/queries/generators/united-states/new-york.rq) | Q134016126 state agency of New York (97); Q13414757 county of New York (62) | 159 |
| [north-carolina.rq](https://github.com/govdirectory/website/blob/main/queries/generators/united-states/north-carolina.rq) | Q133309046 state agency of North Carolina (400); Q13414758 county of NC (100); Q935741 election commission with P1001 in an NC county (100); General Assembly and its houses; Council of State; cabinet; supreme and appellate courts that are part of Q5178756 | 607 |

The live pages matched these counts. [/united-states/](https://www.govdirectory.org/united-states/) has 374
rows: 168 embassies, 72 consulates general, 36 OSDBUs, 29 interstate commissions, 24 legislative agencies, 15
departments, 12 missions, 11 consulates, 6 EOP parts and 1 de facto embassy.
[/united-states/north-carolina/](https://www.govdirectory.org/united-states/north-carolina/) has 607 rows, and
[/united-states/new-york/](https://www.govdirectory.org/united-states/new-york/) has 159. The only entry on the
US page that belongs to one of our states is the Texas Low-Level Radioactive Waste Disposal Compact Commission.

### 2.3 Machine access: API, export, SPARQL

* **No API.** The website is static HTML on GitHub Pages.
* **TSV.** Each country page has a "Download (as TSV)" button. Page JavaScript builds the file from the rendered
  table, with columns Name, Govdirectory URL, Type and Website. Each organisation page has its own TSV of
  platform and account.
* **JSON-LD.** Each organisation page embeds schema.org `GovernmentOrganization` with `name`, `description`,
  `additionalType` (the class QID), `url` and `sameAs`. `sameAs` holds the account URLs and the Wikidata
  entity. Example: [DOJ page](https://www.govdirectory.org/united-states/Q1553390/).
* **Sitemap.** [robots.txt](https://www.govdirectory.org/robots.txt) points to a 1.9 MB `sitemap.xml`.
* **URL pattern.** `https://www.govdirectory.org/<country-slug>/<QID>/`. For NY and NC, the slug is
  `united-states/new-york` or `united-states/north-carolina`. This is what lexflow's unused `Actor.govdirectory`
  field could hold, but only for bodies that are actually published.
* **SPARQL source.** The generator and per-organisation queries in the repository are the canonical way to get
  the data. Running them against WDQS returns fresher data than the website.
* **Caches.** [govdirectory/website-cache](https://github.com/govdirectory/website-cache) is a Snowman cache of the
  query results, last updated 2026-01-02. It exists so that developers do not have to re-run thousands of
  queries. It is a snapshot, not a feed.
* **Related tools.** [health-check-service](https://github.com/govdirectory/health-check-service) sends HEAD
  requests to the P856, P9732 and account URLs of an item and reports errors. It was last pushed in 2021.
  [QuickStatements-upload-support](https://github.com/govdirectory/QuickStatements-upload-support) is a
  spreadsheet template for the WikiProject's bulk-upload guides.
* **Marker property.** The WikiProject's [data model](https://www.wikidata.org/wiki/Wikidata:WikiProject_Govdirectory/Data_model)
  asks editors to add P5008 "on focus list of Wikimedia project" = Q108109790 (WikiProject Govdirectory) to
  published agencies. Of our 978 bodies, 499 carry a P5008 value: 398 in NC and 96 in NY.

### 2.4 Coverage of US states, boards, counties and cities

* Only **New York and North Carolina** have sub-national pages. The [WikiProject US page](https://www.wikidata.org/wiki/Wikidata:WikiProject_Govdirectory/United_States_of_America)
  links a subpage for every state. When this survey fetched them, only `/New_York` and `/North_Carolina`
  existed; Virginia, Florida, California, District of Columbia, Texas, Maryland, Illinois and Washington all
  returned 404.
* **Licensing boards.** In North Carolina, the boards are state agencies on the published list (39 have
  licensing-type names). Fifteen interstate occupational-licensing compact commissions appear on the US page. No
  other corpus state has its boards modelled.
* **Counties and cities.** NY and NC counties are published, and so are NC county election boards. No city
  offices are published anywhere in the US.
* The WikiProject's ["star" scale](https://www.wikidata.org/wiki/Wikidata:WikiProject_Govdirectory) sets the bar
  for publication at three stars. That means a complete and accurate list of current agencies (consistent P31,
  P17, P571 and P576), queryable by level or type, with the structure documented on the country page.
* NC has an Integraality coverage table. Its [NC coverage table](https://www.wikidata.org/wiki/Wikidata:WikiProject_Govdirectory/United_States_of_America/North_Carolina/Coverage_of_state_level_agencies)
  reports, for the 400 state agencies: P856 97.5 %, P968 1.0 %, P1329 4.25 %, Facebook 9 %, X 8.5 %. This
  survey's own count for NC was website 96 %, email 1 % and phone 4 %, which agrees.

### 2.5 How corrections flow

* Govdirectory has no edit function. Every organisation page links to the Wikidata item and to a button that
  opens a new section on [Error reports](https://www.wikidata.org/wiki/Wikidata:WikiProject_Govdirectory/Error_reports),
  with a template and the QID pre-filled. Problems with the website itself go to GitHub issues.
* The Error reports page invites the reporter to fix the data on Wikidata themselves. It holds only about seven
  threads, the first from 2022.
* A fix reaches the site only after a maintainer clears the cache and redeploys. The one exception is the
  organisation page's "Recently updated" panel, which runs `account-data.rq` live against WDQS in the visitor's
  browser.
* A new country or sub-national part is added by pull request: a new generator query, a `countries.rq` line and
  a view. A new agency type is added to a generator's `VALUES` list. Each type item should carry P6104
  (maintained by WikiProject) = Q108109790.

## 3. Wikidata coverage for the corpus jurisdictions

### 3.1 Method

Wikidata has no consistently used class for US state agencies. The generic class is Q327333 (government agency), which has
6,387 subclasses. "State agency of the United States" (Q20857085) has per-state subclasses, but they are sparsely
filled: NC 409, NY 98, CA 69, MD 27, TX 16, FL 13, VA 10, IL 6, WA 4, and **no class at all for DC**. The level
of government is not modelled consistently. This survey therefore took the union of four sets for each
jurisdiction:

* (a) `?i wdt:P131|wdt:P1001 <state>` and `?i wdt:P31/wdt:P279* wd:Q327333`;
* (b) instances of a per-state subclass of Q20857085 that are located in, or apply to, the state;
* (c) all instances of the per-state class;
* (d) government agencies whose P131 is the state capital, minus obviously municipal ones such as city police
  or schools. This set was added because, for example, the Florida Department of State is located only in
  Tallahassee and has no P1001.

The union was then cleaned in four steps:

1. Dissolved and replaced items were dropped (P576, P1366).
2. **Items whose every P31 is a local-government type were dropped.** Wikidata classes school districts,
   cities, villages, park districts and similar as government agencies. Texas alone had 1,015 of these, almost
   all school districts.
3. Federal and foreign bodies were dropped: embassies, consulates, federal agencies, OSDBUs and legislative
   branch agencies.
4. Obviously local bodies whose P131 points at the state were dropped by label: county and city police,
   sheriffs, county schools and similar. For DC, step 3 removed 73 federal offices that are located in
   Washington. Only 7 bodies link to "government of the District of Columbia" (Q16152667) through P749 or
   P361, so the DC row is a hand-checked list of DC government bodies.

Contact properties were counted from `p:`/`ps:` statements. Deprecated statements and statements with an end
time were excluded. "Social" means any current P2002, P2013, P2003, P2397, P4264 or P4033 statement.

Courts were found as instances of a subclass of Q41487 (court), through P131 or P1001 up to two hops from the
state (court → city or county → state). Federal courts were then removed. A wider query over all US courts
found only 326 court items with P17 = United States, out of 12,225 court items worldwide.

Treat every count as a **lower bound**. Bodies that have no P131, P1001 or per-state class can still be
missing.

### 3.2 State-level government bodies

| Jurisdiction | Raw union | Kept | Official website | Email | Phone | Contact page | Social | Licensing boards (n: web/email/phone) | State courts (n: web/email/phone) |
|---|---|---|---|---|---|---|---|---|---|
| VA | 118 | 42 | 37 (88 %) | 2 (5 %) | 3 (7 %) | 0 | 19 (45 %) | 1: 1/1/1 | 6: 5/0/0 |
| DC | 160 | 26 | 24 (92 %) | 4 (15 %) | 4 (15 %) | 0 | 11 (42 %) | 2: 2/0/0 | 2: 2/0/0 |
| MD | 70 | 50 | 42 (84 %) | 4 (8 %) | 10 (20 %) | 1 (2 %) | 30 (60 %) | 1: 1/0/0 | 3: 1/0/0 |
| TX | 1,090 | 54 | 46 (85 %) | 0 | 1 (2 %) | 1 (2 %) | 27 (50 %) | 4: 4/0/0 | 3: 3/0/0 |
| CA | 675 | 143 | 124 (87 %) | 3 (2 %) | 0 | 2 (1 %) | 76 (53 %) | 4: 4/1/0 | 15: 12/0/0 |
| FL | 100 | 45 | 39 (87 %) | 3 (7 %) | 4 (9 %) | 3 (7 %) | 27 (60 %) | 1: 1/0/0 | 8: 5/0/1 |
| NY | 395 | 118 | 111 (94 %) | 38 (32 %) | 7 (6 %) | 77 (65 %) | 83 (70 %) | 3: 0/0/0 | 9: 6/0/0 |
| IL | 345 | 44 | 38 (86 %) | 0 | 2 (5 %) | 1 (2 %) | 26 (59 %) | 1: 1/0/0 | 4: 2/0/0 |
| WA | 104 | 46 | 39 (85 %) | 1 (2 %) | 2 (4 %) | 0 | 26 (57 %) | 0 | 3: 2/0/0 |
| NC | 487 | 410 | 393 (96 %) | 4 (1 %) | 17 (4 %) | 7 (2 %) | 42 (10 %) | 41: 41/0/0 | 2: 1/0/0 |
| **All** | | **978** | **893 (91 %)** | **59 (6 %)** | **50 (5 %)** | **92 (9 %)** | **367 (38 %)** | **58** | **55: 39/0/1** |

How to read the table:

* **Websites are the one dependable field.** Even so, the "kept" lists are thin outside NY, NC and CA. Virginia
  has 42 bodies, among them about 20 departments (Health, Taxation, Transportation, Elections, Education, DEQ,
  DMV, Social Services and others), the State Corporation Commission, the Library of Virginia and the two
  legislative chambers.
* **Emails and phones** cluster where someone curated them. In NY, 38 of the 42 items with an email are in the
  "state agency of New York" class that Govdirectory publishes, and so are all of the items with a contact-page URL. In
  MD, the 10 phones are referenced to the *Maryland Manual*, official web pages or, in five cases, Google Maps.
  Four DC agencies have both an email and a phone.
* **Licensing boards** were matched by P31 Q114634763 (state licensing board, 26 instances nation-wide) or
  Q125771287 (licensing board), by P101 = Q7075804 (occupational licensing), or by a name pattern. Outside NC
  there are: VA, the Board of Medicine; MD, the Board of Cosmetologists; TX, the Medical Board, the Board of
  Nursing, the Board of Dental Examiners and TDLR; CA, the boards of Accountancy, Vocational Nursing, Medicine
  and Court Reporters; FL, DBPR; NY, three State Boards; IL, IDFPR; DC, DLCP and BPLA.
* **Courts.** Every jurisdiction has its supreme court and intermediate appellate court items. A few
  jurisdictions have some trial courts: VA has 4 circuit courts, CA 9 county superior courts, FL 6 circuit
  items, and IL and WA have the Cook County and King County courts. Websites exist on about 70 % of them. Court
  items carry no emails.
* **Clerks.** The only class in use is "county clerk's office" (Q139489412). It has 8 instances in the whole of
  Wikidata, 4 of them in Alabama. In our states there are 3: San Diego County Assessor/Recorder/County Clerk,
  Santa Clara County Clerk-Recorder and Duval County Clerk. "Clerk of the Circuit Court of Cook County" exists,
  but it has no P31. Wikidata cannot be a clerk source for this corpus.

### 3.3 Named examples (checked item by item through `Special:EntityData`)

| Body | Wikidata | What is there |
|---|---|---|
| Florida Department of State | [Q11969252](https://www.wikidata.org/wiki/Q11969252) | P31 government agency only, with no per-state class. P131 is Tallahassee and there is no P1001, so state-level queries miss it. The only P856 is `http://www.dos.state.fl.us/`, which **returned 404**. Its only reference is "imported from Wikimedia project" (a Norwegian Wikipedia). There is no email or phone. |
| Florida Division of Corporations (Sunbiz) | [Q107179384](https://www.wikidata.org/wiki/Q107179384) | **The best-modelled example found.** P31 registration authority, government agency, database and state agency of Florida; P1001 Florida; P749 the Department of State. It has three P856 values with **start and end qualifiers**: sunbiz.org (1999–2016), dos.myflorida.com/sunbiz (2016–2023) and dos.fl.gov/sunbiz (2023–). Its email and phone are each referenced to `dos.fl.gov/contact-us/` with **retrieved 2024-04-11**. Its P101 values (trademarks, fictitious names) are referenced to dos.fl.gov pages retrieved 2025-03-27. Note: all three websites have normal rank, so a truthy `wdt:P856` query returns the two retired ones too. |
| California Department of Justice | [Q5020429](https://www.wikidata.org/wiki/Q5020429) | P31 justice ministry and state agency of California; P1001 California; P749 State of California. P856 `http://oag.ca.gov/` redirects to https and works. It is referenced only "imported from English Wikipedia". There is no email, phone or contact page. |
| Virginia Department of Professional and Occupational Regulation | **none** | `wbsearchentities` and full-text search found no item. Searches for "DPOR Virginia" and "Virginia Board for Contractors" returned 0 hits, and no DPOR board appeared in the Virginia state-level sets. The nearest Virginia business-regulation item is the State Corporation Commission, [Q7603136](https://www.wikidata.org/wiki/Q7603136): preferred P856 scc.virginia.gov, plus a business-search URL referenced to the GLEIF Registration Authorities List. It has no email or phone. |
| DC Office of the Secretary | **none** | There is no organisation item. Only the position *Secretary of the District of Columbia*, [Q7444418](https://www.wikidata.org/wiki/Q7444418), exists (P31 position, P1001 DC), and it has no website. DC's corporate registry is modelled as "Corporations Division", [Q138637634](https://www.wikidata.org/wiki/Q138637634), under DLCP. Its P856 `dlcp.dc.gov/node/1614386` redirects to `/page/corporations-0` and has no reference. |

The other state Secretary-of-State and corporations items found: Maryland Office of the Secretary of State
(Q79946611), Office of the Secretary of State of California (Q141105514), New York Department of State
(Q17110658) and its Division of Corporations (Q125449570), Office of the Secretary of State of Washington
(Q136376328) and North Carolina Department of the Secretary of State (Q136481241). Most have a website. NY
Corporations has an email with a retrieved date, and the Washington item has no website. No Texas or Illinois
Secretary of State item turned up through the state-level sets.

### 3.4 Modelling gaps that matter for lexflow

1. **Level of government is not explicit.** State agencies may have P131 = state, P1001 = state, P131 = the
   capital city or nothing at all. Local bodies such as police departments and county schools sometimes have
   P131 = state. A dependable list therefore needs either a per-state class, as in NC and NY, or a curated
   seed.
2. **Ontology noise.** School districts, cities and park districts are subclasses of government agency. Any
   `P279*` walk from Q327333 pulls them in.
3. **DC is the hardest case.** Federal offices in Washington and the DC government share a location, and the DC
   government has no per-state class.
4. **Positions versus offices.** Clerks, secretaries and similar offices are often modelled as *positions*
   (Q4164871) held by people, not as organisations with contact data.

## 4. Provenance and freshness

### 4.1 What Wikidata can record

* **References on each statement** (`prov:wasDerivedFrom`):
  * P854 reference URL;
  * P813 retrieved, the only per-statement freshness date;
  * P248 stated in, for example *Maryland Manual*, USA.gov, GRID, Common Core of Data, Google Knowledge Graph or
    the GLEIF RA list;
  * P143 imported from Wikimedia project and P4656 Wikimedia import URL. These mean "copied from a Wikipedia".
    They are not an independent source.
* **Qualifiers:**
  * P580 start time and P582 end time. The guidance on P856 says to keep an old URL and mark it, not delete it.
  * P407 language of work.
  * P585 point in time.
* **Ranks.** Preferred, normal and deprecated. Truthy `wdt:` returns the preferred values, or all normal values
  if none is preferred. Deprecated values are never returned.
* **Item-level history.** `schema:dateModified` in WDQS, the revision history and `lastrevid` in
  `Special:EntityData`. These date any edit, not a check of the contact details.

### 4.2 Measured over 1,045 items (the 978 bodies plus courts)

| Property | Statements | With any reference | Ref. URL (P854) | Stated in (P248) | Imported from Wikimedia (P143) | Retrieved (P813) | Start / end qualifier | Preferred / deprecated |
|---|---|---|---|---|---|---|---|---|
| P856 official website | 1,076 | 636 (59 %) | 348 | 83 | 189 (18 %) | 39 (4 %) | 17 / 9 | 50 / 58 |
| P968 email | 61 | 60 (98 %) | 60 | 5 | 0 | 50 (82 %) | 0 / 0 | 0 / 1 |
| P1329 phone | 59 | 57 (97 %) | 57 | 19 | 0 | 31 (53 %) | 0 / 0 | 0 / 0 |
| P11266 contact page | 94 | 6 (6 %) | 6 | 0 | 0 | 6 | 0 / 0 | 0 / 1 |
| P2002 X username | 379 | 71 (19 %) | 25 | 43 | 7 | 48 | 269 / 1 | 4 / 2 |
| P2013 Facebook | 251 | 71 (28 %) | 24 | 49 | 0 | 50 | 14 / 1 | 1 / 3 |

Other observations:

* 973 of the 1,076 P856 statements (90 %) carry P407 language. 121 items in the wider set have more than one
  current P856, and that set holds 148 deprecated P856 statements, kept as history.
* Most P856 reference URLs come from North Carolina, where they point to the state's boards-and-commissions
  directory (`bc.governor.nc.gov`) and `nc.gov`. Without NC, website sourcing is mostly "imported from Wikipedia"
  or nothing.
* On the wider pre-cleaning set, the email retrieval dates cluster in 2025 (41 of 73). Phone retrieval dates
  are spread from 2017 to 2026.
* Item `schema:dateModified`: 958 of 1,045 items were edited in 2025–2026, and the median is 2025-11. It can
  reflect any edit (labels, bots, other properties) and says nothing about whether a phone or URL still works.

### 4.3 URL spot check

A seeded random sample of 48 current P856 values was drawn from the collected agency items before the
federal and label cleaning. Each URL got one GET for a single byte, following redirects, with a 15 s timeout.

* 42 answered 2xx.
* 2 answered 403. This is probably bot filtering, for example at `ed.gov`.
* 4 gave no usable response, among them `dps.texas.gov`, `parks.ca.gov`, `ncbar.com` and `adp.ca.gov`.
* 5 redirected to a different host. For example, `abra.dc.gov` now goes to `abca.dc.gov`, `tdhca.state.tx.us` to
  `tdhca.texas.gov`, and `ncleg.net` to `ncleg.gov`.
* 16 of the 48 were `http://`.
* Separately, the Florida Department of State URL returned 404, and `courts.state.va.us` returned 403 to the
  survey's request.

Govdirectory's 2021 health-check microservice performs this kind of check. No sign was found that its results
are fed back into Wikidata.

### 4.4 Reliability

* **Email and phone are rare but trustworthy.** Almost every one is referenced to an official page with a
  retrieved date. Govdirectory deliberately refuses to show an unreferenced phone.
* **Official website is common but weakly sourced.** Its age is unknown, and it is often `http://` or the
  pre-redirect domain. Start and end qualifiers are rare: the Florida Division of Corporations is the exception,
  not the rule. A website should be treated as a lead to verify, not as a fact.
* **Social accounts** have the most qualifiers (71 % of X usernames have a start time), but they say nothing
  about contact routes for records or FOIA.
* **The level and active status of a body** are the weakest parts: missing P1001, local bodies coded to the
  state, and dissolved bodies not marked. `adp.ca.gov` is an example: the California Department of Alcohol and
  Drug Programs has no P576, yet its website did not answer.

## 5. What this means for lexflow (suggestions, not changes)

* **Use Wikidata QIDs as entity identifiers for agencies, boards and courts**, with the English label, P749 parent
  and P856. Keep the statement ID (`wds:` GUID), its rank and qualifiers, and the reference URL and P813 date, so
  that a contact's provenance can be shown. Use `p:`/`ps:` patterns, not truthy `wdt:`, so that end-dated and
  deprecated values can be filtered.
* **Do not expect Wikidata to supply emails or phones** for VA, DC, MD, TX, CA, FL, IL or WA. Keep official
  state directories and agency contact pages as the primary source, as the existing `local-research` and
  `site-scan` paths do. Lexflow already cites some of these offices (the Virginia FOIA Council, the Maryland
  Public Access Ombudsman, DC licensing and tax). Wikidata items for them can be matched by name later.
* **Treat P143-only references as unsourced.** Prefer statements with P854 and P813. Re-check URLs on a schedule;
  lexflow's `crawl_log` table, which holds per-government scan results, is the natural place to record that.
* **For DPOR, Virginia's boards, county courts and clerks**, Wikidata has nothing to reuse. A lexflow-side
  registry, or the sandbox Lexipedia Wikibase, would hold them. Upstream Wikidata edits would be a separate
  human decision. This survey made none.
* **Govdirectory links** (`govdirectory.org/<slug>/<QID>/`) are only meaningful for federal entries and for NY
  and NC bodies, and only after checking that the QID is on the published list. Its generator queries are a good
  template for per-state class lists.
* **WDQS etiquette.** The hard query deadline is 60 s. Each client (User-Agent plus IP) gets 60 s of processing
  per minute and 30 error queries per minute, with at most 5 parallel queries per IP. Excess gets HTTP 429 with
  `Retry-After`. A descriptive User-Agent is required. During this survey, broad `P279*` queries regularly hit
  the 15 s client timeout. Two-step queries worked reliably: first collect the QIDs, then fetch details with
  `VALUES` in chunks of 120–250. Since May 2025, scholarly articles are served from a separate graph
  ([graph split](https://meta.wikimedia.org/wiki/WikiCite/WDQS_graph_split)). Government items stay on
  `query.wikidata.org`.

## 6. Queries used (abridged)

```sparql
# (a) state-coded government agencies (one state per run; DC used wd:Q61 and wd:Q3551781)
SELECT DISTINCT ?i WHERE {
  VALUES ?S { wd:Q1370 }
  ?i wdt:P131|wdt:P1001 ?S .
  ?i wdt:P31/wdt:P279* wd:Q327333 .
}

# per-state classes under "state agency of the United States"
SELECT ?sib ?sibLabel (COUNT(DISTINCT ?i) AS ?n) WHERE {
  ?sib wdt:P279 wd:Q20857085 .  OPTIONAL { ?i wdt:P31 ?sib }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
} GROUP BY ?sib ?sibLabel ORDER BY DESC(?n)

# (d) agencies located in a capital (Tallahassee shown)
SELECT DISTINCT ?i ?l WHERE {
  wd:Q37043 ^wdt:P131 ?i .  ?i wdt:P31 ?t .
  { SELECT ?t WHERE { ?t wdt:P279* wd:Q327333 } }
  OPTIONAL { ?i rdfs:label ?l . FILTER(LANG(?l)="en") }
  MINUS { ?i wdt:P576 [] }
}

# courts up to two location hops from the state
SELECT DISTINCT ?i WHERE {
  hint:Query hint:optimizer "None" .
  VALUES ?S { wd:Q1370 }
  ?c wdt:P279* wd:Q41487 .  ?i wdt:P31 ?c .
  { ?i wdt:P131|wdt:P1001 ?S }
  UNION { ?i wdt:P131|wdt:P1001 ?l . ?l wdt:P131 ?S }
  UNION { ?i wdt:P131|wdt:P1001 ?l . ?l wdt:P131 ?l2 . ?l2 wdt:P131 ?S }
  MINUS { ?i wdt:P576 [] }
}

# contact statements with references and qualifiers (VALUES chunk of QIDs)
SELECT ?i ?prop ?st ?val ?rank ?ref ?ret ?refurl ?statedin ?start ?end WHERE {
  VALUES ?i { wd:Q107179384 wd:Q5020429 }
  VALUES (?prop ?p ?ps) { ("P856" p:P856 ps:P856) ("P968" p:P968 ps:P968) ("P1329" p:P1329 ps:P1329) ("P11266" p:P11266 ps:P11266) }
  ?i ?p ?st . ?st ?ps ?val ; wikibase:rank ?rank .
  OPTIONAL { ?st prov:wasDerivedFrom ?ref .
             OPTIONAL { ?ref pr:P813 ?ret } OPTIONAL { ?ref pr:P854 ?refurl } OPTIONAL { ?ref pr:P248 ?statedin } }
  OPTIONAL { ?st pq:P580 ?start } OPTIONAL { ?st pq:P582 ?end }
}
```

## 7. Sources (all opened on 2026-10-10)

Govdirectory

* <https://www.govdirectory.org/>, its [about page](https://www.govdirectory.org/about/) and its
  [statistics page](https://www.govdirectory.org/statistics/)
* US listings: [United States](https://www.govdirectory.org/united-states/),
  [North Carolina](https://www.govdirectory.org/united-states/north-carolina/) and
  [New York](https://www.govdirectory.org/united-states/new-york/)
* An organisation page: [US Department of Justice](https://www.govdirectory.org/united-states/Q1553390/)
* [robots.txt](https://www.govdirectory.org/robots.txt) and [sitemap.xml](https://www.govdirectory.org/sitemap.xml)
* The website repository: [README](https://github.com/govdirectory/website),
  [CONTRIBUTING](https://github.com/govdirectory/website/blob/main/CONTRIBUTING.md),
  [ADD_A_COUNTRY](https://github.com/govdirectory/website/blob/main/ADD_A_COUNTRY.md),
  [DEPLOY](https://github.com/govdirectory/website/blob/main/DEPLOY.md) and
  [publiccode.yml](https://github.com/govdirectory/website/blob/main/publiccode.yml)
* The website's queries: [countries.rq](https://github.com/govdirectory/website/blob/main/queries/countries.rq),
  [organization-optional.rq](https://github.com/govdirectory/website/blob/main/queries/organization-optional.rq) and
  [account-data.rq](https://github.com/govdirectory/website/blob/main/queries/account-data.rq)
* Other repositories: [website-cache](https://github.com/govdirectory/website-cache),
  [health-check-service](https://github.com/govdirectory/health-check-service),
  [browser-extension](https://github.com/govdirectory/browser-extension) and
  [QuickStatements-upload-support](https://github.com/govdirectory/QuickStatements-upload-support)

Wikidata and Wikimedia

* The WikiProject: [Wikidata:WikiProject Govdirectory](https://www.wikidata.org/wiki/Wikidata:WikiProject_Govdirectory),
  its [Data model](https://www.wikidata.org/wiki/Wikidata:WikiProject_Govdirectory/Data_model) and its
  [Error reports](https://www.wikidata.org/wiki/Wikidata:WikiProject_Govdirectory/Error_reports)
* WikiProject pages for the US:
  [United States of America](https://www.wikidata.org/wiki/Wikidata:WikiProject_Govdirectory/United_States_of_America),
  [North Carolina](https://www.wikidata.org/wiki/Wikidata:WikiProject_Govdirectory/United_States_of_America/North_Carolina)
  and [New York](https://www.wikidata.org/wiki/Wikidata:WikiProject_Govdirectory/United_States_of_America/New_York)
* Example items: [Q11969252](https://www.wikidata.org/wiki/Q11969252), [Q107179384](https://www.wikidata.org/wiki/Q107179384),
  [Q5020429](https://www.wikidata.org/wiki/Q5020429), [Q7444418](https://www.wikidata.org/wiki/Q7444418),
  [Q7603136](https://www.wikidata.org/wiki/Q7603136), [Q138637634](https://www.wikidata.org/wiki/Q138637634) and
  [Q16152667](https://www.wikidata.org/wiki/Q16152667)
* Classes: [Q20857085](https://www.wikidata.org/wiki/Q20857085), [Q114634763](https://www.wikidata.org/wiki/Q114634763),
  [Q125771287](https://www.wikidata.org/wiki/Q125771287) and [Q139489412](https://www.wikidata.org/wiki/Q139489412)
* WDQS: [User Manual, query limits](https://www.mediawiki.org/wiki/Wikidata_Query_Service/User_Manual#Query_limits),
  the [Wikimedia User-Agent policy](https://foundation.wikimedia.org/wiki/Policy:Wikimedia_Foundation_User-Agent_Policy)
  and the [WDQS graph split](https://meta.wikimedia.org/wiki/WikiCite/WDQS_graph_split)
