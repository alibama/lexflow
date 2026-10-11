# Getting lexflow used: the adoption strategy

_Status: strategy, revised 10 October 2026. The first version was built on the four research notes in this folder:
[landscape.md](landscape.md) (vendors, codes, self-help and rules-as-code), [communities.md](communities.md) (who to
approach, where and when), [models.md](models.md) (money, licences, liability) and [wedge.md](wedge.md) (where to
start). This version applies three critiques written from three chairs: a municipal clerk and records officer
([critique-clerk.md](critique-clerk.md)), a long-time Wikimedian ([critique-wikimedian.md](critique-wikimedian.md)) and
a legal-aid technology lead who practises law ([critique-legalaid.md](critique-legalaid.md)). It also draws on
`README.md`, `docs/questions.md`, `docs/design/*.md` and the code, which were read without changing them. Research and
writing only: nothing was posted, sent, signed up for or edited, and no wiki was touched. This is the only file
written._

_Credit and privacy. This note names organisations, projects, official offices, statutes and published works only.
People appear only as authors of cited works. No organisation named here is a partner, advisor, endorser or
prospective collaborator of lexflow; each is a user, a venue, an incumbent or a source. Places named as "candidates"
have not been asked. Estimates are marked **estimate**, judgements that interviews must test are marked
**judgement**, and dates not confirmed on an official page are marked **unconfirmed**. None of this is legal advice._

_Checks for this revision. On 10 October 2026 I re-read, read-only, with `curl` and the User-Agent
`lexflow-research/0.1 (https://github.com/alibama/lexflow)`, one request at a time and at least 1.5 seconds apart:_

- _Lexipedia: the DokuWiki front page, `lexflow:start`, the Virginia, Maryland and DC records pages and the legacy
  zoning page; the Wikibase main page and the `Project:Copyrights` and `Project:About` titles, through its API._
- _Law: Va. Code §§ 2.2-3704, 2.2-3704.1, 2.2-3704.2, 2.2-3704.3, 2.2-3707, 2.2-3713, 15.2-1427, 15.2-2204, 15.2-2285
  and 54.1-204.1; Md. Gen. Prov. § 4-203; D.C. Code § 2-532; Charlottesville's "Our FOIA Responsibilities" page; the
  Virginia FOIA Council's main page and its FOIA-officer search page._
- _Wikimedia: the Rapid Fund page and the staged Wikibase Cloud hosting policy (both as raw wikitext); English
  Wikipedia's conflict-of-interest and reliable-sources guidelines (raw); article titles through the API; Wikidata
  items Q758545, Q2460456, Q7707919, Q104876318, Q5020891, Q126327443, Q1193907, Q140562024 and Q140562084, the
  property P2241, and the Govdirectory talk page and Virginia subpage title; Govdirectory's CONTRIBUTING.md; Wiki
  Education's "Teach with Wikipedia" page._
- _Other: Interisle's *Phishing Landscape 2025*; NCES's PIAAC 2023 results; Virginia Law Help; the Reporters
  Committee's Legal Hotline page; CCRC's Restoration of Rights Project; ICMA's 2026 Academic Symposium call._
- _Code: `curated/va/records.json`, `lexflow/lab/deadlines.py`, `lexflow/lab/instances.py`, `tests/test_lab.py`,
  `dashboard/lab.js`, `lexflow/publish/wikibase_lexipedia.py` and the README._

_Not read: dokuwiki.org served a bot check in the first round, and I did not work around it. NICAR's pitch form is a
Google Form, and I did not open it. The binding Wikibase Cloud hosting policy renders only with JavaScript; I read
the staged copy on mediawiki.org, which says it was a staging ground and points to the binding one._

### What the critiques changed, in brief

All three critiques said the same first thing: **the front door would end the conversation before any content is
read.** Lexipedia's front page, its licence footer, the "checked by Claude · quality 1.00" label, relabelled deadline
units and a legacy page that miscites the Virginia Code would each lose a clerk, a Wikimedian or a legal-aid attorney
in under a minute. So this version puts a **Gate 0** (§1.9) before every outreach item, and the first four weeks of
the calendar are mostly repair, listening and interviews.

The other big changes:

- **The wedge is narrower and aimed at the people who keep guidance right** (clerks who are their own FOIA officer,
  open-government coalitions, legal-aid content teams), not at requesters in general (§1.3).
- **The custodian lane gets its own safe default** (the earlier date), takes dates only, and comes on paper first
  (§1.3, §3.3).
- **"Reviewed" now means reviewed by a named person**, and anything offered to legal aid needs an attorney of record
  (§5.3, §6.3).
- **The Wikimedia track is an editing programme, not a marketing channel.** Hand edits come first, then the records-act
  items and Govdirectory's Virginia page; Mismatch Finder and QuickStatements come later, if at all (§3.2).
- **English Wikipedia, done properly through Wiki Education, is the biggest public lever**, and it never cites
  Lexipedia (§3.2, P8).
- **A second candidate nail is added for testing**: the deadlines clerks own (meeting notices, hearing
  advertisements), which clerks, planners and municipal attorneys share (§1.2, P2).
- **Several plans are dropped**: filing test requests (an audit in all but name), a league-wide "website health"
  percentage, an ICMA 2027 talk, the Assembly Line deadline offer, selling rule packs to cities, leagues or legal aid,
  and a Rapid Fund bid for lexflow (§1.6).

Where the critiques disagreed, or were wrong on a point I could check, §10 says how I resolved it.

## Contents

0. [The answer on one page](#0-the-answer-on-one-page)
1. [Is this a hammer looking for a nail?](#1-is-this-a-hammer-looking-for-a-nail)
2. [Questions to ask, and how to find the people](#2-questions-to-ask-and-how-to-find-the-people)
3. [The community plan](#3-the-community-plan)
4. [Distribution: plugins and embeds](#4-distribution-plugins-and-embeds)
5. [Sustainability](#5-sustainability)
6. [The graduate-student programme](#6-the-graduate-student-programme)
7. [The 12-week content and outreach calendar](#7-the-12-week-content-and-outreach-calendar)
8. [Metrics and the 90-day plan](#8-metrics-and-the-90-day-plan)
9. [Not verified](#9-not-verified)
10. [How the three critiques were resolved](#10-how-the-three-critiques-were-resolved)

---

## 0. The answer on one page

1. **Is it a hammer looking for a nail? Partly, yes, and the critiques sharpen the "yes".**
   - lexflow was built around what the data made possible, not around a person with a problem. It has no measured
     users. BPMN is the hammer; no US buyer asks for it by name.
   - From the clerk's chair, counting the FOIA clock is not where the week goes. Officers are trained every two years,
     and many work inside portals that count for them. Volume, redaction, cost estimates and machine-written requests
     are the pain (**judgement**, to test first).
   - From legal aid's chair, the finished work (records and business formation) is not in legal aid's areas, and the
     licensing work is AI-written, unreviewed and written for lawyers.
   - **The nail that survives** is narrower: **statutory clocks, counted correctly, quoted, and signed by a named
     person, for the people who keep other people's guidance right.** Those people are clerks who are their own FOIA
     officer, open-government coalitions and newsrooms, and legal-aid self-help content teams. They come back for
     things that are right, printable, dated and kept up to date, not for a process map (§1.2).
2. **Gate 0 comes before everything (§1.9).** No email, post, talk-page note or interview leave-behind links to
   Lexipedia until these are fixed:
   - one accountable organisation and one host for reviewed material (ideally a university-controlled domain);
   - public labels that say who drafted and who reviewed ("Not yet reviewed by a person" until someone has), with no
     model name or "quality 1.00" on public pages;
   - the statute's own unit words on every step ("five working days", not "5 business days");
   - the licence footer, the legacy pages, the `lexflow:start` breadth claim, the "For the wiki" button, staff names on
     place pages, and the receipt-date question in the lab.

   These are days of owner work, not months (**estimate**).
3. **Wedge 1: public-records clocks after a request is received, for intermediaries.** Start in Virginia, linking to
   what the state already publishes (the FOIA Council's officer list, sample letters and advisory opinions, and each
   locality's required rights page) rather than rebuilding it. Then DC and Maryland. Three outputs come from one
   engine:
   - a printable 2027 FOIA due-date calendar for small-town clerks, which their own attorney can check;
   - a dated, human-signed "what happens when the deadline passes" table for coalitions and newsrooms;
   - the deadline engine as a tested JavaScript library, with a section-change watch, for legal-aid self-help
     maintainers.
4. **A second nail to test, not build: the clerk's own deadlines.** These are meeting notices and hearing
   advertisements (Va. Code §§ 2.2-3707, 15.2-2204, 15.2-1427). They are statutory and precise, and the same deadline
   is shared by **clerks, planners and municipal attorneys**, the three audiences the owner named. Ask about it in the
   first interviews. If it beats the FOIA clock at the day-30 test, it becomes the lead (§8.3).
5. **Wedge 2 (licensing after a conviction) waits behind an attorney of record** and is rebuilt around "what governs
   this job?", because Virginia's binding predetermination covers DPOR's boards only, and care jobs fall under
   barrier-crime rules (§1.4).
6. **"Mainstream" means being cited and reused, not visited.** In order of reach:
   - English Wikipedia articles on state records laws, written by students through Wiki Education from secondary
     sources, without AI, never citing Lexipedia;
   - records-act items on Wikidata that Govdirectory already knows how to display;
   - clerk calendars in onboarding binders;
   - a coalition's link to an attorney-signed table;
   - a docassemble interview calling the deadline library.

   Never put Lexipedia links or citations on Wikipedia, and stop calling Lexipedia an encyclopedia (§3.2).
7. **Plugins: not Granicus or CivicPlus now.** Neither has a marketplace or a public API for outside developers, both
   sell the records workflow, and clerks will not install third-party code in their portal (**judgement**, from the
   clerk's critique). The step that works
   through the customer is a **ten-minute portal check**: ten test dates whose lawful due dates the clerk compares in
   the vendor's system. A wrong date becomes the customer's call to its vendor (§4.3). For legal aid, "a plugin"
   means a docassemble package calling the deadline library.
8. **Money.**
   - **Now:** a university lab on grants, with a course and clinic pipeline (Model A).
   - **Cities, leagues and legal aid will not buy "rule packs"** (**judgement** in both practitioner critiques, to
     test in interviews). The plausible later payers are vendors configuring many customers, and grant lines. If
     government pays at all, it buys training hours or a study from a university, not software.
   - **Nothing can be sold while the statute data is CC BY-NC**, and the wiki footer today claims CC BY-SA over it.
     The 22 reviewed models quote **229 sections**, which can be re-fetched from the official publishers. Counsel must
     confirm the path (§5).
9. **Graduate students: start three projects this semester** (§6):
   - **P1, prove the clock:** the deadline engine ported to a JavaScript library, with 100 clerks' hard cases per
     jurisdiction published and checked by two reviewers.
   - **P2, the clerk's own clocks:** interview first, then a quoted backward calendar for notices and hearing
     advertisements, and a FOIA training-records tracker.
   - **P3, Virginia on Wikidata, by hand:** the two hijacked official websites, the records-act items, Govdirectory's
     missing Virginia page and the 14 missing bodies.

   Alongside these, the owner arranges **P4: review under a supervising attorney**, through a law clinic or
   externship. Nothing goes to legal aid, and no table goes out in Sunshine Week, without it. The bridge into the
   mainstream is a clerk, a planner or a docassemble author using a model without hearing the word BPMN.
10. **How we work.**
    - Claude plans, researches, checks facts and drafts.
    - The owner (or a student) reviews, sends or posts under their own name, and logs what happened.
    - Where a community bans AI-written contributions (English Wikipedia, Govdirectory, Hacker News) or judges newcomers
      on their whole pattern (Wikidata), the person writes every word. Claude supplies a facts-only packet, never
      finished prose (§7.2).
    - Never use a public office's FOIA intake for research contact. In Virginia a written ask for records starts the
      clock (§2.3).

---

## 1. Is this a hammer looking for a nail?

### 1.1 The honest answer

Yes, in five ways ([wedge.md](wedge.md) §1, and the three critiques):

- **It was built breadth-first, around the data.** That means 38,640 governments, 47 states of statutes, county
  maps, a Wikibase, and 36 design notes written in one day (C2PA signing, payroll, tax, SBA data).
- **It has no measured users.** The only outside demand on record is one user's licensing question, used to tune the
  planner.
- **Its two founding questions were chosen because they are tractable, not because people struggle with them.**
  Making a records request is easy at step one; the pain comes later. Starting a business is already served by every
  Secretary of State and by paid services.
- **"Every statute as BPMN" has no buyer.** In the US, BPMN lives inside vendors' workflow engines. No state agency
  was found publishing BPMN models ([landscape.md](landscape.md) §5).

  The closest precedent anywhere is Germany's FIM. It publishes master processes in BPMN 2.0, each tied to its legal
  basis down to the paragraph. That works because a national mandate drives it
  ([FIM process concept](https://www.fimportal.de/assets/prozesse_fachkonzept.pdf?version=2)). The US has no such
  mandate.
- **The public face undercuts the work.** Lexipedia's front page says it was "Built by the Center for Civic
  Innovation with the support of" two sponsor logos, lists LexDAO as a "non-profit guild of legal engineers", says
  "attestation models and smart contracts provide best practices for legal review", and lists "Prospera, Roatan,
  Honduras" among its jurisdictions (read 10 October). The lexflow pages lead with "checked by Claude · quality
  1.00". Each of the three reviewers said they would stop there (§1.9).

### 1.2 The nail

lexflow has three traits that its neighbours do not ([communities.md](communities.md) §0):

- a **word-for-word quote behind every step**;
- **the same model shape in every state**;
- **a deadline engine that shows how each date was counted**, with statute-sourced holiday calendars (171 lab tests,
  [lab-plan.md](../design/lab-plan.md) §0).

Those traits matter most where four things meet. The law is statutory. The process has a deadline and an escalation
path. Somebody must get the date right for other people. And the existing guidance has to be kept current by hand.

**What the critiques changed.** The first version assumed that people miscount the clock. The clerk's critique says
that, for a trained FOIA officer with a portal, the date is the easy part. The time goes on volume, vague and bulk
requests, email and video searches, redaction and cost estimates (**judgement**, to test in interviews). The
legal-aid critique says the pull comes from the people who *maintain* self-help content, not from the people who read
it. Both point the same way: the users are the people who keep guidance right, and what they need is a date they can
defend, printed, quoted, signed and kept current.

**Evidence that the records nail is real somewhere:**

| Evidence of pain | Source |
|---|---|
| Median of agencies' average response times: 31 days; success rate 43% (30,000+ requests, 6,000+ agencies, 2017) | [MuckRock 2017](https://www.muckrock.com/news/archives/2017/mar/14/muckrock-foia-response-data/) |
| Massachusetts has a ten-day clock, yet 1,598 of 4,208 MuckRock requests to its agencies were complete (2019) | [MuckRock 2019](https://www.muckrock.com/news/archives/2019/mar/21/feature-state-data/) |
| Washington: 208 reporting agencies received 383,433 requests and spent $101 million in 2019. 1,529 of 2,418 agencies did not report, and 82% of those have budgets under $10 million | [JLARC 2021](https://leg.wa.gov/jlarc/reports/2021/PubRecordsDataCollection/default.html) |
| Illinois Public Access Counselor: 4,234 new requests for assistance in 2024 | [Illinois AG](https://illinoisattorneygeneral.gov/news/story/attorney-general-raoul-issues-2024-public-access-report-during-sunshine-week) |
| Texas Attorney General: 30,939 open-records rulings in fiscal 2018 | [Texas OAG](https://www.texasattorneygeneral.gov/news/releases/ag-paxton-open-records-division-experiences-record-setting-year-public-information-requests-and) |
| Requesters' tools write the first letter and stop, or track requests in calendar days without the statute's units, tolling or appeal path | [lab-research.md](../design/lab-research.md) §2.1 (a desk review, not user research) |

**Evidence against, from Virginia's own law:**

| What the state already provides | Source |
|---|---|
| Every FOIA officer must be trained "at least once during each consecutive period of two calendar years", by the body's counsel or the FOIA Council | [Va. Code § 2.2-3704.2(E)](https://law.lis.virginia.gov/vacode/title2.2/chapter37/section2.2-3704.2/) |
| The Council "shall maintain on its website a listing of all FOIA officers", and does, searchable by public entity with email and telephone | § 2.2-3704.2(G); [FOIA officer search](https://foiaform.dls.virginia.gov/Home/Searchforms/0) |
| The Council publishes "Forms and Sample Letters" and "Searchable Advisory Opinions" | [FOIA Council](https://foiacouncil.dls.virginia.gov/foiacouncil.htm) |
| Every state public body, county, city, school board and town of more than 250 people must post a homepage link to its rights-and-procedures information and to the Council's comment form | [§ 2.2-3704.1(A), (B)](https://law.lis.virginia.gov/vacode/title2.2/chapter37/section2.2-3704.1/) |

So in Virginia lexflow should **link to these first and never rebuild them**. Its own contribution is the counted date,
the edge cases (tolling, extensions, closures, part days), the same shape across states, and the change watch.

Caveat: the MuckRock figures are dated, and they come from one platform whose users skew towards journalists.

**Others pay to drive nearby nails** ([models.md](models.md) §2):

- Granicus sells GovQA, records-request software "fully configurable" to each customer
  ([Granicus](https://granicus.com/solution/public-records-and-compliance/)). Someone has to set each state's clocks
  right.
- LSC funded the adoption of LACI, an open-source legal-aid tool that tracks changes in laws, regulations and court
  rules ([LSC TIG awards](https://www.lsc.gov/grants/technology-initiative-grant-program/technology-initiative-grant-awards-tig-projects-funded-year)).
  That is a precedent for the change watch, and a project to contribute to, not to compete with.
- Mozilla funded a tool that guides people through Spain's freedom-of-information process
  ([Mozilla](https://www.mozillafoundation.org/en/what-we-do/grantmaking/incubator/democracy-ai-cohort/)).

**A second candidate nail: the clerk's own clocks.** The clerk's critique names the deadline that "keeps me up": the
notice and advertisement for a public hearing (**judgement**). The rules are statutory and exact (verified 10
October):

- a meeting notice "shall be posted at least three working days prior to the meeting"
  ([§ 2.2-3707](https://law.lis.virginia.gov/vacode/title2.2/chapter37/section2.2-3707/));
- planning and zoning hearings need two newspaper notices, "the first notice appearing no more than 28 days before
  and the second notice appearing no less than five days before" the meeting
  ([§ 15.2-2204](https://law.lis.virginia.gov/vacode/title15.2/chapter22/section15.2-2204/));
- ordinances are advertised twice, the second "no less than seven days before"
  ([§ 15.2-1427](https://law.lis.virginia.gov/vacode/title15.2/chapter14/section15.2-1427/));
- the clerk of each governing body keeps FOIA-training records "for five years", and new local officials train
  "within two months after assuming the local elected office"
  ([§ 2.2-3704.3](https://law.lis.virginia.gov/vacode/title2.2/chapter37/section2.2-3704.3/)).

The stakes are a re-noticed hearing or a challenged ordinance. The same deadline touches the clerk, the planner and
the municipal attorney. The engine already counts working days forward; counting backward is a small extension. It
is a hypothesis: P2 tests it in interviews before anything is built.

### 1.3 Wedge 1 (recommended): public-records clocks after a request is received

**The job, for each lane:**

- **Requester view** (multi-state requesters, student newsrooms, open-government coalitions): "The office received my
  request on date X. When is the answer due? If it is late, partial, too expensive or refused, what is the next step,
  and by when?"
- **Custodian view** (small-town clerks who are their own FOIA officer): "We received a request on date X. What date
  must we meet, what stops the clock, and what may we send?"
- **Maintainer view** (legal-aid and coalition content teams): "Give me the counted date, the quote and the test
  cases for the clock my guide cites, and tell me when the section changes."

**One model, three defaults.** The model is shared, but the safe default reading is not:

| Lane | Where the law is open (a part day off, the Virginia extension anchor) | Why |
|---|---|---|
| Requester | Show the **later** date as the body's deadline, and the earlier one beside it. The lab already does this for the Virginia extension: its tests expect 19 November, with 16 November shown as "counted from the extension notice" (`tests/test_lab.py`) | Never call a body late while it may still be in time |
| Custodian | Print the **earlier** date as "meet this", and the later reading beside it with its basis | The clerk is the one who breaks the law if a court takes the earlier reading |
| Maintainer | Show both, with each reading's source | They decide what their guide says |

**Count from receipt, not sending.** Every clock with a number of days in the 11 reviewed jurisdictions runs from
receipt ("of receiving", "of the receipt", "after receiving", "from receipt"); Florida, Ohio and North Carolina set no
number of days. The engine handles a receipt date. But the lab page asks only for
"Date the request was sent" (`dashboard/lab.js`), and the engine then assumes receipt on that day, with a muted note
(`lexflow/lab/instances.py`). Ask first when the office *got* the request. Say which date was used in the result line
itself, and never show "overdue" or "deemed denied" on an assumed date without saying so in the same sentence.

**Neutrality.** The same project that sends a clerk a free calendar also tells requesters when a body is late and how
to take it to court. In Virginia the body pays the requester's reasonable costs and fees if the requester
substantially prevails, and officers can face personal civil penalties for wilful violations (§§ 2.2-3713(D),
2.2-3714, per the clerk's critique). Publish one paragraph and keep to it:

> lexflow shows what the law says, for both sides of the counter. We never generate, send or file records requests for
> anyone, never build features that mass-produce requests, and never time, score or rank public offices.

Both lanes also show the rules that make requests go smoothly: describing records with reasonable specificity, asking
for a cost estimate, and who has the right to request.

**Scope.**

- Start with **Virginia**, using the Council's materials. The custodian calendar goes first to **towns**, where the
  clerk usually is the FOIA officer (**judgement**). Charlottesville, the first candidate in the first version, routes
  requests through the City Attorney's Office and a GovQA portal ([city page](https://www.charlottesville.gov/774/Submit-a-FOIA-Request),
  `docs/answers/va-charlottesville.md`). It is a good place to test the portal check (§4.3), not the paper calendar.
- **Who may request matters.** Virginia's right belongs to "citizens of the Commonwealth" and to Virginia-circulating
  newspapers and magazines and stations "broadcasting in or into the Commonwealth"
  ([§ 2.2-3704(A)](https://law.lis.virginia.gov/vacode/title2.2/chapter37/section2.2-3704/)). A multi-state
  journalist from outside may have no right there. Say so on every Virginia page.
- Then **DC and Maryland**. Illinois comes after the audit passes, because its oversight body takes more than 350 new
  matters a month. The other seven reviewed states (CA, TX, NY, FL, OH, WA, NC) wait until the audit passes in three
  states (P1).

**What already exists:**

- 11 Claude-reviewed records models (reviewed by an AI, not yet by a person; `curated/va/records.json` says
  `"reviewed_by": "Claude (claude-opus-5-5), 2026-10-10"`);
- records escalation ladders for all 11 jurisdictions;
- statute-sourced holiday calendars for those 11 and the federal government;
- a deadline engine that shows how each date was counted (business days, roll-forward rules, part days, deemed
  denials, other readings beside the default). `lexflow/lab/deadlines.py` uses only Python's standard library, so it
  can be licensed and ported on its own;
- 171 lab tests ([lab-plan.md](../design/lab-plan.md) §0).

**What is missing:**

- **Gate 0** (§1.9).
- **A named human reviewer for every model**, and an attorney of record before anything reaches legal aid (P4).
- **The edge cases custodians get wrong** (**judgement**, from the clerk's critique): tolling while a cost estimate
  is outstanding, and the request "deemed to be withdrawn" after 30 days without a reply (§ 2.2-3704(F)); tolling while
  a deposit over $200 is pending (§ 2.2-3704(H)); 60 work days for criminal investigative files (§ 2.2-3704(B)(4));
  unplanned closures (§ 1-210(E)); and when a request counts as "received" (after hours, the wrong department, a spam
  filter). The model lists tolling as unmodelled optional steps, and its timer shows only the seven-day extension.
- **A custodian mode that takes dates only.** A case the clerk saves in a browser tab is a public record held outside
  the city's systems, may hold requesters' names, and vanishes when IT resets a profile (§3.3).
- **Recall.** Cases live in the browser. The `.ics` export carries no model ID or version, and its reminder fires one
  day before (`TRIGGER:-P1D` in `dashboard/lab.js`). There is no known-errors page. When a model is fixed, nobody who
  relied on the old date can find out (§4.1).
- **A public surface.** The lab's router is not mounted, so nobody outside a dev harness can start a case.
- **Fee and exemption rules; agency regulations and court rules** for some rungs.
- **Statute text for some states.** PA, HI and NE records law is not in the files, and AR, CO, GA, MS and TN have no
  statute file.

**Why this wedge still comes first:**

- It is the only domain with reviewed models, ladders, calendars and an engine.
- The rules are crisp and statutory, and they can be checked by hand against a printed rule in a minute.
- It serves three audiences from one engine.
- For requesters the risk of unauthorised practice is moderate. For everyone the **reliance risk is high**: people act
  on a date literally, and no disclaimer gives a lost right back. So the date must be right, signed and recallable
  (§5.3).

**Its weaknesses.** An occasional requester needs it once and is hard to reach. Trained FOIA officers with portals may
not need it at all. MuckRock and the Reporters Committee's guide already serve requesters well, so lexflow complements
them (quotes, counting, the edge cases) and never competes. If the day-30 interviews say the date is not the pain,
the custodian calendar shrinks to towns on email and spreadsheets, and the clerk's own clocks (P2) take the lead
(§8.3).

### 1.4 Wedge 2: licensing after a conviction (parked behind an attorney of record)

**The job.** "Before my client trains for this job, what governs it? Can they ask for a binding answer first? How, at
what cost, and how long does the decision take? If they are refused, what is the challenge route and its deadline?"

**Why it is still worth doing later.**

- "Nearly one in five workers needs a license to work". In 21 states boards could deny without considering
  rehabilitation, and 30 states changed these laws between 2015 and 2020 (IJ, 2020, as reproduced by
  [CCRC](https://ccresourcecenter.org/report-card-on-licensing-laws-finds-progress-but-still-a-way-to-go/)). These
  figures are six years old. Replace them with current state-by-state comparisons, such as CCRC's
  [Restoration of Rights Project](https://ccresourcecenter.org/restoration-2/), and date every figure before any
  outreach use.
- lexflow has references and licence-denial ladders for VA, DC, MD, TX and CA, a checked DMN for Cal. Bus. & Prof. Code
  § 480, and the official pre-application forms (Virginia DPOR's predetermination request and the Texas
  criminal-history evaluation letter).
- Given the right sections, its answering scores 0.76 here, against 0.60 for record sealing.

**What the legal-aid critique showed to be wrong:**

- **"Through staff" does not move content to the information side of the line. The content does.** Reentry and
  workforce staff are usually not lawyers, and non-lawyers applying eligibility rules to one person's record is the
  conduct *Upsolve v. James* concerns. A page on a public wiki is public, whoever the plan calls its audience.
- **"Likely barred" is a prediction about one person.** Say instead what a rule says about a *category* ("Under § X,
  a board may deny for a conviction of <category>"), then give the route to a binding answer.
- **"Seal first, then apply" is a recommended course of action.** State the rule instead: if a record is sealed,
  Virginia agencies may not require you to disclose it (§ 19.2-392.15, per the critique), and leave the sequencing to
  the person and their lawyer.
- **"Check with the board" sends a person to the other side.** Every page needs a free-legal-help route: in Virginia,
  [Virginia Law Help](https://www.virginialawhelp.org/), whose header carries "Get Legal Help", English and Español,
  and a Quick Exit button. The partner chooses the wording.
- **The binding route is narrower than the outreach line said.** Va. Code § 54.1-204.1 lets a person "request a
  predetermination from a regulatory board within the Department of Professional and Occupational Regulation or from
  the Department" ([text](https://law.lis.virginia.gov/vacode/title54.1/chapter2/section54.1-204.1/)). It does not
  reach the Department of Health Professions' boards. The Virginia reference also lists barrier-crime employment as an
  off-topic search term, yet barrier crimes govern background checks for many care jobs
  ([§ 19.2-392.02](https://law.lis.virginia.gov/vacode/title19.2/chapter23.1/section19.2-392.02/)). CDL and other
  federal bars, and trades with no licence, are outside the model too.

**So each occupation page opens with "What governs this job?"**: the general licensing rule; a board's own statute; a
background-check rule such as barrier crimes; a federal rule; or no licence at all. Only then does it give a route.
Each page carries a fixed line for staff: "Do not tell a client whether their record disqualifies them. Help them ask
for a binding answer, or refer them to free legal help." "Board-specific; check here" is an allowed answer.

**Gate L (before any licensing page reaches staff):** an attorney of record for the state (P4); the "what governs
this job" structure; the free-legal-help line; the plain-language layer for anything a client sees (P7); and Gate 0.
Then P10 builds it. Otherwise it waits.

**Why not record sealing as the second wedge.** It has the largest measured pain: 6.5% uptake among eligible people
in Michigan, and 20 to 30 million people in the "second chance gap". But four things argue against it
([wedge.md](wedge.md) §3.2):

- the bottleneck is records data, fees and paperwork, not finding the law;
- 14 states and DC now seal automatically;
- lexflow answers sealing worst (0.596 even with Claude's sections);
- applying eligibility rules to one person's record is exactly what unauthorised-practice rules reach.

A question worth asking reentry staff instead: "How does a client get a copy of their own criminal record, and how
long does it take?" If that step stalls everything, it may be a better process to model than the licence ladder
(§2.8).

### 1.5 Alongside both: contact freshness (an on-ramp, and a disclosure duty)

**What the pilot found, stated carefully.** The contacts pilot checked 86 contacts in 49 governments
([entities-contacts.md](../design/entities-contacts.md) §2.5, §3.4):

- About 49 websites could be verified (55 sampled, 6 behind bot walls). 43% (±14 points), about 21, were stale.
- "Stale" mixes harmless and harmful. DNS found 7 dead hosts, title checks found 4 broken sites (3 spam, 1 default
  page), and **8 were redirects to the right new domain** (6 to `.gov`). A redirect that lands on the official site is
  an out-of-date listing, not a broken website.
- It is mostly the frozen Census GUS 2022 file. Where Census and Wikidata agreed, 27% were stale; where Census stood
  alone, 48%.
- The finding that is about Wikidata: **5 of the 6 moved sites still had the old domain on Wikidata.**

**So the 43% is retired as an outreach headline.** It is a figure about directory listings, not about cities'
websites. To a league it sounds like "your members' websites are broken", which is false. To a Wikidata editor it
attributes a mostly-Census problem to their data. Inside the project it stays, with the breakdown.

**Hijacked domains are a disclosure duty first.** Two of the three old domains that now serve spam are still the
"official website" on Wikidata today, at normal rank, with only an "imported from Wikimedia project" reference: the
City of Auburn, Maine (Q758545, `http://www.auburnmaine.org`) and the Village of Lowellville, Ohio (Q2460456,
`http://www.villageoflowellville.com`) (API, 10 October). The third, Androscoggin County, Maine, was the Census listing,
not Wikidata's. The order is:

1. re-check each domain by hand;
2. send a short private note to that government's general office contact (never a FOIA intake), with the evidence;
3. a few working days later, fix Wikidata by hand (§3.2);
4. never name the places in a post, a talk or a ranking.

**Why it is still worth doing.** It costs no legal risk, it protects residents, it improves data that Govdirectory and
many reusers read, and it fixes lexflow's own weakest layer. On-wiki, say it plainly: "we reuse Wikidata's data and
found these errors". Reusers giving back is a respected role. "Gift" language sounds like marketing.

### 1.6 Stop or postpone

| Stop or postpone | Why |
|---|---|
| Growing breadth as a goal: more selector-built states, scoring all 38,640 governments, county confidence maps | No user asked for breadth. Selector models agree with Claude at about 0.60 (records 0.55). Keep the map as an internal QA view |
| The breadth claim on `lexflow:start` ("lexflow answers the same questions for every US county, city and town") | It is live today and contradicts this strategy (§1.9) |
| New infrastructure before a pilot needs it: Wikibase authority properties, C2PA signing, payroll, tax, SBA data | Careful work, but none answers a user's question today |
| Ask (new questions) as a headline feature, and the "For the wiki" publish button for unreviewed answers | 0.40 composite locally, and only 24% of gold sections in the top 10. Keep Ask as a research tool and AskBench; gate the button behind a named reviewer |
| Extending "start a business" | State formation is the solved part. Local licensing is lexflow's weakest layer, and paid services exist |
| Record sealing as a public screener; court debt as a wedge | §1.4. Court debt lives in clerks' and judges' discretion, and courts run their own tools |
| Zoning | The National Zoning Atlas reads more than 200 characteristics per district, and its terms allow no reuse without written permission. The planner product that fits lexflow is a deadline, not zoning content (P2) |
| Building permits | Regulations are not indexed, local amendments vary, and model codes are copyrighted |
| Filing "real requests" to measure agencies (the old P3b) | To the office receiving them it is a compliance audit, and it would poison the clerk relationships the plan needs. Timing comes from published decisions only (P9) |
| A league-wide "website health" percentage | False as framed, and an insult. A private list for each member, if a league asks (§3.7) |
| An ICMA 2027 Lightning Talk (proposals close 13 November 2026) | No practitioner will present a university's tool four weeks after hearing of it (**judgement**). Aim for ICMA's Academic Symposium call in spring 2027 (**estimate**) |
| The Assembly Line "after-filing deadline" offer | No reviewed model covers a court process, and court rules are not indexed. Offer the tested library instead, once it exists (§3.5) |
| Selling rule packs to cities, leagues or legal aid | The FOIA Council trains free; legal aid will not pay from operating funds and already has LACI (§5.1) |
| A Rapid Fund application for lexflow, Lexipedia or paid student editing | Excluded by the fund's own rules (§3.2) |
| Prison wages, phone and commissary, the pretrial clock | Good benchmark questions, not products |

### 1.7 What lexflow is not good at yet

Say these plainly in every venue. Librarians, attorneys, clerks and Wikimedians reward candour, and they will find the
gaps anyway.

- **No person has reviewed the published models.** All 22 say "checked by Claude", and the README names no human
  reviewer. No attorney has looked at any of them.
- **The live pages relabel the law's units.** Virginia's "five working days" and "seven work days" appear as "within 5
  business days" and "within 7 business days". Maryland's "10 working days" appears as "10 business days" in its steps.
  DC's "15 days (except Saturdays, Sundays, and legal public holidays)" appears as "15 business days" in one place and
  "15 working days" in another, and its "25 business days" is lexflow's own sum, shown as if the statute said it (read
  10 October).
- **Pages written for builders.** The Virginia page's "What the text leaves open" section uses code names
  (`respond_extended`, `deemed_denied`) and BPMN terms. There is no plain-language layer, no Spanish, no print view and
  no reading-level target. That matters when 28% of US adults performed at Level 1 or below in literacy in 2023
  ([NCES, PIAAC 2023](https://nces.ed.gov/surveys/piaac/2023/national_results.asp)).
- **No public product.** The dashboard is a local Docker tool. The lab cannot start a case outside a dev harness.
- **No recall.** There is no versioned export and no known-errors page.
- **New questions.** The local composite is 0.40 (0.75 given Claude's sections; Claude against Claude is 0.69).
- **Local law.** There are no local process models. LOCUS gives headings only, under CC BY-NC.
- **Law outside statutes.** Regulations and court rules are not indexed, and 12 ladder rungs depend on rules outside
  the corpus.
- **Coverage holes.** AR, CO, GA, MS and TN have no statute file. PA, HI and NE records law is missing, and ND's text
  is wrong.
- **Time.** Nothing yet watches for amendments to the sections a model quotes.
- **Licences.** The statute compilation is CC BY-NC 4.0; the wiki footer says CC BY-SA 4.0; lexflow's own code has no
  licence file, yet the front page calls it "open-source".
- **The neighbourhood.** The same domain hosts more than 100 older pages outside `lexflow:`. One of them, "How do I
  challenge a zoning decision in Virginia?", says the 30-day appeal is "stated in Virginia Code § 15.2-2284". It is not:
  § 15.2-2284 lists the matters considered in drawing zoning districts, and the 30-day rule is in § 15.2-2285(F)
  ("shall be filed within 30 days of the decision", [text](https://law.lis.virginia.gov/vacode/title15.2/chapter22/section15.2-2285/)).

### 1.8 "It could be really useful for our government". Is it?

**Yes, in bounded ways that need no purchase, but "free" is not free for a government.**

The uses that hold up after the clerk's critique:

1. **A FOIA due-date calendar for a small office**, checked by a named person and signed off by the office's own
   attorney before staff rely on it (§3.3).
2. **A ten-minute check of the office's records portal** against ten lawful due dates (§4.3).
3. **A private stale-domain alert and self-check**, sent only to that government: does the homepage link to the
   § 2.2-3704.1 rights page and the Council's form; does the FOIA officer on the site match the Council's list; does
   any old listed domain now lead somewhere harmful? Never published as a ranking.
4. **If interviews confirm it, a backward calendar for meeting notices and hearing advertisements** (P2).
5. Later, **staff-facing licensing pages** for workforce and reentry programmes, behind Gate L.

What a city still has to do, even for a free resource (**judgement**, except where linked):

- **Terms.** The city attorney reads the terms of any outside service staff use. A wiki footer and an unlicensed
  repository are not terms.
- **IT.** Staff may not use unapproved web tools, and many desktops wipe browser storage at logoff.
- **Records.** Anything staff create in city business is a public record whatever the medium
  ([§ 42.1-77](https://law.lis.virginia.gov/vacode/title42.1/chapter7/section42.1-77/), per the clerk's critique).
- **Accessibility.** From **26 April 2027**, governments of 50,000 or more people must meet WCAG 2.1 AA for web
  content, including content their vendors supply. Smaller ones have until **26 April 2028**
  ([Federal Register, 20 Apr 2026](https://www.federalregister.gov/documents/2026/04/20/2026-07663/extension-of-compliance-dates-for-nondiscrimination-on-the-basis-of-disability-accessibility-of-web)).
  Ship every clerk artefact as a tagged, accessible PDF.
- **Licence.** Share-alike would reach a staff manual that adapts the card. Release clerk artefacts as CC0 (the
  statute words are public domain if fetched from the official publisher; the counting is lexflow's own), once counsel
  confirms (§5.2).
- **Gifts and endorsements.** Some localities bar staff from endorsing products or need approval to accept free
  services. A bulletin about a named tool, "with the clerk as lead author", may not be allowed. A method note may be.

**Not as a product a city buys now.** Cities buy through incumbents and cooperative contracts, and they need an
accessibility conformance report. If a government ever pays, it will more likely buy training hours or a
records-process study from the university than software. Keeping the work inside a public university may make a later
Virginia agreement simpler: the competition rule in Va. Code § 2.2-4303(A) is written for nongovernmental contractors.
The city attorney decides that ([models.md](models.md) §5.3).

### 1.9 Gate 0: the front door, before any outreach

Every outreach piece links somewhere, and every reader judges the whole site behind the link. Until these are done,
outreach is limited to warm-introduction interview requests with no links, and to listening.

| # | Fix | Why (who flagged it) | Size (**estimate**) |
|---|---|---|---|
| 1 | **Choose one accountable organisation and one host for reviewed material.** Recommended: reviewed pages on a university-controlled domain with a named responsible unit, and Lexipedia kept as the workspace and mirror. If that is not possible this term, clean up Lexipedia instead (rows 2 to 6) and give `lexflow:` its own front door | Three identities (university, a civic-tech nonprofit, a legal-engineering guild) on one page; `.xyz` ranked fourth of all top-level domains by phishing domains reported in 2025 (73,509), with "historically high rankings" ([Interisle](https://interisle.net/s/phishinglandscape2025.pdf), p. 11) (all three) | Decision: days. Hosting: weeks |
| 2 | **Front page:** take "smart contracts", the Próspera jurisdiction and the sponsor block off the start page or away from the records work; write the "Community Guidelines" page (a red link today) | Crypto and charter-city politics before any records content (clerk, Wikimedian) | Small |
| 3 | **Legacy pages:** put an "unreviewed draft" banner on every page outside `lexflow:`, move the legal Q&A pages to a `drafts:` namespace with `noindex`, and fix or delete the zoning page | One miscited Virginia section under the same brand undoes "only reviewed work leaves the team" (Wikimedian) | Small |
| 4 | **Public labels:** remove the model name and "quality 1.00" from public pages. Show "Drafted with an AI system from the statute text · Every quote matched to the official text on <date> · Not yet reviewed by a person". When a person signs: "Reviewed by <name>, <role>, on <date>". For anything offered to legal aid: "Reviewed by <name>, attorney licensed in <state>, on <date>". Keep the machine-check details on the method page | "Checked by Claude" reads as "no lawyer looked"; "1.00" reads as "perfect" (all three) | Small |
| 5 | **Units in the law's words** on every step; derived figures marked ("lexflow's count: 15 + up to 10"); all 53 curated deadlines re-checked this way | "In the law's own words" is the selling point (legal aid, clerk) | Small |
| 6 | **Licence footer:** replace the blanket CC BY-SA line with "Licences vary by source; see <data policy page>" until counsel answers; add a `lexflow:` namespace notice on the CC BY-NC origin; add "not affiliated with the Wikimedia Foundation" | BY-SA over NC-derived content reads as carelessness about licences (Wikimedian, legal aid) | Small |
| 7 | **No "open-source" anywhere** until a licence file exists in the repository | A Wikimedian or civic-tech volunteer will click through and look (Wikimedian) | Small |
| 8 | **`lexflow:start`:** reword to the 11 reviewed jurisdictions | The breadth pitch this strategy forbids (Wikimedian) | Small |
| 9 | **"For the wiki":** turn it off for unreviewed answers; keep the 26 "Unreviewed draft" Wikibase items out of search, or hidden | One unreviewed machine answer found by a partner undoes the rest (legal aid, Wikimedian) | Small |
| 10 | **Place pages:** office titles and shared inboxes only, no staff names; remove the business-licence sources from records pages; a takedown and correction promise for governments (fixed or removed within two working days, and a named contact) | The Charlottesville page names two FOIA staff members (clerk) | Small |
| 11 | **The lab:** ask the receipt date first; state assumptions in the result line; a custodian mode that takes dates and closures only; a shared-computer mode, on by default, that keeps nothing after the tab closes, with "Save on this device" and "Clear everything" | Wrong anchor; city records in a browser tab; library computers (legal aid, clerk) | Small |
| 12 | **Builder notes** (code names, BPMN terms) moved off public pages to a method or source page | Readability (legal aid) | Small |
| 13 | **The Wikibase main page** rewritten to describe what is there (item counts, classes, posts not people, 26 unreviewed items), with ambitions under "planned"; `Project:Copyrights` and `Project:About` created (both missing, API check 10 October) | The hosting review requires that "the instance's observed use matches the provided information" (Wikimedian) | Small |
| 14 | **One corrections address**, a public known-errors page, and the neutrality paragraph (§1.3) | Every reviewer's first question is "what happens when you get one wrong?" (all three) | Small |

Rows 2 to 14 are days of work, not months (**estimate**). Row 1's hosting may take longer. The day-14 decision point
(§8.3) checks progress.

---

## 2. Questions to ask, and how to find the people

Questions do not attract users. They find out whether a problem is worth solving and who has it. Users come when the
answer shows up in a channel they already use. So the interviews come first, and every one should end with the
interviewee holding something useful that they can check (a stale-domain note, a citation-freshness check of their
own public guides, the Council's own resources), never a pitch and never a link to an unfixed site.

### 2.1 Questions for the owner first

- **Who is accountable?** Which one organisation signs this work, on which domain? A clerk who gets a card will look
  up the sender (§1.9).
- **Who signs each page?** Who is the named human reviewer for each model, and who is the attorney of record for each
  state before anything reaches legal aid (P4)?
- **Who loses something this month** when a records deadline is miscounted, and do they know it?
- **Who would notice if Lexipedia went offline tomorrow?** Today the answer is nobody outside the team. That is the
  baseline to change.
- **Which one office or organisation** could we serve so well this semester that it tells a peer?
- **What will we refuse to do, even when asked?**
  - individual eligibility advice;
  - selling or showing unreviewed models;
  - generating, sending or filing records requests for anyone, or timing and ranking offices;
  - links or citations to Lexipedia on Wikipedia;
  - AI-written posts in communities that ban them.
- **Who keeps each relationship and each model alive in 2028,** after this year's students graduate? Name one person
  per locality relationship who stays across semesters.

### 2.2 The ten questions to ask first

These ten carry the most information per minute across the audiences that matter for the wedge and the second nail.
Each asks about the last time, not the future, and none asks a public official to admit a violation.

| # | Ask | Of whom | What the answer decides |
|---|---|---|---|
| 1 | "Who here answers records requests? Is that you?" | Clerks, town managers | Whether this person is the custodian at all. In Virginia the FOIA officer can sit anywhere, and constitutional officers are separate public bodies |
| 2 | "Which deadlines are yours personally? When did one last get tight, and what did people do then?" | Clerks, planners, municipal attorneys | The second nail. If notices and hearing advertisements come up before FOIA, P2 takes the lead |
| 3 | "What took the most staff hours last month?" | Clerks, FOIA officers, planners | Whether the date is the pain, or volume, redaction and estimates are |
| 4 | "When did your portal's (or your calendar's) due date and yours last differ? What did you do?" | Clerks on GovQA, NextRequest, JustFOIA or a spreadsheet | The plugin question, with data, and whether the ten-minute portal check (§4.3) is wanted |
| 5 | "Which of your self-help guides went out of date most recently? How did you find out, and how long did the fix take?" | Legal-aid and coalition content teams | The change-watch nail (P5) |
| 6 | "Tell me about the last outside resource you stopped linking to or handing out. Why? And who must approve one before staff use it?" | Everyone | The trust bar, and the real approver |
| 7 | "Tell me about the last time something you handed out turned out to be wrong. How did you reach the people who had it?" | Legal aid, clerks, coalitions | The recall design and the corrections process |
| 8 | "After someone files the request or form you help with most, who tells them the next deadline, and how?" | Legal aid, coalitions, librarians | Whether tools really "stop at filing", which today rests on a desk review |
| 9 | "Tell me about the last request that stalled. What did you do next, and when?" | Requesters, student newsrooms | Whether the next rung is known and used, or the will to use it is missing |
| 10 | "Which state-law questions did departments send you in the last month? Take the last one: how did you answer it, from what sources, and how long did it take?" | Municipal attorneys | Which models to build after records, and the source to beat |

**For Wikimedians, these are not interview questions.** They are not lexflow's users; they are the people whose data
lexflow reuses and whose norms it must meet. Ask in the open, at Collab Hour or on the WikiProject talk page, after
making edits: "What is blocking the next US state from being published on Govdirectory?" (§2.12).

### 2.3 How to run an interview

- **Ask about the last time, not about the future.**
  - "Would you use this?" invites a polite yes.
  - Ask what happened, what they used, what it cost them and who they asked.
  - The method follows *The Mom Test* ([Fitzpatrick](https://www.momtestbook.com/)).
- **Ask in the third person when the subject is compliance.** "When does a deadline get tight in an office like
  yours?", not "Have you ever missed a deadline?" In Virginia a failure to respond "shall constitute a violation"
  (§ 2.2-3704(E)). The "Have you ever missed a deadline?" question in [wedge.md](wedge.md) §7 must not be used.
- **Never ask a public office in writing for its records.** In Virginia a request "need not make reference to this
  chapter" to start the five-day clock (§ 2.2-3704(B)). "Could you show me your tracking spreadsheet?" by email is a
  request, and the office will log it. Ask instead: "Is any of that on your website? Could you describe how it is laid
  out?"
- **Logistics.** 20 to 30 minutes, one interviewer and one note-taker. Never record without consent.
- **Permission.** Many clerks need their manager's or attorney's approval to take part in research about compliance
  (**judgement**). Ask, and offer a one-paragraph description they can forward.
- **Public records, both ways.** Every email to a city is a public record of the city. Interview notes held by a
  public university may be requestable too; unpublished research data may fall under an exemption
  ([§ 2.2-3705.4(A)(4)](https://law.lis.virginia.gov/vacode/title2.2/chapter37/section2.2-3705.4/)), but the IRB and
  university counsel decide. Say this in the consent script, and design the log so that nothing in it would embarrass
  an office if released.
- **Pull** is what counts, and compliments are not pull. Pull looks like this:
  - they describe or show their workaround;
  - they ask when they can use it;
  - they correct your page;
  - they introduce a colleague;
  - they give time or data;
  - they name a budget line.
- **Human-subjects review comes first.**
  - Interviews and usability tests at a university need the IRB's review, or a documented determination that review
    is not needed. Many interview studies fall in an exempt category
    ([45 CFR 46.104(d)(2)](https://www.ecfr.gov/current/title-45/section-46.104)), but the IRB decides.
  - Apply in week 1. No interview happens before the determination.
  - Any study that touches people with criminal records goes through program staff, with the IRB's explicit
    approval.
- **Residents are paid, not "helped".** The first version offered residents "five minutes of help on their own
  question". That is individual help by non-lawyers, it collects case facts, and for an IRB it ties a benefit to
  disclosing a legal problem. Instead: a modest IRB-approved fee or gift card, and the partner's own referral sheet for
  everyone, whether or not they take part. Recruit and consent in plain language, in Spanish where the partner serves
  Spanish speakers, and read the consent aloud.
- **Test understanding, not only speed.** After "your request went unanswered; what is your next step and its
  deadline?", ask "In your own words, what does 'deemed denied' mean here?" and "What would you do tomorrow?"
- **Never collect a person's case facts.** No charges, record contents or request subjects. Ask about process and
  time. Open legal-aid questions with "Without any details about the client…".
- **Timing for clerks** (**judgement**, from the clerk's critique): avoid council meeting days and the days before,
  election weeks (Virginia's Election Day, 3 November 2026, is a legal holiday), the weeks before budget adoption,
  Thanksgiving week and the last two weeks of December.
- **Log every interview the same way.** Record the date; role and organisation type and size (no names in the log);
  the last instance described; the tools used; the time or money it cost; who they asked; artefacts described; pull
  signals; referrals offered; and what would change our plan.

### 2.4 Finding five people per audience without spamming anyone

**General rules:**

1. **One person, one message, written by a person.** Say who you are, your university affiliation, why them, how long
   it takes, and that there is nothing to buy.
2. **Give first, and make the gift checkable in ten minutes.** Never ask an attorney or a clerk to "mark up" an
   AI-written document as the first contact. To the recipient that is unpaid quality work on AI output.
3. **One follow-up after a week, then stop.** Keep a do-not-contact list.
4. **Warm introductions, or the office's general line. Never the FOIA intake or portal.** Use the locality's attorney,
   manager or the VMCA for clerks. The FOIA-officer list exists so people can file requests, not receive research
   pitches; do not mine it for outreach.
5. **Never buy or scrape lists.** Never BCC a group, and never post the same note on several lists.
6. **Read a list or forum for a month before posting to it.** Never recruit on a listserv you have not been part of.
7. **The owner chooses the people, not Claude** ([communities.md](communities.md) §16).
8. **No links until Gate 0 is done** (§1.9). Attach a PDF, or send nothing but the request for 20 minutes.

| Audience | Where five interviewees come from | First thing given (checkable) | Do not |
|---|---|---|---|
| Town clerks who are their own FOIA officer | Small Virginia towns near the university, through their manager, attorney or the VMCA; the Virginia FOIA Council's free trainings (listen only) | The private self-check and stale-domain note for their locality (§1.8) | Use the FOIA intake; ask them to adopt a tool; pitch at a training |
| City and county FOIA officers and clerks | The same routes; Charlottesville's City Attorney's Office through a warm introduction | The ten-minute portal check, once P1 has published the cases | Ask for request logs in writing |
| City planners | The university's planning school; the locality's planning staff and the regional planning district commission; APA Virginia events | Nothing yet: ask question 2 and listen. Later, the notice calendar (P2) | Pitch lexflow as a zoning tool |
| Municipal attorneys | Local government law faculty or clinics; city and county attorney offices through warm introductions; Local Government Attorneys of Virginia conferences | The after-deadline table, only once a named person (and for legal content, an attorney) has signed it | Ask to join IMLA's members-only listservs; show "checked by Claude" before asking about AI citations |
| Legal-aid self-help content teams | A statewide legal-information site's content team; law school clinics; LSNTAP lists (after a month of reading) | A citation-freshness check of their own public guides (§3.5) | Ask for markup of an AI reference; ask about grants in the first interview |
| Reentry and workforce staff | Reentry councils; community college workforce programmes; through legal aid | Nothing yet: questions only, until Gate L | Offer direct-to-client answers |
| Journalists and FOI requesters | The university's student newsroom and journalism faculty; VCOG; IRE events | The state's "after you file" page, once Gate 0 is done | Mine MuckRock users' public request histories |
| Small-business advisors | The nearest SBDC office; the local SCORE chapter | A Charlottesville start-a-business checklist | Show process maps to mentors |
| Residents | A public library, legal-aid intake or a community centre, with the partner's consent and IRB approval | A paid session and the partner's referral sheet | Recruit cold on social media; ask about records or sensitive facts |
| Wikimedians | Not interviewed. Read the talk-page archives, Project chat and the July 2026 case; attend Govdirectory's Collab Hour and the NARWHAL call | Hand-made, referenced edits (§3.2) | Message editors found through edit histories; recruit through user talk pages |

### 2.5 Municipal clerks and records officers

| Question | What the answer tells you |
|---|---|
| Who here answers records requests? Is that you? (ask first) | Whether this is the custodian. Police, constitutional officers and departments often have their own |
| Which deadlines are yours personally? (notices, advertisements, minutes, training records, records requests) | The second nail |
| What took the most staff hours last month? | Where the time really goes |
| Tell me about the last records request that came in. What happened, from the day it arrived? | Finding, redacting, the fee estimate or the letter. If the clock never comes up, the custodian lane may not be the pain |
| How did you work out the date the response was due? Then: when did the portal's date and yours last differ? | Whether counting is hard, and what they use today |
| The last time a request did not fit the pattern (a holiday, a closure, an extension, a cost estimate), what did you do, and who did you ask? | Who they trust: the city attorney or the FOIA Council. Win that intermediary |
| Which kinds of requests do you dread? | Bulk, machine-written, video, email searches: the real load |
| What do you log requests in? Who chose it, and when did it last change? | GovQA, NextRequest, JustFOIA, email or a spreadsheet |
| What did you give the last new deputy? Where did it come from? Who checked it? | Whether a quoted calendar replaces something real |
| Which parts of the rules do requesters most often misunderstand? | What both lanes should say first |
| When the Council's guidance and your attorney's advice differ, what do you do? | Whose sign-off the calendar needs |
| When the records law last changed, how did you find out? | Usually "the Council's training", which names the channel to support, not replace |
| Who would have to approve your office printing an outside resource? What is the last one you printed, and why did you trust it? | The approval path |

**Avoid:**

- "Have you ever missed a deadline?" (and its wedge.md version);
- "Has a requester ever disputed your deadline or gone to the Council or a court?" (live disputes; the attorney will
  forbid it);
- "Could you show me the spreadsheet you used?" by email (a request);
- "Would you use a tool that calculates deadlines?", "How much would you pay?";
- anything that asks them to interpret the law for you.

### 2.6 City planners

| Question | What the answer tells you |
|---|---|
| Think of the last hearing where a notice or advertisement deadline was tight. What happened? | Whether P2's backward calendar is a felt pain |
| Think of the last application where a review deadline mattered. What was it? | Whether statutory review clocks matter too |
| How did your office track that deadline, and who owned it: you, the clerk or the attorney? | The current tool, and who the user is |
| Has a hearing ever been re-noticed, or a decision challenged, because of timing or notice? What happened? | The stakes |
| When you need to know what state law requires of the *procedure* (not the zoning standards), where do you go? | The trusted source |
| What did the last data tool your office adopted replace, and who decided? | The buyer and the approval path |

**Avoid:** "Would a BPMN map of zoning help?"; "What is the Zoning Atlas missing?"; "Could AI read the code for you?"

### 2.7 Municipal attorneys

| Question | What the answer tells you |
|---|---|
| Which state-law questions did departments send you in the last month? | Which models to build after records (open meetings, notices, purchasing, conflicts: C2, C3, C5) |
| Take the last one. How did you answer it, from what sources, and how long did it take? | The time cost and the source to beat |
| When did you last need the same rule in another state? Why, and how did you get it? | Whether cross-state comparison matters |
| When you rely on a non-official source today, what do you check first? | The trust bar for a quoted table |
| Have you checked a citation from an AI tool or a website and found it wrong? What did you do afterwards? (ask before showing anything) | How much candour and quoting you will need |
| Which notice and advertising deadlines does your office review before a hearing? | P2, from the attorney's side |
| Who trains your clerks and department heads on FOIA, and with what material? | A CLE or co-presentation route |

**Avoid:** "Would you trust an AI answer?"; "Would this save you time?"; asking to join members-only lists.

### 2.8 Legal-aid attorneys, self-help and reentry staff

| Question | What the answer tells you |
|---|---|
| Which of your self-help guides or screeners went out of date most recently? How did you find out, and how long did the fix take? (lead with it) | The change-watch nail |
| Where do the rules in your screener come from, and who updates them? | Who maintains them |
| Tell me about the last outside resource you stopped linking to or handing out. Why? Who must approve one, and what do they check? | The approval rule an outside page must meet |
| Tell me about the last time something you handed out turned out to be wrong. How did you reach the people who had it? | Recall |
| After a client files the form you help with most, who tells them the next deadline, and how? | Whether the after-filing gap is real |
| How do clients get the information you give them: paper, phone, text, a website, in person? In what languages? What reading level do your materials aim for, and who checks it? | Format, language and reading level |
| What questions do your non-lawyer staff get that they are not allowed to answer? Where do they send them? | Where the advice line really runs in that programme |
| Without any details about the client: the last time someone asked whether a record would block a job, what did you do, and how long did it take? | Wedge 2's frequency and time cost |
| For the jobs that come up most, what actually blocked people: the licence, an employer's background check, a federal rule, or the cost of training? | The "what governs this job" structure |
| Who in your programme decides which trades you train people for? | The real user of "ask before you train" |
| How does a client get a copy of their own criminal record, and how long does it take? | Whether that step, not the licence, is the process to model |

**Cut from first interviews:** "Which grants pay for your technology work?" Legal-aid technology staff are often
approached by teams who want to be the technical partner on a grant (**judgement**). Ask it only after they have used
something.

**Avoid:** "Would your clients use an app?"; "Would you refer clients to Lexipedia?"; "What makes you trust a summary:
quotes, a review date, a named reviewer?" (it lists lexflow's features as the answers); any question that invites a
story about a specific client.

### 2.9 Journalists and FOI requesters

| Question | What the answer tells you |
|---|---|
| Tell me about the last request that stalled. What did you do next, and when? | Whether the next rung is known and used |
| How did you work out when the answer was due? From when you sent it, or when they got it? | Counting, and the receipt anchor |
| Have you appealed or gone to an oversight body? Why, or why not? | Whether the ladder is the gap, or the will to use it |
| How many requests a year, in how many states? How do you keep track? | Whether they are a multi-state heavy user |
| When a state limits the right to its own citizens, what do you do? | Virginia's § 2.2-3704(A) problem for out-of-state requesters |
| When you file in a new state, what do you read first? | The RCFP guide and MuckRock's place, so you can complement them |
| Do you keep your own list of custodian addresses? How often is it wrong? | The value of checked contacts |

**Avoid:** "Would you use a deadline calculator?"; "What is MuckRock missing?"; "Would you write about lexflow?" (never
ask a journalist for coverage in an interview).

### 2.10 Small-business advisors (low priority)

| Question | What the answer tells you |
|---|---|
| Think of the last client who started a business in this town. What steps did you go through with them? | Whether the local layer is where people get stuck |
| Which step did your last few clients miss or get wrong? | Which step, if any, is worth modelling |
| What did you hand them, and where did it come from? | The artefact to beat |
| How do you find out that a local fee or form changed? | Whether freshness matters to them |

### 2.11 Residents

Reach residents through a library, legal aid or a community partner, with IRB approval and a paid session.

| Question | What the answer tells you |
|---|---|
| Tell me about the last time you had to get something from a government office. What happened? | Which processes hurt, in their words |
| How did you find out what to do? Who did you ask? | The intermediaries to win |
| Was there a deadline? How did you know about it? | Whether deadlines are visible at all |
| What did it cost you: time off, fees, a missed chance? | The stakes |
| Where did you get stuck, and what did you do next? | Whether the next-step view is the gap |
| (In a usability test) In your own words, what does this page tell you to do, and by when? | Comprehension, which a timed task alone misses |

**Avoid:** "Would you use a website that shows the law?"; "Do you trust government websites?"; any question about
criminal records, immigration status, debts or other sensitive facts, unless the IRB has approved it and a legal-aid
partner is in the room.

### 2.12 Wikimedia and Wikidata contributors: listen, then ask in the open

Wikimedians are left out of P6's interviews. On English Wikipedia, a proposal said researchers should describe their
project and "obtain consensus" before mass messaging users; it was never adopted, but it describes what editors expect
([WP:Research recruitment](https://en.wikipedia.org/wiki/Wikipedia:Research_recruitment), per the Wikimedian's
critique). Learn the norms by reading and attending. When a question is needed, ask it once, in the open, after
editing, in the person's own words:

- "How do you want a hijacked official website recorded: deprecated with which reason, and is *usurped URL*
  (Q126327443) used here?"
- "What do you treat as the authoritative list of a state's agencies?"
- "For Virginia, is anyone already working on state agencies or localities? Whose modelling should we follow?" (Read
  first: in 2026 an editor asked on the Govdirectory talk page how to model the Central Virginia Transportation
  Authority, Q140562024, and PlanRVA, Q140562084.)
- "Would a monthly, human-checked worklist of failing official websites for one state help? On which page, and in what
  form?"
- "What is blocking the next US state from being published?"
- "What would you not want from us?"

Ask Wikibase people, not Govdirectory: "Would a federated query joining Wikidata agencies to the duties a statute puts
on them be useful to you?"

**Never ask:** "Could you link to Lexipedia?"; "Can we run a bot?"; "Would you like our statute items imported?"; "What
would make a Lexipedia page worth correcting?" These mark a promoter.

### 2.13 Questions that test the plugin and service idea

Ask these of clerks, legal aid and anyone who mentions a vendor:

- Who pays for the tool you use today, and from which budget line?
- Who must approve a new tool, a printed resource or a new link on your website?
- What happened the last time the law changed and nobody updated your tool or guide?
- If your vendor's system had to be set up with your state's rules, who did that, and how did you check it?
- Who would get in trouble if you relied on this and it was wrong?
- Would you print this? (Clerks and legal-aid staff often work from paper; the answer settles whether paper comes
  before the widget.)

---

## 3. The community plan

### 3.1 Rules for every community

- **Gate 0 first** (§1.9). No links to an unfixed site, in any community.
- **Give before you ask, and give something checkable.** Every first contact carries something the community can
  verify in ten minutes. The one question it asks is "what is wrong or missing?"
- **One community, one person, in their own words.** Posts go out under a named person's own account, with their
  affiliation stated.
- **Show only person-reviewed work outside the team.** "Reviewed" means a named person signed it, with a date. Until
  then the label says "Not yet reviewed by a person". Never show selector drafts (about 0.60) or Ask answers (0.40).
  Machine checks (quotes matched, schemas valid, nets sound) are necessary, not sufficient.
- **Never use a public office's FOIA intake for contact**, and never file requests to test an office.
- **Disclose privately before publishing** anything about a government's own systems (a hijacked domain, a broken
  rights page).
- **Listen before presenting.** Attend a community's meetings before offering a talk. Never present a contribution the
  community has not yet seen.
- **Stop when told no.** If a community says "not like this", stop and adjust. Never repeat a post across lists.

### 3.2 Wikimedia: an editing programme, not a channel

**The framing.** Wikimedians are not a market. Run the Wikimedia track as an editing programme measured by edits that
stick, with its own table (below), outside the content calendar's "call to action" vocabulary. If that vocabulary
leaks into a grant application or a talk page, it reads as outreach marketing.

**Fix the house first (owner, weeks 1 to 2):**

- **DokuWiki licence.** The footer already licenses all content under "CC Attribution-Share Alike 4.0 International".
  The `lexflow:` pages are generated from open-us-law, whose compilation is CC BY-NC 4.0. The task is a decision, not
  a missing statement: either rebuild the quoted sections from the official publishers (the 229-section route, §5.2),
  after which BY-SA or CC0 is true, or post a namespace notice on `lexflow:` stating the CC BY-NC origin until then.
- **The Wikibase.** Its main page calls Lexipedia "a structured, machine-readable encyclopedia of human law" and
  describes deontic and axiomatic ontologies and Akoma Ntoso, none of which the 1,413 items hold. The staged hosting
  policy lists these as required: "The instance's observed use matches the provided information"; "The licensing
  statement is visible on the `Project:Copyrights` page"; "The structured data is in the public domain or released
  under CC0"; and the text licence "allows commercial and non-commercial use and derivatives"
  ([staged policy](https://www.mediawiki.org/wiki/Wikibase/Wikibase.cloud/Hosting_policy); the binding copy at
  wikibase.cloud renders only with JavaScript, so check its wording before submitting).
  - Rewrite the main page to describe what is there, with ambitions under "planned".
  - Create `Project:Copyrights` and `Project:About` (both missing, 10 October).
  - **CC0 is within reach here.** The loader puts section citations, headings and official URLs on the Wikibase, not
    statute quotes; process, step and role items are lexflow's own modelling. Re-check each heading and URL against
    the official publisher, cite the publisher rather than the compilation, and have counsel confirm the CourtListener
    metadata ([models.md](models.md) §9).
  - **Argue external audience, not "staging ground".** In the policy, "a staging ground for a dataset being prepared
    for later contribution ... (for example, to Wikidata)" is an *exception* to one concerning signal, "no clear
    external audience". It is not a general point in an instance's favour, and this strategy says statute and process
    items will not go to Wikidata. A reviewer comparing stated and observed use will see that. The honest case is the
    readers and SPARQL users, plus a working federated query (below).
  - Instances become temporary by default from the end of September 2026, so a review submission is likely due around
    the **end of December 2026** (**estimate**, [communities.md](communities.md) §2.6).
- **The name.** Stop calling Lexipedia an encyclopedia. English Wikipedia's reliable-sources guideline now says
  "Content produced by LLMs, such as AI chatbots (eg. ChatGPT) and Grokipedia, is generally unreliable"
  ([WP:RS](https://en.wikipedia.org/wiki/Wikipedia:Reliable_sources#Sources_produced_by_machine_learning)). An
  AI-checked "-pedia" will be put in that box unless it describes itself plainly ("statute-quoted process models of US
  public-records and business-formation law, with a wiki front end") and names its human reviewers. Keep the "not
  affiliated with the Wikimedia Foundation" line. Do not mimic a Wikimedia site's look
  ([trademark policy](https://foundation.wikimedia.org/wiki/Policy:Trademark_policy)); "Lexipedia" on DokuWiki is not a
  trademark problem in itself (**judgement**).

**Accounts and disclosure:**

- Each person edits under a personal account and writes their own user page.
- The Terms of Use require disclosure of "each and any employer, client, intended beneficiary and affiliation" for
  paid contributions ([Terms of Use](https://foundation.wikimedia.org/wiki/Policy:Terms_of_Use)). Name every
  affiliation: the university; lexflow; that the person maintains Lexipedia (lexipedia.xyz and
  lexipedia.wikibase.cloud), which reuses Wikidata's data; any organisation credited as Lexipedia's builder or
  sponsor, if the person works with it; and, for students, whether the work is paid and by whom. Disclose either way.
- Do not write "open-source" until a licence file exists.
- Points for the person's own user-page wording (not a text to paste): the university and project; the subject
  (state public-records law); that edits are part of that work; that they add facts from official sources with
  references; the Lexipedia maintainer role; any AI assistance in assembling candidate lists.

**What to contribute, in this order, by hand:**

1. **The two hijacked official websites** (Auburn ME, Q758545; Lowellville OH, Q2460456), after a re-check and after
   the private note to each government (§1.5). Find the current site from a government source, add it with P854 and
   P813 and preferred rank, and deprecate the old value with "reason for deprecated rank" (P2241). Ask on the
   Govdirectory talk page which reason the project prefers (for example *link rot*, Q1193907, or *usurped URL*,
   Q126327443, an "access status, for use with P6954") before using one widely. Never delete the old value.
2. **Redirected sites**, the same way, then any small fixes found along the way (a wrong label, a missing P17), even
   when lexflow does not need them. That is what editors do.
3. **The records-act items.** Govdirectory shows an agency's "main regulatory text" (P92) only when the law's item has
   "work available at URL" (P953) and "title" (P1476). On 10 October the Texas Public Information Act (Q7707919) had
   neither, nor P1001; the Illinois FOIA (Q104876318) and California Public Records Act (Q5020891) items had P1001
   but neither P953 nor P1476. Add them from the official publisher. Create items for the Virginia FOIA and the
   Maryland PIA, which have none under those labels. Keep this at the **act** level; section items belong on the
   Wikibase.
4. **Govdirectory's Virginia page.** `Wikidata:WikiProject Govdirectory/United States of America/Virginia` does not
   exist (API, 10 October). The published North Carolina subpage shows the pattern: for each group of agencies, a
   query, "should be N" with an official reference, and a tick when complete. Building it is how Virginia reaches
   "published" on govdirectory.org.
5. **The 14 bodies with no item** (list below), checked for duplicates by label, alias and official domain. Notability
   is not the issue: Govdirectory's guide says "Public agencies are notable so you don't need to worry about that"
   ([CONTRIBUTING.md](https://raw.githubusercontent.com/govdirectory/website/main/CONTRIBUTING.md)). Modelling is:
   how the Texas Board of Criminal Justice relates to the Texas Department of Criminal Justice (Q3819598); creating the
   Maryland parent department before the Central Collection Unit; P576 and P1366 for DC's abolished Board of Parole.
6. **Only after a month of normal history**, and only if a list outgrows hand editing (Virginia's 322 governments
   may): QuickStatements for announced batches, tagged with EditGroups; or a Mismatch Finder upload for *moved* sites,
   where there is an old value and a new external one. Mismatch Finder fits moved sites; it fits hijacked sites
   badly (readers keep landing on spam while a queue waits) and dead hosts worse (there is no external value to
   offer).

**Why hand edits, and why slowly.** The Mass-editing policy recommends "gaining significant experience by doing manual
edits first". In July 2026, 109 sourced, constraint-passing items about one person and his work, made "by an AI agent
(Claude Code) in a semi-automated setup, with me approving before any batch", were mass-deleted and the account
blocked as a "Promotion-only account"
([the operator's own account](https://dev.to/shimo4228/banned-from-wikidata-overnight-i-believed-every-edit-was-compliant-but-all-109-items-were-57nl)).
A new account pasting machine-prepared batches about the bodies its own project models looks too much like that.
Ranks cannot be set reliably with QuickStatements either.

**The 14 bodies** (from `fixtures/entities/agencies.json`; a label and full-text search on 10 October found none,
per the Wikimedian's check):

- Virginia: the Department of Professional and Occupational Regulation; the Department of Health Professions; the
  State Board of Local and Regional Jails; the Compensation Board; the Freedom of Information Advisory Council.
- DC: the Office of Administrative Hearings; the Office of the Chief Financial Officer; the Board of Parole
  (abolished).
- Maryland: the State Department of Assessments and Taxation (the department itself); the Central Collection Unit.
- Texas: the Board of Criminal Justice; the State Auditor's Office; the Office of Court Administration.
- California: the Board of State and Community Corrections.

**Never create items about lexflow, Lexipedia, the university's people or their papers**, and do not propose a
Wikidata external-identifier property for Lexipedia. Link one way, from the Wikibase to Wikidata, until other editors
ask for the reverse.

**What would earn Wikimedians' repeat attention** (from the Wikimedian's critique, in order of value to the projects):

- **A "fix this on Wikidata" link beside every contact Lexipedia shows,** pointing to the item and property it came
  from. It sends editors to Wikidata instead of taking traffic, and it is a template change.
- **The hijacked sites fixed, then the Virginia Govdirectory page built.**
- **The records-act items enriched,** which Govdirectory displays at once.
- **A small, human-checked monthly worklist** on a user subpage: official websites in Virginia that failed two checks
  this month, with the evidence and a SPARQL query. Short, or not at all.
- **A working federated query** from Wikidata agencies to the duties and deadlines Lexipedia's Wikibase says a statute
  places on them. It needs the Wikidata mapping on the Wikibase (formatter URL to P1630, canonical URI to P1921;
  [authority-wikibase.md](../design/authority-wikibase.md) §2.6 says neither is set). It is also a positive signal for
  the hosting review.
- **An organised event, not a campaign:** a "Virginia local government on Wikidata" edit-a-thon with a public library,
  registered on the [Programs & Events Dashboard](https://outreachdashboard.wmflabs.org/) and listed on Wikidata's
  events page, with volunteers editing and no paid editing in scope.

**English Wikipedia: the biggest public lever, done properly.**

- There is no English Wikipedia article titled "Virginia Freedom of Information Act" or "Maryland Public Information
  Act", and "Texas Public Information Act" is 3,709 bytes (API, 10 October; exact titles only, so check redirects and
  other titles before assuming a gap).
- Wiki Education's support for Wikipedia assignments "is free for instructors and their students", and "Students will
  draft their contributions themselves without AI" ([Wiki Education](https://wikiedu.org/teach-with-wikipedia/)).
- So a course assignment (P8) can fill these gaps, on these rules: secondary sources (the RCFP guide, FOIA Council
  publications, law reviews, news), not only the statute; students' own words; affiliation on user pages; **no
  Lexipedia or lexflow citations, ever**. Editing an article about a public law is not a conflict of interest in
  itself; citing your own project in it would be (**judgement**).
- This, not Lexipedia, is how process knowledge about records law reaches the general public.

**No promotional edits on Wikipedia:**

- WP:COI says using material you have written "is allowed within reason, but only if it is relevant ... and is not
  excessive", and that "adding numerous references to work published by yourself and none by other researchers is
  considered to be a form of spamming" ([WP:COI](https://en.wikipedia.org/wiki/Wikipedia:Conflict_of_interest), raw
  text read 10 October).
- The external-links guideline says not to link open wikis without "a substantial history of stability and a
  substantial number of editors" ([WP:EL](https://en.wikipedia.org/wiki/Wikipedia:External_links)), user-generated
  sites "are generally unacceptable as sources", and LLM content is "generally unreliable"
  ([WP:RS](https://en.wikipedia.org/wiki/Wikipedia:Reliable_sources)).
- Lexipedia fails all of these. Do not try.

**Diagrams on Commons, later and carefully.** A person-drawn timeline of a Virginia records request, from the statute,
could be proposed on an article's talk page for uninvolved editors to use or not. An LLM-produced model rendered as a
diagram raises Commons' AI-media questions ([Commons:AI-generated media](https://commons.wikimedia.org/wiki/Commons:AI-generated_media)).
Never add it to an article yourself.

**AI-content norms:**

| Where | The rule | What it means for lexflow |
|---|---|---|
| English Wikipedia | Using LLMs "to generate or rewrite article content is strictly prohibited" (March 2026) ([guideline](https://en.wikipedia.org/wiki/Wikipedia:Writing_articles_with_large_language_models)) | No Claude-drafted article text, ever. Wiki Education's own rule says the same for students |
| Govdirectory | "If your comments, code or other forms of contributions can be recognized as being AI generated you will be blocked". The sentence before it says contributions "that can't be recognized as originating from AI are welcome" ([CONTRIBUTING.md](https://raw.githubusercontent.com/govdirectory/website/main/CONTRIBUTING.md)) | A person writes every issue, talk post and line of code. "Not recognisable" is never the target |
| Wikidata | Meta's list of AI policies by project lists no Wikidata policy or guideline ([list](https://meta.wikimedia.org/wiki/Artificial_intelligence/Policies_by_project)). The bot and mass-editing policies still apply, and the July 2026 block shows how patterns are judged | Edit by hand. Write talk posts, edit summaries, item descriptions and user pages yourself. Say if an AI tool helped prepare a candidate list |
| All Wikimedia projects (proposed) | A global RfC opened on 23 April 2026. Its baseline: disclose AI-generated content, have a human review it, and the editor takes full responsibility. Still open on 10 October 2026; many commenters want disclosure of all AI use, including translation and copyediting ([RfC](https://meta.wikimedia.org/wiki/Requests_for_comment/Artificial_intelligence_policy)) | Plan for the stricter reading everywhere |

**Funding on the wiki side.** The [Rapid Fund](https://meta.wikimedia.org/wiki/Grants:Project/Rapid) gives $500 to
$5,000, but says applicants are not eligible if "the project you have in mind aims to improve third-party websites" or
"the project includes paid editing", and asks for "current contribution history and experience on the target Wikimedia
project(s)" and "organising experience or training experience" (raw text, 10 October). So anything that improves
Lexipedia, its Wikibase or lexflow is out, and so is paid student editing. **Skip cycles 3 (1 November 2026) and 4
(1 February 2027).** The only shape that fits is a community event with volunteers, such as the library edit-a-thon,
with a library or affiliate as co-organiser. Cycle 5 closes **1 April 2027**; decide in week 12 whether that event is
ready. Wiki Education's sponsored Wikidata Institute is one way to train P3's students.

**Events:**

- **Govdirectory Collab Hour:** Fridays at 15:00 CEST, on Jitsi. Go weekly from week 2 and listen.
- **Wikidata Query Service Days:** 17 to 23 October 2026, online ([Wikidata:Events](https://www.wikidata.org/wiki/Wikidata:Events)).
  Expect `maxlag` deferrals during the QLever migration; the contacts design already defers on lag.
- **NARWHAL:** the monthly North American call run by Wikimedia DC and Wikimedia NYC. The place to ask how library
  edit-a-thons are usually run.
- **Wikibase Community User Group:** its mailing list, only after the hosting review is in.
- **Data Reuse Days:** about February 2027 (**unconfirmed**). Watch Govdirectory's 2025 talk on how it monitors data
  quality before proposing anything.
- **Wikimania 2027 and WikiConference North America 2027:** only once there is a community contribution to report.

**The Wikimedia track:**

| Weeks | What | Who | Done when |
|---|---|---|---|
| 1–2 | Fix the house: DokuWiki licence decision per namespace; Wikibase main page rewritten; `Project:Copyrights` and `Project:About`; `lexflow:start` reworded; "For the wiki" gated; labels changed; legacy pages bannered or moved; no "open-source" | Owner | All live |
| 2 onward | Collab Hour weekly; read the talk-page archives and the recent history of Virginia government items | Owner, P3 students | Notes kept |
| 2–3 | User pages with full disclosure, written personally; private notes to the two governments | P3 students; owner sends the notes | Pages live; notes sent |
| 3–5 | Hand edits: the two hijacked websites (after a re-check, a few working days after the notes), then redirects, then small fixes found along the way | P3 | Edits not reverted |
| 4–6 | Records-act statements on TX, IL and CA; VA and MD act items created, by hand | P3 | Statements live, referenced |
| 6–7 | First talk-page post, written by the person, reporting what was done and asking one modelling question; worklist on a user subpage | Owner or P3 lead | A reply; follow the answer |
| 7–10 | Virginia Govdirectory subpage: queries and "should be N" with official references; the 14 bodies created by hand | P3 | Subpage live; counts ticked |
| By week 10 | Wikibase hosting review submitted, arguing external audience; federated-query example on the main page | Owner | Submitted |
| 10–12 | Plan a spring edit-a-thon with a library or affiliate, registered on the Dashboard; decide on a Rapid Fund cycle-5 application for that event only | Owner | Plan written |
| Spring 2027 | A Wiki Education course with a state records-law assignment, if a course fits (P8) | Instructor | Course registered |

**What will not work:**

- driving traffic from Wikipedia, or citing Lexipedia there;
- expecting Wikimedians to edit Lexipedia (a DokuWiki with a separate account and no community guidelines);
- bulk-creating statute or process items on Wikidata;
- a Mismatch Finder upload or a QuickStatements batch as a new account's first act;
- prose "models" labelled "rewrite this";
- percentages in a Wikidata post (bring a list: the item, the old value, the new official page, the date checked);
- off-wiki links in talk posts (put worklists on a user subpage);
- "gift" language;
- claiming "staging ground" in the hosting review;
- a Rapid Fund application for lexflow, Lexipedia or paid editing.

### 3.3 Clerks and records officers

**Who.** Town clerks in small Virginia towns, where the clerk usually is the FOIA officer (**judgement**). "Clerk" in
Virginia often means the elected clerk of the circuit court; say "town or city clerk" or "FOIA officer" and mean it.
The IIMC Records Management Committee and NAGARA deal mainly with retention and archives (**judgement**), so a FOIA
clock is the wrong opener there.

**Venues.**

- **Virginia FOIA Council free trainings** ([training](https://foiacouncil.dls.virginia.gov/training.htm)): the Access
  to Public Records webinar on Tuesday 13 October 2026 at 1:00 p.m.; Local Officials Training on Tuesday 20 October at
  1:00 p.m. and Thursday 12 November at 10:00 a.m. Attend as a listener, check the Virginia model against how the
  Council teaches the clock, and never pitch. The Council is the source clerks trust most.
- **VMCA:** its institutes and newsletter, through a warm introduction. Whether the newsletter takes outside pieces was
  **not checked**.
- IIMC's Annual Conference (Fort Worth, 9 to 12 May 2027) is international; a Virginia clock is a state topic.

**First offers, ranked by how likely a clerk is to use them twice** (from the clerk's critique):

1. **A 2027 FOIA due-date calendar for the office.**
   - Format: a twelve-month grid on two pages. Each received date shows two due dates: the five-working-day date and
     the extended date after a timely written B.4 response. Test the layout with one clerk before offering it to
     three.
   - Defaults: the office's own holidays and closures, confirmed by the office. Where readings differ, print the
     **earlier** date as "meet this" and the later reading beside it with its basis.
   - On the card: the § 2.2-3704(B) words; the B.4 extension ("an additional seven work days"), with the 12-working-day
     total as many bodies' own pages state it (Charlottesville: "a total of 12 working days",
     [city page](https://www.charlottesville.gov/770/Our-FOIA-Responsibilities)); the tolling rules for cost estimates
     and deposits and the 30-day deemed withdrawal (§ 2.2-3704(F), (H)); 60 work days for criminal investigative files
     on police cards; one line on unplanned closures (§ 1-210(E)); links to the Council's guidance and sample letters;
     the schedule used and its date; who checked it, and when.
   - Proof: P1's audit, then the office's own attorney looks at it before staff rely on it. The card says so: "Ask
     your attorney to look at this card before you rely on it."
   - Form: a tagged, accessible PDF attachment, released CC0 once counsel confirms (§5.2). Nothing to install, and the
     office never sends us a request.
   - Commitment: promise the 2028 card in November 2027, from whoever is on the project then.
2. **A ten-minute check of the office's portal** (§4.3).
3. **A private self-check and stale-domain alert** (§1.8), sent only to that locality.
4. **A training-records tracker** for § 2.2-3704.3, timed for the weeks after an election (P2).
5. **If interviews confirm it, the notice and advertisement calendar** (P2).

**Then.** Instead of an IIMC Technical Bulletin with a clerk as lead author (which reads as asking for an
endorsement, and some localities bar it), offer the VMCA a method note written by the team: "how to build a due-date
calendar for your office from the Code", with clerks thanked by name only if they ask.

**Do not:** invite a clerk to "try it with your last request" (a city record in a browser tab); ask clerks in public
how their office counts the half day before Thanksgiving (each office has a factual answer, "were you open?", and
clerks do not state legal readings in public); send a general question about the B.4 anchor anywhere but the Council.

### 3.4 Municipal attorneys

**Venues:** Local Government Attorneys of Virginia, spring and fall 2027 (dates not found); the IMLA Mid-Year
Seminar, Washington DC, 16 to 19 April 2027; the IMLA Annual Conference, Denver, 14 to 18 October 2027
([IMLA](https://imla.org/events/category/conference/list/)).

**First offer, once signed.** The "what happens when the deadline passes" table for VA, DC and MD (then the 11):
deemed denial, the extension or maximum, what stops the clock, who may request, the next rung and its deadline. Every
cell is quoted and linked, the gaps are listed, and a named person signed it (an attorney, for any version offered
to legal aid). Offer it to a Virginia local government attorney to use in a CLE they present.

**Second, to test.** Ask which notice and advertising deadlines the office reviews before hearings (P2). If the
answer is "all of them, by hand", the notice calendar has a second user.

**Avoid:** selector drafts, "AI answers your legal question" framing, and members-only lists.

### 3.5 Legal aid, reentry programmes and law libraries

**The gate.** No link goes to a legal-aid organisation until Gate 0 rows 4, 5, 6, 10, 11 and 12 are done, every page
has a "Free legal help" line worded with the partner (Virginia Law Help; the Reporters Committee's
[Legal Hotline](https://www.rcfp.org/legal-hotline/) for journalists' records questions), and recall works (§4.1).
Nothing on licensing goes out before Gate L (§1.4).

**First offer: a citation-freshness check of their own public guides.** It needs only their public pages, the
statute index and the version flags lexflow already records, and it is checkable in ten minutes. It gives without
asking, and it shows the one thing legal aid will come back for: knowing when the law under a guide changed. A model
of the shape (REWRITE; the person rewrites it, checks every change and signs it):

> Subject: Statute changes affecting <N> of your public guides
>
> I work on lexflow, a research project at <university> that tracks state statutes section by section. We compared
> the sections cited in <organisation>'s public guides on <topic> with the official <state> code as of <date>. <N>
> cited sections have changed since the dates shown on the guides. The attached page lists each one: the guide, the
> section, the old and new words, and the official link. Nothing here is advice, and we looked only at your public
> pages.
>
> If this is useful, I would value 20 minutes to learn how your team keeps guides current. If not, no reply is needed,
> and we will follow up at most once.
>
> <name>, <role>, <university>. An AI tool helped compare the texts; I checked every change myself.

If the check finds no changes, say so. That is useful too, and it is honest.

**Second offer, later: the deadline library, not a deadline.** To the Suffolk LIT Lab's Document Assembly Line
community ([Assembly Line](https://assemblyline.suffolklitlab.org/)), once P1 is done: "a business-day calculator with
statute-sourced holiday calendars and N published test cases per state, under a permissive licence". Let the community
decide which interview needs it. Do not offer an after-filing deadline: no reviewed model covers a court process, and
court rules are not indexed.

**LACI.** LSC funded Atlanta Legal Aid Society to adopt LACI, which Lone Star Legal Aid built to track changes in laws,
regulations and court rules ([models.md](models.md) §2). Find out whether it takes outside contributions (§9). If it
does, lexflow's section-level change matching is a contribution, not a product.

**Money.** Legal aid is a Model A partner at most: a technical partner on a grantee's LSC Technology Initiative Grant,
only if the grantee asks ([LSC](https://www.lsc.gov/grants/technology-initiative-grant-program/how-apply-technology-initiative-grant)).
It is never a Model B customer (§5.1).

**Venues:**

- **LSC ITC27:** 3 to 5 February 2027, New Orleans; registration $800 until 30 October 2026, then $900; no call for
  sessions visible on 10 October ([ITC27](https://www.lsc.gov/itc27)). Attend and listen, if budget allows.
- **LSNTAP's lists:** read for a month before posting ([LSNTAP](https://www.lsntap.org/)).
- **The Stanford Legal Design Lab:** its "AI for Legal Help" class "welcomes partners"
  ([lab](https://justiceinnovation.law.stanford.edu/projects/ai-access-to-justice)). Only after Gate L.

**Law libraries (AALL).** AALL Annual Meeting, Philadelphia, 17 to 20 July 2027. Proposals go through Cadmium; no
deadline was shown on the pages read, and last year's was 22 October 2025, so this year's may be closing now
(**unconfirmed**; check in week 1)
([FAQ](https://www.aallnet.org/conference/resources/proposing-a-program/programproposalfaq/)). Submit only with a
law-librarian co-proposer; otherwise aim for 2028. The offer is "how every quote is checked, where the coverage gaps
are, and what we got wrong". Librarians will ask first about authenticated text, and open-us-law is a third party's
compilation, not the official code.

### 3.6 Journalists and FOI requesters

**Venues:** NICAR 2027 (Denver, 11 to 14 March 2027; IRE membership required; a "Pitch an idea" form with no deadline
shown, [NICAR 2027](https://www.ire.org/training/conferences/nicar-2027/)); Sunshine Week, 14 to 20 March 2027; IRE
2027, Phoenix, 24 to 27 June; VCOG's spring conference (**unconfirmed**).

**The Sunshine Week release,** if the day-90 gate passes (§8.3): the "what happens when the deadline passes" table,
with these columns for each jurisdiction:

- first deadline, in the statute's own unit words;
- extension or maximum (Virginia: seven more work days after a timely written response; Maryland: a written notice
  within 10 working days if production will take longer, a decision within 30 days, and up to 30 more days with the
  applicant's consent; DC: up to 10 more days, not counting Saturdays, Sundays and legal public holidays);
- what stops the clock (Virginia: a cost estimate or a deposit);
- who may request (Virginia: citizens and Virginia media; DC: "Any person");
- what silence means, and the next rung with its deadline;
- where to get free help.

Every cell is quoted and linked, signed by a named person (an attorney, if it is offered to legal aid), and dated.
Offer it first to VCOG.

**For MuckRock and the Reporters Committee: offer corrections, never ask for coverage.** The RCFP guide's last full
edition is 2019, and it invites corrections by email. MuckRock's state guide template asks for the response deadline,
fee waivers, time to appeal and whether a delay can be appealed ([communities.md](communities.md) §9.1). Send a
correction only where the pre-check found a real, sourced disagreement, and never about the Virginia B.4 anchor until
the Council's view is known.

**Follow-on.** A NICAR tipsheet: "find the clause that starts the clock".

### 3.7 City and county managers, and their leagues

- **ICMA 2027** (Philadelphia, 25 to 29 September 2027) takes session proposals until **13 November 2026**, and
  presentations "are not meant to be sales pitches" ([ICMA call](https://conference.icma.org/call-for-presentations/)).
  **Skip it.** No practitioner will present a university project four weeks after first hearing of it
  (**judgement**).
- **ICMA's Academic Symposium** takes a separate call; the 2026 call's priority deadline was 15 May 2026
  ([2026 call](https://www.icma.org/articles/article/2026-icma-academic-symposium-call-presentations)), so expect a
  spring 2027 call (**estimate**). A research talk on "mapping what state law requires of local staff, in the words of
  the law", with no product name, fits it.
- **VML and VACo.** After a Virginia pilot, offer league staff *a private list for each member*: "which old addresses
  in public directories still point at your locality, and whether any now lead somewhere harmful. Nothing is
  published." Never a league-wide percentage.

### 3.8 Planners

lexflow has nothing for planners today. The first version proposed a land-use review clock. The clerk's critique
offers a better bridge: the **notice and advertisement windows** for hearings (§1.2), which planners share with clerks
and municipal attorneys. So:

1. ask question 2 in planner interviews (P2), weeks 3 to 6;
2. if two or more planners or clerks name a notice deadline as tight, build the Virginia backward calendar (P2), and
   offer it to a planning school studio and the regional planning district commission as a "procedure layer";
3. if planners instead name review clocks (site plans, subdivisions), build one of those.

Venues: an ACSP 2027 abstract (deadline about March 2027, **estimate**); an APA Virginia chapter session (summer
2027). NPC27's call closed on 26 August 2026.

### 3.9 Civic tech

**A licence comes first,** because volunteers will not touch an unlicensed repository, and nobody should call it
"open-source" until then. Then:

- list the project on the [Civic Tech Field Guide](https://civictech.guide/);
- offer member groups of the Alliance of Civic Technologists one no-install hack-night task: "check your county's
  listed official website, and fix it on Wikidata by hand, with a reference", with the recording conventions from §3.2.

US Digital Response serves governments, so a government would have to ask it.

### 3.10 Small-business advisors (low priority)

- Ask the nearest SBDC advisor to mark up the Charlottesville start-a-business checklist (SCC filing, fee, BPOL
  licence).
- Advisors refer clients to attorneys and want checklists, not process theory.

### 3.11 Researchers: legal informatics and process modelling

| Venue | Dates | What to do | Status |
|---|---|---|---|
| JURIX 2026 | Toulouse, 8 to 10 December 2026 | Attend if there is budget | Confirmed |
| ICAIL 2027 | Vienna, 5 to 9 July 2027; papers due about 28 January 2027 | A demo paper | **Unconfirmed**: iaail.org shows no 2027 call yet |
| BPM 2027 | KU Leuven, 5 to 10 September 2027; abstracts 4 March, papers 18 March 2027 | A paper | Confirmed |

**The offer.** A paper on "statutes to checked process models with quote grounding", releasing the benchmark with
honest ceilings: Claude-vs-Claude agreement (0.89 for models, 0.69 for answers), human-vs-human agreement from P4, and
the local models' 0.40. It must say plainly who reviewed what. Two conditions come first: a data licence that allows
redistribution (§5.2), and a literature search to confirm the gap before claiming it.

### 3.12 The next twelve months at a glance

[communities.md](communities.md) §15 has the full calendar. These are the dates that need an action:

| Date | What | Action |
|---|---|---|
| 13 Oct, 20 Oct, 12 Nov 2026 | Virginia FOIA Council free webinars | Attend and listen; check the VA model |
| 17 to 23 Oct 2026 | Wikidata Query Service Days | Attend |
| 22 Oct 2026 | IIMC records roundtable | Optional; retention, not access |
| October 2026 (**unconfirmed** deadline) | AALL 2027 proposals | Check in week 1; submit only with a librarian co-proposer |
| 30 Oct 2026 | ITC27 early registration ends | Decide |
| 1 Nov 2026 | Rapid Fund cycle 3 | Skip |
| 3 Nov 2026 | Election Day (Virginia legal holiday) | No clerk contact that week |
| 13 Nov 2026 | ICMA 2027 proposals close | Skip |
| 8 to 10 Dec 2026 | JURIX | Optional |
| ~end Dec 2026 (**estimate**) | Wikibase Cloud hosting review | Owner submits |
| ~28 Jan 2027 (**unconfirmed**) | ICAIL 2027 papers | Demo paper, if the licence allows |
| 1 Feb 2027 | Rapid Fund cycle 4 | Skip |
| 3 to 5 Feb 2027 | ITC27 | Attend if registered |
| 2 Mar 2027 | NSF PESOSE Track 1 | Apply only if the §8.3 rule is met |
| 4 and 18 Mar 2027 | BPM 2027 abstract and paper | Paper |
| 11 to 14 Mar 2027 | NICAR | Tipsheet |
| 14 to 20 Mar 2027 | Sunshine Week | Release the signed table, if the day-90 gate passed |
| 1 Apr 2027 | Rapid Fund cycle 5 | Only for a volunteer edit-a-thon with a library or affiliate |
| Spring 2027 (**estimate**) | ICMA Academic Symposium call | A research talk, no product name |
| 16 to 19 Apr 2027 | IMLA Mid-Year | Attend |
| 26 Apr 2027 | ADA Title II web rule, governments of 50,000+ | Every artefact a city might post must already conform |

---

## 4. Distribution: plugins and embeds

### 4.1 The shape: one engine, one feed, thin surfaces, paper first

- **One source of truth.** A public, read-only, versioned feed of the person-reviewed models only. For each process,
  each entry carries:
  - the clock: amount, **the statute's own unit words**, the internal unit for arithmetic, the anchor (receipt), what
    is due, and what happens on a miss;
  - the counting rules, the holiday calendar and the tolling rules, each with its statute quote;
  - the escalation rungs, with their deadlines and quotes;
  - the official publisher URL, the snapshot release, **the named reviewer and date**, and the model version;
  - the checked office contacts (office titles and shared inboxes only), with a "fix this on Wikidata" link where the
    contact came from Wikidata.
- **Static files, no server.** Static JSON on any static host needs no uptime promise and holds no resident data. It
  keeps lexflow outside Virginia's duties for contractors who operate a personal-information system for an agency
  ([Va. Code § 2.2-3801](https://law.lis.virginia.gov/vacode/title2.2/chapter38/section2.2-3801/)).
- **Paper first for offices.** The clerk calendar and the staff one-pagers are tagged, accessible PDFs. Clerks and
  legal-aid staff often work from paper, and a PDF attachment avoids sending a link to a domain filters may distrust.
- **Text first on screen.** Each surface shows the step list with quotes; the BPMN canvas comes second, because a
  canvas is not accessible on its own. Pages are layered: what this means (plain language, reviewed); what to do next
  and by when (one date per row); what the law says (quotes, expandable); and, on a separate page, notes for builders.
- **The deadline arithmetic runs without a lexflow server.** `lexflow/lab/deadlines.py` uses only Python's standard
  library. Port it to a JavaScript library under a permissive licence, run the 171 lab tests and P1's published cases
  against both, and keep the "nothing about the user leaves the browser" property
  ([lab-research.md](../design/lab-research.md) §1).
- **Recall without a server.** Stamp every case, export and `.ics` file with the model ID, version and date. Keep a
  public known-errors page by model version. When a saved case is opened, compare its version with the current one;
  if it changed, say "The rules this case was counted under have been corrected; check these dates again". Add an
  earlier reminder (for example halfway through the period), not only the one-day `TRIGGER:-P1D`.
- **Modes.** A requester mode (later date as default), a custodian mode (dates and closures only; earlier date as
  "meet this"), and a shared-computer mode, on by default, that keeps nothing after the tab closes.

### 4.2 What to build, in order

| # | Surface | Whose permission | Who it reaches | Prerequisites | Why this order |
|---|---|---|---|---|---|
| 1 | **Gate 0, the public feed and the reviewed pages** on the chosen host | None | Everyone below | §1.9; a code licence | Nothing else is safe to link without it |
| 2 | **The printable custodian calendar** (tagged PDF, CC0 once counsel confirms) and the staff one-pager template | Each office's own attorney, before staff rely on it | Small-town clerks; later, staff programmes | P1's Virginia audit; a named reviewer | Paper is how offices adopt; no install, no data leaves the office |
| 3 | **The JavaScript deadline library**, with per-state test cases and their sources, under a permissive licence; then a docassemble package that calls it | None to publish | docassemble and Assembly Line authors; any site | P1 | docassemble's date helpers have no business-day calendar ([landscape.md](landscape.md) §4). Infrastructure for maintainers, with no advice line in play |
| 4 | **The ten-minute portal check** (ten dates and their lawful due dates, published) | None | Clerks on GovQA, NextRequest or JustFOIA | P1 | Answers the vendor question with data, through the customer (§4.3) |
| 5 | **The DokuWiki plugin `lexflowlab`** on whichever host carries the reviewed pages (thin syntax plugin, loader `script.js`, data inline; [lab-research.md](../design/lab-research.md) §1.6) | lexflow's own wiki | Readers; the place to test with real users | 1, 3 | Already designed |
| 6 | **A Wikidata contribution route**: hand edits first; worklists on a user subpage; Mismatch Finder for moved sites only after a month; a personal user script later; a gadget only by consensus | The community | Wikidata editors, and Govdirectory through Wikidata | §3.2 | Sanctioned, review-first, no bot |
| 7 | **A vendor-neutral embeddable widget**: one "after the office receives your request" card per state, as a web component with an iframe fallback; no cookies, no analytics, prints well | The embedding site | Libraries, legal aid, newsrooms, coalitions | 1, 3; a WCAG 2.1 AA audit | One codebase for every CMS. Whether CivicPlus and Granicus sites allow third-party embeds is **unverified** |
| 8 | **WordPress and Drupal wrappers** around the widget | None to publish; each site to install | Libraries, legal-aid groups and newsrooms on WordPress | 7; GPL-2.0-or-later for the wrappers | WordPress.org requires GPL-compatible code and allows software backed by a documented service ([guidelines](https://developer.wordpress.org/plugins/wordpress-org/detailed-plugin-guidelines/)); Drupal.org requires GPL-2.0-or-later ([licensing](https://www.drupal.org/about/licensing)). Build only after an organisation asks |
| 9 | **Agent-readable state pages**: plain text, one page per state and process, with the quote, the clock, the next step, the contact and the date checked | None | AI answer agents a city points at them | 1 | The CivicPlus route (§4.3), only after Gate 0 and a city attorney's read |
| — | A browser extension using `/api/lookup?url=` | None | Anyone reading a government site | A public server | Later; it needs hosting and support |
| — | A MediaWiki extension | Each wiki's admin | One MediaWiki partner, if one asks | 7 | Only on request; Wikimedia wikis will not install it |
| — | An Accela Civic Storefront app | Accela, then each agency | Accela agencies | — | The only self-serve storefront ([developer.accela.com](https://developer.accela.com/login/login)), but permits are not a wedge |

**A Wikidata gadget is not a near-term goal.** A gadget starts as a personal script, becomes a gadget only after a
proposal at [Wikidata:Tools/Potential gadgets](https://www.wikidata.org/wiki/Wikidata:Tools/Potential_gadgets)
reaches consensus, and is then created by an interface administrator, elected with 75% support and at least 8 votes
([Interface administrators](https://www.wikidata.org/wiki/Wikidata:Interface_administrators)). Not in year one.

### 4.3 Granicus and CivicPlus: what integration would really take

**What exists** ([landscape.md](landscape.md) §1):

- **Neither has a marketplace.** Neither lists a third-party app directory, and neither offers a public API for
  outside developers. API access goes through customer support, product by product.
- **Granicus's partner pages** describe a distributor, resellers, system integrators and cloud hosting
  ([Granicus partners](https://granicus.com/partners/)). **CivicPlus's Integration Hub** connects its own products,
  and its experts set up "all links and integrations" during implementation
  ([Integration Hub](https://www.civicplus.com/tools/integrations-hub/)).
- **Both already sell the records workflow.** Granicus owns GovQA ("nearly 800" agency customers in 2021). CivicPlus
  owns NextRequest ("over 70K active NextRequest users" and "~1 million requests per year", by its own claim).
- **Both are putting AI agents in front of residents:** Granicus GXA (July 2025) and CivicPlus Agent (2026).
- **Clerks will not install a third-party plugin in their records portal.** The vendor set it up, and changes go
  through the vendor's support (the clerk's critique; consistent with the Integration Hub page).

**What would really work, from cheapest to hardest:**

1. **The ten-minute portal check, through the customer.** Publish ten test cases per state: a holiday week, a B.4
   extension letter on day 1 and on day 5, a cost-estimate pause with a reply on day 10, the 30-day deemed withdrawal,
   a deposit, an unplanned closure. A clerk enters them in the portal's test mode and compares. If the portal is
   wrong, the clerk calls the vendor as its customer. Whether these portals model Virginia's extension total or the
   tolling rules was **not checked**; finding out is the point.
2. **Be a source their agents cite.** CivicPlus Agent accepts "external websites" as additional knowledge sources, set
   by the city ([CivicPlus blog, 13 Feb 2026](https://www.civicplus.com/blog/ce/tech-tip-give-residents-faster-answers-with-an-integrated-always-on-civicplus-agent/)).
   But no communications director would point the city's resident-facing agent at a third-party wiki on a `.xyz`
   domain whose front page lists a Honduran charter city (**judgement**); the agent's answers carry the city's name. A
   city would point it at its own § 2.2-3704.1 page. Run the test (20 records questions before and after, scored
   against the reviewed models) only after Gate 0, on the reviewed host, with pages signed by a person and read by the
   city's attorney. Whether GXA accepts outside sources is **unverified**.
3. **A city embeds the widget** on its own site, if the platform allows it (**unverified**).
4. **A rule-pack data agreement with a vendor (Model B).** A vendor licenses reviewed, change-alerted state rule packs
   to configure GovQA or NextRequest correctly across many customers. This needs commercial-clean data (§5.2), a
   named reviewer per pack, liability terms checked by counsel, and an accessibility report for anything residents
   see.
5. **A true plugin.** This would need a vendor partnership that nothing public offers. It is a commercial negotiation,
   not a build.

**What will not work:**

- a free plugin that tracks requests, which competes with products the vendors' customers already have;
- a plugin backed by a paid service built on CC BY-NC data;
- cold pitches to vendor business-development teams before there is evidence.

### 4.4 When to approach the vendors

Only when all of these hold. On today's plan that means month 9 to 12 at the earliest (**estimate**):

- a code licence and a commercial-clean data path for the rule packs (§5.2);
- an accuracy audit passed in at least three states, signed by a named person (P1, P4);
- **at least one customer who ran the portal check, found a discrepancy and raised it with its vendor**, or at least
  one organisation asking for the feed without being chased;
- a WCAG 2.1 AA conformance report for anything residents would see.

**Go through the customer, not cold.** A customer's request carries weight that an outside pitch does not.

### 4.5 "Free plugins, with a service behind them": does it work?

**The shape works, but not with the payers the first version named.**

- WordPress.org sanctions free plugins backed by a documented service, and legal aid runs on free tools with
  grant-funded hosting. Free Law Project and Vaquill run free tiers with paid commercial access.
- **Cities will not pay** for a state's records rules they can get from the FOIA Council free (the clerk's critique,
  **judgement**). **Leagues** have the Council too. **Legal aid will not pay from operating funds** and already has
  LACI (the legal-aid critique, **judgement**).
- **Who might pay:** vendors configuring many customers (a data licence, later); grant programmes; and, for
  government, a university service agreement for training hours or a records-process study, under small-purchase
  rules, once there are references.

**Today it fails on three counts:** the data licence forbids the paid part (§5.2); there are no users yet; and the
vendors already sell the workflow.

**So:** release the free surfaces as non-commercial public-interest work. Treat "paid verification and upkeep" as a
hypothesis to test with vendors' customers (§2.13). It is not a finding.

---

## 5. Sustainability

### 5.1 Three models, in order

Details, evidence and price benchmarks are in [models.md](models.md) §3 and §6.

| Model | When | What is free | Who pays, for what | What it needs first | The candid limit |
|---|---|---|---|---|---|
| **A. A university lab with grants, a course pipeline and a clinic** (the pattern of LII, the Stanford Legal Design Lab, the Suffolk LIT Lab and the early National Zoning Atlas) | Now to 18 months | Everything published | The university: space, credit, a clinic or externship for attorney review, ideally a staff or postdoc line (LII's base is about 60% from its host). NSF PESOSE Track 1 (up to $300,000; next deadline 2 March 2027). A technical role on a legal-aid grantee's LSC TIG, if asked. A Wikimedia Rapid Fund only for a volunteer event | An OSI code licence; IRB and IP sign-off; Gate 0; an attorney of record; one partner organisation with one job; a metrics habit | Grant cliffs, student turnover, LSC's political exposure, and drift into building pipeline instead of serving users |
| **A′. University service agreements** | 12 months on, with references | — | A locality or a league pays the university for FOIA training hours, a records-process review or a study, under small-purchase rules (Va. Code § 2.2-4303(G), per [models.md](models.md) §5.3) | References from Model A users; the university's agreement form; counsel on § 2.2-4303(A) | Consulting, not software; it scales with staff hours |
| **B. Free outputs, paid verification and upkeep, for vendors** (Open Law Library, Free Law Project's data services) | 12 to 36 months | The rules, to read | **Vendors** configuring GovQA, NextRequest or JustFOIA across many customers pay for reviewed state rule packs with change alerts, a named reviewer and a correction channel. About $5,600 to $14,400 per state per process per year (**estimate**: 40 to 80 hours at Free Law Project's published nonprofit rates of $140 to $180 an hour). Not cities, leagues or legal aid (§4.5) | Commercial-clean data; a second human reviewer and an attorney for anything sold; contract terms checked by counsel; customers who found portal discrepancies | Revenue grows with staff hours. Free Law Project took years before services passed half its revenue. Vendors may build it themselves once shown the gap |
| **C. Free embeds and data, with a hosted tier for institutions** (Vaquill's open-us-law, CourtListener, Open States) | Later, only if A shows real use | The widget, the library and the feed | Institutions pay for an uptime commitment, a bulk API, custom questions and support | A, B's clean data, the code-licence decision, a public server, and governance for the open core before any company is involved | Open States survived two changes of owner because it was open, but the community did not keep control |

### 5.2 The licence constraint, and what it takes to lift it

**What the licences say** ([models.md](models.md) §5.1):

- **open-us-law has three layers.** The statute text is public domain (*Georgia v. Public.Resource.Org*). The
  "compilation, normalization, and structuring" is CC BY-NC 4.0. The scrapers are Apache-2.0
  ([README v2026.09.1](https://oss-data-us.vaquill.ai/v2026.09.1/README.md)).
- **NonCommercial turns on the use, not the user.** Creative Commons says the test is "the primary purpose for which
  the work is used, not ... the category or class of reuser"
  ([CC](https://wiki.creativecommons.org/wiki/NonCommercial_interpretation)). A university or a city gets no
  automatic pass.
- **What is live today goes the other way.** The DokuWiki footer licenses everything "CC Attribution-Share Alike 4.0
  International", over pages generated from the CC BY-NC compilation, and
  [credits-research.md](../design/credits-research.md) finding 2 already warns against presenting it under a more open
  licence. That may grant more than lexflow can grant: a question for counsel, and a Gate 0 fix (§1.9, row 6).
- **The other sources:** LOCUS is CC BY-NC 4.0; CourtListener's membership API may not power commercial products or
  tools built for organisations ([FLP](https://free.law/membership/allowed-api-usage/)); pm4py and powl are AGPL-3.0.

**What it takes to lift it, for the wedges:**

1. **Scope everything public and paid to the reviewed models.** The 22 reviewed models quote **229 statute sections**
   in 11 jurisdictions (`fixtures/statutes/*_sections.json`), and the 22 ladders cite about 93. Fetch those sections
   from the official publishers, whose URLs every section already carries. For the Virginia clerk calendar the set is
   small (§§ 2.2-3704, 2.2-3704.2, 1-210, 2.2-3300 and the holiday statutes), so re-fetch it first. Check each
   publisher's terms and robots rules before automating; several block automated clients.
2. **Or buy the licence.** Ask Vaquill AI for a commercial licence or its paid API. That is the quickest start, but
   it makes the service depend on a for-profit upstream.
3. **Drop what cannot be cleared.** Leave LOCUS and CourtListener out of anything paid unless licensed.
4. **Decide the code licence.** AGPL-3.0 fits the pm4py and powl dependencies; AGPL §13 may put vendors off (an
   inference). The deadline engine has no such dependency, so **license the deadline library permissively** (MIT or
   Apache-2.0), which docassemble authors and legal-aid developers need, whatever the rest uses. The WordPress and
   Drupal wrappers are GPL-2.0-or-later.
5. **The Wikibase can be CC0 now, more easily than the wiki.** It carries citations, headings and URLs, not quotes
   (§3.2).
6. **Release clerk artefacts as CC0** once counsel confirms, so a city can reuse them without asking its attorney.
7. **Contribute only facts from official sources to Wikidata (CC0).**
8. **Counsel confirms each step.** [models.md](models.md) §9 lists six questions. Add three:
   - Does using the CC BY-NC corpus only to *find* sections carry its licence into a page that quotes a cleanly fetched
     copy?
   - Does the current CC BY-SA footer need correcting at once?
   - Does the university's insurance cover public legal information and a deadline calculator?

### 5.3 Liability: information with citations, signed by a person

**How others do it:**

- **Texas.** The "practice of law" excludes software and written materials "if the products clearly and conspicuously
  state that the products are not a substitute for the advice of an attorney" (Tex. Gov't Code § 81.101(c),
  [text](https://tcss.legis.texas.gov/resources/GV/htm/GV.81.htm#81.101)). No similar safe harbour was found for VA,
  DC or MD in the legal-aid critique's pass; that is not a finding that none exists (counsel).
- **LII.** It says its compilations "should not be confused with legal advice", and disclaims liability for errors
  ([LII](https://www.law.cornell.edu/lii/terms/documentation)).
- **The case law.** In *Upsolve v. James*, the Second Circuit held that New York's unauthorised-practice rules, as
  applied to individualised advice by trained non-lawyers, are content-neutral, and sent the case back
  ([summary](https://clpblog.citizen.org/second-circuit-holds-unlawful-practice-law-can-apply-to-debt-collection-advice/)).
  The Supreme Court denied certiorari on 30 March 2026
  ([docket 25-948](https://www.supremecourt.gov/search.aspx?filename=/docket/docketfiles/html/public/25-948.html)).

**Two risks, not one.** Counting a statutory period from dates the user enters, with the rule quoted and the counting
shown, is close to general information: the unauthorised-practice risk is moderate. But the **reliance risk** is the
highest in self-help: a wrong "you have until Friday" costs a right. And **for a custodian, the date is the advice**:
the office relies on it, and Virginia names what a court may weigh (an Attorney General opinion, a court decision and,
for the closed-meeting penalty, published FOIA Council opinions; §§ 2.2-3713(D), 2.2-3714(C), per the clerk's
critique). A university page is on neither list.

**lexflow's rules:**

- Every page and artefact quotes the law word for word, in its own unit words, cites it, dates the snapshot, shows how
  each date was counted, and names who reviewed it and when.
- Every surface says plainly that it is not a substitute for the advice of an attorney, and names **free legal help**
  (Virginia Law Help; the RCFP Legal Hotline) as well as the official office to check. For records, the FOIA Council is
  the neutral reference; for a licence denial, the board is the other side and is never the only place named.
- **Never recommend a choice.** Never apply eligibility rules to one person's facts, and never predict a board's or a
  judge's discretion. Describe what a rule says about a category, and give the route to a binding answer.
- **Keep cases in the browser,** with a shared-computer mode on by default. Outcome sharing stays opt-in, with six
  fields and no group under 10.
- **Never show selector drafts (about 0.60) or Ask answers (0.40) as answers.** Never compare lexflow to a lawyer. The
  FTC's DoNotPay order concerned "robot lawyer" claims (from search summaries; the order was not opened).
- **Put risky topics behind staff and an attorney.** Licensing and sealing pages need an attorney of record (P4). The
  partner's own content-approval rule applies, and the page says who approved it.
- **Pull first, fix second.** When a date is reported wrong, the page shows "Under review; do not rely on this date"
  within 4 hours. The fix goes live only after the reviewer of record (an attorney, for legal content) confirms it
  against the text: a clerk's "correction" may be the very miscount the tool exists to catch. Then the known-errors
  page records the error, its exposure and the fix.

**A footer to adapt (for counsel to review):**

> This page is general legal information, not legal advice, and it is not a substitute for the advice of an attorney.
> Every step quotes the statute as published by <official publisher> and checked on <date>. Reviewed by <name, role>
> on <date> (or: Not yet reviewed by a person). Laws change; check with <official office>. Free legal help:
> <partner-chosen line>. Found an error? <corrections address>. Known errors: <link>.

**For a clerk calendar,** add on its face: "Checked by <named person> on <date> against Va. Code § 2.2-3704 and the
FOIA Council's guidance. Your city or county attorney decides how your office counts."

### 5.4 What to do first (owner, in order)

1. **Gate 0's decisions** (§1.9 row 1): one accountable organisation, one host for reviewed material.
2. **Choose the code licence**, with the deadline library permissive. Write a one-page data policy: what is CC BY-NC
   because of its source, and what is lexflow's own.
3. **Gate 0's fixes** (rows 2 to 14), most of them in the first two weeks.
4. **University sign-offs.** The IRB determination for interviews and usability tests. IP or open-source sign-off
   for student code. A law clinic or externship for attorney review (P4). Ask whether the university is a member of
   the Public Interest Technology University Network (**unverified** whether it has a current call).
5. **Take models.md §9's questions to counsel,** plus the three added in §5.2.
6. **Make the lab usable outside the team,** with the receipt question, the modes and the version stamps.
7. **Start a metrics log** (§8.1), including the harm metrics. NSF lists "documented demand for products" among the
   traits PESOSE looks for, and the log is the only honest evidence available
   ([PESOSE](https://www.nsf.gov/funding/opportunities/pesose-pathways-enable-secure-open-source-ecosystems/nsf26-506/solicitation)).

### 5.5 What will not work

| Idea | Why not, now |
|---|---|
| An open-core startup, or software or SaaS sold to cities | CC BY-NC data; no references, insurance or conformance report; the incumbents and cooperative contracts own the channel |
| Rule packs sold to cities, leagues or legal aid | The Council trains cities free; legal aid has no operating budget for it and already has LACI (§4.5) |
| Advertising or donations as the main income | LII's directory and advertising income is about 20% of a budget anchored by Cornell. lexflow has neither the traffic nor the donors |
| A Granicus or CivicPlus plugin as an independent product | No marketplace; they already sell the workflow (§4.3) |
| Grant programmes that are archived, closed or invitation-only | NSF CIVIC is archived. Knight's 2026 call is closed and limited to 26 communities. Arnold Ventures and Schmidt Sciences take no unsolicited proposals ([models.md](models.md) §4) |
| A Rapid Fund for lexflow, Lexipedia or paid student editing | The fund's exclusions (§3.2) |
| Charging for anything built on open-us-law v2026.09.1, LOCUS or CourtListener's membership API | Each forbids it without an agreement |
| Breadth as the pitch ("38,640 governments"), or "43% of websites are stale" | The scores mostly reflect the state tier; the 43% is about directory listings, mostly Census (§1.5) |

---

## 6. The graduate-student programme

### 6.1 Rules for every project

- **One job, one number, one community that can check it.** Each project produces something public that a named kind
  of user can open and say is right or wrong.
- **Virginia first, one semester, one question.** Open-ended goals ("improve Ask", "cover more states") are not
  allowed. AskBench shows that gains there come in hundredths, not tenths, and nobody outside the team can see them.
- **Students draft and attack; a named person signs; an attorney signs legal content.** Students are drafters and
  adversarial checkers, never the final sign-off on anything offered to the public as law.
- **Reverse the burden on practitioners.** The student does the work and brings it to the clerk or attorney to check
  in 20 minutes, three times a term. Clerk time is the scarce input.
- **One named person owns each outside relationship across semesters,** so a clerk who invests in the project in
  October is not met with silence in May.
- **The bridge is the user, not the notation.** A process model becomes mainstream when a clerk, a planner, a
  docassemble author or a Wikipedia reader uses it without knowing it is BPMN. Every project ends in something such a
  person can hold (a printed calendar, a library, a Wikidata statement, an article), with the model underneath.
- **On wikis, students write every word themselves,** under personal accounts with full disclosure, and make ordinary
  fixes beyond lexflow's needs. Their edit histories are the project's reputation for years.

### 6.2 Projects

| # | Project | Wedge | The one number it moves | Start |
|---|---|---|---|---|
| **P1** | **Prove the clock**: the deadline library and its hard cases | 1 | Share of published cases where the library, the Python engine and two reviewers agree | **Now** |
| **P2** | **The clerk's own clocks**: notices, hearing advertisements, training records | Second nail | Clerks or planners who use it for a real hearing and correct it | **Now** (interviews first) |
| **P3** | **Virginia on Wikidata, by hand** | On-ramp | Edits not reverted after 30 days; Virginia's Govdirectory page live | **Now** |
| P4 | Review under a supervising attorney: own a state | All | Models signed by an attorney; human-vs-human agreement | Arranged now by the owner |
| P5 | Citation-freshness check and change watch for one self-help site | Maintainers | Guides whose cited sections were checked; changes confirmed by the organisation | After the first legal-aid interview |
| P6 | User studies | All | Distinct workarounds documented; comprehension, not only speed | Now (IRB first) |
| P7 | A plain-language and Spanish layer for Virginia's "after the office receives your request" page | 1 | Participants who explain the next step correctly in their own words | Spring 2027 |
| P8 | Teaching: reading a statute as a process, with a Wiki Education assignment | Bridge | Courses outside the team that adopt it; articles that survive review | Spring 2027 |
| P9 | Escalation from published decisions | 1 | Rungs with measured real-world timing | Spring 2027 |
| P10 | "What governs this job": licence pages for staff | 2 | Staff-named occupations covered, with no unflagged error | Behind Gate L |
| P11 | Thesis: statute to DMN, checked, or the benchmark | Research | A paper accepted; an outside group runs the benchmark | Any time |

**P1. Prove the clock: the deadline library and its hard cases** (computer science, law)

- **Goal.** One deadline engine, in the browser, that anyone can test.
- **Deliverable:**
  - port `lexflow/lab/deadlines.py` (standard library only) to a JavaScript library under a permissive licence;
  - run the 171 lab tests against both versions;
  - publish 100 hand-worked cases per jurisdiction for VA, DC and MD, each with its source. Make them **the clerks'
    hard cases**: after-hours and holiday receipt; a request sent to the wrong department; a B.4 letter on day 1
    against day 5; a cost-estimate pause with a reply on day 10; the 30-day deemed withdrawal; a deposit over $200; a
    snow closure; a constitutional officer with different holidays; police files at 60 work days;
  - two independent reviewers check each case against the statute and the FOIA Council's advisory opinions (AO-02-08
    already sets day 1 as the first working day after receipt);
  - version stamps on every computed date; the known-errors page; the ten portal-check cases (§4.3).
- **Measure.** 100% agreement, or every disagreement logged and fixed; no known-wrong date live and unflagged for more
  than 4 hours.
- **Who checks it.** A clerk (the cases), a docassemble developer (the library), the attorney of record (P4).
- **Bridge.** A docassemble author calls it, and a clerk checks a printed date against it, without seeing BPMN.

**P2. The clerk's own clocks** (public administration, planning, law)

- **Goal.** Find out whether the deadlines clerks own are a sharper nail than FOIA, then build the smallest useful
  one. This is the project that reaches **planners and municipal attorneys**.
- **Deliverable, weeks 1 to 6:** eight interviews (town clerks, planners, municipal attorneys) built on question 2
  (§2.2). Write up what they said, with no names.
- **Deliverable, if two or more name a notice deadline as tight:** a Virginia backward calendar. Given a hearing date
  and the newspaper's publication days, it gives the window for each notice: § 15.2-2204 (first notice no more than
  28 days before, second no less than five days before; written notice to owners at least five days before),
  § 15.2-1427 (second advertisement no less than seven days before), § 2.2-3707 (meeting notice at least three working
  days before), counted backwards under § 1-210(A), each quoted, printable.
- **Also:** a one-page FOIA training-records tracker for § 2.2-3704.3 (training within two months of taking office,
  then every two calendar years; records kept for five years), timed for the weeks after an election.
- **Measure.** Clerks or planners who use it for a real hearing (self-reported) and correct it; no unflagged error in a
  two-reviewer audit.
- **If the interviews say no,** write up why. That is a finding, and it saves the next team a semester.

**P3. Virginia on Wikidata, by hand** (information science)

- **Goal.** Contribute upstream, with references, by hand, in the community's own format.
- **Deliverable, in order** (§3.2): the two hijacked official websites (after the private notes), then redirects; the
  records-act statements and the VA and MD act items; Govdirectory's Virginia subpage with official counts; the 14
  bodies; a "fix this on Wikidata" link on Lexipedia's contact lines. Mismatch Finder or QuickStatements only after a
  month of hand edits, and only for lists too long to do by hand.
- **Measure.** Edits not reverted after 30 days; no talk-page warnings; the Virginia subpage live; Virginia "published"
  on Govdirectory (stretch). Do not measure edit counts.
- **Skills.** Wikidata modelling and SPARQL; a sponsored Wiki Education Wikidata Institute place if one is available.
- **Rules.** Personal accounts, full disclosure, every on-wiki word the student's own (including edit summaries and
  item descriptions), ordinary fixes beyond lexflow's needs.

**P4. Review under a supervising attorney: own a state** (law clinic or externship)

- **Goal.** Turn "checked by Claude" into "reviewed by a person", and, for legal content, "reviewed by an attorney
  licensed in <state>".
- **Deliverable.** Law students, under licensed faculty, re-read each Virginia, DC and Maryland model against the
  statute, the oversight body's guidance and its advisory opinions; log every disagreement with the AI model and
  resolve it with the text; and the supervising attorney signs. First question: **does the FOIA Council's guidance
  settle whether Virginia's seven extra work days run from the written response or from the end of the five days?**
  (§9). If the opinions are silent, send the Council a general question, and publish and cite its answer.
- **Measure.** Models signed; human-vs-human and human-vs-Claude agreement, reported beside Claude-vs-Claude's 0.89.
- **Feeds lexflow.** The attorney of record that legal aid and Sunshine Week need; a human ceiling for the benchmark.

**P5. Citation-freshness check and change watch** (law, computer science)

- **Goal.** The legal-aid pull, with an organisation's consent.
- **Deliverable.** For one statewide self-help site: list the statute sections its public guides cite; check each
  against the current official text and the guide's own review date; report changes, quoted (§3.5). Then a bill watch
  with Open States, whose data is public domain, that flags bills amending a cited section, measured for precision
  and recall against the session's enacted changes. Contribute to LACI if it takes outside work.
- **Measure.** Guides checked; changes the organisation confirms; precision and recall of the watch.

**P6. User studies** (information science, HCI)

- **Deliverable:**
  - 30 interviews: 6 clerks or FOIA officers, 4 planners, 4 municipal attorneys, 6 legal-aid or coalition content
    maintainers, 5 requesters, 5 reentry or workforce staff (§2). No Wikimedians;
  - a usability test of the lab with 10 people, recruited through a library and paid, including the shared-computer
    mode;
  - the clerk-calendar layout test with one clerk, then three;
  - a timed task ("your request went unanswered; what is your next step and its deadline?") with lexflow against the
    RCFP guide and the statute, plus the comprehension questions (§2.3).
- **Measure.** Distinct workarounds documented; the share who explain the next step correctly in their own words,
  reported separately for participants recruited through literacy or library partners; kill-or-keep decisions
  recorded (§8.3). IRB first.

**P7. A plain-language and Spanish layer** (education, linguistics, law)

- **Deliverable.** For Virginia's records page: "what this means" in five to eight short sentences; "what to do next,
  and by when", one date per row; a reading-level target set with a partner; a Spanish version by a qualified legal
  translator, not machine translation; tested with ten library patrons for understanding.
- **Why.** 28% of US adults performed at Level 1 or below in literacy in 2023 (NCES). Federal LEP guidance under EO
  13166 was revoked in March 2025, so Spanish rests on what audiences expect and partners' own obligations, not on a
  federal mandate (per the legal-aid critique).

**P8. Teaching: reading a statute as a process** (education, law, information science)

- **Deliverable.** An open module of three short lessons on the Virginia records model (the trigger, the actors and the
  clock; counting across real 2026 and 2027 holidays; the next rung when the deadline passes), with exercises, answers,
  a "BPMN in ten minutes" sheet and an instructor's note. Paired with a **Wiki Education course assignment** on a state
  records law, under Wiki Education's rules (§3.2): students' own words, without AI, from secondary sources, never
  citing Lexipedia or lexflow. Whether CALI accepts outside lessons was **not checked**.
- **Measure.** Courses outside the team that adopt the module (target 2 by fall 2027, **estimate**); articles that
  survive review; students' accuracy on the clock task before and after.
- **Bridge.** Teaching reaches people who never asked for a notation, and the Wikipedia article reaches the public,
  with BPMN in neither.

**P9. Escalation from published decisions** (journalism, data science, public policy)

- **Deliverable.** Label each records-ladder rung with how often it is used and how long it takes, from Virginia FOIA
  Council opinions, Illinois PAC opinions and Texas AG letter rulings (the Texas searchable database is from a search
  summary and was not opened).
- **No filed requests.** The first version's "a few real requests" part is dropped: to the office receiving them it is
  a compliance audit, and it would poison the clerk relationships P1 to P3 need.

**P10. "What governs this job": licence pages for staff** (social work, public policy, law), behind Gate L (§1.4)

- **Deliverable.** For the 20 occupations staff name in Virginia and Texas: what governs the job; the binding-answer
  route, its cost and its clock (DPOR's predetermination; TDLR's $10 evaluation); the challenge route and its
  deadline; the fixed "do not tell the client whether they qualify" line; the referral line; a separate plain-language
  client sheet tested with the partner's clients. Signed by an attorney.
- **Measure.** 20 of 20 covered; no unflagged error in a two-reviewer audit; staff lookups.

**P11. Thesis: statute to DMN, checked** (computer science, formal methods, BPM)

- **Options:** translate a reviewed decision table (the § 480 DMN) into Catala and compare outputs over its whole
  domain; map lexflow's IR onto Germany's FIM-BPMN and XProzess, and show where US statutes need what FIM lacks
  (deemed denials, business-day calendars); or write up the models, ladders and AskBench as a citable benchmark with
  honest ceilings and an honest account of who reviewed what.
- **Deliverable.** A paper for BPM 2027 (4 and 18 March 2027) or ICAIL 2027 (**unconfirmed**), with a released
  dataset, once a data licence allows redistribution.

### 6.3 Supervising quality

**The review ladder** (students and Claude both follow it):

1. **Draft.** A student, or Claude, writes the model or page from the statute text.
2. **Adversarial check.** Two reviewers who did not draft it re-read the statute and try to break it, one for legal
   accuracy word by word, one for completeness (missing steps, rungs, exceptions, tolling).
3. **Fix or reject with reasons.** Every finding is applied, or rejected with a reason quoted from the text. In the
   README's first round, 136 findings were raised and all but four were applied.
4. **Machine checks.** `lexflow check-curated` and `check-ask`: every quote word for word, schemas valid, bpmnlint
   clean, Petri nets sound. Unit phrases printed as the statute words them.
5. **Named human sign-off** with a date, before anything leaves the team. **For legal content offered to legal aid,
   or released as a table in Sunshine Week, the sign-off is by an attorney licensed in that jurisdiction** (P4).
   Claude can draft and run adversarial passes. It is never the final reviewer of anything published or sold.

**The benchmark as a regression test.**

- Every change to retrieval, the selector or the scorer is scored on the 22 models (each state held out of its own
  training) and on AskBench.
- A change is kept only if its paired 90% bootstrap interval clears zero.
- Rows carry a version hash, so code changes land before a benchmark run.
- No tuning on a benchmark question without a held-out check. The 10 October planner fix shows why: it lifted the
  question it came from by 0.12 and the others by 0.007.
- Review any new metric adversarially before trusting it. Version 1 of the AskBench scorer was found too generous.

**Human ceilings.** P4 adds human-vs-human agreement beside Claude-vs-Claude's 0.89 for models and 0.69 for answers.
Report all three.

**Weekly rhythm:**

- a 30-minute review of the shared disagreements log;
- once a month, students swap states and try to break each other's models;
- once a month, one practitioner checks one page, in 20 minutes.

**A public corrections and known-errors log.** Each entry records what was wrong, the model version, who reported it
(credited by name only with consent), when the page was pulled, how long it was live, whether exports used it, who
confirmed the fix against the text, and when it went live. Targets: pulled within 4 hours; fixed within two working
days of confirmation.

**Handover.** Each project ends with a short handover note, a re-runnable script, outputs pinned to a snapshot release,
and the named owner of each outside relationship for next term.

### 6.4 Practicalities

- **IRB determination** in week 1, for P2, P5, P6, P7 and P10.
- **IP and open-source sign-off** for student code before release.
- **A clinic or externship agreement** for P4, which also brings supervision and, ideally, insurance.
- **Records awareness.** Every message to a public office is a public record; the project's own notes may be too
  (§2.3).
- **Wikimedia disclosure** for anyone paid or credited for edits (§3.2), and Wiki Education's rules for P8.
- **Credit.** Students are authors of what they write, and contributors are credited on pages. Credit is worded so it
  never implies endorsement.
- **Partners.** No organisation is named as a partner in public until it has agreed in writing.

---

## 7. The 12-week content and outreach calendar

### 7.1 How the loop works

- **Every Monday, Claude prepares a packet:**
  - the week's drafts, with the words tier for each (§7.2);
  - the facts in them, re-checked against the repository and the linked sources, with the date checked;
  - the one ask each contact carries;
  - the Gate 0 status (§1.9), and which links are safe to send;
  - a summary of last week's log.
- **The owner (or a student):**
  - reviews the packet in about 30 minutes;
  - rewrites where §7.2 requires it;
  - sends or posts under their own name;
  - logs what happened.
- **The log is one row per contact or post:**
  - date, channel, audience and piece;
  - link, if public;
  - replies, corrections received, corrections confirmed against the text, corrections applied;
  - pull signals (§2.3);
  - unsubscribes, complaints, and any "we can't use this because…";
  - notes.
- **Claude sees results only when the owner shares the log.**
- **Claude never posts, sends, signs up or edits a wiki.**

**What changes the plan:**

- **A complaint, a "not like this", or a "we can't use this because…":** stop that channel, log the reason, adjust.
- **A reported wrong date:** "Under review; do not rely on this date" on the page within 4 hours; the fix after the
  reviewer of record confirms it against the text; thank the reporter.
- **A pull signal:** follow it before the calendar.

### 7.2 Who writes the words

| Code | Rule | Where it applies |
|---|---|---|
| **OWN** | The person writes from scratch, in their own words. Claude supplies a **facts-only packet**: checked facts, items, links and the one question, as bullets. Never finished prose, and never a "model of the shape" to paraphrase | Wikipedia (any namespace); Wikidata talk pages, Project chat, **edit summaries, item descriptions and user pages**; Govdirectory issues, comments and code; Phabricator tickets; MuckRock and RCFP corrections; Hacker News, which says "Please don't put generated text in HN posts. Write your text yourself" ([guidelines](https://news.ycombinator.com/newsguidelines.html)) |
| **REWRITE** | Claude drafts or outlines; the person rewrites it in their own voice, checks every fact and signs it | Personal emails, including private notes to governments; listserv and mailing-list notes; newsletter pieces; conference abstracts (no product names for ICMA's symposium); social posts and threads |
| **EDIT** | Claude drafts; the person edits it, checks every fact against the source, and publishes it with a prominent note that AI helped draft it **and the name of the person who checked it** | lexflow's own pages: the method page, the "after the office receives your request" pages, the blog, video scripts, changelogs. These are what Wikimedians, librarians and clerks click through to |

**Show HN only once people can try the lab.** HN asks that the work be "something you've made that other people can
play with" ([Show HN](https://news.ycombinator.com/showhn.html)).

### 7.3 The calendar

Week 1 starts on Monday 12 October 2026. The first four weeks are mostly repair, listening and interviews, because
every reviewer said the front door would end the conversation. Measures count replies, corrections and pull from
practitioners, not likes or followers. Targets are **estimates** to be reset at week 6. The Wikimedia track runs
alongside, as an editing programme (§3.2).

| Week | Channel → audience | Piece | One-line message | The one ask | How to measure | Words |
|---|---|---|---|---|---|---|
| **1** (12–18 Oct) | None public. Internal | Gate 0 begins (§1.9); IRB submission; licence decision; AALL deadline checked | — | — | Gate 0 rows done (target 8 of 14); IRB submitted; licence chosen or dated | — |
| **2** (19–25 Oct) | The chosen host → everyone, as the reference for later pieces. Private email → the two or three governments whose old domains now serve spam. Warm-introduction email → first interviewees | (a) Method page: "How we check a quote, and what we have not checked": the snapshot, the word-for-word check, the AI review passes, **no person has reviewed the models yet**, the units, the known-errors page. (b) **Draft 5** (§7.8), a short private note. (c) A 20-minute interview request, no links | (a) "Here is exactly how this was made, and what is not yet checked." (b) "An address listed for your locality now leads to a gambling page; here is the evidence." | (a) None. (b) None needed. (c) 20 minutes | Page live; notes sent; interviews booked (target 5), only once the IRB determination is in | EDIT (a); REWRITE (b, c) |
| **3** (26 Oct–1 Nov) | Interviews → town clerks and one legal-aid content team | Interviews built on §2.2. Leave-behind: the private self-check for the clerk's locality; for legal aid, an offer to run the citation-freshness check of their public guides | — | "May we check the statute sections your public guides cite?" | Interviews held (target 3); answers to questions 2 and 3 logged; consent to the check | REWRITE (requests) |
| **4** (2–8 Nov; Election Day 3 Nov) | No clerk contact. Interviews → requesters and legal-aid maintainers. Email → the legal-aid team that agreed | The citation-freshness check, sent (§3.5 model). Interviews with student newsroom and coalition requesters | "<N> sections your guides cite have changed since their review dates; here they are, quoted." | 20 minutes on how they keep guides current | A reply; changes the organisation confirms; interviews held (target 5 in all) | REWRITE |
| **5** (9–15 Nov) | Interviews → planners and municipal attorneys (P2). Private email → 2 or 3 practitioners (a FOI requester, a coalition, a clerk) | Question 2 interviews. A private pre-check of the VA, DC and MD after-deadline table (with the extension, tolling and who-may-request columns), labelled "checked by <name>; not yet reviewed by an attorney" | "Before we publish this, would you tell us what is wrong in your state's row?" | Mark up one row | Notice deadlines named (P2's test); corrections received (target 3); day-30 decisions recorded (§8.3) | REWRITE |
| **6** (16–22 Nov) | The chosen host → requesters, coalitions, newsrooms. Then a short thread on the owner's own accounts | **Draft 1** (§7.4): the VA, DC and MD pages and table, after the pre-check corrections | "Three records laws, three different clocks, each in the law's own words, counted from when the office receives your request." | "Tell us where it's wrong" | Corrections from outside the team; practitioner replies; aggregate page counts only | EDIT (post); REWRITE (thread) |
| **7** (23–29 Nov; Thanksgiving) | No outreach | Internal: interview synthesis #1; P1 cross-test of the library against the Python engine | — | — | 12 interviews done (target) | — |
| **8** (30 Nov–6 Dec) | Personal email → town clerks who were interviewed or introduced; the VMCA newsletter editor, if it takes outside pieces | **Draft 3** (§7.6): the 2027 FOIA due-date calendar offer, with the December holiday example. Only after P1's Virginia audit and a named reviewer's check | "A free 2027 FOIA due-date calendar for your office, checked against the Code and the FOIA Council's guidance." | Send your office's 2027 closures; ask your attorney to look before you rely on it | Calendars requested (target 3); attorney reviews arranged | REWRITE |
| **9** (7–13 Dec) | The chosen host → requesters. Personal email → VCOG | A screen walkthrough (or a 2-minute video if the lab is usable outside the team): a request received Mon 21 Dec 2026, due Wed 30 Dec if the office closes on 24 Dec and Tue 29 Dec if it is open, and the next rung if no answer comes. For clerks the call is "try it with a date", nothing else. The Virginia page and table offered to VCOG | "From the day the office receives it to the next step, counted and quoted." / "Which rules do requesters get wrong most?" | One answer | Cases started (opt-in reports only); VCOG reply | EDIT (script; the person narrates); REWRITE (VCOG) |
| **10** (14–20 Dec) | The chosen host and email → clerks on portals who asked. Researchers: abstract outline | **Draft 4**: the ten-minute portal check (ten dates and their lawful due dates). BPM 2027 or ICAIL 2027 abstract outline (the person writes the paper) | "Ten dates to test your records portal against the law." | Run it in your portal's test mode | Checks run; discrepancies found and raised with a vendor by the customer | EDIT (check); REWRITE (abstract) |
| **11** (21–27 Dec) | No outreach (offices empty) | Internal: holiday cases re-checked by hand; known-errors page reviewed | — | — | — | — |
| **12** (28 Dec–3 Jan) | The chosen host → everyone, first working day of January. Internal review | "What people corrected this quarter", with each correction, its exposure and its fix; the 90-day review against §8 | "Thank you: here is what you fixed, and what we got wrong." | Keep the corrections coming | Decisions in §8.3 recorded; Q1 plan set | EDIT |

**Alongside, each week (listen, attend, internal):**

| Week | Listen or attend | Internal work |
|---|---|---|
| 1 | Virginia FOIA Council Access to Public Records webinar, Tue 13 Oct, 1 p.m. | Gate 0 rows 1 to 9; IRB submission; code licence; corrections address; counsel questions sent |
| 2 | Wikidata Query Service Days (to 23 Oct); FOIA Council Local Officials Training, Tue 20 Oct; Govdirectory Collab Hour, Fri 23 Oct | Gate 0 rows 10 to 14; Wikidata user pages written personally (**OWN**); start reading LSNTAP; ask the university about a clinic for P4 |
| 3 | Collab Hour | ITC27 early-registration decision (30 Oct); Rapid Fund cycle 3 skipped; P1 hard-case list from the first interviews |
| 4 | Collab Hour | Wikidata hand edits (§3.2); P1 port under way |
| 5 | FOIA Council Local Officials Training, Thu 12 Nov | Day-30 review; ICMA 2027 skipped; P1 Virginia audit under way |
| 6 | Suffolk LIT Lab community meeting (listen) | Wikidata talk-page post (**OWN**) in week 6 or 7 |
| 7 | — (Thanksgiving) | Interview synthesis #1 |
| 8 | NARWHAL monthly call | 20 interviews done; P4 first signed model (target) |
| 9 | JURIX, 8–10 Dec (optional) | Calendars made for clerks who asked |
| 10 | — | Wikibase hosting review submitted (owner) |
| 11 | — | Lab holiday cases re-checked by hand |
| 12 | — | 30 interviews done; 90-day review drafted; Q1 dates set: ITC27 (3–5 Feb), PESOSE (2 Mar), BPM (4 and 18 Mar), NICAR (11–14 Mar), Sunshine Week (14–20 Mar), Rapid Fund cycle 5 for an event only (1 Apr) |

### 7.4 Example draft 1: the "after the office receives your request" post (EDIT)

**Why three jurisdictions and not eleven or fifty.** VA, DC and MD are where places are already researched end to end
and where P1 and P4 start. The other eight reviewed jurisdictions follow once their audits pass; a "50-state map"
would mean showing machine drafts.

**Check before posting:**

- Re-check every quote and date against the official publisher pages linked in the table (they were checked on 10
  October 2026) and against `curated/*/records.json`.
- Fill the `<placeholders>`, including who checked the post and whether an attorney has reviewed it.
- Publish on the host chosen in Gate 0, not on an unfixed site.

---

> ## When is the answer due? Public-records clocks in Virginia, DC and Maryland, in the law's own words
>
> When you ask a government office for public records, the law usually starts a clock. In all three places below,
> the clock starts when the office **receives** your request, not when you send it. How long it runs, what counts as
> a day, what can pause it and who may ask all differ. Here they are, quoted from the official text.
>
> | | Virginia | District of Columbia | Maryland |
> |---|---|---|---|
> | **First deadline** | "within five working days of receiving a request" | "within 15 days (except Saturdays, Sundays, and legal public holidays) of the receipt of any such request" | "promptly, but not more than 30 days after receipt of the application". If it will take more than 10 working days, a written notice "within 10 working days after receipt of the request", giving the time expected, a fee range and the reason |
> | **More time** | If the office answers in writing within the five days, it has "an additional seven work days" (60 work days for criminal investigative files) | By written notice with reasons; it "shall not exceed 10 days (except Saturdays, Sundays, and legal public holidays)" | With your consent, "for not more than 30 days" |
> | **What pauses the clock** | A cost estimate you asked for, until you reply; if you do not reply within 30 days, the request "shall be deemed to be withdrawn". Also a deposit, where charges are likely to exceed $200 | Not covered here | Not covered here |
> | **Who may ask** | "citizens of the Commonwealth", and newspapers, magazines and stations with circulation or broadcasting in Virginia | "Any person" | "a person or governmental unit" |
> | **If the office says nothing** | "Failure to respond to a request for records shall be deemed a denial of the request and shall constitute a violation of this chapter" | "shall be deemed a denial of the request" | Section 4-203 does not use the words "deemed denial"; see the step-by-step page |
> | **The law** | [Va. Code § 2.2-3704](https://law.lis.virginia.gov/vacode/title2.2/chapter37/section2.2-3704/) | [D.C. Code § 2-532](https://code.dccouncil.gov/us/dc/council/code/sections/2-532) | [Md. Gen. Prov. §§ 4-201, 4-203](https://mgaleg.maryland.gov/mgawebsite/Laws/StatuteText?article=ggp&section=4-203&enactments=false) |
>
> **The units are not the same.** Virginia counts "working days", which depend on whether the office was open. DC
> counts days "except Saturdays, Sundays, and legal public holidays". Maryland counts plain days for its 30-day limit
> and "working days" for its notice. Each place has its own holidays, and offices close on other days too.
>
> **A worked example.** Say a Virginia public body receives your request on Monday 21 December 2026. If it is closed
> on Christmas Eve (the state's 2026 calendar gives executive-branch employees that whole day off) and on Christmas
> Day, its five working days are 22, 23, 28, 29 and 30 December, and the answer is due on Wednesday 30 December. If
> the office is open on Christmas Eve, it is due on Tuesday 29 December. If it sends a written explanation in time,
> it has seven more work days. Virginia law does not say plainly whether those seven run from the explanation or from
> the end of the five days; many offices describe "a total of 12 working days", and we show the later date as the
> office's deadline, so that we never call an office late while it may still be in time.
>
> **If no answer comes,** the law treats silence as a refusal. There is no appeal inside the office. You can ask the
> Virginia FOIA Council for an advisory opinion. Or you can ask a court to order the records released: send the
> public body a copy of your petition at least three working days *before* you file it, and the court must then hear
> it within seven days (§ 2.2-3713(C)).
>
> **How we built it.** For each place, an AI system drafted a step-by-step model of the records process from the
> statute text. Separate AI review passes checked it for legal accuracy and completeness, and every quoted phrase was
> matched by machine against a third-party copy of the law (open-us-law v2026.09.1) and linked to the official code.
> <Name> checked this post against the official statutes on <date>. **No attorney has reviewed these models yet.**
> The method, and a list of known errors, are at <method page link>.
>
> **What this is not.**
> - It is general legal information, not legal advice, and not a substitute for the advice of an attorney.
> - It covers the statute only. Regulations, court rules, advisory opinions and local practice can change the answer.
> - It does not cover fees in full or exemptions.
> - Laws change. Each quote is dated; check the official text before you rely on it.
>
> **Where to get help.** In Virginia, the FOIA Council answers questions and gives advisory opinions, and the Virginia
> Coalition for Open Government (VCOG) works on open-government questions. Journalists can call the Reporters
> Committee's [Legal Hotline](https://www.rcfp.org/legal-hotline/).
>
> **Tell us where we're wrong.** If you request or answer records in one of these places and something here doesn't
> match how it works, write to <corrections address>. A reported date is marked "under review" within hours, and we
> fix confirmed errors within two working days. We'll credit you by name if you'd like.
>
> _<Name>, <role>, <university>. This post was drafted with AI assistance and checked line by line against the
> statutes by <name>._

---

### 7.5 Example draft 2: the Wikidata and Govdirectory note (OWN: facts only)

> **There is no prose model here, on purpose.** Govdirectory blocks contributions that "can be recognized as being AI
> generated", and Wikidata judges newcomers on their whole pattern. The person writes the post from scratch, after
> the edits are made, in week 6 or 7, on the Govdirectory talk page. Re-check every fact on the day of posting.

**Facts-only packet:**

- **What was done** (fill in from the person's own contributions): the items edited by hand, with links to the
  diffs; the user subpage holding the worklist and its query.
- **What was fixed:** the official websites of the City of Auburn, Maine (Q758545) and the Village of Lowellville,
  Ohio (Q2460456), after the old domains were re-checked by hand and the governments were told privately. The new
  value is referenced to a government source and preferred; the old one is deprecated with a reason, not deleted.
- **What exists already:** the Central Virginia Transportation Authority (Q140562024) and PlanRVA (Q140562084)
  items and the August 2026 modelling question about them on the talk page. Match that modelling.
- **The one question (pick one):** how should a governing board, such as the Texas Board of Criminal Justice, relate to
  the department it governs (Q3819598)? Or: which reason for deprecated rank (P2241) does the project prefer for a
  usurped official website, and is *usurped URL* (Q126327443) used?
- **The disclosure line, in the person's own words:** affiliation is on the user page; an AI tool helped assemble the
  candidate list; each item was checked against the official page before editing.
- **Leave out:** the 43%; any percentage; Lexipedia; lexflow's features; off-wiki links; any request for links.
- **Second conversation, later and separately:** the Virginia Govdirectory subpage and the 14 bodies.

### 7.6 Example draft 3: a note for town clerks and the clerks' association newsletter (REWRITE)

> **Before sending:** Gate 0 done; the calendar exists, P1's Virginia audit has passed and a named person has checked
> it; the note is in the owner's voice; the newsletter takes outside pieces (**not checked**); counsel has confirmed
> the CC0 release (otherwise drop the sentence about copying and adapting). Send the calendar as a tagged, accessible
> PDF, not a link.

---

> ## A free 2027 FOIA due-date calendar for your office, checked against the Code and the FOIA Council's guidance
>
> A research project at <university> will make your office a 2027 FOIA due-date calendar: a twelve-month grid on two
> pages. For each day a request might arrive, it shows two dates: when the response is due under Va. Code
> § 2.2-3704(B), and when it is due if you send a written explanation within those five working days and take "an
> additional seven work days" (§ 2.2-3704(B)(4)). The calendar is counted with **your** office's 2027 holidays and
> closures, which you send us. It prints the schedule it used and the date we received it.
>
> **Where the law can be read two ways, the calendar prints the earlier date as the one to meet,** and the later
> reading beside it with its basis. One example: the Code does not say plainly whether the seven extra work days run
> from your written response or from the end of the five days. Many offices describe "a total of 12 working days";
> the calendar shows that date and the earlier one.
>
> **It also prints the rules people get wrong:**
>
> - a cost estimate the requester asked for pauses the clock until they reply, and the request "shall be deemed to be
>   withdrawn" if they do not reply within 30 days (§ 2.2-3704(F));
> - a deposit, where charges are likely to exceed $200, pauses it too (§ 2.2-3704(H));
> - criminal investigative files get 60 work days, not 7 (§ 2.2-3704(B)(4)), on any police department's calendar;
> - an unplanned closure, such as a snow day, moves a deadline that falls on it (§ 1-210(E)), so the printed date
>   changes the morning you close.
>
> Each date can be checked by hand against the rule printed beside it. The calendar links to the FOIA Council's
> guidance and sample letters.
>
> **It is free.** There is nothing to install or buy, and we never see your requests. We need only your 2027 holiday
> and closure schedule, which is usually public. It is released so your office can copy and adapt it without asking.
>
> **Who checked it.** <Name, role> checked it on <date> against the Code and the Council's guidance. It is not legal
> advice. Please ask your city or county attorney to look at it before staff rely on it; your attorney decides how
> your office counts. We are glad to send it to your attorney first.
>
> **What we ask in return.** Tell us what's wrong or missing. Corrections go into the calendar and into the
> step-by-step model behind it, with credit if you want it. If a page of ours ever names your staff or is wrong about
> your office, tell us and it will be fixed or removed within two working days.
>
> To get a calendar, send your 2027 schedule, or just your locality's name, to <address>. The 2028 calendar will
> follow in November 2027.
>
> _<Name>, <role>, <university>._

### 7.7 Example draft 4: the ten-minute portal check (EDIT)

A one-page sheet, published on the chosen host and sent only to clerks who asked:

- ten received dates for 2027, each with the lawful due date, the extended date, the rule and how it was counted:
  a holiday week; a closure the office reports; a written response on day 1 and on day 5; a cost-estimate pause with
  a reply on day 10; a 30-day withdrawal; a deposit; a request received after hours; a police file at 60 work days;
- one line: "Enter these in your portal's test or sandbox mode. If a date differs, check it against the rule printed
  here, and raise it with your vendor as its customer. Tell us too, so we can check ours."
- who checked it, and when; the known-errors link.

### 7.8 Example draft 5: a private note to a government about a hijacked old domain (REWRITE)

> **Before sending:** re-check the domain by hand on the day; find the office's general contact (not a FOIA intake);
> attach a screenshot and the date.

> Subject: An old web address listed for <locality> now leads to an unrelated site
>
> While checking public directories of local governments, we found that <old address>, which is still listed for
> <locality> in <the Census file / Wikidata>, now leads to <a gambling site / an unrelated page> (screenshot attached,
> checked <date>). Your current site appears to be <official address>. Residents who follow the old listing may land
> on the wrong site.
>
> We plan to update the public Wikidata entry to your current address in about a week, and we will not publish
> anything naming your locality. Nothing is needed from you. If you would rather we wait, or the address above is
> wrong, just reply.
>
> _(Where only the Census file lists the old address, leave out the Wikidata sentence, and say instead that the
> listing is in the Census Bureau's government directory file.)_
>
> <Name>, <role>, <university>.

---

## 8. Metrics and the 90-day plan

### 8.1 What to measure

| Metric | Definition | How it is measured (no tracking of residents) | 90-day target (**estimate**) | Why it matters |
|---|---|---|---|---|
| Gate 0 | Rows of §1.9 done | Checklist | All 14 by day 30, with row 1's hosting by day 60 | Nothing else can be linked safely |
| Wrong dates live | Errors in a date or unit found on a public page, and hours from report to the page being pulled | Corrections log | 0 known; pulled within 4 hours | The date is the one thing that must be right |
| Exposure | For each confirmed error: days live, and whether any export or `.ics` used it | Known-errors page | Recorded for every error | Recall |
| Sign-off coverage | Share of public pages signed by a named person, and of legal-aid-facing pages signed by an attorney licensed there | Page metadata | 100% of VA, DC and MD pages by a person; 100% of anything offered to legal aid by an attorney | Partners cannot use unsigned material |
| Review age | Days since each page's last review, and since its quoted sections were checked against the official text | Page metadata | Under 180 and under 30 | Freshness |
| Corrections | Distinct errors reported by people outside the team; share confirmed and applied | Corrections log | 10 or more received; all confirmed ones fixed within two working days of confirmation | A clerk's correction is worth more than a page view |
| Pull signals | A workaround described; "when can I use it"; a colleague introduced; data or time given; a budget named; an unprompted request to link, embed or print | Interview and contact log | 5 or more, from at least 2 audiences | The only evidence that the nail is real |
| Interviews | Completed past-behaviour interviews | Log | 30, as allocated in P6 | Grounds every decision in §8.3 |
| The second-nail test | Interviewees (clerks, planners, attorneys) who name a notice or advertisement deadline as tight, unprompted | Log | Recorded; the day-30 rule decides | P2's go or no-go |
| Outside cases | Lab cases started by people outside the team | Opt-in outcome sharing (no group under 10) and voluntary reports, never analytics on the case | 15 within 60 days of the lab being usable outside the team | The requester channel test ([wedge.md](wedge.md) §3.1) |
| Clerk use | Clerks using the calendar 30 days later, with their attorney's look | Follow-up | 3 or more | The government-use test |
| Portal discrepancies | Portal checks run, and discrepancies a customer raised with its vendor | Follow-up | 2 checks run | The vendor question, with data |
| Accuracy | Agreement on 100 published hard cases per jurisdiction | P1's audit | 100% or logged fixes for VA; DC and MD under way | The claim every venue tests first |
| Comprehension | In P6's task, the share who explain the next step correctly in their own words | Usability test | Reported separately for library-recruited participants | Speed alone hides failure |
| Wikidata | Edits not reverted after 30 days; talk-page warnings | Item histories | The hijacked fixes and act statements stick; 0 warnings | Standing in the community |
| Replies per contact | Substantive replies ÷ contacts made | Log | 30% or more | Whether the piece and channel fit |
| Complaints | Unsubscribes, "please stop", moderator actions, and any "we can't use this because…" | Log | 0 complaints; every "can't use" reason logged | Any one means stop and adjust |

**Do not count as success:** page views alone, followers, likes, GitHub stars, edit counts, or the number of
governments "covered".

### 8.2 The 90-day plan

Day 0 is Monday 12 October 2026. Day 90 is about 10 January 2027.

| Days | Goals |
|---|---|
| **0–30** (to about 11 Nov) | Gate 0 done, with the hosting decision made. Code licence; IRB determination; corrections address; known-errors page; counsel questions sent; a clinic approached for P4. 10 interviews, with questions 1 to 4 answered by at least 5 clerks or FOIA officers. The private notes sent and the hijacked-domain fixes made by hand. The first citation-freshness check sent. ICMA skipped |
| **31–60** (to about 11 Dec) | The VA, DC and MD pages published with named reviewers; Virginia's 100 hard cases audited; the clerk calendar offered; the records-act items on Wikidata and the first talk-page post; 20 interviews; P2's go or no-go; the demo walkthrough; the first P4 signed model |
| **61–90** (to about 10 Jan) | 30 interviews and the synthesis; DC and MD audits under way; the portal check published; the Wikibase hosting review submitted; the Virginia Govdirectory subpage under way; the corrections changelog published; decisions recorded (§8.3) |

### 8.3 Decision points

**Day 14 (26 October): the front door.**

- **No hosting decision, or Gate 0 rows 4 to 6 and 10 not done.** No links go to anyone. Interviews continue by warm
  introduction only, with nothing attached but a PDF.
- **Separation chosen but the university host will take months.** Clean up Lexipedia (rows 2 to 14) and give
  `lexflow:` its own front door in the meantime.

**Day 30 (11 November):**

- **No code licence chosen.** Pause anything that depends on it: civic-tech outreach, the library release, plugin work,
  dataset release. Interviews and the Wikidata hand edits continue.
- **The lab is not usable outside the team.** Calls to action switch from "try it" to "check our page". The demo
  becomes a screen walkthrough.
- **Fewer than 5 interviews held.** Change recruitment: warm introductions through university centres and clinics,
  and lead with the self-check or the citation-freshness check.
- **Is the date the pain?** If at least 4 of the first 5 clerks or FOIA officers say the date is handled (a trusted
  portal, training) and their time goes to volume, redaction and estimates: keep the calendar only for towns on email
  and spreadsheets, and move the effort to the portal check and P2.
- **The second nail.** If at least 2 interviewees name a notice or advertisement deadline as tight, unprompted, P2
  builds the backward calendar. If none do, P2 writes up why and switches to the training tracker only.

**Day 60 (11 December):**

- **Fewer than 15 outside cases within 60 days of the lab being usable.** The wedge note's own kill criterion. The
  pain may be real, but the form or the channel is wrong. Move from a tool people visit to things intermediaries hand
  out: the calendar, the table, the library, printed sheets.
- **At least 4 of 5 clerks say their vendor's system already counts the clock and they trust it.** Drop the custodian
  lane for those offices, and keep the portal check. Park "rule audits for vendor configurations" as a Model B
  hypothesis.
- **No outside corrections despite 10 or more practitioner contacts.** Nobody is reading closely. Change the piece
  (shorter, printed, in their venue), not the volume.
- **No attorney of record arranged.** No Sunshine Week table, no legal-aid outreach beyond the citation-freshness
  check, and wedge 2 stays parked.
- **The legal-aid check.** If at least one organisation confirmed a change and asked for more, P5 becomes a standing
  project with that organisation's consent. If two organisations ignore it, stop and ask why in an interview.
- **The Wikimedia community says no, or "not like this".** Stop and adjust. Never push.

**Day 90 (about 10 January):**

- **Sunshine Week release: go** only if the VA, DC and MD audits have passed (100 cases each, two reviewers, every
  disagreement resolved), an attorney of record has signed the table, Gate 0 is done, and at least one FOI
  organisation has agreed to review it. Otherwise release only the signed jurisdictions, or nothing.
- **Wedge 2: start** only if Gate L is met (an attorney of record, the "what governs this job" structure, the
  free-help line, the plain-language layer), at least two staff organisations have given an occupation list and agreed
  to review pages, and a student team owns it (P10). Otherwise keep interviewing.
- **NSF PESOSE Track 1 (2 March 2027): apply** if the licence is chosen and there are at least 3 pull signals and at
  least 2 outside contributors. Otherwise aim for March 2028. NSF looks for ecosystems around tools that "already show
  promise".
- **LSC TIG:** a technical role only if a grantee asks. **Rapid Fund:** cycle 5 (1 April 2027) only for a volunteer
  edit-a-thon with a library or affiliate as co-organiser.
- **WordPress or Drupal wrappers: build** only after an organisation asks to embed. **Vendors: no approach** before
  §4.4's conditions hold.

**The candid fallback.** By day 90 it may be that no audience describes a workaround, no one corrects a page, every
clerk says the portal counts for them, and every legal-aid team says LACI already covers it. Then lexflow is not, for
now, a product. Its real value would be:

- a research dataset and benchmark with honest ceilings;
- a teaching tool, and Wikipedia articles written through Wiki Education;
- referenced fixes to Wikidata, and the records-act items Govdirectory displays;
- a tested deadline library that others can call.

In that case, point the graduate programme at P1, P3, P8 and P11, and stop product work until a user's problem pulls
it back. That would not be failure. It would be the hammer finding out which nails it does not fit, cheaply, before a
year of building.

---

## 9. Not verified

- **Law and practice:**
  - whether the FOIA Council's advisory opinions settle when Virginia's seven extra work days start (P4's first
    question);
  - whether any Maryland provision outside § 4-203 makes silence a denial (the Maryland model treats a missed 30-day
    limit as one; § 4-203's words do not say so);
  - how GovQA, NextRequest and JustFOIA compute Virginia's extension and tolling;
  - the Library of Virginia retention series for request files;
  - unauthorised-practice rules and any software safe harbour in VA, DC and MD;
  - local gift and endorsement policies;
  - Va. Code §§ 2.2-3714, 2.2-3705.4, 19.2-392.15, 42.1-77 and 1-210 are cited from the critiques, which opened them;
    I did not re-open them for this revision.
- **Domains and filters:** whether government or legal-aid mail and web filters block `.xyz`. The Interisle ranking is
  about phishing reports, not filtering.
- **Venue deadlines:** AALL 2027's proposal deadline; ICAIL 2027's dates and deadline; NICAR 2027's pitch deadline;
  VMCA's newsletter policy and 2026 institute dates; ICMA's 2027 Academic Symposium call; Data Reuse Days 2027; the LSC
  TIG 2027 dates; the Wikibase Cloud hosting-review due date (an estimate from the policy timeline).
- **Plugins and integration:** whether Granicus GXA accepts outside sources; whether CivicPlus or Granicus websites
  allow third-party embeds; both vendors' partner terms; DokuWiki's extension-repository rules.
- **Wikimedia:**
  - the outcome of Meta's global AI RfC (open on 10 October 2026);
  - whether the Auburn and Lowellville domains still serve spam today (not opened, deliberately; re-check by hand
    before editing);
  - how quickly Mismatch Finder uploads are reviewed;
  - whether Govdirectory already checks official websites for liveness;
  - the Foundation's paid-contributions FAQ, and how course credit is treated;
  - Wikidata's autoconfirmed thresholds;
  - whether the Virginia and Maryland records acts have Wikipedia articles or Wikidata items under other titles (exact
    titles and labels only);
  - the binding wording of the Wikibase Cloud hosting policy (the staged copy was read).
- **Legal aid:** whether LACI takes outside contributions; legal-aid content-approval norms and reading-level targets
  (the critique's judgement, to confirm in interviews).
- **Funding and teaching:** whether the university is a PIT-UN member and whether PIT-UN has a call; whether CALI
  accepts outside lessons; whether a Wiki Education course fits the spring term.
- **Inherited from the research notes, unconfirmed there:** the Texas Attorney General's searchable letter-ruling
  database; the FTC's DoNotPay order (not opened).
- **Every judgement** in this note, chiefly what clerks find painful and what legal aid would use, is for the
  interviews to test.
- **Estimates:** all targets, prices, effort figures and the "month 9 to 12" vendor timing are estimates for the team
  to reset.

---

## 10. How the three critiques were resolved

### 10.1 Where they agreed (and this note now follows them)

| Point | Clerk | Wikimedian | Legal aid | Resolution |
|---|---|---|---|---|
| Fix the front door before any outreach | Identity, `.xyz`, Próspera, "smart contracts", staff names | Legacy pages, BY-SA footer, Wikibase main page, red-link guidelines | Labels, units, footer, `.xyz` | Gate 0 (§1.9), with a day-14 check |
| "Checked by Claude · quality 1.00" | AI checked AI, claiming certainty | Grokipedia box | Reads as "no lawyer" and "perfect" | Three plain facts on each page; a named person; an attorney for legal content (§1.9 row 4, §6.3) |
| Reviewed pages on a university-controlled host | For clerk material, plus PDF attachments | Recommended "separate" | Recommended | Recommended, with clean-up as the fallback (§1.9 row 1, §8.3 day 14) |
| The custodian needs the earlier date | "Meet this" | — | "Lead with the earlier date" | Three lanes, three defaults (§1.3) |
| Never pitch; give something checkable | Calendar, portal check, private alert | Edits, not posts | Citation-freshness check, not markup | §2.4 rule 2; §3.3; §3.5 |
| The 43% headline misleads | It is the directory, not the city | Mostly Census; redirects counted | — | Retired as a headline; lists, not rates (§1.5) |

### 10.2 Where they conflicted, and how I resolved it

| Conflict | The positions | Resolution, and why |
|---|---|---|
| **Is the records clock the nail?** | The clerk: the date is the easy part for trained officers with portals. Legal aid: the pull is the maintainers' need for dates, tests and change alerts. The first version: people miscount | Keep records first, because it is the only domain with reviewed models and an engine, but aim it at maintainers and small towns, add the portal check, and test the clerk's own clocks (P2) against it at day 30. The interviews, not the critiques, decide (§8.3) |
| **Hijacked domains: fix Wikidata first, or tell the government first?** | Wikimedian: fixing the two items by hand is the best first edit. Clerk: disclose privately to the government before the finding appears anywhere | Both, in order: a private note (draft 5), then the hand fix a few working days later, and never name the places publicly. A Wikidata fix protects readers and is not a publication about the city; the note costs one email |
| **Wikimedia rows in the content calendar** | Wikimedian: take them out; it is an editing programme. The brief: keep the structure | The calendar keeps its shape, but the Wikimedia work lives in its own track table in §3.2, measured by edits that stick, and the calendar only points to it |
| **Who pays for rule packs** | First version: legal aid, leagues, state offices, vendors' customers. Clerk: not cities or leagues. Legal aid: not legal aid | Model B is narrowed to vendors, with grants and university service agreements (Model A′) for government. Legal aid is a Model A partner only (§5.1) |
| **The licence statement** | Wikimedian: decide per namespace; rebuild or notice. Legal aid: a neutral line until counsel. Clerk: CC0 for clerk artefacts | All three: a neutral footer now; a `lexflow:` namespace notice; CC0 for clerk artefacts and the Wikibase once counsel confirms; re-fetch the few Virginia sections the calendar quotes from the official publisher first (§5.2) |
| **Corrections in 48 hours** | Clerk: fix or remove a government's page within two working days. Legal aid: pull within hours; an attorney confirms before the fix goes live | Pull within 4 hours ("under review"); fix within two working days of confirmation by the reviewer of record (§5.3) |
| **The clerk card's layout** | Clerk: a twelve-month grid on two pages. Legal aid: a grid or a lookup by day received; test it first | A two-page grid, tested with one clerk before three (§3.3) |
| **The planner bridge** | First version: a land-use review clock. Clerk: notices and hearing advertisements, shared by three professions | The notice calendar becomes P2, after interviews; review clocks stay an option if planners name them (§3.8) |
| **Wikimedians as interviewees** | First version: 5 of 30 interviews. Wikimedian: not users; learn the norms by reading | Removed from P6; questions asked once, in the open, after editing (§2.12) |

### 10.3 Where a critique was wrong or overstated, on points I could check

- **The clerk's Virginia extension finding.** The clerk said the lab would tell a requester the city was in deemed
  denial four working days early. The lab's timeline already counts the body's extended deadline to the later date and
  shows the earlier one beside it: `tests/test_lab.py` expects 19 November 2026 as the due date and 16 November as the
  "counted from the extension notice" reading, and `instances.py` says it does this "so it never calls a body overdue
  while it may still be in time". The risk the clerk found is real for the **published pages and the model's own
  timer** ("within 7 business days" on the Virginia page) and for the **custodian lane**, so both are fixed here; the
  requester lane in the lab was already safe.
- **The Wikimedian on WP:COI.** The critique said the "form of spamming" wording is not in WP:COI. It is: the raw text
  read on 10 October says "adding numerous references to work published by yourself and none by other researchers is
  considered to be a form of spamming", next to "allowed within reason". §3.2 now quotes both exactly. The first
  version's paraphrase ("many references") was loose, and is fixed.
- **The Wikimedian on the records-act items.** The critique said to add P953, P1476 and P1001 to the Texas, Illinois
  and California items. The Illinois and California items already have P1001; only Texas lacks it. None has P953 or
  P1476 (API, 10 October).
- **Legal aid on "counts from the wrong day".** The engine does count from receipt when a receipt date is entered, and
  warns when it assumes one (`instances.py`). The critique's point stands for the page, which asks only for the
  sending date and shows the assumption as a muted note, so Gate 0 row 11 fixes the page.

---

## Sources

Pages opened for this revision on 10 October 2026 are marked †. The rest were opened by the four research notes or
the three critiques, which say which pages refused automated reads.

**Lexipedia (the project's own sites):**

- † Front page: https://lexipedia.xyz/doku.php?id=start
- † Page index: https://lexipedia.xyz/doku.php?id=start&do=index
- † `lexflow:start`: https://lexipedia.xyz/doku.php?id=lexflow:start
- † Virginia records: https://lexipedia.xyz/doku.php?id=lexflow:va:records
- † Maryland records: https://lexipedia.xyz/doku.php?id=lexflow:md:records
- † DC records: https://lexipedia.xyz/doku.php?id=lexflow:dc:records
- † Zoning Q&A page: https://lexipedia.xyz/doku.php?id=how_do_i_challenge_a_zoning_decision_in_virginia
- † Wikibase main page and page titles (API): https://lexipedia.wikibase.cloud/w/api.php
- Charlottesville records page: https://lexipedia.xyz/doku.php?id=lexflow:va:charlottesville:records

**Virginia, Maryland and DC law, and official guidance:**

- † Va. Code § 2.2-3704: https://law.lis.virginia.gov/vacode/title2.2/chapter37/section2.2-3704/
- † Va. Code § 2.2-3704.1: https://law.lis.virginia.gov/vacode/title2.2/chapter37/section2.2-3704.1/
- † Va. Code § 2.2-3704.2: https://law.lis.virginia.gov/vacode/title2.2/chapter37/section2.2-3704.2/
- † Va. Code § 2.2-3704.3: https://law.lis.virginia.gov/vacode/title2.2/chapter37/section2.2-3704.3/
- † Va. Code § 2.2-3707: https://law.lis.virginia.gov/vacode/title2.2/chapter37/section2.2-3707/
- † Va. Code § 2.2-3713: https://law.lis.virginia.gov/vacode/title2.2/chapter37/section2.2-3713/
- † Va. Code § 15.2-1427: https://law.lis.virginia.gov/vacode/title15.2/chapter14/section15.2-1427/
- † Va. Code § 15.2-2204: https://law.lis.virginia.gov/vacode/title15.2/chapter22/section15.2-2204/
- † Va. Code § 15.2-2285: https://law.lis.virginia.gov/vacode/title15.2/chapter22/section15.2-2285/
- † Va. Code § 54.1-204.1: https://law.lis.virginia.gov/vacode/title54.1/chapter2/section54.1-204.1/
- Va. Code §§ 1-210, 2.2-3705.4, 2.2-3714, 19.2-392.02, 42.1-77 (cited by the critiques):
  https://law.lis.virginia.gov/vacode/title1/chapter2/section1-210/,
  https://law.lis.virginia.gov/vacode/title2.2/chapter37/section2.2-3705.4/,
  https://law.lis.virginia.gov/vacode/title2.2/chapter37/section2.2-3714/,
  https://law.lis.virginia.gov/vacode/title19.2/chapter23.1/section19.2-392.02/,
  https://law.lis.virginia.gov/vacode/title42.1/chapter7/section42.1-77/
- Va. Code § 2.2-3801: https://law.lis.virginia.gov/vacode/title2.2/chapter38/section2.2-3801/
- † Md. Gen. Prov. § 4-201: https://mgaleg.maryland.gov/mgawebsite/Laws/StatuteText?article=ggp&section=4-201&enactments=false
- † Md. Gen. Prov. § 4-203: https://mgaleg.maryland.gov/mgawebsite/Laws/StatuteText?article=ggp&section=4-203&enactments=false
- † D.C. Code § 2-532: https://code.dccouncil.gov/us/dc/council/code/sections/2-532
- † Virginia FOIA Council: https://foiacouncil.dls.virginia.gov/foiacouncil.htm
- † FOIA officer search: https://foiaform.dls.virginia.gov/Home/Searchforms/0
- Virginia FOIA Council training: https://foiacouncil.dls.virginia.gov/training.htm
- Advisory opinion AO-02-08: https://foiacouncil.dls.virginia.gov/ops/08/AO_02_08.htm
- † City of Charlottesville, Our FOIA Responsibilities: https://www.charlottesville.gov/770/Our-FOIA-Responsibilities
- City of Charlottesville, Submit a FOIA Request: https://www.charlottesville.gov/774/Submit-a-FOIA-Request
- Tex. Gov't Code § 81.101: https://tcss.legis.texas.gov/resources/GV/htm/GV.81.htm#81.101
- ADA Title II interim final rule (20 Apr 2026):
  https://www.federalregister.gov/documents/2026/04/20/2026-07663/extension-of-compliance-dates-for-nondiscrimination-on-the-basis-of-disability-accessibility-of-web
- 45 CFR 46.104: https://www.ecfr.gov/current/title-45/section-46.104

**Pain, incumbents and legal help:**

- MuckRock 2017: https://www.muckrock.com/news/archives/2017/mar/14/muckrock-foia-response-data/
- MuckRock 2019: https://www.muckrock.com/news/archives/2019/mar/21/feature-state-data/
- Washington JLARC (2021): https://leg.wa.gov/jlarc/reports/2021/PubRecordsDataCollection/default.html
- Illinois Attorney General, 2024 Public Access report:
  https://illinoisattorneygeneral.gov/news/story/attorney-general-raoul-issues-2024-public-access-report-during-sunshine-week
- Texas Attorney General, FY 2018 release:
  https://www.texasattorneygeneral.gov/news/releases/ag-paxton-open-records-division-experiences-record-setting-year-public-information-requests-and
- CCRC, reproducing IJ's *Barred from Working* (2020):
  https://ccresourcecenter.org/report-card-on-licensing-laws-finds-progress-but-still-a-way-to-go/
- † CCRC Restoration of Rights Project: https://ccresourcecenter.org/restoration-2/
- † NCES, PIAAC 2023 U.S. results: https://nces.ed.gov/surveys/piaac/2023/national_results.asp
- † Interisle, *Phishing Landscape 2025*: https://interisle.net/s/phishinglandscape2025.pdf
- † Virginia Law Help: https://www.virginialawhelp.org/
- † Reporters Committee Legal Hotline: https://www.rcfp.org/legal-hotline/
- Granicus public records: https://granicus.com/solution/public-records-and-compliance/
- Granicus partners: https://granicus.com/partners/
- CivicPlus Integration Hub: https://www.civicplus.com/tools/integrations-hub/
- CivicPlus Agent, external sources (13 Feb 2026):
  https://www.civicplus.com/blog/ce/tech-tip-give-residents-faster-answers-with-an-integrated-always-on-civicplus-agent/
- Accela developer portal: https://developer.accela.com/login/login
- WordPress.org plugin guidelines: https://developer.wordpress.org/plugins/wordpress-org/detailed-plugin-guidelines/
- Drupal licensing: https://www.drupal.org/about/licensing
- FIM process concept: https://www.fimportal.de/assets/prozesse_fachkonzept.pdf?version=2
- LSC TIG awards by year:
  https://www.lsc.gov/grants/technology-initiative-grant-program/technology-initiative-grant-awards-tig-projects-funded-year
- LSC TIG, how to apply: https://www.lsc.gov/grants/technology-initiative-grant-program/how-apply-technology-initiative-grant
- Mozilla Democracy x AI cohort: https://www.mozillafoundation.org/en/what-we-do/grantmaking/incubator/democracy-ai-cohort/

**Wikimedia:**

- † Rapid Fund (raw): https://meta.wikimedia.org/wiki/Grants:Project/Rapid
- † Wikibase Cloud hosting policy, staged copy (raw): https://www.mediawiki.org/wiki/Wikibase/Wikibase.cloud/Hosting_policy
  (binding copy: https://www.wikibase.cloud/hosting-policy)
- † WP:COI (raw): https://en.wikipedia.org/wiki/Wikipedia:Conflict_of_interest
- † WP:RS (raw): https://en.wikipedia.org/wiki/Wikipedia:Reliable_sources
- † English Wikipedia article titles (API): https://en.wikipedia.org/w/api.php
- † Wikidata items and properties (API): Q758545, Q2460456, Q7707919, Q104876318, Q5020891, Q126327443, Q1193907,
  Q140562024, Q140562084, P2241 — https://www.wikidata.org/w/api.php
- † Govdirectory talk page (raw): https://www.wikidata.org/wiki/Wikidata_talk:WikiProject_Govdirectory
- † Govdirectory Virginia subpage (missing; API):
  https://www.wikidata.org/wiki/Wikidata:WikiProject_Govdirectory/United_States_of_America/Virginia
- † Govdirectory CONTRIBUTING.md: https://raw.githubusercontent.com/govdirectory/website/main/CONTRIBUTING.md
- † Wiki Education, teach with Wikipedia: https://wikiedu.org/teach-with-wikipedia/
- Terms of Use: https://foundation.wikimedia.org/wiki/Policy:Terms_of_Use
- Trademark policy: https://foundation.wikimedia.org/wiki/Policy:Trademark_policy
- WP:EL: https://en.wikipedia.org/wiki/Wikipedia:External_links
- English Wikipedia LLM guideline: https://en.wikipedia.org/wiki/Wikipedia:Writing_articles_with_large_language_models
- WP:Research recruitment (failed proposal): https://en.wikipedia.org/wiki/Wikipedia:Research_recruitment
- Meta RfC on an AI policy: https://meta.wikimedia.org/wiki/Requests_for_comment/Artificial_intelligence_policy
- Meta, AI policies by project: https://meta.wikimedia.org/wiki/Artificial_intelligence/Policies_by_project
- Wikidata Mass-editing policy: https://www.wikidata.org/wiki/Wikidata:Mass-editing_policy
- Wikidata Mismatch Finder: https://www.wikidata.org/wiki/Wikidata:Mismatch_Finder
- Wikidata potential gadgets: https://www.wikidata.org/wiki/Wikidata:Tools/Potential_gadgets
- Wikidata interface administrators: https://www.wikidata.org/wiki/Wikidata:Interface_administrators
- Wikidata events: https://www.wikidata.org/wiki/Wikidata:Events
- Commons, AI-generated media: https://commons.wikimedia.org/wiki/Commons:AI-generated_media
- Programs & Events Dashboard: https://outreachdashboard.wmflabs.org/
- Operator's account of the July 2026 block:
  https://dev.to/shimo4228/banned-from-wikidata-overnight-i-believed-every-edit-was-compliant-but-all-109-items-were-57nl

**Venues:**

- ICMA 2027 call for presentations: https://conference.icma.org/call-for-presentations/
- † ICMA 2026 Academic Symposium call: https://www.icma.org/articles/article/2026-icma-academic-symposium-call-presentations
- AALL proposal FAQ: https://www.aallnet.org/conference/resources/proposing-a-program/programproposalfaq/
- LSC ITC27: https://www.lsc.gov/itc27
- IRE, NICAR 2027: https://www.ire.org/training/conferences/nicar-2027/
- IAAIL: https://iaail.org/
- IMLA conferences: https://imla.org/events/category/conference/list/
- Suffolk LIT Lab Document Assembly Line: https://assemblyline.suffolklitlab.org/
- Stanford Legal Design Lab: https://justiceinnovation.law.stanford.edu/projects/ai-access-to-justice
- LSNTAP: https://www.lsntap.org/
- Civic Tech Field Guide: https://civictech.guide/
- Hacker News guidelines: https://news.ycombinator.com/newsguidelines.html
- Show HN: https://news.ycombinator.com/showhn.html

**Licences, liability and funding:**

- open-us-law README v2026.09.1: https://oss-data-us.vaquill.ai/v2026.09.1/README.md
- CC NonCommercial interpretation: https://wiki.creativecommons.org/wiki/NonCommercial_interpretation
- Free Law Project, allowed API usage: https://free.law/membership/allowed-api-usage/
- LII terms: https://www.law.cornell.edu/lii/terms/documentation
- *Upsolve v. James*, summary: https://clpblog.citizen.org/second-circuit-holds-unlawful-practice-law-can-apply-to-debt-collection-advice/
- Supreme Court docket 25-948: https://www.supremecourt.gov/search.aspx?filename=/docket/docketfiles/html/public/25-948.html
- NSF PESOSE (NSF 26-506):
  https://www.nsf.gov/funding/opportunities/pesose-pathways-enable-secure-open-source-ecosystems/nsf26-506/solicitation

**Method:**

- Fitzpatrick, *The Mom Test*: https://www.momtestbook.com/

**In this repository** (read-only): [README.md](../../README.md), [questions.md](../questions.md),
[landscape.md](landscape.md), [communities.md](communities.md), [models.md](models.md), [wedge.md](wedge.md),
[critique-clerk.md](critique-clerk.md), [critique-wikimedian.md](critique-wikimedian.md),
[critique-legalaid.md](critique-legalaid.md), [lab-plan.md](../design/lab-plan.md),
[lab-research.md](../design/lab-research.md), [entities-contacts.md](../design/entities-contacts.md),
[authority-wikibase.md](../design/authority-wikibase.md), [credits-research.md](../design/credits-research.md),
`curated/*/records.json`, `fixtures/statutes/*_sections.json`, `fixtures/entities/agencies.json`,
`docs/answers/va-charlottesville.md`, `lexflow/lab/deadlines.py`, `lexflow/lab/instances.py`, `tests/test_lab.py`,
`dashboard/lab.js`, `lexflow/publish/wikibase_lexipedia.py`, `docs/status.json`.
