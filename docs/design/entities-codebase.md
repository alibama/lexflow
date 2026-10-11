# Entities in lexflow: governments, contacts and Wikidata matches

A read-only map of how lexflow stores governments, contacts and Wikidata matches today, how fresh the
contacts are, and where agency entities, entity links and per-contact provenance can be added.

* Surveyed 2026-10-10. Numbers come from read-only `SELECT`s on `data/lexflow.db`, which was opened with
  `mode=ro`. The database clock read 2026-10-10 13:55 UTC.
* Line numbers refer to the tree as it was on that date. Nothing in the repo was changed for this survey.
* The survey records organisations and official office channels only. It reproduces no email address or phone
  number.

## 1. The short version

| | Today |
|---|---|
| Entity kinds stored | One: **general-purpose governments** (Census GID). There is no table for agencies, departments, boards, courts or clerks. |
| Contacts | 55,181 rows, keyed by `(gov_id, question, kind, value)`. 99.2 % of them are Census GUS 2022 rows: a postal address with an officer's title, or a website. |
| Provenance per contact | Only a `source` tag (`census-gus-2022`, `wikidata`, `site-scan`, `local-research`, `csv-import`). There is no source URL and no vintage. The Wikidata QID is kept only inside the label text. |
| Freshness | `updated_at` is the time the row was last written, not the time it was last checked. Every contact was written between 2026-10-09 18:57 and 2026-10-10 12:58 UTC. No contact has a checked or verified date. |
| Wikidata | 498 of 38,640 governments (1.3 %) have a QID: Virginia 319 of 322, Maryland 179 of 180, DC 0 of 1. The other 48 states were never queried. |
| Website scan | 2 governments in `crawl_log`. The scan found 1 page. |
| Process-model actors | 364 actors in 87 models, named in free text. The IR has `Actor.wikidata` and `Actor.govdirectory` fields, but the compiler drops them, so no actor is linked to anything. |
| Agency contacts | State and city agencies (for example the Virginia FOIA Council, the Maryland Public Access Ombudsman, and DC's tax office and licensing department) are stored as **contacts of a city**. |

## 2. Storage today

### 2.1 Tables (`lexflow/store/db.py`)

| Table | Lines | Key | What it holds | Synced to Turso |
|---|---|---|---|---|
| `governments` | 20-37 | `gov_id` (Census GID, 14 digits) | name, kind (county, municipality or township), county and place FIPS, population, `website`, `address`, **`wikidata`** (QID), `source`, `updated_at`, `origin` | yes |
| `contacts` | 39-51 | `(gov_id, question, kind, value)` | `question` is general, records or business. `kind` is website, postal, email, phone, page or office (`person` is also accepted on import). Also `label`, `source`, `updated_at`, `origin`. | yes |
| `local_answers` | 148-165 | `(gov_id, question)` | Curated local research. `contacts` is a JSON copy that **does** keep each contact's source `url`. Also `researched` (a date) and `verified`, both set per file. | yes |
| `answers` | 127-146 | `(gov_id, question)` | Scores. `contact_level`, plus `summary.offices`: the top 4 contacts with kind, value and label, and no source. | yes |
| `asked_answers` | 195-215 | `(question_id, target)` | `local` is a JSON snapshot of the place's contacts, frozen when the answer was made. | yes |
| `case_law` | 167-183 | `(state, section, cluster_id)` | `court`, `court_id`: CourtListener court identifiers, the only court "entities" there are. | yes |
| `crawl_log` | 245-253 | `gov_id` | Website scan per government: `url`, `status`, `found` (JSON), `checked_at`. | no |
| `scans` | 255-263 | `(source, state)` | When each bulk source last ran for each state (`wikidata`, `crawl`, `locus`). | no |
| `wikibase_items` | 226-231 | `key` | Maps lexflow keys to Lexipedia Wikibase QIDs: `lexflow:gov:<gid>`, `lexflow:role:<st>:<q>:<actor>`, `lexflow:statute:<st>:<ref>` and so on. | no |

These parts of `db.py` matter for any change to the tables:

* `SYNCED` (`db.py:339-350`) lists the shared tables with their keys. Every synced table must have `state`,
  `updated_at` and `origin` columns.
* `MIGRATIONS` (`db.py:353`) holds the `ALTER TABLE ... ADD COLUMN` statements that run when a database is
  opened.
* `db.upsert` (`db.py:398-430`) stamps `updated_at` with the current time whenever a row lacks it (`:412`).
  On conflict it overwrites every column the row carries (`:419-426`), and it cannot keep a stored value such as
  `first_seen`.

### 2.2 Writers

| Step or command | Code | `source` tag | Questions and kinds | Provenance kept |
|---|---|---|---|---|
| `governments` (Census of Governments 2022) | `municipal/governments.py:51-98`. Contacts are built at `:78-85`. | `census-gus-2022` | general: website, postal (the label is the officer's **title** only, `:83`) | The tag only. `URL` (`:18`) is not stored. Every rerun restamps all rows. |
| `contacts` (Wikidata SPARQL) | `municipal/contacts.py:64-99`, run by `pipeline/steps.py:295-302` | `wikidata` | general: website (P856), email (P968), phone (P1329). An email that looks like a records address is copied to the records question (`:87-89`). | The QID appears only inside the `label` string. Statement references and dates are not fetched. |
| `crawl` (home page scan) | `municipal/crawl.py:92-143`, scan at `:55-89` | `site-scan` | page (records or business), email, phone | The value's page URL is not kept. `crawl_log.checked_at` is kept per government. A site is rescanned after 30 days (`:94`). |
| `local` (curated places) | `municipal/places.py:78-111`. Contacts are mapped at `:100-105`. | `local-research` | records or business: page, office, email, phone | The `url` that names the page where the contact was found is **dropped** whenever the contact has a `value` (`:103`): 35 of the 36 curated contacts. `researched` and `verified` stay in `local_answers` only. |
| `lexflow import-contacts file.csv` | `cli.py:8`, `:79-83`, `:397-399` call `municipal/contacts.py:102-119` | `csv-import` | Any question. The kinds include `person` (`:103`). | None beyond the tag. Rows are checked against `governments` only (`:106-110`). |

Two behaviours of these writers affect freshness:

* Contact rows are never removed or aged out. A value a source stopped publishing stays in the table, with its
  old `updated_at`. Today 274 governments have more than one distinct website value.
* `contacts.wikidata()` also restamps `governments.updated_at` for each match (`contacts.py:94-95`).

### 2.3 Readers: where contacts appear

The contact ladder ranks contact levels: page, then direct, then website, then postal, then none.

* `municipal/contacts.py:122-134` (`level`) picks a government's level. A `person` or `office` row counts as
  `page`.
* The level labels and scores live in `municipal/method.py:32-35` and `:43`, with the weights at `:38-41`.

`municipal/scoring.py` scores every government:

* `:38` loads contacts for one state.
* `:54-55` sets the level and the score.
* `:63-64` picks the top 4 offices by `CONTACT_ORDER` (`:12`).
* `:70` writes kind, value and label into `answers.summary`.

`municipal/answer.py:13-36` (`answers_for`) feeds the dashboard place page, the browser-plugin lookup and the
markdown answer.

* `:35` returns every contact with its `source`.
* `:25-29` returns `local_answers.contacts`.
* `markdown()` prints only the curated contacts (`:94-101`).

`ask/local.py:122-129` (`contacts()`) supplies contacts for asked questions.

* It takes `governments.website`, then `DISTINCT kind, value, label` ordered by kind, up to 8 rows.
* It ignores the question and keeps no source, so postal rows come through as well.
* `ask/pipeline.py:238-242` freezes the result into `asked_answers.local`. 1,186 of the 1,195 asked answers carry
  this snapshot.

`publish/lexipedia.py:184-194` (`_contacts_block`) renders the label and the value, with no source and no date.
It is used in three places:

* place pages (`:232-238`), from curated contacts only;
* place-process pages (`:273-274`);
* asked pages (`:340-341`), from the frozen snapshot.

The dashboard draws contacts in three places:

* `dashboard/app.js:388-390` shows the map side panel's `summary.offices`.
* `:979-985` and `:1007` merge curated contacts with the `contacts` table.
* `:827-830` shows asked-answer contacts.

`api/app.py:298-309` (`/api/lookup`) finds a government by matching a URL against website contacts. It then calls
`answers()` (`:272-282`) for each match, and that call raises a 404 for any id that is not in `governments`.

### 2.4 Wikidata matching (`municipal/contacts.py`)

* `COUNTY_QUERY` (`:31-37`) matches counties on P882 (FIPS 6-4). `PLACE_QUERY` (`:39-45`) matches places on
  P774 (FIPS 55-3, `"<state>-<place>"`).
* Only truthy `wdt:` values are read. There are no references, no qualifiers and no `schema:dateModified`.
* Counties are matched by `county_fips` for rows of kind `county` (`:66`). Places are matched by `place_fips`
  (`:67`).
* DC's only government is typed `municipality`, so the county path never considers it. The place path did not
  match it either.
* The QID goes to `governments.wikidata` (`:94-95`). The values go to `contacts` with `source='wikidata'` and
  labels such as `Official website (Wikidata Q...)`.
* Consumers of the QID:
  * `publish/wikibase_lexipedia.py:254-255` adds an "exact match" to Wikidata, but only for the 3 governments
    that have local answers.
  * The IR has `LegalProcessModel.jurisdiction_qid` (`ir.py:243`) and `Actor.wikidata` (`ir.py:146`). Only the
    gold models fill them (`gold.py:71`, `:373`).
  * The renderers that would show them are `bpmn_xml.py:196-197`, `:207` and `:233`, `publish/dokuwiki.py:164-167`
    and `publish/wikibase.py:117-118`.

### 2.5 Actors and statutes in process models

The extraction and IR layers model actors in four places:

* `extract/schema.py:24-28` (`FActor`) is the extraction schema. Each actor has an `id`, a `name`, a `kind`
  (public-body, official, private-party, court or other-government) and an exact `source` quote.
* `extract/strategies.py:89-94` (`actor_kind`) assigns kinds by rule. `:109-124` (`Actors`) collects actors by
  normalised name.
* `extract/compile.py:255` builds the IR actors as `Actor(id, name, kind)` only, which drops `wikidata`,
  `govdirectory` and `description`.
* In `ir.py`:
  * `Actor` is at `:142-148`.
  * Steps refer to actors through `Node.bearer` (`:120`) and `Lane.actor` (`:127`).
  * `Source` (`:46-56`) is the pointer into the law text.
  * `Provenance` (`:222-229`) is kept per model, not per actor.

Statutes are identified by `(state, ref)` everywhere:

* `municipal/statutes.py:169` (`ref_of`) makes the ref;
* `located_law.section`;
* `process_models.metrics.sections`;
* the `sec.ref` column of the per-state FTS index (`ask/index.py:179-236`);
* the Wikibase key `lexflow:statute:<state>:<ref>` (`wikibase_lexipedia.py:261-280`).

`text/citations.py:15-29` and `:58` find section cross-references with regexes. Nothing finds mentions of a
named agency.

On the Wikibase side, `wikibase_lexipedia.py:329-336` makes one "legal role" item for each
`(state, question, actor id)`, and steps point to it as their bearer (`:345-347`). Role items are not linked to
any real organisation. `retire_drafts` touches only `process`, `role` and `step` keys (`:217-220`), so a new
`lexflow:agency:` key would be left alone.

## 3. The numbers

### 3.1 Contacts by source and kind

| Source | Kind | Rows | Governments |
|---|---|---:|---:|
| census-gus-2022 | postal | 38,640 | 38,640 |
| census-gus-2022 | website | 16,118 | 16,118 |
| wikidata | website | 384 | 383 |
| wikidata | email | 1 | 1 |
| wikidata | phone | 1 | 1 |
| local-research | page / phone / email / office | 10 / 10 / 9 / 7 | 3 |
| site-scan | page | 1 | 1 |
| **Total** | | **55,181** | 38,640 |

By question:

* general: 55,144 rows, 54,758 of them from Census and 386 from Wikidata.
* records: 19 rows, 18 curated and 1 from the scan.
* business: 18 rows, all curated.

Other counts:

* There are no `person` or `csv-import` rows.
* Every row has a label.
* All rows share one `origin` (this machine).
* Only **4 governments in the country** have an email or a phone number. 16,228 have something better than a
  postal address.

### 3.2 Freshness

| Source | Rows | `updated_at` (UTC) | What the date means | Age of the data itself |
|---|---:|---|---|---|
| census-gus-2022 | 54,758 | 2026-10-10 01:35:42, one stamp for every row | When the Census file was last re-imported | Census of Governments **2022** |
| wikidata | 386 | 2026-10-10 00:54:05 (md) to 12:58:33 (va) | When the SPARQL query ran | Wikidata at query time. No statement dates are kept. |
| local-research | 36 | 2026-10-10 00:53:43 | When the curated JSON was loaded | Researched 2026-10-10 and checked by a second agent. Recorded per file in `local_answers`, not per contact. |
| site-scan | 1 | 2026-10-09 18:57:52 | When the home page was fetched | Same date |

At query time every contact was less than a day old by `updated_at` (mean 0.2 to 0.8 days by source). That
figure only says when lexflow last wrote the row. **No contact has a checked or verified date.** The only checked
dates in the database are the two `crawl_log.checked_at` values: DC was scanned without error at 2026-10-09 18:57,
and one Virginia government failed at 2026-10-10 12:58.

The `scans` table records when each bulk source last ran:

* wikidata: dc 2026-10-09 18:57, md 2026-10-10 00:54 (179 matched), va 2026-10-10 12:58 (319 matched);
* crawl: dc only;
* locus: va only (2,191 matches).

### 3.3 Governments with and without Wikidata, by state

There are 38,640 active governments in 51 jurisdictions. 498 (1.3 %) have a QID. By kind:

* counties: 118 of 3,031;
* municipalities: 380 of 19,465;
* townships: 0 of 16,144.

| State | Govs | With QID | With website |  | State | Govs | With QID | With website |
|---|---:|---:|---:|---|---|---:|---:|---:|
| va | 322 | **319** | 239 | | mo | 1,332 | 0 | 377 |
| md | 180 | **179** | 136 | | sd | 1,272 | 0 | 128 |
| dc | 1 | 0 | 1 | | ia | 1,039 | 0 | 446 |
| il | 2,821 | 0 | 791 | | ne | 954 | 0 | 254 |
| mn | 2,718 | 0 | 773 | | ga | 689 | 0 | 416 |
| pa | 2,625 | 0 | 1,127 | | ok | 664 | 0 | 157 |
| oh | 2,322 | 0 | 847 | | nc | 652 | 0 | 469 |
| ks | 1,948 | 0 | 340 | | nj | 585 | 0 | 492 |
| wi | 1,921 | 0 | 843 | | ar | 575 | 0 | 141 |
| mi | 1,856 | 0 | 1,034 | | ca | 539 | 0 | 513 |
| nd | 1,711 | 0 | 121 | | ky | 533 | 0 | 249 |
| in | 1,661 | 0 | 366 | | al | 529 | 0 | 249 |
| ny | 1,581 | 0 | 1,008 | | me | 500 | 0 | 268 |
| tx | 1,477 | 0 | 876 | | fl | 478 | 0 | 404 |
| tn | 437 | 0 | 243 | | ms | 380 | 0 | 107 |
| la | 364 | 0 | 147 | | ma | 356 | 0 | 310 |
| co | 332 | 0 | 223 | | wa | 320 | 0 | 257 |
| sc | 317 | 0 | 182 | | vt | 291 | 0 | 148 |
| wv | 285 | 0 | 98 | | ut | 283 | 0 | 190 |
| or | 276 | 0 | 201 | | nh | 244 | 0 | 201 |
| id | 242 | 0 | 128 | | mt | 181 | 0 | 71 |
| ct | 179 | 0 | 163 | | ak | 164 | 0 | 58 |
| nm | 138 | 0 | 81 | | wy | 122 | 0 | 79 |
| az | 106 | 0 | 100 | | de | 60 | 0 | 44 |
| ri | 39 | 0 | 38 | | nv | 35 | 0 | 32 |
| hi | 4 | 0 | 4 | | | | | |

How the Wikidata matches line up with Census:

* 115 matched governments got no website from Wikidata.
* 58 got a website from Wikidata where Census has none.
* 132 Wikidata websites differ from the Census website, after normalising the scheme and the trailing slash.

Census websites are stored as `http://` in 16,104 cases and as `https://` in 66. This is because
`governments._clean_url` (`governments.py:42-48`) adds `http://` when the Census value has no scheme.

### 3.4 Answers, actors and the Wikibase mapping

**Answer contact levels.** There are 77,280 answers: 38,640 governments times 2 questions.

| Level | Answers | Share |
|---|---:|---:|
| postal | 44,824 | 58.0 % |
| website | 32,448 | 42.0 % |
| page | 6 | |
| direct | 2 | |

**Actors.** There are 364 actors in 87 of the 104 process models: 88 in Claude-reviewed models and 276 in
single-extraction models.

* By kind: public-body 155, private-party 127, court 38, official 29, other-government 15.
* There are 166 distinct names. The most common are organizer (34), requester (25), **secretary of state (22)**,
  responsible official (20), court (16), person (15) and public body (10).
* The models of 23 states name a Secretary of State. Other named bodies include "state corporation commission",
  "commissioner of the revenue", "attorney general", "county clerk", "superior court" and "filing office".
* Every actor carries an exact `source.section` quote, which makes it a ready anchor for an "is" link.

**Courts.** `case_law` uses 7 CourtListener courts in its 150 rows. `municipal/caselaw.py:24-38` (`COURTS`) maps
98 court ids across all 51 jurisdictions.

**Wikibase map.** `wikibase_items` holds 1,413 keys:

| Key type | Keys |
|---|---:|
| statute | 496 |
| step | 495 |
| role | 199 |
| courtlistener case | 117 |
| jurisdiction | 52 |
| process | 48 |
| class | 3 |
| gov | 3 (DC, Baltimore and Charlottesville) |

## 4. Gaps that matter for the extension

1. **`updated_at` is not a verification date.** Each writer restamps its rows, and `db.upsert` adds the current
   time (`db.py:412`). Rerunning the `governments` step makes 54,758 Census 2022 values look a few hours old.
2. **No per-contact source.** The Wikidata QID lives only in the label. The scan keeps the page per government
   (`crawl_log`), not per contact. The curated source URL is dropped at `places.py:103`.
3. **No retirement.** Rows are never marked gone. A changed website adds a second row (274 governments have two
   or more).
4. **Agencies are flattened into governments' contacts.**
   * Charlottesville's records contacts include a state body, the Virginia FOIA Council.
   * Baltimore's include the Maryland Public Access Ombudsman and several city departments (Housing, Public
     Works, the Inspector General, the Law Department, the Board of Finance).
   * DC's include the Office of Tax and Revenue, the Department of Licensing and Consumer Protection, and the
     Department of Buildings.

   Without an agency entity, a body that serves every government in a state would need one copy of its contact
   rows per government (322 in Virginia).
5. **Actors are unlinked strings.** The IR fields are there but never filled (`compile.py:255`). Wikibase role
   items are duplicated per question and are not tied to any organisation.
6. **Turso cannot take new columns yet.**
   * `turso.remote_schema` (`store/turso.py:128-137`) sends only `CREATE TABLE IF NOT EXISTS`.
   * `MIGRATIONS` run locally only.
   * `push` selects every local column (`turso.py:181`, `:190`).

   So a column added to a synced table breaks `sync push` until the remote table gets the same `ALTER`.
7. **Privacy.** `import_csv` accepts `kind=person` (`contacts.py:103`), and the ladder rewards it (`:125`). No
   `person` rows exist. Census contacts carry only an officer's title (`governments.py:83`).

## 5. Extension points

### 5.1 Agency entities beside governments

**New table.** Add this to `SCHEMA` right after `governments` (`db.py:37`), and to `SYNCED` (`db.py:339-350`) as
`"agencies": ("agency_id",)`. `turso.remote_schema` then picks it up without further changes.

```sql
CREATE TABLE IF NOT EXISTS agencies (
  agency_id TEXT PRIMARY KEY,   -- "a:va:state_corporation_commission"; a government's own office: "a:47210400100000:clerk"
  state TEXT NOT NULL,
  name TEXT NOT NULL,
  kind TEXT NOT NULL,           -- department | board | commission | court | clerk | office | ombudsman | council | other
  level TEXT NOT NULL,          -- state | local | regional | federal
  gov_id TEXT,                  -- the government a local office belongs to; NULL for state bodies
  parent_id TEXT,               -- a division inside a department
  aliases TEXT,                 -- JSON: the names statutes and models use ("the Commission", "clerk of the circuit court")
  wikidata TEXT,
  courtlistener TEXT,           -- court id, for courts
  website TEXT,
  source TEXT, source_url TEXT, checked_at TEXT,
  updated_at TEXT NOT NULL,
  origin TEXT
);
CREATE INDEX IF NOT EXISTS agencies_state ON agencies(state);
```

The `a:` prefix keeps agency ids apart from 14-digit Census GIDs, which `places.resolve` recognises by regex
(`places.py:33`).

**Contacts for agencies.** Store an agency's contacts in `contacts`, with the `agency_id` in the `gov_id`
column. The primary key, the `SYNCED` keys and the upsert code stay as they are, and SQLite cannot change a
primary key without rebuilding the table anyway. These places assume `gov_id` is a government and need a guard:

* `api/app.py:305-309`: a website match on an agency would 404 the whole lookup. Filter out `gov_id LIKE 'a:%'`,
  or return agency matches separately.
* `municipal/contacts.py:106-110`: `import_csv` checks ids against `governments` only. Also accept `agencies`.
* `pipeline/steps.py:95` and `:103`: the checklist counts `DISTINCT gov_id`. Exclude agencies.
* `municipal/crawl.py:95-99`: the scan targets come from `governments`. To scan agency sites too, add
  `UNION SELECT agency_id, state, website FROM agencies`.

**Seeds.** All of these are read-only and organisation-level:

| Seed | Where it is now | What it gives |
|---|---|---|
| Courts | `caselaw.COURTS` (`caselaw.py:24-38`) and `case_law.court` and `court_id` | 98 appellate courts with CourtListener ids |
| State bodies named in models | `process_models.facts.actors` with kind public-body, official, court or other-government | For example the Secretary of State in 23 states, and the State Corporation Commission |
| Curated research | Contact labels in `curated/places/*/*.json` | About 20 named departments, ombudsmen and councils, each with its source URL |
| Local offices | Census postal labels (`Clerk` 2,335, `City Clerk` 2,173, `Town Clerk` 980, `Treasurer` 678, and so on) | Clerk and treasurer offices as `a:<gid>:clerk` (titles only) |
| Wikidata | A new query beside `COUNTY_QUERY` and `PLACE_QUERY` (`contacts.py:31-45`), for example government agencies located in a state | QIDs plus P856, P968 and P1329 for organisations only |

**Loader and step.** Put the loader in a new `municipal/agencies.py`, modelled on `contacts.wikidata`
(`contacts.py:64-99`). Register it as a step in `pipeline/steps.py`, next to `contacts` (`:504-507`), with an
`st_*` and `run_*` pair like `:90-97` and `:295-302`. `_mark_scan` (`:45-47`) records each run per state.

**Answers.**

* `scoring.run` (`scoring.py:38-39`, `:53-55`) can give a government credit for the contacts of agencies that
  serve it, through the `serves` links in 5.2.
* `ask/local.contacts` (`local.py:122-129`) and `answers_for` (`answer.py:35`) can list those contacts under a
  heading of their own, such as "State offices".

**Wikibase (later; no network writes now).** Add `Loader.agencies()` next to `jurisdictions()`
(`wikibase_lexipedia.py:242-259`), with the key `lexflow:agency:<id>`, "part of" the jurisdiction item, and an
"exact match" to Wikidata. The classes would go in `CLASSES` (`:33-37`).

### 5.2 Links from process-model actors and statute mentions

Use one link table for all link types. Its subject keys reuse the Wikibase key scheme that already exists
(`role:<st>:<q>:<actor>`, `statute:<st>:<ref>`, `gov:<gid>`; see `wikibase_lexipedia.py:217`). Add it to `SCHEMA`
and to `SYNCED` as `("subject", "relation", "object")`.

```sql
CREATE TABLE IF NOT EXISTS entity_links (
  subject TEXT NOT NULL,     -- "role:va:business:commission" | "statute:va:13.1-1011" | "gov:47210400100000"
  relation TEXT NOT NULL,    -- is | mentions | serves | appeals-to | part-of
  object TEXT NOT NULL,      -- an agency_id, or "gov:<gid>"
  state TEXT NOT NULL,
  question TEXT,
  method TEXT,               -- curated | alias-match | wikidata | claude-reviewed
  score REAL,
  section TEXT, quote TEXT,  -- the words that make the link (the actor's source quote, the mention span)
  source TEXT, checked_at TEXT,
  updated_at TEXT NOT NULL, origin TEXT,
  PRIMARY KEY (subject, relation, object)
);
```

**Actor links (`is`).** Resolve actors after a model is built, from `facts.actors` (name, kind, source quote)
against `agencies.aliases`.

* Write the links at read time, or in a separate step, **not** in `extract/compile.py` or `FActor`. That way the
  extraction schema, the facts JSON and the benchmark inputs do not change.
* Generic roles ("public body", "custodian", "requester") stay unlinked. Specific ones ("secretary of state",
  "state corporation commission", "superior court") link to an agency.

Consumers of actor links:

* `municipal/stats.py:193-209` (`steps_of`) turns `who` into a name plus an agency id. That one change feeds
  `lexipedia.py:146-150` and `:257-262`, and `answer.py:76-80`.
* `ir.Actor` (`ir.py:142-148`) gets an optional `entity` field, filled when a model is loaded for rendering.
  `bpmn_xml.py:196-197` already writes actor `wikidata` and `govdirectory` into extension elements, and would
  carry `entity` the same way.
* `publish/dokuwiki.py:164-167` already has a Wikidata column in its actors table.
* `wikibase_lexipedia.py:330-336` links each role item to its agency item.

**Statute mentions (`mentions`).** Write a finder modelled on `text/citations.py` (`PATTERNS` at `:15-29`,
`find_citations` at `:58`) that matches agency alias regexes for each state.

* Run it over the sections the models use, the same set `wikibase_lexipedia.statutes()` collects (`:282-299`:
  `metrics.sections` plus `located_law`).
* Optionally also run it over the per-state FTS `body` table (`ask/index.py:189-197`), so that asked questions
  can name the office.
* Register it as a step like `crawl` and `locus` (`pipeline/steps.py:528-540`).
* The subject is `statute:<state>:<ref>`, using the same `ref` as `statutes.ref_of` (`statutes.py:169`).
* A parallel workflow is building cross-reference support (`lexflow/law/*`, `fixtures/xref/*`). Its section keys
  should be adopted here so that the two kinds of link join.

**Government links (`serves`).** These say which agency handles a question for which government, for example
`gov:<every VA gid> -serves(records)-> a:va:foia_council`. Use `subject='state:va'` to cover a whole state with
one row. Scoring and answers read these links (5.1).

### 5.3 Per-contact provenance and last-verified fields

**Columns.** Add them through `MIGRATIONS` (`db.py:353`):

```sql
ALTER TABLE contacts ADD COLUMN source_url TEXT;   -- the page or record the value was read from
ALTER TABLE contacts ADD COLUMN vintage TEXT;      -- the source's own date: '2022' for Census GUS, Wikidata modified date, curated 'researched'
ALTER TABLE contacts ADD COLUMN first_seen TEXT;
ALTER TABLE contacts ADD COLUMN checked_at TEXT;   -- last time a fetch saw this exact value at source_url
ALTER TABLE contacts ADD COLUMN status TEXT;       -- ok | gone | changed | unreachable
ALTER TABLE contacts ADD COLUMN verified_by TEXT;  -- machine | claude-two-agent | reviewed (a role, never a name)
```

Two things must change alongside the columns:

* **Sync.** `turso.ensure_schema` (`turso.py:139-140`) must apply the same `ALTER`s to the remote database, and
  ignore the "duplicate column" error. Otherwise the first `sync push` after the migration fails.
* **Upsert.** `db.upsert` needs a `keep=` option, so that `first_seen` is written as
  `COALESCE(contacts.first_seen, excluded.first_seen)` on conflict (`db.py:419-426`).

**Writers.**

| Writer | Change |
|---|---|
| `governments.load` (`governments.py:78-85`) | `source_url=URL` (`:18`), `vintage='2022'`, no `checked_at`, so Census rows no longer look fresh |
| `contacts.wikidata` (`contacts.py:80-92`) | `source_url=https://www.wikidata.org/wiki/<qid>`, `checked_at=ts`. Optionally select `schema:dateModified` in the queries (`:31-45`) as the vintage. Keep the QID out of the label. |
| `crawl.run` (`crawl.py:111-126`) | `source_url=res["url"]` (the final page), `checked_at=ts`. Mark this government's earlier `site-scan` rows that were not seen again as `status='gone'`. |
| `places.load_local` (`places.py:100-105`) | `source_url=c["url"]` (currently lost for 35 of 36 contacts), `checked_at=spec["researched"]`, `verified_by` from `spec["verified"]` |
| `import_csv` (`contacts.py:102-119`; documented in `cli.py:8`) | Optional `source_url` and `checked_at` columns. Drop `person` from the documented kinds. |
| New re-check job | For rows whose `checked_at` is older than N days, fetch `source_url` again and confirm the value is still there, at no more than 1 request per second per host. Reuse `crawl._allowed` and `_get` (`crawl.py:29-52`). |

**Readers.**

* `ask/local.contacts` (`local.py:122-129`): select the new columns, skip `status='gone'`, prefer rows for the
  question being asked, and leave out postal rows when better ones exist.
* `scoring.run`: put `checked_at` and `source` into `summary.offices` (`scoring.py:70`). An optional age penalty
  can be set in `method.DEFAULTS` (`method.py:37-47`), for example `contact_stale_days` and
  `contact_stale_factor`, and applied at `scoring.py:55`.
* `answers_for` (`answer.py:35`) returns the new columns. `markdown()` (`answer.py:94-101`) and
  `_contacts_block` (`lexipedia.py:184-194`) add "source, checked YYYY-MM-DD" to each contact.
* `dashboard/app.js:982-985` and `:1007`: show the date as a tooltip or a muted suffix.
* The `asked_answers.local` snapshot (`ask/pipeline.py:238-242`): store `checked_at` with each contact, or
  re-resolve contacts when the page is rendered, so that wiki pages do not show stale contacts as current.

### 5.4 Cautions

* Do not change `FActor`, `extract/compile.py` or the facts JSON to add links. Those feed the benchmark, and
  links can live in `entity_links` instead.
* Agencies and links record organisations and official office channels only: a website, a published general
  email or phone, an office mailbox. Never record a named official's personal contact details.
* Every new synced table needs `state`, `updated_at` and `origin`, and an entry in `SYNCED`.

## 6. Suggested order

1. **Provenance columns.** Add the columns and the `ensure_schema` change. Then fix the five writers, starting
   with the cheap ones: curated source URLs, Census vintage, and Wikidata source URLs.
2. **Agencies.** Add the `agencies` table, seeded from `caselaw.COURTS` and the curated research. Add the contact
   ownership guards at `app.py:305`, `contacts.py:106` and `steps.py:95` and `:103`.
3. **Actor links.** Add `entity_links` with `is` links for the named state bodies in the 22 Claude-reviewed
   models. Render them through `stats.steps_of`.
4. **Statute mentions and `serves` links.** Add these once the cross-reference keys from the parallel workflow
   are settled.
5. **Re-check job and freshness in scores.**
