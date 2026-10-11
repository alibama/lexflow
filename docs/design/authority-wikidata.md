# Authority, positions and escalation: what Wikidata and Govdirectory model, and a design for lexflow

Status: design and read-only research, 2026-10-10. Nothing was written to lexipedia.wikibase.cloud, Wikidata, the
DokuWiki or Govdirectory, and no code, fixture or curated file was changed. Every number below comes from a live read
on 2026-10-10; the method is in section 10.

The question this answers: should Lexipedia's Wikibase hold "all of the Govdirectory entities", so that process
models can be cross-referenced against people and organisational units, and so that lexflow can find the mechanisms
that escalate or defer a process according to who has authority?

| Input | What it gave |
|---|---|
| Wikidata property pages (entity data), the bot-maintained usage templates, WDQS | IDs, live labels, constraints and use counts of 50 organisation, position and authority properties (section 2) |
| The Govdirectory website repository (`queries/`, `templates/org.html`, `views.yaml`), two live organisation pages, the WikiProject data model and Entity Schema E330 | What Govdirectory reads and shows (section 3) |
| `fixtures/entities/agencies.json` | The 144 bodies named in models, answers and statutes; 70 of them have an exact Wikidata item (section 4) |
| `curated/<state>/records.json` (10 models), `curated/*/business.json`, `curated_ask/license_conviction/*.json` | The escalation and deferral steps the reviewed models already contain (section 6) |
| [entities-contacts.md](entities-contacts.md), [entities-sources.md](entities-sources.md), [terms-wikibase.md](terms-wikibase.md), [links-codebase-map.md](links-codebase-map.md), [bpc-480-decision.md](bpc-480-decision.md) | The keys, tables and Wikibase plans this design extends rather than replaces |
| `lexflow/law/xref.py` (`ROLES`, `role_of`), `fixtures/xref/gold_*.json` | Statute-to-statute references with the roles `authority`, `procedure` and `prerequisite_process` |

Scope and privacy rules followed throughout:

* People appear only as holders of public offices, and only as **counts** of Wikidata statements. This note names
  no office-holder, reproduces no contact detail of any person, and models posts, never persons.
* No private individual is looked up. Registered agents, requesters and similar roles stay `lexflow:private-party`
  ([entities-contacts.md](entities-contacts.md) D5).
* No researcher or group is named as a partner, adviser or endorser. Nothing here assumes what the Govdirectory group
  will decide.

---

## 0. The answer in short

| Question | Answer |
|---|---|
| Load all Govdirectory entities into the Wikibase? | **No.** Govdirectory publishes 1,140 US entries: 374 federal (mostly embassies and consulates), 159 for New York and 607 for North Carolina. It has **nothing for VA, DC, MD, TX, CA, FL, IL or WA**, eight of the ten corpus jurisdictions. It holds no data of its own: every value is a Wikidata statement. Its model shows a parent (only when the parent is on the same list) and a "Led by" person name. It has no organisational units below the listed agencies, no posts, no supervision, no appeal and no delegation (section 3). |
| Update the Wikibase at all? | **Yes, but targeted.** Add items for (a) the bodies the reviewed processes name (the ~200 agencies, courts and office types already planned in [entities-contacts.md](entities-contacts.md) 1.2), (b) their parent chain up to the state government (about 20 more), (c) the **posts** that processes escalate to (heads of agencies, the Mayor, the State CIO; about 40 plus about 25 generic post types), and (d) about 20 review and oversight bodies that the statutes create. That is about 320 items. They need 7 new properties, 5 qualifiers and 4 classes (7.7). These are wiki writes, so they wait for your go-ahead. |
| Can the rest come from Wikidata without copying it? | **Yes, live.** Every lexflow item carries `P8 exact match` to its Wikidata item. A federated query from Lexipedia's own query service to WDQS ran on 2026-10-10 (7.7): parents, head positions and other units can be read at query time, so they never need mirroring. |
| Can Wikidata say whom to escalate to? | **No.** It records structure, and only partly: 21 of the 52 state and DC bodies outside the courts in the fixture have a parent, and 8 a head post. It does not record authority. `P12452 appeals to` is used on **no** state agency and no state trial or intermediate court in the ten jurisdictions. `P797 authority` is set on 1 fixture body, and its use elsewhere is inconsistent. There is **no** property for supervision by a body, delegation, ombudsman or FOI review (2.4). The escalation graph has to come from the statutes the models already quote, with Wikidata giving identity and structure. |
| Cross-reference against people? | **Against posts, not people.** A process escalates to "the head of the agency", "the Mayor" or "the Public Access Counselor", which are posts. Holder data in Wikidata is also unreliable: the Secretary of State of California has 6 holder statements with no end date, and the President of the United States has 18 (4.4). No person goes into the DB or the Wikibase (D1). |

---

## 1. Key decisions

| # | Decision | Why |
|---|---|---|
| D1 | **Model posts, never people.** A post is `lexflow:position:<scope>:<slug>` (Mayor of the District of Columbia ↔ wd:Q5190572). A generic post that is resolved per body is `lexflow:position-type:<st>:<slug>` ("head, chief executive or governing body (or designee)", N.Y. Pub. Off. Law § 89(4)(a)). There are no holder columns and no `P39`/`P1308` statements, in the DB or in the Wikibase. | The privacy rule. Escalation goes to the office, not to whoever holds it. Holder data is unreliable (4.4). |
| D2 | **Authority edges are statute-grounded lexflow data.** Wikidata is the identity and structure crosswalk only. | Wikidata has no authority vocabulary in use for US state bodies (2.4). |
| D3 | **Two layers of edges.** *Structural* edges form the organisation chart: part-of, headed-by, has-deputy, reports-to, supervised-by, oversight-by, successor-of. *Procedural* edges are escalates-to, defers-to, forwards-to, requires-approval-of, delegates-to and notifies. Procedural edges are scoped to a question (and, optionally, a decision or step), and each carries its statute, mechanism, deadline and whether it binds. | A body's place in the chart does not create a right of review. The statute does. |
| D4 | **Only statute-grounded rungs are presented as remedies.** A structural fallback (the head of the body, then its parent's head) is labelled "chain of authority, not a legal right of review". | It avoids telling a user that a complaint to a cabinet secretary is an appeal. |
| D5 | **Do not mirror Govdirectory or Wikidata wholesale.** Reuse Govdirectory's query patterns and its link rule ([entities-contacts.md](entities-contacts.md) 1.6). Read Wikidata live through `P8`. | 8 of 10 jurisdictions are absent from Govdirectory. A mirror goes stale, and Govdirectory adds no data. |
| D6 | **Extend the planned tables; build no parallel ones.** Agencies, office types and `entity_links` come from [entities-contacts.md](entities-contacts.md) 1.3. This design adds one table (`positions`) and new relation names in `entity_links`. | One key spelling (that plan's D2). Reviewer decisions survive re-runs (`upsert(keep=…)`). |
| D7 | **Edges are derived, then reviewed.** Escalation edges are proposed from the reviewed models' steps and the xref roles, and accepted by a person. Edges from `single` models stay `proposed`. | The publishing rule in memory. |
| D8 | **Upstream fixes stay human.** Gaps found in Wikidata (4.6) become drafts in the `upstream_suggestions` flow ([entities-contacts.md](entities-contacts.md) 4), which a person reviews and applies under their own account. Nothing is filed with Govdirectory in lexflow-written words. | Wikidata bot policy, and Govdirectory's rule against AI-generated contributions. |

---

## 2. How Wikidata models organisations, units, posts and authority (verified 2026-10-10)

### 2.1 The properties

The property pages were read through the entity data API. The labels below are the live English labels, and several
have changed from the names in common use: P355 is no longer "subsidiary", P1308 is no longer "officeholder", and
P2388's label now says "position held by head of the organization". Counts come from the bot-maintained templates
*Number of main statements / qualifiers by property*, last updated 2026-10-05.

**Structure**

| ID | Label (live) | Links | Constraints that matter | Main statements | As qualifier |
|---|---|---|---|---|---|
| P749 | parent organization or unit | org or unit → its parent | subject and value: organization, organization unit, governing body, independent agency of the US government…; inverse of P355; "contemporary" | 205,787 | 7,440 |
| P355 | child organization or unit | parent → child | inverse constraint → P749. Its description sends non-independent sub-units to P199 | 119,934 | 226 |
| P199 | organizational division | org → division that is not a separate legal entity | subject: company, business, educational institution, organization | 3,444 | 339 |
| P361 | part of | anything → whole | conflicts with "instance of human"; generic | 5,471,205 | 114,293 |
| P527 | has part(s) | whole → part | inverse of P361 | 2,810,297 | 57,643 |

**Heads and posts**

| ID | Label (live) | Links | Constraints that matter | Main | Qualifier |
|---|---|---|---|---|---|
| P2388 | position held by head of the organization | org → post | value: position, board of directors, board of trustees; inverse → P2389 | 79,236 | 83 |
| P2389 | organization directed by the office or position | post → org | subject: position; conflicts with human. Mostly used as a qualifier on P39 | 43,956 | 63,228 |
| P1308 | position holder | post → person | value: human; inverse of P39; qualifiers P580, P582, P1365, P1366… | 32,780 | 727 |
| P39 | position held | person → post | subject: human; qualifiers P580, P582, P1365, P1366, P748, P2715 | 1,999,599 | 119,287 |
| P1037 | director / manager | org → person | value: human | 27,790 | 102 |
| P488 | chairperson | org → person | value: human, organisation or "position not filled"; requires a P580 qualifier | 50,801 | 273 |
| P2098 | substitute/deputy/replacement of office/officeholder | post → deputy post | subject: position | 2,246 | 165 |
| P10645 | reports to | post → post | subject and value: position (created 2022-04-16) | 9,975 | 4 |
| P748 | appointed by | person or post → who appoints | mostly a qualifier on P39 | 6,801 | 6,837 |
| P1313 | office held by the head of government | territory or government → post | single best value | 68,566 | 24 |
| P5052 | **supervisory board member** | org → **human** | value: human | 1,264 | 20 |
| P3320 | board member | org → human or organisation | | 9,765 | 29 |
| P7604 | supervised by | **natural person → natural person** | | 1,034 | 863 |

**P5052 is not "supervisory body".** It lists the people on a supervisory board. No Wikidata property means "this
body is supervised by that body": searches of the property namespace by label and full text found none.

**Jurisdiction, place and government roots**

| ID | Label | Main | Qualifier | Note |
|---|---|---|---|---|
| P1001 | applies to jurisdiction | 1,211,273 | 1,857,059 | institution, law or office → the territory it has power over |
| P131 | located in the administrative territorial entity | 15,301,397 | 319,865 | the Govdirectory data model says it may not apply to state-level agencies |
| P17 | country | 20,995,336 | 153,981 | |
| P2541 | operating area | 54,933 | 3,299 | "area … an organisation … has responsibility for" |
| P208 | executive body | 1,877 | 74 | territory → its executive branch item; single best value |
| P194 | legislative body | 7,113 | 36,136 | |
| P209 | highest judicial authority | 810 | 4 | territory → court; single value |

**Authority, oversight, appeal, legal basis**

| ID | Label | Main | Qualifier | How it is defined and used |
|---|---|---|---|---|
| P797 | authority | 74,305 | 2,544 | "entity having executive power on given entity". It has **no subject or value type constraints**, and its use is inconsistent (2.4) |
| P3719 | regulated by | 1,646 | 10 | activity or market → regulator |
| P12452 | appeals to | 3,242 | 3 | "court or other body that hears appeals from subject's decisions"; subject type: governing body; single best value; created 2024-02-15 |
| P92 | main regulatory text | 17,369 | 509 | org → its governing statute; Govdirectory shows it |
| P457 | foundational text | 52,663 | 52 | org → the act that created it |
| P3014 | laws applied | 419 | 167 | decision or case → statute |
| P101 | field of work | 1,600,813 | 47,974 | Govdirectory uses it to select interstate licensing compacts |

**Lifecycle and roles**

| ID | Label | Main | Qualifier |
|---|---|---|---|
| P571 / P576 | inception / dissolved, abolished or demolished | 4,203,546 / 384,387 | 8,345 / 1,778 |
| P1366 / P1365 | replaced by / replaces | 133,971 / 130,141 | 315,156 / 360,576 |
| P7888 | merged into (requires P576) | 9,637 | 299 |
| P580 / P582 | start time / end time | 958,503 / 835,250 | **12,771,719 / 6,673,816** |
| P2868 / P3831 | subject has role / object of statement has role | 286,199 / 74 | 997,208 / 4,836,065 |
| P5008 | on focus list of Wikimedia project (Govdirectory's marker is Q108109790) | 1,451,920 | 15 |

### 2.2 The pattern for heads and posts

```
organisation ──P2388──▶ post ◀──P39 {P580, P582, P1365/P1366, P748}── person      (persons: not used by lexflow)
     ▲                   │  └──P2098──▶ deputy post        post ──P10645──▶ superior post
     └──────P2389────────┘                                 post ──P1001──▶ jurisdiction
state ──P1313──▶ governor (post)    state ──P208──▶ executive body ("State of Florida")    state ──P209──▶ highest court
organisation ──P749──▶ parent organisation ──P749──▶ … ──▶ state government item
```

What the ten jurisdictions record (state items read live):

| | Executive body (P208) | Head of government (P1313) | Highest court (P209) |
|---|---|---|---|
| VA | Commonwealth of Virginia Q5589334 | Governor of Virginia Q878942 | Supreme Court of Virginia Q2398783 |
| DC | government of the District of Columbia Q16152667 | Mayor of the District of Columbia Q5190572 | District of Columbia Court of Appeals Q5283409 |
| MD | State of Maryland Q5589245 | Governor of Maryland Q693032 | Supreme Court of Maryland Q6781295 |
| TX | State of Texas Q3112637 | Governor of Texas Q5589725 | Supreme Court of Texas Q3694683 **and** Court of Criminal Appeals Q3694688 |
| CA | **missing**; State of California Q5589189 exists and has 31 children (by P749, P361 or P355) | Governor of California Q887010 | Supreme Court of California Q2629503 |
| FL | State of Florida Q3112589 | Governor of Florida Q20198851 | Supreme Court of Florida Q3001105 |
| NY | **missing**; State of New York Q5589272 exists | Governor of New York Q2347975 | New York Court of Appeals Q11991268 |
| IL | **missing**; State of Illinois Q3112583 exists (it is the P797 value of Illinois) | Governor of Illinois Q3112719 | Illinois Supreme Court Q3001109 |
| WA | State of Washington Q16152657 | Governor of Washington Q19647220 | Washington Supreme Court Q4167888 |
| NC | **North Carolina Council of State Q7054461**, a collegial body; State of North Carolina Q7225184 exists | Governor of North Carolina Q16202700 | North Carolina Supreme Court Q7054626 |

So every jurisdiction has a government-root item that lexflow can key to (`lexflow:agency:<st>:government`), but
three state items (CA, NY, IL) do not point to it, and North Carolina's P208 points at the wrong kind of body.

### 2.3 Units

Wikidata has three ways to say "unit of": P749 (with P355 as its inverse), P199 for non-independent divisions, and
P361. The fixture's units use all three. The Florida Division of Corporations has both P749 and P361 to the
Department of State. The California Business Entities Section has P361 to the **post** Secretary of State of
California (Q7024182), not to the office as an organisation. P199 has only 3,444 uses in all of Wikidata. lexflow
should read P749 first, then P361, and accept P199 and P355 as inverse evidence.

### 2.4 Authority, appeal, supervision and delegation: what exists and how it is used

* **P12452 appeals to.** In all of Wikidata, the commonest targets are German regional courts and the Supreme
  People's Court of China. There are 107 statements with a US subject. In the ten jurisdictions only 4 subjects use
  it: the New York Court of Appeals (→ the US Supreme Court) and three federal courts. No state agency and no state
  trial or intermediate court uses it. The property would fit the court ladder and plain agency appeals, but
  nothing populates it.
* **P797 authority.** In the ten jurisdictions it is set on 16 organisations with P1001 there, and the targets mix
  four meanings:
  * the supervising post: Maryland Department of Labor and seven other Maryland bodies → Governor of Maryland; DC
    Public Schools → Mayor; Washington State Guard → Governor of Washington;
  * a legislature: Florida Highway Patrol → Florida Legislature; California Highway Patrol → California State
    Legislature;
  * an unrelated agency: New York State Police → New York State Education Department;
  * Congress: government of the District of Columbia → United States Congress.

  It is a lead, never a fact.
* **P10645 reports to** (post → post) is the only clean "line of authority" property. Of 174 items typed as a
  position or public office with P1001 in the ten jurisdictions, **0** use it. 42 have P2389, 49 have P1308, 8 have
  P748 and 3 have P2098.
* **P2388 is sometimes the supervisor.** The Virginia Department of Taxation's P2388 is the Virginia Secretary of
  Finance (Q28230928), the cabinet secretary above the department, not its own head (the Tax Commissioner). A
  supervision property would have carried that statement; P2388 cannot be trusted without review.
* **No property** exists for: supervision by a body; delegation ("or designee", "may delegate"); referral or
  forwarding; ombudsman, inspector-general or FOI-review jurisdiction; whether a review is advisory or binding;
  exhaustion; or the time limit for an appeal. The nearest general tools are qualifiers (`P2868`, `P3831`,
  `P580`/`P582`) on generic properties.

### 2.5 Consequence for lexflow

Wikidata can supply: the identity of bodies and posts; a partial parent chain; government roots; head posts for a
minority of bodies; and lifecycle (inception, dissolution, replacement). It cannot supply who reviews whom, under
which statute, how fast, or whether the review binds. That has to come from the law the models quote (sections 6
and 7).

---

## 3. Govdirectory's model

### 3.1 What it reads and shows

Govdirectory is a static site. For each country or sub-national part, a *generator* SPARQL query selects
organisations by `wdt:P31` against an explicit list of classes, with no subclass walk. It drops P576 and P1366 items,
and the US generator also drops P3999 items and positions (`MINUS { ?org wdt:P31 wd:Q4164871 }`). One page per
organisation is then rendered from `queries/organization-optional.rq` and `templates/org.html`.

| What the org page shows | Wikidata source (from the query) | Notes |
|---|---|---|
| Official website, email, contact page, FOI request URL, citizens' initiative URL | P856, P968, P11266, P10214, P9732 | truthy `wdt:`, `SAMPLE` |
| Phone | P1329 | only when the statement has a reference |
| Main regulatory text | P92, shown only when the text item has P953 (full work URL) and P1476 (title) | the only link from a body to law |
| **Parent organization** | P749 | shown **only when the parent is itself on the same country list** (the template loops over the generator's results) |
| **Led by** | a **person's name**: the current holder of the P2388 or P1313 post (a P39 statement with no P582; the holder is human and has no P570; the post is not "mayor", Q30185), or a direct P488, P169, P1037 or P3975 value | the post itself is never shown |
| English Wikipedia link, social accounts | sitelink; `account-data.rq` | |

**The organisation page never reads:** P355, P199, P361, P527, P797, P12452, P10645, P2098, P2389, P571, P1001 or
P2541, or any qualifier on the head path except P582. The generators use P361 and P1001 only to select North
Carolina's legislative houses, appellate courts and county election boards.

The WikiProject's data model page and Entity Schema E330 ask for P31, P17, P1001, P131, P749, P92, P101, P571 and
COFOG P9798, and allow at most one each of P355, P2388, P1313 and P488. They say nothing about supervision, appeal or
delegation. The data model's own guidance for drawing the line between a unit and an organisation is whether the
public understands the entity as something it can contact.

### 3.2 Units, heads and posts on Govdirectory (measured)

* **A unit is a flat row.** It is listed only if its P31 is one of the listed classes. It then appears at the same
  level as its department, with its class as the "Type" column, and with a "Parent organization" link only when the
  parent is listed too.
  * NC: the State Highway Patrol (P749 Department of Public Safety) and the State Archives (P749 Department of
    Natural and Cultural Resources) are rows with parent links.
  * NY: the Division of Consumer Protection (P31 "state agency of New York", P749 Department of State) is listed
    with its parent. The Division of Corporations (Q125449570; P31 registration authority and government agency) is
    **not listed at all**.
* **Parent links.** Of the 97 NY state agencies, 16 have a P749 and **10** have a parent that is also listed. Of the
  400 NC agencies, 14 have a P749 and **13** have a listed parent.
* **"Led by."** In NY, 10 agencies resolve a head through the post path, and 3 through direct person properties. In
  NC, 4 of 400 resolve one. The live pages of the NY Department of State and the NC Department of the Secretary of
  State both show "Led by: [missing data]". The NY department's post (Secretary of State of New York, Q16148056)
  has 9 holder statements, none of them open-ended.
* **Posts** never appear as entries. The US generator explicitly removes them.

### 3.3 What this means

Govdirectory is a contact directory built on Wikidata. It is not a model of authority. Loading its entries into
Lexipedia would add about a thousand NY, NC and federal bodies that no lexflow process names, and none for the
other eight jurisdictions. It would add no parent, post or review edge that Wikidata does not already hold. Its
lasting value to lexflow is its curated class lists, its query patterns (the "referenced phone only" rule, the
dissolved-item filters) and its pages as user-facing links for NY, NC and federal bodies.

---

## 4. Coverage for the bodies lexflow's processes name

### 4.1 Totals

The fixture's 70 exact matches are 69 specific bodies plus the New York Supreme Court as a generic court. Their item
kinds are 55 organisations, 6 courts, 5 position items and 4 untyped. Parents were walked breadth-first over P749
and P361 until a state item or the United States. Statements with an end time or deprecated rank were not counted
as current.

| Measure | All 70 | 52 state or DC bodies outside the courts | 8 courts and court councils | 4 federal bodies |
|---|---|---|---|---|
| Any parent (P749 or P361) | 23 | **21** | 0 | 2 |
| Parent chain reaches the state (or DC) government item | 20 | **20** | 0 | n/a |
| Parent chain reaches the federal government | 2 | n/a | n/a | 2 |
| Head post known (P2388, an inverse P2389, or the item is itself a post) | 14 | **8** | 0 | 1 |
| That post has ≥1 open-ended holder statement (4.4) | 10 | 6 | 0 | 1 |
| Supervisory body (no such property; P5052 is people) | 0 | 0 | 0 | 0 |
| P797 authority | 1 | 1 (Maryland Department of Labor → Governor of Maryland) | 0 | 0 |
| P12452 appeals to · P3719 regulated by | 0 · 0 | 0 · 0 | 0 · 0 | 0 · 0 |
| P92 main regulatory text · P457 foundational text | 1 · 1 | | | |
| P1001 jurisdiction | 49 | 39 | | |
| P571 inception · P576/P1366 ended | 37 · 0 | 26 · 0 | | |
| Units listed downward (P355 · P527 · P199) | 6 · 3 · 1 | | | |
| Direct person-valued head (P488, P1037) | 2 | | | |

The 8 court bodies are the 6 courts, the Judicial Council of California and the Ohio Court of Claims. North
Carolina's AOC and Dispute Resolution Commission are counted with the 52. The 4 federal bodies are the Bureau of
Prisons, the US Parole Commission, CSOSA and the DC Pretrial Services Agency. The remaining 6 of the 70 are the 5
position items and the Council of the District of Columbia.

### 4.2 By jurisdiction (exact entries: any parent / reaches government / head post / open-ended holder)

| ca | dc | fl | il | md | nc | ny | oh | tx | va | wa |
|---|---|---|---|---|---|---|---|---|---|---|
| 15: 8/8/1/1 | 15: 4/2/4/3 | 3: 1/0/0/0 | 2: 0/0/1/0 | 9: 3/3/1/1 | 4: 0/0/0/0 | 3: 2/2/1/0 | 3: 1/1/2/2 | 8: 0/0/2/2 | 6: 4/4/1/0 | 2: 0/0/1/1 |

* **Texas and North Carolina have no parent link on any fixture body.** In Texas that covers DPS, TDCJ, TWC, the
  Board of Pardons and Paroles, the Jail Standards commission and SOAH. In North Carolina it covers the Secretary of
  State, the CIO office, the Dispute Resolution Commission and AOC.
* California is the best covered, because its super-agencies (CalSTA, Government Operations, Business and Consumer
  Services) are modelled.

### 4.3 Example chains (live)

| # | Body (fixture) | Chain in Wikidata | Gap |
|---|---|---|---|
| 1 | Florida Division of Corporations Q107179384 | → (P749 and P361) Florida Department of State Q11969252 → **ends** | The Department has no P749. State of Florida Q3112589 (Florida's P208) has only 4 children: AHCA, the Gaming Control Commission, the Governor (P361) and a class item. The expected "→ Government of Florida" link is missing. |
| 2 | DC Corporations Division Q138637634 | → Business and Professional Licensing Administration Q138637617 → Department of Licensing and Consumer Protection Q138637560 → government of the District of Columbia Q16152667 | The deepest chain found. DLCP has no head post. |
| 3 | NY Division of Corporations, State Records and UCC Q125449570 | → NY Department of State Q17110658 → State of New York Q5589272 | The Department's head post is Secretary of State of New York Q16148056, which has no open-ended holder statement. The Division is not on Govdirectory (3.2). |
| 4 | California DMV Q5020431 | → California State Transportation Agency Q16850598 → State of California Q5589189 | |
| 5 | California Franchise Tax Board Q5020495 | → Government Operations Agency Q16967000 → State of California | The Victim Compensation Board and General Services (the parent of the Office of Administrative Hearings) sit on the same chain. |
| 6 | California Department of Consumer Affairs Q5020410 | → Business and Consumer Services Agency Q136668814 → State of California | **The boards under DCA.** Wikidata lists 6 DCA children: Accountancy Q5020272, BPELSG Q114631457, Registered Nursing Q137738669, Vocational Nursing and Psychiatric Technicians Q114658274, Court Reporters Q114658495 and the Medical Board Q6806274. The fixture's DCA bodies, the Contractors State License Board Q5020359, BPPE Q5020287 and the State Athletic Commission Q5021008, have **no** P749. The Board of Pharmacy has no item. |
| 7 | Maryland Motor Vehicle Administration Q82510889 | → Maryland Department of Transportation Q8469802 → State of Maryland Q5589245 | MDOT has P2388 Maryland Secretary of Transportation Q125367752 and P797 Governor of Maryland. |
| 8 | Washington Corporations and Charities Division Q107180324 | → Office of the Secretary of State of Washington Q136376328 → **ends** | The office's head post Q7444392 exists. State of Washington Q16152657 has 18 children, but not this office. |
| 9 | Virginia Department of Taxation Q116797530 | → Commonwealth of Virginia Q5589334 | Its P2388 is the Secretary of Finance, the supervisor, not the head (2.4). |
| 10 | US Parole Commission Q7890865 (the successor named for the abolished DC Board of Parole, which has no item) | → US Department of Justice Q1553390 → Federal Government of the United States Q48525 | DOJ's head post is US Attorney General Q636207. |
| 11 | Texas Department of Criminal Justice Q3819598 | **no parent** | Its governing board, the Texas Board of Criminal Justice, has no item. State of Texas Q3112637 has 3 agency children: TDI, TxDOT and the Facilities Commission. |
| 12 | NC State CIO office Q136430659 | **no parent** | The post NC Chief Information Officer Q136632190 directs the NC Department of Information Technology Q85789496 and has no holder statements. |

### 4.4 Heads and holders (counts only)

* **14 head posts** were reachable from the 70 bodies. Of the 9 found through P2388, every one has the inverse P2389,
  so the two directions agree where both exist.
* **Open-ended holder statements are not "current holders".** These counts are P39 statements with no P582, where
  the holder has no date of death:

  | Post | All holder statements | Open-ended |
  |---|---|---|
  | Secretary of State of California | 19 | 6 |
  | Secretary of State of Texas | 23 | 4 |
  | Ohio Attorney General | 32 | 5 |
  | US Attorney for the District of Columbia | 40 | 8 |
  | President of the United States | 64 | 18 |
  | Governors of California and Maryland | | 2 each |
  | the other governors and the Mayor of DC | | 1 each |
  | Secretary of State of New York, Illinois Secretary of State, Attorney General of DC | 9, 21 and 3 | 0 |
  | NC Chief Information Officer, Secretary of the District of Columbia | 0 | 0 |

* Govdirectory's "Led by" uses the same test (3.1), so it inherits the same errors.

### 4.5 The wider picture (per-state agency classes, dissolved items excluded)

| Class ("state agency of …") | Items | With P749 | With P2388 | With P1001 |
|---|---|---|---|---|
| North Carolina | 400 | 14 | 15 | 343 |
| New York | 97 | 16 | 13 | 93 |
| California | 66 | 51 | 2 | 47 |
| Maryland | 27 | 12 | 4 | 27 |
| Texas | 16 | 3 | 1 | 16 |
| Florida | 13 | 6 | 0 | 13 |
| Virginia | 9 | 5 | 1 | 9 |
| Illinois | 6 | 0 | 0 | 6 |
| Washington | 4 | 0 | 0 | 4 |
| DC | no class | | | |
| state licensing board (nation-wide) | 26 | 8 | 0 | 21 (P797 on 14) |

Head posts are rare everywhere except New Jersey (17 of 23) and New York.

### 4.6 Quality problems found (drafts for the human-applied upstream flow, D8)

1. 31 of the 52 state and DC bodies outside the courts in the fixture have no parent. All Texas and North Carolina
   bodies are among them, as are the three DCA bodies (4.3 #6). The Florida Department of State, a related item in
   the fixture, has none either.
2. California, New York, Illinois and Ohio lack P208 although their government items exist. North Carolina's P208 is
   the Council of State.
3. The Virginia Department of Taxation's P2388 names the supervising cabinet secretary.
4. The Illinois Public Access Counselor Q104879968 has no P31, P749 or P1001. The fixture records only its parent post
   (Q3406491), so the fixture should gain this item.
5. The DC Board of Ethics and Government Accountability Q140357715 has only P31; it needs P1001 and a parent.
6. The California Business Entities Section is "part of" a post (2.3).
7. The Maryland Court of Special Appeals Q6781296 keeps a label from before the court's renaming.
8. Several posts have more than one open-ended holder statement (4.4). That is people data, so lexflow drafts no fix
   for it (entities-contacts 4: never office-holder or staff properties).

---

## 5. Escalation bodies that exist as Wikidata items

Searched by label, alias and full text (with scholarly articles and people excluded), then typed through SPARQL.
"None" means not found by any of those searches, which is a lower bound on absence. "(model)" means a reviewed
model or the fixture names the body.

| | FOI review, ombuds, public access | Compliance boards | Inspector general | Administrative hearings | Appellate and highest courts | Other |
|---|---|---|---|---|---|---|
| VA | FOIA Council (model): **none**. The NGO Virginia Coalition for Open Government Q131572978 must not be matched. | n/a | Office of the State Inspector General Q30272843 (P31 government agency; P131 Richmond; no P1001, no parent) | none | Supreme Court Q2398783; Court of Appeals Q5178333 | Attorney General: post only, Q4818656 |
| DC | Office of Open Government: **none**, but its parent body, the Board of Ethics and Government Accountability Q140357715, exists. FOIA appeals go to the Mayor (model): post Q5190572; the Mayor's Office of Legal Counsel: **none**. | n/a | none | Office of Administrative Hearings (fixture): **none** | Court of Appeals Q5283409 (the highest court) | Attorney General: post only, Q4818659 |
| MD | Public Access Ombudsman (fixture): **none**; its parent post is Attorney General Q4818647 | PIA Compliance Board and Open Meetings Compliance Board: **none** | none | Office of Administrative Hearings Q6781406 (untyped) | Supreme Court Q6781295; Court of Special Appeals Q6781296 | |
| TX | Open Records Division of the Attorney General: **none**. The AG (model) is post Q7707525 only. | n/a | none | SOAH Q25344983 (untyped) | Supreme Court Q3694683; Court of Criminal Appeals Q3694688; Courts of Appeals Q7707612 plus 2 of the individual courts (Q107210008, Q5447501) | State Auditor: none |
| CA | no FOI review body in the statute | n/a | none | OAH: **none** (parent: General Services). Office of Administrative Law Q5020726 reviews rules, not cases. | Supreme Court Q2629503; Courts of Appeal Q5020373 | State Auditor Q5020292 (P749 State of California) |
| FL | Office of Open Government: **none** | n/a | Chief Inspector General: **none** | DOAH: **none** | Supreme Court Q3001105; six District Courts of Appeal (the Sixth, Q118902575, is untyped) | Commission on Ethics Q117290062; Attorney General post Q8563951 |
| NY | Committee on Open Government (model): **none**. Its parent, the Department of State Q17110658, exists. The NGO Q131572971 must not be matched. | n/a | Office of the Inspector General Q136653725; Medicaid IG Q136653374; MTA IG Q104843758 | none | Court of Appeals Q11991268; Appellate Division Q7014754 and its four departments; Supreme Court Q3001111 | Commission on Judicial Conduct Q22061081 |
| IL | Public Access Counselor (model): Q104879968, **untyped, no parent** | n/a | Executive Inspector General: **none** | none. Independent Tax Tribunal Q111913812 (untyped). | Supreme Court Q3001109; Appellate Court Q5999328 | |
| WA | Attorney General's open-government ombuds: **none** | n/a | none (the State Auditor is post Q18394530) | OAH: **none**. Environmental and Land Use Hearings Office Q130360433. | Supreme Court Q4167888; Court of Appeals Q7971796 | Office of Education Ombudsman Q7972263 (untyped) |
| NC | fee mediation by the State CIO (model): office Q136430659 and post Q136632190; mediators certified by the Dispute Resolution Commission Q136387741 (model) | n/a | none | Office of Administrative Hearings Q136430648 (and its Rules Division) | Supreme Court Q7054626; Court of Appeals Q7054467 (both P361 Courts of North Carolina) | State Auditor Q136481273; Department of Justice Q136460101 |

**Summary.**

* Of the 13 open-government review, ombuds and mediation bodies in the first column (some not yet used by a model),
  **3** have a Wikidata item, all thinly modelled: the Illinois PAC (untyped, no parent), the NC State CIO office and
  the NC Dispute Resolution Commission.
* Inspectors general exist as items in 2 of the 10 jurisdictions. General administrative hearing offices exist in 3,
  plus Washington's land-use hearings office. An ombudsman office exists in 1.
* Every highest court and every intermediate appellate court exists. None of them carries P12452 except New York's
  Court of Appeals. Trial courts are mostly classes ([entities-sources.md](entities-sources.md) 3.2).

---

## 6. The mechanisms the reviewed models already contain

### 6.1 The ten records models

| State (sections) | First decision | Escalation and deferral steps in the model | Post or body | Wikidata |
|---|---|---|---|---|
| NY (Pub. Off. Law § 89) | agency: 5 business days (3)(a) | appeal in writing within 30 days to the "head, chief executive or governing body (or designee)", which decides in 10 business days ((4)(a)); the agency forwards the appeal to the Committee on Open Government ((4)(a)); Article 78 review ((4)(b)) | a post type resolved per agency; the Committee; the Supreme Court | P2388 on 13 of 97 NY agencies; Committee none; court Q3001111 |
| IL (5 ILCS 140/3, 9, 9.5) | public body through its FOIA officer: 5 business days | requests are forwarded to the FOIA officer (3(c)); review by the Public Access Counselor within 60 days of the denial (9.5(a)); the PAC may subpoena; binding opinion within 60 days or mediation (9.5(f)); then administrative or judicial review (11, 11.5) | post type "FOIA officer"; PAC; court | PAC Q104879968 untyped; the AG is a post |
| DC (D.C. Code §§ 2-532, 2-537) | public body: 15 business days; a deemed denial counts as exhausted (2-532(e)) | petition to the Mayor, who decides in 10 business days and may order disclosure (2-537(a)); a Superior Court suit if the Mayor does not decide or the body still withholds (2-537(a)) | Mayor (post); Superior Court | Q5190572; Q7643519 |
| TX (Gov't Code §§ 552.221, .301, .302) | officer for public information | **defer**: to withhold, the governmental body must ask the attorney general for a decision within 10 business days (552.301(b)) and send its reasons within 15 (552.301(e)); otherwise the information is presumed public (552.302) | AG (Open Records Division) | AG post Q7707525 only |
| CA (Gov. Code §§ 7922.530–.540) | agency: 10 days | **approval**: an extension of up to 14 days needs written notice by the "head of the agency or a designee" (7922.535(b)) | post type "head of the agency" | P2388 on 2 of 66 CA agencies |
| MD (Gen. Prov. §§ 4-202, -203, -206) | custodian: 30 days | **forward**: an individual who receives an application but is not the custodian notifies the applicant within 10 business days (4-202(c)(1)); fees and waivers by the official custodian (4-206) | post types "custodian" and "official custodian" | none needed |
| FL (§§ 119.07, 119.12) | custodian (or designee) | the custodian asks other officers in the agency (119.07(1)(c)); written notice to the custodian before suit (119.12(1)(b)); civil action, an order to produce, costs | post type "custodian"; circuit court | court class Q5461271 |
| WA (RCW 42.56.080, .520, .550) | agency: 5 business days | internal review of a denial; a deemed final action after 2 business days (42.56.520(4)); superior court show-cause, de novo review (42.56.550) | agency (its review officer); superior court | court class only |
| NC (G.S. 132-6, 132-6.2, 132-9, 7A-38.3E) | custodian | fee dispute → mediation by the State CIO or designee (132-6.2(b)); court action (132-9), with mediation started through the clerk within 30 days of the responsive pleadings, by a mediator certified by the DRC (7A-38.3E) | State CIO (post); DRC; clerk (office type) | Q136632190; Q136387741; clerk none |
| VA (§ 2.2-3704) | public body: 5 working days | the **body** may petition the court for more time, after trying to agree with the requester (2.2-3704(C)) | court (office type) | circuit court class Q16960472 |

### 6.2 Licence denial for a conviction (five reference answers)

The ladder is the same in every state: the board decides; then a hearing, or reconsideration or rehearing within the
agency; then judicial review.

* **VA.** Informal fact-finding, then a formal hearing (§§ 2.2-4019, -4020), then a court action (§ 2.2-4026). The
  board-level statute only points to the APA (§ 54.1-109).
* **CA.** A written request for a hearing (BPC § 485), with an ALJ presiding (§ 487), then reconsideration (Gov. Code
  § 11521), then a writ of mandate (§ 11523; CCP § 1094.5).
* **TX.** A contested case (Gov't Code § 2001.051), then a motion for rehearing (§ 2001.145), then district court
  (Occ. Code § 53.052).
* **MD.** A hearing under State Gov't § 10-207, then the circuit court (§ 10-222).
* **DC.** A petition to the board, then a hearing, then the Court of Appeals (D.C. Code §§ 47-2853.12, .22, .23). DC
  also **defers** the conviction inquiry until the applicant is otherwise qualified (§ 47-2853.17).

Across the 22 reviewed models, the commonest edge is private party → court (9 steps). The 15 reference answers that
carry steps add another 11.

### 6.3 Mechanism vocabulary (items `lexflow:mechanism:<slug>`)

| Mechanism | Binding | Seen in |
|---|---|---|
| `internal-appeal` (to the head or governing body) | yes | NY § 89(4)(a), WA 42.56.520(4) |
| `reconsideration` / `rehearing` | yes | CA § 11521, TX § 2001.145 |
| `hierarchical-appeal` (to the head of government) | yes | DC § 2-537 |
| `administrative-review` (by an external body, binding opinion) | yes | IL 9.5(f) |
| `advisory-review` (an opinion that does not bind) | no | the NY Committee and the VA FOIA Council (not yet modelled) |
| `mediation` | no, unless agreed | NC 132-6.2(b), 7A-38.3E; IL 9.5(f) |
| `contested-case-hearing` (an ALJ or hearing office) | as the statute says | CA § 487, TX § 2001.051, VA § 2.2-4020 |
| `judicial-review` | yes | every state |
| `ruling-request` (the body must obtain another body's ruling: a **deferral**) | yes | TX 552.301 |
| `approval` (a higher post must sign off) | yes | CA 7922.535(b) |
| `referral` (forward to the right holder) | n/a | IL 3(c), MD 4-202(c)(1), FL 119.07(1)(c) |
| `notification` (oversight is told, nothing waits) | n/a | NY § 89(4)(a), to the Committee |
| `oversight-complaint` (to an IG, ombuds or auditor) | no | none modelled yet |

---

## 7. Design

### 7.1 Entity kinds and keys

The keys follow [entities-contacts.md](entities-contacts.md) D2 and 1.2: lexflow mints them, and the QID is a
crosswalk column.

| Kind | Key | Example | Wikidata |
|---|---|---|---|
| Government root | `lexflow:agency:<st>:government`, `lexflow:agency:us:government` | `lexflow:agency:va:government` | Q5589334 (P208 of Virginia, or the State-of item) |
| Agency or unit | `lexflow:agency:<scope>:<slug>`, with `kind` from the plan plus `ombudsman`, `inspector-general`, `hearing-office`, `review-body`, `division` | `lexflow:agency:dc:corporations_division` | Q138637634 |
| Office type (one body per county, profession or case) | `lexflow:office-type:<st>:<slug>` (exists in the plan) | `lexflow:office-type:nc:clerk_of_superior_court` | class only |
| **Post** | `lexflow:position:<scope>:<slug>` | `lexflow:position:dc:mayor`, `lexflow:position:nc:state_cio`, `lexflow:position:va:tax_commissioner` | Q5190572, Q136632190, none |
| **Post type** (resolved per body) | `lexflow:position-type:<st>:<slug>` | `lexflow:position-type:ny:agency_head`, `lexflow:position-type:il:foia_officer`, `lexflow:position-type:fl:records_custodian`, `lexflow:position-type:ca:agency_head` | none |
| Mechanism | `lexflow:mechanism:<slug>` (6.3) | `lexflow:mechanism:administrative-review` | none |
| Person | **not modelled** | | |

A post type is resolved in context. `position-type:ny:agency_head` for the NY Department of Labor resolves to that
department's `headed-by` post. When no post is known, it is shown as the type's own label, "the head of the agency
(or designee)". That is exactly what the statute says.

### 7.2 Relations (new names in `entity_links.relation`)

| Relation | Subject → object | Wikidata equivalent | Made from | Example |
|---|---|---|---|---|
| `part-of` (planned) | agency → agency or government | P749, else P361; P355/P199 as inverse evidence | Wikidata `p:P749` without P582 or deprecated rank; curated | Corporations Division → BPLA → DLCP → DC government |
| `headed-by` | agency → post | P2388 (inverse P2389) | Wikidata, **always reviewed** (the VA Taxation case); statute | NY Department of State → Secretary of State of New York |
| `has-deputy` | post → post | P2098 | Wikidata | Governor of California → Lieutenant Governor |
| `reports-to` | post → post | P10645 | statute, curated | Tax Commissioner → Secretary of Finance (VA) |
| `supervised-by` | agency → agency or post | none (P797 only as a lead) | statute ("under the supervision of", "within the department"), curated | Contractors State License Board → DCA; Maryland Department of Labor → Governor of Maryland |
| `oversight-by` | agency → IG, ombuds or auditor | none | statute, curated | Virginia executive agencies → Office of the State Inspector General |
| `successor-of` (planned) | agency → agency | P1366/P1365 | reviewed | US Parole Commission → DC Board of Parole |
| `escalates-to` | decision-maker (role, agency, office type or post type) → reviewer | P12452, only for an unconditional body → body appeal | reviewed model steps; statute | NY agency → `position-type:ny:agency_head`; IL public body → PAC; DC public body → Mayor |
| `defers-to` | decision-maker → body whose ruling it must wait for | none | statute | TX governmental body → Attorney General (552.301(b)) |
| `requires-approval-of` | decision → post or post type | none | statute | CA extension → `position-type:ca:agency_head` (7922.535(b)) |
| `forwards-to` | receiving body or person → the right holder | none | statute | IL public body → `position-type:il:foia_officer` (3(c)) |
| `delegates-to` | post or agency → post type or agency | none | statute ("or designee", "may delegate"), curated | Mayor → Mayor's Office of Legal Counsel (by Mayor's order; method `curated`) |
| `notifies` | agency → oversight body | none | statute | NY agency → Committee on Open Government (§ 89(4)(a)) |

Every procedural edge carries its ground in the existing `entity_links` columns: `act_id`, `section`, `start`, `end`
and `quote` (at most 400 characters), plus `method`, `status` and `checked_at`. Its qualifiers go in `context`:

```json
{"mechanism": "lexflow:mechanism:internal-appeal", "binding": "binding", "initiated_by": "requester",
 "order": 1, "exhaustion": "required", "alternative_to": [],
 "deadline": {"amount": 30, "unit": "days", "anchor": "the denial of access (written, or by failure to respond in time)"},
 "decide_within": {"amount": 10, "unit": "business_days", "consequence": "deemed-denial"},
 "standard": null, "decision": null, "step": "lexflow:step:ny.records:appeal", "applies_when": null}
```

`order` ranks the rungs of one ladder, and `alternative_to` lists rungs that a user may take instead (Illinois: the
PAC or a court). The deadlines are copied from the model step's `deadline`, so they match the BPMN timers.

### 7.3 Storage

There is one new synced table. It has an entry in `SYNCED` and `state`, `updated_at` and `origin` columns, like the
three tables in [entities-contacts.md](entities-contacts.md) 1.3.

```sql
CREATE TABLE IF NOT EXISTS positions (
  key TEXT PRIMARY KEY,            -- lexflow:position:dc:mayor | lexflow:position-type:ny:agency_head
  state TEXT NOT NULL,             -- va | … | us
  scope TEXT NOT NULL,
  name TEXT NOT NULL,              -- "Mayor of the District of Columbia"; a type keeps the statute's words
  kind TEXT NOT NULL,              -- position | position-type
  body_key TEXT,                   -- the agency the post heads or sits in; NULL for a type
  applies_to TEXT,                 -- for a type: agency | public-body | board | court | any
  selection TEXT,                  -- elected | appointed | ex-officio | civil-service | unknown (from P31)
  wikidata TEXT, wikidata_match TEXT,   -- exact | none; a QID of a position item only
  aliases TEXT, status TEXT DEFAULT 'active',
  source TEXT, source_url TEXT, checked_at TEXT,
  updated_at TEXT NOT NULL, origin TEXT
);
-- deliberately absent: holder, holder_qid, start/end of tenure, any contact column
```

Agencies, office types, links, the seed order (by QID, then name or alias, then a new slug) and the rule that
reviewer decisions survive re-runs are as in [entities-contacts.md](entities-contacts.md) 1.2 and 1.3. That plan's
privacy rule 5.4 ("offices, not office-holders") stays as it is: office-holder claims (P1308, P39, and the person
values P488, P1037, P169, P3975) are dropped when a Wikidata response is parsed. Post items become first-class. Their
holders do not.

### 7.4 How the edges are made

1. **Wikidata crosswalk (structure only).** One run per corpus state, in two steps (collect the QIDs, then `VALUES`
   chunks), with `maxlag=5` and one query at a time. It reads `p:P749`, `p:P361`, `p:P2388`, `p:P2098`, `p:P10645`,
   `p:P1001`, `p:P571`, `p:P576` and `p:P1366`, together with their ranks, end times, references and statement
   GUIDs. P797 is stored as a lead (`status='proposed'`, `method='wikidata-p797'`), never accepted automatically.
   About 115 items cover the fixture today: the 103 start items plus 12 parents.
2. **From the reviewed models.** The candidates are every step whose recipient is a different actor from the one
   that decided, whose `kind` is `filing`, `hearing` or `review`, and whose action or quote matches appeal,
   petition, review, mediation or "ask for the attorney general's decision". Each candidate becomes a proposed
   edge from the decider's player to the recipient's player (`played-by`, from entities-contacts 1.4). Deadlines come
   from the step. Notices to oversight become `notifies`; "forwarded to" becomes `forwards-to`; an approval by a
   post becomes `requires-approval-of`. Of the 110 steps that matched the broad keywords across the 22 models and
   the 15 answers with steps, a reviewer would keep roughly the 45 that are real escalation or deferral edges. That
   count is an estimate, not a measurement.
3. **From xref roles.** In the cited sections, a reference with role `procedure` to an APA section makes the state's
   APA ladder apply. For example, VA § 54.1-109 → §§ 2.2-4019, -4020, -4026: that ladder is stored once per state
   and **inherited**, with the chain recorded in `context.inherited_from`. A `prerequisite_process` reference
   proposes a `defers-to` edge (BPC § 7.5(a) finality, as in [bpc-480-decision.md](bpc-480-decision.md)). An
   `authority` reference ("regulations adopted by the board", "authorized by") marks the body as the rule-maker of a
   DMN knowledge source. The gold files hold 81 `authority`, 96 `procedure` and 76 `prerequisite_process`
   references. The regex classifier gets about 70 % of roles right, so these edges stay proposed until reviewed.
4. **Curated additions** come from a small curated file of statutory oversight and supervision edges (IG
   jurisdiction, boards within departments). Statute sections not yet in the index keep a `quote` and an
   unresolved `act_id`.

### 7.5 The resolver

The resolver lives in `lexflow/entities/authority.py` (new), next to `entities/resolve.py`:

```
escalate(state, question, actor_or_decision, place=None, facts=None) -> list[Rung]
defer(state, question, step, facts=None) -> list[Wait]

Rung = {order, mechanism, target: {key, name, wikidata, kind}, binding, initiated_by, deadline, decide_within,
        exhaustion, alternative_to, source: {citation, quote, act_id}, basis: statute | inherited | oversight | structural}
```

1. Resolve who decided: role → `played-by` → agency, office-type instance or post type, using
   [entities-contacts.md](entities-contacts.md) 1.5 for generic mentions and the place.
2. **Statutory rungs.** Accepted `escalates-to` edges whose subject is the role, its player, the player's office type
   or class, or a post type that applies to it, for this question. Sort by `order`; attach exhaustion and deadlines.
3. **Inherited rungs.** The APA ladder reached through `procedure` references (7.4 step 3).
4. **Oversight channels.** `oversight-by` edges of the body and of its `part-of` ancestors, marked non-binding.
5. **Structural fallback.** Only when steps 2 and 3 found nothing: the body's `headed-by` post, then the head of its
   `supervised-by` or `part-of` parent, up to the government root. Every such rung is `basis: structural`, and its
   text says it is the chain of authority, not a review right (D4).
6. `defer()` returns `defers-to`, `requires-approval-of` and `forwards-to` edges, plus `prerequisite_process`
   references. Each comes with its trigger and the deadline the waiting step already has.

Worked examples (expected outputs; these become tests):

* **NY records, after a denial.**
  1. `internal-appeal` to `position-type:ny:agency_head`, resolved through the agency's `headed-by` post where one is
     known: 30 days to appeal, 10 business days to decide, deemed denial.
  2. `notification` to the Committee on Open Government. This is not a rung for the user; it is shown as "the agency
     must send your appeal to …".
  3. `judicial-review`: the Article 78 proceeding in the Supreme Court, with exhaustion required.
* **IL records.** The PAC (`administrative-review`, binding opinion or mediation, 60 days to file) **or** court
  (`alternative_to`). After an opinion, administrative or judicial review.
* **TX records, the body wants to withhold.** `defer()` returns a `ruling-request` to the Attorney General within 10
  business days, with "presumed public" on a miss (552.302). The requester's ladder is empty in the model, so the
  answer says so and offers no structural rung as a remedy.
* **VA licence denial.** Inherited APA rungs: informal conference → formal hearing → court action, each with its
  citation. DPOR has no Wikidata item, so the target is the lexflow agency key alone.

### 7.6 Process models: where the hooks already are

* **BPMN escalation events need no IR change.** `EventKind` already includes `"escalation"` (`lexflow/ir.py:41`),
  and the writer emits `escalationEventDefinition` with an `escalationCode` (`lexflow/bpmn_xml.py:31-39`,
  `:120-121`). A model step with `consequence: "deemed-denial"` already compiles to a boundary timer
  (`lexflow/extract/compile.py:84-88`). Later, after the benchmark freeze, a non-interrupting escalation boundary
  event can be added beside it, coded by mechanism, flowing to the requester's appeal step. The reviewing body's lane
  is its `played-by` agency.
* **Cross-model escalation** uses the links map's `ModelLink` with two new kinds, `escalates-to` and `defers-to`.
  An example is licence denial → the state's APA review process ([links-codebase-map.md](links-codebase-map.md) §2,
  extension points 8 and 18).
* **DMN.** `decisionMaker` and `decisionOwner` point to an `organizationUnit` whose `uri` is the agency or post key.
  A `knowledgeSource`'s owner is the rule-making body (the board in BPC § 480). `write_dmn` emits neither today
  (links map §0). The BPC 480 model already carries 47 authority requirements to statute knowledge sources, so it is
  the natural first test.
* **Deontic "power".** The IR has `"power"` and `"duty-to-decide"` (`lexflow/ir.py:43`), but the Wikibase
  `MODALITY` map has only the four LegalRuleML classes (`lexflow/publish/wikibase_lexipedia.py:38`). A
  power-conferring step therefore loads with no modality. Add a "Power" class when the authority properties are
  created, after checking LegalRuleML for an equivalent IRI before giving it `P8`.
* **Actors.** `Actor.wikidata` and `Actor.govdirectory` exist but are unused (`lexflow/ir.py:146-147`). Following
  entities-contacts D13, links go in `entity_links`, not in the IR, until the freeze ends.

### 7.7 Lexipedia's Wikibase: what to add

Live state on 2026-10-10: properties P1–P25 only. `P8` values are stored as URIs.

**A federated query works today.** This query ran on Lexipedia's query service and returned Q76 (Baltimore) →
Maryland and Q77 (Charlottesville) → Virginia, joined live from WDQS:

```sparql
SELECT ?item ?wdItem ?pl WHERE {
  ?item <https://lexipedia.wikibase.cloud/prop/direct/P8> ?wdItem .
  FILTER(STRSTARTS(STR(?wdItem), "http://www.wikidata.org/entity/Q"))
  SERVICE <https://query.wikidata.org/sparql> {
    ?wdItem <http://www.wikidata.org/prop/direct/P131> ?p .
    ?p <http://www.w3.org/2000/01/rdf-schema#label> ?pl . FILTER(LANG(?pl) = "en")
  }
}
```

The same pattern reads `P749`, `P2388` or the per-state agency lists at query time. That is why the Wikibase needs
items only for what processes name.

**Classes (new).**

* government agency (P8 wd:Q327333; already in the contacts plan);
* **position** (P8 wd:Q4164871);
* **position type** (P6 subclass of position);
* **review mechanism**, with its ~13 instances from 6.3.

**Properties (new).** Each waits for your go-ahead, and they should be created together with the sets in
[entities-contacts.md](entities-contacts.md) 1.7 and [terms-wikibase.md](terms-wikibase.md) §4.

| Property | Datatype | ≡ Wikidata (`P7`) | On |
|---|---|---|---|
| head position | item | P2388 | agency → post |
| supervised by | item | – | agency → agency or post |
| escalates to | item | P12452, partially | role, agency, office type or post type → reviewer |
| defers to | item | – | role, agency or step → body |
| delegates to | item | – | post or agency → post type or agency |
| requires approval of | item | – | step or role → post or post type |
| oversight by | item | – | agency → IG, ombuds or auditor |
| *qualifier:* review mechanism | item | – | on escalates to, defers to, oversight by |
| *qualifier:* binding | item (binding, advisory, none) | – | on the same |
| *qualifier:* exhaustion required | item (yes, no) | – | on escalates to |
| *qualifier:* time limit | quantity (days, business days) | – | on escalates to, defers to; plus the existing string `P22` for the anchor |
| *qualifier:* for process | item | – | the `lexflow:process:` item, so an edge can be scoped to one question |

**Reused properties:** P5 instance of, P6 subclass of, P8 exact match, **P9 part of** (agency → parent, as the
contacts plan already does), P13 references (→ the statute item), P15 jurisdiction, P17 bearer (step → role), P22
citation (the statute's words), P25 legal identifier, and the planned "played by" and start/end time.

**Deliberately not added:** position holder, position held, any person-valued property, and any contact property on
a post.

**Loader.** After the planned `Loader.agencies()`, add `Loader.positions()` and `Loader.authority()`. All three are
built from the DB, because `clear` replaces statements wholesale
([links-codebase-map.md](links-codebase-map.md) §3). Two changes are needed:

* `_snak` must write quantity snaks; today it writes only item and string snaks
  (`lexflow/publish/wikibase_lexipedia.py:122-125`).
* `retire_drafts` already skips key kinds other than process, role and step (`:218-219`), so the new keys are safe.

**Item shapes.**

* **Agency:** P5 class; P9 parent; *head position*; *supervised by*; P15; P8 (exact matches only).
* **Post:** P5 position or a post type; P15; P8; *reports to*, via a P13-referenced statement, only when a statute
  says so.
* **Role:** gains "played by", and each **decision-maker role** carries its *escalates to* statements with
  qualifiers. A role is per question, so the scope is implicit.

**Rough size.**

* about 200 agencies, courts and office types (already planned);
* 11 government roots;
* about 12 intermediate parents (CalSTA, Government Operations, Business and Consumer Services, MDOT, BPLA, DOJ, the
  Florida Department of State, NC DIT and others);
* about 40 posts (governors, the Mayor, attorneys general, secretaries of state, heads used by models) and about 25
  post types;
* about 20 review and oversight bodies (most with no Wikidata item);
* 13 mechanisms.

That is about **320 items**, against 1,140 US Govdirectory entries, and Govdirectory has none for 8 of the 10
jurisdictions.

### 7.8 If an office-holder ever has to be shown

The default is **off**. If a page ever needs "who holds this post now":

* Read it live from WDQS when the page renders, and never store it.
* Do it only for posts typed public office, elective office or position.
* Use only non-deprecated `P39` statements that have a `P580` and no `P582`. Show a name only when **exactly one**
  such statement exists; otherwise say "Wikidata does not give a single current holder".
* Label it "according to Wikidata, since <P580>", with no contact detail of any kind and no link other than the
  Wikidata item.

This is the stricter form of Govdirectory's own test: it adds the single-statement and start-date checks, which would
have caught the counts in 4.4.

### 7.9 Upstream suggestions

The problems in 4.6 become drafts in `upstream_suggestions` (entities-contacts 2.3 and 4), referenced to the
official page or the statute. Examples: P749 for the three DCA bodies, and for the Florida Department of State →
State of Florida; P31 and P749 for the Illinois PAC; P208 for CA, NY and IL. They are reviewed in batches of 20 or
fewer and applied by a person. Nothing about people is drafted.

---

## 8. Phases and tests

| Phase | Scope | Tests (new files) | Exit check |
|---|---|---|---|
| A. Crosswalk fixture (read-only) | `fixtures/entities/authority.json` from a polite rerun of section 10's queries: parents, heads, posts and escalation bodies for the corpus states | The fixture has no person QIDs or names (a scan for P39/P1308 values and the human class) | The numbers in 4.1 and 5 are reproduced |
| B. DB and resolver | `positions`; the new relations; seeding from A; proposals from the models (7.4), reviewed; `entities/authority.py` | The ten ladders in 6.1 and the four worked examples in 7.5 come out as written; structural rungs are never labelled remedies; deadlines equal the model steps' deadlines; re-runs keep reviewer decisions; P797 is never auto-accepted | At least 90 % of the decision-making actors in reviewed models have a statutory ladder, or an explicit "none in the statute" |
| C. Wikibase (after your go-ahead) | the classes and properties in 7.7, together with the contacts and terms sets; the loader phases; a dry run | Dry-run statements for the NY, IL, TX and DC records roles; no person-valued statements; P8 only on exact matches | A user-triggered load of the corpus states |
| D. BPMN and DMN (after AskBench) | escalation boundary events; `ModelLink` kinds; DMN `decisionMaker` and knowledge-source owners | The BPMN validates; SpiffWorkflow still loads the split DMN | The BPC 480 DMN carries organisation units |
| E. Upstream | drafts from 4.6 | Drafting is idempotent; no people data | The first reviewed batch is exported |

Metrics:

* the share of non-private actors with a resolved escalation ladder;
* the share of rungs with a statute quote;
* the share of agencies with a parent chain to the government root (Wikidata alone: 20 of 52);
* the share with a head post (Wikidata alone: 8 of 52);
* the applied rate of upstream drafts.

## 9. Open questions

1. **Wikibase writes.** The classes, properties and items in 7.7 are writes to lexipedia.wikibase.cloud. Should
   they be decided together with the contacts and terms property sets?
2. **Posts as first-class items.** [entities-contacts.md](entities-contacts.md) 5.4 keeps position items only as
   identity hints for offices. This design makes posts items (still with no holders). Do you accept that change?
3. **A directory beyond the processes.** Should the ~978 state-level bodies from [entities-sources.md](entities-sources.md)
   sit in the DB as an unpublished directory, so that a user can name any body, while the Wikibase holds only what
   processes use?
4. **Officeholder display.** Keep it off (the default), or allow the live, single-statement rule in 7.8?
5. **Generic heads.** Should per-agency head posts be minted lazily, when an answer resolves `agency_head`, or up
   front for every agency in a records model?
6. **Points that could be raised with the Govdirectory group, without assuming their answer.** Showing the head
   *post* (P2388) beside or instead of a person; sub-national lists for the other corpus states; using P12452 for
   courts and agencies; the quality items in 4.6. Any report has to be written by a person.
7. **Court ladders.** The trial → intermediate → highest court ladder could be one curated edge set per state,
   proposed upstream as P12452. Is that worth doing?

## 10. Method and sources

* All requests were read-only GETs on 2026-10-10.
  * User-Agent `lexflow-research/0.1 (https://github.com/alibama/lexflow)`.
  * At least 1.15 s between requests to each host; one SPARQL query at a time; `maxlag=5` on `wbgetentities`,
    retried after waiting.
  * About 400 requests in all, about 35 of them to WDQS.
* No `.env` value was read or printed.
* No lexflow job, build, benchmark or Ollama call was run. The repository's Python was not imported; the fixtures
  and curated JSON were read directly.
* **Wikidata.**
  * `wbsearchentities` and `list=search` over the property namespace, with about 100 keywords;
  * `wbgetentities` for the 50 properties in 2.1 and their constraint items;
  * `Template:Number of main statements by property` and `Template:Number of qualifiers by property` (raw, last bot
    update 2026-10-05);
  * revision history for the creation dates of P12452 and P10645;
  * WDQS queries for the state items, the parent walk, details, posts and holder counts (counts only), the per-state
    classes, Govdirectory's NY and NC lists, the children of parent bodies, P12452 and P797 use, and the escalation
    candidates;
  * `list=search` and `wbsearchentities` for named escalation bodies.
* **Govdirectory.**
  * the GitHub tree of `govdirectory/website`;
  * `queries/organization-optional.rq`, the US, New York and North Carolina generators, `templates/org.html`,
    `templates/org-table.html`, `views.yaml` and `queries/topics.rq`;
  * the live pages `/united-states/new-york/Q17110658/` and `/united-states/north-carolina/Q136481241/` (a person
    name, if any, was redacted when read);
  * `Wikidata:WikiProject Govdirectory/Data model` and Entity Schema E330.
* **Lexipedia.**
  * the property list (`list=allpages`, namespace 122);
  * one local SPARQL query and one federated SPARQL query.
* **Repository.**
  * `fixtures/entities/agencies.json`, `curated/*/*.json`, `curated_ask/*/*.json` and `fixtures/xref/gold_*.json`;
  * `lexflow/law/xref.py` (`ROLES`, `role_of`; cited by name because the file was being edited while this was
    written); `lexflow/ir.py:41-43` and `:142-148`; `lexflow/bpmn_xml.py:31-39` and `:120-121`;
    `lexflow/extract/compile.py:84-88`;
    `lexflow/publish/wikibase_lexipedia.py:29-38`, `:122-125` and `:209-232`.
