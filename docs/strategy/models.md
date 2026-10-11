# How lexflow could pay for itself: sustainability and service models

_10 October 2026. Research and writing only: nothing was posted, no one was contacted, no wiki was edited and no
repository file other than this one was changed. Web pages were read with the User-Agent
`lexflow-research/0.1 (https://github.com/alibama/lexflow)`, one request per host at a time, with pauses between
them. The web-search budget ran out partway through, so some points are marked **unverified**. Section 8 lists them._

_Credit and privacy. Organisations, projects, official offices, statutes and published works only. People appear only
as authors of cited works. Nobody cited here is a partner, advisor, endorser or prospective collaborator of
lexflow. This is information, not legal advice. The licensing, procurement and privacy questions in §5 and §9 are
for counsel and the university._

Companion notes in this folder: [landscape.md](landscape.md) covers the vendors and the plugin question,
[wedge.md](wedge.md) covers where to start, and [communities.md](communities.md) covers who to approach. This note
covers how the work could be paid for, and what any paid version must clear first.

---

## 1. The short answer

**Recommended, in this order:**

1. **Now to 18 months: a university lab, paid for by grants, with a course pipeline.** This is the pattern of the
   Legal Information Institute, the Stanford Legal Design Lab, the Suffolk LIT Lab and the early National Zoning
   Atlas. The money comes from the university and from grants that fit open-source, access-to-justice work:
   NSF PESOSE Track 1, LSC Technology Initiative Grants through a legal-aid grantee, and Wikimedia Rapid Funds for
   the wiki work. Graduate students do the work. Each one owns one niche output that a named kind of user can
   check. No money changes hands with cities yet. (§6.1)
2. **12 to 36 months: free outputs, paid verification and upkeep.** This is the pattern of Open Law Library, Free Law
   Project's data services and the Zoning Atlas's commissioned evaluations. The checked state rules stay free to
   read. Institutions pay for reviewed "rule packs" with change alerts: legal-aid self-help sites, state
   open-government offices, records officers and, through them, the records software they already run. Most such
   jobs are small enough for small-purchase rules. (§6.2)
3. **Later, and only if (1) shows real use: free embeds and data, with a hosted tier for institutions.** This is the
   pattern of Vaquill's own open-us-law, CourtListener and Open States. It means a vendor-neutral widget and a feed,
   not a Granicus or CivicPlus plugin. (§6.3)

**What will not work now** (§7):

- An open-core startup, or selling software to cities.
- Advertising, or donations as the main income.
- Counting on grant programmes that are archived, closed or invitation-only: NSF CIVIC (archived), Arnold Ventures
  and Schmidt Sciences (no unsolicited proposals), and Knight's 2026 call (closed, and limited to 26 communities).
- Any paid product while the statute data is CC BY-NC.

**What has to come first, whichever model is chosen:**

- a licence for lexflow's own code (it has none);
- a licence statement on both Lexipedia sites;
- a commercial-clean path for the statute text;
- a decision about the AGPL dependencies;
- WCAG 2.1 AA conformance for anything a government will show residents;
- IRB and IP sign-off before graduate students interview users or release code.

**Is it a hammer looking for a nail?** Partly. "Every statute as BPMN" is a hammer: no buyer asks for BPMN. But
four of the nails below already have someone paying to drive them, and lexflow's checked, quoted models fit them
(§2):

- legal aid paying, through LSC grants, for tools that keep self-help content in step with changing law;
- records-request software that each customer must configure to its own state's law;
- funders backing tools that guide people through a freedom-of-information process;
- cities paying for expert evaluations of their own codes.

---

## 2. Is there a nail? The evidence that someone pays for this kind of work

| Signal | What it shows | What lexflow already has |
|---|---|---|
| In LSC's 2025 cycle, a Technology Initiative Grant went to Atlanta Legal Aid Society to adopt **LACI (Legal Aid Content Intelligence)**: "an open-source tool developed by Lone Star Legal Aid to automatically track and update changes in laws, regulation, and court rules in order to ensure self-help legal information is always accurate" ([LSC, TIG awards by year](https://www.lsc.gov/grants/technology-initiative-grant-program/technology-initiative-grant-awards-tig-projects-funded-year)) | Legal aid funds tools that watch the law change, and replicates open-source ones across states | Statute snapshots with hashes, checked quotes, `check-curated` re-verification ([README](../../README.md#what-is-verified)) |
| Granicus sells "Records Request Management (GovQA)", "a fully configurable suite of tools", alongside permitting and licensing products (AMANDA, SmartGov) ([Granicus](https://granicus.com/), [public records](https://granicus.com/solution/public-records-and-compliance/)) | Each customer's records workflow has to be configured to its state's clocks, extensions and appeals. Someone has to get those right | 11 Claude-reviewed public-records models with deadlines and appeal routing; the deadline arithmetic in the process lab ([lab-plan.md](../design/lab-plan.md)) |
| Mozilla's 2026 Democracy x AI cohort funded ten projects. One "helps people navigate the entire freedom-of-information process" for Spain's transparency law, up to drafting an appeal ([Mozilla Foundation](https://www.mozillafoundation.org/en/what-we-do/grantmaking/incubator/democracy-ai-cohort/)) | Funders back FOI navigation for requesters | The requester's lane of the same records models |
| A city commissioned the National Zoning Atlas's founder to evaluate its draft zoning code, using the Atlas's data (NZA news items of 22 September 2026, [zoningatlas.org](https://www.zoningatlas.org/projects)) | Cities pay for expert, standardised readings of their own law | Cross-state alignment of process models; the ordinance layer from LOCUS |
| The contacts pilot found 43% (±14 points) of verifiable official websites stale; 3 of 55 sampled now serve gambling or spam ([entities-contacts.md](../design/entities-contacts.md), D8) | A data-quality problem the Wikidata and Govdirectory communities care about. The Census source is frozen (discontinued April 2025, per [credits-research.md](../design/credits-research.md) finding 8) | The re-check loop |

**What is not a nail (yet):**

- **BPMN or DMN as the product.** No buyer was found asking for them ([landscape.md](landscape.md) §Summary). Lead
  with the clock, the next step and the contact; keep the diagram underneath as the checked representation.
- **Coverage claims for all 38,640 governments.** The selector-built models score about 0.60 against Claude's
  references, and Ask scores 0.40 (0.75 when handed Claude's sections). Neither is good enough to sell or to show
  residents as an answer ([README](../../README.md)).
- **Local-model summaries.** On the benchmark they did not help.

---

## 3. How comparable projects actually sustain themselves

Revenue figures are from IRS Form 990 data as extracted by ProPublica's Nonprofit Explorer. They are the last filed
year shown, not audited statements.

| Project | Model | Evidence | Lesson for lexflow |
|---|---|---|---|
| **Free Law Project** (CourtListener, RECAP) | Nonprofit; free site; API through memberships; commercial agreements; paid data services | **2024:** revenue $1,347,431, of which program services $1,037,242 (77.0%) and contributions $292,701 (21.7%). **2023:** $854,099, with program services 48.9% ([ProPublica](https://projects.propublica.org/nonprofits/organizations/463342480)). Data services are billed hourly: $140/h for researchers and academics, $140–180/h for nonprofits, $170–750/h for for-profits. It is "able to join NSF grant proposals" ([FLP](https://free.law/data-consulting/)). Membership API access may not be used "to build tools for for-profit or non-profit organizations" ([FLP](https://free.law/membership/allowed-api-usage/)) | Earned revenue can carry a legal-data nonprofit, but only on a unique asset (bulk federal court data), and only after years of being free. Its rates are a usable price benchmark. Its API terms bind lexflow (§5.1) |
| **MuckRock** (requests, DocumentCloud) | Nonprofit; free and paid tools; mostly philanthropy | **2024:** revenue $5,277,573, of which contributions 87.5% and program services 10.4% ([ProPublica](https://projects.propublica.org/nonprofits/organizations/811485228)) | Tools for records requesters stay grant-dependent even at scale |
| **Code for America** | Nonprofit; products and government partnerships | **2024:** revenue $29,850,899; expenses $38,410,774; contributions 92.3%; program services $1,095,211 ([ProPublica](https://projects.propublica.org/nonprofits/organizations/271067272)). Government *grants* are counted in contributions on the 990, so the split understates government money | Even the largest civic-tech nonprofit runs mainly on philanthropy, and ran a deficit in 2024 |
| **Legal Information Institute** (Cornell) | University-hosted; donations; lawyer directory and advertising | About 60% from Cornell Law School, 20% from individual donors and 20% from the lawyer directory and online advertising. More than 80% of the budget is salaries and student stipends ([LII](https://www.law.cornell.edu/lii/about-lii)) | The host institution is the base, students do much of the work, and earned income is a fifth |
| **Public.Resource.Org** | Donor-funded nonprofit | **2025:** revenue $880,262, 100% contributions; expenses $1,033,958 ([ProPublica](https://projects.propublica.org/nonprofits/organizations/208842127)) | Law-access advocacy draws donors, not customers |
| **Open States / Plural** | Open data core inside a company | A Sunlight Foundation project 2009–2016, then independent; by 2021 it "was being run by just a few people, and was looking for new options to keep the lights on", and Plural adopted it ([Open States](https://open.pluralpolicy.com/about/), [Plural](https://pluralpolicy.com/blog/plural-acquires-open-states-and-invests-in-the-future-of-civic-data/)). In December 2025 SAI360, a portfolio company of STG Partners, acquired Plural ([Paul Hastings](https://www.paulhastings.com/news/paul-hastings-advises-sai360-on-its-acquisition-of-plural-policy)) | The commons survived two changes of owner because it was open. Control did not stay with the community. If lexflow ever sits inside a company, license the data and code openly first |
| **docassemble** | MIT-licensed open source; community Slack; consultants; grant-funded deployments | MIT licence ([docassemble](https://docassemble.org/docs/license.html)); help through Slack and listed consultants ([support](https://docassemble.org/docs/support.html)). A 2025 TIG moves MichiganLegalHelp.org's tools from LawHelp Interactive to docassemble ([LSC](https://www.lsc.gov/grants/technology-initiative-grant-program/technology-initiative-grant-awards-tig-projects-funded-year)) | A free core plus an ecosystem paid through legal-aid grants. Its support page points to a single developer, and one maintainer is lexflow's risk too |
| **Suffolk LIT Lab** | Law-school lab; open-source tools; courses | The Document Assembly Line on docassemble, Court Forms Online, Massachusetts court repositories and class materials ([GitHub](https://github.com/SuffolkLITLab), [Assembly Line](https://github.com/SuffolkLITLab/docassemble-AssemblyLine)). Its own site refused the research fetcher (403), so its funding is **unverified** here | Course plus lab plus court partners is a working pipeline for student-built legal tools |
| **Stanford Legal Design Lab** | Law-school lab; courses; field standards; court partnerships | The Filing Fairness Project, "a national cohort of state courts to propose new technology, procurement, and form strategies"; the LIST legal-issues taxonomy; the Access to Justice Network of "more than 1,300" members; a court partnership "with the support of Stanford Impact Labs" ([Stanford](https://law.stanford.edu/legal-design-lab/)) | Stewarding a shared standard (LIST) and a network gives a lab lasting relevance. lexflow's questions could carry LIST codes |
| **National Zoning Atlas** | Began as a 2020 Connecticut advocacy project; now Land Use Atlas, Inc., a 501(c)(3) that "relies on philanthropic support"; state teams; commissioned evaluations | 11K+ jurisdictions published and 1.3M+ pages of code read ([NZA](https://www.zoningatlas.org/projects), [about](https://www.zoningatlas.org/about)) | The model closest to lexflow's: one published method, state teams, a public map, then a spun-out nonprofit. The Atlas allows no reuse without written permission ([landscape.md](landscape.md)), so it is a model to copy, not a data source |
| **Govdirectory** | Volunteer project on Wikidata; micro-grants | Supported by Wikimedia Deutschland's Unlock Accelerator ([Wikidata](https://www.wikidata.org/wiki/Wikidata:WikiProject_Govdirectory)). An NLnet application asked for €10,000, all for labour, and was funded through the Open Social Fund "at a lower hourly rate (65€/h)" ([application](https://www.wikidata.org/wiki/Wikidata:WikiProject_Govdirectory/NLNet_CommonsFund_application_-_public_organizations_on_the_Fediverse), [about](https://www.govdirectory.org/about/)) | The data lives in Wikidata, so running costs stay tiny. Small grants for named features are the norm in the wiki world |
| **Open Law Library** | 501(c)(3) "open-access publisher"; governments pay for software and services; the law is free to read | "We sustain ourselves on revenues from software and services instead of charging for access to the law" ([about](https://openlawlib.org/about/)). It has worked with the D.C. Council since 2016, cutting the delay in D.C. Code updates "from as much as five months to less than three weeks" ([case study](https://openlawlib.org/case-studies/washington-dc/)) | The cleanest precedent for "free to the public, paid by government". It sells a core operational job (codification), not an add-on |
| **Vaquill AI** (open-us-law, lexflow's upstream) | Free non-commercial dataset; hosted API with a free tier; paid commercial use | Free for "research, teaching, legal aid, journalism, public-interest work and open-source projects"; a hosted API with "500 free credits", free keys for non-commercial use, and paid commercial use ([README v2026.09.1](https://oss-data-us.vaquill.ai/v2026.09.1/README.md)) | A paid lexflow service would be Vaquill's customer, unless it rebuilds the statute layer (§5.1) |
| **DataMade** | Open-source civic consultancy | Works for "governments, nonprofits, researchers, and journalists", including the City of Chicago's Department of Planning and Development and LA Metro ([DataMade](https://datamade.us/)) | "Open source plus services" works as a consultancy. It grows with staff hours, not with users |

**Patterns across the table:**

1. **Nobody here lives on software sales to governments.** Open Law Library comes closest, and it sells a core job.
2. **Earned revenue arrives late, and through services or data licences.** Free Law Project moved from about half
   earned to 77% earned between 2023 and 2024, on top of a large, unique dataset.
3. **The durable academic projects have a host commitment** (LII's 60%) and a teaching pipeline.
4. **Open licences protect the commons when the owner changes** (Open States).

---

## 4. Funders: what is open, what fits, and what needs a partner

| Funder / programme | Status (checked 10 Oct 2026) | Terms that matter | Fit for lexflow |
|---|---|---|---|
| **NSF PESOSE** (NSF 26-506, Pathways to Enable Secure Open-Source Ecosystems) | **Open.** Deadlines: 1 September 2026 (passed), **2 March 2027**, then the first Tuesday in March each year ([NSF](https://www.nsf.gov/funding/opportunities/pesose-pathways-enable-secure-open-source-ecosystems/nsf26-506/solicitation)) | Track 1 (scoping and planning): up to $300,000, about 30 awards. Track 2: up to $1,500,000, about 10 awards. Universities may lead. "I-Corps for PESOSE" is mandatory. It is for ecosystems "built around existing open-source products, tools, and artifacts that already show promise", and NSF lists "documented demand for products" among the traits of successful ones | **Strong, once the code has an OSI licence** and there is some evidence of users and outside contributors. Track 1 pays to plan the managing organisation: exactly the question this note asks |
| **NSF CIVIC** (Civic Innovation Challenge) | **Archived**; NSF 24-534 was the last ([NSF](https://www.nsf.gov/funding/opportunities/civic-civic-innovation-challenge/505728/nsf24-534)) | — | Do not plan on it |
| **LSC Technology Initiative Grants** | The annual cycle ran February–October 2026: announcement 23 February, pre-applications 10 April, full applications 30 June, awards October ([LSC](https://www.lsc.gov/grants/technology-initiative-grant-program/how-apply-technology-initiative-grant)). A 2027 cycle on similar dates is an **estimate** | Only "current LSC basic field grant recipients" may apply; partners such as courts, bar associations and libraries are encouraged. General grants have a recommended minimum of $40,000 and no maximum. Planning grants are new in 2026: Phase 1 up to $75,000. Technology Improvement Projects up to $35,000 ([description](https://www.lsc.gov/grants/technology-initiative-grant-program/tig-program-description)). 2025: 32 grants to 22 organisations, over $4.2 million ([awards](https://www.lsc.gov/grants/technology-initiative-grant-program/technology-initiative-grant-awards-tig-projects-funded-year)). Congress passed $540 million for LSC for FY2026, a 3.6% cut, after the White House proposed eliminating it ([House](https://www.lsc.gov/press-release/bipartisan-show-support-house-passes-540m-legal-services-fy-2026), [Senate](https://www.lsc.gov/press-release/senate-passes-540m-legal-services-fy-2026)) | **Good, with a legal-aid grantee as applicant** and lexflow as a contracted or partner component: for example law-change monitoring for a statewide self-help site, as LACI does. Political risk to LSC is real |
| **Knight Foundation**, Knight Cities Challenge | 2026 call **closed** 30 April 2026 ([Knight](https://knightfoundation.org/knight-cities-challenge/)) | Up to $200,000 for one-year projects; open to universities, governments and others. The project "must take place in one or more of the 26 Knight communities" and fit local news and information, economic opportunity, or arts and culture | **Only through a partner place** among the 26 (for example Charlotte, Philadelphia, Detroit, San Jose, St. Paul or Miami-Dade). "Start a business" fits economic opportunity. Watch for the next call. The Knight Prototype Fund's legacy page reads "closed" (current status **unverified**) |
| **Arnold Ventures** | Does "not currently accept unsolicited grant proposals"; RFPs only ([AV](https://www.arnoldventures.org/grants/)) | — | Only if an RFP matches, for example on court debt. Watch, do not pitch |
| **Schmidt Sciences** | "Do not accept unsolicited proposals"; current calls are science and AI research ([Schmidt Sciences](https://www.schmidtsciences.org/opportunities/)) | — | Not a fit now |
| **Mozilla Foundation**, Democracy x AI cohort | 2026 cohort **selected**: ten projects in a 12-month incubator ([Mozilla](https://www.mozillafoundation.org/en/what-we-do/grantmaking/incubator/democracy-ai-cohort/)) | Per a university funding notice: $50,000 over 12 months, US 501(c)(3) nonprofits, and at least some code open source ([UCSC](https://toolkit.science.ucsc.edu/2026/02/24/open-call-mozilla-foundation-democracy-x-ai-cohort/)) | A good thematic fit (an FOI tool was funded). It needs a nonprofit applicant or fiscal sponsor. Watch for the next call |
| **Alfred P. Sloan Foundation** | Funds university open-source program offices (OSPOs). Syracuse's OSPO received a two-year grant "to transition from a grant-funded initiative to a sustainable, permanent University institution" ([Syracuse](https://news.syr.edu/2025/12/03/open-source-program-office-secures-719k-grant/)) | Sloan's own pages refused the fetcher (403), so current programme terms are **unverified** | **Indirect.** If the university has an OSPO, it is the natural home for lexflow's licensing, contributor and student work |
| **Wikimedia Foundation Rapid Fund** | Open by application ([Meta-Wiki](https://meta.wikimedia.org/wiki/Grants:Project/Rapid)) | $500–5,000 per application; up to $10,000 a year per individual or organisation | **Good for the wiki side**: Wikidata contact freshness, Wikibase tooling, community events. Small, but it builds standing in the community |
| **NLnet, Wikimedia Deutschland Unlock** | Used by Govdirectory (above) | Eligibility of a US university project **unverified** | Check before planning |
| **Public Interest Technology University Network** | No 2025 or 2026 call found (**unverified**) | Earlier calls were for member institutions (**unverified** for 2026) | Ask the university whether it is a member |

---

## 5. Constraints on any paid or government version

### 5.1 Data licences: what a paid service would need

**What the licences actually say.**

- **CC BY-NC 4.0.** "NonCommercial means not primarily intended for or directed towards commercial advantage or
  monetary compensation."
- **Use, not user.** Creative Commons says the test is "the primary purpose for which the work is used, not ... the
  category or class of reuser". So a university or a government gets no automatic pass.
- **Uses that need no permission.** NC "does not limit uses otherwise allowed by limitations and exceptions",
  including activity "for which no permission under such rights is required" ([CC](https://wiki.creativecommons.org/wiki/NonCommercial_interpretation)).
- **open-us-law separates three layers.**
  - The legal text is public domain under *Georgia v. Public.Resource.Org*.
  - The "compilation, normalization, and structuring" is CC BY-NC 4.0.
  - The scrapers are Apache-2.0.
  - "Snapshots published before `v2026.09.1` were released under CC BY 4.0, and that licence continues to apply to
    copies of those snapshots." The copy on disk is v2026.09.1, the CC BY-NC one.
  - Source: [README](https://oss-data-us.vaquill.ai/v2026.09.1/README.md).

**What follows (for counsel to confirm).** A service that a city, a legal-aid office or a vendor pays lexflow for is
"directed towards ... monetary compensation". It needs one of these:

| Path | What it takes | Cost and risk |
|---|---|---|
| A commercial licence or the paid API from Vaquill | Email the address in the README | Cheapest to start. The service then depends on a for-profit upstream |
| Rebuild the statute layer from the official publishers | Every section already carries its publisher URL. The scrapers are Apache-2.0, and the text is public domain. A compilation lexflow builds itself is not Vaquill's CC BY-NC compilation | Engineering and upkeep. State sites have their own terms and robots rules; check each state. **Best long-term path** |
| Use a pre-v2026.09.1 CC BY 4.0 snapshot | A copy of an earlier release (lexflow holds only v2026.09.1) | Free but stale. Only for scoped work where the snapshot date is stated |

**The other data and dependencies:**

- **LOCUS (CC BY-NC 4.0).** lexflow uses it only to find ordinances, never to cite them (README). A paid scope should
  drop it, or get a licence from its publisher ([LocalLaws/LOCUS-v1](https://huggingface.co/datasets/LocalLaws/LOCUS-v1);
  the dataset card cites [arXiv:2606.19334](https://arxiv.org/abs/2606.19334)), or find ordinances some other way.
  Commercial code publishers stay link-only ([landscape.md](landscape.md)).
- **CourtListener.** Membership API access may not "power a revenue-positive commercial product" or "build tools for
  for-profit or non-profit organizations", and internal tooling counts as commercial ([FLP](https://free.law/membership/allowed-api-usage/)).
  - A paid deliverable that includes case links needs FLP's commercial agreement, or must leave the case layer out.
  - The academic research can use FLP's EDU membership.
- **AGPL dependencies.** pm4py and powl are AGPL-3.0 ([credits-research.md](../design/credits-research.md) finding
  6). AGPL §13 requires a modified version to "prominently offer all users interacting with it remotely through a
  computer network" its source ([GNU](https://www.gnu.org/licenses/agpl-3.0.html)).
  - For an open-source hosted service that is easy to meet.
  - For a vendor integration it may not be. Many companies avoid AGPL code in their products; that is an
    inference, not a checked fact.
  - Decide early: license lexflow under the AGPL, or isolate or replace pm4py in anything hosted.
- **Lexipedia's own licence.**
  - Both sites must say which licence covers the pages and items lexflow loads (credits-research finding 2).
  - CC BY-NC is not on the Open Definition's list of conformant licences ([Open Definition](https://opendefinition.org/licenses/)).
  - The Digital Public Goods standard accepts CC BY-NC for content collections. For open data it requires an
    approved open-data licence ([DPG Standard](https://raw.githubusercontent.com/DPGAlliance/DPG-Standard/main/standard.md)).
  - So rebuilding the statute layer, and licensing lexflow's own data openly, could also unlock "open data" status
    and cleaner loading into Wikidata (CC0), which matters for the wiki community.

### 5.2 Unauthorised practice of law and liability

How others handle it, from sources read:

- **The Texas statute.** Texas excludes from the "practice of law" the "design, creation, publication, distribution,
  display, or sale ... of written materials, books, forms, computer software, or similar products if the products
  clearly and conspicuously state that the products are not a substitute for the advice of an attorney"
  (Tex. Gov't Code § 81.101(c), [official text](https://tcss.legis.texas.gov/resources/GV/htm/GV.81.htm#81.101),
  read from the open-us-law snapshot of 30 September 2026).
- **The Texas forms statutes.** The legislature requires the same statement on its own court-promulgated self-help
  forms (§ 22.019(b)(2) for landlord-tenant forms).
- **LII.** Its compilations "should not be confused with legal advice", and LII and Cornell "disclaim all liability
  to any person for any loss caused by errors or omissions" ([LII](https://www.law.cornell.edu/lii/terms/documentation)).
- **Regulatory sandboxes.** Utah closed the alternative-business-structure-only part of its sandbox at the end of
  2024 and narrowed the rest ([Utah](https://utahinnovationoffice.org/)). Arizona runs an ABS programme under
  Supreme Court Rules 31 and 31.1(c) ([Arizona](https://www.azcourts.gov/cld/Alternative-Business-Structure)).
  lexflow does not need either while it stays information. Both matter only if a later model gives advice on a
  person's facts through lawyers.

What this means for lexflow (most is already in [lab-plan.md](../design/lab-plan.md) and
[wedge.md](wedge.md) §3.8):

- **Every answer:**
  - quotes the statute word for word, cites it, and dates the snapshot;
  - states plainly that it is not a substitute for the advice of an attorney;
  - names the official place to check, such as the records officer or the state's FOIA office.
- **The process lab's deadline calculator** is the part closest to applying law to facts. Keep it a calculator of
  statutory periods, with the counting rule shown and quoted.
- **Paid or government deployments** should leave content review with the deploying office or legal-aid partner,
  and say so on the page.
- **Never sell or show residents** the 0.60 selector drafts or the 0.40 Ask answers as answers. Only reviewed
  models (quality 0.99–1.00) go into anything sold.
- **Liability and indemnity in a contract** are for counsel. Universities and public bodies are often limited in
  what they may promise; that is an inference, not checked here.

### 5.3 Accessibility and procurement for government use

**Accessibility is a contract requirement, not a nicety.**

- **The rule.** Under the ADA Title II rule, state and local web content and mobile apps "usually" must meet
  WCAG 2.1 Level AA. Content posted by a government's contractor or vendor is not excepted
  ([ada.gov](https://www.ada.gov/resources/2024-03-08-web-rule/)).
- **The new dates.** An interim final rule published 20 April 2026 moved compliance to **26 April 2027** for
  entities of 50,000 people or more, and **26 April 2028** for smaller ones and special districts
  ([Federal Register](https://www.federalregister.gov/documents/2026/04/20/2026-07663/extension-of-compliance-dates-for-nondiscrimination-on-the-basis-of-disability-accessibility-of-web)).
- **What buyers ask for.** An Accessibility Conformance Report, usually on the ITI VPAT template ("VPAT 2.5Rev WCAG",
  April 2025; [ITI](https://www.itic.org/policy/accessibility/vpat)).
- **For lexflow:**
  - Every embed, BPMN view, decision table and PDF form that a city shows residents needs a WCAG 2.1 AA audit first.
  - A BPMN canvas needs a text equivalent. The step list with quotes already is one; make it the primary view.

**Purchasing thresholds.**

| Rule | Threshold | Source |
|---|---|---|
| Federal micro-purchase threshold (FAR 2.101) | **$15,000** (from $10,000), effective 1 October 2025 | [90 FR 41872](https://www.federalregister.gov/documents/2025/08/27/2025-16412/federal-acquisition-regulation-inflation-adjustment-of-acquisition-related-thresholds) |
| Federal simplified acquisition threshold | **$350,000** (from $250,000), same rule | same |
| Local governments spending federal grant money (2 CFR 200.320) | Micro-purchases may skip quotes if the price is documented as reasonable. A recipient "may self-certify a threshold up to $50,000" a year | [eCFR](https://www.ecfr.gov/current/title-2/section-200.320) |
| Virginia public bodies, small purchases (Va. Code § 2.2-4303(G)) | With written procedures: goods and non-professional services up to **$200,000**; professional services up to **$80,000**; competition "wherever practicable" | [Code of Virginia](https://law.lis.virginia.gov/vacode/title2.2/chapter43/section2.2-4303/) |
| Virginia, who the competition rule covers (§ 2.2-4303(A)) | Competitive sealed bidding or negotiation is required for "public contracts with nongovernmental contractors" | same |
| Virginia, cooperative buying ("piggybacking", § 2.2-4304) | Joint procurement with other public bodies. A public body may buy from another public body's contract "if the request for proposal or invitation to bid specified that the procurement was a cooperative procurement" | [Code of Virginia](https://law.lis.virginia.gov/vacode/title2.2/chapter43/section2.2-4304/) |

**What the thresholds mean in practice:**

- **Small pilots fit small purchase.** A pilot of $5,000–$50,000 (an estimate of typical scope) can usually be bought
  under small-purchase rules. Other states' thresholds differ; check each one.
- **A public university may be outside the competition rule.** In Virginia, § 2.2-4303(A) is written for
  nongovernmental contractors, so a city contracting with a public university may not need competition at all.
  The city attorney decides. This is a real advantage of keeping the service inside the university for now.
- **Cooperative contracts are the incumbents' channel.**
  - Sourcewell "is a local unit of government under Minnesota state statute, and competitively solicits and awards
    contracts" ([Sourcewell](https://www.sourcewell-mn.gov/)).
  - NASPO ValuePoint uses a "Lead State Model" ([NASPO ValuePoint](https://www.naspovaluepoint.org/)).
  - Granicus sells through the distributor Carahsoft and through resellers and system integrators
    ([Granicus partners](https://granicus.com/partners/)).
  - Winning a cooperative contract is a formal competition. It is not a realistic step for lexflow before it has
    references.
- **Hosted resident data brings security reviews.** GovRAMP, a nonprofit, verifies cloud products' security for
  governments ([GovRAMP](https://govramp.org/)). The cheapest way through is to hold no resident data on a server
  (§5.4).

### 5.4 Residents' privacy

- **Virginia's consumer privacy law does not apply to lexflow's likely homes.** The Virginia Consumer Data Protection
  Act exempts political subdivisions, nonprofits and institutions of higher education (Va. Code § 59.1-576(B),
  [text](https://law.lis.virginia.gov/vacode/title59.1/chapter53/section59.1-576/)).
- **Virginia's government data law does apply, and it reaches contractors.**
  - "Agency" in the Government Data Collection and Dissemination Practices Act covers state and local bodies. It
    "shall also include any entity, whether public or private, with which any of the foregoing has entered into a
    contractual relationship for the operation of a system of personal information to accomplish an agency
    function" (§ 2.2-3801, [text](https://law.lis.virginia.gov/vacode/title2.2/chapter38/section2.2-3801/)).
  - So if lexflow runs the process lab for a city with residents' cases on a server, it takes on the Act's duties.
    Among them: collect only what is needed, keep a record of every access for three years, safeguard the system,
    and collect nothing on political or religious beliefs (§ 2.2-3803,
    [text](https://law.lis.virginia.gov/vacode/title2.2/chapter38/section2.2-3803/)).
  - The lab's present design avoids most of this. The timeline is stateless, the case stays in the user's browser,
    and outcomes are opt-in with six fields and no group under 10 ([lab-plan.md](../design/lab-plan.md)). Keep it
    that way in any paid version. It is also the simplest answer to a security review.
- **Research with users needs IRB review first.** Interviews and surveys of planners, clerks or attorneys, and any
  study of lab outcomes, are human-subjects research. Interviews and surveys can fall in an exempt category
  (45 CFR 46.104(d)(2), [eCFR](https://www.ecfr.gov/current/title-45/section-46.104)),
  but the university's IRB decides. Get that determination before graduate students start.
- **Public records.** Data a public university or a city holds may be open to records requests. That is one more
  reason to keep residents' case details off the server.

---

## 6. Recommendation: three models, and what each needs first

### 6.1 Model A (now to 18 months): university lab, grant-funded, with a course pipeline

**What it is.** lexflow becomes a lab project with a public method (like the Zoning Atlas's), a small reviewed core
(the 22 models and the 30 AskBench references), and one niche output per graduate student per semester. Each output
serves a user group that can tell whether it is right. Outputs are published free on Lexipedia. No sales.

**Who pays:**

- the university: space, a staff or postdoc line if possible (LII's base is its host's 60%), and student credit or
  stipends;
- NSF PESOSE Track 1 (2 March 2027);
- an LSC TIG through a legal-aid grantee (likely spring 2027 pre-application, estimated from the 2026 cycle);
- Wikimedia Rapid Funds for the wiki-community work;
- an OSPO, if the university has one.

**Niche goals that also feed the funders' evidence.** These are suggestions that match [wedge.md](wedge.md) §5.

| Goal | User who can check it | Evidence it creates |
|---|---|---|
| The records response clock, extension and appeal for every place in VA, DC and MD, as a mounted lab page | Requesters; records officers; the state FOIA offices | Usage, corrections received, an accuracy audit |
| A law-change watch for the sections behind one statewide self-help site's content (LACI-like) | A legal-aid web team | A TIG partnership letter |
| Contact freshness for one state's governments, contributed back to Wikidata | Wikidata and Govdirectory editors | Edits accepted by the community; a Rapid Fund report |
| Licensing after a conviction, staff-facing, for two states | Reentry program staff | A second partner; AskBench references |

**What it needs first (in order):**

1. **Licences.** An OSI licence for lexflow's code (AGPL-3.0 fits the pm4py and powl dependencies), a licence
   statement on both Lexipedia sites, and a short data policy: what is CC BY-NC because of its source, and what is
   lexflow's own. PESOSE and Mozilla-type funders require open source.
2. **University sign-offs.** Who owns code that graduate students write, and approval to release it openly (the IP or
   tech-transfer office, or the OSPO). An IRB determination for user interviews.
3. **One partner organisation with one job.** A legal-aid grantee's self-help team, or a state open-government
   office. Not a city yet.
4. **A minimal metrics habit.** Page views on Lexipedia, API calls, corrections received and outside contributors.
   NSF lists "documented demand for products" among the traits PESOSE looks for, and these are the only honest evidence available.

**Risks:**

- Grant cliffs, and student turnover every semester.
- LSC's appropriation is politically exposed (the White House proposed eliminating it for FY2026).
- A lab can drift into building more pipeline instead of serving users. [wedge.md](wedge.md) §5.3 lists what to
  stop.

### 6.2 Model B (12 to 36 months): free outputs, paid verification and upkeep

**What it is.** The checked rules stay free to read. Institutions pay for what they cannot easily do themselves:

- a reviewed state rule pack for one process (clock, extensions, fees, appeal path, decision table, quotes);
- change alerts when the law moves, tied to legislative sessions;
- a named reviewer;
- a formal correction channel.

**Who might buy** (hypotheses; none confirmed in the sources):

- legal-aid self-help sites (through TIG or IOLTA budgets);
- state open-government offices;
- municipal leagues buying for their members;
- records officers, whose GovQA or NextRequest set-ups need state rules (see [landscape.md](landscape.md));
- law-school clinics.

**Price.** As an **estimate**, a rule pack is 40–80 hours of review and upkeep a year. At Free Law Project's
published nonprofit rates ($140–180/h), that is about $5,600–14,400 a year per state per process, well inside
small-purchase rules.

**Who invoices:**

- **Inside the university:** a service or sponsored-research agreement, which may also keep the buyer outside
  Virginia's competition rule (§5.3).
- **Or a nonprofit spun out later,** as the Zoning Atlas did with Land Use Atlas, Inc.
- **The open-access position:** never charge for access to the law, as Open Law Library says of itself.

**What it needs first:**

1. **A commercial-clean data path (§5.1).**
   - Rebuild the statute layer from the official publishers with the Apache-2.0 scrapers, or take Vaquill's
     commercial licence.
   - Drop LOCUS and CourtListener from the paid scope unless they are licensed.
2. **A quality bar written into the contract.** Only Claude- or human-reviewed models. A second human reviewer for
   anything sold. A stated snapshot date. The "not a substitute for the advice of an attorney" statement.
3. **An Accessibility Conformance Report** for whatever the buyer will show residents.
4. **Insurance and contract terms** checked by the university's counsel. No resident data held (§5.4).
5. **Two or three Model A users** willing to say the rule packs were right.

**Be candid about the limits:**

- Services revenue grows with staff hours, not users. That is DataMade's and Free Law Project's model, not a
  software margin.
- Free Law Project took years of free service before services passed half its revenue.

### 6.3 Model C (later, only if Model A shows real use): free embeds and data, with a hosted tier for institutions

**What it is.**

- **Free:** a vendor-neutral widget and a machine-readable feed (clock, next step, contact, quote) that any city or
  library site can embed, whatever its CMS. Granicus's own CMS lines are OpenCities and govAccess
  ([Granicus](https://granicus.com/)).
- **Paid:** an institutional tier with an uptime commitment, bulk API, custom questions and support.

It is how Vaquill runs open-us-law (free tier, paid commercial API), how CourtListener runs (memberships, commercial
agreements) and how Plural ran Open States (open data core, paid tools).

**Why not "a Granicus or CivicPlus plugin, free, with a service behind it":**

- **No open marketplace.** Granicus's partner page describes a distributor, resellers, system integrators and cloud
  hosting, not a public app marketplace ([Granicus partners](https://granicus.com/partners/)). CivicPlus's site
  refused the fetcher (403), so its partner terms are **unverified** here. [landscape.md](landscape.md) found that
  neither vendor lists a third-party app directory.
- **They already sell the workflow.** Granicus sells the records-request and licensing workflows itself (§2). So a
  lexflow plugin that tracks requests would compete with its customers' existing tools.
- **The realistic role** is a trusted, quoted source those systems and their AI agents can cite. That is the feed.
  landscape.md notes that CivicPlus Agent accepts "external websites" as sources.

**What it needs first:**

1. Model A's users and Model B's commercial-clean data.
2. A WCAG 2.1 AA audit of the widget.
3. The AGPL decision (§5.1).
4. A public server with an uptime commitment. GovRAMP only if resident data is ever stored, which it should not be.
5. Governance for the open core before any company is involved (the Open States lesson).

---

## 7. What will not work, and why

| Idea | Why not, now |
|---|---|
| An open-core startup selling to cities | The data is CC BY-NC. Local answers score 0.40. Procurement, WCAG, security review and support would land on one developer and some students. Open States shows the core ends up owned by whoever buys the company |
| Software or SaaS sales to local governments | Cities buy through incumbents and cooperative contracts (§5.3). The vendors already sell records and licensing workflows. lexflow has no references, insurance or conformance report |
| Advertising or donations as the main income | LII's directory-and-ads income is 20% of a budget anchored by Cornell. Public.Resource.Org, tax-exempt since 2007, lives on donations of about $0.9M a year. lexflow has neither the traffic nor the donors |
| Plugins for Granicus or CivicPlus as an independent product | No marketplace was found (§6.3). The vendors already own the workflow |
| Grant programmes that are archived, closed or invitation-only | NSF CIVIC is archived; the Knight Cities Challenge is closed and limited to 26 communities; Arnold Ventures and Schmidt Sciences take no unsolicited proposals; Mozilla's 2026 cohort is chosen |
| Charging for anything built on open-us-law v2026.09.1, LOCUS or CourtListener's membership API | Each licence or policy forbids it without a separate agreement (§5.1) |
| Selling unreviewed models or AI answers to residents | It raises accuracy, unauthorised-practice and liability problems at once (§5.2) |
| Breadth as the pitch (38,640 governments) | The scores mostly reflect the state tier, and the contact data is 43% stale where checked ([wedge.md](wedge.md) §5.3) |

---

## 8. Not verified in this pass

The web-search budget ran out partway through, and some sites refused the research fetcher. These were **not
verified** and should be checked before anyone relies on them:

- CivicPlus's partner, marketplace and cooperative-contract terms (its site returned 403).
- Georgetown Law's Iron Tech Lawyer: no official page was found at the address tried, so its model is not described
  here.
- Suffolk LIT Lab's funding sources (its site returned 403; only its GitHub was read).
- The terms of Sloan's Technology programme (sloan.org returned 403; only a grantee's news release was read).
- Code for America's product-level funding, such as state contracts (its site returned 403; only the 990 data was
  read).
- The current status of the Knight Prototype Fund, Wikimedia Deutschland's Unlock Accelerator, NLnet eligibility for
  US projects, and PIT-UN's 2026 call.
- Whether the National Zoning Atlas's founding grants came from the funders that secondary sources name. Its own
  pages say only that it relies on philanthropic support.
- The 2027 LSC TIG dates (estimated from the 2026 cycle) and the price estimates in §5.3 and §6.2.

## 9. Questions for counsel and the university

1. **Data licences.**
   - Is the open repository, and are the sandbox Lexipedia sites, non-commercial under CC BY-NC 4.0? (This repeats
     C1 in [data-expansion.md](../design/data-expansion.md).)
   - Would a fee-for-service agreement with a city or a legal-aid office be commercial?
   - Does a statute compilation lexflow builds itself from official sources with Apache-2.0 scrapers carry any of
     Vaquill's licence?
2. **Code licence.** Which licence for lexflow's code: AGPL-3.0, or a permissive licence with pm4py and powl
   isolated? Who signs off on graduate students' code?
3. **Procurement.** In Virginia, is a contract between a locality and a public university outside the competition
   requirement of § 2.2-4303(A)? If so, which agreement form does the university use for service work?
4. **CourtListener.** Does case-law metadata in the wiki and the Wikibase fit FLP's allowed API usage, or does it
   need an EDU or commercial agreement? (This repeats credits-research finding 1.)
5. **Liability.** What disclaimer and review language should a paid rule pack carry? What may the university promise
   on indemnity and insurance?
6. **Privacy.** If the process lab is ever hosted for a city, which of § 2.2-3803's duties apply, and does a
   stateless design avoid them?

---

## Sources

**Comparable projects:**

- [Free Law Project 990s](https://projects.propublica.org/nonprofits/organizations/463342480)
- [FLP data services and consulting](https://free.law/data-consulting/)
- [FLP allowed API usage](https://free.law/membership/allowed-api-usage/)
- [MuckRock 990s](https://projects.propublica.org/nonprofits/organizations/811485228)
- [Code for America 990s](https://projects.propublica.org/nonprofits/organizations/271067272)
- [LII: about and funding](https://www.law.cornell.edu/lii/about-lii)
- [LII terms of use](https://www.law.cornell.edu/lii/terms/documentation)
- [Public.Resource.Org 990s](https://projects.propublica.org/nonprofits/organizations/208842127)
- [About Open States](https://open.pluralpolicy.com/about/)
- [Plural acquires Open States](https://pluralpolicy.com/blog/plural-acquires-open-states-and-invests-in-the-future-of-civic-data/)
- [SAI360 acquires Plural (Paul Hastings)](https://www.paulhastings.com/news/paul-hastings-advises-sai360-on-its-acquisition-of-plural-policy)
- [docassemble licence](https://docassemble.org/docs/license.html)
- [docassemble support](https://docassemble.org/docs/support.html)
- [Suffolk LIT Lab on GitHub](https://github.com/SuffolkLITLab)
- [Stanford Legal Design Lab](https://law.stanford.edu/legal-design-lab/)
- [National Zoning Atlas](https://www.zoningatlas.org/projects)
- [National Zoning Atlas: about](https://www.zoningatlas.org/about)
- [Govdirectory WikiProject](https://www.wikidata.org/wiki/Wikidata:WikiProject_Govdirectory)
- [Govdirectory NLnet application](https://www.wikidata.org/wiki/Wikidata:WikiProject_Govdirectory/NLNet_CommonsFund_application_-_public_organizations_on_the_Fediverse)
- [Govdirectory about](https://www.govdirectory.org/about/)
- [Open Law Library: about](https://openlawlib.org/about/)
- [Open Law Library: D.C. case study](https://openlawlib.org/case-studies/washington-dc/)
- [open-us-law README v2026.09.1](https://oss-data-us.vaquill.ai/v2026.09.1/README.md)
- [LOCUS-v1](https://huggingface.co/datasets/LocalLaws/LOCUS-v1)
- [DataMade](https://datamade.us/)
- [Granicus](https://granicus.com/)
- [Granicus public records](https://granicus.com/solution/public-records-and-compliance/)
- [Granicus partners](https://granicus.com/partners/)

**Funders:**

- [NSF PESOSE 26-506](https://www.nsf.gov/funding/opportunities/pesose-pathways-enable-secure-open-source-ecosystems/nsf26-506/solicitation)
- [NSF CIVIC 24-534 (archived)](https://www.nsf.gov/funding/opportunities/civic-civic-innovation-challenge/505728/nsf24-534)
- [LSC TIG: how to apply](https://www.lsc.gov/grants/technology-initiative-grant-program/how-apply-technology-initiative-grant)
- [LSC TIG: programme description](https://www.lsc.gov/grants/technology-initiative-grant-program/tig-program-description)
- [LSC TIG: awards by year](https://www.lsc.gov/grants/technology-initiative-grant-program/technology-initiative-grant-awards-tig-projects-funded-year)
- [LSC FY2026: House](https://www.lsc.gov/press-release/bipartisan-show-support-house-passes-540m-legal-services-fy-2026)
- [LSC FY2026: Senate](https://www.lsc.gov/press-release/senate-passes-540m-legal-services-fy-2026)
- [Knight Cities Challenge](https://knightfoundation.org/knight-cities-challenge/)
- [Arnold Ventures grants](https://www.arnoldventures.org/grants/)
- [Schmidt Sciences opportunities](https://www.schmidtsciences.org/opportunities/)
- [Mozilla Democracy x AI cohort](https://www.mozillafoundation.org/en/what-we-do/grantmaking/incubator/democracy-ai-cohort/)
- [UCSC notice of the Mozilla call](https://toolkit.science.ucsc.edu/2026/02/24/open-call-mozilla-foundation-democracy-x-ai-cohort/)
- [Syracuse OSPO Sloan grant](https://news.syr.edu/2025/12/03/open-source-program-office-secures-719k-grant/)
- [Wikimedia Rapid Fund](https://meta.wikimedia.org/wiki/Grants:Project/Rapid)

**Licences and standards:**

- [CC BY-NC 4.0 legal code](https://creativecommons.org/licenses/by-nc/4.0/legalcode.en)
- [CC NonCommercial interpretation](https://wiki.creativecommons.org/wiki/NonCommercial_interpretation)
- [GNU AGPL-3.0](https://www.gnu.org/licenses/agpl-3.0.html)
- [Open Definition conformant licences](https://opendefinition.org/licenses/)
- [DPG Standard](https://raw.githubusercontent.com/DPGAlliance/DPG-Standard/main/standard.md)

**Law and regulation:**

- [Tex. Gov't Code § 81.101](https://tcss.legis.texas.gov/resources/GV/htm/GV.81.htm#81.101)
- [Utah Innovation Office](https://utahinnovationoffice.org/)
- [Arizona ABS programme](https://www.azcourts.gov/cld/Alternative-Business-Structure)
- [ADA Title II web rule (ada.gov)](https://www.ada.gov/resources/2024-03-08-web-rule/)
- [Interim final rule, 20 April 2026](https://www.federalregister.gov/documents/2026/04/20/2026-07663/extension-of-compliance-dates-for-nondiscrimination-on-the-basis-of-disability-accessibility-of-web)
- [ITI VPAT](https://www.itic.org/policy/accessibility/vpat)
- [FAR threshold rule, 90 FR 41872](https://www.federalregister.gov/documents/2025/08/27/2025-16412/federal-acquisition-regulation-inflation-adjustment-of-acquisition-related-thresholds)
- [2 CFR 200.320](https://www.ecfr.gov/current/title-2/section-200.320)
- [Va. Code § 2.2-4303](https://law.lis.virginia.gov/vacode/title2.2/chapter43/section2.2-4303/)
- [Va. Code § 2.2-4304](https://law.lis.virginia.gov/vacode/title2.2/chapter43/section2.2-4304/)
- [Va. Code § 59.1-576](https://law.lis.virginia.gov/vacode/title59.1/chapter53/section59.1-576/)
- [Va. Code § 2.2-3801](https://law.lis.virginia.gov/vacode/title2.2/chapter38/section2.2-3801/)
- [Va. Code § 2.2-3803](https://law.lis.virginia.gov/vacode/title2.2/chapter38/section2.2-3803/)
- [45 CFR 46.104](https://www.ecfr.gov/current/title-45/section-46.104)
- [Sourcewell](https://www.sourcewell-mn.gov/)
- [NASPO ValuePoint](https://www.naspovaluepoint.org/)
- [GovRAMP](https://govramp.org/)

**In this repository:**

- [README.md](../../README.md)
- [credits-research.md](../design/credits-research.md)
- [entities-contacts.md](../design/entities-contacts.md)
- [lab-plan.md](../design/lab-plan.md)
- [data-expansion.md](../design/data-expansion.md)
- [landscape.md](landscape.md)
- [wedge.md](wedge.md)
- [communities.md](communities.md)
