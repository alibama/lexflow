# A Wikimedian's critique of the adoption strategy

_Status: critique, 10 October 2026. It reviews [adoption-strategy.md](adoption-strategy.md) and its research notes
([communities.md](communities.md), [landscape.md](landscape.md), [models.md](models.md), [wedge.md](wedge.md)). It is
written from the chair of a long-time Wikidata and Wikipedia contributor and event organiser. The lens is conflict of
interest, promotional editing, bot and mass-edit norms, and AI-generated content. Research and writing only: nothing
was posted, sent, signed up for or edited, and no wiki was touched. This is the only file written._

_Method. On 10 October 2026 I read pages myself, read-only, with `curl` and the User-Agent
`lexflow-research/0.1 (https://github.com/alibama/lexflow)`, at least 1.5 seconds apart per host. That covered
lexipedia.xyz and lexipedia.wikibase.cloud, Wikidata's API and policy pages, Meta-Wiki, English Wikipedia, the
Foundation's policy site, mediawiki.org (the Wikibase Cloud hosting policy), Commons, Govdirectory's GitHub
repository, the Virginia Code (law.lis.virginia.gov), Wiki Education and dev.to. Policy pages were read as raw
wikitext. The web-search budget ran out partway through, so a few points rest on pages read directly and are marked.
**Judgement** marks my opinion, and **not verified** marks a claim I could not check._

_Credit and privacy. Organisations, projects and published works are named. No person is named, and no editor is
proposed as a partner, advisor or collaborator. Usernames seen on wiki pages are left out._

## Contents

0. [The verdict on one page](#0-the-verdict-on-one-page)
1. [What a Wikimedian sees first: Lexipedia itself](#1-what-a-wikimedian-sees-first-lexipedia-itself)
2. [The Wikidata plan: right, naive, wrong](#2-the-wikidata-plan-right-naive-wrong)
3. [The user-discovery questions for Wikimedians](#3-the-user-discovery-questions-for-wikimedians)
4. [The content drafts, and how they would land](#4-the-content-drafts-and-how-they-would-land)
5. [What would earn my attention and repeat use](#5-what-would-earn-my-attention-and-repeat-use)
6. [Graduate students and the Wikimedia projects](#6-graduate-students-and-the-wikimedia-projects)
7. [What will not work](#7-what-will-not-work)
8. [A revised 12 weeks for the Wikimedia track](#8-a-revised-12-weeks-for-the-wikimedia-track)
9. [Not verified](#9-not-verified)

---

## 0. The verdict on one page

The strategy is far better than most outreach plans that reach Wikimedians. It reads the rules and says "do not"
in the right places: no Wikipedia links, no bot, no items about yourselves, people write their own posts. Keep all of
that. What it misses is mostly not in Wikimedia policy. It is in **what a Wikimedian will see when they click
through**, and in **how the Wikidata contribution is framed**.

1. **The strategy treats Lexipedia as lexflow's 43 reviewed pages. It is not.** lexipedia.xyz is an older, wider
   wiki. Its index lists more than 100 page and namespace names outside `lexflow:`, including wills, divorce, IRB
   questions, a Próspera ZEDE arbitration model, an "AI models" page and many "how do I…" pages. At least one is
   wrong on the law in a way lexflow's own checks would catch (§1.1). The front page also has a red link for
   "Community Guidelines", "smart contracts" language and sponsor logos. Every Wikimedian, librarian and clerk who
   follows a link judges the whole site.
2. **The licence statement the strategy asks the owner to "add" already exists, and it is the wrong one.** The
   DokuWiki footer licenses all content under CC BY-SA 4.0. The lexflow pages say they are generated from
   open-us-law, whose compilation is CC BY-NC 4.0. Nobody needs to add a statement; the owner needs to decide what is
   true for each namespace (§1.2).
3. **The Wikibase's main page describes a project that is not in the instance.** It promises deontic and axiomatic
   ontologies, Akoma Ntoso, an "alignment process" and process mining; the instance holds 1,413 items of a much
   simpler kind. The hosting review requires
   that "the instance's observed use matches the provided information". `Project:Copyrights` and `Project:About`
   are both still missing (§1.3).
4. **"-pedia" plus "encyclopedia" plus "checked by Claude" invites the Grokipedia comparison.** English Wikipedia's
   reliable-sources guideline now names Grokipedia as an example of generally unreliable LLM content. That is the box
   Lexipedia will be put in unless it stops calling itself an encyclopedia and puts named human reviewers on the page
   (§1.4).
5. **The 43% stale-website headline is the wrong number for Wikidata editors.** It is mostly about Census data. It
   counts redirects to the right new site as "stale", and it rests on about 49 websites. Bring a short list, not a
   percentage (§2.2).
6. **Two of the three hijacked domains are still Wikidata's "official website" today.** The City of Auburn ME
   (Q758545) and the Village of Lowellville OH (Q2460456) carry the same domains the pilot found serving spam. Both
   are normal rank, referenced only "imported from Wikimedia project" (P143). Fixing those two by hand, after a
   re-check, is the best first contribution available (§2.3).
7. **The strategy misses the community's own front door.** Govdirectory's Virginia subpage
   (`Wikidata:WikiProject Govdirectory/United States of America/Virginia`) does not exist. Govdirectory also
   displays an agency's "main regulatory text" (P92) only when the law's item has "work available at URL" (P953)
   and "title" (P1476). The Texas, Illinois and California records-act items have neither, and Virginia's and
   Maryland's acts have no item at all. That is lexflow's real strength, statutes tied to agencies with official
   URLs, expressed in Wikidata's own terms (§2.8).
8. **Someone is already modelling Virginia regional bodies on Wikidata.** Items for the Central Virginia
   Transportation Authority (Q140562024) and PlanRVA (Q140562084) were created in 2026, with modelling questions on
   the Govdirectory talk page in August. Look before calling Virginia empty (§2.9).
9. **No QuickStatements in the first months.** A brand-new account pasting machine-prepared batches of edits about
   the bodies its own project models matches the July 2026 block pattern too closely. That operator also "approved"
   each batch. Make the first hundred or so edits by hand in the ordinary interface (§2.6).
10. **The Rapid Fund plan misreads the rules.** The fund excludes projects that "aim to improve third-party
    websites" and projects that include "paid editing". A February 2027 application with paid students, or one that
    touches Lexipedia, would likely be ineligible (§2.11).
11. **The strategy breaks its own rules in public today.** The live `lexflow:start` page says lexflow "answers the
    same questions for every US county, city and town", the breadth pitch §5.5 forbids. The dashboard still has a
    one-click "For the wiki" publish for unreviewed answers. And the 22 published models carry "checked by Claude",
    not the named human sign-off §6.3 requires before anything leaves the team (§1.6).
12. **The biggest "mainstream" lever is missing: English Wikipedia itself, done properly.** There is no article
    titled "Virginia Freedom of Information Act" or "Maryland Public Information Act", and the Texas article is a
    3.7 KB stub. A Wiki Education course assignment can fill those gaps. Students write from secondary sources in
    their own words, without AI (Wiki Education's own rule), and never cite Lexipedia. Thousands will read those
    articles; few will read Lexipedia (§5).

---

## 1. What a Wikimedian sees first: Lexipedia itself

A Wikidata editor who reads a lexflow talk-page post clicks the poster's user page, then the project link, then the
site. A clerk who gets a clock card does much the same. The strategy spends 1,800 lines on venues and almost nothing
on what that click lands on.

### 1.1 Lexipedia is not lexflow's 43 pages

The strategy's §1.7 says "Lexipedia has 43 pages". That is the `lexflow:` namespace. The wiki itself, "Lexipedia -
Process for the people", is older and wider:

- **Who it says it is.** The front page says Lexipedia "is an open-source project building standardized business
  process models". It is "Built by the Center for Civic Innovation with the support of" two sponsor logos (image
  files `sds.png` and `spiffworks.png`). Its audiences are people starting businesses, business-development agencies
  and "legal engineers". It promises that "integration in attestation models and smart contracts" will provide best
  practices for legal review.
- **What else is on it.** The index lists more than 100 non-lexflow page and namespace names. Among them are
  `last_wills`, `divorce`, `reg_cf_exemptions`, `prospera` (a "Próspera ZEDE Arbitration" model with a base64 BPMN
  blob, last changed June 2026), a 2024 `ai-models` page ("Proposed structure for Naptha.ai to build from"), several
  45 CFR 46 IRB questions and dozens of "how do I…" pages.
- **At least one legacy page is wrong on the law.** "How do I challenge a zoning decision in Virginia?" (last changed
  December 2024) says the right to judicial review comes from Va. Code § 15.2-2280 and the 30-day appeal from
  § 15.2-2284. I read both sections on the official site. Neither says anything about appeals, "aggrieved" persons or
  30 days: § 15.2-2280 is "Zoning ordinances generally", and § 15.2-2284 lists the matters to be considered in
  drawing zoning districts. The 30-day rule is in § 15.2-2285(F): an action contesting the governing body's decision
  "shall be filed within 30 days of the decision with the circuit court". Its structure ("Understand Your Rights",
  "Prepare Your Case") reads like unreviewed generated text (**judgement**).
- **The community page is a red link.** "Community Guidelines — how we collaborate (a work in progress)" leads to
  "This topic does not exist yet". Wikimedians judge a wiki by its governance pages before its content.

**Why this matters more than any venue.** The strategy's core promise is "only reviewed work leaves the team". On
this domain, under one brand and one licence banner, sits a page that miscites the Virginia Code. Librarians will
find it in minutes, and attorneys faster. To a Wikimedian, "smart contracts", sponsor logos from a workflow vendor
and a charter-city arbitration model are three different flags. The community voted 232 to 94 in 2022 to ask the
Foundation to stop taking cryptocurrency donations
([Meta RfC](https://meta.wikimedia.org/wiki/Requests_for_comment/Stop_accepting_cryptocurrency_donations)). None of
it is wrong to host, but together it says "not a public-interest reference" before anyone reads a lexflow page.

**Fix (owner).** Choose one:

- **Separate.** Put lexflow's reviewed material on its own host, ideally under the university's domain (see §1.5),
  and keep Lexipedia as the experimental wiki it is.
- **Clean up.** Put a visible "unreviewed draft" banner on every legacy page, move the legal Q&A pages to a
  `drafts:` namespace with `noindex`, fix or delete the zoning page, write the Community Guidelines page, and take
  the "smart contracts" line off the front page.

Do not start Wikimedia outreach until one is done.

### 1.2 The licence footer is already there, and it says CC BY-SA 4.0

Every lexipedia.xyz page ends: "content on this wiki is licensed under the following license: CC Attribution-Share
Alike 4.0 International". The lexflow pages themselves say they were "Generated by lexflow from the state statutes
(open-us-law, government publisher text)". The open-us-law compilation is CC BY-NC 4.0
([models.md](models.md) §5.1), and [credits-research.md](../design/credits-research.md) finding 2 already warns
against presenting it under a more open licence.

The strategy (§0 item 8, §3.2, §5.4) tells the owner to "put licence statements on both Lexipedia sites" as if none
exist. The real task is a decision:

- **Either** rebuild the quoted sections from the official publishers (the 229-section route in §5.2). Then the
  statute words are public domain, lexflow's models are lexflow's own, and BY-SA (or CC0) is true.
- **Or** add a namespace notice on `lexflow:` stating the CC BY-NC origin of the compiled material until that is
  done.

A Wikimedian who sees BY-SA over NC-derived content will assume carelessness about licences. On Wikidata and Commons,
that is the fastest way to lose trust.

### 1.3 The Wikibase main page describes a project that is not there

The Wikibase main page calls Lexipedia "a structured, machine-readable encyclopedia of human law" whose goal is "a
complete reference work". It describes a pipeline in which deontic logic, axiomatic logic and Akoma Ntoso are
"captured as ontologies", then aligned into "a single coherent, aligned legal framework", then turned into Petri nets
for process-mining reports. The README says the instance holds 1,413 items: 55 jurisdictions, 496 section items,
22 processes with 88 roles and 275 steps, 117 court decisions, and 26 items marked "Unreviewed draft".

The hosting policy makes these **required**. I read the staged copy at
[mediawiki.org](https://www.mediawiki.org/wiki/Wikibase/Wikibase.cloud/Hosting_policy); the binding copy at
wikibase.cloud renders only with JavaScript, so check the wording there before submitting.

- "The instance's observed use matches the provided information."
- "The licensing statement is visible on the `Project:Copyrights` page." It is still missing (API check, 10 October;
  `Project:About` is missing too).
- "The structured data is in the public domain or released under CC0."
- "The license for the text in other namespaces allows commercial and non-commercial use and derivatives."

"Misinformation" and "any indication that the dataset … may violate … the Terms of Use (e.g., copyright
violations)" are **disqualifying**.

**What this means:**

- **Rewrite the main page to describe what is there.** State the item counts, the classes, that steps and posts are
  modelled but people are not, that items carry lexflow keys, and that 26 are marked unreviewed. Put ambitions under
  a "planned" heading, or drop them.
- **CC0 is achievable, and the strategy undersells that.** The loader (`lexflow/publish/wikibase_lexipedia.py`) puts
  no statute quotes on the Wikibase. Section items carry a citation, a heading and the official URL; process, step
  and role items are lexflow's own modelling. Those are facts, plus lexflow's own work. To declare CC0 honestly,
  re-check each heading and URL against the official publisher, cite the publisher rather than the compilation, and
  have counsel confirm the CourtListener metadata (models.md §9). This is a much smaller job than the DokuWiki
  question.
- **Argue external audience, not "staging ground".** In the policy, "staging ground for a dataset being prepared for
  later contribution … (for example, to Wikidata)" is an **exception** to one concerning signal: an instance with
  "no clear external audience". It is not a general point in an instance's favour, as communities.md §2.6 and the
  strategy §3.2 say. And the strategy itself says statute and process items will **not** go to Wikidata. A reviewer
  comparing stated with observed use will see that. The honest case is that lexipedia.xyz readers and SPARQL users are
  the external audience, plus whatever positive signals the instance can show (§5).

### 1.4 "-pedia", "encyclopedia" and "checked by Claude": the Grokipedia comparison

The strategy treats the name as a trademark question only. It is a trust question first.

- English Wikipedia's reliable-sources guideline now says: "Content produced by LLMs, such as AI chatbots (eg.
  ChatGPT) and Grokipedia, is generally unreliable"
  ([WP:RSML](https://en.wikipedia.org/wiki/Wikipedia:Reliable_sources#Sources_produced_by_machine_learning)).
- Lexipedia's own pages say the models were "checked by Claude". The Wikibase calls itself an "encyclopedia".
- Many Wikimedians this year see an AI-written "-pedia" as a rival that strips their work. Lexipedia will be
  pattern-matched to that on first sight (**judgement**).

**Fix:**

- **Stop calling it an encyclopedia.** "Encyclopedia" promises an editorial process (sourcing, neutrality, many
  editors) that a one-maintainer wiki with AI-written models does not have. Call it what it is: "statute-quoted
  process models of US public-records and business-formation law, with a wiki front end".
- **Lead with the human, not the model.** Every model page should carry "Reviewed by <name>, <role>, on <date>" and,
  separately, "Drafted and adversarially checked by an AI model (Claude)". Until a person has signed a page, say "AI-
  checked; human review pending". That is also what the strategy's own review ladder requires (§1.6).
- **On the trademark.** The examples the strategy quotes ("a wikipedia for motorcycles", a made-up "-pedia" site)
  are not in the current
  [trademark policy](https://foundation.wikimedia.org/wiki/Policy:Wikimedia_Foundation_Trademark_Policy) text I
  read. The current text asks people not to mimic the "look and feel" of a Wikimedia site. It says plain MediaWiki
  use needs no permission, and it asks people not to register domains similar to Wikimedia marks. "Lexipedia" on
  DokuWiki is not a trademark problem (**judgement**). Keep the "not affiliated with the Wikimedia Foundation" line
  anyway, because readers will assume otherwise.

### 1.5 The domain and the university (judgement)

The strategy leans hard on the university's credibility: IRB, warm introductions, "a research project at
<university>". Then it sends every audience to `lexipedia.xyz`. To a clerk's IT filter, a law librarian and a
Wikimedian, a cheap generic top-level domain, a brand that is not the university's, and logos that are not the
university's all undercut the affiliation the strategy relies on (**judgement**; domain-reputation data was not
checked because the search budget ran out).

A reviewed-models site on a university-controlled host (`lexflow.<dept>.<university>.edu`, or a library-hosted
page) would earn more trust from every audience in the plan than any venue on the calendar. It would also make the
paid-editing disclosure simple: the employer is visibly the publisher.

### 1.6 Where the live site breaks the strategy's own rules

| The strategy's rule | What is live today |
|---|---|
| "Breadth as the pitch ('38,640 governments')" will not work (§5.5) | `lexflow:start`: "lexflow answers the same questions for every US county, city and town" |
| "Show only reviewed work outside the team" (§3.1) | The README's Ask page: "tick **For the wiki** to publish an answer as its own Lexipedia sub-page", with answers "machine-made and marked unreviewed". No answer sub-pages were visible under `lexflow:va` today, but the button exists, and `lexflow:start` announces machine answers |
| "Named human sign-off with a date, before anything leaves the team. Claude … is never the final reviewer of anything published" (§6.3) | All 22 published models say "checked by Claude", with no human reviewer named |
| "lexflow's own code has no licence" (§1.7) | The front page and the model user-page line both say "open-source project" |

**Fix before week 1's method page:**

- reword `lexflow:start` to the 11 reviewed jurisdictions;
- disable or gate the "For the wiki" button behind a named reviewer;
- label the 22 models "AI-checked; human review pending" until P1 signs them;
- do not write "open-source" anywhere, on-wiki or off, until a licence file exists. A Wikimedian will click through
  to GitHub and look for one.

---

## 2. The Wikidata plan: right, naive, wrong

### 2.1 What the strategy gets right

Say this plainly, because it is rarer than it should be:

- personal accounts and disclosure;
- no bot, ever;
- posts, not people, which matches the Living People concerns;
- references on every statement (P854 and P813);
- nothing CC BY-NC on Wikidata, which matches the Mass-editing policy's step 2 ("Data that is not compatible with
  CC0 can not be mass added to Wikidata",
  [policy](https://www.wikidata.org/wiki/Wikidata:Mass-editing_policy));
- no items about yourselves, with the July 2026 block as the cautionary tale.

The operator's own account confirms the strategy's reading. 109 items, every edit referenced and passing
constraints, "executed by an AI agent (Claude Code) in a semi-automated setup, with me approving before any batch",
were mass-deleted in about two and a half minutes, and the account was blocked as "Promotion-only account"
([dev.to](https://dev.to/shimo4228/banned-from-wikidata-overnight-i-believed-every-edit-was-compliant-but-all-109-items-were-57nl)).

The 14 "no item" bodies also hold up. A label and full-text search on 10 October found none of them, and the SDAT
search found only its Business Services unit (Q107179394), as the fixture says. Search is not proof of absence, but
the list is not careless.

### 2.2 The 43% headline is the wrong number for this audience

From [entities-contacts.md](../design/entities-contacts.md) §2.5 and §3.4, my arithmetic:

- **The sample is small.** 55 sampled websites, 6 behind bot walls, so about 49 verifiable. 43% is about 21 sites.
- **"Stale" mixes harmless and harmful.** DNS found 7 dead hosts, title checks found 4 broken sites (3 spam, 1
  default page), and **8 were redirects to the right new domain** (6 to `.gov`). A redirect that lands on the
  official site is an out-of-date value, not a broken one.
- **It is mostly not Wikidata's data.** "Where Census and Wikidata agreed … 27% stale. Where Census stood alone …
  48%." The Census GUS 2022 file is frozen.

Telling Wikidata editors that "43% are stale" therefore attributes a mostly-Census problem to their data. They will
check, see redirects that work, and stop reading. The design note has a finding that **is** about Wikidata, and it
is the one to lead with: "P856 is not fresher: 5 of the 6 moved sites still had the old domain."

**Fix.** Never put a percentage in a Wikidata post. Bring a list:

- "These 2 items list official websites that now serve spam";
- "These 5 list a domain that now redirects to the new `.gov` site";
- "These N list a host that no longer resolves".

Give each with the item, the old value, the new official page and the date checked. Wikidata editors act on lists,
not rates.

### 2.3 Fix the two hijacked domains first, by hand

Checked through the Wikidata API on 10 October:

| Item | P856 on Wikidata today | Rank and reference | The pilot's finding |
|---|---|---|---|
| City of Auburn, Maine (Q758545) | `http://www.auburnmaine.org` | normal; P143 only | the same domain redirected to an unrelated site with a Chinese-language title |
| Village of Lowellville, Ohio (Q2460456) | `http://www.villageoflowellville.com` | normal; P143 only | the same domain shows an Indonesian spam title |
| Androscoggin County, Maine (Q491954) | `http://www.androscoggincounty.com/` | normal; P143 only | the hijacked URL was the **Census** one, `androscoggincountyme.com`, not Wikidata's |

So the "three spam sites" finding applies to Wikidata for **two** items, not three. I did not open the spam domains,
so whether they still serve spam today was **not re-checked**.

These two are the perfect first edits for a new account. They are unambiguous, they protect readers, they are the
opposite of promotion, and they need no permission. Find the current official site from a government source (the
state's municipal directory, the county's own `.gov`). Then:

1. add it with a reference;
2. set it preferred;
3. deprecate the old value with a reason (§2.5).

Then mention it, once, on the talk page **after** doing it.

### 2.4 Mismatch Finder: the right tool for one case only

The strategy makes the Mismatch Finder the main route for stale websites. The tool "stores mismatching data between
Wikidata and external databases, then presents it to editors to review and fix"
([Mismatch Finder](https://www.wikidata.org/wiki/Wikidata:Mismatch_Finder)). That fits **moved** sites, where there
is an old value and a new external value. It fits the others badly:

- **Hijacked sites** are few and harmful now. Queue them, and readers keep landing on gambling pages for months. Fix
  them by hand.
- **Dead hosts** have no external value to offer. A "mismatch" with an empty side asks a volunteer to do the research
  lexflow did not do.
- **A brand-new project with no edit history asking for an allow-list or a Phabricator upload** spends staff and
  volunteer time before showing any of its own (**judgement**). Upload only once the hand-made fixes have been
  accepted and the list is too long to do by hand (Virginia's 322 governments may be).
- **Review throughput is unknown.** I could not check how quickly uploaded mismatches get reviewed (**not
  verified**). Do not plan the contacts layer around someone else's queue.

### 2.5 How to record a stale website on Wikidata

The strategy's draft post says "fix" without saying how. A Wikidatan will want to see that you know the convention.
The design note gets most of it ([entities-contacts.md](../design/entities-contacts.md) §4); the strategy should
carry it into P6 and the post:

- **Never delete the old official website.** Keep it as history.
- **Moved:** add the new P856 with a reference (P854, P813) and **preferred rank**. Deprecate the old value with
  "reason for deprecated rank" (P2241), for example *link rot* (Q1193907), or give it an "end time" (P582) if the
  date is known.
- **Hijacked:** deprecate as above. Wikidata also has *usurped URL* (Q126327443), described as an "access status,
  for use with P6954 (for URLs which no longer point to the intended target)". Ask on the Govdirectory talk page
  which qualifier the project prefers before using it widely.
- **Dissolved bodies:** "dissolved, abolished or demolished date" (P576) and "replaced by" (P1366). Govdirectory asks
  that active and historic agencies can be told apart in a query
  ([CONTRIBUTING.md](https://raw.githubusercontent.com/govdirectory/website/main/CONTRIBUTING.md)).
- **Ranks cannot be set reliably with QuickStatements** (the design note says so), which is one more reason to work
  by hand.

### 2.6 No QuickStatements in the first months

D11 and §3.2 plan batches of 20 or fewer, prepared by lexflow, reviewed and "pasted by the person through
QuickStatements". On paper that is within policy. In an admin's eyes it can look like the July 2026 case:

- a new account;
- edits clustered on the bodies one project needs;
- machine-prepared statements;
- a human who approves batches.

The Mass-editing policy also recommends "gaining significant experience by doing manual edits first", and expects
at least autoconfirmed status before any mass editing.

**Fix:**

- Make the first hundred or so edits by hand in the item interface, typing from the official page you have open. The
  14 new items and the first few dozen website fixes are small enough for that.
- Fix what you find even when lexflow does not need it (a wrong label, a missing P17). That is what editors do, and
  it is what makes an account look like an editor's.
- Use QuickStatements only after a month of normal history, only for batches announced on the talk page, and always
  with an EditGroups tag.

### 2.7 Notability is not the issue for agencies; duplicates and modelling are

The strategy asks students to "check notability first" for each agency. Govdirectory's own guide says "Public
agencies are notable so you don't need to worry about that" (CONTRIBUTING.md). Spend the care where it is needed:

- **Duplicates.** Search by label, by alias and by official domain, and check Wikipedia articles that might already
  have an item under another name.
- **Modelling.** The Texas Board of Criminal Justice governs the Texas Department of Criminal Justice (Q3819598); is
  it a separate item, and how is it linked? The Central Collection Unit sits inside a Maryland department that itself
  has no item (fixture note); create the parent first. The DC Board of Parole was abolished, so it needs P576 and
  P1366 to the US Parole Commission (Q7890865).

Ask Govdirectory about these specific modelling questions; that is a good talk-page post (§4.1).

### 2.8 The missed opening: Govdirectory's Virginia page and "main regulatory text"

Two things in Govdirectory's own materials line up with lexflow's strength better than the freshness check does.

**The Virginia subpage does not exist.** The US page lists every state as a subpage, and
`Wikidata:WikiProject Govdirectory/United States of America/Virginia` is a red link (API check). The published North
Carolina subpage shows the pattern: for each group of agencies, a query, "should be N" with an official reference,
and a tick when complete. That is how a state reaches "published" on govdirectory.org.

A student who builds the Virginia subpage gives the community what it asked for, in its own format:

- Virginia's executive-branch agencies, counted against an official list;
- the 14 missing bodies created by hand;
- the queries;
- the counts.

The strategy's metric "Govdirectory US coverage" exists; this is the mechanism for moving it.

**"Main regulatory text" is the statute-to-agency link, in Wikidata's terms.** Govdirectory shows an agency's main
regulatory text (P92) only when the law's item has "full work available online at" and "title" statements. In
Wikidata today those are P953 ("work available at URL") and P1476 ("title"). Checked 10 October:

| Act | Wikidata item | P953 | P1476 | English Wikipedia |
|---|---|---|---|---|
| Texas Public Information Act | Q7707919 | none | none | a 3,709-byte stub |
| Illinois Freedom of Information Act | Q104876318 | none | none | a 114 KB article |
| California Public Records Act | Q5020891 | none | none | a 25 KB article |
| Virginia Freedom of Information Act | no item found | — | — | no article under that title |
| Maryland Public Information Act | no item found | — | — | no article under that title |

lexflow already holds the official publisher URL for every records act it models. Adding P953, P1476 and "applies to
jurisdiction" (P1001) to the existing act items is factual, CC0-clean and immediately displayed by a reuser.
Creating items for the Virginia and Maryland acts is notable on criterion 2 (an identifiable entity with serious
public references). Linking the oversight bodies to their governing law with P92 follows the pattern the
Govdirectory talk page discussed for municipalities in May and June 2026.

Keep this at the **act** level. Section-level items for 496 sections is where notability fights start, and the
strategy is right to keep those on the Wikibase.

### 2.9 Someone is already working on Virginia

The Govdirectory talk page is active: new threads and replies within a day or two in June and August 2026. In August
an editor asked how to model the Central Virginia Transportation Authority (Q140562024) and its staff support from
PlanRVA (Q140562084). Both items are new in 2026. Govdirectory has also held an extra US office hour (September 2025,
per its events page).

So Virginia is not untouched ground to be "given" to the project. Before creating anything:

- read the recent history of Virginia government items;
- follow the modelling already chosen;
- in the talk-page post, say you have seen the existing work and intend to match it.

Do not contact individual editors found through edit histories (the strategy already forbids that).

### 2.10 Disclosure: name every affiliation, not just the university

The Terms of Use require disclosure of "each and any employer, client, intended beneficiary and affiliation" for
paid contributions ([Terms of Use](https://foundation.wikimedia.org/wiki/Policy:Terms_of_Use)). The strategy's model
user-page line names only the university and lexflow. It should also say:

- that the person maintains Lexipedia (lexipedia.xyz and lexipedia.wikibase.cloud), which uses Wikidata's data;
- any organisation credited as Lexipedia's builder or sponsor, if the person is paid by or works with it;
- for students, whether the work is paid, and by whom. Course credit is commonly treated differently from pay, but I
  could not open the Foundation's paid-contributions FAQ (**not verified**), so disclose either way, as the strategy
  says.

And drop "open-source" from the line until the licence exists (§1.6).

### 2.11 The Rapid Fund: two exclusions the strategy missed

The [Rapid Fund page](https://meta.wikimedia.org/wiki/Grants:Project/Rapid) says applicants are **not eligible** if
"the project you have in mind aims to improve third-party websites" or "the project includes paid editing". It also
asks for "current contribution history and experience on the target Wikimedia project(s)" **and** "organising
experience or training experience".

So:

- anything that improves Lexipedia, its Wikibase or lexflow is out;
- a project in which paid research assistants edit Wikidata is out;
- a fundable project would be a community event, for example a Virginia local-government edit-a-thon run with a
  library or an affiliate, with volunteers editing and no paid editing in scope.

The February 2027 plan in §3.2 and §8.3 should be rewritten on that basis, or dropped. models.md's line that the
fund is "good for the wiki side: … Wikibase tooling" is wrong for the same reason.

### 2.12 Small accuracy problems a Wikimedian will notice

Wikimedians read sources. These would be noticed:

- **WP:COI.** The strategy quotes adding many references to your own work as "a form of spamming". The current
  [WP:COI](https://en.wikipedia.org/wiki/Wikipedia:Conflict_of_interest) text says citing your own work "is allowed
  within reason … and is not excessive". The spamming language, if anywhere, is in the spam guideline (**not
  checked**). Quote the current text.
- **Trademark examples** (§1.4): not found in the current policy text.
- **"Staging ground counts in an instance's favour"** (§1.3): it is an exception to one concerning signal.
- **Govdirectory's AI rule** is quoted correctly, but the full sentence starts "As a general guideline, AI
  contributions that can't be recognized as originating from AI are welcome." The strategy's reading (a person writes
  everything) is the honest one. Do not treat "not recognisable" as the target.
- **The global AI RfC** is still open (no status on 10 October). Many commenters push further than the baseline:
  they want disclosure of all AI use, including translation and copyediting, and one says LLM use on Wikidata
  "absolutely must be disclosed" ([RfC](https://meta.wikimedia.org/wiki/Requests_for_comment/Artificial_intelligence_policy)).
  Plan for that stricter reading.
- **An engineering note.** During this check, Wikidata API reads sent with `maxlag=5` were refused because the
  query service lagged about 6 seconds. The contacts design defers batches on lag, which is correct. During the
  QLever migration (Query Service Days, 17 to 23 October,
  [Wikidata:Events](https://www.wikidata.org/wiki/Wikidata:Events)), expect frequent deferrals.

---

## 3. The user-discovery questions for Wikimedians

**The framing is off before the questions start.** Wikimedians are not lexflow's users. They are the people whose
data lexflow reuses and whose norms it must meet. Interviewing them under an IRB protocol as one of six "audiences"
treats the community as a market. On English Wikipedia, the research-recruitment proposal says researchers should
"describe their research project and recruitment strategy … and obtain consensus … before mass messaging users". It
was never adopted ([WP:Research recruitment](https://en.wikipedia.org/wiki/Wikipedia:Research_recruitment) is marked
failed), but it describes what editors expect.

**Fix.**

- Drop Wikimedians from P7's 30 interviews.
- Learn the norms by reading the talk-page archives, Project chat and the July 2026 case, and by attending Collab
  Hour.
- If a study of Wikimedians is wanted later, describe it on Meta-Wiki first and recruit openly, never through user
  talk pages.

**The questions in §2.11 and wedge.md, one by one:**

| Question as written | Problem | Better |
|---|---|---|
| "What was the last US local-government item you fixed or added? How did you find the source?" | Fine | Keep |
| "How do you find out that an official website has gone stale or been taken over?" | Presumes they look; invites a polite answer | "Is there a report or query you already use for dead official websites? Where?" (Govdirectory presented on monitoring data quality at Data Reuse Days 2025; read those slides first) |
| "When an outside tool gave you suggestions … what made you trust or ignore it?" | Good | Keep |
| "For US agencies, which gap hurts Govdirectory most: missing items, missing websites or stale websites?" | Multiple choice built around what lexflow has | "What is blocking the next US state from being published?" (their own criterion) |
| "When a newcomer project showed up with data, what made it go well or badly?" | Asks volunteers to do your homework | Read the archives instead |
| "How should a domain Wikibase link back to Wikidata so that it counts as a staging ground, not a fork?" | Shows intent to pass a review; wrong audience (Govdirectory is not the review committee) | Ask Wikibase people: "Would a federated query joining Wikidata agencies to the duties a statute puts on them be useful to you?" |
| wedge.md: "What would make a Lexipedia page worth correcting, rather than ignoring?" | A pitch in disguise; Wikimedians will correct Wikidata, not a DokuWiki | Drop it |

**Questions that are missing:**

- "How do you want a hijacked official website recorded: deprecated with which reason, and is *usurped URL* used?"
- "What do you treat as the authoritative list of a state's agencies?"
- "For Virginia, is anyone already working on state agencies or localities? Whose modelling should we follow?"
- "Would a monthly, human-checked worklist of failing P856 values for one state help? On which page, and in what
  form?"
- "What would you not want from us?"

---

## 4. The content drafts, and how they would land

### 4.1 Draft 2, the Wikidata or Govdirectory note (§7.5), would land badly as written

**What goes wrong:**

1. **It is prose, under a rule that says "never paste Claude's prose".** The OWN rule says "Claude supplies only
   checked facts and a list of points". §7.5 then supplies a 200-word "model of the shape" in finished prose. People
   paraphrase lightly, and the result keeps the model's rhythm and hedges ("Separately, …", "Would you rather …,
   or should I …"). Govdirectory blocks recognisable AI text; Wikidata editors read the pattern. Give facts and
   bullets only.
2. **It asks permission for what the project already invites.** "I'd like to create these by hand … Is there a class
   or pattern you'd prefer?" Govdirectory's guide already asks people to "add all public agencies". Asking first
   signals unfamiliarity. On a wiki, "give before you ask" means edit first, then talk.
3. **It carries two asks.** Agencies and websites are two conversations.
4. **Its numbers mislead** (§2.2): "a large share of the ones we could verify no longer work as listed".
5. **Its links go off-wiki.** "Here is the full list: <link>" and "the method is here: <method link>" point to lexflow
   or Lexipedia pages. That is a Lexipedia link by the back door, against the draft's own "do not include" line.
   Wikimedians prefer worklists on-wiki: a user subpage with the list and a query.
6. **"I've checked each entry myself" must be literally true** for all 14 bodies and every URL, on the day of
   posting.

**A facts-only packet (the person writes the post from this, after the edits are made):**

- what I did this week: created N items for Virginia state bodies by hand (list on `User:<name>/Virginia agencies`),
  each referenced to its official page;
- what I fixed: Auburn ME and Lowellville OH official websites (hijacked domains), with old values deprecated and the
  reason given;
- the one question: how should a governing board (for example the Texas Board of Criminal Justice) relate to the
  department it governs, and which qualifier do you prefer for a usurped official website?
- the disclosure: affiliation on the user page; "an AI tool helped assemble the candidate list; I checked each item
  against the official page before editing";
- left out: the 43%, Lexipedia, lexflow's features, any request for links.

### 4.2 Draft 1, the blog post (§7.4): "reviewed adversarially" by whom?

The post says "Each model was then reviewed adversarially, for legal accuracy … and for completeness, and fixed". A
reader assumes people did that. The README and the live pages say the reviews were Claude passes. Librarians and
Wikimedians will find that out, and the post will then read as concealment.

**Fix.** "Each model was checked in two adversarial passes by an AI model (Claude), every quote was matched by
machine against the published text, and <name> checked the table below by hand on <date>." The closing AI-assistance
note is good; keep it. Publish the post off lexipedia.xyz until §1.1 is fixed.

### 4.3 Draft 3, the clerks' note (§7.6)

Outside my lens, and good. One Wikimedian point: if a clerk's office sends its closures, offer to add its official
records page to Wikidata as "contact page URL" (P11266) **only if the clerk wants that**, and only from the office's
own website. A clerk who sees the office correctly listed on Govdirectory has a reason to come back.

### 4.4 The calendar puts Wikidata in week 4, which is too early

Week 2 creates the user page; week 4 posts to the Govdirectory talk page and starts a batch in week 6. That is a
three-week-old account asking a WikiProject for a go-ahead. Better: hand edits from week 2, Collab Hour from week 2,
the first talk-page post in week 6 or 7 reporting what is done (§8).

Take the Wikimedia rows out of the content calendar altogether. A table headed "Channel → audience … Call to action
… How to measure" treats a volunteer community as a marketing channel. If that vocabulary leaks into a grant
application or a talk page, it reads as outreach marketing. Run the Wikimedia track as an editing programme measured
by edits that stick (§8).

### 4.5 Where the OWN, REWRITE and EDIT scheme leaks

- **The EDIT tier** ("Claude drafts; the person edits … with a short note that AI helped draft it") is applied to
  Lexipedia's own pages. That is fine on lexflow's site, but those pages are what Wikimedians click through to. Keep
  the note prominent, and add the named human reviewer.
- **The OWN tier** should list Wikidata **edit summaries**, item **descriptions** and **user pages**, not just talk
  pages. All of these are public text a person writes.
- **Phabricator tickets** are OWN, correctly. A Mismatch Finder upload's "external URL" column should point to the
  official page now in use, never to Lexipedia.

---

## 5. What would earn my attention and repeat use

These are in order of value to the Wikimedia projects, not to lexflow.

1. **A "fix this on Wikidata" link beside every contact Lexipedia shows.** Each contact line on a place page links to
   the Wikidata item and property it came from. That turns Lexipedia's readers into Wikidata editors, the way good
   OpenStreetMap-based apps offer "edit on OSM". It is the one flow that sends Wikidata editors, not takes traffic.
   It costs a template change.
2. **The two hijacked domains fixed, then the Virginia Govdirectory subpage built**, by hand, with counts against an
   official list (§2.3, §2.8). This is the work Govdirectory publicly asks for.
3. **The records-act items enriched.** Add P953, P1476 and P1001 to the existing items; create the Virginia and
   Maryland act items; link the oversight bodies by P92 (§2.8). This is lexflow's statute knowledge in Wikidata's
   own form, displayed by Govdirectory.
4. **A small, human-checked monthly worklist** on a user subpage: "official websites in Virginia that failed two
   checks this month", with the evidence and a SPARQL query. Wikidata editors use database reports and worklists.
   This one is useful only if a person has checked each row and it stays short.
5. **A working federated query.** For each Virginia agency on Wikidata, list the duties and deadlines Lexipedia's
   Wikibase says a statute places on it. That needs the Wikidata mapping on the Wikibase (formatter URL mapped to
   P1630, canonical URI to P1921; [authority-wikibase.md](../design/authority-wikibase.md) §2.6 says neither is on).
   It is the one thing that would make the Wikibase interesting to Wikibase people, and it is a positive signal for
   the hosting review.
6. **An organised event, not a campaign.** A "Virginia local government on Wikidata" edit-a-thon with a public
   library, registered on the [Programs & Events Dashboard](https://outreachdashboard.wmflabs.org/) and listed on
   Wikidata's events page. Admins see an organised event with a dashboard, not a promotional single-purpose account.
   It is also the only Rapid Fund shape that fits (§2.11). Wikimedia DC's events and NARWHAL calls are the place to
   ask how such events are usually run.
7. **English Wikipedia articles on state records laws, through Wiki Education.** Wiki Education's support for
   Wikipedia assignments "is free for instructors and their students" at accredited US and Canadian institutions,
   and "Students will draft their contributions themselves without AI"
   ([Wiki Education](https://wikiedu.org/teach-with-wikipedia/)). The gaps are real: no article titled "Virginia
   Freedom of Information Act" or "Maryland Public Information Act", and the Texas article is a 3.7 KB stub.
   - Rules for this to work: secondary sources (the RCFP guide, FOIA Council publications, law reviews, news), not
     only the statute; students' own words; no Lexipedia or lexflow citations; affiliation on user pages.
   - Editing an article about a public law is not a conflict of interest in itself; citing your own project in it
     would be (**judgement**).
   - This, not Lexipedia, is how process knowledge about records law reaches the general public.
8. **Diagrams on Commons, later and carefully.** A person-drawn timeline of a Virginia records request, from the
   statute, freely licensed, could be proposed on the article's talk page for uninvolved editors to use or not.
   - An LLM-produced model rendered as a diagram raises Commons' AI-media questions (scope, description,
     categorisation; [Commons:AI-generated media](https://commons.wikimedia.org/wiki/Commons:AI-generated_media)).
     A person drawing it from the statute avoids them (**judgement**).
   - Never add it to an article yourself if you made it as part of the project.

---

## 6. Graduate students and the Wikimedia projects

- **P6 (the Wikidata drive), rescoped:**
  - first, the hijacked and redirected websites by hand;
  - then the Virginia Govdirectory subpage with official counts;
  - then the 14 bodies;
  - then the records-act statements;
  - Mismatch Finder or QuickStatements only after a month of hand edits, and only for lists too long to do by hand.
  - Measure: edits not reverted after 30 days, no talk-page warnings, and Virginia "published" on Govdirectory. Do
    not measure edit counts; chasing them is frowned on.
- **P8 (teaching), tied to Wiki Education.** The "reading a statute as a process" module pairs naturally with a
  Wikipedia assignment on a state's records law. Process modelling reaches students through the teaching, and the
  Wikipedia article reaches the public, with no BPMN in either.
- **P7 (user studies).** Leave Wikimedians out (§3). If a later study of Wikimedians is wanted, describe it on
  Meta-Wiki and recruit openly.
- **Every student**:
  - edits under a personal account;
  - writes their own user page with the full disclosure (§2.10);
  - makes ordinary fixes beyond lexflow's needs;
  - writes every on-wiki word themselves.

  Students who leave after a semester leave their edit histories behind. Those histories are the project's
  reputation on Wikidata for years.

---

## 7. What will not work

- **Expecting Wikimedians to edit Lexipedia.** A DokuWiki with a separate account, different syntax and no community
  guidelines will not draw Wikidata or Wikipedia editors. They will fix Wikidata and might reuse the Wikibase through
  federation. Plan for that.
- **Citations to Lexipedia on Wikipedia, not only links.** Beyond the external-links rule (ELNO 12, open wikis without
  "a substantial history of stability and a substantial number of editors",
  [WP:EL](https://en.wikipedia.org/wiki/Wikipedia:External_links)), user-generated sites "are generally unacceptable
  as sources" ([WP:UGC](https://en.wikipedia.org/wiki/Wikipedia:Reliable_sources#User-generated_content)), and LLM
  content is "generally unreliable" (WP:RSML).
- **Claiming "staging ground" in the hosting review** while saying elsewhere that the data will not go to Wikidata.
- **A Mismatch Finder upload or a QuickStatements batch as a new account's first act.**
- **Prose "models" labelled "rewrite this".**
- **A Rapid Fund application for lexflow, Lexipedia or paid student editing.**
- **A Wikidata external-identifier property for Lexipedia or the Wikibase.** It needs a property proposal, and from a
  project with no community use it would read as self-promotion. Link one way, from the Wikibase to Wikidata (the
  design already uses "exact match"), until other editors ask for the reverse.
- **"Gift" language in public.** The strategy is candid internally that the contact work "fixes lexflow's own
  weakest layer". Say that openly on-wiki: "we reuse Wikidata's data and found these errors". Reusers giving back is
  a respected role, and the Mismatch Finder page names it. Calling it a gift sounds like marketing.

---

## 8. A revised 12 weeks for the Wikimedia track

| Weeks | What | Who | Done when |
|---|---|---|---|
| 1–2 | Fix the house: decide the DokuWiki licence per namespace; rewrite the Wikibase main page to match its contents; create `Project:Copyrights` and `Project:About`; reword `lexflow:start`; gate the "For the wiki" button; label models "AI-checked; human review pending"; banner or move the legacy pages; no "open-source" until a licence exists | Owner | All live |
| 2 onward | Attend Govdirectory Collab Hour weekly and listen; read the talk-page archives and the Virginia items' recent history | Owner, P6 students | Notes kept |
| 2–5 | User pages with full disclosure, written personally. Hand edits: the two hijacked websites (after a re-check), then redirected sites, then any small fixes found along the way | P6 students | Edits not reverted |
| 4–6 | Records-act items: P953, P1476 and P1001 on the Texas, Illinois and California items; create the Virginia and Maryland act items, by hand | P6 | Statements live, referenced |
| 6–7 | First talk-page post, written by the person, reporting what was done and asking the one modelling question (§4.1); on-wiki worklist on a user subpage | Owner or P6 lead | A reply; follow the answer |
| 7–10 | Virginia Govdirectory subpage: queries, "should be N" with official references; the 14 bodies created by hand | P6 | Subpage live; counts ticked |
| By week 10 | Wikibase hosting review submitted, arguing external audience; federated-query example on the main page | Owner | Submitted |
| 10–12 | Plan a spring edit-a-thon with a library or affiliate, registered on the Dashboard; decide whether a Rapid Fund application for **that event** makes sense in April 2027 | Owner | Plan written |
| Spring 2027 | Wiki Education course with the records-law assignment, if a course fits | Instructor | Course registered |

Mismatch Finder and QuickStatements come later, only if the Virginia list outgrows hand editing.

---

## 9. Not verified

- **Whether the Auburn and Lowellville domains still serve spam today.** I did not open them, deliberately. Re-check
  by hand before editing.
- **How quickly Mismatch Finder uploads get reviewed.**
- **Whether Govdirectory already checks official websites for liveness.** Its repository shows only test and
  expected-count workflows, but its Data Reuse Days 2025 talk on "How we monitor data quality and changes" was not
  watched.
- **The Foundation's paid-contributions FAQ** (the URL I tried returned 404), so how course credit is treated was
  not checked.
- **Wikidata's autoconfirmed thresholds** (the page read gave none in the text checked).
- **Domain reputation of `.xyz`.** This is judgement only; the search budget ran out.
- **Whether Lexipedia's legacy pages were machine-generated.** This is judgement from their style. The zoning page's
  miscitations were verified against the official Code.
- **Whether Virginia's or Maryland's records acts have Wikipedia articles or Wikidata items under other titles.**
  Exact-title and label searches only.
- **The spam guideline's wording on citing your own work** (WP:REFSPAM) was not read.

---

## Sources

All read on 10 October 2026, read-only.

**Lexipedia (the project's own sites):**

- lexipedia.xyz front page: https://lexipedia.xyz/doku.php?id=start
- lexflow start page: https://lexipedia.xyz/doku.php?id=lexflow:start
- lexflow Virginia page: https://lexipedia.xyz/doku.php?id=lexflow:va
- Zoning Q&A page: https://lexipedia.xyz/doku.php?id=how_do_i_challenge_a_zoning_decision_in_virginia
- Próspera page: https://lexipedia.xyz/doku.php?id=prospera
- AI models page: https://lexipedia.xyz/doku.php?id=ai-models
- Wikibase Main Page, `Project:Copyrights` and `Project:About` (API): https://lexipedia.wikibase.cloud/w/api.php

**Virginia Code:**

- § 15.2-2280: https://law.lis.virginia.gov/vacode/title15.2/chapter22/section15.2-2280/
- § 15.2-2284: https://law.lis.virginia.gov/vacode/title15.2/chapter22/section15.2-2284/
- § 15.2-2285: https://law.lis.virginia.gov/vacode/title15.2/chapter22/section15.2-2285/

**Wikidata:**

- Mass-editing policy: https://www.wikidata.org/wiki/Wikidata:Mass-editing_policy
- Notability: https://www.wikidata.org/wiki/Wikidata:Notability
- Bots: https://www.wikidata.org/wiki/Wikidata:Bots
- Mismatch Finder: https://www.wikidata.org/wiki/Wikidata:Mismatch_Finder
- Autobiography: https://www.wikidata.org/wiki/Wikidata:Autobiography
- Events: https://www.wikidata.org/wiki/Wikidata:Events
- WikiProject Govdirectory: https://www.wikidata.org/wiki/Wikidata:WikiProject_Govdirectory
- Its talk page: https://www.wikidata.org/wiki/Wikidata_talk:WikiProject_Govdirectory
- Its events page: https://www.wikidata.org/wiki/Wikidata:WikiProject_Govdirectory/Events
- Its US page: https://www.wikidata.org/wiki/Wikidata:WikiProject_Govdirectory/United_States_of_America
- Its North Carolina page: https://www.wikidata.org/wiki/Wikidata:WikiProject_Govdirectory/United_States_of_America/North_Carolina
- Data Reuse Days 2025: https://www.wikidata.org/wiki/Event:Data_Reuse_Days_2025
- Items and properties read through the API: Q758545, Q2460456, Q491954, Q7707919, Q104876318, Q5020891,
  Q3819598, Q107179394, Q140562024, Q140562084, Q126327443, Q1193907, P856, P92, P953, P1476, P2241, P6954, P582,
  P11266, P968, P1329

**Govdirectory:**

- CONTRIBUTING.md: https://raw.githubusercontent.com/govdirectory/website/main/CONTRIBUTING.md
- Repository workflows (API): https://api.github.com/repos/govdirectory/website/contents/.github/workflows

**Meta-Wiki and the Foundation:**

- AI policy RfC: https://meta.wikimedia.org/wiki/Requests_for_comment/Artificial_intelligence_policy
- AI policies by project: https://meta.wikimedia.org/wiki/Artificial_intelligence/Policies_by_project
- Rapid Fund: https://meta.wikimedia.org/wiki/Grants:Project/Rapid
- Cryptocurrency RfC (closed 12 April 2022): https://meta.wikimedia.org/wiki/Requests_for_comment/Stop_accepting_cryptocurrency_donations
- Trademark policy: https://foundation.wikimedia.org/wiki/Policy:Wikimedia_Foundation_Trademark_Policy
- Terms of Use: https://foundation.wikimedia.org/wiki/Policy:Terms_of_Use

**Wikibase Cloud:**

- Hosting policy (staged copy; the binding copy is at https://www.wikibase.cloud/hosting-policy, which renders only
  with JavaScript): https://www.mediawiki.org/wiki/Wikibase/Wikibase.cloud/Hosting_policy

**English Wikipedia:**

- LLM guideline: https://en.wikipedia.org/wiki/Wikipedia:Writing_articles_with_large_language_models
- Reliable sources (UGC and machine learning): https://en.wikipedia.org/wiki/Wikipedia:Reliable_sources
- Conflict of interest: https://en.wikipedia.org/wiki/Wikipedia:Conflict_of_interest
- External links: https://en.wikipedia.org/wiki/Wikipedia:External_links
- Research recruitment (failed proposal): https://en.wikipedia.org/wiki/Wikipedia:Research_recruitment
- Article checks (API): Texas Public Information Act, Illinois Freedom of Information Act, California Public Records
  Act, Virginia Freedom of Information Act, Maryland Public Information Act
- Próspera: https://en.wikipedia.org/wiki/Próspera

**Commons:**

- AI-generated media: https://commons.wikimedia.org/wiki/Commons:AI-generated_media

**Other:**

- The operator's account of the July 2026 block:
  https://dev.to/shimo4228/banned-from-wikidata-overnight-i-believed-every-edit-was-compliant-but-all-109-items-were-57nl
- Wiki Education, teaching with Wikipedia: https://wikiedu.org/teach-with-wikipedia/
- Programs & Events Dashboard: https://outreachdashboard.wmflabs.org/

**In this repository** (read-only): [adoption-strategy.md](adoption-strategy.md), [communities.md](communities.md),
[landscape.md](landscape.md), [models.md](models.md), [wedge.md](wedge.md), [README.md](../../README.md),
[entities-contacts.md](../design/entities-contacts.md), [authority-wikibase.md](../design/authority-wikibase.md),
[credits-research.md](../design/credits-research.md), `lexflow/publish/wikibase_lexipedia.py`,
`fixtures/entities/agencies.json`, `fixtures/entities/contacts_pilot.json`.
