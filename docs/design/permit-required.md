# Permit required? A decision model for small residential projects in Virginia, DC and North Carolina

Status: design prototype (N2 in [data-expansion.md](data-expansion.md) §0), 2026-10-10, revised the same day after the
verification in [verify-permit-required.md](verify-permit-required.md) (part 9 lists every change). It answers the first
half of the question lexflow could not answer, "Do I need a building permit for a deck or a shed?", from state-adopted
text only. Nothing was written to the database, the wiki or the Wikibase, and no curated place file was changed.
**This is not legal advice.** The model is a draft for review.

| File | What it is |
|---|---|
| `out/design/permit_required.dmn` | A DMN 1.3 model: 2 decisions (`permit_required`, 69 rules over 17 inputs; `other_approvals`, 12 rules), 17 input data, 13 knowledge sources, 38 requirements, with DMNDI shapes and edges. Every rule quotes the words it rests on (229 quotes; 32 citations marked "(reading)"). |
| `out/design/check_permit_required.py` | Validates the model, checks every quote against the index, checks the premises of the readings, runs 81 cases through lexflow's evaluator and SpiffWorkflow, checks this note's quotes, and mutates copies of the model. All 7 check groups pass (part 7). |
| `docs/design/permit-required.md` | This note. |

How the text was read:

* All law text comes from lexflow's search indexes, built from the open-us-law files already on disk (manifest
  `v2026.09.1`, snapshot 2026-09-30, CC BY-NC 4.0): the regulations indexes of N1 (`/data/index/regulations_va.sqlite`,
  22,396 sections; `regulations_dc.sqlite`, 22,914; `regulations_nc.sqlite`, 21,314) and the statute indexes
  (`statutes_va`, `statutes_nc`). Each quote names its section and the official URL the index row stores.
* **No model-code text.** The model stores only text written and adopted by Virginia, the District and North
  Carolina. It holds no ICC text and no link to ICC or UpCodes, and it names no IRC or IBC section on its own account.
  Where state text itself cites a model-code section number (VA 108.2 item 5's "Section 3306", DC 105.2 item 17's
  "Section 3103") or "the IBC" (VA 101.7), the model quotes that state text and nothing more. The checker tests for ICC
  and UpCodes links, the IRC and IBC titles, and "IRC R105" and "IBC 105" pinpoints. The DC Residential Code supplement
  draws the same line itself: “The International Residential Code is copyrighted by the ICC and therefore is not
  republished here.” Whether state text that mirrors ICC wording (the USBC's Chapter 1, the DC supplements) may be
  quoted in full is counsel question C21 in [data-expansion.md](data-expansion.md) §4.3.
* **Three live reads**, all before the verification. On 2026-10-10 (02:07 UTC on 11 October) the official pages for
  13VAC5-63-80, 13VAC5-63-20 and G.S. 160D-1110 were each read once, with the User-Agent `lexflow-research/0.1
  (https://github.com/alibama/lexflow)`. robots.txt was read first: `law.lis.virginia.gov` has none (it answers 301 to
  `/robots.txt/`, which is 404, so nothing is disallowed under RFC 9309), and `www.ncleg.gov` asks for a 2-second crawl
  delay, which was kept. Eleven of the quoted spans were found word for word on the live pages. The Virginia page's
  history note records the last amendment as "Volume 40, Issue 9, eff. January 18, 2024", which is the effective date
  of the 2021 edition. That date is not in the index text. The DC file was not fetched, because its official URL is a
  download link. Nothing was stored from these reads. The revision made no network request: every section it added
  was read from the indexes.

---

## Summary

| Project | Virginia (13VAC5-63-80, statewide) | District of Columbia (12-A DCMR 105) | North Carolina (G.S. 160D-1110) |
|---|---|---|---|
| Shed | **No permit** if one story, detached, 256 sq ft or less and not Group F-1 or H (108.2 item 2). In a special flood hazard area the building official may require one (Exception 2). An industrialized (modular) shed is answered the same way (429.5) | **No permit** for one garden storage shed of 50 sq ft or less and under 10 ft high per lot (105.2 item 8), **except** in a historic district or on a designated property (105.2.5) or in a Flood Hazard Area (105.2.6). There a limited-review permit application is required | **Not settled** by the statutes on disk |
| Playhouse | As a shed (item 2) | 36 sq ft or less: no permit (item 13). Historic: ask the Historic Preservation Office. Flood Hazard Area: floodplain review | Not settled |
| Play equipment (swing sets, climbing frames) | **No permit**: outside the USBC (102.3 item 7) | No permit (item 12). Historic: ask the Historic Preservation Office. Flood Hazard Area: floodplain review | Not settled |
| Storage container used for storage | **No permit**, at any size: outside the USBC (102.3 item 11) | **Depends**: no item names containers. Flood Hazard Area: an application either way | Not settled |
| Farm building | **No permit**: outside the USBC (102.3 item 9). In a flood plain: **depends** (flood-proofing regulations) | **Permit** (a reading: no item exempts farm buildings) | **Depends**: building rules do not apply outside a municipality's building-rules jurisdiction (143-138(b4)) |
| New deck | **Permit**, at any size, height above grade or attachment. Item 13 lets the building official treat minor work as exempt. A model-code deck exemption does not apply (101.7) | **Permit** | **Permit**: new framing adds load-bearing structure (a reading) |
| Deck resurfacing | **Permit**: a repair is construction (13VAC5-63-200), unless the building official deems it minor and ordinary (item 14.11) | **Depends**: it may be an ordinary repair (105.2.2). In a Flood Hazard Area: **an application either way** (105.2.6) | **No permit** for a single-family residence at $40,000 or less (160D-1110(c)(1)). A two-family dwelling, or over $40,000: permit (a reading). A townhouse: depends |
| Fence, new or replaced | **No permit** at any height (item 5), unless it is a pool barrier or a pedestrian-safety fence | **Permit**: item 4 exempts only repair in kind | Not settled |
| Fence repair in kind | As a fence. A pool-barrier or safety fence: permit, unless the building official deems the repair minor and ordinary (item 14.11) | None (item 4), except in a historic district (depends) or a Flood Hazard Area (an application) | Not settled |
| Masonry wall | 6 ft or less above grade, not counting ornamental column caps: no permit (item 6) | Permit | Not settled |
| Retaining wall | Less than 3 ft of unbalanced fill, with no surcharge: no permit (item 7) | 4 ft or less from the bottom of the footing, disturbing 50 sq ft or less: no permit (item 10), except in a historic district or Flood Hazard Area | Not settled |
| Addition | Permit | Permit | Permit (a reading) |
| Wiring, plumbing, gas or mechanical work, with any project | **Permit** (108.1 item 1). With a structure outside the USBC (play equipment, a container, a farm building): depends | **Permit** (105.1 item 2) | **Permit** (a reading; (a)(2) to (4), (c)(2) and (c)(3)). Farm buildings: as above |

Everywhere, zoning and the other approvals still apply even when no building permit is needed (decision
`other_approvals`, part 2).

The four test cases named in the request, as the model answers them (part 7 has all 81):

| Case | Answer | Exemption item | Rule |
|---|---|---|---|
| A1. Virginia: 200 sq ft one-story detached storage shed | no permit | 13VAC5-63-80 B item 2 | r1 |
| A2. Virginia: 300 sq ft one-story detached storage shed | permit required | none (over 256 sq ft) | r3 |
| A3. Virginia: ground-level deck, 8 in above grade, 120 sq ft, freestanding | permit required | none: no item covers decks | r7 |
| B1. DC: 48 sq ft garden storage shed, 8 ft high, in a historic district | permit application required, subject only to historic preservation review | 12-A DCMR 105.2 item 8, not available under 105.2.5 | r22 |

A3 is the case that most needs saying. The rule many people have heard of, that a low, small, freestanding deck needs
no permit, is a model-code rule. None of the three state texts has it. In Virginia, DC and North Carolina, a deck's
height above grade and attachment do not change the answer, and the model asks for neither when the project is a deck.
Virginia's own text says why a model-code exemption cannot apply there. 101.7 (13VAC5-63-10 G): “Any provisions of
Chapters 2 through 35 of the IBC or any provisions of the codes and standards referenced in the IBC that address the
same subject matter and impose differing requirements are deleted and replaced by the provisions of Chapter 1.” Note 1
to 101.2 lists the IRC among the codes the IBC references, and 101.6 items 1 and 2 give Chapter 1 precedence over both.
So only 108.2's list of exemptions counts. In DC, 12-A DCMR 105 replaces the model code's Section 105 outright, and
12-B DCMR R101.2 sends houses to it (§3.2).

---

## 1. Sources

| Knowledge source | Official URL (as the index stores it) | Used for |
|---|---|---|
| 13VAC5-63-80, USBC Section 108 | <https://law.lis.virginia.gov/admincode/title13/agency5/chapter63/section80/> | the permit duty (108.1), the exemption list (108.2) and its exceptions |
| 13VAC5-63-20, USBC Section 102 | <https://law.lis.virginia.gov/admincode/title13/agency5/chapter63/section20/> | why the list is statewide; the land-use rules it leaves in place; the whole-code exemptions (102.3) |
| 13VAC5-63-10, USBC Section 101 | <https://law.lis.virginia.gov/admincode/title13/agency5/chapter63/section10/> | 101.7: Chapter 1 replaces differing model-code administrative provisions |
| 13VAC5-63-200, USBC Chapter 2 | <https://law.lis.virginia.gov/admincode/title13/agency5/chapter63/section200/> | the definitions of "Construction" and "Farm building or structure" |
| 13VAC5-63-220, USBC Chapter 4 amendments | <https://law.lis.virginia.gov/admincode/title13/agency5/chapter63/section220/> | 429.5: permits for the site work of an industrialized building |
| Va. Code § 36-97 | <https://law.lis.virginia.gov/vacode/36-97/> | zoning is not a building regulation |
| 12-A DCMR 105 | [dcregs.dc.gov file](https://dcregs.dc.gov/Common/DCMR/RuleList.aspx?DownloadFile={64284980-8CFE-4134-BB96-94FBB25965E0}) (67 DCR 5690) | the permit duty, the exemption list, ordinary repairs, public space, the historic and flood limits |
| 12-B DCMR 101 | [dcregs.dc.gov file](https://dcregs.dc.gov/Common/DCMR/RuleList.aspx?DownloadFile={8F32FAD3-B817-49C7-8C53-F4AFFDA1E1FA}) (67 DCR 6033) | the Residential Code is administered under 12-A Chapter 1 |
| 10-C DCMR 303 | [dcregs.dc.gov file](https://dcregs.dc.gov/Common/DCMR/RuleList.aspx?DownloadFile=3092545F-0000-C45F-90B0-FDCCA7A2E4C6) (51 DCR 7447) | work on historic properties needs a permit; the construction permit is governed by 12 DCMR Chapter 1, and no separate preservation permit is required |
| 10-C DCMR 304 | [dcregs.dc.gov file](https://dcregs.dc.gov/Common/DCMR/RuleList.aspx?DownloadFile=3092545F-0000-C379-A514-3E614E04143B) (51 DCR 7447) | what counts as an alteration of a historic property; minor repairs that need a permit there |
| N.C. Gen. Stat. § 160D-1110 | <https://www.ncleg.gov/EnactedLegislation/Statutes/HTML/BySection/Chapter_160D/GS_160D-1110.html> | the permit duty, the trade permits, the $40,000 exclusion, erosion control |
| N.C. Gen. Stat. § 143-138 | <https://www.ncleg.gov/EnactedLegislation/Statutes/HTML/BySection/Chapter_143/GS_143-138.html> | the same exclusion, binding on local variances; farm buildings; what local governments may adopt |
| N.C. Gen. Stat. § 160D-947 | <https://www.ncleg.gov/EnactedLegislation/Statutes/HTML/BySection/Chapter_160D/GS_160D-947.html> | historic districts: a certificate of appropriateness |

The note also quotes 13VAC5-63-30, -40 and -70, Va. Code §§ 36-98 and 36-105, 10-C DCMR 320 and G.S. 160D-1128, from
the same indexes.

Every regulation row is one the index keeps as in force. Superseded DC supplements and repealed stubs are not in the
index (N1 leaves them out).

---

## 2. The model

### 2.1 Decision requirements

```
17 input data ──► permit_required (69 rules, UNIQUE) ◄── 13VAC5-63-80, -20, -10, -200, -220, 12-A DCMR 105,
                                                          12-B DCMR 101, 10-C DCMR 303, 304, G.S. 160D-1110, 143-138
jurisdiction,  ──► other_approvals (12 rules, UNIQUE) ◄── Va. Code 36-97, 13VAC5-63-20, 12-A DCMR 105,
historic, flood                                           10-C DCMR 304, G.S. 160D-1110, 160D-947, 143-138
```

`permit_required` has three outputs:

* `permit`: `yes` (a permit, or a permit application, is required), `no` (no permit is required), or `depends`.
* `exemption`: the exemption item that applies, the item that a limit displaced (for example "12-A DCMR 105.2 item 8,
  not available under 105.2.5"), or `none`.
* `basis`: one or two sentences that say why, and what to ask.

**How the officials' discretion is treated** (the rule is in the decision's description, and the checker tests that it
is there):

* `yes` where the text requires a permit unless the building official deems the work exempt: Virginia's item 13
  (“Construction work deemed by the building official to be minor and ordinary”) and item 14.11 (“Other repair work
  deemed by the building official to be minor and ordinary”). The basis names the item and says to ask. This applies
  to a new deck (r7), deck resurfacing (r8) and the repair of a pool-barrier fence (r12) alike: the VCC's
  “Construction. The construction, reconstruction, alteration, repair, or conversion of buildings and structures.”
  (13VAC5-63-200) puts a repair under 108.1 item 1 just as a new structure is.
* `depends` where the text exempts the work but lets an official require a permit anyway: Exception 2 (r2, r10, r14,
  r17).
* `depends` where the answer turns on a question the text on disk does not settle: whether work is a DC “ordinary
  repair” (r33, and r36 through 105.2.5's “except as deemed an ordinary repair”), whether a playhouse or play equipment
  is an “other site feature” (r29, r60), whether a DC storage container is exempt (r62), whether a townhouse unit is a
  “single-family residence” (r67), whether a Virginia whole-code exemption reaches trade work (r57), and what the North
  Carolina code books require for work the statute does not take out of its $40,000 exclusion (r51).
* In North Carolina, where the statute does take the work out of the exclusion (new load-bearing structure, over
  $40,000, a two-family dwelling, trade work: r47, r49, r50, r66, r69), the answer is `yes` on the reading that the
  Code requires the permit. That `yes` would change if the code books, which are not on disk, exempt the work (§3.3).

`other_approvals` names what the building-permit answer does not replace: zoning, historic district review,
floodplain rules, DC public space permits and North Carolina's erosion control plan.

Both tables are UNIQUE, so exactly one rule matches any input. Precedence is written row by row, never by rule order:
105.2.5 and 105.2.6 over the 105.2 items, Exception 2 over the 108.2 items, and trade work over the structure's
exemption. The checker proves that no two rules overlap and that no input is left without a rule.

The rules added in the revision are numbered after the original 51 (r52 to r69), so r1 to r51 keep their meaning; only
r33 was narrowed (to work outside a Flood Hazard Area), and r8 and r12 changed their answer (part 9).

### 2.2 Inputs, and the questions each project needs

The model's scope is a project at a detached one- or two-family dwelling or a townhouse. That is what DC's items 8,
12 and 13 require (a shed that “is an accessory structure to a building of Use Group R-3 or to a building under the
jurisdiction of the Residential Code”, a playhouse or play equipment “accessory to detached one- and two-family
dwellings and townhouses”), and what the USBC's Residential Code covers. North Carolina's $40,000 exclusion is
narrower, so the model asks which kind of dwelling it is there (`dwelling`).

| Input | Meaning |
|---|---|
| `jurisdiction` | `va`, `dc` or `nc` |
| `project` | `shed`, `playhouse`, `deck` (new deck or new framing), `deck_resurfacing` (new decking, railings, pickets or stair treads on the existing framing), `fence` (new, or replacing an existing fence, in kind or not), `fence_repair` (repair in kind only), `masonry_wall` (freestanding concrete or masonry), `retaining_wall`, `addition`, `playground_equipment` (swing sets, slides, climbing frames and the like; a play structure that is a small building is a playhouse), `storage_container` (a freight, moving or storage container placed for use as a storage container), `farm_building` (as 13VAC5-63-200 defines it) |
| `floor_area_sqft` | the building area of a shed or playhouse |
| `one_story`, `attached_to_dwelling`, `group_f1_or_h` | VA item 2's conditions |
| `height_ft` | as the text measures it: a VA wall above the finished grade, not counting ornamental column caps; a DC shed's overall height; a DC retaining wall from the bottom of the footing |
| `unbalanced_fill_ft`, `surcharge_or_liquids` | VA item 7 |
| `land_disturbance_sqft` | DC item 10 |
| `other_exempt_shed_on_lot` | DC item 8: one exempt shed per lot |
| `safety_barrier` | VA item 5: the fence is a swimming-pool barrier, or is required for pedestrian safety under Section 3306 |
| `cost_usd` | NC's $40,000 exclusion |
| `dwelling` | NC deck resurfacing: `single_family`, `two_family` or `townhouse` |
| `historic` | a historic district, or a historically designated building or structure |
| `flood_hazard_area` | a (special) flood hazard area |
| `trade_work` | the work includes electric wiring, plumbing, gas piping, or heating, cooling or other mechanical work, other than the minor and like-for-like work the states list as exempt |

The checker derives the questions an answer must ask from the table itself. These are the columns the rules of each
jurisdiction and project read, and the rest of the inputs do not matter for that project. `trade_work` is asked for
every project except a North Carolina farm building, so the table leaves it out:

| Project | Virginia | DC | North Carolina |
|---|---|---|---|
| shed | area, one story, attached, Group F-1 or H, flood | area, height, other exempt shed, historic, flood | none (the answer is `depends`) |
| playhouse | area, one story, attached, Group F-1 or H, flood | area, historic, flood | none |
| deck | **none** | **none** | none |
| deck_resurfacing | none | flood | cost, dwelling |
| fence | safety barrier, flood | none | none |
| fence_repair | safety barrier, flood | historic, flood | none |
| masonry_wall | height, flood | none | none |
| retaining_wall | unbalanced fill, surcharge, flood | height, land disturbance, historic, flood | none |
| addition | none | none | none |
| playground_equipment | none | historic, flood | none |
| storage_container | none | flood | none |
| farm_building | flood | none | none (not even `trade_work`) |

In DC, `historic` must always be asked for sheds, playhouses, play equipment, fence repairs and retaining walls, since
it changes the answer. In Virginia it never changes the building-permit answer for these projects, but it does change
`other_approvals`.

---

## 3. The rules

### 3.1 Virginia: 13VAC5-63-80 (USBC Section 108) and 13VAC5-63-20 (Section 102)

**The duty.** 108.1: “Application for a permit shall be made to the building official and a permit shall be obtained
prior to the commencement of any of the following activities”, the first of which is “Construction or demolition of a
building or structure. Installations or alterations involving (i) the removal or addition of any wall, partition, or
portion thereof; (ii) any structural component”, and, further on in the same item, “(v) water supply and distribution
system, sanitary drainage system, or vent system; (vi) electric wiring; (vii) fire protection system, mechanical
systems, or fuel supply systems”.

**The exemptions.** 108.2: “application for a permit and any related inspections shall not be required for the
following; however, this section shall not be construed to exempt such activities from other applicable requirements
of this code”. So an exempt shed, fence or wall must still meet the code; the model's `no` bases say so. The owner can
always opt in: “when an owner or an owner's agent requests that a permit be issued for any of the following, then a
permit shall be issued and any related inspections shall be required”. The model uses these items:

| Item | Text | Rules |
|---|---|---|
| 1 | “Installation of wiring and equipment that (i) operates at less than 50 volts, (ii) is for broadband communications systems, (iii) is exempt under Section 102.3(1) or 102.3(4), or (iv) is for monitoring or automation systems in dwelling units” | r56 (the only wiring item) |
| 2 | “One story detached structures used as tool and storage sheds, playhouses, or similar uses, provided the building area does not exceed 256 square feet (23.78 m 2 ) and the structures are not classified as a Group F-1 or H occupancy.” | r1 to r6 |
| 5 | “Fences of any height unless required for pedestrian safety as provided for by Section 3306 or used for the barrier for a swimming pool.” | r9 to r12 |
| 6 | “Concrete or masonry walls, provided such walls do not exceed six feet in height above the finished grade.” and “Ornamental column caps shall not be considered to contribute to the height of the wall” | r13 to r15 |
| 7 | “Retaining walls supporting less than three feet of unbalanced fill that are not constructed for the purpose of impounding Class I, II, or III-A liquids or supporting a surcharge other than ordinary unbalanced fill.” | r16 to r19 |
| 13 | “Construction work deemed by the building official to be minor and ordinary and that does not adversely affect public health or general safety.” | r7 (the deck caveat) |
| 14.11 | “Other repair work deemed by the building official to be minor and ordinary which does not adversely affect public health or general safety.” | r8, r12 (the caveat) |
| Exception 2 | “Application for a permit may be required by the building official for any items exempted in this section that are located in a special flood hazard area.” | r2, r10, r14, r17 |

**The whole-code exemptions.** 102.3 (13VAC5-63-20 D) takes some structures out of the USBC altogether: “The following
are exempt from this code”. Since 108.2's Exception 2 reaches only “items exempted in this section”, it does not reach
these.

| Item | Text | Rules |
|---|---|---|
| 7 | “Playground or recreational equipment, such as swing sets, sliding boards, climbing bars, jungle gyms, skateboard ramps, and similar equipment.” | r55 |
| 8 | “Industrialized buildings subject to the Virginia Industrialized Building Safety Regulations ( 13VAC5-91 ) and manufactured homes subject to the Virginia Manufactured Home Safety Regulations ( 13VAC5-95 ); except as provided for in Section 429 …” | r3, r20 (no change of answer) |
| 9 | “Farm buildings and structures, except for a building or a portion of a building located on a farm that is operated as a restaurant …”, and “However, farm buildings and structures lying within a flood plain or in a mudslide-prone area shall be subject to flood-proofing regulations or mudslide regulations, as applicable.” | r53, r54 |
| 11 | “Off-site manufactured intermodal freight containers, moving containers, and storage containers placed on site temporarily or permanently for use as a storage container.” | r52 |

Notes on the Virginia rows:

* **The boundaries are the text's.** “does not exceed 256 square feet” includes 256 (case A4). “less than three feet
  of unbalanced fill” excludes 3 (case A23). “do not exceed six feet” includes 6 (case A18), and column caps do not
  count.
* **Decks.** None of the 16 items names a deck. The checker confirms that "deck" occurs in 108.2 only in item 14.6
  (roof decking). So a new deck is construction of a structure under 108.1 (r7, marked as a reading), whatever its size
  or height, unless the building official deems it minor and ordinary under item 13. 101.7 rules out a model-code deck
  exemption (the A3 paragraph above). Item 13 is the official's call, not the owner's, so the model answers `yes` and
  says to ask.
* **Deck resurfacing and pool-barrier repairs** are `yes` with the item 14.11 caveat (r8, r12). The verification found
  the earlier `depends` inconsistent with r7 (W4): with the VCC's definition of “Construction”, a repair of a structure
  is under 108.1 item 1 in the same way a new one is, and only item 14.11, at the official's discretion, lifts it. The
  earlier reasoning, that the question was whether deck boards are a “structural component”, is dropped: the
  definition makes that question unnecessary.
* **Trade work** (r56). 108.1 item 1 requires a permit for installations involving water, drainage and vent systems,
  electric wiring, and mechanical and fuel supply systems. 108.2 exempts wiring only in item 1 (the checker confirms
  that "wiring" occurs in 108.2 only there) and some like-for-like replacements in items 10 and 14.2 to 14.4. That an
  item which exempts a structure (a shed, a fence) does not exempt the circuit run to it is a reading, marked as one. With a
  structure that 102.3 takes out of the code (play equipment, a container, a farm building), whether the exemption
  reaches the trade work the text does not say, so the answer is `depends` (r57).
* **Farm buildings** (r53, r54) are those the state defines: “Farm building or structure. A building or structure not
  used for residential purposes, located on property where farming operations take place, and used primarily for any
  of the following uses” (13VAC5-63-200; Va. Code § 36-97 defines it in nearly the same words). In a flood plain the
  answer is `depends`: the structure is outside the USBC, but subject to flood-proofing regulations, and the model reads the
  special flood hazard area as the flood plain the clause means.
* **Industrialized buildings** keep the answer of what they are (a shed, an addition). 102.3 item 8 excepts “Section
  429”, and 429.5 (13VAC5-63-220) says: “Site work for the erection and installation of an industrialized building
  shall comply with the manufacturer's installation instructions.” and “In addition, all administrative requirements
  of this code for permits, inspections, and certificates of occupancy are also applicable.” Those administrative
  requirements include 108.2, so a small industrialized shed is answered by item 2 as a site-built one is (a reading;
  r3 and r20 carry the citation, marked).
* **Exception 1** (“Application for a permit may be required by the building official for the installation of
  replacement siding, roofing, and windows in buildings within a historic district designated by a locality pursuant
  to § 15.2-2306 of the Code of Virginia.”) covers none of the model's projects. So `historic` does not change a
  Virginia permit answer. It changes `other_approvals`.
* **The edition.** 13VAC5-63-10: “This code is also known as the 2021 edition of the USBC due to the use of the 2021
  editions of the model codes.” The text in force took effect on January 18, 2024, according to the official page's
  history note. 103.2 gave a year's choice of editions: “Construction for which a permit application is submitted to
  the local building department on or after the effective date of the 2021 edition of the code shall comply with the
  provisions of this code, except for permit applications submitted during a one-year period beginning on the
  effective date of the 2021 edition of the code.”

**Statewide, and what it leaves alone.** 102.2 (13VAC5-63-20 B): “The USBC shall supersede the building codes and
regulations of the counties, municipalities, and other political subdivisions and state agencies.” The statute says
the same: “Such building code shall supersede the building codes and regulations of the counties, municipalities and
other political subdivisions and state agencies.” (Va. Code § 36-98). But 102.2 also says “this code shall not
supersede proffered conditions accepted as a part of a rezoning application”, and it lists the others. Among them are
“land use requirements in airport or highway overlay districts, historic districts created pursuant to § 15.2-2306 of
the Code of Virginia” and “local flood plain regulations adopted as a condition of participation in the National Flood
Insurance Program”. Zoning is outside the USBC altogether: “"Building regulations" does not include zoning ordinances
or other land use controls that do not affect the manner of construction or materials to be used in the erection,
alteration, or repair of a building or structure.” (Va. Code § 36-97). Those three passages are the Virginia rows of
`other_approvals`.

### 3.2 District of Columbia: 12-A DCMR 105

12-A DCMR 105 is the District's own Section 105, which replaces the model code's. It governs houses too:
“Administration and enforcement of the Residential Code shall be governed by Chapter 1 of the Building Code, Title
12-A DCMR.” (12-B DCMR R101.2).

**The duty.** 105.1: “Unless specifically exempted under Section 105.2, an owner or authorized agent who intends to
undertake any of the activities set forth in items 1 through 5 below, or to cause any such work to be done shall first
make application to the code official and obtain the required permit(s) relevant to the intended work”. Item 1 is
“Construct, enlarge, alter, repair, move, demolish, raze, or change the occupancy of a building or other structure”.
Item 2 is the trade work: “Erect, install, enlarge, alter, repair, remove, convert or replace any electrical, gas,
mechanical, or plumbing system, the installation of which is regulated by the Construction Codes, or to cause any such
work to be done” (r65). 105.1.1 lists trade permits as their own class, and fence permits among the miscellaneous
permits (“7.4 Fences.”).

**The exemptions, and their limits.** 105.2 opens: “This Section 105.2 sets forth exemptions from permit requirements,
subject to historic and Flood Hazard Area restrictions set forth in Sections 105.2.5 and 105.2.6 respectively.” The
Building items the model uses:

| Item | Text | Rules |
|---|---|---|
| 4 | “Repair in kind of existing fences.” | r35 to r38 |
| 8 | “A single garden storage shed that does not exceed 50 square feet (4.65 m2) in area, is less than ten feet (3048 mm) in overall height, is an accessory structure to a building of Use Group R-3 or to a building under the jurisdiction of the Residential Code, and is erected on a lot with no other exempted storage shed.” | r21 to r27 |
| 10 | “Retaining walls that are not over four feet (1219 mm) in height, measured from the bottom of the footing to the top of the wall, only where the area of land disturbance does not exceed 50 square feet (4.65 m2).” | r40 to r45 |
| 12 | “Swings and other playground equipment accessory to detached one- and two-family dwellings and townhouses.” | r59 to r61 |
| 13 | “A tree house or playhouse, no more than 36 square feet, (3.35 m2) in area and accessory to detached one- and two-family dwellings and townhouses.” | r28 to r31 |
| 105.2.2 | “Permits are not required for ordinary repairs to buildings, other structures or equipment.” Ordinary repairs exclude, among other things, “the removal or cutting of any structural beam or load bearing support” and “Addition to, alteration of, replacement or relocation of any standpipe, water supply, sewer, drainage, drain leader, gas, soil, waste, vent or similar piping, electric wiring or mechanical or other work affecting public health or general safety.” | r33, r58 (deck resurfacing), r65 |

There is no deck item. The checker confirms that no Building item of 105.2 mentions a deck. A new fence, a masonry
wall, a deck and an addition all need a permit under 105.1 (r32, r34, r39, r46).

**Fence repair, not replacement** (r34, r35). Item 4 says “Repair in kind of existing fences.” Item 7 is the
replacement item, “Replacement in kind of one of the items listed hereafter.”, and its list (7.1 to 7.7) has no
fences; the checker confirms both. 105.2.5, on the other hand, describes item 4 as “4. Repair or replacement of
fences, except as deemed an ordinary repair”. This is a judgement call, taken conservatively: `fence_repair` means
repair in kind only, and replacing a fence, even in kind, is `fence`, which answers `yes` (r34). Its basis gives the
105.2.5 wording as the reason to ask the code official whether a replacement in kind is treated as exempt.

**The historic-district limit (105.2.5).** When work that 105.2 would exempt is “on the land of or the exterior of
buildings or other structures located in historic districts, or of historically designated buildings or other
structures, an application for a building permit subject only to historic preservation review pursuant to Section
105.1 shall be required for the following work described in Section 105.2 Building”. The list is items 1, 4, 5, 7,
8, 9 and 10, among them “4. Repair or replacement of fences, except as deemed an ordinary repair”, “8. Garden storage
shed” and “and 10. Retaining walls”. And: “The code official shall not issue a permit based on an application subject
solely to historic preservation review under this section without the prior review and approval of the Historic
Preservation Office.” So:

* an exempt-size shed or retaining wall in a historic district needs that limited permit application (r22, r41:
  `yes`). For retaining walls 10-C DCMR 304.2 agrees: “a permit is required for various minor repairs to historic
  landmarks or properties within historic districts, even though a permit is not required for the same work on
  non-historic properties”, among them “Replacement of retaining walls regardless of height” (r41, r43);
* a fence repair in a historic district needs it unless the work is deemed an ordinary repair (r36: `depends`);
* a playhouse is item 13, and play equipment item 12; 105.2.5 lists neither (the checker confirms the list). So the
  building-code exemption stands. But the preservation rules point both ways. 10-C DCMR 303.1 begins “Permits are
  required for work affecting historic landmarks and historic districts, including demolition, alteration,
  subdivision, and new construction as described in D.C. Official Code §§ 6-1104 through 6-1107.”, and 304.1 counts as
  an alteration “Construction or replacement of a retaining wall, fence, deck, patio, garden storage shed, swimming
  pool, or other site feature”; a playhouse or a swing set may be an "other site feature". 303.1 goes on: “The
  requirements for a construction permit are governed by the D.C. Construction Codes (12 DCMR Chapter 1).”, and 303.3
  says “A separate historic preservation permit or certificate of appropriateness is not required.” Those send the
  permit question back to 12-A DCMR 105, and so to 105.2.5's list. The model answers `depends`: ask the Historic
  Preservation Office (r29, r60).

**The Flood Hazard Area limit (105.2.6).** For exempt work, when “the work is to occur on premises wholly or partially
within a Flood Hazard Area, an application for a permit subject only to review by the Floodplain Administrator shall
be required.” (r23, r24, r30, r37, r38, r42, r43, r61). Unlike 105.2.5, 105.2.6 has no list: it reaches every
exemption of Section 105.2, and ordinary repairs (105.2.2) are one of them, since 105.2 opens by making its exemptions
subject to 105.2.5 and 105.2.6. So deck resurfacing in a Flood Hazard Area needs an application either way (r58): as
an ordinary repair, under 105.2.6; if it is not one, under 105.1. The first version of the model answered `depends`
there (W1). The same logic gives `yes` for a storage container in a Flood Hazard Area (r63). Historic status does not
change the resurfacing answer: 105.2.5 lists only Building items, and ordinary repairs are not among them (case B13c).

**Public space (105.2.4).** “When the proposed scope of work would qualify to be exempted from permit pursuant to
Section 105.2 of this chapter, and the work is to occur wholly or partially on public space, the applicant shall be
responsible for obtaining all public space permit(s) that are required by DDOT.” That is an other approval; every DC
row of `other_approvals` says it.

**Storage containers and farm buildings.** No item of 105.2 names a storage container. A container kept as a storage
building is a structure 105.1 requires a permit to erect, unless it is a garden storage shed within item 8 (project
`shed`); a temporary one may fall under item 17, which turns on “Section 3103”, a model-code section that is not on
disk. So the answer is `depends` (r62). No item exempts farm buildings either (item 11 covers only “Shade cloth
structures constructed for horticultural nursery or agricultural purposes, not including service systems.”), so a farm
building needs a permit (r64, a reading).

**Historic review is separate from the permit's exemptions.** Under 10-C DCMR 304.1, “Work considered an alteration
under the Act shall include, but is not limited to, any of the following, regardless of whether or not the work is
visible from public space”. The list includes the site features above and “Any addition to the building envelope”. That
is the DC historic row of `other_approvals`, for every project, permit or not. For the process model: 10-C DCMR 320.1
delegates much of this to the staff (“The staff is delegated authority to review the following types of work”),
including “Rear decks and roof decks not visible or obtrusive from a public street”, “Fences up to 42 inches high in
front yards and up to 7 feet high in rear yards” and “Retaining walls, patios, garden storage sheds, swimming pools,
and similar site features”.

### 3.3 North Carolina: G.S. 160D-1110 (and 143-138(b4) and (b5))

North Carolina's exemption list is in its building code books, which are published through ICC and are not on disk
(lexflow does not store them; [data-building-codes.md](data-building-codes.md) §3.11). On disk is the statute.

**The duty.** 160D-1110(a): “no person shall commence or proceed with any of the following without first securing all
permits required by the North Carolina State Building Code and any other State or local laws applicable to any of the
following activities”, starting with “The construction, reconstruction, alteration, repair, movement to another site,
removal, or demolition of any building or structure.” The trade work follows: “The installation, extension, or
general repair of any plumbing system”, “The installation, extension, alteration, or general repair of any heating or
cooling equipment system.” and “The installation, extension, alteration, or general repair of any electrical wiring,
devices, appliances, or equipment”. The duty refers back to the Code: the statute requires the permits the Code
requires.

**The $40,000 exclusion.** 160D-1110(c): “No permit issued under Article 9 of Chapter 143 of the General Statutes is
required for any construction, installation, repair, replacement, or alteration costing forty thousand dollars
($40,000) or less and performed in accordance with the current edition of the North Carolina State Building Code in
any single-family residence, farm building, or commercial building unless the work involves any of the following”. Its
first item is “The addition, repair, or replacement of load-bearing structures. However, no permit is required for
replacement of windows, doors, exterior siding, or the pickets, railings, stair treads, and decking of porches and
exterior decks that otherwise meet the requirements of this subsection.” The next two keep trade work out: “The
addition or change in the design of plumbing.” and “The addition, replacement, or change in the design of heating,
air-conditioning, or electrical wiring, devices, appliances, or equipment, other than like-kind replacement of
electrical devices and lighting fixtures.” G.S. 143-138(b5) repeats the exclusion and binds local variances: “No
permit shall be required under the Code or any local variance thereof approved under subsection (e) for any
construction, installation, repair, replacement, or alteration performed in accordance with the current edition of
the North Carolina State Building Code and costing forty thousand dollars ($40,000) or less in any single family
residence, farm building, or commercial building”.

**What the statute settles for decks:**

* Replacing the decking, pickets, railings or stair treads of an existing deck of a single-family residence for
  $40,000 or less needs no permit (r48, explicit; cases C2 and C3, the second at exactly $40,000).
* The exclusion reaches only a “single-family residence” (or a farm or commercial building). A two-family dwelling is
  none of these, so for a duplex the exclusion does not apply, and the answer is a permit on the same reading of (a) as
  r49 (r66, case C2b). Whether a townhouse unit is a single-family residence the statutes do not say: `depends` (r67,
  case C2c). The first version of the model answered `no` for both (W3).
* New deck framing adds load-bearing structure, so the exclusion does not reach it. The permit duty of (a) then applies
  (r47). That is a reading on two counts: that posts, beams and joists are "load-bearing structures", and that the
  Code's own permit section, which is not on disk, requires a permit for the work.
* Resurfacing over $40,000 is outside (c), so the answer is a permit, on the same reading of (a) (r49). Additions
  likewise (r50), and trade work (r69).

**Plainly:** the North Carolina `yes` answers (r47, r49, r50, r66, r69) rest on the same deferral to code books not on
disk that makes r51 `depends`. The difference is that for these the statute itself takes the work out of its
exclusion. If the code books exempt any of this work (a small deck, say), those answers are wrong, and they are
marked "(reading)" so that this stays visible.

**Farm buildings** (r68). 143-138(b4): “Building rules do not apply to (i) farm buildings that are located outside the
building-rules jurisdiction of any municipality, (ii) farm buildings that are located inside the building-rules
jurisdiction of any municipality if the farm buildings are greenhouses or therapeutic equine facilities”, and “A "farm
building" means any nonresidential building or structure that is used for a bona fide farm purpose as provided in G.S.
160D-903(a).” The model does not ask where the building is, so the answer is `depends`, for trade work too.

**Erosion control** (`other_approvals` r9 to r12). 160D-1110(e): “No building permit shall be issued pursuant to
subsection (a) of this section or G.S. 160D-1110.1(h) for any land-disturbing activity, as defined in G.S. 113A-52, or
for any activity covered by G.S. 113A-57, unless an erosion and sedimentation control plan for the site of the
activity or a tract of land including the site of the activity has been approved under Article 4 of Chapter 113A of
the General Statutes, the Sedimentation Pollution Control Act.”

**What is not settled for sheds** (and for playhouses, play equipment, storage containers, fences, walls and retaining
walls; r51, `depends`):

1. **Whether (c) reaches the work at all.** It exempts work “in any single-family residence, farm building, or
   commercial building”. Whether building a detached shed in the yard is work "in" the residence is not answered by
   the text.
2. **If (c) does reach it,** a new shed's walls and roof framing are arguably “load-bearing structures”. That would
   take a new shed back out of the exclusion. Nothing in the statute says how far (c)(1) goes for small accessory
   structures.
3. **Either way, (a) defers to the Code.** Whether the North Carolina Residential Code, or the Code's administrative
   chapter, requires a permit for a small accessory building is in the code books. They are not on disk, and lexflow
   may store at most the facts of them, never their text (data-expansion.md E5).
4. The statute knows accessory buildings as a category: 160D-1110(g) excuses the lien-agent condition “or to the
   addition of an accessory building or accessory structure as defined in the North Carolina Residential Code”. But it
   says nothing about exempting small ones from permits. The checker confirms that "shed" does not occur in
   160D-1110, and that § 143-138 mentions sheds only in its farm, equine and camping exclusions ((b4)).

To settle it, a person reads the administrative chapter and the Residential Code's scope in the free official view,
and records the threshold as a model-code fact with its citation and edition (no text). That is the
`model-code-fact` source type that [data-building-codes.md](data-building-codes.md) §4.2 proposes. The NC rows would
then gain conditions, as the VA and DC rows have, and the readings above would be confirmed or corrected.

---

## 4. Readings

Thirty-two citations carry the grounding `implied`. Each is marked "(reading)" in the rule's "Source" column, and each
states its reading in a note:

| Rule | Reading |
|---|---|
| r3, r20 (VA shed over 256 sq ft, addition) | an industrialized building is answered as a site-built one, since 429.5 applies the permit requirements to its site work |
| r5 (VA attached shed) | an attached shed adds a wall to the dwelling (108.1 item 1) |
| r7 (VA deck) | no 108.2 item names decks, so a deck is construction of a structure; and 101.7 replaces a model-code deck exemption (two marks) |
| r8 (VA resurfacing) | a deck is a structure, and replacing its boards is a repair of it |
| r11, r12 (VA pool fence, new or repaired) | building or repairing such a fence is construction of a structure |
| r29, r60 (DC historic playhouse, play equipment) | 105.2.5 does not list item 13 or 12; the structure may be an "other site feature" under 10-C DCMR 304.1(h) (two marks each) |
| r32, r39, r64 (DC deck, masonry wall, farm building) | with no 105.2 item, the work is construction of a structure under 105.1 |
| r33 (DC resurfacing) | 105.2.2 says only what ordinary repairs exclude, so whether resurfacing is one is not settled |
| r34 (DC fence) | item 7's replacement-in-kind list has no fences, so item 4 does not reach a replacement |
| r47, r50 (NC deck, addition) | the framing is "load-bearing structures"; for r47, also that the Code requires the permit (three marks) |
| r49, r66, r69 (NC resurfacing over $40,000, a duplex's resurfacing, trade work) | the Code requires the permit |
| r51 (NC sheds and walls) | points 1, 3 and 4 of §3.3 (three marks) |
| r54 (VA farm building in a flood plain) | the special flood hazard area is the "flood plain" of 102.3 item 9 |
| r56 (VA trade work) | an item exempting a structure does not exempt the wiring or piping made with it |
| r57 (VA trade work with a 102.3 structure) | whether the whole-code exemption reaches the trade work is not settled |
| r62 (DC storage container) | placing a container for storage is erecting a structure; item 17 turns on a section not on disk (two marks) |
| r67 (NC townhouse resurfacing) | whether a townhouse unit is a "single-family residence" is not settled |

---

## 5. What local amendments can change

**Virginia.** The exemption list is the same in every city, county and town, and a locality cannot amend it:

* 102.2 and Va. Code § 36-98 make the USBC supersede local building regulations (quoted in §3.1).
* What a locality controls:
  * **enforcement**: “Enforcement of the provisions of the USBC for construction and rehabilitation shall be the
    responsibility of the local building department.” (104.1). Its building official exercises the discretion of items 13
    and 14.11 and Exceptions 1 and 2. Exception 2 is where the model answers `depends`; items 13 and 14.11 are the
    caveats on its `yes` answers for decks, deck resurfacing and pool-barrier repairs (§2.1);
  * **fees**: “The local governing body shall establish a fee schedule incorporating unit rates, which may be based on
    square footage, cubic footage, estimated cost of construction, or other appropriate criteria.” (107.1.1), plus the
    state levy, under which “the local building department shall collect a 2.0% levy of fees charged for permits issued
    under this code” (107.2);
  * **the application form**: “The application for a permit shall be submitted on a form supplied by the local
    building department.” (108.6). By mail is always allowed: “In no case shall an applicant be required to appear in
    person.” (108.3);
  * **zoning, historic districts and floodplain rules**, which the USBC leaves in place (`other_approvals`). A shed
    that needs no building permit can still need a zoning clearance, a certificate of appropriateness or a floodplain
    permit.
* **Who enforces.** Usually the locality: “towns with a population of less than 3,500 may elect to administer and
  enforce the Building Code; however, where the town does not elect to administer and enforce the Building Code, the
  county in which the town is situated shall administer and enforce the Building Code for the town.” (Va. Code
  § 36-105). For a town inside Albemarle County, the county's office answers unless the town has elected to enforce.
  Whether any town there has elected was not checked.
* **The edition changes statewide**, when the Board of Housing and Community Development amends 13VAC5-63. The model
  must be re-checked then. The checker fails if a quote is no longer verbatim in a rebuilt index.

**District of Columbia.** There is no local layer below the District. The 2017 supplements change by DC rulemaking.
According to [data-building-codes.md](data-building-codes.md) §1.4 (not re-checked here), the Department of Buildings
aims to adopt the 2024 codes by the end of 2027. That would replace 12-A DCMR 105, and this model with it.

**North Carolina.** The Code is statewide: “Except as otherwise provided in this section, the North Carolina State
Building Code shall apply throughout the State, from the time of its adoption.” (143-138(e)). And: “No such code or
regulations, other than floodplain management regulations and those permitted by G.S. 160D-1128, shall be effective
until they have been officially approved by the responsible Code Council as providing adequate minimum standards to
preserve and protect health and safety”. A local variance cannot require a permit the $40,000 exclusion removes
(143-138(b5), quoted in §3.3). Local governments do keep three levers. First, “any political subdivision of the State
may adopt a fire prevention code and floodplain management regulations within its jurisdiction”, the fire prevention
code only once the Code Council approves it. Second, fire limits: a county may, and every city must, establish them
(G.S. 160D-1128), and inside a city's primary fire limits “no frame or wooden building or structure or addition
thereto shall hereafter be erected, altered, repaired, or moved, either into the limits or from one place to another
within the limits, except upon the permit of the local inspection department” (a county's fire limits may include only
business and industrial areas). Third, historic districts: “A certificate of appropriateness is required whether or
not a building or other permit is required.” (160D-947(a)).

So `jurisdiction` is a state code, not a locality. The local layer is the office, the form, the fee, and the other
approvals, not the answer. The DMN's `jurisdiction` description says the same and points here.

---

## 6. How the Charlottesville, Albemarle and Staunton processes should cite it

The three places' building-permit processes are recorded in the discovery fixtures. The DMN lists them as consumers
(`lex:consumer`). The curated place files (`curated/places/va/*`) are being edited elsewhere, so this note only says what
they should contain. It changes none of them.

| Place (gov_id) | Process id | Fixture |
|---|---|---|
| City of Charlottesville (47210400100000) | `building_permit` | `fixtures/places/va/discovery-charlottesville.json` |
| Albemarle County (47100200200000) | `building_permit_residential` | `fixtures/places/va/discovery-albemarle.json` |
| City of Staunton (47213000100000) | `residential_building_permit` | `fixtures/places/va/discovery-staunton.json` |

**1. The first step decides.** Each process's BPMN should open with a business-rule task, "Decide whether a permit is
needed". Its `decisionRef` is the decision `d_permit_required` (named `permit_required`; the model is
`lexflow:decision:permit_required`), with `jurisdiction` fixed to `"va"`. It asks only the questions of §2.2 for the
project, including `trade_work`. The gateway after it has three branches:

* `no`: end, and show `other_approvals`;
* `depends`: a user task to ask the building official, using the office the place file records (NDS Building
  Inspections; Community Development, Building Inspections; Community Development, Building Services Division);
* `yes`: the application steps (108.3 to 108.6), the fee (107), issue, and the inspections. When the basis names item
  13 or 14.11, the first step of this branch is to ask the building official whether the item applies.

For Albemarle, whose county has farms, the project `farm_building` matters: 102.3 item 9 takes farm buildings out of
the USBC, which a "shed" answer would miss.

**2. The legal basis cites the regulation, not only the statute.** Today the fixtures cite Va. Code §§ 36-98 and
36-105 as "hint, not verified" (Charlottesville), as "lexflow index (va)" (Albemarle), or as bare citations, with
§ 36-97 (Staunton). They should add 13VAC5-63-80 with the item
pinpoint the answer used, and 13VAC5-63-20 B, each with the official URL and the index as the source. In
Charlottesville's shape (`legal_basis.state`):

```json
{"citation": "13VAC5-63-80 B (USBC 108.2), item 2",
 "title": "Section 108 Application for permit",
 "url": "https://law.lis.virginia.gov/admincode/title13/agency5/chapter63/section80/",
 "source": "lexflow regulations index (va), open-us-law v2026.09.1; checked by out/design/check_permit_required.py",
 "decision": "lexflow:decision:permit_required", "rule": "d_permit_required_r1"}
```

The last two fields are new: they tie the citation to the rule that used it. Albemarle's file uses `{"cite", "url",
"source", "note"}` and Staunton's a `va_code` list of strings. The same citation
and URL go in each, with `13VAC5-63-20 B (USBC 102.2)` beside it for why a city or county cannot vary the list.

**3. Quote the state text, and cite the local page as guidance.** The Albemarle fixture records the county's building
code page, read from an Internet Archive copy, as saying "Tool sheds and playhouses less than 256 square feet (zoning
and health department, if applicable, is required)". The regulation says “does not exceed 256 square feet”. At exactly
256 sq ft the two differ, and the regulation governs (case A4). The process should quote 108.2 item 2 and link the
county page as the office's guidance. The page's note that zoning still applies matches `other_approvals`.

**4. The other approvals link to the places' own processes.** For `historic = true`: Charlottesville's and Staunton's
`certificate_of_appropriateness` processes (the Staunton fixture cites Va. Code § 15.2-2306 and its City Code § 18.85).
For `flood_hazard_area = true`: Albemarle's `floodplain_development_permit`. For zoning: each place's zoning clearance
or zoning question process. These are links of the kind the cross-process schema in
[bpc-480-decision.md](bpc-480-decision.md) §6 describes (`lex:requires` with `providedBy`).

**5. Local facts stay local.** These include:

* the fee schedules: Charlottesville's Building Permit Fee Schedule (PDF), Albemarle's fee schedule (accessory
  structures, per the fixture), Staunton City Code § 15.10.120;
* the portals, and Staunton's deck supplemental form;
* Charlottesville's note that permits issued since January 18, 2025 are under the 2021 code. That fits 103.2's one-year
  choice after the January 18, 2024 effective date.

Staunton's "When do I need a permit" page is linked from its process. It was not read here. When the place file is
curated, its list should be compared with the model's answers, and any difference noted as guidance against the
regulation.

---

## 7. Validation (the runs after the revision, 2026-10-10 and 11)

Run as the checker's docstring says (copy the model into a temporary directory in `lexflow-app-1`, run, remove). All
7 groups pass, in 6 to 7 minutes of wall time (357 s and 434 s in the two final runs):

1. **Schema and tools**: the OMG DMN 1.3 XSD, dmnlint (recommended rules) and bpmn.io's dmn-moddle import (32 DRG
   elements, no warnings).
2. **DRD integrity**: hrefs, requirement kinds, columns equal information requirements, variable names, no cycles,
   authority for every rule's citations, nothing unused, UNIQUE everywhere, declared output values, 32 shapes and 38
   edges.
3. **Words**: 229 quotes verbatim in the index and in the subdivision each cites. URLs and act ids are the index rows'.
   13 knowledge sources resolve. 32 "(reading)" marks match the groundings, and every reading has its note. The checker
   also verifies the readings' factual premises:
   * "deck" occurs in VA 108.2 only in item 14.6;
   * DC 105.2's Building items name no deck;
   * DC 105.2.5 lists items 1, 4, 5, 7, 8, 9 and 10;
   * "shed" does not occur in G.S. 160D-1110, and § 143-138 mentions sheds only in (b4);
   * 102.3 items 7, 8, 9 and 11 are play equipment, industrialized buildings, farm buildings and storage containers;
     the VCC's "Construction" includes repair; 429.5 applies the permit requirements to an industrialized building's
     site work;
   * "wiring" occurs in VA 108.2 only in item 1; DC's ordinary repairs exclude electric wiring; DC item 7's list names
     no fence; DC item 12 is playground equipment;
   * NC's exclusion ((c) and (b5)) names a single-family residence and no two-family dwelling.

   It also checks the descriptions the verification asked to correct (`fence_repair` is repair in kind only, column
   caps, the local-amendment part, the rule for the officials' discretion), and that there is no ICC or UpCodes link,
   IRC or IBC title, or "IRC R105" or "IBC 105" pinpoint.
4. **Conflict and empty, over the whole domain**: 1,611 grid points in 36 slices for `permit_required` and 12 for
   `other_approvals`, plus a random sample of 4,000 points of each full product. Exactly one rule matches everywhere.
5. **81 cases** hit all 81 rules, and SpiffWorkflow agrees with lexflow's evaluator on every case and every grid point
   (1,623 evaluations). The 30 cases marked with a finding id (W1 to W5, M1 to M6) each fail on the model as it stood
   before the revision; part 9 lists them.
6. **This note**: all 117 curly-quoted spans are verbatim state text.
7. **Mutations**: 219 output changes (permit, exemption, other approvals); 2,760 single input-cell changes; and 97
   consistent moves (thresholds shifted, opened or closed in every cell of their column, and booleans negated across a
   slice). Groups 4 and 5 catch every one. Group 4 catches every single-cell change. The consistent moves keep the table
   a partition within their slice, so the cases must catch them: group 5 catches 60. The other 37 negate a boolean in
   rules that another slice shares (the trade-work rules span every project of their jurisdiction), which breaks that
   slice, so group 4 catches them. The boundary cases at 256 and 257 sq ft, 50 and 51, 36 and 37, 6 and 7 ft, 4 and 5
   ft, 9.5 and 10 ft, 2.5 and 3 ft of fill, and $40,000 and $40,001 are there for them.

The cases are listed in `CASES` in the checker. Each one states the answer, the exemption item, the rule it must hit,
and what `other_approvals` must mention, independently of the model.

---

## 8. Open questions and limits

1. **North Carolina sheds, fences and walls** (§3.3), and the readings behind the NC `yes` answers. Settling them
   needs the NC Code's administrative chapter and Residential Code scope, read in the free official view and recorded
   as facts. Whether facts taken from ICC-published state code books may be stored is counsel's C16, and their status
   is the same question as Florida's (C17 in [data-expansion.md](data-expansion.md)).
2. **The officials' calls.** Virginia's items 13 and 14.11 are caveats on `yes` answers; Exception 2, DC's ordinary
   repairs (105.2.2), and the Historic Preservation Office's view of playhouses and play equipment are `depends` by
   design (§2.1). A place process can narrow them only with the office's own published guidance, cited as guidance.
3. **Judgement calls taken conservatively**, each stated where it is made: a DC fence replacement in kind is a new
   fence (`yes`, §3.2); a Virginia farm building in a special flood hazard area is `depends` (§3.1); trade work with a
   Virginia whole-code structure is `depends` (§3.1); a DC storage container is `depends` (§3.2); a North Carolina
   townhouse's resurfacing is `depends` and a duplex's is `yes` (§3.3).
4. **Model-code references inside state text.** VA item 5 refers to Section 3306, and DC item 17 to Section 3103, both
   from the incorporated model codes; VA 101.7 refers to "the IBC". The model takes `safety_barrier` as an input,
   quotes only the state text, and answers `depends` where the DC answer would turn on 3103.
5. **Out of scope:** pools, signs, and repairs other than deck resurfacing and fence repair. So are commercial and
   multi-family buildings, and New York (Part 1203 is not on disk; D25). Trade work is an input (`trade_work`), but the
   model says only whether a permit is needed for it, not which trade permit or who may pull it.
6. **Licensing.** The text comes from the CC BY-NC open-us-law compilation (C1, C2), and state text that mirrors ICC
   wording raises C21. This note quotes state text only, with citations and official URLs. The Wikibase would get the
   facts (citations, thresholds, links) only after counsel answers C2.
7. **Live checks.** Only the three pages listed at the top were read live, before the revision. The sections the
   revision added (13VAC5-63-10, -200 and -220, 10-C DCMR 303 and 320, G.S. 160D-1128) and the other DC and NC sections
   rest on the 2026-09-30 snapshot.

---

## 9. Changes after the verification

The verification ([verify-permit-required.md](verify-permit-required.md)) found five errors (W1 to W5) and six gaps
(M1 to M6). All were fixed; none was marked accepted. Each fix is pinned by checker cases or checks that fail on the
model as it stood before (264,822 bytes, 51 + 12 rules): run against it, the new cases fail 62 of 81, every case
marked with a finding id among them.

| Finding | Fix | Pinned by |
|---|---|---|
| W1. DC deck resurfacing in a Flood Hazard Area was `depends` | r33 now reads `flood_hazard_area = false`; new r58 answers `yes` ("12-A DCMR 105.2.2, not available under 105.2.6"), quoting 105.2 and 105.2.6. The summary and §2.2 list `flood` for DC deck resurfacing | case B13b; B13c keeps historic out of it |
| W2. DC `fence_repair` included "replacement in kind" | `fence_repair` is repair in kind only; a replacement is `fence`, `yes` (r34), with the item 4, item 7 and 105.2.5 tension in its basis and a reading note (a judgement call, taken conservatively) | case B14b; the checks on the `project` description and on item 7's list |
| W3. NC deck resurfacing was `no` for two-family dwellings | new input `dwelling`; r48 is single-family only; r66 (two-family, `yes`, a reading) and r67 (townhouse, `depends`) | cases C2b and C2c; C2 says "single-family"; the check on (c) and (b5) |
| W4. Officials' discretion handled inconsistently; r8 missed "Construction" | the rule is stated in the decision description and §2.1; r8 and r12 are `yes` with the item 14.11 caveat; 13VAC5-63-200 is cited, and the "structural component" reading is dropped | cases A12 and A17; the description check; the "Construction" premise check |
| W5. Wrong cross-reference, NC overstated, run time, "names no IBC section" | the `jurisdiction` description points at part 5 and states the NC levers (143-138(b5) and (e), 160D-1128); the run time is measured (part 7); the checker's and this note's model-code claims now say what is tested | the `jurisdiction` description check; the reworded model-code check |
| M1. Trade work had no input | new input `trade_work`; r56 (VA, `yes`), r57 (VA with a 102.3 structure, `depends`), r65 (DC, `yes`), r69 (NC, `yes`, a reading); every other rule reads `trade_work = false`, and its `no` or `depends` basis says the trade work needs a permit; VA `no` bases carry the 108.2 preamble | cases A26, A31, A32, B33 and C10; A1 says "must still meet the code"; the wiring premise checks |
| M2. Virginia's 102.3 whole-code exemptions were missing | new projects `playground_equipment`, `storage_container` and `farm_building`, with VA r52 to r55, DC r59 to r64 (item 12, containers, farm buildings) and NC r68 (143-138(b4)), plus r51 for NC play equipment and containers; industrialized buildings are cited on r3 and r20 (429.5, no change of answer) | cases A27 to A31, B27 to B32, C9 and C11; A2 says "429.5"; the 102.3 and 429.5 premise checks |
| M3. DC public-space permits (105.2.4) | every DC row of `other_approvals` says it and quotes it | every DC case requires "DDOT" in `other_approvals` |
| M4. 10-C DCMR 303 not cited | new knowledge source 10-C DCMR 303; r29 and r60 quote 303.1 and 303.3; r41 and r43 quote 304.2(e); §3.2 notes 10-C DCMR 320.1 for the process model | cases B9, B28, B21 and B23 |
| M5. The deck answer rested only on an absence | new knowledge source 13VAC5-63-10; r7 quotes 101.7 (a reading); the A3 paragraph cites it | case A3 says "101.7" |
| M6. NC erosion control uncited; VA column caps; NC readings | `other_approvals` r9 to r12 quote 160D-1110(e); `height_ft` and r13 and r15 exclude column caps; §3.3 says plainly that the NC `yes` answers would change if the code books exempt the work | every NC case requires "sedimentation"; case A18; the `height_ft` check |
