# A municipal clerk reads the adoption strategy

_Status: critique, 10 October 2026. It reviews [adoption-strategy.md](adoption-strategy.md) and its research notes
([wedge.md](wedge.md), [communities.md](communities.md), [landscape.md](landscape.md), [models.md](models.md)) from
one chair: an experienced clerk and records officer in a mid-sized US city. That clerk answers public-records
requests, works within procurement rules, and has sat through many technology pitches. Research and writing only.
Nothing was posted, sent, signed up for or edited, and no wiki was touched. This is the only file written._

_How to read the labels. **Verified** means I opened the source on 10 October 2026 and link it. **Judgement** means
the practitioner's view from the counter: it is what I would expect to see, not a checked fact, and the interviews
should test it. **Estimate** marks a number that is a guess. None of this is legal advice._

_Method. I read the five strategy notes in full, `README.md`, `curated/va/records.json`,
`docs/answers/va-charlottesville.md`, `docs/answers/md-baltimore.md`, the Virginia part of `lexflow/lab/deadlines.py`
and the storage section of [lab-plan.md](../design/lab-plan.md). Web pages were read with `curl`, one at a time, at
least 1.5 seconds apart per host, with the User-Agent `lexflow-research/0.1 (https://github.com/alibama/lexflow)`.
federalregister.gov served a bot check on its HTML page, so I read the same document through its public API, which
the block page itself points to. One Spamhaus page returned 404. The session's web-search budget was used up before I
could check the reputation of the `.xyz` domain, so that point is marked as judgement. I ran the lab's own date
engine once, locally, to compare two readings of one Virginia deadline._

_Credit and privacy. This note names organisations, official offices, statutes and published works only. No
organisation named here is a partner, advisor, endorser or prospective collaborator of lexflow. The Lexipedia page
for Charlottesville names two city staff members; I do not repeat their names here._

## Contents

0. [The verdict on one page](#0-the-verdict-on-one-page)
1. [The 30-second test: why I would ignore the email](#1-the-30-second-test-why-i-would-ignore-the-email)
2. [What is naive or wrong](#2-what-is-naive-or-wrong)
3. [What would earn my attention, and keep it](#3-what-would-earn-my-attention-and-keep-it)
4. [The discovery questions: which are off, and better ones](#4-the-discovery-questions-which-are-off-and-better-ones)
5. [The content drafts: how each would land, and fixes](#5-the-content-drafts-how-each-would-land-and-fixes)
6. [Plugins and the service model, seen from the counter](#6-plugins-and-the-service-model-seen-from-the-counter)
7. [The graduate-student programme, seen from the counter](#7-the-graduate-student-programme-seen-from-the-counter)
8. [What is missing](#8-what-is-missing)
9. [What the strategy gets right](#9-what-the-strategy-gets-right)
10. [Not verified](#10-not-verified)

---

## 0. The verdict on one page

The strategy is more honest than most pitches I see. It says "partly, yes" to the hammer question, puts
interviews before building, and refuses to show unreviewed drafts. But it was written from the requester's side of
the counter and from the data, and it has not yet met the office it wants to serve. These are my top findings, most
serious first.

1. **The front door would end the conversation.** A clerk who gets a clock card will look up who sent it. Today
   [lexipedia.xyz](https://lexipedia.xyz/) says it was "Built by the Center for Civic Innovation". It lists LexDAO
   as a sponsor, promises "smart contracts" for legal engineers, and shows "Prospera, Roatan, Honduras" as a
   jurisdiction under review (**verified**). Próspera is a privately run charter zone. Honduras repealed the law that
   enabled such zones in 2022, and the zone's developer brought an investment arbitration against Honduras
   ([Wikipedia, "Próspera"](https://en.wikipedia.org/wiki/Pr%C3%B3spera)). The strategy calls lexflow "a research
   project at <university>". A sender with three identities and a crypto flavour reads to me as a vendor in
   disguise. Fix the identity and the start page before any outreach to a public office (§1).
2. **"Reviewed" means reviewed by an AI, and the pages hide it in plain sight.** The Virginia records model carries
   `reviewed_by: "Claude (claude-opus-5-5)"`. The README names no human reviewer (for the AskBench references it
   counts "90 agents"). Nothing in the README or the model files names a person, let alone a lawyer, who signed off
   a model. Yet the live Charlottesville page says "Confidence 1.00: state law 1.00, local
   1.00, contact 1.00" above a caveat that says "Confirm the current contact" (**verified**). §6.3 of the strategy
   says nothing leaves the team without a named human sign-off. The 22 published models already break that rule.
3. **The Virginia model's extension date disagrees with the city's own published rule.** Charlottesville's page says
   a timely extension letter gives "seven additional working days ... a total of 12 working days"
   ([Charlottesville](https://www.charlottesville.gov/770/Our-FOIA-Responsibilities), **verified**). The model's own
   gap note says its timer runs from the date of the extension letter instead. With the lab's engine, a request
   received on Monday 21 December 2026 whose extension letter goes out the next day is due on **Tuesday 5 January
   2027** on lexflow's reading, and on **Monday 11 January 2027** on the city's. A requester using the lab would be
   told the city was in "deemed denial" four working days before the city thinks it is due. That is a fight at my
   counter, and it breaks the lab's own rule that it "does not call a body overdue while it may still be in time"
   (§2.4).
4. **The clerk is often not the person who answers records requests.** In Charlottesville, the strategy's first
   candidate, requests go to the City Attorney's Office and a GovQA portal. The city is 45,672 people, not a small
   office counting its own clock. Baltimore has no central portal: each agency answers its own. DC runs a central
   GovQA portal. None of the three "answered places" is the custodian the strategy describes (small office, email
   and spreadsheet). In Virginia, constitutional officers are separate public bodies with their own FOIA officers
   ([Va. Code § 2.2-3704.2(D)](https://law.lis.virginia.gov/vacode/title2.2/chapter37/section2.2-3704.2/)). Target
   town clerks in small Virginia towns, where the clerk usually is the FOIA officer (**judgement**) (§2.1).
5. **The interview door the strategy picks is a records request.** §2.3 says the FOIA officer's published channel is
   "the right door for a records interview", and §2.2 says to "ask for the artefact". In Virginia a request "need not
   make reference to this chapter" to start the five-day clock
   ([§ 2.2-3704(B)](https://law.lis.virginia.gov/vacode/title2.2/chapter37/section2.2-3704/), **verified**). Email my
   FOIA inbox asking to see our tracking spreadsheet and you have filed a request, and my office logs it. Never use
   the FOIA intake for research contact (§4.3).
6. **The state already publishes what the strategy plans to build for Virginia contacts.** The FOIA Council must
   "maintain on its website a listing of all FOIA officers" (§ 2.2-3704.2(G)), and it does: a searchable list by
   public body, with email and telephone ([FOIA officers](https://foiaform.dls.virginia.gov/Home/Searchforms/0)). It
   also publishes sample letters and searchable advisory opinions
   ([FOIA Council](https://foiacouncil.dls.virginia.gov/foiacouncil.htm)). Every Virginia city, county, school board
   and town over 250 people must link from its homepage to a plain-English rights page (§ 2.2-3704.1(A)). The strategy mentions none of
   this. Link to it; don't rebuild it (§2.6).
7. **"Counting five working days is harder than it looks" is not my pain, and saying so is condescending.** FOIA
   officers must be trained at least every two years by counsel or the Council (§ 2.2-3704.2(E), **verified**). Many
   of us work inside a vendor portal that counts for us. What eats my week is volume, vague and bulk requests,
   email and video searches, redaction, fee estimates and, this year, machine-written requests
   ([Post-Journal, July 2026](https://www.post-journal.com/opinion/in-our-opinion/2026/07/in-our-opinion/)). The
   date is the easy part (**judgement**). The deadlines I actually worry about are my own: meeting notices and
   public-hearing advertisements (§3.3).
8. **"Two lanes, one model" is elegant code and poor diplomacy.** The same project that sends me a free card tells
   requesters when I am late and how to take me to court. Our office pays the requester's attorney fees if they
   substantially prevail (§ 2.2-3713(D)). Officers can face personal civil penalties for wilful violations
   (§ 2.2-3714(A)). Say plainly whose side the project is on: the law's, with both lanes showing the rules that make
   requests go smoothly (specificity, cost estimates, who may request), not only the escalation route (§2.3).
9. **Nothing about my requests can live in a browser tab.** The lab keeps cases in the wiki's `localStorage`,
   "which other plugins' scripts can read" ([lab-plan.md](../design/lab-plan.md)). For a resident that is privacy by
   design. For me it is a public record of the city held outside our systems
   ([§ 2.2-3701](https://law.lis.virginia.gov/vacode/title2.2/chapter37/section2.2-3701/),
   [§ 42.1-77](https://law.lis.virginia.gov/vacode/title42.1/chapter7/section42.1-77/)). Its retention can't be
   controlled, it may hold requesters' names, and IT would not allow it. The custodian lane should take dates only,
   or be paper (§2.8).
10. **Two planned activities would poison the relationships the rest of the plan needs.** P3 files real requests to
    the same small offices whose clerks P4 hopes to recruit, and measures whether they answer on time: that is an
    audit. The VML and VACo "website health" offer would tell leagues that 43% of members' websites are stale. What
    is stale is the listing in the Census and Wikidata, not the city's site. Keep P3 to published decisions. Tell
    each government about its own stale or hijacked domain privately, before anything is published (§2.10, §2.11).

**What would earn repeat use** (§3): a correct, printable FOIA due-date calendar that my own attorney has checked; a
ten-minute check of my vendor portal's due dates against it; a private alert that our old domain now serves
gambling; and, if interviews confirm it, a backward calendar for meeting notices and hearing advertisements. That
last one is the deadline clerks, planners and municipal attorneys share.

---

## 1. The 30-second test: why I would ignore the email

A clerk's first read of an unsolicited email takes seconds. Most pitches fail on the sender, not the content. Here is
what I would see, in the order I would see it.

| What I check | What I find today | What I conclude | Fix |
|---|---|---|---|
| Who is sending this? | The draft signs as "<name>, <role>, <university>". Lexipedia's home page says "Built by the Center for Civic Innovation" and lists LexDAO and Sartography/SpiffWorkflow as sponsors (**verified**) | Three identities: a university, a nonprofit and a "guild of legal engineers". Which one would I hold accountable? | Pick one accountable organisation, and say it everywhere |
| What is the link? | `lexipedia.xyz` | I do not open `.xyz` links from strangers. Some government mail filters strip or flag them (**judgement**; I could not check a TLD reputation source, §10) | Send clerk-facing material from a university-hosted page. Attach the card as a PDF, not as a link |
| What is on the front page? | Starting a business, Wikipedia's dispute process, "Prospera, Roatan, Honduras", "smart contracts", LexDAO (**verified**) | Crypto and charter-city politics. Nothing about my question | Move the experiments off the start page, or give the `lexflow:` pages their own front door |
| Can anyone change it? | A wiki with "Log In", "Define a New Model ... no experience needed" (**verified**) | Can anyone edit the date my staff will rely on? | State who can edit `lexflow:` pages. Lock them, and show the named reviewer and date on each |
| Who checked it? | "checked by Claude", "Confidence 1.00" (**verified**) | An AI checked an AI, and it claims certainty no lawyer would claim | Remove the confidence score from public pages. Name the human reviewer, or say "not yet reviewed by a person" |
| Does it name my staff? | The Charlottesville page names two FOIA staff members (**verified**) | Names go stale and invite harassment. You published my colleagues without asking | Use office titles and shared inboxes only |
| What do they want from me? | Corrections, an interview, closures, later a bulletin with me as lead author | Unpaid work for someone else's project | Give something finished first. Ask for one small thing |
| Is this an audit? | P3 files requests and measures on-time answers | You are testing my compliance | Keep test requests out of any locality you also ask for help |

The strategy's own rule, "give before you ask", is right. But the gift has to come from a sender who passes this
test.

---

## 2. What is naive or wrong

### 2.1 The clerk, the FOIA officer and the records manager are different people

- **Who answers requests varies.** Every Virginia public body must designate a FOIA officer (§ 2.2-3704.2(A)), and
  that officer can sit anywhere. In Charlottesville requests go online or to the City Attorney's Office
  ([Submit a FOIA Request](https://www.charlottesville.gov/774/Submit-a-FOIA-Request), **verified**), and the
  online portal is GovQA (`docs/answers/va-charlottesville.md`). The clerk of council is someone else. In Baltimore
  each agency answers its own requests (`docs/answers/md-baltimore.md`). DC's portal redirects to GovQA
  (`docs/answers/dc-washington_dc.md`). Police
  records often go through their own officer. Sheriffs, treasurers and commissioners of the revenue are separate
  public bodies (§ 2.2-3704.2(D); the Charlottesville page lists them).
- **"Records management" is mostly retention, not access.** The IIMC Records Management Committee and NAGARA deal
  mainly with retention schedules, disposition and archives (**judgement**). A FOIA clock is the wrong opener there.
- **So the first interview question is "who here answers records requests?"** It is not in any of the strategy's
  question lists (§4).
- **The circuit court clerk is not a municipal clerk.** In Virginia "clerk" often means the clerk of the circuit
  court, an elected constitutional officer. Say "town or city clerk" or "FOIA officer" and mean it.

### 2.2 The pain the strategy assumes is not the pain I have

- **The clock is trained and tooled.** FOIA officers must be trained every two years (§ 2.2-3704.2(E)). The Council
  runs the training free, and VMCA gives credit for it
  ([training page](https://foiacouncil.dls.virginia.gov/training.htm), **verified**). Offices on GovQA, NextRequest
  or JustFOIA get a computed due date. For most of us the date is not where the time goes (**judgement**).
- **What does hurt** (**judgement**, to test in interviews):
  - volume, and requests drafted by AI tools that "cast a wide net"
    ([Post-Journal](https://www.post-journal.com/opinion/in-our-opinion/2026/07/in-our-opinion/), **verified**);
  - email and messaging searches, and body-camera video;
  - redaction, and deciding which exemption applies;
  - cost estimates and the tolling rules around them;
  - finding records held by another department, or by a contractor.
- **Where the date does hurt, it is in the edge cases**, and those are exactly what the model leaves out (§2.5).
- **The strategy half-knows this.** §2.4 says "if the clock never comes up, the custodian lane may not be the pain",
  and §8.3's day-60 test drops the custodian tool if 4 of 5 clerks trust their vendor. The first candidate city
  already runs GovQA. Ask the vendor question in the first five interviews, before printing any card.

### 2.3 The two lanes pull against each other

- **Socially.** The requester lane shows when the body is late and how to escalate: the deemed denial, the FOIA
  Council, a court petition that "shall be heard within seven days"
  ([§ 2.2-3713(C)](https://law.lis.virginia.gov/vacode/title2.2/chapter37/section2.2-3713/), **verified**). The
  public body pays the petitioner's reasonable costs and attorney fees if they substantially prevail (§ 2.2-3713(D)).
  A court can fine officers personally for wilful and knowing violations (§ 2.2-3714(A), **verified**). A clerk
  will read a project that helps both sides as a project that helps the other side.
- **Technically.** The engine's default is right for requesters: it never calls a body late while it may still be in
  time, so it takes the later date when a part day off is unsettled (`deadlines.py`). For the custodian the safe date
  is the earlier one. "Two lanes, one model" needs two defaults: the custodian lane should print the earliest
  defensible date as "meet this", and the later one as "the latest reading".
- **Fix the framing.** Put the frictions that requesters create first in the requester lane: describe records with
  reasonable specificity; ask for a cost estimate; know who has the right to request. Every one of those makes my
  job easier and the request faster.

### 2.4 The Virginia extension: lexflow's reading against the city's

- **The statute.** "If the response is made within five working days, the public body shall have an additional seven
  work days" (§ 2.2-3704(B)(4), **verified**).
- **The city's reading.** "This will allow us seven additional working days ... giving us a total of 12 working days"
  ([Charlottesville](https://www.charlottesville.gov/770/Our-FOIA-Responsibilities), **verified**).
- **lexflow's reading.** The model's gap note says "the timer ... runs from the B.4 response, which can be shorter than
  seven work days counted from the end of the five-day period" (`curated/va/records.json`).
- **The difference, counted with lexflow's own engine.** Request received Monday 21 December 2026; office closed 24
  and 25 December and 1 January:

  | Reading | Due |
  |---|---|
  | First response, 5 working days | Wednesday 30 December 2026 |
  | Extension letter sent Tuesday 22 December; 7 working days from the letter (lexflow's timer) | **Tuesday 5 January 2027** |
  | 12 working days from receipt (the city's reading) | **Monday 11 January 2027** |

- **Why it matters.** The custodian lane would be safe on lexflow's date, only early. The requester lane would declare
  a deemed denial on 6 January while the city, by its published rule, still has four working days. The requester
  must give the body a copy of a petition three working days before filing (§ 2.2-3713(C)). A requester could start
  that clock while my office is still in time.
- **Fix.** Default the requester lane to the city's reading, the later date, and show lexflow's as the other reading.
  Before arguing either way, have P1 search the Council's
  [advisory opinions](https://foiacouncil.dls.virginia.gov/foiacouncil.htm) and, if they are silent, send the Council
  a general question. Publish the answer and cite it. Whether the opinions already settle this was **not checked**.

### 2.5 Smaller errors a clerk will spot on the first page

- **"Working days" relabelled "business days".** The statute says "five working days" and "seven work days". The
  model stores both as `business_days`, and the live page prints "within 5 business days" in the state steps but
  "5 working days" in the local section (**verified**). The strategy's own blog draft says units matter. For a
  custodian, "working days" means days my office was open, which is why local closures matter.
- **Tolling is missing from the clock.** The response period is tolled while a cost estimate is outstanding. A request
  is deemed withdrawn if the requester does not answer an estimate within 30 days (§ 2.2-3704(F)). It is also tolled
  while a deposit over $200 is pending (§ 2.2-3704(H)) (**verified**). The model lists these as unmodelled "optional
  steps". They are where custodians actually get the date wrong (**judgement**).
- **Police files get 60 work days**, not 7, for criminal investigative files (§ 2.2-3704(B)(4)). The model knows this
  and "the timer shows only the seven-day figure". Any card for a police department would be wrong.
- **Who may request.** Virginia's right belongs to citizens of the Commonwealth and to media circulating or
  broadcasting in Virginia (§ 2.2-3704(A)). The model has it. The blog table does not. The strategy's core heavy user
  for Virginia, the "multi-state journalist", may have no right at all in Virginia. Say so.
- **Unplanned closures.** A snow day closes my office with a few hours' notice, and § 1-210(E) moves a deadline that
  falls on "any day or part of a day" the office is closed
  ([§ 1-210](https://law.lis.virginia.gov/vacode/title1/chapter2/section1-210/), **verified**). A pre-printed card is
  wrong the morning we close. Print the rule for that on the card.
- **When a request is "received".** After-hours email, a request sent to the wrong department, a request caught by the
  spam filter: these are the arguments I actually have (**judgement**). P2's 100 cases should include them.
- **The state's days off are not mine.** By default the engine treats the state executive branch's days off
  (Christmas Eve 2026, half of 25 November) as closures for every Virginia body. A city sets its own holidays. The
  card asks for the office's own schedule, which is right. Make "were you open?" the first question, not a variant.
- **Housekeeping.** The Charlottesville records page lists business-licence sources under "Sources", including a city
  code section that "could not be loaded" (**verified**). Small, but it tells a careful reader nobody proofread it.

### 2.6 The state already publishes the contacts, the letters and the opinions

- **Contacts.** The FOIA Council keeps the statewide FOIA officer list by law (§ 2.2-3704.2(G)), searchable by public
  body ([list](https://foiaform.dls.virginia.gov/Home/Searchforms/0), **verified**). Officers trained by counsel must
  report themselves to the Council (§ 2.2-3704.2(F)). For Virginia records offices, "verified contacts for 3 places"
  undersells what is already public. Use the official list as the source, cite it, and check websites against it.
  Do not mine it for outreach: those officers are designated to receive requests, not research pitches.
- **Plain-English rights pages.** Every Virginia city, county, school board and town over 250 people must link from
  its homepage to a plain-English explanation of rights and procedures, the FOIA officer's contact and its charges
  policy. It must also link to the Council's comment form (§ 2.2-3704.1(A) and (B),
  [text](https://law.lis.virginia.gov/vacode/title2.2/chapter37/section2.2-3704.1/), **verified**). lexflow's
  "after you file" page for a Virginia locality competes with a page the locality is required to publish. It should
  link to that page first.
- **Letters and opinions.** The Council publishes "Forms and Sample Letters" and "Searchable Advisory Opinions"
  ([FOIA Council](https://foiacouncil.dls.virginia.gov/foiacouncil.htm), **verified**). The custodian view's "lawful
  responses" should link to the Council's letters, not draft its own.
- **Trust follows the Council.** The strategy says so ("the source clerks trust most"). Act on it: every clerk-facing
  page should show how its dates match the Council's guidance, and where they differ, say why.

### 2.7 "Free, no purchase" is not free for a government

The strategy says the clock card and custodian view "need no purchase". True, but a city still has costs and steps
(**judgement**, except where linked):

- **Terms.** Our attorney reads the terms of any outside service staff use, even a free one, and often strikes
  indemnity and choice-of-law clauses. A wiki footer and a GitHub repository with no licence are not terms.
- **IT.** Staff may not use unapproved web tools for city business. Many of our desktops wipe browser storage at
  logoff.
- **Records.** Anything staff create while doing city business is a public record, whatever the medium
  ([§ 42.1-77](https://law.lis.virginia.gov/vacode/title42.1/chapter7/section42.1-77/), **verified**). It falls under
  the Library of Virginia's retention schedules (the exact series for request files was not checked).
- **Accessibility.** If I post the card on our website, it is web content under the ADA Title II rule. Charlottesville
  (45,672) must comply by **26 April 2028**, and governments of 50,000 or more by **26 April 2027**
  ([Federal Register API, doc 2026-07663](https://www.federalregister.gov/api/v1/documents/2026-07663.json),
  **verified**). Ship the card as a tagged, accessible PDF from day one.
- **Licence.** Lexipedia's footer licenses content under CC BY-SA 4.0 (**verified**). If I adapt the card into our
  staff manual, share-alike reaches the manual. Release clerk-facing artefacts as CC0 or public domain, so a city can
  reuse them without asking its attorney.
- **Gifts and endorsements.** Some localities' policies bar staff from endorsing products, and some need approval to
  accept free services (**judgement**; varies by locality). A bulletin "with the clerk as lead author" about a named
  tool may not be allowed. A bulletin about method may be.

### 2.8 Browser storage is wrong for a custodian

The local-first lab is the right design for residents. For an office it is wrong on three counts:

- the case is a public record outside the city's systems, with no retention control (§2.7);
- it may hold requesters' names and request subjects, on an origin "which other plugins' scripts can read"
  ([lab-plan.md](../design/lab-plan.md));
- it disappears when IT resets a profile.

**Fix.** The custodian lane should take a date and the office's closures, and nothing else. Or it should be the
printed card. Never invite a clerk to "try it with your last request" (week 6).

### 2.9 For a custodian, the date is the advice

- §1.3 calls deadline arithmetic "the safest side of the advice line". For a requester, perhaps. For my office the due
  date is the thing we rely on, and the law gives us no credit for relying on a website.
- Virginia names what a court may weigh: an Attorney General opinion or a court decision, for fees (§ 2.2-3713(D)).
  For the closed-meeting penalty it also names published FOIA Council opinions (§ 2.2-3714(C)) (**verified**). A
  university wiki is on neither list.
- So the card must say, on its face: "Checked by <named person> on <date> against Va. Code § 2.2-3704 and the FOIA
  Council's guidance. Your city or county attorney decides how your office counts." The draft's disclaimer is close.
  The missing piece is a named human reviewer.

### 2.10 Filing "real requests" to measure agencies is an audit

- P3(b) files up to 5 requests per state "tracked through the lab to closure", and measures "the share answered by
  the statutory date". To the office receiving them, that is a compliance test, however polite and however openly
  named.
- The records it would ask for (request logs, FOIA policies, templates, holiday schedules) are mostly on the website
  already. The Council's sample letters and the § 2.2-3704.1 page cover most of the rest. A phone call gets the
  holiday schedule.
- Clerks talk to each other. A Virginia clerk who learns that the project behind the free card is also timing
  clerks' responses will warn the VMCA list (**judgement**).
- **Fix.** Drop P3(b), or run it only in states and offices the project never asks for help. Keep P3(a), timing from
  published PAC, Attorney General and Council decisions.

### 2.11 "Website health": what is stale is the directory, not the website

- The pilot measured contacts listed in the Census GUS file and Wikidata
  ([entities-contacts.md](../design/entities-contacts.md) §3). "43% of verifiable official websites stale" means 43%
  of those listings were out of date. A league reading the §3.7 offer ("the share of listed websites that no longer
  work") will hear "your members' websites are broken". That is false, and it is an insult.
- The three domains that now serve gambling or spam are a real hazard: residents searching old links land there. The
  right first move is a private note to that government's clerk or IT, with the evidence, before the finding appears
  on Wikidata, in a blog post or in a talk. That is ordinary responsible disclosure.
- A league would take a private list for each member. It would not take a league-wide percentage, and certainly not
  a published one (**judgement**).

---

## 3. What would earn my attention, and keep it

Ranked by how likely I am to use it twice. Each item gives first, asks one small thing, and runs without install,
login or data leaving my office.

### 3.1 A FOIA due-date calendar that is right, and checked by a person I trust

Keep the clock card, but build it for the custodian:

- **Format.** A twelve-month grid on two pages. Each date shows two due dates: the five-working-day date, and the
  extended date for a timely B.4 letter. A 250-row table cannot be one page.
- **Defaults.** Print the earlier date where readings differ, as "meet this". Use the office's own holidays,
  confirmed by the office.
- **On the card:**
  - the § 2.2-3704(B) words and the B.4 extension, with the 12-working-day total as the city's own page states it;
  - the tolling rules for cost estimates and deposits (§ 2.2-3704(F), (H)) and the 30-day deemed withdrawal;
  - the 60-work-day rule for criminal investigative files, on police department cards;
  - one line on unplanned closures (§ 1-210(E));
  - a link to the Council's guidance and sample letters;
  - who checked it, and when.
- **Proof.** P2's audit, plus a sign-off from the office's own attorney before it is printed for staff.
- **Commitment.** Promise the 2028 card in November 2027, from whoever is on the project then. A clerk who adopts a
  card that stops after one year will not adopt the next thing.

### 3.2 A ten-minute check of my vendor portal

If I run GovQA, NextRequest or JustFOIA, give me ten test dates (a holiday week, a B.4 extension, a cost-estimate
pause) and the due dates the law gives. I enter them in my portal's test or sandbox mode and compare. If the portal
is wrong, I call my vendor, as its customer. This is the strategy's §4.4 "go through the customer" made concrete. It
also answers the plugin question with data. Whether these portals model Virginia's B.4 total or the tolling rules
was **not checked**.

### 3.3 A backward calendar for meeting notices and hearing advertisements (a hypothesis to test)

From the clerk's chair, the deadline that keeps me up is not FOIA. It is the advertisement for a public hearing
(**judgement**). It is a clock I own, the stakes are a re-noticed hearing or a challenged ordinance, and it is shared
with planners and municipal attorneys: exactly the three audiences the owner wants. Virginia's rules are statutory
and precise (**verified**):

- **Meeting notice:** "at least three working days prior to the meeting", posted on the website, at a public
  location and at the clerk's office ([§ 2.2-3707(D)](https://law.lis.virginia.gov/vacode/title2.2/chapter37/section2.2-3707/)).
- **Planning and zoning hearings:** two newspaper notices, "the first notice appearing no more than 28 days before and
  the second notice appearing no less than five days before" the meeting. Written notice goes to owners and abutters
  "at least five days before the hearing" ([§ 15.2-2204(A), (B)](https://law.lis.virginia.gov/vacode/title15.2/chapter22/section15.2-2204/)).
- **County ordinances:** advertised twice, the first "no more than 28 days before" and the second "no less than seven
  days before" ([§ 15.2-1427(F)](https://law.lis.virginia.gov/vacode/title15.2/chapter14/section15.2-1427/)).
- **Counting backwards:** "the day of such motion or proceeding shall not be counted ... but the day on which such act
  is performed may be counted" (§ 1-210(A)).

Give me a hearing date and my newspaper's publication days, and the tool gives me the window for each notice, quoted.
The engine already counts working days forward; counting backward is a small extension. This is a better P10 than
land-use review clocks, because the clerk, the planner and the attorney all touch it. Test it in the first
interviews ("the last time an advertising deadline was tight, what happened?") before building it.

### 3.4 A training-records tracker

The clerk of each governing body must keep records of elected officials' FOIA training for five years. New officials
must train within two months of taking office, then every two calendar years (§ 2.2-3704.3(B), (C),
[text](https://law.lis.virginia.gov/vacode/title2.2/chapter37/section2.2-3704.3/), **verified**). FOIA officers must
train every two years (§ 2.2-3704.2(E)). A one-page tracker with the quoted rule, timed for the weeks after an
election, is small and it is the clerk's own duty. It is a good first-semester student project.

### 3.5 A private self-check and a stale-domain alert

Offer each Virginia locality, privately, a one-page check:

- Does the homepage link to the § 2.2-3704.1 rights page and to the Council's comment form?
- Does the FOIA officer on the site match the Council's list?
- Does any old domain listed for the locality (in the Census file or Wikidata) now lead somewhere harmful?

Send it only to that locality. Never publish it as a ranking. A clerk who receives "your old domain serves gambling
ads; here is the evidence" will remember who told them (**judgement**). This is also the honest form of the league
offer in §3.7 of the strategy.

### 3.6 How to deliver it

- **Through people I already trust.** The office's own attorney, then the VMCA, then a Council training session, as
  an attendee who asks a question, never as a presenter.
- **On paper first.** A PDF attachment, not a link to a wiki.
- **With one ask.** "Tell us what's wrong" is right. "Send us your closure schedule" is fine. "Be lead author" is not
  a first ask.

---

## 4. The discovery questions: which are off, and better ones

### 4.1 Questions that would go badly

| Where | Question | The problem | Ask instead |
|---|---|---|---|
| wedge.md §7 (clerks) | "Have you ever missed a deadline? What happened?" | It asks a public official to admit a violation to a public university. "Failure to respond ... shall constitute a violation" (§ 2.2-3704(E)). The interview ends here | "When does a deadline get tight in an office like yours? What do people do then?" (third person, about the work) |
| strategy §2.4 | "Has a requester ever disputed your deadline or gone to the FOIA Council, the Attorney General or a court? What happened?" | It invites talk about live disputes and litigation. The attorney will forbid it | "Which parts of the rules do requesters most often misunderstand?" |
| communities.md §3.6 | "Would you hand a checklist that quotes the Code to a new deputy clerk? What would stop you trusting it?" | A hypothetical, which the Mom Test the strategy cites warns against | "What did you give the last new deputy? Where did it come from? Who checked it?" |
| strategy §2.2 | "Could you show me the spreadsheet / template / checklist you used?" | In Virginia a written ask for records is a request (§ 2.2-3704(B)). A request log holds requesters' names | "Is any of that on your website? Could you describe how it's laid out?" |
| strategy §2.4 | "How did you work out the date the response was due?" | Fine, but most will say "the portal" or "the calendar", and the interview stalls | Follow up at once: "When did the portal's date and yours last differ?" |
| strategy §2.4 | "When the records law last changed, how did you find out?" | Fine. The answer will nearly always be "the Council's training or update", which is useful: it names the channel to support, not replace | Keep it |
| communities.md §6.3 (leagues) | "Would members want to know when their listed website or records page breaks?" | Hypothetical, and the answer is always yes | "When did a member last find out its listing was wrong? How?" |

### 4.2 Questions missing for clerks

- "Who here answers records requests? Is that you?" Ask it first.
- "Which deadlines are yours personally?" (notices, advertisements, minutes, training records, records requests)
- "What took the most staff hours last month?"
- "Which kinds of requests do you dread?" (bulk, machine-written, video, email searches)
- "When the Council's guidance and your attorney's advice differ, what do you do?"
- "Who would have to approve your office using, or printing, an outside resource?"
- "What's the last outside document you printed for staff, and why did you trust it?"

### 4.3 How to run clerk interviews without causing trouble

- **Contact.** Use a warm introduction through the locality's attorney, manager or the VMCA, or the clerk's general
  office line. Never the FOIA intake address or portal (§0, item 5).
- **Permission.** Many clerks will need their manager's or attorney's approval to take part in research about
  compliance (**judgement**). Ask whether they need it, and offer a one-paragraph description they can forward.
- **Public records, both ways.** Every email the team sends to a city is a public record of the city. The university's
  own records may be requestable too, though unpublished research data at a public university has an exemption
  ([§ 2.2-3705.4(A)(4)](https://law.lis.virginia.gov/vacode/title2.2/chapter37/section2.2-3705.4/), **verified**).
  Whether the interview notes fall in it is for the IRB and university counsel. Write every message as if it will be
  published, and tell interviewees how notes are stored.
- **Timing** (**judgement**):
  - avoid council meeting days and the days before, when agenda packets are due;
  - avoid election weeks, where clerks run elections;
  - avoid the weeks before budget adoption;
  - in Virginia, Election Day is a legal holiday (the engine's calendar includes it);
  - Thanksgiving week and the last two weeks of December are empty offices.

---

## 5. The content drafts: how each would land, and fixes

### 5.1 Draft 1, the blog post with the 11-jurisdiction table (§7.4)

**How it lands with a clerk.** As a requester-advocacy piece. It is accurate as far as it goes. The § 2.2-3713(C)
"seven days ... three working days" sentence checks out (**verified**). But it shows only the first deadline. A
requester reading "5 working days" will call my office on day 6, when I sent a B.4 letter on day 4 and still have
seven work days.

**Fixes:**

- Add three columns: **extension or maximum** (Virginia: 12 working days with a timely letter), **what stops the
  clock** (Virginia: cost estimate and deposit), and **who may request** (Virginia: citizens and Virginia media).
- Replace "checked by machine against the published text (open-us-law release v2026.09.1)". open-us-law is a third
  party's compilation, not "the published text". Write "checked word for word against a third-party copy
  (open-us-law v2026.09.1), and linked to the official code".
- Say who reviewed it: "Each model was drafted and reviewed by an AI model, then checked line by line by <named
  person>." The draft says "reviewed adversarially" and keeps the AI part for a footnote about the post. A librarian
  or clerk who finds that out later will discount everything.
- Link the Council's guidance in the Virginia row.

### 5.2 Draft 3, the clerks' newsletter note (§7.6)

**How it lands.** Mostly well: it is free, asks for nothing to install, never sees requests, and names the FOIA
Council and the attorney. Three things would undercut it:

- **The headline talks down.** "Counting the five working days" and "harder than it looks" tell trained FOIA officers
  something they know. Lead with the utility: "A free 2027 FOIA due-date calendar for your office, checked against the
  Code and the FOIA Council's guidance."
- **It omits the cases clerks get wrong.** Add the 12-working-day total, cost-estimate and deposit tolling, and the
  60-day rule for criminal investigative files.
- **It promises "one page" with "every working day of 2027".** Make it a calendar grid (§3.1).

Also: say who checked it (a person, by name and role), and offer to send the card to the office's attorney first.
Whether the VMCA newsletter takes outside pieces was **not checked**; the strategy already flags this.

### 5.3 The calendar weeks that would misfire

| Week | Piece | Problem | Fix |
|---|---|---|---|
| 2 | Private pre-check with "one Virginia clerk" | Good idea; wrong person if the clerk is not the FOIA officer | Ask a town clerk who is the FOIA officer, or the locality's FOIA officer through a warm introduction |
| 5 | Clock-card offer to clerks; ICMA Lightning Talk "only with a practitioner presenter" by 13 November | No practitioner will agree to present a university's tool four weeks after first hearing of it (**judgement**) | Skip ICMA 2027. Aim for ICMA's academic symposium call in spring 2027 ([communities.md](communities.md) §5.2) |
| 6 | Demo: "Try it with your last request (local-first; nothing is uploaded)" | Invites a custodian to put a city record in a browser tab (§2.8) | For clerks: "try it with a date". Nothing else entered |
| 7 | Public thread asking clerks how their office counts the half day on 25 November, posted Thanksgiving week | Clerks don't state legal interpretations in public, and the week is empty. Each office has a factual answer: were you open? | Ask in interviews. Or send the Council a general question and publish its answer, cited |
| 11 | "If a Virginia body received your request on 21 December..." posted 21–27 December | Nobody in a clerk's office reads it that week, and the case is already live | Publish in early December |
| 9 | Corrections to MuckRock or RCFP | Fine, but if the "correction" is lexflow's B.4 reading, it is wrong by the city's published rule | Settle §2.4 first |

### 5.4 The league "website health" offer (§3.7)

As written, it would land as a scolding (§2.11). Rewrite: "A private list for each member: which old addresses in
public directories still point at your locality, and whether any now lead somewhere harmful. Nothing is published."

### 5.5 The IIMC Technical Bulletin "with a clerk as lead author" (§3.3, P4)

IIMC is international, and a Virginia clock is a state topic. Asking a clerk to be lead author of a piece about a tool
reads as asking for an endorsement (§2.7). Offer the VMCA a method note ("how to build a due-date calendar for your
office from the Code"), written by the team, with clerks thanked by name only if they ask.

### 5.6 The CivicPlus Agent experiment (§4.3)

No communications director I know would point the city's resident-facing AI agent at a third-party, user-editable
wiki on a `.xyz` domain whose home page lists a Honduran charter city (**judgement**). The agent's answers carry the
city's name. The city would point it at its own § 2.2-3704.1 page. Run this test only after the front door is fixed,
the pages are locked and reviewed by a person, and the city's own attorney has read them.

---

## 6. Plugins and the service model, seen from the counter

- **I would not install a third-party plugin in my records portal.** The vendor set it up during implementation, and
  changes go through the vendor's support (the strategy's own finding, [landscape.md](landscape.md) §1). If the
  portal's dates are wrong, I want my vendor to fix them, and §3.2's ten-minute check is what makes me call.
- **Cities will not buy "rule packs".** The FOIA Council trains us free, and our attorney advises us. A city would
  not budget $5,600 to $14,400 a year (the strategy's **estimate**) for a state's records rules it can get from the
  Council (**judgement**). The plausible payers are vendors, configuring many customers at once, and legal aid. The
  strategy lists "leagues buying for members"; Virginia's leagues have the Council for free. Drop that line unless an
  interview contradicts it.
- **"Free plugins, with a service behind them" is fine for WordPress sites.** That means libraries, legal aid and
  newsrooms, which the strategy names. It is not how a city's records office gets help.
- **The real government buyer, if one exists, buys training hours or a study, not software.** A locality might pay a
  university for a records-process review under small-purchase rules (the strategy notes § 2.2-4303(G)). That is a
  consulting relationship, years away, and it needs references. It is not a plugin.

---

## 7. The graduate-student programme, seen from the counter

- **Clerk time is the scarce input.** P4 ("one city end to end with its clerk") needs a clerk's time every week for a
  semester. Reverse the burden: the student does the work and brings it to the clerk to check in 20 minutes, three
  times a term.
- **Start with the clerk's own deadlines.** The training tracker (§3.4) and the notice calendar (§3.3) are
  one-semester projects with a clerk as the natural checker. Better bridges into process modelling than another
  records view: the clerk sees a model of their own job, quoted, without ever hearing the word BPMN.
- **P2's 100 cases should be the clerk's hard cases.** After-hours and holiday receipt, wrong-department receipt, a
  B.4 letter on day 1 against day 5, cost-estimate tolling with a reply on day 10, the 30-day deemed withdrawal, a
  deposit, a snow closure, a constitutional officer with different holidays, and police files at 60 days.
- **P1 should start with the Council's advisory opinions**, not only the RCFP guide. They are what Virginia clerks
  are trained from.
- **Student turnover is a trust risk.** A clerk who invests in a project that goes silent in May will not answer the
  next student. The handover rule in §6.3 is right. Add one named person who owns each locality relationship across
  semesters.
- **Drop P3(b)** (§2.10).

---

## 8. What is missing

1. **A single accountable identity and a clean front door** (§1): one organisation, one hosting domain for clerk
   material, a start page without Próspera, LexDAO or smart contracts next to the records work.
2. **A named human reviewer on every page shown to an office,** and removal of "Confidence 1.00" from public pages.
3. **A neutrality statement.** One paragraph: what lexflow does for requesters and for custodians, and what it will
   never do. Never generate or file requests for anyone. Never build features that mass-produce requests. Never time
   or rank offices. In a year of machine-written requests, that sentence matters to clerks.
4. **The official Virginia sources, used and linked:** the FOIA officer list, the Council's sample letters and
   advisory opinions, and each locality's § 2.2-3704.1 page.
5. **A correction and takedown promise for governments.** If a city says its page is wrong or names staff, it is
   fixed or removed within two working days, and the city knows whom to call.
6. **Records and FOIA awareness in the project's own conduct** (§4.3).
7. **The clerk's own statutory clocks** as a candidate nail (§3.3, §3.4).
8. **A custodian-safe lab mode** that takes dates only (§2.8).
9. **Accessible, CC0 clerk artefacts** (§2.7).
10. **A clerk's calendar** for outreach timing (§4.3).
11. **Responsible disclosure** for stale and hijacked domains (§2.11).

---

## 9. What the strategy gets right

Candour cuts both ways, so these should stay:

- "Partly, yes" to the hammer question, and the candid day-90 fallback.
- Interviews about the last time, not the future; no recording without consent; no case facts.
- "Give before you ask", one person and one message, stop when told no, never buy or scrape lists.
- Show only reviewed work outside the team, and say plainly what is not covered.
- Never pitch at a FOIA Council training; listen and check the model against how the Council teaches.
- No vendor approach until there is evidence, and then through a customer.
- Quote the statute word for word and show how each date was counted. A clerk can check a date against a printed
  rule in a minute, and that is what earns trust.
- The engine's own care: it reads the Council's counting rule (AO-02-08, day 1 is the first working day after
  receipt) and shows other readings where the law is open.

---

## 10. Not verified

- The reputation of the `.xyz` domain with government mail filters. The Spamhaus page I tried returned 404, and the
  web-search budget ran out. This stays **judgement**.
- Whether the FOIA Council's advisory opinions already settle the B.4 extension anchor (§2.4). Not searched.
- How GovQA, NextRequest and JustFOIA compute Virginia's B.4 extension and tolling (§3.2).
- The Library of Virginia retention series for request files (the schedule page did not resolve to the series).
- Whether the VMCA newsletter takes outside contributions, and IIMC's rules for Technical Bulletins.
- Every **judgement** in this note: what clerks find painful, how mail filters treat `.xyz`, how leagues would react,
  and local gift and endorsement policies. These are for the interviews to test.

---

## Sources

Opened on 10 October 2026, read-only, with the User-Agent and spacing in the method note.

**Virginia law** (Code of Virginia, official site):

- § 1-210, computation of time: https://law.lis.virginia.gov/vacode/title1/chapter2/section1-210/
- § 2.2-3701, definitions ("public records"): https://law.lis.virginia.gov/vacode/title2.2/chapter37/section2.2-3701/
- § 2.2-3704, the request, the response, the extension, charges and tolling:
  https://law.lis.virginia.gov/vacode/title2.2/chapter37/section2.2-3704/
- § 2.2-3704.1, posting of rights and responsibilities:
  https://law.lis.virginia.gov/vacode/title2.2/chapter37/section2.2-3704.1/
- § 2.2-3704.2, FOIA officers, training and the Council's list:
  https://law.lis.virginia.gov/vacode/title2.2/chapter37/section2.2-3704.2/
- § 2.2-3704.3, training for local officials and the clerk's records:
  https://law.lis.virginia.gov/vacode/title2.2/chapter37/section2.2-3704.3/
- § 2.2-3705.4, exemptions for educational records and research:
  https://law.lis.virginia.gov/vacode/title2.2/chapter37/section2.2-3705.4/
- § 2.2-3707, meeting notices and minutes: https://law.lis.virginia.gov/vacode/title2.2/chapter37/section2.2-3707/
- § 2.2-3713, petitions, hearing within seven days, costs and fees:
  https://law.lis.virginia.gov/vacode/title2.2/chapter37/section2.2-3713/
- § 2.2-3714, civil penalties: https://law.lis.virginia.gov/vacode/title2.2/chapter37/section2.2-3714/
- § 15.2-1427, adoption and advertising of ordinances:
  https://law.lis.virginia.gov/vacode/title15.2/chapter14/section15.2-1427/
- § 15.2-2204, advertising of plans and zoning ordinances:
  https://law.lis.virginia.gov/vacode/title15.2/chapter22/section15.2-2204/
- § 42.1-77, Virginia Public Records Act definitions:
  https://law.lis.virginia.gov/vacode/title42.1/chapter7/section42.1-77/

**Virginia FOIA Council:**

- Training courses, the FOIA officer list requirement: https://foiacouncil.dls.virginia.gov/training.htm
- Council main page (forms and sample letters, searchable advisory opinions):
  https://foiacouncil.dls.virginia.gov/foiacouncil.htm
- FOIA officers listing: https://foiaform.dls.virginia.gov/Home/Searchforms/0
- Advisory opinion AO-02-08 (counting working days): https://foiacouncil.dls.virginia.gov/ops/08/AO_02_08.htm

**Localities:**

- City of Charlottesville, Our FOIA Responsibilities: https://www.charlottesville.gov/770/Our-FOIA-Responsibilities
- City of Charlottesville, Submit a FOIA Request: https://www.charlottesville.gov/774/Submit-a-FOIA-Request

**Federal:**

- DOJ interim final rule extending the ADA Title II web compliance dates, Federal Register document 2026-07663 (read
  through the API because the HTML page served a bot check):
  https://www.federalregister.gov/api/v1/documents/2026-07663.json

**Other:**

- Post-Journal, "Influx of AI FOIL requests requires legislative response" (July 2026):
  https://www.post-journal.com/opinion/in-our-opinion/2026/07/in-our-opinion/
- Wikipedia, "Próspera": https://en.wikipedia.org/wiki/Pr%C3%B3spera
- Lexipedia start page: https://lexipedia.xyz/
- Lexipedia, `lexflow:start`: https://lexipedia.xyz/doku.php?id=lexflow:start
- Lexipedia, `lexflow:va:charlottesville:records`: https://lexipedia.xyz/doku.php?id=lexflow:va:charlottesville:records

**In this repository** (read-only): [adoption-strategy.md](adoption-strategy.md), [wedge.md](wedge.md),
[communities.md](communities.md), [landscape.md](landscape.md), [models.md](models.md), [README.md](../../README.md),
`curated/va/records.json`, `docs/answers/va-charlottesville.md`, `docs/answers/md-baltimore.md`,
`lexflow/lab/deadlines.py`, [lab-plan.md](../design/lab-plan.md), [entities-contacts.md](../design/entities-contacts.md).
