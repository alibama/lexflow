# Authority, posts and escalation: standards and a model for lexflow

Status: design (research and recommendations), 2026-10-10. Nothing was written to the database, the wiki,
lexipedia.wikibase.cloud, Wikidata or Govdirectory. Every web source in §9 was opened on this date. Network reads
were read-only GETs with the User-Agent `lexflow-research/0.1 (https://github.com/alibama/lexflow)`, at most one
request per second per host, and one SPARQL query at a time. Statute text comes from the lexflow index
(open-us-law v2026.09.1, `I.lookup`).

This note answers one question and designs two things:

* **The question.** Does the Lexipedia Wikibase need every Govdirectory entity loaded, so that processes can
  cross-reference people and organisational units?
* **The entity model.** How lexflow should represent organisations, units, posts (offices) and their relations,
  building on [entities-contacts.md](entities-contacts.md).
* **The escalation model.** How lexflow should represent the ways a matter moves to another authority (appeal,
  review, enforcement) or is held back or handed off (extension, referral, consultation, remand), building on
  [bpc-480-decision.md](bpc-480-decision.md) and [links-codebase-map.md](links-codebase-map.md).

Scope rules followed throughout:

* People appear only as holders of public offices, as Wikidata records them. This note copies no holder's name, no
  contact detail and nothing about private individuals. The holder counts in §1.3 are counts only.
* The recommended model has posts and no persons.
* Researchers are cited as authors of their published work only.

---

## 0. The short answer

**No. Do not load all Govdirectory entities. Do add a small set of classes and properties, then load the bodies,
posts and review routes that reviewed models use.** The reasons, from §1:

1. **Govdirectory does not cover most of the corpus.** Its US lists are federal (374 entries, mostly embassies),
   New York (159) and North Carolina (607) ([entities-sources.md](entities-sources.md) §2.2). Of the 98 specific
   bodies that lexflow's models and reference answers name, 6 are on a Govdirectory list (4 in NC, 2 in NY).
2. **Govdirectory and Wikidata hold little hierarchy and almost no review structure.**
   * Of the 497 New York and North Carolina state agencies on Govdirectory's lists, 30 have a parent organisation
     (P749) and 28 a head post (P2388).
   * Wikidata's *appeals to* (P12452) is on 7 items in the 11 corpus jurisdictions, and on none in VA, MD, TX, FL,
     WA or NC.
3. **The escalation path comes from the statute, not the org chart.** In the 22 reviewed models, decisions are
   reviewed, ruled on or overseen by the head of the deciding entity, a mayor, a public access counselor in an
   attorney general's office, an attorney general, an open-government committee and courts.
   * Most of these sit outside the deciding body's hierarchy.
   * Which one applies can turn on where the deciding body sits. For example, D.C. Code § 2-537(a-1) sends Council
     records straight to court, not to the Mayor.
4. **People are not needed, and Wikidata's holder data would mislead.** The 13 posts checked have 286 *position
   held* statements. Only 112 of them have a start date and 103 an end date, so "no end date" cannot identify a
   current holder. A process needs the post ("the head of the entity"), not the person.

**What the Wikibase needs** (each item is a wiki write, so it waits for the user's go-ahead; decide it together
with the property sets in entities-contacts §8.1 and terms-wikibase §4):

* **Classes:** *government agency* and *office type* (already proposed in entities-contacts §1.7), plus
  *organisational unit*, *post* and *review route*.
* **Properties:** about ten. The organisational ones are *parent organisation*, *post in*, *head post*,
  *reports to*, *competent authority*, *decided by* and *auxiliary party*. The route ones are *route from*,
  *route to*, *invoked by*, *route kind*, *exhaustion* and *next route*. See §6.2.
* **Items:**
  * the 98 specific bodies of `agencies.json` (entities-contacts plans about 200 agencies once courts are added);
  * about 50 office types;
  * 20 to 40 posts and post types;
  * about 50 routes for the 22 models and the 15 answers that have steps. Each links to Wikidata with P8 *exact match* where an exact item
  exists, and to Govdirectory with *described at URL* for the 6 listed bodies.
* **Not needed:** a mirror of Wikidata or Govdirectory, any person items, or federated properties. Wikibase's
  federated properties cannot coexist with the wiki's existing local properties (§2.12).

---

## 1. What lexflow has today (measured 2026-10-10)

### 1.1 Actors, routes and deadlines in the curated data

| Measure | 22 reviewed models (`curated/<st>/<q>.json`) | 15 reference answers with steps (`curated_ask/*/*.json`; 30 answers in all) |
|---|---|---|
| Actors by kind | private-party 33, public-body 21, court 13, other-government 12, official 9 (88) | public-body 17, private-party 17, official 16, court 11, other-government 5 (66) |
| Steps | 275. Kinds: filing 71, decision 52, notice 52, act 35, payment 28, record 23, inspection 8, hearing 4, review 2 | 199 |
| Route-like steps (a private party files, petitions, appeals or sues to a public body or court; a heuristic count) | 24 steps in 13 models: to a court 11, to the deciding body again 7, to another body 6 | 24 steps in 11 answers: to a court 12, to the deciding body 7, to another body 5 |

Deadlines (`FDeadline`), across both sets: 86 in all.

* By consequence: unstated 45, right-lapses 26, deemed-denial 13, action-invalid 1, directory-only 1.
* One deemed approval has no consequence value of its own. The VA licensing answer codes Va. Code
  § 2.2-4021(B), where a late decision counts in the applicant's favour, as `unstated` with
  `on_miss: deemed_favorable`.

Modality and authority vocabulary:

* `FStep.modality` has obligation, permission, prohibition, right and none, but no *power*.
* The IR's `Deontic` type already allows `power` and `duty-to-decide` (`ir.py:43`). Only one hand-built gold model
  uses `duty-to-decide` (`gold.py:169`).
* The Wikibase has P17 *bearer*, but nothing for the step's `recipient`.

### 1.2 Cross-references and bodies

* **Gold cross-references** (`fixtures/xref/gold_{a,b,c}.json`, 893 references): `authority` 81, `procedure` 96,
  `prerequisite_process` 76. `lexflow/law/xref.py` assigns these roles from cue words. Its `AUTHORITY` pattern
  covers "authorized … by", "powers … under" and "regulations adopted pursuant to". Its `AUTHORITY_AGENT` pattern
  covers "agency … designated under". These are the statute-side seeds for authority links.
* **Bodies** (`fixtures/entities/agencies.json`): 144 entries. 98 are specific bodies and 46 generic roles; 70 are
  exact Wikidata matches.
  * 8 entries resolve to a **position** item, not an organisation:
    * 5 as exact matches: the US Attorney for DC, the DC Attorney General, the Illinois and Texas Secretaries of
      State, and the Texas Attorney General;
    * 3 as "parent body only": the DC Mayor (named for FOIA appeals), the Illinois Attorney General (for the
      Public Access Counselor) and the Maryland Attorney General (for the Public Access Ombudsman).

    Review bodies are exactly where Wikidata has a post and no office.
  * 6 bodies are on a Govdirectory list.

### 1.3 Organisation and post structure in Wikidata (read-only SPARQL)

| Set | Items | Parent org (P749) | Child org (P355) | Head post (P2388) | Organisation directed by the post (P2389) | Authority (P797) |
|---|---|---|---|---|---|---|
| The 91 QIDs in `agencies.json` (bodies, units, related positions; 9 are typed directly as *position*) | 91 | 29 | 10 | 10 | 5 (2 of the 9 positions) | 1 |
| Govdirectory's *state agency of New York* (Q134016126) | 97 | 16 | – | 13 | – | 1 |
| Govdirectory's *state agency of North Carolina* (Q133309046) | 400 | 14 | – | 15 | – | 0 |

Two other properties:

* *appeals to* (P12452): 3,064 uses in all, 107 on US items (mostly federal circuit courts to the Supreme Court).
  In the corpus jurisdictions there are 7: NY 3, and DC, CA, IL and OH 1 each.
* *reports to* (P10645), which links one position to another: 9,974 uses, 24 on US items. The sample is federal
  defence posts.

**Holders (counts only, no names).** The 13 posts that lexflow's bodies point at carry 286 non-deprecated *position
held* (P39) statements:

* 112 have a start date (P580) and 103 an end date (P582);
* 183 have no end date, although at most one or a few holders of each post are current;
* the *position holder* (P1308) statements on the 9 position items carry no date qualifiers at all.

So Wikidata cannot reliably say who holds a post now.

### 1.4 The Lexipedia Wikibase

* Properties P1–P25 exist and P26–P30 do not, the same as in [links-codebase-map.md](links-codebase-map.md) §3.1.
* The wiki runs MediaWiki 1.43.11 with WikibaseRepository, WikibaseClient, **EntitySchema**, WikibaseManifest and
  WikibaseCirrusSearch. EntitySchema means ShEx shapes can be stored on the wiki itself (§6.3).

---

## 2. Standards: what each offers lexflow

### 2.1 W3C Organization Ontology (ORG)

A W3C Recommendation of 16 January 2014. Terms that matter here:

* `org:Organization`, `org:FormalOrganization` (recognised in law) and `org:OrganizationalUnit` (a part that has
  no standing outside its parent).
* `org:subOrganizationOf`, its transitive form and its inverse `org:hasSubOrganization`; `org:unitOf` and
  `org:hasUnit` for units.
* `org:Post`: a position that exists apart from whoever fills it. `org:postIn` and `org:hasPost` link it to its
  organisation; `org:holds` and `org:heldBy` link it to an agent.
* `org:reportsTo`: a reporting line like those on an organisation chart. It may join agents or **posts**.
* `org:Role`, and `org:Membership`, an n-ary link (agent, organisation, role) with `org:memberDuring` for time.
* `org:headOf`, which is agent-level: a person heads an organisation.
* `org:classification`, `org:purpose` and `org:identifier`.
* `org:ChangeEvent` with `org:resultedFrom`, `org:changedBy` and `org:originalOrganization`, for mergers and
  renamings.

**For lexflow:**

* ORG is the right backbone. Post versus person is exactly the line this note draws: lexflow models posts and
  never fills `org:heldBy`.
* `org:reportsTo` between posts gives the "officer → head" line. Statutes use that line when they say "the head
  of the agency or a designee".
* ORG has no time property on `Post`; a post's creation and abolition are `ChangeEvent`s. This fits
  entities-contacts' rule that keys never change and abolished bodies get a status and a successor link.
* Wikidata maps its own properties onto ORG: P749 ≡ `org:subOrganizationOf`, P355 ≡ `org:hasSubOrganization`,
  P39 ≡ `org:holds`, P1308 ≡ `org:heldBy`.
* Wikidata also maps P2389 to `org:postIn`, but P2389 means "the organisation this office *directs*". That is
  narrower than `postIn`. lexflow should keep *post in* and *head post* as two relations.

### 2.2 Popolo and Open Civic Data

Popolo defines Person, Organization, Membership, Post, Contact detail, Area, Motion, Vote event, Count, Vote,
Event and Speech. Its last change entry is dated 2022-11-10.

* **Post:** `label`, `role`, `organization`, `area`, `start_date`, `end_date`, contact details and links. The spec
  warns that a post is not a role.
* **Membership:** a member (a person *or* an organisation) and an organisation or a post, with `role`, `label` and
  start and end dates. People hold posts *through* memberships, and Popolo tells implementers not to use
  `org:holds` directly.
* **Organization:** `classification` (one string), `parent`, `other_names` (former names too) and `identifiers`.

Open Civic Data builds on it:

* OCDEP 5 (accepted 2014-06-12) adopts Popolo's Person, Organization, Post and Membership with small changes. A
  Post gets a `division_id`, and an Organization a `jurisdiction_id`.
* OCDEP 2 (accepted 2014-06-06) defines division identifiers such as `ocd-division/country:us/state:nc/county:wake`.

**For lexflow:**

* Popolo's dated Post (start and end) is better than ORG's for statutory offices that a statute creates or
  abolishes.
* Its Membership is the thing lexflow does not store.
* The OCD division id is a useful crosswalk column for `lexflow:jurisdiction:` and `lexflow:gov:` keys: civic-tech
  datasets of officials and legislatures are keyed by it. It is a column, not the key, by the same rule as
  entities-contacts D3.

### 2.3 schema.org

* `GovernmentOrganization` is a subtype of `Organization`. It inherits `parentOrganization`, `subOrganization`,
  `department` (a part described as an organisation in its own right), `member`, `memberOf` and `areaServed`.
  Govdirectory already emits `GovernmentOrganization` JSON-LD on its pages (entities-sources §2.3).
* `GovernmentService` has `jurisdiction`, `serviceOperator` (the operator when it differs from the provider),
  `provider`, `serviceType` and `availableChannel`.
* `Role` (with `roleName`, `startDate`, `endDate`) can sit between an organisation and a member to date the link.

**For lexflow:** this is the publishing vocabulary, not the model.

* DokuWiki agency pages can carry `GovernmentOrganization` JSON-LD with `parentOrganization` and `sameAs`
  (Wikidata, Govdirectory).
* Process pages can carry `GovernmentService` with `provider` set to the competent body and `jurisdiction`.
* This makes Lexipedia pages machine-readable the same way Govdirectory's are.

### 2.4 EU CPOV and CPSV-AP

* **CPOV 2.1.2**, the Core Public Organisation Vocabulary:
  * Its `PublicOrganisation` is a subclass of `org:Organization`. It reuses `org:subOrganizationOf`,
    `org:hasUnit`, `org:classification`, `org:purpose` (ideally a COFOG code) and `org:ChangeEvent`.
  * It adds `dct:spatial` for the area an organisation covers.
  * It defines no post.
* **CPSV-AP 3.2.0**, the Core Public Service Vocabulary Application Profile. Its Public Service has these
  properties:
  * *has competent authority* (the public organisation responsible, at least one);
  * *has legal resource* (the legislation behind the service);
  * *requires* (another public service it uses);
  * *has input* (Evidence) and *produces* (Output);
  * *has channel*, *follows* (Rule), *is grouped by* (Event);
  * *has participation*, a Participation that gives an Agent a *role* within the service.

**For lexflow:** CPSV-AP is the closest existing model of "a legal process with a responsible authority and
prerequisite processes".

* *Has competent authority* is the process-level authority link lexflow lacks.
* *Requires* matches the provides/requires status links of bpc-480-decision §6.2.
* Participation-with-role matches lexflow's per-process roles.
* New Lexipedia properties should carry these as P7 *equivalent property* mappings, with the IRIs taken from the
  3.2.0 specification.

### 2.5 Wikidata properties

These were read from each property's own entity page (§9):

| Property | Meaning (Wikidata's description, paraphrased) | Constraint or mapping noted on the property | Use in lexflow |
|---|---|---|---|
| P749 parent organization or unit / P355 child | containment | ≡ `org:subOrganizationOf` / `org:hasSubOrganization`, `schema:parentOrganization` / `schema:subOrganization`. P31 Q10387680 (organization unit) marks a unit. | seed for *parent organisation*, only for `exact` QIDs |
| P2388 position held by head of the organization / P2389 organization directed by the office or position | the post that heads a body, and its inverse | P2389 ≡ `org:postIn` (loose, see §2.1) | seed for *head post*. It resolves "the head of the entity". |
| P10645 reports to | position → position | subject and value: position (Q4164871) | seed for *reports to*; sparse in the US |
| P12452 appeals to | court or other body that hears appeals from the subject's decisions | subject: governing body (Q895526) | court hierarchy only. Statutory review routes are lexflow's own (§5). |
| P2098 substitute/deputy/replacement of office/officeholder | the post that stands in | subject: position | can seed a *designee* edge where present |
| P797 authority | entity having executive power over the subject | none | too vague to use |
| P1001 applies to jurisdiction | an office, institution or law has power over or applies to a territory | | ≡ Lexipedia P15 |
| P39 / P1308 position held / position holder | person ↔ post | ≡ `org:holds` / `org:heldBy` | **not stored** (§4.5) |
| P5052 supervisory board member | a *person* on a supervisory board | value: human | not an organisational supervision link; do not use |

### 2.6 BPMN 2.0.2 (OMG formal/13-12-09)

* **Escalation**, §8.4.4 and the event tables in §10.5:
  * An escalation names a business situation that the process may need to react to, with an `escalationCode`.
  * An escalation propagates up the process hierarchy, from a sub-process or a called process to the innermost
    enclosing scope that catches it (§10.5.1). Through a call activity it passes from the called element to the
    call activity, where its boundary can catch it (§10.3.6).
  * An escalation is **non-critical**: execution goes on where it was thrown. An error is critical and stops
    execution there (§10.5.1).
  * An escalation boundary event is non-interrupting by default, although a modeller may make it interrupting.
    An error boundary event always interrupts (§10.5.4, Table 10.90).
  * An escalation event sub-process is meant to speed up an activity that fails a constraint such as a deadline
    (§10.5.2).
  * Camunda's engine documentation adds that an uncaught escalation raises no incident.
* **Messages:** a message flow must connect two separate pools and may not join objects in the same pool (§9.4).
  Messages are the cross-participant mechanism.
* **Call activity** (§10.3.6): invokes a reusable process and may override its resource roles.
* **Boundary timer events** (Table 10.90): can interrupt or not. lexflow's compiler already turns agency
  deadlines into interrupting timers, or non-interrupting ones for directory deadlines (`extract/compile.py:11-12`,
  `:85-97`).
* **Lanes** (§10.8): BPMN leaves their meaning open. They are often used for internal roles or departments, and
  they can be nested.
* **Resource assignment** (§10.3.1, §10.3.4.1): `ResourceRole`, `Performer`, `HumanPerformer` and
  `PotentialOwner`, with a `ResourceAssignmentExpression`. BPMN points to WS-HumanTask for people assignment.

**For lexflow:**

* **An appeal to another body is a message flow between pools, never an escalation event.** BPMN escalation stays
  inside one process hierarchy and does not cross participants.
* Use escalation events only for hand-ups inside one body's own process, where the law moves the matter to a
  superior post of the same body. Examples are an officer's matter going to "the head of the agency or a
  designee", or a called internal-review sub-process signalling its parent.
* Use timers for statutory clocks, and lanes per post inside a body's pool.

### 2.7 WS-HumanTask 1.1 (OASIS Committee Specification 01, 17 August 2010)

* **Generic human roles** (§3.1): task initiator, task stakeholders, potential owners, actual owner, excluded
  owners, business administrators and notification recipients.
* **Deadlines and escalations** (§4.9):
  * A task has start and completion deadlines. Each has one or more escalations, and each escalation has an
    optional condition and exactly one action: a notification or a *reassignment*.
  * A reassignment replaces the potential owners.
* **Delegate and forward** (§4.10.3): to *delegate* makes one named user the actual owner; to *forward* replaces
  the forwarder among the potential owners.

**For lexflow:**

* This is the most concrete published semantics of "deadline missed → escalate to someone else".
* *Excluded owners* is the right notion for "the reviewer must not be the person who decided".
* lexflow models law, not task engines, so it should borrow the concepts, not the XML.

### 2.8 DMN 1.3 (OMG formal/2021-01-01; DMN 1.6 is the latest formal version, adopted September 2026)

* **Knowledge sources** (§5.2.1): may model the governance of human decision-making by people (a manager),
  regulatory bodies (an ombudsman), documents or legislation, and they can be chained.
* A **KnowledgeSource** (§6.3.12) has a `locationURI`, a `type` (for example "Regulation") and an **`owner`**,
  which is an organisational unit.
* An **authority requirement** (§6.2.2.3) runs from a knowledge source to a decision, a business knowledge model or
  another knowledge source. Knowledge sources and authority requirements have no execution semantics.
* A **Decision** (§6.3.7) may list `decisionMaker` and `decisionOwner`, both organisational units, plus
  `usingProcess` and `usingTask`.
* **OrganizationUnit** (§6.3.8) has a `URI` and lists `decisionMade` and `decisionOwned`. The specification calls
  it a placeholder for a future organisation metamodel. The local XSD (`schemas/dmn/DMN13.xsd:132-138`) has the
  element.

**For lexflow:** DMN already has slots for who decides and whose rules govern. Fill them with lexflow keys:

* `decisionMaker` → an `organizationUnit` whose `URI` is the post or agency key, for example
  `lexflow:post-type:ny:entity_head`;
* `knowledgeSource@owner` → the body that issues the source, for example the Illinois Attorney General for a
  Public Access Counselor binding opinion;
* the reviewing decision (an appeal determination) gets an information requirement on the decision it reviews.

bpc-480-decision already uses knowledge sources and authority requirements for statutes. This adds the
organisational side.

### 2.9 Legal theory that is useful for modelling

* **Hohfeld's incidents.** Hohfeld (1913; 1917) set out eight positions.
  * Power and liability are correlatives, and so are immunity and disability. A power is the ability to change
    one's own or another's legal relations; an immunity is the absence of another's power to change one's own.
    These are the definitions in Wenar and Cruft's encyclopedia entry (revised 2025).
  * In escalation terms:
    * the right to appeal is a **power** of the affected party;
    * the decider is under a **liability**: its decision can be changed;
    * the reviewer has a **power** to affirm, reverse or order, and usually a **duty** to decide within a time;
    * a bar such as Cal. BPC § 480(b)–(c) gives the board a **disability**, and the applicant an **immunity**.
  * Formal treatments:
    * Allen and Saxon's A-Hohfeld language (ICAIL 1995);
    * Sartor (2006);
    * UFO-L's power–subjection pattern (Griffo et al. 2018; 2022), which argues that power–subjection relations
      can be primitive, with other relations created from them by institutional acts;
    * eFLINT (van Binsbergen et al. 2020), an executable norm language built on transition systems and Hohfeld's
      framework, in which acts held by actors create and end duties.
* **Delegation.**
  * Federal law lets an agency head delegate "to subordinate officials the authority vested in him" for listed
    matters (5 U.S.C. § 302(b)).
  * State texts in the corpus write delegation into the rule itself: "the head of the agency or a designee" (Cal.
    Gov. Code § 7922.535(b)); "the head, chief executive or governing body of the entity, or the person therefor
    designated" (N.Y. Pub. Off. Law § 89(4)(a)).
  * LKIF Core has *Mandate* ("give someone authority to act") and *Delegation* ("entrust a task or responsibility
    to another") as classes, beside *Public_Body* and *Decision* (a written decision of a public body exercising
    a public power).
* **Administrative review, finality and exhaustion.**
  * Under the federal APA, action that is otherwise final is final whether or not reconsideration or "an appeal to
    superior agency authority" was sought. A statute, or a rule that makes the action inoperative meanwhile, can
    require such an appeal first (5 U.S.C. § 704).
  * Courts may not add an exhaustion requirement that neither statute nor rule imposes (*Darby v. Cisneros*, 509
    U.S. 137 (1993)).
  * The doctrine's purposes are to avoid premature interruption of the agency process, to let the agency build the
    record and correct itself, and judicial efficiency (*McKart v. United States*, 395 U.S. 185 (1969)).
  * State statutes in the corpus say it outright:
    * New York: Article 78 review lies from "an appeal determination" (§ 89(4)(b)).
    * D.C.: a requester whose request goes unanswered "shall be deemed to have exhausted" administrative remedies
      (§ 2-532(e)).
    * Washington: internal review is deemed complete after the second business day and "shall constitute final
      agency action" for judicial review (RCW 42.56.520(4)).
    * Texas: "A timely motion for rehearing is a prerequisite to an appeal" (Gov't Code § 2001.145(a)), and the
      motion is "overruled by operation of law" if the agency does not act (§ 2001.146(c)).
    * Illinois: a denial notice must name *both* Public Access Counselor review and judicial review (5 ILCS
      140/9(a)), and a suit does not require going to the Counselor first (140/11, as the curated IL model
      records).

  **Exhaustion is a property of the route, set by the text, and it varies by state. lexflow should record it from
  the text and never infer it.**

### 2.10 LegalRuleML Core 1.0 (OASIS Standard, 30 August 2021)

* **Authority** (§4.3.4): a person or organisation with the power to create, endorse or enforce legal norms. Its
  purpose is the provenance of rules.
* **Jurisdiction** (§4.3.3): a geographic area *or subject matter* over which an authority applies its legal
  power.
* **Agent, Figure and Role** (§4.3.2):
  * an *Agent* acts;
  * a *Figure* is the instantiation of a function by an actor (the function "Senator", filled by an agent);
  * a *Role* ties an actor to an expression.
* **Bearer** and **AuxiliaryParty**: the role a deontic specification is directed at, and a role it relates to.
* **Context and Association** with `appliesAuthority` and `appliesJurisdiction`, and **Override** and
  **Defeater** for defeasibility.

**For lexflow:**

* LegalRuleML's *Authority* answers "who made this norm", not "who decides this case". Lexipedia statute items
  can carry it later, from ELI's `passed_by`.
* Its *Figure* is the post (function) versus the agent (holder): the same line as ORG's Post.
* Lexipedia already has P17 *bearer* (`links-codebase-map` §3.1). It lacks the **auxiliary party**, which is
  exactly the facts' step `recipient` (the body a filing goes to). That property should be added (§6.2).
* *Jurisdiction as subject matter* matters for review bodies whose remit is a topic (open records), not a place.

### 2.11 Akoma Ntoso and ELI

* **Akoma Ntoso 1.0** (OASIS Standard, 29 August 2018):
  * The `<references>` block lists TLCOrganization, TLCRole, TLCPerson and TLCLocation entries (§5.10.12.1).
  * `refersTo` points any mention at a Top Level Class instance, and the `as` attribute on FRBRauthor points at a
    TLCRole (§5.8.2).
  * If lexflow ever emits Akoma Ntoso:
    * agencies are TLCOrganization;
    * posts and process roles are TLCRole;
    * `href` is the Lexipedia item URI;
    * TLCPerson stays unused.
* **ELI**, the ontology OWL published by the EU Publications Office (`owl:versionInfo` 1.4 at the URL fetched):
  * `eli:passed_by` (the legal author, such as a parliament);
  * `eli:responsibility_of_agent` (the responsible body, such as a ministry);
  * `eli:jurisdiction`;
  * `eli:based_on` (empowered by another work, such as an enabling act);
  * `eli:changes`.
  * For lexflow: `based_on` is the delegation chain for rules. A regulation is based on its enabling statute. That
    maps to the existing P14 *based on*, and to DMN knowledge source → knowledge source authority requirements.
    `passed_by` maps to LegalRuleML Authority.

### 2.12 Wikibase mechanics that bear on the answer

* **Federated properties.** They let a *fresh* Wikibase use another Wikibase's properties. They are for evaluation,
  not production, and they cannot coexist with local properties. Lexipedia already has local P1–P25, so they are
  not an option.
* **Wikibase.cloud mapping tables.** The Features tab of the instance settings has tables that map local entities
  to Wikidata entities. Together with P8 *exact match* and P7 *equivalent property*, this is how Lexipedia should
  point at Wikidata instead of copying it.

---

## 3. Literature: resource perspective, organisational mining and deriving routes

* **Workflow resource patterns** (Russell, van der Aalst, ter Hofstede and Edmond, CAiSE 2005; long version on the
  author's site).
  * The organisational model is resources in positions, with roles, units, a *direct report* and a *delegate*.
  * The patterns that map onto law:

    | Pattern | What it does |
    |---|---|
    | Role-based allocation (R-RBA) | allocate to a role |
    | Organisational allocation (R-OA) | allocate by position and relationship, for example "the manager of whoever did task X". This is the form of "the head of the entity". |
    | Deferred allocation (R-FBA) | name the resource only at run time. This is office-type instance resolution. |
    | Authorisation (R-RA) | who may perform a task |
    | Separation of duties (R-SOD) | the same resource may not do two given tasks |
    | Delegation (R-D) | a resource passes its allocated work item to another |
    | Escalation (R-E) | the system offers or allocates a work item to other resources to speed it up, usually after a deadline |

* **Resource assignment languages.**
  * RAL (Cabanillas, Resinas and Ruiz-Cortés 2012), and its analysis (Cabanillas et al. 2015, *Information
    Systems*), express assignments such as "a person in a position that reports to …" and check them at design
    time.
  * Stroppi, Chiotti and Villarreal (2015) define the resource perspective for process-aware systems.
  * Wolter and Schaad (BPM 2007) add task-based authorisation constraints (separation and binding of duty) to
    BPMN.
* **Organisational mining.**
  * Song and van der Aalst (2008) discover organisational models and social networks from event logs.
  * Van der Aalst, Reijers and Song (2005) mine hand-over-of-work and other social networks.
  * Schönig, Cabanillas, Jablonski and Mendling (2016) mine the organisational perspective efficiently.
  * lexflow has no event logs, so mining does not apply now.
  * The analogue for lexflow is *statute mining*: reading who hands what to whom from step actors and recipients,
    which the curated facts already hold.
* **Organisational models of agents.** MOISE+ (Hübner, Sichman and Boissier, SBIA 2002) types links between roles
  as acquaintance, communication or **authority**.
  * In the French version of the paper, an authority link lets the source role control the target role, and it
    implies a communication link, which implies an acquaintance link.
  * This is a clean precedent for typed authority edges between posts, separate from containment.
* **Legal constraints in process models.** Olbrich and Simon (2007) integrate legal constraints into
  public-sector process models. Process-compliance work is surveyed in [links-literature.md](links-literature.md)
  §3.
* **Deriving escalation or appeal routes from legislation.** No published method was found that reads statute text
  into a graph of which body reviews which decision, under which section, with which deadline and exhaustion rule.
  * Searches covered legal knowledge graphs, legal procedure ontologies, LegalRuleML procedural rules and BPMN
    legal modelling.
  * The nearest work models reasoning paths in judgments, or appeals as documents.
  * The pieces exist separately: cross-reference intent classification (links-literature §1), powers in eFLINT and
    UFO-L, remedies as properties of administrative acts, and DMN authority requirements. This note's §5 combines
    them. It is new work, so its first output should be checked against the curated models (§7).

---

## 4. Recommendations: the entity model

### 4.1 Decisions

| # | Decision | Why |
|---|---|---|
| A1 | **Model posts, not persons.** A post is an office that exists apart from its holder (ORG, Popolo, LegalRuleML Figure). lexflow stores no holder. | Privacy; processes need the office; Wikidata holder dates are incomplete (§1.3). |
| A2 | **Three organisational kinds plus generic forms.** Kinds: agency (organisation), organisational unit and post. Generic forms: office type (entities-contacts) and **post type**, a generic post resolved against an instance, such as "the head of the entity" or "the records access officer". | 46 of 144 fixture entries are generic. Statutes name relative posts ("the head of the agency"). |
| A3 | **Two kinds of edge, kept apart.** *Structure*: parent, unit-of, post-in, heads, reports-to. It comes from Wikidata for exact QIDs, from curated data and from statutes. *Authority*: who decides, who reviews, who must be consulted. It comes from statutes only, with quotes. | The review path is not the org chart (§0, point 3). MOISE+ separates containment from authority links. |
| A4 | **Relative targets.** An authority edge may name a target by its relation to the deciding body (`head-of`, `governing-body-of`, `parent-of`, `court-of-venue`). The structure edges resolve it when the answer is made. | Resource patterns R-OA and R-FBA. N.Y. § 89(4)(a) sends the appeal to the head of whichever entity denied. |
| A5 | **Branch and remit are attributes.** Each agency records its branch (executive, legislative, judicial or independent) and its level, from curated data. | Route scope rules turn on them. D.C. § 2-537(a-1) treats Council records differently, and 5 ILCS 140/9.5(a) excludes the General Assembly from Public Access Counselor review. Wikidata rarely records branch. |
| A6 | **Keys follow entities-contacts D2.** `lexflow:post:<scope>:<slug>` (`lexflow:post:dc:mayor`), `lexflow:post-type:<st>:<slug>` (`lexflow:post-type:ny:entity_head`), `lexflow:org-unit:<scope>:<slug>` and `lexflow:route:<model_id>:<route_id>`. QIDs are crosswalk columns only. | One key spelling. Organisational units do not take `lexflow:unit:`, because terms-wikibase already uses that prefix for *statutory* units. |

### 4.2 Mapping to the standards

| lexflow | ORG | Popolo | schema.org | CPOV / CPSV-AP | Wikidata | DMN | LegalRuleML |
|---|---|---|---|---|---|---|---|
| agency | `org:FormalOrganization` | Organization | GovernmentOrganization | PublicOrganisation | instance of a government agency class | organizationUnit | Authority (as norm source) |
| organisational unit | `org:OrganizationalUnit` | Organization (with `parent`) | `department` | `org:hasUnit` | P749 + P31 Q10387680 | organizationUnit | – |
| post | `org:Post` | Post | (Role.roleName) | – | position (Q4164871) | organizationUnit (URI) | Figure (function) |
| post type | `org:Post` + `org:Role` | Post.role | – | – | – | organizationUnit (URI) | Figure |
| process role (exists) | `org:Role` | Membership.role | – | Participation.role | – | – | Role |
| parent organisation | `org:subOrganizationOf` | `parent` | `parentOrganization` | `org:subOrganizationOf` | P749 | – | – |
| post in / head post | `org:postIn` / (agent-level `org:headOf`) | Post.organization | – | – | P2389 / P2388 | – | – |
| reports to | `org:reportsTo` | – | – | – | P10645 | – | – |
| competent authority (process → body) | – | – | `provider` / `serviceOperator` | *has competent authority* | – | decisionOwner | – |
| decided by (step or decision → post) | – | – | – | – | – | decisionMaker | – |
| auxiliary party (step → recipient role) | – | – | – | – | – | – | AuxiliaryParty |
| jurisdiction | – | Area / OCD division | `jurisdiction` | `dct:spatial` | P1001 | – | Jurisdiction |
| holder | `org:heldBy` | Membership | Role | – | P1308 / P39 | – | Agent |

The holder row is **not stored**.

### 4.3 Tables (new, synced-shaped as in entities-contacts §1.3)

```sql
CREATE TABLE IF NOT EXISTS posts (
  key TEXT PRIMARY KEY,           -- lexflow:post:dc:mayor | lexflow:post-type:ny:entity_head
  state TEXT NOT NULL,            -- dc | ny | us
  scope TEXT NOT NULL,            -- a state code, us, or a GID
  name TEXT NOT NULL,             -- "Mayor of the District of Columbia" | "Head, chief executive or governing body of the entity"
  kind TEXT NOT NULL,             -- head | officer | board | hearing_officer | counselor | generic
  generic INTEGER NOT NULL DEFAULT 0,  -- 1 for a post type
  post_in TEXT,                   -- agency, org-unit or office-type key (org:postIn)
  heads TEXT,                     -- agency key this post heads (Wikidata P2389), when it heads one
  reports_to TEXT,                -- post key (org:reportsTo; Wikidata P10645)
  relative TEXT,                  -- for a post type: head-of | governing-body-of | officer-of, applied to the instance
  wikidata TEXT, wikidata_match TEXT,   -- a position QID; exact | broader (never a person)
  aliases TEXT, status TEXT DEFAULT 'active',     -- active | abolished
  start_date TEXT, end_date TEXT,       -- the post's creation and abolition (Popolo), not anyone's tenure
  act_id TEXT, section TEXT, quote TEXT,          -- the words that create or name the post
  source TEXT, checked_at TEXT, updated_at TEXT NOT NULL, origin TEXT
);
```

* **New columns on `agencies`** (entities-contacts §1.3): `branch` (executive | legislative | judicial |
  independent), `remit` (subject matter, for review bodies) and `ocd_division` (a crosswalk).
* **New `entity_links` relations** (entities-contacts §1.4):

  | Relation | Subject → object | Source |
  |---|---|---|
  | `post-in` | post → agency, org unit or office type | curated; statute |
  | `heads` | post → agency | Wikidata P2388/P2389, exact QIDs only |
  | `reports-to` | post → post | curated; P10645 |
  | `unit-of` | org unit → agency | P749 with P31 organization unit; curated |
  | `designee-of` | post or post type → post | "or a designee" clauses; P2098 |
  | `decided-by` | step or decision → post, post type, agency or office type | the step's `actor`, resolved through `played-by` |
  | `competent-authority` | process → agency or office type | the deciding actor of the model's main decision |

  `part-of` stays for agency → agency or government, as entities-contacts has it. `unit-of` is the narrower case
  where the part has no standing outside its parent.

### 4.4 How a process cross-references posts and units

```
process role ──played-by──▶ office type / agency / post type ──(instance at answer time)──▶ agency instance
(lexflow:role:ny:records:appeals_officer)                                                     │
        │                                                     post type entity_head ──relative: head-of──┘
        └─ the step "decide_appeal" ──decided-by──▶ lexflow:post-type:ny:entity_head
                                                   → resolves to the head post of the record holder,
                                                     e.g. Wikidata P2388 of that agency, if exact
```

Resolution order for a post type: first the agency's own `heads` edge (curated or P2388), then its governing
board's post, then the post type itself, shown as a role ("the head of the agency that denied your request"). It
never falls through to a person.

### 4.5 People: the rule

* lexflow never stores who holds a post. Office-holder claims stay dropped when Wikidata responses are parsed
  (entities-contacts §5.4).
* A post item may link to its Wikidata position item. Whoever wants the current holder can read it there.
* Showing holders inside lexflow would need the user's decision. If it is ever wanted:
  * read live P39 statements with P580/P582 at render time;
  * show a holder only for an elected or appointed public office whose statement has a start date, no end date
    and is the only such statement;
  * never cache or log it.

  §1.3 shows that this test would often fail.

---

## 5. Recommendations: the escalation model

### 5.1 Terms

* **Escalate:** the matter goes to a body (or post) with power to change or review the decision. This is a power
  of the party who invokes it, and a liability of the decider.
* **Defer:** the matter is held back, or handed off for a ruling or advice, before the decision. This covers an
  extension of time, a referral for a binding ruling, consultation with a body that has competence, an advance
  determination, a stay, or a remand back down.
* **Inform:** the decider must tell an oversight body, which gets no power over the case.
* **Deemed outcome:** a statutory fiction that turns a missed deadline into a decision. It is not a route. It is a
  *trigger* that opens the next route, and it often satisfies exhaustion.

### 5.2 Route kinds, with corpus examples

| Kind | Direction | Invoked by | Target | Corpus example (statute, curated step) | BPMN form |
|---|---|---|---|---|---|
| `reconsideration` | escalate (same body) | affected party | the decider | Cal. Gov. Code § 11521 (petition deemed denied if not acted on), `ca` licensing `petition_reconsideration`; Tex. Gov't Code §§ 2001.145–.146, `tx` licensing `motion_rehearing` | message flow to the decider's pool; timer on its ruling |
| `internal_appeal` | escalate | affected party | relative: head or governing body of the decider, or a designee | N.Y. Pub. Off. Law § 89(4)(a), `ny.records:appeal`; RCW 42.56.520(4), `wa.records:internal_review` | message flow into the same pool, different lane (post) |
| `contested_hearing` | escalate (formal, same body) | affected party | the decider, often through a hearing officer or ALJ | Cal. BPC § 485(b) and Gov. Code § 11517 (OAH proposes, board decides); Va. Code § 2.2-4020; Tex. Gov't Code § 2001.051 | separate pool for the hearing body; the decision stays with the board |
| `external_review` | escalate | affected party | an independent body (absolute key) | D.C. Code § 2-537(a), Mayor, `dc.records:petition_mayor`; 5 ILCS 140/9.5, Public Access Counselor, `il.records:request_review` | message flow to the reviewer's pool |
| `judicial_review` | escalate | affected party | court office type, resolved by venue | N.Y. CPLR art. 78 via § 89(4)(b); Va. Code § 2.2-4026; RCW 42.56.550; N.C.G.S. § 55D-16; Md. Code SG § 10-222; Cal. Gov. Code § 11523 | message flow to the court's pool |
| `enforcement` | escalate | affected party | court | D.C. Code § 2-537(a)(2), suit when the body keeps withholding after the Mayor's order, `dc.records:sue_to_compel`; the binding opinion action under 5 ILCS 140/11(a-5) | message flow to the court's pool |
| `referral` | defer (up, binding) | the decider | a body whose ruling binds it | Tex. Gov't Code § 552.301(a): a body that wishes to withhold "must ask for a decision from the attorney general", `tx.records:request_ag_decision` | message flow from the decider to the reviewer; the decider's task waits on a message |
| `consultation` | defer (sideways) | the decider | a body with subject competence | RCW 19.02.070(4): the licensing department "must immediately notify the regulatory agency with authority to approve", `wa.business:notify_agency` → `agency_advises` | message flow and an intermediate message catch |
| `extension` | defer (time) | the decider (a post, often with a designee), or a court on petition | self, or court | Cal. Gov. Code § 7922.535(b), head of the agency or a designee, at most 14 days; D.C. Code § 2-532(d); Va. Code § 2.2-3704(C), petition the court for more time | a non-interrupting boundary escalation from the officer's task to the head's lane, where the law moves it up; otherwise a timer change |
| `advance_determination` | defer (before) | affected party | the decider or a designated body | Va. Code § 54.1-204.1 (predetermination); Tex. Occ. Code § 53.102; D.C. Code § 47-2853.12(n) | a separate short process, linked as a provider of a status (bpc-480 §6.2) |
| `remand` | return | court | the decider | the VA licensing answer: a court win means remand, not a licence | message flow back; the decider's process restarts at a named step |
| `notice_to_overseer` | inform | the decider | an oversight body | N.Y. § 89(4)(a), forward the appeal and the determination to the Committee on Open Government, `ny.records:forward_to_committee` | a send task with a message flow and no return |

Deemed outcomes, recorded on the deadline that causes them:

* **Deemed denial:** N.Y. § 89(4)(a) and (b); D.C. § 2-532(e); 5 ILCS 140/3; RCW 42.56.520(4); Cal. Gov. Code
  § 11521; Tex. Gov't Code § 2001.146(c).
* **Deemed in favour:** Va. Code § 2.2-4021(B), as coded in the VA answer.
* **Presumption against the decider:** Tex. Gov't Code § 552.302. A missed referral deadline makes the information
  presumed public.

The `FDeadline.consequence` vocabulary lacks a **`deemed-approval`** value. Add it when the extraction schema
thaws after AskBench; until then the route layer reads `on_miss`.

### 5.3 The route record

```sql
CREATE TABLE IF NOT EXISTS routes (
  key TEXT PRIMARY KEY,           -- lexflow:route:ny.records:appeal
  model_id TEXT NOT NULL,         -- ny.records (the DB model id form)
  state TEXT NOT NULL, question TEXT NOT NULL,
  kind TEXT NOT NULL,             -- §5.2
  direction TEXT NOT NULL,        -- escalate | defer | return | inform
  from_element TEXT NOT NULL,     -- the step, decision or outcome whose result is challenged or deferred
  trigger TEXT NOT NULL,          -- denied | deemed_denied | refused | no_decision | intends_to_deny | final_order | before_decision
  step TEXT,                      -- the model step that invokes the route (appeal, petition_mayor)
  invoked_by TEXT,                -- the process role holding the power (lexflow:role:…); null for a duty of the decider
  target TEXT,                    -- an agency, post, post-type or office-type key, when absolute
  target_rule TEXT,               -- JSON, when relative: {"rel": "head-of", "of": "decider", "or": "designee"}
  scope_rule TEXT,                -- JSON: when the route applies, e.g. {"decider.branch": {"not": "legislative"}}
  time_limit TEXT,                -- JSON FDeadline for invoking the route (amount, unit, anchor, consequence)
  reviewer_deadline TEXT,         -- JSON FDeadline for the target's duty to decide, with its deemed outcome
  exhaustion TEXT NOT NULL,       -- required | optional | alternative | constructive | none | unknown
  next_routes TEXT,               -- JSON list of route keys open after an adverse result or a lapse
  powers TEXT,                    -- JSON: affirm | reverse | order_disclosure | order_filing | remand | binding_opinion | advisory_opinion | award_costs | extend_time
  burden TEXT,                    -- decider | invoker | unstated
  standard TEXT,                  -- de_novo | error_of_law | substantial_evidence | unstated
  suspends TEXT,                  -- yes | no | unstated (does invoking it stay the decision)
  hohfeld TEXT,                   -- JSON: {"invoker": "power", "decider": "liability", "target": "duty-to-decide"}
  sources TEXT NOT NULL,          -- JSON list of quote-anchored sources {section, subsection, quote, act_id}
  method TEXT,                    -- curated-facts | xref | deadline | reviewer
  score REAL, status TEXT DEFAULT 'proposed',     -- proposed | accepted | rejected
  updated_at TEXT NOT NULL, origin TEXT
);
```

Rules for the record:

* **Every value comes from the text or stays `unknown`/`unstated`.** `exhaustion` is never inferred from the
  route's kind (§2.9).
* **The `sources` quote is mandatory.** `lex_checks`-style verification (`validate.py:126-160`) checks it, as for
  every other link.
* **Routes derived from `single` models stay `proposed`.** Only reviewed or agreed models publish, as the
  publishing rule requires.

### 5.4 Worked examples

**New York records (N.Y. Pub. Off. Law § 89).** Three routes:

1. `lexflow:route:ny.records:appeal`
   * kind and direction: `internal_appeal`, escalate;
   * from and trigger: `respond`, `decide_later`; `denied` or `deemed_denied` ("Failure by an agency to conform
     to the provisions of subdivision three of this section shall constitute a denial");
   * invoked by: `lexflow:role:ny:records:requester`;
   * target rule: `{"rel":"head-of","of":"decider","alt":["governing-body-of"],"or":"designee"}`, which is post
     type `lexflow:post-type:ny:entity_head`;
   * time limit: 30 days from the denial, `right-lapses`;
   * reviewer deadline: 10 business days from receipt, `deemed-denial` (§ 89(4)(b), last sentence);
   * powers: `affirm` (explain the further denial) and `order_disclosure` (provide access);
   * exhaustion: `required`. The Article 78 route is triggered by "an appeal determination";
   * next routes: `seek_review`.
2. `lexflow:route:ny.records:forward_to_committee`
   * kind and direction: `notice_to_overseer`, inform;
   * target: `lexflow:agency:ny:committee_on_open_government`;
   * attached to the same appeal.
3. `lexflow:route:ny.records:seek_review`
   * kind: `judicial_review`;
   * target: a court office type (CPLR art. 78), resolved by venue;
   * trigger: an adverse appeal determination or a deemed one;
   * burden: `decider` (§ 89(4)(b): the agency must prove the record is exempt);
   * exhaustion: `none` beyond the appeal.

**D.C. records (D.C. Code §§ 2-532, 2-537).**

* `petition_mayor`:
  * kind: `external_review`;
  * target: `lexflow:post:dc:mayor`, with Wikidata Q5190572 as the position;
  * scope rule: the record holder is not the Council (§ 2-537(a-1) sends Council records to court) and no other
    carve-out of (a-1) or (a-2) applies;
  * reviewer deadline: 10 business days, with no determination opening the court route;
  * powers: `order_disclosure` (§ 2-537(a)(2)).
* `sue`:
  * kind: `judicial_review` in the Superior Court;
  * triggers: the Mayor denies; the Mayor does not decide; or the requester is deemed to have exhausted remedies
    under § 2-532(e);
  * exhaustion for an actual denial: `required` (the Mayor first);
  * exhaustion after a deemed denial: `constructive`.
* `sue_to_compel`: kind `enforcement`, after a Mayor's order the body ignores.
* **What the route check would flag.** The curated DC model lets `sue_superior_court` follow `release_segregable`,
  an actual withholding, without the Mayor's petition. Section 2-537(a)(1) names the court route only after the
  Mayor's denial or silence, or after a deemed exhaustion. A reviewer should confirm or correct that edge. This is
  the kind of finding the checks in §5.6 exist for. It is not a verdict on the law.

**Illinois records (5 ILCS 140/9, 9.5, 11, 11.5).**

* `request_review`:
  * kind: `external_review`, to the Public Access Counselor in the Office of the Attorney General;
  * scope rule: not the General Assembly or its committees, commissions and agencies (§ 9.5(a));
  * time limit: 60 days;
  * exhaustion: `alternative`. Suit under § 11 is open without it;
  * powers: `binding_opinion` or mediation;
  * next routes: administrative review of a binding opinion (§ 11.5) and enforcement of it (§ 11(a-5)).
* The **remedy-notice rule** of § 9(a): every denial notice must name both routes. This becomes a check (§5.6).

**Texas records (Tex. Gov't Code §§ 552.301–.302).**

* `request_ag_decision`:
  * kind: `referral`, invoked by the decider (a duty);
  * target: `lexflow:agency:tx:attorney_general`;
  * time limits: ask within 10 business days of receiving the request, and submit the materials within 15
    business days of it;
  * on lapse: the presumption of § 552.302 (the information must be released unless there is a compelling reason).
* It shows deferral driven by authority: the body has no power to withhold on its own determination.

### 5.5 Deriving routes (deterministic first; no model calls)

1. **From curated facts.** A candidate route is a step whose actor is the affected private party, whose recipient
   is a public actor, and whose predecessor is a decision, a notice of denial or a deemed-outcome timer. The step's
   `source` quote is the route's source.
   * The 24 + 24 route-like steps of §1.1 are the seed set.
   * The target is the recipient's `played-by` entity. When the recipient is a post of the decider's own body
     (`appeals_officer`, `agency_head`), the target is relative.
2. **From deadlines.** A deadline with `deemed-denial` or a deemed `on_miss` becomes a trigger. Wording such as
   "deemed to have exhausted" or "shall constitute final agency action … for the purposes of judicial review" sets
   `exhaustion: constructive`.
3. **From cross-references** (`lexflow/law/xref.py`).
   * A `procedure` or `authority` reference to a known review statute becomes a candidate judicial or
     administrative route. Examples: an APA's judicial-review article (Va. Code § 2.2-4026), CPLR art. 78, 5 ILCS
     140/11.5.
   * "Prerequisite to an appeal" and "need not" cues set `exhaustion`.
   * "Except as provided in subsection (a-1)" around a route becomes a `scope_rule` to fill.
4. **Cue phrases**, as a small table beside `xref.py`'s patterns:
   * "appeal … to the head";
   * "petition the Mayor to review";
   * "file a request for review with";
   * "must ask for a decision from";
   * "may be extended by written notice from the head of the agency or a designee";
   * "must immediately notify the regulatory agency with authority".
5. **Resolve targets** through §4.4.
6. **Review.** Every derived route starts `proposed`. A reviewer accepts it, or two extractions agree on it. Only
   accepted routes are shown or published.

The small-classifier pattern of links-codebase-map §6 (logistic regression over cue features) can rank candidate
route kinds later. The rules come first, because the corpus has only about 50 routes.

### 5.6 Checks (a route checker, in a new test file)

* **Resolves:** every `target`, `target_rule`, `invoked_by` and `next_routes` key resolves. Relative targets
  resolve for every agency the model's `played-by` can reach, or are shown as a role.
* **Separation of duty:** an `internal_appeal` or `external_review` target is not the post that made the
  decision. This is resource pattern R-SOD, or WS-HumanTask's excluded owners.
* **Exhaustion consistency:** a route marked `required` lies on every path to the routes that follow it, unless a
  deemed outcome makes it `constructive`. This is the check that flags the DC edge in §5.4.
* **Remedy notice:** where the statute requires a denial notice to name remedies (5 ILCS 140/9(a); the MD
  `send_denial_statement` step's "remedies"), the notice step names every route that is open from it.
* **No cycles** except `remand` and `reconsideration`.
* **Clocks:** a route with a statutory time limit has one, and a reviewer deadline with a deemed outcome has a
  `next_routes` entry.

### 5.7 How the route appears in each artefact

* **BPMN** (`bpmn_xml.py`).
  * A route to another organisation is a message flow from the invoker's pool to the target's pool.
  * The invoker's side is an event-based gateway: the decision message, or the response timer that produces the
    deemed outcome.
  * A route inside one organisation is a lane per post (for example "Records access officer" and "Entity head").
    An escalation boundary event is used only where the law moves the matter up within that body.
  * Each element carries `lex:route key="lexflow:route:…"`, beside `lex:grounding`. `lex:actor` gains
    `post="lexflow:post…"`.
* **DMN** (`dmn_xml.py`).
  * The reviewing decision (for example `decide_appeal`) gets `decisionMaker` → an `organizationUnit` with `URI`
    set to the post-type key.
  * It gets an information requirement on the decision it reviews, and an authority requirement on the route's
    statute.
  * A binding opinion is a knowledge source whose `owner` is the opinion-giving body.
  * This goes in the FEEL dialect only, as bpc-480-decision §6.4 does.
* **Answers and DokuWiki.**
  * An answer gets an "If the answer is no" block listing accepted routes in order. Each entry gives who decides
    (the post, never a person), the time limit, whether the route is required first, and the citing words.
  * A process page gets a "Review and appeal" table, generated from `routes`.
  * Unknown exhaustion is shown as "the statute does not say whether you must do this first".
* **Simulation.** Route outcomes are `lexflow:status:` keys (bpc-480 §6.2), so `lexflow.simulate` can bind a
  reviewer's result to the next route's trigger.

---

## 6. The Wikibase and Govdirectory plan

### 6.1 What not to do

* Do not bulk-import Govdirectory or Wikidata. Govdirectory adds no data beyond Wikidata (entities-sources §1), and
  covers 6 of the 98 bodies.
* Do not create person items or holder statements.
* Do not try federated properties (§2.12).

### 6.2 What to create (after the user's go-ahead; one combined decision with entities-contacts §1.7 and terms-wikibase §4)

| New property | Datatype | Equivalent (P7) | On → value |
|---|---|---|---|
| parent organisation | item | wd:P749; `org:subOrganizationOf` | agency or unit → agency |
| post in | item | `org:postIn` | post → agency, unit or office type |
| head post | item | wd:P2388 | agency → post |
| reports to | item | wd:P10645; `org:reportsTo` | post → post |
| competent authority | item | CPSV-AP *has competent authority* | process item → agency or office type |
| decided by | item | (DMN decisionMaker) | step or decision → post, post type, agency or office type |
| auxiliary party | item | (LegalRuleML AuxiliaryParty) | step → role item (the recipient) |
| route from / route to / invoked by / next route | item | – | route → step, decision, agency, post, role or route |
| route kind / exhaustion | item | – | route → a kind item, an exhaustion item |
| time limit | string (or quantity with a unit) | – | route (e.g. "30 days from the denial") |

Notes on the table:

* **Choice for the user.** entities-contacts §1.7 puts the parent agency on P9 *part of*. P9 already joins steps to
  processes, so one property would carry two meanings and every SPARQL query would need a class filter. This note
  recommends a dedicated *parent organisation* property.
* **Classes:** *organisational unit* (P8 → wd:Q10387680), *post* (P8 → wd:Q4164871 *position*), *post type* (a P6
  subclass of *post*) and *review route*, with one item per route kind and per exhaustion value.
* **Items:**
  * agencies and office types, as entities-contacts phase 3 plans;
  * posts named by reviewed models: the DC Mayor (as the FOIA reviewer), the Illinois Public Access Counselor,
    "head of the entity" (NY), "head of the agency or a designee" (CA), hearing officers and ALJs, the attorneys
    general;
  * routes for the reviewed models.
* **Regeneration.** The loader regenerates every statement from the DB on each load, because `clear` replaces
  statements (entities-contacts D12). `retire_drafts` must learn the `route`, `post` and `post-type` key kinds.

### 6.3 Shapes and links

* **EntitySchema.** It is installed, so store ShEx shapes for *agency*, *post* and *review route* on the wiki. One
  rule a shape enforces: a post has no *position holder* property. Validate items against the shapes in the
  loader's dry run.
* **Links out.** P8 *exact match* goes to Wikidata only for `exact` QIDs. A position QID goes on the **post**
  item, never on the agency, which settles entities-contacts' "position, not office" case. *Described at URL* goes
  to Govdirectory for the listed bodies. Fill the Wikibase.cloud Features-tab mapping tables for the new
  properties' Wikidata equivalents.

### 6.4 Govdirectory later

* If NY or NC coverage grows, a thin import of the published state-agency lists is possible: label, QID, P749 and
  P2388 where present, and the Govdirectory URL. That is 97 NY items and 400 NC items. It should be on demand,
  item by item, when a model names the body.
* Corrections still go upstream only by a person through Wikidata (entities-contacts D11), never as
  lexflow-written reports to Govdirectory.

---

## 7. Phases, tests and measures

| Phase | Scope | Tests (new files) | Exit check |
|---|---|---|---|
| 1. Posts | `posts` table; `agencies.branch`, `remit` and `ocd_division`; the new `entity_links` relations; a seed from `agencies.json` positions, P2388/P2389 for exact QIDs, and the model actors that are posts (`appeals_officer`, `agency_head`, `mayor`, `pac`); a resolver for relative targets in `lexflow/entities/authority.py` | relative-target resolution; no person field is ever written; a position QID lands on a post, never an agency | every official-kind actor in the 22 models resolves to a post or post type |
| 2. Routes | the `routes` table; `lexflow/law/routes.py` derivation (§5.5); the route checker (§5.6) | derivation reproduces the 48 seed steps as routes; the five checks; the DC edge is flagged | ≥ 90 % of seed steps become routes with a resolved target; every route has a quote |
| 3. Review | a reviewer accepts or rejects the routes of the 22 models and 15 answers; `exhaustion` filled from the text | accepted routes survive re-derivation (`upsert(keep=)`) | no `unknown` exhaustion where the text speaks |
| 4. Surfaces | "If the answer is no" blocks; process-page tables; DMN `decisionMaker` and organisation units; BPMN lanes and route attributes | XSD and dmn-moddle import; a remedy-notice check on rendered answers | dry-run pages show routes with dates and sources |
| 5. Wikibase | classes, properties, shapes and items (§6.2), after the go-ahead | loader dry run against the shapes; no person statements | a user-triggered load of the reviewed states |

Code goes in new modules and new tests. `lexflow/ask/*`, `extract/*`, `ir.py` and the facts schema stay untouched
until AskBench finishes; the `deemed-approval` value and any IR fields wait for that.

Measures:

| Metric | Baseline (today) | Target |
|---|---|---|
| route steps in reviewed models with an accepted route record | 0 of about 48 | ≥ 95 % |
| routes with a resolved target (relative targets resolved, or shown as a role) | – | 100 % |
| routes whose exhaustion is taken from the text, not `unknown` | – | every route whose statute speaks to it |
| official and public-body actors resolved to a post, agency or office type | 0 of 55 non-private actors (entities-contacts §7) | ≥ 95 % |
| denial notices that name every open route where the statute requires it | unchecked | 100 % |

---

## 8. Open questions

1. **The property set.** This note adds about ten properties to entities-contacts' and terms-wikibase's sets.
   Decide them in one go-ahead. Is *parent organisation* a new property, or P9 *part of* with a class filter?
2. **Holders.** Keep the rule of no holders at all (recommended)? Or allow a live, uncached link-out for elected
   offices?
3. **Branch and remit.** Wikidata rarely records them. Is a curated value per body acceptable? It is needed only
   for bodies that a scope rule tests.
4. **Legal readings.** Exhaustion, the burden of proof and suspensive effect are legal judgements. Who reviews them
   beyond the text-quote rule? Until someone does, show "the statute does not say".
5. **Federal routes.** Wikidata's P12452 gives the federal court hierarchy. Is federal review in scope, for example
   § 1983 actions after state remedies? This note leaves it out.
6. **NY and NC thin import.** Only on demand (recommended), or the whole published lists?

---

## 9. Sources (all opened on 2026-10-10)

Standards and specifications

* W3C (2014). *The Organization Ontology.* W3C Recommendation, 16 January 2014.
  <https://www.w3.org/TR/vocab-org/>
* Popolo Project. *Specifications*: [index](https://www.popoloproject.com/specs/),
  [Post](https://www.popoloproject.com/specs/post.html), [Membership](https://www.popoloproject.com/specs/membership.html),
  [Organization](https://www.popoloproject.com/specs/organization.html).
* Open Civic Data. [OCDEP 2: Division Identifiers](https://open-civic-data.readthedocs.io/en/latest/proposals/0002.html)
  (accepted 2014-06-06); [OCDEP 5: People, Organizations, Posts, and Memberships](https://open-civic-data.readthedocs.io/en/latest/proposals/0005.html)
  (accepted 2014-06-12).
* schema.org: [GovernmentOrganization](https://schema.org/GovernmentOrganization),
  [GovernmentService](https://schema.org/GovernmentService), [Role](https://schema.org/Role).
* SEMIC: [Core Public Organisation Vocabulary 2.1.2](https://semiceu.github.io/CPOV/releases/2.1.2/);
  [Core Public Service Vocabulary Application Profile 3.2.0](https://semiceu.github.io/CPSV-AP/releases/3.2.0/).
* OMG (2013). *Business Process Model and Notation (BPMN) 2.0.2*, formal/13-12-09.
  <https://www.omg.org/spec/BPMN/2.0.2/PDF> (about page: <https://www.omg.org/spec/BPMN/2.0.2/About-BPMN>).
  Sections used: 8.4.4, 9.4, 10.3.1, 10.3.4.1, 10.3.6, 10.5.1, 10.5.2, 10.5.4 (Table 10.90), 10.8.
* Camunda. *Escalation events* (Camunda 8 documentation).
  <https://docs.camunda.io/docs/components/modeler/bpmn/escalation-events/>
* OASIS (2010). *Web Services – Human Task (WS-HumanTask) Specification Version 1.1*, Committee Specification 01,
  17 August 2010. <https://docs.oasis-open.org/bpel4people/ws-humantask-1.1-spec-cs-01.html>
* OMG (2021). *Decision Model and Notation 1.3*, formal/2021-01-01. <https://www.omg.org/spec/DMN/1.3/PDF>;
  version list at <https://www.omg.org/spec/DMN/>. Sections used: 5.2.1, 6.2.2.3, 6.3.7, 6.3.8, 6.3.12. Local XSD:
  `schemas/dmn/DMN13.xsd`.
* OASIS (2021). *LegalRuleML Core Specification Version 1.0*, OASIS Standard, 30 August 2021.
  <https://docs.oasis-open.org/legalruleml/legalruleml-core-spec/v1.0/legalruleml-core-spec-v1.0.html>
* OASIS (2018). *Akoma Ntoso Version 1.0, Part 1: XML Vocabulary*, OASIS Standard, 29 August 2018.
  <https://docs.oasis-open.org/legaldocml/akn-core/v1.0/akn-core-v1.0-part1-vocabulary.html>
* Publications Office of the EU. *ELI* ([overview](https://op.europa.eu/en/web/eu-vocabularies/eli);
  [OWL](https://op.europa.eu/documents/3938058/11669184/eli.owl/), `owl:versionInfo` 1.4 at that URL).
* Wikidata property pages (each read as `Special:EntityData/<P>.json`):
  [P749](https://www.wikidata.org/wiki/Property:P749), [P355](https://www.wikidata.org/wiki/Property:P355),
  [P2388](https://www.wikidata.org/wiki/Property:P2388), [P2389](https://www.wikidata.org/wiki/Property:P2389),
  [P10645](https://www.wikidata.org/wiki/Property:P10645), [P12452](https://www.wikidata.org/wiki/Property:P12452),
  [P2098](https://www.wikidata.org/wiki/Property:P2098), [P797](https://www.wikidata.org/wiki/Property:P797),
  [P1001](https://www.wikidata.org/wiki/Property:P1001), [P39](https://www.wikidata.org/wiki/Property:P39),
  [P1308](https://www.wikidata.org/wiki/Property:P1308), [P5052](https://www.wikidata.org/wiki/Property:P5052).
  Counts in §1.3 come from read-only queries to <https://query.wikidata.org/sparql>.
* Wikibase: [Federated Properties](https://doc.wikimedia.org/Wikibase/master/php/docs_components_repo-federated-properties.html);
  [Wikibase.cloud FAQ](https://www.mediawiki.org/wiki/Wikibase/Wikibase.cloud/FAQ). Lexipedia's property list and
  extensions were read from <https://lexipedia.wikibase.cloud/w/api.php> (`wbgetentities`, `siteinfo`).

Law

* 5 U.S.C. § 302, <https://www.law.cornell.edu/uscode/text/5/302>; 5 U.S.C. § 704,
  <https://www.law.cornell.edu/uscode/text/5/704>.
* *Darby v. Cisneros*, 509 U.S. 137 (1993), <https://www.law.cornell.edu/supremecourt/text/509/137>.
* *McKart v. United States*, 395 U.S. 185 (1969), <https://www.law.cornell.edu/supremecourt/text/395/185>.
* State sections quoted, from the lexflow index:
  * N.Y. Pub. Off. Law § 89 (`STATE_NY_APBO_A6_S89`)
  * D.C. Code §§ 2-532, 2-537
  * 5 ILCS 140/9, 9.5, 11
  * RCW 42.56.520, 19.02.070
  * Tex. Gov't Code §§ 552.301, 552.302, 2001.145, 2001.146
  * Cal. Gov. Code §§ 7922.535, 11521, 11523
  * Va. Code §§ 2.2-3704, 2.2-4021, 2.2-4026

  The other sections in §5.2 are cited as the curated models and answers cite them.

Legal theory and legal ontologies

* Hohfeld, W. N. (1913). Some fundamental legal conceptions as applied in judicial reasoning. *Yale Law Journal*
  23(1):16. [doi:10.2307/785533](https://doi.org/10.2307/785533)
* Hohfeld, W. N. (1917). Fundamental legal conceptions as applied in judicial reasoning. *Yale Law Journal*
  26(8):710. [doi:10.2307/786270](https://doi.org/10.2307/786270)
* Wenar, L. and Cruft, R. *Rights.* Stanford Encyclopedia of Philosophy (substantive revision 7 June 2025).
  <https://plato.stanford.edu/entries/rights/>
* Allen, L. E. and Saxon, C. S. (1995). Better language, better thought, better communication: the A-Hohfeld
  language for legal analysis. ICAIL 1995, 219–228. [doi:10.1145/222092.222245](https://doi.org/10.1145/222092.222245)
* Sartor, G. (2006). Fundamental legal concepts: a formal and teleological characterisation. *Artificial
  Intelligence and Law* 14(1–2):101–142. [doi:10.1007/s10506-006-9009-x](https://doi.org/10.1007/s10506-006-9009-x)
* Griffo, C., Almeida, J. P. A. and Guizzardi, G. (2018). Conceptual modeling of legal relations. ER 2018, LNCS,
  169–183. [doi:10.1007/978-3-030-00847-5_14](https://doi.org/10.1007/978-3-030-00847-5_14)
* Griffo, C., Sales, T. P., Guizzardi, G. and Almeida, J. P. A. (2022). Legal power-subjection relations:
  ontological analysis and modeling pattern. ER 2022, LNCS, 65–81.
  [doi:10.1007/978-3-031-17995-2_5](https://doi.org/10.1007/978-3-031-17995-2_5)
* van Binsbergen, L. T., Liu, L.-C., van Doesburg, R. and van Engers, T. (2020). eFLINT: a domain-specific language
  for executable norm specifications. GPCE 2020, 124–136. [doi:10.1145/3425898.3426958](https://doi.org/10.1145/3425898.3426958)
* Hoekstra, R., Breuker, J., Di Bello, M. and Boer, A. (2009). LKIF Core: principled ontology development for the
  legal domain. Frontiers in Artificial Intelligence and Applications.
  [doi:10.3233/978-1-58603-942-4-21](https://doi.org/10.3233/978-1-58603-942-4-21). Ontology files:
  <https://github.com/RinkeHoekstra/lkif-core> (`legal-action.owl`: Mandate, Delegation, Public_Body, Decision).
* Hübner, J. F., Sichman, J. S. and Boissier, O. (2002). A model for the structural, functional, and deontic
  specification of organizations in multiagent systems. SBIA 2002, LNCS, 118–128.
  [doi:10.1007/3-540-36127-8_12](https://doi.org/10.1007/3-540-36127-8_12). French version, read for the
  authority-link definition: <https://www2.pcs.usp.br/~jaime/papers/hubner_jfiadsma02_f.pdf>

Process models: resources, authorisation and organisational mining

* Russell, N., van der Aalst, W. M. P., ter Hofstede, A. H. M. and Edmond, D. (2005). Workflow resource patterns:
  identification, representation and tool support. CAiSE 2005, LNCS 3520, 216–232.
  [doi:10.1007/11431855_16](https://doi.org/10.1007/11431855_16). Long version with the pattern definitions:
  <https://www.vdaalst.com/publications/p250.pdf>
* Cabanillas, C., Resinas, M. and Ruiz-Cortés, A. (2012). RAL: a high-level user-oriented resource assignment
  language for business processes. BPM 2011 Workshops, LNBIP, 50–61.
  [doi:10.1007/978-3-642-28108-2_5](https://doi.org/10.1007/978-3-642-28108-2_5)
* Cabanillas, C., Resinas, M., del-Río-Ortega, A. and Ruiz-Cortés, A. (2015). Specification and automated
  design-time analysis of the business process human resource perspective. *Information Systems* 52:55–82.
  [doi:10.1016/j.is.2015.03.002](https://doi.org/10.1016/j.is.2015.03.002)
* Stroppi, L. J. R., Chiotti, O. and Villarreal, P. D. (2015). Defining the resource perspective in the development
  of processes-aware information systems. *Information and Software Technology* 59:86–108.
  [doi:10.1016/j.infsof.2014.10.006](https://doi.org/10.1016/j.infsof.2014.10.006)
* Wolter, C. and Schaad, A. (2007). Modeling of task-based authorization constraints in BPMN. BPM 2007, LNCS,
  64–79. [doi:10.1007/978-3-540-75183-0_5](https://doi.org/10.1007/978-3-540-75183-0_5)
* Song, M. and van der Aalst, W. M. P. (2008). Towards comprehensive support for organizational mining. *Decision
  Support Systems* 46(1):300–317. [doi:10.1016/j.dss.2008.07.002](https://doi.org/10.1016/j.dss.2008.07.002)
  (working-paper version: <https://research.tue.nl/en/publications/towards-comprehensive-support-for-organizational-mining>)
* van der Aalst, W. M. P., Reijers, H. A. and Song, M. (2005). Discovering social networks from event logs.
  *Computer Supported Cooperative Work* 14(6):549–593. [doi:10.1007/s10606-005-9005-9](https://doi.org/10.1007/s10606-005-9005-9)
* Schönig, S., Cabanillas, C., Jablonski, S. and Mendling, J. (2016). A framework for efficiently mining the
  organisational perspective of business processes. *Decision Support Systems* 89:87–97.
  [doi:10.1016/j.dss.2016.06.012](https://doi.org/10.1016/j.dss.2016.06.012)
* Olbrich, S. and Simon, C. (2007). Integration of legal constraints into business process models. *Transforming
  Government: People, Process and Policy* 1(2):194–210. [doi:10.1108/17506160710752002](https://doi.org/10.1108/17506160710752002)

DOIs were checked against Crossref's public API (`api.crossref.org/works/<doi>`) for title, authors, venue and
pages. Crossref files the Russell et al. chapter under a wrong series name; the venue above is CAiSE 2005, LNCS
3520, as the author's institutional repository lists it.

Lexflow inputs

* [entities-contacts.md](entities-contacts.md), [entities-sources.md](entities-sources.md),
  [terms-wikibase.md](terms-wikibase.md), [links-codebase-map.md](links-codebase-map.md),
  [links-literature.md](links-literature.md), [bpc-480-decision.md](bpc-480-decision.md)
* `curated/<st>/<q>.json` (22 models), `curated_ask/*/*.json` (30 answers, 15 with steps),
  `fixtures/xref/gold_{a,b,c}.json`, `fixtures/entities/agencies.json`, `lexflow/law/xref.py`, `lexflow/ir.py`,
  `lexflow/extract/compile.py`, `lexflow/extract/schema.py`, `lexflow/publish/wikibase_lexipedia.py`
