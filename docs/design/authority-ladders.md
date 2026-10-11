# Authority ladders: who you go to when a step goes wrong

Status: design, 2026-10-10. Nothing has been written to the DB, the DokuWiki, lexipedia.wikibase.cloud, Wikidata or
Govdirectory. The data is in [`fixtures/authority/ladders.json`](../../fixtures/authority/ladders.json).

The ladders answer two questions for each process:

* **Escalation.** What can a person do when a step goes wrong (a denial, no answer by the deadline, a fee
  dispute, a refusal to file or seal)? Which body do they go to, by when, and must they?
* **Hand-off.** Where does the process pass the matter to another body? That covers referral to the right
  custodian, consultation, delegation to a hearing office, and waiting on another body's decision.

Inputs:

* the curated process models (`curated/<state>/<question>.json`);
* the AskBench references (`curated_ask/<question>/<state>.json`);
* the statute text of every section quoted, read from the search index (open-us-law v2026.09.1);
* the cross-references in `fixtures/xref/gold_*.json`, and `lexflow/law/xref.py` for the other sections;
* `fixtures/entities/agencies.json`, plus 36 read-only Wikidata label searches;
* [entities-contacts.md](entities-contacts.md), [entities-sources.md](entities-sources.md),
  [terms-wikibase.md](terms-wikibase.md) and [links-codebase-map.md](links-codebase-map.md).

---

## 1. Key points

* **22 ladders with 143 rungs.** They cover every ladder asked for (14 of 14): public records in VA, DC, MD, CA,
  TX, FL and NY; business formation in FL and VA; record sealing in CA, MD and VA; licence denial after a conviction
  in CA and VA. Eight more were added because the models made them cheap: records in IL, NC, OH and WA, DC business
  formation, and licence denial in DC, MD and TX.
* **All quotes are grounded.** All 280 quotes were found verbatim in the section text, after whitespace and
  punctuation normalisation: 143 mechanism quotes, plus the trigger, deadline and supporting quotes. So all 143
  rungs are fully grounded.
  * 126 rungs need no inference at all.
  * 17 carry an `inferred` note. In 15 the statute does not name the forum, the venue or the trigger. The other 2
    record that lexflow models the post, not the person.
* **Ten mechanism types, all of them in use.**

  | Type | Rungs |
  |---|---|
  | judicial review | 45 |
  | referral | 21 |
  | internal appeal | 20 |
  | delegation | 14 |
  | deferral to another process | 13 |
  | advisory opinion | 8 |
  | oversight / inspector general | 8 |
  | external administrative review | 8 |
  | ombudsman / mediation | 4 |
  | compliance board | 2 |

  * Records ladders use all ten types.
  * Licence ladders are mostly internal appeal, delegation and judicial review.
  * Sealing ladders are mostly referral and judicial review (9 rungs each), because records move between
    custodians.
* **Deadlines.**
  * 67 rungs have a numeric deadline, and 52 of those carry a quote for the number itself.
  * 12 rungs depend on rules outside the corpus. Most are court rules: the Virginia Rules Part 2A, the Maryland
    Rules, the D.C. Court of Appeals rules, the California Rules of Court and the Florida appellate rules. One is a
    statute, the Illinois Administrative Review Law.
* **Cross-references find few hand-offs.**
  * Only 13 rungs have a cross-reference inside the quoted provision that resolves to another rung's section.
  * The other rungs name the next body in words: "petition the Mayor", "the Board", "the Circuit Court of Leon
    County", "the attorney general".
  * So finding ladders needs a body-mention finder (the `mentions` relation in
    [entities-contacts.md](entities-contacts.md) §1.4) as well as xref.
* **Authority attaches to posts, not to people.**
  * Statutes route escalation to "the head of the agency or a designee", "the officer for public information",
    "the FOIA officer", "the appointing authority of the custodian", "the Tax Commissioner", or "the chief judge or
    presiding judge".
  * The model needs **positions** as first-class items. It never needs the people who hold them.
* **Wikibase: do not bulk-import Govdirectory.** Add these bodies, office types and positions, and a few authority
  properties (§5).
  * Govdirectory publishes nothing for VA, DC, MD, TX, CA or FL.
  * None of the 90 ladder bodies is on a Govdirectory list. Two reach one only through a parent body.

## 2. Shape of a ladder

Each ladder has `state`, `process` and `source` (the model or reference, plus every section used), a one-line
`summary`, and its `rungs` in order. A rung has these fields:

| Field | Meaning |
|---|---|
| `trigger`, `trigger_codes`, `trigger_basis` | What goes wrong, in words and as codes: `denied`, `partial`, `deemed_denied`, `no_answer`, `fee`, `delay`, `wrong_custodian`, `refused_filing`, `appeal_denied` and so on. The basis is the quoted rule that turns silence into a denial, where one exists. |
| `who` | Who invokes the rung: requester, public body, court, prosecutor or any party. |
| `body_text`, `body` | The body as the statute names it, and the specific body for the jurisdiction. `body` has a proposed lexflow key (`lexflow:agency:…`, `lexflow:office-type:…`, `lexflow:position:…` or `lexflow:position-type:…`), a Wikidata QID and its match status, and `resolve_by` for generic bodies (venue, county of the place, profession, record holder). |
| `type`, `subtype` | One of the ten types, and a finer label. |
| `deadline`, `basis` | A list of time limits. Each limit has an amount, a unit, an anchor, who must act and a kind (filing limit, decision limit, hearing limit, minimum wait, cure period). Each also carries its own quote where the text supports it. `basis` cites the source of the time limits. |
| `section`, `quote` | The mechanism's section and pinpoint, and the verbatim words. |
| `mandatory`, `mandatory_note` | `true` when the rung is a duty of a body, or a step the person must take to keep the next rung. |
| `supporting_quotes`, `inferred`, `xref_links`, `model_ref` | Extra grounded quotes, the reader's inferences, cross-references to other rungs, and the step ids in the curated model. |

## 3. The ladders at a glance

| Ladder | Rungs, in order (abridged) | Silence rule | Exhaustion before court |
|---|---|---|---|
| VA records | FOIA officer → contact details of the body that holds the records → FOIA Council (advisory) → mandamus or injunction in general district or circuit court, heard within 7 days | deemed denial after 5 working days (+7) | none |
| DC records | FOIA officer → MPD only, for body-camera footage → Mayor (10 working days) → Superior Court; Council and Attorney General records go straight to court; Office of Open Government advises public bodies | deemed denial and deemed exhaustion after 15 (+10) working days | none |
| MD records | redirect to the custodian (10 working days) → Public Access Ombudsman (90 days; cannot compel) → PIA Compliance Board (within 30 days; decision within 30–120 days) → circuit court → Appellate Court; court referral to the appointing authority for discipline | late production counts as a denial; limits tolled while a dispute is pending | none (§ 4-1A-10(a)) |
| CA records | agency head or designee extends (by 14 days at most) → verified petition in superior court → extraordinary writ within 20 days | none | none |
| TX records | body must ask the attorney general within 10 business days (AG rules in 45) → complaints to the AG (no response, overcharge) or to the DA or county attorney (31 days) → mandamus in district court; the body sues the AG in Travis County within 30 days | information presumed public if the body misses its deadline | none |
| FL records | custodian's designee → search across the agency → AG mediation (voluntary) → 5-business-day pre-suit notice → civil action with an immediate hearing; 30-day record hold | no deadline at all | none (notice conditions fees) |
| NY records | appeal to the entity head (30 days to file, 10 business days to decide; copied to the Committee on Open Government) → Article 78 (4 months) → Appellate Division (30 days) | constructive denial at every stage | **yes** |
| IL / NC / OH / WA records | Public Access Counselor (binding) / mandatory mediation / 3-day cure then Court of Claims or mandamus / 2-day internal review, then AG opinion and court | deemed denial; deemed exhaustion (IL) / – / – / review deemed complete | none / **mediation** / **cure complaint** / review is automatic |
| FL business | refusal within 15 days → corrected filing within 60 days keeps the original date → Circuit Court of Leon County → civil appeal; not-for-profits may instead use an APA appeal within 30 days; local tax receipt waits on the fictitious-name filing | none | none |
| VA business | Supreme Court of Virginia only (petition within 120 days); correction petition to the SCC; local licence waits on the assumed-name certificate; licence tax: commissioner of the revenue (1 year) → Tax Commissioner (90/90 days) → circuit court | local appeal can be treated as denied after a year, on 30 days' notice | none |
| CA sealing | 15 days' notice to the prosecutor, who loses any appeal if silent → appeal → disposition report to DOJ; the prosecution can block automatic relief 90 days ahead (hearing within 45), after which the person falls back to a petition; record errors go to DOJ, then the source agency (30 days), then an APA hearing, then a writ | – | – |
| MD sealing | arresting unit, then the Central Repository and other units (60 + 60 days) → "any appropriate legal remedy"; court notices for 3-year automatic expungement; an objection by the State's Attorney forces a hearing | – | – |
| VA sealing | copy to the Commonwealth's attorney (30 days) → CCRE forwards the record → appeal within 30 days; order voidable for 2 years; clerk → State Police → Executive Secretary; automatic pipeline (State Police → Executive Secretary → clerk → chief judge) with a petition fallback | – | – |
| CA licence | hearing request within 60 days (else waived) → OAH judge (proposed decision deemed adopted after 100 days) → reconsideration (30 days, deemed denied) → writ of mandate within 30 days; a certificate of rehabilitation or a § 1203.4 dismissal bars denial; record errors go to DOJ | deemed adopted; deemed denied | none |
| VA licence | binding DPOR predetermination → named agency contact → 90-day decision clock, then deemed approval 30 days after notice → formal hearing (DPOR at the board's option; health boards on request within 30 days) → circuit court → Court of Appeals | **deemed approval** | health boards: a hearing request, or the order becomes final |
| DC / MD / TX licence | early petition (90 days) → response (45 + 45 business days) → hearing, panel or OAH → protest against a Mayor's official → D.C. Court of Appeals / hearing (OAH optional) → circuit court → Appellate Court / evaluation letter (90 days, binding) → 30-day response → SOAH → rehearing (25/55 days) → district court (30 days) | – / – / rehearing overruled by operation of law | full-board rehearing if requested / – / **motion for rehearing** |

## 4. Patterns across states

1. **Silence is handled five ways.**
   * Deemed denial: VA, DC, NY, IL, and Maryland for late production.
   * Deemed exhaustion: DC and IL.
   * Presumption of openness: in Texas, a body that misses its deadline to ask the attorney general loses the
     right to withhold.
   * Deemed approval: Virginia's APA, § 2.2-4021.
   * Nothing: California's CPRA and Florida's chapter 119, which sets no deadline at all.

   A process model needs a timer consequence for each, and the schema's `deemed-denial` value cannot express the
   Virginia and Texas cases. The curated VA licence model already notes this.
2. **Exhaustion is rare.** Only NY, OH and NC force an administrative step before court. In NC, mediation is a
   condition of the court's jurisdiction. Texas licensing requires a motion for rehearing. Elsewhere the
   administrative rungs are optional shortcuts, and the court is always open.
3. **The attorney general's office is the most common non-court escalation body.**
   * TX: binding rulings and complaints.
   * IL: the Public Access Counselor.
   * FL: mediation.
   * WA: opinions.
   * MD: it houses the Ombudsman and publishes Board decisions.
   * NC: reliance on an AG letter protects a body from a fee award.

   These are units *inside* one office, so Wikibase needs `part of` chains below the AG.
4. **Legislative and ethics bodies advise.** Examples are Virginia's FOIA Council (in the legislative branch) and
   D.C.'s Office of Open Government (inside an ethics board, and open to public bodies only). Advice is never a
   prerequisite to anything.
5. **Four bodies give binding administrative decisions between the custodian and the court:** the Maryland PIA
   Compliance Board, the D.C. Mayor, the Texas attorney general and the Illinois Public Access Counselor. Only
   Maryland's is a standing board. Hierarchical review by "the head" is the New York and Washington model.
6. **Fee disputes rarely have a forum.** Only TX (the AG), MD (the Ombudsman, and the Board above $350), WA (court
   review of estimates) and the Virginia licence tax have one. Elsewhere a fee dispute reaches an adviser, or
   counts as a denial (an inference).
7. **Hand-offs to the right custodian are statutory** in VA, MD, FL and DC. Consultation with another body is an
   extension ground in DC, CA and IL. In sealing, most rungs are hand-offs between record holders: court to DOJ or
   the State Police, then to the repositories and the Executive Secretary.
8. **Deferral is everywhere.**
   * Time limits are tolled or extended while a dispute is pending (MD, NC).
   * Records are held until a court decides (FL).
   * One forum stops when another starts (IL; the Ohio "only one, not both" rule).
   * Collection is suspended during an appeal (VA tax).
   * Local permits wait on state filings (FL, VA).
   * A licence outcome waits on a court's certificate or dismissal (CA).
   * Automatic relief falls back to a petition (CA, VA).
9. **Hearings are delegated.**
   * Mandatory: California's Office of Administrative Hearings, and Texas's State Office of Administrative
     Hearings (unless the agency has its own hearing officers).
   * Optional: Maryland and D.C. send hearings to their offices of administrative hearings, and D.C. appeals go
     back to the board. D.C. boards may also use 3-member panels.
   * Virginia boards decide how a hearing officer sits.
10. **Venue is relative.** It can be the county of the record or of the body, the requester's residence, or a
    fixed forum: Travis County, Leon County, Cook or Sangamon County, Richmond, or the Supreme Court of Virginia
    for the SCC. Generic court office types must resolve by a rule (`resolve_by`), as entities-contacts §1.5
    planned.

## 5. What this needs from the entity model and Wikibase

### 5.1 Importing all Govdirectory entities would not help

* **Coverage.** Govdirectory has three US lists: 374 federal entries (mostly embassies), 159 New York entries
  and 607 North Carolina entries ([entities-sources.md](entities-sources.md) §2.4). None of the 90 ladder bodies is
  on them. Two reach a listed item only through a parent: NY's Committee on Open Government, via the Department of
  State, and NC's mediators, via the Dispute Resolution Commission.
* **No data of its own.** Govdirectory adds nothing beyond Wikidata. Wikidata already gives QIDs for 17 of the 37
  specific ladder bodies. It gives 7 more only through a parent body and 2 only as position items. 6 bodies have
  no item: the VA FOIA Council, the MD PIA Compliance Board, the D.C. Office of Open Government, DPOR and the D.C.
  OAH, plus the NY Appellate Division, which was not searched. 5 QIDs come from label searches and need checking.
* **Better route.** Seed Wikibase from lexflow's own lists: `agencies.json` (144 entries), the 90 ladder bodies and
  the 98 courts. Wikidata is the crosswalk, as decisions D1–D3 of entities-contacts.md already set out.

### 5.2 What to add (each item is a wiki write that waits for your go-ahead, with a dry run first)

* **Item kinds.**
  * Agency, court and office type, as entities-contacts §1.7 already proposes.
  * Two new kinds:
    * **position**: `lexflow:position:<scope>:<slug>`, a specific post such as the Tax Commissioner or the
      Public Access Ombudsman;
    * **position type**: `lexflow:position-type:<st>:<slug>`, a post that exists in every body of a kind, such as
      the FOIA officer, the custodian, the officer for public information or the head-or-designee.
  * A position is `part of` (P9) its agency. It is never linked to a person.
* **Rungs as items.**
  * Key: `lexflow:rung:<st>:<process>:<section-slug>:<subtype-slug>`. It is keyed by the quoted provision, not by
    position in the ladder, so inserting a rung changes no key.
  * `retire_drafts` must learn the new kind.
  * Two quotes are over the 400-character string cap (`tx.records.8`, `ny.records.1`). Store their start and link
    to the DokuWiki page.
* **Existing properties that fit a rung.**
  * Type: P5 → one of ten new subclasses of an "escalation mechanism" class.
  * Ladder order: P9 → the process, and P11/P12 follows / followed by.
  * Statute: P13 → the statute section, with P22 citation.
  * Jurisdiction: P15.
  * **Mandatory or optional: P16 deontic modality.** Obligation for duties, Right for the person's remedies,
    Permission for a body's options.
  * **Who invokes it: P17 bearer → the role.**
  * **Trigger: P18 condition** → a trigger item from the vocabulary.
  * **Carve-outs: P21 defeated by**, for example "Council records skip the Mayor".
  * **Sanctions: P20 sanction**, for example Fla. Stat. § 119.10.
* **New properties** (no Wikidata equivalent except where noted):

  | Property | Datatype | Used on |
  |---|---|---|
  | decided by | item | rung → agency, office type, position or position type (the `body`) |
  | played by | item | role → body (already proposed in entities-contacts §1.7) |
  | time limit | quantity (unit: day, business day, month, year) | rung, with qualifiers `time limit anchor` (string) and `time limit holder` (item) |
  | delegates to | item | body or position → body or position (OAH, SOAH, panels, designees) |
  | appointing authority | item | position → position (MD § 4-362(e), the Ombudsman appointed by the AG) |
  | resolves by | string | office type → venue rule (`county_of_record`, `profession` and so on) |
  | exclusive forum | item (qualifier) | on `decided by`, for example the Supreme Court of Virginia for the SCC |

* **Cross-referencing a process against bodies and posts.** The chain is: step → role (P17) → played by → office
  type or agency → part of → government. A rung links to its step through `follows` and P18, and reaches its body
  through `decided by`. Queries then become simple, for example:
  * "for this step in this state, what is the next body and its deadline";
  * "every process that routes to the Tax Commissioner";
  * "where the power to extend a deadline sits";
  * "which remedies are optional".

### 5.3 People: only the post

* **Statutes that require a person to be named are met with the post.** Four do: the names and titles of those
  responsible for a denial (CA § 7922.540(b), IL 140/9(a)), the custodian's designee (FL § 119.07(1)(b)), and the
  agency's designated contact (VA § 2.2-4019(A)). Wikibase and lexflow store the post, not the person.
* **The office-holder rule stands.** entities-contacts §5.4 already drops office-holder claims from Wikidata
  responses.
* **Showing a holder (open question).** If a page ever needs the current holder of a public post, read it live
  from Wikidata. Use the position item with P39 and P580/P582, and show only the name and the dates. Never store
  it, and never attach contact details.
* **Third parties and victims** stay `lexflow:private-party`, or are left out.

### 5.4 Order of work

1. Review the QIDs marked "search match, unverified" and the inferred rungs. This is local work.
2. Seed the `agencies`, `office_types` and new `positions` tables from `agencies.json` and the `bodies` block of
   `ladders.json`.
3. Add an `authority_rungs` table, loaded from `ladders.json`, with `entity_links` relations `decided-by`,
   `delegates-to` and `appointing-authority`.
4. Only then, with your go-ahead: create the classes and properties on Lexipedia, dry-run the loader, and load.

## 6. Limits and open questions

* **Court rules are outside the corpus.** Many appeal and review deadlines live in them. Should the corpus add
  them? Twelve rungs depend on them.
* **Two sources are missing.** Md. Crim. Proc. § 10-105 (the general expungement petition) is missing from the
  downloaded text. The Florida suspension power behind § 119.10 sits in the state constitution.
* **Some type assignments are judgement calls.** Two examples are the D.C. Mayor's review as an external review,
  and Ohio's Court of Claims mediation referral as mediation. The vocabulary in `ladders.json` defines each type so
  that a reviewer can change them consistently.
* **The rungs have not been reviewed.** A curated model can cite a ladder's rungs once a person has reviewed them,
  under the same publishing rule as the models: only reviewed or agreed data goes to the wiki.
