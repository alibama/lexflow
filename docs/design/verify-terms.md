# Verification of the "terms" work (lexflow/law/terms.py, terms-wikibase.md)

Date: 2026-10-10. Adversarial re-check. Nothing was edited except this note, and nothing was written to any wiki.

- **Re-run:** `tests/test_terms.py` and `scripts/terms_eval.py` (`--part terms -v`, `--part link --nested`, and `--part link --embed` on a copy of the private cache: 0 new embedding calls).
- **Extra checks:** extraction on 54 held-out definition sections from the index (10 states, none in gold), and 22 survey pairs re-read on Wikidata.
- **Reads:** 6 on Wikidata and 1 on Lexipedia, at most 1 per second.

## Confirmed

- **Tests:** 20 passed.
- **Definitions, gold:** every reported number reproduces. 128 gold, 103 predicted, 96 matched: P 0.932, R 0.750; with scope, P 0.883, R 0.711. Span IoU 0.849, category 91/96, gold C scope paths 28/28.
- **Classifier, out of fold:** every reported number reproduces.
  - Pair AUC 0.95, log loss 0.174.
  - P≥0.95 threshold 0.9755: 3 linked, 3 correct. Nested estimate: 2 linked, 1 correct.
  - P≥0.90 threshold 0.6424: 81 linked, 73 exact. P≥0.85: 95 linked, 81 exact, 1 a different thing.
  - Rule baseline: 106 linked, 80 correct, 7 a different thing. Embedding variant: 87 linked, 79 exact.
  - "P31 is a statute": wrong in 34 of 35 pairs (the other is related).
- **Incorporator, extractor:** all four sections give `incorporator / acts_as / heading+text / role`, scoped to the enclosing chapter: FL 607.0201, VA 13.1-618, NC 55-2-01, DC 29-302.01. § 607.0101 names chapter 607 the Florida Business Corporation Act. § 607.01401 yields 78 terms, none of them *incorporator*.
- **Incorporator, classifier:** Q140403634 gets p 0.145 from the shipped model (0.157 out of fold), so it is never linked.
- **Incorporator, Wikidata search:**
  - `wbsearchentities "incorporator"` returns only Q140403634 (a PropBank proto-agent) and Q99348672 (an article).
  - The lexeme search returns nothing.
  - A full-text search finds no item for the corporate role. It does find Q3178478, *incorporation (business)*, a possible reviewed *related match*.
- **Lexipedia:**
  - Q168, Q512, Q334 and Q147 carry exactly P25, P5, P22, P15 and P23.
  - Their keys `lexflow:statute:{fl,va,nc,dc}:…` equal the index refs.
  - P26 and P27 do not exist. Q775 is `lexflow:role:fl:business:organizer`.
- **Wikidata labels:** in all 22 spot-checked pairs, the survey's label, description, P31/P279 and sitelink count match live Wikidata. The five SKOS mapping-relation items and P4390 are as stated.

## Wrong or overstated

1. **Precision ≥ 0.95 is not established.**
   - The 0.9755 threshold was picked on the same out-of-fold scores. It sits 0.0008 above a wrong link: *scofflaw* → Q7434243, out-of-fold p 0.9747.
   - 3/3 has a 95% Clopper–Pearson lower bound of 0.29. The nested estimate is 1/2.
   - The docstring's "threshold defaults to … precision >= 0.95" should say "tuned on the survey; not demonstrated".
   - The defensible operating point is review-only at 0.6424: 73/81 = 0.90, with a lower bound of 0.82.
2. **The incorporator non-link is hand-coded, not learned.**
   - `_JUNK` and `_CLASS_NEG` contain `prototypical|proto-agent|PropBank|predicate|semantic role`. Only 5 survey pairs match those words, all of them wrong, incorporator's among them.
   - With those tokens removed, Q140403634's out-of-fold p is **0.80**. It would then be linked at the review threshold.
   - Leave-one-term-out does not measure leakage from feature design. The rule is a reasonable one (PropBank items are a large family), but call it a rule.
3. **"Never a different thing" at P≥0.90 depends on generous labels.** The survey's judgements were made by the same agent that built the classifier.
   - *Custodian of records* → Q5196342 (p 0.905) is the 18 U.S.C. § 2257 records keeper. The term itself comes from public-records models. By the doc's own rule ("a specific statute for a generic term", the reason the federal APA is *wrong*), this is a different thing.
   - *Restitution* → Q1156800 is the civil gains-based remedy. The term is criminal victim restitution, so this is arguably a different thing too.
   - Corrected count: **81 linked, 73 exact, 7 neighbours, 1 different thing (possibly 2).**
4. **A doc error in §7.4.** Articles of incorporation, "p = 0.38, so it goes to review", is wrong: 0.38 is below the 0.6424 review threshold, so nothing is queued. Out of fold, the top candidate for that term is Q3497659 *articles of association* (broader, p 0.42), not the exact item Q17013292.
5. **The extractor generalises worse than the gold numbers suggest.** Gold is the development set. On 54 held-out sections (122 predicted terms):
   - Term precision looked high when I read them.
   - Plural "The terms "A" and "B" **include** …" is never matched, because bare `include` is missing from `_VERB`. Fla. Stat. § 627.652 loses 7 terms this way.
   - 21 of 122 scopes are `None`: `this subchapter`, NC `this Article`, `this Part`, FL `this act`. On gold, none were.
   - 41 terms of Md. Commercial Law § 1-201 (the UCC general definitions) get scope "this section". The right scope is the Maryland UCC.
   - Correct resolved scope: about 59/122 terms, or 22 of the 35 sections that have terms.
   - Load rule: "100% on gold" for `includes`, `excludes` and `acts_as` rests on 1 example each.

## Duplicates on re-runs

- **Terms:** the key is derived, never counted, so it is stable. In 136 sections (gold plus held-out) there were no label+description clashes.
- **Same-key merges:** 9 cases put two or more Terms on one key, always the same term and scope with a different kind. Md. Commercial Law § 1-201 "Security interest" is defined three ways. These are not duplicates. But `Loader.entity()` replaces an item's statements wholesale, so a loader that calls it once per Term keeps only the last definition. Group by key first.
- **No P25 lookup exists.** The doc says "or through a P25 search when that table is lost", but no such code exists. The loader recovers an item only from a label-conflict error (`owner()`), which needs label and description to be unchanged.
  - The proposed label `{term} ({unit name})` uses a unit name that the path cannot supply. So a renamed unit plus a lost `wikibase_items` table creates a duplicate item.
  - Add a `haswbstatement:P25=<key>` lookup before any create.
- **Keys inherit `norm_term`'s crude singulariser.** "gases"→"gase", "statuses"→"statuse", and "damages"→"damage" (so `concept_key` merges two concepts). Changing `norm_term` later changes keys, which means duplicates. Freeze or version `slug()`.
- **Other gaps:**
  - `concept_key()` cannot produce the homonym suffix the doc describes. Concept keys must come from the stored review table.
  - Synonym pairs ("Corporation" or "domestic corporation") become two term items with no alias rule.
  - `retire_drafts` does skip term, concept and unit keys, as the doc says.

## Re-check of the fixes (2026-10-10)

Adversarial re-check of the fixer's revision. Nothing was edited except this section; no wiki, Wikidata or network writes. Everything ran in `lexflow-app-1`.

- **Re-run:** `tests/test_terms.py`, 38 passed (62 with `tests/test_links.py`). `terms_eval.py --part terms` is unchanged (P 0.932, R 0.750; with scope 0.883 / 0.711). `--part heldout` gives 137/148 terms and 140/140 rows.
- **Before numbers:** the original `terms.py` (the fixer's scratch copy) reproduces 119/148 terms, 49/122 rows right, 17/35 sections right and 21 `None` scopes. `--part link --nested --print-model` reproduces every classifier number, and the printed model equals `LINK_MODEL`.
- **Extra checks:**
  - A fresh sample (seed 14), read by me.
  - The original and current extractors compared on 600 random sections, 60 per state.
  - 600 N.C. sections that have dash items.
  - `DECLARE` matches on 4,000 sections.

### Fixed

1. **Precision ≥ 0.95.** No 0.95 threshold remains. `link()` defaults to `review_threshold` 0.7607 and the model is review-only. Out of fold: 64 suggested, 58 exact, lower bound 0.807. Nested: 59/67. The 0.95 diagnostic links 2 terms (lower bound 0.158; nested 1 of 2).
2. **PropBank tokens.** They are gone from `_JUNK` and `_CLASS_NEG`, and no other rule names them. The incorporator item now scores 0.727 out of fold and 0.688 shipped. The L2 weight of 10 is the out-of-fold log-loss minimum.
3. **Disputed labels.** `REJUDGED` gives 4 neighbours, 1 different thing and 1 possible, as now stated.
4. **§7.4.** Q17013292 scores 0.303 shipped (0.273 out of fold). Q3497659 scores 0.418 shipped (0.474 out of fold).
5. **Extractor.**
   - § 627.652 now gives 9 terms.
   - `None` scopes fell from 21 to 4, and those 4 are lists of sections.
   - § 1-201 is scoped to the Maryland UCC. The UCC short titles in `NAMED_UNITS` match their sections (Fla. § 671.101, Va. § 8.1A-101, Md. § 1-101(a), 810 ILCS 5/1-101).
   - The load rule now gives its counts.
6. **Duplicates.**
   - `group_by_key` exists, and the doc states that no P25 lookup exists.
   - The label now uses the citation, and the slug no longer folds plurals. It matches `links.py`'s key formula, so `public-records` is now the same key in both modules.
   - `concept_key` takes a sense suffix, and `alternatives` covers "or" lists.
7. **Seed 14 (untouched by the fixer).** 86 of 93 rows are right, counting anchored units as right the way the fixer did.
   - Wrong: D.C. § 1-204.24f, "For purposes of this part —" (a dash, not a colon), gets the chapter (3 rows). N.C. § 115C-563, "this Part or Parts 1 and 2 of this Article", gets only the Part (2 rows).
   - 1 false heading term: "declaration of policy".
   - 1 unclear.
   - Missed terms: Va. § 18.2-486 (5 unquoted words), Fla. § 90.401 and N.Y. Educ. § 8201.

### Not fixed, or new

1. **DEFECT: N.C. dash items outside a definitions list.**
   - `DASH_DEF` accepts any "(x) Caption. - …" once any lead-in appears earlier in the section, because `lead_at()` never ends.
   - Of 2,427 dash-item terms in 600 N.C. sections, 747 sit outside a definitions heading. In a sample of 70 of those, at least 13 are subsection captions, about 1 in 5. Examples: § 14-150.3 "Punishment", "Merger" and "Civil Remedies"; § 105-130.46 "Credit", "Allocation" and "Carryforward"; § 7B-536 "Coordinators Privilege"; § 136-44.3A "Report".
   - All of them are kind `means` with a `path` scope, so they pass the doc's §6 load rule.
   - The claim "only inside a definitions list" is overstated, and no test covers captions after a lead-in.
2. **DEFECT (it predates the fix; `_LIST` and `_QT` were not changed): exponential backtracking in `DEF_A`/`_LIST`.**
   - In a list of straight-quoted items with no definition verb, the optional `\s*[,;]?\s*…\s*` separators can split each space several ways, so a failed match retries an exponential number of splits.
   - A synthetic list takes 0.12 s at 12 items, 0.39 s at 14 and 1.6 s at 16.
   - N.C. Gen. Stat. § 14-107.1 (9 KB, 18 quoted dishonor reasons) does not finish in 20 s, and a scan stalled on it for minutes.
   - A loader running `definitions()` over every section would hang.
   - A fix to try: make the separator unambiguous, e.g. `\s*(?:[,;]\s*)?(?:(?:or|and|and/or)\s+)?`. On a scratch regex, not the file, § 14-107.1 then takes 0.001 s, 40 items take 0.013 s, and four sample lists match the same way.
3. **OVERSTATED: "incorporator … is not queued".**
   - `review_threshold` 0.7607 is the score of the term just above the incorporator. The incorporator (0.727, wrong) is the next term down, and adding it drops precision to 0.892 < 0.90.
   - So the threshold is placed by the incorporator's own label. Chosen without it (the nested run), the inner threshold is 0.679 and the PropBank item is queued.
   - The out-of-fold margin is 0.034, not 0.07. Harm is limited, because nothing is written without review, but "general features hold it down" should say that the reviewer, not the score, keeps it out.
4. **OVERSTATED: "improving the matcher never moves a key".**
   - `slug` is frozen, but `_singular` still makes the term strings of heading, `acts_as` and "defined as" terms, and those strings become keys.
   - The fix's own `_IRREGULAR` change moved such keys: heading "Bonuses." gave `…:bonuse` before and `…:bonus` now, and "Analyses." gave `analyse` and now `analysis`.
   - Nothing is published yet, so freeze that singulariser too.
5. **DEFECT (minor): anchored units under the wrong parent.**
   - `_INSIDE` treats Maryland's "Article" (a whole code) as a container. Md. Gen. Prov. § 5-857, "In this part", becomes `MD Code / Article ggp / Part containing § 5-857`, which drops Title 5 / Subtitle 8.
   - Illinois has no "act" level. 105 ILCS 5/34-1.1, "this Article", becomes `Illinois Code / Chapter 105 / Article containing …`, without Act 5.
   - Va. § 15.2-6602, "this act", becomes `Virginia Code / Act containing …`. The original code gave chapter 66, which is right.
6. **Compound scopes are cut to their first unit.**
   - "this section and to ss. 605.1006 and …" (Fla. § 605.1061);
   - "this Article and Articles 21A and 21B" (N.C. § 143-212);
   - "throughout this section and RCW 24.03A.715 through …";
   - "this chapter and Chapter 10 (…) of this title".
7. **Minor.**
   - '"Woodland" means woodland as defined in …' now gives two Terms, `means` and `by_reference`, on one key.
   - The rule baseline still counts 8 different things from the survey labels; with `REJUDGED` (custodian) it is 9.
   - "140 of 140" includes 29 anchored and 4 `None` rows that are right by the labelling convention.
8. **Fixes not pinned by tests:**
   - "When used in";
   - Maryland "In this subtitle the following words have the meanings indicated";
   - "the following terms mean:";
   - the section-range colon;
   - "Chapter 10 (…) of this title";
   - "Woodland";
   - the "Definition and purposes." heading;
   - N.C. "(2) Record. - …".

   I probed each one, and all behave as claimed.

## Re-check 2 (2026-10-10)

Adversarial re-check of the second revision. Nothing was edited except this section; no wiki, Wikidata or network writes. Everything ran in `lexflow-app-1`, read-only. "Round 1" below means the first revision's `terms.py`, the fixer's scratch copy, which has `NAMED_UNITS` and `review_threshold` 0.7607.

- **Re-run:** `tests/test_terms.py` gives 66 passed. With `tests/test_links.py`: 90 passed, 4 skipped.
- **Eval:** `terms_eval.py --part terms` is unchanged (P 0.932, R 0.750; with scope 0.883 / 0.711).
  - `--part heldout`: 137/148 terms, 140/140 rows (29 anchored, 4 with no unit).
  - `--part link --nested --print-model`: every number in the doc and the docstrings reproduces, and the printed model equals `LINK_MODEL`.
  - The weights equal round 1's; only `review_threshold` moved (0.7607 → 0.5).
- **Extra checks:**
  - My own sample: 800 N.C. dash sections (seed 77), round 1 against now. I read 90 kept dash terms and 60 dropped ones.
  - All 3,395 N.C. and 288 D.C. dash sections, scanned for lost terms.
  - Compound and cut scopes in up to 400 `title:definitions` sections per state.
  - Fresh samples with seeds 12, 13 and 14, round 1 against now.
  - Mutation checks on the new tests (each fix removed in a scratch copy).
  - Synthetic worst cases for every list-like pattern, and the 3 longest sections per state.

### Fixed

1. **Backtracking.** All of § 14-107.1 now takes 0.01 s. Lists of 300 quoted items take 0.17–0.38 s. A 2,000-part compound or section list takes under 0.1 s. The slowest of the 30 longest sections takes 3.9 s (Fla. § 212.08). The child-process test pins it: with the old separator, the test's list takes 0.15 s at 14 items and grows exponentially.
2. **Dash captions.**
   - The examples are fixed: the captions of §§ 14-150.3, 105-130.46 and 136-44.3A, and § 7B-536's "Coordinators Privilege", are gone.
   - Kept items: I read 45 inside lead-in lists in sections whose heading is not about definitions, 25 under definitions-only headings and 20 in lists under definitions headings. 0 of the 90 are captions.
   - Dropped items: 60 of 190 read, all captions. One borderline case, § 105-277.15 "Deferred Taxes", is a recall loss, not a false term.
   - Across all 3,395 N.C. sections, one caption still passes (item 4 below).
3. **Review threshold.** The fixed 0.5 gives 91 suggested and 77 exact (lower bound 0.755), as stated. The incorporator is queued (0.688 shipped). The docs now say that the reviewer, not the score, keeps it out. The federal APA scores 0.658 alone and 0.251 among its real search hits. Accepted as a deliberate tradeoff.
4. **Keys.** Heading, `acts_as` and "defined as" terms go through `key_singular` only. Its tables equal round 1's (and today's matcher tables), so freezing them moved no key. The checksum and the monkeypatch test both pin it. No other path singularises a term string.
5. **Anchored units.** On the index:
   - Md. Gen. Prov. § 5-857 → `… / Title 5 / Subtitle 8 / Part containing § 5-857`;
   - 105 ILCS 5/34-1.1 → `… / Act 5 / Article containing …`;
   - Va. § 15.2-6602 → `… / Chapter 66 / Act containing …`.

   I accept the "this act" judgement call (anchored and held for review). Removing the Illinois "act" container fails its test.
6. **Compound scopes.** Fla. § 605.1061, N.C. §§ 143-212 and 115C-563, and RCW 24.03A.710 are right on the index. The definitions scan found 23 compound scopes, all real compounds, with the parts split correctly.
7. **Smaller items.**
   - Woodland: N.C. § 106-941 and N.Y. Penal § 179.00 now give one `by_reference` Term each.
   - The rule baseline gives 107 linked, 80 correct and 8 / 9 different things.
   - The held-out report states its 29 + 4 convention rows.
   - The seed-14 wrongs are fixed (D.C. § 1-204.24f, N.C. § 115C-563, "Declaration of policy."). On seeds 12–14, those are the only changes from round 1, plus two by-reference merges.
   - Mutation pins these fixes: the Maryland "In this subtitle", the section-range colon, "Chapter 10 (…) of this title", Woodland, "(2) Record.", "Declaration of policy.", the dash lead-in, the caption lead-in, the list end, "listed meaning", the definitions-only heading and the self-quoting caption.

### Not fixed, or new

1. **NEW REGRESSION (recall): a dash item that quotes its own term is skipped even when the quoted form is never extracted.**
   - `definitions()` drops "(1) Adjustment. - "Adjustment" is an act …" as a duplicate. But "is" is no definition verb, so no other rule finds the term.
   - N.C. Gen. Stat. § 81A-9 ("Definitions.") loses all 22 of its terms. § 20-286 loses "Sell" ("The terms "sell," … are synonymous"). Round 1 found all 23.
   - These are the only losses in all 3,395 N.C. and 288 D.C. dash sections.
   - The fixer's own comparison has the same 23 among its "52 duplicates of the quoted term". So the §2.3 table is wrong: 29 are duplicates and 23 are lost terms. And "a caption that quotes its own term gives one Term" gives none in these sections.
   - No test covers it. The conservative fix: skip the dash item only when a Term with that normalised term was found at the quoted position.
2. **OVERSTATED: three "unpinned fixes now tested" are still unpinned.**
   - With "When used in" removed from `_INTRO`, or the "the following terms mean:" exception removed, `test_pinned_lead_ins_and_forms` still passes. Both rows carry a "Definitions." heading, and its fallback gives the same scope words ("this chapter") and unit.
   - With the `startswith("definition")` heading filter removed, the "Definition and purposes." check still passes, because the test text never mentions the heading.
   - These need rows with no definitions heading and a text that mentions the heading.
3. **Minor: a letter "(i)" is read as a roman numeral, so a list does not end at it.** N.C. § 58-68-60 has "(h) Other Definitions. - As used in this section:" and then "(i) Rights of Replacement Coverage Upon Termination. - …", which becomes a `means` term with a `path` scope. This is 1 caption in 3,395 sections. It is unquoted, so the load rule holds it for review. "(v)" and "(x)" have the same ambiguity.
4. **Minor, latent: an item's inner lead-in ends a definitions-heading list.**
   - Case: a section with a definitions-only heading and no top-level lead-in, where one item says "As used in this subdivision, the following terms apply:".
   - That lead-in's list ends at the next item. Every later dash item is then outside any list and after a lead-in, so it is dropped. A synthetic case loses two items that round 1 kept.
   - No instance was found in the 3,395 N.C. sections.
5. **Minor, latent: some compound scopes are still cut to their first unit.**
   - Four or more comma parts: "this chapter, Chapter 4, Chapter 5, and Chapter 6 of this title" gives "this chapter" with basis `path`, while three parts work.
   - Real lists of this shape exist (Fla. § 253.025, Cal. RTC § 17021.7), but none governs a definition in the index.
   - Number words: N.Y. LLC § 1106 ("sections eleven hundred seven and eleven hundred eight").
   - RCW footnote asterisks: RCW 43.216.157.
6. **Minor:**
   - "Statement of purpose and authorization." (N.C. § 106-1041) still gives a heading term. Heading terms are held for review.
   - Predating this round: "means-tested" is read as the verb *means*. N.C. § 108A-25.3 gives a false unquoted term, "Public assistance program. - Any", which is held for review.
7. **Report only (the doc is right):** the fix report's "8 seen" moved keys is wrong. Dropping the wrong pinpoint moves 22 keys: 4 in § 168A-3 and 18 in § 131E-176, matching the doc's 22 terms. Nothing is published, so no alias is needed. I accept that judgement call.

## Re-check 3 (2026-10-11)

Adversarial re-check of the third revision. Nothing was edited except this section. No wiki, Wikidata or network writes were made. Everything ran in `lexflow-app-1`, read-only, with scratch files in the container's `/tmp/v3terms`.

"Round 2" below means the fixer's scratch copy of the second revision (`/tmp/agent_terms_r2.py`: `REVIEW_THRESHOLD` 0.5, none of the new rules). It reproduces every Re-check 2 failure on the index. `scripts/terms_eval.py` was not run: no benchmarks this round.

- **Re-run:** `tests/test_terms.py` gives 75 passed. With `tests/test_links.py` and `tests/test_design_privacy.py`: 120 passed, 8 skipped, 1 failed. The failure is in `verify-lab.md`, another area's note; no terms file is involved.
- **Extra checks, round 2 against now:**
  - all 3,372 N.C. and 288 D.C. sections with a "(x) Caption. -" item;
  - a fresh sample of 4,000 sections: 100 random sections per state (seed 47), and up to 300 per state from a full-text search for "as used in", "for purposes of" or "following definitions";
  - every section, in every state, that writes a section number in words and quotes a term (2,901 in N.Y., 16 elsewhere);
  - every section with a comma run after "this chapter," (or similar), an RCW footnote asterisk, or a definition verb followed by a hyphen;
  - every field of every Term in the 82 gold and 54 held-out sections;
  - the fixer's 19 mutations plus 3 of mine, in a scratch copy;
  - the 3 longest sections per state, and the fixer's synthetic worst cases;
  - synthetic probes of each new rule.

### Fixed

1. **The regression (Re-check 2, item 1).**
   - N.C. § 81A-9 has its 22 terms again, and § 20-286 has its "Sell". "(3) Mayor. — The term “Mayor” means" still gives one Term.
   - On all the dash sections the result is exactly the fixer's: 22 N.C. sections change and no D.C. section does. 23 terms are added, those 23 and nothing else. 20 are removed: the § 58-68-60 caption, the § 108A-25.3 false term, and the 18 generic heading terms the doc lists.
   - The restored terms start at the caption, so the §6 rule holds them for review.
2. **Pins (item 2).** A test now fails in each of three cases: "When used in" removed, the "the following terms mean:" exception removed, or the `startswith("definition")` filter removed. All 19 of the fixer's mutations fail at least one test, and the unmutated copy passes 75.
3. **The letter "(i)" (item 3).** § 58-68-60's "(i) Rights of Replacement Coverage …" is gone, and the roman-list test holds. The rule changes nothing else in the dash sections and adds no measurable time.
4. **The inner lead-in (item 4).** The reported case is fixed. An "As used in this subdivision, …:" inside a dash item no longer ends a definitions-only heading's list. Later dash items take the heading's unit, and a top-level lead-in still ends the list. New items 3 to 5 give the rule's limits.
5. **Compound scopes (item 5): the comma and asterisk parts.**
   - Comma runs: of all sections with a "this X, Y …," run, 3 change, and all 3 are now right: Cal. Corp. § 5013 and Cal. WIC §§ 14065 and 14066. "this chapter, chapter 2, chapter 3, the rules …" stays one unit.
   - Asterisks: 11 RCW sections change, all right. For example, RCW 48.05.430's 20 terms now have "RCW 48.05.430 through * 48.05.490".
   - N.Y. LLC § 1106 and RCW 43.216.157 are right on the index. The number-word part is not fixed (new item 1).
6. **False terms (item 6).**
   - N.C. § 106-1041 and § 108A-25.3 give no false term.
   - Every heading term the new heading rule removes in my scans is generic: the 18 N.C. ones, 13 in N.Y., Va. § 55.1-1209.1's "policies and procedures", 805 ILCS 180/55-1 and 110 ILCS 685/30-45.
   - The "means-tested" fix is too broad (new item 2).
7. **Claims checked.**
   - Gold and held-out: every field of all 253 Terms in the 136 sections is identical, so §2.1 and §2.2 carry over.
   - The fixer's 9 sample changes are all right. The §2.3 table adds up (29 + 23 + 321 = 373).
   - Speed: the slowest of the 30 longest sections takes 2.6 s (Fla. § 212.08; 2.5 s in round 2). 2,000 comma parts take 0.17 s, 800 number words 0.01 s, and 2,000 asterisked numbers 0.08 s.

### Not fixed, or new

1. **NEW REGRESSION (scope): section numbers written in words.** The fixer's samples held almost no N.Y. sections of this kind. Of the 2,901 N.Y. sections that write a section number in words and quote a term, 39 change:
   - 10 sections (48 rows) are now right, e.g. N.Y. CVP § 5241, GMU § 810 and LLC § 1106;
   - 13 sections lose only a generic heading term;
   - 16 sections (**220 rows**) now carry wrong scope words. In round 2, 65 of these rows had the right unit, with basis `path`.

   The causes:
   - **A letter suffix cuts the number.** `_NUMWORD` refuses a following hyphen, so "section three hundred forty-six-a" is read as "section three hundred", which is another section. Seen in N.Y. EDN §§ 341-A and 2218, GMU § 239-L, LAB § 212-C, PML § 1367 (31 terms), RPP § 339-E and TAX § 501, where "five hundred three-b" gives "five hundred".
   - **A part loses its "of section … of the X law".** EDN § 3602's "this paragraph and subdivision thirty-nine of section sixteen hundred eighty of the public authorities law" gives "this paragraph and subdivision thirty-nine" (66 terms). The same happens in EDN § 3621 (16 terms) and JUD § 753-A.
   - **An item-internal lead-in now governs every later quoted term.** In PBH § 4900 and ISC § 4900, item (b) "Clinical peer reviewer" contains "for purposes of section four thousand nine hundred four and title two of this article:". That is now a lead-in. `lead_at` never ends for a quoted definition, so the 32 and 33 later rows move from "this article" (right, `path`) to that compound.
   - **A mid-sentence "in section …" on a hard-wrapped line is read as a lead-in.** TAX § 1351: 'a unit, as defined\nin section three hundred thirty-nine-e of the real property law'. TAX § 171-V: 'as defined\nin section five hundred one-a …, and the term "past-due tax liabilities" means'. Digits already had this hazard, but N.Y. writes its section numbers in words.
   - **"and of this section" is dropped.** PVH §§ 47-A and 47-B (10 terms): "For the purposes of section forty-seven and of this section:" gives "section forty-seven". Round 2 at least kept the section.

   All of these are `compound` or have no unit, so they are held for review and nothing wrong loads. But the scope words are wrong, and 65 right `path` rows are lost.

   The conservative choice is to read number words only where the reading is complete:
   - accept a letter suffix ("-a", "-eeeee");
   - read or refuse a trailing "of section …" or "of the … law";
   - accept "and of this section";
   - do not let a lead-in inside a definition item pass to later quoted items;
   - do not read a lower-case "in" that continues a sentence on a wrapped line as a lead-in.

   Failing that, take number words out again. The tests need the § 4900 layout and a suffixed number.
2. **NEW REGRESSION (recall): `(?!-)` after `_VERB`.**
   - It also blocks the federal form '"farming purposes" means-' and '"adjusted value" means--'.
   - N.Y. TAX § 999-A loses 8 terms (9 rows): adjusted value, farming purposes, timber operations, replaced property, distribution right, term interest, applicable restriction and interest in a closely held business. "qualified interest" becomes a `contents` term.
   - It is the only section in the index that changes.
   - Fix: refuse only a hyphen followed by a letter (`(?!-[A-Za-z])`), and pin it with § 999-A's layout. `test_means_tested_is_no_definition_verb` would still pass.
3. **NEW (latent): a caption that is itself read as a term makes the lead-in after it "inner".**
   - Example, under a "Definitions." heading: "(a) Interpretation. - In this Article:\n(1) Owner. - …\n(b) Inspections. - The officer may inspect …". "Interpretation" is read as an item, so the lead-in counts as inside it. The heading's list then never ends, and "Inspections" and "Notices to owners" become terms. Round 2 dropped them.
   - It needs a caption that no filter drops, followed directly by a lead-in that `_DASH_NOT` does not catch ("In this …", "The definitions in this section apply …").
   - No instance exists in the 3,372 N.C. or 288 D.C. dash sections.
   - Conservative fix: a lead-in that starts right after an item's caption dash belongs to the caption, not to an inner list.
4. **Gap (latent, the same in round 2): the inner rule misses items that quote their own term.**
   - Cases: '(1) Adjustment. - "Adjustment" means … As used in this subdivision, …:' and '(1) Mayor. — The term “Mayor” means … For purposes of this paragraph, …:'. Both still end the heading's list, so the later items are dropped.
   - The dash item is skipped, and the quoted Term starts more than 12 characters after the enumerator, so the item is never registered.
   - So the docstring's "not counting one inside an earlier definition item" is overstated.
5. **OVERSTATED (§2.4): "The items after it take the heading's scope, not the inner "this subdivision"".**
   - That holds for dash items only. A quoted item after an inner lead-in still takes the inner scope, with its own pinpoint: '(2) "Employer" means …' after item (1)'s "As used in this subdivision" gets "this subdivision", (2).
   - It predates this round. The § 4900 case in new item 1 is the same mechanism at scale.
6. **OVERSTATED: number words "without an "and" inside a number"** (module docstring; §2.4 says "Only numbers without an "and" inside are read"). "sections one hundred and five through one hundred and ten" is kept whole and read as a list, with no unit either way. The real limits are those in new item 1.
7. **Test gaps:** two of my mutations survive all 75 tests:
   - the letter rule ignoring the parenthesis style (`labs[0][1] == paren`);
   - quoted definition items no longer pre-registered in `item_at`, so the case '(2) "Agency" means … As used in this subdivision …' under a definitions-only heading is untested.
8. **Recall (predates; not in earlier notes): a caption written as a quoted term is never read.**
   - N.C.: 130 of 147 items of the form '(2) "Institution". -' in 30 sections, e.g. § 116-15, and § 58-68-60's "Church plan".
   - D.C.: all 5 in § 24-1102 ('(A) “Accused delinquent” —').
   - The fixer's lower-case "b." items are a further case.
