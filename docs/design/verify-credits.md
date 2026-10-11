# Check of the Setup-page credits

Checked on 10 October 2026 against `lexflow/pipeline/credits.py`, the `credits=` lines in `lexflow/pipeline/steps.py`, `/api/setup` in `lexflow/api/app.py` and the `creditList` code in `dashboard/app.js`. All HTTP was read-only, at most one request a second per host, sent with the lexflow-research User-Agent.

## Confirmed

- **Tests.** `tests/test_credits.py`: 5 passed. The two checklist tests in `tests/test_product.py` pass, and `node --check dashboard/app.js` passes.
- **Rendering.** The new credit data was injected into the live Setup page with a stubbed `/api/setup`.
  - All 15 steps render, with 15 credit blocks (13 lists and 2 notes) and 51 lines (33 step credits, 17 general credits and 1 test entry). There were no errors.
  - A test entry made of HTML and a `javascript:` URL was shown as plain text, so `h()` escapes what it writes. The 50 links are all https, `target=_blank` and `rel=noopener`.
  - At 375 px in dark mode the page width is 375, so there is no horizontal scroll. The only element wider than the screen is the existing `nav.tabs` scroller.
  - With the API the container serves now, the page shows 15 steps, no credits and no console errors.
- **Sources checked against the maker's own page:**
  - LOCUS-v1: cc-by-nc-4.0, org LocalLaws. The card's BibTeX `peskoff2026freeing` matches the arXiv API for 2606.19334, and the DOI resolves.
  - Open US Law: CC BY-NC 4.0 for the compilation, Apache-2.0 for the scrapers, and commercial use needs a licence. The BibTeX matches word for word. The local `index.json` says v2026.09.1 and `CC-BY-NC-4.0`.
  - Qwen3-1.7B: apache-2.0, and the citation matches.
  - nomic-embed-text-v1.5: apache-2.0, and the citation matches. Ollama's `latest` tag is the same image as `v1.5` (digest 0a109f422b47).
  - Gemma: the notice text matches the Gemma Terms of Use exactly, and Gemma 3 is in the terms' appendix. The card's BibTeX matches the citation.
  - pm4py: AGPL-3.0-or-later. The source headers say "or any later version" and so does the package metadata. The README says AGPL-3.0, and its citation matches.
  - SpiffWorkflow: the licence file is LGPLv3, and CITATION.cff gives the concept DOI 10.5281/zenodo.14966563, which resolves.
  - CourtListener: the API v4 overview gives 5, 50 and 125 requests for authenticated users.
  - bpmn.io and the bpmnio plugin: both licences include the watermark clause.
  - Census: the page title is "2022 Government Units Listing". The Government Units Survey was discontinued on April 14, 2025.
  - Wikidata is CC0, Govdirectory is CC0 1.0, and SQLite is public domain. Graphviz is EPL. The OMG BPMN 2.0 page gives IPR mode RF-RAND.
  - Every other library licence matches its installed metadata or its GitHub licence.
  - All 49 credit URLs resolve.
- **No endorsement.** No credit uses partner, advisor, endorse or thanks wording. Researchers are named only as authors in citations, and the "Credit is not endorsement" line is shown.

## Wrong

1. **PuLP is MIT, not "BSD".** Both the repository's `LICENSE` and the installed 2.9.0 `dist-info/LICENSE` contain the MIT licence. Only the PyPI classifier says BSD. PuLP also ships the CBC solver binaries under EPL-1.0, and they are not credited.
2. **The CourtListener note leaves out the restrictions.** It lists only the uses the policy allows. The policy (titled "Membership-Based API Usage Restrictions") also says membership access:
   - may not "power a revenue-positive commercial product";
   - may not "be used to build tools for for-profit or non-profit organizations";
   - allows one account per person, with no sharing of API keys.

   The credit links to the project page, not to `https://free.law/membership/allowed-api-usage/`.
3. **The citations are not "exactly as the maker asks".**
   - LOCUS, nomic, Qwen and Gemma are rewritten from BibTeX. Their content is correct.
   - The SpiffWorkflow citation leaves out the authors and version listed in CITATION.cff.
   - POWL asks for no citation: its README only says "please refer to the paper".
4. **"or later" is applied unevenly.** These three keep plain version numbers although their makers grant "or later":
   - SpiffWorkflow: the file headers say LGPL "version 3.0 ... or any later version" (141 files).
   - SearXNG: the SPDX headers say AGPL-3.0-or-later.
   - Wikibase: `extension-repo.json` says GPL-2.0-or-later.
5. **The POWL URL has moved.** The old repository URL, under an individual author's personal account, now redirects (301) to `github.com/fit-process-mining/POWL`.
6. **The module docstring claims too much.** It says every credit "was checked against the maker's page". The research note marks about 14 of them as checked from package metadata only, and Node.js and Python as not checked. PuLP is one of the metadata-only entries.
7. **Small fixes.**
   - The project's own name is "Govdirectory", and its URL redirects to `www.govdirectory.org/about/`.
   - The OMG "licence" shown is the patent IPR mode, not the terms for the XSD files.
   - The page shows "Ollama (Ollama)".
   - Many links have the same text, "github.com ↗", and no aria-label to tell them apart.

## Missing

- **SearXNG has no credit on the Setup page.** It appears there as a service card, but its credit is only on the `ask` job, and that job is not shown on the Setup page.
- **The Open US Law version is fixed in the text.** The credit names v2026.09.1, but `statutes.py` downloads whatever version the manifest currently lists, so the name will fall out of date at the next release.
- **The model credits do not follow `config`.** This was already raised as an open question.
- **Not checked:**
  - CourtListener's site terms (`courtlistener.com` returns 403 to scripted requests);
  - the full text of the Turso, Hugging Face and Wikibase.cloud terms;
  - the OMG DMN 1.3 page;
  - us-atlas's 2017 provenance.

## Re-check, 10 October 2026

This is a second, adversarial check of the fixes in `credits.py`, `steps.py`, `caselaw.py`, `dashboard/app.js`, `scripts/viewer_template.html` and `tests/test_credits.py`. Nothing in the code was edited. There were two read-only requests, both to raw.githubusercontent.com, two seconds apart, sent with the lexflow-research User-Agent: SpiffWorkflow's `CITATION.cff` and Cbc's `README.md`.

### Tests

In `lexflow-app-1`, with no skips:

- `test_credits`, `test_caselaw`, `test_review_pipeline` and `test_product`: 53 passed.
- `test_credits`, `test_review_jobs`, `test_ask` and `test_caselaw`: 54 passed.
- `node --check dashboard/app.js` passes.

A stub-DOM render of `creditList` covered every step, the composite steps and GENERAL: 16 lists and 63 links. All the links are https with `rel=noopener`, no list repeats an aria-label, and no line shows "X (X)".

### Fixed

- **Wrong 1.** The PuLP 2.9.0 `dist-info/LICENSE` is MIT. All six bundled `pulp/solverdir/cbc/*/coin-license.txt` files are EPL-1.0, and CBC is credited on the build step.
- **Wrong 2.** The note now gives the restrictions and the 5, 50 and 125 limits, and `licence_url` links the policy.
- **Wrong 3.**
  - `cite_by` is shown on the page, and only Open US Law is marked "maker".
  - The SpiffWorkflow citation matches `CITATION.cff`: version 3.1.1, released 2025-03-04, the concept DOI and the five authors in order. For one author the file's family and given names look swapped, and the citation copies the file as it is. That is a judgement call and it stands.
- **Wrong 4.** 141 of the 141 SpiffWorkflow file headers say "or any later version". SearXNG and Wikibase now carry the "or later" names.
- **Wrong 5** and **Wrong 7** are fixed.
- **Missing: SearXNG and Open US Law.** SearXNG is in GENERAL. `statutes.py` records the manifest version with each state's file, as the new note says.
- **Missing: model credits.** They follow config. An unknown tag gets an explicit "Not checked" credit.
- **Pacing.** Every request goes through `PACER`, 429 retries included. A refusal counts nothing.
- **Cost text.** The live database has 499 sections over 47 states, a median of 9 per state, so "about 12 a state, about ten states a day" is fair.

### Still wrong, or new

1. **DEFECT: failed searches now count as searched.** This regression comes from the new rerun skip.
   - `search()` logs any non-429 error and returns what it has (`caselaw.py:211-213`). The errors include a 400 from a wrong court id, a 401 or 403 from a bad token, a 5xx and a timeout.
   - `run()` then logs "0 opinions", and `run_cases` writes a `scans` row with status `done` (`steps.py:403-404`). `st_cases` counts that state as done, and the next run that names no states skips it.
   - Reproduced with HTTP 500. The first run logged "search failed" and then "0 opinions", and wrote `scans(courtlistener, va, status=done)`. The second run logged "skipping 1 state already searched" and made 0 requests.
   - Before the fix, a rerun retried the state. With a bad token, every state searched that day is recorded as having no opinions.
   - The comment over `COURTS`, "a wrong id is a 400, logged, not '0 opinions'", is false.
2. **DEFECT: Redo cannot get past the first day's states.**
   - A Redo (`force`) run always starts again from the first state alphabetically and stops at the day's limit.
   - A run without Redo skips every state ever searched, however long ago.
   - Simulated with 15 states and 5 a day: days 1 to 3 covered all 15. Days 4 and 5, both with Redo, both searched ak, al, az, ca and ct. Day 6 searched nothing.
   - States after the first day's worth can be refreshed only by naming them.
3. **DEFECT: the status and the rerun disagree about existing data.**
   - `st_cases` counts a state as done when it has any `case_law` row. The rerun skips only states that have a `scans` row.
   - The live database has `case_law` rows for CA, DC, MD and VA but no `courtlistener` scans rows. The first run that names no states will therefore search all four again: 84 sections, or 84 to 168 requests, which is more than a day's 125. CA and DC come early in alphabetical order.
   - The reverse also happens. A state stopped partway by the daily limit shows as done when one opinion was stored.
4. **OVERSTATED: "a single search from Ask waits a minute at most"** (the `caselaw.py` docstring).
   - Only the pacer's wait is capped. The 429 retry loop sleeps for `Retry-After` (up to 300 s) or for 30 to 120 s on each retry, outside `max_wait`.
   - Reproduced: four 429s with `Retry-After: 300` made one Ask search wait 1,200 s. Ask searches two sections, so it can wait up to 40 minutes.
5. **OVERSTATED: the `credits.py` docstring** still says "The data, service and model credits were checked against the maker's own page".
   - It is false for a model that config names other than the three default tags, whose credit says "Not checked".
   - It is also too broad for the terms listed under "Not checked" above.
6. **Minor: the CBC licence and install note.**
   - The linked `github.com/coin-or/Cbc` README says EPL-2.0. The credit's EPL-1.0 is the licence of the bundled binaries, and the credit should say so.
   - "Installed with pm4py" is loose. pm4py's metadata does not require PuLP; lexflow's `requirements.txt` installs it (`pulp<3`).
7. **Not yet effective in the built viewer.** The built `out/viewer/lexipedia-viewer.html` (9 October) still has `.canvas .bjs-powered-by { opacity: .55; }` at line 82. It needs `scripts/build_viewer.py` to run again. Builds were not run in this check.
8. **Minor: the credit and the code disagree on accounts.**
   - The CourtListener credit says the step "needs a CourtListener account". `run_cases` runs without `COURTLISTENER_TOKEN`, and the `LIMITS` comment says anonymous use is paced the same way. Only Ask requires the token.
   - The pacer adds no margin. It counts reserved times, not the times requests arrive, so network jitter can still bring a 429.
9. **Docs not updated.** These files are not the fixer's.
   - `credits-research.md` line 3 still says every entry was checked against the maker's page. The `credits.py` docstring sends readers to that note.
   - Other stale lines in `credits-research.md`:
     - "Gov Directory" (lines 21, 45, 58, 60 and 143);
     - plain "GPL-2.0" for Wikibase (line 48);
     - plain "AGPL-3.0" for SearXNG, pm4py and powl (lines 52, 82, 83, 132 and 145);
     - plain "LGPL-3.0" for SpiffWorkflow (lines 85, 132 and 145);
     - the old POWL URL (line 83);
     - PuLP as "BSD" (line 84);
     - line 127, which describes the old one-request-a-second pacing as current.
   - README line 342 says a rate limit means a state "is never recorded as 'no opinions'". That holds only for 429; see item 1. README lines 366 and 367 still give plain AGPL-3.0 and LGPL-3.0.
10. **Observation, not checked further.** The viewer's footer presents LOCUS-v1 text as "Local code text". The LOCUS credit says it is "used to find law, never to cite it".

### Privacy

No staff names or contact details were added. The citation names only authors, and the CFF affiliations and ORCIDs were left out. The pace file holds timestamps only.

## Re-check 2, 10 October 2026

This is an adversarial check of the second round of fixes, in `caselaw.py`, `steps.py`, `credits.py`, both test files, `scripts/viewer_template.html`, `out/viewer/lexipedia-viewer.html` and `credits-research.md`. Only this note was edited, and no HTTP request was sent. The live store (`/data/lexflow.db`, opened `mode=ro`), the job logs and the pace file were read but not written. Every reproduction ran in a temporary store, with `requests.get` faked and the pacer on a fake clock and a temporary file. The mutations ran in a throwaway copy under `/tmp` in the container.

### Tests

In `lexflow-app-1`:

- `test_caselaw` and `test_credits`: 48 passed, 1 skipped.
- With `test_product`, `test_review_pipeline`, `test_review_jobs` and `test_ask`: 99 passed, 1 skipped.
- The skip is `test_the_built_viewer_has_the_same_fix`, because `/app/out` is the image's copy. The same checks pass on the host.

### Fixed (confirmed)

- **Defect 1.**
  - Reproduced with HTTP 500. The first run writes `failed: § va-1: HTTP 500 Internal Server Error` and logs no "0 opinions". The second run searches the state again and records it as `done`.
  - With a token set and a 401 answer, the token goes in the request header but not in the scans row, the result or the log.
  - The `COURTS` comment is now true.
- **Defect 2.** This was simulated with the real `caselaw.run` on 20 states of 12 sections each, against the real pacer.
  - Two days covered all 20 states. Four Redo days then alternated between the first ten states and the second ten.
  - A run with `all`, or with a done state named but no Redo, searched nothing.
  - The busiest window held exactly 1, 5, 50 and 125 requests, which are the limits.
- **Defect 3.**
  - The status and the rerun now count the same 52 states with the same meaning of done.
  - A stopped state is recorded as `stopped:` and is searched first.
  - Live, read-only: 7 of 52 states are done. The next run's order is FL to WY, then DC, MD, CA and DE.
- **Overstated 4.** In the old 1,200-second case (429 answers with `Retry-After: 300`), Ask's search now raises after the first 429, having waited 1 s. `court_decisions` makes one request and returns `[]`.
- **Also fixed:**
  - Overstated 5.
  - Minor 6.
  - Item 7, in the checkout. The built page differs from the template only in the CSS and data placeholders, and its footer is identical.
  - Minor 8.
  - Item 10.
  - Item 9, except line 3 of the research note (item 6 below).

### Still wrong, or new

1. **New defect: one failing section blocks every other state.**
   - A failed state is searched first, and a timeout, a 5xx or a non-JSON answer stops the run. So when one section fails that way every time, every run starts with that state and stops there.
   - Reproduced with 5 states, one of them with a section that always times out. Four runs made 3 requests each, and 0 of 5 states were done.
   - The live logs show it can happen:
     - Job 41 timed out on DC § 29-704.04 and HI § 428-203.
     - In job 66 one answer took about 60 s, and the timeout is 90 s.
     - HI is third in the live queue.
   - Nothing false is recorded, and the Setup detail names the state. But a plain rerun cannot get past it: the only way round is to name the other states.
2. **Wrong (minor): states with nothing searched are recorded as `done`.**
   - PR has one verified section but no court ids. `caselaw.run` returns before searching, and `run_cases` writes `done` with 0 rows. The `run_cases` and `_cases_progress` docstrings say a state is done "only when the search of every section answered", which is false for PR. The status counts PR as "searched to the end".
   - AR and CO have no statutes and 0 sections, so they are done without a search and counted the same way.
3. **New (minor): a cancelled or restarted run leaves its state at the back of the queue.**
   - The job is stopped with SIGTERM, so the state it was searching has opinions but no scans row. It counts as "stored" and is searched only after the 40 or so states never searched. Reproduced.
   - Live: DE, which job 66 is searching now (it is waiting 50 min for the hourly limit), is shown as "searched again after the states never searched".
   - The docstring gives only older searches and Turso pulls as the reasons a state can be "stored".
4. **Overstated (minor): 429s are not only from other clients.**
   - The `caselaw.py` docstring calls CourtListener's 429s "the backstop for other clients using the same account".
   - Job 66 runs with no token, so there is no account, and the pace file shows no other lexflow requests at the time. It still got a 429 at 00:11:33 UTC.
   - lexflow sent 5 requests between 00:11:29 and 00:11:33. An earlier one, sent at 00:10:28.7, took about 60 s to answer. So CourtListener does not count requests the way the pacer does, and the difference is more than the 2 s margin.
   - The back-off (56 s) handled it, and nothing was recorded wrongly.
5. **Out of date: anonymous search.** The CourtListener credit says that whether anonymous search still answers "was not checked". Job 66 has no `COURTLISTENER_TOKEN` and gets answers today.
6. **Research note line 3.** It says the data and service entries were checked, except those under "Not verified here". That list leaves out several items the `credits.py` docstring now says were not read:
   - the full Hugging Face and Turso terms;
   - CourtListener's site terms;
   - the OMG DMN 1.3 page and the XSD terms;
   - us-atlas's 2017 provenance.
7. **Test gaps.** The code is right in each case, but each of these mutations survived:
   - a Redo that fails on a done state overwrites its record;
   - the pacer gets `max_wait` rather than `max_wait - waited`;
   - a back-off follows the last 429;
   - a timeout lets the run go on;
   - a JSON answer that is not an object is accepted.

   The fixer's own mutations that were repeated here were caught.
8. **Judgement call (minor): the default states box.**
   - The cases card's states box still defaults to "va", and VA is done. So a run with the default searches nothing.
   - The log says "tick Redo", which would search VA again (about 24 requests) instead of moving on. The cost text does explain that the box should be empty.
9. **Not the fixer's files:**
   - README line 346 still says "150 so far, for CA, DC, MD and VA". The live store has 579 decisions across 9 states.
   - The README licence table still gives plain AGPL-3.0 and LGPL-3.0.
   - The viewer copy in the container's `/app/out` still has the opacity rule. The API does not serve it.

### Privacy

The changed files contain no email addresses or staff names, and citations name authors only. The scans `status` holds the HTTP status and reason phrase. It was checked with a token set and never contained the token.

Privacy pass, 10 October 2026: in this note, an author's personal repository account (Wrong 5) and an author's quoted name fields (Fixed, Wrong 3) were replaced with neutral descriptions. The findings are unchanged.

## Re-check 3, 11 October 2026

This is an adversarial check of the third round of caselaw fixes, in `caselaw.py` and `tests/test_caselaw.py`.
- Only this note was edited, and no HTTP request was sent.
- The live store (`/data/lexflow.db`, opened `mode=ro`), job 66's log and the pace file were read but not written.
- Every reproduction ran in a temporary store, with `requests.get` faked and the pacer on a fake clock and a temporary file.
- The mutations ran in a throwaway copy under `/tmp` in the container. The copy has since been deleted.

### Tests

In `lexflow-app-1`:

- `test_caselaw`, `test_credits` and `test_ask`: 78 passed, 1 skipped.
- With `test_product`, `test_review_pipeline` and `test_review_jobs` added: 118 passed, 1 skipped.
- The skip is `test_the_built_viewer_has_the_same_fix`, as before.
- In the throwaway copy, `test_caselaw` gave 40 passed.
- **Mutations.**
  - The fixer's 13 mutations were repeated here, and all 13 were caught.
  - Of 10 more tried here, 9 were caught:
    - a search with no court ids returning `[]` in strict mode;
    - Skipped without its "skipped:" prefix;
    - 5xx set to go on;
    - not-JSON set to go on;
    - the `next` check alone removed;
    - the result-object check alone removed;
    - `failed` ranked before `new`;
    - the token added to a 401 reason;
    - the 429 back-off ignoring `max_wait`.
  - One survived (item 6 below).
- The fixer's "49 passed, 1 skipped before my changes" could not be repeated, because no earlier copy was available. Re-check 2 recorded 48.

### Fixed (confirmed)

- **Re-check 2, item 1: one failing section blocked every other state.**
  - Reproduced with five states, one of which has a single section that always times out.
  - The first run stopped at that state, as it should, since the state was new.
  - The second run searched the three states not yet searched, then went past the failing state. After two runs, 4 of the 5 states were done.
  - Each later run spends one request on the failing state.
- **Item 2: states with nothing searched were recorded as done.** For new records this is fixed:
  - PR (no court ids) and a state with a model but no section are recorded as `failed: skipped: ...`. They make no request and do not stop the run.
  - The Setup status leaves them out of "searched to the end".
  - Three runs in a row on PR made no request, and each run looked at PR again.
  - Once such a state gets a section, the next run searches it and records it as done.
- **New, found by the fixer: the empty court filter.** `search("pr", ...)` now makes no request. Ask gets `[]`, and strict mode raises Skipped. Both behaviours are pinned.
- **Item 4: 429s described as "the backstop for other clients".** The new docstring matches job 66's log and the pace file:
  - The request sent at 00:10:28.7 UTC was answered at 00:11:29.
  - The five requests from 00:11:29.2 to 00:11:33.3 fitted the minute limit, margin included, with 2.6 s to spare. The last of the five got the 429.
  - The docstring says the cause is not confirmed.
- **Item 7: test gaps.** Each of the five mutations is now caught:
  - a Redo failure overwriting a done record (tested with 500 and timeout, and with 429 for the stop branch);
  - `max_wait` passed to the pacer after a back-off;
  - a back-off after the last 429;
  - a timeout letting the run go on;
  - a JSON answer that is not an object.
- **Docstrings.** These are now true as written:
  - the timeout (it covers the connection and each read, not the whole answer);
  - the reasons for `RateLimited`;
  - the `_get`, `run` and `search` docstrings;
  - the `SearchFailed` `stops_run` list;
  - the `COURTS` comment;
  - the `MARGIN` comment.

  `search()` says `next` must be "a link or empty", but the code checks only that it is a string. A string that is not a URL still fails at the next request, as "the answer was not the JSON expected", so the effect is as the docstring says.
- **The fixer's figures.** The 78 and 118 test counts match. In the live store, AR and CO are `done` with 0 sections, and PR has no scans row.

### Still wrong, or new

1. **Still open, needs `steps.py`: old `done` records for states with nothing searched.**
   - In the live store, AR and CO are still `done` with 0 sections. The live status, "8 of 52 states searched to the end", therefore counts two states that were never searched.
   - A Redo of such a state is skipped and keeps the `done` record. It logs "its earlier complete search stays on record", which is false for these records. Reproduced.
   - The fixer reported this and proposed fixes.
2. **Still open, needs `steps.py`: how a skip is worded.**
   - `run_cases` logs "search failed (skipped: ...); recorded as failed, so the next run searches it again".
   - The Setup status puts the state under "search failed, tried again on the next run".
   - In fact nothing was searched. The next run will not search it either, as long as it has no court ids or no sections.
   - The `run_cases` and `_cases_progress` docstrings do not mention skipped states.
3. **Not in the fixer's report: three more states have no sections.**
   - In the live store, GA, MS and TN have models but no section to search, and no scans row yet. Job 66 stopped at FL before it reached them.
   - The next run will record all three as skipped. With PR, four states then cannot be done, so the Cases step stays "partial" until they get sections (and PR gets court ids).
   - This follows from the fixer's judgement call, which stands as the conservative choice.
4. **Still open, needs `steps.py`: a cancelled or restarted run (Re-check 2, item 3).** Nothing has changed.
5. **New (minor): after earlier failures, a fault every state shares does not stop the run.**
   - The repeat-failure rule goes on whenever a state failed last time, whatever the reason.
   - The `run_cases` docstring gives the reason as "then the fault is its own", which is not always true.
   - Reproduced as follows:
     - three states had failed last time, each with its own HTTP 400;
     - every request then got a 401 (a bad token), in a Redo that also held one done state;
     - the run sent 4 requests, one per state, before it stopped.

     Each state was recorded again with the 401, which is true.
   - A state skipped last time also counts as failed last time.
   - The cost is one request for each such state, and only when no state that was never searched comes before them in the queue.
   - Conservative fix: make 401 and 403 always stop the run, or go on only when the new reason matches the last one.
6. **New test gap: waits across pages.**
   - The docstring says a search's waits add up to `max_wait` at most, over both of its pages.
   - The code does carry `waited` from one page to the next.
   - But a mutation that starts each page at 0 survived, because no test has a wait on the second page.
7. **New (minor): the fields of each result are not checked.**
   - When a result's `caseName` or `absolute_url` is not a string, `run()` raises a TypeError and the job crashes. Reproduced with `caseName: 5`.
     - Nothing is recorded as "no opinions".
     - But the module docstring says an answer that is not the JSON expected makes `run()` raise SearchFailed, which does not happen here.
   - When `citation` is a string rather than a list, it is stored one character per item ("1;  ; V; a; ..."). Reproduced.
   - Either a narrower docstring or a type check would settle this.
8. **Open (minor privacy weakness): the token follows `next`.**
   - `search()` sends the Authorization header to whatever URL `next` names. Reproduced with a `next` on another host.
   - The fixer left this alone because a fix might break paging.
   - Dropping the header when `next` is not on the API's host, while still sending the request, cannot break paging. It is a safe, conservative fix.
9. **Observation: without a token, the daily limit looks lower than 125.**
   - Job 66, which has no token, stopped at 01:14:40 UTC on a 429 whose back-off was 15 h 56 min. At that point the pace file held 96 requests from the past 24 hours, counting the request that got the 429.
   - The back-off ends at about 17:10 UTC on 11 October. That is 24 hours after the oldest request in the pace file (17:10:23 on 10 October).
   - So CourtListener seems to have counted the same requests as the pacer and refused the 96th. This was not confirmed.
   - `caselaw.py` handled it correctly: FL was recorded as `stopped:` with 11 sections. Its docstring says only that the limits without a token are not documented, and that is still true.
   - The cases cost text in `steps.py` says "a run stops when the day's 125 are used". That did not hold without a token.
   - A stopped state is searched again from its first section, so FL's 11 sections will be searched again. The log line says "it goes on from Florida, and sections already searched keep their results". That is true, but it may read as if the search resumes partway through the state.
10. **Still open, not the fixer's files: Re-check 2 items 5, 6, 8 and 9.**
    - Item 5: the CourtListener credit still says it "was not checked" whether CourtListener answers searches without an account. Job 66 got answers without a token.
    - Item 6: line 3 of the research note and its "Not verified here" list are unchanged. The list still says anonymous search was not tested.
    - Item 8 was not re-checked, because `dashboard/app.js` is being edited elsewhere.
    - Item 9: README line 349 (it was line 346) still says "150 so far, for CA, DC, MD and VA".

### Privacy

The changed files add no staff names, email addresses or contact details. The Skipped reasons are fixed text. With a token set, a test checks that the token never appears in a scans row or in the log. The one weakness is item 8: the Authorization header follows `next` to any host.
