# A legal-aid critique of the adoption strategy

_Status: critique, 10 October 2026. It reviews [adoption-strategy.md](adoption-strategy.md) and its research notes
([wedge.md](wedge.md), [communities.md](communities.md), [models.md](models.md), [landscape.md](landscape.md)) from
one seat: a legal-aid technology lead and practising attorney who has run court-form and expungement tools, and who
cares about accuracy, unauthorised practice of law, accessibility and users with low literacy. I also read
`README.md`, `docs/design/lab-plan.md`, `docs/design/lab-research.md`, the licensing and sealing reference answers in
`curated_ask/`, and parts of `lexflow/lab/` and `dashboard/lab.js`. All were read without changing them. This is the
only file written._

_New checks for this note. On 10 October 2026 I read pages myself, read-only, with `curl` and the User-Agent
`lexflow-research/0.1 (https://github.com/alibama/lexflow)`, at least one second apart per host. The pages were
three live Lexipedia pages (Virginia, Maryland and DC records), six statute pages on law.lis.virginia.gov and
mgaleg.maryland.gov, 7 CFR 273.15 on eCFR, and pages from NCES, Pew Research, LSC, the White House, Virginia Law Help,
the Reporters Committee and Interisle. federalregister.gov served a bot check and americanbar.org answered 403; I did
not work around either. Two vsb.org URLs I tried returned 404._

_Credit and privacy. This note names organisations, projects, statutes and published works only. People appear only
as authors of cited works. No organisation named here is a partner, advisor, endorser or prospective collaborator.
Judgements are marked **judgement**, and estimates **estimate**. None of this is legal advice. The licence and
unauthorised-practice questions go to counsel._

## Contents

0. [The verdict on one page](#0-the-verdict-on-one-page)
1. [What the strategy gets right](#1-what-the-strategy-gets-right)
2. [What would make me close the tab today](#2-what-would-make-me-close-the-tab-today)
3. [What is naive or wrong](#3-what-is-naive-or-wrong)
4. [The user-discovery questions](#4-the-user-discovery-questions)
5. [The content drafts](#5-the-content-drafts)
6. [What is missing: a gate before any legal-aid outreach](#6-what-is-missing-a-gate-before-any-legal-aid-outreach)
7. [What would earn my attention and repeat use](#7-what-would-earn-my-attention-and-repeat-use)
8. [Hammer, nail and plugins, from legal aid](#8-hammer-nail-and-plugins-from-legal-aid)
9. [Metrics a legal-aid partner would ask for](#9-metrics-a-legal-aid-partner-would-ask-for)
10. [Not verified](#10-not-verified)

---

## 0. The verdict on one page

**Short version.** The strategy is careful, honest about its gaps, and right about the big moves: go through
intermediaries, never show unreviewed answers, keep record sealing away from the public, get the IRB in first.
I would still ignore lexflow today. That is because of what is live on Lexipedia, and because nothing a low-literacy
client could use exists yet. The plan hardly addresses either. The search terms literacy, reading level, Spanish,
language access and screen reader each appear zero times across the five strategy notes.

**The twelve findings that matter most, in order:**

1. **The live pages say the opposite of "in the law's own words".** Virginia's "five working days" is shown as
   "within 5 business days", and "seven work days" as "within 7 business days". Maryland's "10 working days" is shown
   as "10 business days" on the same page whose notes say "10 working days". DC's "15 days (except Saturdays, Sundays,
   and legal public holidays)" is shown as "15 business days" in one place and "15 working days" in another (§2.2).
   lexflow's own research says these units differ from state to state. A records lawyer or a law librarian would find
   this within a minute, and would stop reading.
2. **"Checked by Claude · quality 1.00" is the top trust label on the model pages** (all three I read). To an attorney, that reads as
   "no lawyer has looked at this". To a lay reader, it reads as "100% accurate". It is neither. The quality score
   measures quote matching and schema checks, not legal correctness. The strategy repeats the same conflation:
   "Claude-reviewed or person-reviewed models (quality 0.99 to 1.00)" (§3.1). It even breaks its own rule that Claude
   "is never the final reviewer of anything published" (§6.3). The three published model pages I read carry the
   "checked by Claude" label, and the README records no named human sign-off for any of the 22 (§2.1).
3. **There is no licensed attorney anywhere in the review ladder.** The "human gold standard" (P1) is a law or
   policy student, and the "two-reviewer audits" (P2, P5) are students too. No legal-aid organisation will hand out
   a page that no attorney in its jurisdiction has signed (§3.6).
4. **The requester lane counts from the wrong day.** The strategy's requester view is "sent on date X, so the answer
   is due on date Y" (§1.3). Every one of the eleven clocks in its own table runs from *receipt*. The lab assumes the
   body received a request on the day it was sent. It says so only in a muted note (§3.1).
5. **The "two lanes, one model" framing hides a reversal of the safe default.** The lab counts a body's deadline to
   the *later* date where the law is open. That is right for a requester, so the lab never calls a body late too
   soon. It is wrong for a clerk, who is the one at risk of breaking the law. The clerk card would inherit the
   requester's default (§3.2).
6. **"Through staff" does not move content to the information side of the line.** A page on Lexipedia is public
   whoever the strategy calls its audience. Non-lawyer reentry and workforce staff applying eligibility rules to one
   client is the very conduct *Upsolve v. James* is about. "Likely barred" and "seal first, then apply" are advice
   (§3.3, §3.4).
7. **"Names the official place to check: … or the board."** For a licence denial, the board is the other side. Every
   page needs a route to *free legal help*, not just to the agency (§3.5).
8. **The licensing wedge will miss what reentry clients actually run into.** Virginia's binding predetermination
   covers DPOR boards only, not the health boards (nurse aides, for example). The Virginia reference drops "barrier
   crimes" as an off-topic search term, yet those rules govern many care jobs. CDL and other federal bars, and trades
   with no licence at all, are outside the model too (§3.10).
9. **The legal-aid offers are not gifts.** In week 8, asking a legal-aid attorney to "mark up" a Claude-written
   reference is asking them to do unpaid quality checks on AI output. The Assembly Line offer cannot be delivered
   with today's assets: no reviewed model covers a court process, and court rules are not in the corpus (§3.8, §5.3).
10. **There is no way to recall a wrong date.** Cases live only in the browser. A deadline exported to `.ics` carries
    no model version, and no "known errors" page exists. A legal-aid partner's first question about any calculator is
    "what happens when you get one wrong?" (§3.7).
11. **Nothing is written for the people the plan says it ultimately serves.** No plain-language layer, no Spanish,
    no reading-level target, nothing print-first, no shared-computer mode. That matters when 28% of US adults score at
    or below Level 1 in literacy ([NCES, PIAAC 2023](https://nces.ed.gov/surveys/piaac/2023/national_results.asp)). It
    also matters when 34% of adults in households under $30,000 rely on a smartphone for home internet
    ([Pew, 2025](https://www.pewresearch.org/internet/fact-sheet/mobile/)) (§6).
12. **The domain and the footer.** `lexipedia.xyz` sits on a top-level domain that ranked fourth of all domains by
    reported phishing in 2025 ([Interisle, Phishing Landscape 2025](https://interisle.net/s/phishinglandscape2025.pdf)).
    The wiki footer licenses everything "CC Attribution-Share Alike 4.0". That sits badly with the CC BY-NC
    compilation the pages are built from (§2.4, §2.5).

**What would earn repeat use** (§7). The pull would come from the people who *maintain* self-help content, not the
people who read it:

- a watch on amendments to the statute sections my guides cite;
- a deadline library with published test cases that my docassemble interviews can call;
- an attorney-signed, dated table I can check my own guides against;
- staff one-pagers on licensing that say plainly what governs each job.

All four keep lexflow on the safe side of the advice line. All four reuse the deadline engine and the quotes. None
needs BPMN on screen.

---

## 1. What the strategy gets right

Most of what the legal-aid world worries about first is already in the plan:

- **Intermediaries, not residents** (§0 item 3). It is right, and it is how legal aid itself works.
- **No public sealing screener** (§1.4). It is right for the right reasons: the bottleneck is records data, the area
  is the hardest to answer correctly, and individual eligibility is what unauthorised-practice rules reach.
- **Never show selector drafts or Ask answers** (§3.1, §5.3).
- **IRB first, no case facts in interviews, people with records reached only through staff with IRB approval**
  (§2.2).
- **Text before canvas, and WCAG 2.1 AA before anything a city shows residents** (§4.1).
- **Corrections log, credit only with consent, a candid fallback at day 90** (§6.3, §8.3).
- **Not competing with the Reporters Committee, MuckRock or the courts' own tools** (§1.3, §1.6).

Keep all of it. The rest of this note is about what is missing or what would backfire.

---

## 2. What would make me close the tab today

These are on the live site now. They come before any outreach, because every outreach piece links to these pages.

### 2.1 "Checked by Claude · quality 1.00"

The Virginia records page ([lexflow:va:records](https://lexipedia.xyz/doku.php?id=lexflow:va:records), read 10
October 2026) opens with "state model checked by Claude · quality 1.00". It goes on to explain that every quote was
matched word for word and the process passed schema, bpmnlint and Petri-net checks, then says "Information, not legal
advice". The Maryland and DC pages carry the same label, with quality 0.99 and 1.00.

- **For an attorney**, the honest part works against the page. "Checked by Claude" says that no lawyer reviewed it.
  After the run of AI-invented citations in legal filings, many attorneys stop reading at that point. Stanford's
  study found commercial legal AI tools wrong more than 17% of the time
  ([Stanford HAI](https://hai.stanford.edu/news/ai-trial-legal-models-hallucinate-1-out-6-or-more-benchmarking-queries),
  cited in [wedge.md](wedge.md) §3.8). lexflow's quotes are better than that, but the label does not say how.
- **For a lay reader**, "quality 1.00" reads as "perfect". The score means the quotes match and the diagram is well
  formed. A model can score 1.00 and still pick the wrong clock (§2.2 shows one way).
- **The strategy conflates the two.** "Show only reviewed work outside the team. That means Claude-reviewed or
  person-reviewed models (quality 0.99 to 1.00)" (§3.1). In legal aid, "reviewed" means reviewed by a person who is
  answerable for it.

**Fix (judgement).** Take the model name and the quality score off public pages. Show three plain facts instead:

- **who drafted it:** "Drafted with an AI system from the statute text";
- **what was checked:** "Every quote matched to the official text on <date>";
- **who signed:** "Reviewed by <licensed attorney, state> on <date>", or, until then, "**Not yet reviewed by an
  attorney**".

Keep the machine-check details on a method page.

### 2.2 The units on the page are not the law's words

The strategy's main selling point is "in the law's own words". The live pages relabel the units that the deadline
turns on:

| Page | What the page says | What the statute says |
|---|---|---|
| [Virginia records](https://lexipedia.xyz/doku.php?id=lexflow:va:records) | "Provide records or answer in writing … within 5 business days"; the extension "within 7 business days" | "within five working days of receiving a request" and "an additional seven work days" ([Va. Code § 2.2-3704](https://law.lis.virginia.gov/vacode/2.2-3704/)) |
| [Maryland records](https://lexipedia.xyz/doku.php?id=lexflow:md:records) | "Send delay notice … within 10 business days" and "Send written denial … within 10 business days" in the steps. The notes on the same page say "10 working days" | "within 10 working days after receipt of the request" and "within 10 working days" ([Md. Gen. Prov. § 4-203](https://mgaleg.maryland.gov/mgawebsite/Laws/StatuteText?article=ggp&section=4-203&enactments=false)) |
| [DC records](https://lexipedia.xyz/doku.php?id=lexflow:dc:records) | "within 15 business days" in the steps, "within 15 working days" in the decision table, and "within 25 business days" for the extended date | "within 15 days (except Saturdays, Sundays, and legal public holidays)", and an extension that "shall not exceed 10 days (except …)" ([D.C. Code § 2-532](https://code.dccouncil.gov/us/dc/council/code/sections/2-532)) |

This is not a quibble. lexflow's own research says that "'Business day' and 'working day' mean different things in
different states" ([lab-research.md](../design/lab-research.md), Summary). It also says the compiler collapses both
into one `business_days` unit. A Virginia clerk's "working day" turns on whether *that office* was open. That is the
whole premise of the clock card in §7.6. The DC "25 business days" figure is lexflow's own sum, presented as if the
statute said it.

**Fix.** Print the statute's own unit phrase on every step ("5 working days", "15 days, not counting Saturdays,
Sundays and legal public holidays"), and keep the internal unit for the arithmetic only. Mark derived figures as
"lexflow's count: 15 + up to 10". Re-check all 53 curated deadlines this way before week 3's blog post links to
these pages.

### 2.3 Developer language and reading level on public pages

The Virginia page's "What the text leaves open" section talks to the model's builders, not its readers:

- it contains code names such as `no_records_released`, `respond_extended`, `deemed_denied`, `notify_charges` and
  `extraordinary_burden_and_intends_petition`;
- it uses BPMN terms ("exclusive merges", "join 'any'", "a boundary event on respond_extended");
- by a rough Flesch–Kincaid count, that section reads at about grade 15 (**estimate**; the formula undercounts legal
  vocabulary).

The reference answers the strategy plans to offer legal aid read at about grade 10 to 12 by the same rough measure.
That is before the bracketed citation markers (`[N13]`) and terms like "case decision" and "summary case decision".
Legal-aid self-help writing usually aims far lower (**judgement**). Lawyer-level text is fine for a staff reference.
It is unusable as anything a counsellor hands to a client.

**Fix.** Split every page into layers:

1. **What this means**: a reviewed, plain-language answer of five to eight short sentences;
2. **What to do next, and by when**: one date per row, in large type;
3. **What the law says**: the quotes, which can be expanded;
4. **For builders**: the model notes. Move these to a separate method or source page, or into the page source.

### 2.4 The licence footer

Every Lexipedia page ends: "Except where otherwise noted, content on this wiki is licensed under the following
license: CC Attribution-Share Alike 4.0 International". That looks like DokuWiki's default. The pages are generated
from open-us-law's compilation, which is CC BY-NC 4.0 (README).

- The strategy's to-do item is to "put licence statements on both Lexipedia sites" (§0 item 8, §5.4). But a
  statement already exists, and it may grant more than lexflow has the right to grant. That is a question for counsel,
  not a conclusion.
- A law librarian will notice. Librarians are the audience §3.5 says "will ask first about authenticated text".

**Fix.** Correct the footer in the same week as the licence decision. Until counsel answers, a neutral line such as
"Licences vary by source; see <data policy page>" is safer than a blanket CC BY-SA.

### 2.5 The domain and the name

- **The domain.** `.xyz` ranked fourth of all top-level domains by phishing domains reported in Interisle's 2025
  study (73,509). It was in the top five in four of the last five annual studies, and the report notes its
  "historically high rankings" ([Interisle](https://interisle.net/s/phishinglandscape2025.pdf), p. 11).
  - Legal-aid and court staff are trained to distrust exactly this.
  - Some organisations' mail and web filters may block such domains (**judgement**, not checked).
  - The strategy's own headline finding is that government websites have been taken over by gambling and spam
    sites. Sending people to a `.xyz` site to check government contacts undercuts that message.
- **The name.** "-pedia" and "wiki" promise an encyclopedia that anyone can edit. But anonymous visitors get only
  "Show pagesource", so the public cannot edit. The pages name no editors and no attorney. That is a reasonable
  accuracy choice, but the name then promises something the site does not offer.

**Fix (judgement).** Serve the reviewed pages, or at least a mirror of them, from the university's own domain, with
the university's name and a named responsible unit on the page. Keep Lexipedia as the wiki and Wikibase workspace.
Point outreach at the university pages.

### 2.6 None of the norms a legal-aid site follows

Virginia's statewide legal-information site, [Virginia Law Help](https://www.virginialawhelp.org/) (valegalaid.org
redirects there), shows in its header:

- text-size controls;
- English and Español;
- a Quick Exit button;
- "Get Legal Help";
- do-it-yourself form tools.

Lexipedia has none of these. Not all of them fit a records page. But a legal-aid reviewer will check for a referral
route, a second language and a print view before reading the content.

---

## 3. What is naive or wrong

### 3.1 "Deadline arithmetic … is the safest side of the advice line"

The strategy says this in §1.3, and it is half right.

- **The unauthorised-practice risk is moderate.** Counting a statutory period from dates the user enters is close to
  general information, the more so when the rule is quoted and the counting is shown.
- **The reliance risk is the highest in self-help.** People act on a date literally. A wrong "you have until Friday"
  costs a right, and no disclaimer gives it back. The legal-aid rule of thumb is that the date is the one thing on
  the page that must be right (**judgement**).

**The "sent" error.** The strategy defines the requester view as "sent on date X, so the answer is due on date Y"
(§1.3; [wedge.md](wedge.md) §3.1 says the same). The clocks it quotes all run from receipt:

- "of receiving" (VA, WA);
- "of the receipt" (DC, NY);
- "after receiving" (MD);
- "from receipt" (CA);
- "after its receipt" (IL);
- "after the date of receiving" (TX).

In the code, `lexflow/lab/instances.py` builds an implied "received" event on the sending date, with the note
"assumed received the day it was sent; record the day it was received if different". The page asks only for "Date
the request was sent" (`dashboard/lab.js`), and the note shows as muted text beside the event. A mailed request, an
email sent after hours, or a request sent to the wrong office can be received days later. The lab would then show
the body as "overdue" and infer a deemed denial too early.

**Fix:**

- Ask "When did the office *get* your request? If you don't know, when did you send it?", and say which one you used
  in the result line itself.
- Where the date is assumed, show "about" and the next working day as well.
- Never show "overdue" or "deemed denied" on an assumed receipt date without saying so in the same sentence.

### 3.2 "Two lanes, one model": the safe default flips by lane

The lab resolves open readings conservatively for requesters ([lab-plan.md](../design/lab-plan.md) §5):

- The Virginia part day off is not counted as a working day by default.
- The B.4 extension is counted "to the later date, so it never calls a body overdue while it may still be in time".
- Christmas Eve 2026 is treated as a closure.

Each of these gives the *body* more time. That is right on the requester's screen. On the custodian's screen, and on
the clerk card in §7.6, it is backwards. The clerk is the person who violates the Act if a court takes the earlier
reading.

**Fix.** For the custodian lane, lead with the *earlier* date and show the later reading beside it with its basis.
Test that each view has its own default. The strategy promises "two lanes, one model". The model can be shared, but
the default reading cannot.

### 3.3 "Only through staff … keeps lexflow on the information side"

The strategy says this in §1.4, and it is not how the line works.

- **The content matters more than the channel.** A page is general information or individual advice because of
  what it says and does. Who forwards it does not change that.
- **Some staff make the risk higher, not lower.** Reentry counsellors, workforce-board staff and community-college
  advisors are usually not lawyers, and often not supervised by one. Non-lawyers applying eligibility rules to one
  person's record is the *Upsolve* fact pattern the strategy cites in §5.3.
- **Public pages are public.** If the licence pre-check pages (P5) are published on Lexipedia, residents will read
  them directly, whatever the plan says the audience is.

**Fix:**

- Keep the protection in the content. Describe the process ("you can ask DPOR's boards for a written, binding
  answer before you train; here is how"). Never apply it to a record.
- Where staff will use the pages with clients, say on the page what staff should *not* do: "Do not tell a client
  whether their record disqualifies them. Help them ask the board, or refer them to <free legal help>".
- Ask each staff partner whether a lawyer supervises the programme, and record the answer.

### 3.4 "Likely barred" and "seal first, then apply"

- **"Where a rule bars, say 'likely barred' plainly"** (§5.3). That is a prediction about one person's facts. The
  same section tells the team never to make one ("never apply eligibility rules to one person's facts"). Say instead
  what the rule says about a *category*: "Under § X, a board may deny for a conviction of <category>". Then give the
  route to a binding answer: the predetermination or the evaluation letter.
- **"Seal first, then apply"** (§1.4) is a recommended course of action. Write it as information: "If a record is
  sealed, Virginia agencies may not require you to disclose it on a licence application (§ 19.2-392.15)". Leave the
  sequencing to the client and their lawyer.

### 3.5 "Names the official place to check: the records officer, the FOIA Council or the board"

The strategy says this in §5.3.

- **For records, two of the three are fine.** The FOIA Council is neutral and trusted. The records officer is the
  other side, but harmless to name.
- **For a licence denial, the board is the adversary.** Telling a person with a record to "check with the board" is
  like telling a tenant to check with the landlord.

**Fix.** Every page gets a "Free legal help" line. In Virginia that means
[Virginia Law Help](https://www.virginialawhelp.org/) and its "Get Legal Help" route. For journalists' records
questions, it means the Reporters Committee's [Legal Hotline](https://www.rcfp.org/legal-hotline/). Have the partner
organisation choose the wording.

### 3.6 No lawyer in the loop

The review ladder in §6.3 has these steps:

- a student or Claude drafts;
- two reviewers attack it;
- the team fixes or rejects each finding;
- machine checks run;
- a "named human sign-off".

Nowhere does it say the human is a licensed attorney in that jurisdiction. P1 calls a law or policy student's model
"the human gold standard". P2 and P5 rely on "two independent reviewers".

- **Why it matters.** Legal-aid organisations have content-approval rules. Typically an attorney signs off, and the
  page shows a review date (**judgement**). They cannot link to, embed or hand out material that fails their own
  rule, however good it is.
- **The governance gap.** Today no one at lexflow can answer a partner's question "who is the responsible attorney
  for this page?"

**Fix (judgement).** Before the licensing wedge, and before any legal-aid outreach:

- Put an attorney of record behind each state's content. The natural routes are a law-school clinic or externship
  run by licensed faculty (which also brings supervision and insurance), or a written review by the partner
  organisation's own attorney.
- Make students drafters and adversarial checkers, never the final sign-off.
- Add two questions to the counsel list in [models.md](models.md) §9:
  - Does the university's insurance cover public legal information and a deadline calculator?
  - Do Virginia, DC and Maryland have anything like Texas's software safe harbour (Tex. Gov't Code § 81.101(c))? I
    did not find one in this pass (§10).

### 3.7 Corrections in 48 hours, and no way to recall a wrong date

- **Corrections from practitioners need legal review too.** The strategy's premise is that people miscount these
  clocks. So a clerk's "correction" may be the very error the tool exists to catch. "Fix it within 48 hours and thank
  the reporter" (§7.1) needs a middle step: an attorney confirms the correction against the text before it goes live.
- **Pull first, fix second.** The 48-hour target is fine for the fix. When a date is reported wrong, the page should
  instead show "Under review; do not rely on this date" within hours.
- **There is no recall path.** Cases are kept in `localStorage`. The case export carries the model ID but no version
  or date. The `.ics` export carries the rule, the quote and how the date was counted, but no model ID or version
  (`dashboard/lab.js`). There is no public list of known errors. When a model is fixed, nobody who relied on the old
  date can find out.
- **The reminder comes too late for anyone who needs help.** The `.ics` alarm fires one day before the deadline
  (`TRIGGER:-P1D`). That is fine for a records reply. For any deadline where the person may need a lawyer or has to
  file something, one day's notice is too late. Add an earlier reminder, for example halfway through the period.

**Fix:**

- Stamp every case, export and `.ics` with the model ID, version and date.
- Keep a public "known errors" page by model version.
- When a saved case is opened, check its version against the current one. If it changed, say "The rules this case
  was counted under have been corrected; check these dates again".

This keeps the no-server privacy design and still gives people a way to find out.

### 3.8 The Document Assembly Line offer cannot be delivered yet

§3.5's first offer to the Assembly Line community is "the after-filing deadline for one existing interview, computed
from a reviewed model".

- The Assembly Line builds **court forms** ([landscape.md](landscape.md) §4). None of the 22 reviewed models is a
  court process. They cover records requests and business formation.
- The deadlines after a court filing live in **court rules**, which lexflow does not index. Most of the 12 ladder
  rungs that depend on rules outside the corpus depend on court rules.
- landscape.md lists the Assembly Line's court and legal-aid contracts in Massachusetts, Alaska, Illinois, Michigan
  and Wisconsin, among others. Of these states, only Illinois is among lexflow's eleven, and only for records and
  business.

As written, the offer would bring the community an unreviewed sealing ladder or nothing. It would land as a newcomer
who has not read the project.

**Fix.** Do not offer it until the deadline engine is a tested JavaScript library (§7.2). Then offer the *library*:
"a business-day calculator with statute-sourced holiday calendars and N published test cases per state, under a
permissive licence". Do not offer a deadline. Let the community decide which interview needs it.

### 3.9 Legal aid as a buyer of "rule packs"

Model B lists "legal-aid self-help sites" among the institutions that would pay about $5,600 to $14,400 per state per
process per year (§5.1, **estimate**).

- **Legal aid will not pay that from operating funds** (**judgement**). At most it would be a line in a grant, and
  LSC's TIG is the main technology grant.
- **An open-source legal-aid tool already does this job.** LSC funded Atlanta Legal Aid Society to adopt LACI, which
  Lone Star Legal Aid developed to "automatically track and update changes in laws, regulation, and court rules"
  (per [models.md](models.md) §2, from LSC's TIG awards page). A university project selling a rival to legal aid
  would be badly received.

**Fix.** Treat legal aid as a Model A partner, at most a technical partner on a grantee's application, and never as a
Model B customer. Find out whether LACI takes outside contributions (§10). If it does, lexflow's section-level
amendment matching (P10, option B) is a contribution, not a product.

### 3.10 The licensing wedge will meet the jobs it does not cover

The Virginia reference is careful, and its own notes show the limits:

- **Predetermination is DPOR only.** The binding predetermination in § 54.1-204.1 is available "from a regulatory
  board within the Department of Professional and Occupational Regulation or from the Department"
  ([Va. Code § 54.1-204.1](https://law.lis.virginia.gov/vacode/title54.1/chapter2/section54.1-204.1/)). It does not
  reach the Department of Health Professions' boards, so it does not reach nurse aides or other health occupations.
- **Barrier crimes are left out.** The reference's search profile lists "employment of persons convicted of barrier
  crimes" among its *negative* (off-topic) terms. Yet "barrier crime", defined in
  [Va. Code § 19.2-392.02](https://law.lis.virginia.gov/vacode/title19.2/chapter23.1/section19.2-392.02/), governs
  background checks for many jobs caring for children, the elderly or disabled people.
- **Other jobs sit outside it too.** Federal bars, such as CDL disqualifications, and trades with no state licence
  are outside the model, and the reference says so in its `out_of_corpus` list.

When program staff name their 20 occupations (P5), several will be care jobs, driving jobs or unlicensed trades
(**judgement**, to be tested in interviews). Most of the pages would then say "board-specific; check here".

**Fix:**

- Plan for this up front. Each occupation page opens with "What governs this job?": the general licensing rule; a
  board's own statute; an employment background-check rule (barrier crimes); a federal rule; or no licence at all.
  Only then does it give the route.
- Fix the outreach line. Week 8's "the law may let them ask the board first" should say "for trades licensed by
  DPOR's boards".

### 3.11 Evidence that is six years old

The licensing figures come from IJ's 2020 report, as reproduced by CCRC (§1.4):

- 21 states where boards may deny without considering rehabilitation;
- 12 states with no guaranteed appeal;
- 30 states that changed their laws between 2015 and 2020.

The argument is that "remembered rules are often wrong", and it rests on numbers that are themselves stale. Legal-aid
and reentry audiences track this closely.

**Fix.** Use current comparisons, such as CCRC's restoration-of-rights resources, and date every figure in outreach.

### 3.12 `localStorage` on library computers

The strategy recruits residents through "a public library's reference desk" (§2.3). Library computers are shared.
The lab keeps every case in the browser's `localStorage` by default, so the next patron sees the list. A per-case
Delete button exists (`dashboard/lab.js`), but nothing prompts a user to use it.

**Fix.** Add a "shared or public computer" mode, on by default, that keeps nothing after the tab closes. Add an
explicit "Save on this device" choice and a "Clear everything" button. Test the mode in the usability study (P7).

---

## 4. The user-discovery questions

The method in §2.2 is sound: past behaviour, artefacts, pull signals, IRB first. These are the edits I would make.

### 4.1 Legal-aid attorneys, self-help and reentry staff (§2.7)

| Question in the strategy | Verdict | Why, and the replacement |
|---|---|---|
| Which of your self-help guides or screeners went out of date most recently? How did you find out, and how long did the fix take? | **Keep; lead with it** | The best question in the plan. It tests the content-maintenance nail (§7.1) |
| Where do the rules in your screener come from, and who updates them? | Keep | — |
| The last time a client asked whether a record would block a licence, what did you do? How long did it take? | Keep, with a guard | Open with "Without any details about the client…". Rule 1.6 makes staff careful, and the strategy wants no case facts |
| Which licences come up most? Which have you seen refused? | Keep, and add a question | Add: "For those jobs, what actually blocked people: the licence, an employer's background check, a federal rule, or the cost of training?" This tests §3.10 |
| Has a client asked a board for a determination before training? What happened? | Keep | Add: "Who in your programme decides which trades you train people for?" That person is the real user of "ask before you train" |
| When you use a summary someone else wrote, what makes you trust it: quotes, a review date, a named reviewer? | **Rewrite** | It is leading: it lists lexflow's own features as the answers. Ask instead: "Tell me about the last outside resource you stopped linking to or handing out. Why?" and "Who in your organisation must approve an outside resource before staff give it to clients? What do they check?" |
| Which grants pay for your technology work, and who writes them? | **Cut from first interviews** | Legal-aid tech staff are approached often by teams who want to be the "technical partner" on their TIG application (**judgement**). Asked early, this reads as fishing. Ask it only after they have used something |

**Add these:**

- "How do clients get the information you give them: paper, phone, text, a website, in person? In what languages?"
- "What reading level do your materials aim for, and who checks it?"
- "Tell me about the last time something you handed out turned out to be wrong. How did you reach the people who had
  it?" This is the harm and recall question, and nothing in the plan asks it.
- "What questions do your non-lawyer staff get that they are not allowed to answer? Where do they send them?" This
  finds where the advice line really runs in that programme.
- "After a client files <the form you help with most>, who tells them the next deadline, and how?" This tests the
  claim that tools "stop at filing", which today rests on a desk review
  ([lab-research.md](../design/lab-research.md) §2.1).
- For reentry staff: "How does a client get a copy of their own criminal record, and how long does it take?" The
  strategy's own sealing analysis says records data is the bottleneck ([wedge.md](wedge.md) §3.2). If getting one's
  own record is the step that stalls everything, it may be a better process to model than the licence ladder.

### 4.2 Residents (§2.10 and §2.3)

- **"Five minutes of help on their own question, with the official office to check"** is §2.3's "give first" offer
  to residents. Cut it.
  - It is individual help by non-lawyers, the very thing the strategy rules out elsewhere.
  - It contradicts "never collect a person's case facts".
  - For an IRB, it is an inducement that ties the benefit to disclosing a legal problem.
- **Instead,** pay participants a modest fee or a gift card, approved by the IRB. Offer everyone the partner's own
  referral sheet whether or not they take part.
- **Recruit and consent in plain language,** and in Spanish where the partner serves Spanish speakers. Read the
  consent aloud. A flyer that only fluent readers can follow will recruit only fluent readers.
- **Test understanding, not only speed.** P7's timed task ("your request went unanswered; what is your next step and
  its deadline?") is good. Then add: "In your own words, what does 'deemed denied' mean here?" and "What would you do
  tomorrow?" Lawyer words like deemed denial, custodian, petition and mandamus are where low-literacy users fail
  (**judgement**).

### 4.3 Clerks and municipal attorneys (§2.4, §2.6)

- **Interview notes held by a public university may themselves be public records.** [models.md](models.md) §5.4 says
  this. The interview guidance does not tell the interviewee. Say it in the consent script, and design the log so
  that nothing in it would embarrass an office if released.
- **[wedge.md](wedge.md) §7 still asks clerks "Have you ever missed a deadline? What happened?"** That asks a public
  official to admit a violation of law to a public institution. The adoption strategy's softer version ("The last time
  a request did not fit the pattern…") is right. Delete the wedge.md version so a student does not use it.
- **Attorneys (§2.6) are well covered.** The question about checking an AI tool's citation and finding it wrong is a
  good one. Ask it *before* showing anything labelled "checked by Claude".

### 4.4 Questions missing for every audience

- "If you found one mistake in a page like this, what would you do?" Stop using it, report it, or warn colleagues?
  The answer sets the bar for the corrections process.
- "Who would get in trouble if you relied on this and it was wrong?" This finds the real approver and the real risk.
- "Would you print this?" Clerks and legal-aid staff often work from paper. The answer settles whether the clock card
  and the one-pagers come before the widget.

---

## 5. The content drafts

### 5.1 Example draft 1: the blog post (§7.4)

It is clear and candid about coverage. Five fixes:

1. **Say who reviewed it.** "Each model was then reviewed adversarially, for legal accuracy against the statute's
   words and for completeness, and fixed" does not say that the reviewers were AI agents. When a reader finds out,
   from the README or the "checked by Claude" label, the post will look evasive. Write instead:
   - "Each model was drafted by an AI system from the statute text, then checked by separate AI reviewers and by
     machine against the official text. **No attorney has reviewed these models yet**; <name> checked this post
     against the statutes."
   - Change the last sentence once an attorney has signed.
2. **Maryland's first deadline is wrong in the table.** The row gives 30 days. But § 4-203(b)(2) requires a written
   notice "within 10 working days after receipt of the request" whenever the custodian expects production to take more
   than 10 working days. That notice must give the time expected, a fee range and the reason
   ([§ 4-203](https://mgaleg.maryland.gov/mgawebsite/Laws/StatuteText?article=ggp&section=4-203&enactments=false)).
   lexflow's own Maryland model has this step. The table should too: "a notice within 10 working days if production
   will take longer; a decision within 30 days".
3. **The Virginia court route is out of order.** "A court, which must hear the petition within seven days once the
   body has had a copy for at least three working days" mixes up the sequence. The statute says the petition is
   heard within seven days "provided the party against whom the petition is brought has received a copy of the
   petition at least three working days prior to filing"
   ([§ 2.2-3713(C)](https://law.lis.virginia.gov/vacode/title2.2/chapter37/section2.2-3713/)). A self-represented
   requester who files first and serves later loses the fast hearing. Write: "send the public body a copy of your
   petition at least three working days *before* you file it; the court must then hear it within seven days".
4. **Add who to ask for help.** For requesters, link VCOG for Virginia and the Reporters Committee's Legal Hotline for
   journalists. One line, under "What this is not".
5. **Use plain words in the text around the table.**
   - "Deemed a denial" → "the law treats silence as a refusal".
   - "Petition a court" → "ask a court to order the records released".
   - Keep the statute's words inside the quote marks only.

### 5.2 Example draft 3: the clerks' newsletter note (§7.6)

This is the strongest draft. Clerks get something real, and the ask is small. Four fixes:

- **Lead with the earlier date** on the card itself (§3.2). Where the law is open, print "Due: Tue 29 Dec (safest).
  Some readings allow Wed 30 Dec; see note". Do not print the reverse.
- **A one-page card cannot list "every working day of 2027"**: that is about 250 rows. Offer a month-by-month grid,
  or a lookup by day received ("Received on a Monday in a week with no holiday → due the next Monday"), with the
  holiday weeks spelled out. Test the layout with one clerk before offering it to three.
- **Say who is responsible.** "It isn't legal advice, and it doesn't replace your city or county attorney or the FOIA
  Council" is right. Add: "Ask your attorney to look at the card before you rely on it". That puts the card inside
  the clerk's own approval chain instead of around it.
- **Local closures are the clerk's to give.** The card's date is only as good as the schedule sent in. Print the
  schedule used, and its date, on the card.

### 5.3 The week 8 legal-aid offer

The offer: "Before a client trains for a licence, the law may let them ask the board first; here is that route,
quoted, for your state". It goes with "the licence-denial reference and ladder for their state, for markup".

- **It is not a gift.** The artefact is a 42 to 67 KB AI-written reference at lawyer reading level
  (`curated_ask/license_conviction/*.json`), and the request is for an attorney to check it for free. To the
  recipient, that is a request for unpaid quality work on AI output (**judgement**).
- **The line overgeneralises.** In Virginia the binding route covers DPOR's boards only (§3.10).

**What to give instead** is something the recipient already needs and can check in ten minutes. For example: "We
checked the statute sections cited in your organisation's five licensing and record-clearing guides against the
current official text. Two sections have been amended since your guides' review dates. Here are the changes, quoted,
with the dates". This needs only public guides, the statute index and the version flags lexflow already records. It
gives without asking, and it shows the one thing legal aid will come back for (§7.1).

**A model of the shape** (REWRITE: the person rewrites it, checks every fact and signs it):

> Subject: Statute changes affecting <N> of your public guides
>
> I work on lexflow, a research project at <university> that tracks state statutes section by section. We checked the
> sections cited in <organisation>'s public guides on <topic> against the official <state> code as of <date>.
> <N> cited sections have changed since the dates shown on the guides. The attached page lists each one: the guide,
> the section, the old and new words, and the official link. Nothing here is advice. We have not looked at anything
> except your public pages.
>
> If this is useful, I would value 20 minutes to learn how your team keeps guides current. If it is not, no reply is
> needed and we will not follow up more than once.
>
> <name>, <role>, <university>. An AI tool helped compare the texts; I checked every change myself.

### 5.4 Example draft 2: the Wikidata note (§7.5)

There is no legal-aid concern here. It is the right register for that community.

---

## 6. What is missing: a gate before any legal-aid outreach

The strategy has gates for vendors (§4.4) and for Sunshine Week (§8.3). It needs one for legal aid. My list, in
order (**judgement**):

| # | Gate | Why it matters to legal aid | Size |
|---|---|---|---|
| 1 | Statutory unit phrases on every step; derived figures marked (§2.2) | Accuracy, in the words the strategy promises | Small |
| 2 | Public labels changed: no model name or "quality" score; "Not yet reviewed by an attorney" until one has (§2.1) | Trust, and honesty about review | Small |
| 3 | Builder notes and code identifiers off the public pages (§2.3) | Readability | Small |
| 4 | Licence footer corrected after counsel (§2.4) | Librarians and attorneys check it | Small |
| 5 | A "Free legal help" line on every page, worded with the partner (§3.5) | The first thing a legal-aid reviewer looks for | Small |
| 6 | An attorney of record per state, through a clinic or the partner (§3.6) | Partners cannot hand out unsigned material | Medium |
| 7 | Receipt, not sending, as the anchor; assumptions stated in the result line (§3.1) | The date must be right | Small |
| 8 | A separate default reading per lane (§3.2) | Clerks must not be told the later date | Small |
| 9 | Versioned cases and exports, a known-errors page, and a stale-case check (§3.7) | Recall | Medium |
| 10 | A shared-computer mode for the lab (§3.12) | Library and legal-aid office computers | Small |
| 11 | A plain-language layer, reviewed, with a reading-level target set with the partner (§2.3) | The people the plan serves in the end | Medium |
| 12 | Spanish for the plain-language layer, by a qualified legal translator rather than machine translation | Legal-aid sites commonly publish in Spanish (**judgement**; Virginia Law Help's header has it). Federal LEP guidance under EO 13166 was revoked in March 2025 ([EO 14224](https://www.whitehouse.gov/presidential-actions/2025/03/designating-english-as-the-official-language-of-the-united-states/)), so this rests on what the audience expects and on partners' own obligations, not on a federal mandate | Medium |
| 13 | Print-first versions of the clock card and the one-pagers; mobile checked on a small phone | Phone-dependent and paper-using audiences (§0 item 11) | Small |
| 14 | The Ask page's "For the wiki" switch turned off for unreviewed answers; the 26 "Unreviewed draft" Wikibase items hidden from the public, or kept out of search | One unreviewed machine answer found by a partner undoes the rest (README: "tick **For the wiki** to publish an answer"; the Wikibase notes 26 draft items "marked … none were deleted") | Small |
| 15 | Reviewed pages on a university domain (§2.5) | Trust and filtering | Small to medium |

Items 1 to 5, 7, 8, 10, 13 and 14 are days of work, not months (**estimate**). Until items 1 to 8 are done, I
would not send a legal-aid organisation a single link.

---

## 7. What would earn my attention and repeat use

People return to tools that tell them something changed, or that they need every week. A static process map is
read once. These four uses fit legal aid and keep lexflow on the information side.

### 7.1 An amendment watch for the sections my guides cite

- **The job.** "Tell my content team when a statute section our guides cite has been amended, or a bill would amend
  it, with the old and new words quoted."
- **Why it fits:**
  - The readers are attorneys maintaining content, not clients, so the advice line is not in play.
  - Every output can be checked against the official text.
  - It uses what lexflow already has: section-level text, version flags, and Open States, whose data is in the public
    domain ([landscape.md](landscape.md) §3).
- **The catch.** LACI already exists for legal aid (§3.9). Contribute, or match its format, rather than compete.
- **The student project.** P10, option B (bill watch), moves from "later" to first in line for legal aid, scoped to
  one state's self-help site with that organisation's consent.

### 7.2 A deadline library, not a deadline page

- **The job.** "Give my docassemble interview a function that counts N working, business or calendar days under
  state X's rules, with the holiday calendar sourced and dated, and show me the test cases."
- **Why it fits.** It is the one technical asset with no equal in the self-help stack: docassemble's date helpers have
  no business-day calendar ([landscape.md](landscape.md) §4).
- **What it needs:**
  - the JavaScript port and the cross-run of the test cases (§4.1, P2);
  - a permissive licence;
  - test cases published per state, with each case's source;
  - clear coverage: which periods are statutory, and which come from court rules it does not cover.

### 7.3 An attorney-signed, dated table I can check my own guides against

The Sunshine Week table (§3.6) is the right idea for journalists. For legal aid, the same thing works for any
statutory clock that self-help guides cite. Every cell is quoted, dated and signed, and the gaps are listed.
Content teams use such a table to check their *own* pages, which is safe, useful and repeatable.

### 7.4 Licensing one-pagers for staff, with "what governs this job" first

This is P5, restructured as in §3.10, and signed by an attorney:

- the board's binding answer route, its cost and its clock;
- the challenge route and its deadline;
- a fixed "do not tell the client whether they qualify" line;
- a referral line;
- a separate plain-language sheet for clients, tested with the partner's clients.

---

## 8. Hammer, nail and plugins, from legal aid

**Is it a hammer looking for a nail? For legal aid, mostly yes, today.**

- **The finished work is not in legal aid's areas.** The 22 reviewed models are records and business formation.
  Low-income households' most common civil legal problems are consumer issues, health care, housing and income
  maintenance ([LSC Justice Gap 2022](https://justicegap.lsc.gov/resource/executive-summary/)).
- **The licensing and sealing work is not finished for any reader.** It is AI-written, has no human review, and is
  written for lawyers.
- **BPMN is irrelevant to legal aid.**
- **Two assets do have legal-aid pull:** the deadline engine with statute-sourced calendars, and section-level change
  detection. Both are infrastructure for people who maintain content, not destinations for people who need help.

**The richer nail, to test and not to assume.** Legal aid lives on *notice-to-deadline* clocks:

- "I got this notice dated X; by when must I appeal?"
- A SNAP household may request a fair hearing on any action in the prior 90 days
  ([7 CFR 273.15(g)](https://www.ecfr.gov/current/title-7/subtitle-B/chapter-II/subchapter-C/part-273/subpart-F/section-273.15)).
- A Virginia unlawful-detainer appeal "shall be taken within 10 days", with the bond posted in the same 10 days
  ([Va. Code § 8.01-129](https://law.lis.virginia.gov/vacode/title8.01/chapter3/section8.01-129/)).

These are frequent, high-stakes and countable, and lexflow's engine is built for exactly this. But they live in
federal regulations and court practice that lexflow does not index. Short periods like these are where a wrong date
does the most harm. They are a reason to ask legal-aid staff about notice-driven deadlines in interviews (§4.1). They
are not a reason to build one.

**Plugins.** Granicus and CivicPlus are irrelevant to legal aid. The legal-aid equivalents of "a plugin" are:

- a docassemble or Assembly Line package that calls the deadline library (§7.2);
- a link or embed approved by a statewide legal-information site's content team. That needs the attorney sign-off
  in §3.6, and probably the plain-language layer.

"Free tools, with a service behind them" is the legal-aid norm. But the service is paid for by grants and courts,
not by legal aid buying it (§3.9).

**The graduate students.** These small, niche goals would actually bridge process modelling into legal-aid practice
(**judgement**). Each runs under a supervising attorney, with the model underneath and invisible:

1. **A citation-freshness audit** of one legal-aid site's public guides, with the organisation's consent (§5.3, §7.1).
2. **The JavaScript deadline library** and its published test suite (§7.2).
3. **A plain-language and Spanish layer** for Virginia's "after you file" page, tested with ten library patrons for
   understanding (§4.2).
4. **"What governs this job"** for the 20 occupations staff name (§3.10).
5. **A shared-computer and recall design** for the lab, with a usability test (§3.7, §3.12).

---

## 9. Metrics a legal-aid partner would ask for

The strategy's metrics (§8.1) measure use and engagement. A legal-aid partner will ask about harm first. Add these:

| Metric | Definition | Target (**estimate**) |
|---|---|---|
| Wrong dates live | Errors in a date or a deadline unit found on a public page, and hours from report to the page being pulled | 0 known; pulled within 4 hours |
| Exposure | For each confirmed error: the days it was live, and whether any exported case or `.ics` used it | Recorded for every error |
| Attorney sign-off coverage | Share of public pages signed by a licensed attorney in that jurisdiction, with a date | 100% of anything offered to legal aid |
| Review age | Days since each page's last attorney review, and since its quoted sections were checked against the official text | Under 180 and under 30 (**estimate**) |
| Comprehension | In P7's task, the share of participants who explain the next step correctly in their own words, not just the share who find the date | Reported separately for participants recruited through literacy or library partners |
| Reading level | The plain-language layer's grade level, checked by the partner's own method | Set with the partner |

Keep the strategy's "complaints = 0" rule. Add to it: any partner saying "we can't use this because…" counts as a
complaint. Log the reason.

---

## 10. Not verified

- **Unauthorised-practice law outside Texas.** I did not read Virginia's unauthorised-practice rule; the two vsb.org
  URLs I tried returned 404. I found no software safe harbour like Tex. Gov't Code § 81.101(c) for VA, DC or MD in
  this pass. That is not a finding that none exists. Counsel to confirm.
- **Lexipedia's edit permissions.** That anonymous visitors cannot edit is inferred from the "Show pagesource" link
  and the "Log In" link on the pages, not from the wiki's configuration.
- **Reading levels.** They come from a rough Flesch–Kincaid formula run on the text (section citations replaced by
  a word). Treat them as indications only.
- **Pew's income figure.** The 34% is the 2025 row of the fact sheet's "smartphone dependent, by annual household
  income" chart, for the lowest income band. The chart's column labels mix two survey series. Both series' lowest
  band is under $30,000.
- **LACI.** It is cited from [models.md](models.md), which opened LSC's TIG awards page. Whether LACI takes outside
  contributions was not checked.
- **Whether `.xyz` domains are blocked** by legal-aid or court mail and web filters was not checked. The Interisle
  ranking is about phishing reports, not filtering.
- **Legal-aid practice norms** (content approval by attorneys, typical reading-level targets, how often legal-aid tech
  staff are approached about TIG partnerships) are the reviewer's judgement, to be confirmed in the interviews in
  §4.1.
- **Federal sources.** federalregister.gov served a bot check, and the ABA site answered 403. Neither was worked
  around, and no claim here rests on them.

---

## Sources

Opened on 10 October 2026 for this note:

- Lexipedia, Virginia records: https://lexipedia.xyz/doku.php?id=lexflow:va:records
- Lexipedia, Maryland records: https://lexipedia.xyz/doku.php?id=lexflow:md:records
- Lexipedia, DC records: https://lexipedia.xyz/doku.php?id=lexflow:dc:records
- Lexipedia, Virginia: https://lexipedia.xyz/doku.php?id=lexflow:va
- Md. Code, General Provisions § 4-203:
  https://mgaleg.maryland.gov/mgawebsite/Laws/StatuteText?article=ggp&section=4-203&enactments=false
- Va. Code § 2.2-3713: https://law.lis.virginia.gov/vacode/title2.2/chapter37/section2.2-3713/
- Va. Code § 54.1-204: https://law.lis.virginia.gov/vacode/title54.1/chapter2/section54.1-204/
- Va. Code § 54.1-204.1: https://law.lis.virginia.gov/vacode/title54.1/chapter2/section54.1-204.1/
- Va. Code § 19.2-392.02: https://law.lis.virginia.gov/vacode/title19.2/chapter23.1/section19.2-392.02/
- Va. Code § 8.01-129: https://law.lis.virginia.gov/vacode/title8.01/chapter3/section8.01-129/
- 7 CFR 273.15 (eCFR):
  https://www.ecfr.gov/current/title-7/subtitle-B/chapter-II/subchapter-C/part-273/subpart-F/section-273.15
- NCES, PIAAC 2023 U.S. national results: https://nces.ed.gov/surveys/piaac/2023/national_results.asp
- Pew Research Center, Mobile fact sheet: https://www.pewresearch.org/internet/fact-sheet/mobile/
- LSC, 2022 Justice Gap Study, executive summary: https://justicegap.lsc.gov/resource/executive-summary/
- Executive Order 14224, "Designating English as the Official Language of the United States" (1 March 2025):
  https://www.whitehouse.gov/presidential-actions/2025/03/designating-english-as-the-official-language-of-the-united-states/
- Virginia Law Help: https://www.virginialawhelp.org/
- Reporters Committee for Freedom of the Press, Legal Hotline: https://www.rcfp.org/legal-hotline/
- Interisle Consulting Group, *Phishing Landscape 2025* (September 2025): https://interisle.net/s/phishinglandscape2025.pdf

Cited through the strategy notes, which opened them:

- Va. Code § 2.2-3704: https://law.lis.virginia.gov/vacode/2.2-3704/
- D.C. Code § 2-532: https://code.dccouncil.gov/us/dc/council/code/sections/2-532
- Tex. Gov't Code § 81.101: https://tcss.legis.texas.gov/resources/GV/htm/GV.81.htm#81.101
- *Upsolve v. James*, summary:
  https://clpblog.citizen.org/second-circuit-holds-unlawful-practice-law-can-apply-to-debt-collection-advice/
- Stanford HAI, legal AI hallucination benchmark:
  https://hai.stanford.edu/news/ai-trial-legal-models-hallucinate-1-out-6-or-more-benchmarking-queries
- LSC TIG awards by year (LACI):
  https://www.lsc.gov/grants/technology-initiative-grant-program/technology-initiative-grant-awards-tig-projects-funded-year
- CCRC, reproducing IJ's *Barred from Working* (2020):
  https://ccresourcecenter.org/report-card-on-licensing-laws-finds-progress-but-still-a-way-to-go/

In this repository (read-only): [adoption-strategy.md](adoption-strategy.md), [wedge.md](wedge.md),
[communities.md](communities.md), [models.md](models.md), [landscape.md](landscape.md),
[README.md](../../README.md), [lab-plan.md](../design/lab-plan.md), [lab-research.md](../design/lab-research.md),
`curated_ask/license_conviction/*.json`, `curated_ask/record_sealing/va.json`, `curated/md/records.json`,
`lexflow/lab/instances.py`, `dashboard/lab.js`.
