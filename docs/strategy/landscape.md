# The landscape lexflow would enter

_10 October 2026. Scope: who already serves the people lexflow wants to reach (requesters, city and county staff,
planners, attorneys, legal aid, the wiki community), what each organisation offers, where it overlaps with
lexflow, and whether there is a real route in: a public API, an app marketplace, a plugin ecosystem, a partner
programme or a data licence. It is meant to answer one practical question first: can lexflow ship "a plugin for
Granicus or CivicPlus", or must it reach people another way?_

_Method. Every claim below comes from a page that was opened, unless it is marked **not opened** or **search
summary**. Pages were read one at a time per host, never more than about one request a second to a host. The
fetch tool sends its own User-Agent and could not send lexflow's research one; this is noted so the rule is not
claimed as met when it was not. Several sites refused automated reads (HTTP 403): tylertech.com, justia.com,
nolo.com, muckrock.com, ilcourthelp.gov and thedroptimes.com. Those were not worked around; where they matter,
the entry uses a search engine's summary and says so. sji.gov failed a TLS check and was not read. The web search
budget for this run ran out before a few last checks (noted in [§9](#9-not-verified)). Third-party API
"report cards" (Supergood) are used only where a vendor gates its own documentation, and they are labelled as
outside assessments. Nothing was posted, filed, signed up for or edited anywhere._

_Credit and privacy. This document names organisations, products and published works only. Nobody here is a
partner, advisor, endorser or prospective collaborator of lexflow. Company figures (customer counts, users) are the
companies' own claims unless stated otherwise. This is information, not legal advice; the licence questions go to
counsel._

## Summary

- **No government-software vendor runs an open plugin marketplace for its website CMS.** Granicus and CivicPlus,
  who between them run about half the websites of the 1,000 largest US cities, gate their APIs behind customer
  support. Neither lists a third-party app directory. "A plugin for Granicus or CivicPlus" cannot be shipped by
  lexflow alone; it needs the vendor, or one city at a time.
- **Accela is the exception.** Its developer portal has self-serve accounts, a REST API, staging environments and
  "Free listing and promotion of apps in our Civic Storefront". But apps run on an agency's own Accela data, and
  Accela's OpenCounter permit guides already do part of what lexflow does.
- **The vendors are building AI answer agents over their own content.** CivicPlus Agent (2026) reads a city's
  CivicPlus website, its Municode code and its agendas; Granicus GXA launched in July 2025. The cheapest real
  integration is not a plugin at all: **CivicPlus Agent accepts "external websites" as knowledge sources**, set by
  the city. A city could point its agent at its Lexipedia page tomorrow, with no code from anyone.
- **The open web stack is a smaller but permission-free route.** WordPress and Drupal run about 17% of large-city
  and 22% of large-county websites (one 2024 study). Both directories require GPL-compatible code; WordPress.org
  allows a free plugin backed by an external service if the service is documented. lexflow has no licence yet, and
  no public server for a plugin to call.
- **Codes publishers are a wall.** Municode (CivicPlus) and ICC Code Solutions (American Legal Publishing and
  General Code, owned by the International Code Council) together publish codes for roughly 11,000 communities by
  their own counts. Text reuse is restricted, and the eCode360 API is "Licensed per municipality" to clients. The
  law itself is not copyrightable, but these compilations stay link-only (as lexflow already decided).
- **The legal-information nonprofits are allies with non-commercial licences.** LII is CC BY-NC-SA 2.5,
  open-us-law and LOCUS are CC BY-NC 4.0, and the National Zoning Atlas allows no reuse without written permission.
  Any paid service built on these needs a licence or a rebuild from official sources.
- **The self-help world is the most natural home.** docassemble and the Suffolk LIT Lab's Document Assembly Line
  are MIT-licensed, court-funded, and take volunteers. LawHelp Interactive serves "more than a million Americans a
  year". These tools assemble the first document and stop; lexflow's deadlines-from-statute follow-up fills that
  gap (see [lab-research.md](../design/lab-research.md) §2.1).
- **Rules as code in the US is about benefits, not procedure.** The live US community is Georgetown's Digital
  Benefits Network; OECD OPSI has tagged nothing on rules as code since 2021; 18F was shut on 1 March 2025. The
  closest precedent for lexflow anywhere is Germany's **FIM**: master processes in BPMN 2.0, each tied to its legal
  basis down to the paragraph, published by the federal level and adapted by states and municipalities.
- **Hammer or nail?** BPMN itself is a hammer: no US buyer was found asking for it. The nails are specific and
  already paid for or funded by someone: records-request deadlines (agencies buy GovQA, NextRequest and JustFOIA to
  manage requests; requesters use MuckRock and the Reporters Committee's guide), record clearance (13 states and DC
  have passed Clean Slate laws; where clearance is not automatic, the person has to act), and permit and licence
  guidance (OpenCounter, UpCodes). Lead with the deadline, the next step and the contact, checked against the
  statute; keep the diagram underneath.

## 1. Government web and records platforms

| Organisation | What it is | Overlap with lexflow | Opening, or the wall |
|---|---|---|---|
| **Granicus** (incl. Legistar, GovQA, govAccess, OpenCities, AMANDA, SmartGov, GXA) | Vendor of government websites (govAccess, OpenCities), communications (govDelivery), agendas (Legistar, OneMeeting, Peak), records requests (GovQA, GovQA Legal), permitting (AMANDA, SmartGov) and video. Claims "more than 7,000 government organizations" ([granicus.com/llms.txt](https://granicus.com/llms.txt)). Bought GovQA in August 2021, when GovQA had "nearly 800 government agency customers" ([GovConWire, 27 Aug 2021](https://govconwire.com/2021/08/granicus-expands-public-records-management-capabilities-with-govqa-buy)); bought SmartGov from Siemens-owned Brightly ([GovTech, 1 Feb 2024](https://govtech.com/biz/granicus-buys-permitting-tech-firm-smartgov-from-siemens)). Launched GXA, an AI agent for residents, on 15 July 2025 ([press release](https://granicus.com/press-release/granicus-launches-government-experience-agent-gxa-marking-a-new-era-of-ai-powered-public-service/)). | GovQA hosts the records portals lexflow's own answers already send people to (Charlottesville and DC, [docs/answers](../answers/)). GovConWire describes GovQA as also supporting agencies' compliance with state rules, which is where the statutory clocks lexflow models live. Legistar is already a lexflow source (`lexflow/sources/legistar.py`, Albemarle fixture). GXA answers the same resident questions. | **Open now:** the Legistar Web API reads any client's public items (`/v1/{Client}/matters`, events, votes; "queries replies are limited to 1000 responses"; "some clients require use of an API Token") ([webapi.legistar.com](https://webapi.legistar.com/Home/Examples)). **Wall:** other product APIs are reached through Granicus support; its API article sits behind the customer portal (HTTP 401). The product index lists no partner programme, app marketplace or developer portal. An outside assessment says API documentation is per acquired product and login-gated ([Supergood](https://supergood.ai/api-report-card/granicus), **search summary**). An older certified-partner programme and "Open Platform API" date from about 2010–11 (CMSWire, **search summary**). A Granicus plugin needs Granicus. |
| **CivicPlus** (incl. CivicEngage / Municipal Websites, Municode, NextRequest, SeeClickFix, CivicPlus Agent) | Website CMS vendor that also owns the largest local-code publisher, a records-request product and a 311 tool. Claims "13K+ local government customers" ([civicplus.com](https://www.civicplus.com/)). Bought Municode, which hosted the codes of "nearly 4,000 local governments" ([GovTech, 27 Aug 2021](https://www.govtech.com/biz/civicplus-acquires-70-year-old-ordinance-compiler-municode)). NextRequest: "over 70K active NextRequest users", "~1 million requests per year" ([CivicPlus](https://www.civicplus.com/foia-request-management/)). It came with CivicPlus's 2022 purchase of Optimere (Wikipedia, **search summary**). | The highest of any vendor. It runs the city's website, its ordinances and its records portal, and its Agent answers residents' questions from all three ([CivicPlus blog, 13 Feb 2026](https://www.civicplus.com/blog/ce/tech-tip-give-residents-faster-answers-with-an-integrated-always-on-civicplus-agent/)). | **Opening:** the Agent can be given "external websites" and documents as "additional knowledge sources" (same blog post). A city's web administrator could add its Lexipedia page; no plugin or vendor deal is needed. **Wall:** the Integration Hub connects CivicPlus products to each other; it names no third-party products and no marketplace, and "all links and integrations will be set up during implementation by our experts" ([Integration Hub](https://www.civicplus.com/tools/integrations-hub/)). The "CivicPlus Marketplace App" is a white-label resident mobile app, not an app store (**search summary**). Outside assessment: Web Central API keys come from CivicPlus Support; SeeClickFix 311 is the publicly documented exception ([Supergood, verified Sept 2026](https://supergood.ai/api-report-card/civicplus)). Municode text stays link-only (below). |
| **Tyler Technologies** (incl. EnerGov permitting, Data & Insights / Socrata, NIC, Odyssey courts) | Public-sector software, including courts, permitting, open data and payments. EnerGov: "More than 500 cities and counties in the U.S. and Canada rely on" it for permitting and licensing ([Tyler release, July 2021](https://s201.q4cdn.com/385562537/files/doc_news/2021/07/rl101103.pdf)). Socrata "was acquired by Tyler Technologies in 2018 and is now the Data and Insights division" ([dev.socrata.com](https://dev.socrata.com/)). Completed the NIC purchase on 21 April 2021; NIC served "more than 7,100" agencies and runs state portals ([SEC exhibit](https://www.sec.gov/Archives/edgar/data/860731/000086073121000020/exhibit991nicclosingpr.htm)). | Business licences and building permits (EnerGov), state business-registration portals (NIC), court e-filing (Odyssey File & Serve), and open data on permits. | **Open now:** every Data & Insights dataset has a SODA API, documented publicly, with app tokens ([dev.socrata.com](https://dev.socrata.com/)). Where a city publishes permit data there, lexflow can compare actual permit times with the law's deadlines. **Partner route:** the Tyler Platform Alliance is a tiered programme (Silver, Gold, Platinum, Technology) for organisations that build on its Application Platform and Data & Insights (**search summary**; the page answered 403). A 2026 job posting describes a planned API marketplace for "third-party partners" and AI agents (**search summary**; 403). **Court route:** the Suffolk LIT Lab's e-filing service is "Certified for Tyler eFile & Serve" ([assemblyline.suffolklitlab.org](https://assemblyline.suffolklitlab.org/)). **Wall:** product APIs are customer-gated per outside assessments (not verified). |
| **OpenGov** | Cloud software for budgeting, ERP, permitting and licensing, procurement, asset management, 311 and more; "Over 2,000 governments" ([opengov.com](https://opengov.com/)). | Permitting and licensing (starting a business), 311. | A public developer portal exists, with an "API Catalog" and "OpenGov Developer Terms" ([developer.opengov.com](https://developer.opengov.com/)). The catalogue is script-rendered and was not read; outside reviews say keys are issued per customer tenant (**search summary**). No marketplace found. |
| **Accela** (incl. Civic Platform, OpenCounter, CivicAI) | Permitting, planning, business and occupational licensing, short-term rental and cannabis regulation, environmental health; "900+" agencies and "50%+" of top US cities and counties ([accela.com](https://www.accela.com/)). | OpenCounter's "dynamic Permit Guides provide a clear, customized path through complex zoning rules, permit selection, and more" ([OpenCounter](https://www.accela.com/opencounter/)). That is the local-permit version of lexflow's how-do-I answer, without statute quotes. | **The most open vendor.** The developer portal offers account creation, "APIs and SDKs", "Staging environments and efficient approval processes" and "Free listing and promotion of apps in our Civic Storefront" ([developer.accela.com](https://developer.accela.com/login/login)); "civic app developers" register apps there ([Construct API](https://developer.accela.com/docs/construct-civicPlatformAndConstructApi.html)). **Wall:** an app needs an agency running Accela to switch it on, and OpenCounter competes with it. |
| **JustFOIA** | Records-request software; first request processed 21 July 2014; "500+" clients in 45 states; "an MCCi brand" ([our story](https://www.justfoia.com/our-company/the-justfoia-story/)). | Agency-side intake, deadlines, redaction and the public portal. | Named integrations: Laserfiche and Veritone Redact. No API, partner programme or marketplace on its site ([justfoia.com](https://justfoia.com/)). Closed; reachable only as a vendor conversation. |

**Does any of them have an open app marketplace or a documented third-party API?** Only Accela has something
close: self-serve developer accounts and a Civic Storefront. Tyler's open-data API (SODA) and Granicus's Legistar
API are public and read-only, which is useful for data but not a plugin channel. Everything else is
product-by-product and customer-gated. None documents a plugin directory for its website CMS.

## 2. What local governments actually run their websites on

The only dated, method-stated study found is by Promet Source, a Drupal vendor (so it has a stake), published
22 June 2024. It covered all 50 states and DC, the 1,000 largest counties and the 1,000 largest cities, towns and
villages by Census population, identified with Wappalyzer and checked by hand where Wappalyzer failed
([Promet Source](https://www.prometsource.com/blog/gov-cms-usage-study)).

| Share of websites | CivicPlus | Granicus | WordPress | Drupal | Revize | Unknown |
|---|---|---|---|---|---|---|
| 1,000 largest cities | 32.3% | 16.3% | 10.0% | 7.3% | – | 15.6% |
| 1,000 largest counties | 22.3% | 6.4% | 13.8% | 8.4% | 5.8% | 26.9% |
| All entities in the study | 26.6% | 11.1% | 11.8% | 8.3% | 5.0% | 21.8% |
| States (51) | – | – | 7.8% | 25.5% | – | 43.1% (SharePoint 9.8%, AEM 7.8%) |

What this means for plugins (arithmetic on the table, so estimates):

- **A Granicus + CivicPlus plugin would reach about 49% of large-city sites and 29% of large-county sites**, but
  only if both vendors agreed. Without them it reaches none.
- **A WordPress plugin plus a Drupal module reaches about 17% of large-city sites and 22% of large-county sites**
  with no one's permission. WordPress.org requires code that complies "with the GPL or a GPL-Compatible license",
  bans trialware, and allows software as a service when the service is documented in the readme
  ([plugin guidelines](https://developer.wordpress.org/plugins/wordpress-org/detailed-plugin-guidelines/)).
  Drupal.org requires "GNU General Public License, version 2 or later"
  ([licensing](https://www.drupal.org/about/licensing)). lexflow has chosen no licence yet (README).
- **The long tail is unmeasured, and much of it has no website.** In lexflow's own snapshot
  ([docs/status.json](../status.json), 10 October 2026), the best contact on record for 22,412 of the 38,640
  governments is a mailing address only; 16,224 have a website, and 4 have a records page or direct contact. That
  undercounts websites (the Census list plus Wikidata for a few states), but it means a website plugin, of any
  kind, cannot reach most townships and small towns. And of the websites on record, the contacts pilot found 43%
  (±14 points) of verifiable ones stale ([entities-contacts.md](../design/entities-contacts.md)).

## 3. Legal information and codes

| Organisation | What it is | Overlap with lexflow | Opening, or the wall |
|---|---|---|---|
| **LII (Cornell)** | Free legal information: US Code, CFR, a state-regulations collection, Wex plain-language entries. Wex passed 25 million pageviews in FY23; students revised or wrote about 5,000 entries since 2020 ([LII 2022–23 project updates](https://about.law.cornell.edu/contribute/annual-reports/2022-2023/project-updates)). | State regulations (where lexflow's "not found" answers point), plain-language definitions (lexflow's terms work). The state regulations collection is "made possible by Public.Resource.Org's multi-year Code Improvement Commission project", with Fastcase and Justia. | **Opening:** "Links to the collection or individual pages in it are welcome" ([terms](https://about.law.cornell.edu/terms/)), so lexflow can link every regulation pointer to LII. LII runs M.Eng. student projects on detecting definitions in rules (same report): the closest existing model for graduate work on legal text. **Wall:** LII-created content is CC BY-NC-SA 2.5; commercial redistribution needs permission ([documentation](https://www.law.cornell.edu/lii/terms/documentation)). No API is described. |
| **Justia** | Free case law, codes and opinion summaries, funded by an attorney directory and webhosting for law firms; founded 2003 ([Wikipedia](https://en.wikipedia.org/wiki/Justia)). | Hosts state codes; attorneys and the public use it. | Link target only. Its terms were not read (justia.com answered 403). It competes for the same search traffic as Lexipedia pages. |
| **FindLaw** | Consumer legal information and law-firm marketing. Thomson Reuters closed its sale to Internet Brands on 2 December 2024 ([Thomson Reuters](https://thomsonreuters.com/en/press-releases/2024/december/thomson-reuters-sells-findlaw-business-to-internet-brands)). Internet Brands lists Avvo, FindLaw and Martindale as "The US's Biggest and Best Legal Marketing Network" ([internetbrands.com](https://www.internetbrands.com/)). | Plain-language explainers of the same processes. | **Wall.** A lead-generation business; there is no route in, and none is needed beyond being a better-cited source. |
| **Nolo** | Self-help legal books and articles in the same Internet Brands legal group (parent MH Sub I, LLC per secondary sources; nolo.com answered 403). | Same as FindLaw: "how do I" explainers for consumers and small businesses. | **Wall,** for the same reason. Nolo's reach is a reminder that consumers already have explainers; what they lack is the statute's exact clock and a checked local contact. |
| **Public.Resource.Org** | Nonprofit "Making Government Information More Accessible"; "Bulk access to primary legal materials of the United States" and a State Building Codes collection on the Internet Archive ([public.resource.org](https://public.resource.org/)). Won *Georgia v. Public.Resource.Org* (2020). | Mission: the law belongs to the public. The Copyright Office will not register "legislative enactments, judicial decisions, administrative rulings, public ordinances" from any level of government ([Compendium §313.6(C)(2)](https://www.copyright.gov/comp3/chap300/ch300-copyrightable-authorship.pdf)). | **Ally in principle.** Bulk use of PRO's copies waits for counsel ([data-building-codes.md](../design/data-building-codes.md) Q4). |
| **Free Law Project / CourtListener** | Nonprofit; "Over 10 million opinions", the RECAP archive of PACER data, oral arguments, judges, alerts, "scalable APIs and database replication" ([free.law](https://www.free.law/projects/courtlistener/)). | lexflow already links 150 decisions that cite its sections (README). | **Open for research:** the API is open with an account, default 5 a minute and 125 a day, with a free EDU tier for academics ([credits-research.md](../design/credits-research.md)). Services beyond that are "offered according to commercial agreements and Free Law Project memberships" ([wiki](https://wiki.free.law/c/courtlistener/help/api)). Graduate students qualify for the academic tier. |
| **Harvard Library Innovation Lab** (Caselaw Access Project, Perma.cc) | CAP's limits "expired" in March 2024 and the data "can now be fully released without restriction on access or use"; search and API were wound down in favour of CourtListener ([LIL, 26 Mar 2024](https://lil.law.harvard.edu/blog/2024/03/26/transitions-for-the-caselaw-access-project/)). Perma.cc makes permanent copies of cited web pages ([perma.cc](https://perma.cc), **not opened**). | Historical case law; and link rot: lexflow's pilot found 43% of verifiable official websites stale. | **Opening:** CAP bulk data for older decisions. Perma.cc is the obvious tool for archiving the local official pages each answer cites; its terms and academic access were not checked. |
| **Municode** (CivicPlus) | "the largest codifier of legal documents for local governments in the United States" ([CivicPlus](https://www.civicplus.com/news/nn/civicplus-acquires-municode/)); about 4,000 governments (2021). | Every local ordinance lexflow's local layer wants to cite; the CivicPlus Agent reads it natively. | **Wall.** lexflow treats Municode as link-only ([credits-research.md](../design/credits-research.md)). The old terms URL returns 404 today; a search engine's cached copy of it says content is "for personal use only" and bars republishing and derivative works (**search summary**). No public API for the code corpus (outside assessment). |
| **ICC Code Solutions** (American Legal Publishing and General Code / eCode360) | The International Code Council bought American Legal Publishing (9 Feb 2023; "over 3,500 municipal clients", [ICC](https://www.iccsafe.org/about/periodicals-and-newsroom/american-legal-publishing-joins-the-international-code-councils-family-of-solutions)), and already owned General Code. They now trade as ICC Code Solutions, serving "more than 7,000 communities across 47 states, Canada, and more than a dozen tribal territories", and all online codes will move to eCode360 ([ICC Code Solutions](https://www.icccodesolutions.org/blog/general-code-and-american-legal-publishing-unite-as-icc-code-solutions/)). | Local ordinances and building-code adoptions. | **Wall.** The eCode360 API is "Available to General Code clients with an active eCode360 product" and "Licensed per municipality" ([ICC Code Connect](https://solutions.iccsafe.org/codeconnect)). The owner is the building-code rights holder that sued UpCodes. Robots rules shut out crawlers ([data-building-codes.md](../design/data-building-codes.md) §3.16). A client city could in principle license its own feed; that is a question for the city and counsel, not a lexflow route. |
| **UpCodes** | Commercial building-code platform: over five million code sections and 160,000 local amendments (2023), an AI Copilot that cites sections, paid tiers ([TechCrunch, 30 May 2023](https://techcrunch.com/2023/05/30/upcodes-copilot-series-a/)). | Building permits, a question lexflow has scoped ([questions.md](../questions.md)). | **Wall.** Its robots.txt disallows generic crawlers ([data-building-codes.md](../design/data-building-codes.md)). Proof that people pay for jurisdiction-fenced, cited answers; also proof that the building-code space is taken. |
| **National Zoning Atlas** | A project of Land Use Atlas, Inc., a 501(c)(3); a master list of 33,295 jurisdictions with zoning authority and about 102,000 districts logged, "upwards of 200 regulatory characteristics" each ([about](https://www.zoningatlas.org/about), [how](https://www.zoningatlas.org/how)). State and regional atlases are made by teams that include university units (University of Colorado Denver, Suffolk University Law School, University of North Texas, St. Anselm College), several of them supported by Mercatus Center grants ([Mercatus datasets](https://mercatus.org/state-and-regional-zoning-atlas-datasets)). | Zoning, the core question for city planners. | **Wall on data:** "Unless you have our express written permission, you may not use, host, store, reproduce, modify, license" its content; no commercial use; no scraping; no embedding ([terms](https://www.zoningatlas.org/terms) §1.3, §2.2). **Opening on method:** the state-team model (a university group takes one state, follows a shared method, publishes under the Atlas) is the clearest existing template for graduate students working on one niche at a time. |
| **Reporters Committee for Freedom of the Press — Open Government Guide** | Open records and open meetings law for all 50 states and DC, each "arranged according to a standard outline", written by volunteer attorneys; editions 1989 to 2019 ([guide](https://www.rcfp.org/open-government-guide/), [introduction](https://www.rcfp.org/introduction-to-the-open-government-guide/)). | Very high: it is the human-written reference for lexflow's records question. | **Opening:** read it as an independent check of each records model (does the model's clock match the guide's?) and link to it from Lexipedia. It invites corrections by email. **Wall:** "© Reporters Committee" with no reuse terms, and the last full edition is 2019; lexflow can be fresher on the statute but cannot replace attorney commentary. |
| **MuckRock** | Nonprofit that files and tracks requests in public; a 2017 analysis of 30,000+ requests found a 31-day median of agencies' average response times and a 43% success rate (cited in [lab-research.md](../design/lab-research.md)). API version 2 has an official Python wrapper covering jurisdictions, agencies, requests and files ([python-muckrock](https://python-muckrock.readthedocs.io/en/latest/)). | The requester side of lexflow's records question, with real outcomes. | **Opening:** its agency and jurisdiction data can test lexflow's statutory clocks against practice. **Wall:** muckrock.com refused automated reads (403); its API terms were not read; requests filed through it are public, which some users will not want. |
| **Ballotpedia** | Encyclopedia of US politics; a developer API for elections, officeholders, ballot measures and districts, with bulk downloads through a client portal ([developer docs](https://developer.ballotpedia.org/llms.txt)). | Low: officeholders, not procedures. lexflow stores role channels, never names. | **Wall:** commercial data access; terms not read. Little reason to integrate. |
| **Open States / Plural** | Free legislative data: legislators, bills and votes per session (the JSON files include full bill text), district shapes and a PostgreSQL dump; "Unless otherwise noted data is provided under a public domain dedication" ([bulk data](https://open.pluralpolicy.com/data/)). A v3 API with a free key (**search summary**). | Bills that would amend the sections lexflow models. | **Open now, and the best-licensed source on this list.** A bill watcher ("a bill before the legislature would change § 2.2-3704") turns a static model into something staff and attorneys revisit. |

## 4. Legal self-help and process tools

| Organisation | What it is | Overlap with lexflow | Opening, or the wall |
|---|---|---|---|
| **docassemble** | "a free, open-source expert system for guided interviews and document assembly"; code MIT, docs CC BY 3.0; produces PDF, RTF or DOCX, or submits applications ([docassemble.org](https://docassemble.org/)). | Guided interviews are a linear walk through a process that lexflow already models as steps and decision tables. Its date helpers have no business-day calendar ([lab-research.md](../design/lab-research.md) §2.1). | **Open.** A lexflow process could export a docassemble interview skeleton plus a statute-sourced deadline calculator. No permission is needed to build one; adoption needs a court or legal aid host. |
| **A2J Author** | Plain-language guided interviews, "co-developed by Chicago-Kent and the Center for Computer-Assisted Legal Instruction (CALI)", "available for free to interested courts, law schools, and legal service organizations" ([Chicago-Kent](https://kentlaw.iit.edu/institutes-centers/center-for-access-to-justice-and-technology/a2j-author)). | Its "path to the courthouse" is a process map for one person. | **Partial.** Free to law schools; whether its interview format can be generated from outside was not checked. |
| **LawHelp Interactive** (Scale Justice, formerly Pro Bono Net) | Pro Bono Net became Scale Justice on 16 March 2026. LawHelp Interactive is "the largest nonprofit online legal forms program in the United States", used by "more than a million Americans a year"; the organisation lists more than 300 partner organisations ([LawNext, 17 Mar 2026](https://www.lawnext.com/2026/03/pro-bono-net-the-a2j-technology-pioneer-rebrands-as-scale-justice-to-reflect-its-evolving-mission.html)). | Forms for the same civil processes; also the LawHelp.org state sites, which explain them. | **Partner route, not a technical one.** Forms are authored by partner organisations; lexflow's value to them would be the checked deadlines and next steps after filing. |
| **Suffolk LIT Lab — Document Assembly Line** | "Open-source tools for court forms, guided interviews, and e-filing", on docassemble; funded by a State Justice Institute grant and contracts with, among others, the Massachusetts Trial Court, the Alaska Court System, the Illinois Supreme Court Commission on Access to Justice, Illinois Legal Aid Online, Michigan Legal Help and Legal Action of Wisconsin; code MIT, documentation CC BY-NC-SA 4.0; e-filing "Certified for Tyler eFile & Serve" ([assemblyline.suffolklitlab.org](https://assemblyline.suffolklitlab.org/)). | Court forms and filing; it "Ends at filing" (lab-research). | **The strongest open door on this map.** It takes volunteers, trains new interview builders, and holds weekly community meetings and monthly workshops (same page). A lexflow contribution that adds the after-filing clock to one existing interview is a concrete, small, publishable piece of work. |
| **Code for America — Clear My Record** | Helps states "automatically clear eligible criminal records"; in 2022 it aimed to help "approximately 1 million people across 20 states" ([CfA, 1 Jun 2022](https://codeforamerica.org/news/google-invests-3m-in-code-for-americas-record-clearance-initiative/)). CfA ended its Brigade programme and fiscal sponsorship of local volunteer groups in 2023 ([CfA](https://codeforamerica.org/news/reflections-on-the-brigade-networks-next-chapter/)). | Record sealing is one of lexflow's AskBench questions (VA, DC, MD, TX, CA). | **Narrow.** CfA works with state governments on automatic clearance; there is no open contributor programme found. The former brigades are now independent local groups, reachable one by one. |
| **Clean Slate Initiative** | Advocacy and implementation support for automatic record sealing; "the 13 states, plus Washington D.C., that have passed Clean Slate laws", Illinois the 13th on 30 October 2025; a data dashboard of affected populations ([CSI, 29 Jan 2026](https://www.cleanslateinitiative.org/updates/states-of-clean-slate-end-of-year-wrap-up)). | Where clearance is not automatic, the person has to act; lexflow can model that process from the statute. | **Opening:** in the 37 states without a Clean Slate law, and for records such laws do not cover, a person still needs the steps and deadlines. **Wall:** an advocacy organisation, not a data platform; no reuse terms were checked. |
| **Court self-help portals** (e.g. California Courts Self-Help Guide, Illinois Court Help, Michigan Legal Help) | Judicial-branch guides by case type, form finders, and "Take the next step" tools ([selfhelp.courts.ca.gov](https://selfhelp.courts.ca.gov/)); the Self-Represented Litigation Network is hosted by the National Center for State Courts (**search summary**). | Court processes; lexflow's agency processes (records, licensing) and the steps before a court case sit beside them. | **Wall on embedding:** these are the courts' own content, written and owned by the judicial branch. The opening is as a reference that their content teams can check against, and a link destination. ilcourthelp.gov answered 403. |
| **Funding route: LSC Technology Initiative Grants** | Only LSC basic-field grantees may apply; "other entities are not eligible to apply, they are encouraged to participate as project partners" ([LSC](https://www.lsc.gov/grants/technology-initiative-grant-program/how-apply-technology-initiative-grant)). FY2026 offered $4.75 million (Federal Register notice, **search summary**). | Legal aid technology. | A university project can be the technical partner on a legal aid organisation's grant; it cannot apply alone. |

## 5. Process modelling and rules as code in government

| Organisation | What it is | Overlap with lexflow | Opening, or the wall |
|---|---|---|---|
| **OpenFisca** (and PolicyEngine US) | "The most widely adopted free and open-source engine to write rules as code"; showcased users include Barcelona's *Les meves ajudes*, the French Assemblée nationale's LexImpact and a Japanese benefits tool ([openfisca.org](https://openfisca.org/en/)). PolicyEngine US is "a microsimulation model of the US state and federal tax and benefit system", AGPL-3.0 ([GitHub](https://github.com/PolicyEngine/policyengine-us)). | Computation (eligibility, amounts), which lexflow's DMN tables touch for fees and thresholds. | **Complement, not overlap.** These compute benefits and taxes; lexflow models procedure. A lexflow step "apply for X" could link to a PolicyEngine eligibility check. AGPL matters if code is combined. |
| **Catala** | "a domain-specific language for deriving faithful-by-construction algorithms from legislative texts", "a research project from Inria", Apache-2.0; "The compiler is yet unstable" ([GitHub](https://github.com/CatalaLang/catala)). Proofs of concept with France's CNAF and DGFiP (Université Paris-Saclay, 2026, **search summary**). | lexflow already borrows Catala's two checks (no conflict, no empty point) for its decision tables ([bpc-480-decision.md](../design/bpc-480-decision.md)). | **Academic opening.** Translating one lexflow decision table into Catala and comparing results is a well-bounded formal-methods project. No US government use was found. |
| **OECD OPSI — rules as code** | *Cracking the Code: Rulemaking for humans and machines*, 12 October 2020, with six principles: "transparency, accountability, traceability, appropriateness and appealability, availability and interoperability, and security" ([OPSI](https://oecd-opsi.org/publications/cracking-the-code/)). | Traceability is what lexflow's word-for-word quotes deliver. | **Citation, not a programme.** OPSI's rules-as-code tag lists nothing after a February 2021 forum for officials ([tag page](https://oecd-opsi.org/tag/rules-as-code)). There is no active OECD effort to join. |
| **18F and Digital.gov** | 18F, GSA's in-house digital consultancy, was eliminated on 1 March 2025 ([Nextgov](https://www.nextgov.com/people/2025/03/gsa-eliminates-18f/403400/)). Digital.gov (GSA) still publishes the plain-language guides, "adapted from PlainLanguage.gov" ([Digital.gov](https://digital.gov/guides/plain-language)). | Plain language for Lexipedia pages and answers. | **Use the guidance; there is no federal partner team.** |
| **Georgetown Beeck Center — Digital Benefits Network, Rules as Code** | "a shared learning and exchange space for people working on public benefits eligibility and enrollment systems"; open to government, nonprofits, academia and companies; a Google Group, a Slack for government practitioners, roundtables, and the 2024 Policy2Code challenge with a Demo Day at BenCon 2024 ([Digital Government Hub](https://digitalgovernmenthub.org/get-involved/rules-as-code-interest-area/)). | The one live US rules-as-code community; its focus is benefits eligibility, not procedure. | **Opening:** academics may join; lexflow's procedure models (with deadlines and authority ladders) would be a new kind of exhibit there. **Wall:** the audience works on SNAP and Medicaid eligibility, so the fit has to be argued. |
| **BPMN and DMN in public administration: Germany's FIM** | FIM (Föderales Informationsmanagement), a product of the IT-Planungsrat, standardises services (XZuFi), data fields (XDatenfelder) and processes (XProzess) ([fimportal.de](https://www.fimportal.de/)). Its process concept (version 1.01, 31 July 2020) models every master process ("Stammprozess") in BPMN 2.0, restricted to a defined subset, and records its legal basis, which "kann bis auf Ebene der Paragraphen bzw. Abschnitte erfolgen" (can go down to the paragraph or section). The federal level publishes master information from federal law, which states and municipalities then adapt ([Fachkonzept Prozesse](https://www.fimportal.de/assets/prozesse_fachkonzept.pdf?version=2)). | Almost exactly lexflow's design: a higher-level process from statute, quoted to the section, with a local layer on top. | **Precedent to cite.** It shows the approach working at national scale where a national mandate drives it (the concept tracks each process's status under the OZG, Germany's Online Access Act). It is not a market for lexflow. |
| **BPMN and DMN elsewhere** | The Dutch tax administration's *Wetsanalyse* method records decision rules in its own language, RegelSpraak, rather than DMN (Eerste Kamer committee briefing, 15 April 2025, **search summary**). In the US, no state agency publishing BPMN process models was found (one search; not exhaustive). | – | **The wall for "BPMN as the product".** In the US, BPMN lives inside vendors' workflow engines, not in anything a buyer asks for by name. |

## 6. Routes, sorted by what they need

| Route | Whose permission | Reach | Status |
|---|---|---|---|
| Read public data: Legistar Web API, SODA open data, Open States, CourtListener (EDU tier), CAP bulk, MuckRock API | None beyond API keys | Data for models and checks | Open now; Legistar and CourtListener are already used |
| City adds a Lexipedia page to its CivicPlus Agent as an external knowledge source | One city's web administrator | That city's residents, through an assistant they already use | Possible now; untested; it needs a page an agent can read well |
| WordPress plugin and Drupal module that show a place's steps, deadlines and contacts | None (GPL-compatible licence required) | About 17% of large-city and 22% of large-county sites (estimate from §2) | Needs a lexflow licence and a public read-only data endpoint, neither of which exists |
| DokuWiki plugin on Lexipedia (the process lab) | lexflow's own wiki | Wiki readers | Already designed ([lab-research.md](../design/lab-research.md)) |
| docassemble / Document Assembly Line package | None to build; a court or legal aid host to deploy | Self-represented people in that host's state | Open; the DAL takes volunteers |
| Browser extension using `/api/lookup?url=` (README) | None | Anyone reading a government site | Needs a public server; today lexflow runs only on the user's machine |
| Accela Civic Storefront app | Accela listing, then each agency | Accela agencies | Open to apply; OpenCounter competes |
| Tyler Platform Alliance; Granicus or CivicPlus partnership | The vendor | Large, if agreed | Commercial negotiation; nothing public to start from |
| Legal aid grant (LSC TIG) as technical partner | An LSC grantee | That grantee's clients | Annual cycle; partner role only |
| Codes text (Municode, eCode360, American Legal), UpCodes, National Zoning Atlas data | The publisher, in writing | – | Walls; link only |

## 7. On plugins, free tools and a service model

- **A Granicus or CivicPlus plugin will not work as an independent product.** There is no marketplace to list in
  and no public API to build against. Both vendors are putting AI agents in front of their own content. The
  realistic role for lexflow there is a trusted source those agents can cite: pages and a machine-readable feed
  with the statute quote, the clock, the next step and a checked contact. Whether either vendor wants that is a
  question to ask them, not something this map can answer.
- **"Free plugins, with a service behind" is a sanctioned pattern on WordPress.org** (software as a service is
  allowed; trialware is not), and it is the norm in legal aid (free tools, grant-funded hosting, as the Document
  Assembly Line does with courts). It is not the norm with the big vendors, who sell.
- **The licences decide what can be sold.** The statute text is public domain, but lexflow's statute file is a
  CC BY-NC 4.0 compilation (open-us-law), LOCUS is CC BY-NC 4.0, LII's own content is CC BY-NC-SA, and the Zoning
  Atlas permits nothing without permission. A paid service built on lexflow's current data needs either a licence
  from Vaquill AI or a rebuild from the official publishers, whose URLs every open-us-law section already carries
  (README). Selling services rather than data (local procedure research, contact freshness checks, model review for
  a state FOIA office) avoids some of this; counsel should confirm.
- **What a service could plausibly sell (hypotheses, not tested demand):** contact freshness for county and city
  directories (the 43% stale finding is the pitch); a statute-checked deadline and calendar table to records
  vendors or state open-government offices; reviewed process models for a state's agencies. None of these has a
  confirmed buyer in the sources read.

## 8. Small niche goals this map suggests

Each one touches one organisation's open door and is small enough for a graduate student in a term.

1. **The records clock table.** For each state: the response deadline, its unit, what "business day" means, and the
   quote. Check it against the Reporters Committee outline and MuckRock's "by law" days, and report disagreements.
2. **One after-filing clock for the Document Assembly Line.** Take an existing interview in a DAL partner state and
   add the statutory deadline and the next step after filing, computed from lexflow's model.
3. **The CivicPlus Agent experiment.** With one willing city, ask the agent 20 records and licensing questions
   before and after adding the city's Lexipedia page as a knowledge source; score the answers against lexflow's
   references.
4. **Bill watch.** Use Open States to flag bills that amend any section a reviewed model quotes.
5. **Petition sealing where Clean Slate has not passed.** Model the petition process in three such states, using
   the AskBench reference format.
6. **Permits in practice.** In two or three cities that publish permit data on Socrata, compare issue times with
   the deadline in the law or ordinance.
7. **lexflow against FIM.** Map lexflow's IR onto FIM-BPMN and XProzess and write up where US statutes need what
   FIM lacks (deemed denials, business-day calendars). A methods paper with an international audience.
8. **One decision table in Catala.** Translate a reviewed DMN table and compare outputs over its whole domain.

## 9. Not verified

- Whether Granicus GXA can take an outside website as a source (only CivicPlus Agent was confirmed).
- Whether CivicPlus or Granicus website platforms let a city paste a third-party script or iframe; no vendor
  documentation was found.
- Tyler's Platform Alliance terms and the planned API marketplace (tylertech.com answered 403; only search
  summaries were read).
- OpenGov's API catalogue contents and whether keys need a customer tenant (script-rendered page).
- Municode's current terms (the known URL returns 404), and Justia's, MuckRock's, Ballotpedia's and Perma.cc's
  terms.
- Where OpenCounter came from, and the current SRLN membership terms (the search budget ran out).
- The State Justice Institute's national document-assembly hosting initiative (TLS error on sji.gov).
- CMS shares below the 1,000 largest cities and counties; no study was found.
- Any confirmed buyer for BPMN process models in US government.
