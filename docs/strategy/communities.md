# Communities: who lexflow could serve, where they gather, and how to approach them

Status: research, 2026-10-10. This work was read-only. Nothing was posted, no one was contacted and no wiki was
edited. Dates were checked against the sources linked here on 10 October 2026. **Unconfirmed** marks a date that
comes from a third-party listing or a past pattern. **Estimate** marks a figure or date that is a judgement. The
web-search budget for this run ran out near the end, so a few items stay unconfirmed and are marked that way.

Inputs: [README.md](../../README.md), [docs/questions.md](../questions.md) and the design notes in
[docs/design](../design), especially [entities-contacts.md](../design/entities-contacts.md),
[entities-sources.md](../design/entities-sources.md), [authority-wikidata.md](../design/authority-wikidata.md),
[authority-wikibase.md](../design/authority-wikibase.md) and [authority-ladders.md](../design/authority-ladders.md).

---

## 0. The short answer

* **Is this a hammer looking for a nail?** Partly. The nails are real. Every community below has the same problem:
  "what does the law make this office do, by when, and what happens if it doesn't?" But each community already has
  a tool that is good enough for it:
  * journalists use the Reporters Committee's Open Government Guide and MuckRock;
  * clerks use their state FOIA office's guidance and their vendor's request portal;
  * planners use Municode and the National Zoning Atlas;
  * legal aid uses its own self-help guides and the Assembly Line form tools.

  lexflow wins only where its three distinct traits matter:
  * **every step is tied to a word-for-word quote;**
  * **the same model shape is used in every state**, so states can be compared;
  * **the local layer is checked**: who to contact, and whether that contact still works.

  Find the communities where those traits save someone time this month, and start there.
* **Reach the public through intermediaries, not directly.** Clerks, law librarians, legal aid self-help teams,
  SBDC advisors and FOI coalitions answer the public's "how do I" questions every day. If one of them trusts a
  lexflow page, they can hand it to hundreds of people. A resident who finds it by search has no way to tell
  whether to trust it.
* **The strongest first fits, in order** (judgement):
  1. **Wikidata and Govdirectory, through contact freshness.** The pilot found 43% (±14 points) of verifiable
     official websites stale. Three of the 55 sampled now serve gambling or spam pages
     ([entities-contacts.md](../design/entities-contacts.md) D8). That is a data-quality gift that community
     wants, and it costs no legal risk.
  2. **Records-response clocks, for clerks and for requesters.** These are the same models seen from two sides.
     The deadlines are already in lexflow, and the gap between law and practice is documented:
     [MuckRock's Maine page](https://www.muckrock.com/place/united-states-of-america/maine/) shows a 5-day legal
     deadline against a 73-day average response, from requesters' own reports. That figure is from the indexed
     page; MuckRock blocked direct reading.
  3. **Record sealing, court debt and licence denial, for legal aid self-help teams.** There are 30 AskBench
     reference answers and 22 authority ladders to offer them.
  4. **"Start a business here" checklists, for small business advisors.** The seven-structure business models and
     the local licence step (BPOL in Virginia) are already built.
  5. **Process modelling and legal informatics researchers, through the benchmark.** AskBench, the Claude-vs-Claude
     ceilings and the published negative results are what that community rewards.
* **Planners are a later fit.** lexflow has no land-use review models yet. The National Zoning Atlas already owns
  zoning content, so lexflow should offer to complement it, not compete with it.
* **The biggest risk is posting AI-written text into communities that ban it.** These rules are in force now:
  * English Wikipedia's content guideline bans LLM-generated or LLM-rewritten article text (March 2026).
  * Govdirectory's contribution guide blocks contributors whose work "can be recognized as being AI generated".
  * In July 2026, an operator ran a Claude Code batch that created 109 Wikidata items about himself and his work.
    All 109 were mass-deleted, and the account was blocked as "Promotion-only account".

  Claude can plan, research and draft facts and tables. People must write the posts in their own words, under
  their own accounts, and say who they work for (§14).
* **Two blockers sit outside every community, and the owner has to fix them:**
  * **lexflow has no licence.** Civic tech volunteers and most university partners will not contribute to code
    without one.
  * **The statute and ordinance data is CC BY-NC.** That rules out vendor plugins and paid services built on it
    unless Vaquill AI licenses it. It also rules out putting it on Wikidata, which takes CC0 only.

---

## 1. What each community needs from lexflow, and what it already uses

| Community | The pain lexflow could address | lexflow asset that fits today | What they already use | What lexflow lacks for them |
|---|---|---|---|---|
| Wikidata / Govdirectory | Stale or missing official websites, contacts and agency items for US local government | The contacts freshness check and pilot; agency gaps found in [authority-wikidata.md](../design/authority-wikidata.md) §4.6 | Hand curation, QuickStatements, constraint reports | A person to make the edits by hand; US coverage beyond the pilot |
| Wikibase community | Worked examples of a domain Wikibase that is documented, queryable and federated | Lexipedia's Wikibase: 1,413 items and stable lexflow keys | Their own instances | A `Project:Copyrights` page and a hosting-policy review (§2.6) |
| Municipal clerks and records officers | Response clocks, what a response must contain, extensions, fee estimates, staff turnover | Records models (custodian steps, deadlines, deemed denial); deadline counting in the process lab; 82 catalogued forms | State FOIA office training, vendor portals (GovQA, NextRequest), their city attorney | A custodian-side view (question C1 is scoped, not built); local holiday calendars |
| Municipal attorneys | The same state-law questions every month, and comparisons across states | Quoted, cross-state models; question catalogue C2 to C5 | Westlaw/Lexis, IMLA listservs, state league counsel | Open meetings, procurement and conflict-of-interest models (scoped, not built) |
| City and county managers | Continuity when staff leave; residents stuck between city and state | Process maps; contacts freshness | Consultants, ICMA resources | Outcomes evidence (time saved) |
| Cities, counties and their leagues | "How do I" questions from residents; stale websites | Place pages (three places); freshness pilot | Vendor websites, 311 | More than three places with local answers |
| Planners | Review deadlines, notice rules, permits | Building-codes design ([data-building-codes.md](../design/data-building-codes.md)); LOCUS ordinance headings | National Zoning Atlas, Municode, OZFS | Land-use review models; zoning content (not lexflow's job) |
| Legal aid | Keeping self-help guides current in each state; triage; deadlines | AskBench references (record sealing, court debt, licence denial); authority ladders; forms | LawHelp guides, Assembly Line (docassemble), court self-help centres | Reviewed models beyond VA, DC, MD, TX and CA; plain-language layer |
| Law libraries | Pointing patrons to the governing section and the process | Quotes with official publisher URLs | Official codes, Westlaw/Lexis, research guides | Authenticated text: open-us-law is not the official code (§8.2) |
| Legal informatics and process modelling | Open benchmarks, statute-to-process datasets | AskBench, the 22 reference models, Claude-vs-Claude ceilings, negative results | Their own corpora | A data licence that allows redistribution |
| FOI requesters (journalists, coalitions, MuckRock users) | Deadlines, appeals, fees, constructive denial, the right custodian | Records models with deemed-denial routing; authority ladders; contacts | RCFP Open Government Guide, MuckRock guides, state coalition hotlines | Coverage of exemptions (B1 is scoped, not built) |
| Civic tech | Projects to volunteer on; open data | Open pipeline, Docker setup | Their own projects | **A licence for lexflow**; "good first issue" tasks |
| Small business advisors | Local start-up checklists; licences; entity choice; reentry entrepreneurs | Business models (seven structures); LOCUS local licence headings; reentry question A4 | SBA guides, state one-stop portals | Local licence models (only LOCUS matches today) |

---

## 2. Wikimedia: Wikidata, Govdirectory, the Wikibase community and the US affiliates

### 2.1 Who they are

* **Wikidata editors and WikiProjects.**
  * [WikiProject Govdirectory](https://www.wikidata.org/wiki/Wikidata:WikiProject_Govdirectory) curates public
    agencies on Wikidata for [govdirectory.org](https://www.govdirectory.org/).
    * It asks volunteers to add agencies "starting with your own country", with sources or external identifiers.
    * It marks dissolved bodies with P576 and P1366.
    * It rates each country from one to five stars.
    * Its United States entries list New York and North Carolina at the first level. lexflow's own reading of the
      US generator (federal, NY and NC) is in [entities-sources.md](../design/entities-sources.md).
    * It is recognised as a Digital Public Good and won the FSF's Award for Projects of Social Benefit for 2024
      ([about](https://www.govdirectory.org/about/)).
    * It covered about 13,000 agencies in nearly 40 countries in mid-2025, against an estimated 800,000 public
      agencies worldwide
      ([The Register, July 2025](https://www.theregister.com/2025/07/04/wikidata_foss_democracy/)).
  * [WikiProject Law](https://www.wikidata.org/wiki/Wikidata:WikiProject_Law) is broad and quiet.
    * It lists 15 participants.
    * It has no data model for statutes or sections.
    * It lists properties such as P92 (main regulatory text), P467, P7588 and P8550 (law identifier).
  * There is **no Wikidata WikiProject for US local government** that this survey could find.
    * The closest are Govdirectory and
      [WikiProject Country subdivision](https://www.wikidata.org/wiki/Wikidata:WikiProject_Country_subdivision).
      The latter has been unedited since August 2022. It models places, not offices.
    * [WikiProject every politician](https://www.wikidata.org/wiki/Wikidata:WikiProject_every_politician) models
      office-holders, who are people. lexflow models posts, not people
      ([authority-wikibase.md](../design/authority-wikibase.md) §4.5), so stay out of it.
* **The Wikibase community** (people who run their own Wikibase instances).
  * [Wikibase Community User Group](https://meta.wikimedia.org/wiki/Wikibase_Community_User_Group): a mailing list
    (`wikibaseug`), a Telegram group and a Mastodon account. In 2025 it met near the end of most months, nine
    meetings in all. No 2026 meetings were listed when checked.
  * [Wikibase Stakeholder Group](https://wbstakeholder.group/): institutions that commission open-source Wikibase
    extensions and documentation. It is a body for institutions, not a venue for newcomers.
  * Wikibase Cloud's own channels (a Telegram group and an announcement channel) are listed on
    [Meta's Wikibase page](https://meta.wikimedia.org/wiki/Wikibase).
* **US affiliates.**
  * [Wikimedia DC](https://meta.wikimedia.org/wiki/Grants:Programs/Wikimedia_Community_Fund/General_Support_Fund/Wikimedia_DC_Annual_Grant_2026)
    targets 20 to 30 events in 2026. It runs monthly North American video calls ("NARWHAL") with Wikimedia NYC. Its
    2026 plan says its Partnerships Manager will work more directly with the DC government. DC is one of lexflow's
    three answered places.
  * Others named in the affiliate lists include Wikimedia NYC and New England Wikimedians
    ([affiliates](https://meta.wikimedia.org/wiki/Wikimedia_movement_affiliates)).
  * Wiki Education runs paid Wikidata courses ([wikiedu.org](https://wikiedu.org/)). Those are a sanctioned way to
    train students.

### 2.2 Where they gather in the next 12 months

| When | What | Notes |
|---|---|---|
| Fridays, 15:00 CEST, weekly | Govdirectory Collab Hour (Jitsi) | Per its [events page](https://www.wikidata.org/wiki/Wikidata:WikiProject_Govdirectory/Events). The Americas-time slot is "on hold". |
| 17 to 23 Oct 2026 | Wikidata Query Service Days (online) | Covers the move from Blazegraph to QLever ([Wikidata:Events](https://www.wikidata.org/wiki/Wikidata:Events)). lexflow's contact step reads the Query Service, so this is worth attending. |
| October 2026 | Wikidata's 14th birthday events, worldwide | Listed on [Wikidata:Events](https://www.wikidata.org/wiki/Wikidata:Events) |
| Periodic | Wikidata office hours (Telegram) | No fixed schedule |
| Feb 2027 (**unconfirmed**) | Data Reuse Days | The 2025 edition ran online 18 to 27 Feb and took proposals from people who reuse Wikidata ([event page](https://www.wikidata.org/wiki/Event:Data_Reuse_Days_2025)). Govdirectory spoke at the 2022 and 2025 editions. No 2026 or 2027 edition was found. |
| Q3 2027 (likely August) | Wikimania 2027, Santiago de Chile, and online | Dates are not yet published ([Meta](https://meta.wikimedia.org/wiki/Wikimania_2027)). Govdirectory has shown posters at Wikimania every year since 2023. |
| Not set | WikiConference North America 2027 | Bids are open and no city is chosen ([Meta](https://meta.wikimedia.org/wiki/WikiConference_North_America/2027)). The 2026 edition (Edmonton, 24 to 27 Sept) had an "AI & Tech" track. Its call closed in May, and proposals were scored on impact, community interest and fit with the theme ([Meta](https://meta.wikimedia.org/wiki/WikiConference_North_America/2026)). Expect the 2027 call around spring 2027 (**estimate**). |
| Monthly | NARWHAL North American call (Wikimedia DC and NYC) | Per the WMDC 2026 grant page |

### 2.3 Policies that bind lexflow

| Topic | The rule | What it means for lexflow |
|---|---|---|
| Paid contributions | The [Terms of Use](https://foundation.wikimedia.org/wiki/Policy:Terms_of_Use) (in force since 7 June 2023): "You must disclose each and any employer, client, intended beneficiary and affiliation", on the user page, on the talk page or in the edit summary. A project may adopt its own policy instead. | A grad student paid to work on lexflow who edits Wikidata or Wikipedia for it should disclose the university and the project. Whether a stipend counts is a reading of "compensation", so disclose anyway (**judgement**). |
| Conflict of interest (English Wikipedia) | Editors with a COI are "strongly discouraged from editing affected articles directly". They propose changes with `{{edit COI}}`. Citing your own work is allowed "within reason", but adding many references to your own work "is considered to be a form of spamming" ([WP:COI](https://en.wikipedia.org/wiki/Wikipedia:Conflict_of_interest)). | Never add Lexipedia or lexflow links or citations to Wikipedia articles yourself. If they help, propose them on the talk page and let others decide. |
| External links | "You should avoid linking to a site that you own, maintain, or represent." Open wikis are not linked "except those with a substantial history of stability and a substantial number of editors" ([WP:EL](https://en.wikipedia.org/wiki/Wikipedia:External_links), ELNO 12). | Lexipedia is a new, open wiki with one editor. Links to it from Wikipedia will be removed. Do not try. |
| AI-written content (English Wikipedia) | "The use of large language models (LLMs) to generate or rewrite article content is strictly prohibited." The exceptions are copyediting your own writing and translation. Persistent misuse can lead to a block ([guideline](https://en.wikipedia.org/wiki/Wikipedia:Writing_articles_with_large_language_models), March 2026 RfC). | No Claude-drafted article text, ever. |
| AI across all projects | A global RfC opened 23 April 2026 proposes disclosing AI-generated content and comments, human review before publishing, and full responsibility for the editor ([Meta RfC](https://meta.wikimedia.org/wiki/Requests_for_comment/Artificial_intelligence_policy)). Its outcome was not visible when checked. | Plan as if disclosure and human review are required everywhere. |
| AI on Govdirectory | Its contribution guide: "If your comments, code or other forms of contributions can be recognized as being AI generated you will be blocked", and the contribution is marked as spam ([CONTRIBUTING.md](https://raw.githubusercontent.com/govdirectory/website/main/CONTRIBUTING.md)). | Issues, talk posts and GitHub comments to Govdirectory are written by a person. This is already decision D11 in [entities-contacts.md](../design/entities-contacts.md). |
| Bots (Wikidata) | A bot needs a request at [Requests for permissions/Bot](https://www.wikidata.org/wiki/Wikidata:Requests_for_permissions/Bot) and a test run of 50 to 250 edits. It must respect maxlag and be able to cap its edits per minute. New statements need sources ([Wikidata:Bots](https://www.wikidata.org/wiki/Wikidata:Bots)). Approvals are scoped to a subject area and properties. In a June 2026 request, one reviewer opposed an operator over "high reliance on AI/LLMs". | lexflow should not run a bot on Wikidata. The design already exports QuickStatements for a person to review and paste, in batches of 20 or fewer. Keep it that way. |
| Mass edits (Wikidata) | The [Mass-editing policy](https://www.wikidata.org/wiki/Wikidata:Mass-editing_policy) covers edits that are not reviewed one by one, with any tool. Controversial batches are first described at Mass editing proposals, with the WikiProjects notified, and go ahead if there are "no major disagreements after 1 week". Batches must be revertable (EditGroups). Batches with "more than 100 or 5% problematic edits" can be quickly reverted. An autoconfirmed account is the minimum. | Even hand-reviewed QuickStatements batches should be small and announced on the Govdirectory talk page first. |
| Notability (Wikidata) | An item needs a sitelink, a "clearly identifiable conceptual or material entity" described by serious public references, or a structural need. Chapters and other subparts are notable only if other items use them. Data outside the guidelines "may fit better" on Wikibase Cloud ([Wikidata:Notability](https://www.wikidata.org/wiki/Wikidata:Notability)). | Agencies and offices are welcome on Wikidata. Lexflow's 496 statute sections and 275 process steps belong on Lexipedia's Wikibase. Uploading them to Wikidata would probably be contested (**judgement**). |
| Self-promotion in practice | In July 2026, 109 items about one person, all sourced and all passing constraints, were created in a semi-automated run with an AI coding agent. They were mass-deleted in about two minutes, and the account was blocked as "Promotion-only account" ([the operator's own account](https://dev.to/shimo4228/banned-from-wikidata-overnight-i-believed-every-edit-was-compliant-but-all-109-items-were-57nl)). The [Autobiography](https://www.wikidata.org/wiki/Wikidata:Autobiography) page allows editing an item about yourself, but not creating one unless it is notable. | Moderators judge an account's whole pattern. Never create items about lexflow, Lexipedia, the university's people or their papers. |
| Trademarks | The Foundation's [trademark policy](https://foundation.wikimedia.org/wiki/Policy:Trademark_policy) says "you cannot use a trademark as a generic term". Its example is "a wikipedia for motorcycles". It also lists a made-up "-pedia" site that copies Wikipedia's look as a prohibited case. | "Lexipedia" as a name is not barred. Never describe it as "a Wikipedia for law", never copy Wikipedia's look, and add a one-line "not affiliated with the Wikimedia Foundation" note. |
| Licence | Wikidata takes CC0 only. Wikibase Cloud's hosting policy needs the structured data to be CC0 too ([authority-wikibase.md](../design/authority-wikibase.md) §2.7). | Contribute only facts from official websites and the Census. Never contribute anything derived from open-us-law or LOCUS (CC BY-NC) without counsel. |

### 2.4 What makes a newcomer project welcome

These points come from the pages above, plus the evidence of what got one newcomer blocked.

1. **Start with their priorities, not yours.**
   * Govdirectory wants complete, sourced agency lists. It does not want "empty" countries.
   * Its US first level covers NY and NC only. Virginia's first-level agencies would be a clear gift.
   * lexflow already knows of 15 bodies its processes name that have no Wikidata item, including Virginia DPOR, the
     DC Office of Administrative Hearings and Maryland's Central Collection Unit
     ([entities-contacts.md](../design/entities-contacts.md) §4).
2. **Ask first, in the open.** Use the project's talk page or Project chat. The bot policy says to discuss "on the
   project chat" when unsure.
3. **Edit by hand, under personal accounts, and disclose.** Keep batches small and send them with references.
4. **Show reuse.** Data Reuse Days exists to show what people build on Wikidata. A talk on "how lexflow checks
   whether government websites still work, and what it found" fits that format.
5. **Turn up.** Go to the Friday Govdirectory hour, the Wikibase user group call and NARWHAL. Listen before you
   present.

### 2.5 Credible first contact

A person on the team, writing in their own words, posts on
[Wikidata talk:WikiProject Govdirectory](https://www.wikidata.org/wiki/Wikidata_talk:WikiProject_Govdirectory). The
post covers four things:

* who they are and their university affiliation;
* the method and headline result of the freshness pilot (43% ±14 of verifiable official websites stale; three now
  spam), linked to the method in [entities-contacts.md](../design/entities-contacts.md) §3;
* an offer to fix, by hand and with references, the websites of one small set of Virginia localities;
* one question: would they want this kind of check run for the US entries?

No links to Lexipedia, no project pitch.

### 2.6 The Wikibase community: one task comes before any outreach

Lexipedia's Wikibase is probably now a **temporary instance**.

* **The policy.** The policy text and the Q2 2026 update say that all instances become temporary by default from
  the end of September 2026. Managers then have three months to submit them for review
  ([authority-wikibase.md](../design/authority-wikibase.md) §2.7;
  [draft policy](https://www.mediawiki.org/wiki/Wikibase/Wikibase.cloud/Hosting_policy_draft_v0.1)). By that
  timeline, the submission would be due around the end of December 2026 (**estimate**).
* **What it needs:**
  * a `Project:Copyrights` page, which is missing;
  * CC0 structured data;
  * a stated purpose.
* **What counts in its favour.** Being a "staging ground" for data meant for Wikidata.
* **Who does it.** The owner. Without the review, there is nothing to show the Wikibase community.

After that, a short write-up on the user group mailing list is a natural first contact. It would say how
Lexipedia models processes, steps, posts and statute sections, and that it holds posts, not people.

### 2.7 Questions to ask Wikimedians

* For US agencies, which gaps hurt Govdirectory most: missing items, missing websites or stale websites?
* Would you accept references to official pages that a script checked, if a person applied each edit?
* How should a domain Wikibase link back to Wikidata so that it counts as a staging ground and not as a fork?
* Is there interest in a WikiProject, or a Govdirectory subpage, for US local government (counties, cities,
  towns)?

### 2.8 What will not work

* Driving traffic from Wikipedia to Lexipedia.
* Bulk-creating statute or process items on Wikidata.
* AI-drafted talk posts.
* Presenting at Wikimania or WikiConference North America before there is a community contribution to report.

---

## 3. Municipal clerks and records officers

### 3.1 Who they are

* **Clerks.** The [International Institute of Municipal Clerks](https://www.iimc.com/) (IIMC) runs certification
  (CMC, MMC) and has regions and state associations.
  * Full membership is for clerks who carry listed duties, records management among them.
  * Its [Records Management Committee](https://www.iimc.com/467/Records-Management-Committee) recommends
    conference sessions, writes best-practice articles and reviews or creates IIMC Technical Bulletins.
  * In Virginia, the Virginia Municipal Clerks Association runs IIMC-approved institutes with
    [VCU Continuing and Professional Education](https://ocpe.vcu.edu/vmca/first-year.html) each October. The 2025
    institutes ran 8 and 9 October in Richmond. The 2026 dates were not found.
* **Records administrators.** [NAGARA](https://www.nagara.org/) is the government records administrators'
  association. Its 2026 conference was in Philadelphia, 21 to 24 July. It also runs spring and fall online forums
  and monthly webinars. No 2027 date was found.
* **The state FOIA office.** In Virginia, the
  [FOIA Council](https://foiacouncil.dls.virginia.gov/training.htm) is the state's adviser and trainer. Virginia
  Code [§ 30-179](https://law.lis.virginia.gov/vacode/title30/chapter21/section30-179/) directs it to hold training
  for public bodies. Its 2026 webinars on records and meetings ran January to May. Clerks trust it more than any
  outside tool.

### 3.2 The pain lexflow could address

* The response clock: Virginia's five working days, the extension, holidays and closures.
* What a lawful response must contain.
* Fee estimates.
* Training new deputies.

These are question C1 in [docs/questions.md](../questions.md). The records models already hold the deadlines and
the deemed-denial routing. The process lab already counts working days.

### 3.3 Where they gather

| When | What | Notes |
|---|---|---|
| 22 Oct 2026 | IIMC Records Management Committee Roundtable, "Records Horror Stories" | Listed on the [iimc.com](https://www.iimc.com/) home page on 10 Oct 2026; the year is inferred |
| October each year | VMCA institutes (VCU) | 2026 dates not found |
| 9 to 12 May 2027 | IIMC Annual Conference, Fort Worth, Texas | From an IIMC-hosted [Region VIII newsletter](https://www.iimc.com/DocumentCenter/View/8483/Region-VIII-Newsletter), which also lists Bellevue, WA for 21 to 24 May 2028. No call for education sessions was found. |
| Monthly | NAGARA webinars | [nagara.org](https://www.nagara.org/) |

### 3.4 Norms

* Clerks are risk-averse. They take legal interpretation from their city or county attorney and from the state FOIA
  office, not from a website.
* IIMC is a professional body. Vendors exhibit and sponsor; they do not teach. The education sessions come from
  clerks.
* Many clerks work inside a vendor's portal:
  * Granicus bought GovQA, a records-request system, in 2021
    ([GovConWire](https://govconwire.com/2021/08/granicus-expands-public-records-management-capabilities-with-govqa-buy)).
  * CivicPlus owns NextRequest, through its 2022 purchase of Optimere, and Municode
    ([Wikipedia](https://en.wikipedia.org/wiki/CivicPlus)).
  * Ask which one each clerk uses before any talk of plugins (§12).

### 3.5 Credible first contact

Ask two or three Virginia clerks, Charlottesville's first, to spend 20 minutes on one printed page. The page is
Virginia's records response steps with:

* the quoted Code words;
* the five-day clock worked through on a real calendar;
* a link to the FOIA Council's own guidance.

The ask: "what is wrong or missing?" Do not ask them to adopt anything. Their corrections are the product.

### 3.6 Questions to ask clerks

* Which part of a request takes the most time: finding the record, redacting, estimating the fee or writing the
  response?
* When the clock is unclear (holidays, closures, extensions), who do you ask?
* What do you log requests in: GovQA, NextRequest, JustFOIA, email or a spreadsheet?
* Which questions from the public are really state-law questions you answer again and again?
* Would you hand a checklist that quotes the Code to a new deputy clerk? What would stop you trusting it?

### 3.7 What will not work

* A new website clerks have to visit.
* Anything that looks like legal advice to the public body.
* An exhibitor booth before a single clerk has reviewed the models.

---

## 4. Municipal attorneys (IMLA and state associations)

### 4.1 Who they are

* **IMLA.** Its members are local governments, represented by their chief legal officer. Deputies and assistants
  join under that membership at no charge, and towns under 2,500 people can use "IMLA Lite"
  ([membership](https://imla.org/become-a-member/)). Its working groups use members-only listservs.
* **State associations.** In Virginia, the Local Government Attorneys of Virginia hold spring and fall conferences.
  The spring 2026 conference ran 9 to 11 April in Portsmouth.

### 4.2 The pain lexflow could address

* The same state-law questions every month: open meetings and closed sessions, purchase thresholds, land-use review
  deadlines, conflicts of interest (C2 to C5 in [docs/questions.md](../questions.md)).
* Comparing states, for amicus work or for drafting.

lexflow's quoted, same-shape models across 11 states are the fit. Only the records and business models are built
today.

### 4.3 Where they gather

| When | What | Notes |
|---|---|---|
| 4 to 6 Nov 2026 | IMLA International Comparative Law Program, Montréal | Low fit |
| 16 to 19 Apr 2027 | IMLA Mid-Year Seminar, Washington DC (Omni Shoreham) | [IMLA conferences](https://imla.org/events/category/conference/list/). No call for speakers was found ("Become a Speaker" link only). |
| Spring and fall 2027 | Local Government Attorneys of Virginia | Dates not found |
| 14 to 18 Oct 2027 | IMLA 92nd Annual Conference, Denver | [IMLA conferences](https://imla.org/events/category/conference/list/) |

### 4.4 Norms

* Continuing legal education (CLE) is the currency.
* The listservs are for members.
* Attorneys carry a duty of competence, and many now distrust AI tools after cases with invented citations.
* They will check every quote. Show only Claude-reviewed models. The local pipeline's AskBench composite of 0.40
  would end the conversation.

### 4.5 Credible first contact

A comparison on one narrow question:

* the records response deadline and what happens when it passes (deemed denial, appeal, fees), across the 11
  reviewed states;
* every cell quoted and linked to the official publisher;
* the known gaps listed (AR, CO, GA, MS and TN have no statute file; HI, NE and PA records law is not in the files).

Offer it to a Virginia local government attorney for a CLE session they would co-present. They present; lexflow
supplies the table.

### 4.6 Questions to ask

* Which state-law questions do department heads send you every month?
* Would you cite a table that quotes the statute but is not the official text? What would you check first?
* Is a cross-state comparison useful to you, or only your own state?

### 4.7 What will not work

* Unreviewed (selector-built) models.
* "AI answers your legal question" framing.
* Asking to join members-only listservs.

---

## 5. City and county managers (ICMA)

### 5.1 Who they are, and the pain

[ICMA](https://icma.org/) is the professional body for chief administrative officers. The pain lexflow could
address:

* processes that break when one person leaves;
* residents stuck between city and state;
* showing that a state mandate is met.

### 5.2 Where they gather

* **17 to 21 Oct 2026: ICMA Annual Conference, Long Beach.** Too soon to present; attending is possible
  ([event](https://icma.org/events/2026-icma-annual-conference)).
* **Open now: the call for presentations for ICMA 2027** (Philadelphia, **25 to 29 Sept 2027**). It accepts
  proposals from **1 October to 13 November 2026**, and "no proposals will be accepted outside of these dates"
  ([call](https://conference.icma.org/call-for-presentations/)).
  * Formats include a **6 minute 40 second Lightning Talk** and a 30-minute "Quick Bite".
  * Presentations are "not meant to be sales pitches". Presenters avoid trade names, company names and product
    names.
* **ICMA's Academic Symposium** at the annual conference takes a separate call. The 2026 call had a 15 May 2026
  priority deadline, so expect a spring 2027 call for the 2027 symposium (**estimate**,
  [2026 call](https://www.icma.org/articles/article/2026-icma-academic-symposium-call-presentations)). This is the
  natural home for a university team.

### 5.3 Credible first contact, and questions

**First contact.** A Lightning Talk proposal, co-presented with a practitioner, on "mapping what state law requires
of your staff, step by step, with the words of the law". No product name, no URL in the abstract.

**Questions to ask managers:**

* Which processes break when one staff member leaves?
* Where do residents get stuck between your city and the state?
* What would you need to see to believe a process map saved staff time?

### 5.4 What will not work

* A product demo in an education session.
* Claims of savings with no measured case.

---

## 6. Cities, counties and their leagues (NLC, NACo, VML, VACo)

### 6.1 Who they are, and the pain

| Body | Who it is | Next dates |
|---|---|---|
| [NLC](https://www.nlc.org/events/city-summit-2026/) | Cities | City Summit **19 to 21 Nov 2026**, Nashville (pre-conference 18 Nov); 2027 in Houston, 17 to 20 Nov |
| [NACo](https://www.naco.org/event/2027-naco-legislative-conference) | Counties | Legislative Conference **20 to 23 Feb 2027**, Washington Hilton, with the **NACo Technology Innovation Forum** as a pre-conference on **19 Feb**; early registration ends 1 Dec. Annual Conference 2027: Chatham County, GA, dates not confirmed ([NACo events](https://www.naco.org/page/conferences)). |
| [Virginia Municipal League](https://www.vml.org/Opportunities/VML-Events) | Virginia cities and towns | Annual Conference every October; the 2026 site was not confirmed |
| [VACo](https://www.vaco.org/education-and-events/annual-conference/) | Virginia counties | 92nd Annual Conference **7 to 10 Nov 2026**, Omni Homestead |

The pain lexflow could address:

* residents' "how do I" questions;
* small towns with no records or licensing staff;
* stale official websites.

Three of the pilot's 55 sampled websites now serve gambling or spam pages
([entities-contacts.md](../design/entities-contacts.md) D8). That is a concrete reputational risk for those
governments.

### 6.2 Norms

* These are big-tent bodies run for elected officials.
* Vendors exhibit and sponsor. The sessions come from members and partners.
* The CivicPlus events page shows its team exhibiting at state municipal and county association meetings
  ([CivicPlus events](https://www.civicplus.com/events/)), so the vendors are already in these rooms.

### 6.3 Credible first contact, and questions

**First contact.** After a Virginia pilot with three to five localities, offer VML or VACo staff a one-page
"website health" finding for their members. The page gives the share of members' listed websites that no longer
work, how it was checked, and a free list for each member. This is a service to the league, not a pitch.

**Questions to ask:**

* Which questions do residents ask your members that are really state law?
* Would members want to know when their listed website or records page breaks?
* Which software do members use for records requests and licences?

### 6.4 What will not work

* Starting at a national meeting.
* Starting before any locality has used the tool.

---

## 7. Planners

### 7.1 Who they are

* **The [American Planning Association](https://www.planning.org/) and its state chapters.**
  * APA Virginia's 2026 conference ran 26 to 29 July in Danville
    ([chapter](https://virginia.planning.org/conferences-and-meetings)).
  * APA's Technology Division runs its webinars through APA's Knowledge Center
    ([division](https://tech.planning.org/conferences-and-meetings)).
* **The [National Zoning Atlas](https://www.zoningatlas.org/about).**
  * It is a project of Land Use Atlas, Inc., a 501(c)(3).
  * Over 500 people have contributed.
  * It reads codes by hand, about 200 characteristics per zoning district, under a published method and a DOI.
  * State and regional atlases are built by university and policy teams. Mercatus's list includes the University
    of Colorado Denver and Suffolk University Law School ([list](https://www.mercatus.org/state-and-regional-zoning-atlas-datasets)).
* **The [Open Zoning Feed Specification](https://research.gsd.harvard.edu/vibelab/2025/08/19/open-zoning-feed-specification-ozfs)**
  (OZFS). An open schema for parcel-level zoning data, modelled on GTFS, from Harvard GSD and Cornell Tech's Urban
  Tech Hub.
* **Planning schools and ACSP.** ACSP's 2026 conference ran 8 to 10 October in Pittsburgh. Its abstracts were due
  31 March 2026 ([ACSP timeline](https://www.acsp.org/page/2026Conf_Timeline)).

### 7.2 The pain lexflow could address

* Review deadlines that bind the locality, and what happens if they are missed (C4).
* Public-notice rules.
* Building permits (A1).

**None of these is built.** lexflow cannot extract zoning district standards, and it should not try.

### 7.3 Where they gather

| When | What | Notes |
|---|---|---|
| 15 to 18 May 2027 | APA National Planning Conference (NPC27), Houston | Session proposals closed **26 Aug 2026**. Only APA members may submit. There are eight tracks, Technology among them. Notifications come in Feb 2027. Source: APA's 11 Aug 2026 [news release](https://planning.org/blog/9333375/apa-invites-planners-to-shape-national-planning-conference-npc27-in-houston/); planning.org was under maintenance when checked, so this comes from the indexed copy. |
| Summer 2027 | APA Virginia chapter conference | Date not announced |
| ~March 2027 | ACSP 2027 abstract deadline | **Estimate**, from 2026's 31 March |

### 7.4 Norms

* Planners earn AICP certification-maintenance credits.
* They work from evidence and from GIS.
* The NZA's method is slow, careful reading by hand, which planners respect. A tool that claims to automate that
  reading will meet scepticism.

### 7.5 Credible first contact, and questions

**First contact.** Build one Virginia model first: the locality's review clock for a subdivision or site plan,
quoted, with deemed approval if the statute has it. Offer it to a planning school studio or a regional atlas team
as a "procedure layer" beside the zoning layer. Make it a student project (§13).

**Questions to ask:**

* Which review deadline do applicants and staff dispute most?
* Would a map of deemed-approval rules by state help your practice or your advocacy?
* Could process steps sit beside zoning data in OZFS or an atlas, or do they belong elsewhere?

### 7.6 What will not work

* Pitching lexflow as a zoning tool.
* Presenting at NPC27 (the call is closed).
* Presenting before a land-use model exists.

---

## 8. Attorneys: legal aid, law libraries and legal informatics

### 8.1 Legal aid

**Who they are.** Legal Services Corporation (LSC) grantees and the technology community around them.

* **Technology Initiative Grants (TIG).** Only current LSC Basic Field grantees may apply. Other organisations "are
  encouraged to participate as project partners" ([how to apply](https://lsc.gov/grants/technology-initiative-grant-program/how-apply-technology-initiative-grant)).
  * The 2026 cycle was announced 23 Feb 2026. Pre-applications were due 10 April and full applications 30 June.
  * A new 2026 **TIG Planning Grant** funds up to $75,000 of planning.
  * Expect a similar calendar in 2027 (**estimate**).
* **[LSNTAP](https://www.lsntap.org/).** Runs fifteen email lists for legal services technologists. The main list
  had over 800 subscribers in 2020 ([LSC notice](https://lsc.gov/sites/default/files/attach/2020/08/LSC_TIG_LSNTAP_LOI_Notice_August_2020.pdf)).
* **[Suffolk LIT Lab](https://suffolklitlab.org/).** Its Document Assembly Line is open-source docassemble form
  tooling, supported by volunteers, courts and legal aid, with meetings, a forum and training. A 2026 State Justice
  Institute project funds national hosting and e-filing
  ([SJI](https://www.sji.gov/national-document-assembly-hosting-and-e-filing-initiative/)).
* **[Stanford Legal Design Lab](https://justiceinnovation.law.stanford.edu/projects/ai-access-to-justice).**
  * Its "AI for Legal Help" class, now in its fourth round, pairs student teams with legal aid groups and courts.
    It "welcomes partners".
  * It co-runs the AIDA2J workshop at ICAIL and JURIX.

**The pain lexflow could address.**

* Keeping self-help content current in each state.
* Deadlines and waiting periods in record sealing.
* Court-debt options.
* Licence denial after a conviction.

lexflow has Claude-written, adversarially reviewed references for all three of those questions, in VA, DC, MD, TX
and CA. It also has 22 authority ladders (143 rungs) for "where to go when a step goes wrong" and 82 catalogued
official forms.

**Where they gather.**

* **3 to 5 Feb 2027: LSC Innovations in Technology Conference (ITC27)**, Hilton New Orleans Riverside
  ([ITC27](https://www.lsc.gov/itc27)).
  * 700 to 800 attendees are expected: legal aid advocates, technologists, court self-help staff, law faculty,
    students and law librarians.
  * Attendee registration is $800 until 30 Oct 2026, then $900.
  * No call for sessions was posted when checked. In 2025, LSC took proposals for workshops, demos and tech talks.

**Norms.**

* Client-centred, plain language.
* Strong caution about the unauthorised practice of law.
* A preference for open source.
* A growing culture of evaluation: the Stanford lab builds evaluation frameworks for legal-help AI.

**Credible first contact.** Offer a legal aid self-help team in one of the five states the record-sealing
reference for that state. Include:

* the quotes;
* the waiting periods as typed slots;
* the escalation ladder;
* lexflow's own coverage call ("partly in the code" and where the rest lives).

Ask them to mark it up. A second route: map one Assembly Line interview to its statute steps, as a contribution to
their project.

**Questions to ask.**

* Which of your self-help guides goes out of date fastest when the law changes?
* What would let you trust a statute quote you did not pull yourself?
* Do you need process maps, checklists or form interviews?
* Which TIG grantee near you would want a university partner?

**What will not work.**

* Direct-to-client answers.
* The local pipeline's answers.
* Applying for a TIG yourself (not eligible).

### 8.2 Law libraries

**Who they are.** [AALL](https://www.aallnet.org/).

* Its [Government Law Libraries SIS](https://www.aallnet.org/gllsis/about-us/) has more than 300 members in
  federal, state, court and county law libraries. It has a "Best A2J Practices" committee.
* The Legal Information Services to the Public SIS is still listed among AALL's
  [sections](https://www.aallnet.org/community/special-interest-sections/).
* Public law librarians answer the public's "which law, which form" questions every day.

**Where they gather.**

* **17 to 20 Jul 2027: AALL Annual Meeting, Philadelphia**
  ([IALL calendar](https://iall.org/?p=12383), linking AALL's future-meetings page).
* AALL's call for program proposals "opens each fall"
  ([FAQ](https://www.aallnet.org/conference/resources/proposing-a-program/programproposalfaq/)). Proposals for the
  2026 meeting were due 22 Oct 2025 ([AALL education update](https://www.aallnet.org/wp-content/uploads/2025/09/AALL-Education-Update_October-2025.pdf)),
  so the 2027 deadline may be **this month** (**unconfirmed**; check now).
* Proposals from non-members are "encouraged". The first review is anonymised and scored on a rubric
  ([overview](https://www.aallnet.org/conference/resources/proposing-a-program/program-proposal-overview/)).

**Norms.** Authentication and official text matter. Several states have enacted the Uniform Electronic Legal
Material Act; Arkansas's took effect 1 January 2026 ([Justia mirror of the Arkansas code](https://law.justia.com/codes/arkansas/title-25/chapter-46/)).
**open-us-law is not the official code.** Librarians will ask about this first. The answer is that every quote
links to the government publisher's URL and states the release it was checked against.

**Credible first contact.** A one-page "how lexflow checks every quote, and where it has gaps" note. It lists the
five missing states, Hawaii, Nebraska and Pennsylvania records, and North Dakota's wrong text. Librarians reward
candour about coverage.

**Local fit.** In Charlottesville, [cvillepedia](https://www.cvillepedia.org/Main_Page), a local wiki of 6,945
articles under CC BY-SA 3.0, has been run by the Jefferson-Madison Regional Library since 2023. A public library
running a local wiki is the most natural local partner for Lexipedia's Charlottesville pages. Mind the licence
mismatch with CC BY-NC data.

**Questions to ask.**

* What do patrons ask that a quoted process map would answer?
* What would you need to see about the source text before recommending it?

### 8.3 Legal informatics and process modelling

**Who they are.**

* [IAAIL](https://iaail.org/) runs ICAIL. It has been annual "from the 2025 edition onwards"; 2026 was in
  Singapore, 8 to 12 June.
* [JURIX](https://www.irit.fr/jurix2026) is the main European conference.
* Stanford's [CodeX FutureLaw](https://conferences.law.stanford.edu/futurelaw/).
* The business process management (BPM) and process mining communities.
* The Rules as Code community of practice, now under the Beeck Center's Digital Government Network after a 2026
  merger ([2025 year in review](https://digitalgovernmenthub.org/?p=32986)).
* Law-as-code projects: [Catala](https://www.microsoft.com/en-us/research/publication/catala-a-programming-language-for-the-law/)
  (on Zulip) and [OpenFisca](https://openfisca.readthedocs.io/en/latest/community.html) (on Slack).

**The pain lexflow could address.** Few open datasets link statutes to processes, and few benchmarks exist with
honest ceilings. lexflow has both:

* 22 reference models;
* 30 AskBench references;
* Claude-vs-Claude agreement of 0.89 (models) and 0.69 (answers);
* a list of what did not work.

**Where they gather.**

| When | What | Notes |
|---|---|---|
| 8 to 10 Dec 2026 | JURIX 2026, Toulouse | Workshops and doctoral consortium on 8 Dec. The paper deadline has passed; attend. |
| 28 Jan 2027 | ICAIL 2027 paper deadline | Long (10 pages), short (5) and 2-page demos. Conference 5 to 9 Jul 2027 at the University of Vienna's Juridicum. **Unconfirmed**: from listings ([BERI](https://www.beri.net/events/icail-2027)), not yet on iaail.org. |
| 8 to 12 Feb 2027 | ICPM 2027 (process mining), Rende | Deadline passed ([ICPM](https://icpmconference.org/conferences/)) |
| 4 Mar and 18 Mar 2027 | BPM 2027 abstract and full-paper deadlines | Conference 5 to 10 Sept 2027, KU Leuven; workshops 6 Sept. Topics include "smart government applications" and process modelling; there is no law or compliance track ([CfP](https://easychair.org/cfp/BPM2027)). The workshop-proposal deadline was not listed. |
| ~April 2027 | CodeX FutureLaw | **Estimate**: 2026 was 16 April |

**Norms.** Reproducibility, held-out evaluation and no overclaiming. lexflow's habit of publishing confidence
intervals and dropped experiments is an asset here.

**Credible first contact.** A 2-page ICAIL demo paper or a BPM paper on "statutes to sound BPMN with quote
grounding". Release the benchmark with it, under a licence counsel approves.

**What will not work.** Releasing data derived from CC BY-NC sources under a more open licence.

---

## 9. Freedom-of-information users

### 9.1 Who they are

* **Investigative journalists and data journalists.** [IRE](https://ire.org/conferences) runs NICAR and the IRE
  conference.
* **[NFOIC](https://www.nfoic.org/).** A network of state FOI coalitions. It runs a research competition and a
  National FOI Summit; the most recent listed was online on 14 Nov 2024, on AI and public records. It shares a
  $1.25M Press Forward grant with MuckRock and others to help local journalists get records.
* **State coalitions.** In Virginia, the Virginia Coalition for Open Government (VCOG), which the General Assembly
  commended in 2026 ([Brechner](https://brechner.org/2026/06/08/virginia-foi-coalition-honored-by-legislature/)).
* **[MuckRock](https://www.muckrock.com/place).** Its jurisdiction pages compare the legal deadline with the
  average response its users report. It has appeal guides, including constructive denial. Its
  [state guide template](https://www.muckrock.com/stateguide/statetemplate/) asks about:
  * the response deadline;
  * tracking numbers;
  * fee waivers;
  * time to appeal;
  * whether a delay can be appealed;
  * attorney's fees.

  Those are almost exactly the slots in lexflow's records models.
* **The Reporters Committee's [Open Government Guide](https://www.rcfp.org/open-government-guide/).** A free
  compendium of "every state's open records and open meetings laws". Each state follows a standard outline, so
  states can be compared. The page shows no last-updated date. The Reporters Committee covers federal law
  separately in a FOIA Wiki, which makes it a natural peer for a wiki project.

### 9.2 The pain lexflow could address, and the competition

The pain:

* deadlines;
* deemed denial;
* appeal routes;
* fees;
* finding the right custodian, which is where the stale-website finding matters.

**The Open Government Guide and MuckRock already do most of this.** lexflow adds three things they do not have:

* a word-for-word quote for every step;
* a process map with deemed-denial routing;
* local contacts that are checked.

Offer those as links into their work, not as a rival guide.

### 9.3 Where they gather

| When | What | Notes |
|---|---|---|
| 11 to 14 Mar 2027 | NICAR 2027, Denver | IRE membership through 1 Apr 2027 is required |
| 14 to 20 Mar 2027 | Sunshine Week | The week that includes 16 March ([Wikipedia](https://en.wikipedia.org/wiki/Sunshine_Week)) |
| Spring (**unconfirmed**) | VCOG annual conference | A recent conference was on 3 April, with a session on AI for civic engagement; the year was not shown ([VCOG post](https://meganrhynevcog.substack.com/p/i-want-to-see-you-on-april-3)) |
| 24 to 27 Jun 2027 | IRE 2027, Phoenix | |
| Oct 2027 | IRE AccessFest (online) | |
| Not announced | NFOIC National FOI Summit | |

### 9.4 Norms

* Journalists value independence.
* Coalitions value non-partisanship.
* Neither wants a pitch. Both want data, tip sheets and corrections.
* MuckRock is a nonprofit newsroom. Offer it data, never ask it for coverage.

### 9.5 Credible first contact, and questions

**First contact.** Release an 11-state "what happens when the deadline passes" table in Sunshine Week 2027, quoted
and linked. Offer it first to VCOG and, as a set of corrections and links, to MuckRock's state guides. A NICAR
tipsheet on "find the clause that starts the clock" is the follow-on.

**Questions to ask:**

* Which state's deadline rules do requesters get wrong most often?
* Would a link to the exact clause help in an appeal letter?
* Do you track which official records pages or emails stop working?

### 9.6 What will not work

* A new FOIA guide site.
* Claims about exemptions; question B1 is not built.

---

## 10. Civic tech

### 10.1 Who they are, and where they gather

* **The Code for America brigades are gone.** In February 2023, Code for America ended its affiliation with about
  60 brigades and its fiscal sponsorship of them ([StateScoop, May 2023](https://statescoop.com/code-for-america-former-brigades-regroup/)).
  * Code for America itself runs a summit: 7 and 8 May 2026 in Chicago, and 2027 in Washington DC, dates not
    announced ([summit](https://summit.codeforamerica.org/)).
* **The successor is the [Alliance of Civic Technologists](https://directory.civictech.guide/listing/alliance-of-civic-technologists-act)**
  (ACT).
  * It is a decentralised network in which each member group has two delegates.
  * Member groups run CityCamp unconferences.
  * An ACT Congress is listed for **17 Oct 2026** in Orlando, hosted by Florida Community Innovation. That comes
    from a third-party listing (**unconfirmed**).
  * Chi Hack Night joined in 2024 ([post](https://chihacknight.org/blog/2024/12/16/2024-joining-act)).
* **[US Digital Response](https://www.usdigitalresponse.org/).** A free, nonpartisan nonprofit. Governments request
  help, and pro-bono experts are matched to them. It reports work with over 550 governments.
* **The [Civic Tech Field Guide](https://civictech.guide/).** Over 12,800 listings, a submit form, a weekly
  newsletter and a Slack. It is a project of Superbloom.

### 10.2 Norms

* An open-source licence and a code of conduct are expected.
* Work comes as "good first issue" tasks.
* Contributors want to see a real government partner.

**lexflow has no licence**, so this community cannot help yet. Note the AGPL-3.0 dependencies (pm4py, powl) when
choosing one.

### 10.3 Credible first contact, and questions

**First contact.** Choose a licence, then list lexflow on the Civic Tech Field Guide. Then offer one hack-night
task: "check your county's listed website, and fix it on Wikidata by hand, with a reference". It needs no
installation, it teaches Wikidata, and it feeds §2.

**Questions to ask:**

* What would your group need to adopt a statewide data-quality task?
* Which local government in your area would review the result?

### 10.4 What will not work

* Recruiting volunteers to an unlicensed repository.
* Asking USDR for help building lexflow. USDR serves governments, so a government would have to ask.

---

## 11. Small business advisors

### 11.1 Who they are

* **[America's SBDC](https://americassbdc.org/future-conferences).** The Small Business Development Center
  network. Its training conference ran 29 Sept to 1 Oct 2026 in Atlanta. The next is listed as **10 to 18 Sept
  2027**, Indianapolis (the span looks long; check). 2028 is in Austin.
* **SCORE.** Volunteer mentors and an SBA resource partner. Counts vary by source, roughly 9,000 to 10,000
  volunteers. An SBA notice of funding to administer the SCORE program closed 14 Aug 2026, so the program's
  administration may change ([grant listing](https://simpler.grants.gov/opportunity/363127)).

### 11.2 The pain lexflow could address

* "Start a business in this town" checklists: entity filing, fee, office, local licence.
* Reentry entrepreneurs (A4 in [docs/questions.md](../questions.md)).

lexflow's seven-structure business models are the fit. Local licences are only LOCUS matches today.

### 11.3 Norms

* Advisors do not give legal advice. They refer clients to attorneys.
* They want checklists and the right local office, not process theory.

### 11.4 Credible first contact, and questions

**First contact.** A Charlottesville "start a business" page: the SCC filing, the fee, and the local BPOL licence
step with the right office, taken from the existing [answer](../answers/va-charlottesville.md). Ask the nearest
SBDC advisor to mark what is wrong.

**Questions to ask:**

* Which step do your clients most often miss: the state filing, the local licence, zoning or tax registration?
* Would a printed checklist with official links help in a first meeting?

### 11.5 What will not work

* Process maps for mentors.
* Anything that implies legal advice.

---

## 12. What this means for the plugin question

The community map does not settle it, but it does narrow it.

* **Where clerks work.** Clerks in many places work inside GovQA (Granicus) or NextRequest (CivicPlus). Municode
  (CivicPlus) hosts codes for nearly 4,000 local governments ([Wikipedia](https://en.wikipedia.org/wiki/Municode)).
  A plugin would meet them where they are.
* **No marketplace found.** No public integrations marketplace turned up for either vendor:
  * Granicus's partner portal serves resellers ([portal](https://granicus.com/granicus-online-partner-portal/)).
  * CivicPlus documents APIs and an Integration Hub, but third-party access appears to go through customer support.
  * A plugin would therefore depend on each vendor's goodwill. That is a business question, not a community one.
* **The licence.** A free plugin with a paid service behind it is commercial use of CC BY-NC data. It needs a
  licence from Vaquill AI (open-us-law) and from LOCUS's publisher first.
* **Ask clerks first.** Ask the questions in §3.6, especially which system they log requests in, before building
  anything. If most small Virginia towns answer "email and a spreadsheet", a plugin for a large vendor serves the
  wrong people.

---

## 13. Small, niche goals for grad students, each tied to a community

Each goal has these properties:

* one state (Virginia first) and one question;
* one community that owns the result;
* a public output with a venue and a date;
* only Claude-reviewed or person-reviewed models are shown outside the team.

| Goal | Community that owns it | Output and venue | Date |
|---|---|---|---|
| Virginia records clock, from the custodian's side, reviewed by three clerks | Clerks; Virginia FOIA Council | A draft IIMC Technical Bulletin with a clerk as lead author; a VMCA session | IIMC: May 2027; VMCA: Oct 2027 |
| Virginia's first-level agencies and localities on Wikidata, by hand, with references | Govdirectory | Bring Virginia to Govdirectory's US page; a Data Reuse Days talk | Rolling; Data Reuse Days (if held) Feb 2027 |
| Stale official websites: the pilot run statewide, with a method paper | Wikidata, VML/VACo, civic tech | A Wikidata talk-page report; a league members' list; a short paper | VACo Nov 2026 is too soon; aim for 2027 league meetings |
| An 11-state deemed-denial and appeal table | FOI coalitions, journalists | Sunshine Week release; NICAR tipsheet | 14 to 20 Mar 2027 |
| Record sealing in five states, reviewed by a legal aid self-help team | Legal aid | An ITC27 conversation; an ICAIL demo paper | ITC 3 to 5 Feb 2027; ICAIL 28 Jan 2027 (**unconfirmed**) |
| Statute-to-BPMN with quote grounding: the benchmark as a dataset paper | BPM and legal informatics | BPM 2027 or an ICAIL 2027 paper | 18 Mar 2027 / 28 Jan 2027 |
| A Virginia land-use review clock | Planning school studio; APA Virginia | ACSP 2027 abstract; chapter session | ~Mar 2027 (**estimate**) |
| A "start a business here" checklist for one city, reviewed by an SBDC advisor | Small business advisors | A printed checklist and a short case note | Spring 2027 |

If students are paid to edit Wikimedia projects, they disclose it (§2.3). Wiki Education's courses are the
sanctioned training route.

---

## 14. A content plan Claude can run and the owner can test

Claude can do the research, the calendar and the fact-checking. People do the posting.

1. **Each month, Claude produces three things.** The owner or a student reviews them.
   * The calendar rows due in the next 60 days, from §15.
   * For each venue, a one-page brief: the community's norms, the question to ask, and the artifact to bring.
   * Fact sheets and tables (quoted statute cells, freshness counts) re-checked against the store.
2. **People write the words.**
   * For Wikimedia projects and Govdirectory, the person writes the post from scratch, under a personal account,
     with an affiliation line. Claude-drafted prose is not pasted.
   * For listservs and conference abstracts, a person rewrites Claude's outline in their own voice. ICMA abstracts
     carry no product name.
3. **One question per contact.** Every message asks one concrete question (§2.7, §3.6 and the rest). Record the
   answers and corrections in a simple log the owner keeps.
4. **What to measure.**
   * Replies.
   * Corrections received.
   * Corrections applied.
   * Requests for another state or question.
   * People who come back.

   A correction from a clerk is worth more than a page view.
5. **Stop rules.**
   * If a community says no, or says not like this, stop and adjust.
   * Never repeat a post across lists.
   * Never send to a list you have not joined and read for a month.

---

## 15. Calendar, October 2026 to October 2027

| Date | Event | Community | Action | Confidence |
|---|---|---|---|---|
| Weekly, Fri 15:00 CEST | Govdirectory Collab Hour | Wikidata | Attend and listen | Project page |
| Monthly | NARWHAL (Wikimedia DC and NYC); Wikibase user group calls (end of month in 2025) | Wikimedia | Attend | Grant page; 2025 pattern |
| 17 Oct 2026 | ACT Congress, Orlando | Civic tech | Optional | **Unconfirmed** |
| 17 to 21 Oct 2026 | ICMA Annual, Long Beach | Managers | Attend only | Confirmed |
| 17 to 23 Oct 2026 | Wikidata Query Service Days (online) | Wikidata reusers | Attend | Confirmed |
| 22 Oct 2026 | IIMC Records Management roundtable | Clerks | Listen | iimc.com (year inferred) |
| Fall 2026 | AALL 2027 call for program proposals | Law libraries | Check now; it may close this month | **Unconfirmed** |
| 30 Oct 2026 | ITC27 early registration ends | Legal aid | Register if going | Confirmed |
| 7 to 10 Nov 2026 | VACo Annual, Omni Homestead | Virginia counties | Attend or skip | Confirmed |
| **13 Nov 2026** | **ICMA 2027 call for presentations closes** | Managers | Lightning Talk with a practitioner | Confirmed |
| 19 to 21 Nov 2026 | NLC City Summit, Nashville | Cities | Skip in year one | Confirmed |
| 1 Dec 2026 | NACo Legislative Conference early registration ends | Counties | | Confirmed |
| 8 to 10 Dec 2026 | JURIX 2026, Toulouse | Legal informatics | Attend | Confirmed |
| ~End of Dec 2026 | Wikibase Cloud hosting review submission for Lexipedia | Wikibase | Owner submits | **Estimate** (§2.6) |
| 28 Jan 2027 | ICAIL 2027 paper and demo deadline | Legal informatics | Demo paper | **Unconfirmed** |
| 3 to 5 Feb 2027 | LSC ITC27, New Orleans | Legal aid | Attend | Confirmed |
| Feb 2027 | Data Reuse Days (if held) | Wikidata | Talk on freshness | **Unconfirmed** |
| ~23 Feb 2027 | LSC TIG 2027 announcement; pre-applications ~April | Legal aid | Partner with a grantee | **Estimate** |
| 19 Feb 2027 | NACo Technology Innovation Forum | Counties | Attend | Confirmed |
| 20 to 23 Feb 2027 | NACo Legislative Conference, DC | Counties | Optional | Confirmed |
| 4 and 18 Mar 2027 | BPM 2027 abstract and paper deadlines | Process modelling | Paper | Confirmed |
| 11 to 14 Mar 2027 | NICAR 2027, Denver | Journalists | Tipsheet | Confirmed |
| 14 to 20 Mar 2027 | Sunshine Week | FOI | Release the deemed-denial table | Rule-based |
| ~Mar 2027 | ACSP 2027 abstracts | Planning schools | Abstract | **Estimate** |
| ~Apr 2027 | CodeX FutureLaw, Stanford | Legal informatics | Optional | **Estimate** |
| Spring 2027 | VCOG conference; LGA Virginia spring conference | FOI; attorneys | Attend | **Unconfirmed** |
| 16 to 19 Apr 2027 | IMLA Mid-Year Seminar, DC | Municipal attorneys | Attend | Confirmed |
| 9 to 12 May 2027 | IIMC Annual, Fort Worth | Clerks | Attend with a clerk | IIMC newsletter |
| 15 to 18 May 2027 | APA NPC27, Houston | Planners | Attend only | APA release |
| 24 to 27 Jun 2027 | IRE 2027, Phoenix | Journalists | Optional | Confirmed |
| 5 to 9 Jul 2027 | ICAIL 2027, Vienna | Legal informatics | Present if accepted | **Unconfirmed** |
| 17 to 20 Jul 2027 | AALL Annual, Philadelphia | Law libraries | Present if accepted | Confirmed (IALL listing) |
| Q3 2027 (likely Aug) | Wikimania 2027, Santiago | Wikimedia | Only with a contribution to report | Partly |
| 5 to 10 Sep 2027 | BPM 2027, Leuven | Process modelling | Present if accepted | Confirmed |
| 10 to 18 Sep 2027 | America's SBDC conference, Indianapolis | SB advisors | Optional | As listed |
| 25 to 29 Sep 2027 | ICMA 2027, Philadelphia | Managers | Present if accepted | Confirmed |
| Oct 2027 | VML Annual; VMCA institutes; IRE AccessFest | Virginia; clerks; journalists | | Pattern |
| 14 to 18 Oct 2027 | IMLA Annual, Denver | Municipal attorneys | | Confirmed |
| Not set | WikiConference North America 2027; Code for America Summit 2027 (DC); NFOIC FOI Summit; NACo Annual 2027 (Chatham County, GA); NAGARA 2027 | | Watch | Not announced |

---

## 16. Open questions for the owner

1. Which licence for lexflow itself, and has counsel looked at what may be redistributed from open-us-law and
   LOCUS? This decides whether Wikidata, civic tech and any vendor can take part.
2. Who on the team will make Wikidata edits by hand, and under which accounts and disclosures?
3. Has the Wikibase Cloud hosting review been submitted, and does `Project:Copyrights` exist?
4. Which Virginia clerk, attorney, planner and SBDC advisor could each give 20 minutes? Each should be chosen by the
   owner, not by Claude.
5. Should the first year stay Virginia-only, using the three answered places as the proof? This survey recommends it
   (**judgement**).
