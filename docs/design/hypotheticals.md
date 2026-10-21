# Hypotheticals: fact patterns computed from grounded decision tables

_21 October 2026. The design behind `lexflow/scenarios/` (`lexflow hypo`), the family file
`fixtures/families/glass_studio_va.json`, the tables `families`, `personas`, `assumptions`, `scenarios` and
`scenario_runs` in `lexflow/store/db.py`, the routes `/api/hypo/...`, and the `computed` signal of the coverage probe.
Several ideas come from [github.com/dam8u/VRSLite](https://github.com/dam8u/VRSLite), a model of one proposed
Virginia Retirement System bill: inputs tagged as published facts, assumptions or scenario values; a scenario-ID
grammar built from small vocabularies; personas; rules as deterministic code reconciled by tests; with and without
baselines; one-at-a-time sensitivity; and invariants enforced by tests. That repository carries no licence, so
nothing was copied from it (no code, text or data): only the ideas, in lexflow's own shapes._

## 1. What a hypothetical is here

"If I open a glass studio with a gas furnace in district X, with classes of 60 people and wine at events, what do I
need, from whom, at what cost and in what order?" has the same answer every time it is asked with the same facts.
lexflow therefore computes it rather than generating it: no model writes the answer, and the same inputs, tables and
engine always give the same output.

* A **question family** is a set of decision tables that answer one kind of question for any fact pattern made of
  its **dimensions**: small vocabularies (locality, zoning district, fuel, occupant load, food, alcohol, employees ...)
  or numeric bins. `glass_studio_va` serves the coverage questions `glass_studio` and `glass_q1`–`q3`, `q5`–`q12`.
* A **fact pattern** (a scenario of kind `fact`) is one value per dimension. It is evaluated against every table of
  the family, and the output lists the requirements that apply, each with its office, status, fee, deadline, the
  quote that grounds it, and its place in the order.
* A **policy variant** (kind `policy`) is an alternative rule set or reading, evaluated against the same population
  of fact patterns so that the two can be compared, with and without (VRSLite's two baselines). The pilot's variant
  `highimpact` is the stricter reading of Charlottesville's use table (a fuel-fired hot shop is "High-impact
  industrial and manufacturing", allowed only in IX-5 and IX-8 and only by special use permit). A variant is tagged
  `ASM` when it is a reading of the law and `SCN` when it is a hypothetical change of it; a hypothetical rule never
  cites a quote it does not have.

The free text of a question is only an input to **intake** (section 10), which turns it into enumerated values or
into the questions still to ask.

## 2. Provenance: SRC, ASM, SCN

Every input value, rule and ordering rule carries one tag (a fee counts as known only when its own quote, or its rule's, matched; otherwise it is listed as a fee not known):

| Tag | Meaning in lexflow | Examples in the pilot |
|---|---|---|
| `SRC` | grounded: a verbatim quote that lexflow's software matched (the statute index for a Code quote, the quote fetch's cached page for the rest, or for a withheld quote the fingerprint the fetch recorded), or a published figure with its URL | the Charlottesville use-table row for an artisan workshop; the $200 Albemarle LP-gas permit; 13VAC5-63-160 for the certificate of occupancy |
| `ASM` | lexflow's assumption, with an `ASM-xx` id, a direction of error and a range | Albemarle district classes (ASM-02: an orientation, not a reading of the use tables); lead times (ASM-08); the 4% surcharge arithmetic (ASM-09); the order "zoning before the lease" (ASM-18) |
| `SCN` | the asker's hypothetical value | "classes of 60", "$75,000 in the first year"; every value intake reads from free text |

lexflow's existing flags map onto them:

* a quote the place file's own check matched (`places.check_quotes`: `by` code, live or archive) is `SRC`; one listed
  as "Not confirmed by lexflow's software" is not grounded, and a rule resting on it is dropped (section 3);
* the backbone's `inferred: true` escalation steps and every place file's `caveats` are assumptions: they become
  `ASM-xx` entries when a rule rests on them (ASM-04 restates the fire-permit caveats, ASM-03 the Staunton zoning
  caveat), never `SRC`;
* a figure read on a site whose terms forbid quoting it (eCode360: Staunton's fee ordinances) is reported as a figure
  with its URL and tagged `ASM-14`, since lexflow's software could not match it;
* the statuses `may be required` (the official decides: SFPC Table 107.2 permits are "may be required") and
  `ask first` (the classification is open) are how an `ASM` shows in an output; `required` rows rest on `SRC`.

## 3. The family file and its grounding

`fixtures/families/glass_studio_va.json` holds, in this order: `grammar`, `dimensions` (12), `derived` (the district's
zoning class), `constraints` (2), `offices` (37), `milestones` (lease, construction, occupancy, opening), `tables`
(8), `order` (38 ordering rules), `appeals` (14), `assumptions` (18), `personas` (4), `variants` (1) and `serves`.

| Table | Rules | Inputs | What it decides |
|---|---|---|---|
| zoning | 23 | locality, district class, building, food, alcohol, occupants, historic, sign | zoning letters and clearances, special use permits and their pre-application meetings, site plans, signs, Staunton's Certificate of Appropriateness, "not allowed here" |
| building | 25 | locality, building, fuel, occupants, food | contractors' licences, building, mechanical, gas, electrical and hood permits, assembly occupancy, the certificate of occupancy |
| fire | 18 | locality, fuel, oxygen, occupants, food | hot work, industrial ovens, LP-gas, compressed gas, assembly, demonstrations, commercial cooking |
| business | 17 | locality, receipts, food, alcohol | sales tax registration, BPOL by receipts tier (numeric tests such as `<= 50000`, `(50000..100000]`), business property returns, meals and food and beverage taxes |
| food | 7 | locality, food, alcohol | health plan review and permit, the packaged-food exemption, temporary food permits |
| abc | 6 | locality, food, alcohol | banquet, wine and beer, arts venue or marketplace licences, the local ABC fee and notice |
| employer | 4 | employees | VEC registration, workers' compensation (three or more), VOSH |
| utilities | 12 | locality, building, fuel, food | gas service, the meter unlock, water and sewer connections, grease, slurry, pretreatment, air-permit records |

Each rule is one row of a COLLECT table in lexflow's decision shape (`when` FEEL unary tests, `then` the requirement
id and its status) and carries the requirement itself: title, office, fee (`usd`, `min_usd` or a `rule`; kind fee,
tax or charge), deadline, lead days, ordering tags, stage, tag and assumptions. Its `source` is a pointer
(`curated/places/va/<place>/glass_studio_<topic>.json#steps[4]`, or `fixtures/places/va/glass/state-backbone.json#topics[5].sections[11]`)
into one of the 21 verified glass files or the state backbone; `fee_source` and `deadline_source` ground a fee or a
deadline that another quote states.

**Grounding** (`python -m lexflow.scenarios.family --fill glass_studio_va`): each pointer's quote, URL and citation are
copied from the file and matched. A place file's quotes go through `places.check_quotes` (the state code through
`validate.quote_in` on Open US Law's copy, the rest against the quote fetch's cached page); a backbone section goes
through the same matcher as a one-entry spec. A withheld quote (Albemarle's pages, under `quotes.NO_REPRINT`) is
copied as its fingerprint and lexflow's paraphrase, never its words, and is matched by the fingerprint the fetch
recorded for its page when the evidence store is absent. A rule whose `source` does not match is dropped when the
family loads and listed (`Family.dropped`, `lexflow hypo family`); an unmatched fee becomes a fee not known.

The first pass matched 252 of 264 sources. Six backbone regulation pages (13VAC5-63-210 and -433.5, 16VAC25-90-1910,
9VAC25-31-50 and -730, 9VAC20-60-261) had never been read by the quote fetch; they were read once, politely, with
`quotes.fetch` and matched. Four backbone Code quotes were not word for word in Open US Law's copy (§§ 4.1-206.3,
4.1-231.1, 35.1-1: the backbone's copies differ from the index text, mostly in spacing around a cited section
number); their pointers were moved to the same sections as the Staunton and Charlottesville files quote them, which
match. The committed family: 264 of 264 sources matched
(134 live page, 39 statute index, 57 Internet Archive copy, 34 fingerprint), 112 rules, none dropped. A quote that a
place file keeps plain on a NO_REPRINT page is printed only when `quotes.free_words` vouches for it (the state code's
words, a free official page's); `python -m lexflow.municipal.quotes --scan` stays at 0.

## 4. The scenario-ID grammar

`{LOC}-{DIST}-{BLD}-{FUEL}-{O2}-{OCC}-{FOOD}-{ALC}-{EMP}-{HIST}-{RCPT}-{SIGN}[-{RULE}]`, each slot a dimension's
value code, so the scenario space is the product of the vocabularies:

| Slot | Codes |
|---|---|
| LOC | CVL, ALB, STN |
| DIST | Charlottesville `C` + code (CCX8, CIX5, CRA ...), Albemarle `A` + code (ALI, AC1, ARA ...), Staunton `S` + code (SB2, SB2R, SI1 ...) |
| BLD | EX existing building (change of use), NB new building or site change |
| FUEL | NG natural gas, LP propane, EL electric only |
| O2 | O2Y oxygen above 504 cubic feet, O2N |
| OCC | P0 none, P1 under 50, P50 50 or more (representative values 0, 30, 60) |
| FOOD | F0, FP packaged only, FK prepared (a café) |
| ALC | W0, W1 one-off event, WR regular |
| EMP | E0, E2 one or two, E3 three or more |
| HIST | H0, H1 (Staunton's H-1 districts only) |
| RCPT | R25, R50, R100, RX (first-year gross receipts bins) |
| SIGN | S1, S0 |
| RULE | RHI (the `highimpact` variant); absent for the baseline |

`CVL-CIX5-EX-NG-O2Y-P50-FP-WR-E2-H0-R100-S1` is the hot shop with classes of 60 and wine nights in Charlottesville's
IX-5; with `-RHI` it is the same studio under the stricter reading. A scenario's id is its key in `scenarios`, and
`Family.parse_id` turns it back into inputs (a bin's representative value; an exact number given at intake is kept in
the stored inputs).

## 5. Personas

Named input bundles, with a district per locality: `cold_studio` (small cold-working studio, electric kilns, no
public), `hot_shop_classes` (gas furnace, oxygen, classes of 60, packaged snacks, wine nights, two employees),
`studio_cafe_historic` (propane lampworking, a café with wine, three staff; in a Staunton historic district),
`new_build_propane` (a new building on an industrial lot). `hot_shop_classes` is the default on the dashboard.

## 6. Evaluation

`lexflow.scenarios.dmn` evaluates lexflow's decision shape with FIRST, UNIQUE, ANY, COLLECT and RULE ORDER, `-`,
booleans, enumerations (`"a","b"`, `not(...)`) and numeric tests (`>= 50`, `<50`, `[1..49]`, `(50000..100000]`) on top
of `lexflow.feel`. It reads DMN 1.3 decision tables too (`from_dmn`). Two implementations are reconciled by tests:
over every curated decision's whole grid (more than 50 tables) it gives the same rule and outputs as
`lexflow.dmn_eval` on the compiled IR, and every applicant of `out/design/bpc_480.dmn` hits, in every table, the rule
the applicant states independently.

`run.evaluate` runs the family's tables on the inputs plus the derived district class (a variant may re-map it), then:

* **order**: a topological sort of the requirements present and the milestones, over the ordering rules whose ends
  are both present (a rule may be scoped to a locality); each edge carries the quote that makes it (zoning before the
  business licence: Charlottesville's licence application; the certificate of occupancy before the food permit:
  12VAC5-421-3660(A); the food permit before the ABC licence: Va. Code § 4.1-230(A)) or, tagged ASM-18, lexflow's
  advice (zoning before the lease);
* **timeline**: the longest path of lead days through that order (an estimate, ASM-08);
* **fees**: known fees for what is required, known fees for what the officials may require, fees with only a known
  minimum, and the fees not known, listed by name; taxes and other charges apart. The summary always begins "Known
  fees:";
* **appeals** for the tables that produced requirements, the **assumptions** the output rests on, and the **trace**
  of the rules fired in each table.

A stored run (`scenario_runs`) records the family version, the tables' content hash and the engine version, so a
changed table gives a new run id.

## 7. The scenario space

`expand.count` walks the space depth first with pruning: 216,000 valid scenarios (of a raw product of 1,446,336 that
pairs every district with every locality). The tables read a district only through its class, so districts of one
locality whose class agrees under the baseline and the variant are interchangeable (equivalence partitioning: a test
checks that swapping one for another never changes an output): 10 classes instead of 31 districts, 84,000 scenarios.
`expand.pairwise` (a deterministic greedy all-pairs generator, in the manner of AETG and IPOG, with the constraints
checked for a full valid completion) covers all 678 feasible pairs of values with **41 scenarios**. Constraints: alcohol
only with events or food (C1), oxygen above 504 cubic feet only with a fuel gas (C2), a district only in its locality
and Staunton's historic flag only in Staunton (value scopes).

All 41 were run under the baseline and the variant and stored (82 runs, 0.8 seconds). The variant changes 6 of the
41: in 3 the studio gains a special use permit and its pre-application conference (IX-5, IX-8), and 3 become blocked
(a fuel-fired studio outside IX).

## 8. Sensitivity

`sensitivity.swings` moves each dimension to each of its other values with the rest held, and measures the change in
the requirements to do (by id; a move that blocks counts as the largest), the known cost floor (known fees, those
that may be required, and known minimums) and the timeline. The ranking sums each swing over the largest swing of its
measure, like a tornado chart's bars. The locality is held by default: each place has its own offices and
requirement ids, so drivers are ranked within a place.

Averaged over the four personas, the top three drivers are district, food and building in Charlottesville; district,
building and food in Albemarle; building, district and food in Staunton (then fuel and, for Staunton alone, the historic flag, tied).

## 9. Invariants (tests/test_hypotheticals.py)

* every requirement in an output cites a matched quote (or, for a site that forbids reposting, the matched
  fingerprint with lexflow's paraphrase); so do its fee and deadline sources;
* changing a dimension that no rule reads never changes the output (a synthetic dimension is added and varied), and
  swapping a district for another of its class never changes it;
* Albemarle's words never appear in committed files: the fixture holds them only as fingerprints and paraphrases,
  outputs print paraphrases, and the scan of the committed files finds no run of withheld words;
* outputs never say "you need" without the office;
* fees are labelled known fees, and every fee not known is listed;
* the order respects every ordering rule, each edge has its reason, and the variant changes only Charlottesville's
  fuel-fired studios.

## 10. Intake and privacy

`intake.intake(text)` asks lexflow's decision model one `choice` question per dimension (the options are the value
codes with their labels, plus "not said"), keeps the probabilities, and accepts a value at confidence 0.8 or more. The
chat fallback gives no confidence, so it is not asked at all (its answers could never be accepted). A short
deterministic pass reads what needs no model (a locality's name, a district code of that locality, "60 people",
"3 employees", a dollar figure next to receipts, fuel, food and alcohol words). Every accepted value is tagged `SCN`
with its method (`decision-model` or `pattern`); the rest become questions, with the model's best guess. Filling them
with the family's defaults is explicit (`--defaults`) and tags them `ASM`.

Privacy: a scenario holds only enumerated values. The free text is returned to the caller and kept nowhere: the
decision cache stores a hash of it, and a scenario recorded from it is `local_only` (and stays so if recorded again),
in a table that is never synced or published. No office holder, staff member or reviewer is named anywhere in a
family; offices are organisations with their public pages.

## 11. Where each thing is stored, and why

| Thing | Where | Synced | Why |
|---|---|---|---|
| a family (dimensions, tables, grounding) | the fixture (source of truth) and `families` | yes | statements about the law and lexflow's readings of it, like `place_processes`; the row holds the committed form only (fingerprints, never withheld words) |
| personas | the fixture and `personas` | yes | named input bundles, part of the family's vocabulary; no person is in them |
| assumptions | the fixture and `assumptions` | yes | lexflow's readings with their direction of error: other copies should see the same caveats |
| scenarios | `scenarios` | no | not statements about the law; recomputable from the family and the id; one from free text is the asker's (`local_only`) |
| runs | `scenario_runs` | no | derived and recomputable, keyed by scenario, tables hash and engine |
| decision inputs and their values | Wikibase (proposed, not written) | – | see below |

**Wikibase.** Decision inputs and their values are legal vocabulary: "occupant load under 50", "oxygen above 504
cubic feet" and "a district where an artisan workshop is permitted by right" are defined by sections. The
recommendation is to write them as items grounded in the sections that define them: a class `decision input` and a
class `input value`, keyed `lexflow:input:<family>:<name>` and `lexflow:input-value:<family>:<name>:<code>`, each with
`P9 part of` the family's process item, *defined in* the section (schema row 56, created and still unused), the
defining quote as the reference (*quoted text*, *source section*, *determination method*), and a *review status*
claim; decision points (`Q9`) would gain `P13 references` to the inputs their rules read. Albemarle's values carry the URL
and the paraphrase only, as section 1 of [wikibase-schema.md](wikibase-schema.md) requires. Scenarios and runs are
not statements about the law and stay in lexflow; if published at all, it is as clearly labelled worked examples on
a page ("computed from the tables of <date>, not reviewed by a person"), never as Wikibase statements. Nothing has
been written to the wiki or the Wikibase.

## 12. Surface

* `lexflow hypo family [--save] | expand | run <scenario-id> or --persona P --locality L or --set dim=value [--variant]
  [--save] | run --pairwise [--save] | sens --persona P --locality L | ask "<text>" [--no-model] [--defaults]
  [--save] | report --out <file>`;
* `GET /api/hypo/families`, `GET /api/hypo/{family}/run?persona=&locality=&scenario=&variant=&<dim>=<value>`,
  `GET /api/hypo/{family}/sens?...` (read-only; nothing stored);
* the dashboard: on the Coverage page, a cell of a question a family serves shows a small form (a persona, one select
  per dimension, the variant) with the requirements, offices, fees, order and citations, and "what matters most";
  `#/hypo/glass_studio_va` shows the same card alone.

## 13. Coverage: the computed signal

`coverage.computed_signal` runs the family that serves a question for each persona, in the place of the cell or, for
a state cell, in each locality keeping only state-level requirements, over the tables the question reads, counting
only requirements whose quote matched. Its kinds: who (an office for every requirement), steps (two or more, ordered),
fee (a known fee or minimum), deadline (grounded), where (an office page), appeal (a grounded route); form is never
claimed. With `--computed` the probe records it as `computed` and lets its kinds count; a cell it answers is not capped
by drafts, and the matrix marks it `c`. The flag is off by default, so that runs stay comparable with the earlier
ones (and so that it could not change a coverage job already running on this copy); turning it on by default is one
line in `coverage.run`.

The glass cells (13 questions x Virginia and its three researched places), local store, no model, run
`hypo-glass-before` and `hypo-glass-after` (reports under `/data/hypo/`, not docs/):

| Column | Adequate before | after | Partial on drafts alone before | after | Kinds missing before | after |
|---|---|---|---|---|---|---|
| va (state) | 1 of 13 | 3 | 8 | 2 | fee 8, who 8, form 5, appeal 3 | fee 6, form 5, appeal 3, who 2 |
| Albemarle | 7 of 10 | 8 | 3 | 0 | fee 3, form 2, who 2, appeal 1 | form 2 |
| Charlottesville | 10 of 10 | 10 | 0 | 0 | – | – |
| Staunton | 10 of 10 | 10 | 0 | 0 | – | – |
| all 43 cells | 28 | 31 | 11 | 2 | | |

## 14. If lexflow ever models bills (out of scope now)

VRSLite's fiscal layer projects money over time for a population. For lexflow to say what a bill would change, a
family would need: a **bill as a variant** with its text and version (rules added, removed or re-mapped, each grounded
in the bill's words rather than the Code's, and tagged until enacted); an **effective-date dimension** and a
transition rule for scenarios that straddle it; a **population** of weighted scenarios (how many studios, applicants
or households fall in each cell, from Census or agency counts, tagged `SRC` with their table and year), so that
changed requirements can be counted, not just listed; **money over time** (fees, taxes and costs by year, discounting,
inflation, take-up rates as `ASM` ranges); and **fiscal notes** reconciled against the official one (Virginia's
Department of Planning and Budget publishes them), the way VRSLite reconciles two implementations. None of this is
built.

## 15. Open problems

1. **Classification is the crux and lexflow cannot settle it.** Whether a gas-fired hot shop is an artisan workshop
   (Charlottesville), how Albemarle's commercial districts treat it (ASM-02, read from the County's pages, not its use
   tables) and Staunton's B-2 limits (ASM-03, eCode360 not quotable) are each an office's determination; the family
   shows them as classes with their tags, and the `highimpact` variant shows what the stricter reading costs.
2. **Fees by floor area or project value are minimums only.** Building and trade permits are per square foot or by
   project value; the family has no floor-area dimension, so their totals are "at least". Adding area bins would turn
   them into ranges.
3. **Fire permits are "may be required" in two places.** Charlottesville publishes no Table 107.2 list or fees, and
   Staunton's schedule lists only LP-gas and hazardous materials (ASM-04).
4. **Lead days are maxima or estimates.** Charlottesville's 90-day statutory answer period for a zoning determination
   dominates its timeline; Albemarle states no time for a clearance. Timelines compare scenarios; they are not
   deadlines.
5. **No forms.** The family names no forms, so the coverage kind `form` stays missing; the place files list forms that
   a later version could attach to rules.
6. **Requirement ids are per locality**, so comparing places needs a shared requirement kind (a building permit is
   `cvl_building_permit`, `alb_building_alteration`, `stn_building_alteration`).
7. **Gaps in the dimensions:** minors (glass_q4), the business entity and an assumed name (glass_q9), outdoor events
   and tents, the Entrance Corridor and Charlottesville's design-control districts are not modelled.
8. **Intake needs the decision model.** It runs only on the Ollama server that serves `tev1`; without it the
   patterns read the plain facts and the rest are asked.
9. **Two copies of the truth.** The fixture is the source; the `families` row is a copy for sync. A changed fixture
   needs `lexflow hypo family --save` again (the content hash tells a stale row).
