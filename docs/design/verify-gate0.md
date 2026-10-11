# Check of the Gate 0 changes (rows 4, 5, 8, 9 and 12)

Checked on 11 October 2026 against [adoption-strategy.md](../strategy/adoption-strategy.md) §1.9 and the three critiques ([clerk](../strategy/critique-clerk.md), [legal aid](../strategy/critique-legalaid.md), [Wikimedian](../strategy/critique-wikimedian.md)).

Method:
- All 44 pages were rendered with `python -m lexflow wiki-pages --out /tmp/gate0check` in `lexflow-app-1` and scanned with the embedded BPMN XML removed.
- The BPMN XML was then checked on its own, and the dashboard's bpmn-js viewer showed what its labels render as.
- `python -m lexflow deadline-words` was run, and every curated deadline was dumped with the text its phrase was read from.
- The review gate was tried through the new API code with FastAPI's TestClient, against a throwaway copy of the database in `/tmp`, with the job runner off and no wiki or Turso credentials. The copy was deleted afterwards. The live database still has 2,921 asked answers, 0 ticked and 0 reviewed.
- Nothing was published or edited apart from this note. No jobs, benchmarks or Ollama were run.

## Confirmed

- **Tests.** The full suite (`python -m pytest -q`) gave 1,075 passed, 14 skipped and 0 failed in 7 min 26 s. `tests/test_gate0.py` has the 22 tests the summary lists.
- **No model name or score on reader pages.** Outside `lexflow:method`, none of the 43 pages says "quality", "Confidence", "checked by", "Claude" or any other model name. That includes the embedded XML: only `lexflow:method` contains "Claude".
- **Labels.** Every page opens with "Drafted with an AI system from … · Every quote matched to the official text on/between <date> · Not yet reviewed by a person".
  - The dates are 9 or 10 October 2026, taken from each model's drafting note, since no model has a `checked_on` yet.
  - A reviewer record shows as "Reviewed by Example Reviewer, attorney licensed in Virginia, on 11 October 2026" (tried on the temporary copy).
- **Method link.** All 44 pages end with the `lexflow:method` link.
- **Deadlines in the step lists.** I sampled 27 of the 53 across all 11 jurisdictions (VA, MD, DC, CA, IL, NY, NC, OH, TX, WA, FL), and `deadline-words --all` covers the rest.
  - Every phrase shown under "time limit:" appears word for word in the deadline's own quote (47 of 53) or in the step's quote (3: DC respond, DC mayor_review, IL respond_extended). None is read from an unrelated quote.
  - The two sums are marked: DC "lexflow's count: 15 + up to 10" and CA "10 + up to 14".
  - NY decide_later says "no number of days in the text".
  - The 11 rows the summary lists are the 11 the command lists.
- **`lexflow:start`.** It lists 11 jurisdictions, 2 questions and 3 places, and says "none has yet been reviewed by a person" and "Other states, places and questions are not covered here". The breadth claim is gone.
- **Review gate (temporary copy).**
  - Ticking without a reviewer returns 409.
  - When all 2,921 answers are ticked in the database with no reviewer, `all_pages` still gives the same 44 pages, with no answer page.
  - A ticked answer whose reviewer is the old Claude note string, `{"name": "Claude"}`, a future date or no role stays off the wiki.
  - Once a reviewer is recorded and the answer is ticked, it goes on with the reviewer line, and the page has no model name, no "Confidence" and a method link.
  - Deleting the review clears the tick. The API returns 400 for "Claude", "Claude (claude-opus-5-5)", "ChatGPT", "GPT-4o", "Example AI", a missing role, a future date, `licensed_in` with a non-attorney role and a one-letter name, and 404 for an answer that does not exist.
  - Re-asking sets `reviewed_by=None` in both `answer_state` and `answer_place`.
- **Live API.** It still runs the old code (`PUT …/review` returns FastAPI's generic 404). Publishing is still gated, because publish jobs run as a subprocess (`pipeline/jobs.py`, `Popen`) and load the new `all_pages`.
- **Builder notes.** No snake_case ids are left on reader pages. Decision tables show yes/no/any, never true/false. The Checks section and the hit-policy and DMN wording are gone, and the full notes are on `lexflow:method`.
- **Namespace rule.** All 44 page ids start with `lexflow:`, and `run_publish` refuses any other id. The edit summary is "lexflow: drafted with an AI system; quotes checked against the statute text".
- **No staff or researcher names.** A name-pattern scan of all 44 pages, plus reading every contact and caveat line on the 9 place pages, found office titles, shared inboxes and street addresses only. No researcher is named. No partner, advisor or endorsement wording appears, beyond the "not affiliated with, or endorsed by" line.
- **`lexflow:method` checked against [credits-research.md](credits-research.md) and the code:**
  - **Licences.** Open US Law is CC BY-NC 4.0 and the compilation is Vaquill AI's. LOCUS-v1 is CC BY-NC 4.0 from LocalLaws. Wikidata is CC0. CourtListener runs under Free Law Project's allowed-usage policy, with no data licence stated. The Census listing is a US government work.
  - **Quote check.** It is an exact substring match after collapsing whitespace and curly apostrophes (`validate.lex_checks`).
  - **Diagram and schema checks.** Five lexflow bpmnlint rules exist (`tools/bpmnlint-plugin-lexipedia`). The XSD and Petri-net soundness checks are part of `validated`.
  - **Model-by-model table.** It matches the database for all 22 models: every one is `reviewed` tier, with 0 quote misses, 0 XSD and 0 lint errors, 0 lint warnings and 1 of 1 sound nets.
  - **Other statements.** "Today 0 of the 22 state process maps name a reviewer" is true. The place files record "a second re-fetched every source and corrected or removed unsupported claims". The README records the review rounds for the 22 models.

## Wrong

1. **The process map still shows lexflow's units, and lexflow's sums unmarked (row 5).** The diagram is the first thing on every state page. Its timer labels come from the stored amount and unit, and bpmn-js draws them. The dashboard's bpmn-js viewer shows the same XML with these labels:
   - VA shows "5 business days" and "7 business days".
   - DC shows "15 business days", "25 business days" and "10 business days". "25 business days" is the sum the legal-aid critique (§2.2) singled out.
   - MD shows "10 business days" three times.
   - CA shows "24 days".
   - NY shows "0 days".
   - IL, NY, OH, TX, WA and NC show their figures as well.

   So the page header ("Time limits are in the law's own words") and the method page ("the page does not show that unit") are not true while the diagram is drawn. The fix is to name the timer events from `law/wording.describe` when the XML is built, or to rewrite the timer `name` attributes in `render_state_model`.
2. **The DC decision table and notes still say "working days".**
   - The table says "No extension: determine within 15 working days of receipt" and "at most 10 more working days".
   - The notes say "before the 15 working days end" and "Body-worn camera recordings … have 25 working days".
   - The statute says "15 days (except Saturdays, Sundays, and legal public holidays)" and "10 days (except …)". The legal-aid critique names the decision table itself.
   - The `deadline-words` audit checks step deadlines only, not decision-table outputs or notes. These strings are in `curated/dc/records.json`, which is not one of the off-limits place files.
3. **Place pages' own deadlines are neither quoted nor marked.** The summary says place pages get the same treatment. They do for the state-law steps, but not for the local layer, which sits under the same "law's own words" header.
   - The DC place page says "Agencies must answer within 15 business days and can add 10 more business days" and "Wait for the response (15 business days, with a possible 10-business-day extension)", and its caveats say "The 15-day clock is in business days".
   - Baltimore says "Within 10 days of receipt, DPW sends …" (the statute says 10 working days).
   - `render_place_process` prints `loc.steps` as free text, and nothing is marked "in lexflow's words".
4. **Method page: "The text is a snapshot as of the date on the page".** The text is the Open US Law v2026.09.1 snapshot (30 September 2026). The date on the page is when the quotes were matched.
5. **Label: "matched to the official text".** The match is against the Open US Law compilation. The method page itself lists "that the compilation matches the official code everywhere" among the things not proven. The label and the method page contradict each other. "matched to the statute text (Open US Law copy of the official code) on <date>" would be true.
6. **"An AI system is never named as a reviewer" is a blocklist, and it lets AI names through.** The API accepted, and the wiki would show, "Reviewed by Claude Code, reviewer", "Fable", "Grok" and "DeepSeek". "claude.ai" also passes, because `\bAI\b` only matches capitals.
7. **Reader notes still carry builder language (row 12).** `notes.BUILDER_TERMS` does not cover these:
   - fl.records: "folded into the custodian lane"
   - il.records: "not given a lane of its own" and "(consequence 'unstated')"
   - md.business: "The limited partnership rule fires before the LLC rule (the comparison table's fixed priority) … the output points …"
   - il.business: "the structure table keeps the seven-rule order … routed to the LLC rule"
   - ca.records: "appears in the decision's output text", "in the allowing rule's quote, not a separate input"
   - tx.records: "the rule falls through to production. On that row the table …"
   - wa.records: "the table's input is …"
   - ny.records: "The table gives no output where neither rule applies"
   - Some cut notes have also lost the gap they record. VA's "Subsection F's opening exception for scholastic records … qualifies the permission to make charges" now ends there, without the open question.
8. **The method page's "How it was drafted" column** repeats the old curated note 22 times: "Claude (claude-opus-5-5), 2026-10-10; every quote checked against open-us-law v2026.09.1". On the page outreach will link to, that reads as "checked by Claude" again. Something like "Drafted by an AI system (Claude) on <date>; quotes checked by lexflow's software" would say who did what.
9. **Smaller method-page claims.**
   - "Every section links to that official publisher": each page links only the governing section. For example, DC links § 2-532 but not § 2-534 or § 2-537.
   - "On local pages, the second AI pass compared each quote with the page it came from": the local layers carry no quotes from official pages, and the place files say only that the second pass re-fetched sources and removed unsupported claims.
   - "must pass" the bpmnlint rules: two of the five (`deadline-anchor`, `assumption-has-note`) are warnings and do not fail validation, and `all_pages` publishes any `reviewed` or `agreed` model whether or not `validated` is true. Both are true of today's 22 models.

## Missing

1. **A reviewer is not tied to the text they read when it arrives through sync.** I tried this on the temporary copy:
   - I recorded a reviewer, then upserted a newer answer the way `turso.pull` does from a shared copy without `reviewed_by`.
   - The new text kept "Reviewed by Example Reviewer" and went on the wiki.
   - The same happens when a machine on older code pushes a re-asked answer, because `ON CONFLICT … DO UPDATE` only sets the columns sent.
   - Curated models and place files have the same gap: there is no hash or date check between the sign-off and the file.
   - Separately, a review date earlier than the answer's `answered_at` is accepted.
2. **Row 9's second half.** The 26 "Unreviewed draft" Wikibase items are still not hidden or kept out of search. The summary lists them as out of scope, but they are half of row 9.
3. **"N of M quotes matched" only works on state model pages.** `render_place_process`, `render_place`, `render_state_index` and `render_index` do not pass `matched`, so those pages would still say "Every quote matched" after a failure. Every count is 0 today.
4. **"Corrections: <address to be set by the operator>"** is a placeholder. It has to be filled before any publish (row 14).
5. **The legacy writer is not covered by the namespace rule.** `scripts/build_all.py --publish` calls `publish/dokuwiki.publish()`, which writes `process:…` and `law:…` pages and media, plus a "Machine checks" JSON block. It is outside the guard in `run_publish`. This was already the case before Gate 0.
6. **Asked answer pages expand LOCUS as "Local Laws Observatory".** That is wrong: it is the Local Ordinance Corpus for the United States, by LocalLaws. It is not live, since no asked answer is published.
7. **`lexflow:start` still links "Lexipedia home"** (`[[start]]`), the page that row 2 says carries the crypto and charter-city content. Rows 1 and 2 cover this.

## Re-check 2 (11 October 2026)

This checks the second round of fixes against every item above.

Method:
- All 44 pages were rendered from the live database with `python -m lexflow wiki-pages --out /tmp/g0r2check` in `lexflow-app-1`. They are still there.
- A throwaway copy of the live database was made in `/tmp` (SQLite backup), and the edited DC and Baltimore place files were loaded into it. The pages were rendered again from the copy.
- Every review, sync, sign-off and publish trial below ran against that copy, with every credential blank and the job runner off. The copy was deleted afterwards.
- Every embedded BPMN block was parsed as XML. The stored XML of all 104 state models in the live database was read too.
- Sync was driven through `turso.pull` and `turso.push` themselves, against a stand-in libSQL server over a local SQLite file.
- Nothing was published, and nothing in the live database was written. No jobs, benchmarks or Ollama were run, and no container was restarted. Only this section was edited.

### Fixed

- **Wrong 1, timer labels: fixed.**
  - All 53 timers on the 22 state pages are named in one of three ways: the statute's phrase in quotes, "lexflow's count: …" (DC "15 + up to 10", CA "10 + up to 14"), or "No number of days in the text" (NY `decide_later`).
  - Each name equals `wording.timer_label` and the step list's "time limit:".
  - VA reads "“within five working days”" and "“an additional seven work days”". MD reads "“within 10 working days”" three times.
  - The stored XML that the dashboard draws has no stored-unit name for any of the 22 reviewed models. They were rebuilt today between 05:28 and 05:29 UTC, with 0 quote misses, 0 lint errors and warnings, and quality 0.987 to 1.0.
  - All 3,561 timers in the stored asked-answer maps are renamed to quoted words when a page is rendered.
- **All 53 deadline phrases: confirmed.**
  - Each phrase is word for word in its source: 47 in the deadline's own quote, and 3 in the step's quote (DC `respond`, DC `mayor_review`, IL `respond_extended`).
  - The other three are the two marked sums and NY's "no number".
  - Every phrase was read in context. Each one is the period of its own step.
- **Wrong 2, DC table and notes: fixed.**
  - The table and notes now say "15 days (except Saturdays, Sundays, and legal public holidays)", "shall not exceed 10 days (except …)" and "lexflow's count of 15 + up to 10 days".
  - The body-worn camera note ("25 days", "up to 15 days", both with the same exception) matches § 2-532(c)(2) and (d)(1).
  - The 22 state pages have 141 time-limit phrases in their tables and notes, and none relabels a unit. The 14 that are not word for word are paraphrases ("five work days" for "the five-work-day period"), sections the page says are not printed, or the shorthand noted under New.
- **Wrong 3, place pages: fixed in the files and the code, but not in the live database.** See Not fixed.
  - From the copy with the two files loaded, the DC summary, the waiting step and the caveat use the law's units. They attribute "business days" to dc.gov/foia.
  - Baltimore's step cites § 4-203 and attributes the 10 days to DPW's page.
  - Both process pages carry the "in lexflow's words" line, and their "What … adds" sections are marked too.
- **Wrong 4 and 5: fixed.**
  - The method page names Open US Law's release v2026.09.1 of 30 September 2026. That matches the release record, and `statute_files` has v2026.09.1 for all 52 states.
  - Every label now says "Open US Law's copy of the official text".
- **Wrong 8: fixed.** The drafting system is named above the table and in "How a page is drafted". The table's columns are "Drafted" and "Quotes matched".
- **Wrong 9: fixed.**
  - Each of the 22 state pages links exactly one statute URL, its governing section, on the state's own site.
  - The lint levels on the method page match `tools/bpmnlint-plugin-lexipedia`: three rules are errors and two are warnings.
  - "Published even if a check fails" and "today every model passes all of them" are both true today.
- **Wrong 7, builder words: mostly fixed.**
  - None of the phrases listed above remains, and the VA scholastic-records note keeps its open question.
  - No snake_case ids or true/false values are left outside the XML.
  - Left over: "scored separately" (fl.business, il.business), "outside the sections used" (tx.records, twice) and "not cited in sections" (il.business).
- **Missing 1, a review applies only to the text it reviewed: fixed for what a page shows.**
  - **Through the API:**
    - A stale `text_hash` returns 409. A date before the answer returns 400, and so does a future date. Ticking without a reviewer returns 409.
    - A valid review shows as "Reviewed by Example Reviewer, attorney licensed in Virginia, on 11 October 2026".
    - Then the text was changed under the review, the way older code re-asks (`reviewed_by` kept). The page dropped out of the pages to publish, and the API reported `review_stale`.
  - **Pull from a read-only shared copy without the column:** the review was cleared and the page dropped out of the pages to publish.
  - **A writable shared copy, where a machine on older code overwrote the text but kept the reviewer:**
    - The pull cleared the review locally.
    - The next incremental push cleared it on the shared copy.
    - A third machine pulled no reviewer.
  - **A review that fits its text** survived push and pull to a fresh database, with the same hash.
  - **A DC local answer and the VA state model, each signed, then replaced by a newer pulled copy:** both pages say "Not yet reviewed by a person". For state models the stale reviewer stays in `metrics`, and only the render-time check hides it, because `process_models` is not in `turso.REVIEWED`.
  - **A curated file through the build, and a place file through `load_local`:** a signed file is named on the page. An edited gap, reader note or caveat with the old hash is not named, and the log says why. A place sign-off dated before `researched` is refused.
- **Missing 3: fixed wherever a count exists.**
  - The test put 2 misses on va.records and dc.records, and 1 of 10 on an asked answer.
  - The pages then read "21 of 23", "36 of 38", "44 of 46 quotes from the statute" (VA index), "753 of 757" (start page, label and body) and "9 of 10" (asked page). The place main and process pages showed their counts too.
  - The 2,921 stored asked answers have no `quotes_checked`, so a reviewed and ticked one says "Every quote matched" with no count behind it. The VA state answer did this on the copy.
- **Missing 4: as the fixer says.** The dry run logs "would not write lexflow:method", and with `LEXFLOW_CORRECTIONS` set it writes the page.
- **Missing 5: fixed.**
  - `scripts/build_all.py --publish` exits with code 2 before building anything, and `out/` is untouched.
  - `save_page` and `save_media` refuse `process:…`, `law:…`, `start`, `:lexflow:x` and `lexflowx:start` with no call made, and the legacy `publish()` makes no call either.
  - `run_publish` checks every id before the first write. These are the only code paths that write to the wiki.
- **Missing 6 and 7: fixed.**
  - LOCUS is expanded correctly on asked pages, in the dashboard and in `ask/local.py`.
  - The start page no longer links the wiki's own start page; its footer is only the method link.
- **Still true from the first check:**
  - No model name, "quality", "Confidence" or "checked by" appears on the 43 reader pages outside the embedded XML. "Claude" is only on `lexflow:method`.
  - No staff or researcher is named, and nothing claims a partner or endorser.
- **Tests:** 1,242 passed, 14 skipped and 1 failed in 3 min 2 s. The failure is `tests/test_design_privacy.py` on `verify-lab.md`, another agent's note. `tests/test_gate0.py` has 34 tests.

### Not fixed

- **Wrong 6, the blocklist: partly fixed.**
  - The names the summary lists are refused: all 20 tried through the API returned 400 (Claude, Claude Code, claude.ai, Anthropic, ChatGPT, GPT-4o, OpenAI, Gemini, Bard, Gemma, Llama 3, Qwen, Mistral, Grok, DeepSeek, Copilot, Fable, Perplexity, xAI, Example AI).
  - It is still a list. Of 73 AI system or product names tried, 29 are accepted. A few of them are also ordinary names (Kimi, Devin, Pi).
  - The accepted ones include Ollama, the runtime lexflow itself uses, and AutoGPT, ChatGLM, Codex, Bing Chat, PaLM 2, LaMDA, Le Chat, Codestral, HuggingChat, Command R, Amazon Q, Watsonx, "Assistant" and "a bot". Look-alike spellings also pass: "C1aude", "Cl aude", and Claude in full-width or Cyrillic letters.
  - Through the API, Ollama, AutoGPT and ChatGLM returned 200.
  - The role is not checked at all when it contains "attorney", "lawyer" or "counsel". "AI attorney" and "attorney (drafted by Claude)" are accepted, and the page would then read "Reviewed by …, attorney (drafted by Claude) licensed in Virginia, on …".
- **Wrong 3, in the live database.** Rendered from the live database, DC still says the following, and only these 3 of the 44 pages differ from the copy:
  - "Agencies must answer within 15 business days and can add 10 more business days".
  - "Wait for the response (15 business days, with a possible 10-business-day extension)".
  - "The 15-day clock is in business days".
  - Baltimore still gives the 10 days as its own statement.

  `python -m lexflow run local --places dc,md:baltimore` loads the new wording, and it needs to run before any publish.
- **As asked, these were left:** Missing 2 (the Wikibase draft items) and the corrections address.
- **As the fixer said:**
  - The dashboard's question list still counts a stale review as "reviewed" and "published". The trial gave 2 and 2 after one review went stale.
  - The live API still runs the old code until a restart.

### New

- **Publishing now would leave the method link dead on every page, and the statute text without a licence notice.**
  - While the placeholder stands, the publish step writes the other pages and skips `lexflow:method`.
  - `docs/wiki`, which the README calls the copies of the published pages, has the 43 pages from before Gate 0 and no method page. So the wiki very likely has never had one. I did not read the live wiki.
  - The CC BY-NC 4.0 notices for Open US Law and LOCUS-v1 are only on `lexflow:method`.
  - Either refuse the whole publish until `LEXFLOW_CORRECTIONS` is set, or publish the method page without its corrections line.
- **The method page claims more than the quote check does.** It says the software "found every quoted phrase on the page, word for word".
  - The check covers the model's quotes (steps, decisions and rules), not quoted words inside the notes.
  - Of the 77 quoted fragments in the reader notes, 9 are not in the cited sections. Most are lexflow's own words in quote marks ('no formation filing', 'See § 29-102.12', 'certificate of organization').
  - Two read as the statute's words but are not. oh.records quotes 'otherwise addresses', where the statute says "otherwise address". wa.business quotes 'uses a trade name', which is nowhere in the Washington code.
  - The note text was there before this round; the claim is new.
- **The API accepts a review with no `text_hash`.** It returns 200 and binds the review to whatever text is stored at that moment. The dashboard sends the hash; other clients need not.
- **Place caveats speak in the first person.** They say "I did not verify those", "I checked" and "I confirmed …" on the DC records and business pages and in Charlottesville. Next to "an AI system summarised the place's official pages", an unnamed "I" reads like a person who checked. The Charlottesville file is in `curated/places/va`, which was off-limits this round.
- **"Today every model passes all of them" ignores warnings.** `_passes` counts lint errors but not lint warnings, though the sentence covers both warning rules. It is true today (0 warnings), but it would stay on the page if a warning appeared.
- **The shorthand "five-day" drops the law's unit word.** It appears in notes on ny, oh, va and wa records, where the law says "five working days" or "five business days".
- **Unpublished drafts on the dashboard.** 140 timers in the single-extraction draft models still read "10 business days" and the like in the stored XML the dashboard draws. They are not on the wiki.
- **The page source still carries builder material.** The embedded XML keeps the full builder notes as `lex:gap` (for example "checked by the fees_paid input of articles_comply"). It also gives business-day limits as calendar durations (`P15D`). bpmn-js draws neither, but both are in the page source that DokuWiki indexes for search.

## Re-check 3 (11 October 2026)

This checks the third round of fixes against Re-check 2.

Method:
- All 44 pages were rendered from the live database with `python -m lexflow wiki-pages --out /tmp/g0r3check` in `lexflow-app-1`. Every file is the same as in the fixer's `/tmp/g0r3after`.
- A throwaway copy of the live database was made in `/tmp/g0r3v` (SQLite backup).
  - On the copy, all 22 state models were rebuilt with `run build --force --no-llm` and Ollama unreachable. Quality was 0.99 to 1.00, and all 22 validated.
  - Only `curated/places/va/charlottesville.json` was loaded, with the process-file loader switched off.
  - The 44 pages rendered from the copy match the fixer's `/tmp/g0r3copy`, apart from one method-page sentence the fixer edited after that render.
- Every review and publish trial ran against the copy. They went through FastAPI's TestClient and `run_publish` itself, with every credential blank, the job runner off and the trial's network calls blocked. The live database and the live API were only read.
- Nothing was published. No benchmarks or Ollama were run, and no container was restarted. Only this section was edited. The copy was deleted afterwards; its pages are in `/tmp/g0r3v/pages`.

### Fixed

- **Roles and attestation: fixed.**
  - Through the API, 18 roles that are not on the list returned 400. They included "AI attorney", "attorney (drafted by Claude)", "staff attorney", "senior attorney", "lawyer", "counsel", "reviewer", "paralegal; AI-assisted", and "attorney" with a zero-width space or in full-width letters.
  - "Records Officer", " Attorney " and "law  student" were stored in the list's own spelling.
  - `attested` missing, false, "false" or 0 returned 400.
  - `licensed_in` with a paralegal, or with "Narnia", returned 400.
- **The names Re-check 2 found: all refused.** All 28 names tried again are refused, including Ollama, AutoGPT, ChatGLM, Codex, Bing Chat, PaLM 2, LaMDA, Le Chat, HuggingChat, Amazon Q, "Assistant", "a bot", "C1aude", "Cl aude", Kimi, Devin and Pi, and Claude in full-width or Cyrillic letters. So were 12 controls, among them "C l a u d e", Claude with a zero-width space, Gemini with a Cyrillic е, ClaudeBot, ReviewBot, LawGPT and "A.I. Reviewer".
- **The review hash: fixed.**
  - Without `text_hash`, or with an empty one, the API returns 400. A wrong hash returns 409, including the right hash in capitals or with a leading space.
  - After a valid review and a tick, the question list showed reviewed 1, published 1 and stale 0. Once the stored answer changed, it showed 0, 0 and 1.
  - The changed answer reported no reviewer and `review_stale`. A new tick and a review with the old hash both returned 409, and `wiki_ready` was false.
- **Publishing without a corrections address: fixed.**
  - These values were tried: `LEXFLOW_CORRECTIONS` unset, blank, the placeholder, "TODO", "corrections", a `mailto:` value, `http://localhost:8080/report` and `javascript:alert(1)`.
  - With each, `run_publish` refused all 44 pages, in a dry run and in a real one. It logged one line starting "publish refused", made no DokuWiki call and no network call, and left `process_models.stages` unchanged.
  - The values it accepts are under New.
- **The method page's quote claim: fixed.**
  - `validate.lex_checks` checks the sources of every node, the timers' deadline quotes among them, and of each decision and each rule. That is what the page now names.
  - On the rebuilt copy, all 91 quoted fragments outside the step lists (in the notes and the tables) are in the Open US Law statute text. One matches only when case is ignored: ny.records "upon payment of, or offer to pay, the fee prescribed therefor".
  - `_passes` counts lint warnings, and all 22 models have every key it reads.
- **Builder phrases, "five-day" and first person on the state pages: fixed in the files.** On the rebuilt copy:
  - None of "scored separately", "outside the sections used", "not cited in sections" or the round-1 phrases is left.
  - No snake_case id or true/false appears outside the XML and `lexflow:method`.
  - "five-day" is gone from the four records pages.
  - No model name or score appears outside `lexflow:method`.
  - The 22 state pages print 120 day counts outside quotation marks, and each uses the unit word the law uses with that number. The two that are not word for word are paraphrases: fl.business's § 605.0207 ("not printed"), and tx.records's "15 business days" for "the 15th business day".
- **Place caveats in the third person: fixed in the files.**
  - No first-person word is left in any field of the DC, Baltimore or Charlottesville files, web addresses aside. Baltimore's one "we" is inside a quote of the city's own page.
  - The 13 quote fields in the Charlottesville file are the same as in the copy the live database loaded before the edit, so its quotes are unchanged.
- **Embedded maps: fixed for what Re-check 2 named.**
  - None of the 22 maps, live or on the copy, has `lex:`, `extensionElements`, `camunda`, `spiffworkflow`, `timeDuration` or an ISO duration.
  - All 53 timers keep their definitions, and every map passes the BPMN 2.0 schema check.
- **Live DC and Baltimore: fixed.**
  - DC's summary, waiting step and caveat use the law's units, and attribute "business days" to dc.gov/foia.
  - Baltimore's time limits read "within 10 working days", quoted from § 4-202 and § 4-203.
- **Design notes: confirmed.**
  - The e-mail addresses in `docs/design` are the four made-up ones in verify-lab.md (now on example.org), two office mailboxes cited as sources and two file names.
  - No phone number, in any format (dotted, bracketed, with +1, or ten digits run together), falls outside 555-0100 to 555-0199. The other hits were section numbers, line references and a timestamp.
  - The one street address is a state revenue office's. The only personal names are the senators who sponsor a bill.
- **No staff or researcher named.** On the 44 pages, live and on the copy, the only personal names are parties in the CourtListener case titles. No partner, adviser or endorsement wording appears.
- **Tests:** 1,221 passed, 44 skipped and 0 failed in 6 min 2 s. `LEXFLOW_DATA` pointed at an empty temporary directory and every credential was blank, so no test could touch `/data`. The 30 skips beyond the fixer's 14 are `tests/test_forms.py` cases that need California's statute text from the downloaded Open US Law store (`pytest -rs`). `tests/test_gate0.py` and `tests/test_design_privacy.py` pass, and `tests/test_gate0.py` has 41 tests.

### Not fixed

- **The AI-name check is still a list.**
  - Of 80 further names chosen from outside it, 77 returned 200 through the API. 25 of them are also ordinary names or words (Harvey, Jules, Watson, Sora, Goose, Transformer and others). These 52 are not:
    - look-alike letters the table does not cover: "Cʟaude" (small capital L), "ᴄlaude" (small capital C), "Ϲlaude" (Greek capital lunate sigma) and "Ꮯlaude" (Cherokee);
    - names run together in lower case: "Reviewbot", "Lawgpt", "legalgpt" and "myclaude", although "ReviewBot" and "LawGPT" are refused;
    - other scripts: "クロード", "Клод", "通义千问" and "文心一言";
    - legal AI products: DoNotPay, Clearbrief, Hebbia, Lexis Protege and ROSS Intelligence;
    - other products: GigaChat, SenseChat, SparkDesk, Yuanbao, DBRX, Galactica, AlphaCode, DALLE, Writesonic, Rytr, GrammarlyGO, Woebot, Wysa, Open Interpreter, Smol Developer, bolt.new, v0 and others;
    - descriptions: "Automated reviewer", "The software", "Foundation model", "Machine learning model" and "AGI".
  - Bidirectional controls stay in the stored name, so a reversed name displays as an AI name.
    - `"Jane Doe \u202eedualC\u202c"` (a right-to-left override, U+202E, and its end, U+202C) returned 200, and the page would show "Jane Doe Claude". `"\u202eTPGtahC\u202c"` would show as "ChatGPT", and `"(\u202eIA\u202c)"` as "(AI)".
    - `is_ai_name` drops these characters before it matches, and the reversed letters match no name.
  - So `lexflow:method` ("lexflow refuses a reviewer whose name contains that of an AI system, model family, assistant or agent product") and README ("A name containing the name of an AI system … is refused") claim more than the code does.
- **The name field can carry what the role list keeps out.**
  - The role "other person" prints no role. With it, "Jane Doe, attorney licensed in Virginia" returned 200, and the line reads "Reviewed by Jane Doe, attorney licensed in Virginia on 11 October 2026". That gets around the `licensed_in` checks.
  - "Jane Doe, attorney licensed in all 50 states" and a 3,000-character name were accepted too.
  - So were names with no letters or no person: "..", "12", "N/A", "Anonymous", "Reviewer", "Admin", "test", "Staff" and "Legal team".
- **Some ordinary names are refused, beyond those the docstring lists.**
  - Chinese given names that are also product names: Wenxin Li, Qianwen Zhang, Yiyan Chen, Baichuan Liu, Hunyuan Ma and Tongyi Xu.
  - Surnames that join into a product name: Marie Lechat and Anna de Vin. Ben Bot is refused too.
  - The initials "P. I." and "A. I." (P. I. Moreno, A. I. Okafor). The docstring tells a reviewer whose name is refused to sign with surname and initials.
- **The live database, as the fixer said.** The 13 state models are not rebuilt, so the live pages still show:
  - the 9 quoted fragments that are not in the statute ('no formation filing' … 'uses a trade name');
  - "five-day" on the ny, oh, va and wa records pages, and the old phrases;
  - "I could not load the Development Code PDF" on Charlottesville's business page.
- **The live API, as the fixer said.** It still runs older code: `GET /api/ask/{qid}/{target}` returns no `text_hash` or `review_roles`. The live database has 0 reviewed and 0 published of its 2,921 answers.
- **As before:** Missing 2, the Wikibase draft items.

### New

- **The corrections check accepts placeholder addresses.**
  - It accepted `corrections@example.org`, which is the value `.env.example` shows (commented out). It also accepted `you@example.com` and `https://example.com/corrections`, an address on the reserved `.invalid` domain, and addresses on the made-up domains `y.zz` and `b.co`.
  - With any of these, a dry run would write all 44 pages, and a real run went on to sign in to the wiki before the trial stopped it.
  - Uncommenting the example line is enough to publish a corrections line that reaches no one. Refusing the reserved names (example.*, .invalid, .test, .localhost) would close this.
- **A researched local process says "Every quote matched" on the strength of an AI's own count.**
  - `local_check` prints "Every quote matched to the page it quotes on <date>" whenever a process file records `checks.quotes_checked`.
  - Six Charlottesville process files carry such a count, all marked `verified: true` and written by `"verified_by": "Claude (lexflow verifier)"`.
  - The function reads `quote_misses`, but these files record `quotes_confirmed`. With 11 fewer quotes confirmed, it still says "Every quote".
  - This contradicts `lexflow:method`, which says "a researched local process says that its quotes are not matched by lexflow's software" and "lexflow's software does not match the words of local pages".
  - None of these pages is among the 44 today: the live `place_processes` has 5 rows, none verified. But `run local --places va:charlottesville`, which the Charlottesville caveat fix needs, loads every process file for that place.
- **"five-day" is left on a place page.** `lexflow:va:charlottesville:records` says "The five-day clock does not run while the deposit request is pending", live and on the copy. The words are a step's `how` in `curated/places/va/charlottesville.json`, and § 2.2-3704 says five working days.
- **The embedded map still carries internal names, and draws some of them.**
  - 108 distinct condition ids stay in `conditionExpression` (articles_ok, denied_in_whole_or_part, extraordinary_burden_and_intends_petition and others), and 17 `[implied]` grounding tags stay in `documentation`. bpmn-js does not draw these, but DokuWiki indexes them.
  - bpmn-js does draw the gateway and end-event names that the compiler makes from those ids: "doing business not exempt?", with its end "Not doing business not exempt", and also "Not articles ok" and "Not applicant complies".
  - It also draws names cut off at 60 characters, mid-word. 23 end events are cut, for example "Record not produced within 30 days: denial under § 4-203(b)(". So are the start events of 19 of the 22 maps ("Someone wants to start a business, here as a limited liabili") and 4 other elements.
  - So "The map on a page is the diagram only … lexflow's notes for builders … are left out of it" is true of the notes, but not of the internal names.
- **Small.**
  - A Baltimore business caveat describes the drafting, not the place: "The original business research arrived cut off after the trader's license fee step. The later steps … were rebuilt and checked against official pages."
  - A malformed `text_hash` ("abc") gets 409, "the answer has changed", rather than 400.
  - `lexflow:method` says "Every lexflow page opens with three facts", but it has no such label itself. Its opening paragraph says only that it was written with an AI system and not yet reviewed.

## Re-check 4 (11 October 2026)

This checks the fourth round of fixes against Re-check 3.

Method:
- A throwaway copy of the live database was made in `/tmp/g0r4v` (SQLite backup), next to a copy of the code with its own `curated/` folder.
  - Every trial ran there, with every credential blank, the job runner off and Python's network calls blocked. None was attempted.
  - The checkout's files, the live database and the live API were only read.
- Reviews were tried through FastAPI's TestClient and the `lexflow reviewer` CLI. They were also tried through `build` with a signed curated file and `load_local` for DC with a signed place file, both on the code copy. Sync went through `turso.pull` and `turso.push` against a stand-in libSQL over a local SQLite file.
- The reviewers in the trials are made-up names (Ana Villamar, Ben Okoro, Dana Whitfield, Eli Marsh, Pat Roe).
- Corrections values went through `run_publish` in a dry run.
- All 44 pages were rendered from a second, fresh backup of the live database with `python -m lexflow wiki-pages`. They are the same files as the fixer's `/tmp/g0r4/live-pages`.
  - Every embedded map was parsed and checked against the BPMN 2.0 schema.
  - The 2,918 stored asked-answer maps and the 87 stored state-model maps were also put through `reader_bpmn`.
- The 60 researched process files in `curated/places/va/*/` were read as they stood and rendered with `render_local_process`, without loading them. The other workflow is still writing them.
- Nothing was published. No benchmarks or Ollama were run, and no container was restarted. Only this section was edited.
- The copies were deleted afterwards. The pages, the trial scripts and their output are in `/tmp/g0r4v`.

### Fixed

- **1. A page names a reviewer only from the list: fixed on every path tried.**
  - **API refusals.** Each of these returned 400 and stored nothing:
    - no reviewer, or a null one;
    - a well-formed id that is not on the list, or a removed reviewer's id;
    - the name in place of the id, the id in capitals, with a leading space or a newline, or inside an object or a list;
    - a typed `name`, `role`, `licensed_in`, `date`, `Name` or `reviewed_by`;
    - `attested` missing, false, "true" or 1.
  - **Other API checks.** A body that is a list, a string, null or not JSON returned 422, and an answer that does not exist returned 404. `GET /api/reviewers` leaves out the removed reviewer, and POST and PUT on it return 405.
  - **A valid review.** It showed "Reviewed by Ana Villamar, attorney licensed in Virginia, on 11 October 2026" and stored only `{reviewer, date, attested, text_hash}`.
  - **After `lexflow reviewer remove`:**
    - The API reported no reviewer and `review_stale`.
    - The question list went from reviewed 1 and published 1 to stale 1.
    - The page left `all_pages`. A new tick returned 409 and a new review 400.
    - Adding the same person again gives a new id, and the old review stays unnamed.
  - **Dates and ticks.** A review dated before the answer's `answered_at` returned 400. Ticking an answer that has no review returned 409.
  - **CLI.** `reviewer add` without `--added-by` exits 2. A licence with a non-attorney role, a second removal and an unknown id are each refused with the reason.
  - **A curated model file** (va.records, on the code copy):
    - With a typed name, an id not on the list, no attestation or a wrong hash, it builds with "Not yet reviewed by a person" and logs why.
    - A valid sign-off shows "Reviewed by Dana Whitfield, attorney licensed in Virginia, on 11 October 2026". After the reviewer is removed, the page says "Not yet reviewed by a person".
  - **A DC place file through `load_local`.** The same held for one of its answers, and a sign-off dated before `researched` was refused.
  - **Sync.**
    - A pulled row with a role in the name ("Jane Roe, attorney licensed in all 50 states") stays off the roster and off every page.
    - A removal pushed from the copy reached a third, empty database. That database has the row with `removed_at`, and the reviewer is not on its roster.
  - **The AI-name warning.**
    - "Claude" is refused without `--confirm-person` and added with it. Wenxin Li, Marie Lechat, "A. I. Okafor", Pi Patel and Devin Smith are added with it.
    - Cʟaude, ᴄlaude and Ꮯlaude now bring the warning. Ϲlaude (lunate sigma) does not, but `clean_name` stores it as "Σlaude", so no page shows the look-alike.
  - **Controls.**
    - "Jane Doe ‮edualC‬" is stored as "Jane Doe edualC", and "‮TPGtahC‬" as "TPGtahC", so neither displays as an AI name.
    - Claude with a zero-width space, a word joiner or a soft hyphen becomes "Claude" and brings the warning.
  - **Names refused.**
    - Every placeholder Re-check 3 named: "..", "12", "N/A", "Anonymous", "Reviewer", "Admin", "test", "Staff" and "Legal team".
    - "Jane Doe, attorney licensed in Virginia", "Jane Doe Attorney Licensed In Virginia", "J.D.", "Esq." and "LL.M." after a name.
    - An 81-character name.
- **2. Corrections address: fixed for the names it lists.**
  - **Refused in a dry run**, each with its reason in one log line and no page written:
    - the `.env.example` value, also in capitals;
    - `you@example.com`, `https://example.com/corrections` and `https://www.example.net/report`;
    - addresses on `.invalid`, `.test`, `.localhost`, `.local` and `.example` names;
    - `http://localhost:8080/report`, `http://127.0.0.1/` and `http://10.0.0.1/report`;
    - a `mailto:` value, a display-name form, `http://[::1]/`, `http://0x7f000001/` and `javascript:alert(1)`.
  - **With an accepted value**, the dry run's first log line is "lexflow:method would print 'Corrections: corrections@lexipedia.xyz': readers will write to corrections@lexipedia.xyz". All 44 pages would be written, no network call was attempted, and `process_models.stages` did not change.
  - The values it still accepts are under Not fixed.
- **3. Local process pages: fixed.**
  - Rendered from the 60 files as they stand, no page says "Every quote matched", and each says "Not yet reviewed by a person".
  - A verified page reads like this one (charlottesville/parking_ticket): "27 of 27 quotes from the Code of Virginia matched by lexflow's software to Open US Law's copy of the official text on 11 October 2026; the other 44 quotes were checked by an AI verifier against the cited page on 10 October 2026; not matched by lexflow's software; the verifier confirmed 71 of the 71 quotes it checked, 0 not confirmed".
  - **Other counts.**
    - With the verifier's count set to 9 of 20, the page says "the verifier confirmed 9 of the 20 quotes it checked, 11 not confirmed". With only `quote_misses` 3, it says 17 of the 20 and 3 not confirmed.
    - Without `verified_by`, the other quotes are "not matched by lexflow's software; sources retrieved on 10 October 2026".
    - A stored `quote_check` made for another version of the file is made again.
  - **Totals today.**
    - Charlottesville: 1,064 of 1,064 Code quotes match, and 502 quotes are AI-checked only. The fixer's 1,057 came before the other workflow's later edits.
    - Albemarle: 1,222 of 1,222, and 734.
    - Staunton: 1,249 of 1,249, and 470.
    - Only one matched quote is three words or fewer ("1. Indictable offenses;").
  - The method page's two passages on researched local processes say what `local_check` prints.
- **4. Charlottesville: fixed in the file.**
  - The deposit step says "The five working days the city has to respond do not run while the deposit request is pending."
  - Its 13 quote fields are the same as in the copy the live database holds.
  - No first-person caveat is left.
- **5. Process maps: fixed on the 22 state pages.**
  - None of the 22 embedded maps has a name with an underscore, a "Not …" end made from a condition id, a condition expression, `extensionElements` or "[implied]". Every one passes the BPMN 2.0 schema check.
  - Seven names are cut, all at a word boundary with "…": the fl.records and va.records start events, an md.business end, two md.records flows, and one flow each on tx.records and wa.records. The other long names are whole titles, steps, outcomes or quoted time limits.
  - Gateways read like "Admit at least one member?", "Issue license to complying applicant?" or "Which path?". Flows are named after the step they lead to, and the ends read "Otherwise this map ends here".
  - No `documentation` or annotation text has a snake_case id. Ids, `flowNodeRef`, `sourceRef`, `targetRef` and `bpmnElement` still do (Not fixed, as the fixer says).
- **6. Small items: fixed.**
  - Baltimore's caveats describe the place, and the "arrived cut off" caveat is gone.
  - Each of these `text_hash` values returned 400: "abc", the right hash in capitals, with a leading space or a newline, 63 or 65 characters, 64 "g"s, a number and a list. A well-formed wrong hash returned 409.
  - `lexflow:method` opens with "Drafted with an AI system from lexflow's code and records · Quotes on this page are not matched by lexflow's software · Not yet reviewed by a person".
- **Live pages: as the fixer says.**
  - **Builder phrases and quotes.** None of Re-check 3's builder phrases is left on the 22 state pages. All 91 quoted fragments in their notes and tables are in the cited sections' text; one matches only when case is ignored, as before.
  - **"five-day".** It is left only on nc.business and in its builder note on `lexflow:method`, and § 55D-15(c) says "within five days".
  - **Model names and scores.** Outside `lexflow:method`, no page has a model name, "quality", "Confidence" or "checked by", in the text or in the embedded XML.
  - **First person.** No page speaks in the first person outside quotes. The only hits are the questions ("How do I …?") and the `myfoiadc` address.
  - **Names.** No staff member or researcher is named. The place pages' contacts are office titles, shared mailboxes, office lines and street addresses. "endorse" appears only in the law's sense and in the two "not … endorsed" lines.
  - **Method page.** Its model table matches the database for all 22 models. "Today every model passes all of them" and "Today 0 of the 22 state process maps name a reviewer" are true.
  - **Live API.** It still runs older code: `GET /api/reviewers` returns 404.
- **Tests.** `LEXFLOW_DATA` pointed at an empty temporary directory and every credential was blank.
  - The suite gave 1,271 passed and 5 skipped in 3 min 40 s, the fixer's count. The skips are four California-store cases in `tests/test_forms.py` and the live-wiki case.
  - A first run on a copy that carried the image's own `out/` gave 1,232 passed, 43 skipped and 1 failed (`test_the_built_viewer_has_the_same_fix`, which reads `out/viewer`). With the checkout's `out/` copied in, those tests pass.
  - `tests/test_gate0.py` has 52 tests.

### Not fixed

- **The live database, as the fixer says.**
  - `lexflow:va:charlottesville:records` still says "The five-day clock does not run while the deposit request is pending", and the business page carries the older caveat.
  - `run local` for va has to run before any publish, once the other workflow is done.
- **Snake_case element ids in the map source, as the fixer says.**
- **`clean_name` is still a set of lists, and four kinds of name get through.**
  - **Look-alike letters in role words.**
    - "Pat Roe Аttorney Lіcensed In Virginia" (Cyrillic А and і) was added with the role "other person". An answer it signed reads "Reviewed by Pat Roe Аttorney Lіcensed In Virginia on 11 October 2026".
    - "Jane Doe Lawyеr" and "Jane Doe Еsq" (Cyrillic е and Е) were added too.
    - Look-alikes are read in `is_ai_name`, but not before the role-word check.
  - **Abbreviations and other languages.** These were added after a name: "Atty", "Juris Doctor", "Virginia Bar", "Member Virginia Bar", "Advocate", "Abogada", "Avocat" and "Rechtsanwältin". So were the names "Fact Checker", "Wiki Editor" and "Moderator".
  - **Invisible letters.**
    - The Hangul filler U+3164 is a letter to `clean_name`, and is stored as U+1160. Two of them were added as an attorney licensed in Virginia.
    - The page then reads `Reviewed by <U+1160><U+1160>, attorney licensed in Virginia, on 11 October 2026`, which shows as a blank name.
    - U+115F and U+FFA0 do the same, and the Khmer inherent vowel U+17B4 can hide inside a name.
  - **Placeholders not on the list.** These were added: "No Name", "Name Withheld", "Not Applicable", "Lorem Ipsum", "Foo Bar", "Xx Xx", "Aa", "Person", "A Person", "Human", "Real Person", "Verified Human", "Jane Q. Public", "Mickey Mouse", "Confidential", "Private", "Withheld", "Me" and "The Operator".
  - **Look-alikes the table does not cover** bring no warning: "Clɑude" (Latin alpha), "ɡemini" (script g), "Cօpilot" (Armenian o) and "Llɑma". This is only a warning now, so it matters less.
  - So README and docs/core.md ("with no role or credential words and no placeholders") and `lexflow:method` ("with no role or credential words and no placeholders such as "Anonymous"") claim more than `clean_name` does.
- **The corrections check accepts 25 placeholder or unreachable values.** With each of these, a dry run would write all 44 pages:
  - **Placeholders on real or made-up domains:** user@domain.com, name@email.com, your.name@yourdomain.com, corrections@your-domain.org, foo@bar.com, test@test.com, changeme@lexflow.org, todo@todo.com, noreply@lexipedia.xyz, x@y.zz, a@b.co, `https://example.co.uk/report` and user@example.edu, as well as a form link with "XXXXXXXX" and an issues link with "OWNER/REPO" in it.
  - **Names that stay on the machine or the local network:** corrections@localhost.localdomain, `http://lvh.me/report`, `http://127.0.0.1.nip.io/report`, `http://192.168.1.10.sslip.io/report`, and names under .home.arpa, .internal, .lan and .corp.
  - **Special-use names:** .onion and .alt.
  - **A wrong reason.** `http://localhost:8080/report` is refused, but the log says it is "not an e-mail address or an http(s) URL".
  - **An overclaim.** docs/core.md says the publish step writes nothing "until it is set to an address readers can reach". The check cannot know that: it refuses the names it lists.
- **As before.**
  - Missing 2, the Wikibase draft items.
  - The 2,921 asked answers still have no `quotes_checked`, so a reviewed and ticked one says "Every quote matched" with no count behind it. In the one tried, all 10 quotes were in the statute text.

### New

- **Once a database is shared, the reviewer list is not only this operator's.**
  - **A reviewer added elsewhere.** A row "Claude", attorney, Maryland, `added_by` "another machine", and an answer signed with it were pulled from the stand-in shared copy.
    - The page read "Reviewed by Claude, attorney licensed in Maryland, on 11 October 2026".
    - No one on this copy added or vouched for that reviewer, and no AI-name warning ran.
  - **A renamed row.** A review stores only the reviewer's id.
    - On the shared copy, Ana Villamar's row was renamed "Claude", with a later `updated_at`, and the pull took it.
    - The page she had signed then read "Reviewed by Claude, attorney licensed in Virginia, on 11 October 2026".
    - So whoever can write the shared `reviewers` table can change the name on every page a person signed.
  - **The claims.** These hold only without sync: `lexflow:method`'s "the list of reviewers that the operator of this lexflow copy keeps. The operator adds each person to that list", and README's "nothing else writes it".
  - **A fix.** Keep the list local, or take only rows from origins this copy trusts, and refuse a pulled name change for a reviewer whose reviews are on record.
- **The attestation is not tied to the reviewer.**
  - The API has no sign-in, and docker-compose publishes it on every interface (`"${LEXFLOW_PORT:-8000}:8000"`).
  - Anyone who can reach the dashboard can:
    - pick any reviewer on the list;
    - tick "I am a person, and I read this exact text against the law";
    - record the review, then tick "For the wiki".
  - `lexflow:method` calls this "their own statement", and README "the reviewer's own statement".
  - Binding the port to 127.0.0.1, or recording reviews only through the operator's CLI, would make that true.
- **A curated model's sign-off can be dated before the model existed.**
  - A signed `curated/va/records.json` dated 2001-01-01 built, and the page read "Reviewed by Eli Marsh, attorney licensed in Virginia, on 1 January 2001".
  - Asked answers and place files refuse a review dated before their text, but `build._signoff` passes no `not_before`. The drafting note's date (2026-10-10) would do.
- **An asked answer's map draws its question id.**
  - All 2,918 stored asked-answer maps keep a start event like "A criminal_record_expunged_sealed process begins" through `reader_bpmn`, because the trigger in their facts carries the id.
  - Once one is reviewed and ticked, bpmn-js draws it. None is live today.
- **Charlottesville's business caveat repeats the claims it removed.**
  - It says "The research could not load the Development Code PDF (over 10 MB) or the Municode City Code pages. Two earlier claims are therefore removed or softened:", and then lists them.
  - It is in the third person now. But it describes the drafting, as the Baltimore caveat did, and it prints the claims it says were removed.
- **The other workflow's process files.** This is provisional, since the files are still being written.
  - **The AI-check date.** It is the file's own record, not bound to the text the way the software's count is.
    - 33 verified files give the AI check as 10 October 2026, while some of their sources were retrieved on 11 October.
    - A page would then date the check before some of the sources it covers were read.
  - **Caveats and source titles about the drafting.** Verified files describe the drafting rather than the place, the kind Re-check 3 found in Baltimore:
    - "rechecked by the verifier on 2026-10-11";
    - "the verifier rendered both pages to read it";
    - "for the modeller and again for the verifier";
    - "(read in full by the verifier)" and "added by the verifier";
    - "(lexflow index row 30394)";
    - in Staunton, "declared research User-Agent (lexflow-research/0.1)".
- **Small.**
  - README still says "every quote matched to the official text", under "No person has reviewed the models yet". The pages say Open US Law's copy.
  - `lexflow:method` says lexflow's software matches the quotes "that cite a section of the state's code". `places.CODE_CITE` reads only Virginia and D.C. citations. That is true today, since every process file is in Virginia.
  - A DC page accepted "local procedure: reviewed by Dana Whitfield, attorney licensed in Virginia". The licence is printed, so a reader can see it, but nothing checks that it is the page's own jurisdiction.

## Re-check 5 (11 October 2026)

This checks the fifth round of fixes against Re-check 4.

Method:
- A throwaway copy of the live database was made in `/tmp/g0r5v` (SQLite backup). Next to it was a copy of the code with its own `curated/` folder, plus the checkout's README.md, .env.example, docker-compose.yml, requirements.txt, `out/`, `schemas/` and `patches/`.
  - Every trial ran there, with every credential blank, the job runner off and Python's network calls blocked. The trials attempted no network call.
  - The checkout's files, the live database and the live API were only read.
- Reviews were tried through FastAPI's TestClient and the `lexflow reviewer` CLI. Curated sign-offs went through `build`, on the code copy's `curated/va/records.json`.
- Sync went through `turso.pull`, `turso.push` and the sync job step. The shared database was a stand-in: `Turso.pipeline` run on a local SQLite file.
- The reviewers in the trials are made-up names (Ana Villamar, Ben Okoro, Cara Lund, Dana Whitfield, Eli Marsh).
- Corrections values went through `corrections_problem`, and three of them through `run_publish` in a dry run.
- All 44 pages were rendered from a fresh backup of the live database with `python -m lexflow wiki-pages`.
- The 2,918 stored asked-answer maps went through `reader_bpmn` three ways: with the question, with only its id, and with neither.
- The 60 researched process files in `curated/places/va/*/` were read as they stood and rendered with `render_local_process`, without loading them. `run local` was not run.
- Nothing was published. No benchmarks or Ollama were run, and no container was restarted. Only this section was edited.
- The database and code copies were deleted afterwards. The pages, the trial scripts and their output are in `/tmp/g0r5v`.

### Fixed

- **1. Reviewer tokens: fixed for the review API.**
  - `reviewer add` printed the token once. Only `scrypt$16384$8$1$…` is stored, and the token appears nowhere in the database or in `GET /api/reviewers`.
  - `PUT …/review` returned:
    - 401 with no token or an empty one;
    - 403 for a string that is not a token, for Ana's id with a random secret, and for Ben's token with Ana's id in the body (the reason is "that token is another reviewer's");
    - 403 for Ana's old token after `reviewer token`, for a removed reviewer's token, and for any token of a reviewer added by older code without one;
    - 200 for Ana's own token, also with the header in lower case or the token padded with spaces.
  - The page then read "Reviewed by Ana Villamar, attorney licensed in Virginia, on 11 October 2026". `review_log` had one row per review, with her id and the text hash.
  - `DELETE` returned 401 without a token and 200 with Ben's token (`removed_by` was Ben's id), as the docs say. The tick returned 409 without a review and 200 after one, with no token.
  - The CLI's `list --all`, `token`, `remove` and the AI-name warning behave as the docs say.
- **2. The reviewer list on an ordinary pull: fixed.**
  - `turso.remote_schema` creates no `reviewers` table. A default pull left the local list unchanged, even with a `reviewers` table on the shared copy holding a renamed Ana and a new reviewer.
  - A review naming an id that is not on the list kept the answer off the wiki, and was logged once ("a review names reviewer rv-12345678, who is not on this copy's reviewer list").
  - The cases this does not cover are under New.
- **3. Curated sign-offs before the drafting note or in the future: refused.**
  - On va.records, sign-offs dated 2001-01-01, 2026-10-09 (the day before the note) and 2026-10-12 each built with "Not yet reviewed by a person", with the reason in the log.
  - One dated 2026-10-10 showed "Reviewed by Eli Marsh, attorney licensed in Virginia, on 10 October 2026".
  - How the floor can be moved back is under Not fixed.
- **4. Names: the ones Re-check 4 found are refused.**
  - All 19 tried again were refused: the Cyrillic "Аttorney Lіcensed", "Lawyеr", "Еsq" and "Еѕԛ"; the Hangul fillers U+3164, U+115F and U+FFA0; the Khmer U+17B4; and Atty, Juris Doctor, Virginia Bar, Member Virginia Bar, Advocate, Abogada, Avocat, Rechtsanwältin, Fact Checker, Wiki Editor and Moderator.
  - Full-width, mathematical-bold and accented "Esq", Braille blank, tag characters, variation selectors and U+061C were refused too.
  - Clɑude, ɡemini, Cօpilot and Llɑma now bring the AI-name warning.
  - Ordinary names were stored in Latin, Cyrillic, Greek, Japanese, Korean, Devanagari, Thai, Arabic and Vietnamese, along with Siobhán O'Brien, Jean-Luc Picard, J. D. Salinger and Ai Weiwei.
- **5. Corrections address: fixed for the names it lists.**
  - 18 of Re-check 4's 25 values are refused. The 7 still accepted are the ones the fixer lists (under Not fixed).
  - `http://localhost:8080/report` now gets the right reason.
  - These were refused: seven numeric forms of an IP address (127.1, 0177.0.0.1, 017700000001, 0x7f.1, `[::ffff:127.0.0.1]`, 169.254.169.254, `corrections@[127.0.0.1]`); names with a trailing dot or in capitals; `https://lexipedia.xyz@example.com/`; 7f000001.nip.io; and app.localtest.me.
  - A dry run with an address on a `.lan` name refused all 44 pages in one log line. `process_models.stages` did not change.
- **6. Asked answers count their quotes when the page is made: fixed.** On criminal_record_expunged_sealed (va), signed with Ana's token and ticked:
  - As stored, the page read "14 of 14 quotes matched to Open US Law's copy of the official text on 11 October 2026".
  - With one quote added that is not in the text, it read "14 of 15". With a step quote changed too, "13 of 15".
  - With its sections not at hand, it read "Quotes not matched by lexflow's software: the statute text was not at hand when this page was made". With no quotes, "No quotes from the statute to match".
  - The Virginia page read "60 of 61 quotes from the statute matched to Open US Law's copy of the official text on 11 October 2026". No asked page says "Every quote".
- **7. Asked-answer maps: fixed.** Of the 8,754 renders, none has the question id, a snake_case word, "process begins" or "[implied]" in a name, a documentation line or an annotation. That holds even with neither the question nor its id passed in.
- **8. Process files checked before their sources were read: fixed in the loader and on the page.**
  - 59 of the 60 files say they are verified. 8 count as verified under the new rule; the fixer's 57 and 7 came before the other workflow's later edits.
  - In a copy of a verified file with its check date moved before a source's retrieval, the page drops the AI-check claim and says "not matched by lexflow's software; sources retrieved on 10 October 2026". It does the same when the file has no check date.
  - The six drafting phrases Re-check 4 quoted are gone from the rendered pages. What remains is under New.
- **9. Charlottesville's place file: fixed in the file.**
  - The business caveat no longer describes the drafting.
  - The MuckRock note is gone, and the Room A130 and assumed-name notes now describe the place.
  - The sentence about a secondary source ("one non-resident worker and no more than three clients at a time") was in the earlier text too, and it is attributed.
- **10. Wording.**
  - README now says "every quote matched to Open US Law's copy of the official text".
  - `lexflow:method` says the local-quote matcher reads only Code of Virginia and D.C. Code citations. That is what `places.CODE_CITE` holds.
- **11. The port in docker-compose.yml: fixed in the file.** `docker compose config` binds the app to `127.0.0.1:8000`, with or without `docker-compose.dev.yml`. The running containers are under Not fixed.
- **Live pages.**
  - The 44 rendered pages are the fixer's `/tmp/g0r5/pages`, apart from one `lexflow:method` sentence the fixer edited after that render.
  - Outside `lexflow:method`, no page has a model name, "quality", "Confidence" or "checked by", in the text or in the embedded XML. No page names a reviewer, and no snake_case id appears outside the XML.
  - No staff member or researcher is named, and no partner or endorser is claimed.
- **Tests.** `LEXFLOW_DATA` pointed at an empty temporary directory and every credential was blank.
  - The suite gave 1,277 passed and 5 skipped in 1 min 59 s, the fixer's count. The skips are four California-store cases and the live-wiki case. `tests/test_gate0.py` has 58 tests.
  - With the network blocked, the suite tried 27 lookups of `oss-data-us.vaquill.ai` (the Open US Law store) and 4 of 127.0.0.1. It passes without them.
  - With this section in place, the suite gave the same count again (2 min 19 s). `tests/test_gate0.py` checks the addresses in the design notes, so this section writes no new e-mail address.

### Not fixed

- **The live database, as the fixer says.**
  - `lexflow:va:charlottesville:business` still says "I could not load the Development Code PDF (over 10 MB) or the Municode City Code pages. Two earlier claims are therefore removed or softened: …".
  - `…:records` still has the MuckRock note and "five-day".
  - `run local` for va has to run once the other workflow is done.
- **The running containers.**
  - `lexflow-app-1` still publishes 8000 on every interface (`0.0.0.0` and `[::]`), because it was not recreated.
  - So does `lexflow-test-ui` on 8001, a `docker compose run` one-off against the live `/data`.
  - Both run older code: `GET /api/reviewers` returns 404, and the API offers no review endpoint. But `POST /api/jobs` queues any step for anyone who can reach the port.
- **The curated sign-off floor can be moved back.** `build.first_built` takes the earliest date anywhere in the drafting note and the stored `first_built`. After builds that had stored 2026-10-10:
  - With the note edited to "…, 2000-01-01; …", a sign-off dated 2000-06-01 showed "Reviewed by Eli Marsh, attorney licensed in Virginia, on 1 June 2000".
  - With a correct note that also mentions "a draft of 1999-01-01", one dated 1999-06-01 was accepted.
  - The stored `first_built` then stayed at 1999-01-01, so with no note at all, one dated 1999-07-01 was accepted.
  - So "the first build this copy recorded" is not a floor. Whoever edits the file answers for it, as the docs say, but the docs' sentence on dates claims more (see below).
  - On the page side, `model_reviewer` reads `first_built` from the stored metrics. A row without it, from older code or from sync, has no floor.
- **Names: still lists, as the docs now say.**
  - Whole words in one script that the look-alike table misses are stored:
    - "Jane Doe ЕЅԚ" (Cyrillic capitals, reading ESQ);
    - "Jane Doe ЈԀ" (reading JD);
    - "Jane Doe ᎫᎠ" (Cherokee, reading JD).
  - `skeleton` maps look-alikes before it folds case, so the capitals of the table's small letters (Ԛ, Ԁ) are missed. Folding case first would catch those two.
  - Still stored: the placeholders Re-check 4 listed (No Name, Person, Human, Mickey Mouse, Me and the rest), and a name with 40 combining accents on one letter.
  - Some real surnames are refused: Jane Lawyer, Agnes Clerk, John Staff.
- **Corrections, as the fixer says.**
  - Still accepted: changeme@lexflow.org, noreply@lexipedia.xyz, a@b.co, `https://example.co.uk/report`, user@example.edu, the form link with "XXXXXXXX" and the issues link with "OWNER/REPO".
  - A dry run with `https://github.com/OWNER/REPO/issues` would write all 44 pages. Its first log line names the address, so the operator sees it.
- **The other workflow's process files.**
  - 51 of the 59 verified files load as not verified and get no page until they are re-dated or re-checked.
  - The AI check is still the file's own record, not bound to its text.
- **As before:**
  - snake_case element ids in the map source;
  - the Wikibase draft items (the administrator's step);
  - nothing checks that a reviewer's licence is the page's own jurisdiction;
  - asked pages date their count to the day they are rendered.

### New

- **A review written into the shared database is shown, with no token.**
  - **An asked answer.** On the stand-in shared copy, its quote was edited ("is FORGED STEP not authorized to"). It was given `reviewed_by` naming Ana's id, the hash of the edited text and `published: 1`, then pulled.
    - The page went on the wiki with "3 of 4 quotes matched … · Reviewed by Ana Villamar, attorney licensed in Virginia, on 11 October 2026", and the edited quote on it.
    - `review_log` was empty, and no token was used.
  - **A state model.** va.records was signed the same way on the shared copy, dated 2001-01-01 and without `first_built`. It read "Reviewed by Ana Villamar, attorney licensed in Virginia, on 1 January 2001".
  - **Why.**
    - Every pushed review carries the reviewer's id.
    - On a pull, `drop_stale_reviews` checks only the hash and the date. It checks nothing for `process_models`.
    - Pages never read `review_log`. In the code, local answers take the same path (not tried).
  - **A fix.** Name a reviewer of an asked answer only when this copy's `review_log` has that review, and drop a pulled one that it does not have. Name a curated or place sign-off only when this copy's own file carries it.
- **`sync pull --tables reviewers` writes the reviewer list.** This runs from the CLI, or as the sync job through `POST /api/jobs`.
  - With a `reviewers` table on the shared copy (older code made one), the pull renamed Ana "Claude", with no AI-name warning. It replaced her token hash, so her own token stopped working and the shared copy's token became hers.
  - It also added "Eli Marsh", who has no token but is on the roster. The job step then renamed him "Dana Whitfield".
  - The page Ana had signed read "Reviewed by Claude, attorney licensed in Virginia, on 11 October 2026".
  - `push --tables reviewers` fails with `KeyError: 'reviewers'`.
  - **A fix.** `push` and `pull` refuse any table not in `db.SYNCED`. `db.upsert` falls back to `LOCAL_KEYS`, which is why the pull works.
- **Anyone who can write the shared database can change what a page says it checked.**
  - The bundled libSQL server is published on every interface (`"${LIBSQL_PORT:-8081}:8080"`, with no key set), and this machine's `TURSO_DATABASE_URL` points at it. `lexflow-libsql-1` is running on `0.0.0.0:8081`.
  - A fabricated step quote ("FABRICATED: the public body may refuse any request without giving a reason") was written into va.records on the stand-in and pulled. The page read "Every quote matched to Open US Law's copy of the official text on 11 October 2026", with the fabricated quote on it.
  - The reason: a state model's count comes from its stored metrics, not from a match made on this copy. So `lexflow:method`'s "On that date lexflow's software found these quotes" holds only for models built on this copy.
  - **A fix.** Bind libSQL to `127.0.0.1` or give it a key. Count a state model's quotes when its page is made, as asked answers now do.
  - Today the live data is local: the 22 models were built on this machine at 09:00 UTC, and the last sync was a push on 9 October.
- **Dropping drafting notes takes reader warnings with it, and leaves other drafting text.** None of these files has a page today.
  - **Warnings lost.** A sentence, or the clause of one, goes with the warning in it when it also mentions the verifier or the research client:
    - staunton/probate_will_qualify_executor: "The modeller and, separately, the verifier rendered the archived copy and read it by eye, so its two quotes (steps s5 and s8) and the description of its questions are transcriptions that a text search cannot confirm."
    - charlottesville/building_permit_residential: "The city's online Permit Fee Calculator is an embedded widget whose script did not load for the research client (the server closed the connection), so fees for project values over $1,500 cannot be computed from the sources read."
    - albemarle/meals_tax_filing: "…but the verifier could not rule out a different adopted text".
  - **Drafting text kept.**
    - Two Staunton caveats keep a model name: "city pages were therefore read in the Claude desktop browser pane, one at a time", and "the pages were read in the Claude desktop browser pane, one page at a time".
    - Others keep "State-law quotes are copied from the lexflow 'va' full-text index (rows 7887-7923, …" and "During this research one request was sent to that host by mistake, before its robots.txt had been checked."
    - Two files that count as verified keep "During verification, Municode's library terms page loaded only as a script shell" and "Municode was not accessed (research rules for code-publishing services)."
  - **A fix.** The files need rewording at the source, by the other workflow. A page scan for "Claude" and "the research" before these pages publish would catch the rest.
- **A future AI-check date is accepted.** A verified file whose check is dated 2026-12-01 counts as verified, and its page says "checked by an AI verifier against the cited page on 1 December 2026".
- **Small.**
  - The DC place file's caveats still describe the research, the kind Re-check 3 found in Baltimore. They appear live on the DC business and records pages: "the research did not fetch the portal's content", "the research checked", "the research did not cover".
  - "yourdomain" names are refused only when "yourdomain" is the first label. `https://www.yourdomain.com/corrections`, an e-mail address on mail.yourdomain.com and `https://corrections.yourdomain.org/` are accepted, and the dry run would write all 44 pages.
  - The asked page tried cites "Va. Code Ann. § 9.1-134 — (Effective until July 1, 2026)". Its steps are cut mid-phrase ("Enter an ex parte order, without notice to"). It is not live.

### Claims the code does not back

- **README.**
  - "The list is this copy's own: it is not synced, and nothing else writes it." `sync pull --tables reviewers` writes it.
  - "An answer can go on the wiki only after a person on the operator's reviewer list has read it against the law." A review written into the shared database puts one there.
  - "…a newer copy arrives through sync … the page says "Not yet reviewed by a person" until someone on the list signs the text it shows". A newer copy that brings its own review in a listed reviewer's name is shown as reviewed.
  - "a sign-off dated before the model was first built (that note's date, or the first build this copy recorded) or in the future is refused". The earliest date anywhere in the note sets the floor.
- **docs/core.md.**
  - "The table is not synced: a pull never adds, renames or removes a reviewer". Not with `--tables reviewers`.
  - "A page names the reviewer … only while they are on it and the page is built from the text they signed". The code checks the record's hash, not who wrote the record.
  - The same sentence on sign-off dates as README.
  - "and "yourdomain" names". Only as the first label.
  - "publishes port 8000 on `127.0.0.1` only". This is true of the file, but the same file publishes libSQL on every interface with no key, and the docs do not say so.
- **`lexflow:method`.**
  - "The list is this copy's own: it is not shared with other copies". Not with `--tables reviewers`.
  - "These answers appear on the wiki only after a person on the operator's reviewer list has reviewed them." Not when the review arrives through sync.
  - "A review covers only that text; … until someone on the list signs the text it shows." The same.
  - "lexflow's review tool records that statement only with the reviewer's own token". This is true of the API. But the page does not say what README and docs/core.md do: a curated file's sign-off, the only kind a state map can carry, is recorded by whoever edits the file, with no token.
  - "On that date lexflow's software found these quotes, word for word, in the statute text it holds". For a model pulled through sync, the count is the other copy's.
- **Docstrings.** `signoff.py` ("it is not synced, and nothing else writes it (the API and the dashboard only read it)") and `reviewers.py` ("a pull never adds, renames or removes a reviewer here") claim the same as README.

### What blocks a first publish

- **Blocks.**
  - `run local` for va, once the other workflow is done, so the Charlottesville pages carry the file's text.
  - `LEXFLOW_CORRECTIONS`, the operator's step.
    - Setting it means recreating `lexflow-app-1`, which also applies the `127.0.0.1` binding.
    - `lexflow-test-ui` has to be stopped. It stays on every interface with a job API.
  - The claims above on `lexflow:method`, which the first publish writes.
    - Either make them true: refuse tables outside `db.SYNCED` in push and pull; name a reviewer only for a review this copy recorded or this copy's file carries; count state-model quotes when the page is made.
    - Or say on the page what the code does. That covers reviews from another copy (they count when they name someone on this list, and whoever can write the shared database can write one) and curated sign-offs (whoever edits the file records them, with no token).
    - The README and docs/core.md sentences go with them.
- **Does not block a first publish run before any pull.**
  - The forged review and the fabricated quote need a pull from a shared database that someone else has written. The live data is local today, and no reviewer is on the list.
  - Until libSQL is bound to `127.0.0.1` or given a key, do not pull from it before a publish.
- **Does not block.**
  - The name and corrections lists: the docs say the operator answers for them.
  - The curated date floor: no curated file is signed. Its README and docs/core.md sentence should still be corrected.
  - The process files: none has a page yet. Their stripping, wording and future check dates have to be settled before they do.
  - The DC "the research" caveats.
  - The render-day dates on asked pages.
  - The snake_case ids in the map source.
  - The Wikibase draft items, the administrator's step.
  - The licence-jurisdiction check.

## Re-check 6 (11 October 2026)

This checks the sixth round of fixes against Re-check 5.

Method:
- The code was a copy of `/app` taken at 20:25 UTC in `/tmp/g0r6v/code`, plus the checkout's README.md, docker-compose.yml, docker-compose.dev.yml, .env.example and `out/`. `/app/lexflow` had not changed since when this section was written.
- Each trial ran on its own SQLite backup of the live database. The statute files were read through a read-only link to `/data/raw`. The quote cache was copied from `/data/cache/quote_pages`, and the copy is identical to it.
- Every credential was blank, the job runner was off and Python's network calls were blocked, apart from loopback. No trial attempted a network call.
- The shared database was a stand-in: a small libSQL server on 127.0.0.1:18081 (Hrana `/v2/pipeline` over a throwaway SQLite file) that logged every request. The real libSQL server was neither pulled from nor pushed to.
- Reviews went through FastAPI's TestClient and the `lexflow reviewer` CLI. The reviewers are made-up names (Ana Villamar, Ben Okoro, Eli Marsh). Curated sign-offs went through `build`, on the code copy's own `curated/va/records.json`.
- The researched process files were loaded with `load_local`, first for Virginia and then for every place file. All 60 local process pages were rendered with `render_local_process`. After the full load, every page a first publish would write was rendered with `all_pages`.
- 30 quotes were drawn at random (seeded, 10 per place), plus a further 12 that lexflow matched to web pages. I matched them myself with a fetcher of my own on this machine:
  - read-only GETs with a plain User-Agent, robots.txt checked, at least 3 s between requests to one host and 6 s to the Internet Archive;
  - an Internet Archive capture (the `id_` form) for the hosts that refuse automated readers; no browser, and never Municode;
  - Code of Virginia quotes were matched against the official publisher's section page, and PDFs were read with pdftotext.
- Nothing was published. No benchmarks or Ollama were run, and no container was restarted. Only this section was edited.
- The database copies were deleted afterwards. The pages, the trial scripts and their output are in `/tmp/g0r6v` in `lexflow-app-1`.

### Fixed

- **1. Push and pull take only the shared tables: fixed.**
  - `lexflow sync pull` and `push` with `--tables reviewers`, `review_log`, `jobs`, `settings`, `sync_marks`, `sqlite_master`, `Reviewers`, `answers,reviewers`, " reviewers " and `answers;DROP TABLE reviewers` each exited 2 with one line ("sync takes only the shared tables (…); refused: reviewers (reviewers: this copy's own, never synced)").
  - `lexflow run sync` gave the same, with `--tables` and with the tables in `--args` (a string, a list, an object or a number).
  - `POST /api/jobs` returned 400 for each of these and queued nothing. A sync job with `tables: "answers"`, or none, was queued. A sync job already in the table with `tables: "reviewers"` fails when it runs (`run_sync`).
  - The stand-in received no request during any refused command.
  - The shared copy then held an old-style `reviewers` table that renamed Ana "Claude" and added Eli Marsh. A default pull left the local list as it was.
- **2. A review that arrives by pull, or is written into the review field by hand, names no one: fixed.**
  - **Asked answers.**
    - On the stand-in, a step quote was edited ("FORGED: the clerk may refuse any request without a reason"), and the answer was given Ana's id, the new text's hash and `published: 1`, then pulled. The page named no one and the answer was not in the publish set. `GET /api/ask` counted it under `review_stale`, and one log line said "carries a review this copy did not record".
    - Ana reviewed a second answer through the API, with her token. The page read "Reviewed by Ana Villamar, attorney licensed in Virginia, on 11 October 2026".
    - A newer copy of that answer was then pulled with other text and a review rebound to Ana, with the same date and the new text's hash. It named no one.
    - A review recorded here and then removed with Ben's token stayed removed when the shared copy brought the old review back.
  - **The state model.** va.records was signed on the shared copy in Ana's name, dated 2001-01-01 and dated today, and pulled. Neither counted. The same sign-off written by hand into this copy's row did not count either.
  - **A place's local answer.** A sign-off pulled in Ana's name, or written by hand in Ben's, named no one.
- **3. State-model quotes are counted when the page is made: fixed.**
  - On the stand-in, va.records' first step quote was replaced with "FABRICATED: the public body may refuse any request without giving a reason", with `quote_misses: 0` left in its metrics, and pulled.
  - The model page read "22 of 23 quotes matched to Open US Law's copy of the official text on 11 October 2026", with the made-up quote on it.
  - The other pages gave the same count: the Charlottesville place-process page ("22 of 23 quotes from the statute matched"), the Charlottesville page and the Virginia page ("45 of 46"), `lexflow:start` ("45 of their 46 quotes were matched"), and `lexflow:method`'s table (23 checked, 1 not exact; "Today 1 of the 2 models pass").
  - A made-up law quote in a decision rule as well gave "21 of 23". With its sections pointed at one this copy lacks, the page read "Quotes not matched by lexflow's software: the statute text was not at hand when this page was made".
- **4. The sign-off floor, once stored: fixed.**
  - va.records was built here with a sign-off dated today. `first_built` was stored as 2026-10-11 (the earliest build the live row records), and the page named Ana.
  - Pulls that lowered `first_built` to 1999-01-01, or dropped it, were undone (`keep_first_built`).
  - A note opening "Claude (claude-opus-5-5), 2000-01-01; …", and a note that mentions "a draft of 1999-01-01", both left the floor at 2026-10-11. A sign-off dated 2026-10-10 was refused under each.
  - What a pull can still do is under New.
- **5. Future check dates.**
  - A model's `checked_on` of 2026-12-01 is ignored (`model_checked_on`), and no page prints that date.
  - A process file whose AI check is dated 2026-12-01 gets "its AI check is dated 2026-12-01, in the future" from `check_date_problem`, and its page shows no such date. The cases that still print a future date are under New.
- **6. Published ports.** `docker compose config` binds app 127.0.0.1:8000, libsql 127.0.0.1:8081 and test-ui 127.0.0.1:8001. That holds with `docker-compose.dev.yml`, with `docker-compose.gpu.yml`, and with every profile. .env sets no `LIBSQL_BIND`. Ollama and SearXNG publish nothing. What test-ui receives from .env is under New.
- **7. Re-check 5's claims.** Most are now true or rewritten, as the trials above show:
  - the reviewer list is not synced and only `lexflow reviewer` writes it;
  - an asked answer goes on the wiki only after a review recorded here with the reviewer's token;
  - a newer asked answer pulled through sync is not reviewed;
  - a map from another copy is counted here;
  - a curated sign-off is not bound to a token;
  - "yourdomain" as any label (`www.yourdomain.com`, `corrections.yourdomain.org` and a `mail.yourdomain.com` address are refused);
  - libSQL's binding is documented.
  - What is still not backed is listed below.
- **8. Names: the three Re-check 5 found are refused**, and so are their other cases: "Jane Doe ЕЅԚ", "еѕԛ", "ЈԀ", "јԁ", "ᎫᎠ", the Cherokee small letters "ꭻꭰ", Lisu "ꓙꓓ", "МԀ", "ӀӀМ", "ΑΤΤΥ", "АТТУ", full-width "ＥＳＱ" and "Ｊ.Ｄ.". Jane Lawyer, Agnes Clerk, John Staff, J. Lawyer and Mary-Jo Clerk are stored. Lawyer, Jane Doe Lawyer, Clerk Smith, City Clerk, Legal Staff, Records Clerk and Unknown Staff are refused.
- **The researched process files.**
  - **The load.** It gave 60 rows and 47 verified (Albemarle 16 of 20, Charlottesville 17 of 20, Staunton 14 of 20). The 13 not verified, and their counts of unmatched quotes, are the ones the fixer lists. The load attempted no network call.
  - **The cache.** It holds 972 pages: 517 read live, 352 from Internet Archive copies and 103 not read. No Municode code page was fetched (each has "not fetched"). Only Municode's terms page was read, from an Internet Archive copy.
  - **My own match of the sample.**
    - Of the 30 drawn at random, 18 cite the Code of Virginia, 11 web pages and PDFs (2 of them read from archive copies), and 1 is a quote lexflow did not match.
    - 28 matched word for word in what I fetched.
    - Va. Code § 24.2-701.1 (Staunton absentee_voting, legal_basis[7]) matches the official page apart from a space before two commas ("§ 24.2-643 , he"). Open US Law's copy has that space.
    - The unmatched one is Staunton building_permit_residential fees[5]. The city refuses automated readers, and the Internet Archive answers 404 for the only capture its index lists (20260413173613), so it stays unmatched for me too.
    - All 12 of the further page quotes matched, 8 of them in archive copies, at the captures lexflow cites.
  - **Unmatched quotes are shown as unmatched.** All 61 are on the 13 files that are not verified. Each such page lists them under "Quotes not matched", and no page in the publish set has one.
  - **The quote policy.**
    - Of the 379 quotes withheld as albemarle.org words, none is printed apart from four item labels of two to six words. One of those is on a published page: "Peddlers, Mobile Food", in Albemarle meals_tax_filing.
    - The 16 published Albemarle pages each have one "Words not reprinted" section.
    - The 12 quotes that cite eCode360 are all matched to Open US Law's copy of the Code of Virginia, and are printed as state law.
  - **The page scan.** Of the 47 pages in the publish set:
    - none has a model name, "Every quote", "the research", "verifier", "browser pane", "index row" or "research client";
    - every mailbox is an office's;
    - no staff member or researcher is named.
    - What the scan did find is under New.
  - **Every page, after a throwaway `run local` of every place file.**
    - There are 97 pages: the 44 of today, the 47 local process pages, and the Albemarle and Staunton main pages with their records and business sub-pages.
    - The 47 local process pages are byte for byte those of the Virginia-only load.
    - Outside `lexflow:method`, no page has a model name, "Confidence" or "checked by", with the embedded map XML removed. "quality" appears only in quoted law ("drinking water quality standards").
    - "Every quote" appears only on state, model, place and place-process pages that count statute quotes, never on a local process page.
    - The publish step refused, since `LEXFLOW_CORRECTIONS` is not set.
- **Tests.**
  - `LEXFLOW_DATA` pointed at an empty temporary directory and every credential was blank. The suite gave 1,303 passed and 5 skipped in 2 min 49 s.
  - `tests/test_gate0.py` has 69 tests and `tests/test_place_processes.py` 18.
  - The six failures the first fixer left are gone.
  - With this section in place, on a fresh copy of the code, the suite gave the same count again (2 min 48 s). This section writes no e-mail address.

### Not fixed

- **The running containers.** `lexflow-app-1` publishes 8000 on `0.0.0.0` and `[::]`, and `lexflow-libsql-1` publishes 8081 the same way, until the operator recreates them. `lexflow-test-ui` is not running.
- **The live database.** It still holds the older place rows:
  - DC's records and business caveats still say "the research";
  - Charlottesville business still has "Development Code PDF", and records the MuckRock note;
  - its five Charlottesville process rows are not verified.
  - `run local` for va and dc puts in the clean files and the 47 verified processes.
- **A researched process's stored quote check is trusted when its hash fits** (the fixer's own note). It is the hash of the row's own spec, not of this copy's file.
  - On the stand-in, the dog_license row's check was changed to `matched_on: ["2027-01-01"]`, with every quote moved to archive copies, and pulled.
  - The page read "63 of 63 quotes matched by lexflow's software: 63 to the cited pages (63 from Internet Archive copies) on 1 January 2027". As built here it reads "36 to Open US Law's copy of the Code of Virginia, 27 to the cited pages on 11 October 2026".
  - A made-up quote in the pulled spec, with a check claiming it matched, was kept out of the publish set: `place_processes` matches the quotes again against this copy's cache. But the row stayed `verified=1`, which is enough for the place to get a main page.
- **A pulled process's other text is printed.** With every quote kept, a pulled spec with a fee of "FORGED: $0, no fee" and a contact "555-0100 (FORGED)" went into the publish set with both on the page. README says pulled text appears, but the page's label still says lexflow's software matched it.
- **The AI check is still the file's own record**, not bound to its text.
- **Still stored:** the placeholders No Name, Person, Human, Mickey Mouse and Me; a name with 40 combining accents on one letter; and the corrections values Re-check 5 listed (`https://github.com/OWNER/REPO/issues`, among others, is still accepted).
- **The app image has neither pdftotext nor pypdf**, so a quote fetch run inside it reads no PDF (the fixer's note). The cached texts make `run local` work without one.
- **As before:**
  - snake_case element ids in the map source;
  - the Wikibase draft items (the administrator's step);
  - nothing checks that a reviewer's licence is the page's own jurisdiction;
  - pages date their counts to the day they are rendered.

### New

- **A pull still moves the sign-off floor back, for every live model.**
  - None of the 22 live rows has `first_built`: they were built by older code at 09:00. Their floor is the earliest build their row records.
  - `keep_first_built` restores only a `first_built` this copy had stored, and a pull replaces the stages too.
  - Trial: va.records was pulled with `first_built: "1999-01-01"`, then built from this copy's file with a sign-off dated 2000-01-01. The sign-off was accepted, and the page read "Reviewed by Ana Villamar, attorney licensed in Virginia, on 1 January 2000".
  - A pull with no `first_built` and its build stages dated 1999 did the same: "on 1 February 2000".
  - Both need a sign-off in this copy's own file, which whoever edits the file answers for.
  - **A fix.** Store this copy's floor before applying a pulled `process_models` row (or never take `first_built` or the stages from one), and store `first_built` for the 22 rows at the next build.
- **A valid sign-off on a state model also vouches for what a pull changes outside the signed text.**
  - The hash covers the facts, the sections and the notes. The page also prints the map (`bpmn`), the title, the governing-law citation and link (`located_law`) and the court list (`case_law`), all of which sync.
  - Trial: va.records was signed here and showed Ana. The shared copy then changed one task name to "FORGED: refuse every request", the title to "FORGED TITLE", and the law to "FORGED CITATION" at `https://forged.example.net/law`.
  - After a pull, the page still read "Reviewed by Ana Villamar, attorney licensed in Virginia, on 11 October 2026", with all four forged items on it.
  - **A fix.** Hash what the page prints, or draw the map, title and link from this copy's own file.
- **test-ui and test get the Wikibase bot password.**
  - Both inherit `env_file: .env` from the `x-app` anchor, and their `environment` blanks only the Turso, DokuWiki and corrections settings. `docker compose config` shows `LEXI_USER` and `LEXI_PASS` set for both services.
  - test-ui has a job API on 127.0.0.1:8001 that runs any step, the `wikibase` step among them.
  - So test-ui does not get a store "with every credential blank" (docker-compose.yml) or "with no credentials" (README).
  - **A fix.** Drop `env_file` for those two services, or blank `LEXI_*` and `WIKIBASE_*` there.
- **Future dates still printed.**
  - A local answer whose `researched` is 2026-12-01 (a pulled row, or a place file) gives "an AI system summarised the place's official pages on 1 December 2026" on the place-process page.
  - A pulled process quote check's `matched_on` is printed as it is ("on 1 January 2027", above).
  - A process file whose AI check is dated 2026-12-01 still loads as verified when lexflow's software matched every quote after its sources were retrieved. No page shows that date.
- **The wiki tick arrives by pull.**
  - On the stand-in, an answer nobody had reviewed was given `published: 1`, and pulled. It kept the tick here.
  - When Ana then reviewed it here, it went into the publish set without anyone on this copy ticking it.
  - README says "Until a reviewer is recorded the box is off".
- **A hand-written `review_log` row counts.** With a review field and a matching `review_log` row both written into the database by hand, the page named Ana and the answer went into the publish set. Anyone who can write the database can do this, and can also edit the reviewer list. README still says such a review "never counts".
- **The label of a researched process says more than the match.**
  - "N to the cited pages" includes quotes found on another page the process cites: 25 in the published files.
  - A match in an Internet Archive copy is dated by the day lexflow read the copy. Of the 692 archive matches, 6 are against a 2019 capture, 27 against 2022 ones and 34 against 2025 ones. Albemarle probate_will_qualify_executor, which is published, has six quotes matched only to a 2019 capture of a county form, under "on 11 October 2026". The label gives no capture date.
- **Albemarle wording in lexflow's own text.**
  - Lexflow's fee lines and paraphrases on 14 published Albemarle pages repeat 9 to 15 consecutive words of the county wording they replace, mostly penalty formulas. For example, Albemarle personal_property_vehicle_registration has "10% of the tax levied on the return or $10.00, whichever is greater, not more than the tax".
  - One caveat quotes the county page directly: "MUST be postmarked no later than Election Day" (absentee_voting).
  - Whether a fee formula is the County's "content" is for the operator to judge.
- **Builder ids, code names and a file path on 13 of the 47 local process pages.** The page scan for drafting words does not look for these:
  - "The four local legal_basis entries are office procedures …" (7 pages);
  - the source title "Code of Virginia(va) with I.lookup and I.text_of: Va. Code §§ 15.2-521, …" (3 Albemarle and Charlottesville pages), which names lexflow's own index functions;
  - escalation triggers printed with their ids: "**no_answer: the Zoning Administrator does not decide …", "body_silent:", "appeal_denied:", "court_lost:" (Charlottesville and Staunton zoning_variance);
  - "see the bpol_business_license process", "Details are in the separate process business_tangible_personal_property_return", "see the va:charlottesville meals_tax_filing process", and "(see curated/places/va/charlottesville/personal_property_change_report.json)".
  - Row 12 kept such ids off the state pages. These pages get them at the first publish after `run local`.
  - **A fix.** Reword the files at the source, and add snake_case ids and `curated/` paths to the page scan.
- **One "The research" sentence is left in the DC place file.** "The research found no FR-500 registration fee stated." is in DC's business fees, and it is on the DC business page after `run local`.
- **Fetch notes left on published pages (11 pages).** None of these uses the words `places.DRAFTING_LEFT` looks for:
  - robots.txt files listed as sources on 8 pages (for example "robots.txt of forms.office.com (it bars automated readers)");
  - "consulted for reference only" and "the city's official copy was not consulted" (Staunton small_claims_civil);
  - "loads its content in the browser and was not used" (Albemarle meals_tax_filing);
  - "the portal was not used or submitted" (Charlottesville meals_tax_filing).
- **Names: other look-alike scripts and title-like surnames are stored.**
  - Canadian Syllabics "Jane Doe ᒍᗪ" and "ᒍᗞ" (reading JD) and "ᕮᔕᑫ", Coptic "ⲈⲤ", and Cherokee "ᏗᎠ" were stored.
  - So were Trial Lawyer, Chief Lawyer, Virginia Lawyer, Bar Lawyer, Real Lawyer, Senior Clerk, Head Clerk, Probate Clerk, Circuit Clerk and Senior Staff. The page would read "Reviewed by Virginia Lawyer, attorney licensed in Virginia, on …".
  - The docs say the lists catch only what they hold.
- **A real publish job ran on the live store.**
  - Job 68 (`publish`, `dry_run: false`) was queued at 13:28 UTC today and ran in `lexflow-app-1` (runner `cf5e9c47ad44`, that container's hostname).
  - Its log says "publish refused: no page was written, because LEXFLOW_CORRECTIONS is not set". Nothing was written.
  - The corrections check is what held it. Whoever can reach the job API can queue one, and the live app is still on every interface.

### Claims the code does not back

- **`lexflow:method`.**
  - "A researched local process gives two counts instead: … and, for its other quotes (from the place's own pages, other offices' pages, city codes and regulations), that they were "checked by an AI verifier against the cited page on <date>; not matched by lexflow's software", with the number of quotes the AI verifier did not confirm."
    - The label gives one count, made by lexflow's software, page quotes included.
  - "lexflow's software does not match the words quoted from local pages, other offices' pages, city codes or regulations: for those, an AI verifier's check against the cited page is the only check, and the page says so".
    - It matches them, and no page gives an AI verifier's count.
  - The sources table says of each place's official pages "The government's own terms; summarised, with a link".
    - Local process pages quote those pages word for word (other than the three sites in `quotes.NO_REPRINT`).
    - Internet Archive copies are a source the table does not list.
    - The page has none of `quotes.method_label`, `method_check` and `method_policy`.
  - "A map's sign-off may not be dated before the map was first built (the date this copy stored at its first build, which nothing later moves back)".
    - No live model has that date stored, and a pull moves the floor back (New).
  - "A review covers only that text; if the text changes … the page says it has not yet been reviewed by a person".
    - A pulled map, title or governing-law link does not unsign a state map.
- **README.**
  - "…and then kept, so a later build, an edited note or a pull never moves it back." A pull does, for every live model.
  - "A review that arrives through sync, or that someone writes into the database by hand, never counts." It counts with a hand-written `review_log` row.
  - "Until a reviewer is recorded the box is off." A tick arrives by pull.
  - The `test-ui` row: "on a throwaway store with no credentials". It gets `LEXI_USER` and `LEXI_PASS`.
  - Also stale: "What is verified" ("Tests: 150 pass", "43 pages are live") and "Known gaps" ("No local process models are built yet").
- **docs/core.md.**
  - "a model stored by older code without one takes the earliest build its row records. Once stored it is kept: a later build, an edited drafting note or a pull (`turso.keep_first_built`) never moves it back." A pull rewrites that row.
  - "Any other review field, pulled from another copy or written into the database by hand, counts as not reviewed". Not with a hand-written `review_log` row.
  - "A page names the reviewer … only while … the page is built from the text they signed". Not for a state map's map, title and link.
- **docker-compose.yml.** The test-ui comment: "with every credential blank".
- **`signoff.py` docstring.** "(…; then kept, so a later build, an edited note or a pull never moves it back)".

### What blocks a first publish

- **Blocks.**
  - `lexflow:method`'s sentences on researched local processes, and its sources row for local pages.
    - The first publish after `run local` writes 47 local process pages beside them.
    - The fixer left `quotes.method_label()`, `method_check()` and `method_policy()` for this. The sources table also needs a row for Internet Archive copies.
  - `lexflow:method`'s sentence that nothing moves the floor back, and the one that a changed text unsigns a page.
    - Either make them true (the fixes under New) or say what the code does.
    - The README, docs/core.md and `signoff.py` sentences go with them.
  - The builder ids, lexflow function names and file path on 13 of the 47 local process pages (New), reworded in the files before `run local`.
  - `run local` for va and dc on the live store, so the DC and Charlottesville pages carry the clean files and the 47 verified processes get pages.
  - `LEXFLOW_CORRECTIONS`, the operator's step.
    - Setting it means recreating `lexflow-app-1`, which also applies the 127.0.0.1 binding.
    - Recreate `lexflow-libsql-1` as well, so 8081 is on 127.0.0.1.
- **Does not block a first publish run before any pull.**
  - Everything that needs a hostile shared database: the floor moved back, a pulled map under a sign-off, a forged process check or a future date in it, pulled process text, and a pulled tick.
  - The live data is local today: no reviewer is on the list, no file is signed, and the last sync was a push on 9 October.
  - Until libSQL is bound to 127.0.0.1 (or given a key), do not pull before a publish.
- **Before starting test-ui:** give it no `.env` credentials.
- **Does not block.**
  - The name and corrections lists (the docs say the operator answers for them).
  - The hand-written `review_log` case.
  - The label's "to the cited pages" and its missing capture dates. These are worth fixing before outreach points at the Albemarle probate page.
  - The Albemarle fee wording.
  - The fetch notes on 11 pages, and DC's "The research found no FR-500 registration fee stated."
  - The future AI-check date.
  - The pdftotext gap in the image.
  - The Wikibase draft items, the licence-jurisdiction check, the snake_case ids and the render-day dates.
