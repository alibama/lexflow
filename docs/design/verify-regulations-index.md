# Verification: the regulations search index (N1)

Checked 2026-10-10, late evening (US Eastern), against [data-expansion.md](data-expansion.md) (§0 N1, §1 E1 and E9,
§2.1, §2.3, §3.1) and [data-building-codes.md](data-building-codes.md) (§1.3, §3.1, §4.1). The work under review
added `lexflow/corpus/regulations.py`, gave `lexflow/ask/index.py` an optional `corpus` parameter, added
`lexflow index --regulations`, `lexflow ask-search --regulations` and the `regulations` Setup card, and built 39
indexes at `/data/index/regulations_<st>.sqlite` in `lexflow-app-1`. Nothing was edited except this note.

**How it was checked.**

* No downloads and no network requests. The only HTTP request was one GET to the dashboard running in the container
  (`127.0.0.1:8000/api/setup`).
* Every index and parquet file was opened read-only (`mode=ro`). `lexflow.db` was also opened read-only, to read the
  `ask_bench` rows; `db.connect()` was not used, because it runs migrations.
* No index was built or rebuilt. `ask-search` calls `ensure()`, and every index was already current, so nothing was
  built.
* The check scripts are in this session's scratchpad (`vr_counts.py`, `vr_statutes.py`, `vr_quote.py`,
  `vr_titles.py`, `vr_bench.py`). They were piped into `python -` in the container. The pre-edit `index.py` was
  embedded in `vr_statutes.py` as base64 and loaded as a separate module, so both versions ran side by side on the
  same index files.
* No model-code text is quoted here. 13VAC5-63-80 was compared with the file on disk, but none of its wording is
  copied into this note.

## Verdict

The index is built correctly, matches the parquet files exactly, and leaves the statute index's behaviour unchanged.
The search results, the setup card and the credits all check out.

**One serious problem, which the report does not mention:** the edit to `lexflow/ask/index.py` changes the
AskBench code hash. That makes all 162 stored benchmark rows stale (W1). Fix this before anything else.

## Confirmed

| Claim | Result |
|---|---|
| Tests: `test_regulations_index.py` + `test_ask.py` = 19 passed | **19 passed** (8 + 11) |
| With `test_review_index.py` and `test_credits.py`: 54 passed, 1 skipped | **54 passed, 1 skipped**. The skip is `test_credits.py:424`, "out/ here is not the checkout's own folder". `test_credits.py` alone: 27 passed, 1 skipped |
| `test_product.py::test_remote_schema_covers_only_shared_tables` fails, unrelated | Confirmed. `place_processes` is in `db.SYNCED` but missing from `turso.remote_schema()`. That is the places workstream, not N1 |
| 39 regulations files, 39 indexes, the plan's 7 states among them | Confirmed. The manifest lists 40 regulations files: 39 states plus `federal`. The federal file is not on disk, and `R.FILE` cannot match its name |
| 13 states with no file: AZ CA HI IN LA MA MO NJ NY RI TN TX VT | Confirmed from the manifest (52 lexflow codes minus 39) |
| 851,889 sections; 4,402,307,072 bytes | **Exact.** For every state: rows in force or with no status (counted directly with pyarrow) = `sec` rows = `body` rows = `fts_docsize` rows = `meta.sections` |
| Per-state counts: VA 22,396; DC 22,914 of 27,401; MD 12,773; FL 16,711; IL 55,076; NC 21,314 of 45,826; WA 51,026; MT 12,151 of 50,009; PR 126,853; CO 763 | All exact. MB figures are MiB, for example VA 114,671,616 B = 109.4 |
| Regulations parquet files total 638,731,694 bytes; the statutes card's "2.1 GB" includes the federal file | Confirmed: 638,731,694 + 1,449,364,168 (federal) = 2.09 GB. `run_statutes` loops over state codes only |
| 14 rows with no status kept (VA 1, WA 12, WI 1), each its section's only row | Confirmed. None of the 14 has a `citation_short` or a heading, so `ref` falls back to the number and the heading is synthetic |
| The stamp is `2-regulations1:<size>:<mtime>`; every index is ready | 39/39 ready with the current code |
| The current code reproduces the indexes | `regulations.py` was last saved at 01:43:08 UTC, while the build ran (01:39:33 to 01:46:47). Rebuilding every state's rows in memory with today's `prepare()` gives the same `ref`, heading, `kind`, `citation_short`, `norm_short`, citation, URL and `act_id` for all 851,889 rows (0 mismatches). So that edit changed nothing that was indexed |
| The statute index is unchanged | Old and new `index.py` ran side by side on the 47 real statute indexes. Both report 47/47 ready, with the same stamps and paths. Ten searches (VA, DC, NC, MD, WA, CA, IL, FL) and 13 lookups gave identical results, and so did `by_id`, `neighbours`, `text_of`, `by_ref` and `in_units` on every hit: **0 differences**. No statute index was modified after 2026-10-10 12:48 UTC |
| Shed and deck in VA: 8 hits, 13VAC5-63-80 third, after 13VAC5-63-438 and 9VAC25-151-240 | Confirmed through the CLI |
| Shed + permit + exempt ranks it first; `{title} : "permit" AND (shed)` ranks it first | Both confirmed |
| The same query over the statutes: 0 hits | Confirmed |
| 13VAC5-63-80: index id 5175, 1,931 words, kind `regulation`, official URL `https://law.lis.virginia.gov/admincode/title13/agency5/chapter63/section80/` | Confirmed. The index text equals the parquet's text exactly; there is one row, and it is `in_force` |
| Quotes from 13VAC5-63-80 are word for word | The preamble and items 2, 13 and 14.6 are exact substrings of both the index and the parquet. The Exceptions passage matches word for word, but the file puts line breaks after "Exceptions:" and before "2.", and the quote joins them with spaces |
| The B list is 1,025 words; the items not quoted are as summarised; no item covers new decks | Confirmed. Items 1 (1.1 to 1.9) and 3 to 16 match the summary, including 3 (150 sq ft), 11 (30 ft) and 15 (1,500 sq ft). The only "deck" in the section is "roof decking" (14.6) |
| Headings lose the citation they start with; "COVID-19", "PM-10" and "Appendix C" are kept | Over all 851,889 rows, every cleaned heading is a suffix of the raw one. Only 3 rows lost a word, all OCR-style single tokens ("1Markings" OK, "PURPO8E8" and "1Autoridad" PR), and 17 keep a citation prefix |
| `lookup()` by short citation | `13VAC5-63-80`, `13 Va. Admin. Code § 5-63-80`, `12-A DCMR 105`, `COMAR 09.12.51.04`, `WAC 51-51-003` and `WAC 173-303-830` each resolve to one row |
| No NULL `ref`; duplicate refs: PR 18,899, IL 673, MS 135, NH 112, WY 24, UT 15, NC 14, WV 14 | No NULLs. The figures are extra rows (rows minus distinct refs), and they are exact, but MI and MT are missing (W4) |
| Setup card | Optional, right after `index`, needs `statutes`, params `states` and `force`. Credits: Open US Law (the regulations `used_for`, with the commercial-use note) and SQLite FTS5 |
| `lexflow status` | Shows `[x] 4. Make the state regulations searchable (optional 39/39)` |
| The running dashboard needs a restart | Confirmed. `/api/setup` from the process started at 19:24 UTC lists 15 steps without `regulations` |
| Other agents' `steps.py` edits (CASES_RANK, the run_cases retry) were left alone | Confirmed. Ignoring line endings, the diff from `n1_orig/steps.py` contains only the card, the two new functions and those edits |
| No downloads, network requests, jobs or Ollama | Nothing found that contradicts this. The manifest sizes equal the files on disk |

## Wrong

**W1. Editing `lexflow/ask/index.py` breaks the AskBench freeze and makes every stored benchmark row stale.**

* `bench.version()` hashes `CODE = ("ask/*.py", …)`, and `index.py` is one of those files.
* With the original `index.py`, the hash is `2-1bbcb0aed8c9`. That is the version of all 162 `ask_bench` rows, and
  of `docs/askbench.json`. With the edited file it is `2-e15bddfe239f`.
* Substituting only the original `index.py` bytes reproduces the old hash, so this edit is the only cause.
* `bench.stored()` now returns **0 current rows and 162 excluded as `stale_code`**. The next `lexflow ask-bench` run
  will rewrite `docs/askbench.json` without the earlier arms, unless the whole benchmark is re-run.
* The plan forbids this edit. E9 says the Ask wiring in `lexflow/ask/*` waits for the freeze, entities-contacts D13
  says changes to `lexflow/ask/*` wait until AskBench finishes, and BC §4.1 says the index "belongs in a new module
  … not in `lexflow/ask/*`".
* The report calls the edit "additions only", and that is true for statute behaviour. But it never mentions the
  freeze or the hash.
* **Fix (for the owner to choose):**
  * Restore `index.py` from `n1_orig/index.py`, which brings back `2-1bbcb0aed8c9`, and move the corpus-aware code
    to a new module (for example `lexflow/corpus/index.py`). That module could wrap `index.py` or copy its query
    helpers.
  * Or accept the hash change and re-run AskBench once the freeze ends.

**W2. The DC lookup example describes the synthetic test, not the real file.**

* "In DC both '12-A DCMR 105' and '11-B DCMR 105' resolve, and lookup('105') returns both" holds only for the test
  fixture.
* In the real index, `11-B DCMR 105` returns nothing: subtitle 11-B has 35 rows and no § 105.
* `lookup('dc', '105')` returns **37** rows across DC's titles, not two.
* The mechanism works; the example is wrong.

**W3. "Repealed, reserved, transferred and similar stubs are dropped" is true only where the file marks them so.**

* The filter keeps every row whose `act_status` is `in_force`.
* About 7,522 kept rows have headings that say they are stubs and fewer than 60 words: IL 5,873 (for example
  "Miniatures (Repealed)"), DC 1,536 ("RESERVED", "REPEAL"), VA 62, NC 23, NH 15, MD 6, PA 3, OH 2 and OK 2.
* NC also keeps codifier's notes as `in_force` rows ("The rules in 01 NCAC 41 have been transferred to 15A NCAC 01U
  …").
* This is how the plan specified the filter (§2.3, `act_status` only), so it is a data caveat, not a code bug. A
  heading or text test could drop these rows later.

**W4. The list of states with duplicate refs is incomplete.**

* MI has one, `Mich. Admin. Code R 400.12703`: two identical rows, ids 9325 and 9326.
* MT has one, `Mont. Admin. R. 32.3.105`: two different rules, one of which is headed "32.2.105 …".

**W5. Smaller points.**

* The Exceptions quote is "word for word" but not character for character: the line breaks are flattened.
* `steps.py` changed from CRLF to LF line endings. That makes a plain diff against the old copy show all 740 lines;
  `--strip-trailing-cr` shows the real changes. Which agent caused this could not be determined.

## Missing

* **Rows dropped in addition to stubs.** The filter also drops 38 `not_yet_effective` rows (GA 9, NV 22, NC 7), 2 of
  them in GA with no in-force version of their citation, plus 1,364 `expired` rows. Statute lookups keep future
  versions, ordered after current ones. For regulations, a rule adopted but not yet effective cannot be found. The
  plan allows this ("in_force only"), but the report does not say it.
* **The status-less rows are not documented in detail.** None of the 14 has a short citation or a heading, so their
  headings are synthetic (for example "9 Va. Admin. Code: A.").
* **The freeze.** The report should state that the edited file is under the benchmark hash (W1).
* **The plan's card cost.** §2.1 says the card shows "regulations add 2.1 GB" and needs the same approval. The card
  says about 640 MB for the 39 state files. That figure is the more accurate one, but the plan text was not updated.
* **Ask is not wired yet**, as the report says (E9). Nothing in `retrieve.py` or `plan.py` reads the new indexes, so
  the Ask answer for "deck or shed" is still "not found" until that work is done after the freeze.

## Numbers

| Measure | Value |
|---|---|
| Regulations files on disk / indexes / ready | 39 / 39 / 39 |
| Parquet rows / kept (in force or no status) / indexed | 1,041,580 / 851,889 / 851,889 |
| Status of the dropped rows | superseded 56,288; repealed 80,025; reserved 28,037; revoked 12,644; transferred 8,964; expired 1,364; rescinded 844; renumbered 765; deleted 550; recodified 98; not_yet_effective 38; relocated 37; rejected 34; removed, unconstitutional, terminated 1 each |
| Index bytes | 4,402,307,072 (4.10 GiB) |
| Statute indexes ready (old code / new code) | 47/47 / 47/47; 0 differences in 10 searches and 13 lookups |
| AskBench version (original `index.py` / edited) | `2-1bbcb0aed8c9` / `2-e15bddfe239f`; 162 rows, all now `stale_code` |
| Tests | 19 passed (required); 54 passed, 1 skipped (extended); `test_product.py`: 1 unrelated failure |
