# Lexipedia Wikibase schema, version 2: laws, bodies, posts, processes and contacts

_15 October 2026. This is the contract for `lexflow/publish/schema.py` (the one table of classes and properties),
`lexflow/publish/qs.py` (QuickStatements batches for Claude in Chrome), `lexflow/publish/rdf.py` (the same data as
RDF for local SPARQL) and `lexflow/publish/sparql/*.rq` (the queries). It builds on
[authority-wikibase.md](authority-wikibase.md) §4, [authority-escalation.md](authority-escalation.md) §1,
[entities-contacts.md](entities-contacts.md) §1.7 and §5, and [terms-wikibase.md](terms-wikibase.md) §3–4, and
settles what those notes left as proposals._

## 0. What is wrong today, and what version 2 changes

Measured on 15 October 2026 against https://lexipedia.wikibase.cloud (1,413 lexflow items, 25 properties):

1. **Queries written the Wikidata way return nothing.** On this instance the `wd:` and `wdt:` prefixes do not
   resolve to Lexipedia's own entities: `SELECT * { wd:Q168 ?p ?o }` gives 0 rows, while the full IRI
   `<https://lexipedia.wikibase.cloud/entity/Q168>` gives 18. Every query must declare
   `PREFIX lx: <https://lexipedia.wikibase.cloud/entity/>`, `lxt: <…/prop/direct/>`, `lxp: <…/prop/>`,
   `lxps: <…/prop/statement/>`, `lxpq: <…/prop/qualifier/>`, `lxpr: <…/prop/reference/>`.
2. **Law has no structure.** A section item (Q10) carries a citation, a URL and a jurisdiction, and nothing says
   which title, chapter or code it belongs to, what comes before or after it, or when it is in force. "Virginia
   Code, Title 2.2, Chapter 37, in order" cannot be asked.
3. **Processes do not reach bodies.** A step's bearer is a per-process role item (Q23); no role is "played by" an
   agency, no agency has a contact channel, no post or appeal target exists. "Who does what" stops at the role.
4. **Deadlines, fees, forms, outcomes and escalation are not statements.** They are in lexflow's facts and in the
   BPMN, but the wiki holds only `follows`.
5. **Drafts are marked in description text only**, so a query cannot filter to reviewed material.
6. **Nothing says what a process is for.** No topic, audience or plain-language question is attached, so an item
   cannot be found by what a person wants to do.

Version 2 adds 18 classes and vocabularies and 46 properties (§2–§3), writes law as a hierarchy (§4.1), joins roles
to bodies, posts and contacts (§4.3–§4.5), writes deadlines, fees, forms, outcomes and escalation as statements
with the statute quote as the reference (§4.6), and marks review status as a claim. §5 is the Claude in Chrome
packet; §6 the SPARQL that must work afterwards; §7 the local runner.

## 1. Rules that do not change

- **Keys.** Every item carries `P25 legal identifier` = its lexflow key (`lexflow:<kind>:…`). Keys are minted once
  and never change; the generator finds by key before it creates. The key forms are those of
  authority-escalation.md §1.3 plus the new ones in §2 below.
- **One source of truth.** Every claim is regenerated from lexflow's database and fixtures. A hand edit on the wiki
  survives only if it is also recorded in lexflow (a reviewed mapping goes into a table, never only on the wiki).
- **Privacy** (entities-contacts.md §5, `lexflow/privacy.py`): organisations and office channels only; no office
  holders, no staff names, no personal mailboxes, no direct lines; reviewers are never named on Wikibase (the wiki
  gets `review status`, not the reviewer); registered agents, incorporators and requesters are `lexflow:private-party`.
- **Licence.** Wikibase Cloud's hosting policy requires structured data to be CC0. Statements hold facts, keys,
  citations, URLs, dates, amounts and short quotes from statutes (public domain in the US). Words from sites whose
  terms forbid reposting (`quotes.NO_REPRINT`: albemarle.org, eCode360, Municode) are never written; the statement
  carries the URL and lexflow's paraphrase.
- **Drafts.** Only reviewed or agreed models get full statements. A `single`-tier model's items are written with
  `review status = draft` and may be retired; they are never deleted.
- **Nothing is deleted** on the wiki by lexflow or by the Chrome packet. Superseded items are relabelled and get
  `review status = superseded`.

## 2. Classes and vocabularies

Existing class items are kept: Q7 legal process, Q8 legal process step, Q9 decision point, Q10 statute or legal
provision, Q11–Q20 (LegalRuleML norm classes), Q21 jurisdiction, Q22 court decision, Q23 legal role. Q24–Q75 are
the 52 jurisdictions. Q5 and Q6 are the sandbox's Douglas Adams items and are left alone.

New class items (`P5 instance of` targets; key `lexflow:class:<slug>`; `P8 exact match` to the Wikidata IRI where
one fits, otherwise none). Wikidata QIDs marked *verify* must be checked read-only with `wbgetentities` by the
generator before they are written; the others were checked in earlier rounds.

| Class (label) | Key slug | ≡ Wikidata | Used for |
|---|---|---|---|
| legal code | `legal-code` | Q922203 (code of law; checked 15 Oct 2026: Q1156854 is "policy") | "Virginia Code", "D.C. Code", "Fla. Stat." (one per jurisdiction code); a named code inside a state's codes (Cal. GOV, N.Y. PBO Law, Md. Code General Provisions, Tex. Government Code) is `lexflow:code:<st>:<token>` with P9 → the state's code |
| statutory unit | `statutory-unit` | – | title, subtitle, part, division, chapter, subchapter, article, act (Illinois); the level is a claim (§3) |
| regulation | `regulation` | Q11861227 (administrative regulation; checked: Q3493304 does not exist) | administrative code sections (13VAC5-63-80) |
| government | `government` | – | a Census government (`lexflow:gov:<gid>`): city, county, town |
| government agency | `government-agency` | Q327333 | departments, boards, commissions, offices with standing |
| organizational unit | `organizational-unit` | Q10387680 | divisions and sections inside an agency |
| court | `court` | Q41487 | courts and court systems |
| office type | `office-type` | – | a body each county, profession or record holder has ("the clerk of the circuit court"); `P6 subclass of` → agency or court |
| position | `position` | Q294414 (public office, a subclass of position Q4164871) | a post that exists apart from its holder (Secretary of State of Florida) |
| position type | `position-type` | – | a post every body of a kind has (FOIA officer of the public body) |
| local process | – (reuse Q7) | – | a researched local process (`lexflow:process:<gid>:<process>`) is a legal process whose jurisdiction is a government |
| process outcome | `process-outcome` | – | an end state of a process (records released, deemed denied) |
| escalation mechanism | `escalation-mechanism` | – | one rung of a ladder: an appeal, petition, review, referral or complaint path the law creates |
| statutory power | `statutory-power` | – | what a body may do (deny a licence, extend time, decide an appeal) |
| government form | `government-form` | Q1335296 (form, a genre of document; checked: Q8162 is "linguistics") | an official form or online application a step uses |
| topic | `topic` | – | vocabulary: public records, business, building and zoning, taxes, voting, courts, animals, property, benefits, licensing, criminal records |
| audience | `audience` | – | vocabulary: resident, business, visitor, property owner, requester, applicant |
| review status | `review-status` | – | vocabulary: reviewed, agreed, draft, superseded |
| time unit | `time-unit` | – | vocabulary: calendar days, business days, working days, work days (the law's own word), hours, weeks, months, years |
| reference type | `reference-type` | – | vocabulary from `lexflow.law.xref.ROLES`, verbatim: definition, override, exception, penalty, prerequisite_process, authority, procedure, condition, scope, other |
| step kind | `step-kind` | – | vocabulary from `facts.steps[].kind` as the curated models use it: filing, notice, decision, act, payment, record, inspection, hearing, review (plus delivery, unused today) |
| unit level | `unit-level` | – | vocabulary: code, title, subtitle, part, division, chapter, subchapter, article, act, section, subsection; for civil-law codes also book, paragraph, item, supplementary provision (§4.8) |
| escalation type | `escalation-type` | – | vocabulary: the ten types of `ladders.json.vocabulary.type` (property 43's targets) |
| determination method | `determination-method` | – | vocabulary: matched by lexflow's software, AI verifier, curated, HTTP check, found on official page (property 19's targets) |
| currency | `currency` | Q8142 | vocabulary: US dollar, the unit of every fee (property 46) |
| defined term, concept, legal document, legal status | per terms-wikibase.md §3 | Q2135465, Q49848, Q2628882 | the terms plan; created now, filled when that plan runs |

Vocabulary items are keyed `lexflow:vocab:<set>:<slug>` and carry `P5` → their vocabulary class and a one-line
description. They are written first, because everything else points at them.

## 3. Properties

The wiki holds 25 properties; the 21 from P5 are reused unchanged: P5 instance of, P6 subclass of, P7 equivalent property, P8 exact
match, P9 part of, P10 has part, P11 follows, P12 followed by, P13 references, P14 based on, P15 applies to
jurisdiction, P16 deontic modality, P17 bearer, P18 condition, P19 governed by norm, P20 sanction, P21 defeated
by, P22 citation, P23 official text, P24 effective date, P25 legal identifier. P1–P4 (sandbox) are left alone.

New properties, in the order Claude in Chrome creates them (QuickStatements `CREATE_PROPERTY`). Datatypes are
QuickStatements' lower-case names. "≡" is written as `P7 equivalent property` = `http://www.wikidata.org/entity/P…`
on the property item, so federated queries can map them.

| # | Label | Datatype | ≡ Wikidata | On → value | Notes |
|---|---|---|---|---|---|
| 1 | Wikidata item ID | external-id | – | any item → `Q812` | formatter `https://www.wikidata.org/wiki/$1`; RDF URI `http://www.wikidata.org/entity/$1` (see 2, 3). The identity crosswalk; `P8` stays the SKOS match |
| 2 | formatter URL | string | P1630 | property → template | on 1, 5, 6, 44 |
| 3 | formatter URI for RDF resource | string | P1921 | property → template | on 1, so `lxn:` normalised IRIs join Wikidata in `SERVICE` |
| 4 | unit level | item | – | code, unit, section → vocab | title / chapter / section … |
| 5 | act identifier | external-id | – | section, unit → `STATE_VA_T2.2_SII_PB_C37_S2.2-3704` | Open US Law's `act_id`; the unit's is the prefix of its sections' |
| 6 | government ID | external-id | – | government → Census GID | formatter to lexflow's place page |
| 7 | sort key | string | – | unit, section, step → `00002.00002-00002-b-00037-00002.00002-03704` (every act_id token after the state, level letter dropped, digit runs padded to five, roman numerals as numbers; a step's is its position, `0005`) | zero-padded; the only way to order "in the code's order" (`schema.sort_key`) |
| 8 | section number | string | – | section → `2.2-3704` | the bare number; P22 keeps the full citation |
| 9 | effective until | time | P582-like | section → date | with P24 effective date (from); P24 is renamed in description only ("effective from") |
| 10 | replaced by | item | P1366 | section → section | versioned sections (`…v1`) |
| 11 | heading text | monolingualtext | P1476 | section, unit → `en:"Public records to be open…"` | the label is `Va. Code § 2.2-3704`; the heading is searchable text |
| 12 | reference type | item | – | qualifier on P13 → vocab | authority, procedure, … |
| 13 | quoted text | string | – | reference on any claim → ≤400 chars of the statute | the grounding quote; every claim made from a model's `source` carries one |
| 14 | source section | item | – | reference → section item | with 15 |
| 15 | pinpoint | string | – | reference or qualifier → `B.4`, `(g)` | subsection |
| 16 | source URL | url | P854 | reference → URL | for claims made from an official page (local processes, contacts) |
| 17 | retrieved | time | P813 | reference → date | lexflow's fetch or check date |
| 18 | archive URL | url | P1065 | reference → Internet Archive capture | when the live page refused automated reading |
| 19 | determination method | item | P459 | reference → vocab | `matched by lexflow's software`, `AI verifier`, `curated`, `HTTP check`, `found on official page` |
| 20 | played by | item | – | role → agency, unit, office type, court, position type, or `lexflow:private-party` | the join from processes to bodies |
| 21 | head position | item | P2388 | agency → position | |
| 22 | position in | item | P2389 / P361 | position → agency | never P9, so P9 paths never return posts |
| 23 | appointed by | item | P748 | position → position or agency | |
| 24 | supervised by | item | – | agency → agency or position | from statute only |
| 25 | designee of | item | – | position type → position or position type | "or a designee" |
| 26 | authority conferred by | item | P92-like | agency, position, office type, role → section | qualifiers: 27 power, 13 quote |
| 27 | power | item | – | qualifier on 26 → `lexflow:power:<slug>` item | deny licence, extend time, decide appeal |
| 28 | official website | url | P856 | agency, government | |
| 29 | contact page URL | url | P11266 | agency, government, process | the records page, the permits page |
| 30 | email address | url | P968 | agency, government, process → `mailto:FOIA@…` | office mailboxes only (`privacy.is_office_mailbox`) |
| 31 | phone number | string | P1329 | → `434-555-0100` | main lines only (`privacy.is_office_phone`) |
| 32 | postal address | string | P6375-like | → office address | `privacy.office_value` applied |
| 33 | described at URL | url | P973 | agency → Govdirectory page | never copied, only linked |
| 34 | step kind | item | – | step → vocab | |
| 35 | recipient | item | – | step → role | who receives the filing or notice |
| 36 | time limit | quantity | – | step, rung, process → `5` | qualifiers: 37 time unit, 38 counted from, 39 on expiry, 13 quote |
| 37 | time unit | item | – | qualifier → vocab | the law's own word (working days ≠ business days) |
| 38 | counted from | string | – | qualifier → `receiving a request` | |
| 39 | on expiry | item | – | qualifier → outcome item | deemed denial |
| 40 | outcome | item | – | process, step → process outcome | |
| 41 | escalates to | item | – | step, role, process → role, agency, position, court, office type, position type | statutory escalation; qualifiers 13, 14, 15, 36, 42 |
| 42 | defers to | item | – | same | referral, forwarding, concurrence |
| 43 | escalation type | item | – | rung, qualifier → vocab | the ten types in `ladders.json.vocabulary.type` |
| 44 | form used | item | – | step, process → government form | |
| 45 | form number | string | – | form → `DC-495` | with P23 official text = the form's URL |
| 46 | fee | quantity | – | step, process → amount in USD (unit item `US dollar`) | qualifiers 16 source URL, 13 quote, 47 fee basis |
| 47 | fee basis | string | – | qualifier → `plus project value × BR over $1,500` | when the amount is not a single number, 46 holds the minimum and 47 the rule |
| 48 | topic | item | P921 | process, section, form, law → vocab | discovery |
| 49 | audience | item | – | process → vocab | discovery |
| 50 | question asked | monolingualtext | – | process → `en:"How do I request public records…?"` | the plain-language question; also added as an alias |
| 51 | review status | item | – | process, step, role, rung, local process → vocab | reviewed / agreed / draft / superseded |
| 52 | checked on | time | – | process, local process → date | the date lexflow's software last matched the quotes |
| 53 | court | item | P1001-like | court decision → court | |
| 54 | date decided | time | P577 | court decision → date | |
| 55 | CourtListener ID | external-id | – | court decision → cluster id | formatter `https://www.courtlistener.com/opinion/$1/` |
| 56 | defined in | item | – | defined term → section | terms plan |
| 57 | scope | item | – | defined term → unit or section | terms plan |
| 58 | concept | item | – | defined term → concept | terms plan |
| 59 | role of actor | item | – | role → defined term or concept | terms plan |
| 60 | close match / broad match / narrow match / related match | url ×4 | skos | concept → Wikidata IRI | terms plan (four properties) |
| 61 | match probability | quantity | – | qualifier on P8 and 60 | terms plan |
| 62 | quoted text in language | monolingualtext | – | reference → verbatim text in the law's language | international law (§4.8); `quoted text` keeps English quotes |
| 63 | law number | monolingualtext | P8550 | law (unit at level act) → its number as the source writes it | `平成五年法律第八十八号`@ja; Wikidata writes `平成5年法律第88号` |
| 64 | promulgation date | time | P7589 | law → 公布日 | effective date is the enforcement date of the version described |
| 65 | e-Gov law ID | external-id | P8610 | Japanese law → `405AC0000000088` | formatter `https://laws.e-gov.go.jp/law/$1`; wikidata-laws.md |
| 66 | ComLaw ID | external-id | P2461 | Australian law → `C2004A00467` | formatter `https://www.legislation.gov.au/Details/$1` |
| 67 | short name | monolingualtext | P1813 | law → abbreviation | `行手法`@ja |
| 68 | law digest | monolingualtext | P9376 | law → official summary | Brazil's ementa; only from a source whose text may be copied (§4.8) |
| 69 | published in | item | P1433 | law → gazette | qualifier page; no data yet |
| 70 | page | string | P304 | qualifier on published in | |
| 71 | approved by | item | P790 | law → office or body | never a person (Brazil's items add a signatory; lexflow does not); no data yet |
| 72 | legislated by | item | P467 | law → legislature, cabinet, ministry or office | from the law's type and number (`schema.egov_makers`) |
| 73 | language of work | item | P407 | law, code → vocab language | |
| 74 | amended by | item | P2567 | law → amending law | qualifiers point in time, effective date; `law_amendments` |
| 75 | repealed by | item | P2568 | law → repealing law | qualifier effective date |
| 76 | repeals | item | P3148 | law → repealed law | qualifier effective date |
| 77 | amending law number | monolingualtext | – | law → number of an amending law with no item | qualifiers point in time, effective date |
| 78 | point in time | time | P585 | qualifier | an amendment's promulgation |
| 79 | stated in | item | P248 | reference → database item | `lexflow:source:egov-laws` |

That is 79 numbered rows and, with row 60's four SKOS matches, 82 new properties (`schema.PROPERTIES` holds them
in this order). Properties 1–61 were created on 15 October 2026 (P26–P89); 62–64 are created by the next push's
pass 1, for the international law of §4.8, and 65–79 with them, for the law shape of WikiProject Brazilian Laws
(docs/design/wikidata-laws.md). Of the live properties, `schema.EXISTING_WIKIDATA` gives thirteen their Wikidata
equivalent (citation ≡ P1031, official text ≡ P953, effective date ≡ P7588, part of ≡ P361 …), appended as `P7`
by pass 2. Properties 56–61 are created now so the terms plan needs no second
property round; they stay empty until it runs.

## 4. Item shapes

### 4.1 Law as a hierarchy

From Open US Law's `path` (`Virginia Code / Title 2.2 / Subtitle II / Part B / Chapter 37 / Section 2.2-3704`) and
`act_id`:

```
lexflow:code:va                 "Virginia Code"             P5 legal code; P15 Q(Virginia); unit level = code
lexflow:unit:va:t2.2            "Va. Code Title 2.2"        P5 statutory unit; P9 part of → code; unit level = title; sort key; act identifier = STATE_VA_T2.2; heading text
lexflow:unit:va:t2.2-sii        "… Subtitle II"             P9 → title
lexflow:unit:va:t2.2-sii-pb     "… Part B"
lexflow:unit:va:t2.2-sii-pb-c37 "Va. Code Title 2.2, Chapter 37"   P9 → part; heading text = "Virginia Freedom of Information Act"
lexflow:statute:va:2.2-3704     "Va. Code Ann. § 2.2-3704" (exists)  + P9 → chapter; unit level = section; section number; sort key; act identifier; heading text; P24 effective from; effective until; P11 follows → the previous section in sort order; P13 references → cited sections with reference type
```

Unit keys are the lower-cased act_id tokens joined by `-`, as terms-wikibase.md §6 proposed. A unit is written
only when at least one of its sections is in the build (today: the 496 sections on the wiki plus the sections the
models, rungs and local processes cite, 529 sections; their ancestors are 349 units and 63 code items, measured by
`graph.build` on 15 October 2026). Regulations (`13VAC5-63-80`) follow the same shape under `lexflow:code:va:vac` with class
*regulation*.

### 4.2 Jurisdictions and governments

The 52 jurisdiction items gain *Wikidata item ID* (Q812 for Florida and so on, from `states.py`) and *official
website*. A government (`lexflow:gov:<gid>`, class *government*) carries P15 → its state, *government ID*,
*Wikidata item ID* when `governments.wikidata` is set, *official website*, and the office channels from `contacts`
with `question = general` (§4.5). Governments are written only when something points at them: today the 3 that
have place pages plus the three Virginia localities.

### 4.3 Bodies, units, office types and posts

From `fixtures/entities/agencies.json` (bodies with an `exact` match), `fixtures/authority/ladders.json` (`bodies`)
and `caselaw.COURTS`: about 200 agencies and courts, 60 office types, 40 positions and 25 position types, with
the keys of authority-escalation.md §1.3. Each carries P5, P15, P9 part of (agency → parent agency or government
root `lexflow:agency:<st>:government`), *head position*, *position in*, *appointed by*, *supervised by*,
*designee of*, *authority conferred by* (+ *power*), *Wikidata item ID* (kind-checked: an agency key takes only an
organisation or court QID, a position key only a position QID), *described at URL* (Govdirectory) and the office
channels (§4.5). A structural edge is written only with `status = accepted` in lexflow's tables or `proposed` with
`review status = draft`.

### 4.4 Processes, steps, decisions, outcomes and roles

For the 22 reviewed and the agreed models (`process_models.tier in ('reviewed','agreed')`), from `facts`:

- **process** (Q7): P15, P22 citation, P23, *question asked* (the question's plain title), *topic*, *audience*,
  *review status*, *checked on*, P10 has part → steps and decisions, *outcome* → outcomes, P13 references →
  sections used (with *reference type* from xref where known), *time limit* for the headline deadline.
- **step** (Q8): P9 part of → process, P17 bearer → role, *recipient* → role, *step kind*, P16 deontic modality,
  P11 follows → previous steps (`after`), P18 condition → decision point when the step hangs on one, *time limit*
  (+ *time unit*, *counted from*, *on expiry*, reference: *source section*, *pinpoint*, *quoted text*), *form
  used*, *fee*, *escalates to* / *defers to* from the ladder rungs whose `step` matches, *review status*.
- **decision point** (Q9): P9 → process, *heading text* = the decision question, P13 → the sections its rules
  quote (one reference per rule, with the quote). Rules themselves stay in the DMN on the DokuWiki page.
- **outcome**: P9 → process, label = description, P11 follows → the steps that lead to it, reference quote.
- **role** (Q23, exists): + *played by* → body, office type, position type or `lexflow:private-party`; *authority
  conferred by*; *Wikidata item ID* never (it goes on the body).
- **rung** (escalation mechanism): key `lexflow:rung:<st>:<question>:<section-slug>:<subtype-code>`; P9 → process;
  *escalation type*; *escalates to* / *defers to* → body; *time limit*; P13 → section; *review status*; the quote
  as reference. Steps and processes point at rungs through *escalates to* on the step; the rung item holds the
  detail so one mechanism can serve several steps.

Draft (`single`) models get the process, steps and roles with `review status = draft`, no contacts and no
escalation.

**Asked answers as drafts** (`graph.Build.asked`, off unless `--asked-drafts` is given to `lexflow wikibase push`
or `lexflow wikibase lint`; `lexflow sparql --build` includes them with the other drafts so the coverage probe sees
them before any push). A state answer of `asked_answers` (the ask pipeline's answer to a question people asked, or
to a coverage question the gap-filling loop `lexflow run coverage --fill` answered) goes up as a **process** item
keyed `lexflow:process:asked:<state>:<question_id>` when its status is answered or partial, it holds facts (a map)
and every quote was matched word for word against the statute text (`pipeline.quote_counts`: no miss). It carries
`review status = draft`, *question asked* (the question's text), *topic* and *audience* from the coverage question
(`fixtures/coverage/questions.json`) when the id is one, *checked on* (when the quotes were taken), P13 references →
the sections the answer chose, and its steps (`lexflow:step:asked:<state>:<question_id>:<step>`), roles
(`lexflow:role:<state>:<question_id>:<actor>`) and deadlines exactly as the model branch writes them, each quote in
the grounding reference with *determination method* = matched by lexflow's software. Like every draft it never
carries contacts, office types, escalation, decisions or outcomes; its roles are played by `lexflow:private-party`
or nothing. Nothing in a draft's label or description says it is one (the lint's drafting-words check): the review
status claim does. The coverage probe counts draft process items apart (`counts.drafts`) and a cell that rests on
drafts alone is at most `partial` (`D` in docs/coverage.md).

### 4.5 Local processes and contacts

For each verified researched process (`place_processes.verified = 1`; on 15 October 2026 the live table holds
5 unverified rows while 60 curated files under `curated/places/va/` say verified, so `places.load_processes`
must run before any local process is built): a *legal process* item keyed
`lexflow:process:<gid>:<process>` with P15 → the government, *topic*, *audience*, *question asked*, *review
status* (= `agreed` when lexflow's software matched every quote and the AI verifier passed it; never `reviewed`
until a person signs), *checked on*; steps as in §4.4 with the office as bearer (a *played by* → the government's
agency or office-type item minted from `office`); *form used* → form items (`lexflow:form:<gid>:<process>:<id>`)
with *form number*, P23 and *topic*; *fee* with *fee basis* and the source URL; *escalates to* from `escalation`;
P13 → the state sections in `legal_basis`; *contact page URL*, *email address*, *phone number*, *postal address*
from `contacts` after `privacy.is_office_channel`.

Contact statements carry a reference (*source URL*, *retrieved*, *determination method*) and are written for the
process **and** for the body that owns the channel. A quote whose URL is under `quotes.NO_REPRINT` gives a reference
with *source URL* only and no *quoted text*.

**State bodies' channels** (16 October 2026). `python -m lexflow.municipal.agencies --load` puts the office
channels of `fixtures/entities/agencies.json` (website, office mailbox, main line, Govdirectory page; the bodies
with an `exact` match, their units and related positions, under the keys `graph.build` mints) into `contacts`
with the body's key as `gov_id` and `question = general`, after `privacy.is_office_channel` (82 rows from 70
bodies, 1 refused), and the pilot's `moved` websites (`contacts_pilot.json`) as a second `website` row with the
live URL (8 rows). `lexflow run local` is unchanged; run the command after the fixtures change. The graph does
not read these rows yet; the hook is three lines in `Build._agencies_fixture`, after the item is made:
`self.channels(it, key, "general", name, mailboxes=False)` (and the same for each unit). Meanwhile
`lexflow.ask.who` reads them directly, so a body's card shows its channels either way.

**Who do I ask** (`lexflow/ask/who.py`, `GET /api/who?q=&place=&live=0|1`, the dashboard's "Who do I ask" page).
A plain question ("who handles a FOIA request in Charlottesville") is routed to a jurisdiction (the `governments`
table and the 52 states), a topic (`who.RULES` first; the decision model as a choice over `VOCAB["topic"]` when
`LEXFLOW_DECIDE=1`, accepted at confidence 0.8) and process keys (the state's models by `QUESTION_TOPIC`, the
place's researched processes by category or a shared word). The answer runs `who-does-what.rq` for the state and
for the government, `body-contacts.rq` per body, and three inline queries (a body's details and parent chain, a
role's *authority conferred by* quote), and groups by role: played by, parent chain, channels with source and
date, Wikidata and Govdirectory links (`lexflow.publish.govdirectory`: the page URL pattern
`govdirectory.org/united-states[/<state-slug>]/<QID>/`, checked read-only once per QID and cached in
`fixtures/entities/govdirectory_links.json`), the quote and the steps. Without a store it answers from the
models' facts.

### 4.6 Grounding

Every claim derived from a model's `source`, a rung's `quote` or a local process's `legal_basis` carries a
reference: *source section* (item) or *source URL*, *pinpoint*, *quoted text* (≤400 characters, verbatim), and
*determination method*. This is what lets SPARQL answer "show me the words that create this deadline".

### 4.7 Case law

The 117 existing cluster items (Q22) gain *court* (→ court item), *date decided*, *CourtListener ID* and keep P13
→ the section. New ones follow when `case_law` grows.

### 4.8 International law: country keys, languages, laws as units

**Jurisdiction keys.** A US state keeps its two-letter postal code (`va`); a country is keyed by its ISO 3166-1
alpha-3 code in lower case (`jpn`; later `chl`, `aus`, `rou`, `gha`, `per`), never alpha-2, because alpha-2 codes
collide with postal codes (`co` Colombia and Colorado, `de` Germany and Delaware, `in` India and Indiana, `md`
Moldova and Maryland, `pa` Panama and Pennsylvania, and `ar`, `ga`, `id`, `la`, `ma`, `ms`, `mt`, `nc`, `sc`).
The key is the same everywhere: `lexflow:jurisdiction:jpn`,
`lexflow:code:jpn`, `lexflow:unit:jpn:<law id>`, `lexflow:statute:jpn:<citation>`, the index file
`data/index/statutes_jpn.sqlite` and the dashboard's pickers (`schema.is_country_key`, `states.COUNTRIES`). The
ELI IRIs lexflow mints keep the alpha-2 jurisdiction (`/eli/jp/act/1993/88/art_13/ja@2026-07-24`), as ELI
publishers write it; the US ones stay `/eli/us-va/...`.

**Languages.** Labels, descriptions and aliases may carry languages beside English (`graph.Item.labels`,
`.descriptions`, `.lang_aliases`; the push writes every language in one `wbeditentity`). A Japanese law's `ja`
label is its title; its English label is the official English title of the Japanese Law Translation database when
lexflow has one, never a romanisation, and until then it has none: an English description says what it is
("Japanese law (Act No. 88 of 1993)") and the English citation form is an English alias (changed 22 October 2026;
docs/design/wikidata-laws.md §3, which also gives the law item's full shape: identifiers, makers, amendments,
references).
*Heading text*, *law number* and *quoted text in language* are monolingual text tagged with the law's language
(`ja`); English *quoted text* keeps its string datatype, and verification compares a quote only with the text of
its own language (the `.../ja@<date>` expression), never across translations.

**Laws, not articles.** A country's body of law is one *legal code* item and each law one *statutory unit* at unit
level `act`:

```
lexflow:jurisdiction:jpn         "Japan" (ja 日本)        P5 jurisdiction; Wikidata item ID Q17
lexflow:code:jpn                 "Laws of Japan" (ja 日本の法令)   P5 legal code; P15 → Japan; unit level = code; official text https://laws.e-gov.go.jp/
lexflow:unit:jpn:405ac0000000088 (no en label; ja 行政手続法; alias "Act No. 88 of 1993", 行手法, 平成五年法律第八十八号)
                                 P5 statutory unit; P9 part of → code; P15 → Japan; unit level = act; heading text 行政手続法@ja;
                                 law number 平成五年法律第八十八号@ja; act identifier = 405AC0000000088 (e-Gov law_id);
                                 official text https://laws.e-gov.go.jp/law/405AC0000000088; effective date (the enforcement
                                 date of the version indexed); promulgation date; sort key; topic where the e-Gov category maps
```

Articles (条, one index row each, 附則 articles under their supplementary provision) stay in the search index; an
article becomes a *statute* item (unit level `article`, *part of* → its law, heading text in `ja`) only when a
process, rung or local process cites it, as US sections do. The e-Gov category maps to a topic where one fits
(`schema.EGOV_CATEGORY_TOPIC`: 国税 and 地方財政 taxes, 社会福祉 and 社会保険 benefits, 建築・住宅 and 都市計画 building and
zoning, 土地 property, 商業 and 事業 business, 司法 courts); the others have no topic yet.

## 5. The Claude in Chrome packet (`out/wikibase/`)

Claude Code cannot sign in to Wikibase Cloud (OAuth in the in-app browser fails), so writes go through Claude in
Chrome, signed in as the user, pasting QuickStatements batches into
`https://lexipedia.wikibase.cloud/tools/quickstatements/`. Reads (resolving the Q and P ids the batches created)
need no login and run from lexflow.

`python -m lexflow.publish.qs` writes:

| File | Pass | What |
|---|---|---|
| `README.md` | – | the instructions for Claude in Chrome (§5.1) |
| `01-properties.qs` | 1 | `CREATE_PROPERTY` lines for §3, with `Len`, `Den`, `Aen`, then P7 / formatter claims using `LAST` |
| `02-classes.qs` | 1 | class and vocabulary items: `CREATE`, `LAST Len`, `LAST Den`, `LAST P25 "lexflow:class:…"`, `LAST P5 …` (P5's target must already exist, so classes come before vocabularies) |
| `03-items-<kind>.qs` | 1 | every new item of §4 with only its label, description, aliases and P25 (no relations yet). One file per kind: codes and units, governments, agencies, positions, forms, outcomes, rungs, local processes and their steps |
| `ids.json` | between | written by `--resolve`: every P25 key → Q, every property label → P, read from the public API (`wbsearchentities` plus `haswbstatement:P25=` via CirrusSearch, then `wbgetentities` to confirm) |
| `04-claims-<kind>.qs` | 2 | every relation, qualifier and reference of §4, with ids from `ids.json` |
| `05-updates.qs` | 2 | additions to existing items (sections gain P9, sort key, heading; roles gain played by; jurisdictions gain Wikidata item ID; clusters gain court and date) |
| `check.rq` | after | the SPARQL of §6 with the expected counts, run by `--check` against the live endpoint |

Batch sizes stay under 2,000 lines so QuickStatements' batch mode finishes; the generator splits with `-a`, `-b`
suffixes. Lines are tab-separated V1 commands; strings are quoted; times use `+2026-10-15T00:00:00Z/11`; quantities
`5` or `75U<USD item>`; monolingual text `en:"…"`. Item creation uses `CREATE` and `LAST`; nothing else in a
pass-1 file refers to a new item, which is why the passes are split.

### 5.1 README for Claude in Chrome (generated)

1. Sign in at https://lexipedia.wikibase.cloud with the operator's account (the operator does this; Claude never
   handles the password).
2. Open QuickStatements, "New batch", paste `01-properties.qs`, check the preview shows 49 property creations
   and nothing else, "Run". Wait until every line shows done. Note the P-ids QuickStatements prints (the resolver
   reads them anyway).
3. Paste `02-classes.qs`, then each `03-*.qs` in name order. Each file says how many `CREATE` lines it holds; the
   preview count must match before running. Run batches in the background ("Run in background"), one at a time.
4. Tell Claude Code "pass 1 is done". It runs `--resolve` (reads only) and writes the `04-*.qs` and `05-*.qs` files.
5. Paste those in name order the same way.
6. Tell Claude Code "pass 2 is done". It runs `--check`: the §6 queries against the live endpoint with the expected
   counts, and reports what is missing.
7. Never: delete an item, merge items, edit `Project:` pages, change a label by hand, or run a batch whose preview
   count differs from the file's header. If QuickStatements shows errors, stop and paste the error lines back.

Each `.qs` file starts with a comment header: the pass, the counts by command type, and the lexflow git commit it
was generated from.

### 5.2 EntitySchemas (optional, same packet)

`06-entityschemas/*.shex` holds a ShEx shape per kind (section, unit, agency, position, process, step, rung, local
process). Claude in Chrome creates each at `Special:NewEntitySchema` (paste label, description and the text). They
document the shapes on the wiki itself; nothing depends on them.

## 6. Queries that must work afterwards (`lexflow/publish/sparql/*.rq`)

Every file begins with the six `lx*` prefixes and uses `{P:label}` / `{Q:key}` tokens that the runner replaces from
`ids.json` (local or live), so one file runs against both stores.

| File | Question |
|---|---|
| `law-in-order.rq` | every section of Va. Code Title 2.2 Chapter 37 in the code's order, with heading, effective dates and official text |
| `law-tree.rq` | the ancestors of § 2.2-3704 up to the code (`lxt:P9+`), with unit levels |
| `law-neighbours.rq` | what § 2.2-3704 references and what references it, with reference types and the quoted words |
| `law-in-force.rq` | sections of a chapter in force on a given date |
| `who-does-what.rq` | for a jurisdiction: process → step → bearer role → played by body → body's parent chain and head position, with the step's deadline and the quote that creates it |
| `process-steps.rq` | one process's steps in order (`lxt:P11*`), with kind, bearer, recipient, deadline, form and fee |
| `deadlines.rq` | every time limit in a jurisdiction, with unit, counted-from, on-expiry and the quote |
| `escalation.rq` | from any step: the escalation and deferral chain (`(lxt:{P:escalates to}|lxt:{P:defers to})+`) with type, body, time limit and section |
| `body-contacts.rq` | a body, its office channels with sources and retrieval dates, and every process it plays a role in |
| `by-topic.rq` | processes by topic and audience, with their plain-language question and review status |
| `find-process.rq` | full-text search over labels, aliases and question asked (`MCRS` / `wikibase:mwapi` on the live service; `CONTAINS` locally) |
| `federated-body.rq` | a body's Wikidata head and parent through `SERVICE <https://query.wikidata.org/sparql>` using `lxn:` normalised IRIs (live only) |
| `coverage.rq` | counts by class and review status (the `--check` numbers) |

## 7. Running SPARQL locally

`lexflow/publish/rdf.py` writes the same items and statements as Turtle under `data/wikibase/lexipedia.ttl`, using
the Wikibase RDF layout (`lx:`, `lxt:`, `lxp:`/`lxps:`/`lxpq:`/`lxpr:` with statement nodes, `rdfs:label`,
`schema:description`, `skos:altLabel`), with ids from `ids.json` where resolved and provisional ids (`P900+`,
`Q900000+`) where not, so the queries run before anything is on the wiki. `pyoxigraph` (BSD/Apache, pure wheel,
added to `requirements.txt`) loads it into `data/wikibase/store/`.

- `lexflow sparql <file.rq|query> [--live]` runs a query locally, or against
  `https://lexipedia.wikibase.cloud/query/sparql` with `--live`, and prints a table or `--json`.
- `GET /api/sparql?q=…&live=0|1` for the dashboard, and a **Query** page with the §6 queries as buttons, a text box
  and a results table. The dashboard is on 127.0.0.1 only, so no sign-in question arises.
- Local and live results for `coverage.rq` are compared by `--check`.

## 8. Open questions for the operator

1. Hosting review: the Wikibase Cloud policy of 27 August 2026 needs `Project:Copyrights` (CC0 for data) and a
   `Project:People` rule; the packet's README reminds the operator, since these are wiki pages, not QuickStatements.
2. Whether governments beyond the six with place pages should be written (38,640 exist; the recommendation is no,
   only those something points at).
3. Whether draft (`single`) models go up at all. The recommendation is yes, marked `draft`, so the coverage query
   shows what is unreviewed.

### 8.1 Vocabulary links suggested by the classifier (16 October 2026)

`python -m lexflow.publish.vocab_links --build` ran the suggestion classifier of `lexflow.law.terms` (`link`, the
survey-fitted model, review threshold 0.5) over every vocabulary item and every class without a Wikidata QID
(108 targets; Wikidata searched read-only, `wbsearchentities` and `wbgetentities`, one request every two
seconds) and wrote `fixtures/entities/vocab_links.json` (`{key: {qid, label, relation, p, reviewed: false}}`;
`vocab_links.get(key)` reads it). 66 targets got a suggestion; the two marked
**write** (relation exact, p ≥ 0.9) are the ones the graph may write as `P8 exact match` once reviewed, through
the three-line hook in `vocab_links.writable`. The operator's example holds: `lexflow:vocab:topic:courts` →
[Q41487](https://www.wikidata.org/wiki/Q41487) court (p 0.815). The classifier was fitted on defined legal terms,
not on these one-word labels, so several suggestions are plainly wrong and are listed for that reason (condition →
disease, other → non-binary, part → partitive case, act → statute, superseded → deprecation, resident →
inhabitant, applicant → candidate): set `reviewed` to true with the right `qid` (or `null`) in the file. Nothing is
a match until reviewed.

| Key | Term | Wikidata | Relation | p |
|---|---|---|---|---|
| `lexflow:class:audience` | audience | [Q211198](https://www.wikidata.org/wiki/Q211198) audience | exact | 0.686 |
| `lexflow:class:court-decision` | court decision | [Q327000](https://www.wikidata.org/wiki/Q327000) court decision | exact | 0.889 |
| `lexflow:class:decision-point` | decision point | [Q942966](https://www.wikidata.org/wiki/Q942966) Decision Points | exact | 0.542 |
| `lexflow:class:government` | government | [Q7188](https://www.wikidata.org/wiki/Q7188) government | exact | 0.715 |
| `lexflow:class:jurisdiction` | jurisdiction | [Q471855](https://www.wikidata.org/wiki/Q471855) jurisdiction | exact | 0.9 **write** |
| `lexflow:class:legal-process` | legal process | [Q85776190](https://www.wikidata.org/wiki/Q85776190) legal process | exact | 0.549 |
| `lexflow:class:legal-role` | legal role | [Q83856136](https://www.wikidata.org/wiki/Q83856136) legal position | exact | 0.778 |
| `lexflow:class:permission` | Permission | [Q7169333](https://www.wikidata.org/wiki/Q7169333) permission | exact | 0.307 |
| `lexflow:class:reference-type` | reference type | [Q1334113](https://www.wikidata.org/wiki/Q1334113) reference data type | exact | 0.482 |
| `lexflow:class:right` | Right | [Q780687](https://www.wikidata.org/wiki/Q780687) rights | exact | 0.592 |
| `lexflow:class:statutory-unit` | statutory unit | [Q65330337](https://www.wikidata.org/wiki/Q65330337) statutory unit | exact | 0.663 |
| `lexflow:class:time-unit` | time unit | [Q1790144](https://www.wikidata.org/wiki/Q1790144) unit of time | exact | 0.689 |
| `lexflow:vocab:audience:applicant` | applicant | [Q618536](https://www.wikidata.org/wiki/Q618536) candidate | exact | 0.423 |
| `lexflow:vocab:audience:business` | business | [Q4830453](https://www.wikidata.org/wiki/Q4830453) business | exact | 0.79 |
| `lexflow:vocab:audience:property-owner` | property owner | [Q11293375](https://www.wikidata.org/wiki/Q11293375) proprietor | exact | 0.486 |
| `lexflow:vocab:audience:resident` | resident | [Q22947](https://www.wikidata.org/wiki/Q22947) inhabitant | exact | 0.257 |
| `lexflow:vocab:currency:usd` | US dollar | [Q4917](https://www.wikidata.org/wiki/Q4917) United States dollar | exact | 0.88 |
| `lexflow:vocab:determination-method:curated` | curated | [Q101392702](https://www.wikidata.org/wiki/Q101392702) Curated | exact | 0.856 |
| `lexflow:vocab:escalation-type:advisory-opinion` | advisory opinion | [Q4686864](https://www.wikidata.org/wiki/Q4686864) advisory opinion | exact | 0.828 |
| `lexflow:vocab:escalation-type:delegation` | delegation | [Q1184065](https://www.wikidata.org/wiki/Q1184065) delegation | exact | 0.732 |
| `lexflow:vocab:escalation-type:judicial-review` | judicial review | [Q898871](https://www.wikidata.org/wiki/Q898871) judicial review | exact | 0.928 **write** |
| `lexflow:vocab:escalation-type:referral` | referral | [Q2667988](https://www.wikidata.org/wiki/Q2667988) referral | exact | 0.587 |
| `lexflow:vocab:reference-type:authority` | authority | [Q174834](https://www.wikidata.org/wiki/Q174834) authority | exact | 0.58 |
| `lexflow:vocab:reference-type:condition` | condition | [Q12136](https://www.wikidata.org/wiki/Q12136) disease | exact | 0.449 |
| `lexflow:vocab:reference-type:definition` | definition | [Q101072](https://www.wikidata.org/wiki/Q101072) definition | exact | 0.777 |
| `lexflow:vocab:reference-type:exception` | exception | [Q779608](https://www.wikidata.org/wiki/Q779608) exception | exact | 0.343 |
| `lexflow:vocab:reference-type:other` | other | [Q48270](https://www.wikidata.org/wiki/Q48270) non-binary | exact | 0.207 |
| `lexflow:vocab:reference-type:penalty` | penalty | [Q7162177](https://www.wikidata.org/wiki/Q7162177) penalty | exact | 0.368 |
| `lexflow:vocab:review-status:agreed` | agreed | [Q141103400](https://www.wikidata.org/wiki/Q141103400) agreed | exact | 0.701 |
| `lexflow:vocab:review-status:draft` | draft | [Q244777](https://www.wikidata.org/wiki/Q244777) draft | exact | 0.347 |
| `lexflow:vocab:review-status:reviewed` | reviewed | [Q65066798](https://www.wikidata.org/wiki/Q65066798) Reviewed | exact | 0.522 |
| `lexflow:vocab:review-status:superseded` | superseded | [Q280943](https://www.wikidata.org/wiki/Q280943) deprecation | exact | 0.283 |
| `lexflow:vocab:step-kind:act` | act | [Q820655](https://www.wikidata.org/wiki/Q820655) statute | exact | 0.573 |
| `lexflow:vocab:step-kind:decision` | decision | [Q16513426](https://www.wikidata.org/wiki/Q16513426) decision | exact | 0.711 |
| `lexflow:vocab:step-kind:filing` | filing | [Q17146064](https://www.wikidata.org/wiki/Q17146064) filing | exact | 0.547 |
| `lexflow:vocab:step-kind:hearing` | hearing | [Q160289](https://www.wikidata.org/wiki/Q160289) hearing | exact | 0.778 |
| `lexflow:vocab:step-kind:inspection` | inspection | [Q1137655](https://www.wikidata.org/wiki/Q1137655) inspection | exact | 0.631 |
| `lexflow:vocab:step-kind:notice` | notice | [Q7063001](https://www.wikidata.org/wiki/Q7063001) notice | exact | 0.561 |
| `lexflow:vocab:step-kind:payment` | payment | [Q1148747](https://www.wikidata.org/wiki/Q1148747) payment | exact | 0.874 |
| `lexflow:vocab:step-kind:review` | review | [Q265158](https://www.wikidata.org/wiki/Q265158) review | exact | 0.818 |
| `lexflow:vocab:time-unit:business-days` | business days | [Q12779928](https://www.wikidata.org/wiki/Q12779928) business day | exact | 0.852 |
| `lexflow:vocab:time-unit:calendar-days` | calendar days | [Q5019497](https://www.wikidata.org/wiki/Q5019497) calendar day | exact | 0.418 |
| `lexflow:vocab:time-unit:hours` | hours | [Q25235](https://www.wikidata.org/wiki/Q25235) hour | exact | 0.702 |
| `lexflow:vocab:time-unit:months` | months | [Q5151](https://www.wikidata.org/wiki/Q5151) month | exact | 0.708 |
| `lexflow:vocab:time-unit:weeks` | weeks | [Q23387](https://www.wikidata.org/wiki/Q23387) week | exact | 0.551 |
| `lexflow:vocab:time-unit:work-days` | work days | [Q12779928](https://www.wikidata.org/wiki/Q12779928) business day | exact | 0.659 |
| `lexflow:vocab:time-unit:working-days` | working days | [Q138507936](https://www.wikidata.org/wiki/Q138507936) Working Days | exact | 0.373 |
| `lexflow:vocab:time-unit:years` | years | [Q577](https://www.wikidata.org/wiki/Q577) year | exact | 0.422 |
| `lexflow:vocab:topic:animals` | animals | [Q729](https://www.wikidata.org/wiki/Q729) animal | exact | 0.662 |
| `lexflow:vocab:topic:business` | business | [Q4830453](https://www.wikidata.org/wiki/Q4830453) business | exact | 0.79 |
| `lexflow:vocab:topic:courts` | courts | [Q41487](https://www.wikidata.org/wiki/Q41487) court | exact | 0.815 |
| `lexflow:vocab:topic:criminal-records` | criminal records | [Q1070100](https://www.wikidata.org/wiki/Q1070100) criminal record | exact | 0.509 |
| `lexflow:vocab:topic:licensing` | licensing | [Q117037890](https://www.wikidata.org/wiki/Q117037890) licensing | exact | 0.351 |
| `lexflow:vocab:topic:property` | property | [Q1400881](https://www.wikidata.org/wiki/Q1400881) property | exact | 0.561 |
| `lexflow:vocab:topic:public-records` | public records | [Q7257959](https://www.wikidata.org/wiki/Q7257959) public records | exact | 0.765 |
| `lexflow:vocab:topic:taxes` | taxes | [Q8161](https://www.wikidata.org/wiki/Q8161) tax | exact | 0.472 |
| `lexflow:vocab:topic:voting` | voting | [Q189760](https://www.wikidata.org/wiki/Q189760) voting | exact | 0.806 |
| `lexflow:vocab:unit-level:act` | act | [Q820655](https://www.wikidata.org/wiki/Q820655) statute | exact | 0.573 |
| `lexflow:vocab:unit-level:article` | article | [Q103184](https://www.wikidata.org/wiki/Q103184) article | exact | 0.418 |
| `lexflow:vocab:unit-level:chapter` | chapter | [Q1980247](https://www.wikidata.org/wiki/Q1980247) chapter | exact | 0.674 |
| `lexflow:vocab:unit-level:division` | division | [Q1226939](https://www.wikidata.org/wiki/Q1226939) division | exact | 0.427 |
| `lexflow:vocab:unit-level:part` | part | [Q857325](https://www.wikidata.org/wiki/Q857325) partitive case | exact | 0.227 |
| `lexflow:vocab:unit-level:section` | section | [Q3181348](https://www.wikidata.org/wiki/Q3181348) section | exact | 0.844 |
| `lexflow:vocab:unit-level:subsection` | subsection | [Q5998839](https://www.wikidata.org/wiki/Q5998839) subsection | exact | 0.537 |
| `lexflow:vocab:unit-level:subtitle` | subtitle | [Q204028](https://www.wikidata.org/wiki/Q204028) subtitle | exact | 0.685 |
| `lexflow:vocab:unit-level:title` | title | [Q216353](https://www.wikidata.org/wiki/Q216353) title | exact | 0.819 |

No suggestion (best candidate below p 0.2): `achievement-obligation`, `deontic-specification`, `determination-method`, `escalation-mechanism`, `escalation-type`, `legal-process-step`, `maintenance-obligation`, `norm`, `office-type`, `position-type`, `process-outcome`, `prohibition`, `review-status`, `statute`, `statutory-power`, `step-kind`, `strong-permission`, `topic`, `unit-level`, `weak-permission`, `audience:requester`, `audience:visitor`, `determination-method:ai-verifier`, `determination-method:http-check`, `determination-method:official-page`, `determination-method:software-match`, `escalation-type:compliance-board`, `escalation-type:deferral-to-another-process`, `escalation-type:external-administrative-review`, `escalation-type:internal-appeal`, `escalation-type:ombudsman-mediation`, `escalation-type:oversight-inspector-general`, `reference-type:override`, `reference-type:prerequisite_process`, `reference-type:procedure`, `reference-type:scope`, `step-kind:delivery`, `step-kind:record`, `topic:benefits`, `topic:building-and-zoning`, `unit-level:code`, `unit-level:subchapter`.
