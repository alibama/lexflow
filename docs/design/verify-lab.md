# Verification: process lab prototype

_10 October 2026. Adversarial check of `lexflow/lab/*`, `dashboard/lab.{html,js}`, `docs/design/lab-plan.md` and
`tests/test_lab.py`. No file other than this note was edited, and nothing was written to the network. Read-only
requests (1 per second or slower, with lexflow's research User-Agent) went to law.lis.virginia.gov (§§ 2.2-3300 and
1-210), dhrm.virginia.gov (the 2026 Pay and Holiday Calendar), courts.ca.gov (court holidays and rule 1.11) and
foiacouncil.dls.virginia.gov (AO-02-08). leginfo.legislature.ca.gov sits behind a bot challenge, so it was not used;
the California statute text was read from the local open-us-law copy._

## Confirmed

- `tests/test_lab.py`: **45 passed** in the container, with the parse report as its single warning. There are 53
  curated deadlines: 47 agree with their fields, 5 quotes state no number and 1 differs (California
  `determine_extended`). `node --check dashboard/lab.js` passes, both as a script and as a module.
- **Virginia 2026.** The table's 13 dates match the current text of § 2.2-3300, including its weekend-shift
  sentence, and the statutory days on DHRM's 2026 calendar: 1 Jan, 19 Jan, 16 Feb, 25 May, 19 Jun, 3 Jul (for Sat 4
  Jul), 7 Sep, 12 Oct, 3 Nov, 11 Nov, 26 and 27 Nov, and 25 Dec. The § 1-210(A) and (E) text says what the code
  says, so the builder's broader reading of (E) is right. AO-02-08 (Fri 18 Jan 2008 to Mon 28 Jan 2008, with MLK Day
  skipped) is as cited.
- **Hand-worked cases** (counted by hand first, then run through the code):
  - VA, 5 working days from Mon 21 Dec 2026: Tue 29 Dec.
  - VA, 5 working days from Tue 30 Jun 2026: Wed 8 Jul.
  - VA, 5 working days from Wed 17 Jun 2026: Thu 25 Jun.
  - VA, 7 working days from Fri 20 Nov 2026: Thu 3 Dec.
  - VA, 7 calendar days from Tue 27 Oct 2026: Election Day, rolled to Wed 4 Nov.
  - CA, 3 business days from Wed 23 Sep 2026: Tue 29 Sep.
  - CA, 10 days from Mon 14 Dec 2026: Thu 24 Dec.

  All seven match under the statutes' own reading. So do the two B.4 dates (16 and 19 Nov).
- **Outcome endpoint.** The table has exactly six columns. Any extra body field gets a 422. `lab_outcomes` is not in
  `db.SYNCED`, so Turso can never push it. The real store (`/data/lexflow.db`, opened read-only) has no
  `lab_outcomes`. The timeline response does not echo the place or the notes.

## Wrong

1. **The place does leave the browser.** `showCase` calls `GET /api/lab/places/{gov_id}/channels` every time a case
   that has a place is opened (lab.js lines 260 and 287), with no share click. The place search also sends what the
   user types (line 187). This contradicts the summary ("the place [is] removed before anything is sent"), lab-plan
   §3 ("Never") and the page's own notice. `lexflow serve` writes uvicorn access logs at info level, with the client
   IP, so the path is logged.
2. **California 2026: Fri 3 Jul is missing.** The official 2026 court schedule closes on 3 Jul. Under the last
   sentences of CCP § 135, the Judicial Council observes a Saturday holiday on the Friday before (rule 1.11). The
   table only applies Gov. § 6701, so 3 Jul counts as a business day. Example: CPRA 10 days from Tue 23 Jun 2026.
   The lab gives Fri 3 Jul; under the judicial calendar it is Mon 6 Jul. In 2027 the official schedule also
   differs, on 9 Apr (Farmworkers Day), 18 Jun and 24 Dec. The test `(2027-03-30, 1) -> 2027-04-01` pins 31 Mar
   2027, a day the courts are open.
3. **Virginia 2026: the Governor's Thu 24 Dec closure is missing.** DHRM's 2026 calendar grants 8 hours that day
   (and 4 hours on 25 Nov); see the last paragraph of § 2.2-3300 and § 1-210(F). The lab counts 24 Dec as a working
   day. Example: a request to a state body received Mon 21 Dec. The lab says due Tue 29 Dec; with the closure it is
   Wed 30 Dec. The lab would show the body overdue a day early. Users are told to record closures themselves, and
   no per-year list is offered.
4. **"A row identifier the sender could be linked to."** SQLite keeps an implicit, sequential `rowid`. The probe
   rows came back numbered 1 to 5. Together with the access log of each `POST /api/lab/outcomes`, that order links
   each row to a time and an IP. Unknown query-string parameters are also accepted (201), and they reach the log.
5. **`opens`, `observes` and `closures` cannot be reached from the page.** `forServer()` hard-codes them to empty
   lists, so "a case can mark them open" (North Carolina) is not true in the UI, and imported options are dropped.
6. **The office-channel filter matches substrings.** Synthetic addresses such as `prakash.n@`, `spratt@`,
   `kopenhaver@` and `j.clerkin@` pass as role mailboxes, and so does any labelled phone. In the real store, 3 of
   the 5 emails that pass do so only on a substring; one has a first.last shape. Match whole tokens instead.

## Plausible / weak

- **Virginia B.4.** Many Virginia bodies' own FOIA notices describe the extension as a total of 12 working days,
  which is the alternative reading (19 Nov). The default (16 Nov) can show "overdue" while the body is still in
  time. The later date may be the safer default.
- `GET /outcomes/summary` creates the table, which is a write on a GET.
- k = 10 applies per cell, so a cell can show `"denied": 1`.
- The "stores nothing" test only counts the tables in `sqlite_master`, not rows.
- Plan §2 proposes serving `POST /timeline` from a public host. Users' event dates would then leave their machine.

## Missing

- Setup does not reference the lab yet. Only the snippets in the plan exist, and the owners of app.js, steps.py,
  credits.py and app.py have to apply them.
- With the router not mounted, a new case cannot be started (the model list is empty).
- There is no JavaScript port of the counting, no per-year list of executive closures, and no authentication or
  rate limit on outcomes. Port 8000 is published on 0.0.0.0.

## Re-check (10 October 2026, after the fix)

_Adversarial re-check of the fixer's report against the current files. Only this section was added; no other file
was edited and nothing was written to the network. Three read-only requests (lexflow's research User-Agent, more than
a second apart): dhrm.virginia.gov/payandholidaycalendar, the DHRM 2027 Pay and Holiday Calendar PDF linked from it,
and courts.ca.gov/about/court-holidays. The real store was opened read-only; only counts and masked shapes were
printed. Probes ran on scratch databases under the container's /tmp, deleted afterwards._

**Tests.** `tests/test_lab.py`: 118 passed (the parse report is the one warning). Doctests in `lexflow/privacy.py`
and `lexflow/lab/deadlines.py`: 4 passed. The rest of the suite: 473 passed, 5 skipped (more than the fixer's 460,
because other agents have added tests since). `node --check dashboard/lab.js` passes.

### Fixed, and checked

1. **Place leak: fixed.** No route takes a place or a search (`/places?q=` and `/places/{gov_id}/channels` give
   404). The search and "where to send" run on `GET /states/{state}/places`. Every `api()` call in `lab.js` is
   `/models`, `/models/{id}/steps`, `/states/{st}/places`, `/timeline?today=` or `/outcomes`. `forServer()` sends no
   place, label or note.
2. **California: fixed.** Every holiday now shifts both ways (rule 1.11). The live Judicial Council page matches
   `CA_2026` and `CA_2027` day for day, including Fri 3 Jul 2026, Fri 9 Apr 2027 (Farmworkers Day), Fri 18 Jun 2027
   and Fri 24 Dec 2027. CPRA 10 days from 23 Jun 2026 now ends Mon 6 Jul. 1 business day from 30 Mar 2027 now ends
   31 Mar. The extra Fri 31 Dec 2027 (New Year's Day 2028 on a Saturday) is not on the 2027 page. It follows from
   rule 1.11, and it errs late for the body: an acceptable judgement call.
3. **Virginia 24 Dec 2026: fixed.** 5 working days from Mon 21 Dec 2026 now end Wed 30 Dec. The DHRM 2027 PDF
   confirms the table: 4 hours on 24 Nov and 23 Dec 2027, Christmas observed Fri 24 Dec, and New Year's Day 2028
   observed Fri 31 Dec 2027. `VA_2027` matches. The "Confirmed" hand-worked case above ("Tue 29 Dec") is superseded.
   The other six cases are unchanged.
4. **Outcome rowid: fixed.** The table is `WITHOUT ROWID`, under a random key, with no date. `SELECT rowid` fails.
   A query string gives 422, `Origin`/`Sec-Fetch-Site` cross-site gives 403, and the rate limit gives 429. The WAL
   and access-log limits are stated.
5. **Per-case options: fixed.** The holiday card sets opens, observes, closures and the variant. `forServer()`
   sends `cleanOptions(c.options)`, and import keeps them. The API test pins the effect.
6. **Office-channel substrings: fixed for mailboxes.** `prakash.n`, `spratt`, `kopenhaver`, `j.clerkin` and the
   §5.2 table are refused. On the real store, the passing mailboxes segment cleanly (`city+clerk`, `town+clerk`,
   `foia+council`, ...).

Plausible items: B.4 now uses the later date (19 Nov, with 16 Nov shown). The summary GET creates nothing. The
"stores nothing" test compares rows and `data_version`. Plan §2 keeps `POST /timeline` off public hosts. All fixed.

### Not fixed, or only partly

- **k inside a cell.** Outcomes are pooled, but `other` itself can be 1. Ten `answered_in_time` and one `denied`
  give `{"answered_in_time": 10}, "other": 1`, which shows that exactly one report differs. Suppress `other` below k
  as well (or coarsen `n`).
- **Virginia part days: not the conservative choice.** A request received Wed 18 Nov 2026 is due Wed 25 Nov by
  default, and the body shows *overdue* on Fri 27 Nov. The § 1-210(E) reading shown beside it gives Mon 30 Nov. This
  is the same failure mode as Wrong 3. It is also inconsistent with the B.4 rule ("never call a body overdue while it
  may still be in time"). For a body's deadline the later date should be the default. A related point: the
  executive days are applied to local bodies as well, which errs late, but against a requester's own deadline.
- **MISSING items left open, as the report says:** no JavaScript port, the router is not mounted, Setup has no
  reference, there is no authentication, and port 8000 is on 0.0.0.0. Executive closures exist only for VA and the
  CA courts, for 2026-27.

### New findings

1. **Privacy weakness: a label's leading name gives a person's initials.** `_context` makes an initialism from every
   run of the label's first words, whether or not they name an office. `jd@…` with the label "Jane Doe" (or "Jane
   Doe, FOIA Officer") is classed `role` and shown. §5.2 rule 3 means the *office* name that starts the label. Take
   initials only from a leading phrase that contains an office word (department, office, division, board, ...).
2. **Privacy weakness: an all-caps name in a phone label passes.** Every 2-6 letter upper-case word is skipped as an
   acronym, so "Clerk's Office - MARY SMITH" and "Records: JANE DOE" are accepted as office lines. The docstring's "a
   word outside the vocabulary (a person's name, say) … is refused" is therefore OVERSTATED. Accept an acronym only
   when it is an initialism of the owner or the office, or when it is in the vocabulary.
3. **Privacy weakness: labels are not filtered.** `state_places` returns `label` (and `source`) unchanged for
   e-mail, page, office and website rows. A role mailbox labelled "Jane Doe, FOIA Officer" is sent with that label,
   and the page shows it in bold. Only phone labels are checked.
4. **MISSING against §5.2, and OVERSTATED in two docstrings: staff names in office values.** `office_value` drops
   only lines that begin with Attn/Attention/c/o. "Jane Doe, Records Custodian\nP.O. Box 2" and "FOIA Officer: Jane
   Doe; 123 Main St" are returned unchanged. §5.2 says "and so is a staff name anywhere else in the value". The
   docstrings of `api.state_places` ("office values without a line naming a person") and `privacy` ("without a line
   that names a person") claim more than the code does.
5. **Rule 5 of §5.2 is not applied to mailboxes.** The bundle shows every role-shaped address, checked or not. The
   real store is being filled by a crawl as this is written: 1,450 e-mail and 2,953 phone rows, most written after
   17:00 UTC today. The plan's "7 of the 9 mailboxes" (§5) is a snapshot, and hundreds of crawled mailboxes would
   now be shown. Plan §6.7 names only websites and pages; it should name mailboxes too.
6. **Page text, minor:**
   - The share card says the log "notes that a report arrived, and when". It also records the client address,
     which the plan states.
   - "(part day; counted unless marked open)" is wrong: a part day is counted as a working day either way, and
     marking it open only removes the note.
   - `lab.js`'s header says the bundle loads when "a case of that state is opened". It loads only when the case
     has a place, so the server learns whether an opened case has a place (one bit; low).
7. **Robustness, low.** `_ensure`'s migration is not atomic: the RENAME and CREATE autocommit before the copy. An
   interruption leaves `lab_outcomes_rowid`, with its sequential rowids, which is never cleaned up (simulated: the orphan survives the next post). Two concurrent
   first posts on an old table can race on the RENAME (reasoned, not run).

## Re-check 2 (10 October 2026, after the second fix)

_Adversarial re-check of the second fixer's report against the current files. Only this section was added; no other
file was edited. No network request was made. The real store was opened read-only (`mode=ro`); only counts and
masked shapes were printed. One probe ran on a scratch database under the container's /tmp, deleted afterwards._

**Tests.** `tests/test_lab.py`: 172 passed (the parse report is the one warning). Doctests in `privacy.py` and
`lab/*.py`: 9 passed. The rest of the suite, without `tests/test_terms.py` (another area): 857 passed, 10 skipped.
`node --check dashboard/lab.js` passes as a script and as a module.

### Fixed, and checked

1. **k inside a cell: fixed.** Ten `answered_in_time` and one `denied` give `n = 11`, `outcomes {}`, `other 11`.
   The five parametrised cases hold: no group shown, or worked out from `n`, is between 1 and 9.
2. **Virginia part days: fixed, the conservative way.** Received Wed 18 Nov 2026: due Mon 30 Nov, *on time* on Fri
   27 Nov (§ 1-210(E) reading also Mon 30 Nov; without the executive days, Wed 25 Nov, shown beside it). 7 working
   days from Fri 20 Nov: Fri 4 Dec by default, Thu 3 Dec under § 1-210(E). The "Confirmed" hand-worked case above
   ("Thu 3 Dec") is now the other reading. Over 460 start days from 1 Oct 2026, with 1-12 business days, 1-31
   calendar days and 1-2 months, the default is never earlier than the § 1-210(E) reading, and that one is never
   earlier than the reading without the executive days (0 violations). The other five hand-worked cases are
   unchanged. An old case with `part_days_closed` (now `part_days_1210e`) gets a warning and the default, which is never
   earlier than that reading.
3. **A requester's own deadline: fixed.** It takes `executive_open`, the earliest reading, with the default beside it.
   No curated Virginia model has such a deadline today, as the plan says.
4. **Initials from a person's name, all-caps names in phone labels, unfiltered labels and sources, staff names in
   office values (the re-check's two examples), rule 5 for mailboxes: fixed** as reported. In the store: 3,216
   e-mail rows, 1,196 role-shaped, **0 shown** (`contact_status` does not exist); 4 of 5,913 phones pass; 5,555 page
   rows are shown, 747 of them without their label; 26 contact links and 33 governments' own websites are refused
   (the plan's 59). `contact_status`'s columns in entities-contacts.md §2.1 match the query.
5. **Page text: fixed.** The share card names the client IP; the part-day text comes from `part_day_rule`; the
   state's list is loaded for every opened case, before any test of its place.
6. **Migration: fixed.** One `BEGIN IMMEDIATE` transaction; the forced failure leaves the old table and its rows;
   an orphan `lab_outcomes_rowid` is moved in and dropped; a second connection waits for the lock.

### Not fixed, or only partly

1. **Privacy weakness, and OVERSTATED: text after a number in an office value is kept unchecked.** `_part_ok`
   checks only the words before a piece's first number, and keeps everything after a leading number. On a scratch
   store the bundle showed `City Hall Room 101 Jane Doe, Clerk` and `P.O. Box 911 Attn Jane Doe` unchanged;
   `Room 200 Jane Doe`, `Phone 434-555-0100 Jane Doe` and `123 Main St Jane Doe` are kept too, while
   `434-555-0100 Jane Doe` is dropped. So "any other piece, such as a staff name, is dropped" (privacy header,
   `office_value`), "every piece of an office value that could name a person" (`api.state_places`) and plan §0 and
   §5 claim more than the code does. The store's 8 office rows do not hit it today: their unchecked words sit before
   a street word (street names, already stated). Fix: after the number, accept only street words, digits and line
   words ("ext"), and check the rest.
2. **Privacy weakness: phone values are shown unchecked.** Only the label is checked; `434-555-0100 Jane Doe`
   labelled "Clerk's Office main line" is shown as is. In the store, 1 of the 4 passing phones carries text (by word
   class, an office address). Fix: pass phone values through `office_value`, which already drops that example.
3. **OVERSTATED, low: `is_office_url`.** A URL-encoded address (`?to=jane.doe%40example.gov`) and an encoded tilde
   (`/%7Ejdoe/`) pass, so "refused when it carries an e-mail address" and "no ~user path" are not quite true; `vbscript:`
   and `file:` links pass ("not a script ... link"). `lab.js` links only `http(s)` values, so those two are shown as
   text only. The store has no such row. Fix: unquote before testing, and accept only `http`/`https`.
4. **Page text, minor.** `lab.html` says the page is "Reached from Setup"; Setup does not reference it yet (Missing).
5. **Plan §0, minor.** It says 171 tests; there are 172.

### Low, or judgement calls (left as they are)

- Two-letter initialisms of the owner count: for City of Charlottesville, `cc@` is role-shaped and "Clerk's Office -
  CC" passes as an office line. That is §5.2 rule 3 as written, but two letters are also a person's initials.
  Mailboxes are hidden anyway.
- A name made only of vocabulary words ("Will Parks" as a label, "Records - Page Law" as a phone label) passes; no
  shape check can avoid this.
- Websites, pages and phones are still shown unchecked, against entities-contacts.md §2.2 ("not shown, from phase
  1"); plan §6.7 states it. Still open from the first note: the router is not mounted, Setup has no reference, there
  is no JavaScript port, no authentication, port 8000 on 0.0.0.0, and executive closures only for VA and the CA
  courts in 2026-27.

## Re-check 3 (11 October 2026, after the third fix)

_Adversarial re-check of the third fixer's report against the current files. Only this section was added; no other
file was edited. No network request was made. The real store was opened read-only (`mode=ro`); only counts and
masked shapes were printed. Probes ran from the container's /tmp/recheck3 (one on a scratch database), deleted
afterwards. To see whether the tests pin the fixes, each round-2 change was undone in memory by a pytest plugin; no
repository file was changed. All names and addresses below are made up._

**Tests.** `tests/test_lab.py`: 226 passed (the parse report is the one warning), and the plan's count matches a
fresh collection. Doctests in `privacy.py` and `lab/*.py`: 10 passed. `tests/test_crawl.py` and
`tests/test_design_privacy.py`: 40 passed. `node --check dashboard/lab.js` passes. The rest of the suite: 981 passed, 14 skipped, 0 failed. Other agents
have fixed or added tests since the report's run, which had 7 failures in their areas.

**Do the tests pin the fixes?** Yes, with one gap (New 5). Each change undone in turn, and the tests it fails: initials
of 2 letters (2); no decoding of links (7); the old scheme list (5); phone values unchecked (5); an emulation of the
old rule, which checked only the words before a number (17); no split before an inline "Attn" (4); two-letter pieces
in run-together words (1, "Wayne"); a room number taken as a house number (1); letters run into digits not split (1).

### Fixed, and checked

1. **Text after a number: fixed.** Re-check 2's examples now give `Clerk`, `P.O. Box 911`, and None for "Room 200 Jane
   Doe", "Phone 434-555-0100 Jane Doe", "123 Main St Jane Doe" and "434-555-0100 Jane Doe". Addresses, ext., TTY,
   ordinal streets and office hours are kept.
2. **Phone values: fixed for the reported cases.** "434-555-0100 Jane Doe" with the label "Clerk's Office main line"
   is refused, and it is left out of the bundle. New 1 to 4 show values that still get through.
3. **`is_office_url`: fixed.** `%40`, `%7E`, `%2540`, `&#64;`, `%73taff`, `vbscript:`, `file:`, `FILE:`, `ftp:`,
   `data:`, `tel:` and `java\tscript:` are refused. Plain office links are kept.
4. **Two-letter initials: the conservative choice was taken.** `cc@` and "Clerk's Office - CC" are refused for the
   City of Charlottesville; `coc.clerk@` and `hr@` are still accepted. `crawl.py` calls the function as before (its
   tests pass), and it now stores fewer mailboxes.
5. **Page text: fixed.** `lab.html` no longer says "Reached from Setup". Neither `app.js` nor `index.html` links to
   `lab.html`, so "does not yet" is true today.
6. **Plan §0 count: fixed** (226). The new test re-collects the file, so the count cannot go stale unnoticed.

**Store figures: confirmed** (they match the store as it is now). On governments there are 1,204 e-mail, 5,929 phone,
5,593 page, 16,502 website and 29 office rows. 1,192 mailboxes are role-shaped with 3-letter initials and 1,196 with
2-letter ones (the report's 4). Phone labels: 7 pass with 2-letter initials, 6 with 3, and 5 phones are shown (the
report's 2). 5,567 pages pass (759 of them without their label) and 16,468 websites pass. All 29 office values keep
some text, and 17 of them lose a piece. The only unchecked words left in them are 6 street-name words and 18 state
codes. `contact_status` does not exist, so no mailbox row is shown.

### Untrue, or not reproduced

- **"1 page with an encoded `~` is now left out" (report; plan §5): the wrong reason.** No page or website row in the
  store has `%7E`, `%40` or `&#`, and decoding changes the verdict on none of them. The one page now left out has a
  plain `~` in its fragment: a scroll-to-text directive (`#:~:text=…`). The old check refused only a `~user` path,
  while the new "any `~`" refuses this link too. Refusing it is conservative, since the directive quotes text from the
  page, but the plan should give that reason. Stripping a `:~:` directive and showing the bare link would also work.
- **"No office value lost a piece it kept before; 7 now keep their office hours": not reproduced.** The old module
  was not kept. Today's output is consistent with it.

### New findings

1. **Privacy weakness, and OVERSTATED: a state without a ZIP code, and long "city" pieces.** `_ST_ZIP` makes the ZIP
   optional and matches state names in any case. So a piece that is only a state code or name is kept, and the
   piece of up to 4 words before it is kept unchecked as a city. `_CITY_ST_ZIP` takes up to 41 characters of any
   words as the city. With the owner City of Charlottesville:
   - "Clerk's Office, Jane Doe, VA" and "Jane Doe - Virginia" come back unchanged.
   - "Clerk's Office - Georgia" and "Records - Washington" are kept. Several state names are also people's names.
   - "Clerk's Office Jane Doe Charlottesville VA 22902" and "Records Custodian Jane Doe Richmond VA 23219" are kept
     whole.

   The module header, `office_value`, `api.state_places` and plan §0 all say that the only city text kept unchecked
   is "the short piece before a state and ZIP code". Fix: require the ZIP for the city rule, or keep a bare state only
   right after a city piece. Limit the city to the last one to three words of its piece, and check the words before
   them.
2. **DEFECT against this round's own claim: `office_phone_value` inherits every hole of `office_value`.** Its
   docstring, `api.state_places`, plan §0 and the report all say a phone value is shown only when nothing but office
   or line words stands beside the number. But a value is in fact shown whenever `office_value` keeps it unchanged.
   So under the label "Clerk's Office main line" the bundle on a scratch store sent "434-555-0100, Jane Doe, VA" and
   "434-555-0101 - Washington". `office_phone_value` also keeps "Jane Doe, VA; 434-555-0100", "1 Jane Doe St
   434-555-0100" and "Room 200JD" whole. In the real store, 1 of the 5 phones shown has an office's street address and city
   beside its number (masked: `P ; v v, N v X v, o, S Z`). That is harmless, but it is not what the docstring says.
   Fix: for a phone value, accept only the number, line and number words (ext, TTY, option), office vocabulary and
   parenthesised vocabulary, with no street-name, city or state rule.
3. **Privacy weakness: letters outside A-Z are never checked.** `_words` finds only `[A-Za-z]`, so a word in
   another script, or in full-width letters, does not count as a word at all. It passes `office_value`,
   `office_phone_value`, `is_office_phone` and `office_label`. On a scratch store the bundle sent all of these:
   - "Records Office, Иван Петров" (office);
   - "434-555-0102 王伟" (phone value);
   - "Clerk's Office 王伟" and "Clerk's Office Ｊａｎｅ Ｄｏｅ" (phone labels);
   - a page labelled "Records Иван Петров".

   A name with accents is dropped only because its ASCII fragments happen not to be vocabulary ("José Pérez" splits
   into jos, p and rez). So the header's "keeps only text it can account for and refuses the rest" is untrue for such
   text. No row shown from the store has such letters today. Fix: apply NFKC normalisation, then refuse any piece,
   label or phone value with a letter outside A-Z.
4. **Privacy weakness: an e-mail address inside an office value, phone value or label skips the mailbox rule and
   rule 5.** The words of the address's domain count as the owner's name, so (the trial used made-up addresses on
   the owner's own domain; they are written here on the reserved domain example.org):
   - "Clerk's Office, will.page@example.org" and "P.O. Box 911, hall.may@example.org" are kept, although
     `mailbox_shape` calls both personal;
   - "434-555-0100, records@example.org" is shown as a phone value;
   - "Clerk's Office foia@example.org" passes both as a phone label and as a row label.

   Meanwhile every mailbox row is hidden, because no check has found it. So plan §5's "No mailbox is shown" holds only
   because the store has no such value today (0 rows). Fix: drop any piece, value or label that has an `@`, after the
   same decoding as for links.
5. **Test gap.** No test pins the rule that a number right after a phone number is never a house number (the phone
   branch of `_house_number`). With that branch removed, the other 225 tests pass, and "434-555-0100 1 Jane Doe St"
   would be kept whole. Add that row.
6. **Low.**
   - The run-together cut still builds surnames out of pieces of three letters or more. Cannon (can + non), Southall
     (south + all), Newhall, Mayhall and Northway all pass `_vocab`. "Wayne" was one case of a class that remains.
     Labels and phone labels are still cut into two-letter pieces. Cutting only into office words (not joining,
     filler or street words) would close most of it.
   - The new office-hours words widen the accepted class of "names made of vocabulary words". "Records Office - Will
     Sun" and "Clerk's Office - May Noon" are kept.
   - A number token keeps up to two letters (`_NUMBER`), so "Room 200JD" and "434-555-0100 12JD" pass. Two letters
     are what `MIN_INITIALS` treats as a person's initials. Single address letters pass too ("Clerk's Office - S. W.").
   - Run-together words that contain a unit word ("Courtroom 3", "Mailbox 5") are not unit words, and neither are
     building words such as Hall or Annex ("City Hall Annex 2"). So the number after them can start a street name:
     "Courtroom 3 Jane Doe Court" is kept. The report's "a number after a room, suite, box or line word can never
     start a street name" holds for the listed words only. This stays inside the accepted street-name hole.
   - `_decoded` stops after 5 rounds, so a link with an `@` percent-encoded six times passes. The docstring's "however
     often they are nested" is therefore OVERSTATED. A browser decodes only once, so such a link does not show an
     address.
   - Links on social or personal hosts are judged by their path only: `linkedin.com/in/jane-doe`,
     `facebook.com/janedoe` and `janedoe.example.org` all pass. In the store, 1 Facebook page, 1 Facebook website and
     8 sites.google.com websites pass today; their handles were not inspected.

### Still open (accepted, or for other owners)

- The accepted limits stay as stated: a street's name, the short city piece before a state and ZIP code, and names
  made only of vocabulary words. So do the conservative losses: "100 Broadway", "DC Department of Buildings", and the
  phone whose value carries a remark.
- The router is not mounted and Setup has no link. There is no JavaScript port and no authentication. Port 8000 is
  published on 0.0.0.0. Executive closures exist only for VA and the CA courts, for 2026-27. Websites, pages and
  phones are shown by shape before any `contact_status` check (plan §6.7).
