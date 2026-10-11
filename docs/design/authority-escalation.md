# Authority, escalation and deferral: how processes cross-reference bodies, units and posts

Status: design, 2026-10-10; revised the same day to fix every point that
[verify-authority.md](verify-authority.md) marked wrong or missing. This note is the only file written. Nothing was
written to the database, the DokuWiki, lexipedia.wikibase.cloud, Wikidata or Govdirectory, and no code, fixture or
curated file was changed. The few live reads made for it were read-only and rate-limited (section 9).

This note answers one question and designs one thing:

* **The question.** Does the Lexipedia Wikibase need every Govdirectory entity, so that processes can be
  cross-referenced against people and organisational units, and so that lexflow can find the mechanisms that
  escalate or defer a process according to who holds authority?
* **The design.** It covers four things:
  * how a process step reaches the body, unit and post that acts in it;
  * how authority is recorded: who may decide, review, rule or advise, and who must wait;
  * how escalation and deferral "ladders" are derived from statutes and checked;
  * how they appear in BPMN, DMN, the dashboard, the wiki and the Wikibase.

It builds on four research notes written the same day, and settles the points where they differ (0.4):

* [authority-wikidata.md](authority-wikidata.md): what Wikidata and Govdirectory model;
* [authority-wikibase.md](authority-wikibase.md): Lexipedia's Wikibase and what Wikibase Cloud allows;
* [authority-ladders.md](authority-ladders.md), with [`fixtures/authority/ladders.json`](../../fixtures/authority/ladders.json): the 22 hand-built
  ladders;
* [authority-standards.md](authority-standards.md): ORG, Popolo, CPSV-AP, BPMN, DMN, WS-HumanTask, LegalRuleML and Hohfeld.

It extends [entities-contacts.md](entities-contacts.md) (agencies, office types, `played-by`, contacts),
[terms-wikibase.md](terms-wikibase.md) (defined terms and concepts), [bpc-480-decision.md](bpc-480-decision.md)
(DMN knowledge sources and cross-process status links) and [links-codebase-map.md](links-codebase-map.md) (keys,
properties and extension points). Where it departs from them, 0.4 says so.

Scope rules followed throughout:

* **People.** People appear only as holders of public offices, as Wikidata records them. In this note they appear
  only as counts:
  * no office-holder is named;
  * no person's contact detail appears;
  * no private individual is looked up.

  The design models posts, never persons.
* **Neutrality.** No researcher or group is named as a partner, adviser or endorser. Nothing here assumes what the
  Govdirectory group will decide.

---

## 0. The answer

### 0.1 In one paragraph

**No: do not load all of Govdirectory into the Wikibase. Do make a smaller, targeted update, and send the
structural gaps upstream to Wikidata.** Govdirectory lists 21,084 organisations, but only 1,140 in the US (federal,
New York and North Carolina), nothing for 9 of lexflow's 11 jurisdictions, and 7 of the 91 Wikidata items our
models name. It holds no data of its own and no units, posts, supervision, appeal or delegation, so a 29,000-item
copy would answer none of the authority questions. Instead, add to Lexipedia, after your go-ahead: 11 properties,
4 qualifiers, about 25 classes and about 77 vocabulary items; then about 265–320 items for the bodies, units, office
types and posts (never people) that reviewed processes name, with their parent chains; and one item for each
accepted escalation or deferral rung of a reviewed model. That is at most 85 rungs now. The fixture's other 58 rungs
come from reference answers, and they load only once those answers become reviewed models with process items. In
all that is about 450–500 new items. The loader rewrites every item it owns on each run, so a full load is about
2,000 writes: some 33 minutes at one edit a second. Keep identity, parents, head posts, contacts and office-holders
in Wikidata, reached through `P8 exact match` and a federated query that already works. Propose upstream to Wikidata, as reviewed edits a person applies, the missing bodies, parent links,
head posts, per-state agency classes and FOI request URLs; Govdirectory then shows them for the states it lists.
The escalation routes themselves come from the statutes the models quote, because neither source records who
reviews whom.

### 0.2 The reasons, with the numbers

* **Govdirectory covers little of the corpus.** It lists 21,084 organisations in 45 countries and the European
  Union, but only 1,140 are in the US: 374 federal (mostly embassies and consulates), 159 for New York and 607 for
  North Carolina. It has nothing for 9 of lexflow's 11 jurisdictions (VA, DC, MD, TX, CA, FL, IL, WA and OH). Of the
  91 Wikidata items that lexflow's models name, 7 are on its lists. None of the 90 bodies on the fixture's 22
  ladders is.¹

  ¹ That last count is partly an artifact of the fixture. The reviewed NC records model has a fee-mediation step
  (requester → State CIO, G.S. § 132-6.2(b)) that the fixture gives no rung (9.2 #7). The North Carolina Chief
  Information Officer office (Q136430659, a state agency of North Carolina) **is** on Govdirectory's NC list.
* **It adds nothing that would answer an authority question.** It holds no data of its own: every value is a
  Wikidata statement. It has no units below the listed agencies, no posts, and no supervision, appeal or
  delegation. A full copy would be about 29,000 items and some 8 hours of writes, and 95 % of it would be outside
  the US. It would be a stale duplicate.
* **What to add to Lexipedia.**
  * First, after your go-ahead: 11 properties, 4 qualifiers and about 25 class items.
  * Then about 265–320 items for the bodies, units, office types, posts and post types that reviewed processes
    name, with each body's parent chain up to its state government.
  * One item for each accepted rung of a reviewed model: at most 85 now, from the 14 reviewed models that have a
    ladder (86 with the NC fee-mediation rung). The other 58 fixture rungs come from AskBench reference answers
    (sealing in CA, MD and VA; licensing in CA, VA, DC, MD and TX). Lexipedia has no process item for them, so under
    A7 they wait until those answers become reviewed models.
  * About 77 vocabulary items.
  * Several of the bodies that matter most for escalation have no Wikidata item at all: the NY Committee on Open
    Government, the VA FOIA Council, the MD PIA Compliance Board, the D.C. Office of Open Government and Virginia's
    DPOR.
* **What to keep in Wikidata, reached by QID.** Identity, labels, parent organisations and head posts where
  Wikidata has them, lifecycle dates, contacts, and everything about office-holders. Each Lexipedia item carries
  `P8 exact match` to its Wikidata item. A federated query from Lexipedia's query service to Wikidata already
  works.
* **What belongs upstream.** These go to Wikidata as reviewed suggestions that a person applies, never as
  automatic edits:
  * items for the missing bodies;
  * parent links for the 31 of 52 state bodies that lack one. For example, Cal. Bus. & Prof. Code § 7000.5(a)
    places the Contractors State License Board in the Department of Consumer Affairs, but its Wikidata item has no
    parent.
  * head posts where a statute names them. Fla. Stat. § 20.10(1) says the Secretary of State heads the Department
    of State.
  * per-state agency classes and FOI request URLs.

  Govdirectory shows such fixes for the bodies it already lists in New York and North Carolina after its next
  build. Listing other states is its own decision.
* **Escalation cannot come from either source.** Wikidata's *appeals to* (P12452) is used on no state agency in
  the corpus. In California, the director of the parent department may not review a board's decisions on
  "setting standards, conducting examinations, passing candidates, and revoking licenses" (Bus. & Prof. Code
  § 109(a)). A licence denial falls under "passing candidates" on a fair reading, which the design records as an
  inference. The escalation and deferral routes come from the statutes the models already quote. All 143 rungs in
  `fixtures/authority/ladders.json` are grounded verbatim.

### 0.3 What goes where

| | What | Size | Why |
|---|---|---|---|
| **Add to Lexipedia** (wiki writes, after your go-ahead) | Classes and properties for organisations, units, posts, post types and rungs (5.2–5.4). Items for what reviewed processes name, and their parent chains (5.5). *Played by* on roles, *recipient* on steps, *review status* everywhere. | about 450–500 new items. A load also rewrites the 1,413 items lexflow already keyed, so it is about 2,000 writes: about 33 minutes at one edit a second, or 7–8 minutes at the 268 a minute the account reached | The wiki today has no class for an organisation, a unit or an office. A step's bearer points at a role item that holds only a key, a class and a state, so nothing joins a process to a body or a post. |
| **Keep in Wikidata, reach by QID** | Labels, aliases, parent chains and head posts where present, inception and dissolution, contacts, holders of public offices (never copied) | 76 distinct body QIDs in `agencies.json`, 31 in the ladders (7 of them new) | It is the source Govdirectory renders. A copy would go stale. The federated query was tested on 2026-10-10. |
| **Propose upstream** (drafts that a person reviews and applies; never automatic) | Missing items, P749 parents, P2388 head posts, P31 per-state classes, P10214 FOI request URLs, and fixes such as the Florida Division of Corporations being typed "database" | about 65 drafts to start (5.8) | Fixes made there reach every reuser, Govdirectory included. |
| **Do not do** | A Govdirectory or Wikidata mirror; person items or holder statements; federated properties; remedies inferred from the organisation chart | – | Section 3.8 and 7.1 |

### 0.4 Key decisions, including where the research notes differed

| # | Decision | Why | Settles |
|---|---|---|---|
| A1 | **Model posts, never persons.** Escalation goes to "the head of the agency or a designee", "the Mayor" or "the Public Access Counselor": offices, not people. No holder columns, no `P39`/`P1308` statements, no person items. | Privacy; the hosting policy; Wikidata's holder data cannot say who holds a post now (1.7). | – |
| A2 | **One key spelling for posts:** `lexflow:position:<scope>:<slug>` and `lexflow:position-type:<st>:<slug>`. | `ladders.json` already uses these (12 keys), as does authority-wikidata. `lexflow:office:` (authority-wikibase) collides with *office type*. `lexflow:post:` (authority-standards) is a third spelling. | wikidata, ladders vs wikibase, standards |
| A3 | **Units keep `lexflow:agency:` keys**, with `standing = 'unit'` and a `part-of` link. | entities-contacts 1.2 already lists "division" as an agency kind. A unit made independent later keeps its key. `lexflow:unit:` is the statutory-unit prefix of terms-wikibase. | standards (`lexflow:org-unit:`) |
| A4 | **Two layers.** Structural edges (part of, headed by, appointed by) live in `entity_links`, and standing powers in their own `power_grants` table (3.1). Procedural mechanisms live in one `rungs` table, keyed by the statute provision and bound to model steps. | A rung has about 25 fields: trigger, deadlines, exhaustion, binding effect, quotes and next rungs. The ladders already key it by provision, so inserting a rung changes no key. Power grants need their own key: in `entity_links`, a power and a disability over the same thing would collide. | standards (`routes`) vs ladders (rungs) vs wikidata (procedural `entity_links`) |
| A5 | **Authority is data.** Each power, duty or disability a statute gives a body or post is a grounded power grant. Negative grants are included, such as Cal. BPC § 109(a), under which the director may not review a board's decisions on standards, examinations, passing candidates and revocations (3.1). | This is what lets lexflow say why the director of the parent department is *not* the next rung. | – |
| A6 | **Only statute-grounded rungs are remedies.** A structural fallback (head, then parent, then government) is labelled "chain of authority, not a legal right of review". Exhaustion, binding effect and time limits are read from the text, or shown as "the statute does not say". | The review path is not the organisation chart (3.8). | all four |
| A7 | **Derive, then review.** Rungs are proposed from steps, deadlines, cross-references and body mentions. A person accepts them. Only accepted rungs of reviewed or agreed models are shown or published. A rung from a reference answer waits until that answer becomes a reviewed model with a process item. | The publishing rule in memory. | – |
| A8 | **Wikidata link: `P8 exact match` only, with a kind check.** A position QID goes on a position item, an organisation QID on an agency item, and a parent's QID on the parent's own item. Seeding matches only on `exact`, kind-checked QIDs (1.3). No separate "Wikidata item ID" property is needed now. | The tested federated query joins on P8. The fixture has QIDs on the wrong kind of item in both directions (9.2 #5), and `agencies.json` shares 5 QIDs between exact and parent-only entries. | wikibase (external-id property becomes optional); contacts 1.2 (seeding by any QID) |
| A9 | **A dedicated *parent organization* property** (≡ wd:P749), not `P9 part of`. | P9 already carries step → process and statute part-of. One property per meaning keeps property paths clean, and maps exactly to P749 for federated joins. This is your call, because entities-contacts 1.7 planned P9. | contacts vs standards |
| A10 | **DMN decision makers go in `lex:decisionMaker`.** The standard `decisionMaker`/`organizationUnit` appears only in an opt-in export. | bpmn.io's dmn-moddle cannot read `organizationUnit`, so dmnlint fails ([bpc-480-decision.md](bpc-480-decision.md) §2). | wikidata, standards (both proposed `organizationUnit`) |
| A11 | **BPMN: an appeal to another body is a message flow between pools.** An escalation event is used only for a hand-up inside one body. Timers carry statutory clocks. | BPMN escalations propagate within one process hierarchy (authority-standards 2.6). | wikidata (escalation boundary events) vs standards |
| A12 | **No mirror.** A Govdirectory page is linked with *described at URL* for listed bodies. | 0.2 | – |
| A13 | **Upstream stays human.** Drafts go through `upstream_suggestions` (entities-contacts 2.3, 4). Nothing is filed with Govdirectory in lexflow-written words. | Wikidata bot policy; Govdirectory's rule against AI-generated contributions. | – |
| A14 | **New code goes in new modules** (`lexflow/entities/authority.py`, `lexflow/entities/authority_bpmn.py`) and new tests. IR or schema fields wait until AskBench finishes. | The benchmark freeze. The IR already has pools, lanes, message flows, escalation events and call activities. | – |
| A15 | **Two changes to entities-contacts 5.4.** (1) P2388 *position held by head of the organization* and P1313 *office held by head of government* are kept when a Wikidata response is parsed, as reviewed leads for `headed-by`. Their values are posts, not people. Every person-valued claim (P1308, P39, P488, P169, P1037, P3975) is still dropped. (2) Position items become first-class `positions` rows (1.5), not only `related_items` for identity. | 5.4 drops P2388 and P1313 at parse time because Govdirectory reaches the person through them. This design needs the post they name, and never follows it to a holder. | contacts 5.4 |

---

## 1. The entity model

### 1.1 Kinds

| Kind | What it is | Key (Wikibase P25) | Stored in | Example | To start |
|---|---|---|---|---|---|
| Jurisdiction | The territory a law applies to | `lexflow:jurisdiction:<st>` | Wikibase (exists) | Florida, Lexipedia Q33 | 52, plus 3 cities |
| Government root | The state's government as an organisation: the top of every parent chain | `lexflow:agency:<st>:government`; `lexflow:agency:us:government` | `agencies` | State of Florida (wd:Q3112589) | 11, plus federal |
| Organisation | A body with standing in law: department, board, commission, court, office | `lexflow:agency:<scope>:<slug>`, `standing='organisation'` | `agencies` (entities-contacts 1.3) | Florida Department of State (Q11969252) | about 130 |
| Organisational unit | A part with no standing outside its parent: division, section, bureau | `lexflow:agency:<scope>:<slug>`, `standing='unit'` | `agencies` | Florida Division of Corporations (Q107179384) | about 15 |
| Office type | One body per county, profession, venue or record holder | `lexflow:office-type:<st>:<slug>` | `office_types` | `lexflow:office-type:ca:licensing_board` | about 60 |
| **Position** (post) | An office that exists apart from whoever holds it (ORG `Post`; LegalRuleML *Figure*) | `lexflow:position:<scope>:<slug>` | `positions` (new, 1.5) | `lexflow:position:fl:secretary_of_state` (Q7444366) | about 40 |
| **Position type** | A post that every body of a kind has, resolved against the body in question | `lexflow:position-type:<st>:<slug>` | `positions` | `lexflow:position-type:ny:foil_appeals_officer` ("head, chief executive or governing body of the entity, or the person it designates") | about 25 |
| Office holder | A person, only as Wikidata records the holder of a public office, with dates | **no key** | **not stored**: a live view, off by default (1.7) | – | 0 |
| Process role | An actor in one process | `lexflow:role:<st>:<q>:<actor>` | exists | `lexflow:role:fl:business:department` (Lexipedia Q776) | 199 items |
| Defined term, concept | What a section defines for a scope; the shared meaning across states | `lexflow:term:…`, `lexflow:concept:…` | terms plan | `lexflow:term:fl:607.0201:incorporator` | terms plan |
| Private party | The marker for roles that are never resolved to a person or company | `lexflow:private-party` | constant | incorporator, requester | 1 |
| **Rung** | One escalation, hand-off or deferral mechanism that a statute creates (section 3) | `lexflow:rung:<st>:<question>:<section-slug>:<subtype-code>` (1.3) | `rungs` (new, 3.5) | `lexflow:rung:fl:business:605.0210-7:court-petition` | 143 in the fixture, 85 of them from reviewed models |

### 1.2 Mapping to the standards and to Wikidata

| lexflow | W3C ORG | Popolo / Open Civic Data | schema.org | Wikidata | Lexipedia (5.2) |
|---|---|---|---|---|---|
| government root | `org:FormalOrganization` | Organization | GovernmentOrganization | the item that a state's P208 points to (*executive body*) | P5 *government* |
| organisation | `org:FormalOrganization` | Organization (`classification`) | GovernmentOrganization | P31 Q327333 *government agency*, or a per-state class | P5 *government agency* / *court* |
| unit | `org:OrganizationalUnit` | Organization with `parent` | `department` | P31 Q10387680 *organization unit*; P749, P199 or P361 | P5 *organizational unit* |
| office type | `org:Organization` + `org:classification` | – | – | a class item (for example a court system) | P5 *office type* (entities-contacts 1.7) |
| position | `org:Post` | Post (`organization`, `role`, start and end) | `Role.roleName` | P31 Q4164871 *position* or Q294414 *public office* | P5 *position* |
| position type | `org:Post` + `org:Role` | Post.role | – | – | P5 *position type* |
| office holder | `org:holds` / `org:heldBy`, `org:Membership` | Membership | Role with dates | P39 / P1308, qualifiers P580 and P582 | **none** |
| process role | `org:Role` | Membership.role | – | – | P5 *legal role* (Q23) |
| part of | `org:subOrganizationOf`, or `org:unitOf` for a unit | `parent` | `parentOrganization` / `subOrganization` | P749 (P355 inverse; P199, P361 as evidence) | *parent organization* |
| headed by | `org:headOf` is agent-level, so no exact term; nearest is an `org:Post` with role "head" | Post.organization + role | – | P2388 (inverse P2389) | *head position* |
| position in | `org:postIn` | Post.organization | – | P2389 for heads; otherwise P361 | *position in* (not `P9 part of`, so that P9 paths never return posts) |
| appointed by | – | – | – | P748 | *appointed by* |
| reports to | `org:reportsTo` | – | – | P10645 | DB only, for now |
| jurisdiction | – | Area; OCD division id (a crosswalk column) | `areaServed`, `jurisdiction` | P1001 | P15 |
| played by | `org:Role` filled by an organisation | – | `GovernmentService.provider` | – | *played by* (entities-contacts) |

### 1.3 Keys

The rules of entities-contacts 1.2 apply unchanged:

* lexflow mints every key, and a QID is only a crosswalk column;
* a slug is lower-case ASCII, at most 48 characters, with the leading state name dropped;
* keys never change: a rename adds an alias, and an abolition sets a status;
* seeding matches by QID first, then by name or alias, then mints a new slug.

Two changes to the seeding rule:

* **Match only on `exact`, kind-checked QIDs.** `agencies.json` shares 5 QIDs between an `exact` entry and
  `parent body only` entries. Q6781312 (the Maryland Department of Public Safety and Correctional Services) is
  shared by 5 entries, and Q17110658 by the NY Department of State and the Committee on Open Government. Matching
  on any QID would merge the Committee into the Department.
* **Seed by key, with a merge rule.** In `ladders.json`, 3 office-type keys stand for 2 or 3 bodies each, with
  different `kind` values: `lexflow:office-type:il:circuit_court`, `…:md:circuit_court` and `…:tx:district_court`
  (90 bodies, 85 keys). The seed merges their names into `aliases` and keeps the generic kind. A body named as one
  instance ("District court of Travis County") goes to review as an office-type instance. Last-writer-wins is
  never used.

New key kinds:

| Kind | Form | Example | Model-scoped? |
|---|---|---|---|
| position | `lexflow:position:<scope>:<slug>` | `lexflow:position:dc:mayor`, `lexflow:position:ca:director_of_consumer_affairs` | no |
| position type | `lexflow:position-type:<st>:<slug>` | `lexflow:position-type:ca:agency_head_or_designee` | no |
| rung | `lexflow:rung:<st>:<question>:<section-slug>:<subtype-code>`. It is keyed by the quoted provision, not by its place in the ladder. | `lexflow:rung:ca:license_conviction:gov-11523:writ-of-mandate` | by question. Retired by its own rule (5.6). |
| power | `lexflow:power:<slug>` | `lexflow:power:review`, `lexflow:power:extend-time` | no |
| vocabulary | `lexflow:vocab:<set>:<slug>` | `lexflow:vocab:trigger:deemed_denied`, `lexflow:vocab:exhaustion:optional` | no |

**How a rung key is built.** Re-runs must compute the same key, so nothing in it is free text:

* **`<section-slug>` comes from the `act_id`.** It is the act_id's code or act token where it has one, lower-cased
  and without its letter prefix (California `STATE_CA_Cgov_…` gives `gov`, `Cbpc` gives `bpc`; New York
  `STATE_NY_APBO_…` gives `pbo`; Florida's and Virginia's act_ids have none). Then come the section number as the
  act_id spells it, and the pinpoint, with each parenthesised part joined by `-`. Examples: `gov-11523`,
  `bpc-485-b`, `605.0210-7`, `pbo-89-4-a`. California has several codes, so a bare `485` would be ambiguous.
* **`<subtype-code>` comes from a closed code list**, kept in code beside the ten types (3.2). Examples:
  `court-petition`, `civil-appeal`, `corrected-refiling`, `hearing-request`, `reconsideration`, `writ-of-mandate`,
  `reapplication`, `fee-mediation`, `registration-prerequisite`. The fixture's `subtype` stays as free-text
  description; the deriver maps it to a code, and never slugs it. The code carries the uniqueness where one
  pinpoint has two rungs, as four already do: N.Y. § 89(4)(a), Fla. § 605.0210(7), Cal. PEN § 11126(c) and Va.
  § 19.2-392.12(I). The codes are part of the key only; they are not Wikibase items.
* **A corrected pinpoint keeps the old key.** When a reviewer corrects a pinpoint or a code, the rung keeps its
  first key, and the newly computed key goes into `rung_aliases` (3.5). A re-run that computes the new key finds
  the rung through the alias.

**QIDs are kind-checked.**

* A position key takes only a QID typed *position* or *public office*.
* An agency key takes only an organisation or court item.
* An office type takes only a class or system item, never one member of it.
* A parent's QID goes on the parent's own item, never on the child.

The fixture's `qid_status` already records `parent` and `position` matches. A loader must still test the QID's
class, because `ladders.json` has three errors that `qid_status` marks `exact` (9.2 #5):

* a post carrying its department's QID (`lexflow:position:va:tax_commissioner`, Q116797530);
* an agency carrying a post's QID: `lexflow:agency:tx:office_of_the_attorney_general` carries Q7707525, *Texas
  Attorney General*, which is P31 *position*;
* an office type carrying one court's QID: `lexflow:office-type:md:court_of_disposition` carries Q16932596, the
  Maryland District Court, though the type covers the District Court and the circuit courts.

### 1.4 Structural and standing relations (`entity_links`)

Every row carries the existing grounding columns of entity-contacts 1.3: `act_id`, `section`, `start`, `end`,
`quote`, `method`, `status` and `checked_at`. A row read from Wikidata also records the entity URL, the statement
GUID, its rank and the retrieval date in `context`. One new column, `valid_until`, holds a statutory end date read
from the text. For example, Cal. BPC § 7000.5(c) and § 7011(e) are each repealed "as of" January 1, 2029, so the
CSLB `part-of` edge and the registrar's `position-in` edge carry that date (5.6 re-reads such clauses).

| Relation | Subject → object | Wikidata | Made from | Grounded example |
|---|---|---|---|---|
| `part-of` (planned) | agency or unit → agency or government root | P749, with P361 as evidence | statute, Wikidata exact items, curated | "There is in the Department of Consumer Affairs a Contractors State License Board, which consists of 15 members." (Cal. BPC § 7000.5(a)) |
| `headed-by` | agency → position | P2388 (inverse P2389) | statute; Wikidata, **always reviewed** (the Virginia Department of Taxation's P2388 names the supervising cabinet secretary) | "The head of the Department of State is the Secretary of State." (Fla. Stat. § 20.10(1)) |
| `position-in` | position → agency | P2389 for heads; otherwise P361 | statute, curated | "The registrar shall be the executive officer and secretary of the board" (Cal. BPC § 7011(b)) |
| `appointed-by` | position → position or agency | P748 | statute | "The Secretary of State shall be appointed by the Governor, subject to confirmation by the Senate, and shall serve at the pleasure of the Governor." (§ 20.10(1)) |
| `reports-to` | position → position | P10645 (used by 0 of 174 corpus posts) | statute, curated | |
| `supervised-by` | agency → agency or position | none; P797 *authority* is only a lead, never accepted on its own | statute | "such officer or board generally remains subject to oversight, direction, and supervision by the Governor" (Fla. Stat. § 20.02(3)) |
| `designee-of` | position type → position or position type | P2098, loosely | text such as "or a designee" or "the person therefor designated" | "the head of the agency or a designee" (Cal. Gov. Code § 7922.535(b)) |
| power grant | agency, position, office type or position type → `lexflow:power:<slug>` | none | statute (3.1). Stored in `power_grants`, **not** in `entity_links`, whose key would merge a power and a disability over the same thing. | "a board may deny a license … only if" (Cal. BPC § 480(a)) |
| `successor-of`, `played-by`, `mentions`, `instance-of`, `serves` | as in entities-contacts 1.4 | | | |

These rules apply to every relation:

* A structural edge describes the organisation. It is never shown as a remedy (3.8).
* `status` is `proposed` until a person accepts it.
* The P797 and P2388 leads are never accepted automatically.

### 1.5 Tables

One new synced table for posts. It has an entry in `SYNCED`, and `state`, `updated_at` and `origin` columns, like the
tables in entities-contacts 1.3. It merges the `positions` table of authority-wikidata 7.3 and the `posts` table of
authority-standards 4.3.

```sql
CREATE TABLE IF NOT EXISTS positions (
  key TEXT PRIMARY KEY,            -- lexflow:position:fl:secretary_of_state | lexflow:position-type:ny:foil_appeals_officer
  state TEXT NOT NULL,             -- fl | … | us
  scope TEXT NOT NULL,
  name TEXT NOT NULL,              -- "Secretary of State of Florida"; a type keeps the statute's words
  kind TEXT NOT NULL,              -- position | position-type
  role TEXT,                       -- head | officer | board | hearing-officer | counselor | designee | other
  body_key TEXT,                   -- the agency it sits in (mirrors the position-in link); NULL for a type
  applies_to TEXT,                 -- for a type: agency | public-body | board | court | any
  relative TEXT,                   -- for a type: head-of | governing-body-of | officer-of | designee-of (of the decider)
  selection TEXT,                  -- elected | appointed | ex-officio | civil-service | unknown
  wikidata TEXT, wikidata_match TEXT,   -- a position or public-office item only; exact | none
  aliases TEXT, status TEXT DEFAULT 'active',      -- active | abolished
  start_date TEXT, end_date TEXT,  -- when the post was created or abolished, never anyone's tenure
  valid_until TEXT,                -- a statutory sunset of the words that create the post (BPC § 7011(e): 2029-01-01)
  act_id TEXT, section TEXT, quote TEXT,           -- the words that create or name the post
  source TEXT, source_url TEXT, checked_at TEXT,
  updated_at TEXT NOT NULL, origin TEXT
);
-- deliberately absent: holder, holder_qid, tenure dates, any contact column
```

**New columns on `agencies`** (entities-contacts 1.3):

| Column | Values | Why |
|---|---|---|
| `standing` | `organisation` or `unit` | ORG's FormalOrganization against OrganizationalUnit; it decides whether contacts and remedies belong to the unit or to its parent |
| `branch` | executive, legislative, judicial or independent | scope rules turn on it. D.C. § 2-537(a-1) sends Council records straight to court, and 5 ILCS 140/9.5(a) excludes the General Assembly |
| `remit` | subject matter | review bodies whose jurisdiction is a topic, not a place (LegalRuleML: jurisdiction "or subject matter") |
| `ocd_division` | an OCD division id | crosswalk only |

The procedural tables, `rungs` and `rung_aliases`, are in 3.5. The `power_grants` table is in 3.1. All three are
synced in the same way.

### 1.6 Provenance

| Source | What is kept | Where it shows |
|---|---|---|
| Statute | `act_id` (the stable open-us-law key), section and pinpoint, character offsets, the verbatim quote (at most 400 characters), and the index version (open-us-law v2026.09.1) | On every structural edge, power and rung. On Wikibase as `P13 references` to the statute item, with a `P22 citation` qualifier holding the words. |
| Wikidata | QID, statement GUID, rank, P580/P582, the statement's own references, and `retrieved_at` | As Wikibase references: *reference URL* (the entity), *retrieved*, *determination method* = "from Wikidata, reviewed" (entities-contacts 1.7) |
| Curated | file and model id, and the reviewer as a role ("reviewer", "two-agent") | `method='curated'` |
| Reviewer decision | `status`, `method`, `checked_at`, `verified_by` (a role, never a name) | kept across re-runs by `db.upsert(keep=…)` |
| Inference | the reader's note, as in the fixture's `inferred` list | shown to reviewers. Never published as fact; the rung says "the statute does not name the forum". |

### 1.7 Office holders

The rule:

* **Nothing about a holder is stored.** That covers the DB, the fixtures, the wiki, the Wikibase and the logs.
  Office-holder claims (P1308, P39, and the person-valued "led by" claims P488, P169, P1037 and P3975) are dropped
  when a Wikidata response is parsed, as entities-contacts 5.4 requires. 5.4 also drops P2388 and P1313; this
  design keeps those two, because their values are posts, and makes posts first-class rows (A15).
* **Showing a current holder is off by default.** If you ever turn it on:
  * it is allowed only on the dashboard, never on a DokuWiki page or in the Wikibase. DokuWiki pages are rendered
    and stored, so a name shown there would be kept;
  * it is read live from Wikidata when the dashboard page renders, and never cached or logged;
  * it is shown only for posts typed *public office*, *elective office* or *position*;
  * it uses only non-deprecated P39 statements that have a P580 and no P582;
  * a name is shown only when exactly one such statement exists. Otherwise the page says "Wikidata does not give a
    single current holder".
  * the label reads "according to Wikidata, since <P580>", with no contact detail and no link other than the
    post's Wikidata item.
* **Why the default is off.** The holder data does not support it:
  * the Secretary of State of California has 6 holder statements with no end date, and the President of the United
    States has 18;
  * the 13 posts checked carry 286 holder statements, of which only 112 have a start date and 103 an end date;
  * the Florida Secretary of State post (Q7444366) carries 27 holder statements (counted here, names not read).

  Processes need the office in any case: "the head of the agency or a designee".
* **Statutes that ask for a person to be named** are met with the post. Four do: Cal. Gov. Code § 7922.540(b), 5
  ILCS 140/9(a), Fla. Stat. § 119.07(1)(b) and Va. Code § 2.2-4019(A) (authority-ladders 5.3).

---

## 2. How a process cross-references them

### 2.1 The chain

```
process ──P10 has part──▶ step ──bearer (P17)────▶ role ──played by──▶ agency | unit | office type | position | position type | private party
                           │   └──recipient (new)──▶ role ──played by──▶ …
                           │
                           └◀──follows (P11)── rung ──addressed to──▶ body / post / court / another process / a status
                                                │   ├─ condition (P18) ──▶ trigger (denied, deemed denied, refused filing …)
                                                │   └─ references (P13) ──▶ statute item, with the words (P22)
                                                └─ followed by (P12) ──▶ next rung

role ──role of actor──▶ defined term ──concept──▶ concept                            (terms-wikibase)
unit ──parent organization──▶ agency ──parent organization──▶ … ──▶ government root
agency ──head position──▶ position ──appointed by──▶ position (for example the Governor)
agency | position ──authority conferred by──▶ statute item   {power, modality, the words}
```

* **Every step reaches a body in two hops.** The step's bearer and recipient are roles, and each role is played by
  a body, unit, office type, post or post type.
* **Every body reaches its government in a few more.** The parent chain runs up to the government root.
* **The rung is the authority link.** It is the only edge that says a matter may or must go somewhere else, and it
  carries its own statute words.

### 2.2 Resolving a generic actor through the statute's context

This extends entities-contacts 1.5. The resolver tries these in order and records the rule that fired in
`entity_links.context`:

1. **A defined term in scope.**
   * Cal. BPC § 477(a), scope Division 1.5, reads: "“Board” includes “bureau,” “commission,” “committee,”
     “department,” “division,” “examining committee,” “program,” and “agency.”"
   * Cal. BPC § 22 sets the code-wide rule for which board is meant: "“Board,” as used in any provision of this
     code, refers to the board in which the administration of the provision is vested". `terms.definitions()`
     extracts § 477 but not § 22, because "refers to" is not one of its definition forms (9.2).
2. **A full name earlier in the same section or model.** For example, "the State Corporation Commission … the
   Commission".
3. **The question's default player.** For records, the government the user picked; for business, the state filing
   office.
4. **An office-type instance chosen by `resolve_by`.** The rule is one of `profession`, `venue`, `county_of_place`,
   `record_holder` or `appellate_district`.
5. **A post type resolved relative to the decider.**
   * `head-of` follows the deciding body's `headed-by` link.
   * `designee-of` keeps the statute's words ("or a designee").
   * When no post is known, the type's own label is shown: "the head of the agency that denied your request". It
     never falls through to a person.
6. **Unresolved.** The mention is shown as a role, with its office type's `parent_hint` contacts labelled as that
   body's.

### 2.3 Worked example: Florida incorporation (Fla. Stat. §§ 607.0201–607.0202)

The texts (lexflow index, open-us-law v2026.09.1):

* § 607.0201: "One or more persons may act as the incorporator or incorporators of a corporation by delivering
  articles of incorporation to the department for filing."
* § 607.0202(1)(e): the articles must set forth "The name and address of each incorporator."
* § 607.01401: "“Department” means the Florida Department of State."
* § 20.10: "There is created a Department of State." Subsection (2) lists the divisions: "(c) Division of
  Corporations."
* § 607.0125(1): "If a document delivered to the department for filing satisfies the requirements of s. 607.0120,
  the department shall file it." Subsection (4): "The department’s duty to file documents under this section is
  ministerial."
* § 607.0125(3): "If the department refuses to file a document, the department shall return the document … within
  15 days after the document was received for filing, together with a brief, written explanation of the reason for
  refusal."
* § 607.0123(3): "If the applicant returns the document with corrections in accordance with the rules of the
  department within 60 days after it was mailed to the applicant by the department and if at the time of return
  the applicant so requests in writing, the filing date of the document will be the filing date that would have
  been applied had the original document not been deficient". The LLC route has the same rule in § 605.0210(4).
* § 607.0126: "If the department refuses to file a document delivered to its office for filing, the person who
  submitted the document for filing may petition the Circuit Court of Leon County to compel filing of the document."
  It ends: "The court’s final decision may be appealed as in other civil proceedings."
* § 205.023: the local business tax receipt needs "either" (1) "A copy of the applicant’s or new owner’s current
  fictitious name registration, issued by the Division of Corporations of the Department of State", or (2) "A
  written statement, signed by the applicant or new owner, which sets forth the reason that the applicant or new
  owner need not comply with the Fictitious Name Act."

| Model element | Key | Resolves to | Grounding and source |
|---|---|---|---|
| actor *incorporator* (in a corporation-route model; the reviewed `fl.business` model follows the LLC route, whose founder is Lexipedia Q775 `lexflow:role:fl:business:organizer`) | `lexflow:role:fl:business:incorporator` | term `lexflow:term:fl:607.0201:incorporator` (kind `acts_as`, scope ch. 607, as `terms.definitions()` returns it) → concept `lexflow:concept:incorporator` → **played by `lexflow:private-party`** | § 607.0201. The articles name each incorporator (§ 607.0202(1)(e)), but lexflow never looks up or stores who that is (entities-contacts D5). |
| actor *the department* | `lexflow:role:fl:business:department` (Q776) | **legal holder of the duty:** term `lexflow:term:fl:607.01401:department` → `lexflow:agency:fl:department_of_state` (Q11969252). **Operating unit:** `lexflow:agency:fl:division_of_corporations` (Q107179384), `standing='unit'`. The role is `played-by` the unit, as entities-contacts 1.1 already has it, so contacts come from the unit. | § 607.01401; § 20.10(2)(c) |
| unit → department | `part-of` | Division of Corporations → Department of State | § 20.10(2)(c). Wikidata agrees (P749 and P361). |
| department → head | `headed-by` | `lexflow:position:fl:secretary_of_state` (Q7444366, P31 *public office*) | § 20.10(1). **Wikidata has neither direction**: Q11969252 has no P2388, and Q7444366 has no P2389. |
| head → appointer | `appointed-by` | `lexflow:position:fl:governor` (Q20198851) | § 20.10(1); § 20.02(3) for the Governor's supervision. Wikidata has no P748 on Q7444366. |
| department → root | `part-of` | `lexflow:agency:fl:government` (Q3112589) | Wikidata has no P749 on Q11969252. |
| powers | power grants (3.1) | the department: `file`, a **duty** (Obligation), ministerial, conditioned on § 607.0120. The court: `order-filing`, a **power**. | § 607.0125(1), (4); § 607.0126 |
| rung 1 | `lexflow:rung:fl:business:607.0123-3:corrected-refiling` | internal appeal (the fixture's type for the LLC counterpart, `fl.business.1`), relation `returns-to`, direction `return`: back to the department, which files the corrected document under its original date | Trigger `refused_filing`. **60 days** after the department mailed the document back, with a written request at the time of return; the original date does not hold "as to persons who relied on the record before correction and were adversely affected thereby". An alternative to rung 2, not a step that must come first. |
| **rung 2** | `lexflow:rung:fl:business:607.0126:court-petition` | judicial review, `escalates-to` the circuit court sitting for Leon County (`lexflow:agency:fl:circuit_court_leon_county`, labelled "Circuit Court of the Second Judicial Circuit (Leon County)"; Q7443383, which Wikidata labels "Second Judicial Circuit Court of Florida", an `exact` match) | Trigger `refused_filing`. Invoker: "the person who submitted the document for filing", which may be the incorporator or anyone who delivered the document. **Time limit: none stated.** Exhaustion: none. Attachments: "The document and the explanation from the department of the refusal to file must be attached to the petition." |
| rung 3 | `…:607.0126:civil-appeal` | judicial review, to a district court of appeal (`resolve_by: appellate_district`) | "as in other civil proceedings". The district is not named, so the rung carries an `inferred` note, as the fixture's LLC ladder does. |
| rung 4 | `…:205.023:registration-prerequisite` | deferral to another process: the local business tax receipt waits on the Division's fictitious-name registration, **only for a business that must register a fictitious name**. Any other applicant gives a signed statement instead (§ 205.023(2)), so the rung carries a `scope_rule`. | the fixture's `fl.business` rung 5 (§ 205.023), whose subtype already says "(or a signed statement)" |
| **not a rung** | – | the Secretary of State, the Governor | Nothing in chapter 607 gives either a power to review a refusal. They appear only as the chain of authority. |

Two things the model now makes visible:

* **The corporation and LLC routes match on corrections.** § 607.0123(3) gives a corrected corporate filing the
  same 60-day return and original date that § 605.0210(4) gives an LLC filing. So a corporation-route ladder can
  copy that LLC rung, citing chapter 607's own section.
* **The refusal limit has no consequence.** The 15-day limit binds the department, but the statute sets no effect
  if it is missed. So there is no deemed outcome and no timer path to court; the dashboard says "the statute sets
  no consequence".

### 2.4 Worked example: Cal. Bus. & Prof. Code § 480 (the licensing board of the profession)

§ 480(a): "Notwithstanding any other provision of this code, a board may deny a license regulated by this code on
the grounds that the applicant has been convicted of a crime or has been subject to formal discipline only if
either of the following conditions are met".

This ladder comes from an AskBench reference answer (`curated_ask/license_conviction/ca.json`), not from a reviewed
process model. Lexipedia has no `lexflow:process:ca.license_conviction` item (checked 2026-10-10). So, under A7, its
rungs live in the DB and the tests, and reach the wiki only once a reviewed model exists for the question.

**From "a board" to a body and its chain.**

| Element | Key | Resolves to | Grounding |
|---|---|---|---|
| "a board" | role `lexflow:role:ca:license_conviction:board` | defined term `lexflow:term:ca:Cal. BPC § 477:board` (scope Division 1.5) and the § 22 rule → office type `lexflow:office-type:ca:licensing_board` (`resolve_by: profession`, `parent_hint` DCA) | § 477(a); § 22 |
| the instance for a contractor | `lexflow:agency:ca:contractors_state_license_board` | Q5020359 (P31 *state licensing board*) | § 480(a)(1)(B)(ii) names "Chapter 9 (commencing with Section 7000) of Division 3", the Contractors State License Law (§ 7000) |
| board → department | `part-of` | `lexflow:agency:ca:department_of_consumer_affairs` (Q5020410) | "There is in the Department of Consumer Affairs a Contractors State License Board" (§ 7000.5(a)). **Wikidata lacks this P749.** Section 101 lists the department's boards and bureaus; § 108 says each board "exists as a separate unit". The section is repealed on January 1, 2029 (§ 7000.5(c)), so the edge carries `valid_until`. |
| department → agency | `part-of` | Business and Consumer Services Agency (Q136668814) | "There is in the state government, in the Business and Consumer Services Agency, a Department of Consumer Affairs." (§ 100(a), operative July 1, 2026 under (b)). Wikidata agrees. |
| agency → root | `part-of` | `lexflow:agency:ca:government` (State of California, Q5589189) | Wikidata P749 |
| board's executive officer | `lexflow:position:ca:registrar_of_contractors`, `position-in` the board, `appointed-by` the board | | "The board, by and with the approval of the director, shall appoint a registrar of contractors" (§ 7011(a)). Repealed on January 1, 2029 (§ 7011(e)), so the post's edges carry `valid_until`. |
| the director | `lexflow:position:ca:director_of_consumer_affairs`, `headed-by` from the department | no Wikidata post item was found | |
| the hearing officer | `lexflow:position-type:ca:administrative_law_judge`, `position-in` `lexflow:agency:ca:office_of_administrative_hearings` | the OAH has no item of its own; Q5020423 is its parent, General Services | defined in Gov. Code § 11500(d); appointed by the OAH director (§ 11502(b)) |
| "a board" in another profession | the same office type | its own instance. The parent comes from that instance's own statute, never from the office type: the office type's DCA link is only a `parent_hint`. | § 101 lists the department's boards and ends with "(am) Any other boards, offices, or officers subject to its jurisdiction by law." |

**Powers** (power grants, 3.1):

* **The board.**
  * A conditional *power* to deny (§ 480(a)).
  * *Disabilities* in § 480(b)–(d): "shall not be denied" after a certificate of rehabilitation, a dismissal, or
    an arrest that did not end in a conviction.
  * A non-delegable *power* to reconsider. Gov. Code § 11521(a) says "The agency itself may order a
    reconsideration". Gov. Code § 11500(a) says that "wherever the words “agency itself” are used the power to act
    shall not be delegated unless the statutes relating to the particular agency authorize the delegation".
* **The OAH.** A *duty* to provide the judge: "All hearings of state agencies required to be conducted under this
  chapter shall be conducted by administrative law judges on the staff of the Office of Administrative Hearings."
  (§ 11502(a)). The board still chooses the route. "A contested case may be originally heard by the agency itself
  … Alternatively, at the discretion of the agency, an administrative law judge may originally hear the case alone"
  (Gov. Code § 11517(a)). When the board hears it, the judge "shall be present … and, if requested, shall assist
  and advise the agency" (§ 11517(b)(1)).
* **The DCA director.**
  * A *disability* to review: "The decisions of any of the boards comprising the department with respect to setting
    standards, conducting examinations, passing candidates, and revoking licenses, are not subject to review by the
    director, but are final within the limits provided by this code which are applicable to the particular board,
    except as provided in this section." (§ 109(a)). The section lists four kinds of decision. A denial under § 480
    fits only as "passing candidates" (compare § 108, "passing upon applicants"). That reading is sound, but it is a
    reading, so the grant carries an `inferred` note naming the four kinds.
  * A *power* to investigate misconduct "in the review of qualifications which are a part of the licensing process
    of any board" (§ 109(b)), and to "investigate the work of the boards in the department" (§ 153).
  * A *power* to intervene: "The director may intervene in any matter of any board where an investigation by the
    Division of Investigation discloses probable cause to believe that the conduct or activity of a board, or its
    members or employees constitutes a violation of criminal law" (§ 109(c)). Intervening may include a
    restraining order, an injunction or a referral for prosecution. It is an oversight power, not a review of the
    applicant's case.

**The ladder** (from `ladders.json`, `ca.license_conviction`, 8 rungs; all quotes verified in the fixture):

| # | Type (relation) | Section | Addressed to | Time limit | Must it come first? |
|---|---|---|---|---|---|
| 1 | internal appeal (`escalates-to`) | BPC § 485(b) | the board (APA hearing) | 60 days after service of the notice of denial; otherwise "the applicant’s right to a hearing is deemed waived" | **yes**, for the hearing route (`mandatory` in the fixture) |
| 2 | delegation (`delegates-to`) | Gov. § 11502(a) | OAH administrative law judge | hearing within 90 days (§ 487). The rest turns on the route the board picks (§ 11517(a)), so these deadlines carry a `scope_rule`. **Judge alone** (subdivision (c)): a proposed decision within 30 days, a directory limit, because a late one "does not prejudice the rights of the agency" ((c)(1)); the board acts within 100 days of receiving it, or it is deemed adopted ((c)(2)). **The board itself, with the judge present** ((b)): "The agency shall issue its decision within 100 days of submission of the case", and the statute deems no outcome. | duty of the board; the route is the board's choice |
| 3 | internal appeal (`escalates-to`) | Gov. § 11521(a) | the board itself (non-delegable) | the power "shall expire 30 days after the delivery or mailing of a decision", or sooner on an effective date the board sets. The board may stay the expiry by up to 30 days to allow a petition, and by up to 10 days more to consider one filed in time; a petition not acted on in time "shall be deemed denied". The deadline record carries these as `extensions` (3.5). | **no**: "The right to petition shall not be affected by the failure to seek reconsideration before the agency." (§ 11523) |
| 4 | judicial review (`escalates-to`) | Gov. § 11523 | superior court (`resolve_by: venue`), writ of mandate | "within 30 days after the last day on which reconsideration can be ordered", extended if the record is requested within 10 days | – |
| 5 | referral (`refers-to`) | BPC § 480(f)(3)(D) | Department of Justice (Q5020429), record correction under Penal Code §§ 11122–11127 | – | duty to describe the route in the notice |
| 6 | deferral (`defers-to`) | BPC § 480(b) | the certificate-of-rehabilitation court process (Penal Code § 4852.01 et seq.; no model yet) | – | no |
| 7 | deferral (`defers-to`) | BPC § 480(c) | process `ca.record_sealing`, status `lexflow:status:ca:conviction-dismissed` (bpc-480 6.1) | – | no |
| 8 | internal appeal, subtype reapplication (`returns-to`, direction `return`) | BPC § 486(a) | the board, as a new application after a minimum wait, not a review of the denial | "The earliest date on which the applicant may reapply for a license which shall be one year from the effective date of the decision, or service of the notice under subdivision (b) of Section 485, unless the board prescribes an earlier date or a later date is prescribed by another statute." | – |

**Scope.** "This section does not in any way modify or otherwise affect the existing authority of the following
entities in regard to licensure": the State Athletic Commission, the Bureau for Private Postsecondary Education and
the California Horse Racing Board (§ 480(i)). The § 480 power grants (the conditional power to deny and the
disabilities of (b)–(d)) and the § 480 rungs (5, 6 and 7) carry a `scope_rule` that leaves those three deciders
out. For them the resolver says that the body's own statute governs, rather than showing the § 480 limits.

**Not rungs:** the DCA director, the Business and Consumer Services Agency and the Governor.

* § 109(a) says that the director does not review a board's decisions on "setting standards, conducting
  examinations, passing candidates, and revoking licenses", "except as provided in this section". Applying it to a
  § 480 denial reads that denial as "passing candidates". The conclusion is stored with that `inferred` note, and
  the resolver shows "Not reviewed by: the Director of Consumer Affairs (Bus. & Prof. Code § 109(a))".
* § 109(b) and (c) are *oversight channels*, not a review of the decision. They become new candidate rungs of type
  "oversight/inspector general", which the fixture does not have yet. Both are non-binding on the applicant's case:
  under (b) the director's request goes to the Division of Investigation, and under (c) the director may intervene
  on probable cause of a crime.

### 2.5 Queries this enables

* **Which steps of which reviewed processes does a given body act in, or receive?** Bearer or recipient → role →
  played by.
* **Which processes route to a given body or post?** For example, every rung addressed to the Texas attorney
  general.
* **After a given outcome, what is the next body, by when, and must the person go there first?**
* **What is a body's chain of authority up to its government root?** It is labelled as structure.
* **Where does a power sit?** For example, who may extend a records deadline (the head of the agency or a designee
  in CA; the Mayor in DC).
* **Which remedies are optional, and which bodies bind?**

---

## 3. Authority, escalation and deferral

### 3.1 Authority: powers, duties and disabilities

A **power grant** records which body or post holds which legal position over which kind of decision, under which
words. Grants have their own synced table. They cannot be `entity_links` rows: that table's key is (subject,
relation, object, question), so § 480(a) (a power to deny) and § 480(c) (a disability to deny) on the same board
office type would collide, and so would two sections that grant the same power.

```sql
CREATE TABLE IF NOT EXISTS power_grants (
  holder TEXT NOT NULL,            -- an agency, position, office-type or position-type key
  power TEXT NOT NULL,             -- lexflow:power:<slug>
  hohfeld TEXT NOT NULL,           -- power | duty | disability | immunity
  over TEXT NOT NULL DEFAULT '',   -- license_denial | records_denial | filing_refusal | …
  question TEXT NOT NULL DEFAULT '',
  act_id TEXT NOT NULL, section TEXT NOT NULL,     -- the pinpoint, e.g. 480(c)
  state TEXT NOT NULL,
  condition TEXT,                  -- "§ 480(a)(1) or (a)(2) holds"
  delegable INTEGER, designee INTEGER, exclusive INTEGER,
  scope_rule TEXT,                 -- JSON, as on rungs (the § 480(i) carve-out)
  start INTEGER, "end" INTEGER, quote TEXT NOT NULL,
  inferred TEXT,                   -- JSON: a reader's note, e.g. the § 109(a) "passing candidates" reading
  valid_until TEXT,
  method TEXT, score REAL, status TEXT DEFAULT 'proposed',
  checked_at TEXT, updated_at TEXT NOT NULL, origin TEXT,
  PRIMARY KEY (holder, power, hohfeld, over, question, act_id, section)
);
```

* **The power vocabulary** has 17 items: `decide`, `deny`, `file`, `refuse-filing`, `hear`, `review`, `reconsider`,
  `order-disclosure`, `order-filing`, `extend-time`, `rule` (a binding opinion), `advise`, `mediate`,
  `investigate`, `intervene`, `appoint` and `delegate`.
* **The correlatives follow from the grant.** A person's power to invoke a rung meets the decider's liability, and
  the reviewer's power usually comes with a duty to decide in time (authority-standards 2.9).

How the resolver uses grants:

1. **A rung's target must hold a power over the decision.** Either a grant shows it, or the rung's own quote
   confers it ("may petition the Mayor to review"). Otherwise the checker flags the rung.
2. **A disability or a duty to obtain another body's ruling produces a deferral.**
   * Tex. Gov't Code § 552.301(a): a governmental body that wishes to withhold "must ask for a decision from the
     attorney general".
   * Cal. Gov. Code § 7922.535(b): an extension needs written notice from "the head of the agency or a designee".
3. **A negative grant suppresses a structural suggestion and explains why.** The DCA director under § 109(a) is the
   example.

| Holder | Power over | Position | Words (section) |
|---|---|---|---|
| CA licensing board | deny a licence | power, conditional | "a board may deny a license … only if" (BPC § 480(a)) |
| CA licensing board | deny on a dismissed conviction | disability | "a person shall not be denied a license on the basis of any conviction … that has been dismissed" (§ 480(c)) |
| CA Office of Administrative Hearings | hear | duty (by statute); the board may hear the case itself, with a judge present | § 11502(a); Gov. Code § 11517(a)–(b) |
| CA licensing board | reconsider | power, not delegable | Gov. § 11521(a) with § 11500(a) |
| Director of Consumer Affairs | review board decisions on standards, examinations, passing candidates and revocations | **disability**; a § 480 denial is covered as "passing candidates" (an `inferred` note) | BPC § 109(a) |
| Director of Consumer Affairs | investigate | power | BPC § 109(b); § 153 |
| Director of Consumer Affairs | intervene, including by injunction, on probable cause of a crime | power (oversight) | BPC § 109(c) |
| FL Department of State | file | duty, ministerial | Fla. Stat. § 607.0125(1), (4) |
| Circuit Court of Leon County (Second Judicial Circuit) | order filing | power | § 607.0126 |
| TX governmental body | withhold | disability without an AG ruling | Gov't Code § 552.301(a); ask within 10 business days (§ 552.301(b)) |
| CA head of the agency or a designee | extend time (at most 14 days) | power, with designee | Gov. Code § 7922.535(b) |

### 3.2 Mechanism types

These are the ten types of the ladders vocabulary, with their counts in the fixture. They map onto the route kinds
of authority-standards 5.2 and the mechanisms of authority-wikidata 6.3. A type answers "what kind of mechanism"; a
relation (3.4) answers "how the bodies connect". The two are stored separately.

| Type | Rungs | Direction | Usual target | Binding | Standards route kind | Wikidata-note mechanism |
|---|---|---|---|---|---|---|
| judicial review | 45 | escalate | a court office type, `resolve_by: venue` | yes | `judicial_review`, `enforcement` | `judicial-review` |
| referral | 21 | hand-off | the right custodian or holder; a repository; a consulted body | n/a | `referral` (to the right holder), `consultation` | `referral` |
| internal appeal | 20 | escalate; `return` for a corrected refiling or a reapplication | the decider, its head, its full board or a designee | yes | `reconsideration`, `internal_appeal`, `contested_hearing` | `internal-appeal`, `reconsideration` |
| delegation | 14 | hand-off | a designee, officer, panel or hearing office | as the statute says | – (an attribute of the route) | – |
| deferral to another process | 13 | defer | another process, a status, or another body's pending decision | – | `advance_determination`, `extension`, `remand` | `ruling-request` |
| advisory opinion | 8 | inform or advise | a FOIA council, an open-government office, the AG | no (unless a statute makes it binding) | – | `advisory-review` |
| oversight / inspector general | 8 | inform | an IG, ombuds, prosecutor or appointing authority | no | `notice_to_overseer` | `notification`, `oversight-complaint` |
| external administrative review | 8 | escalate | a different administrative body (the D.C. Mayor, the TX AG, the IL Public Access Counselor) | yes | `external_review` | `hierarchical-appeal`, `administrative-review` |
| ombudsman / mediation | 4 | escalate, non-binding | an ombudsman or mediator | no | – | `mediation` |
| compliance board | 2 | escalate | a standing board that decides and orders | yes | `external_review` | – |

Type and relation are read separately, and the checker (3.7) matches on the fixture's type. Two cases show why:

* **Tex. Gov't Code § 552.301.** The fixture types `tx.records.2` as external administrative review, with
  `mandatory: true`: the attorney general decides, and the decision binds. Its relation is `defers-to`, because the
  body must ask and then wait for the ruling. The deriver keeps the fixture's type and sets the relation.
* **Cal. BPC § 486(a) and Fla. Stat. § 605.0210(4).** The fixture types both as internal appeals. Neither reviews
  the decision: one is a new application after a minimum wait, the other a corrected refiling. They keep the type,
  with the relation `returns-to` and the direction `return`.

### 3.3 Triggers and deemed outcomes

* **Triggers.** The fixture uses 25 trigger codes. The most common are `denied` (42 rungs), `any` (21), `partial`
  (17), `fee` (13), `adverse_ruling` (13), `appeal_denied` (12), `deemed_denied` (11), `prerequisite` (9), `delay`
  (8), `court_lost` (8), `no_answer` (8) and `refused_filing` (6). Each becomes a vocabulary item, which a rung
  points at with `P18 condition`.
* **Deemed outcomes are triggers, not rungs.** A deemed outcome is recorded on the deadline that causes it, and it
  opens the next rung. The corpus handles silence in five ways:

  | Outcome | Where |
  |---|---|
  | deemed denial | VA, DC, NY, IL; MD for late production |
  | deemed exhaustion | DC § 2-532(e); IL |
  | presumption of disclosure | TX § 552.302, when the body misses its deadline to ask the AG |
  | deemed approval | Va. Code § 2.2-4021(B) |
  | nothing | Cal. CPRA; Fla. ch. 119 |

  A deemed adoption (Cal. Gov. § 11517(c)(2), on the judge-alone route only) and an overruling by operation of law
  (Tex. Gov't § 2001.146(c)) are further consequence values. Both are in the lapse-consequence vocabulary (5.3).
* **One schema gap.** `FDeadline.consequence` has no `deemed-approval`. The rung layer reads the reference answers'
  `on_miss` until the schema thaws after AskBench.

### 3.4 Edges

Each edge is grounded in a section, a verbatim quote and, where the statute gives one, a time limit. All quotes below
are from `ladders.json`, where a script found every one verbatim in the section text.

| Relation | Meaning | From → to | Types | Grounded example (section: words; time limit) |
|---|---|---|---|---|
| `escalates-to` | the matter goes to a body with power to change the decision | the invoker's matter → reviewer | internal appeal, external review, compliance board, judicial review | N.Y. Pub. Off. Law § 89(4)(a): "any person denied access to a record may within thirty days appeal in writing such denial to the head, chief executive or governing body of the entity". 30 days to appeal; 10 business days to decide, a miss counting as a denial. |
| `reviews` | the reviewer's side of an escalation, as a standing jurisdiction: reviewer → the bodies it reviews | body → body, office type or class | external review, compliance board | D.C. Code § 2-537(a): "any person denied the right to inspect a public record of a public body may petition the Mayor to review the public record to determine whether it may be withheld from public inspection". 10 business days. |
| `hears-appeals-from` | a court's standing jurisdiction over a body's decisions; the inverse of Wikidata P12452 *appeals to*, for unconditional cases only | court → body | judicial review | Fla. Stat. § 607.0126: "may petition the Circuit Court of Leon County to compel filing of the document". No time limit. |
| `mediates` | a neutral tries to settle the dispute and cannot compel | → ombudsman or mediator | ombudsman / mediation | Md. Code, Gen. Prov. § 4-1B-04(a): "the Ombudsman shall make reasonable attempts to resolve disputes between applicants and custodians relating to requests for public records under this title". 90 days to a final determination. |
| `advises` | a non-binding opinion | → adviser | advisory opinion | Va. Code § 30-179(1): "Furnish, upon request, advisory opinions or guidelines, and other appropriate information regarding the Virginia Freedom of Information Act". No time limit. |
| `refers-to` | the matter, a notice or a record goes to the right holder | decider or receiver → holder | referral | Md. Code, Gen. Prov. § 4-202(c): "If the individual to whom the application is submitted is not the custodian of the public record, within 10 working days after receiving the application, the individual shall give the applicant" (the custodian's details). |
| `delegates-to` | a body's function is carried out by a designee, officer, panel or hearing office | decider → delegate | delegation | Cal. Gov. Code § 11502(a), quoted in 3.1. Hearing within 90 days (BPC § 487). |
| `defers-to` | the decider must wait for, or the outcome turns on, another body's ruling or another process | decider or step → body, process or status | deferral to another process; external administrative review where the decider must obtain the ruling (Tex. § 552.301, 3.2) | Tex. Gov't Code § 552.301(a): "must ask for a decision from the attorney general about whether the information is within that exception". 10 business days to ask (§ 552.301(b)); on a miss, the information is presumed public (§ 552.302). Also Cal. BPC § 480(c) → `ca.record_sealing`. |
| `returns-to` | a new submission to the same decider: a corrected refiling, or a reapplication after a minimum wait. It is not a review of the decision. | the invoker → the decider | internal appeal (the fixture's type), with direction `return` | Fla. Stat. § 605.0210(4): "If the applicant returns the document with corrections in accordance with the rules of the department within 60 days after it was mailed to the applicant by the department". 60 days. Cal. BPC § 486(a): "The earliest date on which the applicant may reapply for a license". A minimum wait of one year by default. |
| `requires-approval-of` | a higher post must sign off | decision or step → post or post type | delegation (the fixture's type) | Cal. Gov. Code § 7922.535(b): "may be extended by written notice from the head of the agency or a designee to the person making the request". At most 14 days. |
| `notifies` | an oversight body is told; nothing waits | decider → overseer | oversight | N.Y. § 89(4)(a): "each agency shall immediately forward to the committee on open government a copy of such appeal when received by the agency and the ensuing determination thereon." |
| `oversight-by` | complaint, discipline or enforcement by an overseer, not a review of the case | → IG, ombuds, prosecutor or appointing authority | oversight / inspector general | Md. Code, Gen. Prov. § 4-362(e)(1): "the court shall send a certified copy of its finding to the appointing authority of the custodian". Tex. § 552.3215(e): the district or county attorney decides within 31 days. |

`reviews` and `hears-appeals-from` are the target-side views. They are computed from accepted `escalates-to` rungs
when a body page needs "Decisions this body reviews", and they are stored only when the jurisdiction is standing and
unconditional. Only those few cases are proposed upstream as P12452.

### 3.5 The rung record

One synced table. It merges the ladders' rung fields with the route fields of authority-standards 5.3 and the
qualifiers of authority-wikidata 7.2. Structural rungs are never stored: the resolver computes them and labels them.

```sql
CREATE TABLE IF NOT EXISTS rungs (
  key TEXT PRIMARY KEY,            -- lexflow:rung:ca:license_conviction:gov-11523:writ-of-mandate
  state TEXT NOT NULL, question TEXT NOT NULL,
  model_id TEXT,                   -- ca.license_conviction (the DB model id form), when bound to a model
  steps TEXT,                      -- JSON: model step ids it binds to (the fixture's model_ref)
  after TEXT,                      -- JSON: step, decision, outcome or rung keys whose result it follows
  type TEXT NOT NULL,              -- one of the ten (3.2)
  subtype_code TEXT NOT NULL,      -- from the closed code list (1.3): writ-of-mandate; part of the key
  subtype TEXT,                    -- free-text description: "petition for a writ of mandate"; never part of the key
  relation TEXT NOT NULL,          -- escalates-to | delegates-to | defers-to | refers-to | returns-to | mediates | advises | notifies | requires-approval-of | oversight-by
  direction TEXT NOT NULL,         -- escalate | defer | hand-off | inform | return
  trigger_codes TEXT NOT NULL,     -- JSON list (3.3)
  trigger_basis TEXT,              -- JSON source of a deemed outcome ("shall constitute a denial")
  invoked_by TEXT,                 -- the role holding the power, or 'decider' for a duty of the body
  target TEXT,                     -- agency | office-type | position | position-type | lexflow:process: | lexflow:status: key
  target_rule TEXT,                -- JSON for relative targets: {"rel":"head-of","of":"decider","or":"designee"} | {"resolve_by":"venue"}
  scope_rule TEXT,                 -- JSON: when it applies, e.g. {"decider.branch":{"not":"legislative"}} (5 ILCS 140/9.5(a)),
                                   --   {"decider":{"not_in":[the three bodies of BPC § 480(i)]}}, {"route":"alj-alone"} (§ 11517(c))
  deadlines TEXT,                  -- JSON list: amount, unit, anchor, who_must_act, kind, consequence, directory (a late act
                                   --   keeps its effect, as in § 11517(c)(1)), extensions (stays and their caps, as in
                                   --   § 11521(a)), scope_rule, section, quote, verified
  exhaustion TEXT NOT NULL DEFAULT 'unknown',  -- required | optional | alternative | constructive | none | unknown
  mandatory INTEGER,               -- the fixture's flag: a duty of the body, or a step the person must take to keep the next rung
  binding TEXT NOT NULL DEFAULT 'unstated',    -- binding | advisory | none | unstated
  powers TEXT,                     -- JSON: affirm | reverse | order_disclosure | order_filing | remand | binding_opinion | …
  next TEXT, alternative_to TEXT,  -- JSON rung keys
  act_id TEXT, section TEXT NOT NULL, quote TEXT NOT NULL,
  supporting TEXT, inferred TEXT, xref_links TEXT,   -- JSON
  basis TEXT NOT NULL,             -- statute | inherited (an APA ladder reached through a procedure reference) | oversight
  method TEXT,                     -- fixture | curated-facts | xref | mentions | cue | reviewer
  score REAL, status TEXT DEFAULT 'proposed',        -- proposed | accepted | rejected
  valid_until TEXT,                -- a statutory sunset of the section (1.4)
  updated_at TEXT NOT NULL, origin TEXT
);

CREATE TABLE IF NOT EXISTS rung_aliases (
  alias TEXT PRIMARY KEY,          -- a key the deriver computes today, after a corrected pinpoint or code
  key TEXT NOT NULL,               -- the rung's first key, which never changes
  reason TEXT,                     -- pinpoint corrected | code corrected
  state TEXT NOT NULL, updated_at TEXT NOT NULL, origin TEXT
);
```

Rules for the record:

* **Keys are computed, never typed** (1.3). The deriver looks a computed key up in `rungs`, then in
  `rung_aliases`, before it inserts.

* **No quote, no rung.** The quote must be verbatim within the cited section, and is checked like every other link
  (`lex_checks`, `validate.py`).
* **Text only.** `exhaustion`, `binding` and every deadline come from the text, or stay `unknown` or `unstated`.
  The ladders' `mandatory` flag is kept, but exhaustion is a separate reading. Cal. BPC § 485(b) makes the hearing
  request mandatory for the hearing route, while Gov. Code § 11523 makes reconsideration optional before court.
* **Re-runs keep decisions.** Re-derivation writes with `upsert(keep=…)`, so a reviewer's `status`, `exhaustion`,
  `binding` and `target` survive.
* **The view.** A SQL view, `authority_edges`, unions accepted rungs (subject = the decider's player, object = the
  target's key) with the structural `entity_links` and the accepted `power_grants`. Graph queries and the Wikibase
  loader read from it.

### 3.6 Deriving ladders automatically

Deterministic first, with no model calls, and starting from the 22 reviewed models and the 15 reference answers
that have steps. For each `(state, question)`:

1. **Candidates from steps.** A candidate is:
   * a step whose bearer differs from the decider, whose recipient is a public actor, whose kind is `filing`,
     `hearing` or `review`, and whose predecessor is a decision, a denial notice or a deemed-outcome timer;
   * or a step where the decider itself sends the matter elsewhere (forward, notify, ask for a decision).

   The step's quote becomes the rung's quote. authority-standards counted 24 + 24 such steps, a heuristic count.
2. **Triggers from deadlines.** A `deemed-denial` consequence, or a deemed `on_miss`, becomes a trigger. Words such
   as "deemed to have exhausted" or "shall constitute final agency action" set `exhaustion: constructive`.
3. **Cross-references with their roles.** `lexflow/law/xref.py` labels each reference in the model's sections:
   * **`procedure`** to a review chapter makes that chapter's ladder apply, recorded with `basis: inherited`. For
     example, BPC § 485 cites "Chapter 5 (commencing with Section 11500) …" of the Government Code, so the APA's
     hearing, reconsideration and writ rungs apply.
   * **`prerequisite_process`** proposes a `defers-to` rung to the producing process or status, through the
     bpc-480 6.2 link schema. In § 480, 18 references carry this role, including PEN §§ 1203.4–1203.425 and
     § 4852.01.
   * **`authority`** proposes a *power grant*, never a rung. In this pass the role fired on two PEN § 290
     references in § 480, which are scope references, and missed "regulations adopted by the board" (9.2). The
     gold files hold 81 `authority`, 96 `procedure` and 76 `prerequisite_process` references, and the classifier
     gets about 70 % of roles right.
4. **Bodies named in words.** Only 13 of the 143 rungs cross-reference another rung's section. The rest name the
   next body in words: "petition the Mayor", "the Circuit Court of Leon County", "the attorney general". `xref`
   finds no reference at all in Fla. Stat. § 607.0126. So the `mentions` finder of entities-contacts 1.4 runs over
   the same sections, and the defined-term resolver (2.2) handles "the board" and "the department".
5. **Cue phrases** set the type and relation. A small table sits beside `xref.py`'s patterns:

   | Cue | Type, relation |
   |---|---|
   | "appeal in writing … to the head" | internal appeal, `escalates-to` |
   | "petition the Mayor to review" | external review, `escalates-to` |
   | "file a request for review with" | external review |
   | "must ask for a decision from" | external administrative review (the reviewer decides and binds), `defers-to` (3.2) |
   | "may reapply", "returns the document with corrections" | internal appeal, `returns-to`, direction `return` |
   | "ask … to mediate the dispute" | ombudsman / mediation, `mediates` |
   | "may be extended by written notice from the head of the agency or a designee" | delegation, `requires-approval-of` |
   | "shall be conducted by administrative law judges" | delegation, `delegates-to` |
   | "advisory opinions" | advisory opinion, `advises` |
   | "shall … forward to" | referral or `notifies` |
   | "attempts to resolve disputes" | ombudsman / mediation, `mediates` |
   | "petition … to compel" | judicial review |
   | "shall not be affected by the failure to seek" | sets `exhaustion: optional` on the earlier rung |
   | "is a prerequisite to an appeal" | sets `exhaustion: required` |

   The small-classifier pattern of links-codebase-map §6 can rank types later. Rules come first, because the corpus
   has only about 150 rungs.
6. **Targets resolve through the entity graph** (2.2). Relative targets use `headed-by`. Venue-bound courts use
   `resolve_by`.
7. **The graph checks the result** (3.7):
   * the target must hold a power (3.1);
   * the target must not be the deciding post (separation of duty);
   * a structural parent never becomes a target unless a quote names it.
8. **Review.** Every derived rung starts `proposed`. A person accepts it, or two extractions agree on it.

### 3.7 Checking against `fixtures/authority/ladders.json`

* **Matching.** A derived rung matches a fixture rung when state, question, section pinpoint (normalised) and type
  agree. Its target then counts as right when the key is the same, or when it resolves to the same body.
* **Metrics.**

  | Metric | Target (on the development set) |
  |---|---|
  | rung recall | ≥ 0.85 |
  | rung precision (after removing rungs a reviewer accepts as new) | ≥ 0.90 |
  | target-key accuracy | ≥ 0.90 |
  | deadline amount and unit agreement | ≥ 0.95 |
  | trigger-code overlap (Jaccard) | ≥ 0.8 |
  | `mandatory` and `exhaustion` agreement | reported only; legal readings |

* **Circularity.** The fixture was built from the same models, so it is a development set and its scores flatter.
  A held-out set of at least three new ladders, built by hand before the deriver runs on them, gives the honest
  number. Candidates are NY business, WA business and IL licence.
* **A known gap in the fixture.** The reviewed `curated/nc/records.json` has a step `request_fee_mediation`
  (requester → State CIO): "the requester may ask the State Chief Information Officer or his designee to mediate
  the dispute" (G.S. § 132-6.2(b)). The fixture's `nc.records` ladder has 3 rungs and none for this step. The deriver
  will propose it (ombudsman / mediation, `mediates`, addressed to the State CIO post in the NC Chief Information
  Officer office, Q136430659). A reviewer should accept it as new, so it does not count against precision. With
  it, the fixture would hold 144 rungs, 86 of them from reviewed models.
* **Other checks, in a new test file.**
  * **Resolves.** Every key resolves.
  * **Separation of duty.** An escalation's target is not the deciding post.
  * **Exhaustion consistency.** A `required` rung lies on every path to its successors, unless a deemed outcome
    makes it `constructive`. This is the check that flags the D.C. edge in authority-standards 5.4.
  * **Remedy notice.** Where the statute requires it (5 ILCS 140/9(a); Cal. BPC § 485(b); MD denial statements),
    the notice step names every open rung.
  * **No cycles,** except remand and reconsideration.
  * **Clocks.** A statutory time limit is present, and a deemed outcome has a `next`.
  * **Quotes.** Every quote is verbatim within its section.
  * **QIDs.** Every QID is kind-checked (1.3).
  * **No structural rung is ever labelled a remedy.**
  * **A negative fixture.** A new file of parents that must not appear as rungs. It starts with three entries: the
    DCA director for California licensing (§ 109(a), with its `inferred` note); the Florida Secretary of State as a
    reviewer of a refused filing (§§ 607.0125(4), 607.0126); and the Governor of Florida (§ 20.02(3), supervision,
    not review). The Department of State is not an entry: it is the decider, and the corrected-refiling rungs
    (§ 605.0210(4), § 607.0123(3)) are addressed to it.

### 3.8 What is never inferred from the organisation chart alone

* **A parent body is not an appeal body unless the law says so.** California says the opposite for four kinds of
  board decision: they "are not subject to review by the director" (BPC § 109(a)).
* **The head of a body is a reviewer only where a statute sends the matter to the head.** N.Y. § 89(4)(a) does; Fla.
  ch. 607 does not.
* **These are read only from the text:**
  * exhaustion (for the federal rule, 5 U.S.C. § 704, as the Supreme Court read it in 509 U.S. 137 (1993));
  * whether a review binds;
  * time limits;
  * who may invoke a rung;
  * whether a power may be delegated ("agency itself", Gov. Code § 11500(a));
  * which branch's records skip a reviewer (D.C. § 2-537(a-1)).
* **Wikidata never supplies an edge on its own.** Its P797 *authority* is never one. Its P2388 is never accepted
  without review.
* **Supervision is not review.** `supervised-by` (Fla. § 20.02(3)) is not a review right.

### 3.9 The resolver

`lexflow/entities/authority.py` (new), next to `entities/resolve.py`:

```
escalate(state, question, step_or_outcome, place=None, facts=None) -> list[Rung]
defer(state, question, step, facts=None) -> list[Wait]
not_rungs(state, question, body_key) -> list[Reason]        # negative grants, e.g. BPC § 109(a)

Rung = {key, order, type, relation, target: {key, name, kind, wikidata}, trigger, deadlines, exhaustion, binding,
        invoked_by, alternative_to, next, source: {citation, quote, act_id}, basis: statute | inherited | oversight | structural,
        contact: best() of the target's player | None}
```

The resolver works in this order:

1. **Who decided.** Role → `played-by` → body, office-type instance (by `place` or `facts`) or post type.
2. **Statutory rungs.** Accepted rungs whose `after` matches the step or outcome, filtered by `scope_rule` and
   `facts`, then ordered.
3. **Inherited rungs.** The APA ladder reached through a `procedure` reference.
4. **Oversight channels.** Marked non-binding.
5. **Structural fallback.** Used only when steps 2 and 3 return nothing:
   * the body's `headed-by` post, then its parent's head, up to the root;
   * minus anything `not_rungs()` returns;
   * labelled `basis: structural`, "chain of authority, not a legal right of review".
6. **`defer()`.** It returns `defers-to`, `requires-approval-of` and `refers-to` rungs, and `prerequisite_process`
   links, each with the waiting step's own deadline.

Expected outputs, which become tests:

* **FL refused filing, corporation route.**
  * Rung: a corrected return to the department within 60 days of its mailing, keeping the original date if asked
    for in writing (§ 607.0123(3)). Or, as an alternative, § 607.0126 and the Leon County court: no time limit;
    nothing required first; attach the document and the explanation.
  * Structural line: Division of Corporations → Department of State → Secretary of State, appointed by the
    Governor.
* **CA licence, after a notice of denial.**
  * § 485(b) hearing request within 60 days, which is required for that route.
  * Then the hearing, before a judge alone or the board with a judge present (the board's choice, § 11517(a)),
    the optional reconsideration, and the writ within 30 days.
  * `not_rungs` returns the DCA director (§ 109(a)), with the "passing candidates" note for reviewers.
  * `defer()` offers § 480(b) and (c) as paths that bar the denial, except for the three bodies of § 480(i).
  * The reapplication date of § 486(a) is shown as a return to the board, not as an appeal.
* **TX records, the body wants to withhold.** `defer()` returns the AG ruling request: 10 business days
  (§ 552.301(b)), with "presumed public" on a miss.
* **NY records.** The appeal to `position-type:ny:foil_appeals_officer` (30 days; 10 business days to decide,
  deemed denial on a miss), the notice to the Committee on Open Government (shown as "the agency must send your
  appeal to …"), then Article 78 (4 months).

---

## 4. Representation

### 4.1 BPMN

The work is a post-compile IR transform, `attach_rungs(model, rungs)`, in a new module
(`lexflow/entities/authority_bpmn.py`). The IR already has participants, lanes, message flows, escalation events,
boundary timers and call activities, so neither `ir.py` nor `extract/*` changes during the freeze.

| Rung | BPMN form | Example |
|---|---|---|
| To another body (an appeal, external review, court, mediation, advice) | **The target's pool**: a participant keyed by its body. **A message flow** from the invoker's send task to the target's receive event, and back with the decision. | `petition_court` (organizer pool) → Circuit Court of Leon County pool; `court_order` → Division pool. The curated `fl.business` model already has these pools and flows. The rung adds `lex:rung`. |
| Inside one body (to the head, or a sign-off by the head) | **A lane per post** (`ln_<position slug>`) in the body's pool. An **escalation event** is thrown in the officer's sub-process and caught by a non-interrupting boundary event that leads to the head's task. | Cal. Gov. Code § 7922.535(b): an extension needs the head or a designee; N.Y. § 89(4)(a): an appeal to the head |
| A statutory clock | the existing **boundary timer** (`extract/compile.py` turns deadlines into timers). The rung's lapse consequence sets the outgoing path: a deemed denial leads to the next rung, a deemed approval to a favourable end, and a lapse to an end. | NY: 10 business days to decide the appeal, deemed denial |
| Waiting on another body's ruling | an **event-based gateway** in the decider's pool: a message catch for the ruling, or a timer for the statutory limit, with the presumption on the timer path | TX § 552.301: ask the AG within 10 business days (§ 552.301(b)), otherwise § 552.302 |
| Deferral to a status another process produces | a **data store reference** with `lex:requires` (bpc-480 6.3), never a call activity | § 480(c) → `ca.record_sealing` |
| The text sends the step into another procedure | a **call activity**, `calledElement` = the provider process key | BPC § 485(a) → the APA formal hearing |
| Notice to an overseer | a send task with a message flow and no return | N.Y. § 89(4)(a) → Committee on Open Government |

Every element the transform adds carries
`<lex:rung key="lexflow:rung:…" type="…" exhaustion="…" binding="…"/>` beside `lex:grounding`. `lex:actor` gains
`body="lexflow:agency:…"` and `position="lexflow:position…"`.

**Checks.** The XSD, the existing BPMN validator, and SpiffWorkflow loading the result.

### 4.2 DMN

* **One decision per rung that can be open or closed:** "Is this remedy open?" Each is a UNIQUE table, as in
  bpc-480 3, so conflicts and gaps can be checked.
* **Inputs:** the trigger, the time since the anchor, whether an earlier rung was used or lapsed, and scope facts.
* **Requirements:**
  * an authority requirement to the rung's section, as a knowledge source at subdivision level;
  * an information requirement to the decision it reviews.
* **Who decides, and who owns the rules:**
  * the decider is carried as `lex:decisionMaker body="…" position="…" role="…"`;
  * a binding opinion is a knowledge source whose `lex:owner` is the opinion-giving body;
  * the standard `decisionMaker`/`organizationUnit` goes only into an opt-in export variant, validated against the
    XSD alone (A10).

Example: `writ_open` for California licensing, grounded in Gov. Code § 11523.

| days since the last day reconsideration could be ordered | record requested within 10 days of that day | days since the record was delivered | `writ_open` |
|---|---|---|---|
| ≤ 30 | - | - | true |
| > 30 | true | not delivered yet | true |
| > 30 | true | ≤ 30 | true |
| > 30 | true | > 30 | false |
| > 30 | false | - | false |

The second row closes a gap: a record requested in time but not yet delivered keeps the window open, because the
time "shall be extended until 30 days after its delivery".

"The last day on which reconsideration can be ordered" is computed, not fixed (§ 11521(a)). It is 30 days after
the decision is delivered or mailed, or an earlier effective date the board sets, or the end of a stay of up to 30
days granted to allow a petition. A further stay of up to 10 days may follow, to consider a petition already filed.
The deadline record carries these as `extensions` (3.5), and the table's first input reads the computed day.

Authority requirement: § 11523, "the petition shall be filed within 30 days after the last day on which
reconsideration can be ordered", and "If the petitioner, within 10 days after the last day on which reconsideration
can be ordered, requests the agency to prepare all or any part of the record, the time within which a petition may
be filed shall be extended until 30 days after its delivery to him or her."

* `reconsideration_used` is not an input. The rule "The right to petition shall not be affected by the failure to
  seek reconsideration before the agency" is recorded as `exhaustion: optional` on rung 3, not as a column.
* The Florida example needs no table. Its rung has no time limit, so `court_petition_open` is a FEEL literal,
  `trigger = "refused_filing"`, with § 607.0126 as its authority.
* As in bpc-480 6.4, these elements go into the FEEL dialect only, until SpiffWorkflow's Python dialect is shown to
  accept them.

### 4.3 The dashboard: an "If this goes wrong" panel per process

A new endpoint, `GET /api/authority/{state}/{question}?step=…&place=…`, calls `escalate()` and `defer()`. The panel
sits on each model and answer page:

| What went wrong | Where to go | By when | Must you do this first? | Does it bind? | The law says |
|---|---|---|---|---|---|
| The Division refuses to file your articles | Circuit Court of Leon County: a petition to compel filing | The statute sets no deadline | Nothing else is required first | A court order | "If the department refuses to file a document delivered to its office for filing, the person who submitted the document for filing may petition the Circuit Court of Leon County to compel filing of the document." (Fla. Stat. § 607.0126) |

Display rules:

* **Contacts.** The next body's contact comes from `entities.provenance.best()` (entities-contacts 2.5). Only
  values with status `ok`, verified within their tier interval, are shown, with "source · checked YYYY-MM-DD".
  Otherwise the panel says "No verified contact yet": unchecked websites stay hidden (entities-contacts D8).
* **Posts are never people.** A position shows its body's contact, never a person's.
* **Generic targets.** An office type shows the instance for the user's place; a court is chosen by venue.
* **Unknowns.** An unknown exhaustion reads "The statute does not say whether you must do this first". A missing
  limit reads "The statute sets no deadline".
* **Structure.** The structural chain appears in a muted line below the table, labelled "Chain of authority (not a
  right of review)". `not_rungs()` adds "Not reviewed by …" with its section.
* **Health.** A small badge counts reviewed models whose decision steps have a ladder, or an explicit "the statute
  names none".

### 4.4 DokuWiki pages (`lexflow:` namespace)

* **Model page** (`render_state_model`). Three new sections, generated from accepted rungs:
  * **"If this goes wrong"**, the same table as the panel;
  * **"Who acts"**: roles → bodies → posts, with links to agency pages;
  * **"Hand-offs and waiting"**: referrals, delegations and deferrals, with the provider model's page.
* **Agency page** (planned in entities-contacts 3.7):
  * "Part of", "Head position" and "Appointed by", each with its section;
  * "Decisions of this body are reviewed by", from incoming rungs;
  * "This body reviews", from outgoing rungs;
  * "Not reviewed by", from negative grants. The DCA page would say "A board's decisions on setting standards,
    conducting examinations, passing candidates and revoking licences are not subject to review by the director
    (Bus. & Prof. Code § 109(a))";
  * schema.org `GovernmentOrganization` JSON-LD with `parentOrganization` and `sameAs` (Wikidata, and Govdirectory
    when listed).
* **Law page.** "Mechanisms this section creates" lists the rungs it grounds, beside "Used by processes".
* Nothing on any page names a person.

### 4.5 Wikibase statements

**Item shapes.** The P-numbers are existing; the names in italics are new (5.2).

| Item | Statements |
|---|---|
| agency or unit | P25 key; P5 *government agency* / *organizational unit* / *court* / *government*; P15; *parent organization* → parent (statute-grounded: qualifiers P13 → statute item and P22 words; Wikidata-grounded: the references in 5.6); *head position* → position; *authority conferred by* → statute (qualifiers *power*, P16, P22); P8 → Wikidata (exact and kind-checked only); *described at URL* → Govdirectory, if listed |
| position | P25; P5 *position*; P15; *position in* → its agency (`org:postIn`; not P9, so that `P9*` paths never return posts); *appointed by* → position or agency (P13 + P22); *authority conferred by*; P8 → a Wikidata position item. It has start and end time only for the post's own creation and abolition. **It never has P39, P1308 or a person.** |
| position type | P25; P5 *position type*; P15; P22 the statute's words; P13 → the defining statute |
| office type | as in entities-contacts 1.7. The `resolve_by` rule goes in the description ("resolved by the county of the record"). |
| role (exists) | gains *played by* → body, office type, position, position type or the *private party* item; *role of actor* (terms plan); *review status* |
| step (exists) | gains *recipient* → role; *review status* |
| **rung** (new) | P25 key; P5 → a mechanism subclass; P15; P9 → the process item; P11 *follows* → the step (or earlier rung); P12 *followed by* → the next rung; P17 *bearer* → the invoking role; *addressed to* → the target; P18 *condition* → trigger items; P16 → Right (the person's remedy), Obligation (the body's duty) or Permission (the body's option); *time limit* (with qualifiers); *exhaustion*; *binding effect*; P13 → statute item with P22 = the quote (at most 400 characters); P21 *defeated by* → the carve-out's statute item, with P22; *review status* = reviewed |

**Example rung item.** This is the fixture's `fl.business` rung 2. Some of what it links to exists on the wiki
today: the process (Q774), the step (Q784), the organizer role (Q775), the § 605.0210 statute item (Q164) and the
*Right* class. The rest does not exist yet: the court item, the *judicial review* class, the trigger item, the
exhaustion, binding and review-status value items, and every new property. The corporation route's § 607.0126 has
no statute item either; only § 605.0210 does.

| P | Value |
|---|---|
| label / description | "petition to compel filing (Fla. Stat. § 605.0210)" / "escalation in Start a business in Florida: judicial review after a refused filing" |
| P25 | `lexflow:rung:fl:business:605.0210-7:court-petition` (the fixture's subtype, "petition to compel filing (summary proceeding)", maps to the code `court-petition`) |
| P5 | *judicial review* (a subclass of *authority mechanism*) |
| P9 / P11 | Q774 `lexflow:process:fl.business` / Q784, the step item of `lexflow:step:fl.business:refuse_filing` |
| P17 | Q775 (organizer role) |
| *addressed to* | the item for `lexflow:agency:fl:circuit_court_leon_county`, labelled "Circuit Court of the Second Judicial Circuit (Leon County)" (P8 → wd:Q7443383) |
| P18 | `lexflow:vocab:trigger:refused_filing` |
| P16 | Right |
| *exhaustion* / *binding effect* | none / binding |
| P13 | the § 605.0210 statute item (Q164), with P22 "petition the Circuit Court of Leon County to compel filing of the record" |
| *review status* | reviewed (only once a person has accepted the rung) |

**Queries.** Names in angle brackets stand for P-ids that do not exist yet.

```sparql
PREFIX lx:  <https://lexipedia.wikibase.cloud/entity/>
PREFIX lxt: <https://lexipedia.wikibase.cloud/prop/direct/>
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
# After a given step: the next bodies, the trigger and the statute; plus the body's parent from Wikidata if Lexipedia lacks one
SELECT ?rung ?rungLabel ?body ?bodyLabel ?trigger ?statute ?wdParentLabel WHERE {
  ?step lxt:P25 "lexflow:step:fl.business:refuse_filing" .
  ?rung lxt:P11 ?step ; lxt:<addressed to> ?body ; lxt:P18 ?trigger ; lxt:P13 ?statute ;
        lxt:<review status> lx:<reviewed> .
  OPTIONAL { ?rung rdfs:label ?rungLabel FILTER(LANG(?rungLabel) = "en") }
  OPTIONAL { ?body rdfs:label ?bodyLabel FILTER(LANG(?bodyLabel) = "en") }
  OPTIONAL { FILTER NOT EXISTS { ?body lxt:<parent organization> [] }
             ?body lxt:P8 ?wd . FILTER(STRSTARTS(STR(?wd), "http://www.wikidata.org/entity/Q"))
             SERVICE <https://query.wikidata.org/sparql> {
               ?wd wdt:P749 ?wdParent . ?wdParent rdfs:label ?wdParentLabel FILTER(LANG(?wdParentLabel) = "en") } }
}
```

The step is found by its P25 key, so the query needs no local Q-id. Two other queries are one line each:

* **Every reviewed process that routes to a body.**
  `?rung lxt:<addressed to> ?b ; lxt:P9 ?process . ?b lxt:P25 "lexflow:agency:tx:office_of_the_attorney_general"`.
* **A body's chain of authority.** `?body lxt:<parent organization>* ?up . OPTIONAL { ?up lxt:<head position> ?head }`.
  It runs locally, so it does not depend on Wikidata being up.

---

## 5. The exact Wikibase changes

### 5.1 First, the steps only you can take

1. **The hosting review is the most urgent.** Wikibase Cloud's new hosting policy makes every new and existing
   instance temporary by default, with the workflows due by the end of September 2026. Managers then have three
   months to submit it for review, and unreviewed instances are suspended. Lexipedia is probably temporary now;
   authority-wikibase could not see the dashboard to confirm. Please check the dashboard's Review tab and submit
   Lexipedia. Mention its use as a staging ground for later Wikidata contributions, which the policy counts in an
   instance's favour.
2. **A `Project:Copyrights` page.** The review requires a licensing statement: structured data CC0, and text under
   a reuse licence.
3. **A short `Project:People` rule** saying that Lexipedia models public offices, not people, and holds no personal
   data. The policy asks for local rules wherever living people could appear. Writing it is a wiki edit for you to
   approve.
4. **One go-ahead for the property set.** That is this note's list together with entities-contacts 1.7,
   terms-wikibase §4, bpc-480 6.5 and links-codebase-map 4.1, about 30 properties already proposed there, so that
   labels and meanings are fixed once. Two things to settle in the same go-ahead (5.2):
   * bpc-480's *reference role* qualifier and links-codebase-map's *reference type* are one idea, a qualifier on
     `P13` naming the reference's role (authority, procedure, prerequisite_process, …). Pick one label.
   * `lexflow/publish/wikibase.py` `PROPOSED` already defines a competing set. Retire or align it first.
5. **Optional: put the loader's account in the `bot` group.** Its edits currently flood Recent changes. The account
   keeps its sysop rate exemption.

### 5.2 Properties to create

The loader finds properties by English label (`wikibase_lexipedia.py` `PROPS` and `prepare()`), so each label below
is part of the contract. Each property gets an English description and a `P7 equivalent property` where one exists.

| # | Label | Datatype | On → value | Purpose | ≡ Wikidata (P7) |
|---|---|---|---|---|---|
| 1 | parent organization | item | agency or unit → agency or government root | the organisational hierarchy, separate from P9 (A9) | P749 (also `org:subOrganizationOf`) |
| 2 | head position | item | agency → position | "the head of …": resolves position types and the structural chain | P2388 |
| 3 | appointed by | item | position → position or agency | appointment and supervision lines (§ 20.10(1); BPC § 7011(a)) | P748 |
| 4 | authority conferred by | item | agency, position, office type or position type → statute item | power grants (3.1); qualifiers *power*, P16, P22 | none exact (nearest P92 *main regulatory text*, P457 *foundational text*) |
| 5 | recipient | item | step → role | the body a filing or notice goes to (LegalRuleML *AuxiliaryParty*; the facts' `recipient`) | none |
| 6 | addressed to | item | rung → body, position, office type, position type, court, process or status | where the mechanism goes | none. P12452 *appeals to* is narrower: only an unconditional body → body appeal. |
| 7 | time limit | quantity (units are local items: hour, day, business day, week, month, year) | rung | the statutory clock; qualifiers below | none |
| 8 | exhaustion | item | rung → `required`, `optional`, `alternative`, `constructive`, `none` (no statement means unknown) | whether the person must use it before the next rung | none |
| 9 | binding effect | item | rung → `binding`, `advisory`, `none` | whether the outcome binds the decider | none |
| 10 | review status | item | process, step, role, rung → `reviewed`, `agreed`, `draft` | today 357 drafts are marked only by their description, so queries cannot filter them | none |
| 11 | position in | item | position → agency | the body a post sits in (`org:postIn`), kept apart from `P9 part of` so that `P9*` paths return no posts (A9) | none exact (P2389 is the inverse for head posts only) |

**Needed from the other plans, and created in the same go-ahead:**

* *played by* (entities-contacts): the join between processes and bodies;
* *described at URL* (≡ P973): the Govdirectory link;
* *reference URL* (P854), *retrieved* (P813) and *determination method* (P459): references.
  entities-contacts makes *determination method* item-valued, and terms-wikibase makes it a string. Choose
  item-valued, as Wikidata's P459 is, and keep terms' free text in a P22 qualifier.
* *start time* and *end time* (P580/P582): for a post's creation and abolition only;
* *provides status* and *requires status* (bpc-480): deferral to another process through a status;
* *reference role* (bpc-480 6.5 and its open question 4) and *reference type* (links-codebase-map 4.1, cited in
  authority-wikibase 4.2): one qualifier on `P13`, under one label.

**A competing set in code.** `lexflow/publish/wikibase.py` `PROPOSED` already defines:

* "time limit" as a **string** (an ISO 8601 duration), where this note wants a quantity;
* "deadline runs from", where this note has *time limit anchor*;
* "performed by", where this note and entities-contacts have *played by*.

Labels are the contract, so these must be retired or aligned before the go-ahead. links-codebase-map's list of code
changes (item 19) already suggests retiring that path in favour of the loader.

### 5.3 Qualifiers

| Label | Datatype | On | Values |
|---|---|---|---|
| time limit anchor | string (≤ 400) | *time limit* | "service of the notice of denial" |
| time limit kind | item | *time limit* | filing limit, decision limit, response limit, hearing limit, notice limit, minimum wait, cure period, extension cap, earliest reapplication, tolling |
| consequence of lapse | item | *time limit* | deemed denial, deemed approval, deemed exhaustion, deemed adoption, presumption of disclosure, overruled by operation of law (Tex. Gov't Code § 2001.146(c)), right lapses |
| power | item | *authority conferred by* | the 17 power items (3.1) |

These existing properties are reused as qualifiers:

* `P13 references`: the statute basis on structural claims;
* `P22 citation`: the words;
* `P17 bearer`: who must act on a *time limit*;
* `P16 deontic modality`: the Hohfeld position on *authority conferred by*. It needs two new classes, *Power* and
  *Disability*. Check LegalRuleML for equivalent IRIs before giving them P8.
* `P18 condition`: the trigger.

### 5.4 Classes and vocabulary items

| Class | P6 / P8 | Count |
|---|---|---|
| organizational unit | P8 → wd:Q10387680 | 1 |
| position | P8 → wd:Q4164871 | 1 |
| position type | P6 → position | 1 |
| government | – | 1 |
| authority mechanism, plus its 10 subclasses (3.2) | – (no exact Wikidata items) | 11 |
| Power, Disability | P6 as for the existing deontic classes (Q13–Q20) | 2 |
| value-set classes: trigger, exhaustion value, binding value, lapse consequence, time-limit kind, power, review status value, time unit | – | 8 |
| **classes, this note** | | **25** |
| planned elsewhere, needed here | government agency (wd:Q327333), court (wd:Q41487), office type; and the terms plan's classes | – |

**Vocabulary items** (`lexflow:vocab:…`, 77):

| Set | Items |
|---|---|
| triggers | 25 |
| exhaustion | 5 |
| binding | 3 |
| lapse consequences (5.3, including "overruled by operation of law") | 7 |
| time-limit kinds | 10 |
| powers (3.1, including `intervene` for BPC § 109(c)) | 17 |
| review status | 3 |
| time units (each with P8 to its Wikidata unit item where exact) | 6 |
| the *private party* marker | 1 |

The rung subtype codes (1.3) are not items: they live in code and in rung keys only.

### 5.5 Items to load (after the classes and properties exist)

| Group | Items | Source |
|---|---|---|
| government roots | 11 | the P208 items in authority-wikidata 2.2 (CA, NY and IL use the "State of …" items) |
| bodies in `agencies.json` | 98 (76 distinct QIDs) | entities-contacts phase 3 seed |
| further specific bodies on the ladders, including the review bodies with no Wikidata item | about 15 | `ladders.json` `bodies` |
| intermediate parents up to the roots | about 15 | Wikidata P749 chains plus statutes (BCSA, DCA, MDOT, BPLA, the FL Department of State, NC DIT …) |
| office types | about 60 | 46 generic `agencies.json` entries plus the ladders' 42 office-type keys, which overlap |
| positions | about 40 | governors, the D.C. Mayor, attorneys general, secretaries of state, and heads the rungs and chains use (Tax Commissioner, NC State CIO, DCA director, Registrar of Contractors, OAH directors) |
| position types | about 25 | the ladders' 11, plus head-or-designee types per state |
| **entity items** | **about 265–320** | the rows above add up to 264; more if the contacts plan also loads its 98 CourtListener courts |
| rung items | at most 85 now (86 with the NC fee-mediation rung, 3.7) | only accepted rungs of reviewed or agreed models. These come from the 14 reviewed models that have a ladder (11 records models, and business in FL, VA and DC). The fixture's other 58 rungs come from reference answers (sealing in CA, MD and VA; licensing in CA, VA, DC, MD and TX), which have no process item on Lexipedia. They load once those answers become reviewed models. |
| classes and vocabulary | about 100 (25 + 77) | 5.4 |
| **all new items** | **about 450–500** | |
| **writes per load** | **about 1,900–2,000** | `Loader.entity()` saves every item it owns on every run (there is no diff), and *review status* or *played by* must be added to the 1,413 items lexflow already keyed. So a load rewrites those as well as creating the new ones: about 33 minutes at one edit a second, or 7–8 minutes at the 268 edits a minute the account reached in its last load. |

Against these: a Govdirectory mirror would be about 29,000 items, and would cover 7 of the 91 body QIDs.

### 5.6 Keys, references and the update policy

* **Keys.** Each item carries its lexflow key in P25 (1.3).
  * Today the loader finds an earlier item only through `wikibase_items`, or through `owner()`, which recovers an
    item only when a create clashes on an identical label and description. So a lost local table can cause
    duplicates.
  * New: before any create, the loader also looks the key up with `haswbstatement:P25=<key>`. Search indexes
    asynchronously, so the lookup runs for a whole batch before its creates, or after a short wait, and is tested
    in a dry run.
  * **Statute keys are not re-minted.** Lexipedia's California statute keys mix two spellings: bare numbers
    (`lexflow:statute:ca:7922.535`, `…:12190`) and full citations (`lexflow:statute:ca:Cal. CORP § 200`). A rung's
    `P13` finds the existing item through the act_id-to-key map, never by minting `lexflow:statute:ca:<another
    spelling>`. Otherwise `owner()` fails on the label clash (the keys differ), the loader appends a suffix, and a
    duplicate statute item results.
  * **Classes are found by key.** `prepare()` looks classes up by English label, and `labels()` keeps the first
    item per label in page order. The new labels include "position", "court", "government" and "Power", and value
    items such as "none" and "binding", so an item with a class's label could shadow the class. Classes are looked
    up by their `lexflow:class:<label>` P25 key instead, and the base classes that lack one get it in the same
    go-ahead.
* **References.**
  * A statute-grounded claim carries `P13` → the statute item, with `P22` = the words.
  * A Wikidata-grounded claim carries *reference URL* = the Wikidata entity URL, *retrieved* = the read date, and
    *determination method* = "from Wikidata, reviewed".
  * A curated claim carries *determination method* = "curated".
* **Regenerated from the DB.** The loader sends `wbeditentity` with `clear`, so every statement is rebuilt from the
  DB on each load, and anything typed into the wiki by hand is erased (entities-contacts D12). Edits belong in the
  DB.
* **One writer per item.** Because of `clear`, two phases that save the same item erase each other's claims.
  *Played by*, *recipient* and *review status* go on role, step and process items, which `processes()` writes.
  So `processes()` adds those claims itself, reading `played-by` links, step recipients and review tiers from the
  DB. The new
  `authority()` phase writes only the items it owns: agencies, positions, rungs and vocabulary.
* **What loads.** Only accepted rungs of reviewed or agreed models. Bodies and posts load when a loaded process or
  rung reaches them.
* **Retiring.** `retire_drafts` cannot do this as it stands: it skips every key whose model is `reviewed` or
  `agreed`, and rungs load only for those models. Rungs get their own rule instead: every rung key of the run's
  states that has an item but was not written in this run is relabelled as retired and loses its *review status*,
  whatever its model's tier. That covers a rung rejected after loading and a key given up for an alias. Nothing is deleted without
  asking.
* **Loader changes.**
  * `_snak` must write quantity snaks; today it writes only item and string snaks.
  * `_snak` and `entity()` write main snaks only, and the wiki today holds 0 qualifiers and 0 references (checked
    2026-10-10). The design needs both: P22 on P13, the time-limit qualifiers, *power*, and the *reference URL*,
    *retrieved* and *determination method* references. The loader learns to write them.
  * The `haswbstatement` key lookup, the class lookup by key, and the rung retirement rule above.
  * `processes()` builds each role, step and process item's full claim list in one place.
  * `MODALITY` gains Power and Disability.
  * New phases `agencies()`, `positions()` and `authority()` run after `jurisdictions()`.
  * Every load runs a dry run first, and the publish stays user-triggered.
* **Two quotes exceed the 400-character string cap** (`tx.records.8`, 433 characters; `ny.records.1`, 432). Store
  their start and link the DokuWiki page. Keep the limit at 400 by choice, because the DokuWiki page holds the full
  words. The limit can be raised, to as much as 2,500, but a platform quirk means raising the monolingual-text
  setting as well as the string setting (authority-wikibase 2.6).
* **Refresh.** A monthly polite Wikidata crosswalk read follows redirects and watches P576/P1366 dissolutions and
  new P749/P2388 values. Wikidata alone would miss statutory sunsets, so each new index release also re-reads the
  sections that carry a `valid_until` (Cal. BPC § 7000.5(c) and § 7011(e), January 1, 2029) and looks for new
  ones. Changes go to the review queue and are never auto-accepted for authority edges.
* **Renames.** A body's label changes and its old name becomes an alias; the key stays. Example: BPC § 100's 2026
  move of DCA into the Business and Consumer Services Agency.

### 5.7 What not to create

* **No mirror.** No Govdirectory or Wikidata mirror, and no Tier B import of the NY and NC lists, unless a process
  needs them wholesale.
* **No people.** No person items. No *position holder*, *position held*, person-valued "led by" or office-holder
  contact properties.
* **No federated properties.** They need a fresh wiki with no local properties.
* **No federated items either.** Wikibase's "federated items" (ontology federation) is in its alpha version, so it
  is not an alternative to local items now.
* **No separate "Wikidata item ID" property for now.** P8 already holds the entity IRI, and the federated query
  joins on it (A8). Add it later only if clickable formatter links or `haswbstatement` lookups by QID are wanted.
* **No `reports to` or `supervised by` on the wiki yet.** No ladder needs them. They stay in the DB.

### 5.8 What to propose upstream to Wikidata instead

The flow is the `upstream_suggestions` flow of entities-contacts 4:

* drafts are referenced to the official statute page (P854, with P813);
* a person reviews them in batches of 20 or fewer and applies them under their own account;
* nothing about people is ever drafted.

Govdirectory reads Wikidata. So a fix shows on Govdirectory for the bodies it already lists, after a maintainer's
next build, which can take months. For other states nothing shows there until Govdirectory adds a list.

| Kind | Examples found in the research and in this pass | About |
|---|---|---|
| New items for bodies that have none | NY Committee on Open Government; VA FOIA Council; MD PIA Compliance Board; D.C. Office of Open Government; Virginia DPOR; D.C. and California offices of administrative hearings; FL DOAH | 15–20 |
| Parent links (P749) | the Contractors State License Board → DCA (BPC § 7000.5(a)); the Florida Department of State → State of Florida; the 31 of 52 state bodies with no parent, including every TX and NC body in the fixture | 30 |
| Head posts and their inverses | Q11969252 P2388 → Q7444366, and Q7444366 P2389 → Q11969252 and P748 → the Governor of Florida (Fla. Stat. § 20.10(1)) | 10 |
| Typing and jurisdiction | review P31 "database" (Q8513) on the Florida Division of Corporations (Q107179384), flagged for a person with no value proposed; P31, P749 and P1001 for the Illinois Public Access Counselor (Q104879968); P1001 and a parent for the D.C. Board of Ethics and Government Accountability; P208 for CA, NY and IL; the English description of Q7707525 (*Texas Attorney General*), which reads "head of the Texas Department of Criminal Justice", flagged for a person | 9 |
| Per-state class membership and FOI request URLs | P31 "state agency of <state>" where it is missing; P10214 for records bodies whose request page lexflow has verified (after the contacts checks) | after phase 2 of entities-contacts |
| Court ladders (P12452) | only unconditional court → court appeals | later |

---

## 6. Questions to bring to the Govdirectory group

These are points to raise, not assumptions about the answers. Any written report or pull request to Govdirectory
should be in your own words, because its contribution guide blocks contributions recognisable as AI-generated.

1. **US state coverage.** The US lists are federal, New York and North Carolina. Are other states planned, such as
   VA, DC, MD, TX, CA, FL, IL, WA or OH? A new state needs a generator query and class items carrying P6104 =
   Q108109790. Would a person-written pull request for one state be welcome?
2. **Classes for state agencies.**
   * Per-state classes exist with very uneven use: CA 66 items, MD 27, TX 16, FL 13, VA 9, IL 6 and WA 4, and DC has
     no class.
   * Does the group prefer per-state classes, or a generic class plus P1001?
   * Is a "D.C. government agency" class wanted?
3. **Units.**
   * Their data model draws the line at "something the public can contact". The NY Division of Corporations
     (Q125449570, typed *registration authority*) is not listed, though the public files with it.
   * Would divisions with their own public channels be listed, with their P749 parent?
4. **Posts.**
   * The US generator drops positions, and "Led by" shows a person's name chosen by an open-ended P39 test. Several
     posts have more than one such statement.
   * Would the group consider showing the head *post* (P2388), beside or instead of the person?
5. **Review and oversight bodies.**
   * Ombuds, FOI review bodies, compliance boards and hearing offices often have no item.
   * Are they in scope for the lists?
   * Is *appeals to* (P12452), or any review relation, in scope for the WikiProject data model?
6. **Contributions sourced from lexflow.** Would they welcome Wikidata additions that a person reviews and applies
   with official references? Examples: new items for missing bodies, P749 parents, P10214 FOI request URLs, and
   website moves. Which reference standard do they want? How should a tool-assisted pipeline be described, given
   their rule on AI-generated contributions?
7. **Contact freshness.**
   * lexflow's pilot found 43 % of verifiable websites stale (±14 points), and 3 hijacked domains in a sample of 55.
   * Would periodic lists of moved or broken official websites be useful, applied as referenced Wikidata edits by a
     person?
   * Is there a preferred way to report a hijacked domain?
8. **Cadence.** Builds are deployed by hand, with gaps of up to about four months in 2026. Is there a way for fixes
   in listed states to appear sooner?
9. **Main regulatory text** (P92 with P953 and P1476). Would statute items for agencies' founding sections, such as
   Fla. Stat. § 20.10, be useful on their pages?

---

## 7. Privacy, risks and the plan

### 7.1 Privacy rules

1. **Posts, never persons** (A1). There is no holder column, no person key, and no person item or statement on the
   wiki.
2. **Holder data is dropped at parse time.** P1308, P39 and the person-valued "led by" claims (P488, P169, P1037,
   P3975) are never stored or logged. P2388 and P1313 are kept, because they name posts; this is a declared change
   to entities-contacts 5.4, which drops them (A15).
3. **Showing a current holder is off.** If you ever turn it on, it follows the live, single-statement rule of 1.7,
   labelled "according to Wikidata", on the dashboard only: never on a DokuWiki page or in the Wikibase.
4. **No contact details of any person.** A post shows its body's office channels only, through the office-mailbox
   guard of entities-contacts 5.2.
5. **Private roles are markers.** The incorporator, organizer, registered agent, requester and applicant resolve to
   `lexflow:private-party`, and lexflow never looks up who they are. The names that § 607.0202(1)(e) puts in
   articles of incorporation are never read.
   * **Certified mediators are private persons.** The reviewed NC model types the mediator `private-party`. The
     fixture's key `lexflow:position-type:nc:certified_mediator` stays only as a type label that never resolves to
     anyone: it is `played-by` `lexflow:private-party`, with no Wikidata item, no contact and no list of names.
6. **Statutes that ask for a named person are met with the post** (1.7).
7. **Reviewers are recorded by role.** No researcher or person is named as a source, partner or endorser.
8. **Tests enforce it.** Fixtures and dry-run payloads are scanned for human-class QIDs, P39/P1308 values and
   personal-looking mailboxes. An EntitySchema (ShEx) shape for *position* forbids holder properties. Both are new
   test files.

### 7.2 Risks

| Risk | Effect | Mitigation |
|---|---|---|
| A legal reading is wrong (exhaustion, binding effect, venue) | a user skips a required step or misses a deadline | text-only values; "the statute does not say" when unknown; review before publish; the open question in 8 on who reviews legal readings |
| The organisation chart is shown as a remedy | a user writes to a cabinet secretary instead of filing an appeal | structural rungs are never stored; they are always labelled; the negative fixture and `not_rungs()` cover the parents |
| Wikidata structure is trusted too far | wrong heads or parents (VA Taxation's P2388; the Division typed "database") | P2388 is always reviewed; P797 is a lead only; kind-checked QIDs |
| A QID lands on the wrong kind of item | a post carries its department's identity, or the reverse | the 1.3 kind check; 9.2 lists the fixture cases |
| The evaluation is circular | the deriver looks better than it is | a held-out set of at least 3 ladders built before the run |
| Court rules are outside the corpus | 12 rungs' deadlines cannot be grounded | marked `basis` outside the corpus; the court rules are an open corpus question |
| Lexipedia is suspended under the hosting policy | every load is lost | 5.1 step 1, now |
| `clear` erases hand edits | lost corrections | edits go in the DB; the dry-run diff is reviewed |
| The benchmark freeze | IR, schema and `ask/*` changes wait | new modules; a post-compile transform; `deemed-approval` waits |
| Upstream rules | contributions are blocked or reverted | human-applied, referenced, small batches; no lexflow-written reports to Govdirectory |
| Bodies are renamed or reorganised | stale labels (DCA's 2026 move) | stable keys, aliases, the monthly refresh to review |

### 7.3 Phased plan

| Phase | Scope | Depends on | Effort | Exit check |
|---|---|---|---|---|
| **0. Your decisions** | Hosting review and `Project:Copyrights`; one go-ahead for the combined property set; A9 (dedicated parent property); the conversation with Govdirectory | – | your time | instance submitted; property list approved |
| **1. Data and tables** (local, no network writes) | Fix the 9.2 #5 cases: the VA Tax Commissioner QID; the Texas Attorney General post's QID (Q7707525) off the TX OAG agency key and onto `lexflow:position:tx:attorney_general`; the Maryland District Court QID (Q16932596) off `lexflow:office-type:md:court_of_disposition` and onto the District Court; parent and position QIDs onto their own items; verify the 5 search-matched QIDs. Review the 17 inferred rungs, and add the NC fee-mediation rung (3.7) for review. Add the `positions`, `power_grants`, `rungs` and `rung_aliases` tables, the new `agencies` columns, `valid_until`, and the new `entity_links` relations. Seed from `agencies.json` and `ladders.json` by the 1.3 rules (exact QIDs only; merge shared office-type keys), plus the statute-grounded edges of 2.3–2.4 | entities-contacts phase 3 (`agencies`, `office_types`, `entity_links`, `played-by`) | 3–4 days | every ladder body has a key and a kind-correct QID or none; 0 person fields; re-runs keep decisions and compute the same rung keys |
| **2. Derivation and checks** | `derive_rungs()` (3.6), the cue table, the checker (3.7), the negative fixture, a held-out set of ladders | 1 | 4–5 days | development set: recall ≥ 0.85, precision ≥ 0.90, target-key accuracy ≥ 0.90; held-out reported; 0 rungs without a verbatim quote; 0 structural rungs as remedies |
| **3. Resolver and surfaces** | `escalate()`, `defer()`, `not_rungs()`; the API and the "If this goes wrong" panel; the DokuWiki sections, as a dry run only | 2; contacts phases 1–2 for `best()` | 3–4 days | ≥ 90 % of decision steps in the 22 reviewed models show a ladder or "the statute names none"; the four worked outputs of 3.9 pass as tests |
| **4. Wikibase** (after your go-ahead) | Retire or align `PROPOSED` in `publish/wikibase.py`. Create the 11 properties, 4 qualifiers, 25 classes and the vocabulary. Loader changes (5.6): quantity snaks; qualifiers and references; the `haswbstatement` key lookup; classes by key; one writer per item; the rung retirement rule; the `agencies()`, `positions()` and `authority()` phases. Dry run; your load of the 11 states | 0, 1, 3 | 3–4 days | the dry-run diff is reviewed; 0 person statements; *review status* on 100 % of process, step, role and rung items; a second dry run after a simulated loss of `wikibase_items` creates no new item |
| **5. BPMN and DMN** (after AskBench) | `attach_rungs()`; the remedy decisions; `lex:decisionMaker`; the `deemed-approval` value | the end of AskBench | 3 days | the BPMN validates and SpiffWorkflow loads it; the DMN passes the XSD and dmnlint; the CA `writ_open` table is checked for conflicts and gaps |
| **6. Upstream** | Drafts for 5.8; dashboard review; a QuickStatements export for a person to paste | 1 | 1–2 days, plus review time | the first batch of 20 or fewer is exported; the applied rate is tracked |

The total is about 17–22 developer days, sharing tables with entities-contacts phases 1–3.

### 7.4 Success measures

| Measure | Baseline (2026-10-10) | Target |
|---|---|---|
| Non-private actors in the 22 reviewed models resolved to a body, unit, office type, post or post type | 0 of 55 | ≥ 95 % after phase 1 |
| Decision steps with a statutory ladder, or an explicit "the statute names none" | 14 of the 22 reviewed models have a hand-built ladder in the fixture (85 rungs); the business models of CA, IL, MD, NC, NY, OH, TX and WA have none. The fixture's other 8 ladders (58 rungs) come from reference answers. 0 in the DB | ≥ 90 % after phase 3 |
| Derived rungs against the fixture (recall / precision) | – | ≥ 0.85 / ≥ 0.90; plus a held-out number |
| Rungs with a verbatim quote | 143 of 143 in the fixture | 100 %, always |
| Structural rungs shown as remedies | – | 0, always |
| Person-valued statements or holder fields anywhere | 0 | 0, always |
| Bodies named in reviewed models with a parent chain to the government root | 20 of 52 from Wikidata alone | ≥ 90 % with statute-grounded local edges |
| Bodies with a head post | 8 of 52 from Wikidata alone | every body that a position-type rung resolves against |
| "If this goes wrong" entries whose next body has a verified contact | 0 | ≥ 80 % after phase 3; ≥ 90 % with contacts phase 4 |
| Lexipedia items with a review status (process, step, role, rung) | 0 (357 drafts marked only in descriptions) | 100 % after phase 4 |
| Upstream drafts applied | – | ≥ 80 % of approved drafts |

---

## 8. Open questions

1. **The property set.** Will you approve this note's 11 properties, 4 qualifiers and 25 classes together with the
   contacts, terms, bpc-480 and links-map sets, in one go-ahead, with one label for *reference role* / *reference
   type* and the `PROPOSED` set in `publish/wikibase.py` retired?
2. **Parent organisation.** A dedicated property (recommended), or `P9 part of` as entities-contacts 1.7 planned?
3. **Holders.** Keep the display of current holders off (recommended), or allow the live single-statement rule
   of 1.7?
4. **Rungs on the wiki.** Rungs as Wikibase items (recommended, reviewed rungs only), or on DokuWiki pages only?
5. **Legal readings.** Exhaustion, binding effect and venue are legal judgements. Who reviews them beyond the
   text-quote rule? Until someone does, pages say "the statute does not say".
6. **Court rules.** Should the corpus add court rules? Twelve rungs depend on them.
7. **Tier B.** Should the 1,140 US Govdirectory bodies ever be loaded? This note says only on demand, when a
   process needs them wholesale (for example the NC licensing boards).

---

## 9. Method, and what this pass found

### 9.1 Method

* **Read.**
  * The four research notes and the five design notes named at the top.
  * `fixtures/authority/ladders.json` (22 ladders, 143 rungs, 90 bodies) and `fixtures/entities/agencies.json`.
  * `curated/fl/business.json` and `curated_ask/license_conviction/ca.json`.
  * `lexflow/ir.py`, `bpmn_xml.py`, `extract/compile.py`, `dmn_xml.py` and `publish/wikibase_lexipedia.py`, for the
    hooks cited by name.
* **Statute text,** from the lexflow index (open-us-law v2026.09.1), read in the `lexflow-app-1` container with
  `I.lookup`:
  * Fla. Stat. §§ 20.02, 20.05, 20.10, 605.0201, 605.0210, 607.0120, 607.0125, 607.0126, 607.0201, 607.0202 and
    607.01401;
  * Cal. Bus. & Prof. Code §§ 22, 100, 101, 108, 109, 129, 153, 310, 477, 480, 485, 486, 487, 7000, 7000.5 and
    7011;
  * Cal. Gov. Code §§ 11500, 11502 and 11523.
* **Code run read-only:** `lexflow.law.xref.references()` on 11 of those sections, and `lexflow.law.terms.definitions()`
  on four. No lexflow job, build, benchmark or Ollama call was run.
* **Network, read-only:**
  * one WDQS query over 7 items (the Florida Division and Department, DCA, CSLB, the Board of Registered Nursing,
    BCSA and the Leon County court);
  * one `wbsearchentities` call for the Florida Secretary of State post;
  * one WDQS query on that post (classes, jurisdiction and a count of holder statements; no names read);
  * one search for a DCA director post, which found none;
  * two earlier calls that returned nothing.

  Each was at least 1.2 s apart, with the User-Agent `lexflow-research/0.1 (https://github.com/alibama/lexflow)`.
  No `.env` value was read.
* **The revision** (after [verify-authority.md](verify-authority.md)). Every fact changed was checked again,
  read-only:
  * statute text, with `I.lookup` in the container: Fla. Stat. §§ 205.023, 605.0210, 607.0123 and 607.0125; Cal.
    Bus. & Prof. Code §§ 108, 109, 480(i), 485, 486, 7000.5 and 7011; Cal. Gov. Code §§ 11517, 11521 and 11523; Tex.
    Gov't Code §§ 552.301 and 2001.146; N.C. Gen. Stat. § 132-6.2. The `act_id` of seven sections, for the rung key
    rule;
  * files: `ladders.json` (ladder sources and rung counts, the `fl.business`, `nc.records`, `tx.records` and
    `ca.license_conviction` rungs, shared body keys, long quotes, pinpoints with two rungs), `agencies.json` (shared
    QIDs), `curated/nc/records.json`, `publish/wikibase_lexipedia.py`, `publish/wikibase.py`, entities-contacts 1.2–1.4
    and 5, authority-wikibase 2.6, bpc-480 and links-codebase-map;
  * Lexipedia's query service, 7 queries: 1,413 items with a P25 key; 0 qualifiers and 0 references; the 48 process
    keys (none for a licensing or sealing question); the California and Florida statute keys; the five example
    items (Q164, Q774–Q776, Q784);
  * Wikidata: one `wbgetentities` call (labels and descriptions of Q7707525, Q16932596, Q7443383, Q136430659 and
    Q5461329) and one WDQS query (their P31 only; no holder data read);
  * Govdirectory: `sitemap.xml`, once (21,084 distinct QIDs; Q136430659 under North Carolina);
  * mediawiki.org: the *Wikibase/Federation* page, once.

  Requests were one at a time and at least 2 s apart per host, with the same User-Agent. Nothing was written
  anywhere but this file.
* **Written:** this file only. The helper scripts sit in the session scratchpad.

### 9.2 Findings from this pass

1. **The law can rule out the organisation chart in so many words.** Cal. BPC § 109(a) makes a board's decisions
   "with respect to setting standards, conducting examinations, passing candidates, and revoking licenses" "not
   subject to review by the director", "except as provided in this section". A § 480 denial fits as "passing
   candidates" (§ 108 speaks of "passing upon applicants"): a sound reading, stored as an inference. It is the
   clearest statutory proof that a parent body is not an appeal body, and it becomes a negative grant (3.1).
   § 109(c) keeps the director a power to intervene on probable cause of a crime, as oversight.
2. **California's code-wide rule for "the board" is not extracted.** BPC § 22 ("refers to the board in which the
   administration of the provision is vested") is not returned by `terms.definitions()`, because "refers to" is not
   one of its definition forms. BPC § 477(a) is returned (`lexflow:term:ca:Cal. BPC § 477:board`, scope Division
   1.5).
3. **`xref.references()` has gaps for authority work.**
   * It returns no reference for Fla. Stat. § 607.0126: the court is named in words.
   * It labels two PEN § 290 references in BPC § 480 as `authority`, though they are scope references.
   * It returns nothing for "regulations adopted by the board".
   * It labels BPC § 485's citation of Gov. Code ch. 5 both `procedure` and `prerequisite_process` (the same span
     twice).

   So the `authority` role can propose power grants, never edges.
4. **Wikidata lacks links the statutes give.**
   * The Florida Department of State (Q11969252) has no P749, P2388 or P1001. Its only P355 child is the Division
     of Historical Resources.
   * The Secretary of State of Florida post (Q7444366, P31 *public office*, P279 *state secretary of state*) has no
     P2389 and no P748, though Fla. Stat. § 20.10(1) gives both.
   * The Florida Division of Corporations (Q107179384) is typed P31 *database* (Q8513), beside *registration
     authority*, *government agency* and *state agency of Florida*.
   * The Contractors State License Board (Q5020359) has no P749, though BPC § 7000.5(a) places it in DCA.
   * DCA (Q5020410) → the Business and Consumer Services Agency (Q136668814) → State of California (Q5589189) is
     present, matching BPC § 100(a).
   * No Wikidata post for the Director of Consumer Affairs was found.
5. **QID placement in `ladders.json`.**
   * `lexflow:position:va:tax_commissioner` carries Q116797530 with `qid_status: exact`. That item is the Virginia
     Department of Taxation (the fixture's own note says so). A loader that writes P8 for every `exact` would put
     an agency's QID on a post. The QID belongs on `lexflow:agency:va:department_of_taxation`, and the post has no
     Wikidata item.
   * The reverse error: `lexflow:agency:tx:office_of_the_attorney_general` carries Q7707525 marked `exact`, but
     Q7707525 is *Texas Attorney General*, P31 *position*. The QID belongs on `lexflow:position:tx:attorney_general`.
     Its English description reads "head of the Texas Department of Criminal Justice", a candidate upstream draft
     (5.8).
   * `lexflow:office-type:md:court_of_disposition` carries Q16932596, the Maryland District Court, marked `exact`.
     The type covers the District Court and the circuit courts, so the QID belongs on the District Court itself.
   * Nine agency keys carry a parent's or a position's QID, correctly labelled `parent` or `position`. Among them:
     the D.C. Mayor's post (Q5190572) on the Mayor's Office of Legal Counsel; the NY Department of State (Q17110658)
     on the Committee on Open Government; and the Illinois Attorney General's post (Q3406491) on the Public Access
     Counselor, whose own item is Q104879968.
   * The fix is the kind check of 1.3 and new position items: `lexflow:position:dc:mayor` as the reviewing post,
     with a curated `delegates-to` to the Office of Legal Counsel.
6. **The corporation and LLC routes match on corrected filings in Florida.** Fla. Stat. § 607.0123(3) gives a
   corporation the same 60-day corrected return, keeping the original filing date, that § 605.0210(4) gives an LLC.
   A corporation-route ladder can copy that rung, citing chapter 607's own section (2.3).
7. **The fixture misses one rung of a reviewed model.** `curated/nc/records.json` has `request_fee_mediation`
   (requester → State CIO, G.S. § 132-6.2(b)), and `nc.records` has no rung for it (3.7). The NC Chief Information
   Officer office (Q136430659) is on Govdirectory's NC list, so once the rung exists one ladder body is listed there.
