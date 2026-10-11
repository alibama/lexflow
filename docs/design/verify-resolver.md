# Verification: statute cross-reference resolver (`lexflow/law/xref.py`)

Adversarial check of the "resolver" report, 2026-10-10. All runs were read-only in `lexflow-app-1`. I edited no
files and wrote nothing to the network. The only network reads were one Lexipedia read and one Wikidata search. Lexipedia Q168 is "Fla. Stat. § 607.0201,
Incorporators", and the resolver correctly finds no references in it. Searching Wikidata for "incorporator" finds
only Q140403634, a PropBank role, and one article.

One of my read-only scans, a full-text regex over the California index, ran for about 20 minutes of CPU in the
container before its `timeout` ended the `docker exec`. I then stopped the orphaned process. My `/tmp` files in the
container are deleted.

## 1. Re-run of `scripts/xref_eval.py --resolver both`

Every headline number in the report reproduces exactly.

| metric (82 sections, 893 gold refs) | current `cited()` | new `xref` |
|---|---|---|
| detection, specific (820) | 34.5% | 100.0% (strict 1-1 100%) |
| detection, all / generic | 31.7% / 0% | 98.4% / 80.8% |
| targets outward P / R / F1 | 0.975 / 0.349 / 0.514 (158/162/453) | 1.000 / 0.967 / 0.983 (438/438/453) |
| targets all P / R | 0.975 / 0.312 | 1.000 / 0.970 |
| role / kind / unit / pinpoint accuracy | n/a | 69.6% / 86.1% / 97.9% / 97.5% |
| without BPC 480 and Va. 54.1-204, outward P / R | 0.978 / 0.323 | 1.000 / 0.964; role 68.8% |
| ms per section; table build | 2.4 | 6.5; 6.5 s |

The per-state, per-kind and per-role tables and the role confusions also match the report.
`tests/test_xref.py`: 37 passed in 2.75 s.

## 2. Spot-check of 42 gold labels against the statute text

I sampled 14 labels per file with a fixed seed: 30 with targets and 12 without. Every span equals
`text_of[start:end]`. All 30 target citations are the section the text names; I checked each target's heading and
path. I disagree with no target. Five role labels are debatable but defensible:
- "petition ... pursuant to this section" is labelled procedure;
- "plan required under RCW 36.57A.170" is labelled authority;
- "covered entity under HIPAA, 42 U.S.C. 1320d et seq." is labelled definition;
- "(SEE 5892.SL)" is labelled other_code, though it is an editorial session-law note;
- "the Central Collection Fund established under § 3-306" is labelled definition (seen in the role-error list).

Targeted checks of the labels behind the remaining errors:
- **Md. "the Maryland Vehicle Law" -> § 11-206: the gold is right and the report is wrong.** § 11-206 reads "Titles
  11 through 27 of this article may be cited as the Maryland Vehicle Law." It is the short-title section, not a
  definition. `xref.table("md").names["maryland vehicle law"]` even holds § 11-206 as its anchor. The miss happens
  because a name ending in "Law" is read as a whole code (kind other_code, and the anchor is used only for
  named_act). Its unit is also wrong: the whole Transportation Article instead of Titles 11-27.
- **N.C. "Article 33C of Chapter 143" -> 14 rows, G.S. 143-318.9 to 143-318.18: the gold is right.** These are the
  open-meetings law sections, and the headings say "violations of Article". The resolver cannot find the
  boundaries from the index paths.
- **Fla. RICO Act -> 895.01-895.06: right.** It follows the short-title range.
- **Cal. BPC § 480(g)(2)(D) "subparagraph (A), (B), or (C)" is a gold omission**, as the report says. These are
  three real self-references.
- **"Subject to X" convention conflict confirmed.** Gold A has 6 condition, 1 exception and 1 procedure; gold B has
  2 exception and 1 penalty; gold C has 2 exception and 1 condition.

Small corrections:
- `cited()` has 4 false positives from 4 causes, not 3. The fourth is a truncated number: "1203.1ab" is read as
  "1203.1a" (Cal. PEN § 1465.9).
- Of the 9 spurious generic predictions, 8 are in gold A sections. The ninth ("other law", N.C. 57D-10-02) is in
  the section's heading line.

## 3. Overfitting

- **To the two user examples: no material effect.** Dropping them leaves every number within 0.01, apart from kind
  accuracy for gold_b (93% -> 98%).
- **To specific gold sentences: real, but small for targets.**
  - 7 matched gold references are detected only by phrases that occur in 1 to 28 sections of the 586,313-section
    corpus. "copyright or trade secret laws" occurs in 1 section, the gold Fla. 119.011. "its published rules"
    and "constitutional rights, powers, privileges, or immunities" occur in 3 each, "procedures adopted by the
    Judicial Council" in 6.
  - Without these phrases, generic detection is 52/73 = 71% rather than 80.8%, and all-detection is 97.6%.
  - About 40 correct roles depend on cue rules that fit specific gold passages. 24 of them come from `FEE_ITEM`
    matching one section's fee schedule (N.Y. LLC § 1101, 27 items). Expect held-out role accuracy nearer 65%
    than 70%.

## 4. Held-out check: 30 random non-gold sections I read myself

Sample: seed 4242, 2 sections per state, 300-2,600 characters; seed 9001, 1 per state, 2,000-5,000 characters.
Each section has at least 3 reference cues.

| | current `cited()` | new `xref` |
|---|---|---|
| outward target ids | 20 TP / 1 FP / 66 gold -> P 0.95, R 0.30 | 64 TP / 0 FP / 66 gold -> P 1.00, R 0.97 |

The new resolver's two misses are N.Y. UCC "Section 8--404" and "Section 8--405": the double hyphen stops the
number at "8". The current resolver's false positive is Cal. BPC § 11270 for "Section 11270 and following of the
Government Code".

Errors that produced no wrong outward id in this sample:
- **Two wrong self-targets.** "such subdivision six" (N.Y. PBA § 2050-P, meaning GML 120-w(6)) and "G.S. 59-68,
  subdivision (b)(2)" (N.C. § 59-71) both resolve to the citing section.
- **About 5 wrong pinpoints in list continuations.** "RCW 48.110.030 (2)(a) and (b), (3), and (4)" gives (2)(3)
  and (2)(4). "subsection (c)(2), (3), or (4)" gives (3) and (4).
- **A detection gap.** In "(2)(a) through (c), (3), and (4), 48.110.040, and 48.110.073 (2)", the list stops after
  (2)(a).
- **Wrong kinds:**
  - Florida land-survey "Section 23, Township 14 South" is read as a statute section (16 Fla. sections contain
    this pattern).
  - "federal or State program allowing a law" is read as federal law.
  - "Article 8280-581, Vernon's Texas Civil Statutes" is read as a Code of Criminal Procedure container.
  - Session laws ("chapter 274, Laws of 2006"; "Chapter 697, Acts of the 62nd Legislature") are read as
    containers.

## 5. Systematic false targets the gold does not contain (targeted corpus scans)

I sampled sections that contain each construction and ran `xref.references` on them. "False ids" means index
section ids returned for text that names no section of the index.

| construction | where | sections with it | sample | result |
|---|---|---|---|---|
| "subdivision (e) of Section 4 of Article VII of the California Constitution" | ca | 1,044 | 80 sections, 101 phrases | 26 phrases resolve to the citing code's § N (Cal. BPC § 4, Cal. GOV § 3, Cal. RTC § 35) |
| same, Illinois Constitution | il | 471 | 80 sections, 88 phrases | 15 resolve to the citing act's Section N (20 ILCS 3105/6, 225 ILCS 340/6) |
| "Section 7 of Chapter 129 of the Statutes of 1999" (uncodified session law) | ca | 279 | 80 sections, 143 phrases | 93 resolve to the citing code (Cal. PEN § 7, § 5) |
| "section 1 of chapter 1040 of the laws of 1981" | ny | 40 | all, 40 phrases | 17 resolve to the citing law's § 1 |
| "Section 8--404" (double hyphen) | ny | 575 | 80 sections, 174 phrases | 167 not resolved, number read as "8" |

Extrapolated: about 340 + 320 false edges in California, about 90 in Illinois and 17 in New York. These are small
next to the hundreds of thousands of correct edges, but systematic. About 1,200 New York references are missed.
The pass1 `named_act` rule catches session laws only in the Maryland form ("Chapter N of the Acts of YYYY"). The
constitution rule needs "Section N, Article X" with a comma. Neither form above occurs in the gold.

A corpus-wide count was not run: the permission system refused the job, since a benchmark is using the container.
The figures above come from samples.

Minor: the code table still has an empty root for "Tex. Insurance Code - Not Codified" (68 rows), the same bug
class as the fixed Health and Safety Code one. Speed is fine: 4.7 s for the largest section, 526k characters.

## Verdict

The report's numbers are reproduced exactly, and the gold labels I checked are sound.
- On random held-out sections the target precision (64/64) and recall (64/66) hold up. The improvement over
  `cited()` (recall 0.30) is real.
- The in-sample precision of 1.000 does not carry over to every construction. Constitution citations of the form
  "Section N of Article X of the ... Constitution" and uncodified session-law citations ("Section 7 of Chapter
  129 of the Statutes of 1999") produce false edges into the citing code. New York's "Section 8--404" style is
  missed.
- Role accuracy (69.6%) is in-sample and partly fitted to gold passages; treat about 65% as the realistic figure.
- Generic detection without the one-sentence phrases is 71%, not 81%.
- The explanation for the Maryland Vehicle Law miss is wrong: the gold target is the short title, and the
  resolver already holds that anchor.

## Re-check of the fixes, 2026-10-10

An adversarial re-check of the fixes to `lexflow/law/xref.py`, `tests/test_xref.py` and `scripts/xref_eval.py`.
- All runs were read-only in `lexflow-app-1`. I edited no file except this note and wrote nothing to the network.
- The original resolver is the fixer's snapshot (`xref_orig.py`). It was loaded under another module name, side
  by side with the current one.
- My `/tmp/xrc_*` files in the container are deleted.
- Seeds and patterns differ from the ones the verifier and the fixer used.

### Confirmed fixed

| finding | re-check |
|---|---|
| Constitution citations give false ids | Seed 777, broader patterns, 0 false ids: CA 82 phrases in 60 sections (my pattern flagged 2, both neighbouring real container references), IL 69, NY 73, FL 110, TX 74. |
| Session laws give false ids (the forms named above) | 0 false ids: CA "Statutes of" 85 phrases, WA "Laws of" 81, TX "Acts of the" 88, FL "Laws of Florida" 58. Digit-form NY "section N of chapter M of the laws of" also gives none. Other NY forms do not: see below. |
| "Section 8--404" | 157 of 158 NY double-hyphen phrases resolve. The one left is Partnership Law "section 8--103(c)", which inherits no "of the uniform commercial code". |
| Held-out: the 30 sections | I took the verifier's own 30 sections by citation from its output files; I did not re-draw them. Outward ids go from 64 to 66. The only new ids are UCC § 8-404 and § 8-405; none is lost. |
| Held-out errors | All fixed in the real sections: the PBA § 2050-P anaphor, G.S. 59-68(b)(2), the RCW 48.110.030 pinpoints and the full list, Md. (c)(3)/(c)(4), the survey text in Fla. § 601.091, IL "federal or State program", Vernon's, and the TX and WA session laws. |
| Empty code root | No prefix has an empty root in any of the ten tables. "Tex. Insurance Code - Not Codified" is rooted at "TX Code / Code i1". |
| Maryland Vehicle Law | Real index: named_act, target § 11-206. The 19 member units run from Title 11 to Title 27, with 18.5 and 18.7. Md. outward recall on the gold is 1.00. |
| Gold numbers in the fix report | They reproduce exactly. Outward P / R 1.000 / 0.969 (439/439/453). Detection is 99.9% specific and 78.1% generic. Role 70.1%: 69.2% without N.Y. LLC § 1101, 68.6% with the fee rule off. Kind 86.1%, unit 97.9%, pinpoint 97.0%, 17 spurious. |
| Tests | 82 passed in `test_xref.py`, 106 with `test_links.py`. Of the 82, 40 fail on the original resolver. |
| No new false edges | Fresh random diff, seed 8080, 500 sections (50 per state): 778 outward ids become 782. One false IL constitution edge is lost. Five ids are gained, all correct: four UCC, and Cal. GOV § 16720 for "the State General Obligation Bond Law". |
| Anchored search = full scan | 1,199 texts, 2,398 pattern runs, 619 matches: 0 differences. |
| Speed | Same process, alternating, 82 gold sections: 57.9 ms per section old, 60.0 ms new. The machine was loaded. |

### Not fixed, or only partly

- **New York session laws cited through a part.** "Section 3 of part A of chapter 57 of the laws of 2009" still
  resolves "section 3" in the citing law, and its "part A of chapter 57" becomes a container that swallows the
  session-law span. This form appears in 41 sections (56 phrases); 41 of the phrases give a false id. A list of
  spelled-out items before a session law ("section one or section two of chapter seven hundred seventy-two of the
  laws of ...") gives the first item a false id in 5 sections, because the list rule compares digit numbers only.
  The fix report's "New York 'laws of': 17/21 -> 0" holds for the digit form only. With a broader pattern, 16 of 92
  phrases in 60 sections still give false ids.
- Already listed by the fixer and confirmed: N.C. "Article 33C of Chapter 143" (N.C. recall stays 0.61), the N.C.
  57D-10-02 heading-line "other law", and `cited()`.

### New problems

- **Regression in federal-law detection.** The pattern that fixed "federal or State program allowing a law"
  stops at an "and" or "or" after "federal". So "federal or state law" now yields only a generic "state law".
  "comply with all federal and state laws" and "federal and state requirements" now yield nothing. In 149 sections
  that contain "federal or/and state", federal references fall from 264 to 182. The gold does not show this. The
  guard against an article or verb before the head word fixes the reported case on its own.
- **Bill sections in California.** These forms resolve into the citing code, as before:
  - "Section 8 of the act that added this section": 47 sections, 76 phrases, 39 false ids (Cal. HSC § 8, EDC § 90,
    GOV § 5 ...);
  - "Section 1 of Assembly Bill 2257": 5 sections, 4 false ids.
  - The note above did not report these.
- **The fee rule fires outside fee schedules.** In 120 random sections that have a "For ..." clause naming money,
  the rule changes 14 of 1,659 roles:
  - 7 are real fee items (Tex. BOC §§ 4.152, 4.153, 4.159; RCW 90.03.470);
  - 1 is debatable (Cal. HSC § 25299.41);
  - 6 are Cal. GOV § 17581.9 "For purposes of making the computations required by Section 8 of Article XVI ...,
    N dollars", which turns authority into scope.
  - The fixer's 36 of 41 came from fee schedules only.
- Minor:
  - The xref.py list of removed phrases leaves out "other statute of limitations" (6 sections).
  - Generic detection (78%) still leans on two rare alternatives: "applicable statutory law" (6 sections) and
    "rules of law and equity" (11).
  - No test pins the full-stop span fix.
  - Article-less "subdivision (d) of Section 16 of the California Constitution" (Cal. ELEC § 8228, the statute's
    own slip) still gives a false id.

## Re-check 2, 2026-10-10

A second adversarial re-check, of the fixes to the items above.
- All runs were read-only in `lexflow-app-1`, one at a time. I edited no file except this note and wrote nothing to
  the network.
- "orig" is the original resolver and "base" is the fixer's pre-change snapshot. Both were loaded under other module
  names, side by side with the current code ("new").
- Seeds and scan patterns are new; where a form occurs in fewer sections than the sample size, every section was
  read.
- My `/tmp/xr2_*` files in the container are deleted.

### Reproduced

| item | result |
|---|---|
| Tests | `test_xref.py` 102 passed; with `test_links.py`, 126 passed and 4 skipped. On base, 19 of the 102 fail; on orig, 56 fail, including the full-stop test. |
| Gold | `xref_eval.py --resolver new --failures 3` matches the fixer's output line for line, apart from timing (39.9 ms per section). |
| Held-out 30 sections | Outward ids are 64 (orig), 66 (base) and 66 (new). Nothing changes between base and new at the reference level. |

### Confirmed fixed (fresh samples)

"Ids" means any index id on a reference that overlaps the cited section words.

| form | sections / phrases | phrases with ids, base -> new |
|---|---|---|
| NY "section N of part X of (a/the) chapter ...", seed 2024 | 41 / 56 (all but one section over 200k characters) | 40 -> 0. One more scan hit is a real "this section". |
| NY list before a session law, digits or words | 39 / 55 (all) | 7 -> 0. The one hit left is a real self-pinpoint, "subdivision twelve, as added by ...". |
| NY broad "laws of" scan, seed 4321 | 80 of 193 / 106 | 20 -> 5 into other sections. Four of the 5 are the "a chapter" form below, and one is a real § 94. |
| NY bare "part X of chapter M of the laws of" | 15 / 21 (all but one large section) | 0 -> 0. The kind is now session_law instead of container. |
| NY "laws of New Jersey" | 1 / 1 | 1 -> 0 |
| CA "Section N of the act that added/adding/amending ..." | 49 / 78 (all) | 41 -> 0 |
| CA "act enacting this section", "initiative", "measure" | 7 / 7 | 6 -> 1. Left: Cal. ELEC § 2123, "Section 11 of the initiative act approved by ..." -> § 11. |
| CA "Section N of Assembly/Senate Bill M" | 5 / 9 (all) | 4 -> 0. Extraordinary-session numbers ("X1 2") do not occur. |
| TX "Section N of the Act enacting this chapter", ", H.B." | 80 of 618 / 141 | 0 -> 0. The kind is now session_law. |
| Federal, seed 6061: 200 sections that contain "federal" (not only "federal or/and state") | 200 | Federal refs: 181 orig, 169 base, 177 new. |
| Fee rule, seed 1212 | 120 / 1,686 refs | Roles changed: 14 with the base rule, 13 with the new rule. |
| Random diff, seed 2468, 40 sections per state | 400 | Outward ids: 610 base -> 610 new, none lost or gained. |

Federal detail:
- New lacks 7 of orig's spans:
  - 4 are not federal law: "federal law enforcement agency", "federal or military law enforcement agency", "federal
    government grants of money appropriated under any act" and "federal project as defined in the public housing
    law";
  - 3 were over-long and are now shorter and correct.
- The 40 new federal spans I sampled at random all name federal law.

Fee rule detail:
- The change that is gone is Cal. EDC § 84321.63, "For purposes of making the computations required by Section 8 of
  Article XVI".
- 11 of the 13 changes are fee or amount schedule items: Md. CL § 14-1209; Tex. Ins. § 202.051 (2); Tex. BOC
  § 4.152; RCW 21.20.340 (4); Va. § 19.2-163 (2); D.C. § 47-4676.
- 2 are debatable: D.C. § 10-1601.03, a bond cap, and Tex. Tax § 31.032, "For the 2009 tax year, the limit ...".

Random diff detail:
- The 7 references that change between base and new all improve:
  - "Section 2 of the Act enacting this chapter" (2) is now session_law;
  - "federal or member state law" is now federal;
  - "the federal Law Enforcement Officers Safety Act of 2004" (2) is now whole.
- From orig to new, 10 ids are lost and all were false (Cal. WIC § 14; Tex. CCP § 4 × 9). One is gained: Va.
  § 8.1A-101 for "the Uniform Commercial Code".

### Not fixed

- **New York "section N of a chapter of the laws of YYYY"** (with "a", not "the"). It occurs in 12 sections and 16
  phrases in the whole corpus, and 12 of the phrases (9 sections) give a false id in the citing law, the same as base.
  Examples: "section four of a chapter of the laws of two thousand five known as ..." -> N.Y. STF § 4; Bnk. § 14-E
  -> § 1; Tax § 1261 -> § 1; PBO §§ 17, 19 -> § 13; STF §§ 61, 74, 88, 92-E, 92-F. The session-law pattern
  accepts only "the chapter of the laws of". The broad scan's 4 remaining false ids are all this form.
- "section two of such part" (already listed by the fixer). It occurs in 4 sections and 9 phrases. 4 phrases still
  carry ids: STF § 92-II -> § 2, § 92-JJ -> § 7, and § 92-GG*2 twice to itself.
- Rare: "Section 2 of Proposition 184" (Cal. PEN § 1170.125, 2 phrases -> PEN § 2) and the ELEC § 2123 initiative
  act above.
- Not judged: Illinois "Section N of this amendatory Act" (7 sections, 9 phrases) resolves into the citing act,
  before and after the fix. Amendatory acts usually carry the codified numbers, so most of these ids may be right.
- Carried over and not re-run: N.C. "Article 33C of Chapter 143" (the gold eval still shows N.C. recall 0.61), the
  57D-10-02 heading-line "other law", Cal. ELEC § 8228, and the rare generic alternatives.

### New or remaining weaknesses (no false ids)

- **The federal pattern still allows verbs and prepositions inside the span.** "The federal grant funds are subject
  to State law" and "the federal agency in accordance with State law" are each read as one federal span. Orig and
  base do the same. "federal or State court rules" is now federal; base found nothing there.
- **The "law enforcement" guard misses the hyphenated form.** "federal or State law-enforcement agency" now gives
  "federal or State law" as federal; base gave a generic "State law". The hyphenated form occurs in 94 sections and
  133 phrases (Va. 74 sections, N.C. 16). Of the 40 phrases I checked, 21 give a "federal law" or "State law" span.
- **Latent: the list rule reads the session law's first section number from 160 characters past the session law's
  start, not from within its span.** So "section 5 or part A of chapter 57 of the laws of 2009, as amended by section
  3 of this chapter" makes "section 5" session_law on the strength of "section 3", which comes after the span. Base
  has the same window. The change that makes a bare "part A of chapter 57" a session law exposes it. No corpus phrase
  of this shape was found (0 in New York).

## Re-check 3, 2026-10-11

A third adversarial re-check, of the fixes to the Re-check 2 items.
- All runs were read-only in `lexflow-app-1`, one at a time. I edited no file except this note and wrote nothing to the
  network.
- "base" is the round-2 code: a copy of `xref.py` from before this round, still held in another agent's scratch tree
  in the container. The current tests fail 19 of 125 on it, the figure the fixer gives for its own snapshot. "new" is
  the current code. Both were loaded side by side.
- Scans read every section that has the form, unless a sample is named. My `/tmp/xr3_*` files in the container are
  deleted.

### Reproduced

| item | result |
|---|---|
| Tests | `test_xref.py` 125 passed; with `test_links.py`, 149 passed and 8 skipped. On base, 19 of the 125 fail. |
| Each fix pinned | I reverted each change on its own (34 reverts) and re-ran the tests. Every fix this note asked for is pinned by at least one test. The changes that are not pinned are listed under "Minor" below. |
| Gold | On the 82 gold sections every reference is the same on base and new: 895 each, with the same span, kind, code, ids, pinpoint, role, unit, confidence and note. So the `xref_eval.py` figures cannot have changed. I did not run the eval script itself. |

### Confirmed fixed

"False ids" means index ids on a reference that overlaps the cited words, for text that names no section of the index.

| form | sections / phrases | false ids, base -> new |
|---|---|---|
| NY "section N of a chapter of the laws of YYYY" | 13 / 16 | 12 phrases (9 sections) -> 0. One more hit is a real "this section" (N.Y. CRC § 101). The docstring's "12 of 14 phrases (11 sections)" matches neither this count nor Re-check 2's. |
| NY "section N of such/said part" | 4 / 7 | 4 (3 sections) -> 0. N.Y. SOS § 384-B now gets N.Y. FCT § 635, which is right: its index path is Article 6 / Part 1-A. Of the other nine states only Washington has the form (3 phrases), and nothing changes there. |
| CA "Section N of Proposition M", "... of the initiative act ..." | 11 / 12 | 4 -> 1 (see below). Seven "Sec. 117 of Proposition 1" (Cal. WIC) are now session_law; base found no reference there. |
| "law-enforcement" (hyphenated) read as federal or generic law, sections under 200,000 characters | 1,389 / 3,684 | 144 -> 0, exactly the docstring's figures |
| "other / by / general / under law enforcement", same size limit | all ten states: 969 / 1,262 | 688 -> 0. In the docstring's five states, 195 -> 0 as stated, but my pattern finds 393 phrases there, not 430. |
| NY starred citations: a starred row's "section N" read as the row itself | 1,044 starred rows (only New York stars a citation) | 7 -> 0 (N.Y. RSS §§ 89-N\*2, 89-S\*2, 89-T\*2, 89-V\*2, 604-C\*2; N.Y. STF § 92-GG\*2 twice) |
| NY repeated-letter numbers ("§ 160-aaa"), sections under 150,000 characters | 159 / 330 | 170 with another section's id -> 0. 325 now get the section named; the docstring says 324. No other state writes such numbers. |
| Federal names: seed 2626, 400 sections that contain "federal" (40 per state, under 60,000 characters) | 400 | Federal refs 428 -> 427. Of the 2 lost spans, one is not law ("federal government of publicly owned treatment works ..."). The other was an over-long span around a real federal law ("federal GI bills and in compliance with all applicable eligibility requirements", N.Y. EDN § 6206). The one gained is "federal 21st Century Cures Act". Outward ids are unchanged. 40 random new federal spans all name federal law. |
| Random diff: seed 31337, 50 sections per state (200 to 120,000 characters) | 500 | References 2,600 -> 2,585; outward ids 861 -> 862. All 9 sections that differ improve: in 7 NY sections starred labels and version notes stop being references, 2 "other law enforcement" generics go, and the one new id (N.Y. TAX § 1202-O\*3 -> § 1230) is right. |

Also confirmed: tests pin the window fix and the "or one of its affiliates" guard. No corpus phrase of the window shape
exists. The Re-check 2 figures that the docstring quotes match that section.

### Not fixed, or only partly

- **A California initiative's sections cited as a range.** "Sections 2 to 6, inclusive, of Proposition 36" (Cal. PEN
  § 667.2) still resolves to Cal. PEN §§ 2, 3, 4, 5 and 6, on base and new. The ", inclusive," between the range and "of
  Proposition" stops the session-law pattern. It is the only such phrase in California: I scanned the 1,307 sections
  that hold "inclusive" and a session-law word, for a range before Statutes, act-that, bill, Proposition and initiative
  forms. So the docstring's "3 of 3 -> 0" holds for the phrases it scanned, but not for the whole form.
- **The guard for "or one of its affiliates" is narrow.** After a New York section, "..., or one of the entities ...",
  "..., and one of the members shall ..." and "..., and two of such members ..." still give list items with the citing
  law's § 1 or § 2, on base and new. A sample of 3,000 NY sections (under 60,000 characters) has no such phrase, so
  this is rare.
- Carried over and not re-run: Illinois "this amendatory Act", N.C. "Article 33C of Chapter 143", the 57D-10-02
  heading-line "other law", Cal. ELEC § 8228, the rare generic alternatives and New York "such chapter". The 30
  held-out sections were not re-read, because their list is gone.

### New problems

- **Regression: a section of a federal act whose name holds a stop word now falls back to the citing code.**
  `code_qual` (" of the federal ... act") now uses `FED_ACT_WORD`. That refuses the words of `_FED_STOP`, which
  include "every", "no", "the", "its" and words ending in "enforcement".
  - Scan: every section in the ten states with a section citation before " of the federal " (California 1,219
    phrases). In California, phrases with ids go from 83 to 89; the other states are unchanged.
  - All 6 new ids are false:
    - Cal. EDC § 44690 and § 64001 (twice): "Section 1003(e)(1)(A)/(B) of the federal Every Student Succeeds Act" ->
      Cal. EDC § 1003;
    - Cal. VEH § 11752 (twice): "Section 31301 of the federal Moving Ahead for Progress in the 21st Century Act" ->
      Cal. VEH § 31301;
    - Cal. BPC § 19641.2: "Section 501(c)(3) of the federal Internal Revenue Code or its compliance with ..." -> Cal.
      BPC § 501. Base's span ran on to a later "Act", but its kind was federal.
  - Some citations now get the wrong kind but no id:
    - "Section 1114(b)(6) of the federal Every Student Succeeds Act" (Cal. EDC § 64001);
    - "Section 221 of the federal Small Business Regulatory Enforcement Fairness Act of 1996" (415 ILCS 5/42);
    - "section 1413 of the Federal Act" (D.C. § 31-3171.04).
  - On text snippets, base read "Section 1111 of the federal No Child Left Behind Act of 2001" and "Section 5362 of
    the federal Unlawful Internet Gambling Enforcement Act of 2006" as federal. New reads the second as Cal. EDC § 5362.
  - No test pins the `code_qual` change: reverting it leaves all 125 tests passing. The fix report does not mention it.
- **The star fix's main effect is not reported.** In the 1,044 starred NY rows, outward ids go from 325 to 1,548
  (new ids in 259 rows). 39 of 40 new ids I sampled at random are right. The false ones come from forms that the old
  prefix hid:
  - N.Y. RSS § 445-F\*2: an editor's note "(as amended by ch. 35/2005 § 2)" -> N.Y. RSS § 2;
  - N.Y. EXC § 837-M\*2: "section seven of executive order number sixteen of the mayor ..." -> N.Y. EXC § 7, and "section
    one of executive order seventy-two" -> § 1;
  - N.Y. TAX § 1439-BBB\*2: "section twenty-three of the municipal home rule law" -> N.Y. TAX § 23.

  The docstring's random diff ("529 -> 529") gives no hint of this change.
- **Older false-id forms found this round.** The fixes did not cause them; base gives the same.
  - **New York spelled-out lists joined by "and" are read as one number, the sum.**
    - Examples: "sections three and four of this chapter" -> § 7; "sections ten and eleven" -> § 21; "sections
      twenty-four, twenty-five and twenty-six" -> § 24 and § 51.
    - Cause: `NUMWORDS` allows "and" between any two number words, not only after "hundred" or "thousand".
    - 929 NY sections (under 200,000 characters) have the form. In a sample of 150 of them, 176 of the 185 phrases are
      read as one section number. 18 give a false id, because the summed section exists: N.Y. STF § 71-A "sections
      seventy-one and seventy-five" -> § 146; N.Y. EXC § 156-G "sections seventeen and eighteen" -> N.Y. PBO § 35.
      The rest lose both real targets.
    - Of the problems in this section, this one affects the most edges.
  - **New York editor's notes that cite session-law sections**, "expires per ch. 627/2007 §22", "§10 of ch.
    339/1972". These occur in 41 phrases in 20 sections, and 34 give the citing law's § N (N.Y. EDN § 509 -> § 22). The
    fixer chose to keep other "\* NB" notes as text. That is right for notes that point at the law's own sections, but
    not for these.
  - **"Section N of the federal act", with "federal act" in lower case as a defined term.** In California, 36 of 168
    phrases (82 sections) give the citing code's § N (Cal. GOV § 100501 "Section 1301 of the federal act" -> Cal. GOV §
    1301). In New York, 8 of 9 do (N.Y. PBH §§ 268-C, 268-D -> §§ 1302, 1311).
  - **New York law names the table lacks.**
    - "of the municipal home rule law": 60 phrases in 49 sections, with false ids 35 -> 38 (N.Y. GCT § 2 "section
      twenty-three of the municipal home rule law" -> § 23).
    - Others: "of the agriculture and markets law" (N.Y. PBH § 1311 -> § 260) and repealed laws such as "the general
      corporation law".
    - In a sample of 2,500 NY sections (under 100,000 characters), 11 phrases got such an id.
- Minor:
  - The session-law pattern now accepts "a part", and no test pins it. Its only corpus effect is a wider span:
    RCW 41.16.920 "authorized as a part of chapter 5, Laws of 1959" now gives the span "a part of chapter 5, Laws of
    1959".
  - Test gaps. Each of these changes can be reverted with all 125 tests passing:
    - the preposition stop list `_FED_PREP` (the test sentence already stops at "accordance");
    - "general law enforcement" and "under law enforcement";
    - `code_qual`.

    The optional star in the three label patterns is pinned only when all three are reverted together.
  - Docstring wording:
    - "A word for police" ends a federal name only as "enforcement" or "law-enforcement". "Police" itself is not a stop
      word: "the federal police rules" is federal.
    - The docstring lists "federal courts to comparable antitrust statutes" (D.C. § 28-4515) among spans that "name no
      federal law". It refers to federal antitrust law without naming it, so dropping it is defensible.

### Verdict

- Six of the seven Re-check 2 items are fixed in every phrase I found. The seventh, California initiative sections, is
  fixed except for one range phrase (5 false ids).
- The four extra fixes hold, and the gold output is unchanged, reference for reference.
- One change the report does not mention is a regression: the `code_qual` change gives 6 false ids in 4 California
  sections, and no test covers it.
- The star fix adds about 1,200 outward ids. Nearly all are right, and the docstring does not report them.
- The largest open defect is older: New York's "sections X and Y" are added together.
