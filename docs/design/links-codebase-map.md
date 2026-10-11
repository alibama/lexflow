# Links, terms and decision requirements: codebase map

Status: design input (read-only survey), 2026-10-10. Nothing in the code was changed.

This map covers three planned additions:

1. **Typed cross-references between statute sections.** For example, "must comply with s. 605.0112" becomes a resolved edge of type *requirement incorporated by reference*.
2. **Defined terms and roles as addressable entities.** For example, *incorporator* becomes one item that Fla. Stat. § 607.0201 (Wikibase Q168), Va. Code § 13.1-618, N.C.G.S. § 55-2-01 and D.C. Code § 29-302.01 all point at.
3. **Links between process models and DMN decision requirements.** One process's output becomes another's input or condition. Decisions, input data and knowledge sources point at sections.

For each one, the map says what exists today, which IDs exist and which of them are stable, and where the new links would be stored (IR fields, DB tables, XML, Wikibase properties). It ends with concrete extension points as `file:line`.

Numbers marked *measured* come from read-only probes of the running container's DB and indexes, and from read-only `wbgetentities` calls to lexipedia.wikibase.cloud and wikidata.org, all on 2026-10-10.

---

## 0. Key points

- **Cross-references are found but never stored.** Three mechanisms exist and none of them persists edges.
  - `ask/retrieve.py:91 cited()` is a regex resolver used only as a retrieval vote.
  - `text/citations.py:58 find_citations()` covers only Virginia municipal codes. It has typed `kind` values and character offsets. It is used by `extract/searx.py:70`.
  - `FCrossRef` in the facts schema (`extract/schema.py:91`) is quote-checked (`extract/ollama.py:62`), but `compile_facts` drops it. It never reaches the IR, BPMN, DMN, Wikibase or the wiki pages.
- **`cited()` finds nothing in Florida.** Florida cites as `s. 605.0112` and `ss. 605.0213`, and the `XREF` regex (`retrieve.py:78`) needs `§`, `section` or `article`. Measured: `cited()` returned `[]` for 605.0201, 605.0210, 607.0201, 205.023 and 607.193. Each of those texts holds 1 to 6 `s. N` citations.
  - A naive `s. N` pattern would also catch history notes ("ch. 2019-90, s. 16"). These must be stripped (`statutes.strip_history`) or excluded.
  - Virginia works: 2.2-3704 resolves 4 of its 6 citations. There is noise such as the "60" in `§ 2.2-3706.1 , 60 work days`, and an unresolved federal `§ 1232g`.
- **Most curated "cross_references" are annotations, not edges.** Measured over 282 curated cross-references:
  - 222 cite the very section their quote comes from. Their free-text `role` describes what the provision does (fee rows, effects).
  - Only 60 point to another section.
  - 214 of the 282 resolve to an index row. Only 29 of the resolved ones are also found by `cited()` from the model's own sections.
  - Some do not resolve because the code name is abbreviated: Maryland `Corps. & Ass'ns` against the index's `Corporations and Associations`, and several California codes.
  - The design needs two relation types, *cites* and *annotates*, plus an alias table of code names.
- **Roles exist only per state and per question. No item stands for the concept.**
  - Wikibase role items are keyed `lexflow:role:{state}:{question}:{actor_id}` (`publish/wikibase_lexipedia.py:331`).
  - Each carries only P25, P5 → Q23 (legal role) and P15. Example: Q775 "Authorized representative (founder) (Florida)".
  - No role item links to the section that names the role, although `FActor.source` holds that quote. No role item links to a cross-state concept.
  - Actor ids repeat across curated models: `requester` ×10, `court` ×10, `organizer` ×9, `llc` ×9. These are the natural seeds for concept items.
- **Q168 today.** Measured: Q168 = `lexflow:statute:fl:607.0201`, "Fla. Stat. § 607.0201", described as "607.0201 Incorporators."
  - Its claims are P25, P5 → Q10, P22, P15 → Q33 and P23.
  - Its only backlink is Q774, the fl.business process, through an unqualified P13.
  - Inside the model, § 607.0201 is quoted only by `business_structure` decision rules. Decisions are not loaded to Wikibase, so that use is invisible there.
  - The same "Incorporators" section exists as Q512 (va 13.1-618), Q334 (nc 55-2-01) and Q147 (dc 29-302.01). All are descendants of Model Business Corporation Act § 2.01.
- **Wikidata has no "incorporator" legal concept and no English lexeme for it.** The search hit Q140403634 is a PropBank agent prototype and is unrelated.
  - Nearby Wikidata anchors: Q17013292 *articles of incorporation*, Q6888224 *Model Business Corporation Act*, Q16821865 *articles of organization*, Q7309406 *registered agent*, Q149789 *limited liability company (US)*, Q1417728 *trade name*, Q102046748 *freedom of information law*.
  - Class for terms: Q2135465 *legal term or legal concept*.
  - So *incorporator* should be a Lexipedia-native, addressable concept. It would carry `P8 exact match` only where Wikidata has an item. Otherwise it relates to MBCA and *articles of incorporation*.
- **DMN today is decision tables only.**
  - `dmn_xml.write_dmn` (`dmn_xml.py:39`) emits `decision` + `decisionTable`. It emits no `inputData`, `knowledgeSource`, `informationRequirement`, `authorityRequirement`, `decisionMaker`, `usingProcess` or DMNDI edges.
  - Requirements exist only implicitly:
    - 55 flow conditions in curated models are named exactly like a decision output (FL `articles_ok`).
    - 72 conditions are free variables, which is undeclared input data (`contests_refusal`, `local_tax_required`).
    - Decision input names are shared across all 11 business models (`owners`, `nonprofit`, `licensed_profession`, `limited_liability`, `outside_investors`, `passive_partners`). They are a ready vocabulary for addressable input data.
- **The Wikibase ontology already anticipates more than lexflow writes.** P14 *based on*, P18 *condition* ("may reference a DMN decision"), P19 *governed by norm*, P20 *sanction*, P21 *defeated by* and P24 *effective date* exist and are unused by the live loader. P6 *subclass of* is looked up and never written. There is no P26 or higher. The eight `PROPOSED` properties in `publish/wikibase.py:36` were never created.
- **IDs.**
  - `act_id` (open-us-law, e.g. `STATE_FL_TXXXVI_C607_PI_S607.0201`) is unique per index row in every state probed (fl, va, ny, md, az). It is the best stable section key. It already rides into the IR, but only inside the free-text `SectionText.retrieved_from` (`municipal/statutes.py:233`).
  - Index `sec.id` is a row number and changes with every rebuild. It must never be persisted.
  - `ref` can flip between a bare number and a full citation when uniqueness changes.
  - Wikibase statute keys use hand-typed spec strings and are not normalised.
- **A latent linking bug: step → statute P13 is chosen by suffix match.** At `wikibase_lexipedia.py:349`, `ref.endswith(src.section)` picks the first match. Quote sections are short (`402`, `090`, `1`), and the spec refs are long. Ambiguous cases measured:
  - NY `402` ∈ {BSC § 402, NPC § 402}
  - WA `010` ∈ {RCW 23B.02.010, RCW 19.80.010}
  - IL `1` matches 5 refs
  - IL `2.05` and `15.10` are ambiguous

  The fix is to resolve by quote containment. `_fix_sources` (`municipal/build.py:150`) already does exactly this for the IR.

---

## 1. Identifier inventory

| Thing | Example | Formed at | Stable? |
|---|---|---|---|
| State | `fl` | `municipal/states.py` | yes |
| Question | `business`, `records` | `municipal/questions.py` (`QUESTIONS`) | yes |
| DB model id | `fl.business` | `municipal/build.py:34-35` | yes (state models) |
| IR model id | `fl-business` (**differs from the DB id**) | `municipal/build.py:189` | yes, but a second spelling |
| BPMN/DMN namespaces | `https://lexipedia.xyz/ns/process/fl_business`, `.../ns/decision/fl_business` | `bpmn_xml.py:108`, `dmn_xml.py:45` | yes (derived from the IR id) |
| Process id | `proc_fl_business` | `extract/compile.py:247` | yes |
| Participant / lane | `p_agency`, `p_<actor>`, `ln_<actor>` | `compile.py:46,66,249-251` | as stable as the actor id |
| Step / node id | `review_articles` (curated, hand-chosen); `slug(action)` (selector) | `extract/schema.py:44`; `extract/strategies.py:145` | curated yes; selector **no** (changes with the extracted wording) |
| Derived node ids | `{id}_gw`, `{id}_join`, `{id}_deadline`, `{id}_done`, `{id}_merge` | `compile.py:86-235` | deterministic given the facts |
| Flow ids | `sf1`… | `compile.py:52-55` | **no** (positional counter) |
| Actor id | `organizer` (curated); `slug(normalised name)[:24]` (selector) | `schema.py:25`; `strategies.py:111-124` | curated yes; selector **no**; local to one model in both cases |
| Decision id | `articles_comply` | `schema.py:73` → `compile.py:240` | curated yes |
| Input / output clause ids | `{decision}_in_{name}`, `{decision}_out_{name}` | `compile.py:241-242` | yes (by column name) |
| Rule id | `{decision}_r{n}` | `compile.py:243` | **no** (positional) |
| Index row | `sec.id` = 22375 | `ask/index.py:208` (enumerate) | **no**: rebuilt with each statute file; never persist |
| Index `ref` | `607.0201`, or a full citation when the number is not unique | `ask/index.py:210`, `municipal/statutes.py:169-174` | mostly; can flip when a duplicate number appears |
| `norm_cite` | `fla stat § 607 0201` | `statutes.py:165-166` | yes, but VA has 4 duplicate citations |
| `act_id` | `STATE_FL_TXXXVI_C607_PI_S607.0201` | open-us-law column, `ask/index.py:194,216` | **unique per row in fl/va/ny/md/az**; best candidate (stability across releases unverified) |
| `SectionText.section` | `402` | `statutes.py:231` (`section_number`) | **not unique** in multi-code states (NY BSC § 402 vs NPC § 402) |
| Curated spec sections | `N.Y. LLC Law § 203`, `Corporations and Associations § 4A-202`, `RCW 25.15.071` | `curated/<st>/<q>.json` | hand-typed, mixed forms |
| Wikibase key (P25) | `lexflow:statute:fl:607.0201` | `publish/wikibase_lexipedia.py` (see §4) | yes as strings; built from the unnormalised refs above |
| Wikibase QID | Q168 | `wikibase_items(key, qid)` (`store/db.py:226-231`) | yes; the table is **local only** (not in `SYNCED`, `db.py:339`) |
| DokuWiki law page | `law:ny:402` | `publish/dokuwiki.py:41-42` | **collides** across codes in multi-code states |
| Old QuickStatements keys | `provision:{jurisdiction}:{section}`, `step:{model.id}:{node}`, `actor:{model.id}:{actor}` | `publish/wikibase.py:76-118` | a second, incompatible key scheme (alias `lexflow:<key>`) |
| Government | Census `gov_id`, optional Wikidata QID | `governments` table, `db.py:20-35` | yes |
| Court decision | `courtlistener:cluster:{id}` | `wikibase_lexipedia.py:378` | yes |

**Recommendation.** Key every section-level link by `(state, act_id)`, with `norm_cite` as the readable fallback. Keep `ref` and the hand-typed spec strings only as aliases. In Wikibase, add a canonical statute key, for example `lexflow:statute:{state}:act:{act_id}` or a normalised citation key, as a second P25 value. That way the old keys keep resolving.

---

## 2. What exists today, per link kind

### 2.1 Statute → statute cross-references

| Mechanism | Where | Output | Persisted? | Notes |
|---|---|---|---|---|
| `XREF` / `XNUM` regex + `cited(state, row)` | `ask/retrieve.py:77-80`, `:83-88` (`_code`), `:91-109` | index rows of cited sections in the same code | no, a retrieval vote only (`retrieve.py:163-169`, weight `PASS_WEIGHT["cited"]`) | misses `s. N` (Florida); `art.` handled only for article-numbered codes; resolves a bare number only within `_code(row)`, so "section 402 of the Not-for-Profit Corporation Law" from a BCL section resolves wrongly or not at all; returns at most 12 |
| `find_citations(text, jurisdiction)` | `text/citations.py:15-30` (patterns), `:33-40` (`Citation`), `:58-92` | `Citation(kind, section, text, start, end, url, wiki)` | no | Virginia municipal only; the best precedent for a typed, offset-anchored edge (`va-code`, `va-admin`, `charter`, `federal-pl`, `usc`, `local`) |
| `FCrossRef(citation, role, source: Quote)` | `extract/schema.py:91-94`, `:105` | inside `process_models.facts` JSON | as JSON only | quote checked in `extract/ollama.py:62`; ignored by `extract/compile.py` (no reference to `cross_references`); not rendered by `publish/lexipedia.py:129-181` |
| `located_law.related` | `municipal/locator.py:120-123` | up to 3 other candidate sections | JSON column | search alternates, not citations |
| Verified seed `alternates` | `municipal/build.py:91-119` (`related_sections`) | extra sections read with the located one | not as edges | "related sections" by human or Claude judgement, untyped |
| Section → process backlinks | `publish/dokuwiki.py:104-117` (`cited_by` → "Used by processes") | a DokuWiki section | page text only | the only rendered backlink |

Measured on curated data (282 cross-references, 229 model sections, all in the index):

- 222 are self-annotations, where the citation equals the quoted section. Only 60 are outgoing.
- 214 resolve to an index row by `I.lookup`. 178 of those resolve into the model's own sections.
- Only 29 of the resolved targets are also found by `cited()`. `cited()` found 235 edges in total from the model sections, and none in Florida.
- Unresolved citations are mostly abbreviation mismatches. Examples: `Md. Code, Corps. & Ass'ns § 1-204` against the index form `Md. Code, Corporations and Associations § …`, `Cal. Corp. Code § 200`, `6 DCMR § 1803` (regulation), `Fla. Const. art. I, § 24` (constitution), and lists such as `5 ILCS 140/7 and 140/8.5`.

### 2.2 Roles and defined terms

**Where actors come from**

| Path | Where | What is kept |
|---|---|---|
| Curated / Claude | `curated/<st>/<q>.json` → `facts.actors[]` = `FActor(id, name, kind, source: Quote)` (`extract/schema.py:24-28`) | 88 actors: private-party 33, public-body 21, court 13, other-government 12, official 9. Only 4 actor quotes are definitions ("Registrant" means…, FL 865.09(2)(d)) |
| Learned selector / strategies | `extract/strategies.py:111-124` (`Actors`, id = `slug(name)`); `:89-94` (`actor_kind` regex); `:132-133` (`filer_for`: `requester` / `organizer` / `applicant`); `:610-621` (`assign_actors`, kNN kinds) | id, name, kind, and the first clause that names it |
| LLM one-shot | `extract/ollama.py` prompt → `FActor` | same as curated |
| Hand gold models | `lexflow/gold.py:68-75` | IR `Actor` with `wikidata` (Albemarle Q488653, Charlottesville Q123766), `description` |
| Compilation | `extract/compile.py:43-47`, `:255` | IR `Actor(id, name, kind)`. **`FActor.source` is dropped**, and `wikidata`, `govdirectory` and `description` stay empty |
| BPMN | `bpmn_xml.py:194-197` (`lex:model/lex:actor`), `:203-208` (participant), `:229-233` (lane) | `lex:actor ref/wikidata` |
| Wikibase | `wikibase_lexipedia.py:329-335` | role item per (state, question, actor): P5 Q23, P15 only. It is built from `facts`, not from the IR, so even an IR `Actor.wikidata` would not reach it |
| DokuWiki | `publish/dokuwiki.py:164-167` | actor table with a Wikidata column |

**Defined terms.** None anywhere. Related hooks:

- `retrieve.py:26` and `ask/relevance.py:21` only *demote* definitions sections.
- The LOCUS `triage()` routes non-process chunks to a `glossary` bucket (`sources/locus.py:43-56`) that nothing consumes.
- Clause segmentation (`extract/segment.py`, `Clause(id, label, text, start, section)`) already yields exact, labelled spans. These are the natural unit for a `"X" means …` extractor.

**Incorporator case.** The word appears in curated quotes and outputs in 8 of 11 business models, but only DC has it in an actor name ("Founder (organizer or incorporator)"). The sections are below; the quotes come from `business_structure` rules.

| State | Section | Index title | Wikibase item |
|---|---|---|---|
| fl | 607.0201 | 607.0201 Incorporators. | Q168 |
| va | 13.1-618 | Incorporators | Q512 |
| nc | 55-2-01 | Incorporators. | Q334 |
| dc | 29-302.01 | Incorporators. | Q147 |
| wa | RCW 24.03A.090 (nonprofit) | | Q536 |
| ny | BSC § 402, NPC § 402 | | |
| il | 805 ILCS 5/2.05 | | |
| md | Corps. & Ass'ns § 2-102 | | |

A search of the Definitions sections (fl 607.01401, va 13.1-603, nc 55-1-40) found no "Incorporator" definition. The term is defined functionally by the section that the heading names. So a term can be anchored in two ways:

- by a definitions clause (`"X" means`)
- by a section whose heading is the term

### 2.3 Process ↔ process

| Mechanism | Where | Scope |
|---|---|---|
| `Node.called_element` (callActivity) | `ir.py:106`; written at `bpmn_xml.py:312-313` | free string; "may live in another model". The only working example is gold Albemarle `a_jr` → `va_62_1_44_15_46_judicial_review` (`gold.py:256-257`, stub `:347-366`), resolved at simulation time (`tests/test_simulation.py:15`) |
| `DataRef` + `data_inputs` / `data_outputs` | `ir.py:75-81`, `:112-114`; `bpmn_xml.py:289-300`, `:355-365` | within one model; only gold models use them; `compile_facts` never creates DataRefs |
| `MessageFlow` | `ir.py:158-164`; `compile.py:81-82,106` | between pools of one model |
| Flow conditions | `SequenceFlow.condition` (`ir.py:71`); `compile.py:166-198` | variable names. 55 curated conditions equal a decision output name; 72 are free (undeclared process inputs, often another process's result, e.g. FL `local_tax_required` → the local business tax receipt process) |
| State model → local procedure | `publish/lexipedia.py:243-289` ("Full state model:" link); `answers.model_id` (`db.py:139`) | by question id only |
| Wikibase | P9 / P10 / P11 per process (`wikibase_lexipedia.py:336-366`); `_precedence` P11/P12 (`publish/wikibase.py:156-178`) | within one process |

### 2.4 DMN generation today

1. **Facts.** `FDecision(id, question, hit_policy UNIQUE|FIRST, inputs[FColumn(name, label, type string|number|boolean)], outputs[…], rules[FRule(when, then, source)])` (`extract/schema.py:60-78`). A step points at a decision with `FStep.decision` (`:56`). `check_facts` checks that the decision id exists and that the cell counts match (`extract/ollama.py:77-78,88-90`). It does not check that conditions name outputs.
2. **Compile.** `compile.py:237-244` produces an IR `Decision`:
   - `name = question[:80]`
   - `InputClause(id, label, expression=name, type_ref)`, with no allowed `values`
   - `Rule(id positional, sources=[src(rule.source)])`
   - `Decision.sources` is **empty**, so `dmn_xml.py:54-59` writes no "Grounded in" description for compiled models.

   A step with a decision becomes a `businessRuleTask` with `decision_ref` (`compile.py:72,77`).
3. **BPMN.** `camunda:decisionRef` (`bpmn_xml.py:327-328`) and `spiffworkflow:calledDecisionId` (`:343-344`).
4. **DMN XML.** `write_dmn` (`dmn_xml.py:39-101`) writes:
   - `definitions`
   - per decision: `description`, `extensionElements/lex:grounding`, `question`, then `decisionTable` (inputs, outputs, a FEEL-only `annotation` "Source" column, rules with `lex:source`)
   - DMNDI: one `DMNShape` per decision, with no edges

   `write_dmn_split` (`:104-106`) writes one decision per file in the Python dialect for SpiffWorkflow.
5. **Built and checked.** `municipal/quality.py:35-40`: `write_dmn` runs when decisions exist, then the DMN 1.3 XSD (`validate.xsd_errors`). Stored in `process_models.dmn` (`db.py:87`).
6. **Evaluated.** `dmn_eval.py:8-45` (`decide`, `completeness_gaps`, `overlaps`).
7. **Published.**
   - DokuWiki: `publish/lexipedia.py:117-126,152-155` (table from facts) and `publish/dokuwiki.py:153-154` (inline `<bpmnio type="dmn">`).
   - Wikibase: decisions **not loaded**. A step with a decision becomes `instance of` Q9 *decision point* (`wikibase_lexipedia.py:338`). `publish/wikibase.py:94-95` adds `{P:dmn_model}`, a placeholder for a property that does not exist.

DMN 1.3 already has the needed slots. In XSD order inside `tDecision` (`schemas/dmn/DMN13.xsd:92-113`) they are:

- `question`
- `allowedAnswers`
- `variable`
- `informationRequirement*`, `knowledgeRequirement*`, `authorityRequirement*`
- `supportedObjective*`, `impactedPerformanceIndicator*`
- `decisionMaker*`, `decisionOwner*`
- `usingProcess*`, `usingTask*`
- `expression` (the `decisionTable`)

`tKnowledgeSource` (`:176-187`) has a `locationURI`, a `type` and an `owner`. `tInputData` (`:166-174`) has a `variable`. Section URL → `knowledgeSource@locationURI`, actor → `decisionMaker` or `owner`, businessRuleTask → `usingTask`: the standard DMN elements cover all three.

---

## 3. Wikibase (lexipedia.wikibase.cloud): properties and item kinds

### 3.1 Properties on the live wiki

All P-numbers that exist (P1–P60 were queried; nothing above P25). "≡" is the `P7 equivalent property` value on the property itself.

| P | Datatype | Label | Meaning (wiki description) | ≡ Wikidata | Written by |
|---|---|---|---|---|---|
| P1–P3 | item | father / mother / child | sandbox defaults, unrelated | – | – |
| P4 | commonsMedia | image | sandbox default | – | – |
| P5 | item | instance of | class membership | P31 | Loader, QS |
| P6 | item | subclass of | subclass | P279 | looked up by Loader (`PROPS`), **never written** |
| P7 | url | equivalent property | owl:equivalentProperty mapping | – | wiki admin |
| P8 | url | exact match | skos:exactMatch to an external IRI (Wikidata, LegalRuleML/NRV) | – | Loader (governments only, `:254-255`), QS |
| P9 | item | part of | node is part of a whole (process, statute) | P361 | Loader, QS |
| P10 | item | has part | whole has the node as a part | P527 | Loader, QS |
| P11 | item | follows | process order | P155 | Loader, QS |
| P12 | item | followed by | process order | P156 | QS only |
| P13 | item | references | node references / cites an entity (statute, work) | P2860 (cites work) | Loader (process → statutes, step → statute, case → statutes), QS |
| P14 | item | based on | derived from | P144 | unused |
| P15 | item | applies to jurisdiction | jurisdiction | P1001 | Loader, QS |
| P16 | item | deontic modality | Obligation / Permission / Prohibition / Right (LegalRuleML) | – | Loader, QS |
| P17 | item | bearer | party bound by the norm (LegalRuleML Bearer) | – | Loader (step → role), QS (as a qualifier) |
| P18 | item | condition | condition under which the deontic specification holds; **may reference a DMN decision** | – | unused |
| P19 | item | governed by norm | the norm that governs this node | – | unused |
| P20 | item | sanction | penalty / reparation on violation | – | unused |
| P21 | item | defeated by | norm or exception that defeats / overrides this one | – | unused |
| P22 | string | citation | statutory citation | – | Loader, QS (also as a qualifier) |
| P23 | url | official text | link to the official text | – | Loader, QS |
| P24 | time | effective date | date the provision takes effect | – | QS only (`publish/wikibase.py:108-111`) |
| P25 | external-id | legal identifier | canonical external id; lexflow puts its key here | – | Loader (every item), QS (as `legal_id`) |

Classes: Q7 legal process, Q8 legal process step, Q9 decision point, Q10 statute or legal provision, Q11 norm, Q12 deontic specification, Q13 Obligation, Q14 Permission, Q15 Prohibition, Q16 Right, Q17 weak permission, Q18 strong permission, Q19 achievement obligation, Q20 maintenance obligation. Q21 jurisdiction, Q22 court decision and Q23 legal role were created by lexflow. Q1–Q6 are sandbox examples.

There are two writers, and they do not agree:

- **Live loader, `publish/wikibase_lexipedia.py`.** It looks properties and classes up by English label (`PROPS` `:29-32`, `CLASSES` `:33-37`, `prepare` `:142-155`) and writes with `wbeditentity`. With `clear` it replaces lexflow-owned items' statements on update (`:163-169`).
- **Older `publish/wikibase.py`.** It has hard-coded P and Q numbers (`:29-35`, which match the live wiki) and emits QuickStatements/bot payloads with `{P:…}` placeholders for 8 proposed properties (`:36-45`: `bpmn_model`, `dmn_model`, `wiki_page`, `time_limit`, `deadline_anchor`, `grounding`, `bpmn_element`, `performed_by`). Those were never created. It is used for the gold models (`out/wikibase/*.qs`).

### 3.2 Item kinds and how keys are formed (live loader)

| Kind | P25 key | Formed at | Claims | Count (local `wikibase_items`) |
|---|---|---|---|---|
| class | `lexflow:class:{label}` | `:155` | – | 3 (Q21–Q23) |
| state | `lexflow:jurisdiction:{state}` | `:244` | P5 Q21 | 52 |
| place | `lexflow:gov:{gov_id}` | `:256` | P5 Q21, P9 → state, P8 → Wikidata URL | 3 |
| statute | `lexflow:statute:{state}:{ref}`; `ref` = an entry of `metrics.sections` (the curated spec string) or `located_law.section` | `:261-280`; refs collected `:282-299`; deduplicated by citation label within a run `:265-273` | P5 Q10, P22, P15, P23 | 496 |
| process | `lexflow:process:{model_id}` (`fl.business`) | `:310` | P5 Q7, P15, P13 → every `metrics.sections` statute, P10 → steps | 48 |
| role | `lexflow:role:{state}:{question}:{actor_id}` | `:331` | P5 Q23, P15 | 199 |
| step | `lexflow:step:{model_id}:{step_id}` (a facts step id = an IR node id) | `:358` | P5 Q8 or Q9, P9 → process, P11 → earlier steps, P16, P17 → role, P13 → statute (**suffix-matched**, `:349`) | 495 |
| case | `courtlistener:cluster:{cluster_id}` | `:378` | P5 Q22, P15, P23, P13 → statutes, P22 | 117 |

Constraints a new kind must respect:

- **Label and description must be unique together.** The loader appends `[key-suffix]` on a clash (`:183-186`), and `owner()` reuses an item already carrying the same key (`:198-207`).
- **Strings are capped at 400 characters** (`_snak` `:126`). Full quotes do not fit, so link to DokuWiki or use the quote's start only.
- **`retire_drafts` parses keys** (`:216-221`) and only knows `process`, `role` and `step`. Any new model-scoped key (decision, input, term-use) must be added there, or its drafts are never retired.
- **Tests assert these key formats** (`tests/test_review_publish.py:225-234`, e.g. `lexflow:step:va.records:s1`). Keep the existing forms and add new kinds beside them.
- **Only `reviewed` and `agreed` models are loaded.** `single` models only relabel items an earlier version wrote (`:306-313`). The same rule must apply to links derived from a model.

---

## 4. Where each new link would be stored

The rule followed throughout: every new link carries a quote-anchored `Source`, the same discipline the IR uses (`ir.py:46-56`), so `lex_checks` (`validate.py:126-160`) can verify it.

### 4.1 Typed section → section references

| Layer | Proposal |
|---|---|
| Extraction | A new module, for example `lexflow/text/xref.py`, beside `text/citations.py` (do not edit `ask/retrieve.py` while the benchmark runs). Per state: number patterns from `_NUM` (`retrieve.py:77`) plus the `s.` / `ss.` / `subsection` / `chapter` / `of the X Law` forms, history lines stripped, and a **code-alias table** (`Corps. & Ass'ns` ↔ `Corporations and Associations`, `BSC` ↔ `Business Corporation Law`, `NPC` ↔ `Not-for-Profit Corporation Law`). Resolve through `I.lookup` with the qualifier code; otherwise use the same code (`_code`, `retrieve.py:83-88`). Emit `Citation`-like records with offsets, as in `text/citations.py:33-40`. |
| DB | A new table `section_links` in the main store, SYNCED-shaped (state, updated_at, origin; the contract is at `store/db.py:338-350`): `state, src_act_id, src_cite, src_subsection, start, end, quote, tgt_state, tgt_act_id, tgt_cite, tgt_kind (section/chapter/article/act/external), relation, method (regex/curated/model), confidence, dataset_version`. Do not key it by `sec.id`. It could also live in a sidecar per-state SQLite next to `data/index/statutes_<state>.sqlite`, rebuilt with the same stamp (`ask/index.py:77-90`). |
| Relation types | Distinguish `cites` (outgoing; 60 curated examples) from `annotates` (222 self-notes). Typed `cites` values seeded from the curated `role` vocabulary: `incorporates-requirement` ("must comply with s. 605.0112"), `procedure-as-provided-in`, `definition-from`, `exception-to` / `defeated-by`, `deadline-override` (Va. 2.2-3706.1 "60 work days instead of seven"), `fee-schedule`, `penalty` / `sanction`, `effective-date`, `review-by-court`. |
| IR | `LegalProcessModel.references: list[CrossRef]`, with `CrossRef(source: Source, target_citation, target_section, target_code, target_key, relation, note)`. Compile it from `facts.cross_references` (`compile.py:252-258` has no such field yet). |
| BPMN | `lex:reference` beside `lex:grounding` (`bpmn_xml.py:75-91`) on the node that quotes it, or under `lex:model` (`:187-197`). |
| Wikibase | `P13 references` (≡ wd:P2860), statute → statute, with qualifiers: `P22 citation` (the citing words) and a new item-valued **`reference type`** property (Wikidata uses the `P3831 object has role` pattern for this). Map special types to the existing properties: exception → `P21 defeated by`, penalty → `P20 sanction`, the provision a process follows → `P19 governed by norm`. |
| DokuWiki | "Cites" and "Cited by" lists on law pages (`dokuwiki.py:104-117` already has "Used by processes"); a cross-references section on model pages (`publish/lexipedia.py:129-181`). |

### 4.2 Defined terms and roles

Two levels. Without them, *incorporator* is either 8 unrelated strings or one blurred item.

| Entity | Key (P25) | Wikibase claims | Backing data |
|---|---|---|---|
| Concept, cross-jurisdiction | `lexflow:concept:role:incorporator` (also `concept:term:<slug>` for non-role terms such as *articles of incorporation*) | P5 → a new class "legal concept" (`P8` → wd:Q2135465 *legal term or legal concept*) or P6 → Q23 *legal role*; `P8 exact match` → a Wikidata item only when one exists (none for incorporator; Q7309406 for registered agent); `P14 based on` → an MBCA item (`P8` wd:Q6888224) where the uniform-act lineage is known | the shared curated actor ids (`requester` ×10, `organizer` ×9, `court` ×10, `llc` ×9, `custodian` ×3) and shared decision inputs |
| Term as defined in one jurisdiction | `lexflow:term:{state}:{act_id or ref}:{slug}`, e.g. `lexflow:term:fl:607.0201:incorporator` | P5 → concept (or a "defined term" class); P15 → state; `P13 references` → Q168 with `P22` qualifier = the defining words; `P9 part of` → the statute item | `"X" means …` clauses, or a section heading equal to the term |
| Role in one process (exists) | `lexflow:role:{state}:{question}:{actor}` | **add**: P5 → the concept (or a term item); `P19 governed by norm` / P13 → the statute item of `FActor.source.section`; `P8` → Wikidata for public bodies (the governments table already has QIDs) | `facts.actors[].source` (dropped today by compile) |

| Layer | Proposal |
|---|---|
| Facts schema | `FActor.term: Optional[str]` (a concept slug) and `FActor.defined_in: Optional[Quote]`. Add a new `FTerm(id, term, definition: Quote, scope)`, plus `LegalProcessFacts.terms`, at `extract/schema.py:24-28,97-106`. |
| IR | `Actor.concept: Optional[str]` and `Actor.sources: list[Source]` (`ir.py:142-148`, where `wikidata`, `govdirectory` and `description` already sit). Add `Term(id, term, concept, sources)` and `LegalProcessModel.terms`. `InputClause.term` lets a column such as `registered_agent` point at its term. |
| DB | `terms(state, term_key, term, concept_key, defining_act_id, defining_cite, subsection, quote, scope (section/chapter/title/code), kind (role/document/fee/act/thing), method, confidence, updated_at, origin)`, and `concepts(concept_key, label, kind, wikidata, description)`. Concepts carry no `state`, so they would need a non-state sync key, as `asked_questions` stays local today (`db.py:349`). |
| Compile | Carry `FActor.source` into `Actor.sources` (`compile.py:255`). |
| BPMN | `lex:actor` gains `concept=` and `term=` attributes (`bpmn_xml.py:194-197,205-207,231-233`). |
| DMN | `decisionMaker` / `decisionOwner` → the actor or role; `knowledgeSource@owner` → the role. |

### 4.3 Process ↔ process links

| Layer | Proposal |
|---|---|
| IR | `LegalProcessModel.links: list[ModelLink]`, with `ModelLink(id, kind, source_element, target_model_key, target_element, variable, sources)`. `kind` is one of: `calls` (generalises `called_element`), `output-feeds-input` (an outcome or DataRef of A → an input variable of B), `condition-of` (A's outcome is a flow condition in B: FL `local_tax_required`), `triggers` (A's end event starts B), `precondition` (an entity must exist: formation → local license). Targets use the Wikibase-style key `lexflow:process:{model_id}` plus a node or decision id, never a bare `called_element` string. A small `ProcessInterface` per model (declared inputs = the free condition variables and decision inputs; declared outputs = outcomes and decision outputs) makes the links checkable. |
| Validation | In `_integrity` (`ir.py:271-348`) add the local checks; a new cross-model checker resolves `target_model_key` against `process_models`. |
| DB | `model_links(from_model, from_element, kind, to_model, to_element, variable, quote_source JSON, method, updated_at, origin, state)`, SYNCED-shaped, with the primary key `(from_model, from_element, kind, to_model, to_element)`. |
| BPMN | `callActivity@calledElement` for `calls` (`bpmn_xml.py:312-313`); `lex:link` extension elements for the others (signal / message names could carry them for simulation). |
| Wikibase | Process or step → process via `P13` qualified by a link type, or via new item properties (`uses output of`, `precondition`). For `condition-of`, use the existing **`P18 condition`** with the value = the decision or outcome item that sets the variable. |

### 4.4 DMN decision requirements (DRD)

| Layer | Proposal |
|---|---|
| IR (`ir.py:167-206`) | `InputData(id, name, variable, type_ref, term?, sources)` on the model; `Decision.requires: list[str]` (decision or input-data ids, which become `informationRequirement`); `Decision.authorities: list[KnowledgeSourceRef]` (section keys with `Source`, which become `authorityRequirement` → `knowledgeSource`); `Decision.maker: Optional[str]` (actor id); `Decision.sources` filled from the rules' sections (empty today). |
| Derivation (deterministic, no LLM) | Condition named like an output → information requirement of the deciding task (55 curated cases). Input named like another decision's output → decision → decision (WA records `clarification_requested`). Remaining inputs and free conditions → `InputData` (72 free conditions). Each rule's `source.section` → a `knowledgeSource` with `locationURI` = `SectionText.url`. Every `cites` edge from a rule's section → a candidate knowledge source (FL `name_ok` "Name complies with § 605.0112"). |
| DMN XML | In `write_dmn` (`dmn_xml.py:53-62`), after `question` (`:60-61`) and before `decisionTable` (`:62`), write `informationRequirement` (`requiredDecision` / `requiredInput href="#id"`) and `authorityRequirement` (`requiredAuthority`), then `decisionMaker`, then `usingTask href` → the businessRuleTask. Add top-level `inputData` and `knowledgeSource` siblings. DMNDI (`:93-100`) needs shapes for them plus `DMNEdge`s. These elements belong in the `feel` dialect only until SpiffWorkflow (`write_dmn_split`, `:104-106`) is shown to accept them; it already rejects annotation columns (`:75`). |
| Shared vocabulary | Business-structure inputs are identical across 11 states, and `all_exempt` / `some_exempt` across 5 records models. Key them `lexflow:input:{question}:{name}` to make them addressable across jurisdictions. |
| Wikibase | Decision items `lexflow:decision:{model_id}:{decision_id}` (a new class "decision (DMN)", or Q9) with P9 → process, P13 / P19 → statutes (authorities), and P13 → input-data items. The step's `P18 condition` → the decision item. Rules stay on DokuWiki (the 400-character cap). |

---

## 5. Concrete extension points (`file:line`)

Data model

1. `lexflow/ir.py:46-56` `Source`: add `act_id` (today it is only inside `SectionText.retrieved_from`, `municipal/statutes.py:233`) so every quote resolves to a stable section key.
2. `lexflow/ir.py:142-148` `Actor`: `concept`, `sources`.
3. `lexflow/ir.py:167-206` `InputClause` / `Decision`: `term`, `requires`, `authorities`, `maker`; a new `InputData`.
4. `lexflow/ir.py:238-251` `LegalProcessModel`: `references`, `terms`, `links`, `inputs`.
5. `lexflow/ir.py:271-348` `_integrity`: check the new ids.
6. `lexflow/extract/schema.py:24-28,91-106`: `FActor.term`, `FTerm`, and a `FCrossRef.relation` enum next to the free `role`.

Compilation and build

7. `lexflow/extract/compile.py:237-244`: fill `Decision.sources`, derive requirements and input data. `:252-258`: carry cross-references, terms and actor sources.
8. `lexflow/municipal/build.py:150-185` `_fix_sources`: the quote-containment resolver to reuse for P13 linking and xref sources. `:188-193` `_compile`: sets the IR id `{state}-{question}`, which differs from the DB id at `:34-35`. `:213-241`: the curated path, where links would be built and stored next to the `process_models` row.
9. `lexflow/municipal/quality.py:35-40`: DMN generation and XSD checks; add DRD checks.
10. `lexflow/validate.py:126-160` `lex_checks`: verify the quotes on new links and terms.

XML

11. `lexflow/dmn_xml.py:53-62` (requirement slots), `:93-100` (DMNDI edges).
12. `lexflow/bpmn_xml.py:75-91` (`_lex_sources`; a sibling `lex:reference`), `:186-197` (`lex:model` / `lex:actor`), `:312-313` (`calledElement`), `:327-344` (decision binding).

Cross-references

13. `lexflow/ask/retrieve.py:77-109`: **read only for now** (benchmark). Port `_NUM`, `_code` and `cited` into a new module; extend the patterns for `s.` / `ss.`, qualified codes and history stripping.
14. `lexflow/text/citations.py:15-92`: the typed-citation precedent; generalise its `Citation` dataclass.
15. `lexflow/ask/index.py:327-350` `lookup` and `:353-362` `by_id`: the resolvers to call; `:194,216`: `act_id` is in `sec`.
16. `lexflow/municipal/statutes.py:150-174` `find` / `_norm_cite` / `ref_of`: normalisation to extend with code aliases (do not edit `statutes.py` while the benchmark runs).

Store

17. `lexflow/store/db.py:19-336` `SCHEMA` (new tables), `:338-350` `SYNCED`, `:353` `MIGRATIONS`.

Publishing

18. `lexflow/publish/wikibase_lexipedia.py`:
    - `:29-37` `PROPS` / `CLASSES`: add P14, P18, P19, P20, P21 and new classes ("legal concept", "defined term", "decision (DMN)", "input data").
    - `:301-368` `processes()`: role → concept and statute links at `:329-335`; replace the suffix match at `:348-351`; decision and input items after `:359`.
    - `:261-299`: add a canonical statute key.
    - `:209-232` `retire_drafts`: add the new key kinds.
    - `:392-413` `run`: a new `loader.terms()` and `loader.links()` phase after `statutes()`.
19. `lexflow/publish/wikibase.py:36-45` `PROPOSED`: replace with the properties actually to be created (reference type, uses output of, precondition), or retire this QS path in favour of the loader. Its keys (`:84-118`) conflict with the live scheme.
20. `lexflow/publish/lexipedia.py:129-181` `render_state_model`: render cross-references, terms and DRD; `lexflow/publish/dokuwiki.py:104-117`: "Cites" / "Cited by" on law pages; `:41-42` `law_page_id`: needs the code in the id for multi-code states.

Small classifiers

21. `lexflow/extract/selector.py:626` `_fit_lr`, the NaiveBayes / kNN / stack pipeline (module docstring `:1-20`), and `lexflow/ask/relevance.py:30-90` (features, `fit`, `score`): the in-repo pattern for a small classifier (see §6).

Pipeline

22. `lexflow/pipeline/steps.py:389-400,542-546`: the `wikibase` job step; a links/terms build step would sit beside it, with `needs=["build"]`.

---

## 6. A small model for small classifications ("jev model")

The request suggested "a jev model to classify small stuff". The term is not defined anywhere in the repo, so this section reads it as: a small, cheap local classifier that needs no chat model.

The repo already has that pattern, and the label sources for it:

- **Pattern.** Logistic regression over hand features and cached `nomic-embed-text` vectors (`extract/selector.py`: NaiveBayes + embedding kNN + stacked LR, held out one state at a time; `ask/relevance.py`: LR with leave-one-question-out).
- **Labels already in hand:**
  - 282 curated cross-references with a free-text `role`: map them to the relation enum once, then train.
  - 88 curated actors with `kind` and a source quote: role vs not-role, and concept alignment through shared ids.
  - 758 clause labels in `curated_labels/*/*.json` (`is_step`, `actor_kind`, `why`) for 24 state/question pairs.
  - 11 business decision tables with identical input names.

Tasks where a small classifier pays off, after deterministic regex and quote anchoring have found the candidates:

1. **Cross-reference relation type** for a resolved `cites` edge: incorporates-requirement / procedure / definition / exception / deadline-override / fee / penalty. Features: the cue words around the citation ("must comply with", "as provided in", "except as", "instead of", "$"), target heading words, and an embedding of the citing sentence.
2. **Defined-term kind**: role (party or office) vs document vs fee vs act vs thing. This decides whether a term item also becomes a `legal role`.
3. **Role → concept alignment across states**: is FL "Authorized representative (founder)" the same concept as VA "organizer"? Use embedding similarity of name plus defining quote, with shared curated ids as positives.
4. **Wikidata candidate acceptance** for a concept: from `wbsearchentities` hits (rate-limited reads), accept only when the description matches the legal sense. Incorporator shows why: the only exact-label hit is a PropBank prototype.

Budget, given the rules for this container: embeddings for a few hundred short strings at most, no chat models, all reads cached.

---

## 7. Pitfalls to design around

- **The benchmark freeze.** Do not edit `lexflow/ask/`, `lexflow/extract/`, `municipal/statutes.py`, existing tests, `curated*/` or `docs/askbench.json` while AskBench runs. Put new code in new modules (`lexflow/links/…`, `lexflow/text/xref.py`) and new test files.
- **Two model-id spellings** (`fl.business` vs `fl-business`) and **two Wikibase key schemes** (`lexflow:statute:` live vs `provision:` in the QS path). Pick the live scheme and the DB id for every new key.
- **Short section numbers are ambiguous** within a state (`SectionText.section`, `Quote.section`, DokuWiki `law_page_id`). Resolve by quote containment or `act_id`, never by suffix.
- **Index ids (`sec.id`) are not stable**, and `ref` can change form. Persist `act_id` and `norm_cite`.
- **Florida `s. N` citations and Laws-of-Florida history lines** (`s. 2`, `s. 16`) look alike. Strip the history first.
- **Wikibase limits.** Unique label+description, 400-character strings, statements replaced wholesale on update (`clear`). Every new claim must be produced by the loader on every run, or it disappears on the next `clear`.
- **`wikibase_items` is local** (not synced). A second machine would duplicate items unless it adopts them by key (`owner()`, `wikibase_lexipedia.py:198-207`).
- **Only reviewed and agreed models publish.** Links derived from `single` models stay drafts, by the publishing rule in memory and `wikibase_lexipedia.py:306-313`.

---

## 8. Open questions

1. Is open-us-law's `act_id` stable across releases (v2026.09.1 → next)? Check this before using it as the canonical key. If it is not, use `(state, norm_cite, effective_from)`.
2. Concept items: should a concept be a **class** (role items `P5` → concept, concept `P6` → Q23) or an **instance** linked by a new property? The class form matches how Q13–Q20 are modelled.
3. Should new properties be created on the wiki (`reference type`, `uses output of`, `precondition`), or should everything be expressed with P13/P18/P19/P21 plus qualifiers? Creating properties is a write and needs the user's go-ahead.
4. Should uniform-act lineage (MBCA § 2.01 → FL 607.0201, VA 13.1-618, NC 55-2-01, DC 29-302.01) be recorded as `P14 based on` → an MBCA item, or as a statute → statute `equivalent provision` link?
5. Which SpiffWorkflow version, if any, accepts DRD elements in the Python dialect? Until that is checked, emit them in the FEEL dialect only.
6. What exactly is a "jev model"? This map assumes a small local classifier (§6).
