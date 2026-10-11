# Authority cross-references in Lexipedia's Wikibase: the wiki today, what Wikibase Cloud allows, and the Govdirectory question

Status: survey and recommendation, 2026-10-10. Read-only. Nothing was written to lexipedia.wikibase.cloud, Wikidata,
the DokuWiki or Govdirectory, and no dashboard setting was changed.

The question behind this note: should Lexipedia's Wikibase hold every Govdirectory entity, so that process models
can be cross-referenced against organisational units and offices, and so that escalation or deferral can be
derived from who holds authority?

Inputs:

* live reads of `https://lexipedia.wikibase.cloud` (API, query service, `Special:EntityData`, WikibaseManifest);
* Wikibase Cloud's documentation (mediawiki.org, meta.wikimedia.org) and its open-source platform code
  (`github.com/wbstack/mediawiki`, `wbstack/api`, `wbstack/ui`, read with raw GETs);
* Govdirectory's `sitemap.xml` and statistics page, and WDQS counts over the organisations listed there;
* `lexflow/publish/wikibase_lexipedia.py`, `fixtures/entities/agencies.json`, `fixtures/xref/gold_*.json`,
  `curated/ny/records.json`;
* the earlier designs this note builds on: [entities-contacts.md](entities-contacts.md) (agencies, office types,
  "played by", contacts), [entities-sources.md](entities-sources.md) (Govdirectory and Wikidata coverage),
  [terms-wikibase.md](terms-wikibase.md) (terms, concepts, SKOS matches) and
  [links-codebase-map.md](links-codebase-map.md) §3 (the wiki's properties and the loader's keys).

Method. Every request was a GET (or a read-only SPARQL POST to WDQS). The User-Agent was
`lexflow-research/0.1 (https://github.com/alibama/lexflow)`. Requests were spaced at least 1.1 s apart per host,
and SPARQL queries ran one at a time. Wikidata API reads sent `maxlag` and waited when the query service lagged.
No login was made, so rights and limits are those a reader can see plus the platform's published configuration.

---

## 0. The short answer

**Yes, the wiki needs updating. No, not by mirroring Govdirectory.**

* **Today the wiki cannot answer an authority question.** It has no class for an organisation, a unit or an
  office. A process step's bearer (P17) points at a per-process *legal role* item that carries only a key, a class
  and a state. None of the 52 state items has a Wikidata link. So there is nothing to join a process to an
  organisational unit, a post or a superior.
* **A full Govdirectory mirror is technically possible and practically wrong for lexflow.**
  * Size: 21,084 organisations, plus about 6,650 head-of-organisation posts and up to about 1,250 classes, is
    roughly 29,000 items. That is a few hours of writes, and Wikibase Cloud already hosts instances 30 times
    larger.
  * Relevance: 94.6 % of those organisations are outside the US. Only 1,140 are US bodies, and those are federal
    bodies, New York and North Carolina only.
  * Coverage: of the 91 Wikidata items that lexflow's own models and references name (bodies, units and
    related posts in `agencies.json`), **7 are on Govdirectory**.
  * Freshness: Govdirectory adds no data beyond Wikidata ([entities-sources.md](entities-sources.md) §1), so a
    mirror would be a monthly-stale copy of Wikidata.
* **What to do instead.**
  1. Create items only for the bodies, units, office types and posts that reviewed processes reference: about
     300 to 450 items for the 11 corpus jurisdictions.
  2. Give each one a Wikidata QID as an external identifier.
  3. Reach the rest of Wikidata, including Govdirectory's organisations, at query time. **Lexipedia's query
     service can federate to `query.wikidata.org`; this was tested here and works.**
  4. Model posts, never persons.
* **Changes needed on the wiki.**
  * 12 new properties (3 of them already proposed in earlier designs), 2 qualifier properties and 5 classes
    (§4.2).
  * Two property mappings in the Wikibase Cloud dashboard, so that the QID becomes a link and an RDF IRI.
  * A `Project:Copyrights` page and a hosting-review submission. Under Wikibase Cloud's new hosting policy, every
    instance becomes temporary unless its manager applies (§2.7).
  * Each of these is a wiki write or a settings change, so each waits for the user.

| Option | Items | First load at 1 edit/s | Covers lexflow's bodies | Verdict |
|---|---|---|---|---|
| A. Mirror all of Govdirectory | ~29,000 (+46,431 contact points if mirrored) | ~8 h | 7 of 91 QIDs | No: mostly non-US, stale copy, hosting-policy risk |
| B. Mirror US Govdirectory (federal, NY, NC) | ~1,500 | ~25 min | 7 of 91 QIDs | Only if a process needs federal, NY or NC bodies wholesale (e.g. NC licensing boards) |
| **C. Mint what processes reference, link the rest** | **~300–450** | **< 10 min** | **all, including the 15 bodies with no Wikidata item** | **Recommended** |

---

## 1. Lexipedia's Wikibase today (measured 2026-10-10)

### 1.1 The site

| Fact | Value |
|---|---|
| Software | MediaWiki 1.43.11, PHP 8.1.31, MariaDB 10.5.15, CirrusSearch + WikibaseCirrusSearch |
| Wikibase extensions | WikibaseRepository, WikibaseClient, EntitySchema (0 schemas), WikibaseManifest, Wikibase EDTF. Not loaded: WikibaseLexeme, WikibaseQualityConstraints (so no constraint checks) |
| Datatypes on offer | item, property, string, external-id, url, quantity, time, monolingualtext, globe-coordinate, commonsMedia, geo-shape, tabular-data, math, EDTF, musical-notation |
| Pages / items / properties | 1,459 pages; **1,433 items** (Q1–Q1438, 5 ids unused); **25 properties** (P1–P25) |
| Edits / accounts | 5,272 edits; 2 accounts: the wiki's administrator (5,259 edits; lexflow's bot password writes as this account) and the platform's maintenance account (13 edits) |
| Statements | 8,162 on items; **0 qualifiers, 0 references, 0 sitelinks** |
| Last write | 2026-10-10 06:29 UTC (the loader's `retire_drafts`) |
| Endpoints (WikibaseManifest) | API `/w/api.php`, REST `/w/rest.php`, query UI `/query`, SPARQL `/query/sparql`, QuickStatements `/tools/quickstatements` (HTTP 200), Cradle `/tools/cradle` (HTTP 200), OAuth consumer registration |
| Entity URIs | `https://lexipedia.wikibase.cloud/entity/Q168`; direct claims `…/prop/direct/P25`; normalised `…/prop/direct-normalized/` |
| Wiki pages that the hosting policy asks for | Main Page describes the intended use (5.9 KB). `Project:About`, `Project:Copyrights` and `Project:SPARQL/examples` do not exist |

**Lexipedia's Q-ids are local and collide with Wikidata's.** Lexipedia Q30 is Connecticut, but wd:Q30 is the
United States. Lexipedia Q33 is Florida, but wd:Q33 is Finland. Every query and every stored link must carry a
namespace: an entity IRI, or a QID in a property whose meaning is "Wikidata item".

### 1.2 Properties

"Items" counts the items that use the property as a main statement. "≡" is the property's own `P7 equivalent
property` value.

| P | Datatype | Label | Description (abridged) | ≡ | Items using it |
|---|---|---|---|---|---|
| P1 | item | father | base-import sandbox property | – | 0 |
| P2 | item | mother | base-import sandbox property | – | 0 |
| P3 | item | child | base-import sandbox property | – | 0 |
| P4 | commonsMedia | image | base-import sandbox property | – | 0 |
| P5 | item | instance of | class membership (Wikidata's text) | wd:P31 | 1,392 |
| P6 | item | subclass of | subclass (Wikidata's text) | wd:P279 | 8 (the deontic classes) |
| P7 | url | equivalent property | owl:equivalentProperty mapping | owl:equivalentProperty | properties only |
| P8 | url | exact match | skos:exactMatch to an external IRI (Wikidata, LegalRuleML) | skos:exactMatch | 8 (6 LegalRuleML classes, 2 cities) |
| P9 | item | part of | node is part of a whole (process, statute) | wd:P361 | 483 |
| P10 | item | has part | whole has the node as a part | wd:P527 | 48 (480 statements) |
| P11 | item | follows | process order | wd:P155 | 390 (440 statements) |
| P12 | item | followed by | process order | wd:P156 | 0 |
| P13 | item | references | node references or cites an entity | wd:P2860 | 645 (949 statements) |
| P14 | item | based on | derived from | wd:P144 | 0 |
| P15 | item | applies to jurisdiction | jurisdiction in which the node applies | wd:P1001 | 857 |
| P16 | item | deontic modality | Obligation / Permission / Prohibition / Right (LegalRuleML) | – | 465 |
| P17 | item | bearer | party legally bound by the norm (LegalRuleML Bearer) | – | 479 |
| P18 | item | condition | condition under which the deontic specification holds; may reference a DMN decision | – | 0 |
| P19 | item | governed by norm | the norm that governs this node | – | 0 |
| P20 | item | sanction | penalty on violation (LegalRuleML Penalty) | – | 0 |
| P21 | item | defeated by | norm or exception that defeats this one | – | 0 |
| P22 | string | citation | statutory citation | – | 575 |
| P23 | url | official text | link to the official text | – | 613 |
| P24 | time | effective date | date the provision takes effect | – | 0 |
| P25 | external-id | legal identifier | canonical external id; lexflow's key | – | 1,413 (every lexflow item) |

The query service lists the same 25 properties with the same types. P1–P6 and Q1–Q6 are the Wikibase Cloud
"Import base entities" set (§2.3). P7–P25 and the ontology classes Q7–Q20 were created on the wiki before
lexflow's loader ran. The loader created Q21–Q23.

### 1.3 Item classes and counts

The API (`wbgetentities` over every item) and the query service (`SELECT ?c (COUNT(?i)) { ?i P5 ?c }`) gave
identical counts, so the query service was in sync.

| Class (P5) | Items | Of which drafts | Written by |
|---|---|---|---|
| Q10 statute or legal provision | 496 | – | loader, `lexflow:statute:` |
| Q8 legal process step | 437 | 205 steps across Q8 and Q9 | loader, `lexflow:step:` |
| Q23 legal role | 196 | 108 | loader, `lexflow:role:` |
| Q22 court decision | 117 | – | loader, `courtlistener:cluster:` |
| Q21 jurisdiction | 55 (52 states, DC and PR; 3 cities) | – | loader, `lexflow:jurisdiction:`, `lexflow:gov:` |
| Q7 legal process | 48 | 26 | loader, `lexflow:process:` (22 reviewed: 11 jurisdictions × records and business) |
| Q9 decision point | 43 | (counted with Q8) | loader |
| no P5 | 41 | 18 retired drafts (15 steps, 3 roles) | 6 base-import items, 17 class items (Q7–Q23), 18 retired drafts |

* **357 items are drafts.** Their description begins "Unreviewed draft". That text is the only marker: no
  statement records review status. So a SPARQL query for "processes" returns 26 unreviewed models unless it
  filters on the description.
* **Jurisdictions have no Wikidata link.** None of the 52 state items has P8. Of the 3 city items, Baltimore
  (Q76) and Charlottesville (Q77) carry P8; Washington DC (Q75) does not.

### 1.4 What three kinds of item look like

**Statute section, Q168** (`lexflow:statute:fl:607.0201`). Label "Fla. Stat. § 607.0201", description
"607.0201 Incorporators.". It is unchanged from the reads in [terms-wikibase.md](terms-wikibase.md).

| P | Value |
|---|---|
| P25 legal identifier | `lexflow:statute:fl:607.0201` |
| P5 instance of | Q10 statute or legal provision |
| P22 citation | `Fla. Stat. § 607.0201` |
| P15 applies to jurisdiction | Q33 Florida |
| P23 official text | the leg.state.fl.us URL of 0607.0201 |

**Jurisdiction, Q33** (`lexflow:jurisdiction:fl`). Label "Florida", description "US state or district (lexflow
jurisdiction)". It has only P25 and P5 → Q21. A city is one step richer: Q76 "City of Baltimore, Maryland" has
P5 Q21, P9 part of → Q44 Maryland, and P8 → `http://www.wikidata.org/entity/Q5092`.

**Process, Q774** (`lexflow:process:fl.business`), "Start a business in Florida (LLC filing path) (Florida)".
Its description says "… Process model by lexflow, checked by Claude."

| P | Value |
|---|---|
| P5 | Q7 legal process |
| P15 | Q33 Florida |
| P13 references | 18 statute items, Q161–Q178 (including Q168) |
| P10 has part | 17 step items, Q780–Q796 |

The process's steps and roles:

* **Step Q780** "Sign and deliver articles of organization (Florida start a business)":
  * P5 Q8; P9 → Q774; P16 → Q14 Permission;
  * **P17 bearer → Q775**;
  * P13 → Q161 (§ 605.0201).
* **Step Q782** "Check articles and fees": P5 Q9 decision point, P11 follows → Q781, P16 Obligation,
  **P17 → Q776**.
* **Role Q776** "Department of State, Division of Corporations (Florida)", described as "public-body in the start a
  business process". It has only P25 `lexflow:role:fl:business:department`, P5 Q23 and P15 Q33.
  * This is the join point the authority work needs, and it is a dead end today. It does not say which
    organisation plays the role (Wikidata Q107179384), which body that one is part of (Florida Department of
    State, Q11969252), or which post heads it.

### 1.5 How lexflow writes (`publish/wikibase_lexipedia.py`)

* **Lookups by label.** Properties and classes are found by English label (`PROPS`, `CLASSES`, `prepare()`
  `:142-155`). A new class is created once, under the key `lexflow:class:<label>`.
* **Keys.**
  * Every entity carries its key in P25 (`entity()` `:157-196`).
  * The local table `wikibase_items(key, qid)` maps keys to items, so a re-run updates rather than duplicates.
  * If that table is lost, `owner()` (`:198-207`) recovers an item through a label clash that names it.
  * CirrusSearch also indexes P25: `haswbstatement:P25=lexflow:statute:fl:607.0201` returns Q168. That is a
    cheaper recovery path than the label clash.
* **Updates replace.** An update sends `wbeditentity` with `clear`, which replaces every statement. So every
  claim must be regenerated from the database on each load. Qualifiers and references are no exception.
* **Constraints.**
  * Label + description must be unique; the loader appends `[key-suffix]` on a clash.
  * Strings are capped at 400 characters (`_snak` `:126`).
  * Only `reviewed` and `agreed` models load. `single` models only relabel items an earlier version wrote, and
    `retire_drafts` blanks superseded ones (`:209-232`).
* **Throughput and flags.**
  * The last load wrote up to **268 edits in one minute**. The MediaWiki default for ordinary users is 90 a
    minute; the admin account it writes as has `noratelimit` through its sysop group (§2.6).
  * The loader sends `bot=1`, but the account is not in the `bot` group. So 0 of the last 500 edits carry the
    bot flag, and every load floods Recent changes.

---

## 2. What Wikibase Cloud allows (verified)

### 2.1 Summary

| Capability | On Lexipedia | Evidence |
|---|---|---|
| Create properties | **Yes, for any logged-in account.** `property-create` is granted to `*`, and edit rights come with `user` | siteinfo `usergroups` |
| Create classes | **Yes.** A class is an ordinary item (as Q21–Q23 were made) | loader `:155` |
| Bulk import through the API (bots, `wbeditentity`) | **Yes.** This is what lexflow does | §1.5 |
| QuickStatements, Cradle | **Yes**, hosted per wiki at `/tools/quickstatements` and `/tools/cradle`, with login through the wiki's OAuth | manifest; both answer HTTP 200 |
| OpenRefine, WikibaseIntegrator, Pywikibot | Yes, as API clients | [Wikibase/Importing](https://www.mediawiki.org/wiki/Wikibase/Importing) |
| WikibaseImport, RaiseWikibase, XML import | **No.** They need a server shell or the database. Only sysops have the `import` right, and that is the web XML import, not entity import | Importing page; siteinfo |
| Import entities from Wikidata | **Only the fixed base set, once per wiki**: 6 properties and 6 items, already used here (P1–P6, Q1–Q6). There is no general importer | dashboard card `EntityImport.vue`; meta update, Sept 2024 |
| Federated properties (use Wikidata's P-ids directly) | **No for Lexipedia.** The platform has a hidden `wikibaseFedPropsEnable` setting, but the dashboard does not expose it. Wikibase allows it only on a fresh wiki with no local properties, with no way back. Lexipedia has 25 local properties and 8,162 statements using them | §2.4 |
| Query service | **Yes**, Blazegraph at `/query/sparql`, in sync at survey time | §2.5 |
| Federated SPARQL from Lexipedia to `query.wikidata.org` | **Yes, tested.** A 2-row join from Lexipedia's P8 links to Wikidata labels and P131 parents answered in 2.45 s | §2.5 |
| Federated SPARQL from WDQS to Lexipedia | **No, not today.** Lexipedia is not on WDQS's allowlist; 5 other wikibase.cloud endpoints are. It would need a nomination | §2.5 |
| External identifier linking to Wikidata QIDs, with a formatter URL | **Yes, after two property mappings in the dashboard**, with a known delay of up to 24 h before links turn clickable | §2.6 |
| Lexemes | Off; can be switched on in the dashboard's Features tab | Wikibase settings doc |
| Entity schemas (ShEx) | Installed, none written | siteinfo |

### 2.2 Properties and classes

* Properties are created with `wbeditentity` `new=property` (with a datatype) or with Special:NewProperty. This
  needs a logged-in account; anonymous users cannot edit (`*` has no `edit` right).
* The ontology's own conventions should be kept:
  * an English description;
  * a `P7 equivalent property` → the Wikidata property where one exists (P9, P13 and P15 already do this);
  * a `P8 exact match` on classes.
* The loader finds properties by label, so a new property's English label is part of the contract. It must be
  unique and stable.
* There are no property constraints (WikibaseQualityConstraints is not loaded). Validation would be an
  EntitySchema (ShEx) per class, checked by hand or by a lexflow test, not by the wiki.

### 2.3 Bulk import

* **The loader is the import path.**
  * It already has keys, `clear`-based idempotence, retry on `ratelimited` and `maxlag`, and the
    reviewed-only rule.
  * QuickStatements and OpenRefine would bypass the `wikibase_items` mapping, and the next `clear` would erase
    whatever they wrote. They are useful only for one-off manual fixes.
* **No server-side tools.**
  * Wikibase Cloud runs no WikibaseImport and offers no shell. RaiseWikibase writes straight into MariaDB.
  * So "copying entities from Wikidata" always means reading Wikidata and writing new local items through the
    API, each with its own local Q-id.
* **The base import is spent.** "Import base entities" offers six Wikidata properties (mother, father, child,
  image, instance of, subclass of) and six items (Universe, World, Human, Berlin, Douglas Adams, *The
  Hitchhiker's Guide to the Galaxy*), "once per Wikibase instance" (`wbstack/ui`
  `src/components/Pages/ManageWiki/Cards/EntityImport.vue`). That is exactly P1–P6 and Q1–Q6 here.

### 2.4 Federated properties

* **What Wikibase says.** Federated Properties v1 makes a wiki use Wikidata's properties instead of its own. The
  Wikibase docs say it:
  * must be enabled "only for a fresh Wikibase installation without any existing local Properties";
  * cannot be switched off again;
  * is for evaluation, not production.

  Federated Properties v2, which would mix local and remote properties, is an ADR with status "proposed".
* **What the platform has.**
  * `wbstack/mediawiki` `dist-persist/wbstack/src/Settings/LocalSettings.php` turns it on when the per-wiki
    setting `wikibaseFedPropsEnable` is set ("By default not enabled").
  * The platform API accepts that setting (`wbstack/api` `app/Http/Controllers/WikiSettingController.php:25`).
  * The dashboard's Features tab shows only entity mapping and Lexemes (`ManageFeatures.vue`), and the user
    documentation never mentions the option.
* **For Lexipedia it is closed.** Its own properties carry the whole ontology, and the hybrid that would let it
  borrow, say, wd:P2388 alongside local P1–P25 does not exist. The workable substitutes:
  * **property mapping** (P7 statements, plus the dashboard's "Mapping properties to Wikidata" table);
  * **QIDs stored on local items**;
  * **SPARQL federation at query time**.

### 2.5 Query service and SPARQL federation

* **Endpoint.** `https://lexipedia.wikibase.cloud/query/sparql`. Write prefixes out explicitly. The entity data
  uses `wd:`/`wdt:` for Lexipedia's own entities, and the getting-started doc says the opposite for the UI.
  Explicit `PREFIX lx: <https://lexipedia.wikibase.cloud/entity/>` and
  `lxt: <https://lexipedia.wikibase.cloud/prop/direct/>` avoid the ambiguity.
* **Freshness.** Class counts matched the API exactly at survey time. Wikibase Cloud's updater is asynchronous,
  so a check right after a load may lag.
* **Outbound federation works.** Two queries were tried:
  * `SERVICE <https://query.wikidata.org/sparql> { wd:Q30 rdfs:label ?l }` returned "United States" in 1.46 s.
  * The join below returned Charlottesville → Virginia and Baltimore → Maryland in 2.45 s:
    ```sparql
    SELECT ?item ?wd ?wdLabel ?parentLabel WHERE {
      ?item lxt:P8 ?wd . FILTER(STRSTARTS(STR(?wd), "http://www.wikidata.org/entity/"))
      SERVICE <https://query.wikidata.org/sparql> {
        ?wd rdfs:label ?wdLabel FILTER(LANG(?wdLabel) = "en")
        OPTIONAL { ?wd wdt:P131 ?parent . ?parent rdfs:label ?parentLabel FILTER(LANG(?parentLabel) = "en") } } }
    ```
  * Wikibase Cloud's own updates page records why this works:
    * federation between instances was enabled in October 2024;
    * new instances have been allowlisted automatically since November 2024;
    * Q1 2026 aligned the allowlist with "the same endpoints that Wikidata Query Service supports".
* **Inbound federation does not.** WDQS keeps its own allowlist. Its mediawiki.org copy is marked obsolete, last
  edited 1 October 2026; the authoritative list is in the WDQS puppet module. That copy lists five
  wikibase.cloud endpoints (beyond-notability, metabase, snarc-llgc, sweopendata, lgbtdb) and no wildcard.
  Nominations go to *Wikidata:SPARQL query service/Federated queries/Allowlist*. Lexipedia does not need this
  direction: lexflow queries outwards.
* **Practical limits.**
  * A `SERVICE` block sends its bindings to WDQS, which has a 60 s timeout and its own usage policy, so keep
    federated joins small: per process or per state.
  * Bulk crosswalks, such as checking every agency's QID for redirects, are better run by lexflow straight
    against WDQS, one query at a time, as the contacts plan already does.

### 2.6 Limits

| Limit | Value on Lexipedia | Source |
|---|---|---|
| Edits, anonymous IP | 8 per 60 s (`wikibase-idgenerator` the same) | `meta=userinfo&uiprop=ratelimits` |
| Edits, logged-in user / bot group | 90 per 60 s; a "newbie" (not autoconfirmed) 8 per 60 s. New-entity ids inherit the create/edit limit | MediaWiki 1.43 `MainConfigSchema::RateLimits`; Wikibase `extension-repo.json` (`&inherit-create-edit`). The platform's `LocalSettings.php` does not override `$wgRateLimits` |
| Exempt groups | `sysop` and `bureaucrat` have `noratelimit`; the `bot` group does not, but has `apihighlimits` | siteinfo `usergroups` |
| Observed | 268 edits in one minute during the last load | `list=recentchanges` |
| maxlag | 5 s | WikibaseManifest `max_lag` |
| Strings (string, monolingualtext) | 400 characters by default; 400–2,500 settable in the dashboard | Wikibase settings doc; `WikiSettingController.php:22-24` |
| Labels, descriptions, aliases | 250 by default; 250–2,500 settable | same |
| Page size (one entity's JSON) | 2,097,152 bytes | siteinfo `maxarticlesize` |
| Upload | 100 MB (no files uploaded) | siteinfo |
| Dataset size, traffic | **No fixed numeric limits.** Decided case by case; "abusive and unjustified" size or load disqualifies an instance | hosting policy (§2.7) |
| Largest instances, for scale | 929,785 pages; 880,923 pages; 652,232 pages (of 2,304 active instances) | `api.wikibase.cloud/wiki?sort=pages` (the dashboard's discovery list) |
| Backups | daily, 7 days kept, in Finland | Wikibase Cloud FAQ |
| Bulk export | No dump service is documented (the FAQ's "How can I download all my data" has no answer). Per entity: `Special:EntityData/Q….json` or `.ttl`; or SPARQL `CONSTRUCT` | FAQ |
| Large POST bodies | a user report of HTTP 413 on big batch edits (not an official limit) | OpenRefine forum |

**A platform quirk: the string limit follows the wrong setting.** `LocalSettings.php` reads
`wwWikibaseStringLengthMonolingualText` for the VT:string limit as well. So raising "string length" alone does
nothing; raise the monolingual-text setting too. This matters only if quotes longer than 400 characters (for
example, the conferring words of an authority clause) are ever stored as qualifiers.

**External identifier to Wikidata with a formatter URL.** The FAQ's recipe:

1. Create a string property *formatter URL*.
2. Map it to wd:P1630 in Dashboard → ⚙ → Features → "Mapping properties to Wikidata".
3. Create an external-id property, *Wikidata item ID*, and give it the statement *formatter URL* =
   `https://www.wikidata.org/wiki/$1`.

There is a known delay of up to 24 hours before the identifiers become clickable (phabricator T364744). A second
string property *formatter URI for RDF resource*, mapped to wd:P1921 with the value
`http://www.wikidata.org/entity/$1`, sets Wikibase's `canonicalUriProperty`. With it, the query service also emits
`…/prop/direct-normalized/<P> <http://www.wikidata.org/entity/Q812>`, an IRI that a `SERVICE` block can join on
directly. Without it, a query has to build the IRI with `IRI(CONCAT(...))`.

Today the manifest lists no mapped entities, so neither function is on. P25 is an external-id with no formatter.

### 2.7 The hosting policy: Lexipedia is probably now a temporary instance

* **The timeline.** Wikibase Cloud's Q2 2026 update says:
  * workflows were to be in place "by the end of September 2026";
  * "all new and existing Wikibases become temporary by default";
  * managers then "have three months to submit them for review".
* **What happens to a temporary instance.**
  * The policy text (staged on mediawiki.org; the binding copy is at wikibase.cloud/hosting-policy) says that
    temporary instances that never apply are suspended after 3 months.
  * Suspended instances are deleted 3 months after that.
  * The dashboard's Review tab says: "This instance is temporary. To keep it, submit it for review by the
    hosting policy review committee."
* **Required criteria.**
  * The main page or `Project:About` describes the intended use. **The Main Page already does.**
  * A licensing statement on `Project:Copyrights`. **Missing.**
  * The structured data is CC0.
  * Text in other namespaces allows reuse.
* **Disqualifiers that touch this work.**
  * "Data about living people … without appropriate local rules". This is the strongest reason to model posts,
    not holders, and to write a short local rule saying so (§4.5).
  * Abusive or unjustified dataset size or load. A 29,000-item copy of Wikidata content with no lexflow use
    would be hard to justify.
* **A positive exception.** "Staging ground for a dataset being prepared for later contribution" (to Wikidata)
  counts in an instance's favour.

The review submission, the Copyrights page and the deadline are the user's to handle. This survey could not see
the dashboard.

---

## 3. Mirroring Govdirectory: size and practicality

### 3.1 How many organisations

Govdirectory's statistics page (data "last updated 2026-09-25") gives 46 countries, 21,105 organisations and
46,431 contact points. Its `sitemap.xml` (1.9 MB, one GET on 2026-10-10) lists 21,105 organisation pages and
21,084 distinct QIDs:

| Pages | Organisations |
|---|---|
| Bulgaria 3,638 · Austria 2,208 · Switzerland 2,154 · Philippines 1,764 | 9,764 |
| Belgium 966 · Sweden 766 · Indonesia 739 · Bangladesh 700 · Norway 594 · East Timor 566 | 4,331 |
| Morocco 431 · Finland 429 · Netherlands 429 · Portugal 346 · South Africa 322 · Ghana 305 | 2,262 |
| European Union 264 · Germany 263 · Peru 240 · Poland 240 · Czech Republic 234 · UK/Scotland 232 · Japan 229 · Malaysia 205 | 1,907 |
| Cyprus 198 · New Zealand 175 · Chile 171 · Luxembourg 132 · Denmark 124 · Nepal 112 | 912 |
| 16 more pages, 5–98 each (Eswatini … Greenland) | 789 |
| **United States: federal 374 · North Carolina 607 · New York 159** | **1,140** |
| **Total** | **21,105 page entries; 21,084 distinct QIDs (21 non-US URLs are listed twice)** |

**US total: 1,140.** It breaks down as:

* **federal (374)**: mostly embassies and consulates, plus 15 departments, 24 legislative agencies, 36 small
  business offices and 29 interstate commissions;
* **North Carolina (607)**: 400 state agencies, 100 counties, 100 county election boards, and the legislature and
  courts;
* **New York (159)**: 97 state agencies and 62 counties.

There is nothing for VA, DC, MD, TX, CA, FL, IL, WA or OH ([entities-sources.md](entities-sources.md) §2.2–2.4).

### 3.2 What Wikidata holds for those organisations

These come from WDQS queries over the 21,084 QIDs, run in chunks of at most 2,500 on 2026-10-10. For the non-US
row, "distinct" counts are summed over chunks, so they are upper bounds.

| Set | Orgs | Head post (P2388 or P1313) | Distinct head posts | Parent org (P749) | Regulatory or foundational text (P92/P457) | P1001 jurisdiction | Person as head (P488/P169/P1037/P3975) | Official website | Classes (P31) |
|---|---|---|---|---|---|---|---|---|---|
| US federal | 374 | 201 (54 %) | 203 | 122 | 86 (47 texts) | 250 | 22 | 356 | 52 |
| US / New York | 159 | 14 (9 %) | 13 | 16 | 1 | 92 | 3 | 154 | 31 |
| US / North Carolina | 607 | 17 (3 %) | 17 | 14 | 103 (2 texts) | 450 | 0 | 594 | 66 |
| Non-US | 19,944 | 6,547 (33 %) | ≤ 6,421 | 1,351 | 1,247 (≤ 309 texts) | 3,154 | 337 | 14,224 | ≤ 1,102 |

**Authority structure is thin even inside Govdirectory's own US set.**

* Only 3 % of NC's and 9 % of NY's listed bodies name a head post, and hardly any names a parent.
* Two examples from the corpus:
  * The *Office of the Secretary of State of California* (Q141105514) has P2388 → the post *Secretary of State of
    California* (Q7024182). That post is P31 position, P279 state secretary of state, P1001 California and
    P2389 → the office. Both directions are there.
  * The *Florida Division of Corporations* (Q107179384) has P749 → *Florida Department of State* (Q11969252),
    but that department names no head post at all.

So an escalation chain such as "division → department → the post that heads it" cannot come from Wikidata alone,
even where Wikidata has the bodies.

### 3.3 What a full mirror would cost

| | Full Govdirectory | US Govdirectory only |
|---|---|---|
| Organisation items | 21,084 | 1,140 |
| Head-post items | ~6,650 | ~233 |
| Class items | up to ~1,250 | up to ~149 |
| Jurisdiction items beyond the existing 55 | the countries and regions named by P1001/P131 (not counted here) | federal, NY, NC counties |
| Statements, about 5 per org and 4 per post | ~130,000 | ~7,000 |
| Contact points, if copied with references as [entities-contacts.md](entities-contacts.md) proposes | +46,431 | +2,000 or so |
| First load, one `wbeditentity` per item | ~8 h at 1 edit/s; ~2 h at the 268/min the account reached | ~25 min at 1 edit/s |
| Refresh | monthly diff against WDQS, re-sending every changed item in full (because of `clear`) | the same |

**Is that size practical on Wikibase Cloud? Technically, yes.**

* There is no numeric cap.
* 29,000 items is 3 % of the largest instance.
* Item JSON is a few kilobytes, far below the 2 MB page limit.
* The loader already handles rate limits and maxlag.

Three practical frictions come with it:

* **Labels.** Label + description must be unique together. Non-US ministries repeat labels ("Ministry of
  Health"), so every description needs the country, which is the same work the loader already does for steps.
* **Rate.** At the default 90 edits a minute, a non-sysop bot account would take about 5½ hours.
* **The review committee.** It would see a mostly foreign, monthly-stale copy of Wikidata with no use on the
  wiki.

### 3.4 Why the recommendation is option C

1. **Relevance.**
   * The 22 reviewed processes and the AskBench references are all US state law in 11 jurisdictions.
   * `fixtures/entities/agencies.json` names 144 bodies: 98 specific ones and 46 generic office types. They
     resolve to 76 distinct body QIDs, plus 7 units and 8 related items. Of those 91 QIDs, **7 appear on
     Govdirectory**: 2 New York, 5 North Carolina.
2. **Missing bodies are the important ones.** The escalation targets are often absent from Wikidata altogether:
   * NY's Committee on Open Government (only its parent, the Department of State, has an item);
   * the California Office of Administrative Hearings (only its parent, General Services);
   * Virginia's Department of Professional and Occupational Regulation (no item).

   Lexipedia must mint these whatever Govdirectory holds.
3. **No new data.**
   * Govdirectory is a rendering of Wikidata. Its value to lexflow is the curated class lists, the query
     patterns and the URL `govdirectory.org/<slug>/<QID>/` ([entities-sources.md](entities-sources.md) §1).
   * The URL can go on Lexipedia's own agency items as *described at URL* (wd:P973), as the contacts plan
     proposes.
4. **Freshness and ownership.**
   * A copy is stale from the next Wikidata edit.
   * Under `clear`, Lexipedia's copy would also be overwritten wholesale on each refresh. Any local correction
     would have to live in lexflow's database, which is exactly the D12 rule in
     [entities-contacts.md](entities-contacts.md).
5. **Privacy and policy.** Govdirectory's `organization-optional.rq` reads person-valued "led by" statements.
   Mirroring them would put living people's data on the wiki, which the hosting policy disqualifies without local
   rules and which this project's privacy rule excludes.

**Tiers.**

* **Tier A (now).** Mint the bodies, units, office types, courts and posts that reviewed processes and
  references name, plus each one's parent chain up to the state government: about 300–450 items (§4).
* **Tier B (later, on demand).** The US Govdirectory set, if a process needs it wholesale. Examples: the 39 NC
  licensing boards for a licence-after-conviction model, or federal departments for a federal process.
  Load it from the Govdirectory generator queries run against WDQS, never from the website.
* **Tier C (never).** The 19,944 non-US organisations. Reach them with `SERVICE` when needed.

---

## 4. What the authority work needs from the wiki

This section gives the minimum shape that any escalation or deferral design will need on Lexipedia. The design of
the escalation logic itself (BPMN escalation events, DMN conditions and when to defer) is out of scope here.

### 4.1 The chain to make queryable

```
process step ──bearer (P17)──▶ legal role ──played by──▶ agency / unit / office type / court
     │                          (per process)                │        │
     │                                                       │   part of (P9) ──▶ parent agency ──▶ … ──▶ government
     │                                                       │
     │                                                head position ──▶ public office (post)
     │                                                                     │
     │                                                          appointed by ──▶ appointing post or body
     │
     ├──escalates to──▶ role / body / post   (qualifiers: references → statute, condition → decision)
     └──defers to────▶ role / body / post    (the same qualifiers)

agency / post ──authority conferred by──▶ statute section (Q10 item; the xref "authority" role)
agency / post / jurisdiction ──Wikidata item ID──▶ "Q…"  (federated joins to WDQS at query time)
```

**Two kinds of escalation.** Structural escalation (a superior body or post) comes from *part of*, *head position*
and *appointed by*. Statutory escalation (an appeal, a petition, a referral) comes from *escalates to* and
*defers to*, and each of those carries the statute that creates the path.

**Where the statutes come from.** Gold labels them already: 81 `authority`, 96 `procedure` and 76
`prerequisite_process` references in `fixtures/xref/gold_{a,b,c}.json`. `lexflow/law/xref.py` labels new text
with the same `ROLES`.

### 4.2 Classes and properties to add

This list merges the earlier proposals with what authority adds. Names are proposals; the loader will look them
up by label.

| New entity | Kind | ≡ Wikidata | On → value | Why authority needs it | Proposed in |
|---|---|---|---|---|---|
| *government agency* | class | P8 → wd:Q327333 | – | bodies that act in processes | entities-contacts §1.7 |
| *organization unit* | class | P8 → wd:Q10387680 | – | divisions and sections (Florida Division of Corporations, the CA Business Entities Section) | **this note** |
| *public office* | class | P8 → wd:Q294414 (Wikidata's posts are P31 wd:Q4164871 *position*) | – | the post, not the person: "head of the agency", Secretary of State | **this note** |
| *court* | class | P8 → wd:Q41487 | – | review and appeal targets (Article 78 → NY Supreme Court) | entities-contacts §1.7 |
| *office type* | class, P6 → agency, court or public office | – | – | generic actors resolved per county or per agency ("the clerk", "head of the agency holding the record") | entities-contacts §1.7 |
| *Wikidata item ID* | external-id, formatter `https://www.wikidata.org/wiki/$1`, RDF URI `http://www.wikidata.org/entity/$1` | – (its values are Wikidata QIDs; the identity counterpart of the SKOS `P8 exact match`) | agency, unit, post, court, jurisdiction → `Q812` | crosswalk; clickable; `haswbstatement` lookup; normalised IRI for `SERVICE` joins. Put it on the 52 state items first (Q33 Florida → Q812) | **this note** |
| *formatter URL* | string, mapped to wd:P1630 | P1630 | property → template | makes external IDs clickable | Wikibase Cloud FAQ |
| *formatter URI for RDF resource* | string, mapped to wd:P1921 | P1921 | property → template | normalised IRIs in the query service | **this note** |
| *played by* | item | – | role → agency, unit, office type, court or `lexflow:private-party` | the missing join between processes and organisations | entities-contacts §1.7 |
| *head position* | item | P7 → wd:P2388 | agency → public office | structural escalation to "the head" (NY FOIL appeals go to the head of the entity) | **this note** |
| *appointed by* | item | P7 → wd:P748 | public office → public office or body | oversight and appointment paths (a post appointed by the Governor) | **this note** |
| *authority conferred by* | item | none exact; nearest wd:P92 *main regulatory text*, wd:P457 *foundational text* | agency, post, office type or role → statute item | ties a body or post to the section that gives it the power. Qualifiers: `P22 citation` = the conferring words; *power* (string: `decide appeal`, `extend time`, `deny licence`) | **this note** |
| *escalates to* | item | – | step or role → role, body, post or court | statutory escalation. Qualifiers: `P13 references` → the statute; `P18 condition` → the decision or outcome that triggers it; *time limit* (quantity, days; the old `time_limit` proposal in `publish/wikibase.py:36`) | **this note** |
| *defers to* | item | – | step or role → role, body, post or court | referral, forwarding or concurrence ("immediately forward appeal and determination to Committee"), with the same qualifiers | **this note** |
| *review status* | item → *reviewed*, *agreed* or *draft* items | – | process, step, role | today drafts are marked only in description text (357 items), so authority queries cannot filter them reliably | **this note** |
| *reference type* | item | P3831-style | qualifier on statute → statute `P13` | authority, procedure, prerequisite_process, …, from `xref.ROLES` | links-codebase-map §4.1 |
| *described at URL* | url | P973 | agency → its Govdirectory page | link users to Govdirectory without copying it | entities-contacts §1.7 |

**Deliberately not added:**

* *parent organization*. Keep `P9 part of` for agency → parent, as [entities-contacts.md](entities-contacts.md)
  already decided, so there is one hierarchy property. Its P7 points at wd:P361. The loader can write the
  P749-sense here, because it only ever writes organisational parents on agency items.
* *organization directed by* (wd:P2389). SPARQL traverses *head position* both ways, and a second direction would
  only drift.
* *position holder* / *position held* (wd:P1308 / wd:P39). See §4.5.

**Rules that carry over.**

* Every claim, qualifier and reference is regenerated from lexflow's database on each load (`clear`).
* Agency, post and office-type keys are not model-scoped, so `retire_drafts` leaves them alone.
* `escalates to` and `defers to` on steps are model-scoped. `retire_drafts` already covers `lexflow:step:` keys,
  so a superseded draft's escalation claims disappear with the rest of its statements.
* Keys follow D2/D3 of [entities-contacts.md](entities-contacts.md). Examples: `lexflow:agency:ny:department_of_state`,
  `lexflow:agency:ny:committee_on_open_government`, `lexflow:office-type:ny:head_of_foil_entity`. A new kind for
  posts: `lexflow:office:<scope>:<slug>`, e.g. `lexflow:office:ca:secretary_of_state`.

### 4.3 Worked example: a New York FOIL appeal (`curated/ny/records.json`, N.Y. Pub. Off. Law § 89)

The reviewed model has five actors and these escalation steps:

* `respond`: the agency grants or denies;
* `appeal`: the requester appeals in writing to the entity's head;
* `decide_appeal`: the appeals officer decides;
* `forward_to_committee`: the agency forwards the appeal and the determination to the Committee on Open
  Government;
* `seek_review`: the requester seeks Article 78 review in court.

| Model element | Today on the wiki | With §4.2 |
|---|---|---|
| actor `agency`, "Agency or entity subject to FOIL" | role item, P5 Q23, P15 Q58 | *played by* → office type "entity subject to FOIL" (generic; the concrete agency is chosen when the answer is made) |
| actor `appeals_officer`, "Head, chief executive or governing body (or designee)" | role item | *played by* → office type "head of the entity holding the record" (P6 → *public office*). For a concrete agency it resolves through that agency's *head position*. For NY's Department of State (Q17110658, on Govdirectory) that post would be the Secretary of State of New York |
| step `appeal` | P17 → requester | + *escalates to* → the appeals-officer role; `P13` → § 89 statute item; `P18 condition` → the `respond` outcome "denied" |
| step `forward_to_committee` | P17 → agency | + *defers to* → `lexflow:agency:ny:committee_on_open_government`. That is a **new local item with no Wikidata QID** (Wikidata has none; beware the NGO false friend Q131572971), with `P9 part of` → the NY Department of State item, which carries *Wikidata item ID* Q17110658 |
| step `seek_review` | P17 → requester | + *escalates to* → the court role, *played by* → NY Supreme Court (court class, *Wikidata item ID* Q3001111; not on Govdirectory) |

**What Govdirectory contributes here:** one of the three escalation targets, and only as a parent body. Lexipedia
must hold the Committee item and the office types itself. Wikidata supplies the identity of the Department of
State and the Supreme Court.

### 4.4 Query sketch: local structure, Wikidata detail at query time

Once *played by*, *Wikidata item ID* (with the P1921 mapping) and *review status* exist, this query lists the
bearer of every reviewed step, the body behind that bearer, and that body's head post and parent from Wikidata,
without copying either. Property names in angle brackets stand for P-ids that do not exist yet.

```sparql
PREFIX lx:   <https://lexipedia.wikibase.cloud/entity/>
PREFIX lxt:  <https://lexipedia.wikibase.cloud/prop/direct/>
PREFIX lxn:  <https://lexipedia.wikibase.cloud/prop/direct-normalized/>
PREFIX wdt:  <http://www.wikidata.org/prop/direct/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?process ?step ?role ?body ?wd ?headLabel ?parentLabel WHERE {
  ?process lxt:P5 lx:Q7 ; lxt:P15 lx:Q58 ; lxt:P10 ?step ;      # New York processes
           lxt:<review status> lx:<reviewed> .
  ?step lxt:P17 ?role .
  ?role lxt:<played by> ?body .
  OPTIONAL { ?body lxn:<Wikidata item ID> ?wd .
    SERVICE <https://query.wikidata.org/sparql> {
      OPTIONAL { ?wd wdt:P2388 ?head . ?head rdfs:label ?headLabel FILTER(LANG(?headLabel) = "en") }
      OPTIONAL { ?wd wdt:P749 ?parent . ?parent rdfs:label ?parentLabel FILTER(LANG(?parentLabel) = "en") } } }
}
```

Two rules apply:

* **Local claims win.** Lexipedia's own *head position* and *part of* claims take precedence over Wikidata's,
  which are often missing (§3.2). The query reads Wikidata only for what Lexipedia lacks.
* **Escalation chains are walked locally.** A chain such as
  `?x (lxt:P9|lxt:<head position>|lxt:<appointed by>)* ?top` runs locally with SPARQL property paths, so it does
  not depend on WDQS being up.

### 4.5 People: posts, not persons

* **No person items.** Lexipedia holds no item for a person and no *position holder* / *position held* statements.
  A post is an item: *Secretary of State of California*, with its Wikidata item ID Q7024182, *applies to
  jurisdiction* California, and *appointed by* the Governor's post.
* **Current holders are looked up when a page needs them.** If a page must show who holds a post now, it is read
  from Wikidata's `P1308` with its `P580`/`P582` dates at page-build time, through `SERVICE` or a direct WDQS
  read, and shown only as "holder of this public office, per Wikidata, since <start date>". Nothing about the
  person is stored, and no contact details are ever shown.
* **No person-valued "led by".** Govdirectory's person-valued statements (P488, P169, P1037, P3975) are never read
  into Lexipedia.
* **A short local rule for the review committee.** A page such as `Project:People` should say that Lexipedia
  models public offices, not people, and holds no personal data. The hosting policy asks for "appropriate local
  rules" whenever living people could appear. Writing it is a wiki edit for the user to approve.

---

## 5. What to do, and who does it

| # | Step | Kind | Who |
|---|---|---|---|
| 1 | Check the dashboard's Review tab. If the instance is temporary, submit it for review within the 3-month window. Mention the staging-for-Wikidata use and the public lexipedia.xyz audience | dashboard | user |
| 2 | Write `Project:Copyrights` (structured data CC0; text under a reuse licence). Optionally write `Project:About` and the people rule (§4.5) | wiki edit | user, or lexflow after a go-ahead |
| 3 | Create *formatter URL* and *formatter URI for RDF resource*. Map them to wd:P1630 and wd:P1921, and map P5 → P31 and P6 → P279, in Dashboard → Features. Allow 24 h before identifiers turn clickable | wiki edit + dashboard | user |
| 4 | Create the classes and properties in §4.2 (12 properties, 2 qualifier properties, 5 classes, 3 review-status items) | wiki edit | lexflow after a go-ahead (a dry-run list first) |
| 5 | Add *Wikidata item ID* to the 52 state items and to Q75–Q77. This is 55 statements; the QIDs come from `states.py` and the `governments` table | loader | lexflow, after 3–4 |
| 6 | `Loader.agencies()` / `offices()`: Tier A items from the `agencies` and `office_types` tables of [entities-contacts.md](entities-contacts.md), plus *played by* on roles and *review status* on processes, steps and roles | code (new module) + load | lexflow; publishing stays user-triggered after a dry run |
| 7 | *escalates to* / *defers to* from reviewed models, with the statute and condition qualifiers | code + load | lexflow, once the authority design fixes the vocabulary |
| 8 | Optional: put the loader's account in the `bot` group, so loads stop flooding Recent changes. The `bot` group lacks `noratelimit`; the account keeps its sysop exemption | wiki rights | user (bureaucrat) |
| 9 | Optional: nominate `https://lexipedia.wikibase.cloud/query/sparql` for WDQS's allowlist, only if Wikidata-side queries ever need Lexipedia data | outside request | user |

None of steps 1–9 was taken in this survey.

---

## 6. Open questions

1. **Generic actors.** Should "head of the entity" be an *office type* (P6 → *public office*) resolved through
   each agency's *head position*, as proposed here, or a property path that the query computes with no item at
   all? The item form is reviewable and can carry *authority conferred by*. The path form needs no item.
2. **Where escalation lives.** Steps (per process, model-scoped, retired with drafts), roles (reused across
   steps), or both? NY FOIL needs it on steps, because the same agency role both decides and forwards.
3. **Tier B trigger.** Which process would justify loading the 1,140 US Govdirectory bodies: an NC licensing
   model, a federal process, or none until Govdirectory covers a corpus state?
4. **Raising the 400-character string limit** (it is tied to the monolingual-text setting; see §2.6), so that
   *authority conferred by* can quote whole conferring clauses. Or keep 400 and link to the DokuWiki page instead?
5. **WDQS allowlist nomination.** Is there any Wikidata-side consumer that would need to query Lexipedia, or is
   outbound federation enough?
