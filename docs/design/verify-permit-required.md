# Verification: the `permit_required` decision model

Checked 2026-10-10 (US Eastern; 11 October UTC). Under review: `out/design/permit_required.dmn` (264,822 bytes),
`out/design/check_permit_required.py` and [permit-required.md](permit-required.md). The plan they implement is
[data-expansion.md](data-expansion.md) (§0 N2, §1 E1 and E5, §2.1, §3.1) and
[data-building-codes.md](data-building-codes.md) (§1.3 to §1.6, §4.2). Nothing was edited except this note.
**This is not legal advice.**

**How it was checked.**

* **The text.** Each section below was read in full from the indexes in `lexflow-app-1` (open-us-law v2026.09.1; the
  regulations indexes were built 2026-10-11 between 01:40 and 01:45 UTC):
  * Virginia: 13VAC5-63-10, -20, -80 and -200, and Va. Code §§ 36-97, 36-98 and 36-105;
  * DC: 12-A DCMR 105, 12-B DCMR 101, and 10-C DCMR 300 to 304 and 320;
  * North Carolina: G.S. 160D-1110, 143-138 and 160D-947.

  The section counts the note gives (22,396 VA, 22,914 DC, 21,314 NC) match the indexes' `meta` rows.
* **The quotes, checked independently.** A separate script cut each subdivision out of the text with its own
  boundaries, not the checker's outline parser. Results:
  * all **145 of 145** model quotes lie exactly (no whitespace folding needed) inside the subdivision they cite;
  * every `url` and `actId` equals the index row's;
  * all **66 of 66** curly-quoted spans in the design note are verbatim state text (an ellipsis splits a quote into
    parts, each verbatim);
  * the note's 19 straight-quoted spans are the question, the live history note, fixture text and JSON keys. That
    follows the note's own rule that local-page text goes in straight quotes.
* **The checker.** It was run as its docstring says: a `mktemp` directory in the container, `TMPDIR` passed, and the
  directory removed afterwards. Result: **ALL CHECKS PASSED**, 95 `[ok]` lines, 0 FAIL, 1 min 46 s wall time (the
  report says about 64 s).
* **The rules.** All 63 rules were read against the text (the tables at the end).
* **The fixtures.** The three discovery fixtures were read, not changed.
* **Live reads.** Read-only, with the User-Agent `lexflow-research/0.1 (https://github.com/alibama/lexflow)`, and
  nothing stored:
  * `law.lis.virginia.gov/robots.txt` answers 301, redirecting to `/robots.txt/`, which is 404. So the report's
    "404" holds after the redirect.
  * One read of the [13VAC5-63-80 page](https://law.lis.virginia.gov/admincode/title13/agency5/chapter63/section80/).
    Its Historical Notes end "Volume 40, Issue 9 , eff. January 18, 2024", and 8 quoted spans matched.
  * `www.ncleg.gov/robots.txt` gives `User-agent: *` a `Crawl-delay: 2`, and has no Disallow line for
    `/EnactedLegislation/` or `/`.
  * One read of [G.S. 160D-1110](https://www.ncleg.gov/EnactedLegislation/Statutes/HTML/BySection/Chapter_160D/GS_160D-1110.html),
    3 s after robots.txt. 5 quoted spans matched, "shed" does not occur, and the history ends "2024-49, ss. 1.4(a),
    1.5."
  * **Disclosure:** following the robots.txt redirect sent two requests to `law.lis.virginia.gov` less than a second
    apart, so the one-request-per-second limit was missed once, by the redirect.
* **Not done.** No benchmark, job or Ollama call. `lexflow/law/xref.py`, `lexflow/law/terms.py` and
  `curated/places/va/*` were neither opened nor touched. No ICC or other model-code text was read or stored.

## Verdict

The model is careful and mostly right:

* the four named cases (A1, A2, A3, B1) are correct;
* every threshold and boundary matches the text;
* every quote is verbatim and in place;
* every number the report gives was reproduced, except the run time.

The checker cannot catch the problems below, because its cases encode the same readings as the model. Mutation
testing measures how strong the cases are, not whether the reading of the law is right. Fix these before the model is
used or published:

1. **W1.** DC deck resurfacing in a Flood Hazard Area is answered `depends`. The text requires a permit application
   either way, so the answer is `yes`.
2. **W2.** DC `fence_repair` includes "replacement in kind", but item 4 exempts only "Repair in kind".
3. **W3.** NC deck resurfacing answers `no` for two-family dwellings, but the $40,000 exclusion covers only a
   "single-family residence".
4. **M1.** Trade work (wiring, plumbing, gas, mechanical) has no input, and the `no` answers carry no caveat.
5. **M2.** Virginia's whole-code exemptions in 102.3 (storage containers, farm buildings, playground equipment) are
   missing. A shipping-container shed or a farm shed gets a wrong `yes`.
6. **W4.** The model treats the building official's discretion inconsistently: item 13 gives `yes`, item 14.11 gives
   `depends`. r8's reasoning also misses the VCC's definition of "Construction".

---

## Wrong

### W1. DC deck resurfacing in a Flood Hazard Area: `depends` should be `yes` (r33)

* **Model.** r33 has no `flood_hazard_area` condition, so `jurisdiction="dc", project="deck_resurfacing",
  flood_hazard_area=true` answers `depends` ("It may be an ordinary repair, which needs no permit … Ask the code
  official"). The checker's slice confirms it: "dc deck_resurfacing 1 rules: (none)".
* **Text.** 105.2.2 ("Permits are not required for ordinary repairs …") is part of Section 105.2. 105.2 opens: "This
  Section 105.2 sets forth exemptions from permit requirements, subject to historic and Flood Hazard Area
  restrictions set forth in Sections 105.2.5 and 105.2.6 respectively."
* 105.2.6 applies whenever the work "would qualify to be exempted from permit requirements pursuant to Section 105.2
  of this chapter". Unlike 105.2.5, it has no list limiting it to the Building items. 105.2.3's exception ("for all
  work described in Sections 105.2.5 and 105.2.6") also treats the two limits as reaching exemptions outside the
  Building list.
* **Either way, an application is required:**
  * if the resurfacing is an ordinary repair, it is exempt only subject to 105.2.6: "an application for a permit
    subject only to review by the Floodplain Administrator shall be required";
  * if it is not, 105.1 item 1 requires a permit to "repair" a structure.
* **This contradicts the report**, which says 105.2.6 "displaces every exemption in the same way". The model does
  so for items 4, 8, 10 and 13 (r23, r24, r30, r37, r38, r42, r43), but not for 105.2.2.
* **Fix.** Split r33 on `flood_hazard_area`. When it is true, answer `yes`, with an exemption such as "12-A DCMR
  105.2.2, not available under 105.2.6" and the 105.2.6 quote. Add a case, for example "B13b: DC: replacing deck
  boards in a Flood Hazard Area: yes". Then update the note's Summary row and §2.2, which list no DC questions for
  `deck_resurfacing`; `flood_hazard_area` becomes one.
* Historic status does not change r33: 105.2.5 lists only Building items, and ordinary repairs are not among them.
  HPO review stays in `other_approvals` (10-C DCMR 304.1(h): "Construction or replacement of a … deck").

### W2. DC `fence_repair` covers "replacement in kind", but item 4 exempts only repair (r35)

* **Model.** The input description defines `fence_repair` as "repair or replacement in kind of an existing fence".
  r35 answers `no`, cites item 4 as explicit, and quotes "Repair in kind of existing fences."
* **Text.** DC separates the two ideas. Building item 7 is "Replacement in kind of one of the items listed hereafter",
  with its own definition (""replacement in kind," means replacement with a feature of like material that replicates
  the existing feature …"). Its list (7.1 to 7.7) does not include fences. Item 4 says only "Repair in kind".
* **Against that,** 105.2.5 describes item 4 as "4. Repair or replacement of fences, except as deemed an ordinary
  repair", which suggests the drafters read item 4 as reaching replacement.
* **So** replacing a whole fence in kind outside a historic district is, at best, a reading. It is not the explicit
  `no` the model gives, and a fence permit (105.1.1, "7.4 Fences.") is the other plausible answer.
* **Fix.** For DC, either limit `fence_repair` to repair in kind and send replacement to r34 (`yes`), or add a
  replacement case answered `depends`, with the item 4 / item 7 / 105.2.5 tension as its reading note. Virginia is
  unaffected: item 5 covers "Fences of any height", and the VCC's "Construction" includes repair.

### W3. NC deck resurfacing: `no` is extended to two-family dwellings (r48)

* **Model scope** (input `project`; note §2.2): "a detached one- or two-family dwelling or a townhouse". r48 answers
  `no` at $40,000 or less with no condition on the dwelling type.
* **Text.** Both exclusions reach only work "in any single-family residence, farm building, or commercial building"
  (160D-1110(c); 143-138(b5) says "single family residence"). A two-family dwelling is none of these.
* **So** for a duplex, (c) does not apply. On the model's own logic (r49), the answer is a permit (a reading) or
  `depends`, not `no`. Whether a townhouse unit is a "single-family residence" is itself a reading. It probably is,
  but it is not explicit.
* **Fix.** Add a `dwelling` input (single-family, two-family, townhouse) to the NC rows, or narrow the NC scope to
  single-family residences in the input description and the note. Add a duplex case.

### W4. The building official's discretion is handled inconsistently, and r8's reasoning misses a definition

* **Same posture, different answers.** The VCC defines "Construction. The construction, reconstruction, alteration,
  repair, or conversion of buildings and structures." (13VAC5-63-200). So 108.1 item 1, "Construction or demolition
  of a building or structure", already reaches repairs. That puts deck resurfacing (r8) and pool-fence repair (r12) in
  the same posture as a new deck (r7):
  * the permit duty applies by default;
  * the only way out is an item the building official must "deem" to apply: item 13 for construction, item 14.11
    for repair.
* The model answers r7 `yes` (with the item 13 caveat) but r8 and r12 `depends`.
* **The model's own definition** of `depends` is "the answer turns on a determination the model does not take as an
  input: the building or code official's". Read literally, it covers r7 too, and every other Virginia `yes`, since
  item 13 applies to any construction work.
* **r8's basis and reading note** rest on a different point: "108.1 requires a permit for alterations involving a
  structural component", and "whether deck boards are a 'structural component' is for the building official". The
  definition makes that question unnecessary: a repair of a structure is "construction" either way.
* **Fix.** Say the principle in the decision's description. One consistent choice:
  * `yes` where the text sets a permit default that the official may lift (items 13 and 14.11);
  * `depends` where the text exempts work that the official may pull back in (Exception 2), or where the law on disk
    does not settle the question.

  Under that rule, r8 and r12 become `yes` with a 14.11 caveat. If `depends` is kept for 14.11, say why repair
  differs from construction. Either way, cite 13VAC5-63-200 for "Construction" and drop the "structural component"
  reading.
* The task's test ("depends where the text leaves it to the building official") is met for Exception 2 (r2, r10,
  r14, r17), item 14.11 (r8, r12), DC 105.2.2 (r33) and 105.2.5 item 4 (r36). It is deliberately not met for item 13
  (r7). That is defensible as a default, and it is what the plan wrote ([data-building-codes.md](data-building-codes.md)
  §4.2, rule 4), but it should be stated as a rule.

### W5. Smaller errors of fact or wording

* **Wrong cross-reference.** The DMN's `jurisdiction` description says "Local governments cannot change the VA or NC
  answers (docs/design/permit-required.md part 6)". Local amendments are part 5 of the note; part 6 is the place
  processes.
* **NC is overstated in the same sentence.** (b5) itself presupposes "any local variance thereof approved under
  subsection (e)". Under (e), a political subdivision may adopt floodplain management regulations, and fire
  prevention code provisions once "officially approved by the responsible Code Council". G.S. 160D-1128 (fire limits)
  also lets a county or city require "the permit of the inspection department" for any frame building, or addition,
  erected inside its fire limits. What a locality cannot do is require a permit that the $40,000 exclusion removes.
  The note's §5 states this correctly; the DMN description does not.
* **The run time** was 1 min 46 s here, not about 64 s. This is harmless.
* **"Names no IBC section."** The DMN mentions "Section 3306" 8 times. It appears in the state text of item 5 and in
  the `safety_barrier` description, which glosses it as "protection of pedestrians during construction". 3306 is an
  incorporated IBC section number, cited by state text. That is a fact, not model-code text, and the note's §8 item 3
  discloses it. The checker's claim should be read as "quotes no IBC text".

---

## Missing

### M1. Trade work: no input, and no caveat on the `no` answers

* **Virginia.** 108.1 item 1 requires a permit for "Installations or alterations involving … (v) water supply and
  distribution system, sanitary drainage system, or vent system; (vi) electric wiring; (vii) fire protection system,
  mechanical systems, or fuel supply systems". 108.2 item 1 exempts only low-voltage, broadband, monitoring and
  similar wiring. Item 2 exempts the shed; it does not exempt a circuit run to it.
* **DC.** 105.1 item 2 covers "Erect, install, enlarge, alter, repair, remove, convert or replace any electrical, gas,
  mechanical, or plumbing system", with trade permits in 105.1.1 item 4. Ordinary repairs exclude "electric wiring"
  (105.2.2).
* **NC.** 160D-1110(a)(2) to (4) require permits for plumbing, heating or cooling, and electrical work. (c)(2) and
  (c)(3) keep that work out of the $40,000 exclusion.
* **Failure.** A Virginia 200 sq ft shed with a new circuit gets `no` (r1, "Exempt: …").
* **Fix.** Add a `trade_work` boolean (any wiring, plumbing, gas or mechanical work), or put a fixed caveat in every
  `no` and `depends` basis (r1, r2, r9, r10, r13, r14, r16, r17, r21, r28, r35, r40, r48): "wiring, plumbing, gas or
  mechanical work needs its own permit". Virginia's `no` bases should also carry the 108.2 preamble: "this section
  shall not be construed to exempt such activities from other applicable requirements of this code".

### M2. Virginia's whole-code exemptions (13VAC5-63-20 D, Section 102.3)

* 13VAC5-63-20 is already a knowledge source, but only subsection B is used. Subsection D exempts these from the USBC
  altogether, so no building permit is needed:
  * "7. Playground or recreational equipment, such as swing sets, sliding boards, climbing bars, jungle gyms,
    skateboard ramps, and similar equipment."
  * "8. Industrialized buildings subject to the Virginia Industrialized Building Safety Regulations ( 13VAC5-91 ) …;
    except as provided for in Section 429 …"
  * "9. Farm buildings and structures, except for a building or a portion of a building located on a farm that is
    operated as a restaurant …". It adds that those "lying within a flood plain or in a mudslide-prone area shall be
    subject to flood-proofing regulations or mudslide regulations". The definition is in 13VAC5-63-200 and Va. Code
    § 36-97.
  * "11. Off-site manufactured intermodal freight containers, moving containers, and storage containers placed on site
    temporarily or permanently for use as a storage container."
* **Failure.** A 320 sq ft shipping container used as a storage shed gets r3 `yes`. So does a farm storage building
  over 256 sq ft (relevant to Albemarle, one of the three consumers). The text says neither is subject to the USBC. A
  large play structure could likewise be "playground … equipment" rather than a playhouse.
* **Fix.** Add inputs (`storage_container`, `farm_structure`), or state the exclusion in the project description and
  in the r3 and r4 bases.
* **Analogues.** DC Building item 12 ("Swings and other playground equipment accessory to detached one- and
  two-family dwellings and townhouses") is exempt, and 105.2.5 does not list it. In NC, 143-138(b4) puts farm
  buildings outside municipal jurisdiction beyond building rules; the NC rows are `depends` anyway.

### M3. DC public-space permits (12-A DCMR 105.2.4)

* "When the proposed scope of work would qualify to be exempted from permit … and the work is to occur wholly or
  partially on public space, the applicant shall be responsible for obtaining all public space permit(s) that are
  required by DDOT."
* This is in a knowledge source already cited, and it is exactly an "other approval". The DC rows of
  `other_approvals` (r5 to r8) do not mention it.
* **Fix.** Add a sentence and the quote to r5 to r8, or add an `on_public_space` input.

### M4. 10-C DCMR 303 is the section r29 turns on, and it is not cited

* 303.1: "Permits are required for work affecting historic landmarks and historic districts, including demolition,
  alteration, subdivision, and new construction as described in D.C. Official Code §§ 6-1104 through 6-1107. The
  requirements for a construction permit are governed by the D.C. Construction Codes (12 DCMR Chapter 1)."
* 303.3: "A separate historic preservation permit or certificate of appropriateness is not required."
* **Why it matters.** These two passages are the tension behind r29 (a DC playhouse in a historic district):
  * the first sentence of 303.1 says alteration needs a permit, and 304.1(h) makes "other site feature[s]"
    alterations;
  * the second sentence of 303.1, and 303.3, send the permit question back to 12-A DCMR 105, and 105.2.5 does not
    list item 13.
* So `depends` is right, but the basis should cite 303.1 and 303.3. 304.2(e) ("Replacement of retaining walls
  regardless of height") independently supports r41 and r43 and could be added. 10-C DCMR 320.1 (staff-delegated
  review of fences, decks, sheds and site features) is useful context for the process model.

### M5. Virginia's deck answer can rest on text, not only on an absence (13VAC5-63-10 G, Section 101.7)

* r7 rests on "no 108.2 item names decks". The USBC says why a model-code deck exemption cannot apply in Virginia.
  Section 101.7: "Any provisions of Chapters 2 through 35 of the IBC or any provisions of the codes and standards
  referenced in the IBC that address the same subject matter and impose differing requirements are deleted and
  replaced by the provisions of Chapter 1."
* Note 1 to 101.2 lists the IRC among those referenced codes. 101.6 items 1 and 2 give Chapter 1 precedence too.
* Citing 101.7 for r7 (and in the note's A3 paragraph) answers the "but the IRC says…" objection with state text,
  without naming or quoting any model-code item.
* The DC equivalent is already there: 12-A 105 begins "Strike Section 105 of the International Building Code in its
  entirety and substitute new Section 105", and 12-B R101.2 sends houses to it.

### M6. Smaller gaps

* **NC erosion control is uncited.** NC `other_approvals` r9 to r12 say "erosion control", but the only quote is
  160D-1110(a). The rule is (e): "No building permit shall be issued … for any land-disturbing activity … unless an
  erosion and sedimentation control plan … has been approved". Quote it.
* **VA ornamental column caps.** Item 6 adds that "Ornamental column caps shall not be considered to contribute to
  the height of the wall". `height_ft` should say it excludes them.
* **NC readings rest on the same missing books.** r47 and r49 answer `yes` on the reading that the Code requires the
  permit. That is the same deferral to code books not on disk (160D-1110(a)) that makes r51 `depends`. The asymmetry
  is disclosed, since both are marked "(reading)", but the note should say plainly that the NC deck `yes` would
  change if the NC code books exempt something.

---

## Confirmed

### The rules, against the text

| Rules | Answer | Basis in the text | Verdict |
|---|---|---|---|
| VA r1, r2 | no; depends in a special flood hazard area | 108.2 item 2 ("does not exceed 256 square feet", so 256 is in); Exception 2 ("may be required by the building official") | Confirmed. Subject to M1 and M2 |
| VA r3 to r6 | yes: over 256, more than one story, attached, Group F-1 or H | item 2's four conditions; 108.1 item 1 | Confirmed. r5's reading (an attached shed is an addition) is sound. r3 is wrong for containers and farm buildings (M2) |
| VA r7 | yes, at any size or height | no deck item; "deck" in 108.2 only in 14.6, roof decking (checked) | Confirmed (A3). Add 101.7 (M5). Item 13 handling: W4 |
| VA r8, r12 | depends (14.11) | 14.11 | The answer is defensible, but inconsistent with r7, and the reasoning should rest on the "Construction" definition (W4) |
| VA r9 to r11 | no / depends in flood / yes for a pool barrier or pedestrian-safety fence | item 5 ("Fences of any height unless …"); Exception 2 | Confirmed |
| VA r13 to r15 | ≤ 6 ft no / flood depends / > 6 ft yes | item 6 ("do not exceed six feet", so 6 is in) | Confirmed |
| VA r16 to r19 | < 3 ft of fill no / flood depends / ≥ 3 ft yes / surcharge or liquids yes | item 7 ("less than three feet", so 3 is out) | Confirmed |
| VA r20 | addition yes | 108.1 item 1 | Confirmed |
| VA, historic | never changes the permit answer | Exception 1 covers only "replacement siding, roofing, and windows" | Confirmed; only `other_approvals` changes |
| DC r21, r25 to r27 | no only for ≤ 50 sq ft, < 10 ft, one per lot | item 8 ("less than ten feet", so 10 is out; "does not exceed 50") | Confirmed |
| DC r22 to r24 | yes: the limited application under 105.2.5 and/or 105.2.6 | 105.2.5 lists "8. Garden storage shed"; HPO approval first; 105.2.6 | Confirmed (B1) |
| DC r28, r30, r31 | ≤ 36 sq ft no / Flood Hazard Area yes / > 36 yes | item 13 ("no more than 36 square feet"); 105.2.6 | Confirmed |
| DC r29 | historic playhouse: depends | 105.2.5 does not list item 13; 10-C 304.1(h) | Confirmed. Cite 10-C 303.1 and 303.3 (M4) |
| DC r32, r39, r46 | deck, masonry wall, addition: yes | no 105.2 item; 105.1 item 1 | Confirmed |
| DC r33 | resurfacing depends | 105.2.2 | Confirmed outside Flood Hazard Areas; **wrong inside them (W1)** |
| DC r34 | new fence yes | item 4 is repair only; 105.1.1 "7.4 Fences." | Confirmed |
| DC r35 to r38 | repair no / historic depends / Flood Hazard Area yes | item 4; 105.2.5 "except as deemed an ordinary repair"; 105.2.6 | Confirmed for repair in kind; **replacement is W2** |
| DC r40 to r45 | ≤ 4 ft from the bottom of the footing and ≤ 50 sq ft disturbed: no, except historic or flood | item 10 ("not over four feet", "does not exceed 50"); 105.2.5; 105.2.6 | Confirmed; 10-C 304.2(e) agrees for historic |
| NC r47, r50 | new deck, addition: yes (a reading) | (c)(1) "addition … of load-bearing structures"; (a) | Confirmed as marked readings (M6 on the asymmetry) |
| NC r48 | resurfacing at $40,000 or less: no | (c)(1) second sentence; "or less", so $40,000 is in; (b5) binds local variances | Confirmed for a single-family residence; **not for two-family dwellings (W3)** |
| NC r49 | resurfacing over $40,000: yes (a reading) | outside (c); (a) | Confirmed as a marked reading |
| NC r51 | sheds, playhouses, fences, walls: depends | "shed" absent from 160D-1110 (and from the live page); in 143-138 only three times, all inside (b4); the "in any single-family residence" question | Confirmed |
| other_approvals r1 to r12 | zoning; historic review; floodplain | Va. Code § 36-97; 102.2's preserved land-use conditions; 12-A 105.2 and 105.2.6; 10-C 304.1; 160D-947(a) ("whether or not a building or other permit is required"); 143-138(e) | Confirmed. Add DC 105.2.4 (M3) and the NC erosion citation (M6) |

### The report's claims

| Claim | Result |
|---|---|
| Counts: 2 decisions; 51 + 12 rules; 15 inputs; 9 knowledge sources; 32 requirements; 145 quotes; 16 reading marks | Reproduced by the checker. The 16 implied groundings were counted in the XML |
| 59 cases hit all 63 rules; SpiffWorkflow agrees at 797 points (785 + 12) | Reproduced |
| 165, 1,693 and 57 mutants all caught (2 of the 57 by group 4) | Reproduced |
| 66 curly-quoted note spans are verbatim | Reproduced by the checker and independently |
| Every quote is verbatim, in the subdivision it cites, with the index's URL and act id | Reproduced independently (145/145 exact) |
| No 'low freestanding deck' rule in VA, DC or NC text on disk | Confirmed. No Virginia statute on disk mentions sheds or decks for permits either (full-text search of `statutes_va`) |
| DC 105.2.5 lists Building items 1, 4, 5, 7, 8, 9 and 10 only | Confirmed |
| "105.2.6 displaces every exemption in the same way" | True of the text, but the model does not apply it to 105.2.2 (W1) |
| NC (c)(1): re-decking at $40,000 or less needs no permit; new framing is a reading | Confirmed, live and in the index (W3 for duplexes) |
| NC sheds not settled; § 143-138 mentions sheds only in (b4) | Confirmed: three occurrences, all inside (b4) |
| Albemarle fixture: "Tool sheds and playhouses less than 256 square feet …" | Confirmed verbatim in `fixtures/places/va/discovery-albemarle.json`. The regulation says "does not exceed 256 square feet", so the two differ at exactly 256 |
| VA history note "Volume 40, Issue 9, eff. January 18, 2024"; the date is not in the index text | Confirmed live. "2024" occurs in neither 13VAC5-63-10, -30 nor -80 in the index |
| Charlottesville fixture: "New permits since January 18, 2025 are under the 2021 …" | Confirmed verbatim |
| Process ids `building_permit`, `building_permit_residential`, `residential_building_permit` | Confirmed in the three fixtures, with the legal-basis shapes the note describes (`legal_basis.state`; `{cite, url, source, note}`; `va_code` strings) |
| VA localities cannot amend the list (102.2; § 36-98) | Confirmed. The local levers are the building official's discretion, fees, the form, zoning, historic districts and NFIP |
| No ICC or UpCodes link and no model-code text | Confirmed. No `iccsafe` or `upcodes` string in the DMN, and the 12-B R101 ICC link is not copied. "Section 3306" appears (W5) |
| Network use | Consistent with what this check saw (robots.txt 301 then 404; Crawl-delay 2) |

## Suggested order of fixes

1. W1, W3 and M1 change answers, and need new cases: DC resurfacing in a Flood Hazard Area, an NC duplex, and a shed
   with wiring.
2. M2 and W2 change answers for common projects (container sheds, farm sheds, whole-fence replacement in DC).
3. W4: state the `depends` rule, then align r7, r8 and r12 with it.
4. The citations: M3, M4, M5 and M6.
5. The wording in W5.

---

## Re-check 3 (2026-10-11)

Checked 2026-10-11, 00:20 to 00:55 US Eastern (04:20 to 04:55 UTC). This note had no earlier Re-check section, and
nothing in it was marked accepted, so every finding above was re-checked. Under review:

* `out/design/permit_required.dmn`: 396,011 bytes, sha256 `eb02430a…`;
* `out/design/check_permit_required.py`: 67,092 bytes, sha256 `2f3786cf…`;
* [permit-required.md](permit-required.md): 67,557 bytes, sha256 `c719d3db…`.

Nothing was edited except this section. **This is not legal advice.**

**How it was checked.**

* **The checker**, run exactly as its docstring says (a `mktemp` directory in `lexflow-app-1`, `TMPDIR` passed, the
  directory removed afterwards). Result: **ALL CHECKS PASSED**, exit 0, 129 `[ok]` lines, 0 FAIL, 435 s wall time.
  Every number the fixer gives was reproduced:
  * 2 decisions, 69 + 12 rules, 17 inputs and 13 knowledge sources;
  * 32 shapes and 38 edges, 229 quotes and 32 reading marks;
  * 1,611 grid points in 36 slices, plus 12 in 3, and 1,623 SpiffWorkflow evaluations;
  * 81 cases hitting 81 rules, and 117 verbatim note quotes;
  * 219, 2,760 and 97 mutants caught. Of the 97, group 4 caught 37 and group 5 caught 60.
* **The old model.** The fixer kept a 264,822-byte copy of the old model in the scratchpad. It has the same sha256
  (`e5c20fe2…`) as the copy this note checked on 2026-10-10, and so does the fixer's regenerated copy.
* **The pins, reproduced.**
  * Run against the old model, the new `CASES` fail 62 of 81, and all 30 finding-tagged cases are among them.
  * The blanket "DDOT" and "sedimentation" words were then taken out of the other-approvals expectations. Each of the
    30 still fails in `permit_required`: a wrong rule or answer, no rule at all, or missing basis words. So each one
    pins its own finding.
  * The three description checks (W2, W4, M6) also fail on the old model, as does the W5 `jurisdiction` check.
* **The rules.** r1 to r51 were compared cell by cell, old model against new, and all 69 + 12 rules were read against
  the text.
* **The text**, read from the indexes. Their `meta` rows are unchanged: 22,396 VA, 22,914 DC and 21,314 NC sections,
  built 01:40 to 01:45 UTC on 11 October. Sections read:
  * Virginia: 13VAC5-63-10, -20, -80, -200 and -220, and Va. Code § 36-97;
  * DC: 12-A DCMR 105, and 10-C DCMR 303, 304 and 320;
  * North Carolina: G.S. 160D-1110, 160D-1128 and 143-138; G.S. 87-15.5, which 160D-1110(g) cites; and G.S.
    105-277.02, found by a full-text search of `statutes_nc` for "townhouse".
* **Not done.** No network request, benchmark, build, job or Ollama call, and no container was restarted.

### Status of each finding

| Finding | Status | Evidence |
|---|---|---|
| W1 | **Fixed** | r33 now reads `flood_hazard_area = false`. r58 answers `yes` and quotes 105.2 and 105.2.6. B13b fails on the old model (it hits r33, `depends`), and B13c keeps historic status out of it |
| W2 | **Fixed** | `fence_repair` means repair in kind only. A replacement is `fence`, which answers `yes` (r34, with the item 7 reading). B14b and the description check fail on the old model |
| W3 | **Fixed** | New `dwelling` input. r48 is single-family only, r66 answers `yes` and r67 `depends`. C2b and C2c fail on the old model (both hit r48, `no`). See N7 on r67's wording |
| W4 | **Fixed**, but see N3 | r8 and r12 are `yes` with the 14.11 caveat, and both cite 13VAC5-63-200. No "structural component" reading is left: the phrase now occurs only inside the 108.1 quote. A12 and A17 fail on the old model |
| W5 | **Fixed**, but see R2 and R4 | The `jurisdiction` description points at part 5 and names 143-138(b5) and (e) and 160D-1128 (but see N2 and N5). The run time is measured: 435 s here, within the note's "6 to 7 minutes" |
| M1 | **Fixed** | New `trade_work` input, with r56, r57, r65 and r69. Every other rule reads `trade_work = false`. Every `no` or `depends` basis says so, except r68, which the note names as the exception. The VA `no` bases (r1, r9, r13, r16) quote the 108.2 preamble. A26, A32, B33 and C10 fail on the old model, which answers `no` |
| M2 | **Fixed** for Virginia and North Carolina. **DC containers: see N1** | r52 to r55, r57 and r68 match 102.3 items 7, 9 and 11 and 143-138(b4). r3 and r20 cite 102.3 item 8 and 429.5, marked as a reading |
| M3 | **Fixed**, but the quote is not pinned (R3) | r5 to r8 state and quote 105.2.4 |
| M4 | **Fixed** | 10-C DCMR 303 is a knowledge source. r29 and r60 quote 303.1 and 303.3, r41 and r43 quote 304.2(e), and the note cites 320.1 |
| M5 | **Fixed** | r7 cites 101.7 as a reading. The A3 paragraph's account of Note 1 to 101.2 and of 101.6 items 1 and 2 matches the text |
| M6 | **Fixed**, but the (e) quote is not pinned (R3) | r9 to r12 quote 160D-1110(e). `height_ft`, r13 and r15 exclude column caps, and §3.3 states the NC caveat |

### Still wrong or overstated in the revision

* **R1. Wrong (wording): "only r33 was narrowed".**
  * Note §2.1 says r1 to r51 keep their meaning, and that "only r33 was narrowed … and r8 and r12 changed their
    answer". The fixer's summary says the same.
  * The comparison shows two more changes. r48 now also reads `dwelling = "single_family"`, so it was narrowed (W3).
    r51's project cell gained `playground_equipment` and `storage_container`, so it was widened (M2). All 51 rules also
    now read `trade_work = false`; §9 does say that.
  * **Fix:** name r48 and r51 in §2.1.
* **R2. Overstated: "the model quotes that state text and nothing more".**
  * This is the note's wording ("How the text was read"). The checker's docstring and its check label likewise say the
    references "are quoted as state text".
  * Outside the quotes, "Section 3306" appears in two places:
    * the `safety_barrier` description, with the model's own gloss of that IBC section's subject ("protection of
      pedestrians during construction");
    * r11's basis.
  * Also outside the quotes, "Section 3103" appears in r62's reading note and "the IBC" in r7's.
  * These are facts, not model-code text, but "nothing more" is not true.
  * The check's label also begins "no model-code text", which the check cannot test. It tests only for links, titles
    and two pinpoints.
  * **Fix:** say that the model also repeats these references in its own descriptions and notes. Either drop the 3306
    gloss or disclose it.
* **R3. Test gap: the citations the fixes added are not pinned.**
  * A mutant was built that removes 13 `lex:source` entries and regenerates the Source annotations, keeping every basis
    word. It removes:
    * 105.2.4 from `other_approvals` r5 to r8, and 160D-1110(e) from r9 to r12;
    * 13VAC5-63-200 from r8 and r12;
    * 304.2(e) from r41 and r43;
    * the 108.2 preamble from r1.
  * It passes groups 1 to 6 (**ALL CHECKS PASSED**, 216 quotes). Group 7 mutates only cells and outputs, so the full
    checker would pass too.
  * Only the basis words pin these fixes. The unused-source check catches only the removal of a section's last
    citation.
  * **Fix:** check in group 3 a table of the citations each rule must carry (rule id to section and subsection).
* **R4. Overstated: §9 says each fix is pinned by checks that fail on the old model.**
  * The "reworded model-code check" listed for W5 passes on the old model: none of the forbidden strings is in either
    file.
  * The premise checks listed for W2, W3, W4, M1 and M2 read only the index, so they pass on any model. They are: the
    "Construction" definition, wiring in 108.2, 102.3, 429.5, item 7's list, and (c) and (b5). They check premises; they
    do not pin fixes.
  * The cases and the three description checks do fail on the old model.
  * **Fix:** list only those as pins. The wording part of W5 has no pin, and cannot have one.

### New

* **N1. Wrong answer: a DC storage container answers `depends` at any size (r62), but item 17 settles most cases.**
  * Building item 17 reads in full: "Structures erected for a period of less than 180 days in a 12-month period that
    cover an area of 150 square feet (13.9 m2) or less and are exempted from permit requirements by Section 3103;".
  * Item 8 covers only a garden storage shed of 50 sq ft or less.
  * So no 105.2 item covers a container kept for 180 days or more, or one over 150 sq ft. r62's own reading is "placing
    a container on a lot for use as a storage building is erecting a structure under 105.1". On that reading the answer
    is `yes`, as it is for a deck, a masonry wall and a farm building (r32, r39, r64).
  * Case B30 ("shipping container kept in the yard as storage", 160 sq ft) expects `depends`, but the text gives `yes`
    (a reading). So `depends` is not the conservative choice that §8 item 3 calls it.
  * **Fix:**
    * split r62 on `floor_area_sqft`. Over 150 sq ft, answer `yes`, giving item 17's "150 square feet (13.9 m2) or less"
      as the reason it cannot apply;
    * keep `depends` only for a container of 150 sq ft or less that may stay under 180 days, and name both limits in
      the basis. A `temporary` input would narrow this further;
    * change B30 to `yes` and add a case for a 120 sq ft temporary container;
    * extend `floor_area_sqft`'s description to containers, and update the Summary row, §3.2 and §8 item 3.
* **N2. Missing caveat and an untrue sentence: NC fire limits can require a permit for deck resurfacing.**
  * G.S. 160D-1128(c): within a city's primary fire limits "no frame or wooden building or structure or addition
    thereto shall hereafter be erected, altered, repaired, or moved, either into the limits or from one place to another
    within the limits, except upon the permit of the local inspection department approved by the governing board and by
    the State Fire Marshal or the State Fire Marshal's designee". Subsection (a) says the same for a county's fire
    limits.
  * Neither exclusion removes that permit. 160D-1110(c) covers a "permit issued under Article 9 of Chapter 143", and
    143-138(b5) a permit "required under the Code or any local variance thereof".
  * So r48's "No permit … A local variance cannot require one (143-138(b5))" is wrong for a wooden deck inside primary
    (or county) fire limits.
  * For the same reason, note §5's "The local layer is the office, the form, the fee, and the other approvals, not the
    answer" is not true for North Carolina.
  * Primary fire limits cover "the principal business portions of the city", and a county's may include "only business
    and industrial areas". So few houses are affected, but some are.
  * **Fix:**
    * caveat r48 and the Summary's NC resurfacing cell, or add the fire-limits permit to NC `other_approvals` r9 to r12,
      quoting (c);
    * reword §5;
    * make the `jurisdiction` description's "inside fire limits" say primary city or county limits. Inside secondary
      limits, (d) asks only for compliance "with any rules and regulations established by ordinance".
* **N3. The rule for the officials' discretion is stated more widely than it is applied.**
  * The decision description says the answer is `yes` "where the text requires a permit unless the building official
    deems the work exempt (VA 108.2 items 13 and 14.11), with that caveat in the basis".
  * Item 13 reads "Construction work deemed by the building official to be minor and ordinary and that does not
    adversely affect public health or general safety." As W4 noted, it can reach every Virginia construction answer.
  * But only r7, r8 and r12 carry the caveat. r3 to r6, r11, r15, r18 to r20 and r56 do not.
  * Note §2.1 and §5 limit the caveat to those three rules, so only the DMN description overstates.
  * **Fix:** either add the item 13 caveat to those ten bases, or say in the description that the caveat is given
    where the item is the live question (decks, deck resurfacing and pool-barrier repairs).
* **N4. Minor: the stated `depends` rule leaves out two rules and a third kind of `depends`.**
  * §2.1's list and the decision description leave out r54 (a VA farm building in a flood plain) and r68 (an NC farm
    building).
  * r68 turns on a fact the model does not ask: whether the building is inside a municipality's building-rules
    jurisdiction. After N1, the remaining r62 cases turn on how long a container stays. Neither branch of the stated
    rule describes this kind of `depends`.
  * r68's basis gives only (b4)(i) and (ii). It leaves out (iii) "a primitive camp" and (iv) "a primitive farm
    building".
* **N5. Minor, incomplete: a proviso of 143-138(e) is left out.**
  * 143-138(e) also says a political subdivision "shall not adopt local fire prevention code provisions which apply to
    dwellings subject to the North Carolina Residential Code which are not prescriptively required by the North
    Carolina Residential Code."
  * The `jurisdiction` description and §5 give the fire-prevention lever without this proviso, which narrows it for
    the model's dwellings.
* **N6. Nit: "only 108.2's list of exemptions counts".**
  * The phrase is in the A3 paragraph and the 13VAC5-63-10 knowledge-source description. r7's reading note says "only
    108.2's list counts".
  * The wording predates M2. Now that the model uses 102.3, Chapter 1's exemptions are 108.2's list and 102.3's
    whole-code exemptions. The phrase is right for decks, but "only Chapter 1's exemptions count" would be exact.
  * Optional: 13VAC5-63-200 defines "Structure" as "An assembly of materials forming a construction for occupancy or
    use, including stadiums, gospel and circus tents, reviewing stands, platforms", which could ground the readings in
    r7 and r8 that a deck is a structure.
* **N7. Overstated: "the statutes do not say" whether a townhouse unit is a single-family residence.**
  * The claim appears in r67's basis, the `dwelling` description, note §2.1 and note §3.3.
  * 160D-1110(g), in the same section, speaks of "an existing single-family residential dwelling unit as defined in G.S.
    87-15.5". G.S. 87-15.5(7) defines that term: "A separately owned residence for use of one or more persons as a
    housekeeping unit with space for eating, living, and permanent provisions for cooking and sanitation, whether or not
    attached to other such residences."
  * A separately owned townhouse unit fits that definition. Against it, G.S. 105-277.02 (property tax) speaks of "a
    new single-family residence, a townhouse, or a duplex" as separate kinds.
  * Whether (c)'s "single-family residence" takes (g)'s definition is still a reading, so `depends` stays defensible,
    and it is the conservative choice. But the text on disk does say something, and it points both ways.
  * **Fix:** keep `depends`. Reword the four places, and cite (g), 87-15.5(7) and 105-277.02 in r67, with their
    readings.
  * The same definition could cover each half of a duplex whose halves are separately owned. r66's `yes` stays the
    conservative answer, but its basis should say so.

### Accepted as stated

* The judgement calls in note §8 item 3, except the DC storage container (N1):
  * a DC fence replacement in kind answers `yes`, which is the conservative side;
  * a VA farm building in a flood plain, and VA trade work with a 102.3 structure, answer `depends`;
  * an NC townhouse answers `depends` and a duplex `yes` (see N7 on the wording).
* r36 (a DC fence repair in a historic district) stays `depends`. 105.2.5's "except as deemed an ordinary repair" turns
  on the DC "ordinary repair" question, and §2.1 puts that question in the unsettled branch for r33 and r36 alike.
* The added sections were not re-read live. The note discloses this (§8 item 7).
* Other agents' files that still describe the old answers are outside this area. One example is the VA deck's "rule 4"
  at line 477 of [data-expansion.md](data-expansion.md).
* Privacy: the model and the note name only places and offices (place names, government ids and office names). They
  give no staff names and no pay figures, and they name no researcher as partner, advisor or endorser.

### Suggested order

1. N1 and N2 change an answer or add a caveat to one. Each needs a case: B30 at 160 sq ft, and an NC resurfacing inside
   fire limits (or a mention of fire limits in NC `other_approvals`).
2. R3: pin the citations the fixes added.
3. N3 and N7.
4. The wording in R1, R2, R4 and N4 to N6.
