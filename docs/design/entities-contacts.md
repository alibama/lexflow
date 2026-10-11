# Addressable entities and up-to-date contacts: the plan

Status: plan, 2026-10-10. Revised the same day to fix every finding of the adversarial review in
[verify-entities.md](verify-entities.md). Every `file:line` below was re-checked against the code after the review.
Nothing described here is built yet.

This plan turns the read-only surveys below into one design:

| Input | What it gave |
|---|---|
| [entities-sources.md](entities-sources.md) | What Govdirectory and Wikidata can supply, and how far their provenance can be trusted |
| [entities-codebase.md](entities-codebase.md) | How lexflow stores governments and contacts today, and the extension points. Some of its line numbers have since drifted; this plan uses the current ones. |
| `fixtures/entities/agencies.json` | 144 bodies named in models, AskBench references and statute text, matched to Wikidata and Govdirectory |
| `fixtures/entities/contacts_pilot.json` (made by `scripts/contacts_check.py`) | A polite, read-only freshness check of 86 contacts in 49 governments |
| [links-codebase-map.md](links-codebase-map.md), `lexflow/law/terms.py` | The parallel design for cross-references, defined terms, roles and process links, with its key formats |
| [verify-entities.md](verify-entities.md) | The adversarial review of the first draft of this plan |

Scope rules followed throughout:

* The plan covers organisations and official office channels only.
* It names no individual and reproduces no email address or phone number. The mailbox examples in 5.2 are local
  parts only, and the personal-looking ones are made up.

---

## 0. Key decisions

| # | Decision | Why |
|---|---|---|
| D1 | **One chain from law to a working contact.** A model actor is a *role* (per process). A role is an instance of a *concept* or *term*, which comes from the links workflow. A role is *played by* an *agency*, an *office type* or a *government* in a jurisdiction. That entity *has contacts*, and each contact carries its own provenance. | Today the chain breaks at the first link: 364 actors are unlinked strings (`compile.py:255`). Agencies are flattened into cities' contact rows. |
| D2 | **One key spelling everywhere: the Wikibase P25 key.** Examples: `lexflow:agency:<scope>:<slug>`, `lexflow:office-type:<state>:<slug>`, `lexflow:gov:<gid>`, plus the existing `lexflow:role:`, `lexflow:statute:`, `lexflow:term:` and `lexflow:concept:` keys. Agency contacts store this key in `contacts.gov_id`. | The links map warns against second spellings (`fl.business` vs `fl-business`, `provision:` vs `lexflow:statute:`). A `lexflow:agency:` key cannot be mistaken for a 14-digit Census GID. |
| D3 | **lexflow mints the keys. A Wikidata QID is a crosswalk column, never the key.** | Of the 98 specific bodies, 15 have no item and 14 match only a parent body. 5 of the exact matches are position items, not offices. Items also get merged and redirected. |
| D4 | **Generic mentions resolve to an *office type*, and then to an instance when the answer is made.** Examples: "the clerk of the circuit court", "the board", "a court", "the sheriff". | 46 of the 144 fixture entries are generic. Their body depends on the county, the profession or the record. |
| D5 | **Private-party roles are never resolved to a person or company.** Registered agent, incorporator, organizer and requester are roles. They link to an explicit `lexflow:private-party` marker, so the resolver counts them as resolved and never expects a contact for them. | Privacy, and the scope of the product. |
| D6 | **Provenance lives on the contact row. Check state lives in its own synced table, `contact_status`, keyed by the normalised contact.** A check records two separate dates, `checked_at` and `verified_at`. `updated_at` stays a write stamp only. | Today no contact has a checked date, and rerunning the Census step makes 2022 data look a few hours old. Turso sync replaces whole rows by `updated_at`, so check columns on `contacts` would be lost to another machine's reload (2.1). |
| D7 | **Choosing among stored values is automatic. Adding or replacing a value needs a person.** The recheck job changes status, dates and evidence, and hides bad values. It never stores a new website, mailbox or phone; a new value goes to a review queue. | A redirect target or a scraped number can be wrong or hostile. The pilot found 3 hijacked domains. |
| D8 | **Only checked websites are shown.** From phase 1, before any checker exists, unchecked, broken and quarantined websites and pages are hidden from every user-facing surface. Quarantine takes effect on first sight, but it needs two signals (3.4). | The pilot found 43 % of verifiable websites stale (±14 points). 3 of its 55 sampled websites (Androscoggin County ME, the City of Auburn ME and the Village of Lowellville OH) now serve gambling or spam pages. |
| D9 | **Rechecks are spread out: one budgeted daily run of a `recheck` job step.** It picks rows by tier and due date: weekly for contacts in published answers, every 14 days for contacts shown in answers, monthly for the rest. | A full pass is about 16,200 URLs. Spread over a month, with tiers 0 and 1, that is about 650 URLs a day: about 1,350 page GETs plus up to about 650 robots.txt GETs, roughly 5 minutes with 8 workers. |
| D10 | **Wikidata is a lead and a corroborating source, not ground truth for freshness.** | Wikidata still had the old domain for 5 of the 6 moved governments, and 4 % of P856 statements have a retrieved date. |
| D11 | **Nothing goes upstream automatically.** lexflow drafts Wikidata suggestions with references. A person reviews each one and applies it under their own account. | Wikidata bot policy, and Govdirectory's rule against AI-generated contributions. Corrections reach Govdirectory only through Wikidata. |
| D12 | **The DB is the source of truth. The dashboard, DokuWiki and Wikibase are projections of it.** Publishing stays user-triggered, with a dry run first. | The publishing rules in memory. Also, the Wikibase loader replaces statements wholesale (`clear`), so every claim must be regenerated from the DB on each load. |
| D13 | **New code goes in new modules (`lexflow/entities/`) and new test files.** Changes to `lexflow/ask/*`, `extract/*`, `FActor` and the facts JSON wait until AskBench finishes, or are not needed at all. | The benchmark freeze. Links live in `entity_links`, not in the extraction schema. |
| D14 | **Privacy outranks the benchmark freeze.** Personal data found in curated files, the DB or wiki pages is removed as soon as it is found. The wiki change is published after a dry run. | On 2026-10-10 two staff mailboxes and staff names had to be removed from the curated Baltimore file, the DB and two live wiki pages (5.2). |

---

## 1. Entity model

### 1.1 The chain

```
statute section ──mentions──▶ agency / office type ◀──played-by── role ──instance of──▶ concept / term
 (lexflow:statute:…,                │      ▲                (lexflow:role:     (lexflow:concept:…,
  act_id from the xref work)        │      │                 st:q:actor)        lexflow:term:st:ref:slug)
                                    │   instance-of                ▲
                              has contacts │                   bearer (P17)
                                    ▼      │                       │
                      contacts (provenance) office type      process step
                       + contact_status
                                    ▲
government (lexflow:gov:<gid>) ─────┘   agency ──part-of──▶ agency | government
                                        agency ──serves(question)──▶ government | jurisdiction
```

**Worked example (Florida business formation).**

* *The filing office.* The FL business model's actor `department` (Fla. Stat. § 605.0210) becomes the role
  `lexflow:role:fl:business:department` (Wikibase Q776).
  * It is `played-by` `lexflow:agency:fl:division_of_corporations`, which is Wikidata Q107179384, the
    best-modelled item in the survey.
  * That agency is `part-of` `lexflow:agency:fl:department_of_state` (Q11969252).
  * The Division's office mailbox and main line come from Wikidata. Both are referenced to the official contact
    page, retrieved 2024-04-11. They enter lexflow with that date as their `vintage` and no status row, so they
    are `unchecked`. They become `ok` only when lexflow's own check finds them on that page. The mailbox's local
    part is two role words, so it passes the privacy guard (5.2).
* *The founder.* The model's actor `organizer`, "Authorized representative (founder)", signs an LLC's articles
  of organization (Fla. Stat. § 605.0203(1)(b)). It is the role Q775, `lexflow:role:fl:business:organizer`.
  * Its term is `lexflow:term:fl:605.0201:authorized-representative`. Section 605.0201(1) says who may act as an
    authorized representative to form an LLC. The links workflow maps that term to the concept
    `lexflow:concept:organizer`, under a lay `lexflow:concept:founder` concept.
  * It is not the incorporator. `lexflow:concept:incorporator` belongs to the corporation route in chapter 607.
    Section 607.0201 ("Incorporators", Wikibase Q168) says who may act as incorporator; it is not a definitions
    section, and chapter 607's definitions are in § 607.01401. Incorporator and organizer are sibling concepts
    under the founder concept.
  * The role is `played-by` `lexflow:private-party`, so no contact is ever looked for.

### 1.2 Entity kinds and keys

| Kind | Canonical key (P25) | Stored in | Seed | Count to start |
|---|---|---|---|---|
| Jurisdiction | `lexflow:jurisdiction:<st>` | exists (Wikibase only) | `states.py` | 52 |
| Government | `lexflow:gov:<gid>`; the DB keeps the bare GID | `governments` (exists) | Census GUS 2022 | 38,640 |
| Agency (department, board, commission, court, clerk's office, ombudsman, council, division) | `lexflow:agency:<scope>:<slug>`. `scope` is a state code, `us` for federal bodies, or a GID for a government's own office. | `agencies` (new) | `agencies.json` (98 specific bodies), `caselaw.COURTS` (98 courts), agency contacts now filed under cities (Virginia FOIA Council, Maryland Public Access Ombudsman, DC OTR, DLCP and DOB) | about 200 |
| Office type (one body per county, profession or record) | `lexflow:office-type:<st>:<slug>`, e.g. `lexflow:office-type:fl:clerk_of_circuit_court` | `office_types` (new) | the 46 generic entries in `agencies.json`, with a `class_qid` where the fixture gives one (see below) | about 50 |
| Office instance | `lexflow:agency:<gid>:<office-type slug>` (an agency with `office_type_key` set) | `agencies` | minted lazily, when a contact is first recorded for it | 0 |
| Role (per process) | `lexflow:role:<st>:<q>:<actor>` | exists (`wikibase_items`) | `facts.actors` | 199 Wikibase items |
| Concept, term | `lexflow:concept:<slug>`, `lexflow:term:<st>:<ref>:<slug>` | links workflow (`concept_key` at `law/terms.py:676`, `term_key` at `:662`) | definitions, headings | (theirs) |
| Statute | `lexflow:statute:<st>:<ref>` plus the canonical `act_id` key the links map proposes | exists | | 496 |
| Private party | `lexflow:private-party` (a single marker, not an entity) | constant | | 1 |

The fixture gives 8 class QIDs for office types:

* six court systems: Q7643515 (superior courts of California), Q5461271 (Florida Circuit Courts), Q17021934
  (Illinois circuit courts), Q6781282 (Maryland Circuit Courts), Q7707643 (Texas District Courts) and Q16960472
  (Virginia Circuit Court);
* Q5152849, Commissioner of the Revenue, which has no P31;
* Q5153671, Commonwealth's Attorney. It is a **position** item (P31 Q4164871), so by rule 5.4 it is kept only as
  an identity hint, never as `class_qid`.

Rules for keys:

* **Slug.** Lower-case ASCII words joined by `_`, at most 48 characters, with the leading state name and "the"
  dropped: `state_corporation_commission`, `division_of_corporations`.
* **Stable.** A key is minted once and never changes.
  * A rename updates `name` and adds the old name to `aliases`. For example, the California Prison Industry
    Authority is now the California Correctional Training and Rehabilitation Authority, and its key stays.
  * A body that is abolished or merged keeps its key and gets `status='abolished'` and a `successor-of` link. For
    example, the DC Board of Parole links to the US Parole Commission.
* **Identity when seeding.** Every seed run matches before it mints:
  1. by QID: an agency whose `wikidata` is the candidate's QID, after following Wikidata redirects;
  2. else by name or alias: an exact normalised match on `name` or any `aliases` entry, in the same `state` and
     `scope`;
  3. else a new key from the slug. If that key already belongs to a different body (two names can truncate to
     the same 48-character slug), the new key gets a suffix: `_2`, `_3` and so on.

  A candidate that matches two existing agencies goes to review and is not minted. A changed Wikidata label
  becomes an alias; it never mints a second key.
* **No QIDs in keys.** A QID never appears in a key.
* **Contacts.** A contact's identity stays its primary key `(owner, question, kind, value)`. The owner is a GID
  or an agency key. A changed value is a new row. Each row also stores `norm_value`, the normalised value
  (2.1), which keys its check state.

### 1.3 Tables

These three tables are synced, as is `contact_status` (2.1). Each has `state`, `updated_at` and `origin`, and an
entry in `SYNCED` (`db.py:339`). Federal bodies use `state='us'`:

* Sync filters by state (`turso._state_filter`, `turso.py:159-162`), and the dashboard pulls with a state list
  (`api/app.py:220`). The filter becomes `AND (state IN (…) OR state='us')`. Without that change, federal rows
  never reach a machine that pulls by state.

```sql
CREATE TABLE IF NOT EXISTS agencies (
  key TEXT PRIMARY KEY,            -- lexflow:agency:va:state_corporation_commission
  state TEXT NOT NULL,             -- va | … | us
  scope TEXT NOT NULL,             -- va | us | <gid> (an office of one government)
  name TEXT NOT NULL,
  kind TEXT NOT NULL,              -- department | board | commission | court | clerk | office | ombudsman | council | division
  level TEXT NOT NULL,             -- federal | state | regional | local
  gov_id TEXT,                     -- the government a local office belongs to
  parent_key TEXT,                 -- a division inside a department (part-of is also an entity_link)
  office_type_key TEXT,            -- set for an instance of an office type
  aliases TEXT,                    -- JSON: names statutes and models use ("the Commission")
  wikidata TEXT, wikidata_match TEXT,   -- QID; exact | parent | position (mapped from agencies.json, 1.6)
  courtlistener TEXT,              -- court id, for courts
  govdirectory_url TEXT,           -- only when the QID is on a published Govdirectory list
  status TEXT DEFAULT 'active',    -- active | abolished | merged
  source TEXT, source_url TEXT, checked_at TEXT,
  updated_at TEXT NOT NULL, origin TEXT
);

CREATE TABLE IF NOT EXISTS office_types (
  key TEXT PRIMARY KEY,            -- lexflow:office-type:fl:clerk_of_circuit_court
  state TEXT NOT NULL,
  name TEXT NOT NULL,
  kind TEXT NOT NULL,              -- court | clerk | board | sheriff | prosecutor | probation | public-body | local-government
  instance_scope TEXT NOT NULL,    -- county | city | judicial_circuit | profession | record_holder | venue
  parent_hint TEXT,                -- an agency key whose channels serve when the instance is unknown (CA boards -> DCA)
  class_qid TEXT,                  -- a Wikidata system or class item, when there is one (never a position)
  aliases TEXT,
  updated_at TEXT NOT NULL, origin TEXT
);

CREATE TABLE IF NOT EXISTS entity_links (
  subject TEXT NOT NULL,           -- a role, statute, agency or government key
  relation TEXT NOT NULL,          -- see 1.4
  object TEXT NOT NULL,            -- an agency, office type, government or jurisdiction key, or lexflow:private-party
  question TEXT NOT NULL DEFAULT '',
  state TEXT NOT NULL,
  context TEXT,                    -- JSON: how a generic mention resolves (1.5)
  method TEXT,                     -- curated | alias | defined-term | wikidata | claude-reviewed | reviewer
  score REAL,
  status TEXT DEFAULT 'proposed',  -- proposed | accepted | rejected
  act_id TEXT, section TEXT, start INTEGER, "end" INTEGER, quote TEXT,   -- the words that make the link (at most 400 characters)
  source TEXT, checked_at TEXT,
  updated_at TEXT NOT NULL, origin TEXT,
  PRIMARY KEY (subject, relation, object, question)
);
```

**Re-runs keep decisions.** The agency seed and the `mentions` finder write with `db.upsert(keep=…)` (2.1):

* in `entity_links`, a re-run never overwrites a reviewer's `status`, `method` or `score`;
* in `agencies`, it never overwrites `status`, and `aliases` is merged (a union), never replaced.

Agency contacts go into `contacts`, with the agency key in `gov_id`. This avoids a table rebuild. Every place
that assumes `gov_id` is a government needs a guard on `gov_id LIKE 'lexflow:agency:%'`:

* `api/app.py:310-315`, so that a website match on an agency does not 404 the lookup. The same query also skips
  websites that are hidden (2.2), so the browser plugin never names a government for a hijacked domain;
* `contacts.py:106-110`, so that `import_csv` accepts agency keys;
* `steps.py:101` and `:109`, so that the checklist counts exclude agencies;
* `crawl.py:95-99`, to add agency sites to the scan.

**Agency contacts that move out of city rows.** The curated JSON stays frozen, so `places.load_local`
(`places.py:100-105`) would write these contacts back under the city on every run. Instead:

* the loader maps known agency contacts to their agency key, through a small curated map from label or value to
  agency key, and writes them under the agency;
* the old city rows are not deleted. They get status `retired` in `contact_status`, which no loader overwrites.

The codebase doc proposed `a:` ids and an `is` relation. Both are replaced here by the canonical key and by
`played-by` (D2).

### 1.4 Link relations

| Relation | Subject → object | Example | How it is made |
|---|---|---|---|
| `played-by` | role → agency, office type, government or `lexflow:private-party` | `role:va:business:commission` → `agency:va:state_corporation_commission` | alias match on `facts.actors` (name, kind, source quote), then review. Links from `single` models stay `proposed`, by the publishing rule. |
| `mentions` | statute → agency or office type | `statute:fl:607.0201` → `agency:fl:department_of_state` | an alias finder over model sections and AskBench gold sections, modelled on `text/citations.py`. It reuses the xref module's section keys (`act_id`) and stores offsets. |
| `instance-of` | agency → office type | Leon County's clerk → `office-type:fl:clerk_of_circuit_court` | at minting |
| `part-of` | agency → agency or government | Division of Corporations → Department of State. A county clerk → that county. | Wikidata P749 for exact matches, the fixture's `units`, and curated data |
| `serves` | agency → government or `lexflow:jurisdiction:<st>`, for one question | Virginia FOIA Council `serves(records)` → `jurisdiction:va`, one row for all 322 governments | curated |
| `successor-of` | agency → agency | US Parole Commission → DC Board of Parole | Wikidata P1366 or P576, or the statute; always reviewed |

### 1.5 Resolving a generic mention, with jurisdiction context

`lexflow/entities/resolve.py` provides `resolve(key_or_actor, state, question, place=None, facts=None)`. It
returns an agency, an office type, a government or the private-party marker, together with the rule that fired.
That rule is stored in `entity_links.context`. The resolver tries these in order:

1. **A defined term in scope.** The terms module gives each definition a `scope_unit`. If a definition such as
   "'Board' means …" covers the citing section, the mention is that body.
2. **A full name earlier in the same section or model.** For example, "the State Corporation Commission … the
   Commission".
3. **The question's default player.**
   * Records: "the public body" or "the custodian" is the government the user picked, and its records contacts
     are used.
   * Business: the state filing office.
4. **An office type with an instance chosen when the answer is made.** `instance_scope` says what picks the
   instance: the county of the user's place, the venue, or the profession.
5. **Otherwise, unresolved.** The mention is shown as a role, for example "the board for your profession". It
   is shown with the channels of its office type's `parent_hint` body, labelled as that body's. This is the same
   display rule as for a body whose only Wikidata match is its parent (in `agencies.json`,
   `match: "parent body only"` with `contact_scope: "parent"`; here, `wikidata_match='parent'`).

| Text | State | Resolves to | Context recorded |
|---|---|---|---|
| "the clerk of the circuit court" | fl | `office-type:fl:clerk_of_circuit_court`, then the instance for the place's county | `{"resolve_by":"county_of_place"}` |
| "the board" (licence denial) | dc | `office-type:dc:occupational_licensing_board`. Non-health boards are staffed by DLCP, health boards by DC Health. | `{"resolve_by":"profession","parent_hint":"agency:dc:department_of_licensing_and_consumer_protection"}` |
| "Secretary of State" | ca | `agency:ca:secretary_of_state` (the office, not the office-holder position Q7024182) | `{"rule":"alias"}` |
| "public body", "custodian" | any | the chosen government | `{"resolve_by":"record_holder"}` |
| "registered agent", "incorporator", "organizer", "requester" | any | `lexflow:private-party` | `{"rule":"concept-category:role/private"}` |

### 1.6 Wikidata and Govdirectory links

* **QIDs.** `agencies.wikidata` holds the QID. The seed maps the fixture's `match` and `item_kind` fields like
  this:

  | `agencies.json` | `wikidata_match` |
  |---|---|
  | `match: "exact"`, `item_kind` organisation, court or untyped | `exact` |
  | `match: "exact"`, `item_kind: "position"` | `position` |
  | `match: "parent body only"` (the QID is the parent's) | `parent` |
  | `match: "none"` | none; `wikidata` stays empty |

  * A `parent` QID never supplies the agency's own contacts. They are shown as the parent body's.
  * A `position` item (for example the Illinois Secretary of State) is used for the office's identity only.
    Office-holder claims are dropped when a response is parsed (5.4).
* **Reading Wikidata.** Contacts are read with `p:`/`ps:` patterns: rank, `P580`/`P582` qualifiers, references
  (`P854`, `P813`, `P248`) and the statement GUID.
  * Deprecated values and values with an end time (`P582`) are dropped. The pilot's `wikidata_p856`
    (`contacts_check.py:765-812`) skips only deprecated values, so it would count Q107179384's sunbiz.org URL
    (normal rank, ended 2016) as current. The recheck does not copy that.
  * A value whose only reference is `P143` counts as unsourced.
  * This replaces the truthy-only reads at `contacts.py:31-45` for agencies.
  * **maxlag.** Every API read sends `maxlag=5`. On a lag error, the reader waits as `Retry-After` says, at most
    twice, and then defers the batch to the next run. The pilot drops `maxlag` on its third try
    (`contacts_check.py:774`); the recheck never does. Lag on the query service counts towards maxlag, so on a
    lagged day the batch simply waits.
* **Govdirectory.** Set `govdirectory_url` (`https://www.govdirectory.org/<slug>/<QID>/`) only when the QID is on
  a published list.
  * In the US that means federal entries, New York and North Carolina only. In the fixture that is 6 bodies
    and 1 parent.
  * The lists are refreshed monthly from the 1.9 MB `sitemap.xml`, which is one GET.
  * Govdirectory adds no data beyond Wikidata, so it is a link for users, not a source.

### 1.7 Wikibase items and properties (lexipedia.wikibase.cloud)

Existing properties are reused where they fit: P5, P6, P8 (exact match: the Wikidata URL), P9 part of, P15
jurisdiction, P17 bearer, P22, P25.

**New classes:**

* government agency (P8 → wd:Q327333);
* court (wd:Q41487);
* county clerk's office (P8 → wd:Q139489412, which is "county clerk's office" and has only 8 instances). A
  broader clerk's office class, which also covers clerks of circuit courts, gets no P8;
* office type, modelled as a P6 subclass of agency or court, which is the class form the links map recommends.

**New properties.** Creating them is a wiki write, so it waits for the user's go-ahead; the links map asks the
same question.

| Property | Datatype | ≡ Wikidata | Used on |
|---|---|---|---|
| played by | item | – (no direct equivalent) | role → agency or office type |
| official website | url | P856 | agency, government |
| email address | url (mailto:) | P968 | agency (office mailboxes only) |
| phone number | string | P1329 | agency (main lines only) |
| contact page URL | url | P11266 | agency |
| reference URL | url | P854 | references on the four contact properties |
| retrieved | time | P813 | references (= lexflow `verified_at`) |
| determination method | item | P459 | references (HTTP check, found on official page, curated) |
| start time / end time | time | P580 / P582 | qualifiers on retired values |
| reason for deprecated rank | item | P2241 | deprecated values (link rot, hijacked domain) |
| described at URL | url | P973 | agency → its Govdirectory page |
| names body (optional, later) | item | – | statute → agency, for `mentions` |

Item shapes:

* **Agency** (`lexflow:agency:…`):
  * P5 → its office type or class;
  * P15 → jurisdiction; P9 → parent agency or government;
  * P8 → Wikidata, **only** where `wikidata_match='exact'` and the item is an organisation or a court. A parent
    QID goes on the parent agency's own item. A position QID is never an exact match for an office;
  * P973 → Govdirectory, when listed;
  * contact statements, each with a reference (reference URL, retrieved, determination method). The primary
    `ok` value has preferred rank. `moved` and `broken` values are deprecated with P2241.
* **Role items** gain P5 → concept (links workflow) and "played by", with the jurisdiction already on P15.

The loader adds `Loader.agencies()` after `jurisdictions()` (`wikibase_lexipedia.py:242`). Agency keys are not
model-scoped, so `retire_drafts` (`:209`) leaves them alone. Because `clear` replaces statements, every claim is
regenerated from the DB on each load.

---

## 2. Contacts with provenance

### 2.1 Provenance on `contacts`, check state in `contact_status`

**New columns on `contacts`.** Loaders write these.

| Column | Meaning |
|---|---|
| `norm_value` | the normalised value, which keys the check state. Websites and pages: the host without `www.`, the path without a trailing slash, and the query; the scheme and fragment are dropped. Emails: the lower-cased address. Phones: the 10 digits. Postal: upper-cased, with punctuation and spacing collapsed. |
| `source_url` | the page or record the value was read from (the Census file, the Wikidata entity, the official page) |
| `retrieved_at` | when lexflow read the value from that source |
| `vintage` | the source's own date: `2022` for Census GUS, a statement's P813, a curated `researched` date |
| `first_seen` | first time lexflow stored this value; kept on conflict |

They are added through `MIGRATIONS` (`db.py:353`) locally. On Turso:

* `turso.ensure_schema` (`turso.py:139-140`) sends only `CREATE … IF NOT EXISTS` statements today, and
  `Turso.pipeline` raises on the first failing statement (`turso.py:111-113`). One failing `ALTER` in that batch
  would abort every push.
* So each `ALTER TABLE contacts ADD COLUMN …` goes to Turso in its own `pipeline` call. A "duplicate column
  name" error is caught and ignored. Any other error stops the sync with its message.
* `pull` (`turso.py:212`) asks the remote table for every local column (`:226-227`), but only `push` calls
  `ensure_schema` today (`:177`). `pull` must run the same schema step first.

**The `contact_status` table.** It is synced, with an entry in `SYNCED`:
`"contact_status": ("owner", "question", "kind", "norm_value")`. Only checkers (including the one-off import of
the pilot's results in phase 1), reviewers and the curated loader (2.4) write it.

```sql
CREATE TABLE IF NOT EXISTS contact_status (
  owner TEXT NOT NULL,             -- contacts.gov_id: a GID or an agency key
  question TEXT NOT NULL,
  kind TEXT NOT NULL,
  norm_value TEXT NOT NULL,        -- contacts.norm_value
  state TEXT NOT NULL,
  status TEXT NOT NULL,            -- ok | moved | unverifiable | broken | quarantined | retired (2.2); no row = unchecked
  reason TEXT,                     -- the pilot's reasons: dns_nxdomain, http_404, hijacked_spam, domain_changed, blocked_http_403 …
  checked_at TEXT NOT NULL,        -- the last check, whatever its result
  verified_at TEXT,                -- the last check that confirmed the value (status ok): the "last verified" date users see
  method TEXT,                     -- how verified_at was earned: http | page-contains | dns-mx | wikidata-ref | curated | reviewer
  verified_by TEXT,                -- machine | two-agent | reviewer: a role, never a name
  evidence TEXT,                   -- small JSON: final URL, hop chain, title (at most 200 characters), MX hosts, where a value was found. Never page bodies.
  fails INTEGER NOT NULL DEFAULT 0,  -- consecutive failed checks
  next_check_at TEXT, tier INTEGER,  -- the schedule (3.2)
  display_changed_at TEXT,         -- when the value last went from shown to hidden, or back
  updated_at TEXT NOT NULL, origin TEXT,
  PRIMARY KEY (owner, question, kind, norm_value)
);
CREATE INDEX IF NOT EXISTS contact_status_due ON contact_status(next_check_at);
```

Why a separate table:

* **Sync is whole-row last-writer-wins.** `push` selects rows by `updated_at`, and the remote upsert applies
  `WHERE excluded.updated_at >= …` (`turso.py:165-171`). `pull` calls `db.upsert(newer_only=True)`
  (`turso.py:234`, `db.py:425-426`). If check results were columns of `contacts`, a check would have to bump
  `contacts.updated_at` to sync at all. Any later write of the same row elsewhere, such as a Census reload on a
  machine that had not pulled first, would then put stale check columns back.
* **Loaders never touch check state.** Apart from the curated loader, no loader writes `contact_status`, so a
  reload cannot drop check results.
* **Newest check wins.** For this table, both sides of sync compare `checked_at` instead of `updated_at`: a
  per-table order column in `_upsert_sql` and in `db.upsert(newer_only=True)`. An older check never replaces a
  newer one, whichever machine writes last. `updated_at` stays the write time, so `push` still finds new rows.
* **One machine runs the check.** The `schedule.recheck` setting is local to each machine, and it is switched on
  for one. The merge rule keeps results consistent if a second machine runs `recheck` anyway.
* **No backfill.** A contact with no row is `unchecked`, so the 55,181 rows need no backfill. A backfill would
  not bump `updated_at` and so would not sync anyway.
* **The checklist does not go stale every day.** `st_score` (`steps.py:161-172`) marks a state "re-score" when
  any contact's `updated_at` is newer than its oldest answer. Check writes never touch `contacts.updated_at`, so
  a daily recheck no longer flags every checked state. A check that moves a value from shown to hidden, or back,
  sets `display_changed_at`, and `st_score` adds `max(display_changed_at)` per state to its inputs. A check that
  only confirms a value changes neither.

`db.upsert` gains a `keep=` option (`db.py:398-430`; the conflict clause is at `:419-428`). When a loader
rewrites an unchanged value, it keeps `first_seen`, and decision columns elsewhere (1.3). Rerunning the Census
step then no longer makes old data look fresh: the date users see is `verified_at`, which a loader never writes.

### 2.2 Status vocabulary

| Status | Meaning | User-facing surfaces | Dashboard |
|---|---|---|---|
| `unchecked` | no `contact_status` row yet (all 55,181 rows today) | websites, pages, emails and phones: **not shown**, from phase 1; postal: shown as "Census 2022" (see 8.6) | listed muted, never as a link |
| `ok` | confirmed at `verified_at` | shown with "source · checked YYYY-MM-DD". Treated as `unverifiable` once `verified_at` is more than 90 days old. | ✓ |
| `moved` | the stored address redirects to a working page on another registrable domain | the stored link is shown only when the target is an official domain (`.gov`, or the state's locality pattern such as `*.va.us`) or its page carries the owner's name or an alias. Otherwise it is hidden until a person reviews it. A proposal is opened either way. | review queue |
| `unverifiable` | bot wall, robots disallow, no URL, name absent, page fetched without TLS verification, mailbox with MX only, phone not found, or a first failure of a value that was not `ok` | shown only if the value was `ok`, or confirmed by a reviewer, within the last 90 days; else hidden | review queue for tier 0 |
| `broken` | two failures at least 20 h apart: DNS, a 4xx or 5xx that is not a bot wall, timeout, an unsafe redirect, or a parked, default or suspended page | hidden | listed |
| `quarantined` | spam or gambling content plus a second signal (3.4) | **hidden at once, everywhere**, including frozen answer snapshots and the browser-plugin lookup | alert; only a person can clear it |
| `retired` | replaced by an accepted new value, or moved to an agency owner | hidden; kept for history and Wikibase deprecation | history |

Parked domains have one rule: a parked page is `broken`, after two strikes, and never `quarantined` on its own,
because a parked domain has lapsed and is not hostile. A parked page that also carries spam is quarantined by the
spam rule, where the parked marker counts as the second signal.

### 2.3 Check log, proposals and upstream drafts

These three tables stay local, like `crawl_log`. `contact_status` is the synced one (2.1).

```sql
CREATE TABLE IF NOT EXISTS contact_checks (      -- append-only; kept 12 months
  id INTEGER PRIMARY KEY AUTOINCREMENT, run_id INTEGER,       -- jobs.id
  owner TEXT, question TEXT, kind TEXT, norm_value TEXT,
  checked_at TEXT, method TEXT, result TEXT, reason TEXT, evidence TEXT, requests INTEGER, elapsed_s REAL);

CREATE TABLE IF NOT EXISTS contact_proposals (   -- new values waiting for a person
  id INTEGER PRIMARY KEY AUTOINCREMENT, owner TEXT NOT NULL, state TEXT, question TEXT NOT NULL, kind TEXT NOT NULL,
  old_value TEXT, old_norm TEXT NOT NULL DEFAULT '', new_value TEXT NOT NULL, new_norm TEXT NOT NULL,
  source TEXT, source_url TEXT, evidence TEXT,
  found_at TEXT, seen_count INTEGER DEFAULT 1,
  status TEXT DEFAULT 'open',                    -- open | accepted | rejected | superseded
  decided_at TEXT, decided_by TEXT);             -- a role
CREATE UNIQUE INDEX IF NOT EXISTS contact_proposals_open
  ON contact_proposals(owner, question, kind, old_norm, new_norm) WHERE status = 'open';

CREATE TABLE IF NOT EXISTS upstream_suggestions (  -- section 4
  id INTEGER PRIMARY KEY AUTOINCREMENT, qid TEXT NOT NULL, property TEXT NOT NULL, action TEXT NOT NULL,
  value TEXT, value_norm TEXT NOT NULL DEFAULT '', old_value TEXT, refs TEXT, evidence TEXT,
  status TEXT DEFAULT 'draft',                   -- draft | approved | exported | applied | rejected
  created_at TEXT, decided_at TEXT, decided_by TEXT, applied_seen_at TEXT);
CREATE UNIQUE INDEX IF NOT EXISTS upstream_suggestions_live
  ON upstream_suggestions(qid, property, action, value_norm) WHERE status IN ('draft', 'approved', 'exported');
```

Re-runs do not create duplicates:

* **Proposals.** A proposal seen again is an upsert on the open index: `ON CONFLICT(owner, question, kind,
  old_norm, new_norm) WHERE status='open' DO UPDATE SET seen_count = seen_count + 1`. A target that a person
  rejected is not proposed again for 90 days.
* **Upstream drafts.** The same, on `(qid, property, action, value_norm)` while a row is a draft, approved or
  exported.
* **Shared URLs.** Each run fetches each `norm_value` once, even when several rows or owners share it, and
  writes the result to every `contact_status` row with that value. 274 governments have two or more stored
  websites, often one site stored as the Census `http://x.gov` and the Wikidata `https://www.x.gov/`. Both rows
  share one `norm_value`, so they share one check.

### 2.4 How each writer fills provenance

| Writer | `source_url` | `vintage` | Status on write |
|---|---|---|---|
| `governments.load` (`governments.py:78-85`) | the Census file URL (`:18`) | `2022` | none, so `unchecked` |
| `contacts.wikidata` (`contacts.py:64-99`) | `https://www.wikidata.org/wiki/<QID>`; the QID leaves the label | the statement's P813, if any | none; Wikidata is a source, not a check |
| `crawl.run` (`crawl.py:111-126`) | the page where the value was found | scan date | An email or phone found on the owner's home page gets `ok`, method `page-contains`, when that home page is itself `ok` and was fetched with TLS verified. Emails pass the guard first (5.2); today every `mailto:` link is stored. Page links stay `unchecked` until the recheck fetches them. Rows of that government not seen again are rechecked, not deleted. |
| `places.load_local` (`places.py:100-105`) | `c["url"]` (lost today for 35 of 36 contacts) | `researched` | `ok`, method `curated`, `verified_by='two-agent'`, for values that pass the guard and have an official `source_url`. It writes only when no newer status row exists. Known agency contacts go under their agency key, and the old city rows are `retired` (1.3). |
| `import_csv` (`contacts.py:102-119`) | optional column | optional | none; `kind=person` is refused (5) |
| agency seed (new) | the Wikidata entity, or the official page | P813 | none |

### 2.5 Precedence when sources disagree

All readers call one shared function, `entities.provenance.best(rows)`. It joins `contact_status` on
`(owner, question, kind, norm_value)` and feeds `ask/local.contacts`, `scoring` `summary.offices`,
`answers_for`, `markdown()`, `_contacts_block` and the dashboard. It picks one primary value per
`(owner, question, kind)`:

1. **Status.** The order is `ok` > `unverifiable` that was `ok` or reviewer-confirmed within 90 days > `moved`
   that passes the display rule (2.2) > `unchecked` (shown for postal only) > anything else. Anything else is
   never shown.
2. **Method strength**, strongest first:
   * curated or reviewer, with an official `source_url`;
   * `page-contains` on the owner's own verified site;
   * Wikidata with a `P854` reference on an official domain and a `P813` date;
   * live over HTTP only;
   * Census, with no check.
3. **Recency.** A newer `verified_at` wins.
4. **Official domain.** `.gov` or the state's locality pattern (`*.va.us`), with the owner's name in the page
   title, wins.
5. **Tie-break by source:** local-research > site-scan > wikidata > census.

Rules:

* **No value overwrites another.** Both stay stored, and the lower one is ranked below.
* **Two `ok` values that differ open one review item:** emails or phones that differ, or websites on different
  registrable domains (a tourism site against the government site). For example, of the 273 governments with
  both a Census and a Wikidata website, 94 differ by registrable domain. (131 differ when only the scheme and
  trailing slash are normalised, and 100 when `www.` is also ignored; those are the same site.)
* **Wikidata alone never outranks a lexflow `ok` check for a website** (D10).
* **Agreement is evidence.** Where Census and Wikidata agreed, the pilot's websites were 27 % stale (of
  verifiable). Where Census stood alone, they were 48 % stale. Rows that disagree get an earlier check (3.3).
* **Scores count shown values only.** The contact ladder (`contacts.level`) and `summary.offices` see only the
  values `best()` shows. So the first re-score after phase 1 lowers the level of a government whose only website
  is unchecked, and phase 2's checks raise it again.

---

## 3. The recurring check ("circle around")

### 3.1 The job step and its schedule

* **Code.** A new module, `lexflow/entities/recheck.py`, built from the pilot's `scripts/contacts_check.py`. It
  takes `Fetcher`, `Throttle`, `classify_web`, `check_email` and the phone checks, with the changes in 3.4 and
  3.5, and writes `contact_status` and `contact_checks` instead of JSON.
  * It does not reuse `crawl._allowed` (`crawl.py:42-52`) as it is. That function has no cache and no throttle,
    and its GET follows redirects. robots.txt is handled as in 3.5.
* **Step.** It is registered as `Step("recheck", "Keep contacts up to date", …, "recommended", st_recheck,
  run_recheck, needs=["governments"], params=["states","budget_minutes","tiers","force"],
  credits=[C.WIKIDATA, C.GOV_DIRECTORY])`, next to `crawl` (`steps.py:546`).
  * Every step now needs `credits` or a `credits_note` (`steps.py:29-44`). Wikidata (CC0) is credited, and so is
    Govdirectory, because its sitemap is read.
  * `st_recheck` reports due rows, the last run and the stale rate.
  * `_mark_scan` (`steps.py:51`) records each run.
* **Run group.** `jobs.py:26` gains a group `NETWORK = {"recheck", "crawl"}`, so two web sweeps never run at
  once and the per-domain budget holds. `recheck` does not use Ollama.
* **Schedule.** Nothing schedules jobs today; the runner only starts queued rows. On each 30-second heartbeat in
  `Runner.run` (`jobs.py:133`), a small due-check reads `settings` key `schedule.recheck` (default
  `{"enabled": false, "every_hours": 24, "budget_minutes": 20, "workers": 8}`). The setting is local; it is
  switched on for one machine (2.1). When the job is due, and none is queued or running, it enqueues one
  `recheck`. An external cron calling `python -m lexflow run recheck` works the same way.
* **Each run.** It takes rows with `next_check_at <= now`, plus rows with no status row, ordered by priority,
  until the time budget runs out:
  1. tier 0 first;
  2. then by days overdue × tier weight;
  3. then a boost for rows whose sources disagree, and for rows an answer used since their last check.

  Due rows are grouped by `norm_value`, so each normalised URL is fetched once per run (2.3).

### 3.2 Tiers and cadence

| Tier | What | Size today | Interval |
|---|---|---|---|
| 0, published | contacts on published pages: the 36 curated contacts of DC, Baltimore and Charlottesville; contacts of agencies that play roles in reviewed or agreed models; any contact in a published answer | about 250 (the fixture holds 61 agency websites, plus units, mailboxes and main lines) | **7 days**, plus a forced check of anything older than 7 days before a publish dry run |
| 1, shown in answers | contacts frozen in asked answers (1,818 distinct in 1,186 snapshots for 861 governments: 951 websites, 860 postal, 7 other); all other agency contacts; the map panel's top 4 offices for governments in corpus states | about 1,000 URLs | **14 days** |
| 2, bulk | every other website and page row (Census and Wikidata) | about 15,000 URLs | **30 days**. The first pass is spread over 30 days. |
| postal | 38,640 Census addresses (70 % of contacts) | – | not fetched. Shown with "Census 2022". Verified only when the owner's verified website shows the address (phase 6). |

Today's load is about 650 URLs a day: about 1,350 page GETs (2.07 per URL in the pilot) and up to about 650
robots.txt GETs. With 8 workers and the pilot's mean of 2.8 s per URL, plus the robots.txt fetches, that takes
about 5 minutes. A forced full pass spans several days because of the per-domain cap (3.5).

### 3.3 Staleness and backoff

* **After `ok`:** the next check is due after the tier interval, ±10 % jitter, so that load spreads out.
* **After a failure:** recheck after 1 day, then 3 days, then 7 days.
  * The first failure is a strike: `fails=1`. A value that was `ok` stays `ok` and shown. A value with no status
    gets `unverifiable`, with the failure as its reason, and stays hidden.
  * A value becomes `broken` (hidden) only after two failures at least 20 h apart, because timeouts and 5xx
    errors are often transient.
  * NXDOMAIN also needs two strikes, after one `www.` toggle. Parked, default and suspended pages follow the
    same two-strike rule.
* **Spam or gambling content with a second signal (3.4):** the value becomes `quarantined` on first sight. It is
  rechecked monthly, and only a person can clear it.
* **`moved`:** the open proposal for that old and new value is opened, or its `seen_count` is raised (2.3), and
  the value is rechecked in 7 days. Seeing the same target twice makes the proposal "confirmed", but it still
  waits for a person.
* **`unverifiable`:** the interval is doubled. For tier 0, an item goes into the review queue so that a person
  can confirm it by hand (`method='reviewer'`, valid 90 days).
* **Trigger events** put rows back to "due now":
  * an import or a source rerun that changes a value;
  * a reader rendering a contact whose `verified_at` is older than the tier interval;
  * a Wikidata read that shows a new value or a dissolution (P576 or P1366).

### 3.4 Checks per kind (what worked in the pilot)

| Kind | Checks, in order | Outcome | Pilot evidence |
|---|---|---|---|
| website, page | 1. robots.txt for the origin (3.5). 2. **DNS of the stored host**, with one `www.` toggle. 3. GET with redirects followed by hand: at most 8 hops, 15 s per request, 30 s per item in all, 1.5 MB, stream only. Every hop passes the address check (3.5). 4. Classify (see below). | `ok`, `moved`, `broken`, `quarantined` or `unverifiable`. The proposal carries the replacement address. | DNS was the cheapest check and caught 7 dead hosts. Redirects found 8 moved sites: 6 to `.gov`, 1 to a county's `*.va.us` domain and 1 to a town site whose title carries the town's name, so all 8 pass the `moved` display rule. Title checks caught 4 broken sites that answered 200 (3 spam, 1 default server page). There were 6 bot walls (5 × 403, 1 × 503). |
| email (office mailboxes only) | 1. The privacy guard (5.2): role-shaped local parts only. 2. DNS MX, with an A record as fallback; a null MX counts as broken. 3. Is the domain the owner's live website domain? Is it a retired site's domain (suspect)? 4. **Does the address appear on a fetched page of the owner's own official site?** That is the strong signal. | `ok` only with step 4. A Wikidata P968 counts once lexflow finds the address on the statement's P854 page. MX alone gives `unverifiable`. | MX passed 9 of 9, so it is weak. 1 address was on a fetched page and 1 on a retired site's domain. All 9 are role-shaped under the new guard. |
| phone (main lines only) | 1. Valid NANP shape. 2. **Found on its `source_url` page, or on the owner's verified home or contact page.** | `ok` if found; `unverifiable` if not; `broken` only if invalid | 2 of 11 were found on the home page and 1 on another official page; 8 were not found. The home page alone finds too few, so the check also reads the contact page. |
| Wikidata crosswalk | `wbgetentities` in batches of 50 with `maxlag=5` (1.6): follow redirects automatically, flag deletions, compare P856/P968/P1329 statements without deprecated or end-dated values, watch P576/P1366. Office-holder claims are dropped at parse. | disagreement flags; proposals | P856 is not fresher: 5 of the 6 moved sites still had the old domain. About 10 batches per pass. |
| Govdirectory | one monthly GET of `sitemap.xml` to see which agency QIDs are listed | `govdirectory_url` | only federal, NY and NC |

Website classification, in order:

1. A redirect hop to a refused address or port (3.5) → `broken` (`unsafe_redirect`). The hop is not fetched.
2. 401, 403, 406, 418, 429 or 999 → `unverifiable`. So is a 5xx with a challenge header (`cf-ray`,
   `cf-mitigated`, `x-sucuri-id`, `x-iinfo`, or a Cloudflare, Akamai, Incapsula or Sucuri `Server` header) or a
   bot-wall marker in the page, and a status below 300 whose title is a bot-wall marker. These are the pilot's
   rules (`contacts_check.py:587-590`). Without them, the pilot's 503 bot wall would come out `broken`.
3. Any other status of 400 or more → `broken`.
4. Spam with a second signal (below) → `quarantined`.
5. Parked hosts or markers, or default or suspended page markers → `broken`.
6. The final registrable domain differs from the stored one → `moved`, shown only under the display rule (2.2).
7. The owner's name is absent from the title and visible text → `unverifiable`. For an agency, the test uses its
   name and every alias. The pilot's `core_name` (`contacts_check.py:192-198`) strips only government prefixes,
   so agency sites would otherwise mostly come out `unverifiable`.
8. Otherwise → `ok`. A same-host `http` → `https` or `www.` change is a normalisation recorded in the evidence,
   not a new value. That was 26 of the 55 sampled sites; the pilot's `https_upgrade` flag counts 34 because it
   also fires on the 8 moved sites.

Whatever the class: if any hop was fetched without certificate verification (the pilot retries a certificate
failure that way, `contacts_check.py:487-494`), an `ok` or `moved` result becomes `unverifiable`
(`tls_unverified`). Such a page earns no `page-contains` evidence for mailboxes or phones. The pilot had 0 such
items.

**The spam rule.** Quarantine hides a value everywhere until a person clears it, so one spam signal is not
enough.

* Spam signals:
  * a word from the spam vocabulary seen on hijacked US government domains, mostly Indonesian gambling and SEO
    terms: `situs`, `gacor`, `togel`, `judi`, `bandar`, `jasa`, `bisnis`, `sbobet`, `maxwin`;
  * an English gambling or adult word: `casino`, `poker`, `betting`, `slot`, `porn`, `escort`, `viagra`. A state
    lottery or gaming regulator uses the gambling words on its own site;
  * a title more than half of whose letters are CJK, Hangul or another script the owner does not use. A single
    such character is not a signal; the pilot's `SPAM_TITLE_RE` (`contacts_check.py:120-121`) fires on one.
* Second signals:
  * the owner's name and aliases are absent from the title and the visible text;
  * the final registrable domain differs from the stored one and is not official;
  * a parked or lapsed-domain marker.
* A value is quarantined on first sight when its title has two vocabulary words, or when it has one spam signal
  and one second signal. Otherwise classification goes on, and the words are recorded in the evidence.
* The three pilot cases all qualify:
  * Androscoggin County's site redirects to an unrelated domain whose title is Indonesian slot-gambling spam;
  * Auburn's redirects to an unrelated domain with a Chinese-language title;
  * Lowellville's own domain shows a title with two vocabulary words.
* A gaming regulator's page on its own `.gov` domain, with its name in the title, stays `ok`.

A records or business page must also still carry its topic words ("records request", "FOIA", "business
license").

**The regression fixture.** The pilot's 86 classified results become the classifier's offline regression
fixture, through this written mapping. One replay is one run, so failures are first strikes.

| Pilot result | Expected outcome |
|---|---|
| website `ok/live` (28) and page `ok/live` (6) | `ok` |
| website `moved/domain_changed` (8) | `moved`; all 8 shown |
| website `broken`: `dns_nxdomain` 7, `http_404` 1, `timeout` 1, `default_or_suspended_page` 1 | first strike (`fails=1`, `unverifiable` while hidden); `broken` after a second failure at least 20 h later |
| website `broken/hijacked_spam` (3) | `quarantined` |
| website `unverifiable`: `blocked_http_403` 5, `blocked_http_503` 1 | `unverifiable` |
| page `unverifiable/no_url_stored` (5) | `unverifiable` |
| email `ok/mx` (9) | `unverifiable`, except the 1 found on a fetched official page: `ok` |
| phone `ok`: 2 on the home page, 1 on another official page | `ok` |
| phone `unverifiable/not_on_home_page` (8) | `unverifiable` |

* The fixture holds no page bodies. Replaying `classify_web` from it with an empty body gives 64 of the 66 web
  items. The 2 misses are a site whose name appears only in the body, and the 503 bot wall. The fixture needs
  recorded `name_present` and `challenge_header` fields for each web item before the test can pass.
* The pilot never fetched robots.txt. A re-recorded fixture must come from a run that respects it.

### 3.5 Politeness, safety and rate budget

* **Requests.**
  * GET only, no JavaScript, no cookies kept across domains, no forms, no logins.
  * User-Agent `lexflow/<version> (+https://github.com/alibama/lexflow)`. The contact URL is the project, not a
    person.
* **Addresses.** Before each hop, the host is resolved, and the connection goes to the address that was checked.
  A hop is refused when that address is loopback, private, link-local, unique-local, shared (carrier-grade NAT),
  multicast or unspecified, or when its port is not 80 or 443.
  * A hijacked domain then cannot send the checker to `localhost:8000`, `ollama:11434` or other services inside
    the container.
  * `crawl`'s `_get` (`crawl.py:29-39`) lets `requests` follow redirects to any host today. It needs the same
    check.
* **robots.txt.** It is fetched once per origin (scheme and host) and cached for 24 h, in memory and in a small
  local table, so later runs that day reuse it.
  * The fetch goes through the same `Throttle` and counts towards the per-domain cap and the run's budget.
  * It follows at most 5 redirects, each through the address check.
  * A 4xx means no rules apply. A 5xx or a timeout means the origin is skipped for that run.
* **Per domain.**
  * At most one request start per second per registrable domain (`Throttle`), robots.txt included, so shared
    hosts such as govoffice.com (108 sites), govoffice2.com (75) and in.gov (52) are paced as one.
  * At most 60 requests per registrable domain in any 24 hours, counted across runs.
  * On a 429, or a 503 with `Retry-After`, skip the domain until the end of the run or the `Retry-After` time,
    whichever is later.
* **Time limits.** 15 s per request, and one 30 s deadline per item that covers every hop, the fallback, a client
  redirect and the body read. The pilot sets `(15, 15)` timeouts per GET plus a 15 s body loop, with up to 8
  hops, a fallback and a client redirect on top; that is how its 60.1 s case happened. 8 workers.
* **Wikidata.**
  * The API: at most 1 request per second, and `maxlag=5` on every read (1.6).
  * WDQS: one query at a time, run in two steps (collect QIDs, then `VALUES` chunks of 120–250), within its
    60 s/min budget.
  * A pass needs about 10 + 2 batches: 498 government QIDs and 76 agency QIDs.
* **Monthly budget.** About 33,500 page GETs for tier 2, plus about 6,000 for tiers 0 and 1, plus up to about
  19,500 robots.txt GETs (at most one per origin per day). That is about 59,000 a month, or about 2,000 a day.
  The busiest domain, govoffice.com, gets about 7.5 page GETs and up to about 3.6 robots.txt GETs a day, so about
  11, well under the cap.
* **A forced full pass** (`force`) marks every row due at once, and it still respects the cap. Most domains
  finish in the first run. govoffice.com needs about 224 page GETs and up to 108 robots.txt GETs against a cap
  of 60 a day, so it finishes after 4 to 6 days. The fetching alone would take about 1.6 h with 8 workers, plus
  the robots.txt fetches.
* **Never.** No SMTP connections or recipient probing, no emails sent, no calls placed, no third-party
  validation or lookup services, no requests to non-public addresses. No contact data leaves lexflow through a
  check.

### 3.6 What changes automatically, and what needs a person

| Automatic (the machine, idempotent) | Needs a person (the review queue) |
|---|---|
| the `contact_status` columns: `status`, `reason`, `checked_at`, `verified_at`, `method`, `evidence`, `fails`, `next_check_at`, `tier` | any **new value**: a redirect target, a value the recheck job finds on a page, a Wikidata value that differs, a replacement for a broken value |
| Hiding `broken` values, and quarantining spam that has a second signal, on every surface | clearing a quarantine; retiring a value for good |
| Choosing the primary value among values already stored (2.5); showing or hiding a `moved` link by the display rule | confirming a tier-0 `unverifiable` contact by hand; showing a `moved` link whose target is neither official nor named |
| Same-host `https`/`www.` normalisation | marking an agency abolished, renamed or merged; accepting `successor-of` |
| Following a Wikidata redirect (merge) to the new QID | accepting `played-by` and `mentions` links for reviewed models; minting office instances that will be published |
| Opening proposals and raising `seen_count`; drafting upstream suggestions | every upstream suggestion (4); every publish and Wikibase load, after a dry run; creating Wikibase properties |

### 3.7 How changes reach the dashboard, wiki pages and Wikibase

* **DB first.** Each batch writes `contact_status` and `contact_checks`, never `contacts`, then calls `db.bump`
  (`db.py:433`) so that the dashboard refreshes. `contact_status` reaches other machines through Turso sync,
  merged by `checked_at` (2.1).
* **Dashboard.**
  * The Setup checklist row for `recheck`: due count, last run, stale rate.
  * A new Contacts page:
    * stale rate per sweep, by kind, tier, state and source;
    * the review queue, showing the old and new values, hop chain, title and source URL;
    * a quarantine list. A quarantined address is never a link there; only its truncated title is shown.
  * A provenance tooltip on every contact: "Census 2022 · checked 2026-10-12 · ok"
    (`dashboard/app.js:388-390` for the map panel, `:998-1003` and `:1026` for the place page, `:846-849` for
    asked answers).
  * Endpoints: `GET /api/contacts/health`, `GET /api/contacts/review` and `POST /api/contacts/review/{id}`. The
    POST accepts or rejects a proposal; it is a local DB write in the user's own app.
* **Answers and the browser plugin.** Hidden statuses disappear as soon as the run commits, through `best()`.
  * The plugin's lookup (`api/app.py:310-315`) skips hidden websites.
  * Asked answers render contacts **live** from `contacts`, keyed by `gov_id`; the frozen
    `asked_answers.local` snapshot is kept for audit only. Changing `ask/pipeline.py` waits for the benchmark to
    finish. Until then, the renderers pass the snapshot's contacts through `best()`.
* **DokuWiki pages.**
  * `_contacts_block` (`lexipedia.py:184-194`) adds "source, checked YYYY-MM-DD" and omits hidden statuses.
  * Its three callers render JSON copies, not `contacts`: place pages (`:232-238`), place-process pages
    (`:273-274`) and asked pages (`:340-341`). Each passes its contacts through `best()` and the privacy guard
    (5.2) first.
  * Agency pages are added in the `lexflow:` namespace.
  * A sweep never publishes. When a tier-0 contact's status or primary value changes, the run marks the pages
    that show it as "needs republish". The dashboard then offers the existing publish dry run, and the real
    publish stays user-triggered.
* **Wikibase.** The next user-triggered `wikibase` load, after a dry run, regenerates agency items and contact
  statements. Each statement carries references: retrieved = `verified_at`, plus the method. Primary `ok`
  values get preferred rank. Moved and broken values are deprecated with P2241, and retired values get an end
  time.

---

## 4. Upstream: proposing corrections to Wikidata

**Principle.** lexflow drafts suggestions and never edits. It holds no Wikidata credentials. A person checks each
suggestion against its reference and applies it under their own account. Govdirectory reads Wikidata, so for
federal, NY and NC bodies an applied fix appears there after its next build.

* Builds are deployed by hand, at irregular intervals. The 2026 deploys were on 01-24, 02-21, 03-12, 04-06,
  07-29, 08-28, 08-29 and 09-25, with a 114-day gap from 04-06 to 07-29.
* So an applied fix can take up to about 4 months to appear on Govdirectory.

| Trigger | Suggested edit | Reference attached |
|---|---|---|
| A government or agency website `moved`, accepted by a person | Add the new P856 value. Mark the old value deprecated with P2241 (link rot), or give it an end time if the date is known. Make the new value preferred. | P854 = the new official page, P813 = `verified_at` |
| The P856 value is broken (`broken` after two strikes), and no accepted replacement exists | Flag for a person to research; no value is proposed | the check evidence (hop chain) |
| An office mailbox, main line or contact page found on the body's official page, for an item that lacks it | Add P968, P1329 or P11266 | P854 = the page where it was found, P813 |
| A statement referenced only with P143 (imported from Wikipedia) that lexflow verified | Add a real reference | P854, P813 |
| A body with no item (Virginia DPOR, DC Office of Administrative Hearings, Maryland Central Collection Unit and others among the 15 in the fixture) | Create an item: P31 government agency (or a per-state class), P17, P1001 or P131, P749 parent, P856 | the official page |
| P576 or P1366 missing for an abolished body (for example the California Department of Alcohol and Drug Programs, whose site no longer answers) | Add the dissolution or "replaced by" | the statute, or an official notice |

Workflow:

1. The `recheck` job and the agency loader draft `upstream_suggestions` rows, one live row per item, property,
   action and value (2.3). Rows that do not touch tier-0 bodies are drafted at most weekly.
2. A person reviews them on the dashboard, in small batches of 20 or fewer.
3. lexflow exports the approved rows as QuickStatements text, for example
   `Q…|P856|"https://…/"|S854|"https://…/"|S813|+2026-10-12T00:00:00Z/11`. The person pastes it into the tool
   themselves.
4. Rank changes are listed as manual steps, because QuickStatements cannot reliably set ranks.
5. The next Wikidata read that sees the change marks the row `applied`, which feeds a metric.

Guardrails:

* Only organisations and official channels. Never office-holder or staff properties.
* Every suggestion has an official reference.
* No bulk runs.
* Nothing is filed on Govdirectory's error-report page or GitHub in lexflow-written words. The repository blocks
  recognisably AI-generated contributions, so a person writes any report.

---

## 5. Privacy and scope rules

1. **Organisations and official channels only.** That means an agency or government website, a contact or
   records page, a published general office mailbox (records, FOIA, info and similar), a main office line, and
   an office postal address.
2. **No contact details of individuals,** even public ones. That covers named officials' direct lines and
   addresses, staff contacts in the places models, and anyone's personal mailbox.
   * **The office-mailbox guard.** The pilot's `is_office_mailbox` (`contacts_check.py:236-244`) matches role
     words as substrings, and accepts an upper-case acronym only when the same row spells it out. It lets
     made-up personal mailboxes through, and it refuses three of the four office mailboxes in `agencies.json`.
     A whole-token rule replaces it:
     1. **Tokens.** Split the local part at `.`, `_`, `-` and `+`, at changes from lower to upper case
        (`CorpHelp` gives `corp` and `help`), and between letters and digits. Digit tokens are ignored.
     2. **Role words, as whole tokens.** A token is allowed when it is a role word, or when it can be cut into
        role words with nothing left over (`publicrecords`, `foiacouncil`). Role words are a fixed list of
        office and request words: `foia`, `records`, `mpia`, `pia`, `oig`, `clerk`, `info`, `help`, `contact`,
        `request`, `corporations`, `corps`, `corp`, `business`, `licensing`, `permits`, `revenue`, `tax`,
        `appeals`, `council` and similar. The list leaves out titles of office-holders (`mayor`, `manager`,
        `director`) and short words that are also common names (`cor`).
     3. **The office's own initials.** A token is also allowed when it is the initialism of the owner's name,
        its core name (without "City of", "County" and the like), an alias, or the office name that starts the
        row's label, or an upper-case acronym written in one of them: `mpd` for the Metropolitan Police
        Department, `oig` for an Office of the Inspector General. A word of the owner's own name is allowed
        beside a role word (`baltimorecity` + `license`), never alone.
     4. **Role-shaped or personal-looking.** A local part whose every token is allowed, with at least one role
        word or initialism, is **role-shaped**. Any other local part is **personal-looking** and is refused at
        write time: it is not stored, only counted. That covers first.last, initial+surname and
        surname+initial, with or without digits, and a role word beside a name.
     5. **Shown only from the office's own page.** A role-shaped address is stored as `unchecked` and is not
        shown. It becomes `ok`, and is shown, only when it is published on the owner's own official page as the
        office's mailbox for requests or inquiries, and lexflow's fetch of that page finds it there (3.4).
   * **Test cases** for the guard's tests:

     | Local part | Expected |
     |---|---|
     | made up, from the review: `courtney.smith`, `jtownsend`, `kwaters`, `aborowski`, `firestone.j`, `apressley`, `boardman.t`, `publicover.d`, `jmailer`, `pia.jones`, `cor.devries`, `mayor.brown` | refused as personal-looking. The pilot's guard accepted every one. |
     | made up, with digits or reversed: `jtownsend2`, `townsendj`, `courtney.smith1`, `kwaters77` | refused |
     | the four office mailboxes in `agencies.json`: the DC Metropolitan Police Department (`mpd`, its initialism), the Florida Division of Corporations (`CorpHelp`), the New York Division of Corporations (`corporations`) and the Washington Corporations and Charities Division (`corps`) | role-shaped; shown once found on the office's own page. The pilot's guard refused all but the Florida one. |
     | role words: `foia`, `records`, `mpia`, `oig`, `publicrecords`, `foia.appeals`, `cityclerk` | role-shaped |

   * **Where it runs.** At write time for every writer: `import_csv`, `crawl` (which today stores every `mailto:`
     link on a home page), `local`, Wikidata and the agency seed. The places loader also applies it to the
     `local_answers.contacts` JSON it writes. The renderers apply it to the JSON copies they show (3.7), because
     place pages and asked pages do not render from `contacts`.
   * `kind=person` is removed from `import_csv` (`contacts.py:103`) and from the contact ladder (`:125`).
   * **No staff names in office values.** A postal or office value keeps the office name and the address. An
     "Attn:" or "c/o" line is kept only when it names an office or a title, such as "Attn: Records Custodian".
     A line that names a person is dropped, and so is a staff name anywhere else in the value. Census postal rows
     have no such lines today.
   * **The Baltimore case.** On 2026-10-10, two personal-looking mailboxes on the Baltimore government's domain,
     and staff names, were removed from `curated/places/md/baltimore.json`, from the database and from the live
     wiki pages `lexflow:md:baltimore` and `lexflow:md:baltimore:records`. The pilot's guard had skipped both
     mailboxes, but it ran only in the pilot, and those pages render from `local_answers.contacts`. Old DokuWiki
     revisions of the two pages still hold them until a wiki admin removes those revisions (8.7).
3. **Registered agents, incorporators, organizers and requesters are roles, not people to contact.**
   * They resolve to `lexflow:private-party`.
   * lexflow never looks up who a company's registered agent, incorporator or organizer is.
   * It stores no business-registry person data.
4. **Offices, not office-holders.** "The Secretary of State" links to the office. Position items are kept only as
   `related_items` for identity. `wbgetentities` returns every claim of an item, so office-holder claims (P1308,
   and the "led by" claims Govdirectory reads: P2388, P1313, P488, P169, P1037 and P3975) are dropped when the
   response is parsed. They are never stored or logged.
5. **Census labels stay titles only** (`governments.py:83`).
6. **Evidence is minimal.** It holds parsed URLs, status codes, hop chains, titles of at most 200 characters and
   MX host names. It holds no page bodies, screenshots or form contents. Hijacked pages are never linked; only
   their title is kept, truncated.
7. **People are recorded by role, never by name.** A person who verifies or approves is recorded as `reviewer`.
   No person is named in the app, on wiki pages or in Wikibase as a contact, a source of questions or a credit
   without their agreement. Step credits name organisations: the `recheck` step credits Wikidata and
   Govdirectory.
8. **Nothing leaves lexflow through a check.** There are no third-party lookups, no SMTP probes and no messages
   sent.

---

## 6. Phased implementation plan

| Phase | Scope | Effort | Tests (new test files) | Exit check |
|---|---|---|---|---|
| **1. Hide first, then honest dates** (no network) | **First, the safety item.** (a) Load the pilot's results for its 86 contacts into `contact_status` through the mapping in 3.4, so the 3 hijacked websites (Androscoggin County ME, Auburn ME, Lowellville OH) are `quarantined` and the other failures carry a first strike. (b) Ship `best()` with the display policy on every user-facing surface, so flagged and unchecked websites and pages are not linked, and the plugin lookup skips them. (c) Run an audit query that lists every published wiki page and asked snapshot that links a hidden website; the user republishes those pages after a dry run. **Then** the `contacts` columns, `contact_status`, the Turso schema step, `upsert(keep=)`, the five writers filling provenance (2.4), the `us` sync filter and the privacy guard. Readers outside `lexflow/ask/` come first; `ask/local.contacts` follows when the benchmark ends. | 3 days | The three hijacked domains are hidden on every surface and in the plugin lookup. No surface links an `unchecked` website. Keep semantics: a Census reload leaves `first_seen` and every `contact_status` row alone. A check-only write leaves `contacts.updated_at` alone and does not trip `st_score`. Ranking order and tie-breaks. Hidden statuses never reach `answers_for`, `_contacts_block` or the dashboard. The guard's test cases (5.2). `kind=person` is refused. The migration is idempotent locally and on Turso: one `ALTER` per call, a duplicate column ignored, any other error raised. `contact_status` sync keeps the newer `checked_at`, whichever side writes last. A pull with a state list brings `us` rows. | `sync push` and `pull` work after the migration. After the republish, the audit query finds no hidden website on a public surface. |
| **2. The recheck job** | `entities/recheck.py` built from the pilot; `contact_checks` and `contact_proposals` with their unique keys; `Step("recheck")` with its credits; the `NETWORK` group; the runner's due-check (off by default, on for one machine); tiers, backoff and budget; the robots.txt cache, the address check, the TLS rule, the per-item deadline and the per-domain cap across runs; one fetch per `norm_value`. It starts with a one-off budgeted check of tiers 0 and 1, so that verified websites reappear soon after phase 1 hid them. | 4–5 days | The classifier reproduces the written mapping (3.4) from recorded hop chains, titles, `name_present` and `challenge_header` (offline, sockets blocked). The spam rule: a regulator's "casino" page on its own domain with its name stays `ok`; a single CJK character is not a signal; the 3 pilot cases are quarantined. The `moved` display rule. A redirect to loopback, a private address or another port is refused. A page fetched without TLS verification is never `ok`. robots.txt is fetched once per origin per 24 h and counted. The fake-clock throttle spaces requests at least 1 s apart per registrable domain, robots.txt included. A forced pass stops at 60 requests per domain per 24 h and resumes the next day. A second sighting raises `seen_count` and opens no second proposal. The two-strike rule. Immediate quarantine. A proposal on `moved`, never a new value. No port-25 connection anywhere. | The one-off check of tiers 0 and 1, then a first budgeted daily run on the corpus states; the stale rate is reported by kind, tier, state and source |
| **3. Agencies and links** | `agencies`, `office_types`, `entity_links`; a seed from `agencies.json`, `caselaw.COURTS` and the curated agency contacts, with the identity rule (1.2); the places loader's agency map and retired city rows (1.3); `entities/resolve.py`; `played-by` for the 88 actors of the 22 Claude-reviewed models; a `mentions` finder that shares `act_id` with the xref module; agency contacts with Wikidata references through `p:`/`ps:`; the `gov_id` guards | 4–6 days | Resolver cases from 1.5. Key stability across a rename. Seeding is idempotent: a re-run matches by QID, then by name or alias, and mints a suffixed key on a slug collision; it keeps a reviewer's `status`, `method` and aliases. A second `load_local` run writes no agency contact back under a city. A website lookup that hits an agency no longer 404s. `mentions` spans match their quote. No link points at a person. | At least 95 % of the actors in reviewed models are resolved (private-party included). Agency contacts appear under "State offices" in answers. |
| **4. Surfaces** | Dashboard Contacts page and API; provenance on DokuWiki pages and agency pages; the "needs republish" marker; the Wikibase classes, properties and loader (after the user's go-ahead) | 3 days | A loader dry run on a fixture agency gives the expected statements, references and ranks. P8 appears only on exact organisation and court matches. Hidden statuses are deprecated or omitted. There are no person statements. Publish dry runs flag changed pages. | A dry run, then a user-triggered load of the corpus states' agencies |
| **5. Upstream** | `upstream_suggestions` with its unique key, the drafting rules (4), dashboard review, QuickStatements export, applied-detection | 2 days | Drafting from fixtures: a moved site gives an add plus a deprecate step, with references. Re-drafting the same edit adds no second live row. Nothing is drafted for personal or unreferenced data. The export format. The module has no write code path (no POST, no credentials). | The first reviewed batch is exported, and the applied rate is tracked |
| **6. Deeper checks** (optional) | Postal addresses verified when found on the owner's verified site; agencies' records and licence contact pages found by `crawl` | 2 days | Address matching (normalised); topic-word checks | The share of postal-only governments falls |

The total is about 18 to 21 developer days.

Phase 1 has a cost: until phase 2's first checks run, almost every website is hidden, because nothing is
checked yet. That is the price of never linking an unchecked website. Phase 2 starts with tiers 0 and 1 to keep
the gap short.

Three constraints apply until AskBench finishes:

* Do not edit `lexflow/ask/*`, `extract/*`, `municipal/statutes.py`, existing tests or curated data.
* Privacy is the exception (D14). Personal data found in curated data is removed as soon as it is found, as it was
  on 2026-10-10.
* Phases 1 to 3 are designed so that their core lives in `lexflow/entities/` and new tests. The edits to existing
  files (writers, `db.py`, `turso.py`, `steps.py`, `jobs.py`, `crawl.py`, the guards and the renderers) are small
  and listed above.

## 7. Measuring success

| Metric | Definition | Baseline (2026-10-10) | Target |
|---|---|---|---|
| Actors resolved | actors in reviewed or agreed models with an accepted `played-by` link (the private-party marker included) ÷ all such actors | 0 of 88 (22 Claude-reviewed models). There are 364 actors across all models. | ≥ 95 % after phase 3 |
| **Actors with a verified contact** | of the non-private actors, the share whose player has at least one `ok` contact verified within its tier interval. For an office type, the player is the instance in the place's context, or the parent body. | 0 of 55 (public body 21, court 13, other government 12, official 9) | ≥ 80 % after phase 3; ≥ 90 % after phase 4 |
| **Stale rate after each sweep** | (moved + broken + quarantined) ÷ verifiable checked rows, by kind, tier, state and source | pilot: websites 43 % (±14), all kinds 31 %, Census-only websites 48 % | the stored rate is below 15 % within 3 months, as proposals are accepted |
| Stale shown | the share of **displayed** contacts that are stale at render time | unknown; nothing is checked | below 2 % for tier 0 and below 5 % overall, at all times |
| Freshness coverage | the share of each tier verified within its interval | 0 % | tier 0: 100 %; tier 1: ≥ 95 %; tier 2: ≥ 90 % after the first month |
| Exposure | quarantined or broken values on any public surface, from an audit query after each publish dry run | 3 hijacked domains in a sample of 55 | 0 |
| Privacy | personal-looking mailboxes or staff names on any surface, from the same audit query | 2 mailboxes on two live wiki pages, removed on 2026-10-10; old wiki revisions still hold them | 0, and the old revisions removed |
| Review flow | open proposals; median days to a decision | – | tier 0 decided in under 7 days |
| Politeness | the maximum request rate per registrable domain, robots.txt included; requests per domain per 24 h; 429 responses; GETs per run against the budget | the pilot: at most 10 requests per domain, and no robots.txt fetched | at most 1 per second and 60 per day per domain; no ignored `Retry-After`; within 10 % of budget |
| Upstream | suggestions approved, exported and applied; the share of moved websites whose Wikidata P856 shows the new domain at the next read | 1 of 6 | ≥ 80 % of the approved suggestions applied |
| Agency coverage | agencies with a QID; with a verified website; with a verified office mailbox or main line from an official page | the fixture: 69 exact of 98, 61 websites (unchecked), 2 with an email or phone | every corpus-state body named in a reviewed model has a verified website |

`GET /api/contacts/health` computes each metric from `contacts`, `contact_status`, `contact_checks` and
`entity_links`. It keeps one row per sweep, so that the stale-rate trend can be charted.

## 8. Open questions

1. **Wikibase writes.** Creating "played by", the four contact properties and the reference properties on
   lexipedia.wikibase.cloud is a wiki write. It needs the user's go-ahead, and the links map raises the same
   question for its own properties. Both sets should be decided together.
2. **Proposal sync.** Should `contact_proposals` sync through Turso, so that more than one machine or reviewer
   can work the queue? This plan starts local.
3. **Office instances.** Should they be minted lazily, or up front for the corpus states? Up front means, for
   example, 67 Florida clerks of court and about 120 Virginia circuit court clerks. Lazily keeps the tables small.
4. **Which address a shown `moved` link uses.** When a `moved` link passes the display rule, show the stored
   address, which still redirects, or the final address before a person accepts it? This plan shows the stored
   one and flags it.
5. **Review capacity.** Is a person available weekly? Without review, proposals pile up. The hiding rules still
   protect users, but coverage will not grow.
6. **Postal addresses.** Should postal rows be dropped from public answers once a verified website exists? They
   are 70 % of contacts, and their vintage is 2022. Many township and small-town Census addresses (there are
   16,144 townships) are probably an officer's home or a PO box, so showing them as "Census 2022" may publish a
   residence. Options: show postal rows only for governments above a population floor, or only once phase 6
   verifies them on the owner's site.
7. **Old wiki revisions.** The old revisions of `lexflow:md:baltimore` and `lexflow:md:baltimore:records` that
   still hold the removed mailboxes need a wiki admin to remove them. That is an admin action on the wiki,
   outside lexflow's publishing.
