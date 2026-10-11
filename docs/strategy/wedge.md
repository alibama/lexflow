# Is lexflow a hammer looking for a nail? Where to start

Status: assessment, 2026-10-10. Research and writing only. This note is the only file written. Nothing was posted,
sent, signed up for or edited anywhere. No wiki was touched.

Method:

* **What lexflow has.** I read `README.md`, `docs/questions.md` and `docs/design/*.md` (read-only). I recomputed the
  per-question AskBench scores from `docs/askbench.json` and listed `fixtures/authority/ladders.json`,
  `curated_ask/*/*.json` and the calendars in `lexflow/lab/deadlines.py`.
* **Pain evidence.** Web pages were read with read-only GETs, one at a time and at least 1.5 s apart per host,
  with the User-Agent `lexflow-research/0.1 (https://github.com/alibama/lexflow)`. Every number below is
  linked to the page it came from, and the [Sources](#sources) list says which pages were opened.
* **Pages that refused the client.** ftc.gov, ij.org, civicplus.com, bls.gov, papers.ssrn.com and businesswire.com
  refused the client (403, a bot challenge or a dropped connection). These blocks were not worked around. Claims
  that rest only on search-result summaries of those pages are marked **(not opened)**.
* **Search budget.** The session's web-search budget ran out before a few last checks: Granicus and CivicPlus
  partner-marketplace terms, the current BJS release count, and a US survey of unpermitted home work. Those points
  are marked **unverified** and listed in §9.
* **People.** People appear only as authors of cited works. No organisation named here is a partner, endorser or
  prospective collaborator of lexflow. Named organisations are users, incumbents or sources.
* **Estimates.** Targets and estimates are marked as such. None of this is legal advice.

---

## 1. The short answer

**Partly, yes.** lexflow was built breadth-first, around what the data made possible rather than around a person
with a problem:

* It covers 38,640 governments, 47 states of statutes, a county confidence map and a Wikibase.
* It has 36 design notes, including C2PA signing, payroll aggregates, tax and SBA data. Most of them were
  written on one day.
* It has no measured users. The only sign of outside demand I found in the README and the design notes is one
  user's licensing question, which the README cites because it was used to tune the planner.
* Its two founding questions were chosen because they are universal and tractable, not because people
  struggle with them:
  * *How do I request public records?* The first step is easy. The pain comes later.
  * *How do I start a business?* State entity formation is already well served by every Secretary of State's
    online filing and by commercial formation services.

That is what a hammer looking for a nail looks like.

**But there are nails here, and lexflow fits two of them.** In both, the law is mostly statutory, the process
has deadlines and an escalation path, people repeatedly miss those deadlines or never take the next step, and
the tools they use today stop at the first document:

1. **After you file a records request: the clock and the next move** (wedge 1, recommended first). This is for
   requesters whose request stalls, and for clerks in small governments who must count their own response
   clock.
   * Evidence of pain: MuckRock found a median agency response time of 31 days, with a 43% success rate. The
     statutory clocks in the states it discusses run from 3 to 20 days. Washington agencies reported 383,433 requests and $101 million spent in
     one year. Illinois's Public Access Counselor took 4,234 new matters in 2024. The Texas Attorney General
     issued 30,939 rulings in one fiscal year (§3.1).
   * Existing tools assemble the first letter and stop, or track requests without the statute's units, tolling
     or appeal path ([lab-research.md](../design/lab-research.md) §2.1).
   * lexflow already has the missing piece for 11 jurisdictions: Claude-reviewed records models, records
     escalation ladders, statute-sourced holiday calendars and a deadline engine.
2. **Licensing after a conviction: can I ask before I train, and how do I challenge a denial?** (wedge 2). This
   is for reentry, workforce and education programs and the people they serve.
   * Evidence of pain: "nearly one in five workers needs a license to work". In 21 states boards may deny
     without considering rehabilitation, and in 12 states applicants have no guaranteed right to appeal (IJ,
     2020). 30 states changed these laws between 2015 and 2020, so the rules people remember are often wrong
     (§3.3).
   * lexflow has Claude references for 5 states, licence-denial ladders for the same 5, a worked DMN for Cal.
     Bus. & Prof. Code § 480, and the official pre-application forms that exist (Virginia DPOR, Texas).

**Stop or postpone** (§5.3):

* Stop growing coverage for its own sake: more states from the learned selector, scoring all 38,640
  governments, county maps.
* Stop designing infrastructure before a pilot asks for it: Wikibase authority modelling, C2PA signing,
  payroll, tax, SBA programs.
* Stop extending state business formation.
* Postpone four areas: building permits (except one small Virginia project), zoning, court debt as a
  stand-alone wedge, and record sealing as a public eligibility screener. Record sealing has the largest
  measured pain, but it is the hardest for lexflow to answer correctly, and it is the area where automation by
  the state is already replacing self-help.

**What lexflow is not good at yet** (§6):

* It cannot answer new questions reliably. AskBench scores 0.40 composite, and the local search puts only 24% of
  the gold sections in its top 10.
* It knows little local law.
* Its contacts are often stale: 43% of verifiable websites were stale in the pilot.
* It does not index the regulations and court rules where many deadlines live.
* It has no public product: the lab's API is not mounted and the dashboard is a local Docker tool.
* Its main statute source is CC BY-NC, which blocks a paid service without a licence.

---

## 2. What exists, and how good it is

| Asset | State today | Quality | Source |
|---|---|---|---|
| Claude-reviewed process models | 22: public records and business formation, 11 jurisdictions (VA, DC, MD, CA, TX, NY, FL, IL, OH, WA, NC) | Every quote word for word; quality 0.99 to 1.00; two rounds of adversarial review | README "What is verified" |
| Learned-selector models | 65 more, across 35 states | About 0.60 agreement with a Claude reference (records 0.55, business 0.65; worst case WA records 0.35). Drafts only. | README "Local models vs Claude" |
| Ask (new questions, any place) | Statute index for 47 states; answers marked unreviewed | AskBench composite **0.40** local vs **0.75** given Claude's sections, against Claude-vs-Claude 0.69. Gold sections in top 10: 0.24. Vital points quoted: 0.19. | README, `docs/askbench.json` |
| AskBench references | 30: six questions (court debt, licence after conviction, phone/commissary, pretrial clock, prison wages, record sealing) × VA, DC, MD, TX, CA | All pass `check-ask`; reviewed adversarially | `curated_ask/` |
| Escalation ladders | 22 ladders, 143 rungs: records in all 11 jurisdictions; business in FL, VA, DC; record sealing in CA, MD, VA; licence denial in CA, VA, DC, MD, TX | All 280 quotes grounded; 12 rungs depend on rules outside the corpus (mostly court rules) | [authority-ladders.md](../design/authority-ladders.md) §1 |
| Process lab | Case tracking, statute-sourced holiday calendars for the federal government and the 11 jurisdictions, `.ics` reminders, opt-in outcome sharing with no group under 10 | 171 tests. **The router is not mounted**: no one outside a dev harness can start a case. | [lab-plan.md](../design/lab-plan.md) §0 |
| Official forms | 82 forms, portals, letters and guides; 72 answered HTTP 200; tied to 74 step references | Sampled 15 of 82 re-checked | [forms-research.md](../design/forms-research.md) §1 |
| Contacts | 55,181 rows, 99.2% Census GUS 2022 addresses or websites; Wikidata checked for 3 of 51 states | Pilot: **43% (±14) of verifiable websites stale**; 3 of 55 sampled sites now serve gambling or spam pages | [entities-contacts.md](../design/entities-contacts.md) D8 |
| Local law | LOCUS headings scanned for Virginia only: local law found for 110 governments | Headings, not text; CC BY-NC; "used to find law, never to cite it" | README "Known gaps" |
| Lexipedia | 43 DokuWiki pages; 1,413 Wikibase items | Only reviewed models published | README |

Per-question AskBench composites, recomputed from `docs/askbench.json` (5 states each). They matter for choosing a
wedge:

| Question | Local pipeline | Claude's sections given (oracle) |
|---|---|---|
| `license_conviction` | 0.375 | 0.760 |
| `court_debt` | 0.394 | 0.782 |
| `record_sealing` | 0.403 | **0.596** (lowest of all six) |
| `pretrial_clock` | 0.454 | 0.814 |

Even with the right sections in hand, record sealing is the question lexflow answers worst. Its references need 9
to 30 sections each and turn on offence lists and waiting periods.

---

## 3. The candidate wedges

Each subsection answers the same questions:

* who has the pain;
* how often;
* what they use today;
* what lexflow has;
* what is missing;
* how a 90-day pilot would be judged;
* the risks;
* the verdict.

### 3.1 Public-records requests across jurisdictions: deadlines, fees, appeals

**Who has the pain.**

* *Requesters.* Local journalists, student newsrooms, researchers, watchdogs and residents.
  * Above all, people who file in several states. Each state has its own clock, its own units (working days,
    business days, calendar days) and its own appeal route.
  * The pain comes after filing: no answer, a partial answer, a large fee estimate, a denial.
* *Custodians.* Clerks and records officers, especially in small governments that do not buy request software.
  They must count a statutory clock across their own holidays and closures.

**How often.**

* **Delay.** MuckRock's 2017 analysis covered more than 30,000 requests to more than 6,000 agencies. It found a
  median of 31 days among the agencies' average response times, and a 43% success rate
  ([MuckRock 2017](https://www.muckrock.com/news/archives/2017/mar/14/muckrock-foia-response-data/)).
* **Deadlines missed.** In 2019, across 2,600 agencies, Oregon averaged 148 days, Iowa 121 and Texas 95, while
  Vermont, Idaho and Rhode Island averaged under 15 days. Massachusetts has a ten-day clock, yet only 1,598 of
  4,208 MuckRock requests to its agencies were complete
  ([MuckRock 2019](https://www.muckrock.com/news/archives/2019/mar/21/feature-state-data/)). Both analyses are
  dated and come from one platform's users, who skew towards journalists.
* **Government volume and cost.** In 2019, 208 Washington agencies reported to JLARC that they received 383,433
  requests and spent $101 million responding. 1,529 of the 2,418 agencies did not report, and 82% of those have
  annual budgets under $10 million ([JLARC 2021](https://leg.wa.gov/jlarc/reports/2021/PubRecordsDataCollection/default.html)).
  That long tail of small agencies has the same clocks and little help.
* **Disputes.** Illinois's Public Access Counselor received 4,234 formal requests for assistance in 2024, more
  than 350 a month, and more than 59,000 since 2010
  ([Illinois AG, 17 Mar 2025](https://illinoisattorneygeneral.gov/news/story/attorney-general-raoul-issues-2024-public-access-report-during-sunshine-week)).
  In fiscal 2018, the Texas Attorney General's Open Records Division issued 30,939 rulings and answered more than
  10,000 hotline calls
  ([Texas OAG, 19 Sep 2018](https://www.texasattorneygeneral.gov/news/releases/ag-paxton-open-records-division-experiences-record-setting-year-public-information-requests-and)).
* **New pressure.** A July 2026 New York editorial describes "bot-driven FOIL requests" flooding local records
  offices, with Chautauqua County adding a position to handle them
  ([Post-Journal, Jul 2026](https://www.post-journal.com/opinion/in-our-opinion/2026/07/in-our-opinion/)).
  This is opinion journalism, not data.
* **Federal context.** lexflow is about state law, but the federal trend points the same way: 1,501,432
  federal FOIA requests in FY 2024, up 25.15%
  ([DOJ OIP](https://www.justice.gov/oip/blog/summary-fiscal-year-2024-annual-foia-reports-published)), and a
  backlog that grew from 200,843 to 267,056
  ([Brechner Center](https://brechner.jou.ufl.edu/2025/04/30/foia-requests-denials-surge-fy-2024/)).

**What they use today.**

* *Requesters*:
  * the RCFP Open Government Guide, a 50-state narrative reference
    ([RCFP](https://www.rcfp.org/open-government-guide/));
  * the SPLC letter generator, which writes the first letter only;
  * MuckRock, which files and tracks in public, counting calendar days
    ([lab-research.md](../design/lab-research.md) §2.1);
  * the state oversight bodies themselves (Virginia FOIA Council, Illinois PAC, the Texas AG hotline).
* *Custodians*: request-management products sold by the two largest civic-software vendors.
  * Granicus bought GovQA in August 2021. GovQA then served "nearly 800 government customers", and the
    announcement said some governments saw "a 500% increase in requests"
    ([Granicus, 26 Aug 2021](https://granicus.com/press-release/granicus-acquires-leading-compliance-software-provider-govqa-to-help-government-agencies-manage-exponential-increase-in-public-records-requests/);
    a vendor's claim).
  * CivicPlus agreed in May 2022 to acquire Optimere, the owner of NextRequest **(not opened**: civicplus.com
    refused the client; the deal is from search-result summaries of CivicPlus's news page and of
    ArchiveSocial's republished release).
  * Small agencies use spreadsheets and email. That is the vendors' own pitch in the GovQA release.

**What lexflow already has.**

* Claude-reviewed records models for VA, DC, MD, CA, TX, NY, FL, IL, OH, WA and NC.
* Records escalation ladders for all 11 (3 to 10 rungs each).
* Statute-sourced holiday calendars and a deadline engine for the same 11 plus the federal government. The
  engine handles business days, roll-forward rules, part-days and deemed denials, and it shows *how* each date
  was counted.
* Request forms and sample letters where they exist, and `no_form` notes where the statute sets the content.
* A local-first case tracker with `.ics` reminders.

No tool reviewed in [lab-research.md](../design/lab-research.md) §2.1 counts business days from a calendar sourced in
statute.

**What is missing.**

1. **A public surface.** The lab router is not mounted. Lexipedia shows the models but not "I sent it on this
   date; what now?"
2. **Records-office contacts.** There are verified records contacts for 3 places only, and the contact pilot found
   43% of verifiable websites stale.
3. **Fee rules and exemptions.** The models cover the requester's path and the custodian's response types. Fee
   limits beyond the statute (advisory opinions on "actual cost") and exemption-by-exemption checks
   ([questions.md](../questions.md) B1, B2) are not modelled.
4. **Rules outside the statute.** Agency regulations (for example DC's 1 DCMR), court rules for the judicial
   rungs, and local closures.
5. **States outside the 11.** Pennsylvania's Right-to-Know Law, Hawaii and Nebraska are not in the downloaded
   files. AR, CO, GA, MS and TN have no statute file at all.

**A 90-day pilot.** Use the three places already researched (VA, DC, MD) plus Illinois, where an oversight body
takes more than 350 new matters a month.

Product:

* Mount the lab.
* Publish one Lexipedia page per state: "after you file: deadlines and next steps".
* Offer two views:
  * the requester's: sent on date X, so the answer is due Y; if it is late, here is the next rung and its
    deadline, quoted;
  * the clerk's: received on date X, so the response is due Y; the lawful responses and the extension rule.

Measures. The targets are estimates for the team to set, not predictions.

| Measure | How | Target (estimate) |
|---|---|---|
| Deadline accuracy | 100 hand-worked cases (dates, holidays, closures, extensions) per state, each checked by two independent reviewers against the statute and published advisory opinions | 100% agreement or a logged, fixed disagreement; no known-wrong date live for more than 48 hours |
| Real use | Cases started by people outside the team (counted locally per opt-in, or by voluntary report) | 50 or more cases; 20 or more returning users |
| Changed behaviour | Exit interviews: did the user follow up, appeal or go to the oversight body because of the tool? | 5 or more of 15 interviewees name a concrete action |
| Time to answer | Task test: "your request went unanswered; what is your next step and its deadline?" With lexflow vs with the RCFP guide and the statute | Faster and more often right; measure, do not assume |
| Custodian use | Clerks in small localities using the response clock for a month | 3 or more, with 2 or more saying they would keep it |
| Pull | An organisation asks to link to or embed it without being chased | At least 1 |

Kill or rethink if fewer than 15 outside cases have been started by day 60. That would mean the pain is real but
lexflow's channel or form is wrong.

**Risks.**

* *Accuracy.* A wrong date can cost someone an appeal window. The mitigations are already in the design:
  show the counting, quote the rule, show other readings where the law is open. A **wrong rung** (sending
  someone to a forum that cannot act) is worse than a wrong date, so the 12 rungs that depend on court rules
  outside the corpus need human checks.
* *Liability.* This is general legal information about deadlines. Keep the tool from telling a person whether
  an exemption fits their record ([questions.md](../questions.md) B1 says the same).
* *Maintenance.* The holiday calendars need yearly updates (Virginia's DHRM schedule is already handled), and
  records acts are amended from time to time. Each of the 11 models needs a re-check when its act changes.
  There is no built process yet that flags this. The canonical-package design marks a package `stale` when a
  new open-us-law release changes a quoted section, but it is a design
  ([canonical-workflows.md](../design/canonical-workflows.md)).

**Verdict: the best first wedge.** It has the strongest fit, the cheapest next step (mount what exists), crisp
statutory rules, and evidence of repeated pain on both sides of the counter. Its weakness: for an occasional
requester, the need comes once and is hard to reach. Expect heavy users to be multi-state requesters and small
clerks' offices, not the general public.

### 3.2 Record sealing and clean-slate eligibility

**Who has the pain.**

* People with records, and their families.
* Legal aid and reentry organisations that run clinics and screeners.

**How often.** Here the pain is the largest measured of any candidate.

* In Michigan, "just 6.5%" of people legally eligible for expungement obtained it within five years. Those who
  did saw wages rise "by over 22%" within a year
  ([Prescott & Starr, 133 Harv. L. Rev. 2460 (2020)](https://harvardlawreview.org/print/vol-133/expungement-of-criminal-convictions-an-empirical-study/)).
* Nationally, "at least twenty to thirty million American adults" fall into the "second chance expungement
  gap" ([Chien, 119 Mich. L. Rev. (2020)](https://michiganlawreview.org/journal/americas-paper-prisons-the-second-chance-gap/)).
* About 19 million people had felony convictions in 2010
  ([Shannon et al., Demography 2017](https://pmc.ncbi.nlm.nih.gov/articles/PMC5996985/)).

**What they use today.**

* Legal aid screeners, such as Legal Services of New Jersey's "Clearing Your Record Online" toolkit
  ([LSNJ](https://lsnjlaw.org/pages/expunge)).
* Clinics, and the courts' official forms (fillable statewide forms exist in CA, VA, MD and IL:
  [forms-research.md](../design/forms-research.md) §1).
* **Increasingly, nothing, because the state does it.** 14 states and DC have passed Clean Slate laws that meet
  the Clean Slate Initiative's criteria. Missouri was the 14th, in July 2026
  ([CSI](https://www.cleanslateinitiative.org/states)). CSI's 2025 report counted more than 18
  million adults "on a path to full or partial automated record sealing"
  ([CSI 2025](https://www.cleanslateinitiative.org/updates/2025-annual-report)). Of lexflow's 11 jurisdictions,
  VA, DC, CA, NY and IL are Clean Slate states.
* The research names the barriers as "dirty data", debt, awareness and costly processes. Its remedy is to move
  "administrative burdens from the defendant and onto the state" (Chien, above). That is not a gap in legal
  information that a better map closes.

**What lexflow has.**

* AskBench references for VA, DC, MD, TX and CA, with 9 to 30 gold sections each.
* Sealing ladders for CA, MD and VA.
* Many fillable forms.

**What is missing.**

* The facts eligibility turns on: a crosswalk from each charge to its offence class and exclusion lists, the
  disposition, and the date the sentence was completed.
* The implementation status of automatic sealing.
* Answering quality: the oracle arm, given Claude's sections, scores only 0.596.

**A 90-day pilot, if it were chosen.** A staff-facing "which remedy and when" table for one state, checked against
a legal aid organisation's own screener. Measure the rate of disagreement on real (de-identified) dispositions.

**Risks.**

* *Accuracy and harm.* A wrong "eligible" costs fees and false hope. A wrong "not eligible" deters someone who
  qualifies.
* *Maintenance.* High. The law changes yearly in many states.
* *Liability.* Applying eligibility rules to one person's record is the individualised kind of help that
  unauthorized-practice rules reach (§3.8).

**Verdict: postpone as a public screener.** The need is huge, but lexflow's comparative advantage (statute quotes,
process maps) is not the bottleneck, and its answering is weakest here. Two narrower roles fit later:

* tracking Clean Slate *implementation duties*: what the state must do, by when, and how a person checks that it
  happened;
* the sealing rung inside the licensing wedge ("seal first, then apply").

### 3.3 Occupational licensing after a conviction

**Who has the pain.**

* People with records who choose a trade.
* Reentry programs, workforce boards, prison and jail education programs, community colleges and trade schools.
  They pay to train people for licences those people may be refused.
* Licensing board staff, who must apply new "directly related" tests.

**How often.**

* "Nearly one in five workers needs a license to work", and IJ adds that one in three Americans has a
  criminal record of some kind (IJ, *Barred from Working*, June 2020; the release is reproduced in full by
  [CCRC](https://ccresourcecenter.org/report-card-on-licensing-laws-finds-progress-but-still-a-way-to-go/)).
* The same report found that:
  * in 21 states boards may deny "without ever considering whether an applicant has been rehabilitated";
  * in 12 states applicants have "no guaranteed right to appeal";
  * boards in 34 states may consider arrests that led to no conviction;
  * "30 states have enacted reforms since 2015".
* The National Inventory of Collateral Consequences of Conviction lists "more than 44,000 separate collateral
  consequences", licensing among them
  ([NIJ](https://nij.ojp.gov/topics/articles/national-inventory-collateral-consequences-conviction)).
* No national count of licence denials or predetermination requests was found. How often one program meets the
  question is **unknown**, and is the first thing to learn in interviews (§7).

**What they use today.**

* The Restoration of Rights Project's state profiles and 50-state comparisons, a lawyer-maintained narrative
  reference ([CCRC](https://ccresourcecenter.org/restoration-2/)).
* The NICCC database, which lists consequences, not procedures.
* Board websites one at a time, and lawyers where they can be found.
* For companies with many licences, commercial licence-tracking services: Harbor Compliance advertises 51
  jurisdictions and "800+" licence types catalogued ([Harbor Compliance](https://www.harborcompliance.com/licensesure)).
  These are aimed at firms, not at people with records.

**What lexflow has.**

* AskBench references for VA (§ 54.1-204), DC, MD, TX (Occ. Code ch. 53) and CA (Bus. & Prof. Code § 480).
* Licence-denial ladders for the same five states.
* A worked DMN for § 480, with 15 decisions and every quote checked
  ([bpc-480-decision.md](../design/bpc-480-decision.md), [verify-dmn-links.md](../design/verify-dmn-links.md)).
* The pre-application forms that exist, catalogued
  ([forms-research.md](../design/forms-research.md) §1):
  * Virginia DPOR's predetermination request;
  * Texas criminal-history evaluation letters (TDLR's costs $10);
  * the DC (§ 47-2853.12(n)), North Carolina (§ 93B-8.1(b6)) and Washington (RCW 18.400.020) statutory
    petitions.
* The answering arm with Claude's sections scores 0.760, far better than sealing.

**What is missing.**

* **Board-level detail.** Regulations, board policies and federal bars (for example childcare and some
  transport endorsements) sit outside the statute index.
* **A per-occupation list** of which licences the general rule covers and which have their own bars.
* **A tested "ask before you train" flow.** The ladders show challenge routes. The pre-application step is the
  one that saves tuition, and it needs its own model.

**A 90-day pilot.**

* Scope: VA and TX, the two states with both a general statute and an official pre-application form.
* Users: the 20 occupations that program staff actually ask about. Build the list from interviews; do not guess
  it.
* For each occupation, a page with:
  * does the general rule apply, or does the board have its own?
  * can I get a determination before I apply, how, at what cost, and how long does the board have?
  * if I am denied: the rung, the deadline and the quote.

Measures (targets are estimates):

* coverage of the staff-named occupations: 20 of 20, with "board-specific; check here" an allowed answer;
* accuracy, with two reviewers per page against statute, regulation and the board's own page: no unflagged
  error;
* use by staff: 5 or more programs and 30 or more lookups;
* outcomes reported by staff: predetermination requests filed and answers received, counted per opt-in.

**Risks.**

* *Accuracy.* The statute promises an individual review, not a licence ([questions.md](../questions.md) A4).
  The tool must say "likely barred" plainly where a board or federal rule bars, and must never predict a
  board's discretion.
* *Maintenance.* Medium to high, given the pace of reform.
* *Liability.* Lower than sealing, because the output is a process ("you may ask the board for a
  determination; here is how"), not a verdict on a person's record. Delivering it through program staff
  lowers both the accuracy and the liability risk.

**Verdict: the best second wedge.** The fit is good, the answering scores are better, and the users are
organisations that meet the question repeatedly. It also reuses the business model for the reentry
self-employment question ([questions.md](../questions.md) A4).

### 3.4 Court debt and fees

**Who has the pain.** People with fines, fees and restitution they cannot pay, and the clerks and public defenders
around them.

**How often.** In 2019, "over 11 million" driver's licences were suspended for unpaid court debt, and 44 states
and DC suspended, revoked or refused to renew licences for it
([FFJC, 10 Sep 2019](https://finesandfeesjusticecenter.org/news/2019/09/11/ffjc-convenes-free-to-drive-campaign-to-end-debt-related-drivers-license-suspensions/)).
Many states have reformed since, so current counts are lower. I found no dated current national figure.

**What they use today.** Courts' own tools.

* California's MyCitations lets people "request a reduction in court-ordered debt", a payment plan, more time or
  community service, in "all 58 California Superior Courts"
  ([Judicial Council](https://courts.ca.gov/programs-initiatives/criminal-justice-services/mycitations-online-traffic-adjudication-program)).
* Clerk counters, and statewide financial-statement forms in CA, VA, MD, IL, WA and NC
  ([forms-research.md](../design/forms-research.md) §1).

**What lexflow has.** AskBench references for 5 states. Claude judged three of them (CA, DC, MD) "partly in the
code": the statute sets the menu, but clerks and judges decide case by case.

**What is missing.** The discretion. That is where the answer lives: the local payment-plan policy and the
judge's practice.

**Risks.**

* Telling someone "you can get a waiver" where the court rarely grants one.
* Maintenance: the reform pace is high.

**Verdict: postpone as a wedge.** The pain is acute, but the decisive information is discretionary and local, and
the best tools are run by the courts themselves. Keep it as one rung of the licensing wedge, where unpaid debt
blocks a licence or a driving privilege the job needs.

### 3.5 Small-business licences and permits across city lines

**Who has the pain.** Owners of new and expanding businesses, especially those in several cities: restaurants,
contractors, mobile vendors.

**How often.**

* IJ's 2022 *Barriers to Business* study of 20 cities reported that none met all five of its one-stop-shop
  criteria, and that restaurant openings took dozens of steps **(not opened**: ij.org served a bot challenge;
  figures from search-result summaries).
* NFIB's 2024 *Problems and Priorities* ranked "unreasonable government regulations" seventh of 75 issues
  **(not opened**: search-result summary of an NFIB release).

**What they use today.**

* City portals.
* Paid licence research: Avalara's License Guidance finds "which federal, state, and local licenses your business
  requires" and offers filing
  ([Avalara](https://www.avalara.com/us/en/products/business-licenses/license-guidance-and-preparation.html)).
* Formation and compliance services.

**What lexflow has.**

* State entity formation for 11 jurisdictions, the part that is already commoditised.
* LOCUS headings for Virginia.
* Local business-licence processes for Charlottesville, DC and Baltimore, researched by hand.

**What is missing.** The local layer: actual local process models, fee schedules and officials' contacts. The
README says so ("No local process models are built yet"). Municipal code publishers' text is link-only
([data-building-codes.md](../design/data-building-codes.md) §3.16).

**Verdict: stop extending state business formation; postpone local licensing.** Commercial incumbents show people
pay for this, but lexflow would compete on its weakest layer. Revisit only with a city that supplies its own
current licence and fee data.

### 3.6 Building permits for small projects

**Who has the pain.** Homeowners, small landlords, handymen and small contractors (decks, sheds, fences, water
heaters), and builders on housing projects.

**How often.**

* For housing projects, the author of California's AB 2234 (2022) told the Senate Housing Committee that "many
  projects spend months or even years waiting" for post-entitlement permits. The bill set 30 and 60
  business-day review limits and required online permitting, with delays allowed for smaller jurisdictions
  ([Senate Housing Committee analysis](https://shou.senate.ca.gov/sites/shou.senate.ca.gov/files/16.%20AB%202234%20%28Robert%20Rivas%29%20-%20analysis.pdf);
  an analysis of the bill in progress, not of the final text).
* Venture-funded firms sell permit automation to builders. PermitFlow announced a $54 million Series B in
  December 2025 **(not opened**: businesswire.com dropped the connection).
* For homeowners' small projects, I found no US survey of how often people skip or misjudge permits
  (**unverified**; the search budget ran out).

**What they use today.** The local building department's web page and counter, contractors, and government
permitting systems.

**What lexflow has.**

* A research note, [data-building-codes.md](../design/data-building-codes.md). The regulation text for 7 of the
  10 states is already on disk but not indexed. Virginia's exemption list (13VAC5-63-80) can be quoted today.
* A clear finding that the answers differ widely: a VA shed up to 256 sq ft needs no permit; in DC the limit is 50
  sq ft; Baltimore City removed the model-code deck exemption.

**What is missing.**

* Local adoption and amendment ordinances, for every state where the list is local text.
* Model-code text, which is copyrighted. The note proposes storing facts only.
* Local fees, and an index of which government issues permits for each place (Census BPS).

**Risks.**

* A wrong "no permit needed" can mean fines, removal or insurance trouble.
* Maintenance: codes are re-adopted on roughly three-year cycles (the note's own caveat).

**Verdict: postpone, with one exception.** A Virginia-only "do I need a permit for a shed or deck?" decision table,
quoted from state text, is a good bounded graduate-student project (§8). It is not a wedge.

### 3.7 Zoning questions

**Who has the pain.** Planners, housing advocates, homeowners, developers and researchers.

**What they use today.** Above all, the National Zoning Atlas. It extracts "more than 200 regulatory
characteristics for each zoning district" and is working towards "more than 33,000 jurisdictions"
([National Zoning Atlas](https://www.zoningatlas.org/)). It has state and regional teams, and its findings are
already cited in state legislation debates (same page).

**What lexflow has.** Nothing on zoning substance. [questions.md](../questions.md) C4 sketches the statutory side:
review deadlines, notice rules, and what happens on a missed deadline (for example deemed approval).

**What is missing.** Everything substantive: the local text, the maps, and the licence to use municipal codes.

**Verdict: stop.** Do not compete with the zoning atlas on substance. Lexflow's only zoning-related asset would be
**statutory land-use review clocks** for planning staff (C4). That is a reasonable *later* extension for the
city-planner audience, because it is process and deadlines from state statute: lexflow's strength.

### 3.8 Cross-cutting risk: accuracy claims and unauthorized practice

* **Accuracy claims.** Stanford RegLab and HAI tested three commercial legal AI research tools. Two "produced
  incorrect information more than 17% of the time", and the third hallucinated more than 34% of the time
  ([Stanford HAI, May 2024](https://hai.stanford.edu/news/ai-trial-legal-models-hallucinate-1-out-6-or-more-benchmarking-queries)).
  Lexflow's quote-first answers are a real difference, but only when retrieval finds the right sections, and
  locally it puts only 24% of the gold sections in its top 10. Do not market Ask as an answer engine. Market the reviewed
  models and their quotes.
* **Overclaiming.** The FTC's order against DoNotPay bars deceptive claims about its "robot lawyer" and requires
  $193,000 in relief **(not opened**: ftc.gov refused the client; from search-result summaries of the FTC
  announcement). Never compare lexflow to a lawyer.
* **Unauthorized practice of law.** In *Upsolve v. James* (September 2025), a nonprofit wanted to train
  non-lawyer volunteers to give individualised advice. The Second Circuit held that New York's
  unauthorized-practice rules, as applied to that advice, regulate speech but are content-neutral, so strict
  scrutiny does not apply. It vacated the injunction that had shielded the volunteers and sent the case back
  ([Public Citizen CLP blog](https://clpblog.citizen.org/second-circuit-holds-unlawful-practice-law-can-apply-to-debt-collection-advice/)).
  The Supreme Court denied certiorari on 30 March 2026
  ([docket 25-948](https://www.supremecourt.gov/search.aspx?filename=/docket/docketfiles/html/public/25-948.html)).
* **The practical line.** Publish general information about processes and deadlines, keyed to statutes. Do not
  apply eligibility rules to one person's facts and tell them what to do. The process lab sits close to that
  line, because it is one person's case. It stays on the safe side by:
  * computing deadlines and showing the law;
  * never recommending a choice;
  * keeping cases in the browser.

---

## 4. Scorecard

Ratings are this note's judgement, from the evidence above.

| Wedge | Measured pain | Incumbents | lexflow fit today | Accuracy / liability risk | Upkeep | Verdict |
|---|---|---|---|---|---|---|
| Records: deadlines and next steps | Strong, repeated, both sides | Strong for workflow (Granicus GovQA, CivicPlus NextRequest, MuckRock); weak on quoted per-state clocks and ladders | **Best**: 11 reviewed models, ladders, calendars, forms | Medium | Medium | **Wedge 1** |
| Licensing after a conviction | Strong at population level; per-program volume unknown | Narrative references (CCRC, NICCC); no process tool found | **Good**: 5 states of references and ladders, § 480 DMN, forms | Medium (process, not verdict) | Medium–high | **Wedge 2** |
| Record sealing | Strongest (6.5% uptake; 20–30 M in the gap) | Legal aid screeners; Clean Slate automation in 14 states + DC | Weak: offence-level facts missing; oracle 0.596 | High | High | Postpone screener |
| Court debt | Strong (11 M suspensions in 2019) | Courts' own tools (MyCitations in all 58 CA courts) | Weak: discretion decides | Medium–high | High | Postpone; one rung of wedge 2 |
| Small-business licences across cities | Medium (not-opened sources) | Paid services (Avalara, Harbor Compliance), city portals | Weak at the local layer | Medium | High | Stop formation work; postpone |
| Building permits, small projects | Strong for builders; thin data for homeowners | Building departments, permitting systems, venture-funded builder tools | Weak: regulations not indexed, local amendments, copyright | High | High | Postpone (one VA student project) |
| Zoning | Strong | National Zoning Atlas | None | High | Very high | Stop; maybe land-use clocks later |

---

## 5. Recommendation

### 5.1 Wedge 1: records, after you file

What makes it one product, not a database:

* **One job.** "I sent a request (or received one) on this date. When is the answer due, and what can I do if it
  is late, partial, too expensive or denied?"
* **One scope.** VA, DC and MD first, where the places are already researched end to end, then IL. Extend to the
  other 7 reviewed states only after the accuracy audit passes.
* **One surface.** The lab, mounted, with a link from each state's Lexipedia page. Embed it in DokuWiki as a thin
  widget, as designed in [lab-research.md](../design/lab-research.md) §1.6.
* **Two audiences, one model.** The requester's view and the custodian's view are the same process from opposite
  lanes, so building one gives most of the other.

### 5.2 Wedge 2: licensing after a conviction, staff-facing

* **One job.** "Before my client trains for this licence, can they ask the board? How? What if they are
  refused?"
* **One scope.** VA and TX first, then CA (the § 480 DMN exists), DC and MD.
* **One delivery.** Through program staff, not directly to the public, for accuracy and for the
  unauthorized-practice line.

Do wedge 2 second, or in parallel only if a separate team of graduate students owns it (§8).

### 5.3 Stop or postpone

| Stop or postpone | Why |
|---|---|
| Growing breadth as a goal: more selector-built states, scoring all 38,640 governments, county confidence maps | No user has asked for breadth. The scores mostly reflect the state-law tier, not local truth, and 43% of verifiable websites in the contact sample were stale. Keep the map as an internal QA view. |
| New infrastructure designs before a pilot needs them: Wikibase authority properties, C2PA signing, payroll aggregates, tax and SBA data | Each is careful work, but none answers a user's question today. Revisit when a pilot user asks "can I trust this?" (provenance) or "who decides?" (authority). |
| Extending "start a business" | State formation is the solved part, and local licensing is where lexflow is weakest. |
| Ask as a headline feature | 0.40 composite. Keep it as a research tool and as AskBench. Publish only reviewed answers. |
| Record sealing as a public screener | §3.2 |
| Building permits, zoning, court debt as wedges | §3.4, §3.6, §3.7 |
| Prison wages, phone/commissary, pretrial clock | Good research benchmarks with a clear micro-economic angle. They are research projects, not wedges. Keep them in AskBench. |

Keep and narrow:

* the 11 records models and ladders;
* the lab;
* the forms registry;
* the contacts re-check, but for records offices in the pilot places only;
* the AskBench loop.

---

## 6. What lexflow is not good at yet

1. **It has no public product and no users.**
   * The dashboard is a local Docker developer tool.
   * The lab's API is not mounted. Its page says so and cannot start a case.
   * Lexipedia has 43 pages.
2. **New questions.**
   * The local search puts 24% of the gold sections in its top 10, and the local composite is 0.40.
   * Given the right sections, it still quotes only half the vital points (0.49).
   * A small local model's summary does not help.
   * The planner fix of 10 October was not held out.
3. **Local law.**
   * There are no local process models.
   * LOCUS gives headings, not text, under CC BY-NC.
   * Records-office contacts are verified for 3 places.
   * Wikidata gave an email or phone for 4 governments.
   * 43% (±14) of verifiable official websites in the pilot were stale, and some now serve spam.
4. **Law outside statutes.** Regulations are not indexed (building codes, DC's records rules). Court rules sit
   under 12 ladder rungs. Advisory opinions and agency practice carry fee and exemption answers.
5. **Coverage holes.**
   * There is no statute file for AR, CO, GA, MS or TN.
   * The records laws of PA, HI and NE are not in the files, and ND's text is wrong.
6. **Time.** Models pin an open-us-law release (v2026.09.1). Nothing yet watches the official publishers for
   amendments to quoted sections. That matters most in fast-moving areas: 30 states reformed licensing
   between 2015 and 2020, and Clean Slate laws keep passing.
7. **Selector-built models** agree with Claude at about 0.60. They are drafts and must not be shown as answers.
8. **People's facts.** Eligibility questions turn on a person's charges, dates and dispositions, which lexflow
   neither has nor should collect.
9. **Licences.**
   * No licence has been chosen for lexflow itself.
   * open-us-law and LOCUS are CC BY-NC 4.0, so a paid service built on that data needs a licence from Vaquill
     AI (README).
   * The statute text itself is a government edict. A service model would need either that licence or its own
     fetch from the official publishers, which several of them block for automated clients
     ([forms-plan.md](../design/forms-plan.md), [lab-research.md](../design/lab-research.md)).
   * Take this to counsel before any service is priced.

---

## 7. Questions to ask, by audience

Ask about past behaviour, not opinions. "Would you use this?" invites a polite yes. The method follows *The Mom
Test* ([Fitzpatrick](https://www.momtestbook.com/)).

* **Real pull** looks like this: they show you their spreadsheet or checklist; they ask when they can use it;
  they introduce a colleague; they give time or data; they name a budget line.
* **Compliments are not pull.**

**Requesters** (journalists, student newsrooms, researchers, residents):

* Tell me about the last request that stalled. What did you do next, and when?
* How did you work out the deadline? Were you sure? Did you check business days and holidays?
* Have you ever appealed or gone to an oversight body? Why, or why not?
* How many requests a year, and in how many states? What do you use to keep track?
* Have you ever missed a window you were entitled to? What did it cost you?

**Clerks and records officers** (small governments first):

* Walk me through the last request that came in. How did you count the response deadline?
* Who decides on an extension? What does your response letter have to say?
* Have you ever missed a deadline? What happened?
* What software or template do you use? Who chose it, and who would approve a change?
* Where do you look when the law changes?

**Reentry, workforce and education program staff:**

* The last time a client asked whether a record would block a licence, what did you do? How long did it take?
* Which licences come up most? Which ones have you seen refused?
* Has anyone asked a board for a determination before training? What happened, and how long did it take?
* Who pays for training that ends in a refused licence?

**Legal aid and clinics** (for wedge 2, and to test sealing later):

* Where do your screener's rules come from? Who updates them when the law changes? How often has a change broken
  them?
* What would you need to trust a rules table you did not write: quotes, review dates, a named reviewer?

**City planners** (for later, and to test the land-use clock idea):

* Which statutory clock or notice rule do you most worry about missing? Has a decision ever been challenged over
  one?

**Attorneys:**

* When you need the same rule in many states, what do you do today, and what does it cost?
* Have you checked an AI research tool's citation and found it wrong? What would make a quoted, dated table
  trustworthy?

**The wiki community:**

* What would make a Lexipedia page worth correcting, rather than ignoring? Expect the answer to be a topic people
  care about, with sources. Ask it about the records pages, not about 38,640 machine-made place pages.

The questions that test the free-plugin-plus-service idea (§7.1):

* Who pays today, and from which budget?
* Who must approve a new tool?
* What happens when the rules change and nobody updates the tool?

### 7.1 What the evidence says about plugins (for example for Granicus or CivicPlus)

* **The vendors already own the workflow.** Both large vendors already sell the custodian's records workflow:
  * Granicus bought GovQA (August 2021);
  * CivicPlus agreed to acquire NextRequest's owner (May 2022, not opened);
  * Granicus reports "7000+" public-sector customers ([Granicus](https://granicus.com/)).
* **So do not compete with them.** A lexflow plugin that tracks requests would compete with products their
  customers already have.
* **What might be missing:**
  * transparent, quoted, per-state deadline and escalation rules, with the counting shown;
  * the long tail of small agencies that do not buy either product (§3.1, JLARC).
* **What was not checked.** I did not check how those products encode state rules, or the vendors' marketplace
  or partner terms (**unverified**; the search budget ran out).
* **The cheaper test first.** Publish the records rules openly, as Lexipedia pages, an embeddable lab and a
  machine-readable feed. Then see who pulls:
  * small clerks;
  * multi-state requesters;
  * the vendors themselves.
* **A service behind a free release.** Maintained, reviewed rule updates with change alerts would be a
  hypothesis worth testing in the interviews. It is not a finding. The CC BY-NC data licence (§6, item 9) must
  be settled first.

---

## 8. Graduate students: small niche goals that bridge process modelling into the mainstream

Give each student one bounded job with a public, checkable output and one number to move. Each project below fits a
semester and serves a wedge.

| Project | Wedge | Output | The number it moves |
|---|---|---|---|
| **Records clock audit** (law, public policy) | 1 | 100 hand-worked deadline cases per state for VA, DC and MD, from the statutes and published advisory opinions, run against the lab | Share of cases where the lab and two reviewers agree (target 100%, every disagreement fixed or explained) |
| **Escalation in practice** (data science, journalism) | 1 | Label each records-ladder rung with how often it is used and how long it takes, from published oversight decisions: Illinois PAC opinions, Texas AG letter rulings, Virginia FOIA Council opinions. (Texas's searchable letter-ruling database for requests from 21 Dec 2023 is from a search summary, **not opened**.) | First real-world timing data behind a lexflow model. It turns the ladders from "what the law says" into "what happens". |
| **Small-office response clock** (public administration, HCI) | 1 | The custodian view of the lab, tested with clerks in small localities | Clerks still using it after 30 days (target 3) |
| **Licence pre-check pages** (social work, public policy, law) | 2 | VA and TX pages for the 20 occupations that program staff name, each with its pre-application step, decision deadline and challenge rung | Pages passing two-reviewer audit; staff lookups |
| **User research** (information science, HCI) | 1 and 2 | 30 interviews across requesters, clerks and program staff, using §7; a usability test of the lab with 10 people | Number of distinct workarounds documented. Kill or keep decisions recorded. |
| **An open legal-process benchmark** (systems engineering, BPM) | Both | Publish the 22 reviewed BPMN and DMN models, the ladders and AskBench as a citable, versioned test suite for process mining and BPM researchers | Outside groups that run it, the cleanest bridge from process modelling into the mainstream. **Not checked**: whether the BPM community lacks such a suite; verify with a literature search before claiming it. |
| **One Virginia permit question** (planning, civil engineering) | Bounded side project | A `permit_required` table for sheds and decks from 13VAC5-63-80, compared with the published guidance of Virginia building departments | Agreement with published local guidance; every disagreement explained |

Practical notes:

* **Human-subjects review.** Interviews and usability tests at a university, above all with people who have
  records, need review by the university's IRB, or a documented determination that review is not needed. Plan
  for it in week 1, not week 8.
* **What students should not get.** Avoid open-ended goals ("improve Ask", "cover more states"). AskBench shows
  why: gains there are hundredths, not tenths, and nobody outside the team can see them.
* **The niche framing is the mainstream bridge.** A process model becomes mainstream when a clerk or a reentry
  counsellor uses it without knowing it is BPMN. Each project above ends in something such a person can open,
  with the model underneath.

---

## 9. Not verified here

* Granicus and CivicPlus partner or marketplace terms, and how GovQA and NextRequest encode state rules (search
  budget ran out; civicplus.com refused the client).
* IJ's 2022 *Barriers to Business* figures and NFIB's 2024 ranking (ij.org challenge; NFIB not opened).
* FTC's DoNotPay order details (ftc.gov refused the client).
* PermitFlow's Series B (businesswire.com dropped the connection).
* A US survey of permits skipped on small home projects (none found before the budget ran out).
* A current national count of debt-based licence suspensions (only the 2019 figure was opened).
* The current BJS count of people released from prison each year (not searched).
* The Texas AG's searchable letter-ruling database (from a search summary only).
* All targets in §3 and §8 are estimates for the team to set.

---

## Sources

Opened on 2026-10-10 unless marked otherwise.

Public records:

* MuckRock, "MuckRock request data shows big difference in backlogs between states" (21 Mar 2019):
  https://www.muckrock.com/news/archives/2019/mar/21/feature-state-data/
* MuckRock, FOIA response-time data (14 Mar 2017):
  https://www.muckrock.com/news/archives/2017/mar/14/muckrock-foia-response-data/
* Washington JLARC, Public Records Data Collection report (2021, 2019 data):
  https://leg.wa.gov/jlarc/reports/2021/PubRecordsDataCollection/default.html
* Illinois Attorney General, 2024 Public Access report release (17 Mar 2025):
  https://illinoisattorneygeneral.gov/news/story/attorney-general-raoul-issues-2024-public-access-report-during-sunshine-week
* Texas Attorney General, Open Records Division FY 2018 release (19 Sep 2018):
  https://www.texasattorneygeneral.gov/news/releases/ag-paxton-open-records-division-experiences-record-setting-year-public-information-requests-and
* Post-Journal (Jamestown, NY), "Influx of AI FOIL requests requires legislative response" (Jul 2026):
  https://www.post-journal.com/opinion/in-our-opinion/2026/07/in-our-opinion/
* DOJ Office of Information Policy, FY 2024 annual FOIA reports summary (29 Apr 2025):
  https://www.justice.gov/oip/blog/summary-fiscal-year-2024-annual-foia-reports-published
* Brechner Center, "FOIA requests, denials, backlogs, delays, costs surge in FY 2024" (30 Apr 2025):
  https://brechner.jou.ufl.edu/2025/04/30/foia-requests-denials-surge-fy-2024/
* Reporters Committee for Freedom of the Press, Open Government Guide: https://www.rcfp.org/open-government-guide/
* Granicus, GovQA acquisition release (26 Aug 2021):
  https://granicus.com/press-release/granicus-acquires-leading-compliance-software-provider-govqa-to-help-government-agencies-manage-exponential-increase-in-public-records-requests/
* Granicus home page ("7000+ public sector customers"): https://granicus.com/
* CivicPlus, Optimere acquisition news page (**not opened**, HTTP 403):
  https://www.civicplus.com/news/nn/civicplus-enters-into-agreement-to-acquire-optimere/

Record sealing:

* Prescott & Starr, "Expungement of Criminal Convictions: An Empirical Study", 133 Harv. L. Rev. 2460 (2020):
  https://harvardlawreview.org/print/vol-133/expungement-of-criminal-convictions-an-empirical-study/
* Chien, "America's Paper Prisons: The Second Chance Gap", 119 Mich. L. Rev., issue 3 (2020):
  https://michiganlawreview.org/journal/americas-paper-prisons-the-second-chance-gap/
* Paper Prisons Initiative: https://paperprisons.org/
* Clean Slate Initiative, state campaigns: https://www.cleanslateinitiative.org/states
* Clean Slate Initiative, 2025 annual report: https://www.cleanslateinitiative.org/updates/2025-annual-report
* Legal Services of New Jersey, "Clearing Your Record Online": https://lsnjlaw.org/pages/expunge

Licensing after a conviction:

* Shannon et al., "The Growth, Scope, and Spatial Distribution of People With Felony Records in the United
  States, 1948–2010", *Demography* 54 (2017): https://pmc.ncbi.nlm.nih.gov/articles/PMC5996985/
* CCRC, "Report card on licensing laws finds progress, but still a way to go" (quoting IJ's *Barred from
  Working* release, June 2020):
  https://ccresourcecenter.org/report-card-on-licensing-laws-finds-progress-but-still-a-way-to-go/
* CCRC, Restoration of Rights Project: https://ccresourcecenter.org/restoration-2/
* NIJ, National Inventory of the Collateral Consequences of Conviction:
  https://nij.ojp.gov/topics/articles/national-inventory-collateral-consequences-conviction
* Harbor Compliance, LicenseSure: https://www.harborcompliance.com/licensesure

Court debt:

* Fines and Fees Justice Center, Free to Drive launch (10 Sep 2019):
  https://finesandfeesjusticecenter.org/news/2019/09/11/ffjc-convenes-free-to-drive-campaign-to-end-debt-related-drivers-license-suspensions/
* Judicial Council of California, MyCitations (page dated February 2025):
  https://courts.ca.gov/programs-initiatives/criminal-justice-services/mycitations-online-traffic-adjudication-program

Business licensing:

* Avalara, License Guidance and Preparation:
  https://www.avalara.com/us/en/products/business-licenses/license-guidance-and-preparation.html
* IJ, *Barriers to Business* release (Feb 2022) (**not opened**, bot challenge):
  https://ij.org/press-release/new-report-reveals-how-cities-make-it-needlessly-expensive-time-consuming-and-challenging-to-start-a-small-business/

Building permits and zoning:

* California Senate Housing Committee, analysis of AB 2234 (2022):
  https://shou.senate.ca.gov/sites/shou.senate.ca.gov/files/16.%20AB%202234%20%28Robert%20Rivas%29%20-%20analysis.pdf
* PermitFlow Series B release (**not opened**, connection dropped):
  https://www.businesswire.com/news/home/20251202551013/en
* National Zoning Atlas: https://www.zoningatlas.org/

Accuracy, liability and method:

* Stanford HAI, "AI on Trial: Legal Models Hallucinate in 1 out of 6 (or More) Benchmarking Queries" (updated
  30 May 2024): https://hai.stanford.edu/news/ai-trial-legal-models-hallucinate-1-out-6-or-more-benchmarking-queries
* Public Citizen Consumer Law & Policy Blog, on *Upsolve v. James* (10 Sep 2025):
  https://clpblog.citizen.org/second-circuit-holds-unlawful-practice-law-can-apply-to-debt-collection-advice/
* Supreme Court docket 25-948, *Upsolve, Inc. v. James* (certiorari denied 30 Mar 2026):
  https://www.supremecourt.gov/search.aspx?filename=/docket/docketfiles/html/public/25-948.html
* FTC, DoNotPay final order announcement (**not opened**, HTTP 403): https://www.ftc.gov/node/87474
* Fitzpatrick, *The Mom Test*: https://www.momtestbook.com/

lexflow (read-only): `README.md`, `docs/questions.md`, `docs/askbench.json`,
[lab-research.md](../design/lab-research.md), [lab-plan.md](../design/lab-plan.md),
[authority-ladders.md](../design/authority-ladders.md), [forms-research.md](../design/forms-research.md),
[entities-contacts.md](../design/entities-contacts.md), [data-building-codes.md](../design/data-building-codes.md),
[bpc-480-decision.md](../design/bpc-480-decision.md), [canonical-workflows.md](../design/canonical-workflows.md),
`fixtures/authority/ladders.json`, `curated_ask/*/*.json`, `lexflow/lab/deadlines.py`.
