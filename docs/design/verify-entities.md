# Verification: the entities and contacts plan

An adversarial review of [entities-contacts.md](entities-contacts.md) and the files it rests on:
[entities-sources.md](entities-sources.md), [entities-codebase.md](entities-codebase.md),
`fixtures/entities/agencies.json`, `fixtures/entities/contacts_pilot.json` and `scripts/contacts_check.py`.

* Reviewed 2026-10-10. No repository file was changed except this new one.
* The database was opened read-only (`mode=ro`). Every number below was recomputed from the files, the DB or a
  live read-only request.
* Network use: read-only GETs (and one HEAD) with the User-Agent
  `lexflow-research/0.1 (https://github.com/alibama/lexflow)` and 15 s timeouts. Hosts: Wikidata API (29 requests),
  WDQS (4 queries, one at a time), lexipedia.wikibase.cloud (1), lexipedia.xyz (3 `export_raw` reads),
  govdirectory.org (7), GitHub API and raw files (6). Nothing was edited, posted, sent or submitted.
  * One lapse: the `robots.txt` GET and the `sitemap.xml` HEAD to govdirectory.org went out less than 1 s apart.
    Every other pair of requests to the same host was at least 1.1 s apart.
* This note names no individual and reproduces no email address or phone number.

## 0. Verdict

The plan is sound in its main lines. The source claims and nearly all of its numbers hold up. It never edits
Wikidata or the wikis, and it never sends anything on its own. Four things need fixing before it is built:

1. **A privacy exposure that already exists.** Two staff mailboxes in first.last form are live on two public
   DokuWiki pages (§3.1; since removed from the current pages, see the status note there). The plan's own guard
   would let addresses like these through (§3.2).
2. **Sync loses check results.** Turso sync is whole-row last-writer-wins on `updated_at`. Check columns that
   ride on `contacts` can be overwritten by another machine's reload. Daily checks would also mark every state
   "re-score" on the checklist (§5, items 1 and 2).
3. **Re-runs create duplicates.** `contact_proposals` and `upstream_suggestions` have no unique key. The agency
   seed has no rule for matching existing keys. The places loader puts back the agency contacts that the plan
   moves out of city rows (§5).
4. **Some classifier rules over-reach.** A redirect to an unofficial domain is still shown. Spam-title
   quarantine hides pages on first sight, so a gaming regulator's page or a single CJK character in a title is
   enough. Parked domains are called both `broken` and `quarantined` (§4).

## 1. The relayed user instruction about a named researcher

The user asked that the fourth author of the LOCUS citation not be listed explicitly in the app, because they
have not spoken personally yet.

* The entities plan and its fixtures do not name this person. Rule 7 in §5 of the plan ("no person is named …
  as a credit without their agreement") agrees with the request.
* The app still lists the person in full in these places (line numbers as re-checked in the privacy pass later
  the same day):
  * `lexflow/pipeline/credits.py:91` (the LOCUS `cite=` string);
  * `scripts/viewer_template.html:224`, and the built `out/viewer/lexipedia-viewer.html:224`;
  * also outside the app: `scripts/make_locus_fixture.py:5`, `:78`, `fixtures/locus/va_samples.json:4` and
    `docs/design/credits-research.md:42`.
* `docs/design/verify-credits.md:27` currently accepts "researchers are named only as authors in citations".
  That conflicts with the request.
* `credits.py` was being edited by another workflow during this review (modified 10:58), so this review did not
  touch it.
* A form that keeps the attribution CC BY needs without naming the person: "Peskoff et al. (2026), *Freeing the
  Law with LOCUS* …, arXiv:2606.19334", with the DOI link and the dataset organisation (LocalLaws).
* The `Step.credits` comment asks for the citation "exactly as the maker asks". The user's request outranks
  that, so the comment's rule needs an exception.

## 2. Confirmed

### 2.1 Govdirectory (opened live)

| Claim | Evidence |
|---|---|
| 46 countries, 21,105 organisations, 46,431 contact points, last updated 2026-09-25 | statistics page |
| US 374 rows, North Carolina 607, New York 159; no page for Virginia | 375, 608 and 160 `<tr>` rows (one is the header); `/united-states/virginia/` returns 404 |
| WikiProject US subpages exist only for New York and North Carolina | MediaWiki API: VA, FL, CA, DC, TX, MD, IL and WA are missing |
| `robots.txt` points to `sitemap.xml` | fetched |
| `publiccode.yml`: `mainCopyrightOwner: Govdirectory`, `developmentStatus: stable` | fetched |
| Contributions recognisable as AI-generated lead to a block | CONTRIBUTING, section "AI contributions" |
| Two maintainers, "for now" | README |
| website-cache last pushed 2026-01-02; health-check-service last pushed 2021-07-26 | GitHub API |
| Deploys on 2026-04-06, 07-29, 08-28, 08-29 and 09-25 | `gh-pages` commits (also 01-24, 02-21 and 03-12) |
| The Error reports page holds about seven threads | 8 sections |

### 2.2 Wikidata (wbgetentities and WDQS, read-only)

* **Q107179384 (Florida Division of Corporations).**
  * P31: registration authority, government agency, database, state agency of Florida. P1001 Florida. P749 is
    Q11969252.
  * Three P856 values with start/end qualifiers (1999–2016, 2016–2023, 2023–), all of normal rank.
  * P968 and P1329 are each referenced to dos.fl.gov, retrieved 2024-04-11. All as stated.
* **Q11969252 (Florida Department of State).** P31 government agency only. P131 Tallahassee, no P1001. Its only
  P856 is the dos.state.fl.us URL, referenced only by P143, "Norwegian Wikipedias" (Q191769).
* **Other items.**
  * Q5020429: P856 referenced only by P143 English Wikipedia.
  * Q7603136: preferred P856, plus the business-search URL referenced to the GLEIF RA list (Q106448148).
  * Q7444418 is a position with no website.
  * Q138637634: P856 has no reference.
  * Q7024182 and Q3477292 are positions with P1308.
* **Classes.**
  * Q139489412 has exactly 8 instances: 4 in Alabama, plus Santa Clara, San Diego, Duval and Tulsa.
  * Per-state subclasses of Q20857085: NC 409, NY 98, CA 69, MD 27, TX 16, FL 13, VA 10, IL 6, WA 4. There is
    none for DC.
  * `?c wdt:P279* wd:Q327333` returns 6,387.
* **"No item" bodies.** 8 of the fixture's 15 were spot-checked: MD SDAT, VA DHP, DC OCFO, VA FOIA Council, TX
  Board of Criminal Justice, VA DPOR, TX State Auditor and TX OCA. `wbsearchentities` and full-text search found
  no item for any of them.

### 2.3 Lexipedia Wikibase

P5 instance of, P6 subclass of, P8 exact match (url), P9 part of, P15 applies to jurisdiction, P17 bearer, P22
citation (string) and P25 legal identifier (external-id) all exist with the meanings the plan uses.
`wikibase_items` gives `lexflow:statute:fl:607.0201` = Q168 and `lexflow:role:fl:business:department` = Q776.

### 2.4 Numbers in the plan that match the files

* **`agencies.json`.**
  * 144 entries: 98 specific and 46 generic.
  * Of the specific bodies: 69 exact, 14 parent only, 15 none.
  * Exact-match kinds: 55 organisations, 5 courts, 5 positions, 4 untyped.
  * 61 exact matches have a website. 2 have an email or phone. 76 distinct body QIDs.
  * Govdirectory: 6 listed bodies (4 NC, 2 NY) and 1 listed parent.
* **`contacts_pilot.json`.**
  * 86 items in 49 governments.
  * Websites: 21 stale of 49 verifiable, 42.9 % (Wald 95 % CI ±13.9). All kinds: 31.3 %.
  * 3 of 55 hijacked. 7 NXDOMAIN. 8 moved, 6 of them to `.gov`. 4 broken pages that answered 200. 6 bot walls
    (5 × 403, 1 × 503).
  * Email: MX found for 9 of 9. 1 address on a fetched page, 1 on a retired domain.
  * 2.07 requests and 2.79 s per URL. One 60.1 s case. At most 10 requests per domain.
  * Wikidata: 6 moved governments, and only 1 has the new domain in P856.
  * Stale share where Census and Wikidata agree: 27.3 % (3 of 11). Census alone: 48.4 % (15 of 31).
  * A full sweep: 16,204 distinct URLs, 33,542 GETs, 1.57 h with 8 workers. Busiest domains: govoffice.com 108,
    govoffice2.com 75, in.gov 52. 498 government QIDs, 10 batches.
  * 2 personal mailboxes skipped and not written to the fixture. The fixture and the docs contain neither
    address.
* **DB.**
  * 55,181 contacts; postal 70.0 %. 36 curated contacts, 35 of them with their source URL dropped. 274
    governments have more than one website.
  * 1,186 of 1,195 asked answers carry a snapshot: 1,818 distinct contacts for 861 governments (951 websites, 860
    postal, 7 other).
  * 364 actors. In the 22 reviewed models: 88 actors, 33 private parties. The 55 others: public body 21, court
    13, other government 12, official 9.
  * `caselaw.COURTS` holds 98 court ids in 51 jurisdictions.
  * Wikibase map: 199 roles, 496 statutes, 3 governments.
* **Arithmetic.** About 650 URLs a day × 2.07 ≈ 1,350 GETs. 650 × 2.8 s ÷ 8 workers ≈ 3.8 min. The busiest host
  gets about 7.5 GETs a day.

### 2.5 No edits and nothing sent

* **The plan.**
  * D11 and §4: lexflow drafts only, holds no Wikidata credentials, and a person pastes QuickStatements.
  * §3.5: GET only. No SMTP, forms or third-party validators.
  * D12 and §3.7: every publish and Wikibase load is user-triggered, after a dry run. New Wikibase properties wait
    for the user's go-ahead.
* **The pilot script.**
  * The DB is opened with `mode=ro` and `query_only`.
  * HTTP is `GET` only. The Wikidata API is called with GET (`wbgetentities`).
  * Email checks are DNS only, through the system resolver. No port-25 code exists.
  * The only file it writes is OUT.json. Importing `lexflow.config` has no side effects.

### 2.6 Code references that hold

| Area | References |
|---|---|
| `db.py` | `:339` SYNCED, `:353` MIGRATIONS, `:419-428` the conflict clause, `:433` bump |
| `jobs.py` | `:26` GROUPS, `:30` BEAT = 30 s, `:133` Runner.run |
| `turso.py` | `:128-140` |
| `wikibase_lexipedia.py` | `:209` retire_drafts ignores keys other than process, role and step; `:242` jurisdictions; `clear` on every update |
| `contacts.py` | `:31-45`, `:102-119`, `:103`, `:125` |
| `crawl.py` | `:42`, `:94-99` |
| `governments.py` | `:18`, `:78-85`, `:83` |
| Other | `places.py:100-105`; `compile.py:255`; `dashboard/app.js:388` |

The plan's `Step(...)` call fits the dataclass (`steps.py:30-44`).

## 3. Privacy

### 3.1 Live exposure of staff mailboxes (needs the user)

* **What.** Two Baltimore `local-research` contacts are first.last-shaped mailboxes on a `.gov` domain. The
  pilot's guard rejected both (the pilot's "2 personal mailboxes").
  * Their labels are "Department of Public Works MPIA contact" and "Office of the Inspector General PIA
    requests".
* **Where.**
  * Stored in `curated/places/md/baltimore.json`, `local_answers` and `contacts`.
  * Present today, by a read-only `export_raw` check, on the public pages `lexflow:md:baltimore` and
    `lexflow:md:baltimore:records` at lexipedia.xyz.
* **Why the plan's design does not catch them.** They breach the plan's rule 5.2 ("staff contacts in the places
  models"), but nothing in the plan removes them:
  * The guard in phase 1 runs on writes to `contacts`. `render_place` and the place-process pages render from the
    `local_answers.contacts` JSON (`lexipedia.py:232-238`, `:273-274`). Asked pages render from the
    `asked_answers.local` snapshot.
  * `places.load_local` would mark them `ok` with `verified_by='two-agent'`. The two-agent research did not
    remove them.
  * The benchmark freeze (§6: "do not edit … curated data") blocks the fix to the curated file.
* **Needed.** A privacy carve-out from the freeze. A one-off purge from the curated file and both tables, then a
  republish of the two pages after a dry run. The user decides and triggers both.
* **Not done here.** This review edited and republished nothing.
* **Status after this review (privacy pass, 2026-10-10).** The plan records the purge (D14, §5.2 "The Baltimore
  case"). A read-only check later the same day found no first.last-shaped mailbox in
  `curated/places/md/baltimore.json`, in the Baltimore rows of `contacts` and `local_answers`, or in the
  `export_raw` text of the two live pages. The plan notes that old revisions of the two pages still hold the
  addresses until a wiki admin removes them (§8.7); this check did not open old revisions.

### 3.2 The `is_office_mailbox` guard

The plan makes this test the write-time guard for every writer. It is not fit for that job.

* **False positives.** It matches role words as substrings, so made-up personal mailboxes pass: `courtney.smith`
  (court), `jtownsend` (town), `kwaters` (water), `aborowski` (boro), `firestone.j` (fire), `apressley` (press),
  `boardman.t` (board), `publicover.d` (public) and `jmailer` (mail). `pia.jones` and `cor.devries` pass through
  `ROLE_SHORT` tokens that are also first names. `mayor.brown` passes too.
* **False negatives.** Three of the four office mailboxes in `agencies.json` fail: DC MPD, the NY Division of
  Corporations and the WA Corporations and Charities Division. The acronym rule needs the upper-case acronym in
  the same row of text.
* **Needed.**
  * Match whole tokens only.
  * Refuse a mailbox whose local part has the shape *name.name* or *initial+surname*, unless it is on an
    allowlist.
  * Accept role mailboxes found on the owner's official page, or ones Wikidata references to that page.
  * Send everything else to review, never straight to a public surface.

### 3.3 Other privacy points

* The three plan docs contain no email address, no phone number and no person's name.
* Census postal rows have no attention line (0 rows contain ATTN or c/o), and their labels are titles.
* **Open question.** Many township and small-town Census addresses (16,144 townships) are probably an officer's
  home or PO box. Showing them as "Census 2022" on public surfaces may publish a residence. Consider showing
  postal rows only for governments above a population floor, or only once phase 6 verifies them.
* Reading Wikidata with `wbgetentities` returns P1308 and the "led by" claims along with everything else. The
  plan should say these are dropped at parse and never stored. "Never read" is not literally possible with that
  API.

## 4. Wrong, with evidence

### 4.1 Plan statements that are false or imprecise

1. **Line drift.** `steps.py`, `api/app.py` and `dashboard/app.js` were edited at 10:54–10:55, after the survey.
   * `steps.py:95` and `:103` are now `:101` and `:109`. `Step("crawl")` `:528` is now `:546`. `_mark_scan` is
     at `:51`.
   * `/api/lookup` is now at `app.py:303-315`.
   * `app.js` `:979-985` is now about `:998-1000`, and `:827-830` is now about `:846-849`.
2. **`ensure_schema`.** The plan describes `turso.ensure_schema` (`turso.py:139`) as one "which ignores duplicate
   column errors". Today it sends only `CREATE … IF NOT EXISTS`. `Turso.pipeline` raises on the first statement
   error (`turso.py:111-113`), so a failing `ALTER` would abort every push. The ALTERs must go in their own calls,
   with that one error filtered out.
3. **"Census and Wikidata differ for 132 governments" (§2.5).** The plan uses the figure for registrable domains.
   * Of 273 governments with both: 131 differ when only the scheme and trailing slash are normalised. 100 differ
     when `www.` is also ignored. 94 differ by registrable domain.
   * The review-queue rule concerns registrable domains, so the figure there is 94.
4. **"34 of 55 sites were upgraded this way" (§3.4).** The `https_upgrade` flag also fires on all 8 moved sites.
   Same-host `http`→`https`/`www.` normalisations are **26 of 55**.
5. **"The home-page check found 3 of 11" phones.** 2 were found on the home page and 1 on another official page.
6. **`wikidata_match` values "as in agencies.json".** The fixture's `match` values are `exact`,
   `parent body only` and `none`. Positions are recorded in `item_kind`. The seed needs an explicit mapping.
7. **Office-type `class_qid`s.** §1.2 lists 4. The fixture has 8. It adds Q7707643 Texas District Courts,
   Q16960472 Virginia Circuit Court, Q5152849 Commissioner of the Revenue (no P31) and Q5153671 Commonwealth's
   Attorney. Q5153671 is a **position** (P31 Q4164871), so by rule 5.4 it is only an identity hint.
8. **The worked example.** Q775 is `lexflow:role:fl:business:organizer`, the organiser of an LLC under ch. 605.
   The plan makes it an instance of `concept:incorporator`, taken from § 607.0201 of the Business Corporation
   Act.
   * § 607.0201 says who may act as incorporator. The chapter's definitions are in § 607.01401.
   * Use `concept:organizer`, or a broader founder concept with both as subtypes.
9. **Parked domains: `broken` or `quarantined`?**
   * §2.2 and §3.4 say parked → `broken` (two strikes).
   * §2.2 (quarantine row) and §3.3 say "spam, gambling **or parked**" → quarantined on first sight.
   * Pick one. Parked usually means lapsed, not hostile, so `broken` fits.
10. **The phase-2 regression test.** It says the classifier "reproduces the pilot's 86 classes". The plan's own
    rules differ from the pilot's:
    * The plan has no 418 rule, and no "5xx + challenge header or bot-wall marker → unverifiable" rule. Under the
      plan, the pilot's 503 bot wall becomes `broken`.
    * Spam becomes `quarantined` where the pilot said `broken`.
    * NXDOMAIN needs two strikes.

    The test needs a written mapping. Replaying `classify_web` offline from the fixture with an empty body gives
    64 of 66 web items. The 2 misses (one name found only in the body, and the 503 bot wall) need recorded
    `name_present` and challenge-header fields.
11. **"Deployed by hand about monthly" (§4).** The deploy log has a 114-day gap, from 2026-04-06 to 2026-07-29. An
    applied fix can take up to about 4 months to show on Govdirectory.

### 4.2 Pilot behaviour that differs from what the plan assumes it reuses

* `wikidata_p856` skips only deprecated values and keeps end-dated ones.
  * Q107179384's sunbiz.org URL (end 2016, normal rank) would count as current.
  * The recheck must drop values with P582, as §1.6 says.
* `maxlag`: the pilot drops `maxlag` on its third attempt.
  * Today a `maxlag=5` read was refused at once: WDQS lag (about 15 s) is counted in maxlag.
  * Decide the policy: back off on `Retry-After`, then defer the batch to the next run instead of dropping
    `maxlag`.
* No robots.txt. The pilot never fetched robots.txt, so the regression fixture comes from a run that ignored it.
* No item deadline. The plan's "30 s per item including the fallback" needs an overall per-item deadline.
  Today each GET has `(15, 15)` timeouts plus a 15 s body loop. Up to 8 hops, a fallback and a client redirect
  come on top, which is how the 60 s case happened.

## 5. Schema fit, sync and re-runs

**Fits.**

* `agencies`, `office_types` and `entity_links` all carry `state`, `updated_at` and `origin`. With an entry in
  `SYNCED`, `turso.remote_schema()` creates them and their indexes remotely.
* `entity_links.question NOT NULL DEFAULT ''` avoids the NULL-in-primary-key duplicates of the codebase draft. A
  test showed SQLite 3.40 stores two rows for `('x', NULL)`.
* SQLite 3.40 accepts the unquoted `end` column in `db.upsert`'s generated SQL.
* The `agencies` key mapping in `wikibase_items` stops duplicate Wikibase items.

**Gaps.**

1. **Lost updates through sync.**
   * `push` selects by `updated_at`, and the remote upsert applies `WHERE excluded.updated_at >= …`. `pull` calls
     `db.upsert(newer_only=True)`. Both are whole-row.
   * So a check write must bump `updated_at`, or it never syncs. The plan does not say whether it does.
   * Then any newer write of the same row on another machine replaces its check columns with stale ones. For
     example, a Census reload on a machine that had not pulled first.
   * Fixes: keep check state in its own synced table keyed by the contact's primary key, with its own
     `updated_at`. Or merge check columns by `checked_at`. Or run `recheck` on one designated machine.
2. **The checklist goes stale every day.** `st_score` (`steps.py:161-172`) marks a state "re-score" when any
   contact's `updated_at` is newer than its oldest answer. A daily recheck would flag every checked state. Leave
   check-only writes out of that test.
3. **`status` default.** Use `ADD COLUMN status TEXT NOT NULL DEFAULT 'unchecked'`, locally and on Turso, so that
   the 55,181 rows are `unchecked` without a backfill. A backfill would not bump `updated_at`, so it would not
   sync.
4. **The `us` state.** Federal rows (`state='us'`) are dropped whenever sync gets a state list
   (`turso._state_filter`; the dashboard's pull at `app.py:220`). The filter needs `OR state='us'`; the plan only
   says "must include us".
5. **Duplicates on re-runs.**
   * `contact_proposals` and `upstream_suggestions` have no unique key. Add partial unique indexes on
     `(owner, question, kind, old_value, new_value) WHERE status='open'` and on
     `(qid, property, action, value) WHERE status IN ('draft','approved','exported')`.
   * Contacts: the primary key holds the raw value. The Census `http://x.gov` and the Wikidata
     `https://www.x.gov/` stay two rows (274 governments have two or more websites), and both get rechecked. Add
     a normalised-URL column, and fetch each normalised URL once per run.
   * `entity_links` and agency seeding: re-running the finder or the seed must not overwrite a reviewer's
     `status`, `method` or aliases. Use `keep=` for decision columns.
   * Agency keys: the seed needs an identity rule — match on QID, then on name or alias, and mint a key only
     when neither matches, with a collision suffix. Otherwise a renamed label, or two names that truncate to the
     same 48-character slug, mints a second key.
   * Agency contacts "moved out of the city rows". `places.load_local` writes them back under the city on its
     next run, because the curated JSON is frozen. Retire the city rows (`status='retired'`, kept by `keep=`),
     and map known agency contacts in the loader. Do not delete.
6. **Wikibase P8.** The plan puts "P8 → Wikidata" on every agency. It must appear only where
   `wikidata_match='exact'` and the item is an organisation or a court. A parent QID belongs on the parent's item,
   and a position QID is not an exact match for an office. Also, Q139489412 is "county clerk's office". It is not
   a fit `P8` for a generic "clerk's office" class that includes circuit-court clerks.
7. **`Step.credits`.** Steps now need `credits` or a `credits_note`. The `recheck` step should credit Wikidata
   (CC0), and Govdirectory if its sitemap is read.

## 6. Missing safeguards in the recheck design

* **Redirects to private addresses.** Hops are followed to any host. A hijacked domain can redirect to
  `localhost:8000`, `ollama:11434` or other private addresses inside the container. Refuse loopback, private,
  link-local and non-80/443 targets at every hop, after DNS resolution.
* **The `moved` display rule.**
  * The domain check runs before the name check, in both the plan's order and `classify_web`. A lapsed domain
    that redirects to a neutral-looking third-party site becomes `moved`, and `moved` links stay public.
  * Show `moved` only when the target is an official domain (`.gov`, or the state's locality pattern) or carries
    the owner's name. Otherwise hide it until a person reviews it.
* **Spam quarantine on first sight is too broad.**
  * `SPAM_TITLE_RE` fires on `casino`, `betting` or `poker`, which state lottery and gaming regulators use. It
    also fires on any single CJK or Hangul character.
  * Quarantine hides everywhere at once and only a person can clear it. Require a second signal (owner name
    absent, a lapsed-domain marker, or a changed registrant domain), or apply the immediate rule only to the
    Indonesian spam vocabulary.
* **robots.txt cost.** `crawl._allowed` has no cache and no throttle, and it follows redirects. Reused as it is,
  it adds about one GET per URL outside `Throttle`, so the 1,350-a-day and 40,000-a-month budgets are about 50 %
  low. Cache robots.txt per host for 24 h and route the fetch through the same throttle.
* **TLS.** The pilot retries a certificate failure without verification. A page fetched that way must never earn
  `ok` or `page-contains` evidence. Today there are 0 such items.
* **The per-domain cap.** A forced full pass cannot finish in one run: govoffice.com needs about 224 GETs against
  a cap of 60. Say that the forced pass spans runs.
* **Phase order.** At the phase-1 exit, "no public surface links an `unchecked` website" — and no checker exists
  until phase 2. Ship the display policy with phase 2, or run a one-off tier-0 check first.
* **Agencies and the name check.** `name_present` strips government prefixes (`core_name`). Agencies need
  matching on their aliases, or most agency sites will come out `unverifiable`.

## 7. What a person should decide

1. The fix for the two Baltimore staff mailboxes (§3.1): a carve-out from the freeze, a purge, a republish.
   Done for the current pages (see the status note in §3.1); the old page revisions remain.
2. The form of the LOCUS citation in the app (§1).
3. How check results reach other machines: a separate synced table, or one designated `recheck` machine (§5, item 1).
4. A postal-address policy for small governments (§3.3).
