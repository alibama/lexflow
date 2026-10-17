# Legal ontologies: what lexflow adopts, the mapping, and a nationwide section tagger

_16 October 2026. A review of the ontologies listed by the Liquid Legal Institute's
[Legal-Ontologies](https://github.com/Liquid-Legal-Institute/Legal-Ontologies) collection (its README of 15 October
2026 and the sources it links), the mapping that follows from it (`lexflow/publish/ontology_map.py`), and the
design, prototype and measurement of `lexflow run ontology` (`lexflow/law/ontology.py`), which tags every section of
a state index with its Akoma Ntoso structure, its LKIF norm types and an ELI-style identifier. Companion to
[wikibase-schema.md](wikibase-schema.md) (the classes and properties the mapping attaches to) and
[authority-escalation.md](authority-escalation.md) §1.2 (the organisation-side mapping to W3C ORG, Popolo,
schema.org and Wikidata, which this note keeps). Every licence and class name below was read from the ontology's
own source file, not a summary page; §1.1 says which file._

## 0. The answer

1. **Adopt five ontologies as mappings** (written as `P7 equivalent property` on properties and `P8 exact match`
   or `close match` on classes, nothing else changes on the wiki): **ELI** for codes, units, sections, versions,
   citations, official text and in-force dates; **LKIF-Core** for norms, roles, bodies and powers; **schema.org
   Legislation / GovernmentOrganization** for the public-facing side; **PROV-O** for the reference qualifiers
   (quoted text, source section, source URL, retrieved, determination method); **SKOS / OntoLex** for the terms
   plan's concepts and matches, with **W3C ORG** and **DCMI terms** for the two properties they fit best
   (`position in`, `replaced by`). 87 IRIs, every one re-resolved read-only on 16 October 2026
   (`python -m lexflow.publish.ontology_map`: 87 of 87).
2. **Adopt Akoma Ntoso as a tagging vocabulary only.** It is XML, not RDF: there is nothing to `P8` to, but its
   hierarchy element names (`title`, `chapter`, `article`, `section` ...) are the right names for the structure
   tag, and USLM (the US Code's schema, CC0) uses the same ones. LegalRuleML stays what it already is (the deontic
   classes Q11–Q20); it publishes no RDF IRIs, so `sanction` and `bearer` get no `P7`.
3. **Skip** FIBO (one class, `CourtOfLaw`, is taken; the rest is finance), ELI-DL (EU legislative procedure),
   UNDO (UN document types), DALICC (licences of data, not law), ALLOT (its w3id IRIs no longer resolve), the Lynx
   LKG, SALI LMSS (legal-services taxonomy), the UK Parliament ontologies, Common Core, DOLCE, and the US
   candidates (LII and OLRC publish schemas and identifiers, not ontologies; USLM's element names are taken
   through Akoma Ntoso). Reasons in §1.1.
4. **The tagger is go for rules, no-go for a nationwide model pass.** Structure and ELI identifiers come from the
   path and act_id alone (rules, 99.4% on unit levels in decision-models.md §3.1, no model). Norm types by cue
   phrases plus `lexflow.law.terms.definitions` cost about 4 ms a section; the decision model's seven `noul`
   questions cost 12 s a section on this CPU (the endpoint encodes the state once per question) and, measured on
   150 sections (§4), add nothing the rules miss on the labelled types
   while its probabilities are not calibrated at 0.5. Running the rules over the 1,676,357 sections of the 47
   indexed states takes about an hour here (§5); the model over the same would take 118–237 days on this CPU
   and 10–16 days on a 16 GB GPU node, for a gain the measurement does not support. The step therefore runs
   rules by default and the model only when asked (`model: decision|chat`, `budget` calls per run), so a reviewer
   can request a model pass over one chapter, never over a state.

## 1. The review

### 1.1 Ontologies that could matter to lexflow

Kinds are lexflow's (wikibase-schema.md §2–4): **code/unit/section/version**, **role/body/post**,
**process/step/deadline**, **term/concept**, **reference/citation**, **provenance**. "Source" is the file the
licence and the names were read from. Verdicts: *P7/P8* = adopt as `equivalent property` / `exact match` (or
`close match`) mapping; *vocabulary* = adopt as a tagging vocabulary (names, no IRIs written); *skip*.

| Ontology | Models | Licence (source) | Maturity | lexflow kinds | Classes / properties to map | Verdict |
|---|---|---|---|---|---|---|
| **ELI** (European Legislation Identifier ontology, v1.5) | Legislation as FRBR work / expression / manifestation: `LegalResource`, `LegalResourceSubdivision`, `LegalExpression`, `Format`, with in-force dates, citations, versions, jurisdictions and the URI template | No licence statement in the OWL (`http://data.europa.eu/eli/ontology`, RDF/XML, `owl:versionInfo` 1.5); published by the Publications Office under the EU reuse policy (Commission Decision 2011/833/EU); the dataset page is script-rendered and could not be read, so verify before redistributing the file itself. Mapping to its IRIs needs no licence | Mature: EU, FR, IT, LU, IE, PT, NO and others use it; 2012 Council conclusions; v1.5 | code/unit/section/version; reference/citation | `eli:LegalResource` (code), `eli:LegalResourceSubdivision` (unit, section), `eli:SubdivisionType` (unit level), `eli:AdministrativeArea` (jurisdiction); `eli:is_part_of`, `eli:has_part`, `eli:cites`, `eli:based_on`, `eli:jurisdiction`, `eli:id_local`, `eli:number`, `eli:title`, `eli:type_subdivision`, `eli:first_date_entry_in_force`, `eli:date_no_longer_in_force`, `eli:changed_by`, `eli:is_about` | **P7/P8**, and the identifier template of §3.3 |
| **ELI-DL** (draft legislation) | Legislative procedure: `eli-dl:LegislativeProcess`, `Activity`, `Vote`, `Decision`, `ProcessStage`, `DraftLegislationWork` | Same publisher, same position as ELI (`http://data.europa.eu/eli/eli-draft-legislation-ontology`, Turtle) | Mature for EU institutions | none: it models how a bill becomes law, not how a citizen uses one; lexflow's processes are administrative, not legislative | – | **skip** (wrong process) |
| **Akoma Ntoso 1.0** (OASIS LegalDocML) | XML for legal documents: hierarchy elements `title part chapter subchapter article section subsection paragraph division subtitle book tome clause rule ...` (`type="hierarchy"` in `akomantoso30.xsd`), FRBR metadata (`FRBRWork/Expression/Manifestation`), `ref`, `quotedText`, `def`, `term`, `lifecycle` | OASIS **RF on Limited Terms** mode (the spec's Status section, part 1 vocabulary HTML); the schema is freely implementable | OASIS Standard 2018; used by the EU (AKN4EU), UN (AKN4UN), several parliaments | code/unit/section (structure names); reference/citation (`ref`, `quotedText`) | the hierarchy element names, as the `structure` tag's vocabulary (`ontology_map.STRUCTURE_MATCH`) | **vocabulary** (XML: no IRIs to match; `hcontainer` noted as `close match` of *statutory unit* via the XSD URL) |
| **USLM** (OLRC / GPO United States Legislative Markup, `USLM.xsd`) | The US Code's XML: the same hierarchy names (`title subtitle chapter subchapter part division article section subsection paragraph`), `ref`, `def`, `term`, `quotedContent`, `sourceCredit` | **CC0 / public domain** (`LICENSE.md`: 17 U.S.C. 105 plus CC0 1.0) | Production: uscode.house.gov, govinfo | code/unit/section | the element names, recorded beside AKN's in `STRUCTURE_MATCH` (`uslm`) | **vocabulary** (through AKN's names; USLM is federal and XML) |
| **LKIF-Core** (ESTRELLA, Hoekstra et al.) | 15 OWL modules: `norm.owl` (`Norm`, `Obligation`, `Permission`, `Prohibition`, `Right`, `Hohfeldian_Power`, `Enabling_Power`, `Action_Power`, `Definitional_Expression`, `Code`, `Statute`, `Regulation`, `Legal_Document`, `Legal_Source`), `legal-action.owl` (`Public_Body`, `Legislative_Body`, `Decision`, `Mandate`, `Delegation`, `Natural_Person`, `Legal_Person`), `legal-role.owl` (`Legal_Role`), `role.owl` (`Role`, `played_by`, `plays`), `action.owl` (`Action`, `Agent`, `Organisation`), `process.owl` (`Process`), `expression.owl` (`Document`, `Qualification`) | **CC BY 4.0** (`LICENSE` in github.com/RinkeHoekstra/lkif-core) | Stable since 2008, unchanged; the estrellaproject.org IRIs no longer dereference (the host answers with its home page), the GitHub files are the source | role/body/post; norms and powers; term (`Definitional_Expression`) | as listed; the norm types of the tagger (`NORM_TYPE_MATCH`) | **P7/P8** (`played_by` as `P7` of *played by*; the classes above as `P8`/`close match`) |
| **LegalRuleML 1.0** (OASIS) | Rules with deontic operators, bearers, penalties, temporal scope: `PrescriptiveStatement`, `ConstitutiveStatement`, `PenaltyStatement`, `Obligation`, `Permission`, `Prohibition`, `Right`, `Bearer` | OASIS **RF on Limited Terms** (the spec's Status section) | OASIS Standard 2021; already the source of Q11–Q20 and P16–P21 | norms; `sanction`, `bearer` | nothing new to write: the `ns/v1.0/` namespace URLs (`metamodel`, `rule`, `vocab`) all answer 404 (checked 15 October 2026), so there is no IRI for `PenaltyStatement` or `Bearer` | **already used**; no `P7` possible for `sanction`/`bearer` until OASIS publishes IRIs |
| **FIBO** (EDM Council) FND/Law | Finance ontology; `LegalCore.rdf` has `Law`, `StatuteLaw`, `Constitution`, `CourtOfLaw`, `hasInForce`, `isInForceIn`; jurisdictions are in `BE/GovernmentEntities/*` | **MIT** (`LICENSE`) | Mature, quarterly releases | body (`CourtOfLaw`) | `fibo-fnd-law-cor:CourtOfLaw` as `P8` of *court*; nothing else fits | **P8 for one class, otherwise skip** (finance) |
| **schema.org** Legislation, GovernmentOrganization, GovernmentService | `Legislation`, `LegislationObject`, `LegalForceStatus` (`InForce`, `NotInForce`, `PartiallyInForce`), `legislationIdentifier`, `legislationJurisdiction`, `legislationDateOfApplicability`, `legislationPassedBy`, `legislationChanges`, ...; `GovernmentOrganization`, `GovernmentOffice`, `GovernmentService`, `AdministrativeArea`; the ELI team contributed the Legislation terms (`schema:contributor` ELI, `skos:closeMatch eli:id_local`) | **CC BY-SA 3.0** (`docs/terms.html`) | Mature; read by search engines | code/section; role/body; reference/citation; process (`GovernmentService`, close) | `Legislation` (code; close for section), `GovernmentOrganization` (government, agency), `AdministrativeArea` (jurisdiction), `GovernmentService` (close for process); `legislationIdentifier`, `legislationJurisdiction`, `legislationDateOfApplicability`, `isPartOf`, `hasPart`, `name`, `url`, `email`, `telephone`, `address`, `about`, `audience`, `result`, `archivedAt`, `lastReviewed`, `identifier` | **P7/P8** |
| **SKOS** | `Concept`, `ConceptScheme`, `exactMatch`, `closeMatch`, `broadMatch`, `narrowMatch`, `relatedMatch`, `definition` | W3C Document Licence (skos-reference, `skos.rdf`) | W3C Recommendation 2009 | term/concept; the match properties | `exactMatch` → P8, the four matches → property 60, `Concept` → *concept* | **P7/P8** (already implied by P8's name; now explicit) |
| **OntoLex-Lemon** | `LexicalEntry`, `LexicalSense`, `LexicalConcept`, `Form`, `evokes`, `denotes`, `reference`, `sense` | **CC0** (`cc:license` in the ontology file) | W3C Community Group final report 2016 | term/concept | `evokes` as `P7` of *concept* (term → concept); `LexicalEntry`, `LexicalConcept` as `close match` | **P7/P8** for the terms plan |
| **FRBR** (vocab.org core; FRBRoo in ELI) | Work / Expression / Manifestation / Item | CC BY 2.0 UK (`core.rdf`); FRBRoo via CIDOC | FRBR is library practice; ELI already subclasses FRBRoo (`eli:LegalResource` ⊂ `frbroo:F1_Work`) | version | taken through ELI (`LegalResource` = work, `LegalExpression` = version, the `en@date` expression IRI of §3.3) | **through ELI**, not directly |
| **PROV-O** | `Entity`, `Activity`, `Agent`, `SoftwareAgent`, `wasQuotedFrom`, `wasDerivedFrom`, `hadPrimarySource`, `wasAttributedTo`, `generatedAtTime`, `value`, `Quotation` | W3C Document Licence (`prov-o`) | W3C Recommendation 2013 | provenance (the reference on every grounded claim, wikibase-schema.md §4.6) | `wasQuotedFrom` (source section), `hadPrimarySource` (source URL), `value` (quoted text), `generatedAtTime` (retrieved), `wasAttributedTo` (determination method) | **P7** |
| **DCMI Terms** | `isReplacedBy`, `license`, `rights` (ELI's `licence`/`rights` are declared specific sub-properties of them) | CC BY 4.0 (DCMI) | Stable | version | `dcterms:isReplacedBy` as `P7` of *replaced by* | **P7** for one property |
| **W3C ORG** | `FormalOrganization`, `OrganizationalUnit`, `Post`, `Role`, `postIn`, `subOrganizationOf` | W3C Document Licence | W3C Recommendation 2014; already chosen in authority-escalation.md §1.2 | role/body/post | `Post` (position), `OrganizationalUnit`, `FormalOrganization`, `postIn` (position in) | **P7/P8** (as §1.2 already said) |
| **UNDO** (UN System Document Ontology) | UN document types (`Resolution`, `Decision`, `Convention`, `Judgment` ...) and AKN4UN | CC BY 4.0 (`dc:rights` in `undo.ttl`, github.com/essepuntato/undo); the w3id IRI redirects to HTML documentation only | 2017; one organisation's corpus | none | – | **skip** (UN documents) |
| **DALICC** (licence library) | Licences as ODRL policies, compatibility reasoning | licence data CC BY 4.0, code AGPL-3.0 (README `## Licensing`) | Maintained | none for law; it could describe the licences of lexflow's *sources* (the credits page), which is a different job | – | **skip** here; note for the credits page |
| **ALLOT** (AKN ontology of referenced entities) | `Person`, `Organization`, `Role`, `Concept`, `Event`, `Process`, `Term`, `Reference`, `FRBRWork/Expression/Manifestation/Item` (the TLC classes of AKN) | no licence statement found in `allot.ttl`; the `https://w3id.org/akn/ontology/allot/` IRIs answer 404 (checked 15 October 2026) | 2017; unmaintained | role/term (would have been the AKN-side names) | – | **skip** (IRIs dead, licence unknown) |
| **Lynx LKG** | Compliance documents: `Legislation`, `CaseLaw`, `Standard`, `LynxDocument`, `hasEli`, `annotation` | page says "License:" with no value; reuses ELI | EU project 2018–2021 | none beyond ELI | – | **skip** (ELI covers it) |
| **SALI LMSS** | Legal-services taxonomy (matter types, areas of law, players) | MIT (`LICENSE`) | Industry standard, active | topic vocabulary, loosely | – | **skip** for now (a `topic` crosswalk could come later; nothing structural) |
| **UK Parliament ontologies** | Procedure, legislation, laying, formal bodies | not fetched (the repository paths moved; nothing verified) | Active, UK-specific | process (a parliamentary one) | – | **skip** (unverified, UK procedure) |
| **Common Core Ontologies, DOLCE** | Upper ontologies | BSD-3 / CC BY | Mature | none directly | – | **skip** (nothing legal to map) |
| **LII / Cornell** | Publishes the US Code and CFR with citation microformats and a "definitions" service; no published ontology | – | – | – | – | **skip** (not an ontology; its citation forms are already what `xref` parses) |
| **OLRC** | See USLM above | CC0 | – | – | – | **through USLM** |

### 1.2 Why these five, and why nothing replaces LegalRuleML

ELI is the only one of the set that models exactly what wikibase-schema.md §4.1 writes: a code (work) made of
subdivisions with types, each with an identifier, a title, in-force dates and citations, in a form a European
legal-data consumer already understands. Its `type_subdivision` is lexflow's `unit level`; its
`first_date_entry_in_force` / `date_no_longer_in_force` are `effective date` / `effective until`; its
`LegalExpression` is the versioned section. schema.org's Legislation terms were written with the ELI team, so the
two mappings agree. LKIF-Core is the only published OWL with `Obligation`, `Permission`, `Prohibition`,
`Definitional_Expression` and `Hohfeldian_Power` side by side with `Public_Body`, `Legal_Role` and `played_by`,
which is what the tagger and the organisation side both need; LegalRuleML has the deontic operators but no RDF
IRIs, so it stays the vocabulary of the existing classes and LKIF carries the matches. PROV-O is the standard
for "where did this claim come from", which is what the reference qualifiers of §4.6 are.

## 2. The mapping (`lexflow/publish/ontology_map.py`)

Four tables and three helpers, all data, nothing reads the network except the checker:

* `PROPERTY_EQUIV: dict[label, list[IRI]]`: 43 of the 85 property labels (`schema.ALL_PROPERTY_LABELS`) get one
  to two IRIs. `PROPERTY_RELATED` lists the kin that are *not* equivalents and why (inverse direction, wrong
  domain, an id string rather than an IRI) so nobody re-adds them.
* `CLASS_MATCH: dict[slug, list[IRI]]`: 20 of the 45 class slugs get `P8 exact match` IRIs; `CLASS_CLOSE` gives
  18 slugs their `close match` (property 60). A vocabulary class (`topic`, `audience`) is a `skos:ConceptScheme`
  (close), its items are the concepts.
* `NORM_TYPE_MATCH`: the seven norm types of §3.2 → LKIF classes (`penalty` and `procedure` have none; the table
  says so rather than inventing one).
* `STRUCTURE_MATCH`: each `unit-level` slug (plus `book`, `rule`) → its Akoma Ntoso element, ELI class and USLM
  element.
* `eli_uri`, `eli_unit_uri`, `eli_code`: the identifiers of §3.3.
* `resolve_all(iris, cache)`: one GET per *document* (not per IRI), a second apart, user agent
  `lexflow-research/0.1`, a JSON cache (30 days) under `data/cache/ontology_iris.json`; for a hash IRI it checks the
  local name occurs in the document, and for LKIF it reads the GitHub file since the estrellaproject.org IRIs no
  longer serve the OWL (`DOCUMENTS`). `python -m lexflow.publish.ontology_map` prints the report;
  `tests/test_ontology.py::test_every_iri_resolves_live` runs it with `LEXFLOW_NET=1` (the rest of the tests stub
  the fetch).

**The hook for `schema.py`** (another change owns that file; this is what it needs): `Prop` gains
`equivalents: tuple[str, ...] = ()` and `Cls` gains `exact: tuple[str, ...] = ()` and `close: tuple[str, ...] = ()`;
after `PROPERTIES` and `CLASSES` are built,

```python
from . import ontology_map as OM
PROPERTIES[:] = [replace(p, equivalents=tuple(OM.PROPERTY_EQUIV.get(p.label, ()))) for p in PROPERTIES]
CLASSES[:] = [replace(c, exact=tuple(OM.CLASS_MATCH.get(c.slug, ())), close=tuple(OM.CLASS_CLOSE.get(c.slug, ())))
              for c in CLASSES]
```

and `qs.py` writes, on a property, one `P7` line per equivalent beside the Wikidata one (`P7` is a url
datatype on this wiki, `EXISTING_DATATYPES`); on a class item one `P8` per exact match beside
`WIKIDATA_ENTITY + qid`, and one `close match` (property 60) per close IRI. The 21 `EXISTING` properties get their
`P7` lines through `05-updates.qs`. `rdf.py` emits the same as `owl:equivalentProperty` / `skos:exactMatch` /
`skos:closeMatch` triples so the local store can be joined with any of the five ontologies. Nothing in the
mapping touches item labels, keys or the privacy rules.

## 3. The tagger: `lexflow run ontology --states ...`

### 3.1 The step

`Step("ontology", ...)` in `lexflow/pipeline/steps.py`, optional, `needs=["index"]`, `params` states / force /
no_llm, in the jobs runner's `EXCLUSIVE` group (it may use Ollama). `run_ontology` takes the usual `args`:
`states` (default every state with an index), `force` (retag), `model` (`decision` or `chat`; unset = rules only),
`budget` (model calls per run, default 200), `pace` (seconds between model calls), `limit` (sections per state,
for a trial). It logs through the job's `log`, reports `progress` per batch of 500 rows, marks a `scans` row
(`source='ontology'`) per state, and **resumes**: a section already tagged by the same `method` is skipped, so a
run that stops (or a budget that runs out) continues next time where it left off; a run with a new method retags.
`lexflow/law/ontology.py` holds the rules, the questions, the table and `run_state`.

### 3.2 What a row holds

```
section_tags(state, ref, act_id, structure, norm_types JSON, method, model, confidence JSON, updated_at, origin)
PRIMARY KEY (state, ref)      -- one row per ref; where a ref has versions, the one the index lists first (in force)
```

* **structure** (rules, no model): the chain of levels from the code to the section's own element, in the
  `unit-level` vocabulary plus `book` and `rule`, joined by `/`: `title/subtitle/part/chapter/section` (Virginia),
  `code/division/chapter/section` (California), `chapter/act/section` (Illinois), `code/article` (Louisiana's
  codes), `act/article` and `book/article` (Puerto Rico), `article/title/subtitle/section` (Maryland). The last
  token is the section's Akoma Ntoso element (`section`, or `article` where the code's unit is the article);
  `STRUCTURE_MATCH` turns every token into its `akn:`, `eli:` and USLM name. The levels come from
  `schema.unit_level` (the path's word, else the act_id's letter), which decision-models.md §3.1 measured at
  99.4% against 157 labelled units. There is nothing for a model to do here.
* **norm_types** (`ontology_map.NORM_TYPES`): the subset of `definition, obligation, permission, prohibition,
  power, penalty, procedure` the section carries. `method` says how: `rules` (cue phrases on the whole text,
  with `lexflow.law.terms.definitions` for *definition*), `rules+decision` (the decision model's seven `noul`
  questions on the citation + heading + first 1,500 characters, one call, through `decide.Decider`'s cache) or
  `rules+chat` (the same questions through the chat fallback). The final list is the rules' types plus the
  model's at or over `THRESHOLD[type]`; `confidence` keeps both sides (`{"rules": {...}, "model": {...}, "ms",
  "eli"}`) so thresholds can change without a re-run. The cue phrases are deliberately conservative ("shall"
  that is not "shall not", "shall mean", "shall be unlawful" or "shall apply"; "may" that is not "may not" or
  "may be fined"; "is authorized to", "has the power to", "may adopt rules" for *power*; "guilty of a
  misdemeanor", "punishable", "civil penalty", "fine of not more than" for *penalty*; "within N days", "shall
  file", "upon receipt of", "hold a hearing" for *procedure*).
* **ELI identifier** (rules): `confidence.eli` holds `eli_uri(state, act_id)` (§3.3); it is a pure function of
  `act_id`, which the row keeps, so it needs no column of its own.
* **Local, not `SYNCED`** (`db.LOCAL_KEYS`). The table is derived (every value comes from the index or from a
  cached model call), it is large (1.68 million rows for the 47 indexed states, against the ten shared tables'
  thousands), and it is tied to this copy's index files and version. Pushing it through Turso would be most of the
  shared database for data any copy can rebuild in two hours. `updated_at` and `origin` are kept so it can be
  promoted (add it to `SYNCED`, run `turso.ensure_schema`) if a shared copy is ever wanted, for instance for
  the model-tagged rows only.

### 3.3 ELI-style identifiers per state

ELI's pattern is `/eli/{jurisdiction}/{type}/{year}/{natural number}/{language}/{version}`, each publisher fixing
its own template (`eli:uri_schema`). lexflow's, from the act_id, is:

| What | Template | Example |
|---|---|---|
| code | `{base}/us-{st}/{code}` | `https://lexipedia.wikibase.cloud/eli/us-va/code`, `.../us-ca/gov` |
| unit | `{base}/us-{st}/{code}/unit/{unit slug}` | `.../us-va/code/unit/t2.2-sii-pb-c37` (`schema.unit_slug`) |
| section (work) | `{base}/us-{st}/{code}/{section}` | `.../us-va/code/2.2-3704` |
| version (expression) | `{work}/en@{effective_from}` | `.../us-va/code/2.2-3704/en@2026-07-01` |

`{code}` (`ontology_map.eli_code`) is the word `code` for a single-code state (VA, FL, DC, UT, MN, MI, OK, NC ...)
and the act_id's code token where a state has several codes, since section numbers repeat across them: California
`Cbpc` → `bpc`, `Cgov` → `gov`; Texas `Cag` → `ag`; New York `AABC` → `abc`, `APBO` → `pbo`; Maryland `Agab` →
`gab`; Louisiana `Cchildrens-code` → `childrens-code`; Puerto Rico `AMBIENTAL` → `ambiental`, `CIVIL` → `civil`;
Illinois `C105_A5` → `105-5` (chapter and act, because act numbers repeat across chapters). `{section}` is the
act_id's last token without its level letter (`S2.2-3704` → `2.2-3704`, Utah `S10_15_4` → `10_15_4`, Puerto Rico
`ART15` → `15`), which is the same string as the index's `section_number` for every state checked and is stable
across index rebuilds. `{base}` is the wiki's host; nothing serves `/eli/` yet: the operator's step is a
redirect rule (or a `Special:` resolver) from `/eli/us-{st}/...` to the item whose `act identifier` matches,
which the §5 packet does not need. The template is written on the code item as `eli:uri_schema` once that
property exists; until then it is this table.

### 3.4 Tests

`tests/test_ontology.py` (38 tests): the structure rules on twelve path shapes, the ELI identifiers for ten
states and their stability across codes, the cue phrases per type and their exclusions, the model state window,
`tag_row` with a stubbed `Decider` (merge over threshold, a failing model, the chat fallback's method name), the
table round trip and upsert, `run_state`'s resume and budget, the step's registration, the mapping keys against
`schema.py`'s labels and slugs, `document_of` / `_found`, `resolve_all` with a stubbed fetch and its cache, and
the live resolution of every IRI behind `LEXFLOW_NET=1`.

## 4. Measurement

`python -m scripts.ontology_eval --max 150 --budget 180 --chat 30`, 16 October 2026, in the app container (8 CPU
threads, no GPU) while a Wikibase push was running in the same container, so the model timings are contended;
the decision model served by `lexflow-ollama2` (Ollama 0.40.4, `tev1:0.8b`; the main `ollama` host answers
`/v1/systemone` with `unsupported decision encoding "pplx-decider"`, so `LEXFLOW_DECIDE_URL` must name the second
host), the chat fallback `qwen3:1.7b`. 181 model calls in all (150 decision, 30 chat, one single-question probe).

**Sample.** 150 sections: the 82 gold sections of `fixtures/xref/gold_{a,b,c}.json` (10 states) and 68 of the 85
sections the 22 reviewed models' steps quote (resolved in the state index by the model's citation prefix). Median
356 words. Labels: the facts' step modalities for the 68 model sections (obligation 59, permission 24 counting
`right`, prohibition 1: a partial label, so recall is the honest number and precision is against what the facts
name); `lexflow.law.terms.definitions` for *definition* on all 150 (70 define a term); the gold's `penalty`
reference role on the 82 gold sections (8), which says the section cites a penalty provision and is a weak
label. *power* and *procedure* have no label in either set; only agreement is reported for them.

**Arms.** Rules = the cue phrases on the whole text (the eval runs `rule_types` without `row`, so *definition* is
the cue phrase alone; in the step the definition type is `terms.definitions`, the label itself). Decision = the
seven `noul` questions, head + 1,500 characters, one call. Chat = the same through the fallback, first 30.

| type | n / positives | rules P / R | decision @0.5 P / R | decision @best threshold P / R (thr) | union rules + model@best | chat @0.5 (n=30) |
|---|---|---|---|---|---|---|
| definition (cue phrase vs `terms`) | 150 / 70 | 92 / 34 | 93 / 19 | 47 / 87 (0.05) | 48 / 89 | 100 / 20 |
| obligation (facts) | 68 / 59 | 90 / 97 | 89 / 92 | 87 / 100 (0.05) | 87 / 100 | – |
| permission (facts) | 68 / 24 | 46 / 88 | 56 / 62 | 60 / 75 (0.45) | 42 / 88 | – |
| prohibition (facts) | 68 / 1 | 3 / 100 | 11 / 100 | 100 / 100 (0.95) | 3 / 100 | – |
| penalty (gold role, weak) | 82 / 8 | 38 / 38 | 60 / 38 | 70 / 88 (0.10) | 50 / 88 | 67 / 80 |
| power | 150 / – | – | – | – | – | – |
| procedure | 150 / – | – | – | – | – | – |

Agreement of rules and model at 0.5 on all 150 (rules yes / model yes): definition 89% (26 / 14), obligation 89%
(132 / 131), permission 63% (108 / 70), prohibition 57% (67 / 29), power 80% (30 / 12), penalty 93% (13 / 6),
procedure 67% (51 / 46).

**Timing.** Rules 0.7 ms a section (cue phrases), 4.8 ms with `terms.definitions`, 2.1 ms a section end to end
through the step on Virginia (31,773 sections in 66 s, one commit per 500 rows, resume in 0.4 s). Decision model:
median 12.2 s a call (mean 12.8; 24 s cold), because `/v1/systemone` encodes the state once per question: 3,979
input tokens for seven questions against 567 for one, at about 300 tokens a second on this contended CPU. Chat
fallback: median 18.1 s a call.

**Reading it.**

* The model does not beat the rules where a label exists. On obligations it is the same (89 / 92 against 90 / 97);
  on permissions it trades recall for a little precision (56 / 62 against 46 / 88; the facts under-count
  permissions, so both precisions are floors); on definitions at 0.5 it finds 19% of what `terms` finds, where the
  cue phrase alone finds 34% and `terms` is what the step uses.
* Its probabilities are not calibrated at 0.5, as decision-models.md §3.2 found for mailboxes: the best in-sample
  thresholds are 0.05 (definition, obligation), 0.10 (penalty) and 0.95 (prohibition), fitted on 1 to 70 positives,
  which is a shape to note, not a setting to ship. The medians say the same: definition 0.12, penalty 0.001,
  power 0.08, obligation 0.79.
* Penalty is the one type where the model looks useful (at 0.10: 70 / 88 against the rules' 38 / 38), but against
  8 positives of a weak label. The rules' penalty cue list is the cheaper thing to improve, with the model's
  disagreements (6 sections it says yes to that the rules do not) as the review list.
* Prohibition has one positive; nothing can be said. Power and procedure have no label; the model says yes to far
  fewer sections than the rules (12 against 30, 46 against 51), with 80% and 67% agreement.
* `THRESHOLD` stays at 0.5 for every type; the measured "best" values are recorded here and not adopted.

**Where `section_tags` stands after the run.** Virginia is tagged by rules: structure in 8 shapes
(`title/chapter/article/section` 9,807, `title/subtitle/chapter/article/section` 9,777, `title/chapter/section`
5,305 ...), norm types obligation 24,475, permission 17,915, prohibition 10,035, definition 8,960, procedure
6,335, power 4,447, penalty 2,490 of 31,773 sections; `scans` has its row.

## 5. Nationwide estimate and go/no-go

Sections per state index (`/data/index/statutes_<st>.sqlite`, 47 states; AR, CO, GA, MS and TN have no file):
CA 161,382, TX 122,152, IN 75,961, IL 68,485, NJ 55,048, WA 51,491, NV 49,173, LA 42,947, AL 42,505, MI 42,349,
NY 40,162, SD 39,572, OR 39,265, MD 38,182, OK 35,266, OH 33,158, VA 31,777, MT 30,360, SC 30,292, MO 29,363,
NC 29,049, NE 28,429, UT 27,556, MN 27,570, NM 27,281, ND 25,480, WV 25,490, IA 25,593, NH 25,215, ME 25,162,
FL 25,020, PR 24,685, AZ 24,766, KS 24,284, VT 23,376, MA 23,057, ID 22,754, DE 21,394, KY 21,167, RI 21,024,
HI 18,842, DC 18,613, WI 18,158, AK 17,068, WY 16,370, CT 15,942, PA 14,122: **1,676,357 sections**, mean 35,667
a state (median 25,593), California 9.6% of the whole. The 39 regulation indexes are not counted; the same rules
apply to them (`corpus="regulations"`).

| Pass | per section | Virginia (31,777) | California (161,382) | all 47 states (1,676,357) |
|---|---|---|---|---|
| rules (structure, ELI id, norm types with `terms`), this CPU, measured | 2.1 ms | 66 s (measured) | 5.6 min | **58 min**, plus about 400 MB in `lexflow.db` |
| decision model, seven `noul` in one call, this CPU, measured contended | 12.2 s (24 s cold) | 4.5 days | 23 days | **237 days** (118 at the uncontended 6 s the benchmark's token rate implies) |
| decision model, one `noul` per call (567 tokens), this CPU | about 1.8–3 s | 16–26 h | 3.4–5.6 days | 35–58 days per question type, times seven |
| decision model on a 16 GB GPU node (tev1 0.8B Q8, 834 MB; a 4,000-token prompt pass at 5,000–8,000 tokens/s, one stream) | 0.5–0.8 s | 4.4–7 h | 22–36 h | **10–16 days** single stream; 3–5 days with 3–4 concurrent streams if Ollama is allowed to batch; the 16 GB holds the model with room for a 4B decision model (4.4 GB) at roughly 4x the time |
| chat fallback `qwen3:1.7b`, this CPU | 18 s | 6.6 days | 34 days | 350 days |

The GPU row is an estimate from token counts, not a measurement: nothing here has a GPU. Everything scales with
the number of questions per call, because the endpoint re-encodes the state per question; a nationwide model pass
should ask one combined question only if a multi-label answer can be had from one encoding, which `/v1/systemone`
does not offer.

**Go / no-go.**

* **Go: rules nationwide.** `lexflow run ontology` with no `model` tags all 47 states in about an hour on this
  machine and is idempotent and resumable; the structure tag is rule-exact (99.4% on unit levels), the ELI
  identifier is a pure function of the act_id, and the norm-type rules sit at 90 / 97 on obligations and are the
  only arm with a full definition label. The run writes about 1.7 million rows to this copy's own table and nothing
  to the wiki. What goes to the wiki from it, when wikibase-schema.md's packet is extended, is `unit level` (already
  planned), the ELI identifier as `act identifier`'s companion, and the norm types as `P5 instance of` the LKIF-
  matched classes Q13–Q15 plus new items for *definition*, *power*, *penalty* and *procedure*, with
  `determination method = matched by lexflow's software`: a reviewer should see the Virginia counts above and say
  whether the permission and prohibition tags (17,915 and 10,035 sections) are too generous before any of that is
  written.
* **No-go: the decision model nationwide.** 118–237 days on this CPU, 10–16 days on a 16 GB GPU node, for no
  measured gain over the rules on the labelled types and probabilities that need per-type thresholds fitted on a
  hand-labelled sample first. The model path stays in the step for targeted use: `model: decision` with
  `budget` (default 200 calls) and `limit`, so a reviewer can ask for a model opinion on one chapter's sections
  (a 200-section chapter is 40 minutes here), and `confidence` keeps every probability so a later threshold needs
  no re-run.
* **What would change the answer:** a labelled sample of 50 sections with the seven yes/no columns (open problem
  4), a decision model that encodes the state once for all questions, or a GPU node, in that order. With a GPU and
  the labels, the penalty type is the first candidate for a model pass, since it is the one the rules find worst
  and the model finds best.

## 6. Open problems

1. **LegalRuleML has no IRIs.** `sanction`, `bearer`, `deontic modality` and Q11–Q20 cannot get `P7`/`P8` to
   LegalRuleML until OASIS publishes the RDF vocabulary its spec describes; LKIF carries the deontic matches
   meanwhile, and the two are not the same theory (LKIF's `Right` is Hohfeldian, LegalRuleML's is a permission
   with correlative duties).
2. **LKIF's IRIs do not dereference.** The ontology is cited everywhere and unchanged since 2008, but
   estrellaproject.org now serves a home page for every path. The mapping keeps the canonical IRIs (that is what
   other data uses) and the checker reads GitHub; a consumer that follows the IRI gets HTML.
3. **ELI's licence is not in the file.** The OWL carries no `dcterms:license`; the Publications Office's reuse
   policy is the general answer, and the dataset page is script-rendered. This matters only if the ontology file
   is ever redistributed, not for using its IRIs.
4. **The norm-type labels are partial.** The reviewed models' facts say which modalities a section grounds, not
   which it lacks; the gold's `definition` and `penalty` roles are about the cited section. `terms.definitions` is
   the only full section-level label, and it is lexflow's own. A hand-labelled sample (50 sections, seven yes/no
   columns) would settle the precision numbers that §4 can only bound.
5. **Thresholds.** The decision model's `noul` probabilities are not calibrated at 0.5 (decision-models.md §3.2
   saw the same on mailboxes); the per-type thresholds in `THRESHOLD` come from 150 sections and should be
   re-fitted on the hand-labelled sample above before any model-tagged row is shown.
6. **Puerto Rico's structure** is bilingual and its paths carry the ley's name rather than a level, so its
   structure tag is `act/article` or `book/article` for every section; a Spanish level vocabulary (`libro`,
   `título`, `capítulo`) would refine it.
7. **Versions.** The table keys by `(state, ref)` and tags the version the index lists first; the four Virginia
   refs with two versions get one row. A `sec_id` column would allow one row per version at the cost of a
   second key form.
8. **Serving `/eli/`.** The template is defined and written nowhere yet; a redirect on the wiki host, and
   `eli:uri_schema` on the code items once the property exists, make the identifiers real.
