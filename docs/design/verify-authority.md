# Verification of authority-escalation.md

Status: adversarial review, 2026-10-10. This file is the only one written. Nothing was written to the DB, the
DokuWiki, lexipedia.wikibase.cloud, Wikidata or Govdirectory. Every live read was a GET (or a read-only SPARQL
query), one at a time, at least 1.5 s apart per host, with the User-Agent
`lexflow-research/0.1 (https://github.com/alibama/lexflow)`. No `.env` value was read. No lexflow job, build,
benchmark or Ollama call was run. The method is in section 6.

What was reviewed: [authority-escalation.md](authority-escalation.md) (the design), against
[authority-wikidata.md](authority-wikidata.md), [authority-wikibase.md](authority-wikibase.md),
[authority-ladders.md](authority-ladders.md), [authority-standards.md](authority-standards.md),
[`fixtures/authority/ladders.json`](../../fixtures/authority/ladders.json), [entities-contacts.md](entities-contacts.md),
[terms-wikibase.md](terms-wikibase.md), [bpc-480-decision.md](bpc-480-decision.md) and
`lexflow/publish/wikibase_lexipedia.py`.

---

## 0. Verdict

* **The up-front answer holds.** Do not load all of Govdirectory. Do make a targeted Wikibase update. The live
  numbers back it: Govdirectory lists 21,084 distinct organisations, of which 1,140 are in the US (federal 374,
  North Carolina 607, New York 159). Wikidata's *appeals to* (P12452) is used on no state agency in the corpus
  jurisdictions. A federated query from Lexipedia to Wikidata, written the way the design writes it, ran in 1.1 s.
* **Some of the numbers behind the answer are too high.**
  * Only 85 of the 143 fixture rungs come from reviewed process models. The other 58 come from AskBench reference
    answers, and those have no process item on Lexipedia. Under the design's own rule (A7, 5.6), at most 85
    rungs can load today, not "up to 143".
  * The "about 540 items" total therefore falls to about 450–500.
  * A load also rewrites every existing item, so it takes longer than "10 minutes".
* **One legal claim in the worked example is wrong.** Florida corporations do have the 60-day corrected-filing
  rule (§ 607.0123(3)). The design says they do not.
* **Several other rungs are right in substance but need a qualifier.** These are the CA hearing deadlines, the
  § 486 reapplication, § 109(a) and the TX type. The fixture also leaves out one NC rung that the reviewed model
  has.
* **Re-runs can create duplicates in eight places** (section 5). The main ones:
  * the rung key depends on free text;
  * a rejected rung is never retired;
  * the `haswbstatement` lookup the design relies on does not exist in the loader;
  * the `entity_links` primary key cannot hold a power and a disability over the same thing.
* **Privacy holds, with three small fixes** (4.3). No office-holder is named, no contact detail of a person
  appears, and posts are modelled, not persons.

---

## 1. The up-front answer and its numbers

| Claim (design 0.1–0.3, 5.5) | Checked | Result |
|---|---|---|
| Govdirectory: 21,084 organisations, 46 countries | `sitemap.xml`: 21,105 pages, 21,084 distinct QIDs, 46 top-level sections | **Confirmed.** One of the 46 is the European Union, so it is 45 countries plus the EU. |
| 1,140 US: 374 federal, 159 NY, 607 NC; nothing for 9 of 11 jurisdictions | sitemap paths | **Confirmed** |
| 7 of the 91 Wikidata items the models name are listed | `agencies.json` (6 listed, 1 parent listed); the 91 is 76 body QIDs + 7 units + 8 related items | **Confirmed** |
| None of the 90 ladder bodies is listed | sitemap against the ladder QIDs | **True of the fixture as built, but an artifact.** See M1: the reviewed NC model's State CIO step has no rung, and the NC Chief Information Officer office (Q136430659) **is** on the NC list. |
| A full copy is ~29,000 items, ~8 h at one edit a second | 21,084 organisations + ~6,650 head posts + ~1,250 classes | **Confirmed** (authority-wikibase 3.3) |
| Up to 143 rung items | `ladders.json` sources | **Wrong.** 14 ladders (85 rungs) come from curated models. 8 ladders (58 rungs: sealing in CA, MD, VA; licence in CA, VA, DC, MD, TX) come from `curated_ask` references. Live Lexipedia has no `lexflow:process:ca.license_conviction` item. Under A7, at most 85 rungs can load now. |
| 270–320 entity items | the design's own 5.5 rows: 11 + 98 + 15 + 15 + 60 + 40 + 25 | **The rows add up to 264.** That is below the range's lower end. |
| ~540 items in all, ~10 minutes of writes | the loader | **Too high, and too fast.** With at most 85 rungs, the total is about 450–500 items. `Loader.entity()` re-saves every item on every run (there is no diff), and *review status* or *played by* must be added to the 1,433 existing items anyway. A real load is therefore about 1,900–2,000 writes: about 33 min at one edit a second, or 7–8 min at the 268 a minute the account reached. |
| 75 vocabulary items | 5.4 | **74 + 1.** 3.3 names "overruled by operation of law" (Tex. Gov't Code § 2001.146(c)), but the 6 lapse consequences leave it out. Make it 7 lapse consequences, 76 items. |
| 22 hand-built ladders as the baseline (7.4) | ladder sources against the 22 reviewed models | **Misleading.** 14 of the 22 reviewed models have a ladder. Eight business models (CA, IL, MD, NC, NY, OH, TX, WA) have none. |

**Corrected one-paragraph answer:** no full mirror. Add the property set, about 25 classes and about 76
vocabulary items. Add about 265–320 entity items. Add the accepted rungs of reviewed models: at most 85 now, and
the other 58 once the sealing and licence references become reviewed models with process items. That is about
450–500 new items, and a full load is about 2,000 writes.

---

## 2. Confirmed (live or from the text)

### 2.1 Wikidata (read 2026-10-10)

| Claim | Evidence |
|---|---|
| The property IDs and meanings used: P749, P355, P199, P361, P2388 ("position held by head of the organization"), P2389, P748, P10645, P797, P1001, P1308, P39, P488, P169, P1037, P3975, P973, P854, P813, P459, P580/P582, P92, P457, P953, P1476, P6104, P576, P1366, P2098, P10214 ("freedom of information requests URL"), P12452 ("appeals to"), P208, P1313 | `wbgetentities`, labels and datatypes |
| Q327333 *government agency*, Q10387680 *organization unit*, Q4164871 *position*, Q294414 *public office*, Q41487 *court*, Q8513 *database* | labels |
| P12452 is used on no state agency in the corpus jurisdictions. Its only subjects there are the New York Court of Appeals and federal courts. | WDQS, P1001 or P131 in the corpus states |
| Florida Department of State Q11969252: no P749, P2388 or P1001; its only P355 child is the Division of Historical Resources | WDQS |
| Secretary of State of Florida Q7444366: P31 *public office*, P279 *state secretary of state*, P1001 Florida; no P2389 and no P748 | WDQS |
| Florida Division of Corporations Q107179384: P31 includes *database*, beside *registration authority*, *government agency* and *state agency of Florida*; P749 and P361 point to the Department | WDQS |
| CSLB Q5020359 has no P749. DCA Q5020410 → BCSA Q136668814 → State of California Q5589189 is present. | WDQS |
| Virginia Department of Taxation Q116797530: P2388 → Virginia Secretary of Finance Q28230928 | WDQS |
| Illinois PAC Q104879968 has no P31, P749 or P1001 | WDQS |
| Holder counts, counted without reading any name: Q7444366 has 27 P39 holder statements; CA Secretary of State has 6 open-ended; the US President has 18 open-ended | WDQS counts |
| No item found for the NY Committee on Open Government, Virginia DPOR or the VA FOIA Council | `wbsearchentities` (a prefix search, so a lower bound; it agrees with the research's full-text searches) |
| Govdirectory's class items carry P6104 = Q108109790 (494 items, including NY's class Q134016126). Its organisations carry P5008 = Q108109790 (20,639 items). | WDQS. Both the design (P6104 for classes) and authority-wikidata (P5008) are right, for different things. |

### 2.2 Govdirectory

* The US generator selects by an explicit P31 class list and has `MINUS { ?org wdt:P31 wd:Q4164871 }`, so
  positions are dropped. The NY generator lists class Q134016126 (97 agencies) and counties.
* "Led by" in `queries/organization-optional.rq` is P2388|P1313 → a human's P39 statement with no P582 and no
  P570, excluding Q30185 (mayor), or a direct P488, P169, P1037 or P3975 value. It shows a person, never the
  post.
* The NY Division of Corporations (Q125449570) is not listed.
* `CONTRIBUTING.md` blocks contributions that "can be recognized as being AI generated". The design's rule (A13,
  section 6) fits it.

### 2.3 Wikibase Cloud and Lexipedia

| Claim | Evidence |
|---|---|
| Lexipedia has 25 properties, P1–P25, with the labels and types in authority-wikibase 1.2; P8 *exact match* is a URL property | Lexipedia SPARQL |
| Q33 Florida, Q774 `lexflow:process:fl.business`, Q775 organizer role ("Authorized representative (founder)"), Q776 department role; step `refuse_filing` is Q784; statute `lexflow:statute:fl:605.0210` is Q164 | Lexipedia SPARQL on P25 |
| 199 role keys, of which 196 are typed *legal role*; 357 items whose description starts "Unreviewed draft" | Lexipedia SPARQL |
| The 4.5 query pattern runs: an `OPTIONAL { FILTER NOT EXISTS {…} … P8 … SERVICE <https://query.wikidata.org/sparql> {…} }` block. It joined Baltimore and Charlottesville to their Wikidata parents in 1.1 s. | Lexipedia SPARQL (the P749 step swapped for P131, because no agency items exist yet) |
| The hosting policy: instances are temporary by default; temporary instances that never apply are suspended after 3 months; existing instances must apply; it requires a licensing statement on `Project:Copyrights`, CC0 structured data and "appropriate local rules" for data about living people; a staging ground for later Wikidata contribution is an exception that counts in an instance's favour | mediawiki.org staging copy of the policy, which points to wikibase.cloud/hosting-policy as binding. The September 2026 date was not re-read. |

### 2.4 Statute text (lexflow index, open-us-law v2026.09.1)

Each of these was read in full, and the quote, trigger, body and deadline match the design:

* **Florida.**
  * § 607.0126: the petition, attachments, summary proceeding and "as in other civil proceedings". No time limit.
  * § 607.0125(1), (3) (15 days, no consequence stated) and (4) ("ministerial").
  * § 607.01401(16); § 607.0201; § 607.0202(1)(e).
  * § 20.10(1)–(2)(c); § 20.02(3) (supervision, not review).
  * § 605.0210(3), (4) and (7).
  * § 617.0126 (30 days; an APA appeal or a Leon County petition); § 205.023.
* **California, Business and Professions Code.**
  * § 22 and § 477(a); § 100(a)–(b) (operative July 1, 2026); § 101; § 108.
  * § 109(a) (the quote is exact; see W10); § 109(b); § 153.
  * § 480(a), (a)(1)(B)(ii), (b), (c), (d) and (f)(3)(D) (the pinpoint is right); § 485(b) (60 days; "deemed
    waived"); § 486(a); § 487 (90 days).
  * § 7000.5(a); § 7011(a)–(b).
* **California, Government Code.**
  * § 11370.2(a)–(b) (OAH sits in General Services).
  * § 11500(a) and (d); § 11502(a)–(b).
  * § 11517(c)(1)–(2) (but see W8); § 11521(a) (30 days; deemed denied); § 11523.
  * § 7922.535(b) (the quote is exact; 14 days); § 7922.540(b).
* **New York.** Pub. Off. Law § 89(4)(a) (30 days; 10 business days; forward to the Committee). § 89(4)(b): its
  last sentence, "Failure by an agency to conform to the provisions of paragraph (a) … shall constitute a
  denial", grounds the deemed denial of an appeal. CPLR § 217(1) is in the corpus.
* **D.C.** Code § 2-537(a), (a)(1)–(2) and (a-1); § 2-532(e) (deemed denial and deemed exhaustion).
* **Texas.** Gov't Code § 552.301(a)–(b); § 552.302; § 552.3215(e) and (g); § 2001.146(a) and (c).
* **Illinois.** 5 ILCS 140/9.5(a) (excludes the General Assembly; 60 days); 140/9(c).
* **Maryland.** Gen. Prov. § 4-1B-04(a)–(b) (90 days); § 4-202(c); § 4-362(e)(1).
* **Virginia.** § 30-179(1); § 2.2-4019(A) (asks for a person's name, telephone and government email, so the
  post-for-person rule is needed); § 2.2-4021(B) (deemed in the party's favour).

### 2.5 Code and fixtures

* **`lexflow.law.xref.references()`.** It returns 0 references for Fla. Stat. § 607.0126. For BPC § 480, it
  labels the two PEN § 290 references `authority` and returns 18 `prerequisite_process`. For § 485, it labels
  the Gov. Code Chapter 5 span both `procedure` and `prerequisite_process`.
* **`terms.definitions()`.** It returns nothing for BPC § 22, and returns "Board" and "License" for § 477, with
  the key `lexflow:term:ca:Cal. BPC § 477:board`. So 9.2 #2 and #3 hold.
* **`ladders.json`.** 22 ladders, 143 rungs, 90 bodies; the type counts; 25 trigger codes with the stated counts;
  17 inferred rungs; 13 rungs with a cross-reference link; two quotes over 400 characters (`tx.records.8` 433,
  `ny.records.1` 432); 12 position keys (11 types and 1 post); 31 body QIDs, 7 of them not in `agencies.json`.
* **The reviewed models.** The 22 models have 55 non-private actors, as 7.4 says.
* **The loader.** `wikibase_lexipedia.py` finds properties by English label (`prepare()`) and uses
  `wbeditentity` with `clear` on update. `_snak` writes only item and string main snaks. `MODALITY` has four
  classes. The role, process and step key forms are as the design uses them.

---

## 3. Wrong, with evidence

Severity: **H** changes what a user would be told, or the published answer; **M** breaks a check, a count or a
re-run; **L** wording or presentation.

| # | Sev | Design says | Evidence | Fix |
|---|---|---|---|---|
| W1 | H | 2.3 and 9.2 #6: "§ 607.0125 has no counterpart" to § 605.0210(4). "A corporation-route ladder cannot copy the LLC one." | Fla. Stat. § 607.0123(3): "If the applicant returns the document with corrections … within 60 days after it was mailed to the applicant by the department and if at the time of return the applicant so requests in writing, the filing date of the document will be the filing date that would have been applied had the original document not been deficient". | The routes match on this point. Add a corporation rung at § 607.0123(3), and drop the "routes differ" bullet and 9.2 #6. |
| W2 | M | 0.1, 0.3, 5.5: up to 143 rung items; ~540 items; ~10 minutes | Section 1 above: 58 rungs come from references with no process item; the loader rewrites everything | Use ≤ 85 rungs now and about 450–500 items; give the load as about 2,000 writes. |
| W3 | M | 3.4, 3.9 and 3.6's cue table treat Tex. Gov't Code § 552.301 as a deferral (`defers-to`). 3.7 matches a rung only when the type agrees. | The fixture types `tx.records.2` as "external administrative review", with `mandatory: true`. | Change one side, or the evaluation misses this rung by construction. Also, the 10 business days is in § 552.301(b), not (a) (3.4's example). |
| W4 | M | 2.4 rung 2 and 3.1 present the OAH hearing as a duty, with a 30-day proposed decision and deemed adoption after 100 days | Gov. Code § 11517(a): "A contested case may be originally heard by the agency itself … Alternatively, at the discretion of the agency, an administrative law judge may originally hear the case alone". The (c) deadlines apply only to the ALJ-alone route. Under (b) the agency decides "within 100 days of submission", with no deemed outcome. § 11517(c)(1) also says a late proposed decision "does not prejudice the rights of the agency". | Make the deadlines conditional on the route (`scope_rule`), and mark the 30-day limit as directory. |
| W5 | M | 2.4 rung 8: § 486(a) is an "internal appeal" that escalates to the board | § 486(a) sets "the earliest date on which the applicant may reapply". That is a new application after a minimum wait, not a review of the denial. | Use `direction: return` (the schema already has it) and a "reapplication" subtype, not `escalates-to`. |
| W6 | M | 2.4 and 0.2: § 109(a) "says outright that the parent's head does not review"; DCA is "barred by statute from reviewing its boards' licensing decisions" | § 109(a) covers decisions "with respect to setting standards, conducting examinations, passing candidates, and revoking licenses", "except as provided in this section". A § 480 denial fits only as "passing candidates" (compare § 108, "passing upon applicants"). § 109(c) lets the director "intervene", including by injunction, on probable cause of a crime. | The not-a-rung conclusion is a sound reading. Store it with an `inferred` note naming the four listed decision kinds, add § 109(c) as an oversight power, and say "the director", not "the department". |
| W7 | M | 9.2 #5 and 1.3: one post in the fixture carries its department's QID marked `exact` (VA Tax Commissioner) | `lexflow:agency:tx:office_of_the_attorney_general` carries Q7707525 marked `exact`, but Q7707525 is P31 *position*: the reverse error. `lexflow:office-type:md:court_of_disposition` carries the specific court Q16932596 marked `exact`. | Add both to phase 1's fix list. Q7707525's English description also reads "head of the Texas Department of Criminal Justice", which is a candidate upstream draft. |
| W8 | M | 3.7: the negative fixture lists "the Florida Secretary of State **and Department of State** for refused filings" as parents that must not be rungs | The Department is the decider, not a parent. The fixture's own rung `fl.business.1` (a corrected resubmission to the Division, § 605.0210(4)) and § 607.0123(3) are rungs addressed to the Department. | Narrow the entry to "the Secretary of State as reviewer of a refusal", plus the Governor. |
| W9 | M | 5.6: "Before any create, the loader looks the key up in `wikibase_items`, then with `haswbstatement:P25=<key>`" | The loader has no `haswbstatement` lookup. It uses only `wikibase_items` and `owner()`, which recovers an item only through an identical label-and-description clash. The design's list of loader changes does not include it. CirrusSearch also indexes asynchronously. | List it as a new loader change. Run it after a short wait, or before creates in batch. |
| W10 | M | 5.6: "A rung rejected after loading is relabelled as retired" through `retire_drafts` learning the kind | `retire_drafts` skips every key whose model is `reviewed` or `agreed`, and rungs load only for those models. So a rejected or re-keyed rung would never be retired, and it would keep *review status* = reviewed. | Use a separate rule: retire every rung key not touched in this run, whatever the model's tier. |
| W11 | M | 1.4 and 3.1: power grants are `entity_links` rows (subject, `power`, `lexflow:power:<slug>`), with the Hohfeld position and question in `context` | The `entity_links` primary key is (subject, relation, object, question). § 480(a) (a power to deny) and § 480(c) (a disability to deny) on the same board office type collide on one key. So do two sections that grant the same power. `question` sits in JSON, not in the key column. | Add `hohfeld` and `section` to the key, or give grants their own table. |
| W12 | M | 4.2: the `writ_open` table is UNIQUE, "so conflicts and gaps can be checked" | It has a gap: when the record was requested within 10 days but not yet delivered, no rule matches. § 11523 keeps the window open "until 30 days after its delivery". | Add a row: > 30, true, not delivered → true. |
| W13 | M | 1.7, 7.1 #2: holder claims are dropped "as entities-contacts 5.4 already requires"; posts become first-class | entities-contacts 5.4 also drops **P2388 and P1313** at parse time, and keeps position items "only as `related_items` for identity". The design reads P2388 for `headed-by` and mints post items. | Declare both changes to entities-contacts 5.4 in 0.4. |
| W14 | L | 4.5: "Every item it links to already exists on the wiki, apart from the court" | The *judicial review* class, the trigger vocabulary item, the exhaustion, binding and review-status value items, and every new property do not exist yet. The corporation route's § 607.0126 has no statute item either: only § 605.0210 (Q164) exists. | Reword the claim. |
| W15 | L | A9 argues for a dedicated *parent organization* property so that P9 keeps one meaning, but 4.5 gives position items "P9 part of → its agency" | This mixes `org:postIn` into P9. `?x lxt:P9* ?agency` would then return posts. | Use a *position in* property, or the P2389 mapping, for posts. |
| W16 | L | 2.3 and 2.4: the Leon County court is Q7443383 | Q7443383 is "Second Judicial Circuit Court of Florida", the right court (it sits for Leon County). | Label the item "Circuit Court of the Second Judicial Circuit (Leon County)". Keep `exact`; the key can stay. |
| W17 | L | 5.6: "Do not raise the [400-character] limit: the platform ties it to the monolingual-text setting" | authority-wikibase 2.6: both limits are settable from 400 to 2,500, and the quirk means raising both. | Keep 400 by choice (links to the DokuWiki suffice), but drop the stated reason. |
| W18 | L | 1.1 example: `lexflow:rung:fl:business:605-0210-7:petition-to-compel-filing` | The fixture's subtype for that rung is "petition to compel filing (summary proceeding)". Slugged, it gives `…:petition-to-compel-filing-summary-proceeding`. | See D1. |

---

## 4. Missing

### 4.1 Legal

* **M1. The NC State CIO fee-mediation rung.** The reviewed model `curated/nc/records.json` has
  `request_fee_mediation` (requester → State CIO). G.S. § 132-6.2(b) reads: "the requester may ask the State
  Chief Information Officer or his designee to mediate the dispute". `nc.records` has only 3 rungs and no rung for
  this step. With it:
  * the ladder count is 144;
  * the NC CIO office, Q136430659, becomes a ladder body that Govdirectory lists, so section 0.2's "none of the
    90" needs a footnote;
  * the deriver will propose a rung that the fixture lacks.
* **M2. Statutory sunsets.** BPC § 7000.5(c) and § 7011(e) are repealed on January 1, 2029. So the CSLB `part-of`
  edge and the registrar post carry a statutory end date. The refresh in 5.6 watches only Wikidata P576 and
  P1366, so it would miss this. Store `valid_until` from the text.
* **M3. The BPC § 480(i) carve-out.** The State Athletic Commission, BPPE and the Horse Racing Board keep their
  existing authority. The CA licence ladder needs a `scope_rule` for it.
* **M4. Fla. Stat. § 205.023(2).** A signed statement can replace the fictitious-name registration, so the rung
  is a deferral only for businesses operating under a fictitious name.
* **M5. Gov. Code § 11521(a) stays.** The agency may stay the 30-day expiry by up to 10 days to consider a
  petition, or for up to 30 days to allow one. The deadline record needs an extension rule.

### 4.2 Wikibase and loader

* **M6. Qualifiers and references.** `_snak` and `entity()` write main snaks only, and the wiki holds 0
  qualifiers and 0 references. The design depends on both: P22 on P13, time-limit qualifiers, *power*, and
  *reference URL*, *retrieved* and *determination method*. Add this to the 5.6 loader changes, beside quantity
  snaks.
* **M7. A competing property proposal in code.** `lexflow/publish/wikibase.py` `PROPOSED` already defines:
  * "time limit" as a **string** (ISO 8601 duration), where the design wants a quantity;
  * "deadline runs from", where the design has *time limit anchor*;
  * "performed by", where the design has *played by*.

  Labels are the contract, so retire or align these before the go-ahead.
* **M8. Other plans' properties left out of the combined go-ahead.** *reference role* (bpc-480 6.5, §746) and
  *reference type* (links-codebase-map 4.1, cited in authority-wikibase 4.2) are not in 5.2's list.
* **M9. Statute-item keys for California are inconsistent on Lexipedia.** Some are bare numbers
  (`lexflow:statute:ca:7922.535`, `…:12190`), some full citations (`lexflow:statute:ca:Cal. CORP § 200`). A
  rung's P13 must find the existing item through the act_id-to-key map, never by minting
  `lexflow:statute:ca:<other spelling>`. Otherwise `owner()` fails on the label clash (the keys differ), the
  loader appends a suffix, and a duplicate statute item results.

### 4.3 Privacy

* **M10. Live holder display on DokuWiki.** If the 1.7 option is ever turned on, the name is "read live … never
  cached". DokuWiki pages, however, are rendered and stored. Restrict the option to the dashboard, and never
  allow it on DokuWiki or Wikibase. "No link other than the Wikidata item" should say the *post's* item.
* **M11. A private individual in a case caption.** 3.8 cites a Supreme Court case by a caption that names a
  private litigant. Cite it as 509 U.S. 137 (1993), or as the federal rule under 5 U.S.C. § 704.
* **M12. Certified mediators are private persons.** The NC model types the mediator `private-party`, but the
  fixture keys it as `lexflow:position-type:nc:certified_mediator`. Either keep it a private-party role, or state
  that this type never resolves to anyone.

### 4.4 Other

* **M13. Federated items.** Wikibase's "federated items" (ontology federation) is in alpha. One line saying it is
  not available as an alternative to local items would close the question 5.7 leaves open.

---

## 5. Will re-runs create duplicates?

| # | Where | Risk | Fix |
|---|---|---|---|
| D1 | The rung key `…:<section-slug>:<subtype-slug>` | `subtype` is free text, and the deriver writes its own (W18). The section slug is unspecified: the design writes `gov-11523` with the code, but `605-0210-7` and `607-0126` without it. CA has several codes, so `485` would be ambiguous. Four pinpoints already carry two rungs each, so the subtype carries the uniqueness: N.Y. § 89(4)(a), Fla. § 605.0210(7), Cal. PEN § 11126(c) and Va. § 19.2-392.12(I). A reviewer who corrects a pinpoint would mint a new key. | Build the key from the act_id, the pinpoint and a **closed subtype code list** (a vocabulary beside the ten types). Keep a `rung_aliases` table so that a corrected pinpoint keeps the old key. |
| D2 | `retire_drafts` | a rejected rung is never retired (W10) | a separate rule for untouched rung keys |
| D3 | A lost `wikibase_items` table | no `haswbstatement` lookup; `owner()` needs an identical label and description (W9) | add the lookup and test it in a dry run |
| D4 | `entity_links` primary key | power and disability grants collapse (W11) | extend the key |
| D5 | Seeding "by QID first" (entities-contacts 1.2) | `agencies.json` shares 5 QIDs between `exact` and `parent body only` entries. Q6781312 is shared by 5 entries, and Q17110658 by the NY Department of State and the Committee on Open Government. Matching on any QID would merge the Committee into the Department. The design's kind check covers P8, not seeding. | match only on `exact`, kind-checked QIDs |
| D6 | `clear` across phases | *played by*, *recipient* and *review status* go on role, step and process items that `processes()` writes. A separate `authority()` phase that saves those items again with `clear` erases `processes()`'s claims, and the reverse. | build every claim of an item in one place, or merge the claim lists before each save |
| D7 | Shared office-type keys in the fixture | 3 keys stand for 2–3 bodies each, with different `kind` values: `il:circuit_court`, `md:circuit_court`, `tx:district_court` (90 bodies, 85 keys) | seed by key with a merge rule, not last-writer-wins |
| D8 | Class lookup by label | `labels(120)` keeps the first item per label in `allpages` order. The new labels include "position", "court", "government" and "Power", and vocabulary items such as "none" and "binding". An item with the same label as a class can shadow it. | look classes up by their `lexflow:class:<label>` P25 key |

Upstream drafts are not a duplicate risk: entities-contacts 4 already makes drafting idempotent.

---

## 6. Method

* **Read.** The design; the four research notes; `ladders.json`; `agencies.json`; entities-contacts 1.2–1.7, 5
  and D1–D14; terms-wikibase §4; bpc-480 §2 and 6.5; `wikibase_lexipedia.py` and `publish/wikibase.py`;
  `curated/fl/business.json`, `curated/nc/records.json` and the actor lists of all 22 models.
* **Statute text,** from the `lexflow-app-1` container with `I.lookup` (the sections in 2.4, plus Fla. Stat.
  § 607.0123 and G.S. § 132-6.2).
* **Code, read-only:** `xref.references()` on 4 sections and `terms.definitions()` on 2.
* **Network, read-only:**
  * Wikidata: 2 `wbgetentities` calls (labels only; sent without `maxlag`, because the query service was lagged
    and both were single small reads) and 3 `wbsearchentities` calls.
  * WDQS: 9 requests, one at a time. One was rejected as malformed and rewritten; one returned 429 and was
    retried after a pause. Holder data was read as counts only, and no person's name or claim was read.
  * Lexipedia's query service: 8 queries.
  * Govdirectory: `sitemap.xml`, once.
  * GitHub: the `govdirectory/website` tree, the US and NY generators, `organization-optional.rq` and
    `CONTRIBUTING.md`.
  * mediawiki.org: 4 searches and 3 page reads (the hosting policy, twice; Wikibase/Federation).
* **Written:** this file only. Helper scripts are in the session scratchpad.
