# Defined terms and roles in Lexipedia's Wikibase: a data model

Status: proposal, 2026-10-10, revised after the verification in `docs/design/verify-terms.md`, again after its re-check (§2.3), and a third time after its second re-check (§2.4). Nothing has been written to lexipedia.wikibase.cloud or Wikidata. Creating the classes and properties below is a wiki write, so it waits for the user's go-ahead.

Inputs:

- the codebase map (`docs/design/links-codebase-map.md`, §2.2, §3 and §4.2);
- the Wikidata survey (`fixtures/xref/wikidata_terms.json`: 155 terms, 150 of them with candidates, 714 hand-judged candidates). The judgements were made by the same agent that built the classifier, and two of them are disputed (§5);
- the gold terms in `fixtures/xref/gold_{a,b,c}.json`;
- the verifier's 54 held-out definitions sections, listed with hand-read terms and scopes in `scripts/terms_eval.py` (`HELD_OUT`);
- the extractor and the review-only classifier in `lexflow/law/terms.py`, scored by `scripts/terms_eval.py`.

Live reads on 2026-10-10 found Q168 unchanged. Its claims are P25 `lexflow:statute:fl:607.0201`, P5 → Q10, P22, P15 → Q33 and P23. No property above P25 exists.

---

## 1. Key points

- **A term is a thing a section defines for a scope, not a string.** *Incorporator* is defined by Fla. Stat. § 607.0201 for chapter 607, the Florida Business Corporation Act. It is not defined by § 607.01401, the chapter's definitions section. The same sentence, inherited from MBCA § 2.01, defines it in four codes, each for its own chapter:
  - Fla. Stat. § 607.0201 (Q168)
  - Va. Code § 13.1-618 (Q512)
  - N.C.G.S. § 55-2-01 (Q334)
  - D.C. Code § 29-302.01 (Q147)

  So the model has three levels:
  1. A **defined term**: one jurisdiction's definition, keyed by its section.
  2. A **concept**: shared across jurisdictions, minted on review.
  3. The existing **process role** (`lexflow:role:…`): it points at the term its actor plays.
- **Wikidata links are SKOS mappings that a person has reviewed.**
  - `P8 exact match` exists already. Add `broad match`, `narrow match`, `close match` and `related match`, the same way.
  - Every mapping carries `match probability` and `determination method`.
  - The classifier only suggests. Nothing is written until a person accepts a suggestion. No threshold has been shown to make unreviewed exact matches safe: the 0.95-precision target links 2 survey terms out of fold, with a 95% lower bound of 0.16.
  - The review queue holds suggestions with p ≥ `review_threshold`, 0.5 (`terms.REVIEW_THRESHOLD`). That is the model's even-odds point, a convention, not a value searched for on the survey's scores. Out of fold it suggests 91 terms, 77 exact (precision 0.85, 95% lower bound 0.76). The other 14 are 11 neighbouring concepts, 2 different things and 1 that possibly is (§5).
  - The earlier threshold, 0.7607, was the lowest at which out-of-fold precision reached 0.90. The next term below it is the PropBank *incorporator* (0.727, wrong), so that one term's label placed it. It is now a diagnostic only.
- **Incorporator gets no Wikidata link.** Its only exact-label hit, Q140403634, is a PropBank semantic role for the verb *mainstream.01*. No cue list names PropBank any more. The general features score it 0.69 (0.73 out of fold), above the review threshold, so it is queued and the reviewer rejects it: the reviewer, not the score, keeps it out. Lexipedia's own concept item becomes the addressable identifier for the corporate-law role. Q3178478, *incorporation (business)*, is a possible reviewed `related match`.
- **Keys are derived, never counted.**
  - The term key is the statute key with `statute` replaced by `term`, plus the term's slug: `lexflow:term:fl:607.0201:incorporator`.
  - The slug is frozen (`terms.KEY_VERSION = 1`): lower case, other characters → `-`, and no plural folding. "gases" stays `gases`, and `damages` never merges with `damage`.
  - The heading "Incorporators." and the text's "incorporator or incorporators" give one key because the extractor writes both in the singular, not because the slug folds plurals. It does that with `terms.key_singular`, a frozen copy of the singulariser's tables, never with the matcher's `_singular`. So improving the matcher's normalisation (`norm_term`) moves no key.
  - A key still moves when the extractor captures other words for a term, or reads another sub-section pinpoint. This revision moved the keys of terms whose scope was misread as an earlier item's "this subdivision": `lexflow:term:nc:168A-3:undue-hardship@11` is now `…:undue-hardship`. Nothing has been published under any term key, so no old key is kept. Once a term item is published, a key that moves keeps its old key as a second P25 value.
  - A re-run finds an existing item through the `wikibase_items` table only. No lookup by P25 exists yet. A loader must add one (`haswbstatement:P25=<key>`, if the wiki indexes string statements, else a query on P25) and run it before any create. Otherwise a lost table plus a changed label creates a duplicate.

## 2. What the extractor gives (measured)

`definitions(state, row)` returns `Term(term, definition_span, scope_unit, kind, start, end, scope, scope_pinpoint, term_start, source, category, defined_in, scope_basis, alternatives, scope_parts)`.

### 2.1 Gold (the development set; unchanged by the revision)

Scored on the 82 gold sections:

| Set (each gold in its own convention) | Gold | Found | P | R | P, term + scope | R, term + scope |
|---|---|---|---|---|---|---|
| A (va, dc, md, tx; liberal heading convention) | 51 | 28 | 1.000 | 0.549 | 0.929 | 0.510 |
| B (ca, ny, il; no heading terms) | 37 | 34 | 0.971 | 0.892 | 0.912 | 0.838 |
| C (fl, wa, nc) | 40 | 41 | 0.854 | 0.875 | 0.829 | 0.850 |
| **All** | 128 | 103 | **0.932** | **0.750** | **0.883** | **0.711** |
| All, without by-reference definitions | 111 | 85 | 0.941 | 0.721 | 0.894 | 0.685 |

By kind, among the terms found:

- `means`: 60 of 60 are gold terms.
- `contents` 4 of 4, `parenthetical` 2 of 2, `establishes` 2 of 2.
- `includes` 1 of 1, `excludes` 1 of 1 and `acts_as` 1 of 1. One example each proves nothing.
- `by_reference`: 16 of 18.
- `heading`: 9 of 14. The 5 "extra" ones are headings that gold C or B chose not to label, such as *certificate of formation*, *articles of organization* and *covered entity*.

Gold recall by convention:

- in-text definitions: B's explicit ones 23/23, and C's 32/37 (C's misses are four appositive "X, which …" definitions and one descriptive phrase in § 605.0113);
- gold A's heading head-nouns: 7/25 (e.g. "clerks" in "clerks to report unsatisfied fines"; these are deliberately not extracted);
- B's functional definitions 2/6, and A's condition and criteria definitions 0/3.

Other checks:

- `scope_path()` agrees with all 28 of gold C's own scope paths.
- Matched spans overlap the gold spans with a mean IoU of 0.85.
- The cheap role/document/other guess is right for 91 of 96 matched terms.

All four "Incorporators" sections give the same result: `incorporator`, kind `acts_as`, source `heading+text`, category `role`, scope = the enclosing chapter. The sections are FL 607.0201, VA 13.1-618, NC 55-2-01 and DC 29-302.01. Fla. Stat. § 607.01401 alone yields 78 terms, all scoped to chapter 607.

### 2.2 Held-out sections

Gold is the development set, and it flattered the scopes. The verifier drew 54 definitions sections that no gold contains (seed 11, six per state from a `title:definitions` search; Illinois has none, because its headings never say "definitions"). `scripts/terms_eval.py --part heldout` scores them against the terms and units read by hand from each text. The reader also changed the extractor, so after the revision these 54 are a second development set, not a blind test.

| Verifier's 54 sections | Before | After |
|---|---|---|
| Expected terms found (of 148) | 119 (R 0.80) | 137 (R 0.93) |
| Predicted terms that are real terms | 119 of 119 | 137 of 137 |
| Term rows with the right scope | 49 of 122 | 140 of 140 |
| Sections with every scope right | 17 of 35 | 37 of 37 |

The 140 include 29 anchored rows and 4 rows with no unit. Those are right only by the labelling convention: an anchored unit is labelled the way `resolve_scope()` anchors it, and a list of sections is right only as no unit at all. Both kinds are held for review (§6).

The verifier's own count was "about 59 of 122". The 10 extra misses counted here are scopes taken from the definitions heading where the text says otherwise: "this Article" in N.C. § 95-240, "For purposes of this article" in N.Y. Env. § 19-1101, the lists of sections in N.Y. Gen. Oblig. § 13-109 and RCW 39.23.010, and the heading term of Fla. Stat. § 627.652.

What changed:

- **Plural "The terms … include".** Bare `include` is a definition verb, so Fla. Stat. § 627.652 now yields its 7 lost terms. "shall be defined to include" (N.C. § 14-58.1) is one too.
- **Lead-ins that are not "As used in X:".** These now set the scope:
  - "In construing this chapter" (Fla.);
  - "The following definitions apply in this Article:" (N.C.);
  - "the definitions in this section apply throughout this chapter" (Wash.);
  - "In this subtitle the following words have the meanings indicated" (Md.);
  - "…, the following terms mean:" and "When used in this chapter:";
  - 'The term "X", as used in this chapter, …'.
- **Levels the index path lacks** ("this subchapter" in D.C. and Texas, "this Article" and "this Part" in N.C., "this act" in Fla.). These were `None`. They are now *anchored*: the unit that holds the section, such as `DC Code / Title 2 / Chapter 15 / Subchapter containing § 2-1561`. That names the right unit but not its extent, and another section of the same subchapter gets another anchor. So these go to review (§6). The second revision corrected where an anchor sits (§2.3).
- **The UCC's general definitions.** Md. Code, Com. Law § 1-201 scoped its 41 terms to "this section". They now scope to the Maryland UCC, `MD Code / Article gcl / Titles 1-10`, from the short title in § 1-101(a). This comes from a small table of named units, `terms.NAMED_UNITS`, which also covers the UCCs of Florida (chapters 669–680, where "this code" means the UCC), Virginia (Titles 8.1A–8.9A) and Illinois (810 ILCS 5). It is not a general resolver for named acts. The same section now also finds "Agreement", as distinguished from "contract", means; "Burden of establishing" a fact means; and "Send" in connection with a writing means. That gives 46 terms, one per definition.
- **North Carolina list items** "(1) Owner. - The holder …" are read. N.C. also captions ordinary subsections this way ("(b) Applicability. - …"). The first revision read an item after *any* earlier lead-in, which let captions through (§2.3).
- **A list of sections** ("As used in sections 13-101, …, and 13-107") has no unit. The words stay in `scope`, and `scope_unit` is `None` rather than the title a definitions heading would suggest.
- **`scope_basis`** records how each unit was found: `path`, `named`, `anchored`, `compound` (several units; §2.3), `heading` (no scope words; a definitions heading's enclosing unit), `default` (no scope words; the section) or `None`. After the revision the 140 rows are 58 `path`, 46 `named`, 29 `anchored`, 4 `None`, 1 `heading` and 2 `default`. The second revision leaves these counts as they were.

Still missed, all term recall:

- Wash. RCW 82.04.216, "when the terms 'tangible personal property,' … are used in this chapter, the terms do not include steam" (9 terms);
- N.Y. Com. Law § 131, "a small business shall be deemed to be one which …";
- the "Adirondack" half of "Adirondack or Catskill parks as defined in section 9-0101".

Two fresh samples of 54 sections each (`--part heldout --sample 12` and `--sample 13`, no gold and no `HELD_OUT` section) were read by hand:

- **Seed 12.** Read after the changes above: 78 of 116 term rows had the right scope. It exposed:
  - Maryland's lead-in without a colon (16 terms in Md. Lab. & Empl. § 11-503);
  - "the following terms mean:";
  - "are applicable to this article";
  - a colon swallowed by a section range ("ss. 876.37-876.50:");
  - "The term … as used in this chapter".

  After those fixes: 111 of 118 right, 1 unclear. Still wrong:
  - RCW 26.60.025 ("used in the Revised Code of Washington");
  - Md. Educ. § 7-1301 (scoped to an interstate compact);
  - one heading term that is not a defined term.
- **Seed 13.** Untouched until it was read: 98 of 103 term rows right. The misses:
  - Va. § 8.01-669, "As used in Chapters 26, 26.1 and 26.2" (4);
  - a heading "Definition and purposes." taken as a term.

  Fixing those, and a North Carolina item "(2) Record. - …" that was wrongly treated as a caption, gives 104 of 104.
- **Scopes from a definitions heading** (`heading`, 16 rows in seed 13) follow gold C's convention: the enclosing unit. They are guesses where the text has no scope words.

### 2.3 Second revision, after the re-check

The re-check (`docs/design/verify-terms.md`, "Re-check of the fixes") found two defects and several overstatements. The gold scores (§2.1) and the held-out scores (§2.2) are unchanged by this revision; one held-out label, Fla. Stat. § 606.03's "this act", moved with the anchored-unit fix below. The comparisons below ran the extractor before and after this revision on the same sections. Every reading of a sample was done by the person who made the change, so the samples are evidence, not a blind test.

- **Long quoted lists.** `_LIST`'s separator `\s*[,;]?\s*(?:or|and|and/or)?\s*` could split a run of spaces three ways. A list that then failed to match retried every split, exponentially:
  - 12 quoted items took 1.4 s, 14 items took 11 s;
  - N.C. Gen. Stat. § 14-107.1, with 18 quoted reasons for dishonor and no definition verb, never finished.

  The separator is now `\s*(?:[,;]\s*)?(?:(?:and/or|or|and)\s*)?`. Each piece starts with its own kind of character, so the same strings match, but in one way only. All of § 14-107.1 now takes 0.02 s, and the list pattern takes 0.06 s on 200 items. A test runs the § 14-107.1 list and a 60-item list in a child process with a 60 s timeout.
- **N.C. dash items outside a definitions list.** A dash item "(x) Caption. - …" is now a definition only:
  - inside the list a lead-in opens. That list ends at the next line that opens with an enumerator of the lead-in's own line's kind. "(a) … For purposes of this section: (i) …" ends at "(b) Punishment. - …" (§ 14-150.3);
  - or, before any lead-in, in a section whose heading is about definitions alone. "Definitions." and "Definitions relating to resources." qualify. "Definitions; description of boundaries." and "Definition of service districts." do not.

  Lead-ins are also found after a caption ("(a) Definitions. - For the purpose of this Article:", § 87-21), after a dash ("For purposes of this part —", D.C. Code § 1-204.24f), and in "The following words have the listed meaning in this Article:" (§ 15A-1368). A caption that quotes its own term ("(3) Mayor. — The term “Mayor” means") gives one Term, not two. But this revision dropped such an item even when nothing defined the quoted term, which lost real terms; the third revision fixed that (§2.4).

  Measured on 1,500 random N.C. sections that contain ". - " (seed 21). The second re-check corrected the "duplicates" row: 23 of the 52 it counted were lost terms, not duplicates.

  | | Count |
  |---|---|
  | Dash-item terms dropped | 373 |
  | of which duplicates of the quoted term | 29 |
  | of which terms lost: the item quotes its term with "is" or "are synonymous", which no rule reads as a definition (N.C. § 81A-9's 22, § 20-286's "Sell"); restored in §2.4 | 23 |
  | of which the rest: 80 sampled, all captions | 321 |
  | Terms added (definitions after a caption lead-in, e.g. § 113-211) | 77 |
  | Terms whose scope changed | 99 |
  | Dash-item terms kept | 3,091 |
  | kept inside a lead-in's list, in sections with no definitions heading: 60 sampled, no caption (95% upper bound about 6%) | 840 |
  | kept under a definitions-only heading before any lead-in: 50 sampled, no caption | 221 |

  The scope changes are lead-ins now read. For example, 18 terms of § 162A-85.1 moved from the chapter to "this Article". Another 22 terms of §§ 168A-3 and 131E-176 had inherited an earlier item's "this subdivision".

  This is still a reading of layout, not of meaning. A caption inside a list, or a list printed without line breaks, can be misread. So unquoted dash items are held for review (§6).
- **Anchored units under the right parent.** A missing level now lies inside the deepest unit of the path that can contain it (`terms._INSIDE`):
  - Maryland's "Article" is a whole code, so Md. Gen. Prov. § 5-857's part is `MD Code / Article ggp / Title 5 / Subtitle 8 / Part containing § 5-857`;
  - an Illinois article lies in its Act: `Illinois Code / Chapter 105 / Act 5 / Article containing § 34-1.1`;
  - a Texas subtitle lies in its code: `TX Code / Code bc / Subtitle containing § 1.201`;
  - an act is no level of these paths, and its extent is unknown. It may be the whole chapter, as Va. Code ch. 66 is the Middle Peninsula Chesapeake Bay Public Access Authority Act, or less, or more. So it is anchored under the section's own enclosing unit: `Virginia Code / Title 15.2 / Subtitle IV / Chapter 66 / Act containing § 15.2-6602`. It still goes to review: the conservative choice, rather than reading "this act" as the chapter outright.

  The held-out label of Fla. Stat. § 606.03 moved the same way. On 600 random sections, 60 per state (seed 5), nothing changed. On 350 sections from a `title:definitions` search (seed 9), the changes were:
  - 30 terms of 7 Florida and Virginia "this act" sections, whose anchor moved under the chapter or part;
  - 2 D.C. terms moved to their subchapter (a dash lead-in);
  - 5 Washington terms got compound scopes;
  - 3 "means X as defined in" pairs became single by-reference Terms.
- **Compound scopes** are no longer cut to their first unit:
  - "this section and to ss. 605.1006 and 605.1062-605.1072" (Fla. § 605.1061);
  - "this Article and Articles 21A and 21B of this Chapter" (N.C. § 143-212);
  - "this Part or Parts 1 and 2 of this Article" (N.C. § 115C-563);
  - "this section and RCW 24.03A.715 through …";
  - "this chapter and Chapter 11 (…) of this title".

  No one unit expresses such a scope. So `scope_unit` is `None`, `scope_basis` is `compound`, and `Term.scope_parts` lists each part with its own unit, or `None` where no unit expresses the part. A unit followed by other words ("this chapter and in any rule adopted under it") stays one unit. Scopes of four or more comma parts, section numbers in words and RCW footnote asterisks were still cut to their first unit; §2.4 fixed them.
- **Smaller fixes:**
  - '"Woodland" means woodland as defined in G.S. 105-277.2' is one `by_reference` Term, no longer a `means` and a `by_reference` Term on one key. Its `defined_in` no longer stops at the period of "G.S.".
  - "Declaration of policy." and "Statement of purpose." headings name no term. Nor does "description of …".
  - The rule baseline counts 9 links to a different thing with `REJUDGED` applied (8 by the survey's labels).
  - The held-out report says how many right rows are right only by convention.
- **Keys:** see §1 and §6. The singularisation that reaches a key is frozen. A test pins a checksum of its tables, and checks that a changed matcher moves no key.
- **The review threshold:** see §1 and §5.
- **Speed.** Sentence splitting no longer copies the text before every period. On the 15 longest sections of each state (150 sections, up to 1.2 MB), the slowest took 4.4 s (N.Y. Tax Law § 606, 412 KB).
- **Not changed** (recall, not defects): Va. § 18.2-486's five unquoted words, Fla. § 90.401 and N.Y. Educ. § 8201 are still missed. Fixing them risks new false terms.

### 2.4 Third revision, after the second re-check

The second re-check (`docs/design/verify-terms.md`, "Re-check 2") found one regression, three test pins that pinned nothing, and seven smaller defects (its items 3 to 6). Where a fix needed a judgement call, the conservative reading was taken, and each is named below.

- **The regression: a dash item that quotes its own term.** The second revision skipped "(1) Adjustment. - "Adjustment" is an act …" as a duplicate of the quoted term. But "is" is no definition verb, so no other rule found the term. N.C. § 81A-9 lost all 22 of its terms this way, and § 20-286 lost "Sell" ("The terms "sell," … are synonymous"). The item is now skipped only when a Term with the same normalised term was found at the quoted position: "(3) Mayor. — The term “Mayor” means" still gives one Term, the quoted definition. This is the verifier's conservative fix. The restored items are unquoted `means` terms by the §6 test (the term starts at the caption, not at a quotation mark), so they are held for review.
- **Three pins that pinned nothing.** The "When used in" and "the following terms mean:" rows had a "Definitions." heading, whose fallback gave the same chapter. They now have no heading, so only the lead-in can give the chapter. The "Definition and purposes." row's text never mentioned its heading. The heading rows now repeat their heading in the text, as N.C. texts do. "Definition and regulation of auctioneers." is not generic, so only the "definition" word rule keeps it out.
- **A letter "(i)".** A lower-case "(i)", "(v)" or "(x)" is read as a roman numeral, unless the lead-in's own line has the letter before it ("(h) Other Definitions. - As used in this section:", N.C. § 58-68-60). Then it is that letter, and the list ends there, unless "(ii)" ("(vi)", "(xi)") opens a line before "(j)" ("(w)", "(y)") does. When neither follows, it is read as the letter. That ends the list, the conservative reading: it can lose a one-item roman list, but it cannot turn a caption into a term.
- **An item's inner lead-in.** Under a definitions-only heading with no lead-in of its own, an item's "As used in this subdivision, the following terms apply:" made every later item "after a lead-in", so they were dropped. A lead-in inside a definition item that opens its line now opens its own list but does not end the heading's. The items after it take the heading's scope, not the inner "this subdivision". Any other lead-in still ends the heading's list, so a caption after a top-level list is still dropped.
- **Compound scopes.**
  - A run of four or more comma parts: "this chapter, Chapter 4, Chapter 5, and Chapter 6 of this title" (the shape of Fla. § 253.025 and Cal. Rev. & Tax. § 17021.7). A run counts only when "and" or "or" closes it, so "this chapter, chapter 2, chapter 3, the rules …" stays one unit.
  - Section numbers in words: "this section and sections eleven hundred seven and eleven hundred eight of this article" (N.Y. LLC § 1106). Only numbers without an "and" inside are read.
  - RCW footnote asterisks: "this section and RCW * 43.215.145 , * 43.215.147 , and ** 43.121.185" (RCW 43.216.157). The scope keeps the text's own words, asterisks included.
- **False terms.**
  - A heading segment is now generic when every "and" part is generic ("Powers and duties.", "Purpose and scope.") or when it opens with a generic phrase of two or more words ("Statement of purpose and authorization.", N.C. § 106-1041).
  - "means-tested" is no definition verb, so N.C. § 108A-25.3 no longer gives "Public assistance program. - Any".

Measured, old (the second revision) against new, with every changed Term read by the person who made the change:

| Sections | Changed | What changed |
|---|---|---|
| All 3,372 N.C. and 288 D.C. sections with a "(x) Caption. -" item | 22 N.C., 0 D.C. | +23 terms: § 81A-9's 22 and § 20-286's "Sell", the verifier's 23 and nothing else. −20: the § 58-68-60 caption, the § 108A-25.3 false term, and 18 heading terms of generic headings ("Powers and duties." in 5 sections and "Powers and duties of …" in 3, "Legislative findings and intent.", "Records and reports.", "Duties and authority.") |
| 600 random sections (60 per state, seed 31) and 3,230 `title:definitions` hits (up to 400 per state) | 9 | 2 generic heading terms gone (Fla. § 379.2351, N.C. § 58-44-70). Asterisked numbers kept in four RCW section lists ("RCW 47.76.400 through * 47.76.450"). RCW 43.216.157 and N.Y. LLC § 1106 now compound. N.Y. Educ. § 6901, "As used in section sixty-nine hundred two", is now a list of sections with no unit (it was the article, from the heading) |
| The 82 gold and 54 held-out sections | 0 | every field of every Term identical, so §2.1 and §2.2 stand. `terms_eval.py` was not re-run for this revision; the identical output is what carries its numbers over |

Tests and speed:

- `tests/test_terms.py`: 75 passed (66 before).
- Mutation check: 19 mutations, each undoing one part of the fixes above in a scratch copy, some in both directions (for example, the dash item always skipped and never skipped). Each fails at least one test.
- On synthetic worst cases, 2,000 comma parts, 800-word number lists and 2,000 asterisked numbers each take under 0.4 s.
- The inner-lead-in check is linear in the lead-ins. A synthetic section of 600 items, each with an inner lead-in, takes 6 s. Most of that is the existing "also includes" pass, which compiles one pattern per known term: 5 s for the second revision's 600 terms, 6 s for this revision's 1,198.

## 3. Item kinds

| Kind | Class (P5) | Key (P25) | Label pattern | One per |
|---|---|---|---|---|
| **Defined term** | new class *defined term* (its own close match → wd:Q2135465 *legal term or legal concept*) | `lexflow:term:{state}:{ref}:{slug}`, plus `@{pin}` for a sub-section scope | `incorporator (Fla. Stat. § 607.0201)` | key: (section, term, pinpoint); several definitions can share it |
| **Concept** | its kind class: Q23 *legal role*, new *legal document* (wd:Q49848 / Q3150005), new *legal status* (wd:Q2628882), or new *legal concept* (wd:Q2135465) for the rest | `lexflow:concept:{slug}`, plus `--{sense}` for a homonym | `incorporator` | concept, across jurisdictions |
| **Scope unit** | new class *statutory unit* | `lexflow:unit:{state}:{path-slug}` (path, named or anchored unit) | from the path: `Fla. Stat. ch. 607`; a name such as `Florida Business Corporation Act` only once a reviewer adds it from the short-title section | chapter / act / article that some term's scope names |
| **Process role** (exists) | Q23 *legal role* | `lexflow:role:{state}:{question}:{actor}` (unchanged) | `Authorized representative (founder) (Florida)` | (state, question, actor) |
| **Statute** (exists) | Q10 | `lexflow:statute:{state}:{ref}` (unchanged) | `Fla. Stat. § 607.0201` | section |

The earlier draft labelled a term `{term} ({unit name})`. But the index path gives no unit name: "Chapter 607" is in the path, "Florida Business Corporation Act" is not. So the label uses the citation, which every row carries.

The concept's kind is a claim, not part of its key. The map sketched `lexflow:concept:role:incorporator`, but a term re-classified from *concept* to *status* would then change identity. Defined terms carry the extractor's `category` (role / document / other) only as a hint for which concept class to propose.

Roles, documents and statuses are concepts with a kind, not separate hierarchies:

- *incorporator* and *registered agent* are roles;
- *articles of incorporation* and *arrest record* are documents;
- *indigency* and *conviction* are statuses.

`P6 subclass of` (already on the wiki, never written) carries concept → broader concept. Examples: *professional corporation* → *corporation*, and *incorporator* and *organizer* → a lay *founder* concept. This keeps broader links inside Lexipedia, where they can be reviewed, instead of pointing them at Wikidata.

## 4. Properties

Existing properties reused: P5, P6, P8, P13 *references*, P14 *based on*, P15, P22 *citation*, P25.

New ones (string values are capped at 400 characters by the loader's `_snak`):

| New property | Datatype | On | Value | Notes |
|---|---|---|---|---|
| **defined in** | item | defined term | the statute item (Q168) | one statement per definition that shares the key (`terms.group_by_key`): Md. Code, Com. Law § 1-201 says what a "Security interest" means, includes and does not include, so that item carries three. Qualifiers: `P22 citation` = the defining words (the first 400 characters of `definition_span`), **definition form** (string: `means`, `includes`, `excludes`, `by_reference`, `parenthetical`, `contents`, `acts_as`, `establishes`, `heading`). By-reference terms also get `P13 references` → the item of the section that holds the meaning |
| **scope** | item | defined term | the scope-unit item, or the statute item itself for "this section" | qualifier **pinpoint** (string, `(g)`) for sub-section scopes. An anchored unit is a unit item labelled from its anchor ("Subchapter containing D.C. Code § 2-1561"). A scope that no unit expresses (a list of sections) gets a P22 string instead of an item. A compound scope gets one statement per part in `scope_parts`: an item where the part has a unit, a P22 string where it has none |
| **concept** | item | defined term | the concept item | separate from P5, so a term can move to another concept without changing its kind, and "all defined terms" stays one P5 query |
| **role of actor** | item | process role | the defined term the actor plays (or the concept, when the state has no definition) | qualifier P13 → the statute item of the actor's source quote (`FActor.source`, dropped by `compile_facts` today) |
| **used in process** | item | defined term or concept | a process item (`lexflow:process:{model_id}`) | qualifier **as** (string): the actor id or decision-input name (`registered_agent`, `founder`) that uses it |
| **close match** / **broad match** / **narrow match** / **related match** | url | concept (else defined term) | `http://www.wikidata.org/entity/Q…` | beside the existing `P8 exact match`; `P7 equivalent property` → skos:closeMatch, etc. Wikidata itself records the same relations as `P4390 mapping relation type` with Q39893449 exact, Q39893184 close, Q39894595 broad, Q39893967 narrow, Q39894604 related |
| **match probability** | quantity | qualifier on P8 and the four above | `link()`'s p, 0–1 | the loader needs a quantity snak (it writes only item and string snaks today) |
| **determination method** | string | qualifier on the same | `reviewed by <role>, suggested by lexflow.law.terms (2026-10-10)` | `P7` → wd:P459. Every mapping is reviewed, so there is no `classifier` value |

## 5. Wikidata links: when and where

1. **Search** with `wbsearchentities(term)` (limit 5) per concept. Use read-only calls, at most one request per second, cached. Add one more `wbgetentities` call to name the P31/P279/P17/P1001 values. `candidate_from_entity()` turns the JSON into the classifier's input.
2. **Score** with `link(term, candidates, state=…)` (also `terms.suggest`): a logistic regression over 29 cheap features.
   - Label and alias match, word overlap.
   - Description cue words: legal, person who, document, United States, junk patterns (generic kinds of non-legal item: works, people, places, organisms).
   - P31/P279 class cues, including "P31 is a specific statute".
   - Jurisdiction: a foreign country, or another US state when the term names none.
   - Sitelinks, search rank, and whether the candidate has the most sitelinks among the label matches.

   It needs no model server. The cue lists no longer contain the PropBank tokens ("prototypical", "proto-agent", "PropBank", "predicate", "semantic role"). They matched only the survey's 5 PropBank pairs, all judged wrong, incorporator's among them, so they encoded the answers. The other junk words were also written while reading the survey, and leave-one-term-out cannot measure that. Two general features tried in their place, "has a class but no legal or non-legal class cue" and "has a description with no legal, person or document cue", changed the log loss by less than 0.001 and were not adopted.

   Leave-one-term-out on the survey, with the cue lists as shipped:

   | | Value |
   |---|---|
   | Pair AUC | 0.947 (log loss 0.178; 0.95 and 0.174 with the PropBank tokens) |
   | Rule baseline (label or alias match, no junk, no foreign tag) | links 107 terms: 80 right; 9 links to a different thing with `REJUDGED` applied (8 by the survey's labels) |
   | **Review queue**: the fixed `review_threshold` 0.5 (`terms.REVIEW_THRESHOLD`, the even-odds point; not tuned on these scores) | 91 suggested, 77 exact: precision 0.846, 95% Clopper–Pearson lower bound 0.755, recall 0.73 of the 106 terms that have an exact item. The threshold was not searched for on these scores, so this estimate needs no nested correction for threshold selection (the L2 weight was chosen on the out-of-fold log loss) |
   | The 14 non-exact suggestions there | 11 neighbours, by the survey's labels: *judicial review* → the judicial-review doctrine Q898871, *chief information officer* → Q2589465, *garnishment* → Q186302, *secretary of state* → Q736559, *arrest record* → Q1070100, *corporation* → Q167037 and *jail* → Q40357 (broader); *scofflaw* → the word sense Q7434243, *certificate of incorporation* → Q3629341, *community supervision* → Q6538366 and *records officer* → Q3499285 (related). 2 different things: *custodian of records* → Q5196342, the 18 U.S.C. § 2257 records keeper (the survey labelled it *related*, but by the rule in "What not to link", a specific statute's item for a generic term, it is a different thing), and *incorporator* → the PropBank item Q140403634 (0.727). 1 possibly different: *restitution* → Q1156800, the civil gains-based remedy, where the term is criminal victim restitution (survey: *broader*). `terms_eval.REJUDGED` records the two disputed ones |
   | Term-level P≥0.90 (diagnostic only; the first revision's review threshold) | threshold 0.7607: 64 linked, 58 right, lower bound 0.81. The next term below is *incorporator* (0.727, wrong), so that one label places the threshold. With the threshold chosen inside each training fold: 59 of 67 (0.88, lower bound 0.78), median inner threshold 0.731, again just above the incorporator. Not an operating point |
   | Term-level P≥0.95 (diagnostic only) | threshold 0.9538: 2 linked, 2 right, lower bound 0.16. Nested: 2 linked, 1 right. Before the first revision, the shipped 0.9755 threshold linked 3 (lower bound 0.29) and sat 0.0008 above a wrong link (*scofflaw*, p 0.9747). Not an operating point |
   | Term-level P≥0.85 (diagnostic only) | threshold 0.5453: 88 linked, 75 right, 2 different things, 1 possibly |
   | Optional nomic-embed-text similarity of the term and its context to the candidate (`--embed`) | measured before the PropBank tokens were removed (log loss 0.174 → 0.1705; at P≥0.90 87 linked, 79 right), not re-run since. It needs the embedding server and a context string, so the shipped model leaves it out. It is still the first thing to try for ordering the review queue |

3. **Decide.** A person decides every mapping.
   - `p ≥ review_threshold` (0.5): a row in the review table (below), nothing on the wiki. Out of fold on the survey, 14 of 91 such rows are not an exact match, so the reviewer, not the score, is the safeguard.
   - A reviewer then writes exact, broad, narrow, close or related match with `determination method = reviewed by …`, or rejects the pair.
   - `p < review_threshold`: nothing is suggested. A reviewer may still search by hand.
4. **Attach to the concept, not to each term,** once a concept exists. One fix then reaches every jurisdiction. A defined term carries a mapping itself only while it has no concept.
5. **Keep decisions in the database.** The loader replaces lexflow-owned items' statements wholesale (`clear`). So reviewed links must live in the database and be re-emitted on every run, or the next run erases them.

   A sketch of the table: `term_links(concept_key, wikidata_qid, relation, p, method, reviewed_by, reviewed_at, status suggested|accepted|rejected)`. A rejected pair is never suggested again. `reviewed_by` is a role or an account, never a person's contact details.

### What not to link

- **Same-label items of another kind**: PropBank proto-agent and proto-patient items (Q140403634 for *incorporator*), lexeme-like word senses (Q7434243 *scofflaw*), scholarly articles, films, episodes, albums, family names, genes and proteins (*serine incorporator*). The classifier's strongest negative cue is still the junk-description pattern, but it no longer names PropBank. The PropBank *incorporator* does reach the queue (0.69), and the reviewer rejects it.
- **A specific statute for a generic term**:
  - the federal 1946 APA (Q25344901) is not Texas's APA (Gov't Code ch. 2001);
  - the Adam Walsh Act is not "sex offender registration";
  - the 18 U.S.C. § 2257 custodian of records is not the public-records custodian.

  The feature for this is "P31 is an Act or statute": 34 of the 35 survey pairs that have it are wrong, and the other is related. It does not always keep such an item out of the queue. Alone, the federal APA scores 0.66 for "Administrative Procedure Act" and is queued. Among its real search results, four other countries' same-label Acts, it scores 0.25 and is not.
- **One instance for a class**: one agency or one certificate for the generic term.
- **Another jurisdiction's namesake**:
  - foreign legal forms: Latvian or New Zealand LLCs, Swiss or French general partnerships;
  - another state's item: Connecticut PURA for "public utilities commission";
  - the four other states' Offices of Administrative Hearings for Maryland's. Pass `state=` so the right state's item escapes the other-state penalty.
- **Items with no description and no class**: nothing says which sense they are. `unlinkable()` gates them out whatever their label, e.g. *Ability-to-pay* and *Undue hardship*.
- **A broader concept as an exact match**: the judicial-review doctrine Q898871 for review of agency action, and the generic secretary-of-state positions Q736559 for the US state office. At most a reviewed `broad match`.
- **Per-state GLEIF legal-form items as exact**: they are narrower, and the generic concept is the target.
- **Words the statute only uses**: a section that uses a term defined elsewhere gets no term item. It gets a `P13 references` to the defining section, if anything.
- **Construction words**: NC 57D-10-02's "herein", "hereof", "or", "any" and "including". They are extracted (gold C lists them), but they get no concept and no Wikidata link. Only when they become useful as `P13` targets should they get items at all.

## 6. Keys, labels and re-runs

| Key | Example | Formed from | Stable because |
|---|---|---|---|
| term | `lexflow:term:fl:607.0201:incorporator`; `lexflow:term:il:5 ILCS 140/2:request@g` | `terms.term_key(state, ref, term, pinpoint)`. `ref` is the same string as in the section's statute key. `slug` is frozen at `KEY_VERSION` 1: lower case, other characters → `-`, no plural folding, and no call to `norm_term`. It is the same rule as `lexflow.law.links`' definition keys. Heading, "may act as" and "defined as" terms are made singular by the frozen `key_singular` | derived from the statute key and the words. No counter, no index row id (`sec.id` changes with every rebuild). Changing the matcher's normalisation (`norm_term`, `_singular`) moves no key. A key moves when the extractor captures other words or another pinpoint. Changing `slug`, `key_singular` or its tables means a new `KEY_VERSION`, and every published item keeps its old key as a second P25 value |
| concept | `lexflow:concept:incorporator`; `lexflow:concept:agency--public-records` | `terms.concept_key(name, sense)`. `name` and `sense` come from the stored review table, where a reviewer accepts that terms from several states are one concept. The extractor never mints one | the reviewed name. A homonym gets the reviewer's sense as a suffix (`agency--public-records` vs `agency`, agency law) |
| unit | `lexflow:unit:fl:florida-code-title-xxxvi-chapter-607`; `lexflow:unit:md:md-code-article-gcl-titles-1-10`; `lexflow:unit:dc:dc-code-title-2-chapter-15-subchapter-containing-2-1561` | `terms.unit_key(state, scope_unit)`: the unit's path (or named or anchored unit), lower case | the code's structure. Renumbering a chapter is a new unit. An anchored unit is stable while its anchor section keeps its number, but two anchors can name one unit: a reviewer merges them |

Rules for re-runs:

- **Find before create.** Look the key up in `wikibase_items`, then by P25 on the wiki. That second lookup does not exist yet and must be written before the first load. Only then create.
- **Section key.** When the statute keys move to the act_id form proposed in the map (`lexflow:statute:{state}:act:{act_id}`), each term item gets that form as a second P25 value. Both keep resolving.
- **Label and description.** The wiki allows one item per label + description pair:
  - label: `{term} ({citation})`, e.g. `incorporator (Fla. Stat. § 607.0201)`;
  - description: `term defined by {citation}`, plus `, subsection (g)` when pinpointed.

  Two definitions of one word in one section with different scopes (5 ILCS 140/2 *request* for (g) and for (h)) already differ by pinpoint, both in key and in description. Two keys of one section differ in term or pinpoint, so in label or description. The verifier found no label + description clash in 136 sections (gold plus held-out).
- **One item per key.** `Loader.entity()` replaces an item's statements wholesale. So a loader that writes once per Term keeps only the last definition. The verifier found 9 keys with two or more Terms in those 136 sections, always one term and scope defined in several ways. Group first (`terms.group_by_key`), then write each key once, with one *defined in* statement per Term.
- **Synonyms.** '"Local government" or "locality" means' gives two Terms, and each lists the other in `alternatives`. Each keeps its own key and item, and carries the others as aliases, so a search for either finds both. A reviewer can then put them under one concept. An "and" list ('The terms "policy" and "insurance policy" include') is several terms with one definition, not synonyms.
- **Which terms load.** Only reviewed or agreed material goes to the sites, so the conservative rule is this. A `means` term that the text quotes (the character at its `term_start` is a quotation mark; 60 of 60 `means` terms on gold, and every one read on the held-out sets was a real term) and whose `scope_basis` is `path`, `named`, `heading` or `default` may load for sections whose statute item exists. Everything else is held for review until more gold exists:
  - unquoted `means` terms: N.C. dash items, whose reading is a layout heuristic (§2.3), and "X shall mean";
  - `includes`, `excludes` and `acts_as` (one gold example each);
  - `contents` (4) and `by_reference` (16 of 18);
  - `heading`, `parenthetical` and `establishes`;
  - every `anchored` and `compound` scope, and every scope with no unit.
- **Retiring drafts.** `retire_drafts` parses keys and knows only `process`, `role` and `step`. Term, concept and unit keys are not model-scoped. It skips them already, because `parts[1]` is not in its list. A term whose section text no longer defines it is relabelled "no longer defined by …", not deleted.
- **Where the code goes.** A `Loader.terms()` phase after `statutes()` in `publish/wikibase_lexipedia.py:392-413`, fed by a `terms` table filled by `lexflow.law.terms.definitions()` over the sections the wiki holds. Both are outside the frozen files.

## 7. Worked example: Fla. Stat. § 607.0201 (Q168, "Incorporators.")

Section text (index row `STATE_FL_TXXXVI_C607_PI_S607.0201`):

> One or more persons may act as the incorporator or incorporators of a corporation by delivering articles of incorporation to the department for filing.

Extractor output: one `Term` with these fields.

| Field | Value |
|---|---|
| `term` | `incorporator` |
| `kind` | `acts_as` |
| `source` | `heading+text` |
| `category` | `role` |
| `definition_span` | the sentence above |
| `scope` | `this chapter` |
| `scope_unit` | `Florida Code / Title XXXVI / Chapter 607` |
| `scope_basis` | `path` |

Chapter 607 is the Florida Business Corporation Act by its own short-title section, § 607.0101.

Items and statements. "new" means a new item, and only after the classes and properties exist. `acts_as` terms are held for review under §6, so a reviewer accepts this term before it loads:

1. **Unit** (new): key `lexflow:unit:fl:florida-code-title-xxxvi-chapter-607`, labelled `Fla. Stat. ch. 607` from the path. A reviewer adds the name *Florida Business Corporation Act* from § 607.0101.
   - P5 *statutory unit*, P15 Florida (Q33), P13 → the § 607.0101 (short title) statute item once that section is loaded.
2. **Defined term** (new): `incorporator (Fla. Stat. § 607.0201)`, described "term defined by Fla. Stat. § 607.0201", key `lexflow:term:fl:607.0201:incorporator`.
   - P5 *defined term*; P15 Q33.
   - *defined in* → **Q168**, with qualifiers P22 "One or more persons may act as the incorporator or incorporators of a corporation by delivering articles of incorporation to the department for filing." and *definition form* "acts_as; heading 'Incorporators.'".
   - *scope* → the unit item.
   - *concept* → item 3.
   - *used in process* → Q774 (`lexflow:process:fl.business`), with *as* = `decision business_structure`. That decision's rules are the ones in the model that quote § 607.0201.
3. **Concept** (new): `incorporator`, described "person who signs and delivers a corporation's articles of incorporation for filing", key `lexflow:concept:incorporator`.
   - P5 Q23 *legal role*.
   - P14 *based on* → an MBCA § 2.01 item (P8 exact match wd:Q6888224 belongs on the MBCA's own item, not on the section's).
   - P6 → a lay *founder* concept. Its own exact match to wd:Q4479442 is a reviewer's call: the survey judged Q4479442 exact for the curated actor label "Founder (person forming the business)", not for *incorporator*.
   - **No Wikidata exact match.** Q3178478 *incorporation (business)* is a candidate `related match` for review.
   - The same concept is reached from `lexflow:term:va:13.1-618:incorporator` (Q512), `lexflow:term:nc:55-2-01:incorporator` (Q334) and `lexflow:term:dc:29-302.01:incorporator` (Q147). The extractor returns the identical term, kind and chapter scope for all three.
4. **Neighbours** that stay separate concepts:
   - *organizer* (LLC; N.Y. LLC Law § 203, 805 ILCS 180/1-5) and Florida's *authorized representative* (§ 605.0201). The extractor finds the latter as `acts_as` with chapter 605's scope. But its Act, the Florida Revised LLC Act, is only §§ 605.0101–605.1108, a section range that the path-based scope over-states. That is a known limit of path scopes.
   - *articles of incorporation*, the document. Wikidata Q17013292 is the exact item, but the classifier gives it p = 0.30 (0.27 out of fold). Its top candidate is Q3497659 *articles of association*, a broader concept, at p = 0.42 (0.47 out of fold). Both are below the review threshold of 0.5, so nothing is queued. A reviewer who wants the link adds Q17013292 by hand.
5. **Process role**: Q775 "Authorized representative (founder) (Florida)" gets *role of actor* → `lexflow:term:fl:605.0201:authorized-representative`, the LLC route. A corporation-route actor in a future model would point at the incorporator term instead.

**Why not Wikidata Q140403634.**

- Its label is "incorporator", an exact match. That is why a label-matching linker takes it, and why the rule baseline now links it.
- But its description is "prototypical agent (PAG) for predicate 'mainstream.01': incorporate into popular culture", with P279 *proto-agent* (Q134480019).
- It is a PropBank semantic role of the verb *incorporate* in the sense of "mainstream". It is not a legal role, a person who files articles, or anything in corporate law.
- The other hits are a 2020 scholarly article (Q99348672) and *serine incorporator* proteins and genes.
- Wikidata has no item and no English lexeme for the corporate role. A wrong exact match would be worse than none: SKOS exactMatch is transitive, so every jurisdiction's incorporator would inherit "is a PropBank proto-agent".
- The shipped classifier gives it p = 0.69 (0.73 out of fold). No feature names PropBank. General features lower its score: an exact label is worth less when the item has no sitelinks, its description has no legal cue, and its class is no legal class. But 0.69 is above the review threshold of 0.5, so the pair is queued and the reviewer rejects it. The first revision's threshold, 0.7607, sat just above it (0.034 out of fold) because its own label placed that threshold. The earlier p = 0.145 came from the PropBank tokens, which were removed because they encoded the survey's answer. The safeguard is the reviewer, not the score. A rejected pair is never suggested again (§5.5).

So the corporate-law role is addressed by Lexipedia's concept item and its key `lexflow:concept:incorporator`. Wikidata gains a matching item only if someone chooses to create one there; that is a separate, manual decision.

## 8. Open questions

1. Concept as an instance with a *concept* property (proposed here) or as a class that defined terms are instances of (`P5` → concept, the map's question 2)? The property form keeps P5 for kinds and makes re-assignment a one-statement change.
2. Scope units for section ranges ("ss. 605.2101–605.2802", the Florida Revised LLC Act; "Titles 1-10" of Maryland's Commercial Law article): a unit item with a P22 range string, or a list of member statute items?
3. Anchored units: should a reviewer merge two anchors of one subchapter into one unit item, or should the loader find the unit's other sections (its neighbours that say "this subchapter") and name it once?
4. Who reviews, and where? A Lexipedia talk page per concept, a DokuWiki page, or a local review table only. The decision has to be stored in the database either way (§5.5).
5. Should accepted concepts with no Wikidata item (incorporator, organizer, requester, custodian of public records and the 23 survey gaps) ever be proposed to Wikidata? That is an outside write and the user's call.
6. Heading terms: gold A labels head nouns of heading segments ("clerks", "Director"), while gold C labels only whole-heading roles. Which convention should the wiki follow? The extractor follows C, with a text-mention check.
