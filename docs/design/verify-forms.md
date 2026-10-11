# Verification: forms registry and statute drafts

_10 October 2026. Adversarial check of `lexflow/forms/*`, `tests/test_forms.py`, `docs/design/forms-plan.md` and
`out/forms/*`. This note is the only file edited. Nothing was written to the network. Read-only requests used
lexflow's research User-Agent, a 15 s timeout, robots.txt read once per host and at least 1.2 s between requests to
the same host. They went to the 15 sampled form URLs and to law.lis.virginia.gov (§ 2.2-3704). PDF bytes were
parsed in memory and never saved. leginfo.legislature.ca.gov answers robots.txt with HTTP 403 (a bot challenge), so
it was not fetched. The California text was read from the local open-us-law copy._

## Confirmed

- **Tests.** As shipped, the container gives **27 passed, 4 skipped**: the worked-example tests skip because
  `/app/out` is not bind-mounted. With `out/forms` copied to the container's `/tmp` (the module's `OUT` was patched;
  no repository file changed), **31 passed**. The copy was then deleted. Rebuilding both drafts from their saved
  sources gives JSON, form, letter and index output byte-identical to `out/forms/`.
- **Forms sample (15 of 82).** Every URL returned HTTP 200 with the expected type. The form number, title and
  publisher match the file in every case. For each fillable PDF, the field count is the same as the fixture's.

  | id | number / title / publisher in the file | notes |
  |---|---|---|
  | va-foia-request-letter | Word .doc, "Request for records under the Virginia Freedom of Information Act" | no number (correct) |
  | va-cc-1201 | "FORM CC-1201", title, Supreme Court of Virginia | 104 fields; prints "07/26", fixture revision null |
  | va-dpor-a406-01predet | "A406-01PREDET-V2", title, DPOR | 171 fields; prints 08/20/2026, fixture revision null |
  | dc-dlc-1 | DLC-1, "Ver. 8", "October 2022", DLCP Corporations Division | 9 fields; PDF metadata title is a stale "Application for Construction Permits" |
  | md-cc-dc-cr-072a | number, title (fixture shortens it), Maryland courts | 48 fields; "rev. 10/01/2026" not found in text (Last-Modified 2026-09-30); robots.txt is a redirect loop |
  | tx-sos-205 | number and title (in the XMP; body fonts are custom-encoded) | 128 fields; "revised 09/26" not checkable (Last-Modified 2026-09-28) |
  | tx-tdlr-chel | ENF001, title, TDLR | 33 fields |
  | ca-jc-cr-180 / 181 / 409 | number, title, "Judicial Council of California", "Rev. January 1, 2024" | 81 / 58 / 39 fields; AES-256 permission encryption; fixture revision null |
  | ca-jc-cr-410 | number, title, Judicial Council, "New January 1, 2019" | 26 fields; fixture revision null |
  | ca-doj-bcia-8016rr | "BCIA 8016RR (Rev. 03/2024)", California DOJ | 48 fields; full title adds "or Foreign Adoption" |
  | fl-sunbiz-cr2e047 | CR2E047, Articles of Organization, Division of Corporations | 46 fields |
  | ny-doccs-crd-cgc-application | title, DOCCS | 251 fields; revision only in the URL and Last-Modified (2026-01-08) |
  | wa-crrlj-09-0100 | "CrRLJ 09.0100", "(11/2024)" | no AcroForm (fixture `fillable: false` is right); the AOC is not named in the text |

  The four Judicial Council URLs redirect (301, 301) to `courts.ca.gov/sites/default/files/courts/default/2024-11/`.
  The fixture records no `final_url`.
- **Virginia statute.** All 18 quotes appear word for word on the official LIS page today. The stored § 2.2-3704
  text matches LIS sentence for sentence (48 sentences, none different).
- **California statute.** All 20 quotes appear word for word in the stored §§ 480, 481, 482, 485 and 486, each under
  the subsection it cites. The snapshot in `out/forms` equals the store (same SHA-256). The texts were not compared
  with leginfo (see above).
- **Element review, by hand.** Every `required` element rests on a mandatory sentence that does require it: VA
  `records` (§ 2.2-3704(B)), CA `hearing_request` (§ 485(b)) and CA `dismissal_proof` (§ 480(c), with its
  condition). `name_address` is correctly `if_asked` (§ 2.2-3704(A)). No element states a duty that its section
  lacks. Neither draft has a phone, purpose or signature field. The builder's legal point is right: §§ 480 and 482
  limit the board and create no request of their own, and § 485(b) is the request.
- **Banner and privacy.** The banner appears twice on each form page and each letter page, and once on the index.
  The form has no `action` or `method` and uses no fetch, XHR, beacon, storage or cookie APIs. Outbound links are
  `noopener noreferrer`.
- **Registry.** `check_steps()` finds no problems in the 94 references (74 form links and 20 `no_form` links).
  Recomputing the node types with the compiler's rules (`compile.py` lines 70-74 and 103) gives 57 private-party message
  events, 1 court message event, 8 `receiveTask`, 5 `task`, 2 `sendTask`, 1 `businessRuleTask` and **0
  `userTask`**. The `no_form` links are 18 message events and 2 `sendTask`. `setup_status` gives `partial`, and its
  stale list is `il-sos-llc-5-5`. Setup is tied in through `setup_entry`/`setup_status` only. No page was added, and
  `steps.py` and `ir.py` are unchanged.

## Wrong

1. **The printable letter lists the official alternatives last.** `render_letter` puts `_official_box(d)` after the
   letter (`draft.py:955`). That contradicts the module docstring ("each page lists the official alternatives first") and the
   report ("Every page ... lists official alternatives first"). The test checks only the form page.
2. **CA `seven_years` quotes § 480(a)(1) selectively.** The letter says a board "may deny on this ground where" a
   substantially related conviction falls within seven years, and then says "That condition is not met". It leaves
   out the other branch of the same sentence: a conviction "for which the applicant is presently incarcerated or for
   which the applicant was released from incarceration within the preceding seven years". It also leaves out the
   (A)/(B) exceptions. The letter therefore states a narrower test than the statute.
3. **The CA scope is too broad.** "For a licence regulated by the Business and Professions Code" ignores § 476(a):
   "nothing in this division shall apply" to State Bar (Ch. 4, Div. 3), alcoholic-beverage (Div. 9) or gambling
   (Ch. 5, Div. 8) licences. The curated file's notes also list practice-act departures from § 480.
4. **BCIA 8016RR is shown as the "Official form" for evidence of rehabilitation.** The form is a record-review
   Live Scan request. The fixture links it to that step only as `related`, and element-level links drop the match
   label.
5. **The rule checker misses invented content (shown in memory, with real section text).** `check()` returns `[]`
   in three cases:
   - a `right` "phone" element whose field label is "Phone number (required)", with placeholder "you have to give
     one" (field labels and placeholders are not scanned);
   - a `required` "purpose" element resting on the unrelated sentence "shall take all necessary precautions for
     their preservation";
   - `locate()`, which accepts § 485's unlettered closing paragraph as "(b)".

   So "nothing invented" holds for these two specs because a person reviewed them, not because code enforces it.
   Plan §6.4, "Fields the statute does not ask for are left out", is not enforced. It is also not literally true:
   custodian address, email, medium, board address, application number and notice date are all optional fields
   that the statute does not ask for.
6. **Defaults with a legal effect.** VA `cost_estimate` is ticked by default. Under § 2.2-3704(F), the response
   period is "tolled" from notice of the estimate until the requester answers. `cite_law` is also ticked, and
   `access` is preset to copies. Plan §8 says the draft has "never a default value".
7. **Wording.**
   - "Deposits over $200": the trigger is charges "likely to exceed $200", and the deposit is capped at the advance
     determination.
   - `extension` help: omits the 60 work days for criminal investigative files in (B)(4).
   - The `email` sentence cites (G) for all records, but (G) covers database records, where the body has the
     capability.
8. **"All 31 tests pass in the container" is true only with `out/forms` copied in.** The CA snapshot-versus-store
   test also never runs by default: the host has no store, and the container has no snapshot.

## Missing

- CA notes for:
  - § 487: the board "shall conduct such hearing within 90 days" of the request. The curated next step,
    `hold_hearing`, cites it.
  - § 486(b), and the duty to serve the § 482 criteria.
  - The § 481(b) substantial-relationship factors.
  - The § 476 exclusions.
- VA notes for (F), the written notice and estimate inquiry required before a search, and for (C), the court
  petition for more time.
- Fixture revisions for CC-1201, A406-01PREDET, CR-180/181/409 and CR-410, and `final_url` for the redirected CA
  links.
- Code and test fixes:
  - a test that the official box comes first on the letter page;
  - an obligation check on field labels and placeholders;
  - neutral defaults.
- California statute text in `fixtures/statutes/ca_sections.json`: §§ 476, 480-482 and 485-487. I agree with the
  builder's open question.
- A comparison of the CA text with the official site.
- Lawyer review of both specs.
- Wiring in `steps.py`, `steps_of` and `ir.py`. This was out of the builder's scope.

## Re-check, 10 October 2026

_An adversarial re-check of the fixes, in container `lexflow-app-1`. No repository file was changed except this
section. No network request was made. `out/forms` was copied to the container's `/tmp` for one test run and then
deleted. The probes ran in memory from scripts piped to `python -`._

**Tests.** By default: **40 passed, 4 skipped**. The 4 skips are the worked-example and snapshot-vs-store tests,
because `/app/out` is not mounted. With `LEXFLOW_FORMS_OUT` pointing at the copy: **44 passed**. Rebuilding both
drafts in memory from the fixture and the local store (`as_of` 2026-10-10) gives JSON, form, letter and index
output byte-identical to `out/forms`. `check_steps()` returns `[]`, with 74 form references and 20 `no_form`
references. The Setup detail line is the one the plan quotes.

### Fixed (confirmed)

- **W1.** The scope and "Official form first" come before the letter, inside `.first-page{break-after:page}`, and
  a test covers this.
- **W2.** `seven_years` quotes all of § 480(a)(1)'s first sentence, word for word under (a)(1). It names (A) and
  (B), asks for the person's facts and asserts nothing. "not met" appears in no output. `seven_year_exceptions`
  quotes (A), (B) and (i)-(v).
- **W3.** § 476 is a source, and its (a) and (b) are correctly summarised. The practice-act wording in the scope
  matches the store for §§ 4202.6, 5100.2, 1687, 1958.1, 2660.5 and 4989.24.
- **W4.** Element links carry `match` and `role`. Pages show "Related official form" for BCIA 8016RR, never
  "Official form:". An `exact` link is refused, and so is BCIA as `partial`.
- **W5, the three cases as described.** Each is reproduced and now refused:
  - the phone element, on field label, placeholder, label and field relevance;
  - the purpose element, on bearer and relevance;
  - § 485's closing text cited as (b).

  The layout paths of all 8 sections were dumped and are right.
- **W6.** No defaults in either spec or page, and a truthy default is refused.
- **W7.** The deposit text follows (H), the extension follows (B)(4), and the email text is limited to (G)
  database records.
- **W8.** The counts in the plan are right.
- **Missing notes.** These are present, and each quote was checked against the store or fixture text:
  - California: §§ 487, 486(b), 486 (closing), 481(b) and 476(a);
  - Virginia: (F) notice before a search, and (C).
- **Fixture.** It now records these revisions: CC-1201 "07/26", A406-01PREDET "V2, 08/20/2026", CR-180, CR-181 and
  CR-409 "Rev. January 1, 2024", and CR-410 "New January 1, 2019".
  - The MD, TX and NY entries carry `revision_note`.
  - 13 entries have `verification.final_url`, 9 of them forms the fix had no reason to touch. That supports "it
    was already there". There is no history to prove it.
  - No contact details or personal names were found.

### Not fixed, or only partly fixed

1. **W5 is only partly fixed. Natural mistakes still pass `check()` and `build()`.** All of these were shown in
   memory against the real section text:
   - **Bearer false-accepts.** A `required` element "Mitigating information about your criminal history" can rest
     on § 480(f)(2). That is the sentence saying "disclosure is voluntary", yet it builds with the label
     "Required by the statute". § 487's duty of the board to hold the hearing within 90 days also passes as
     `required`. So do Va. (E) "Failure to respond ... shall be deemed a denial" and (F) "the request shall be
     deemed to be withdrawn". There are two causes:
     - "request" counts as a word for the person;
     - any "unless the applicant" or "applicant’s ... shall not" in the quote satisfies the check.
   - **`context` and `notice` elements are exempt from the relevance rule.** A `context` "Phone number" or
     "Purpose of the request" field resting on "within five working days of receiving a request" gives `[]`. So
     does a `notice` element with a phone field in the letter.
   - **The obligation list misses common words.** "need" (alone), "needed", "necessary", "compulsory",
     "obligatory", "mandated" and "expected to" are not caught, nor is a "*" marker. For example, field label
     "Medium (compulsory)" or help "You need a medium ..." on a `right` element passes.
   - **Spec-level free text is not scanned.** `summary`, `scope` and `related` titles can contain "You must give
     your phone number" and pass.
2. **WRONG (docs).** These sentences are false or overstated:
   - Plan §6.3, "So a duty of the public body cannot be presented as a requirement of the requester, and the
     reverse": § 487 is a counterexample.
   - The `draft.py` docstring says the checks catch "the kinds of invented content" in this note. They catch the
     listed cases; level-shifted variants pass.
   - The fix report says "The label and each field of an element must share a word with its quote". That holds
     only for `required`, `if_asked`, `duty` and `right`.
   - Plan §6 says the tests cover rules 1-11. Rule 10's `noopener noreferrer`/`no-referrer` is not tested. Of
     rule 11, only `sha256` is tested, in a test that skips by default; `url`, origin and `review` are not.
3. **Element-link strength check (W4 follow-on).** The check works only where the fixture links the form to a step
   of the same process. CR-180 is linked only under record sealing, so CR-180 as `partial` on `dismissed` passes.
   The conservative rule: a form with no link to the process may be at most `related`.
4. **The snapshot-vs-store comparison (W8) still never runs by default.** It runs only with `LEXFLOW_FORMS_OUT`.
   This is documented, and the open question about `ca_sections.json` stands.

### New observations (minor)

- **The printed letter's first sheet (scope and official box) has no banner,** and neither do the notes sheets.
  The top banner is `noprint`, and only the letter block carries one. Rule 8 ("on every page ... on the printed
  letter") holds for the letter block only. A banner inside `.first-page` and `.notes` would close this.
- **`only_if` help summarises § 480(a)(2) without its two qualifiers.** First, discipline older than seven years
  may still be grounds for the sexual-misconduct conduct described there. Second, discipline based on a dismissed
  conviction may not. This is the same selective pattern as W2, in a note.
- **The CA scope lists § 4989.24 among sections that "depart from § 480",** but its (b) says such a denial "shall
  comply with the conditions for denial specified in Section 480". The scope also omits the cannabis provision
  the curated notes list (§ 26057(b)(2), "except as otherwise specified"). Judgement call: soften the § 4989.24
  wording and add § 26057.
- **In (a)-style sections, `locate()` treats every unlettered paragraph as the section's own text,** not only one
  after the last subdivision as the docstring says. A flush paragraph inside (a) cited to (a) is refused, which is
  conservative. Cited with no subsection, it is accepted. No current spec is affected.

## Re-check 2, 10 October 2026

_A second adversarial re-check, of the round-2 fixes, in container `lexflow-app-1`. No repository file was changed
except this section. No network request was made. `out/forms` was copied to the container's `/tmp/rc2_forms` for
one test run and then deleted. The probes ran in memory from scripts piped to `python -`, against the real stored
section texts and some made-up ones. `registry.py` and `fixtures/forms/forms.json` are unchanged since the first
re-check (file times)._

**Tests.** By default: **68 passed, 4 skipped**. Two skips are the worked-example tests and two are the text-by-text
snapshot-vs-store tests, because `/app/out` is not mounted. With `LEXFLOW_FORMS_OUT` pointing at the copy: **72
passed**, including the byte-identical rebuild. The SHA-256 test runs by default and passes for both specs, with
California's text read from the store.

### Fixed (confirmed)

- **W5, who a `required` element binds.** All four cases are refused: § 480(f)(2), § 487, Va. (E) and Va. (F).
  Every sentence of the 8 stored sections was tried at each mandatory level:
  - Only 3 pass as `required`: Va. (B) "shall identify", § 480(c) "shall provide proof", and § 485(b) "Unless
    written request ...". Each is a real requirement of the person.
  - Only 2 pass as `if_asked`: Va. (A) name and address, and Va. (I) earlier unpaid bills. Both are right.
  - 28 pass as `duty`. Each is a duty or a prohibition of the board or the public body. None is a grant or a deemed
    effect.
- **Level shifts.** § 480(f)(2) as `if_asked`, (B)(4)'s extra days as `duty`, and a requester's duty as a public-body
  `duty` are refused. The "Unless" clause bug is gone: § 485(b) now gets its own clause.
- **Context and notice.** A context "Phone number" or "Purpose" field on the date quote is refused. So is a notice
  that has fields or sits in the letter, and a duty that has fields.
- **Obligation words.** Every word the re-check named is caught, and so is "*". The title, summary, scope, related
  headings, the fixture's no-form note and the letter's fixed parts are all scanned.
- **W4.** CR-180 as `partial` on `dismissed` is refused.
- **Docs.** The false §6.3 sentence is gone, and the docstring no longer overstates. The rule 10 and rule 11 tests
  run by default. The counts in the plan are right: 72 tests, VA 20 elements (10 + 10), CA 26 (13 + 13).
- **Banner.** In the built letter page, the scope and official box, the letter and the notes each start with the
  banner. The `@page` top-center rule is there.
- **§ 480(a)(2).** The `only_if` help gives both qualifiers correctly. The `formal_discipline` quote equals the
  whole stored (a)(2) paragraph, with only its "(2)" mark left off.
- **Scope.** § 4989.24(a) and (b), § 26057(b)(2) and § 26001(w) match the store. So do §§ 5100.2 and 2660.5.
- **`locate()`.** None of the 84 paragraphs in the 8 sections is ambiguous.
- **Privacy.** The forms files hold no email addresses, phone numbers, personal names or pay.

### Not fixed, or new

1. **DEFECT and OVERSTATED: a requirement of the person can be shown as a choice, a context line or a note.**
   These elements pass `check()` and `build()` with their real quotes:
   - § 485(b) `hearing_request`, § 480(c) `dismissal_proof` and Va. (B) `records` as `right`, which the page labels
     "Your choice under the statute";
   - the same three as `context`;
   - the same three as `notice`, once they are taken out of the letter.

   A `required` element can also be left out of the letter. Plan rule 3 says "Levels say how strong each element
   is, and the quote must bear it out". That holds only for `required`, `if_asked` and `duty`.

   The conservative fix: refuse a `right` or `context` element whose quote passes the `required` test, and require
   every `required` and `if_asked` element to be in the layout. A `notice` is a judgement call. I checked that no
   current element would be refused by either rule.
2. **DEFECT (minor): the letter-field exemption checks only that the label contains the word.** These context
   fields pass:
   - `name` labelled "Your name and phone number", or "Name, phone and date of birth";
   - `date_sent` labelled "Date you send it and your date of birth".

   This reopens the re-check's context "Phone number" case. The fix: an exempt field's label may hold only the
   name or date words.
3. **DEFECT (minor): gaps in the obligation list.** These pass in a `right` element's field label: "should", "ought
   to", "requiring", "essential", "compelled", "obliges", "obligate", "necessity", "needful", "req.", "please
   provide", "is to be given", and the "＊" and "∗" marks.

   "should" matters most, because rule 12 says help does not recommend. None of these words is in the current
   specs.
4. **OVERSTATED (minor): the limit in plan rule 3 is narrower than the real one.** It names only hidden bearers and
   party words the spec does not list. These made-up sentences are accepted although they are neither:
   - As `required`:
     - "The requester shall receive a copy of the records." and "shall obtain a refund" (a benefit with an active
       verb);
     - "Unless the requester agrees, the request shall not be denied." (a negated consequence);
     - "A request for public records that the public body shall answer ... is valid." The real subject is passed
       over as subordinate, so the "shall" falls to "request".
     - "The public body or the requester shall decide."
   - As `duty`: "However, a public body shall not be required to create a new record." and "shall not be obliged
     to answer". These are exemptions, which the page would show as "What the other side has to do". Other states'
     records acts use this wording, and they are the plan's next specs (§9).

   The real sections give no false accept, and the general sentence in the limits paragraph covers these cases.
   Rule 3 should still name them, or the code should refuse them: receive/obtain after the mandatory word,
   negation in the consequence, a mandatory word whose nearest party is passed over, and "shall not be
   required/obliged" for a duty.
5. **WRONG (minor), docs.** Plan rule 11 quotes the review status as "draft, machine-checked; not reviewed by a
   lawyer". The code writes "draft, machine-checked (quotes and rules); not reviewed by a lawyer".
6. **Nits.**
   - The docstring and rule 3 say a subject may follow "a comma, a paragraph mark or and/or". The code also accepts
     ";", ":", "but" and "then".
   - In rule 3, "For this reason § 481(b) ..." comes right after the sentence about "shall not". The real reason is
     that "Criteria" is not the other side.
   - § 480(f)(2)'s "shall not be a factor" passes as a `duty`. That outcome is defensible, but the bearer the code
     finds is "a board may request", not the clause's real subject.
   - The scope's "that registration" for § 4989.24 leaves out "or the equivalent in another state or territory".
     That is acceptable in a pointer that says to read the act.
7. **Unchanged and documented.**
   - The text-by-text snapshot-vs-store test needs `LEXFLOW_FORMS_OUT`.
   - `ca_sections.json` lacks the sections.
   - The CA text has not been compared with leginfo.
   - Both specs still need a lawyer's review.
   - The wiring is outside this area.

   The fix report's metric "23 false accepts now refused" was not recounted.

## Re-check 3, 11 October 2026

_A third adversarial re-check, of the round-3 fixes, in container `lexflow-app-1`. No repository file was changed
except this section. No network request was made, and nothing was written to any service. Probes ran in memory
from scripts piped to `python -`, against the real stored section texts and some made-up ones. `out/forms` was
copied to the container's `/tmp/rc3_forms` for one test run. For a mutation check, a copy of the code, the
fixtures, the curated files, the test file and the plan went to `/tmp/rc3_tree`. Both copies were then deleted.
`draft.py`, `test_forms.py` and `forms-plan.md` had the same MD5 at the start and the end, and nothing was
written to `out/forms`._

**Tests.** By default: **104 passed, 4 skipped**. The skips are the 2 worked-example rebuild tests and the 2
text-by-text snapshot tests, because `/app/out` is not mounted. With `LEXFLOW_FORMS_OUT` pointing at the copy, the
worked-example, snapshot, hash and provenance tests give **8 passed**, including the byte-identical rebuild. So all
108 tests pass across the two runs.

**Mutation check.** In the throwaway copy, each of 22 round-3 fixes was undone in turn and the matching tests were
run. Each undo made at least one test fail:

- the `passes()` checks, the layout rule and the no-parties rule;
- the exempt label's word list, and its no-placeholder and no-options rule;
- NFKC folding, format-character removal, the non-Latin letter check and the asterisk-name check;
- the benefit verbs, the negated consequence and the relative-clause rule;
- the own-verb rule, its second-verb exception and the joint-subject rule;
- the exemption rule and "should";
- the rule 11 wording, a joiner that the docs do not name, and the old § 4989.24 scope;
- "Please send me" in the VA letter.

The fixer's "41 failed" against the original code was not recounted: the round-2 code is not kept.

### Fixed (confirmed)

- **Item 1, levels.** With their real quotes, § 485(b) `hearing_request`, § 480(c) `dismissal_proof` and Va. (B)
  `records` are refused as `right`, `context` and `if_asked`. With them taken out of the letter, they are refused
  as `notice` and `duty`. Left out of the layout as `required`, each is refused. `name_address` is refused as
  `right`, as `context`, and when left out of the layout. A spec with no parties is refused. Neither real spec
  gives a problem.
  - The judgement call on (I) `unpaid`, a `notice` resting on "may require", is accepted.
- **Item 2.** "Your name and phone number", "Name, phone and date of birth" and "Date you send it and your date of
  birth" are refused. So is an exempt field with a placeholder or options.
- **Item 3.** Every word and mark the re-check named is refused in a `right` element's field label. That includes
  "should", "please provide", "is to be given", "＊" and "∗".
- **Item 4.** All seven made-up sentences are refused: receive, obtain, the negated consequence, the relative
  clause, the joint subject, "shall not be required" and "shall not be obliged".
- **Item 5.** Rule 11 quotes the status the code writes, and a test compares them.
- **Nits.**
  - The docstring and rule 3 name every joiner, and a test checks them against `_JOINERS`.
  - The reason given for § 481(b) is right.
  - § 480(f)(2) is refused as a `duty`, while Va. (F) "may ... and shall" and (G) "may ... but shall" stay duties.
  - The § 4989.24 scope matches the store text. Subsection (a) says "shall not issue a license to a person who
    has been convicted of a crime in this or any other state or in a territory of the United States ... or the
    equivalent in another state or territory".
- **Sweep.** The 8 stored sections hold 139 sentences. Each was tried at each mandatory level:
  - `required`: 3 pass, Va. (B), § 480(c) and § 485(b);
  - `if_asked`: 2 pass, Va. (A) and (I);
  - `duty`: 27 pass, none of them a grant, a deemed effect or an exemption.

  This matches the report. The claim that the only change from the old code is § 480(f)(2) could not be checked.
- **Worked examples.** `out/forms` holds the new VA cost-estimate sentence and the new CA scope, and no "Please send
  me". The statute hashes equal the test's `BUILT_FROM`.
- **Privacy.** The forms files hold no email addresses or phone numbers.

### Not fixed, or new

1. **DEFECT and OVERSTATED: a requirement can still be shown as a choice, a context line or a note, if its quote is
   trimmed.** `passes()` runs the `required` test on the quote, and that test wants the bearer inside the quote.
   A quote that starts at "shall" leaves the bearer out, so the lower-level check never fires. These pass `check()`
   and `build()`:
   - Va. (B) `records` as `right` (the page shows "Your choice under the statute"), as `context` and as `notice`.
     Its quote is "shall identify the requested records with reasonable specificity".
   - § 480(c) `dismissal_proof` as `right` and as `notice`. Its quote is "shall provide proof of the dismissal if
     it is not reflected on the report furnished by the Department of Justice".
   - Va. (B) as `right` with no marker at all: "identify the requested records with reasonable specificity".

   So these claims are false:
   - the docstring's "a requirement is never shown as a choice (`right`), a context line, a note or a duty of the
     other side";
   - plan rule 3's "§ 485(b)'s hearing request, § 480(c)'s proof of dismissal and Va. Code § 2.2-3704(B)'s
     identification of the records cannot be shown as a choice, a context line, a note or a duty of the other
     side".

   They hold only for the full-sentence quotes. `duty` is safe, because its bearer test reads the whole clause.

   The conservative fix: for the lower-level check, run the `required` test on the whole sentence or sentences of
   the section text that the quote overlaps, and do not ask for the bearer inside the quote. I tried this in
   memory. It refuses all three trimmed cases and no current element.
2. **NEW (regression from the relative-clause rule).** The rule gives no bearer when the party right before the
   mandatory word is passed over. It also fires when that party is the object of a preposition inside the subject,
   not only in a relative clause. These made-up sentences are refused as `required`:
   - "A request made to the custodian shall identify the records with reasonable specificity."
   - "A request to the custodian shall identify the records."
   - "Any request submitted to the public body shall be in writing."
   - "A request made to a public body shall be signed."

   Because `passes()` uses the same rule, the first is then **accepted as `right`**. That is item 1's defect again.
   None of the 8 stored sections has this wording, and the sweep is unchanged. But records acts often word a rule
   this way, and they are the plan's next specs (§9).

   The `_bearer_at` docstring says the word is "that party's, in a subordinate clause". That is wrong for these
   sentences.

   The fix: apply the rule only when a relative word ("that", "which", "who", "whom", "whose") stands between the
   subject and that party. For the lower-level check, the conservative choice is to count such a sentence as
   passing.
3. **DEFECT (minor): a letter sentence's own words are not checked.** The relevance rule reads labels and fields,
   and the obligation rule reads obligation words. Nothing reads the rest of the letter text, so the first
   verification's phone case can move into it. These pass:
   - `name_address` with the letter "My name, legal address and phone number: ... Phone: ________";
   - `records` with "My purpose: ____ My date of birth: ____";
   - `applicant` (context) with "Telephone: ____________";
   - a closing of "Sincerely, {name} Phone: ______________".

   The conservative fix: refuse a run of underscores (blanks come only from fields), and make the content words of
   letter text outside its placeholders share a word with the element's quote or labels, or come from a short list
   of letter words. The closing, subject and salutation would be held to that short list. The exact rule is a
   judgement call.
4. **DEFECT (minor): Unicode gaps of the same kind as DEFECT 3.** These pass in a `right` element's field label:
   - **Invisible characters that are not format characters (Cf):** "required" with U+034F (combining grapheme
     joiner) inside it, "need" with U+FE00 (a variation selector) and "must" with U+180B (a Mongolian variation
     selector).
   - **Look-alike letters in the Latin script:** "ʀequired" (U+0280), "muꜱt" and "ꜱhould" (U+A731) and "neeɗ"
     (U+0257).
   - **Whitespace other than one space inside a phrase:** "have  to" (two spaces), "have" and "to" split by a tab
     or a newline, and "Be  sure". HTML shows each of these as one space.

   The fix: remove every default-ignorable code point, or refuse any combining mark. Require each letter's NFKD base
   to be ASCII (the specs use no other letters). Write `\s+` inside the phrases of `_OBLIGATION`.
5. **MISSING (minor): obligation words not on the list.** A `right` element's help may say "It is imperative
   that ...", "You have a duty to ...", "You are bound to ...", "Ensure you ...", "We insist that ..." or "... is
   vital". "Duty" has to be matched as a phrase ("a duty to"), because "duties" appears in the CA
   `seven_year_exceptions` help. "Recommended" and "important to" are advice. Under rule 12 that is for review, not
   code.
6. **OVERSTATED (minor): the joint-subject rule.** The docstring says there is no bearer when "the party found is
   joined to a party of the other side". The code only sees "and", "or", "nor", "either", "both", "neither" and
   commas between the two parties. "The requester, as well as the public body, shall decide." passes as
   `required`. "Together with" and "along with" are refused, but only because the relative-clause rule happens to
   catch them. Rule 3 should list this as a gap, or the code should add "as well as", "together with", "along
   with" and "in addition to".
7. **Minor: exemptions worded a little differently pass as `duty`.** The rule reads only the words right after
   "shall". These pass:
   - "The public body shall not, however, be required to create a record."
   - "... shall in no case be required ..."
   - "... shall never be required ..."
   - "... shall be under no obligation to ..."

   Rule 3's gaps should name this, or the check should search the rest of the clause.
8. **Minor: a `required` element can be made optional in the letter.** Give `hearing_request` a checkbox field
   "Ask for a hearing" and `when` set to that field. It passes, and the printed letter shows the sentence with a ☐
   that the page says to strike out if it does not apply. `dismissal_proof` uses `when` correctly, because its
   `condition` says when it applies. The conservative rule: a `required` element with a `when` must have a
   `condition`.
9. **Nit: symbols in an exempt label.** The label check reads only word characters. So "Your name ☎", "Your name
   ✉" and "Your name @" stay exempt. The fix: an exempt label may hold only letters, spaces and basic punctuation.
10. **Unchanged and documented.** These are the same as before:
    - the text-by-text snapshot test needs `LEXFLOW_FORMS_OUT`;
    - `ca_sections.json` lacks §§ 476, 480-482 and 485-487;
    - the CA text has not been compared with leginfo;
    - both specs need a lawyer's review;
    - the wiring in `steps.py`, `steps_of` and `ir.py` is outside this area.
